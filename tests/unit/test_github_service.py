from datetime import datetime
from unittest.mock import MagicMock, patch
from github import Github, GithubException

import pytest

from autoscribe.models.changelog import Category, Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.github import GitHubService


class MockUser:
    @property
    def login(self):
        return "test-user"


class MockRelease:
    @property
    def html_url(self):
        return "https://github.com/test/repo/releases/v1.0.0"

    @property
    def id(self):
        return 1

    @property
    def tag_name(self):
        return "v1.0.0"

    @property
    def body(self):
        return "Test release"

    @property
    def draft(self):
        return False

    @property
    def prerelease(self):
        return False

    def update_release(self, **kwargs):
        pass

    def delete_release(self):
        pass


class MockRepo:
    def create_git_release(self, **kwargs):
        return MockRelease()

    def get_release(self, id_or_tag):
        return MockRelease()


class MockGithub:
    def __init__(self, token=None):
        self.token = token
        self.user = MockUser()

    def get_user(self):
        if not self.token:
            raise GithubException(401, {"message": "Bad credentials"})
        return self.user

    def get_repo(self, full_name):
        if not self.token:
            raise GithubException(401, {"message": "Bad credentials"})
        return MockRepo()


@pytest.fixture
def github_service():
    """Create a GitHub service instance with mocked client."""
    config = AutoScribeConfig(github_release=True, github_token="test-token")
    with patch("github.Github", MockGithub):
        service = GitHubService(config)
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
    assert release["tag_name"] == "v1.0.0"


def test_delete_release(github_service):
    """Test deleting a release."""
    success = github_service.delete_release(
        owner="test",
        repo="test",
        release_id=1,
    )

    assert success is True


def test_make_request_no_token():
    """Test making a request without a token."""
    service = GitHubService(AutoScribeConfig(github_token=None))
    success, error = service.create_release(
        owner="test",
        repo="test",
        tag_name="v1.0.0",
        name="v1.0.0",
        body="Test release",
    )
    assert success is False
    assert error == "GitHub token is required but not provided or invalid" 