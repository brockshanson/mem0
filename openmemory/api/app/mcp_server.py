"""
MCP Server for OpenMemory with resilient memory client handling.

This module implements an MCP (Model Context Protocol) server that provides
memory operations for OpenMemory. The memory client is initialized lazily
to prevent server crashes when external dependencies (like Ollama) are
unavailable. If the memory client cannot be initialized, the server will
continue running with limited functionality and appropriate error messages.

Key features:
- Lazy memory client initialization
- Graceful error handling for unavailable dependencies
- Fallback to database-only mode when vector store is unavailable
- Proper logging for debugging connection issues
- Environment variable parsing for API keys
"""

import contextvars
import datetime
import json
import logging
import uuid

from app.database import SessionLocal
from app.models import Memory, MemoryAccessLog, MemoryState, MemoryStatusHistory
from app.utils.client_detection import get_enhanced_client_info, is_client_approved
from app.utils.unknown_client_handler import UnknownClientHandler
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from app.utils.validation import (
    validate_memory_operations, 
    should_use_raw_storage, 
    log_memory_operation_metrics
)
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from qdrant_client import models as qdrant_models

# Load environment variables
load_dotenv()

# Initialize MCP
mcp = FastMCP("mem0-mcp-server")

# Don't initialize memory client at import time - do it lazily when needed
def get_memory_client_safe():
    """Get memory client with error handling. Returns None if client cannot be initialized."""
    try:
        return get_memory_client()
    except Exception as e:
        logging.warning(f"Failed to get memory client: {e}")
        return None

# Context variables for user_id and enhanced client information
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")
client_info_var: contextvars.ContextVar[dict] = contextvars.ContextVar("client_info")

def detect_claude_client_type(request: Request, base_client_name: str) -> str:
    """
    Detect specific Claude client type based on request headers and metadata.
    
    Args:
        request: FastAPI Request object
        base_client_name: Base client name from URL path
        
    Returns:
        Specific client identifier (e.g., "Claude Desktop", "Claude Code", "Claude VS Code Extension")
    """
    headers = request.headers
    user_agent = headers.get("user-agent", "").lower()
    
    # Check for Claude Code specific indicators
    if "claude-code" in user_agent or "anthropic-claude-code" in user_agent:
        return "Claude Code"
    
    # Check for VS Code extension indicators
    if "vscode" in user_agent or "visual studio code" in user_agent:
        return "Claude VS Code Extension"
    
    # Check for Desktop app indicators
    if "electron" in user_agent or "claude-desktop" in user_agent:
        return "Claude Desktop"
    
    # Check for browser-based access
    for browser in ["chrome", "firefox", "safari", "edge"]:
        if browser in user_agent:
            return f"Claude Web ({browser.title()})"
    
    # Check for mobile indicators
    if any(mobile in user_agent for mobile in ["mobile", "android", "iphone", "ipad"]):
        return "Claude Mobile"
    
    # Check request headers for additional context
    referer = headers.get("referer", "")
    if "claude.ai" in referer:
        return "Claude Web"
    
    # Check for MCP-specific headers that might indicate client type
    mcp_client = headers.get("x-mcp-client", "")
    if mcp_client:
        return f"Claude {mcp_client.title()}"
    
    # Check for custom client identification
    client_id = headers.get("x-client-id", "") or headers.get("x-client-name", "")
    if client_id:
        return f"Claude {client_id.title()}"
    
    # Enhanced VS Code detection
    # Check for VS Code specific patterns
    vs_code_indicators = [
        "vscode", "vs-code", "visual-studio-code", 
        "code-oss", "code-insiders", "cursor"
    ]
    
    # Check if this looks like a VS Code Claude extension vs Claude Code extension
    if base_client_name and any(indicator in base_client_name.lower() for indicator in vs_code_indicators):
        return "Claude VS Code"
    
    # More specific Claude Code extension detection
    if base_client_name and "claude-code" in base_client_name.lower():
        return "Claude Code"
    
    # Check User-Agent for VS Code patterns
    if any(indicator in user_agent.lower() for indicator in vs_code_indicators):
        return "Claude VS Code"
    
    # Fallback to enhanced base name with additional context
    connection_type = "SSE" if "/sse/" in str(request.url) else "HTTP"
    
    # Try to infer from URL patterns or other request characteristics
    if base_client_name and base_client_name != "claude":
        # Clean up the client name for better formatting
        clean_name = base_client_name.replace("-", " ").replace("_", " ").title()
        
        # Special handling for known client types
        if "code" in clean_name.lower() and "claude" not in clean_name.lower():
            return f"Claude {clean_name}"
        return f"Claude {clean_name} ({connection_type})"
    
    return f"Claude Desktop ({connection_type})"  # Default assumption

# Create a router for MCP endpoints
mcp_router = APIRouter(prefix="/mcp")

# Initialize SSE transport
sse = SseServerTransport("/mcp/messages/")

@mcp.tool(description="Add a new memory. This method is called everytime the user informs anything about themselves, their preferences, or anything that has any relevant information which can be useful in the future conversation. This can also be called when the user asks you to remember something. Pass 'infer=False' when the text is already summarized or contains structured facts that don't need LLM inference. Pass 'async_mode=True' for faster responses with background categorization.")
async def add_memories(text: str, infer: bool = True, async_mode: bool = False) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    client_info = client_info_var.get({})

    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app using client identifier for better tracking
            app_id = client_info.get('client_identifier', client_name)
            user, app = get_user_and_app(db, user_id=uid, app_id=app_id)

            # Check if app is active
            if not app.is_active:
                return f"Error: App {app.name} is currently paused on OpenMemory. Cannot create new memories."

            # Check if content should use raw storage (minimal content auto-fallback)
            effective_infer = infer
            metadata = {
                "source_app": "openmemory",
                "mcp_client": client_name,  # Display name
                "client_identifier": client_info.get('client_identifier', client_name),
                "client_type": client_info.get('client_type', 'unknown'),
                "model_name": client_info.get('model_name'),
                "client_version": client_info.get('client_version'),
                "endpoint_source": client_info.get('endpoint_source', 'unknown'),
                "confidence_score": client_info.get('confidence_score', 0),
                "registry_status": client_info.get('registry_status', 'unknown'),
            }
            
            if should_use_raw_storage(text, infer):
                effective_infer = False
                if infer:  # Only add fallback metadata if originally requested inference
                    metadata["auto_fallback"] = "true"
                    metadata["fallback_reason"] = "minimal_content"
                    logging.info(f"Auto-fallback to raw storage for minimal content: '{text}'")
            
            # Format text as messages for mem0
            messages = [{"role": "user", "content": text}]
            
            response = memory_client.add(messages,
                                         user_id=uid,
                                         infer=effective_infer,
                                         metadata=metadata)

            # Process the response and update database with validation
            if isinstance(response, dict) and 'results' in response:
                # Apply validation to prevent phantom operations
                validated_results = validate_memory_operations(response['results'], db, uid)
                
                for result in validated_results:
                    memory_id = uuid.UUID(result['id'])
                    memory = db.query(Memory).filter(Memory.id == memory_id).first()

                    if result['event'] == 'ADD':
                        if not memory:
                            # Include enhanced client information and parameters in metadata
                            memory_metadata = {
                                'source_app': 'openmemory',
                                'mcp_client': client_name,  # Display name
                                'client_identifier': client_info.get('client_identifier', client_name),
                                'client_type': client_info.get('client_type', 'unknown'),
                                'model_name': client_info.get('model_name'),
                                'client_version': client_info.get('client_version'),
                                'endpoint_source': client_info.get('endpoint_source', 'unknown'),
                                'confidence_score': client_info.get('confidence_score', 0),
                                'registry_status': client_info.get('registry_status', 'unknown'),
                                'infer': infer,
                                'async_mode': async_mode
                            }
                            memory = Memory(
                                id=memory_id,
                                user_id=user.id,
                                app_id=app.id,
                                content=result['memory'],
                                metadata_=memory_metadata,
                                state=MemoryState.active
                            )
                            db.add(memory)
                        else:
                            memory.state = MemoryState.active
                            memory.content = result['memory']
                            # Update metadata to include enhanced client information and parameters
                            existing_metadata = memory.metadata_ or {}
                            existing_metadata.update({
                                'source_app': 'openmemory',
                                'mcp_client': client_name,  # Display name
                                'client_identifier': client_info.get('client_identifier', client_name),
                                'client_type': client_info.get('client_type', 'unknown'),
                                'model_name': client_info.get('model_name'),
                                'client_version': client_info.get('client_version'),
                                'endpoint_source': client_info.get('endpoint_source', 'unknown'),
                                'confidence_score': client_info.get('confidence_score', 0),
                                'registry_status': client_info.get('registry_status', 'unknown'),
                                'infer': infer,
                                'async_mode': async_mode
                            })
                            memory.metadata_ = existing_metadata

                        # Create history entry
                        history = MemoryStatusHistory(
                            memory_id=memory_id,
                            changed_by=user.id,
                            old_state=MemoryState.deleted if memory else None,
                            new_state=MemoryState.active
                        )
                        db.add(history)

                    elif result['event'] == 'DELETE':
                        if memory:
                            memory.state = MemoryState.deleted
                            memory.deleted_at = datetime.datetime.now(datetime.UTC)
                            # Create history entry
                            history = MemoryStatusHistory(
                                memory_id=memory_id,
                                changed_by=user.id,
                                old_state=MemoryState.active,
                                new_state=MemoryState.deleted
                            )
                            db.add(history)

                db.commit()

            return str(response)
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error adding to memory: {e}")
        return f"Error adding to memory: {e}"


@mcp.tool(description="Search through stored memories. This method is called EVERYTIME the user asks anything.")
async def search_memory(query: str) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    client_info = client_info_var.get({})
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app using client identifier
            app_id = client_info.get('client_identifier', client_name)
            user, app = get_user_and_app(db, user_id=uid, app_id=app_id)

            # Get accessible memory IDs based on ACL
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]
            
            conditions = [qdrant_models.FieldCondition(key="user_id", match=qdrant_models.MatchValue(value=uid))]
            
            if accessible_memory_ids:
                # Convert UUIDs to strings for Qdrant
                accessible_memory_ids_str = [str(memory_id) for memory_id in accessible_memory_ids]
                conditions.append(qdrant_models.HasIdCondition(has_id=accessible_memory_ids_str))

            filters = qdrant_models.Filter(must=conditions)
            embeddings = memory_client.embedding_model.embed(query, "search")
            
            hits = memory_client.vector_store.client.query_points(
                collection_name=memory_client.vector_store.collection_name,
                query=embeddings,
                query_filter=filters,
                limit=10,
            )

            # Process search results
            memories = hits.points
            memories = [
                {
                    "id": memory.id,
                    "memory": memory.payload["data"],
                    "hash": memory.payload.get("hash"),
                    "created_at": memory.payload.get("created_at"),
                    "updated_at": memory.payload.get("updated_at"),
                    "score": memory.score,
                }
                for memory in memories
            ]

            # Log memory access for each memory found
            if isinstance(memories, dict) and 'results' in memories:
                print(f"Memories: {memories}")
                for memory_data in memories['results']:
                    if 'id' in memory_data:
                        memory_id = uuid.UUID(memory_data['id'])
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="search",
                            metadata_={
                                "query": query,
                                "score": memory_data.get('score'),
                                "hash": memory_data.get('hash')
                            }
                        )
                        db.add(access_log)
                db.commit()
            else:
                for memory in memories:
                    memory_id = uuid.UUID(memory['id'])
                    # Create access log entry
                    access_log = MemoryAccessLog(
                        memory_id=memory_id,
                        app_id=app.id,
                        access_type="search",
                        metadata_={
                            "query": query,
                            "score": memory.get('score'),
                            "hash": memory.get('hash')
                        }
                    )
                    db.add(access_log)
                db.commit()
            return json.dumps(memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(e)
        return f"Error searching memory: {e}"


@mcp.tool(description="List all memories in the user's memory")
async def list_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    client_info = client_info_var.get({})
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app using client identifier
            app_id = client_info.get('client_identifier', client_name)
            user, app = get_user_and_app(db, user_id=uid, app_id=app_id)

            # Get all memories
            memories = memory_client.get_all(user_id=uid)
            filtered_memories = []

            # Filter memories based on permissions
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]
            if isinstance(memories, dict) and 'results' in memories:
                for memory_data in memories['results']:
                    if 'id' in memory_data:
                        memory_id = uuid.UUID(memory_data['id'])
                        if memory_id in accessible_memory_ids:
                            # Create access log entry
                            access_log = MemoryAccessLog(
                                memory_id=memory_id,
                                app_id=app.id,
                                access_type="list",
                                metadata_={
                                    "hash": memory_data.get('hash')
                                }
                            )
                            db.add(access_log)
                            filtered_memories.append(memory_data)
                db.commit()
            else:
                for memory in memories:
                    memory_id = uuid.UUID(memory['id'])
                    memory_obj = db.query(Memory).filter(Memory.id == memory_id).first()
                    if memory_obj and check_memory_access_permissions(db, memory_obj, app.id):
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="list",
                            metadata_={
                                "hash": memory.get('hash')
                            }
                        )
                        db.add(access_log)
                        filtered_memories.append(memory)
                db.commit()
            return json.dumps(filtered_memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error getting memories: {e}")
        return f"Error getting memories: {e}"


@mcp.tool(description="Delete all memories in the user's memory")
async def delete_all_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    client_info = client_info_var.get({})
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app using client identifier
            app_id = client_info.get('client_identifier', client_name)
            user, app = get_user_and_app(db, user_id=uid, app_id=app_id)

            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            # delete the accessible memories only
            for memory_id in accessible_memory_ids:
                try:
                    memory_client.delete(memory_id)
                except Exception as delete_error:
                    logging.warning(f"Failed to delete memory {memory_id} from vector store: {delete_error}")

            # Update each memory's state and create history entries
            now = datetime.datetime.now(datetime.UTC)
            for memory_id in accessible_memory_ids:
                memory = db.query(Memory).filter(Memory.id == memory_id).first()
                # Update memory state
                memory.state = MemoryState.deleted
                memory.deleted_at = now

                # Create history entry
                history = MemoryStatusHistory(
                    memory_id=memory_id,
                    changed_by=user.id,
                    old_state=MemoryState.active,
                    new_state=MemoryState.deleted
                )
                db.add(history)

                # Create access log entry
                access_log = MemoryAccessLog(
                    memory_id=memory_id,
                    app_id=app.id,
                    access_type="delete_all",
                    metadata_={"operation": "bulk_delete"}
                )
                db.add(access_log)

            db.commit()
            return "Successfully deleted all memories"
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"


# Enhanced endpoint routing for different client types
@mcp_router.get("/claude-code/sse/{user_id}")
@mcp_router.get("/claude-desktop/sse/{user_id}")
@mcp_router.get("/ollama/sse/{user_id}")
@mcp_router.get("/vscode-claude/sse/{user_id}")
@mcp_router.get("/vscode-gpt/sse/{user_id}")
@mcp_router.get("/vscode-{model}/sse/{user_id}")
@mcp_router.get("/unknown/sse/{user_id}")
@mcp_router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    """Handle SSE connections for a specific user and client with enhanced detection"""
    # Extract user_id and client_name from path parameters
    uid = request.path_params.get("user_id")
    user_token = user_id_var.set(uid or "")
    base_client_name = request.path_params.get("client_name")
    
    # Get enhanced client information
    endpoint_path = str(request.url.path)
    client_info = get_enhanced_client_info(request, endpoint_path)
    
    # Handle unknown/unapproved clients
    if client_info['client_type'] == 'unknown' or not is_client_approved(client_info['client_identifier']):
        unknown_handler = UnknownClientHandler()
        try:
            # This will either quarantine or allow based on previous approval status
            result = unknown_handler.handle_unknown_client(
                # Create a simple detection result object
                type('ClientDetectionResult', (), client_info)(), 
                request
            )
            if result.get('action') == 'quarantined':
                logging.warning(f"Client quarantined: {client_info['client_identifier']} - {result.get('reason')}")
                # Continue with limited functionality
        except Exception as e:
            logging.error(f"Error handling unknown client: {e}")
            # For now, continue with limited access
    
    # Set context variables
    enhanced_client_name = f"{client_info['client_type']}"
    if client_info['model_name']:
        enhanced_client_name += f" ({client_info['model_name']})"
    
    client_token = client_name_var.set(enhanced_client_name)
    client_info_token = client_info_var.set(client_info)
    
    # Log the detected client for debugging
    logging.info(f"Enhanced MCP client detection: {client_info['client_identifier']} "
                f"[Type: {client_info['client_type']}, Model: {client_info.get('model_name', 'N/A')}, "
                f"Confidence: {client_info['confidence_score']}%]")

    try:
        # Handle SSE connection
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    finally:
        # Clean up context variables
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)
        client_info_var.reset(client_info_token)


@mcp_router.post("/messages/")
async def handle_get_message(request: Request):
    return await handle_post_message(request)


@mcp_router.post("/{client_name}/sse/{user_id}/messages/")
async def handle_post_message(request: Request):
    return await handle_post_message(request)

async def handle_post_message(request: Request):
    """Handle POST messages for SSE"""
    try:
        body = await request.body()

        # Create a simple receive function that returns the body
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        # Create a simple send function that does nothing
        async def send(message):
            return {}

        # Call handle_post_message with the correct arguments
        await sse.handle_post_message(request.scope, receive, send)

        # Return a success response
        return {"status": "ok"}
    finally:
        pass

def setup_mcp_server(app: FastAPI):
    """Setup MCP server with the FastAPI application"""
    mcp._mcp_server.name = "mem0-mcp-server"

    # Include MCP router in the FastAPI app
    app.include_router(mcp_router)
