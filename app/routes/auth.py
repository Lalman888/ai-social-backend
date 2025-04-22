from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.services.auth_service import process_google_login, process_google_callback
from app.models.token import Token
from app.models.user import UserPublic
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/login/google", summary="Initiate Google OAuth2 login")
async def login_google(request: Request):
    '''
    Redirects the user to Google's authentication page.
    '''
    try:
        response = await process_google_login(request)
        return response
    except Exception as e:
        logger.error(f"Error initiating Google login: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not initiate login.")


@router.get("/google/callback", summary="Handle Google OAuth2 callback")
async def auth_google_callback(request: Request):
    '''
    Handles the callback from Google after user authentication.
    If successful, returns user info and a JWT token.
    '''
    try:
        user, access_token = await process_google_callback(request)

        if user and access_token:
            # Option 1: Return token and user info directly in JSON response
            # This is common for SPAs that store the token in localStorage/sessionStorage
            logger.info(f"Google callback successful for user: {user.email}. Returning JWT.")
            # Convert user model to public representation before returning
            user_public = UserPublic.model_validate(user) # Pydantic V2
            return JSONResponse(content={
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_public.model_dump() # Convert to dict
            })

            # Option 2: Redirect user to frontend with token (e.g., in query param or fragment)
            # Be cautious with tokens in URLs. Fragments (#) are generally safer.
            # frontend_url = f"http://localhost:3000/auth/callback#token={access_token}"
            # return RedirectResponse(url=frontend_url)

            # Option 3: Set token in a secure, HttpOnly cookie (more traditional web app approach)
            # response = RedirectResponse(url="/profile") # Redirect to a protected page
            # response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True, secure=True, samesite='lax')
            # return response

        else:
            # This case should ideally be handled by exceptions within process_google_callback
            logger.error("Google callback processing returned None for user or token without raising exception.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication processing failed.")

    except HTTPException as e:
        # Re-raise HTTPExceptions raised from the service layer
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in Google callback route: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication failed.")

# Example of a protected route (to be added later or in a different router)
# from app.dependencies import get_current_user # Need to create this dependency
#
# @router.get("/users/me", response_model=UserPublic, summary="Get current user")
# async def read_users_me(current_user: UserPublic = Depends(get_current_user)):
#     return current_user
