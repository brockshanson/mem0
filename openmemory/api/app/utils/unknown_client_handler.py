"""
Unknown Client Handler for OpenMemory MCP Server

This module handles unknown clients with isolation and approval workflows.
It prevents pollution of the tracking system while allowing admins to approve new clients.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from app.database import SessionLocal
from app.models import ClientRegistry, ClientRegistryStatus
from app.utils.client_detection import ClientDetectionResult
from fastapi import HTTPException, Request


class UnknownClientHandler:
    """Handle unknown clients with isolation and approval workflow."""
    
    def __init__(self):
        self.quarantine_endpoint = "/mcp/unknown/sse/{user_id}"
    
    def handle_unknown_client(
        self, 
        detection_result: ClientDetectionResult, 
        request: Request
    ) -> Dict:
        """
        Handle an unknown client access attempt.
        
        Args:
            detection_result: Client detection result
            request: FastAPI Request object
            
        Returns:
            Response dictionary with action taken
        """
        db = SessionLocal()
        try:
            # Check if this unknown client has been seen before
            existing = db.query(ClientRegistry).filter(
                ClientRegistry.client_identifier == detection_result.client_identifier
            ).first()
            
            if existing:
                if existing.status == ClientRegistryStatus.blocked:
                    # Client is blocked - deny access
                    logging.warning(f"Blocked client attempted access: {detection_result.client_identifier}")
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Client '{detection_result.client_identifier}' is blocked"
                    )
                elif existing.status == ClientRegistryStatus.approved:
                    # Client was approved - allow access
                    return {"action": "allowed", "reason": "previously_approved"}
                else:
                    # Client is pending - update last seen
                    existing.last_seen_at = datetime.now(timezone.utc)
                    db.commit()
                    return self._quarantine_client(detection_result, "pending_approval")
            else:
                # New unknown client - create registry entry and quarantine
                new_client = self._create_unknown_client_registry(detection_result, request, db)
                return self._quarantine_client(detection_result, "new_unknown_client")
                
        finally:
            db.close()
    
    def _create_unknown_client_registry(
        self, 
        detection_result: ClientDetectionResult, 
        request: Request,
        db
    ) -> ClientRegistry:
        """Create registry entry for unknown client."""
        headers = dict(request.headers)
        
        client_registry = ClientRegistry(
            client_identifier=detection_result.client_identifier,
            client_type="unknown",
            model_name=None,
            client_version=None,
            endpoint_pattern=self.quarantine_endpoint,
            status=ClientRegistryStatus.unknown,
            auto_approved=False,
            detection_patterns={
                "user_agent": headers.get("user-agent", ""),
                "headers": dict(headers),
                "endpoint_path": str(request.url.path),
                "confidence_score": detection_result.confidence_score,
                "detection_method": detection_result.endpoint_source
            },
            metadata_={
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "ip_address": request.client.host if request.client else None,
                "referer": headers.get("referer"),
                "origin": headers.get("origin"),
                "host": headers.get("host"),
                "quarantined": True,
                "requires_manual_approval": True
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc)
        )
        
        db.add(client_registry)
        db.commit()
        db.refresh(client_registry)
        
        logging.info(f"Created unknown client registry entry: {detection_result.client_identifier}")
        
        # Send notification to admins (could be email, webhook, etc.)
        self._notify_admins_of_unknown_client(client_registry)
        
        return client_registry
    
    def _quarantine_client(self, detection_result: ClientDetectionResult, reason: str) -> Dict:
        """Put client in quarantine mode."""
        return {
            "action": "quarantined",
            "reason": reason,
            "client_identifier": detection_result.client_identifier,
            "message": f"Unknown client '{detection_result.client_identifier}' has been quarantined. "
                      f"Admin approval required for full access.",
            "quarantine_endpoint": self.quarantine_endpoint,
            "limited_functionality": True
        }
    
    def _notify_admins_of_unknown_client(self, client_registry: ClientRegistry):
        """Notify administrators of new unknown client."""
        # In a production system, this could send emails, webhooks, Slack messages, etc.
        logging.warning(
            f"ADMIN NOTIFICATION: New unknown client requires approval: "
            f"{client_registry.client_identifier} (ID: {client_registry.id})"
        )
        
        # Log structured data for monitoring systems
        logging.info(
            "unknown_client_detected",
            extra={
                "client_identifier": client_registry.client_identifier,
                "registry_id": str(client_registry.id),
                "detection_patterns": client_registry.detection_patterns,
                "metadata": client_registry.metadata_,
                "requires_action": True
            }
        )


def is_client_quarantined(client_identifier: str) -> bool:
    """Check if a client is currently quarantined."""
    db = SessionLocal()
    try:
        client = db.query(ClientRegistry).filter(
            ClientRegistry.client_identifier == client_identifier,
            ClientRegistry.status.in_([ClientRegistryStatus.unknown, ClientRegistryStatus.pending])
        ).first()
        
        return client is not None
        
    finally:
        db.close()


def get_quarantined_clients() -> Dict:
    """Get list of all quarantined clients requiring approval."""
    db = SessionLocal()
    try:
        quarantined = db.query(ClientRegistry).filter(
            ClientRegistry.status.in_([ClientRegistryStatus.unknown, ClientRegistryStatus.pending])
        ).order_by(ClientRegistry.created_at.desc()).all()
        
        return {
            "total_quarantined": len(quarantined),
            "clients": [
                {
                    "id": str(client.id),
                    "client_identifier": client.client_identifier,
                    "first_seen": client.created_at.isoformat(),
                    "last_seen": client.last_seen_at.isoformat() if client.last_seen_at else None,
                    "detection_info": client.detection_patterns,
                    "metadata": client.metadata_
                }
                for client in quarantined
            ]
        }
        
    finally:
        db.close()


def approve_quarantined_client(client_id: str, client_type: str, model_name: Optional[str] = None) -> Dict:
    """Approve a quarantined client and move it to approved status."""
    db = SessionLocal()
    try:
        client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
        
        if not client:
            raise ValueError(f"Client with ID {client_id} not found")
        
        if client.status not in [ClientRegistryStatus.unknown, ClientRegistryStatus.pending]:
            raise ValueError(f"Client {client.client_identifier} is not quarantined")
        
        # Update client to approved status
        client.status = ClientRegistryStatus.approved
        client.client_type = client_type
        client.model_name = model_name
        client.endpoint_pattern = f"/mcp/{client_type}/sse/{{user_id}}"
        client.updated_at = datetime.now(timezone.utc)
        
        # Update metadata
        if not client.metadata_:
            client.metadata_ = {}
        client.metadata_.update({
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "quarantined": False,
            "manually_approved": True
        })
        
        db.commit()
        
        logging.info(f"Approved quarantined client: {client.client_identifier} as {client_type}")
        
        return {
            "action": "approved",
            "client_identifier": client.client_identifier,
            "new_client_type": client_type,
            "new_endpoint": client.endpoint_pattern
        }
        
    finally:
        db.close()


def block_quarantined_client(client_id: str, reason: str = "Manual block") -> Dict:
    """Block a quarantined client permanently."""
    db = SessionLocal()
    try:
        client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
        
        if not client:
            raise ValueError(f"Client with ID {client_id} not found")
        
        # Update client to blocked status
        client.status = ClientRegistryStatus.blocked
        client.updated_at = datetime.now(timezone.utc)
        
        # Update metadata
        if not client.metadata_:
            client.metadata_ = {}
        client.metadata_.update({
            "blocked_at": datetime.now(timezone.utc).isoformat(),
            "block_reason": reason,
            "quarantined": False
        })
        
        db.commit()
        
        logging.info(f"Blocked client: {client.client_identifier} - {reason}")
        
        return {
            "action": "blocked",
            "client_identifier": client.client_identifier,
            "reason": reason
        }
        
    finally:
        db.close()