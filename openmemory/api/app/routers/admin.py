"""
Admin endpoints for client management and configuration.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import ClientRegistry, ClientRegistryStatus, ClientSession, User
from app.utils.unknown_client_handler import (
    approve_quarantined_client,
    block_quarantined_client,
    get_quarantined_clients
)
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page, Params, paginate
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class ClientRegistryResponse(BaseModel):
    id: UUID
    client_identifier: str
    client_type: str
    model_name: Optional[str]
    client_version: Optional[str]
    endpoint_pattern: str
    status: str
    auto_approved: bool
    detection_patterns: dict
    metadata_: dict
    created_at: datetime
    updated_at: datetime
    last_seen_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ClientSessionResponse(BaseModel):
    id: UUID
    client_registry_id: UUID
    user_id: UUID
    session_token: str
    endpoint_used: str
    user_agent: Optional[str]
    ip_address: Optional[str]
    confidence_score: int
    started_at: datetime
    last_activity_at: datetime
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UpdateClientRegistryRequest(BaseModel):
    status: Optional[ClientRegistryStatus] = None
    auto_approved: Optional[bool] = None
    detection_patterns: Optional[dict] = None
    metadata_: Optional[dict] = None


class CreateClientRegistryRequest(BaseModel):
    client_identifier: str
    client_type: str
    model_name: Optional[str] = None
    client_version: Optional[str] = None
    endpoint_pattern: str
    status: ClientRegistryStatus = ClientRegistryStatus.pending
    auto_approved: bool = False
    detection_patterns: dict = {}
    metadata_: dict = {}


# List all client registries
@router.get("/clients", response_model=Page[ClientRegistryResponse])
async def list_client_registries(
    status: Optional[ClientRegistryStatus] = None,
    client_type: Optional[str] = None,
    model_name: Optional[str] = None,
    params: Params = Depends(),
    db: Session = Depends(get_db)
):
    """List all client registries with optional filtering."""
    query = db.query(ClientRegistry)
    
    if status:
        query = query.filter(ClientRegistry.status == status)
    if client_type:
        query = query.filter(ClientRegistry.client_type == client_type)
    if model_name:
        query = query.filter(ClientRegistry.model_name == model_name)
    
    query = query.order_by(ClientRegistry.created_at.desc())
    
    return paginate(query, params)


# Get specific client registry
@router.get("/clients/{client_id}", response_model=ClientRegistryResponse)
async def get_client_registry(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """Get specific client registry by ID."""
    client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# Update client registry
@router.put("/clients/{client_id}", response_model=ClientRegistryResponse)
async def update_client_registry(
    client_id: UUID,
    request: UpdateClientRegistryRequest,
    db: Session = Depends(get_db)
):
    """Update client registry configuration."""
    client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)
    
    client.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(client)
    
    logging.info(f"Updated client registry {client_id}: {update_data}")
    return client


# Create new client registry
@router.post("/clients", response_model=ClientRegistryResponse)
async def create_client_registry(
    request: CreateClientRegistryRequest,
    db: Session = Depends(get_db)
):
    """Create new client registry entry."""
    # Check if client identifier already exists
    existing = db.query(ClientRegistry).filter(
        ClientRegistry.client_identifier == request.client_identifier
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Client identifier '{request.client_identifier}' already exists"
        )
    
    client = ClientRegistry(
        client_identifier=request.client_identifier,
        client_type=request.client_type,
        model_name=request.model_name,
        client_version=request.client_version,
        endpoint_pattern=request.endpoint_pattern,
        status=request.status,
        auto_approved=request.auto_approved,
        detection_patterns=request.detection_patterns,
        metadata_=request.metadata_,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    logging.info(f"Created new client registry: {request.client_identifier}")
    return client


# Delete client registry
@router.delete("/clients/{client_id}")
async def delete_client_registry(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete client registry."""
    client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client_identifier = client.client_identifier
    db.delete(client)
    db.commit()
    
    logging.info(f"Deleted client registry: {client_identifier}")
    return {"message": f"Client registry '{client_identifier}' deleted successfully"}


# Approve pending clients
@router.post("/clients/{client_id}/approve")
async def approve_client(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """Approve a pending client."""
    client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.status = ClientRegistryStatus.approved
    client.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logging.info(f"Approved client: {client.client_identifier}")
    return {"message": f"Client '{client.client_identifier}' approved successfully"}


# Block client
@router.post("/clients/{client_id}/block")
async def block_client(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """Block a client."""
    client = db.query(ClientRegistry).filter(ClientRegistry.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.status = ClientRegistryStatus.blocked
    client.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    logging.info(f"Blocked client: {client.client_identifier}")
    return {"message": f"Client '{client.client_identifier}' blocked successfully"}


# List client sessions
@router.get("/sessions", response_model=Page[ClientSessionResponse])
async def list_client_sessions(
    client_registry_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    active_only: bool = Query(False, description="Show only active sessions"),
    params: Params = Depends(),
    db: Session = Depends(get_db)
):
    """List client sessions with optional filtering."""
    query = db.query(ClientSession)
    
    if client_registry_id:
        query = query.filter(ClientSession.client_registry_id == client_registry_id)
    if user_id:
        query = query.filter(ClientSession.user_id == user_id)
    if active_only:
        query = query.filter(ClientSession.ended_at.is_(None))
    
    query = query.order_by(ClientSession.started_at.desc())
    
    return paginate(query, params)


# Get client activity statistics
@router.get("/stats/client-activity")
async def get_client_activity_stats(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get client activity statistics."""
    from sqlalchemy import func
    from datetime import timedelta
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get client type statistics
    client_type_stats = db.query(
        ClientRegistry.client_type,
        func.count(ClientSession.id).label('session_count'),
        func.count(func.distinct(ClientSession.user_id)).label('unique_users')
    ).outerjoin(ClientSession).filter(
        ClientSession.started_at >= cutoff_date
    ).group_by(ClientRegistry.client_type).all()
    
    # Get model statistics
    model_stats = db.query(
        ClientRegistry.model_name,
        func.count(ClientSession.id).label('session_count')
    ).outerjoin(ClientSession).filter(
        ClientSession.started_at >= cutoff_date
    ).group_by(ClientRegistry.model_name).all()
    
    # Get recent registrations
    recent_registrations = db.query(ClientRegistry).filter(
        ClientRegistry.created_at >= cutoff_date
    ).order_by(ClientRegistry.created_at.desc()).limit(10).all()
    
    return {
        "period_days": days,
        "client_type_stats": [
            {
                "client_type": stat.client_type,
                "session_count": stat.session_count,
                "unique_users": stat.unique_users
            }
            for stat in client_type_stats
        ],
        "model_stats": [
            {
                "model_name": stat.model_name,
                "session_count": stat.session_count
            }
            for stat in model_stats
        ],
        "recent_registrations": [
            {
                "client_identifier": reg.client_identifier,
                "client_type": reg.client_type,
                "status": reg.status.value,
                "created_at": reg.created_at
            }
            for reg in recent_registrations
        ]
    }


# Bulk approve/block clients
@router.post("/clients/bulk-action")
async def bulk_client_action(
    client_ids: List[UUID],
    action: str = Query(..., regex="^(approve|block)$"),
    db: Session = Depends(get_db)
):
    """Bulk approve or block clients."""
    if action not in ["approve", "block"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'block'")
    
    clients = db.query(ClientRegistry).filter(ClientRegistry.id.in_(client_ids)).all()
    
    if len(clients) != len(client_ids):
        raise HTTPException(status_code=400, detail="Some client IDs not found")
    
    new_status = ClientRegistryStatus.approved if action == "approve" else ClientRegistryStatus.blocked
    
    for client in clients:
        client.status = new_status
        client.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    logging.info(f"Bulk {action}ed {len(clients)} clients")
    return {"message": f"Successfully {action}ed {len(clients)} clients"}


# Quarantine management endpoints
@router.get("/quarantine")
async def list_quarantined_clients():
    """List all quarantined clients requiring approval."""
    return get_quarantined_clients()


class ApproveQuarantinedClientRequest(BaseModel):
    client_type: str
    model_name: Optional[str] = None


@router.post("/quarantine/{client_id}/approve")
async def approve_quarantined_client_endpoint(
    client_id: UUID,
    request: ApproveQuarantinedClientRequest
):
    """Approve a quarantined client."""
    try:
        result = approve_quarantined_client(
            str(client_id),
            request.client_type,
            request.model_name
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class BlockQuarantinedClientRequest(BaseModel):
    reason: str = "Manual block by admin"


@router.post("/quarantine/{client_id}/block")
async def block_quarantined_client_endpoint(
    client_id: UUID,
    request: BlockQuarantinedClientRequest
):
    """Block a quarantined client."""
    try:
        result = block_quarantined_client(
            str(client_id),
            request.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))