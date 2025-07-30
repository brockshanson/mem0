"""
Background task utilities for async processing
"""
import asyncio
import logging
from uuid import UUID

from app.database import get_db
from app.models import Memory, Category, memory_categories
from app.utils.categorization import get_categories_for_memory


async def categorize_memory_async(memory_id: UUID):
    """
    Asynchronously categorize a memory in the background.
    
    Args:
        memory_id: UUID of the memory to categorize
    """
    try:
        # Get a fresh database session
        db = next(get_db())
        
        # Fetch the memory
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if not memory:
            logging.error(f"Memory {memory_id} not found for background categorization")
            return
        
        # Extract infer parameter from metadata
        metadata = memory.metadata_ or {}
        infer = metadata.get('infer', True)
        
        # Get categories for the memory (without processing status)
        category_names = get_categories_for_memory(memory.content, infer=infer)
        
        # Update metadata with processing status (separate from categories)
        processing_status = "processed" if infer else "unprocessed"
        metadata['processing_status'] = processing_status
        memory.metadata_ = metadata
        
        # Get or create categories in the database (using same logic as synchronous version)
        for category_name in category_names:
            category = db.query(Category).filter(Category.name == category_name).first()
            if not category:
                category = Category(
                    name=category_name,
                    description=f"Automatically created category for {category_name}"
                )
                db.add(category)
                db.flush()  # Flush to get the category ID

            # Check if the memory-category association already exists
            existing = db.execute(
                memory_categories.select().where(
                    (memory_categories.c.memory_id == memory.id) &
                    (memory_categories.c.category_id == category.id)
                )
            ).first()

            if not existing:
                # Create the association
                db.execute(
                    memory_categories.insert().values(
                        memory_id=memory.id,
                        category_id=category.id
                    )
                )
        
        # Commit the changes
        db.commit()
        
        logging.info(f"Background categorization completed for memory {memory_id}: {category_names}")
        
    except Exception as e:
        logging.error(f"Error in background categorization for memory {memory_id}: {e}")
        db.rollback()
    finally:
        if 'db' in locals():
            db.close()


def schedule_background_categorization(memory_id: UUID):
    """
    Schedule a memory for background categorization.
    
    Args:
        memory_id: UUID of the memory to categorize
    """
    try:
        # Schedule the async task to run in the background
        # Note: In a production environment, you'd want to use a proper task queue like Celery
        asyncio.create_task(categorize_memory_async(memory_id))
        logging.info(f"Scheduled background categorization for memory {memory_id}")
    except Exception as e:
        logging.error(f"Failed to schedule background categorization for memory {memory_id}: {e}")
