"""Add client tracking tables

Revision ID: add_client_tracking_001
Revises: 
Create Date: 2025-01-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_client_tracking_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create client_registry_status enum
    client_registry_status = postgresql.ENUM(
        'pending', 'approved', 'blocked', 'unknown',
        name='clientregistrystatus',
        create_type=False
    )
    client_registry_status.create(op.get_bind(), checkfirst=True)
    
    # Create client_registry table
    op.create_table(
        'client_registry',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_identifier', sa.String(), nullable=False, unique=True),
        sa.Column('client_type', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=True),
        sa.Column('client_version', sa.String(), nullable=True),
        sa.Column('endpoint_pattern', sa.String(), nullable=False),
        sa.Column('status', client_registry_status, nullable=False, default='pending'),
        sa.Column('auto_approved', sa.Boolean(), default=False),
        sa.Column('detection_patterns', postgresql.JSON(), default={}),
        sa.Column('metadata_', postgresql.JSON(), default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for client_registry
    op.create_index('idx_client_identifier', 'client_registry', ['client_identifier'])
    op.create_index('idx_client_type', 'client_registry', ['client_type'])
    op.create_index('idx_client_model_name', 'client_registry', ['model_name'])
    op.create_index('idx_client_status', 'client_registry', ['status'])
    op.create_index('idx_client_created_at', 'client_registry', ['created_at'])
    op.create_index('idx_client_last_seen_at', 'client_registry', ['last_seen_at'])
    op.create_index('idx_client_type_status', 'client_registry', ['client_type', 'status'])
    op.create_index('idx_client_model_status', 'client_registry', ['model_name', 'status'])
    
    # Create client_sessions table
    op.create_table(
        'client_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('client_registry_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(), nullable=False, unique=True),
        sa.Column('endpoint_used', sa.String(), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('request_headers', postgresql.JSON(), default={}),
        sa.Column('confidence_score', sa.Integer(), default=100),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['client_registry_id'], ['client_registry.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
    )
    
    # Create indexes for client_sessions
    op.create_index('idx_session_client_registry_id', 'client_sessions', ['client_registry_id'])
    op.create_index('idx_session_user_id', 'client_sessions', ['user_id'])
    op.create_index('idx_session_token', 'client_sessions', ['session_token'])
    op.create_index('idx_session_started_at', 'client_sessions', ['started_at'])
    op.create_index('idx_session_last_activity_at', 'client_sessions', ['last_activity_at'])
    op.create_index('idx_session_user_client', 'client_sessions', ['user_id', 'client_registry_id'])
    op.create_index('idx_session_activity', 'client_sessions', ['last_activity_at'])
    
    # Insert default approved clients
    op.execute("""
        INSERT INTO client_registry (
            id, client_identifier, client_type, model_name, endpoint_pattern, 
            status, auto_approved, created_at, updated_at
        ) VALUES
        (
            gen_random_uuid(), 'claude-code', 'claude-code', 'claude-3.5-sonnet',
            '/mcp/claude-code/sse/{user_id}', 'approved', true, NOW(), NOW()
        ),
        (
            gen_random_uuid(), 'claude-desktop', 'claude-desktop', 'claude-3.5-sonnet',
            '/mcp/claude-desktop/sse/{user_id}', 'approved', true, NOW(), NOW()
        ),
        (
            gen_random_uuid(), 'claude-vscode', 'claude-vscode', 'claude-3.5-sonnet',
            '/mcp/vscode-claude/sse/{user_id}', 'approved', true, NOW(), NOW()
        ),
        (
            gen_random_uuid(), 'ollama', 'ollama', null,
            '/mcp/ollama/sse/{user_id}', 'approved', true, NOW(), NOW()
        )
    """)


def downgrade():
    # Drop tables
    op.drop_table('client_sessions')
    op.drop_table('client_registry')
    
    # Drop enum
    client_registry_status = postgresql.ENUM(
        'pending', 'approved', 'blocked', 'unknown',
        name='clientregistrystatus'
    )
    client_registry_status.drop(op.get_bind())