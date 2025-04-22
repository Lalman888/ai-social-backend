import pytest
from httpx import AsyncClient
from fastapi import status

# Import the FastAPI app instance
# Make sure the path is correct relative to the tests directory
# If tests/ is at the same level as app/, this might work:
from app.main import app

# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_read_root():
    '''Test the root endpoint (/)'''
    # Use AsyncClient for testing FastAPI async endpoints
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Welcome to the FastAPI LangChain MongoDB API"}

# Add more tests for main app logic if needed
