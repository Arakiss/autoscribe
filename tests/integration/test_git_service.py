from datetime import datetime
from pathlib import Path

import pytest

from autoscribe.core.git import GitCommit, GitService
from autoscribe.models.changelog import Change


def test_git_service_initialization(git_repo):
    """Test GitService initialization."""
    service = GitService(str(git_repo))
    assert service.repo_path == str(git_repo)

    service = GitService()
    assert service.repo_path is None


def test_run_command(git_repo):
    """Test running Git commands."""
    service = GitService(str(git_repo))

    # Test successful command
    result = service._run_command("git status")
    assert "On branch main" in result

    # Test failed command
    with pytest.raises(RuntimeError):
        service._run_command("git invalid-command")


def test_get_commits_since_tag(git_repo, sample_commits):
    """Test getting commits since a tag."""
    service = GitService(str(git_repo))

    # Test without tag
    commits = service.get_commits_since_tag()
    assert len(commits) == len(sample_commits) + 1  # +1 for initial commit
    assert all(isinstance(commit, GitCommit) for commit in commits)
    assert commits[0].message == sample_commits[-1]  # Last commit is first in list

    # Create a tag and test with it
    service._run_command('git tag -a v1.0.0 -m "Version 1.0.0"')
    commits = service.get_commits_since_tag("v1.0.0")
    assert len(commits) == 0


def test_get_latest_tag(git_repo):
    """Test getting the latest tag."""
    service = GitService(str(git_repo))

    # Test with no tags
    assert service.get_latest_tag() is None

    # Create a tag
    service._run_command('git config --global user.email "test@example.com"')
    service._run_command('git config --global user.name "Test User"')
    service._run_command('git init')
    service._run_command('touch README.md')
    service._run_command('git add README.md')
    service._run_command('git commit -m "Initial commit"')
    service._run_command('git tag v1.0.0')

    # Test with tag
    result = service._run_command('git tag')
    assert "v1.0.0" in result
    assert service.get_latest_tag() == "v1.0.0"

    # Test with multiple tags
    service._run_command('git tag -a v1.1.0 -m "Version 1.1.0"')
    assert service.get_latest_tag() == "v1.1.0"


def test_parse_conventional_commit():
    """Test parsing conventional commit messages."""
    service = GitService()

    # Test basic commit
    type_, scope, desc, breaking = service.parse_conventional_commit("feat: add new feature")
    assert type_ == "feat"
    assert scope is None
    assert desc == "add new feature"
    assert breaking is False

    # Test commit with scope
    type_, scope, desc, breaking = service.parse_conventional_commit("fix(core): resolve bug")
    assert type_ == "fix"
    assert scope == "core"
    assert desc == "resolve bug"
    assert breaking is False

    # Test breaking change
    type_, scope, desc, breaking = service.parse_conventional_commit("feat!: breaking change")
    assert type_ == "feat"
    assert scope is None
    assert desc == "breaking change"
    assert breaking is True

    # Test non-conventional commit
    type_, scope, desc, breaking = service.parse_conventional_commit("update something")
    assert type_ == "other"
    assert scope is None
    assert desc == "update something"
    assert breaking is False


def test_create_change_from_commit():
    """Test creating Change objects from commits."""
    service = GitService()
    commit = GitCommit(
        hash="abc123",
        message="feat(api): add new endpoint",
        author="Test User",
        date=datetime.now(),
    )

    change = service.create_change_from_commit(commit)
    assert isinstance(change, Change)
    assert change.commit_hash == "abc123"
    assert change.commit_message == "feat(api): add new endpoint"
    assert change.author == "Test User"
    assert change.type == "feat"
    assert change.scope == "api"
    assert change.breaking is False
    assert change.ai_enhanced is False


def test_create_and_push_tag(git_repo):
    """Test creating and pushing tags."""
    service = GitService(str(git_repo))

    # Test creating tag
    service.create_tag("v1.0.0", "Version 1.0.0")
    assert "v1.0.0" in service._run_command("git tag")

    # Test creating tag without message
    service.create_tag("v1.1.0", "Version 1.1.0")
    assert "v1.1.0" in service._run_command("git tag")


def test_get_remote_url(git_repo):
    """Test getting remote URL."""
    service = GitService(str(git_repo))

    # Test without remote
    assert service.get_remote_url() is None

    # Test with remote
    service._run_command("git remote add origin https://github.com/test/repo.git")
    assert service.get_remote_url() == "https://github.com/test/repo.git"


def test_extract_repo_info(git_repo):
    """Test extracting repository information."""
    service = GitService(str(git_repo))

    # Test without remote
    owner, repo = service.extract_repo_info()
    assert owner is None
    assert repo is None

    # Test with HTTPS remote
    service._run_command("git remote add origin https://github.com/test/repo.git")
    owner, repo = service.extract_repo_info()
    assert owner == "test"
    assert repo == "repo"

    # Test with SSH remote
    service._run_command("git remote set-url origin git@github.com:test/repo.git")
    owner, repo = service.extract_repo_info()
    assert owner == "test"
    assert repo == "repo"
