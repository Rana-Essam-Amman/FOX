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

# Protected routes require a verified JWT. The old optional API-key path is
# removed so an unset key can no longer silently disable authentication.
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

@router.post("/materials")
async def upload_material(
    request: Request,
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(require_authenticated_user),
):
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    content = await file.read()
    # Use the runtime storage adapter. In production this is SupabaseStorageAdapter.
    from app.security.runtime import create_storage
    storage = create_storage()
    if hasattr(storage, "put_owned"):
        material_id = storage.put_owned(user, content, file.content_type, request_id)
    else:
        material_id = store_owned_material(user, content, file.content_type, request_id)
    return utils.get_response(200, {"material_id": material_id, "content_type": file.content_type, "size": len(content)})
