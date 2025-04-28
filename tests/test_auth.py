import pytest
from httpx import AsyncClient
from fastapi import status, Request
from unittest.mock import patch, MagicMock

from app.main import app # Import the main app instance
from app.models.user import User, UserPublic # Import user models
from app.models.token import Token # Import token model
from app.utils.config import settings # For checking if configured
import logging # Import logging
from typing import Optional # Import Optional for type hinting

# Use the API prefix defined in main.py
API_PREFIX = "/api/v1"
AUTH_URL_PREFIX = f"{API_PREFIX}/auth"

# --- Mocks ---
# Mock user data returned by the service layer after successful login/creation
mock_user_dict = {
    "id": "mock_user_123",
    "_id": "mock_user_123", # Simulate _id being present
    "email": "test@example.com",
    "full_name": "Test User",
    "picture": "http://example.com/pic.jpg",
    "google_id": None,
    "facebook_id": "fb_12345",
    "instagram_id": None,
    "refresh_token": None,
}
# Ensure all fields required by User model are present, even if None
mock_user_dict.setdefault('google_id', None)
mock_user_dict.setdefault('facebook_id', None)
mock_user_dict.setdefault('instagram_id', None)
mock_user_dict.setdefault('refresh_token', None)

mock_user = User.model_validate(mock_user_dict) # Use model_validate

mock_access_token = "mock_jwt_token_string"

# --- Helper for Assertions ---
def assert_auth_response(response, expected_status: int, expected_user: Optional[User] = None, expected_token: Optional[str] = None):
    assert response.status_code == expected_status
    if expected_status == status.HTTP_200_OK:
        assert "access_token" in response.json()
        assert "token_type" in response.json()
        assert "user" in response.json()
        assert response.json()["access_token"] == expected_token
        assert response.json()["token_type"] == "bearer"
        # Validate user structure matches UserPublic (or the expected subset)
        user_resp = response.json()["user"]
        assert user_resp["id"] == expected_user.id
        assert user_resp["email"] == expected_user.email
        assert user_resp["full_name"] == expected_user.full_name
        # Check linked status based on mock user
        assert user_resp["facebook_linked"] == bool(expected_user.facebook_id)
        assert user_resp["google_linked"] == bool(expected_user.google_id)
        assert user_resp["instagram_linked"] == bool(expected_user.instagram_id)

# --- Facebook Tests ---

@pytest.mark.asyncio
@patch("app.routes.auth.process_facebook_login") # Patch where it's called
async def test_login_facebook_redirect(mock_process_login):
    '''Test GET /login/facebook redirects correctly'''
    # Mock the service function to simulate a redirect response
    mock_redirect_response = MagicMock()
    mock_redirect_response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    mock_redirect_response.headers = {'location': 'https://facebook.com/oauth/dialog...'}
    mock_process_login.return_value = mock_redirect_response

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/login/facebook", follow_redirects=False) # Don't follow redirect

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert "location" in response.headers
    assert "facebook.com" in response.headers["location"]
    mock_process_login.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.routes.auth.process_facebook_callback") # Patch where it's called
async def test_auth_facebook_callback_success(mock_process_callback):
    '''Test GET /facebook/callback success'''
    # Mock the service function to return a user and token
    mock_process_callback.return_value = (mock_user, mock_access_token)

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Simulate the callback request (no specific query params needed if mocked)
        response = await client.get(f"{AUTH_URL_PREFIX}/facebook/callback")

    assert_auth_response(response, status.HTTP_200_OK, mock_user, mock_access_token)
    mock_process_callback.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.routes.auth.process_facebook_callback")
async def test_auth_facebook_callback_failure(mock_process_callback):
    '''Test GET /facebook/callback when service raises HTTPException'''
    # Mock the service function to raise an HTTPException
    mock_process_callback.side_effect = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed via Facebook: invalid_credentials"
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/facebook/callback")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Authentication failed via Facebook: invalid_credentials"}
    mock_process_callback.assert_awaited_once()


# --- Instagram Tests ---

@pytest.mark.asyncio
@patch("app.routes.auth.process_instagram_login")
async def test_login_instagram_redirect(mock_process_login):
    '''Test GET /login/instagram redirects correctly'''
    mock_redirect_response = MagicMock()
    mock_redirect_response.status_code = status.HTTP_307_TEMPORARY_REDIRECT
    mock_redirect_response.headers = {'location': 'https://api.instagram.com/oauth/authorize...'}
    mock_process_login.return_value = mock_redirect_response

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/login/instagram", follow_redirects=False)

    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert "location" in response.headers
    assert "instagram.com" in response.headers["location"]
    mock_process_login.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.routes.auth.process_instagram_callback")
async def test_auth_instagram_callback_success(mock_process_callback):
    '''Test GET /instagram/callback success'''
    # Adjust mock user for Instagram (e.g., no email, has instagram_id)
    mock_ig_user_dict = {
        "id": "mock_ig_user_456", "_id": "mock_ig_user_456",
        "email": None, "full_name": "Insta User", "picture": None,
        "google_id": None, "facebook_id": None, "instagram_id": "ig_67890",
        "refresh_token": None,
    }
    mock_ig_user = User.model_validate(mock_ig_user_dict)
    mock_ig_token = "mock_ig_jwt_token"

    mock_process_callback.return_value = (mock_ig_user, mock_ig_token)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/instagram/callback")

    assert_auth_response(response, status.HTTP_200_OK, mock_ig_user, mock_ig_token)
    mock_process_callback.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.routes.auth.process_instagram_callback")
async def test_auth_instagram_callback_failure(mock_process_callback):
    '''Test GET /instagram/callback when service raises HTTPException'''
    mock_process_callback.side_effect = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed via Instagram: token_exchange_failed"
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/instagram/callback")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Authentication failed via Instagram: token_exchange_failed"}
    mock_process_callback.assert_awaited_once()

# --- Tests for Configuration Not Set ---
# These tests check if the endpoints return 501 Not Implemented if config is missing

@pytest.mark.asyncio
@patch("app.services.auth_service.settings", MagicMock(facebook_client_id=None)) # Patch settings in service layer
@patch("app.routes.auth.process_facebook_login") # Patch route to check call behavior
async def test_login_facebook_not_configured(mock_process_login_route):
    # The service layer (process_facebook_login) should raise the 501 error
    # We are mocking the settings used *within* the service layer
    # The route should still call the service function
    mock_process_login_route.side_effect = HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Facebook login is not configured.")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/login/facebook")

    # Assert based on the exception raised by the mocked service function via the route
    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert response.json() == {"detail": "Facebook login is not configured."}
    mock_process_login_route.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.services.auth_service.settings", MagicMock(instagram_client_id=None)) # Patch settings in service layer
@patch("app.routes.auth.process_instagram_login") # Patch route
async def test_login_instagram_not_configured(mock_process_login_route):
    mock_process_login_route.side_effect = HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Instagram login is not configured.")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/login/instagram")

    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert response.json() == {"detail": "Instagram login is not configured."}
    mock_process_login_route.assert_awaited_once()


# Add similar tests for callback endpoints if configuration is missing.
# The service layer should raise the 501 error in those cases too.
@pytest.mark.asyncio
@patch("app.services.auth_service.settings", MagicMock(facebook_client_id=None)) # Patch settings in service layer
@patch("app.routes.auth.process_facebook_callback") # Patch route
async def test_callback_facebook_not_configured(mock_process_callback_route):
    mock_process_callback_route.side_effect = HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Facebook login is not configured.")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/facebook/callback")

    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert response.json() == {"detail": "Facebook login is not configured."}
    mock_process_callback_route.assert_awaited_once()

@pytest.mark.asyncio
@patch("app.services.auth_service.settings", MagicMock(instagram_client_id=None)) # Patch settings in service layer
@patch("app.routes.auth.process_instagram_callback") # Patch route
async def test_callback_instagram_not_configured(mock_process_callback_route):
    mock_process_callback_route.side_effect = HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Instagram login is not configured.")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"{AUTH_URL_PREFIX}/instagram/callback")

    assert response.status_code == status.HTTP_501_NOT_IMPLEMENTED
    assert response.json() == {"detail": "Instagram login is not configured."}
    mock_process_callback_route.assert_awaited_once()
