"""
Memory Operation Validation Utilities

This module provides validation functions to prevent phantom memory operations
and ensure data consistency between PostgreSQL and Qdrant.
"""

import logging
import uuid
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.models import Memory, MemoryState

logger = logging.getLogger(__name__)


def validate_memory_exists(db: Session, memory_id: str, user_id: str) -> bool:
    """
    Validate that a memory exists in the database before performing operations.
    
    Args:
        db: Database session
        memory_id: Memory ID to validate
        user_id: User ID for additional validation
        
    Returns:
        True if memory exists and is accessible, False otherwise
    """
    try:
        # Convert string ID to UUID
        memory_uuid = uuid.UUID(memory_id)
        
        # Query for the memory with proper filters
        memory = db.query(Memory).filter(
            Memory.id == memory_uuid,
            Memory.state != MemoryState.deleted,
            Memory.state != MemoryState.archived
        ).first()
        
        return memory is not None
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid memory ID format: {memory_id}, error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error validating memory existence for {memory_id}: {e}")
        return False


def validate_memory_operations(operations: List[Dict[str, Any]], db: Session, user_id: str) -> List[Dict[str, Any]]:
    """
    Validate memory operations to prevent phantom operations and inappropriate relationships.
    
    Args:
        operations: List of memory operations from mem0
        db: Database session
        user_id: User identifier
        
    Returns:
        Filtered list of validated operations
    """
    validated_operations = []
    
    for operation in operations:
        operation_type = operation.get('event', '').upper()
        memory_id = operation.get('id')
        
        # Log the operation for debugging
        logger.info(f"Validating {operation_type} operation on memory {memory_id}")
        
        # Always allow ADD operations (new memories)
        if operation_type == 'ADD':
            validated_operations.append(operation)
            continue
        
        # For UPDATE and DELETE operations, validate memory exists
        if operation_type in ['UPDATE', 'DELETE'] and memory_id:
            if validate_memory_exists(db, memory_id, user_id):
                validated_operations.append(operation)
                logger.info(f"Validated {operation_type} operation on existing memory {memory_id}")
            else:
                logger.warning(f"Phantom operation prevented: {operation_type} on non-existent memory {memory_id}")
                continue
        
        # Allow NONE operations (no change)
        elif operation_type == 'NONE':
            validated_operations.append(operation)
        
        # For any other operation types, allow them but log
        else:
            logger.info(f"Allowing operation type: {operation_type}")
            validated_operations.append(operation)
    
    logger.info(f"Operation validation complete: {len(operations)} -> {len(validated_operations)} operations")
    return validated_operations


def is_minimal_content(text: str) -> bool:
    """
    Determine if content is too minimal for LLM processing.
    
    Args:
        text: The content to evaluate
        
    Returns:
        True if content should be processed in raw mode
    """
    if not text or not isinstance(text, str):
        return True
    
    # Check word count and character count
    word_count = len(text.split())
    char_count = len(text.strip())
    
    # Consider minimal if very short or just a few words
    return word_count <= 3 or char_count <= 20


def should_use_raw_storage(text: str, infer: bool) -> bool:
    """
    Determine if content should use raw storage instead of LLM processing.
    
    Args:
        text: Content to evaluate
        infer: Original infer parameter
        
    Returns:
        True if raw storage should be used
    """
    if not infer:
        return True
    
    # Auto-fallback for minimal content
    if is_minimal_content(text):
        logger.info(f"Auto-fallback to raw storage for minimal content: '{text}'")
        return True
    
    return False


def log_memory_operation_metrics(operation_type: str, memory_id: str, 
                                success: bool, details: Optional[Dict] = None):
    """
    Log memory operation metrics for monitoring and debugging.
    
    Args:
        operation_type: Type of operation (ADD, UPDATE, DELETE, etc.)
        memory_id: Memory ID involved
        success: Whether operation was successful
        details: Additional operation details
    """
    status = "SUCCESS" if success else "FAILED"
    details_str = f" - {details}" if details else ""
    
    logger.info(f"MEMORY_OPERATION: {operation_type} on {memory_id} - {status}{details_str}")


def validate_database_consistency(db: Session, memory_client, user_id: str) -> Dict[str, Any]:
    """
    Validate consistency between PostgreSQL and Qdrant for debugging.
    
    Args:
        db: Database session
        memory_client: mem0 memory client
        user_id: User identifier
        
    Returns:
        Consistency report dictionary
    """
    try:
        # Get memories from PostgreSQL
        pg_memories = db.query(Memory).filter(
            Memory.state != MemoryState.deleted,
            Memory.state != MemoryState.archived
        ).all()
        
        pg_memory_ids = {str(memory.id) for memory in pg_memories}
        
        # Get memories from Qdrant via mem0
        try:
            qdrant_memories = memory_client.get_all(user_id=user_id)
            if isinstance(qdrant_memories, dict) and 'results' in qdrant_memories:
                qdrant_memory_ids = {memory.get('id') for memory in qdrant_memories['results'] if memory.get('id')}
            else:
                qdrant_memory_ids = {memory.get('id') for memory in qdrant_memories if memory.get('id')}
        except Exception as e:
            logger.error(f"Error getting Qdrant memories: {e}")
            qdrant_memory_ids = set()
        
        # Calculate differences
        only_in_pg = pg_memory_ids - qdrant_memory_ids
        only_in_qdrant = qdrant_memory_ids - pg_memory_ids
        in_both = pg_memory_ids.intersection(qdrant_memory_ids)
        
        consistency_report = {
            'total_pg_memories': len(pg_memory_ids),
            'total_qdrant_memories': len(qdrant_memory_ids),
            'memories_in_both': len(in_both),
            'only_in_postgresql': len(only_in_pg),
            'only_in_qdrant': len(only_in_qdrant),
            'consistency_percentage': (len(in_both) / max(len(pg_memory_ids), len(qdrant_memory_ids))) * 100 if pg_memory_ids or qdrant_memory_ids else 100,
            'phantom_memory_ids': list(only_in_qdrant)[:10],  # Limit to first 10 for logging
            'orphaned_memory_ids': list(only_in_pg)[:10]
        }
        
        if only_in_pg or only_in_qdrant:
            logger.warning(f"Database inconsistency detected: {consistency_report}")
        else:
            logger.info(f"Database consistency check passed: {len(in_both)} memories in sync")
        
        return consistency_report
        
    except Exception as e:
        logger.error(f"Error during consistency validation: {e}")
        return {'error': str(e)}