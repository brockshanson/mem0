"""
Enhanced Client Detection System for OpenMemory MCP Server

This module provides sophisticated client detection and tracking capabilities,
including support for various clients (Claude Code, Claude Desktop, OLLAMA, VS Code extensions)
with model-specific differentiation and unknown client isolation.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from app.database import SessionLocal
from app.models import ClientRegistry, ClientRegistryStatus, ClientSession, User
from fastapi import Request
from sqlalchemy.orm import Session


class ClientDetectionResult:
    """Result of client detection with all relevant metadata."""
    
    def __init__(
        self,
        client_identifier: str,
        client_type: str,
        model_name: Optional[str] = None,
        client_version: Optional[str] = None,
        confidence_score: int = 100,
        endpoint_source: str = "detection",
        is_registered: bool = False,
        registry_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None
    ):
        self.client_identifier = client_identifier
        self.client_type = client_type
        self.model_name = model_name
        self.client_version = client_version
        self.confidence_score = confidence_score
        self.endpoint_source = endpoint_source
        self.is_registered = is_registered
        self.registry_id = registry_id
        self.metadata = metadata or {}


class EnhancedClientDetector:
    """Enhanced client detection with registry-based tracking."""
    
    def __init__(self):
        self.detection_patterns = {
            # Claude Code specific patterns
            'claude-code': {
                'user_agent_patterns': [
                    r'claude-code',
                    r'anthropic-claude-code',
                    r'@anthropic/claude-code'
                ],
                'header_patterns': {
                    'x-client-id': ['claude-code'],
                    'x-mcp-client': ['claude-code']
                }
            },
            
            # Claude Desktop patterns
            'claude-desktop': {
                'user_agent_patterns': [
                    r'electron.*claude',
                    r'claude-desktop',
                    r'anthropic.*desktop'
                ],
                'header_patterns': {
                    'x-client-id': ['claude-desktop', 'desktop'],
                    'x-mcp-client': ['desktop']
                }
            },
            
            # VS Code extension patterns
            'claude-vscode': {
                'user_agent_patterns': [
                    r'vscode.*claude',
                    r'visual.?studio.?code.*claude',
                    r'code-oss.*claude',
                    r'cursor.*claude'
                ],
                'header_patterns': {
                    'x-client-id': ['vscode-claude', 'claude-vscode'],
                    'x-model-name': ['claude-3.5-sonnet', 'claude-3-haiku', 'claude-3-opus']
                }
            },
            
            # OLLAMA patterns - model-specific detection
            'ollama': {
                'user_agent_patterns': [
                    r'ollama',
                    r'llama.*cpp',
                    r'ollama.*client',
                    r'ollama-[\w\.\:]+',  # Match ollama-model:version patterns
                ],
                'header_patterns': {
                    'x-client-id': ['ollama', 'ollama-llama3.1:8b', 'ollama-mistral', 'ollama-codellama', 'ollama-phi'],
                    'x-model-name': ['llama', 'mistral', 'codellama', 'phi', 'llama3.1:8b', 'qwen', 'gemma']
                }
            },
            
            # Generic VS Code (any model)
            'vscode-generic': {
                'user_agent_patterns': [
                    r'vscode',
                    r'visual.?studio.?code',
                    r'code-oss',
                    r'cursor'
                ],
                'header_patterns': {
                    'x-client-id': ['vscode'],
                    'x-editor': ['vscode', 'cursor']
                }
            }
        }
    
    def detect_client_from_request(self, request: Request, endpoint_path: str) -> ClientDetectionResult:
        """
        Detect client type from HTTP request with enhanced accuracy.
        
        Args:
            request: FastAPI Request object
            endpoint_path: The endpoint path used (for endpoint-based detection)
            
        Returns:
            ClientDetectionResult with detection details
        """
        headers = dict(request.headers)
        user_agent = headers.get("user-agent", "").lower()
        
        # First, try endpoint-based detection (highest confidence)
        endpoint_result = self._detect_from_endpoint(endpoint_path)
        if endpoint_result:
            endpoint_result.endpoint_source = "endpoint"
            endpoint_result.confidence_score = 95
            # Enhance with header information
            self._enhance_with_headers(endpoint_result, headers)
            return endpoint_result
        
        # Then try header-based detection
        header_result = self._detect_from_headers(headers)
        if header_result:
            header_result.endpoint_source = "headers"
            header_result.confidence_score = 85
            return header_result
        
        # Finally, try user-agent based detection
        ua_result = self._detect_from_user_agent(user_agent)
        if ua_result:
            ua_result.endpoint_source = "user_agent"
            ua_result.confidence_score = 70
            return ua_result
        
        # Unknown client - check if it should be blocked
        unknown_result = self._create_unknown_client_result(request)
        
        # Log unknown client access attempt
        logging.warning(f"Unknown client access attempt: {unknown_result.client_identifier} "
                       f"from {headers.get('user-agent', 'unknown')} at {endpoint_path}")
        
        return unknown_result
    
    def _detect_from_endpoint(self, endpoint_path: str) -> Optional[ClientDetectionResult]:
        """Detect client from endpoint path pattern."""
        endpoint_patterns = {
            r'/mcp/claude-code/': ('claude-code', 'Claude Code'),
            r'/mcp/claude-desktop/': ('claude-desktop', 'Claude Desktop'),
            r'/mcp/ollama-([^/]+)/': ('ollama', 'OLLAMA'),  # Model-specific Ollama endpoints
            r'/mcp/ollama/': ('ollama', 'OLLAMA'),  # Generic Ollama endpoint
            r'/mcp/vscode-claude/': ('claude-vscode', 'Claude VS Code'),
            r'/mcp/vscode-gpt/': ('vscode-gpt', 'GPT VS Code'),
            r'/mcp/vscode-([^/]+)/': ('vscode-generic', 'VS Code'),
        }
        
        for pattern, (client_type, display_name) in endpoint_patterns.items():
            match = re.search(pattern, endpoint_path)
            if match:
                # Extract model name from patterns
                model_name = None
                if 'ollama-' in pattern and match.groups():
                    # Extract Ollama model name (e.g., ollama-llama3.1:8b)
                    model_name = match.group(1).replace(':', '_')  # Replace : with _ for URL safety
                elif 'vscode-' in pattern and match.groups():
                    model_name = match.group(1)
                elif client_type == 'vscode-gpt':
                    model_name = 'gpt-4'
                elif client_type == 'claude-vscode':
                    model_name = 'claude-3.5-sonnet'  # default
                
                # Create unique identifier for model-specific clients
                if client_type == 'ollama' and model_name:
                    client_identifier = f"ollama-{model_name}"
                    display_name = f"OLLAMA ({model_name.replace('_', ':')})"
                else:
                    client_identifier = f"{client_type}-{model_name}" if model_name else client_type
                    display_name = None
                
                return ClientDetectionResult(
                    client_identifier=client_identifier,
                    client_type=client_type,
                    model_name=model_name.replace('_', ':') if model_name else None,  # Convert back for storage
                    endpoint_source="endpoint"
                )
        
        return None
    
    def _detect_from_headers(self, headers: Dict[str, str]) -> Optional[ClientDetectionResult]:
        """Detect client from HTTP headers."""
        # Check for OpenMemory Web UI first (highest priority)
        referer = headers.get('referer', '')
        origin = headers.get('origin', '')
        
        # If request comes from localhost:3000 (Web UI), it's OpenMemory
        if 'localhost:3000' in referer or 'localhost:3000' in origin:
            return ClientDetectionResult(
                client_identifier='openmemory',
                client_type='openmemory',
                confidence_score=100,
                endpoint_source='web_ui'
            )
        
        # Check for explicit client identification headers
        client_id = headers.get('x-client-id', '')
        mcp_client = headers.get('x-mcp-client', '')
        model_name = headers.get('x-model-name', '')
        client_version = headers.get('x-client-version', '')
        
        if client_id or mcp_client:
            client_identifier = client_id or mcp_client
            
            # Map known client identifiers
            client_type_mapping = {
                'claude-code': 'claude-code',
                'claude-desktop': 'claude-desktop', 
                'desktop': 'claude-desktop',
                'vscode-claude': 'claude-vscode',
                'claude-vscode': 'claude-vscode',
                'vscode': 'vscode-generic',
                'ollama': 'ollama'
            }
            
            # Handle model-specific Ollama clients (e.g., ollama-llama3.1:8b)
            if client_identifier.lower().startswith('ollama-'):
                client_type = 'ollama'
                # Use the full identifier for model-specific clients
                return ClientDetectionResult(
                    client_identifier=client_identifier,
                    client_type=client_type,
                    model_name=model_name if model_name else client_identifier.split('-', 1)[1],
                    client_version=client_version if client_version else None
                )
            
            client_type = client_type_mapping.get(client_identifier.lower(), 'unknown')
            
            return ClientDetectionResult(
                client_identifier=client_identifier,
                client_type=client_type,
                model_name=model_name if model_name else None,
                client_version=client_version if client_version else None
            )
        
        return None
    
    def _detect_from_user_agent(self, user_agent: str) -> Optional[ClientDetectionResult]:
        """Detect client from User-Agent string."""
        for client_type, patterns in self.detection_patterns.items():
            for pattern in patterns['user_agent_patterns']:
                if re.search(pattern, user_agent, re.IGNORECASE):
                    # Extract version if possible
                    version_match = re.search(r'(?:version|v)[\s/]?(\d+\.\d+\.\d+)', user_agent, re.IGNORECASE)
                    client_version = version_match.group(1) if version_match else None
                    
                    return ClientDetectionResult(
                        client_identifier=client_type,
                        client_type=client_type,
                        client_version=client_version
                    )
        
        return None
    
    def _enhance_with_headers(self, result: ClientDetectionResult, headers: Dict[str, str]):
        """Enhance detection result with header information."""
        if not result.model_name:
            result.model_name = headers.get('x-model-name')
        
        if not result.client_version:
            result.client_version = headers.get('x-client-version')
        
        # Add additional metadata
        result.metadata.update({
            'user_agent': headers.get('user-agent'),
            'referer': headers.get('referer'),
            'origin': headers.get('origin'),
            'host': headers.get('host')
        })
    
    def _create_unknown_client_result(self, request: Request) -> ClientDetectionResult:
        """Create result for unknown client."""
        headers = dict(request.headers)
        user_agent = headers.get('user-agent', 'unknown')
        
        # Create a hash-based identifier for unknown clients
        client_hash = hashlib.md5(user_agent.encode()).hexdigest()[:8]
        
        return ClientDetectionResult(
            client_identifier=f"unknown-{client_hash}",
            client_type="unknown",
            confidence_score=0,
            endpoint_source="unknown",
            metadata={
                'user_agent': user_agent,
                'headers': dict(headers),
                'url': str(request.url),
                'method': request.method
            }
        )


def get_or_create_client_registry(
    db: Session, 
    detection_result: ClientDetectionResult
) -> Tuple[ClientRegistry, bool]:
    """
    Get or create client registry entry.
    
    Returns:
        Tuple of (ClientRegistry object, created boolean)
    """
    # Check if client already exists
    existing = db.query(ClientRegistry).filter(
        ClientRegistry.client_identifier == detection_result.client_identifier
    ).first()
    
    if existing:
        # Update last seen time
        existing.last_seen_at = datetime.now(timezone.utc)
        db.commit()
        return existing, False
    
    # Create new registry entry
    registry = ClientRegistry(
        client_identifier=detection_result.client_identifier,
        client_type=detection_result.client_type,
        model_name=detection_result.model_name,
        client_version=detection_result.client_version,
        endpoint_pattern=f"/mcp/{detection_result.client_type}/sse/{{user_id}}",
        status=ClientRegistryStatus.pending if detection_result.client_type == "unknown" else ClientRegistryStatus.approved,
        auto_approved=detection_result.client_type != "unknown",
        detection_patterns={
            'confidence_score': detection_result.confidence_score,
            'endpoint_source': detection_result.endpoint_source
        },
        metadata_=detection_result.metadata,
        last_seen_at=datetime.now(timezone.utc)
    )
    
    db.add(registry)
    db.commit()
    db.refresh(registry)
    
    return registry, True


def create_client_session(
    db: Session,
    client_registry: ClientRegistry,
    user: User,
    request: Request,
    detection_result: ClientDetectionResult
) -> ClientSession:
    """Create a new client session."""
    # Generate session token
    session_data = f"{user.id}{client_registry.id}{datetime.now(timezone.utc).isoformat()}"
    session_token = hashlib.sha256(session_data.encode()).hexdigest()
    
    session = ClientSession(
        client_registry_id=client_registry.id,
        user_id=user.id,
        session_token=session_token,
        endpoint_used=str(request.url.path),
        user_agent=request.headers.get('user-agent'),
        ip_address=request.client.host if request.client else None,
        request_headers=dict(request.headers),
        confidence_score=detection_result.confidence_score
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


def get_enhanced_client_info(request: Request, endpoint_path: str) -> Dict:
    """
    Main function to get enhanced client information.
    
    Returns comprehensive client information for memory metadata.
    """
    detector = EnhancedClientDetector()
    detection_result = detector.detect_client_from_request(request, endpoint_path)
    
    db = SessionLocal()
    try:
        # Get or create registry entry
        registry, created = get_or_create_client_registry(db, detection_result)
        
        client_info = {
            'client_identifier': detection_result.client_identifier,
            'client_type': detection_result.client_type,
            'model_name': detection_result.model_name,
            'client_version': detection_result.client_version,
            'endpoint_source': detection_result.endpoint_source,
            'confidence_score': detection_result.confidence_score,
            'is_registered': not created,
            'registry_status': registry.status.value,
            'registry_id': str(registry.id),
            'detection_metadata': detection_result.metadata
        }
        
        return client_info
        
    finally:
        db.close()


def is_client_approved(client_identifier: str) -> bool:
    """Check if a client is approved for memory operations."""
    db = SessionLocal()
    try:
        registry = db.query(ClientRegistry).filter(
            ClientRegistry.client_identifier == client_identifier,
            ClientRegistry.status == ClientRegistryStatus.approved
        ).first()
        
        return registry is not None
        
    finally:
        db.close()