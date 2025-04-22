from fastapi import HTTPException, status, Request
from typing import Optional # Added Optional import
from app.db.database import get_database
from app.models.user import UserBase, UserCreate, UserInDBBase, User
from app.utils.jwt import create_access_token
from app.auth.google import oauth # Import the configured OAuth object
from authlib.integrations.base_client.errors import OAuthError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

async def get_user_by_google_id(google_id: str) -> Optional[User]:
    '''Finds a user in the database by their Google ID.'''
    db = get_database()
    user_doc = await db.users.find_one({"google_id": google_id})
    if user_doc:
        # Convert ObjectId to string if necessary for Pydantic model
        # Ensure '_id' exists before converting
        if "_id" in user_doc:
            user_doc["_id"] = str(user_doc["_id"])
        else:
            logger.warning(f"'_id' field missing in user document for google_id {google_id}")
            # Handle this case based on your application logic, maybe return None or raise error
            # return None
        try:
            # Use model_validate for Pydantic V2
            return User.model_validate(user_doc)
        except ValidationError as e:
             logger.error(f"Error validating user data from DB for google_id {google_id}: {e}")
             return None # Or handle differently
    return None

async def create_or_update_user(user_info: dict) -> Optional[User]:
    '''Creates a new user or updates an existing one based on Google profile info.'''
    db = get_database()
    google_id = user_info.get("sub") # 'sub' is the standard unique identifier in OIDC
    email = user_info.get("email")

    if not google_id or not email:
        logger.error("Google user info missing 'sub' or 'email'")
        return None # Cannot proceed without essential info

    existing_user = await get_user_by_google_id(google_id)

    user_data = UserInDBBase(
        google_id=google_id,
        email=email,
        full_name=user_info.get("name"),
        picture=user_info.get("picture"),
        # Storing refresh token needs careful consideration regarding security
        # refresh_token=token.get('refresh_token') # Only if available and needed
    )

    if existing_user:
        # Update existing user (maybe only non-null fields)
        logger.info(f"Updating existing user: {email} (Google ID: {google_id})")
        # Use model_dump for Pydantic V2
        update_data = user_data.model_dump(exclude_unset=True, exclude={'google_id'}) # Don't update google_id
        # You might want more specific update logic, e.g., only update if changed
        await db.users.update_one(
            {"google_id": google_id},
            {"$set": update_data}
        )
        # Re-fetch the updated user to ensure consistency
        return await get_user_by_google_id(google_id)
    else:
        # Create new user
        logger.info(f"Creating new user: {email} (Google ID: {google_id})")
        # Convert Pydantic model to dict for MongoDB insertion (use model_dump)
        user_dict = user_data.model_dump()
        insert_result = await db.users.insert_one(user_dict)
        if insert_result.inserted_id:
             # Fetch the newly created user to return the full User object
             # The document fetched will have '_id', which get_user_by_google_id handles
             newly_inserted_user = await db.users.find_one({"_id": insert_result.inserted_id})
             if newly_inserted_user:
                 newly_inserted_user["_id"] = str(newly_inserted_user["_id"])
                 try:
                     return User.model_validate(newly_inserted_user)
                 except ValidationError as e:
                     logger.error(f"Error validating newly inserted user data from DB: {e}")
                     return None
             else:
                 logger.error(f"Could not re-fetch newly inserted user with id {insert_result.inserted_id}")
                 return None # Or handle as appropriate
        else:
             logger.error(f"Failed to insert new user for email: {email}")
             return None


async def process_google_login(request: Request):
    '''Initiates the Google OAuth login flow.'''
    redirect_uri = settings.google_redirect_uri # Or construct dynamically if needed
    # The redirect_uri here MUST match one registered in Google Cloud Console
    # and ideally the one used in oauth.register client_kwargs
    logger.info(f"Initiating Google login, redirecting to Google. Callback URI: {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)


async def process_google_callback(request: Request) -> tuple[Optional[User], Optional[str]]:
    '''Handles the callback from Google, fetches user info, creates/updates user, generates JWT.'''
    try:
        # Exchange authorization code for tokens (access, refresh, id_token)
        token = await oauth.google.authorize_access_token(request)
        logger.debug(f"Received token from Google: {token}") # Be careful logging tokens

        # Fetch user information from Google using the access token
        # 'userinfo' endpoint is standard for OIDC
        # Ensure token is passed correctly based on Authlib version/method
        user_info = await oauth.google.userinfo(token=token)
        # Alternatively, decode the id_token if present and configured:
        # user_info = await oauth.google.parse_id_token(request, token=token) # Check Authlib docs for exact usage
        logger.info(f"Received user info from Google: {user_info}")

        # Validate user info (optional, but good practice)
        if not user_info or not user_info.get("sub"):
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not fetch valid user info from Google",
             )

        # Create or update user in our database
        user = await create_or_update_user(user_info)
        if not user:
            # Logged within create_or_update_user
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create or update user profile.",
            )

        # Generate JWT access token for our application session
        # Use user's unique ID from *our* database or email as the 'sub' claim
        # Using email as subject ('sub') is common and convenient
        access_token_data = {"sub": user.email} # Or user.id if preferred
        access_token = create_access_token(data=access_token_data)

        logger.info(f"JWT generated successfully for user: {user.email}")
        return user, access_token

    except OAuthError as error:
        logger.error(f"OAuth Error during Google callback: {error.description} (Error: {error.error}, URI: {error.uri})")
        # Provide more specific feedback if possible, but avoid leaking sensitive details
        detail = f"Authentication failed via Google. Please try again."
        if "access_denied" in str(error.error):
            detail = "Access denied by user or Google."
        elif "invalid_grant" in str(error.error): # Often due to expired code or redirect_uri mismatch
             detail = "Authentication session expired or invalid. Please try logging in again."

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValidationError as e:
         # Catch validation errors from Pydantic models if they occur here
         logger.error(f"Data validation error during Google callback: {e}", exc_info=True)
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail="Invalid user data encountered during processing.",
         )
    except Exception as e:
        # Catch-all for other unexpected errors
        logger.error(f"Unexpected error processing Google callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during authentication.",
        )
