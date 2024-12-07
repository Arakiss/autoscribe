from github import Github, GithubException
import pytest
from unittest.mock import patch

from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.github import GitHubService
from ..unit.test_github_service import MockGithub


@pytest.fixture
def sample_config():
    """Create a test configuration."""
    return AutoScribeConfig(
        github_token="test-token",
        github_release=True,
    )


def test_github_service_initialization(sample_config):
    """Test GitHubService initialization."""
    with patch("github.Github", MockGithub):
        service = GitHubService(sample_config)
        assert service.config == sample_config
        assert service._github is not None


def test_make_request_without_token():
    """Test making request without token."""
    config = AutoScribeConfig(github_token=None)
    service = GitHubService(config)
    assert service._github is None


def test_create_release(sample_config):
    """Test creating a GitHub release."""
    with patch("github.Github", MockGithub):
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


def test_update_release(sample_config):
    """Test updating a GitHub release."""
    with patch("github.Github", MockGithub):
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
        assert url == "https://github.com/test/repo/releases/1"


def test_get_release_by_tag(sample_config):
    """Test getting a release by tag."""
    with patch("github.Github", MockGithub):
        service = GitHubService(sample_config)

        success, release = service.get_release_by_tag(
            owner="test",
            repo="repo",
            tag="v1.0.0",
        )

        assert success is True
        assert release["id"] == 1
        assert release["tag_name"] == "v1.0.0"


def test_delete_release(sample_config):
    """Test deleting a release."""
    with patch("github.Github", MockGithub):
        service = GitHubService(sample_config)

        success = service.delete_release(
            owner="test",
            repo="repo",
            release_id=1,
        )

        assert success is True


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


def test_is_available(sample_config):
    """Test service availability check."""
    with patch("github.Github", MockGithub):
        # Test with token and enabled
        config = AutoScribeConfig(github_release=True, github_token="test-token")
        service = GitHubService(config)
        assert service.is_available() is True

        # Test without token
        config = AutoScribeConfig(github_release=True, github_token=None)
        service = GitHubService(config)
        assert service.is_available() is False

        # Test disabled
        config = AutoScribeConfig(github_release=False, github_token="test-token")
        service = GitHubService(config)
        assert service.is_available() is False
