"""Unit tests for mock MCP server"""

import pytest


def test_mock_data_structure():
    """Test that mock data includes all required Graphiti MCP tools."""
    from mock_api.data import MOCK_RESPONSES

    required_tools = [
        'search_nodes',
        'search_facts',
        'add_episode',
        'get_episodes',
        'get_entity_edge'
    ]

    for tool in required_tools:
        assert tool in MOCK_RESPONSES, f"Missing mock data for tool: {tool}"


def test_mock_search_nodes_response():
    """Test that search_nodes mock data has correct structure."""
    from mock_api.data import MOCK_RESPONSES

    response = MOCK_RESPONSES['search_nodes']

    assert 'nodes' in response
    assert isinstance(response['nodes'], list)
    assert len(response['nodes']) > 0

    # Check first node structure
    node = response['nodes'][0]
    assert 'uuid' in node
    assert 'name' in node
    assert 'summary' in node
    assert 'node_type' in node


def test_mock_search_facts_response():
    """Test that search_facts mock data has correct structure."""
    from mock_api.data import MOCK_RESPONSES

    response = MOCK_RESPONSES['search_facts']

    assert 'facts' in response
    assert isinstance(response['facts'], list)
    assert len(response['facts']) > 0

    # Check first fact structure
    fact = response['facts'][0]
    assert 'uuid' in fact
    assert 'source_node_uuid' in fact
    assert 'target_node_uuid' in fact
    assert 'relationship' in fact


def test_mock_add_episode_response():
    """Test that add_episode mock data has correct structure."""
    from mock_api.data import MOCK_RESPONSES

    response = MOCK_RESPONSES['add_episode']

    assert 'episode_uuid' in response
    assert 'status' in response
    assert response['status'] == 'created'


def test_mock_get_episodes_response():
    """Test that get_episodes mock data has correct structure."""
    from mock_api.data import MOCK_RESPONSES

    response = MOCK_RESPONSES['get_episodes']

    assert 'episodes' in response
    assert isinstance(response['episodes'], list)


def test_mock_get_entity_edge_response():
    """Test that get_entity_edge mock data has correct structure."""
    from mock_api.data import MOCK_RESPONSES

    response = MOCK_RESPONSES['get_entity_edge']

    assert 'entity' in response or 'edge' in response


def test_mock_api_server_import():
    """Test that mock API server can be imported without FastAPI installed."""
    try:
        from mock_api.server import app
        # If FastAPI is installed, app should be a FastAPI instance
        # If not, app should be a stub
        assert app is not None
    except ImportError:
        pytest.fail("Mock API server module should be importable even without FastAPI")


def test_get_mock_response_helper():
    """Test the get_mock_response helper function."""
    from mock_api.data import get_mock_response

    # Test basic retrieval
    response = get_mock_response('search_nodes')
    assert response is not None
    assert 'nodes' in response

    # Test with params (if function supports it)
    response = get_mock_response('search_nodes', params={'query': 'test'})
    assert response is not None
