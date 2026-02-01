"""Unit tests for environment detection in core/client.py"""

import os
import pytest


def test_environment_detection_development_mode():
    """Test that API_MODE=development returns mock server URL."""
    # Import function after setting environment
    os.environ['API_MODE'] = 'development'
    # Remove any overrides
    os.environ.pop('GRAPHITI_MCP_URL', None)
    os.environ.pop('PYTEST_CURRENT_TEST', None)

    from core.client import get_graphiti_mcp_url

    url = get_graphiti_mcp_url()
    assert 'localhost:8001' in url or '127.0.0.1:8001' in url
    assert '/mcp/' in url

    # Cleanup
    os.environ.pop('API_MODE', None)


def test_environment_detection_production_mode():
    """Test that API_MODE=production returns real server URL."""
    os.environ['API_MODE'] = 'production'
    os.environ.pop('GRAPHITI_MCP_URL', None)
    os.environ.pop('PYTEST_CURRENT_TEST', None)

    from core.client import get_graphiti_mcp_url

    url = get_graphiti_mcp_url()
    assert 'localhost:8000' in url or '127.0.0.1:8000' in url
    assert '/mcp/' in url

    # Cleanup
    os.environ.pop('API_MODE', None)


def test_environment_detection_pytest_auto_detect():
    """Test that pytest auto-detection works (PYTEST_CURRENT_TEST env var)."""
    # Simulate pytest environment
    os.environ['PYTEST_CURRENT_TEST'] = 'test_something.py::test_function'
    os.environ.pop('API_MODE', None)
    os.environ.pop('GRAPHITI_MCP_URL', None)

    from core.client import get_graphiti_mcp_url

    url = get_graphiti_mcp_url()
    assert 'localhost:8001' in url or '127.0.0.1:8001' in url

    # Cleanup
    os.environ.pop('PYTEST_CURRENT_TEST', None)


def test_environment_detection_override():
    """Test that GRAPHITI_MCP_URL overrides API_MODE."""
    os.environ['API_MODE'] = 'development'
    os.environ['GRAPHITI_MCP_URL'] = 'http://custom-server:9999/mcp/'

    from core.client import get_graphiti_mcp_url

    url = get_graphiti_mcp_url()
    assert url == 'http://custom-server:9999/mcp/'

    # Cleanup
    os.environ.pop('API_MODE', None)
    os.environ.pop('GRAPHITI_MCP_URL', None)


def test_environment_detection_custom_mock_port():
    """Test that MOCK_MCP_PORT can customize the mock server port."""
    os.environ['API_MODE'] = 'development'
    os.environ['MOCK_MCP_PORT'] = '9001'
    os.environ.pop('GRAPHITI_MCP_URL', None)

    from core.client import get_graphiti_mcp_url

    url = get_graphiti_mcp_url()
    assert '9001' in url
    assert '/mcp/' in url

    # Cleanup
    os.environ.pop('API_MODE', None)
    os.environ.pop('MOCK_MCP_PORT', None)
