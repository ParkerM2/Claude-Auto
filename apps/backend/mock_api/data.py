"""
Mock Data for Graphiti MCP Tools
=================================

Provides mock responses for Graphiti Memory MCP server tools.
These responses simulate the real Graphiti knowledge graph server
for development and testing purposes.

Tool Reference:
- search_nodes: Search entity summaries in the knowledge graph
- search_facts: Search relationships between entities
- add_episode: Add new data to the knowledge graph
- get_episodes: Retrieve recent episodes from the graph
- get_entity_edge: Get specific entity or relationship details
"""

# =============================================================================
# Mock Responses for Graphiti MCP Tools
# =============================================================================

MOCK_RESPONSES = {
    # Search for entity nodes in the knowledge graph
    "search_nodes": {
        "nodes": [
            {
                "uuid": "node-001",
                "name": "Authentication System",
                "summary": "Core authentication system handling user login and session management",
                "node_type": "Component",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-20T14:22:00Z",
                "metadata": {
                    "location": "apps/backend/auth/",
                    "language": "Python",
                    "framework": "FastAPI"
                }
            },
            {
                "uuid": "node-002",
                "name": "Database Connection Pool",
                "summary": "SQLAlchemy connection pool configuration for PostgreSQL database",
                "node_type": "Infrastructure",
                "created_at": "2024-01-12T08:15:00Z",
                "updated_at": "2024-01-18T16:45:00Z",
                "metadata": {
                    "location": "apps/backend/core/database.py",
                    "max_connections": 20
                }
            },
            {
                "uuid": "node-003",
                "name": "User Model",
                "summary": "SQLAlchemy ORM model representing user entities in the database",
                "node_type": "Model",
                "created_at": "2024-01-10T12:00:00Z",
                "updated_at": "2024-01-22T09:30:00Z",
                "metadata": {
                    "table_name": "users",
                    "fields": ["id", "email", "username", "created_at"]
                }
            }
        ],
        "total_results": 3,
        "query": "authentication database"
    },

    # Search for relationships (facts) between entities
    "search_facts": {
        "facts": [
            {
                "uuid": "fact-001",
                "source_node_uuid": "node-001",
                "target_node_uuid": "node-002",
                "relationship": "uses",
                "summary": "Authentication System uses Database Connection Pool for user session persistence",
                "created_at": "2024-01-15T10:35:00Z",
                "confidence": 0.95,
                "metadata": {
                    "discovered_by": "code_analysis",
                    "file_reference": "apps/backend/auth/session.py"
                }
            },
            {
                "uuid": "fact-002",
                "source_node_uuid": "node-001",
                "target_node_uuid": "node-003",
                "relationship": "manages",
                "summary": "Authentication System manages User Model instances for login operations",
                "created_at": "2024-01-15T10:40:00Z",
                "confidence": 0.98,
                "metadata": {
                    "discovered_by": "code_analysis",
                    "pattern": "CRUD operations"
                }
            },
            {
                "uuid": "fact-003",
                "source_node_uuid": "node-003",
                "target_node_uuid": "node-002",
                "relationship": "stored_in",
                "summary": "User Model data is stored in Database Connection Pool",
                "created_at": "2024-01-12T09:00:00Z",
                "confidence": 1.0,
                "metadata": {
                    "discovered_by": "schema_analysis"
                }
            }
        ],
        "total_results": 3,
        "query": "authentication relationships"
    },

    # Add a new episode to the knowledge graph
    "add_episode": {
        "success": True,
        "episode_uuid": "episode-mock-001",
        "message": "Episode added successfully to knowledge graph",
        "nodes_created": 2,
        "facts_created": 1,
        "timestamp": "2024-01-31T16:00:00Z",
        "metadata": {
            "processing_time_ms": 45,
            "graph_size": {
                "total_nodes": 156,
                "total_facts": 423
            }
        }
    },

    # Retrieve recent episodes from the graph
    "get_episodes": {
        "episodes": [
            {
                "uuid": "episode-001",
                "content": "Implemented user authentication feature with JWT tokens and refresh token rotation",
                "created_at": "2024-01-20T14:30:00Z",
                "source": "build_session_001",
                "metadata": {
                    "spec_id": "001-user-authentication",
                    "agent": "coder",
                    "subtask": "subtask-3-2"
                }
            },
            {
                "uuid": "episode-002",
                "content": "Fixed database connection pool exhaustion issue by implementing connection timeout and retry logic",
                "created_at": "2024-01-22T09:15:00Z",
                "source": "build_session_005",
                "metadata": {
                    "spec_id": "005-db-connection-fix",
                    "agent": "qa_fixer",
                    "issue_type": "bug_fix"
                }
            },
            {
                "uuid": "episode-003",
                "content": "Added email validation and password strength requirements to User Model",
                "created_at": "2024-01-23T11:00:00Z",
                "source": "build_session_007",
                "metadata": {
                    "spec_id": "007-user-validation",
                    "agent": "coder",
                    "subtask": "subtask-2-1"
                }
            }
        ],
        "total_episodes": 3,
        "offset": 0,
        "limit": 10
    },

    # Get details of a specific entity or edge (relationship)
    "get_entity_edge": {
        "type": "entity",
        "entity": {
            "uuid": "node-001",
            "name": "Authentication System",
            "summary": "Core authentication system handling user login and session management",
            "node_type": "Component",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-20T14:22:00Z",
            "metadata": {
                "location": "apps/backend/auth/",
                "language": "Python",
                "framework": "FastAPI"
            },
            "edges": [
                {
                    "uuid": "fact-001",
                    "relationship": "uses",
                    "target_uuid": "node-002",
                    "target_name": "Database Connection Pool"
                },
                {
                    "uuid": "fact-002",
                    "relationship": "manages",
                    "target_uuid": "node-003",
                    "target_name": "User Model"
                }
            ],
            "edge_count": 2
        }
    }
}


# =============================================================================
# Error Responses
# =============================================================================

MOCK_ERROR_RESPONSES = {
    "not_found": {
        "success": False,
        "error": "Entity or edge not found",
        "error_code": "NOT_FOUND",
        "message": "The requested entity or relationship does not exist in the knowledge graph"
    },
    "invalid_query": {
        "success": False,
        "error": "Invalid query parameters",
        "error_code": "INVALID_QUERY",
        "message": "Query must include at least one search term"
    },
    "server_error": {
        "success": False,
        "error": "Internal server error",
        "error_code": "SERVER_ERROR",
        "message": "An unexpected error occurred while processing the request"
    }
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_mock_response(tool_name: str, params: dict = None) -> dict:
    """
    Get mock response for a specific Graphiti MCP tool.

    Args:
        tool_name: Name of the Graphiti MCP tool (without mcp__graphiti-memory__ prefix)
        params: Optional parameters to customize the response

    Returns:
        Mock response dictionary

    Examples:
        >>> get_mock_response("search_nodes")
        {'nodes': [...], 'total_results': 3, ...}

        >>> get_mock_response("add_episode", {"content": "New episode"})
        {'success': True, 'episode_uuid': 'episode-mock-001', ...}
    """
    # Remove prefix if present
    tool_name = tool_name.replace("mcp__graphiti-memory__", "")

    if tool_name not in MOCK_RESPONSES:
        return MOCK_ERROR_RESPONSES["not_found"]

    response = MOCK_RESPONSES[tool_name].copy()

    # Customize response based on params if needed
    if params and tool_name == "search_nodes" and "query" in params:
        response["query"] = params["query"]
    elif params and tool_name == "search_facts" and "query" in params:
        response["query"] = params["query"]

    return response


def list_available_tools() -> list[str]:
    """
    List all available Graphiti MCP tools with mock data.

    Returns:
        List of tool names
    """
    return list(MOCK_RESPONSES.keys())
