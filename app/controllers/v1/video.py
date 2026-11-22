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
from app.controllers.manager.base_manager import TaskQueueFullError
from app.controllers.manager.memory_manager import InMemoryTaskManager
from app.controllers.manager.redis_manager import RedisTaskManager
from app.controllers.v1.base import new_router
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
from app.security import (
    require_authenticated_user,
    require_task_owner,
    ownership_store,
    TaskOwnershipRecord,
    rate_limiter,
    AuthenticatedUser,
    store_owned_material,
)
from datetime import datetime, timezone

# Protected routes require a verified JWT.
router = new_router(dependencies=[Depends(require_authenticated_user)])

_enable_redis = config.app.get("enable_redis", False)
_redis_host = config.app.get("redis_host", "localhost")
_redis_port = config.app.get("redis_port", 6379)
_redis_db = config.app.get("redis_db", 0)
_redis_password = config.app.get("redis_password", None)
_max_concurrent_tasks = config.app.get("max_concurrent_tasks", 5)
_max_queued_tasks = config.app.get("max_queued_tasks", 100)

def _build_redis_url(host: str, port: int, db: int, password: str | None) -> str:
    auth = f":{quote(password, safe='')}@" if password else ""
    url_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"redis://{auth}{url_host}:{port}/{db}"

redis_url = _build_redis_url(_redis_host, _redis_port, _redis_db, _redis_password)
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
    if not filename:
        raise HttpException(task_id=request_id, status_code=400, message="filename required")
    name = pathlib.Path(filename).name
    if not name or name in (".", ".."):
        raise HttpException(task_id=request_id, status_code=400, message="invalid filename")
    return name

def _resolve_path_within_directory(base_dir: str, unsafe_path: str, request_id: str) -> str:
    base = pathlib.Path(base_dir).resolve()
    candidate = (base / unsafe_path).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HttpException(task_id=request_id, status_code=403, message="path escapes base") from exc
    return str(candidate)

def _parse_byte_range(range_header: str | None, file_size: int, request_id: str) -> tuple[int, int]:
    if not range_header:
        return 0, file_size - 1
    if file_size <= 0:
        raise HttpException(task_id=request_id, status_code=416, message=f"{request_id}: requested range is not satisfiable")
    try:
        unit, separator, positions = range_header.strip(" \t").partition("=")
        if unit.lower() != "bytes" or not separator or "," in positions:
            raise ValueError("unsupported range format")
        start_text, end_text = positions.split("-", 1)
        if not start_text and not end_text:
            raise ValueError("empty range")
        if any(value and not (value.isascii() and value.isdigit()) for value in (start_text, end_text)):
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
        raise HttpException(task_id=request_id, status_code=416, message=f"{request_id}: requested range is not satisfiable") from exc
    return start, end

def create_task(request: Request, body: Union[TaskVideoRequest, SubtitleRequest, AudioRequest], stop_at: str):
    task_id = utils.get_uuid()
    request_id = base.get_task_id(request)
    try:
        if stop_at == "video" and isinstance(body, TaskVideoRequest) and body.subtitle_enabled:
            _resolve_path_within_directory(utils.font_dir(), body.font_name or "STHeitiMedium.ttc", request_id)
        task = {"task_id": task_id, "request_id": request_id, "params": body.model_dump()}
        sm.state.update_task(task_id)
        try:
            task_manager.add_task(tm.start, task_id=task_id, params=body, stop_at=stop_at)
        except Exception:
            sm.state.delete_task(task_id)
            raise
        return utils.get_response(200, task)
    except TaskQueueFullError as e:
        raise HttpException(task_id=task_id, status_code=429, message=str(e))
    except Exception as e:
        raise HttpException(task_id=task_id, status_code=500, message=str(e))

def get_all_tasks(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    request_id = base.get_task_id(request)
    tasks = sm.state.get_all_tasks()
    start = (page - 1) * page_size
    page_items = tasks[start:start + page_size]
    return utils.get_response(200, {"tasks": page_items, "total": len(tasks), "page": page, "page_size": page_size})

def get_task(request: Request, task_id: str = Path(...)):
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException(task_id=task_id, status_code=404, message="task not found")
    return utils.get_response(200, task)

def delete_video(request: Request, task_id: str = Path(...)):
    request_id = base.get_task_id(request)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException(task_id=task_id, status_code=404, message="task not found")
    sm.state.delete_task(task_id)
    return utils.get_response(200)

def get_bgm_list(request: Request):
    request_id = base.get_task_id(request)
    files = bgm_service.list_bgm()
    return utils.get_response(200, {"files": files})

def upload_bgm_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    content = file.file.read()
    name = _sanitize_upload_filename(file.filename or "bgm.mp3", request_id)
    bgm_service.save_bgm(name, content)
    return utils.get_response(200, {"file": name})

def get_video_materials_list(request: Request):
    request_id = base.get_task_id(request)
    materials_dir = utils.storage_dir("materials")
    items = []
    for p in pathlib.Path(materials_dir).iterdir() if pathlib.Path(materials_dir).exists() else []:
        if p.is_file() and not p.is_symlink():
            items.append({"name": p.name, "size": p.stat().st_size, "file": p.name})
    items.sort(key=lambda item: (item["name"].casefold(), item["name"]))
    return utils.get_response(200, {"files": items})

def upload_video_material_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    name = _sanitize_upload_filename(file.filename or "material.bin", request_id)
    if not name.lower().endswith((".mp4", ".mov", ".png", ".jpg", ".jpeg", ".webp")):
        raise HttpException(task_id=request_id, status_code=400, message="unsupported extension")
    content = file.file.read()
    materials_dir = pathlib.Path(utils.storage_dir("materials", create=True))
    dest = materials_dir / name
    dest.write_bytes(content)
    return utils.get_response(200, {"file": name})

async def stream_video(request: Request, file_path: str):
    request_id = base.get_task_id(request)
    video_path = _resolve_path_within_directory(utils.storage_dir("tasks"), file_path, request_id)
    if not os.path.isfile(video_path):
        raise HttpException(task_id=request_id, status_code=404, message="file not found")
    size = os.path.getsize(video_path)
    range_header = request.headers.get("Range")
    if range_header:
        start, end = _parse_byte_range(range_header, size, request_id)
        def iterator():
            with open(video_path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        return StreamingResponse(iterator(), status_code=206, headers={"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"})
    return FileResponse(video_path)

async def download_video(request: Request, file_path: str):
    request_id = base.get_task_id(request)
    video_path = _resolve_path_within_directory(utils.storage_dir("tasks"), file_path, request_id)
    if not os.path.isfile(video_path):
        raise HttpException(task_id=request_id, status_code=404, message="file not found")
    filename = pathlib.Path(video_path).name
    return FileResponse(video_path, filename=filename)

@router.post("/videos", response_model=TaskResponse, summary="Generate a short video")
def create_video_route(background_tasks: BackgroundTasks, request: Request, body: TaskVideoRequest):
    return create_task(request, body, stop_at="video")

@router.post("/subtitle", response_model=TaskResponse, summary="Generate subtitle only")
def create_subtitle_route(background_tasks: BackgroundTasks, request: Request, body: SubtitleRequest):
    return create_task(request, body, stop_at="subtitle")

@router.post("/audio", response_model=TaskResponse, summary="Generate audio only")
def create_audio_route(background_tasks: BackgroundTasks, request: Request, body: AudioRequest):
    return create_task(request, body, stop_at="audio")

@router.get("/tasks", response_model=TaskListResponse, summary="Get all tasks")
def get_all_tasks_route(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    return get_all_tasks(request, page, page_size)

@router.get("/tasks/{task_id}", response_model=TaskQueryResponse, summary="Query task status")
def get_task_route(request: Request, task_id: str = Path(...)):
    return get_task(request, task_id)

@router.delete("/tasks/{task_id}", response_model=TaskDeletionResponse, summary="Delete a task")
def delete_video_route(request: Request, task_id: str = Path(...)):
    return delete_video(request, task_id)

@router.get("/bgm", response_model=BgmRetrieveResponse, summary="Retrieve local BGM")
def get_bgm_list_route(request: Request):
    return get_bgm_list(request)

@router.post("/bgm", response_model=BgmUploadResponse, summary="Upload local BGM")
def upload_bgm_file_route(request: Request, file: UploadFile = File(...)):
    return upload_bgm_file(request, file)

@router.get("/video_materials", response_model=VideoMaterialRetrieveResponse, summary="Retrieve local video materials")
def get_video_materials_list_route(request: Request):
    return get_video_materials_list(request)

@router.post("/video_materials", response_model=VideoMaterialUploadResponse, summary="Upload local video material")
def upload_video_material_file_route(request: Request, file: UploadFile = File(...)):
    return upload_video_material_file(request, file)

@router.get("/stream/{file_path:path}")
@router.head("/stream/{file_path:path}", summary="Inspect video stream metadata")
async def stream_video_route(request: Request, file_path: str):
    return await stream_video(request, file_path)

@router.get("/download/{file_path:path}")
@router.head("/download/{file_path:path}", summary="Inspect artifact download metadata")
async def download_video_route(request: Request, file_path: str):
    return await download_video(request, file_path)

@router.post("/materials")
async def upload_material(
    request: Request,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    content = await file.read()
    from app.security.runtime import create_storage
    storage = create_storage()
    if hasattr(storage, "put_owned"):
        material_id = storage.put_owned(user, content, file.content_type, request_id)
    else:
        material_id = store_owned_material(user, content, file.content_type, request_id)
    return utils.get_response(200, {"material_id": material_id, "content_type": file.content_type, "size": len(content)})
