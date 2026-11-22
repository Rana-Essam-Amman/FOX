from fastapi import Depends, Request

from app.controllers import base
from app.controllers.v1.base import new_router
from app.models.exception import HttpException
from app.models.schema import (
    VideoScriptRequest,
    VideoScriptResponse,
    VideoSocialMetadataRequest,
    VideoSocialMetadataResponse,
    VideoTermsRequest,
    VideoTermsResponse,
)
from app.services import llm
from app.utils import utils
from app.security import require_authenticated_user
from app.security.rate_limit import rate_limiter

# LLM endpoints use the same JWT authentication as the video routes.
router = new_router(dependencies=[Depends(require_authenticated_user)])


@router.post(
    "/scripts",
    response_model=VideoScriptResponse,
    summary="Create a script for the video",
)
def generate_video_script(request: Request, body: VideoScriptRequest, user=None):
    if user is None:
        user = require_authenticated_user(request)
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    rate_limiter.check_generation(user, request_id)
    video_script = llm.generate_script(
        video_subject=body.video_subject,
        language=body.video_language,
        paragraph_number=body.paragraph_number,
        video_script_prompt=body.video_script_prompt,
        custom_system_prompt=body.custom_system_prompt,
    )
    if not video_script or video_script.startswith("Error: "):
        raise HttpException(
            task_id=base.get_task_id(request), status_code=503,
            message="script generation is unavailable",
        )
    response = {"video_script": video_script}
    return utils.get_response(200, response)


@router.post(
    "/terms",
    response_model=VideoTermsResponse,
    summary="Generate video terms based on the video script",
)
def generate_video_terms(request: Request, body: VideoTermsRequest, user=None):
    if user is None:
        user = require_authenticated_user(request)
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    rate_limiter.check_generation(user, request_id)
    video_terms = llm.generate_terms(
        video_subject=body.video_subject,
        video_script=body.video_script,
        amount=body.amount,
        match_script_order=body.match_materials_to_script,
    )
    if not video_terms:
        raise HttpException(
            task_id=base.get_task_id(request), status_code=503,
            message="search term generation is unavailable",
        )
    response = {"video_terms": video_terms}
    return utils.get_response(200, response)


@router.post(
    "/social-metadata",
    response_model=VideoSocialMetadataResponse,
    summary="Generate social publishing metadata",
)
def generate_video_social_metadata(
    request: Request,
    body: VideoSocialMetadataRequest,
    user=None,
):
    if user is None:
        user = require_authenticated_user(request)
    request_id = base.get_task_id(request)
    rate_limiter.check_request(user, request_id)
    rate_limiter.check_generation(user, request_id)
    metadata = llm.generate_social_metadata(
        video_subject=body.video_subject,
        video_script=body.video_script,
        language=body.language,
        platform=body.platform,
    )
    return utils.get_response(200, metadata)
