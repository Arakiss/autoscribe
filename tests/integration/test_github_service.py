from datetime import datetime
from unittest.mock import patch

import pytest

from autoscribe.models.changelog import Category, Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.github import GitHubService


@pytest.fixture
def sample_config():
    """Create a test configuration."""
    return AutoScribeConfig(
        github_token="test-token",
        github_release=True,
    )


def test_github_service_initialization(sample_config, mock_github):
    """Test GitHubService initialization."""
    with patch("github.Github", mock_github):
        service = GitHubService(sample_config)
        assert service.config == sample_config
        assert service._github is not None
        assert service.is_available()


def test_make_request_without_token():
    """Test making request without token."""
    config = AutoScribeConfig(github_token=None)
    service = GitHubService(config)
    assert service._github is None


def test_create_release(sample_config, mock_github):
    """Test creating a GitHub release."""
    with patch("github.Github", mock_github):
        service = GitHubService(sample_config)

        success, url = service.create_release(
            owner="test",
            repo="repo",
            tag_name="v1.0.0",
            name="Release v1.0.0",
            body="Release notes",
            draft=False,
            prerelease=False,
        )

        assert success is True
        assert url == "https://github.com/test/repo/releases/v1.0.0"


def test_update_release(sample_config, mock_github):
    """Test updating a GitHub release."""
    with patch("github.Github", mock_github):
        service = GitHubService(sample_config)

        success, url = service.update_release(
            owner="test",
            repo="repo",
            release_id=1,
            tag_name="v1.0.0",
            name="Release v1.0.0",
            body="Updated release notes",
            draft=False,
            prerelease=False,
        )

        assert success is True
        assert url == "https://github.com/test/repo/releases/v1.0.0"


def test_get_release_by_tag(sample_config, mock_github):
    """Test getting a release by tag."""
    with patch("github.Github", mock_github):
        service = GitHubService(sample_config)

        success, release = service.get_release_by_tag(
            owner="test",
            repo="repo",
            tag="v1.0.0",
        )

        assert success is True
        assert release["id"] == 1
        assert release["tag_name"] == "v1.0.0"
        assert release["name"] == "Release v1.0.0"
        assert release["body"] == "Test release notes"
        assert release["created_at"] == "2024-01-01T00:00:00Z"
        assert release["published_at"] == "2024-01-01T00:00:00Z"


def test_delete_release(sample_config, mock_github):
    """Test deleting a release."""
    with patch("github.Github", mock_github):
        service = GitHubService(sample_config)

        success, error = service.delete_release(
            owner="test",
            repo="repo",
            release_id=1,
        )

        assert success is True
        assert error is None


def test_error_handling(sample_config):
    """Test error handling in requests."""
    class MockGithubError:
        def __init__(self, token=None):
            pass

        def get_user(self):
            raise GithubException(401, {"message": "Bad credentials"})

    with patch("github.Github", MockGithubError):
        service = GitHubService(sample_config)
        assert service._github is None


def test_is_available(sample_config, mock_github):
    """Test service availability check."""
    with patch("github.Github", mock_github):
        # Test with token and enabled
        service = GitHubService(sample_config)
        assert service.is_available() is True

        # Test without token
        config = AutoScribeConfig(github_token=None)
        service = GitHubService(config)
        assert service.is_available() is False

        # Test with invalid token
        config = AutoScribeConfig(github_token="invalid-token")
        service = GitHubService(config)
        assert service.is_available() is False

        # Test with disabled GitHub
        config = AutoScribeConfig(github_release=False)
        service = GitHubService(config)
        assert service.is_available() is False
