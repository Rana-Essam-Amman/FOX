import mimetypes
import os
import pathlib
import shutil
from typing import Union
from urllib.parse import quote

from fastapi import BackgroundTasks, Depends, Path, Query, Request, UploadFile
from fastapi.params import File
from fastapi.responses import FileResponse, Response, StreamingResponse
from loguru import logger
from starlette.background import BackgroundTask

from app.config import config
from app.controllers import base
from app.security import require_authenticated_user, require_task_owner, ownership_store, TaskOwnershipRecord
from app.security.private_materials import list_owned_materials, record_owned_material
from app.security.private_bgm import list_owned_bgm, record_owned_bgm
from app.security.material_admission import MaterialAdmissionError, admit_video_materials
from app.security.material_resolution import MaterialNotFound
from datetime import datetime, timezone
from app.controllers.manager.base_manager import TaskQueueFullError
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.controllers.manager.redis_manager import RedisTaskManager
from app.controllers.v1.base import new_router
from app.controllers.base import verify_token
from app.models.exception import HttpException
from app.models.schema import (
    AudioRequest,
    BgmRetrieveResponse,
    BgmUploadResponse,
    SubtitleRequest,
    TaskDeletionResponse,
    TaskListResponse,
    TaskQueryRequest,
    TaskQueryResponse,
    TaskResponse,
    TaskVideoRequest,
    VideoMaterialUploadResponse,
    VideoMaterialRetrieveResponse
)
from app.services import bgm as bgm_service
from app.services import material_upload as material_upload_service
from app.services import state as sm
from app.services import task as tm
from app.utils import file_security, utils

# 统一在 V1 视频路由入口执行鉴权：先验证 Bearer JWT 得到身份（属主隔离依赖它），
# 再按管理员配置校验共享 api_key；api_key 为空时只跳过共享密钥检查，JWT 仍必需。
router = new_router(dependencies=[Depends(require_authenticated_user), Depends(verify_token)])

_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)
_max_concurrent_tasks = config.app.get("max_concurrent_tasks", 5)
_max_queued_tasks = config.app.get("max_queued_tasks", 100)


def _build_redis_url(host: str, port: int, db: int, password: str | None) -> str:
    # Passwords are URL userinfo. Escape reserved characters so Redis receives
    # the exact configured secret rather than parsing part of it as a host,
    # port, path, query, or fragment.
    auth = f":{quote(password, safe='')}@" if password else ""
    # URL authorities require brackets around IPv6 literals. RedisState also
    # accepts a plain IPv6 host, so keep the queue client compatible with it.
    url_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"redis://{auth}{url_host}:{port}/{db}"


redis_url = _build_redis_url(_redis_host, _redis_port, _redis_db, _redis_password)
# 根据配置选择合适的任务管理器
if _enable_redis:
    task_manager = RedisTaskManager(
        max_concurrent_tasks=_max_concurrent_tasks,
        redis_url=redis_url,
        max_queued_tasks=_max_queued_tasks,
    )
else:
    task_manager = InMemoryTaskManager(
        max_concurrent_tasks=_max_concurrent_tasks,
        max_queued_tasks=_max_queued_tasks,
    )


def _sanitize_upload_filename(filename: str, request_id: str) -> str:
    # 浏览器或客户端有时会附带目录信息，甚至可能夹带 ../ 这类穿越片段。
    # 这里只保留纯文件名，避免上传接口把文件写到目标目录之外。
    normalized_name = (filename or "").replace("\\", "/").split("/")[-1].strip()
    if not normalized_name or normalized_name in {".", ".."}:
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message=f"{request_id}: invalid filename",
        )
    return normalized_name


def _resolve_path_within_directory(base_dir: str, unsafe_path: str, request_id: str) -> str:
    try:
        return file_security.resolve_path_within_directory(base_dir, unsafe_path)
    except ValueError as exc:
        logger.warning(
            f"reject unsafe file path, request_id: {request_id}, path: {unsafe_path}, "
            f"error: {str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=404 if str(exc) == "file does not exist" else 403,
            message=f"{request_id}: invalid file path",
        )


def _public_task_data(task: dict) -> dict:
    """复制任务状态并移除仅用于服务端进程协调的内部字段。"""
    public_task = dict(task)
    public_task.pop("cross_post_owner", None)
    return public_task


def _task_file_to_uri(file: str, endpoint: str, task_dir: str, request_id: str) -> str:
    if not isinstance(file, str):
        return file

    if file.startswith(("http://", "https://")):
        return file

    try:
        resolved_path = file_security.resolve_path_within_directory(task_dir, file)
    except ValueError as exc:
        # 任务状态理论上只应保存任务目录内的产物路径。这里不再继续拼接 URL，
        # 避免把异常路径包装成可访问链接；同时保留原值，便于排查历史脏数据。
        logger.warning(
            f"skip unsafe task output path, request_id: {request_id}, path: {file}, "
            f"error: {str(exc)}"
        )
        return file

    relative_path = os.path.relpath(
        resolved_path, os.path.realpath(task_dir)
    ).replace("\\", "/")
    # Private task outputs are served only through authenticated,
    # ownership-checked endpoints. Static /tasks mount has been removed.
    uri_path = f"api/v1/download/{quote(relative_path, safe='/')}"
    if endpoint:
        return f"{endpoint.rstrip('/')}/{uri_path}"
    return f"/{uri_path}"


def _task_response_data(task: dict, endpoint: str, task_dir: str, request_id: str) -> dict:
    response_task = _public_task_data(task)
    for key in ("videos", "combined_videos"):
        if key in task:
            response_task[key] = [
                _task_file_to_uri(file, endpoint, task_dir, request_id)
                for file in task[key]
            ]
    for key in ("audio_file", "subtitle_path"):
        if task.get(key):
            response_task[key] = _task_file_to_uri(
                task[key], endpoint, task_dir, request_id
            )
    return response_task


def _parse_byte_range(
    range_header: str | None, file_size: int, request_id: str
) -> tuple[int, int]:
    """解析单段 HTTP Range，并把无效或越界请求稳定转换成 416。"""
    # 416 只用于回应 Range 请求。没有 Range 时空文件也是完整表示，
    # 返回 0 字节的 200，与 /download 的行为一致。
    if not range_header:
        return 0, file_size - 1

    if file_size <= 0:
        raise HttpException(
            task_id=request_id,
            status_code=416,
            message=f"{request_id}: requested range is not satisfiable",
        )

    try:
        # 视频播放器这里只需要单段 bytes range。拒绝多段请求可以避免返回体
        # 与 Content-Range 不一致，也避免异常字符串落入 int() 产生 500。
        unit, separator, positions = range_header.strip(" \t").partition("=")
        if unit.lower() != "bytes" or not separator or "," in positions:
            raise ValueError("unsupported range format")
        start_text, end_text = positions.split("-", 1)
        if not start_text and not end_text:
            raise ValueError("empty range")
        # HTTP positions use ASCII DIGIT, not Python's broader int syntax.
        if any(value and not (value.isascii() and value.isdigit())
               for value in (start_text, end_text)):
            raise ValueError("invalid byte position")

        if not start_text:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise ValueError("invalid suffix length")
            start = max(file_size - suffix_length, 0)
            end = file_size - 1
        else:
            start = int(start_text)
            end = int(end_text) if end_text else file_size - 1
            if start < 0 or start >= file_size or end < start:
                raise ValueError("range outside file")
            end = min(end, file_size - 1)
    except (TypeError, ValueError) as exc:
        logger.warning(
            f"reject invalid video range, request_id: {request_id}, "
            f"range: {range_header}, file_size: {file_size}, error: {str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=416,
            message=f"{request_id}: requested range is not satisfiable",
        ) from exc

    return start, end


@router.post("/videos", response_model=TaskResponse, summary="Generate a short video")
def create_video(
    background_tasks: BackgroundTasks, request: Request, body: TaskVideoRequest
):
    return create_task(request, body, stop_at="video")


@router.post("/subtitle", response_model=TaskResponse, summary="Generate subtitle only")
def create_subtitle(
    background_tasks: BackgroundTasks, request: Request, body: SubtitleRequest
):
    return create_task(request, body, stop_at="subtitle")


@router.post("/audio", response_model=TaskResponse, summary="Generate audio only")
def create_audio(
    background_tasks: BackgroundTasks, request: Request, body: AudioRequest
):
    return create_task(request, body, stop_at="audio")


def create_task(
    request: Request,
    body: Union[TaskVideoRequest, SubtitleRequest, AudioRequest],
    stop_at: str,
    user=None,
):
    if user is None:
        user = require_authenticated_user(request)
    from app.security.rate_limit import rate_limiter
    rate_limiter.check_request(user, base.get_task_id(request))
    rate_limiter.check_generation(user, base.get_task_id(request))
    # Every local material reference (material_id and each video_materials
    # entry) is resolved against the authenticated owner before admission.
    # Any foreign, unowned, unknown or malformed reference rejects the request.
    if stop_at == "video" and isinstance(body, TaskVideoRequest):
        try:
            body.video_source, body.video_materials = admit_video_materials(
                video_source=body.video_source,
                material_id=body.material_id,
                materials=body.video_materials,
                owner_id=user.sub,
                storage_dir=utils.storage_dir("local_videos", create=True),
                lookup=ownership_store.get,
            )
        except MaterialNotFound:
            raise HttpException(
                task_id=base.get_task_id(request),
                status_code=404,
                message="material not found",
            )
        except MaterialAdmissionError as exc:
            raise HttpException(
                task_id=base.get_task_id(request),
                status_code=400,
                message=str(exc),
            )
    task_id = utils.get_uuid()
    request_id = base.get_task_id(request)
    try:
        if (
            stop_at == "video"
            and isinstance(body, TaskVideoRequest)
            and body.subtitle_enabled
        ):
            tm.video.validate_subtitle_colors(body)
            # 字体名可由 API 客户端直接提交，不能等到后台渲染时才发现路径越界。
            # 这里与渲染层共用目录边界校验，让非法请求在创建付费任务前返回 403/404。
            # Route the font pre-check through the file-serving
            # wrapper so the 403/404 error codes match the other
            # task-output paths in this file instead of 400. The
            # create_task outer except ValueError no longer covers
            # this branch.
            _resolve_path_within_directory(
                utils.font_dir(),
                body.font_name or "STHeitiMedium.ttc",
                request_id,
            )
        task = {
            "task_id": task_id,
            "request_id": request_id,
            "params": body.model_dump(),
        }
        if not sm.state.create_task(task_id):
            raise HttpException(
                status_code=409,
                message="Task identifier collision; please retry the request",
            )
        try:
            ownership_store.create(
                TaskOwnershipRecord(
                    task_id=task_id,
                    owner_id=user.sub,
                    created_at=datetime.now(timezone.utc),
                    kind=stop_at,
                    metadata={"request_id": request_id, "policy": "user"},
                )
            )
        except Exception:
            # Ownership must exist before the task can be admitted to the queue.
            # If persistence fails after the database committed but its
            # acknowledgement was lost, remove a possibly-created owner record
            # as well as the initial state record.
            try:
                sm.state.authorized_delete(task_id)
            except Exception as cleanup_exc:
                logger.error(
                    f"failed to clean task state after ownership failure, "
                    f"task_id={task_id}: {cleanup_exc}"
                )
            try:
                ownership_store.delete(task_id, user.sub)
            except Exception as cleanup_exc:
                logger.error(
                    f"failed to clean ownership after persistence failure, "
                    f"task_id={task_id}: {cleanup_exc}"
                )
            raise
        try:
            task_manager.add_task(
                tm.start, task_id=task_id, params=body, stop_at=stop_at
            )
        except Exception:
            # 状态记录在调度前创建，默认标记为 processing。如果调度器没能
            # 接管任务（例如线程启动失败或 Redis 队列不可用），必须回滚该
            # 记录，否则 API 和 WebUI 会永久展示一个实际从未运行的任务。
            # Also remove the ownership record so it cannot become an orphan.
            sm.state.authorized_delete(task_id)
            try:
                ownership_store.delete(task_id, user.sub)
            except Exception as cleanup_exc:
                logger.error(f"failed to clean ownership after queue failure, task_id={task_id}: {cleanup_exc}")
            raise
        logger.success(f"Task created: {utils.to_json(task)}")
        return utils.get_response(200, task)
    except TaskQueueFullError as e:
        logger.warning(
            f"reject task because queue is full, request_id: {request_id}, task_id: {task_id}"
        )
        raise HttpException(
            task_id=task_id, status_code=429, message=f"{request_id}: {str(e)}"
        )
    except ValueError as e:
        raise HttpException(
            task_id=task_id, status_code=400, message=f"{request_id}: {str(e)}"
        )

@router.get("/tasks", response_model=TaskListResponse, summary="Get all tasks")
def get_all_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=1000),
    user=Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    endpoint = config.app.get("endpoint", "").rstrip("/")
    task_dir = utils.task_dir()
    # List only tasks owned by the authenticated user.
    owned_records = ownership_store.list_for_owner(user.sub, limit=1000)
    owned_ids = {r.task_id for r in owned_records}
    all_tasks, _ = sm.state.get_all_tasks(1, 10000)
    owned_tasks = [t for t in all_tasks if t.get("task_id") in owned_ids]
    total = len(owned_tasks)
    start = (page - 1) * page_size
    tasks = owned_tasks[start:start + page_size]

    response = {
        "tasks": [
            _task_response_data(task, endpoint, task_dir, request_id) for task in tasks
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
    return utils.get_response(200, response)



@router.get(
    "/tasks/{task_id}", response_model=TaskQueryResponse, summary="Query task status"
)
def get_task(
    request: Request,
    task_id: str = Path(..., description="Task ID"),
    query: TaskQueryRequest = Depends(),
    user=Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    endpoint = config.app.get("endpoint", "").rstrip("/")
    require_task_owner(task_id, user)
    task = sm.state.get_task(task_id)
    if task:
        task_dir = utils.task_dir()
        response_task = _task_response_data(task, endpoint, task_dir, request_id)
        return utils.get_response(200, response_task)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.delete(
    "/tasks/{task_id}",
    response_model=TaskDeletionResponse,
    summary="Delete a generated short video task",
)
def delete_video(request: Request, task_id: str = Path(..., description="Task ID"), user=Depends(require_authenticated_user)):
    request_id = base.get_task_id(request)
    require_task_owner(task_id, user)
    task = sm.state.get_task(task_id)
    if task:
        if tm.is_task_busy(task):
            logger.warning(
                f"refuse to delete busy task, request_id: {request_id}, "
                f"task_id: {task_id}, state: {task.get('state')}, "
                f"cross_post_state: {task.get('cross_post_state')}"
            )
            raise HttpException(
                task_id=task_id,
                status_code=409,
                message=f"{request_id}: task is still running",
            )

        tasks_dir = utils.task_dir()
        current_task_dir = os.path.join(tasks_dir, task_id)
        if os.path.exists(current_task_dir):
            try:
                shutil.rmtree(current_task_dir)
            except FileNotFoundError:
                # Another completed-task deletion may remove this directory
                # after our existence check. Only accept an absent root;
                # partial deletion and other filesystem errors must keep state.
                if os.path.lexists(current_task_dir):
                    raise

        sm.state.authorized_delete(task_id)
        ownership_store.delete(task_id, user.sub)
        logger.success(f"video deleted: {utils.to_json(task)}")
        return utils.get_response(200)

    raise HttpException(
        task_id=task_id, status_code=404, message=f"{request_id}: task not found"
    )


@router.get(
    "/musics", response_model=BgmRetrieveResponse, summary="Retrieve local BGM files"
)
def get_bgm_list(request: Request, user=None):
    if user is None:
        user = require_authenticated_user(request)
    # Built-in presets are shared. User uploads are owner-scoped and never
    # include another user's files or unowned legacy uploads.
    builtin = []
    for file in bgm_service.list_builtin_bgm_files():
        filename = os.path.basename(file)
        try:
            size = os.path.getsize(file)
        except OSError as exc:
            logger.warning(f"skip unavailable background music: name={filename}, error={exc}")
            continue
        builtin.append({"name": filename, "size": size, "file": filename})
    owned = list_owned_bgm(user.sub, bgm_service.uploaded_bgm_dir(create=True))
    response = {"files": builtin + owned}
    return utils.get_response(200, response)


@router.post(
    "/musics",
    response_model=BgmUploadResponse,
    summary="Upload a background music file",
    description=(
        "Validate an MP3, M4A, AAC, WAV, FLAC, OGG, OPUS, or WMA file up to "
        "30 MB and store it under an immutable UUID filename in storage/bgm."
    ),
    responses={
        400: {"description": "The filename, format, size, or audio stream is invalid"},
        500: {"description": "FFmpeg validation or persistent storage is unavailable"},
    },
)
def upload_bgm_file(
    request: Request,
    file: UploadFile = File(...),
    user=None,
):
    if user is None:
        user = require_authenticated_user(request)
    from app.security.rate_limit import rate_limiter
    rate_limiter.check_request(user, base.get_task_id(request))
    request_id = base.get_task_id(request)
    stored_filename = None
    stored_path = None
    try:
        stored_filename = bgm_service.save_bgm_upload(file.filename, file.file)
        stored_path = os.path.join(
            bgm_service.uploaded_bgm_dir(create=True), stored_filename
        )
        # Ownership is recorded before the upload is returned. On failure the
        # helper removes only the file this request just wrote.
        record_owned_bgm(
            stored_path,
            stored_filename,
            file.filename or stored_filename,
            user.sub,
            request_id,
        )
    except bgm_service.BgmUploadError as exc:
        # 上传失败通常可以由用户更换文件后恢复，因此记录 request_id 和明确原因，
        # 但不输出文件内容或绝对路径，避免日志泄露用户数据。
        logger.warning(
            f"background music upload rejected: request_id={request_id}, error={str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message=f"{request_id}: {str(exc)}",
        )
    except bgm_service.BgmServiceError as exc:
        # 工具链或存储故障属于服务端问题，不能伪装成用户文件错误。日志保留
        # request_id 和内部原因，HTTP 响应只返回稳定文案，避免暴露服务器路径。
        logger.error(
            f"background music upload failed: request_id={request_id}, error={str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=500,
            message=f"{request_id}: background music validation is unavailable",
        )

    response = {"file": stored_filename}
    return utils.get_response(200, response)

@router.get(
    "/video_materials", response_model=VideoMaterialRetrieveResponse, summary="List the caller's private video materials"
)
def get_video_materials_list(request: Request, user=None):
    # Only materials with an ownership record for the caller are listed. Files
    # in the shared directory without a record (legacy/unowned) stay hidden.
    if user is None:
        user = require_authenticated_user(request)
    local_videos_dir = utils.storage_dir("local_videos", create=True)
    response = {"files": list_owned_materials(user.sub, local_videos_dir)}
    return utils.get_response(200, response)


@router.post(
    "/video_materials",
    response_model=VideoMaterialUploadResponse,
    summary="Upload the video material file to the local videos directory",
)
def upload_video_material_file(
    request: Request,
    file: UploadFile = File(...),
    user=None,
):
    if user is None:
        user = require_authenticated_user(request)
    from app.security.rate_limit import rate_limiter
    rate_limiter.check_request(user, base.get_task_id(request))
    request_id = base.get_task_id(request)
    try:
        # Keep accepting browser-supplied client paths, but persist an immutable
        # UUID storage key so repeated names cannot overwrite queued task inputs.
        safe_filename = _sanitize_upload_filename(file.filename, request_id)
        stored_filename = material_upload_service.save_material_upload(
            safe_filename, file.file
        )
        stored_path = os.path.join(utils.storage_dir("local_videos"), stored_filename)
        record_owned_material(
            stored_path, stored_filename, safe_filename, user.sub, request_id
        )
    except material_upload_service.MaterialUploadError as exc:
        logger.warning(
            f"local material upload rejected: request_id={request_id}, "
            f"error={str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message=f"{request_id}: {str(exc)}",
        )
    except material_upload_service.MaterialServiceError as exc:
        logger.error(
            f"local material upload failed: request_id={request_id}, "
            f"error={str(exc)}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=500,
            message=f"{request_id}: local material validation is unavailable",
        )

    response = {"file": stored_filename}
    return utils.get_response(200, response)


@router.post(
    "/materials",
    summary="Upload a private material (image or video) and return a material id",
)
def upload_material(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(require_authenticated_user),
):
    """Authenticated material upload. Owner is derived from the JWT subject.
    Returns material_id expected by the mobile client. Uses the existing
    validated material upload service (200 MiB video / 20 MiB image) and
    records an ownership entry so later retrieval can be owner-checked.
    If ownership persistence fails after the file is saved, the newly
    created file is deleted. Cleanup failure is logged; the original
    ownership exception is re-raised. Not atomic across filesystem and
    ownership storage.
    """
    from app.security.rate_limit import rate_limiter
    rate_limiter.check_request(user, base.get_task_id(request))
    request_id = base.get_task_id(request)
    stored_filename = None
    stored_path = None
    try:
        safe_filename = _sanitize_upload_filename(file.filename, request_id)
        stored_filename = material_upload_service.save_material_upload(
            safe_filename, file.file
        )
        stored_path = os.path.join(utils.storage_dir("local_videos"), stored_filename)
        # Ownership is recorded before the upload is returned; on failure the
        # helper removes only the file this request just wrote.
        record_owned_material(
            stored_path, stored_filename, safe_filename, user.sub, request_id
        )
    except material_upload_service.MaterialUploadError as exc:
        raise HttpException(
            task_id=request_id,
            status_code=400,
            message=f"{request_id}: {str(exc)}",
        )
    except material_upload_service.MaterialServiceError:
        raise HttpException(
            task_id=request_id,
            status_code=500,
            message=f"{request_id}: local material validation is unavailable",
        )
    # Best-effort size; mobile tolerates missing size/content_type.
    try:
        size = os.path.getsize(stored_path) if stored_path else None
    except OSError:
        size = None
    return utils.get_response(200, {
        "material_id": stored_filename,
        "content_type": file.content_type,
        "size": size,
    })


@router.get("/materials", summary="List materials owned by the authenticated user")
def list_materials(request: Request, user=Depends(require_authenticated_user)):
    """Return only materials owned by the authenticated principal."""
    owned = ownership_store.list_for_owner(user.sub, limit=200)
    materials = [
        {
            "material_id": r.task_id,
            "filename": (r.metadata or {}).get("filename"),
            "size": (r.metadata or {}).get("size"),
            "content_type": (r.metadata or {}).get("content_type"),
        }
        for r in owned
        if r.kind == "material"
    ]
    return utils.get_response(200, {"materials": materials})


@router.delete("/materials/{material_id}", summary="Delete an owned material")
def delete_material(
    request: Request,
    material_id: str = Path(...),
    user=Depends(require_authenticated_user),
):
    """Delete a material only if the caller is the owner.
    Object is removed first; ownership record is deleted only after
    successful object removal. Failure of either step is not reported
    as success.
    """
    request_id = base.get_task_id(request)
    record = ownership_store.get(material_id)
    if record is None or record.owner_id != user.sub or record.kind != "material":
        raise HttpException(
            task_id=request_id,
            status_code=404,
            message="material not found",
        )
    # Object deletion first. Ownership record stays if this fails.
    path = os.path.join(utils.storage_dir("local_videos"), material_id)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError as exc:
        logger.error(
            f"material object deletion failed, request_id={request_id}, "
            f"material={material_id}: {exc}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=503,
            message="material deletion failed; retry later",
        )
    # Ownership record only after object is gone.
    deleted = ownership_store.delete(material_id, user.sub)
    if not deleted:
        logger.error(
            f"ownership delete returned false after object removal, "
            f"request_id={request_id}, material={material_id}"
        )
        raise HttpException(
            task_id=request_id,
            status_code=503,
            message="material deletion incomplete; retry later",
        )
    return utils.get_response(200, {"deleted": material_id})


@router.get("/stream/{file_path:path}")
@router.head("/stream/{file_path:path}", summary="Inspect video stream metadata")
async def stream_video(request: Request, file_path: str, user=Depends(require_authenticated_user)):
    request_id = base.get_task_id(request)
    # file_path is expected to be "{task_id}/..." ; resolve ownership before serving
    parts = file_path.strip("/").split("/", 1)
    if not parts or not parts[0]:
        raise HttpException(task_id=request_id, status_code=404, message="task not found")
    task_id = parts[0]
    require_task_owner(task_id, user)
    tasks_dir = utils.task_dir()
    video_path = _resolve_path_within_directory(tasks_dir, file_path, request_id)
    range_header = request.headers.get("Range")
    if range_header and request.headers.get("If-Range") is not None:
        # This stream does not publish strong ETag/Last-Modified validators.
        # An unverifiable If-Range must fall back to the full representation,
        # so a client cannot combine old cached bytes with a new video tail.
        range_header = None
    # The body is produced after this handler returns. Open now so a task
    # deletion or replacement between headers and iteration cannot make the
    # stream fail or mismatch the size used for Content-Range.
    try:
        video_file = open(video_path, "rb")
    except FileNotFoundError as exc:
        raise HttpException(
            task_id=request_id,
            status_code=404,
            message=f"{request_id}: file no longer exists",
        ) from exc
    try:
        video_size = os.fstat(video_file.fileno()).st_size
        if request.method == "HEAD":
            # Range applies to GET only. Close before returning metadata; no
            # generator or deferred background cleanup is needed for HEAD.
            video_file.close()
            return Response(
                media_type="video/mp4",
                headers={"Accept-Ranges": "bytes", "Content-Length": str(video_size)},
            )
        start, end = _parse_byte_range(range_header, video_size, request_id)
    except Exception:
        video_file.close()
        raise
    length = end - start + 1

    def file_iterator():
        try:
            video_file.seek(start, os.SEEK_SET)
            remaining = length
            while remaining > 0:
                data = video_file.read(min(4096, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data
        finally:
            video_file.close()

    response = StreamingResponse(
        file_iterator(),
        media_type="video/mp4",
        background=BackgroundTask(video_file.close),
    )
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(length)
    if range_header:
        response.headers["Content-Range"] = f"bytes {start}-{end}/{video_size}"
        response.status_code = 206  # Partial Content

    return response


@router.get("/download/{file_path:path}")
@router.head("/download/{file_path:path}", summary="Inspect artifact download metadata")
async def download_video(request: Request, file_path: str, user=Depends(require_authenticated_user)):
    """
    download video
    :param request: Request request
    :param file_path: video file path, eg: /cd1727ed-3473-42a2-a7da-4faafafec72b/final-1.mp4
    :return: video file
    """
    request_id = base.get_task_id(request)
    parts = file_path.strip("/").split("/", 1)
    if not parts or not parts[0]:
        raise HttpException(task_id=request_id, status_code=404, message="task not found")
    task_id = parts[0]
    require_task_owner(task_id, user)
    tasks_dir = utils.task_dir()
    video_path = _resolve_path_within_directory(tasks_dir, file_path, request_id)
    file_path = pathlib.Path(video_path)
    filename = file_path.name
    media_type, _ = mimetypes.guess_type(filename)
    stat_result = None
    if request.method == "HEAD":
        try:
            stat_result = os.stat(video_path)
        except FileNotFoundError as exc:
            raise HttpException(
                task_id=request_id,
                status_code=404,
                message=f"{request_id}: file no longer exists",
            ) from exc
    response = FileResponse(
        path=video_path,
        filename=filename,
        media_type=media_type or "application/octet-stream",
        stat_result=stat_result,
    )
    if request.method == "HEAD":
        # Reuse FileResponse's metadata without reading its body or applying
        # GET-only Range processing to this HEAD request.
        return Response(headers=response.headers)
    return response
