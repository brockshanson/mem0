import logging
import os
from typing import List

from app.utils.prompts import MEMORY_CATEGORIZATION_PROMPT
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# Only initialize OpenAI client if API key is available
openai_client = None
if os.getenv("OPENAI_API_KEY"):
    openai_client = OpenAI()
else:
    logging.info("OpenAI API key not found, using fallback categorization")


class MemoryCategories(BaseModel):
    categories: List[str]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=15))
def get_categories_for_memory(memory: str, infer: bool = True) -> List[str]:
    """
    Get categories for a memory.
    
    Args:
        memory: The memory content to categorize
        infer: Whether LLM processing was used (True) or not (False)
    
    Returns:
        List of category names (does NOT include processing status to avoid interference with metadata relationality)
    """
    try:
        # If OpenAI client is not available, use simple keyword-based categorization
        if not openai_client:
            return _fallback_categorization(memory)
        
        # Get semantic categories from OpenAI
        messages = [
            {"role": "system", "content": MEMORY_CATEGORIZATION_PROMPT},
            {"role": "user", "content": memory}
        ]

        # Let OpenAI handle the pydantic parsing directly
        completion = openai_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=messages,
            response_format=MemoryCategories,
            temperature=0
        )

        parsed: MemoryCategories = completion.choices[0].message.parsed
        categories = [cat.strip().lower() for cat in parsed.categories]
        
        # NOTE: We deliberately do NOT add processing status as a category 
        # to avoid interference with metadata relationality.
        # Processing status should be tracked in metadata instead.
        
        return categories

    except Exception as e:
        logging.error(f"[ERROR] Failed to get categories: {e}")
        try:
            logging.debug(f"[DEBUG] Raw response: {completion.choices[0].message.content}")
        except Exception as debug_e:
            logging.debug(f"[DEBUG] Could not extract raw response: {debug_e}")
        
        # Fallback to simple categorization on error
        return _fallback_categorization(memory)


def _fallback_categorization(memory: str) -> List[str]:
    """
    Simple keyword-based categorization when OpenAI is not available.
    """
    memory_lower = memory.lower()
    categories = []
    
    # Work-related keywords
    if any(word in memory_lower for word in ['work', 'job', 'career', 'office', 'meeting', 'project', 'client', 'business']):
        categories.append('work')
    
    # Technology keywords
    if any(word in memory_lower for word in ['code', 'programming', 'python', 'javascript', 'api', 'software', 'tech', 'computer']):
        categories.append('technology')
    
    # Personal/Hobby keywords
    if any(word in memory_lower for word in ['hobby', 'guitar', 'music', 'game', 'sport', 'exercise', 'travel', 'book']):
        categories.append('personal')
    
    # Health keywords
    if any(word in memory_lower for word in ['health', 'doctor', 'medicine', 'exercise', 'diet', 'wellness']):
        categories.append('health')
    
    # Default category if none match
    if not categories:
        categories.append('general')
    
    return categories
