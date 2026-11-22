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
        raise HttpException(task_id=request_id, status_code=400, message="path escapes base") from exc
    return str(candidate)

def _public_task_data(task: dict) -> dict:
    return {k: v for k, v in task.items() if k not in {"internal"}}

def _task_file_to_uri(file: str, endpoint: str, task_dir: str, request_id: str) -> str:
    safe = _resolve_path_within_directory(task_dir, file, request_id)
    rel = pathlib.Path(safe).relative_to(pathlib.Path(task_dir).resolve())
    return f"{endpoint}/{quote(str(rel))}"

def _task_response_data(task: dict, endpoint: str, task_dir: str, request_id: str) -> dict:
    data = _public_task_data(task)
    if "videos" in data:
        data["videos"] = [_task_file_to_uri(v, endpoint, task_dir, request_id) for v in data["videos"]]
    return data

def _parse_byte_range(header: str, total: int, request_id: str) -> tuple[int, int]:
    if not header or not header.startswith("bytes="):
        raise HttpException(task_id=request_id, status_code=416, message="invalid range")
    spec = header[6:].split(",")[0].strip()
    if "-" not in spec:
        raise HttpException(task_id=request_id, status_code=416, message="invalid range")
    start_s, end_s = spec.split("-", 1)
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else total - 1
    if start < 0 or end >= total or start > end:
        raise HttpException(task_id=request_id, status_code=416, message="range not satisfiable")
    return start, end

def create_video(request: Request, body: TaskVideoRequest):
    return create_task(request, body, "video")

def create_subtitle(request: Request, body: SubtitleRequest):
    return create_task(request, body, "subtitle")

def create_audio(request: Request, body: AudioRequest):
    return create_task(request, body, "audio")

def create_task(
    request: Request,
    body: Union[TaskVideoRequest, SubtitleRequest, AudioRequest],
    stop_at: str,
    user: AuthenticatedUser = Depends(require_authenticated_user),
):
    task_id = utils.get_uuid()
    request_id = base.get_task_id(request)
    rate_limiter.check_generation(user, request_id)
    try:
        task = {
            "task_id": task_id,
            "request_id": request_id,
            "params": body.model_dump(),
        }
        sm.state.update_task(task_id)
        ownership_store.create(
            TaskOwnershipRecord(
                task_id=task_id,
                owner_id=user.sub,
                created_at=datetime.now(timezone.utc),
                kind=stop_at,
                metadata={"stop_at": stop_at},
            )
        )
        try:
            task_manager.add_task(
                tm.start, task_id=task_id, params=body, stop_at=stop_at
            )
        except Exception:
            sm.state.delete_task(task_id)
            raise
        return utils.get_response(200, task)
    except Exception as e:
        raise HttpException(task_id=task_id, status_code=500, message=str(e))

def get_all_tasks(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: AuthenticatedUser = Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    tasks = sm.state.get_all_tasks()
    owned = [t for t in tasks if ownership_store.get(t.get("task_id", "")) and ownership_store.get(t["task_id"]).owner_id == user.sub]
    start = (page - 1) * page_size
    page_items = owned[start:start + page_size]
    return utils.get_response(200, {"tasks": page_items, "total": len(owned), "page": page, "page_size": page_size})

def get_task(
    request: Request,
    task_id: str = Path(...),
    user: AuthenticatedUser = Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    require_task_owner(task_id, user)
    task = sm.state.get_task(task_id)
    if not task:
        raise HttpException(task_id=task_id, status_code=404, message="task not found")
    return utils.get_response(200, task)

def delete_video(
    request: Request,
    task_id: str = Path(...),
    user: AuthenticatedUser = Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    require_task_owner(task_id, user)
    sm.state.delete_task(task_id)
    ownership_store.delete(task_id, user.sub)
    return utils.get_response(200)

def get_bgm_list(request: Request):
    request_id = base.get_task_id(request)
    files = bgm_service.list_bgm()
    return utils.get_response(200, {"files": files})

def upload_bgm_file(request: Request, file: UploadFile = File(...)):
    request_id = base.get_task_id(request)
    content = file.file.read()
    name = _sanitize_upload_filename(file.filename or "bgm.mp3", request_id)
    path = bgm_service.save_bgm(name, content)
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
