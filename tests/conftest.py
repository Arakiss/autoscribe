import os
from collections.abc import Generator
from pathlib import Path

import pytest
from _pytest.fixtures import FixtureRequest
from github import GithubException
from openai import OpenAIError

from autoscribe.models.config import AutoScribeConfig


class MockGithubRelease:
    @property
    def id(self) -> int:
        return 1

    @property
    def html_url(self) -> str:
        return "https://github.com/test/repo/releases/v1.0.0"

    @property
    def tag_name(self) -> str:
        return "v1.0.0"

    @property
    def title(self) -> str:
        return "Release v1.0.0"

    @property
    def body(self) -> str:
        return "Test release notes"

    @property
    def draft(self) -> bool:
        return False

    @property
    def prerelease(self) -> bool:
        return False

    @property
    def created_at(self) -> str:
        return "2024-01-01T00:00:00Z"

    @property
    def published_at(self) -> str:
        return "2024-01-01T00:00:00Z"

    def update_release(self, **kwargs) -> None:
        pass

    def delete_release(self) -> None:
        pass


class MockGithubRepo:
    def create_git_release(self, **kwargs) -> MockGithubRelease:
        return MockGithubRelease()

    def get_release(self, id_or_tag) -> MockGithubRelease:
        return MockGithubRelease()

    def get_release_by_tag(self, tag) -> MockGithubRelease:
        return MockGithubRelease()


class MockGithubUser:
    @property
    def login(self) -> str:
        return "test-user"


class MockGithub:
    def __init__(self, token: str | None = None):
        self.token = token

    def get_user(self) -> MockGithubUser:
        if not self.token or self.token == "invalid-token":
            raise GithubException(401, {"message": "Bad credentials"})
        return MockGithubUser()

    def get_repo(self, full_name: str) -> MockGithubRepo:
        if not self.token or self.token == "invalid-token":
            raise GithubException(401, {"message": "Bad credentials"})
        return MockGithubRepo()


class MockOpenAIMessage:
    def __init__(self, content: str):
        self.content = content
        self.role = "assistant"


class MockOpenAIChoice:
    def __init__(self, content: str):
        self.message = MockOpenAIMessage(content)
        self.finish_reason = "stop"
        self.index = 0


class MockOpenAIResponse:
    def __init__(self, content: str):
        self.id = "test-id"
        self.choices = [MockOpenAIChoice(content)]
        self.model = "gpt-4"


class MockOpenAIChat:
    def create(self, *args, **kwargs) -> MockOpenAIResponse:
        return MockOpenAIResponse("Enhanced description")


class MockOpenAIModels:
    def list(self):
        return [{"id": "gpt-4"}]


class MockOpenAI:
    def __init__(self, api_key: str | None = None):
        if not api_key or api_key == "invalid-key":
            raise OpenAIError("Invalid API key")
        self.api_key = api_key
        self.chat = MockOpenAIChat()
        self.models = MockOpenAIModels()


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
        ai_model="gpt-4",
        openai_api_key="test-key",
    )


@pytest.fixture
def git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary Git repository for tests."""
    import subprocess

    # Initialize Git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)

    # Configure Git globally for this process
    subprocess.run(
        ["git", "config", "--global", "user.name", "Test User"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--global", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )

    # Configure Git locally for this repo
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (temp_dir / "README.md").write_text("# Test Repository")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir,
        check=True,
        capture_output=True,
    )

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
        subprocess.run(
            ["git", "add", file_name],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", commit],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

    yield commits


@pytest.fixture
def mock_github():
    """Provide a mock GitHub client."""
    return MockGithub


@pytest.fixture
def mock_openai():
    """Provide a mock OpenAI client."""
    return MockOpenAI


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
