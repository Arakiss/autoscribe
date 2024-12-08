from unittest.mock import patch

import pytest

from autoscribe.services.github import GitHubService


@pytest.fixture
def github_service(sample_config, mock_github):
    """Create a GitHub service instance with mocked client."""
    with patch("github.Github", mock_github):
        service = GitHubService(sample_config)
        return service


def test_is_available(github_service):
    """Test GitHub service availability check."""
    assert github_service.is_available()


def test_create_release(github_service):
    """Test creating GitHub release."""
    success, url = github_service.create_release(
        owner="test",
        repo="test",
        tag_name="v1.0.0",
        name="v1.0.0",
        body="Test release",
        draft=False,
        prerelease=False,
    )

    assert success is True
    assert url == "https://github.com/test/repo/releases/v1.0.0"


def test_update_release(github_service):
    """Test updating a release."""
    success, url = github_service.update_release(
        owner="test",
        repo="test",
        release_id=1,
        tag_name="v1.0.0",
        name="v1.0.0",
        body="Updated release",
    )

    assert success is True
    assert url == "https://github.com/test/repo/releases/v1.0.0"


def test_get_release_by_tag(github_service):
    """Test getting a release by tag."""
    success, release = github_service.get_release_by_tag(
        owner="test",
        repo="test",
        tag="v1.0.0",
    )

    assert success is True
    assert release["id"] == 1
    assert release["html_url"] == "https://github.com/test/repo/releases/v1.0.0"
    assert release["tag_name"] == "v1.0.0"
    assert release["name"] == "Release v1.0.0"
    assert release["body"] == "Test release notes"
    assert not release["draft"]
    assert not release["prerelease"]
    assert release["created_at"] == "2024-01-01T00:00:00Z"
    assert release["published_at"] == "2024-01-01T00:00:00Z"


def test_delete_release(github_service):
    """Test deleting a release."""
    success, error = github_service.delete_release(
        owner="test",
        repo="test",
        release_id=1,
    )

    assert success is True
    assert error is None


def test_error_handling(github_service):
    """Test error handling."""
    # Test with invalid token
    github_service.config.github_token = "invalid-token"
    assert not github_service.is_available()

    # Test with disabled GitHub release
    github_service.config.github_release = False
    assert not github_service.is_available()

    # Test with no token
    github_service.config.github_token = None
    assert not github_service.is_available()
