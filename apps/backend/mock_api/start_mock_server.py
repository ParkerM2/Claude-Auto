#!/usr/bin/env python3
"""
Mock MCP Server Startup Script
================================

Starts the mock Graphiti MCP server for development and testing.

This script launches a FastAPI server on localhost:8001 (default) that
simulates the real Graphiti MCP server with canned responses. Use this
during development and testing to avoid conflicts with production data.

Usage:
    python mock_api/start_mock_server.py

    # Or from apps/backend/
    python -m mock_api.start_mock_server

Environment Variables:
    MOCK_MCP_PORT - Port to run the server on (default: 8001)
    API_MODE - Set to 'development' for verbose logging

Example:
    export MOCK_MCP_PORT=8002
    python mock_api/start_mock_server.py
"""

import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mock_server_startup")


def main():
    """Start the mock MCP server."""

    # Check dependencies
    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn is required to run the mock server")
        logger.error("Install with: pip install uvicorn fastapi")
        sys.exit(1)

    try:
        from mock_api.server import app
    except ImportError as e:
        logger.error(f"Failed to import mock server: {e}")
        logger.error("Make sure you're running from the apps/backend directory")
        sys.exit(1)

    # Get configuration from environment
    port = int(os.environ.get("MOCK_MCP_PORT", "8001"))
    host = "127.0.0.1"  # Only bind to localhost for security

    # Determine log level based on API_MODE
    api_mode = os.environ.get("API_MODE", "production")
    log_level = "debug" if api_mode == "development" else "info"

    # Print startup information
    logger.info("=" * 60)
    logger.info("Starting Mock Graphiti MCP Server")
    logger.info("=" * 60)
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Mode: {api_mode}")
    logger.info(f"URL: http://{host}:{port}")
    logger.info("=" * 60)
    logger.info("Available endpoints:")
    logger.info(f"  - Health check:    http://{host}:{port}/health")
    logger.info(f"  - API docs:        http://{host}:{port}/docs")
    logger.info(f"  - Tool list:       http://{host}:{port}/mcp/tools")
    logger.info(f"  - Tool invocation: http://{host}:{port}/mcp/tools/{{tool_name}}")
    logger.info("=" * 60)
    logger.info("Press CTRL+C to stop the server")
    logger.info("")

    # Start server
    try:
        uvicorn.run(app, host=host, port=port, log_level=log_level, access_log=True)
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
        sys.exit(0)
    except OSError as e:
        if "address already in use" in str(e).lower():
            logger.error(f"Port {port} is already in use")
            logger.error("Either stop the other process or use a different port:")
            logger.error(f"  MOCK_MCP_PORT=8002 python {sys.argv[0]}")
        else:
            logger.error(f"OS error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
