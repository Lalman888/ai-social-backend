from app.services.ai_service import llm # Reuse the LLM from ai_service (or initialize similarly)
from app.models.automation import GeneratedContentCreate, GeneratedContentInDB, GeneratedContent, SocialPlatform
from app.db.database import get_database
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from pydantic import ValidationError
from typing import List, Optional, Dict, Any # Ensure necessary types are imported
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Example prompt template - can be customized heavily
CONTENT_PROMPT_TEMPLATE = """\
Generate a social media post for {platform} based on the following requirements:
Keywords: {keywords}
Tone: {tone}
Approximate Length: {length} words
Additional Notes: {notes}

Post Content:
"""

async def generate_post_content(
    user_id: str,
    platform: str, # Keep as string or use SocialPlatform enum? String for flexibility.
    keywords: List[str],
    tone: str,
    length: int = 50, # Default length
    notes: Optional[str] = None
) -> Optional[GeneratedContent]:
    '''
    Generates social media post content using an LLM based on input parameters
    and saves the result to the database.
    '''
    if not llm:
        logger.error("LLM not initialized in ai_service. Cannot generate content.")
        raise RuntimeError("AI Service (LLM) is not available.")

    prompt_details = {
        "platform": platform,
        "keywords": ", ".join(keywords), # Join keywords for the prompt
        "tone": tone,
        "length": length,
        "notes": notes or "N/A"
    }

    try:
        # Create prompt and chain
        prompt = PromptTemplate(
            template=CONTENT_PROMPT_TEMPLATE,
            input_variables=["platform", "keywords", "tone", "length", "notes"]
        )
        chain = LLMChain(llm=llm, prompt=prompt)

        logger.info(f"Generating content for user {user_id} with prompt: {prompt_details}")
        # Use arun for async execution if the LLM/chain supports it, otherwise run
        generated_text = None
        if hasattr(chain, 'arun'):
             generated_text = await chain.arun(prompt_details)
        elif hasattr(chain, 'ainvoke'): # Langchain's newer async method
             result = await chain.ainvoke(prompt_details)
             generated_text = result.get('text', '') # Adjust based on actual chain output structure
        else:
             # Fallback to synchronous if no async method available (not ideal in async context)
             logger.warning("Using synchronous LLM chain execution.")
             # Ensure 'run' method exists and handles dict input if needed
             if hasattr(chain, 'run'):
                  if isinstance(prompt_details, dict):
                       # Some older run methods might need kwargs or specific input structure
                       try:
                           generated_text = chain.run(**prompt_details)
                       except TypeError:
                           logger.error("Chain 'run' method doesn't accept keyword arguments directly. Adjusting.")
                           # Try passing the dict directly if that's expected
                           generated_text = chain.run(prompt_details)
                  else:
                       generated_text = chain.run(prompt_details) # Pass dict if chain expects it
             else:
                  logger.error("LLM chain does not have a supported run method (arun, ainvoke, run).")
                  raise RuntimeError("LLM chain execution method not found.")


        if not generated_text:
             logger.error("LLM returned empty content.")
             # Consider if empty content is valid or an error
             return None # Or raise error

        logger.info(f"Content generated successfully for user {user_id}.")

        # --- Save generated content to DB ---
        db = get_database()
        # Ensure collection name is defined, e.g., 'generated_content'
        content_collection = db.generated_content

        content_data = GeneratedContentCreate(
            user_id=user_id,
            prompt=prompt_details, # Store the structured prompt
            model_used=getattr(llm, 'model_name', 'unknown'), # Safer attribute access
            generated_text=generated_text.strip()
        )

        content_dict = content_data.model_dump()
        insert_result = await content_collection.insert_one(content_dict)

        if insert_result.inserted_id:
            created_doc = await content_collection.find_one({"_id": insert_result.inserted_id})
            if created_doc:
                 # Ensure _id is converted for validation
                 if "_id" in created_doc:
                      created_doc["id"] = str(created_doc["_id"]) # Map to 'id' field in model
                 # Validate and return the full DB object using the correct model
                 return GeneratedContent.model_validate(created_doc)
            else:
                 logger.error("Failed to retrieve saved generated content from DB.")
                 return None
        else:
            logger.error("Failed to save generated content to DB.")
            return None

    except ValidationError as e:
        logger.error(f"Validation error creating GeneratedContent model: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error during content generation or saving: {e}", exc_info=True)
        raise RuntimeError(f"Failed to generate or save content: {e}")
