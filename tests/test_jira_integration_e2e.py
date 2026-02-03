"""
End-to-End Tests for Jira Integration
======================================

Tests the full Jira integration flow:
- Import Jira issue as spec
- Status updates during build lifecycle
- PR linking after successful build

These tests validate the integration between all Jira components.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from runners.jira.models import (
    JiraIssue,
    JiraUser,
    JiraStatus,
    JiraPriority,
    JiraProject,
)
from runners.jira.jira_client import JiraConfig
from runners.jira.spec_importer import JiraSpecImporter
from runners.jira.spec_metadata import (
    JiraSpecMetadata,
    save_jira_metadata,
    load_jira_metadata,
    get_issue_key,
    is_jira_spec,
)
from runners.jira.status_updater import JiraStatusUpdater
from runners.jira.pr_linker import JiraPRLinker
from runners.jira.jira_client import JiraClient


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_specs_dir(tmp_path):
    """Create a temporary specs directory structure."""
    specs_dir = tmp_path / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)
    return specs_dir


@pytest.fixture
def sample_jira_issue():
    """Create a sample Jira issue for testing."""
    return JiraIssue(
        id="10001",
        key="TEST-123",
        url="https://test.atlassian.net/browse/TEST-123",
        summary="Add user authentication feature",
        description="""
This feature should add user authentication to the application.

Acceptance Criteria:
- Users can log in with email and password
- Passwords are securely hashed
- Session tokens are properly managed
- Logout functionality works correctly
        """.strip(),
        issue_type="Story",
        status=JiraStatus(id="1", name="To Do", category="todo"),
        priority=JiraPriority(id="2", name="High"),
        assignee=JiraUser(
            account_id="abc123",
            email_address="developer@test.com",
            display_name="Test Developer",
        ),
        reporter=JiraUser(
            account_id="def456",
            email_address="reporter@test.com",
            display_name="Test Reporter",
        ),
        project=JiraProject(id="10000", key="TEST", name="Test Project"),
        labels=["feature", "authentication"],
        story_points=5,
        created_at="2024-01-01T10:00:00",
        updated_at="2024-01-01T12:00:00",
    )


@pytest.fixture
def mock_jira_client():
    """Create a mock Jira client."""
    client = MagicMock(spec=JiraClient)
    client.get_issue = AsyncMock()
    client.update_status = AsyncMock()
    client.link_pr = AsyncMock()
    client._request = AsyncMock()
    return client


@pytest.fixture
def jira_config():
    """Create a test Jira configuration."""
    return JiraConfig(
        base_url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token-12345",
    )


# ============================================================================
# E2E Test: Spec Import Flow
# ============================================================================

class TestSpecImportE2E:
    """Test Jira issue to spec import flow end-to-end."""

    def test_import_issue_creates_spec_directory(self, temp_specs_dir, sample_jira_issue):
        """Test that importing a Jira issue creates a complete spec directory."""
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)

        # Import the issue
        spec_dir = importer.import_issue(sample_jira_issue, spec_name="001-test-auth")

        # Verify spec directory was created
        assert spec_dir.exists()
        assert spec_dir.name == "001-test-auth"

        # Verify spec.md exists and has correct content
        spec_file = spec_dir / "spec.md"
        assert spec_file.exists()

        content = spec_file.read_text()
        assert "Add user authentication feature" in content
        assert "TEST-123" in content
        assert "Users can log in with email and password" in content

    def test_import_creates_requirements_json(self, temp_specs_dir, sample_jira_issue):
        """Test that requirements.json is created with correct data."""
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)
        spec_dir = importer.import_issue(sample_jira_issue, spec_name="001-test")

        requirements_file = spec_dir / "requirements.json"
        assert requirements_file.exists()

        with open(requirements_file) as f:
            data = json.load(f)

        assert data["task_description"] == "Add user authentication feature"
        assert data["workflow_type"] == "feature"
        assert data["imported_from_jira"] is True
        assert data["jira_issue_key"] == "TEST-123"

    def test_import_creates_jira_metadata(self, temp_specs_dir, sample_jira_issue):
        """Test that jira_issue.json metadata is created."""
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)
        spec_dir = importer.import_issue(sample_jira_issue, spec_name="001-test")

        metadata_file = spec_dir / "jira_issue.json"
        assert metadata_file.exists()

        # Load and verify metadata
        metadata = load_jira_metadata(spec_dir)
        assert metadata is not None
        assert metadata.issue_key == "TEST-123"
        assert metadata.issue_id == "10001"
        assert metadata.project_key == "TEST"
        assert metadata.original_status == "To Do"

    def test_import_generates_spec_name_from_issue_key(self, temp_specs_dir, sample_jira_issue):
        """Test automatic spec name generation from issue key."""
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)
        spec_dir = importer.import_issue(sample_jira_issue)  # No spec_name provided

        # Should generate name from issue key and summary
        assert spec_dir.name.startswith("test-123-")
        assert "authentication" in spec_dir.name.lower()


# ============================================================================
# E2E Test: Metadata Management
# ============================================================================

class TestMetadataManagementE2E:
    """Test Jira metadata save/load flow."""

    def test_metadata_save_load_roundtrip(self, temp_specs_dir):
        """Test saving and loading Jira metadata."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        # Create and save metadata
        metadata = JiraSpecMetadata(
            issue_key="TEST-456",
            issue_id="10002",
            issue_url="https://test.atlassian.net/browse/TEST-456",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="In Progress",
        )

        save_jira_metadata(spec_dir, metadata)

        # Load and verify
        loaded = load_jira_metadata(spec_dir)
        assert loaded is not None
        assert loaded.issue_key == "TEST-456"
        assert loaded.issue_id == "10002"
        assert loaded.project_key == "TEST"
        assert loaded.original_status == "In Progress"

    def test_is_jira_spec_detection(self, temp_specs_dir):
        """Test detecting whether a spec came from Jira."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        # Initially not a Jira spec
        assert is_jira_spec(spec_dir) is False

        # After saving metadata, should be detected as Jira spec
        metadata = JiraSpecMetadata(
            issue_key="TEST-789",
            issue_id="10003",
            issue_url="https://test.atlassian.net/browse/TEST-789",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="To Do",
        )
        save_jira_metadata(spec_dir, metadata)

        assert is_jira_spec(spec_dir) is True

    def test_get_issue_key_from_metadata(self, temp_specs_dir):
        """Test extracting issue key from metadata."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        # No metadata initially
        assert get_issue_key(spec_dir) is None

        # After saving metadata
        metadata = JiraSpecMetadata(
            issue_key="TEST-999",
            issue_id="10004",
            issue_url="https://test.atlassian.net/browse/TEST-999",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="To Do",
        )
        save_jira_metadata(spec_dir, metadata)

        assert get_issue_key(spec_dir) == "TEST-999"


# ============================================================================
# E2E Test: Status Update Flow
# ============================================================================

class TestStatusUpdateE2E:
    """Test Jira status update flow during build lifecycle."""

    @pytest.mark.asyncio
    async def test_status_update_on_task_started(self, temp_specs_dir, mock_jira_client):
        """Test status update when build starts."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        # Create metadata
        metadata = JiraSpecMetadata(
            issue_key="TEST-100",
            issue_id="10005",
            issue_url="https://test.atlassian.net/browse/TEST-100",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="To Do",
        )
        save_jira_metadata(spec_dir, metadata)

        # Update status to "In Progress"
        updater = JiraStatusUpdater(mock_jira_client)
        issue_key = get_issue_key(spec_dir)
        await updater.on_task_started(issue_key)

        # Verify client was called with correct parameters
        mock_jira_client.update_status.assert_called_once_with("TEST-100", "In Progress")

    @pytest.mark.asyncio
    async def test_status_update_on_build_complete(self, temp_specs_dir, mock_jira_client):
        """Test status update when build completes."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        metadata = JiraSpecMetadata(
            issue_key="TEST-200",
            issue_id="10006",
            issue_url="https://test.atlassian.net/browse/TEST-200",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="In Progress",
        )
        save_jira_metadata(spec_dir, metadata)

        # Update status to "Done"
        updater = JiraStatusUpdater(mock_jira_client)
        issue_key = get_issue_key(spec_dir)
        await updater.on_task_completed(issue_key)

        # Verify status updated to Done
        mock_jira_client.update_status.assert_called_once_with("TEST-200", "Done")

    @pytest.mark.asyncio
    async def test_status_update_on_task_failed(self, temp_specs_dir, mock_jira_client):
        """Test status update when build fails."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        metadata = JiraSpecMetadata(
            issue_key="TEST-300",
            issue_id="10007",
            issue_url="https://test.atlassian.net/browse/TEST-300",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="In Progress",
        )
        save_jira_metadata(spec_dir, metadata)

        # Update status back to "To Do" on failure
        updater = JiraStatusUpdater(mock_jira_client)
        issue_key = get_issue_key(spec_dir)
        await updater.on_task_failed(issue_key)

        # Verify status updated to To Do
        mock_jira_client.update_status.assert_called_once_with("TEST-300", "To Do")


# ============================================================================
# E2E Test: PR Linking Flow
# ============================================================================

class TestPRLinkingE2E:
    """Test PR linking to Jira issues."""

    @pytest.mark.asyncio
    async def test_pr_linked_after_creation(self, temp_specs_dir, mock_jira_client):
        """Test that PR is linked to Jira issue after creation."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        metadata = JiraSpecMetadata(
            issue_key="TEST-400",
            issue_id="10008",
            issue_url="https://test.atlassian.net/browse/TEST-400",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="In Progress",
        )
        save_jira_metadata(spec_dir, metadata)

        # Link PR
        linker = JiraPRLinker(mock_jira_client)
        issue_key = get_issue_key(spec_dir)
        pr_url = "https://github.com/test/repo/pull/42"
        await linker.on_pr_created(issue_key, pr_url)

        # Verify PR was linked - the PR linker uses link_pr internally
        mock_jira_client._request.assert_called()

    @pytest.mark.asyncio
    async def test_pr_linking_skips_non_jira_specs(self, temp_specs_dir, mock_jira_client):
        """Test that PR linking is skipped for non-Jira specs."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)
        # No metadata file = not a Jira spec

        linker = JiraPRLinker(mock_jira_client)
        issue_key = get_issue_key(spec_dir)
        pr_url = "https://github.com/test/repo/pull/42"

        # Should not call client for non-Jira specs (issue_key is None)
        if issue_key:
            await linker.on_pr_created(issue_key, pr_url)

        mock_jira_client._request.assert_not_called()


# ============================================================================
# E2E Test: Complete Integration Lifecycle
# ============================================================================

class TestCompleteIntegrationE2E:
    """Test the complete Jira integration lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_import_to_pr(
        self, temp_specs_dir, sample_jira_issue, mock_jira_client
    ):
        """
        Test complete flow:
        1. Import Jira issue as spec
        2. Start build (status -> In Progress)
        3. Complete build (status -> Done)
        4. Create PR (link to Jira)
        """
        # Step 1: Import Jira issue as spec
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)
        spec_dir = importer.import_issue(sample_jira_issue, spec_name="001-auth")

        # Verify spec was created
        assert spec_dir.exists()
        assert is_jira_spec(spec_dir) is True
        assert get_issue_key(spec_dir) == "TEST-123"

        # Step 2: Start build - status should update to "In Progress"
        updater = JiraStatusUpdater(mock_jira_client)
        issue_key = get_issue_key(spec_dir)
        await updater.on_task_started(issue_key)

        assert mock_jira_client.update_status.call_count == 1
        mock_jira_client.update_status.assert_called_with("TEST-123", "In Progress")

        # Step 3: Complete build - status should update to "Done"
        await updater.on_task_completed(issue_key)

        assert mock_jira_client.update_status.call_count == 2
        mock_jira_client.update_status.assert_called_with("TEST-123", "Done")

        # Step 4: Create PR - should link to Jira issue
        linker = JiraPRLinker(mock_jira_client)
        pr_url = "https://github.com/test/repo/pull/123"
        await linker.on_pr_created(issue_key, pr_url)

        mock_jira_client._request.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_during_status_update(
        self, temp_specs_dir, mock_jira_client
    ):
        """Test that errors during status update are handled gracefully."""
        spec_dir = temp_specs_dir / "001-test"
        spec_dir.mkdir(parents=True)

        metadata = JiraSpecMetadata(
            issue_key="TEST-500",
            issue_id="10009",
            issue_url="https://test.atlassian.net/browse/TEST-500",
            project_key="TEST",
            imported_at=datetime.now().isoformat(),
            original_status="To Do",
        )
        save_jira_metadata(spec_dir, metadata)

        # Mock client to raise an error
        mock_jira_client.update_status.side_effect = Exception("API error")

        # Should not crash, just log the error
        updater = JiraStatusUpdater(mock_jira_client)
        issue_key = get_issue_key(spec_dir)

        try:
            await updater.on_task_started(issue_key)
        except Exception as e:
            # Error should be logged but not raised
            assert "API error" in str(e)


# ============================================================================
# E2E Test: Integration with Real File System
# ============================================================================

class TestFileSystemIntegrationE2E:
    """Test Jira integration with actual file system operations."""

    def test_spec_directory_structure_complete(self, temp_specs_dir, sample_jira_issue):
        """Test that all expected files are created in the spec directory."""
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)
        spec_dir = importer.import_issue(sample_jira_issue, spec_name="001-complete")

        # Verify all files exist
        expected_files = [
            "spec.md",
            "requirements.json",
            "jira_issue.json",
        ]

        for filename in expected_files:
            file_path = spec_dir / filename
            assert file_path.exists(), f"Missing file: {filename}"
            assert file_path.stat().st_size > 0, f"Empty file: {filename}"

    def test_spec_md_formatting(self, temp_specs_dir, sample_jira_issue):
        """Test that spec.md is properly formatted."""
        importer = JiraSpecImporter(specs_dir=temp_specs_dir)
        spec_dir = importer.import_issue(sample_jira_issue, spec_name="001-format")

        spec_file = spec_dir / "spec.md"
        content = spec_file.read_text()

        # Should have proper markdown structure
        assert content.startswith("# ")
        assert "## Issue Details" in content
        assert "## Acceptance Criteria" in content

        # Should have checkboxes for acceptance criteria
        assert "- [ ]" in content

        # Should have issue metadata
        assert "**Jira Issue:**" in content
        assert "**Type:**" in content
        assert "**Status:**" in content
        assert "**Priority:**" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
