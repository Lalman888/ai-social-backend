from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.services.ai_service import summarize_text
from pydantic import BaseModel, Field
import logging

# If you implement authentication for this route later:
# from app.dependencies import get_current_user
# from app.models.user import UserPublic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Services"])

class SummarizationRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Text to be summarized")

class SummarizationResponse(BaseModel):
    summary: str

@router.post(
    "/summarize",
    response_model=SummarizationResponse,
    summary="Summarize Text",
    # dependencies=[Depends(get_current_user)] # Uncomment to protect route
)
async def handle_summarize(
    request_body: SummarizationRequest = Body(...)
    # current_user: UserPublic = Depends(get_current_user) # Uncomment for authenticated user info
):
    '''
    Receives text input and returns a summarized version using LangChain.
    Requires authentication.
    '''
    logger.info(f"Received request to summarize text (length: {len(request_body.text)})")
    # logger.info(f"Request received from user: {current_user.email}") # If authenticated

    try:
        summary = await summarize_text(request_body.text)
        return SummarizationResponse(summary=summary)
    except RuntimeError as e:
         logger.error(f"Runtime error during summarization: {e}", exc_info=True)
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e: # e.g., if input validation fails in service
         logger.warning(f"Value error during summarization: {e}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process summarization request.")
