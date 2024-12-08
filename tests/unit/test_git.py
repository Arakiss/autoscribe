from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from autoscribe.core.git import GitCommandError, GitCommit, GitService


@pytest.fixture
def git_service():
    """Create a GitService instance for testing."""
    return GitService()


def test_git_commit():
    """Test GitCommit dataclass."""
    now = datetime.now()
    commit = GitCommit(
        hash="abc123",
        message="feat: add feature",
        author="Test User",
        date=now,
    )

    assert commit.hash == "abc123"
    assert commit.message == "feat: add feature"
    assert commit.author == "Test User"
    assert commit.date == now


def test_parse_conventional_commit(git_service):
    """Test parsing of conventional commit messages."""
    # Test feature commit
    type_, scope, desc, breaking = git_service.parse_conventional_commit(
        "feat(api): add new endpoint"
    )
    assert type_ == "feat"
    assert scope == "api"
    assert desc == "add new endpoint"
    assert not breaking

    # Test breaking change with !
    type_, scope, desc, breaking = git_service.parse_conventional_commit(
        "feat!: breaking feature"
    )
    assert type_ == "feat"
    assert scope is None
    assert desc == "breaking feature"
    assert breaking

    # Test breaking change in body
    type_, scope, desc, breaking = git_service.parse_conventional_commit(
        "feat: feature\n\nBREAKING CHANGE: breaks stuff"
    )
    assert type_ == "feat"
    assert scope is None
    assert desc == "feature"
    assert breaking

    # Test non-conventional commit
    type_, scope, desc, breaking = git_service.parse_conventional_commit(
        "random commit message"
    )
    assert type_ == "other"
    assert scope is None
    assert desc == "random commit message"
    assert not breaking


@patch("subprocess.run")
def test_run_command(mock_run, git_service):
    """Test running git commands."""
    mock_run.return_value = MagicMock(
        stdout="test output\n",
        stderr="",
        returncode=0,
    )

    output = git_service._run_command("git status")
    assert output == "test output"
    mock_run.assert_called_once()

    # Test command failure
    mock_run.side_effect = Exception("Command failed")
    with pytest.raises(GitCommandError):
        git_service._run_command("git status")


@patch("subprocess.run")
def test_get_commits_since_tag(mock_run, git_service):
    """Test getting commits since tag."""
    mock_run.return_value = MagicMock(
        stdout="abc123|feat: add feature|Test User|2024-01-01T12:00:00+00:00\n"
              "def456|fix: fix bug|Test User|2024-01-02T12:00:00+00:00",
        stderr="",
        returncode=0,
    )

    # Test with tag
    commits = git_service.get_commits_since_tag("v1.0.0")
    assert len(commits) == 2
    assert commits[0].hash == "abc123"
    assert commits[0].message == "feat: add feature"
    assert commits[1].hash == "def456"
    assert commits[1].message == "fix: fix bug"

    # Test without tag
    commits = git_service.get_commits_since_tag()
    assert len(commits) == 2


@patch("subprocess.run")
def test_get_latest_tag(mock_run, git_service):
    """Test getting latest tag."""
    mock_run.return_value = MagicMock(
        stdout="v1.0.0\n",
        stderr="",
        returncode=0,
    )

    tag = git_service.get_latest_tag()
    assert tag == "v1.0.0"

    # Test no tags
    mock_run.side_effect = Exception("No tags")
    assert git_service.get_latest_tag() is None


def test_create_change_from_commit(git_service):
    """Test creating Change from GitCommit."""
    commit = GitCommit(
        hash="abc123",
        message="feat(api): add feature",
        author="Test User",
        date=datetime.now(),
    )

    change = git_service.create_change_from_commit(commit)
    assert change.commit_hash == "abc123"
    assert change.description == "add feature"
    assert change.type == "feat"
    assert change.scope == "api"
    assert not change.breaking
    assert not change.ai_enhanced


@patch("subprocess.run")
def test_tag_operations(mock_run, git_service):
    """Test tag creation and pushing."""
    mock_run.return_value = MagicMock(
        stdout="",
        stderr="",
        returncode=0,
    )

    # Test creating tag
    git_service.create_tag("v1.0.0", "Release v1.0.0")
    mock_run.assert_called_with(
        'git tag -a v1.0.0 -m "Release v1.0.0"',
        shell=True,
        cwd=git_service.cwd,
        capture_output=True,
        text=True,
        check=True,
    )

    # Test pushing tag
    git_service.push_tag("v1.0.0")
    mock_run.assert_called_with(
        "git push origin v1.0.0",
        shell=True,
        cwd=git_service.cwd,
        capture_output=True,
        text=True,
        check=True,
    )


@patch("subprocess.run")
def test_remote_operations(mock_run, git_service):
    """Test remote URL operations."""
    # Test HTTPS URL
    mock_run.return_value = MagicMock(
        stdout="https://github.com/user/repo.git\n",
        stderr="",
        returncode=0,
    )

    url = git_service.get_remote_url()
    assert url == "https://github.com/user/repo.git"

    owner, repo = git_service.extract_repo_info()
    assert owner == "user"
    assert repo == "repo"

    # Test SSH URL
    mock_run.return_value.stdout = "git@github.com:user/repo.git\n"
    owner, repo = git_service.extract_repo_info()
    assert owner == "user"
    assert repo == "repo"

    # Test invalid URL
    mock_run.return_value.stdout = "invalid-url\n"
    owner, repo = git_service.extract_repo_info()
    assert owner is None
    assert repo is None

    # Test no remote
    mock_run.side_effect = RuntimeError("No remote")
    assert git_service.get_remote_url() is None
    owner, repo = git_service.extract_repo_info()
    assert owner is None
    assert repo is None
