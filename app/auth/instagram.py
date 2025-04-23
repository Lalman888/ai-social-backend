from authlib.integrations.starlette_client import OAuth
from app.utils.config import settings
import logging

logger = logging.getLogger(__name__)

oauth_instagram = OAuth()

if settings.instagram_client_id and settings.instagram_client_secret:
    logger.info("Registering Instagram OAuth client.")
    # Instagram Basic Display API uses different endpoints than Facebook Graph API
    oauth_instagram.register(
        name='instagram',
        client_id=settings.instagram_client_id,
        client_secret=settings.instagram_client_secret,
        access_token_url='https://api.instagram.com/oauth/access_token',
        access_token_params=None,
        authorize_url='https://api.instagram.com/oauth/authorize',
        authorize_params=None,
        api_base_url='https://graph.instagram.com/', # Base URL for API calls after auth
        # User info endpoint requires user ID and access token
        # Authlib might not have a built-in userinfo endpoint for Insta Basic Display
        # We'll likely need to fetch it manually in the callback handler using the access token
        # userinfo_endpoint='me?fields=id,username', # Example structure - adjust based on API docs
        client_kwargs={
            'scope': 'user_profile,user_media', # Required scopes for Basic Display API
            'redirect_uri': settings.instagram_redirect_uri,
            # Instagram requires response_type=code
            'response_type': 'code',
        },
    )
else:
    logger.warning("Instagram OAuth client not registered due to missing configuration (INSTAGRAM_CLIENT_ID or INSTAGRAM_CLIENT_SECRET).")

# To use this, import oauth_instagram from this file.
