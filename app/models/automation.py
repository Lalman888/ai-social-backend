from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Enum for supported platforms (can be expanded)
class SocialPlatform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    # TWITTER = "twitter" # Add when implemented
    # LINKEDIN = "linkedin" # Add when implemented

# Enum for scheduled post status
class PostStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"

# Model for storing scheduled posts
class ScheduledPostBase(BaseModel):
    user_id: str = Field(..., description="ID of the user who scheduled the post")
    platforms: List[SocialPlatform] = Field(..., description="List of platforms to post to")
    text_content: Optional[str] = Field(None, description="Text content of the post")
    media_urls: Optional[List[HttpUrl]] = Field(None, description="List of URLs for images/videos (requires handling)") # Consider how media is stored/accessed
    scheduled_at: datetime = Field(..., description="Time the post is scheduled to be published (UTC)")
    status: PostStatus = Field(PostStatus.PENDING, description="Current status of the scheduled post")

class ScheduledPostCreate(ScheduledPostBase):
    pass # Inherits all fields for creation

class ScheduledPostInDB(ScheduledPostBase):
    id: str = Field(..., description="MongoDB document ID (_id as string)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the schedule was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the schedule was last updated")
    # Store results per platform
    post_results: Optional[Dict[SocialPlatform, Dict[str, Any]]] = Field(
        None,
        description="Dictionary storing the outcome per platform, e.g., {'facebook': {'success': True, 'post_id': 'fb_post_123'}, 'instagram': {'success': False, 'error': 'API error'}}",
        example={'facebook': {'success': True, 'post_id': 'fb_post_123'}}
    )

# Model for API response/retrieval
class ScheduledPost(ScheduledPostInDB):
    pass # Could add computed fields if needed

# --- Generated Content ---

class GeneratedContentBase(BaseModel):
    user_id: str = Field(..., description="ID of the user who requested generation")
    prompt: Dict[str, Any] = Field(..., description="Details of the prompt (keywords, tone, etc.)")
    model_used: str = Field("gpt-3.5-turbo", description="AI model used for generation") # Example default
    generated_text: str = Field(..., description="The generated text content")

class GeneratedContentCreate(GeneratedContentBase):
    pass

class GeneratedContentInDB(GeneratedContentBase):
    id: str = Field(..., description="MongoDB document ID (_id as string)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of generation")

class GeneratedContent(GeneratedContentInDB):
    pass

# --- Post Analytics ---

class PostAnalyticsBase(BaseModel):
    user_id: str = Field(..., description="ID of the user who owns the post")
    platform: SocialPlatform = Field(..., description="Social media platform")
    platform_post_id: str = Field(..., description="The unique ID of the post on the platform")
    metrics: Dict[str, Any] = Field(..., description="Fetched analytics data (likes, comments, shares, etc.)")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the analytics were fetched")

class PostAnalyticsCreate(PostAnalyticsBase):
    pass

class PostAnalyticsInDB(PostAnalyticsBase):
    id: str = Field(..., description="MongoDB document ID (_id as string)")
    # Add other relevant fields if needed, e.g., association to a ScheduledPost ID

class PostAnalytics(PostAnalyticsInDB):
    pass

# --- Auto-Reply Configuration ---

class AutoReplyTrigger(str, Enum):
    KEYWORD = "keyword"
    ALL_COMMENTS = "all_comments"
    # Add more trigger types (e.g., specific users, sentiment)

class AutoReplyAction(str, Enum):
    TEMPLATE = "template"
    AI_GENERATED = "ai_generated"

class AutoReplyConfigBase(BaseModel):
    user_id: str = Field(..., description="ID of the user this config belongs to")
    platform: SocialPlatform = Field(..., description="Platform this applies to")
    name: str = Field(..., description="User-defined name for this configuration")
    is_active: bool = Field(True, description="Whether this auto-reply is active")
    trigger_type: AutoReplyTrigger = Field(..., description="Condition that triggers the reply")
    trigger_details: Optional[Dict[str, Any]] = Field(None, description="Details for the trigger (e.g., {'keywords': ['price', 'buy']})")
    action_type: AutoReplyAction = Field(..., description="Type of reply action")
    action_details: Dict[str, Any] = Field(..., description="Details for the action (e.g., {'template': 'Thanks!'} or {'prompt': 'Generate a friendly thank you'})")

class AutoReplyConfigCreate(AutoReplyConfigBase):
    pass

class AutoReplyConfigInDB(AutoReplyConfigBase):
    id: str = Field(..., description="MongoDB document ID (_id as string)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AutoReplyConfig(AutoReplyConfigInDB):
    pass
