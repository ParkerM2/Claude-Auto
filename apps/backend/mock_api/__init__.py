"""
Mock MCP API Module
===================

Lightweight mock Graphiti MCP server that simulates the real MCP server
with canned responses for development and testing.

This module provides:
- Mock data definitions for all Graphiti MCP tools
- FastAPI-based mock server implementation
- Isolated testing environment (runs on port 8001 by default)
- Environment-aware initialization for dev/test modes

Usage:
    # Start mock server
    python mock_api/start_mock_server.py

    # Or programmatically
    from mock_api.server import app
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)

The mock server is automatically used when:
- API_MODE=development environment variable is set
- Running under pytest (PYTEST_CURRENT_TEST detected)
"""

__version__ = "0.1.0"
__all__ = [
    "MOCK_RESPONSES",
    "app",
]


def __getattr__(name):
    """Lazy imports to avoid loading server dependencies unless needed."""
    if name == "MOCK_RESPONSES":
        from .data import MOCK_RESPONSES
        return MOCK_RESPONSES
    elif name == "app":
        from .server import app
        return app
    raise AttributeError(f"module 'mock_api' has no attribute '{name}'")
