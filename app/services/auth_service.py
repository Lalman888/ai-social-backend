from fastapi import HTTPException, status, Request
from typing import Optional
from app.db.database import get_database
from app.models.user import User, UserInDBBase # Import updated models
from app.utils.jwt import create_access_token
from app.utils.config import settings # Import settings
from app.auth.google import oauth as oauth_google # Rename import to avoid clash
from app.auth.facebook import oauth_facebook
from app.auth.instagram import oauth_instagram
from authlib.integrations.base_client.errors import OAuthError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

# --- Database Access Functions ---
# (get_user_by_provider_id and get_user_by_email remain unchanged)

async def get_user_by_provider_id(provider: str, provider_id: str) -> Optional[User]:
    '''Finds a user in the database by their provider-specific ID.'''
    db = get_database()
    query_field = f"{provider}_id"
    user_doc = await db.users.find_one({query_field: provider_id})
    if user_doc:
        if "_id" not in user_doc:
            logger.error(f"'_id' field missing in user document for {query_field} {provider_id}")
            return None
        user_doc["_id"] = str(user_doc["_id"])
        try:
            return User.model_validate(user_doc)
        except ValidationError as e:
             logger.error(f"Error validating user data from DB for {query_field} {provider_id}: {e}")
             return None
    return None

async def get_user_by_email(email: str) -> Optional[User]:
    '''Finds a user in the database by their email address.'''
    db = get_database()
    if not email:
        return None
    user_doc = await db.users.find_one({"email": email})
    if user_doc:
        if "_id" not in user_doc:
             logger.error(f"'_id' field missing in user document for email {email}")
             return None
        user_doc["_id"] = str(user_doc["_id"])
        try:
            return User.model_validate(user_doc)
        except ValidationError as e:
             logger.error(f"Error validating user data from DB for email {email}: {e}")
             return None
    return None

# --- User Creation / Update Logic (MODIFIED) ---

async def create_or_update_social_user(provider: str, user_info: dict, token: Optional[dict] = None) -> Optional[User]: # Added token parameter
    '''
    Creates a new user or updates an existing one based on social profile info.
    Handles linking accounts based on verified email (if available).
    Stores the latest access token received from the provider.
    '''
    db = get_database()
    provider_id = None
    email = user_info.get("email")
    full_name = user_info.get("name")
    picture = None

    # Extract access token if provided
    access_token = token.get('access_token') if token else None
    if access_token:
         logger.debug(f"Received access token from {provider} callback.")
         # SECURITY WARNING: Log tokens only in DEBUG, be cautious in production.

    # Extract provider-specific ID and details
    if provider == "google":
        provider_id = str(user_info.get("sub"))
        picture = user_info.get("picture")
    elif provider == "facebook":
        provider_id = str(user_info.get("id"))
        picture = user_info.get("picture", {}).get("data", {}).get("url")
    elif provider == "instagram":
        provider_id = str(user_info.get("id"))
        full_name = user_info.get("username")
        email = None
        picture = None

    if not provider_id:
         logger.error(f"Social user info from {provider} missing required ID ('sub' or 'id')")
         return None

    # --- Find Existing User ---
    existing_user = await get_user_by_provider_id(provider, provider_id)

    if not existing_user and email and provider in ["google", "facebook"]:
        logger.info(f"User not found by {provider} ID ({provider_id}). Checking by email: {email}")
        existing_user_by_email = await get_user_by_email(email)
        if existing_user_by_email:
            logger.info(f"Found existing user by email ({email}). Linking {provider} account.")
            existing_user = existing_user_by_email

    # --- Prepare User Data for DB ---
    if existing_user:
        # Update existing user
        logger.info(f"Updating existing user (ID: {existing_user.id}) with {provider} info.")
        update_fields = {f"{provider}_id": provider_id}
        # Optionally update name/picture if not already set
        if full_name and not existing_user.full_name: update_fields["full_name"] = full_name
        if picture and not existing_user.picture: update_fields["picture"] = picture

        # Add/Update access token
        if access_token:
             logger.info(f"Updating access token for user {existing_user.id} from {provider}.")
             update_fields['access_token'] = access_token # Store latest token

        if not hasattr(existing_user, 'id') or not existing_user.id:
             logger.error(f"Cannot update user: existing_user object lacks a valid 'id' attribute.")
             return None

        await db.users.update_one(
            {"_id": existing_user.id}, # Use the User model's primary id attribute
            {"$set": update_fields}
        )
        # Re-fetch the updated user to get the complete object including the new token
        updated_user_doc = await db.users.find_one({"_id": existing_user.id})
        if not updated_user_doc:
             logger.error(f"Failed to re-fetch user after update (ID: {existing_user.id})")
             return None
        updated_user_doc["_id"] = str(updated_user_doc["_id"])
        return User.model_validate(updated_user_doc)

    else:
        # Create new user
        logger.info(f"Creating new user via {provider}: ID={provider_id}, Email={email}")
        new_user_data = {
            f"{provider}_id": provider_id,
            "email": email,
            "full_name": full_name,
            "picture": picture,
            "google_id": provider_id if provider == "google" else None,
            "facebook_id": provider_id if provider == "facebook" else None,
            "instagram_id": provider_id if provider == "instagram" else None,
            "access_token": access_token, # Add access token for new user
        }
        new_user_data_cleaned = {k: v for k, v in new_user_data.items() if v is not None}

        try:
             user_to_create = UserInDBBase(**new_user_data_cleaned)
             user_dict = user_to_create.model_dump(exclude_unset=True)

             insert_result = await db.users.insert_one(user_dict)
             if insert_result.inserted_id:
                 new_user_doc = await db.users.find_one({"_id": insert_result.inserted_id})
                 if not new_user_doc:
                      logger.error(f"Failed to fetch newly created user (ID: {insert_result.inserted_id})")
                      return None
                 new_user_doc["_id"] = str(new_user_doc["_id"])
                 return User.model_validate(new_user_doc)
             else:
                 logger.error(f"MongoDB insert_one failed for new user via {provider} (ID: {provider_id})")
                 return None
        except ValidationError as e:
             logger.error(f"Validation error creating user via {provider} (ID: {provider_id}): {e}")
             return None
        except Exception as e:
             logger.error(f"Unexpected error creating user via {provider} (ID: {provider_id}): {e}", exc_info=True)
             return None


# --- OAuth Callback Handlers ---
# (process_google_callback, process_facebook_callback, process_instagram_callback remain unchanged
# as they already pass the 'token' dictionary to create_or_update_social_user)

async def process_google_callback(request: Request) -> tuple[Optional[User], Optional[str]]:
    '''Handles the callback from Google, fetches user info, creates/updates user, generates JWT.'''
    if not oauth_google or not hasattr(oauth_google, 'google'): # Check if client exists
         logger.error("Google OAuth client not configured properly.")
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login is not configured.")
    try:
        token = await oauth_google.google.authorize_access_token(request) # token dict includes access_token
        logger.debug(f"Received token from Google: {token}")
        user_info = await oauth_google.google.userinfo(token=token)
        logger.info(f"Received user info from Google: {user_info}")

        if not user_info or not user_info.get("sub"):
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not fetch valid user info from Google")

        # Pass the full token dict to the updated function
        user = await create_or_update_social_user(provider="google", user_info=user_info, token=token)
        if not user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create or update user profile.")

        access_token_data = {"sub": user.email} # Google provides email
        access_token_jwt = create_access_token(data=access_token_data) # Our app's JWT
        logger.info(f"JWT generated successfully for Google user: {user.email}")
        return user, access_token_jwt

    except OAuthError as error:
        logger.error(f"OAuth Error during Google callback: {error.description} (Error: {error.error})", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed via Google: {error.error or error.description}")
    except Exception as e:
        logger.error(f"Error processing Google callback: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during Google authentication.")


async def process_facebook_callback(request: Request) -> tuple[Optional[User], Optional[str]]:
    '''Handles the callback from Facebook, fetches user info, creates/updates user, generates JWT.'''
    if not oauth_facebook or not hasattr(oauth_facebook, 'facebook'):
         logger.error("Facebook OAuth client not configured.")
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Facebook login is not configured.")
    try:
        token = await oauth_facebook.facebook.authorize_access_token(request) # token dict includes access_token
        logger.debug(f"Received token from Facebook: {token}")
        user_info = await oauth_facebook.facebook.userinfo(token=token)
        logger.info(f"Received user info from Facebook: {user_info}")

        if not user_info or not user_info.get("id"):
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not fetch valid user info from Facebook")

        # Pass the full token dict to the updated function
        user = await create_or_update_social_user(provider="facebook", user_info=user_info, token=token)
        if not user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create or update user profile.")

        jwt_subject = user.email or f"facebook:{getattr(user, 'facebook_id', 'UNKNOWN')}"
        access_token_data = {"sub": jwt_subject}
        access_token_jwt = create_access_token(data=access_token_data) # Our app's JWT
        logger.info(f"JWT generated successfully for Facebook user: {jwt_subject}")
        return user, access_token_jwt

    except OAuthError as error:
        logger.error(f"OAuth Error during Facebook callback: {error.description} (Error: {error.error})", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed via Facebook: {error.error or error.description}")
    except Exception as e:
        logger.error(f"Error processing Facebook callback: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during Facebook authentication.")


async def process_instagram_callback(request: Request) -> tuple[Optional[User], Optional[str]]:
    '''Handles the callback from Instagram Basic Display, fetches user info, creates/updates user, generates JWT.'''
    if not oauth_instagram or not hasattr(oauth_instagram, 'instagram'):
        logger.error("Instagram OAuth client not configured.")
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Instagram login is not configured.")
    try:
        token = await oauth_instagram.instagram.authorize_access_token(request) # token dict includes access_token
        logger.debug(f"Received token from Instagram: {token}")

        user_id = token.get('user_id')
        access_token_ig = token.get('access_token') # This is the provider token to store
        if not user_id or not access_token_ig:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not get user_id or access_token from Instagram.")

        async with oauth_instagram.instagram.sessions.JsonSession() as session:
             resp = await session.get(
                 f'https://graph.instagram.com/{user_id}',
                 params={'fields': 'id,username', 'access_token': access_token_ig}
             )
             resp.raise_for_status()
             user_info = resp.json()
             logger.info(f"Received user info from Instagram Graph API: {user_info}")

        if not user_info or not user_info.get("id"):
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not fetch valid user info from Instagram")

        # Pass the full token dict (which contains the access_token_ig)
        user = await create_or_update_social_user(provider="instagram", user_info=user_info, token=token)
        if not user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create or update user profile from Instagram.")

        jwt_subject = f"instagram:{getattr(user, 'instagram_id', 'UNKNOWN')}"
        access_token_data = {"sub": jwt_subject}
        access_token_jwt = create_access_token(data=access_token_data) # Our app's JWT
        logger.info(f"JWT generated successfully for Instagram user: {jwt_subject}")
        return user, access_token_jwt

    except OAuthError as error:
        logger.error(f"OAuth Error during Instagram callback: {error.description} (Error: {error.error})", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed via Instagram: {error.error or error.description}")
    except Exception as e:
        logger.error(f"Error processing Instagram callback: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during Instagram authentication.")

# --- Login Initiation Functions ---
# (process_google_login, process_facebook_login, process_instagram_login remain unchanged)

async def process_google_login(request: Request):
    redirect_uri = settings.google_redirect_uri
    if not oauth_google or not hasattr(oauth_google, 'google'):
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Google login not configured.")
    return await oauth_google.google.authorize_redirect(request, redirect_uri)

async def process_facebook_login(request: Request):
    redirect_uri = settings.facebook_redirect_uri
    if not oauth_facebook or not hasattr(oauth_facebook, 'facebook'):
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Facebook login not configured.")
    return await oauth_facebook.facebook.authorize_redirect(request, redirect_uri)

async def process_instagram_login(request: Request):
    redirect_uri = settings.instagram_redirect_uri
    if not oauth_instagram or not hasattr(oauth_instagram, 'instagram'):
         raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Instagram login not configured.")
    return await oauth_instagram.instagram.authorize_redirect(request, redirect_uri)
