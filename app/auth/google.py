from authlib.integrations.starlette_client import OAuth
from app.utils.config import settings

# Initialize OAuth registry
oauth = OAuth()

# Register Google OAuth client
# Note: 'openid' and 'profile' are often needed along with 'email'
#       to get basic user information including name and picture.
oauth.register(
    name='google',
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile', # Request necessary scopes
        'redirect_uri': settings.google_redirect_uri,
        # Consider adding 'prompt': 'consent' if you always want user approval
        # or need offline access for refresh tokens.
        # 'prompt': 'consent select_account'
    }
    # If you need offline access to get a refresh token:
    # access_type='offline' # Add this within client_kwargs
    # prompt='consent'      # Usually required with offline access
)

# You can potentially add other providers here later
# oauth.register(name='github', ...)
