from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer # Use Bearer token security scheme
from jose import JWTError
from pydantic import ValidationError # Import ValidationError
from typing import Optional

from app.utils import jwt as jwt_utils # Import JWT utility functions
from app.services.auth_service import get_user_by_email # Import function to fetch user
from app.models.user import UserPublic, User # Import User models
from app.models.token import TokenData # Import TokenData model
import logging

logger = logging.getLogger(__name__)

# Define the OAuth2 scheme. tokenUrl is not strictly needed if we don't use
# the Swagger UI "Authorize" button with password flow, but it's good practice.
# It points to the endpoint where tokens *would* be obtained (e.g., login callback).
# For social OAuth, the token is obtained externally, so this URL is somewhat arbitrary.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/google") # Example token URL

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    '''
    Dependency function to get the current authenticated user.
    Verifies JWT token from the Authorization header and fetches user data.
    '''
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data: Optional[TokenData] = jwt_utils.decode_access_token(token)

    if token_data is None or token_data.sub is None:
        logger.warning("Token decoding failed or 'sub' missing in token payload.")
        raise credentials_exception

    # Assuming the 'sub' field contains the user's email address
    # If it contains user ID, change get_user_by_email to get_user_by_id
    user: Optional[User] = await get_user_by_email(email=token_data.sub)

    if user is None:
        logger.warning(f"User with email {token_data.sub} from token not found in DB.")
        raise credentials_exception

    # Convert the DB user model to the public representation
    # Ensure all necessary fields for UserPublic are present in User
    try:
        # We need a way to construct UserPublic from User.
        # Let's assume UserPublic can be validated from User model directly
        # or use a helper function if defined (like the example in user.py)

        # Option 1: Direct validation (if UserPublic fields are subset of User)
        # user_public = UserPublic.model_validate(user) # Pydantic V2

        # Option 2: Manual construction (more explicit control)
        user_public = UserPublic(
            id=str(user.id), # Ensure id is string
            email=user.email,
            full_name=user.full_name,
            picture=user.picture,
            google_linked=bool(user.google_id),
            facebook_linked=bool(user.facebook_id),
            instagram_linked=bool(user.instagram_id)
        )
        return user_public

    except ValidationError as e:
         logger.error(f"Failed to validate UserPublic model for user {user.id}: {e}", exc_info=True)
         # Raise credentials exception as user data seems inconsistent
         raise credentials_exception
    except Exception as e:
         # Catch any other unexpected errors during model conversion
         logger.error(f"Error creating UserPublic for user {user.id}: {e}", exc_info=True)
         raise credentials_exception


# Example of a dependency for optional authentication
async def get_optional_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[UserPublic]:
     if not token:
          return None
     try:
          return await get_current_user(token)
     except HTTPException:
          # If token is provided but invalid, treat as unauthenticated
          return None
