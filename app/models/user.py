from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class UserBase(BaseModel):
    email: Optional[EmailStr] = Field(None, description="User's email address (Optional as might not be provided by all OAuth providers initially)") # Made email optional
    full_name: Optional[str] = Field(None, description="User's full name")
    picture: Optional[str] = Field(None, description="URL to user's profile picture")
    # Add other fields obtained from profiles if needed

class UserCreate(UserBase):
    # Fields required specifically for creation, if any
    # Might require email depending on your policy
    pass

class UserUpdate(BaseModel):
    # Fields that can be updated
    full_name: Optional[str] = None
    picture: Optional[str] = None
    email: Optional[EmailStr] = None # Allow email update/addition?

class UserInDBBase(UserBase):
    # Fields that are stored in the DB
    google_id: Optional[str] = Field(None, description="User's unique Google ID") # Made optional
    facebook_id: Optional[str] = Field(None, description="User's unique Facebook ID") # Added
    instagram_id: Optional[str] = Field(None, description="User's unique Instagram ID") # Added

    refresh_token: Optional[str] = Field(None, description="Stored Google Refresh Token (Optional, secure storage needed)")

    class Config:
        from_attributes = True # Pydantic V2 replaces orm_mode

# Represents a user object as stored in MongoDB (inherits new fields)
class User(UserInDBBase):
    # Assuming Pydantic handles ObjectId conversion via alias or custom type later
    # If using standard string IDs from the start:
    id: str = Field(..., description="MongoDB document ID (_id as string)")

    # Override Config if needed, but inherits by default
    # class Config:
    #    from_attributes = True


# Represents the final user object returned by the API (excluding sensitive data)
class UserPublic(UserBase):
     id: str = Field(..., description="User's public ID")
     # Ensure it inherits changes like optional email from UserBase
     # Add any other fields safe for public exposure
     google_linked: bool = Field(False, description="Indicates if Google account is linked")
     facebook_linked: bool = Field(False, description="Indicates if Facebook account is linked")
     instagram_linked: bool = Field(False, description="Indicates if Instagram account is linked")

     # Custom validator or logic might be needed to set linked status
     # Or compute it in the route before returning UserPublic
