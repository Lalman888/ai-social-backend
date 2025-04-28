from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Path
from typing import List, Optional
from app.services.automation_service import (
    create_scheduled_post,
    get_scheduled_posts_for_user,
    get_scheduled_post_by_id,
    request_content_generation,
    get_analytics_for_post,
    configure_auto_reply,
    get_auto_reply_configs_for_user,
)
from app.models.automation import (
    ScheduledPostCreate, ScheduledPost,
    GeneratedContent,
    PostAnalytics,
    AutoReplyConfigCreate, AutoReplyConfig,
    SocialPlatform # Import enum
)
# Need BaseModel for inline request model
from pydantic import BaseModel
from app.models.user import UserPublic # To receive the current user
# Assume the dependency exists or will be created in the next step
from app.dependencies import get_current_user # Placeholder for authentication dependency
import logging

logger = logging.getLogger(__name__)
# Define the router with prefix and tags
router = APIRouter(
    prefix="/automation",
    tags=["Automation"],
    # Add dependency here to apply auth to all routes in this router
    dependencies=[Depends(get_current_user)]
)

# --- Scheduled Post Endpoints ---

@router.post(
    "/schedule_post",
    response_model=ScheduledPost,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a new social media post"
)
async def schedule_post_endpoint(
    post_data: ScheduledPostCreate = Body(...),
    current_user: UserPublic = Depends(get_current_user) # Get authenticated user
):
    '''
    Schedules a post to be published at a future time on selected platforms.
    Requires authentication.
    '''
    try:
        # Pass user_id from the authenticated user
        scheduled_post = await create_scheduled_post(user_id=current_user.id, post_data=post_data)
        if not scheduled_post:
             # This case might indicate DB error after insert or validation issue
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create or schedule post.")
        return scheduled_post
    except ValueError as e: # Catch validation errors from service (e.g., past schedule time)
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e: # Catch runtime errors from service
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in schedule_post_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.get(
    "/scheduled_posts",
    response_model=List[ScheduledPost],
    summary="List scheduled posts for the current user"
)
async def list_scheduled_posts_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserPublic = Depends(get_current_user)
):
    '''
    Retrieves a list of posts scheduled by the currently authenticated user.
    Supports pagination.
    '''
    posts = await get_scheduled_posts_for_user(user_id=current_user.id, skip=skip, limit=limit)
    return posts

@router.get(
    "/scheduled_posts/{post_id}",
    response_model=ScheduledPost,
    summary="Get details of a specific scheduled post"
)
async def get_scheduled_post_endpoint(
    post_id: str = Path(..., description="The ID of the scheduled post to retrieve"),
    current_user: UserPublic = Depends(get_current_user)
):
    '''
    Retrieves details of a single scheduled post by its ID.
    Ensures the post belongs to the authenticated user.
    '''
    post = await get_scheduled_post_by_id(user_id=current_user.id, post_id=post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled post not found or access denied.")
    return post

# --- Content Generation Endpoint ---

class ContentGenerationRequest(BaseModel): # Define request model inline or import
    platform: str
    keywords: List[str]
    tone: str
    length: int = 50
    notes: Optional[str] = None

@router.post(
    "/generate_content",
    response_model=GeneratedContent,
    summary="Generate social media content using AI"
)
async def generate_content_endpoint(
    request_data: ContentGenerationRequest = Body(...),
    current_user: UserPublic = Depends(get_current_user)
):
    '''
    Generates social media post content based on provided parameters using AI.
    Saves the generated content and returns it. Requires authentication.
    '''
    try:
        generated_content = await request_content_generation(
            user_id=current_user.id,
            platform=request_data.platform,
            keywords=request_data.keywords,
            tone=request_data.tone,
            length=request_data.length,
            notes=request_data.notes
        )
        if not generated_content:
             # Service layer handles LLM/DB errors, might return None or raise RuntimeError
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate or save content.")
        return generated_content
    except RuntimeError as e:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) # LLM unavailable etc.
    except Exception as e:
        logger.error(f"Unexpected error in generate_content_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during content generation.")


# --- Analytics Endpoint ---

@router.get(
    "/analytics/{platform}/{platform_post_id}",
    response_model=Optional[PostAnalytics], # Return type can be None if fetched in background
    summary="Get analytics for a specific social media post"
)
async def get_post_analytics_endpoint(
    platform: SocialPlatform = Path(..., description="The social media platform (e.g., 'facebook', 'instagram')"),
    platform_post_id: str = Path(..., description="The unique ID of the post on the platform"),
    current_user: UserPublic = Depends(get_current_user)
):
    '''
    Retrieves stored analytics for a given post.
    If analytics are not available or stale, triggers a background fetch task.
    Returns stored data immediately if available, otherwise returns null/empty response (client might need to poll or use WebSockets).
    Requires authentication.
    '''
    analytics = await get_analytics_for_post(
        user_id=current_user.id,
        platform_str=platform.value, # Pass enum value as string
        platform_post_id=platform_post_id
    )
    # Service returns None if fetching in background
    if analytics is None:
         # Return 202 Accepted to indicate background processing? Or just 200 with null body?
         # Returning 200 with null body might be simpler for client.
         return None # FastAPI handles Optional[Model] correctly
    return analytics


# --- Auto-Reply Configuration Endpoints ---

@router.post(
    "/auto_reply_config",
    response_model=AutoReplyConfig,
    status_code=status.HTTP_201_CREATED,
    summary="Configure a new auto-reply rule"
)
async def configure_auto_reply_endpoint(
    config_data: AutoReplyConfigCreate = Body(...),
    current_user: UserPublic = Depends(get_current_user)
):
    '''
    Creates a new auto-reply configuration for the authenticated user.
    Requires authentication.
    '''
    try:
        auto_reply_config = await configure_auto_reply(user_id=current_user.id, config_data=config_data)
        if not auto_reply_config:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save auto-reply configuration.")
        return auto_reply_config
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in configure_auto_reply_endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.get(
    "/auto_reply_configs",
    response_model=List[AutoReplyConfig],
    summary="List auto-reply configurations for the current user"
)
async def list_auto_reply_configs_endpoint(
    current_user: UserPublic = Depends(get_current_user)
):
    '''
    Retrieves all auto-reply configurations set up by the authenticated user.
    Requires authentication.
    '''
    configs = await get_auto_reply_configs_for_user(user_id=current_user.id)
    return configs

# Remember to include this router in app/main.py
# from app.routes import automation
# app.include_router(automation.router)
