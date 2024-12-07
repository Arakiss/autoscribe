from datetime import datetime
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from autoscribe.models.changelog import Category, Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.github import GitHubService


@pytest.fixture
def config():
    """Create a test configuration."""
    return AutoScribeConfig(
        github_token="test-token",
        github_release=True,
    )


@pytest.fixture
def github_service(config):
    """Create a GitHub service instance."""
    return GitHubService(config)


def test_is_available(github_service):
    """Test GitHub service availability check."""
    assert github_service.is_available()

    # Test without token
    service = GitHubService(AutoScribeConfig(github_token=None))
    assert not service.is_available()


@patch("urllib.request.urlopen")
def test_create_release(mock_urlopen, github_service):
    """Test creating GitHub release."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status = 201
    mock_response.read.return_value = b'{"html_url": "https://github.com/test/test/releases/v1.0.0"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

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
    assert url == "https://github.com/test/test/releases/v1.0.0"

    # Test error
    mock_error = HTTPError("url", 422, "Unprocessable Entity", {}, None)
    mock_error.read = lambda: b'{"message": "Validation Failed"}'
    mock_urlopen.return_value.__enter__.side_effect = mock_error

    success, error = github_service.create_release(
        owner="test",
        repo="test",
        tag_name="v1.0.0",
        name="v1.0.0",
        body="Test release",
    )

    assert success is False
    assert error == "Validation Failed"


@patch("urllib.request.urlopen")
def test_update_release(mock_urlopen, github_service):
    """Test updating a release."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"html_url": "https://github.com/test/test/releases/v1.0.0"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    success, url = github_service.update_release(
        owner="test",
        repo="test",
        release_id=1,
        tag_name="v1.0.0",
        name="v1.0.0",
        body="Updated release",
    )

    assert success is True
    assert url == "https://github.com/test/test/releases/v1.0.0"


@patch("urllib.request.urlopen")
def test_get_release_by_tag(mock_urlopen, github_service):
    """Test getting a release by tag."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"id": 1, "tag_name": "v1.0.0"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    success, release = github_service.get_release_by_tag(
        owner="test",
        repo="test",
        tag="v1.0.0",
    )

    assert success is True
    assert release["id"] == 1
    assert release["tag_name"] == "v1.0.0"


@patch("urllib.request.urlopen")
def test_delete_release(mock_urlopen, github_service):
    """Test deleting a release."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status = 204
    mock_urlopen.return_value.__enter__.return_value = mock_response

    success = github_service.delete_release(
        owner="test",
        repo="test",
        release_id=1,
    )

    assert success is True


def test_make_request_no_token(github_service):
    """Test making a request without a token."""
    service = GitHubService(AutoScribeConfig(github_token=None))
    with pytest.raises(ValueError, match="GitHub token is required but not provided"):
        service._make_request("test") 