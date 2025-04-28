from authlib.integrations.starlette_client import OAuth
from app.utils.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize a new OAuth registry or potentially reuse one if managed carefully
# For simplicity, let's assume we might add it to the existing google.py registry later,
# or manage multiple registries. Creating a new one for clarity here:
oauth_facebook = OAuth()

if settings.facebook_client_id and settings.facebook_client_secret:
    logger.info("Registering Facebook OAuth client.")
    oauth_facebook.register(
        name='facebook',
        client_id=settings.facebook_client_id,
        client_secret=settings.facebook_client_secret,
        access_token_url='https://graph.facebook.com/oauth/access_token',
        access_token_params=None,
        authorize_url='https://www.facebook.com/dialog/oauth',
        authorize_params=None,
        api_base_url='https://graph.facebook.com/',
        userinfo_endpoint='me?fields=id,name,email,picture', # Request specific fields
        client_kwargs={
            'scope': 'email public_profile', # Request necessary permissions
            'redirect_uri': settings.facebook_redirect_uri,
            # Facebook uses 'state' for CSRF protection by default with Authlib
        },
    )
else:
    logger.warning("Facebook OAuth client not registered due to missing configuration (FACEBOOK_CLIENT_ID or FACEBOOK_CLIENT_SECRET).")

# To use this, you'd import oauth_facebook from this file in your service/routes.
