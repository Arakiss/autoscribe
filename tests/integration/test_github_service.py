from urllib.error import HTTPError

import pytest

from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.github import GitHubService


def test_github_service_initialization(sample_config):
    """Test GitHubService initialization."""
    service = GitHubService(sample_config)
    assert service.config == sample_config
    assert service.base_url == "https://api.github.com"


def test_make_request_without_token():
    """Test making request without token."""
    config = AutoScribeConfig(github_token=None)
    service = GitHubService(config)

    with pytest.raises(ValueError, match="GitHub token is required"):
        service._make_request("repos/test/repo")


def test_create_release(sample_config, monkeypatch):
    """Test creating a GitHub release."""
    service = GitHubService(sample_config)

    def mock_urlopen(request):
        class MockResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): 
                return b'{"html_url": "https://github.com/test/repo/releases/v1.0.0"}'
            @property
            def status(self): return 201

        return MockResponse()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

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


def test_update_release(sample_config, monkeypatch):
    """Test updating a GitHub release."""
    service = GitHubService(sample_config)

    def mock_urlopen(request):
        class MockResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): 
                return b'{"html_url": "https://github.com/test/repo/releases/v1.0.0"}'
            @property
            def status(self): return 200

        return MockResponse()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

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


def test_get_release_by_tag(sample_config, monkeypatch):
    """Test getting a release by tag."""
    service = GitHubService(sample_config)

    def mock_urlopen(request):
        class MockResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): 
                return b'{"id": 1, "html_url": "https://github.com/test/repo/releases/v1.0.0"}'
            @property
            def status(self): return 200

        return MockResponse()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    success, release = service.get_release_by_tag(
        owner="test",
        repo="repo",
        tag="v1.0.0",
    )

    assert success is True
    assert release["html_url"] == "https://github.com/test/repo/releases/v1.0.0"


def test_delete_release(sample_config, monkeypatch):
    """Test deleting a release."""
    service = GitHubService(sample_config)

    def mock_urlopen(request):
        class MockResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b''
            @property
            def status(self): return 204

        return MockResponse()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    success = service.delete_release(
        owner="test",
        repo="repo",
        release_id=1,
    )

    assert success is True


def test_is_available():
    """Test service availability check."""
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


def test_error_handling(sample_config, monkeypatch):
    """Test error handling in requests."""
    service = GitHubService(sample_config)

    def mock_urlopen_error(*args, **kwargs):
        class MockHTTPError(HTTPError):
            def read(self):
                return b'{"message": "Not Found"}'
            def __init__(self, *args, **kwargs):
                super().__init__(
                    url="https://api.github.com/test",
                    code=404,
                    msg="Not Found",
                    hdrs={},
                    fp=None,
                )

        raise MockHTTPError()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_error)

    # Test error in create_release
    success, result = service.create_release(
        owner="test",
        repo="repo",
        tag_name="v1.0.0",
        name="Release v1.0.0",
        body="Release notes",
    )

    assert success is False
    assert "Not Found" in result


def test_request_headers(sample_config, monkeypatch):
    """Test request headers."""
    service = GitHubService(sample_config)
    captured_request = None

    def mock_urlopen(request):
        nonlocal captured_request
        captured_request = request
        class MockResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): 
                return b'{"html_url": "https://github.com/test/repo/releases/v1.0.0"}'
            @property
            def status(self): return 201

        return MockResponse()

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    service.create_release(
        owner="test",
        repo="repo",
        tag_name="v1.0.0",
        name="Release v1.0.0",
        body="Release notes",
    )

    assert captured_request is not None
    assert captured_request.headers["Authorization"] == f"Bearer {sample_config.github_token}"
    assert captured_request.headers["Accept"] == "application/vnd.github.v3+json"
    assert captured_request.headers["Content-Type"] == "application/json"
