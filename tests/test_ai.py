import pytest
from httpx import AsyncClient
from fastapi import status
from unittest.mock import patch # Use unittest.mock for patching

from app.main import app, API_PREFIX # Import the main app instance and API_PREFIX

# Use pytest-asyncio for async tests
@pytest.mark.asyncio
@patch("app.routes.ai.summarize_text") # Patch the service function where it's *used* in the router
async def test_summarize_endpoint_success(mock_summarize_text):
    '''Test the /ai/summarize endpoint with mocking - Success case'''
    # Configure the mock to return a successful summary
    mock_summary = "This is the mocked summary."
    # Use awaitable mock for async functions if using AsyncMock,
    # otherwise return_value works for simple cases with standard Mock
    mock_summarize_text.return_value = mock_summary

    test_payload = {"text": "This is a long text that needs summarization."}
    endpoint_url = f"{API_PREFIX}/ai/summarize" # Construct the full URL

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(endpoint_url, json=test_payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"summary": mock_summary}
    # Check if the mocked function was called correctly
    mock_summarize_text.assert_awaited_once_with(test_payload["text"])

@pytest.mark.asyncio
@patch("app.routes.ai.summarize_text") # Patch the service function
async def test_summarize_endpoint_service_unavailable(mock_summarize_text):
    '''Test the /ai/summarize endpoint when the service raises RuntimeError'''
    # Configure the mock to raise a RuntimeError (simulating LLM failure)
    error_message = "AI Service (LLM) is not available."
    mock_summarize_text.side_effect = RuntimeError(error_message)

    test_payload = {"text": "Another text to summarize."}
    endpoint_url = f"{API_PREFIX}/ai/summarize"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(endpoint_url, json=test_payload)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json() == {"detail": error_message}
    mock_summarize_text.assert_awaited_once_with(test_payload["text"])

@pytest.mark.asyncio
async def test_summarize_endpoint_bad_request():
    '''Test the /ai/summarize endpoint with invalid payload'''
    # Test with missing 'text' field
    invalid_payload = {"wrong_field": "some data"}
    endpoint_url = f"{API_PREFIX}/ai/summarize"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(endpoint_url, json=invalid_payload)

    # FastAPI/Pydantic usually returns 422 Unprocessable Entity for validation errors
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    # Check for detail structure if needed, it can be complex
    # Example check for Pydantic V2:
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert len(response_data["detail"]) > 0
    # Check the first error detail
    first_error = response_data["detail"][0]
    assert first_error.get("type") == "missing" # Pydantic V2 type
    assert first_error.get("loc") == ["body", "text"]
    assert "Field required" in first_error.get("msg", "")

# Add more tests for edge cases, authentication (when added), etc.
