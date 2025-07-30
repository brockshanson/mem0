"""
Client seeding utilities for OpenMemory MCP server.
Seeds the database with default client configurations.
"""

import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import ClientRegistry, ClientRegistryStatus


def seed_default_clients():
    """Seed database with default client configurations."""
    db = SessionLocal()
    try:
        default_clients = [
            {
                'client_identifier': 'claude-code',
                'client_type': 'claude-code',
                'model_name': 'claude-3.5-sonnet',
                'endpoint_pattern': '/mcp/claude-code/sse/{user_id}',
                'status': ClientRegistryStatus.approved,
                'auto_approved': True,
                'detection_patterns': {
                    'user_agent_patterns': ['claude-code', 'anthropic-claude-code', '@anthropic/claude-code'],
                    'header_patterns': {
                        'x-client-id': ['claude-code'],
                        'x-mcp-client': ['claude-code']
                    }
                },
                'metadata_': {
                    'description': 'Official Claude Code CLI client',
                    'official': True,
                    'supports_sse': True
                }
            },
            {
                'client_identifier': 'claude-desktop',
                'client_type': 'claude-desktop',
                'model_name': 'claude-3.5-sonnet',
                'endpoint_pattern': '/mcp/claude-desktop/sse/{user_id}',
                'status': ClientRegistryStatus.approved,
                'auto_approved': True,
                'detection_patterns': {
                    'user_agent_patterns': ['electron.*claude', 'claude-desktop', 'anthropic.*desktop'],
                    'header_patterns': {
                        'x-client-id': ['claude-desktop', 'desktop'],
                        'x-mcp-client': ['desktop']
                    }
                },
                'metadata_': {
                    'description': 'Official Claude Desktop application',
                    'official': True,
                    'supports_sse': True
                }
            },
            {
                'client_identifier': 'claude-vscode',
                'client_type': 'claude-vscode',
                'model_name': 'claude-3.5-sonnet',
                'endpoint_pattern': '/mcp/vscode-claude/sse/{user_id}',
                'status': ClientRegistryStatus.approved,
                'auto_approved': True,
                'detection_patterns': {
                    'user_agent_patterns': ['vscode.*claude', 'visual.?studio.?code.*claude'],
                    'header_patterns': {
                        'x-client-id': ['vscode-claude', 'claude-vscode'],
                        'x-model-name': ['claude-3.5-sonnet', 'claude-3-haiku', 'claude-3-opus']
                    }
                },
                'metadata_': {
                    'description': 'Claude extension for VS Code',
                    'official': True,
                    'supports_sse': True,
                    'supports_model_switching': True
                }
            },
            {
                'client_identifier': 'vscode-gpt',
                'client_type': 'vscode-gpt',
                'model_name': 'gpt-4',
                'endpoint_pattern': '/mcp/vscode-gpt/sse/{user_id}',
                'status': ClientRegistryStatus.approved,
                'auto_approved': True,
                'detection_patterns': {
                    'user_agent_patterns': ['vscode.*gpt', 'visual.?studio.?code.*gpt'],
                    'header_patterns': {
                        'x-client-id': ['vscode-gpt', 'gpt-vscode'],
                        'x-model-name': ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo']
                    }
                },
                'metadata_': {
                    'description': 'GPT extension for VS Code',
                    'official': False,
                    'supports_sse': True,
                    'supports_model_switching': True
                }
            },
            {
                'client_identifier': 'ollama',
                'client_type': 'ollama',
                'model_name': None,
                'endpoint_pattern': '/mcp/ollama/sse/{user_id}',
                'status': ClientRegistryStatus.approved,
                'auto_approved': True,
                'detection_patterns': {
                    'user_agent_patterns': ['ollama', 'llama.*cpp', 'ollama.*client'],
                    'header_patterns': {
                        'x-client-id': ['ollama'],
                        'x-model-name': ['llama', 'mistral', 'codellama', 'phi']
                    }
                },
                'metadata_': {
                    'description': 'OLLAMA local LLM client',
                    'official': False,
                    'supports_sse': True,
                    'supports_local_models': True,
                    'variable_models': True
                }
            },
            {
                'client_identifier': 'vscode-generic',
                'client_type': 'vscode-generic',
                'model_name': None,
                'endpoint_pattern': '/mcp/vscode-{model}/sse/{user_id}',
                'status': ClientRegistryStatus.approved,
                'auto_approved': True,
                'detection_patterns': {
                    'user_agent_patterns': ['vscode', 'visual.?studio.?code', 'code-oss', 'cursor'],
                    'header_patterns': {
                        'x-client-id': ['vscode'],
                        'x-editor': ['vscode', 'cursor']
                    }
                },
                'metadata_': {
                    'description': 'Generic VS Code client (any model)',
                    'official': False,
                    'supports_sse': True,
                    'supports_model_switching': True,
                    'variable_models': True
                }
            }
        ]
        
        clients_created = 0
        clients_updated = 0
        
        for client_data in default_clients:
            existing = db.query(ClientRegistry).filter(
                ClientRegistry.client_identifier == client_data['client_identifier']
            ).first()
            
            if existing:
                # Update existing client with new data
                for key, value in client_data.items():
                    if key not in ['client_identifier', 'created_at']:
                        setattr(existing, key, value)
                existing.updated_at = datetime.now(timezone.utc)
                clients_updated += 1
                logging.info(f"Updated existing client: {client_data['client_identifier']}")
            else:
                # Create new client
                client = ClientRegistry(
                    **client_data,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(client)
                clients_created += 1
                logging.info(f"Created new client: {client_data['client_identifier']}")
        
        db.commit()
        logging.info(f"Client seeding completed: {clients_created} created, {clients_updated} updated")
        
        return {
            'clients_created': clients_created,
            'clients_updated': clients_updated,
            'total_processed': len(default_clients)
        }
        
    except Exception as e:
        db.rollback()
        logging.error(f"Error seeding clients: {e}")
        raise
    finally:
        db.close()


def get_client_config_summary():
    """Get summary of current client configurations."""
    db = SessionLocal()
    try:
        clients = db.query(ClientRegistry).all()
        
        summary = {
            'total_clients': len(clients),
            'by_status': {},
            'by_type': {},
            'auto_approved': 0,
            'official_clients': 0
        }
        
        for client in clients:
            # Count by status
            status = client.status.value
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            # Count by type
            client_type = client.client_type
            summary['by_type'][client_type] = summary['by_type'].get(client_type, 0) + 1
            
            # Count auto-approved
            if client.auto_approved:
                summary['auto_approved'] += 1
            
            # Count official clients
            if client.metadata_ and client.metadata_.get('official'):
                summary['official_clients'] += 1
        
        return summary
        
    finally:
        db.close()


if __name__ == "__main__":
    # Run seeding if script is executed directly
    print("Seeding default clients...")
    result = seed_default_clients()
    print(f"Seeding result: {result}")
    
    print("\nClient configuration summary:")
    summary = get_client_config_summary()
    print(f"Summary: {summary}")