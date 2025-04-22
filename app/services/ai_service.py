from langchain_openai import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document
from app.utils.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize the language model (ensure OPENAI_API_KEY is set in .env)
try:
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", api_key=settings.openai_api_key)
    # You could potentially use different models or configurations based on settings
except Exception as e:
    logger.error(f"Failed to initialize OpenAI LLM: {e}. Ensure OPENAI_API_KEY is set.", exc_info=True)
    # Handle initialization failure appropriately - maybe raise or use a dummy LLM
    llm = None # Or raise an error that prevents the service from being used

async def summarize_text(text: str) -> str:
    '''
    Summarizes the provided text using LangChain and OpenAI.
    '''
    if not llm:
        logger.error("LLM not initialized. Cannot perform summarization.")
        # Consider raising a specific exception or returning an error message
        raise RuntimeError("AI Service (LLM) is not available.")
        # return "Error: AI Service is not available."

    if not text or not isinstance(text, str) or len(text.strip()) == 0:
         logger.warning("Summarization requested for empty or invalid text.")
         return "" # Or raise ValueError("Input text cannot be empty.")

    try:
        # LangChain expects Document objects
        docs = [Document(page_content=text)]

        # Load the summarization chain (e.g., map_reduce, stuff, refine)
        # 'map_reduce' is often good for longer documents
        chain = load_summarize_chain(llm, chain_type="map_reduce")

        logger.info("Running summarization chain...")
        summary_result = await chain.arun(docs) # Use arun for async execution
        logger.info("Summarization complete.")
        return summary_result

    except Exception as e:
        logger.error(f"Error during LangChain summarization: {e}", exc_info=True)
        # Re-raise or return an error message
        raise RuntimeError(f"Failed to summarize text: {e}")
        # return f"Error: Could not summarize text. {e}"

# You could add other AI functions here (e.g., retrieval, classification)
# async def answer_question(question: str, context: str) -> str:
#     # Implement RAG or QA chain
#     pass
