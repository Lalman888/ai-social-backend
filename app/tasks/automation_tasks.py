from app.core.celery_app import celery_app
from app.db.database import get_database
from app.models.automation import ScheduledPost, PostStatus, SocialPlatform, PostAnalyticsCreate
from app.utils.social_media_api import (
    post_to_facebook,
    post_to_instagram,
    get_facebook_post_analytics,
    get_instagram_post_analytics,
    get_user_access_token # Helper to get token
)
from bson import ObjectId # Import ObjectId to query MongoDB by ID
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60) # Example retry config
async def schedule_social_post(self, scheduled_post_id: str):
    '''
    Celery task to publish a scheduled post to its target platforms.
    '''
    logger.info(f"Executing task schedule_social_post for ID: {scheduled_post_id}")
    db = get_database()
    post_doc = await db.scheduled_posts.find_one({"_id": ObjectId(scheduled_post_id)})

    if not post_doc:
        logger.error(f"Scheduled post with ID {scheduled_post_id} not found.")
        return {"status": "error", "message": "Post not found"}

    # Convert to model for easier access (optional)
    # post = ScheduledPostInDB.model_validate(post_doc) # Requires id field mapping if using model

    user_id = post_doc.get("user_id")
    platforms = post_doc.get("platforms", [])
    text_content = post_doc.get("text_content")
    media_urls = post_doc.get("media_urls") # Assume these are ready-to-use URLs

    post_results = {}
    overall_status = PostStatus.POSTED # Assume success unless a platform fails

    for platform_str in platforms:
        platform = SocialPlatform(platform_str) # Convert string to enum
        platform_success = False
        platform_post_id = None
        error_message = None

        logger.info(f"Attempting to post to {platform.value} for user {user_id}")
        access_token = await get_user_access_token(user_id, platform)

        if not access_token:
            logger.error(f"No valid access token found for user {user_id} and platform {platform.value}")
            error_message = "Authentication token missing or invalid."
            overall_status = PostStatus.FAILED # Mark overall as failed if one platform fails critically
            post_results[platform] = {"success": False, "error": error_message}
            continue # Skip to next platform

        try:
            result = {}
            if platform == SocialPlatform.FACEBOOK:
                # Ensure required args are passed based on API function
                result = await post_to_facebook(access_token, text_content, media_urls)
            elif platform == SocialPlatform.INSTAGRAM:
                if not media_urls:
                     raise ValueError("Instagram requires media URLs.")
                result = await post_to_instagram(access_token, media_urls, text_content)
            # Add elif for Twitter, LinkedIn etc.
            else:
                raise NotImplementedError(f"Posting to {platform.value} is not implemented.")

            platform_post_id = result.get("id")
            if platform_post_id:
                platform_success = True
                logger.info(f"Successfully posted to {platform.value}. Platform Post ID: {platform_post_id}")
            else:
                 # Handle cases where API returns success but no ID (shouldn't happen often)
                 logger.warning(f"Post to {platform.value} reported success but no ID returned.")
                 error_message = "Post successful but platform ID missing."
                 # Consider if this is a failure or partial success

        except Exception as e:
            logger.error(f"Failed to post to {platform.value} for scheduled post {scheduled_post_id}: {e}", exc_info=True)
            error_message = str(e)
            overall_status = PostStatus.FAILED # Mark overall as failed

        post_results[platform] = {
            "success": platform_success,
            "post_id": platform_post_id,
            "error": error_message,
            "timestamp": datetime.utcnow()
        }

    # Update the scheduled post document in DB with results and final status
    logger.info(f"Updating scheduled post {scheduled_post_id} with status {overall_status} and results.")
    await db.scheduled_posts.update_one(
        {"_id": ObjectId(scheduled_post_id)},
        {"$set": {
            "status": overall_status,
            "post_results": post_results,
            "updated_at": datetime.utcnow()
        }}
    )

    return {"status": overall_status.value, "results": post_results}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300) # Retry less often for analytics
async def fetch_post_analytics(self, platform_post_id: str, platform_str: str, user_id: str):
    '''
    Celery task to fetch analytics for a specific post and store them.
    '''
    logger.info(f"Executing task fetch_post_analytics for {platform_str} post {platform_post_id} (User: {user_id})")
    db = get_database()
    platform = SocialPlatform(platform_str)
    access_token = await get_user_access_token(user_id, platform)

    if not access_token:
        logger.error(f"No valid access token found for user {user_id} and platform {platform.value} to fetch analytics.")
        # Consider retry? Or just fail?
        return {"status": "error", "message": "Authentication token missing or invalid."}

    try:
        analytics_data = {}
        if platform == SocialPlatform.FACEBOOK:
            analytics_data = await get_facebook_post_analytics(access_token, platform_post_id)
        elif platform == SocialPlatform.INSTAGRAM:
            analytics_data = await get_instagram_post_analytics(access_token, platform_post_id)
        # Add elif for other platforms
        else:
            raise NotImplementedError(f"Analytics fetching for {platform.value} is not implemented.")

        logger.info(f"Successfully fetched analytics for {platform.value} post {platform_post_id}: {analytics_data}")

        # Save analytics data to DB
        analytics_doc = PostAnalyticsCreate(
            user_id=user_id,
            platform=platform,
            platform_post_id=platform_post_id,
            metrics=analytics_data, # Store the raw dict returned by the API function
            fetched_at=datetime.utcnow()
        )
        await db.post_analytics.insert_one(analytics_doc.model_dump()) # Use a dedicated collection
        logger.info(f"Analytics saved successfully for post {platform_post_id}.")
        return {"status": "success", "analytics": analytics_data}

    except Exception as e:
        logger.error(f"Failed to fetch or store analytics for {platform.value} post {platform_post_id}: {e}", exc_info=True)
        # Optional: Retry logic using self.retry()
        # try:
        #     raise e # Re-raise to trigger Celery's retry mechanism
        # except Exception as exc:
        #     self.retry(exc=exc)
        return {"status": "error", "message": str(e)}


# Placeholder for Auto-Reply task (requires webhook integration)
@celery_app.task
async def process_incoming_comment_for_autoreply(comment_data: dict, user_id: str):
    logger.info(f"Placeholder: Processing comment for user {user_id}: {comment_data}")
    # 1. Fetch AutoReplyConfig for user_id and platform
    # 2. Check if comment matches trigger conditions
    # 3. If match:
    #    a. Get reply content (template or AI generated via content_service)
    #    b. Get user access token
    #    c. Call social_media_api to post the reply
    pass
