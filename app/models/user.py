from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's unique email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    picture: Optional[str] = Field(None, description="URL to user's profile picture")
    # Add other fields obtained from Google profile if needed

class UserCreate(UserBase):
    # Fields required specifically for creation, if any
    # Often the same as UserBase initially
    pass

class UserUpdate(BaseModel):
    # Fields that can be updated
    full_name: Optional[str] = None
    picture: Optional[str] = None

class UserInDBBase(UserBase):
    # Fields that are stored in the DB, potentially including hashed passwords etc.
    # For Google OAuth, we might store the Google ID
    google_id: str = Field(..., description="User's unique Google ID")
    refresh_token: Optional[str] = Field(None, description="Stored Google Refresh Token") # Store securely!

    class Config:
        from_attributes = True # Pydantic V2 replaces orm_mode

# Represents a user object as stored in MongoDB (potentially including ObjectId)
# We might not need a separate model if UserInDBBase covers it,
# but useful if DB representation differs significantly.
class User(UserInDBBase):
    id: str = Field(..., alias="_id", description="MongoDB document ID") # Or handle ObjectId conversion

# Represents the final user object returned by the API (excluding sensitive data)
class UserPublic(UserBase):
     id: str = Field(..., description="User's public ID (can be same as DB ID)")
     # Exclude sensitive fields like refresh_token
