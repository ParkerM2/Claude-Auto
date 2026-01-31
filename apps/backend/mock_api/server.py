"""
Mock MCP Server Implementation
================================

FastAPI-based mock server that simulates the Graphiti MCP server
for development and testing purposes. Runs on port 8001 by default.

The server implements the MCP (Model Context Protocol) HTTP interface,
providing mock responses for all Graphiti memory tools.

Usage:
    # Start server programmatically
    import uvicorn
    from mock_api.server import app
    uvicorn.run(app, host="localhost", port=8001)

    # Or use the startup script
    python mock_api/start_mock_server.py

Endpoints:
    GET /health - Health check endpoint
    POST /mcp/tools/{tool_name} - MCP tool invocation
    GET /mcp/tools - List available tools
"""

import os
import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

# Deferred imports to allow module import without FastAPI installed
# FastAPI is only required when actually running the server
if TYPE_CHECKING:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock_mcp_server")


# =============================================================================
# Factory Function - Creates FastAPI app when needed
# =============================================================================

def _create_fastapi_app():
    """
    Create and configure the FastAPI application.

    This function is called lazily to allow the module to be imported
    without FastAPI installed. FastAPI is only required when actually
    running the server.

    Returns:
        Configured FastAPI application or stub if FastAPI not available

    Note:
        Returns a stub object if FastAPI is not installed to allow module import.
        The stub will raise an error when actually used.
    """
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field
    except ImportError:
        # Return a stub that will fail with a helpful message if actually used
        class FastAPIStub:
            """Stub object when FastAPI is not installed."""
            def __init__(self):
                self._error_msg = (
                    "FastAPI is required for the mock MCP server. "
                    "Install with: pip install fastapi uvicorn"
                )

            def __call__(self, *args, **kwargs):
                raise ImportError(self._error_msg)

            def __getattr__(self, name):
                raise ImportError(self._error_msg)

            def __repr__(self):
                return "<FastAPI stub - not installed>"

        logger.warning("FastAPI not installed - mock MCP server will not be functional")
        return FastAPIStub()

    from .data import get_mock_response, list_available_tools

    # =============================================================================
    # Pydantic Models
    # =============================================================================

    class ToolInvocationRequest(BaseModel):
        """Request model for MCP tool invocation."""

        name: Optional[str] = Field(None, description="Tool name (optional if in URL)")
        arguments: Optional[Dict[str, Any]] = Field(
            default_factory=dict,
            description="Tool arguments"
        )

        class Config:
            json_schema_extra = {
                "example": {
                    "name": "search_nodes",
                    "arguments": {"query": "authentication"}
                }
            }

    class ToolResponse(BaseModel):
        """Response model for MCP tool invocation."""

        success: bool = Field(True, description="Whether the tool call succeeded")
        result: Optional[Dict[str, Any]] = Field(None, description="Tool result")
        error: Optional[str] = Field(None, description="Error message if failed")
        error_code: Optional[str] = Field(None, description="Error code if failed")

    # =============================================================================
    # FastAPI Application
    # =============================================================================

    app = FastAPI(
        title="Mock Graphiti MCP Server",
        description="Lightweight mock server simulating Graphiti MCP tools for development and testing",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # =============================================================================
    # Middleware and Event Handlers
    # =============================================================================

    @app.on_event("startup")
    async def startup_event():
        """Log server startup."""
        port = os.environ.get("MOCK_MCP_PORT", "8001")
        logger.info(f"Mock MCP Server starting on port {port}")
        logger.info(f"Available tools: {', '.join(list_available_tools())}")
        logger.info("Environment: DEVELOPMENT/TESTING")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Log server shutdown."""
        logger.info("Mock MCP Server shutting down")

    # =============================================================================
    # Health Check Endpoint
    # =============================================================================

    @app.get("/health")
    async def health_check():
        """
        Health check endpoint.

        Returns:
            Status information about the mock server
        """
        return {
            "status": "healthy",
            "service": "mock-graphiti-mcp",
            "version": "0.1.0",
            "mode": "development",
            "available_tools": list_available_tools()
        }

    # =============================================================================
    # MCP Tool Endpoints
    # =============================================================================

    @app.get("/mcp/tools")
    async def list_tools():
        """
        List all available MCP tools.

        Returns:
            List of tool names and their descriptions
        """
        tools = list_available_tools()
        return {
            "tools": [
                {
                    "name": f"mcp__graphiti-memory__{tool}",
                    "description": f"Mock implementation of {tool}",
                    "available": True
                }
                for tool in tools
            ],
            "total": len(tools)
        }

    @app.post("/mcp/tools/{tool_name}")
    async def invoke_tool(tool_name: str, request: ToolInvocationRequest):
        """
        Invoke an MCP tool with the given arguments.

        Args:
            tool_name: Name of the tool to invoke (with or without mcp__graphiti-memory__ prefix)
            request: Tool invocation request with arguments

        Returns:
            Mock response for the tool
        """
        # Normalize tool name (remove prefix if present)
        normalized_name = tool_name.replace("mcp__graphiti-memory__", "")

        logger.info(f"Tool invocation: {normalized_name} with args: {request.arguments}")

        # Get mock response
        result = get_mock_response(normalized_name, request.arguments)

        # Check if it's an error response
        if "error" in result and "error_code" in result:
            return ToolResponse(
                success=False,
                result=None,
                error=result.get("message", result["error"]),
                error_code=result["error_code"]
            )

        return ToolResponse(
            success=True,
            result=result,
            error=None,
            error_code=None
        )

    @app.post("/mcp/invoke")
    async def invoke_tool_legacy(request: ToolInvocationRequest):
        """
        Legacy MCP tool invocation endpoint (tool name in request body).

        This endpoint supports the alternative MCP protocol format where
        the tool name is specified in the request body rather than the URL.

        Args:
            request: Tool invocation request with name and arguments

        Returns:
            Mock response for the tool
        """
        if not request.name:
            raise HTTPException(
                status_code=400,
                detail="Tool name is required in request body"
            )

        # Normalize tool name
        normalized_name = request.name.replace("mcp__graphiti-memory__", "")

        logger.info(f"Tool invocation (legacy): {normalized_name} with args: {request.arguments}")

        # Get mock response
        result = get_mock_response(normalized_name, request.arguments)

        # Check if it's an error response
        if "error" in result and "error_code" in result:
            return ToolResponse(
                success=False,
                result=None,
                error=result.get("message", result["error"]),
                error_code=result["error_code"]
            )

        return ToolResponse(
            success=True,
            result=result,
            error=None,
            error_code=None
        )

    # =============================================================================
    # Error Handlers
    # =============================================================================

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent error format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "error_code": f"HTTP_{exc.status_code}"
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "message": str(exc) if os.environ.get("DEBUG") else "An unexpected error occurred"
            }
        )

    # =============================================================================
    # Root Endpoint
    # =============================================================================

    @app.get("/")
    async def root():
        """
        Root endpoint with server information.

        Returns:
            Basic information about the mock MCP server
        """
        return {
            "service": "Mock Graphiti MCP Server",
            "version": "0.1.0",
            "status": "running",
            "mode": "development",
            "endpoints": {
                "health": "/health",
                "tools_list": "/mcp/tools",
                "tool_invoke": "/mcp/tools/{tool_name}",
                "legacy_invoke": "/mcp/invoke",
                "docs": "/docs"
            },
            "message": "Mock MCP server for development and testing. See /docs for API documentation."
        }

    return app


# =============================================================================
# Module-level app instance (lazy initialization)
# =============================================================================

# Create a module-level variable that will be initialized on first access
_app = None


def _get_app():
    """Get or create the FastAPI app instance."""
    global _app
    if _app is None:
        _app = _create_fastapi_app()
    return _app


# Make 'app' available as a module attribute via lazy loading
def __getattr__(name):
    """Lazy load the FastAPI app when accessed."""
    if name == "app":
        return _get_app()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
