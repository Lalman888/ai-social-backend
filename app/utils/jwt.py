from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.utils.config import settings
from app.models.token import TokenData
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    '''Creates a JWT access token.'''
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except JWTError as e:
        logger.error(f"Error encoding JWT: {e}")
        raise  # Re-raise the error to be handled upstream

def decode_access_token(token: str) -> Optional[TokenData]:
    '''Decodes a JWT access token and returns the payload.'''
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 'sub' is a standard claim for subject (often user identifier)
        subject: Optional[str] = payload.get("sub")
        if subject is None:
            logger.warning("Token payload missing 'sub' (subject)")
            # Depending on policy, might return None or raise an error
            # return None # Or raise credentials_exception

        # You can add more validation here (e.g., check for required claims)

        token_data = TokenData(sub=subject) # Pass other claims if defined in TokenData
        # Optionally check token expiry here again, though jwt.decode handles it
        # expire = payload.get("exp")
        # if expire and datetime.fromtimestamp(expire, timezone.utc) < datetime.now(timezone.utc):
        #     logger.warning("Token has expired (redundant check)")
        #     # raise credentials_exception # Handled by jwt.decode

        return token_data
    except JWTError as e:
        logger.error(f"Could not validate credentials: {e}")
        # Return None or raise a specific exception (e.g., FastAPI's HTTPException)
        return None # Indicates failure to decode/validate
    except Exception as e:
        logger.error(f"An unexpected error occurred during token decoding: {e}")
        return None

# Example usage (for testing)
# if __name__ == "__main__":
#     test_data = {"sub": "test@example.com"}
#     token = create_access_token(test_data)
#     print(f"Generated Token: {token}")
#     decoded = decode_access_token(token)
#     print(f"Decoded Token Data: {decoded}")
#     invalid_token = token + "invalid"
#     decoded_invalid = decode_access_token(invalid_token)
#     print(f"Decoded Invalid Token: {decoded_invalid}")
