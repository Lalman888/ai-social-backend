from app.db.database import get_database
from app.models.automation import (
    ScheduledPostCreate, ScheduledPostInDB, ScheduledPost,
    GeneratedContent, GeneratedContentCreate,
    PostAnalytics, PostAnalyticsCreate,
    AutoReplyConfigCreate, AutoReplyConfigInDB, AutoReplyConfig,
    PostStatus, SocialPlatform
)
from app.tasks.automation_tasks import schedule_social_post, fetch_post_analytics # Import Celery tasks
from app.services.content_service import generate_post_content # Import content generation service
from bson import ObjectId
from datetime import datetime, timezone
import logging
from typing import List, Optional, Dict, Any
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# --- Scheduled Post Service Functions ---

async def create_scheduled_post(user_id: str, post_data: ScheduledPostCreate) -> Optional[ScheduledPost]:
    '''Saves a scheduled post to the DB and triggers the Celery task.'''
    db = get_database()
    # Ensure user_id from auth matches payload or is set correctly
    # The route handler should ensure user_id is correct. Here we trust it.
    # We need to map the input ScheduledPostCreate to ScheduledPostInDB structure if needed
    # or ensure ScheduledPostCreate includes all necessary fields for DB insertion.
    # post_data.user_id = user_id # Assuming user_id is part of ScheduledPostCreate or set by caller

    post_to_save = post_data.model_dump() # Convert Pydantic model to dict
    post_to_save["user_id"] = user_id # Ensure user_id is set
    post_to_save["status"] = PostStatus.PENDING # Ensure status starts as pending
    post_to_save["created_at"] = datetime.now(timezone.utc)
    post_to_save["updated_at"] = datetime.now(timezone.utc)
    post_to_save["post_results"] = None # Initialize results

    # Validate schedule time (e.g., must be in the future)
    scheduled_at_utc = post_data.scheduled_at # Assume input is already UTC or timezone-aware
    # If not, ensure conversion: scheduled_at_utc = post_data.scheduled_at.astimezone(timezone.utc)
    if scheduled_at_utc <= datetime.now(timezone.utc):
        logger.warning(f"Scheduled time {post_data.scheduled_at} is in the past.")
        # Decide policy: reject or schedule immediately? Rejecting for now.
        raise ValueError("Scheduled time must be in the future.")

    try:
        # Use ScheduledPostInDB for validation before insertion? Or rely on MongoDB structure?
        # Let's assume the structure matches and insert directly.
        insert_result = await db.scheduled_posts.insert_one(post_to_save)

        if insert_result.inserted_id:
            # Schedule the Celery task to run at the specified time
            # Ensure scheduled_at_utc is correctly passed if timezone handling is complex
            task_id = schedule_social_post.apply_async(
                args=[str(insert_result.inserted_id)],
                eta=scheduled_at_utc # Use eta for scheduled time (must be UTC datetime)
            )
            logger.info(f"Scheduled post created (ID: {insert_result.inserted_id}) and Celery task {task_id.id} scheduled for {scheduled_at_utc}.")

            # Retrieve the created document to return
            created_doc = await db.scheduled_posts.find_one({"_id": insert_result.inserted_id})
            if created_doc:
                 # Map _id to id before validation
                 created_doc["id"] = str(created_doc["_id"])
                 try:
                     # Validate against the full ScheduledPost model for return
                     return ScheduledPost.model_validate(created_doc)
                 except ValidationError as e_val:
                     logger.error(f"Validation error retrieving scheduled post {insert_result.inserted_id}: {e_val}")
                     # Decide if this is a critical error or if partial data is okay
                     return None # Failed validation on retrieval
            else:
                 # This case is unlikely but handle defensively
                 logger.error(f"Failed to retrieve newly created scheduled post {insert_result.inserted_id}")
                 return None # Or raise internal error
        else:
            logger.error("Failed to insert scheduled post into database.")
            return None
    except ValidationError as e:
         # This might catch validation errors if we used a model like ScheduledPostInDB(**post_to_save) before insert
         logger.error(f"Validation error preparing scheduled post data: {e}", exc_info=True)
         raise ValueError(f"Invalid post data: {e}") # Re-raise as ValueError for API layer
    except Exception as e:
        logger.error(f"Error creating or scheduling post: {e}", exc_info=True)
        raise RuntimeError(f"Could not schedule post: {e}")


async def get_scheduled_posts_for_user(user_id: str, skip: int = 0, limit: int = 100) -> List[ScheduledPost]:
    '''Retrieves a list of scheduled posts for a given user.'''
    db = get_database()
    posts_cursor = db.scheduled_posts.find({"user_id": user_id})                                     .sort("scheduled_at", -1)                                     .skip(skip)                                     .limit(limit)
    posts = []
    async for post_doc in posts_cursor:
        post_doc["id"] = str(post_doc["_id"]) # Map _id to id
        try:
            posts.append(ScheduledPost.model_validate(post_doc))
        except ValidationError as e:
             logger.error(f"Validation error for scheduled post {post_doc.get('_id')}: {e}")
             # Skip invalid data for now
    return posts

async def get_scheduled_post_by_id(user_id: str, post_id: str) -> Optional[ScheduledPost]:
     '''Retrieves a single scheduled post by its ID, ensuring user ownership.'''
     db = get_database()
     try:
          object_id = ObjectId(post_id)
     except Exception:
          logger.warning(f"Invalid ObjectId format for post_id: {post_id}")
          return None

     post_doc = await db.scheduled_posts.find_one({"_id": object_id, "user_id": user_id})
     if post_doc:
          post_doc["id"] = str(post_doc["_id"]) # Map _id to id
          try:
               return ScheduledPost.model_validate(post_doc)
          except ValidationError as e:
               logger.error(f"Validation error for scheduled post {post_id}: {e}")
               return None # Treat validation error as not found/invalid
     return None

# --- Content Generation Service Function (Passthrough) ---

async def request_content_generation(
    user_id: str, platform: str, keywords: List[str], tone: str, length: int, notes: Optional[str]
) -> Optional[GeneratedContent]:
    '''Handles the request for content generation by calling the content service.'''
    logger.info(f"Relaying content generation request for user {user_id}")
    try:
        # generate_post_content handles saving to DB internally
        generated_content = await generate_post_content(
            user_id=user_id,
            platform=platform,
            keywords=keywords,
            tone=tone,
            length=length,
            notes=notes
        )
        return generated_content # Return the saved GeneratedContent object or None
    except RuntimeError as e:
         # Catch runtime errors from the underlying service (e.g., LLM unavailable)
         logger.error(f"Content generation failed: {e}")
         raise # Re-raise the runtime error to be caught by the API layer
    except Exception as e:
         logger.error(f"Unexpected error during content generation request: {e}", exc_info=True)
         raise RuntimeError("An unexpected error occurred during content generation.")


# --- Analytics Service Functions ---

async def get_analytics_for_post(user_id: str, platform_str: str, platform_post_id: str) -> Optional[PostAnalytics]:
    '''Retrieves stored analytics or triggers a fetch task.'''
    db = get_database()
    try:
        platform = SocialPlatform(platform_str) # Validate platform string
    except ValueError:
         logger.warning(f"Invalid platform string requested for analytics: {platform_str}")
         raise ValueError(f"Invalid social platform: {platform_str}")

    # Check if analytics exist in DB first
    analytics_doc = await db.post_analytics.find_one({
        "user_id": user_id,
        "platform": platform.value, # Store enum value in DB
        "platform_post_id": platform_post_id
    })

    if analytics_doc:
        # Optionally: Check how old the data is and decide if a refresh is needed
        # fetched_at = analytics_doc.get("fetched_at")
        # if datetime.now(timezone.utc) - fetched_at > timedelta(hours=1): # Example: refresh if older than 1 hr
        #     logger.info(f"Analytics for {platform_post_id} are old, triggering refresh task.")
        #     fetch_post_analytics.delay(platform_post_id, platform.value, user_id) # Trigger async refresh
        # else:
        #     logger.info(f"Returning stored analytics for {platform_post_id}.")

        analytics_doc["id"] = str(analytics_doc["_id"])
        try:
             return PostAnalytics.model_validate(analytics_doc)
        except ValidationError as e:
             logger.error(f"Validation error for stored analytics {analytics_doc.get('_id')}: {e}")
             # Fall through to trigger refresh if validation fails? Or return error?
             # For now, fall through might be okay, but log the error.

    # If not found or decided to refresh, trigger the Celery task
    logger.info(f"Analytics not found or refresh needed for {platform_post_id}. Triggering fetch task.")
    # Use .delay for simplicity, or apply_async for more options
    fetch_post_analytics.delay(platform_post_id, platform.value, user_id)

    # Return None to indicate data is being fetched in the background
    return None


# --- Auto-Reply Configuration Service Functions ---

async def configure_auto_reply(user_id: str, config_data: AutoReplyConfigCreate) -> Optional[AutoReplyConfig]:
    '''Creates or updates an auto-reply configuration.'''
    db = get_database()
    # config_data.user_id = user_id # Ensure user_id is set by route handler/dependency

    # Prepare data for DB insertion
    config_to_save = config_data.model_dump()
    config_to_save["user_id"] = user_id # Ensure user_id is set
    config_to_save["updated_at"] = datetime.now(timezone.utc)
    config_to_save["created_at"] = datetime.now(timezone.utc) # Set created_at on insert

    try:
        # Simple approach: Insert new config. Update/delete logic could be added later.
        insert_result = await db.auto_reply_configs.insert_one(config_to_save) # Use dedicated collection

        if insert_result.inserted_id:
             created_doc = await db.auto_reply_configs.find_one({"_id": insert_result.inserted_id})
             if created_doc:
                  created_doc["id"] = str(created_doc["_id"]) # Map _id to id
                  try:
                       return AutoReplyConfig.model_validate(created_doc)
                  except ValidationError as e_val:
                       logger.error(f"Validation error retrieving auto-reply config {insert_result.inserted_id}: {e_val}")
                       return None # Failed validation on retrieval
             else:
                  logger.error("Failed to retrieve newly created auto-reply config.")
                  return None
        else:
             logger.error("Failed to insert auto-reply config into database.")
             return None
    except ValidationError as e: # This would catch validation errors if using a model before insert
         logger.error(f"Validation error preparing auto-reply config data: {e}", exc_info=True)
         raise ValueError(f"Invalid auto-reply config data: {e}")
    except Exception as e:
         logger.error(f"Error configuring auto-reply: {e}", exc_info=True)
         raise RuntimeError(f"Could not configure auto-reply: {e}")

async def get_auto_reply_configs_for_user(user_id: str) -> List[AutoReplyConfig]:
    '''Retrieves all auto-reply configurations for a user.'''
    db = get_database()
    configs_cursor = db.auto_reply_configs.find({"user_id": user_id})
    configs = []
    async for config_doc in configs_cursor:
        config_doc["id"] = str(config_doc["_id"]) # Map _id to id
        try:
            configs.append(AutoReplyConfig.model_validate(config_doc))
        except ValidationError as e:
             logger.error(f"Validation error for auto-reply config {config_doc.get('_id')}: {e}")
             # Skip invalid data
    return configs
