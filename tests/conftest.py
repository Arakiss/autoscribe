import os
from pathlib import Path
from typing import Generator

import pytest
from _pytest.fixtures import FixtureRequest

from autoscribe.models.config import AutoScribeConfig


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_config(temp_dir: Path) -> AutoScribeConfig:
    """Provide a sample configuration for tests."""
    return AutoScribeConfig(
        output=temp_dir / "CHANGELOG.md",
        version_file=temp_dir / "pyproject.toml",
        version_pattern="version = '{version}'",
        categories=[
            "Added",
            "Changed",
            "Fixed",
            "Documentation",
        ],
        github_release=True,
        github_token="test-token",
        ai_enabled=True,
        ai_model="gpt-4o-mini",
        openai_api_key="test-key",
    )


@pytest.fixture
def git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary Git repository for tests."""
    import subprocess

    # Initialize Git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    
    # Configure Git globally for this process
    subprocess.run(["git", "config", "--global", "user.name", "Test User"], check=True, capture_output=True)
    subprocess.run(["git", "config", "--global", "user.email", "test@example.com"], check=True, capture_output=True)
    
    # Configure Git locally for this repo
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_dir, check=True, capture_output=True)

    # Create initial commit
    (temp_dir / "README.md").write_text("# Test Repository")
    subprocess.run(["git", "add", "README.md"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, check=True, capture_output=True)

    yield temp_dir

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir / ".git")


@pytest.fixture
def sample_commits(git_repo: Path) -> Generator[list[str], None, None]:
    """Create sample commits in the repository."""
    import subprocess

    commits = [
        "feat: add new feature",
        "fix: resolve critical bug",
        "docs: update documentation",
        "feat!: breaking change",
        "chore: cleanup code",
    ]

    for i, commit in enumerate(commits, 1):
        # Create a dummy file for each commit
        file_name = f"file_{i}.txt"
        (git_repo / file_name).write_text("dummy content")
        subprocess.run(["git", "add", file_name], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit], cwd=git_repo, check=True, capture_output=True)

    yield commits


@pytest.fixture
def mock_openai_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock OpenAI API responses."""
    class MockResponse:
        def __init__(self, content: str):
            self.content = content
            self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})]

    def mock_create(*args, **kwargs):
        messages = kwargs.get("messages", [])
        if not messages:
            return MockResponse("Enhanced description")
        
        last_message = messages[-1].get("content", "")
        if "Generate a concise, user-friendly summary" in last_message:
            return MockResponse("This version introduces new features and includes breaking changes.")
        elif "Rewrite it as a clear, user-friendly changelog entry" in last_message:
            return MockResponse("Enhanced description")
        return MockResponse("Enhanced description")

    # Mock the OpenAI client
    class MockOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = type("ChatCompletion", (), {"create": mock_create})()
            self.api_key = kwargs.get("api_key", "test-key")

        def __bool__(self):
            return True

        def is_authenticated(self):
            return True

    monkeypatch.setattr("openai.OpenAI", MockOpenAI)


@pytest.fixture
def mock_github_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock GitHub API responses."""
    class MockResponse:
        def __init__(self):
            self.status = 201
            self.data = {
                "html_url": "https://github.com/test/repo/releases/v1.0.0",
                "message": "Success",
            }

        def read(self):
            import json
            return json.dumps(self.data).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def mock_urlopen(request, *args, **kwargs):
        # Capture headers for testing
        if hasattr(request, "headers"):
            mock_urlopen.last_request = request
        return MockResponse()

    mock_urlopen.last_request = None
    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)


@pytest.fixture
def env_vars(request: FixtureRequest) -> Generator[None, None, None]:
    """Set environment variables for tests."""
    old_environ = dict(os.environ)
    
    # Set test environment variables
    os.environ.update({
        "GITHUB_TOKEN": "test-github-token",
        "OPENAI_API_KEY": "test-openai-key",
    })

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(old_environ)
