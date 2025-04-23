import os
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from dotenv import load_dotenv

# Determine the base directory and load .env
# This assumes .env is in the project root, two levels up from app/utils/
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = Field(..., alias='MONGO_URI')

    # Google OAuth2
    google_client_id: str = Field(..., alias='GOOGLE_CLIENT_ID')
    google_client_secret: str = Field(..., alias='GOOGLE_CLIENT_SECRET')
    google_redirect_uri: str = Field(..., alias='GOOGLE_REDIRECT_URI')

    # JWT
    jwt_secret_key: str = Field(..., alias='JWT_SECRET_KEY')
    algorithm: str = Field("HS256", alias='ALGORITHM')
    access_token_expire_minutes: int = Field(30, alias='ACCESS_TOKEN_EXPIRE_MINUTES')

    # OpenAI
    openai_api_key: str = Field(..., alias='OPENAI_API_KEY')

    # App Settings (e.g., for Authlib session signing)
    app_secret_key: str = Field(..., alias='APP_SECRET_KEY')

    # Facebook OAuth2
    facebook_client_id: Optional[str] = Field(None, alias='FACEBOOK_CLIENT_ID')
    facebook_client_secret: Optional[str] = Field(None, alias='FACEBOOK_CLIENT_SECRET')
    facebook_redirect_uri: Optional[str] = Field(None, alias='FACEBOOK_REDIRECT_URI')

    # Instagram Basic Display API OAuth2
    instagram_client_id: Optional[str] = Field(None, alias='INSTAGRAM_CLIENT_ID')
    instagram_client_secret: Optional[str] = Field(None, alias='INSTAGRAM_CLIENT_SECRET')
    instagram_redirect_uri: Optional[str] = Field(None, alias='INSTAGRAM_REDIRECT_URI')

    class Config:
        # If you don't use alias, Pydantic will expect env var names
        # to match field names exactly (e.g., MONGO_URI for mongo_uri)
        # Using alias allows us to use the .env names directly.
        # Pydantic v2 automatically looks for .env files, but explicit loading
        # ensures the correct path relative to this file.
        env_file = str(env_path)
        env_file_encoding = 'utf-8'
        case_sensitive = True # Important if your env var names have mixed case

# Create a single instance to be imported elsewhere
settings = Settings()

# Example usage (optional, for testing):
if __name__ == "__main__":
    print("Loaded settings:")
    print(f"Mongo URI: {settings.mongo_uri}")
    print(f"Google Client ID: {settings.google_client_id}")
    # Add other prints as needed
