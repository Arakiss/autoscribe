import os
from datetime import datetime
from pathlib import Path

import pytest

from autoscribe.core.git import GitCommandError, GitInitError, GitService
from autoscribe.models.changelog import Change


def test_git_service_initialization(git_repo):
    """Test GitService initialization."""
    service = GitService(str(git_repo))
    assert service.repo_path == str(git_repo)
    assert service.cwd == str(git_repo)

    # Test with non-existent directory
    with pytest.raises(GitInitError):
        GitService("/non/existent/path")

    # Test with non-git directory
    temp_dir = Path(git_repo).parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    try:
        with pytest.raises(GitInitError):
            GitService(str(temp_dir))
    finally:
        temp_dir.rmdir()

    # Test with None (current directory)
    current_dir = os.getcwd()
    os.chdir(str(git_repo))
    try:
        service = GitService()
        assert service.repo_path == str(git_repo)
    finally:
        os.chdir(current_dir)


def test_get_commits_since_tag(git_repo, sample_commits):
    """Test getting commits since tag."""
    service = GitService(str(git_repo))
    commits = service.get_commits_since_tag()
    # Account for the initial commit plus sample commits
    assert len(commits) == len(sample_commits) + 1
    assert all(isinstance(commit.date, datetime) for commit in commits)

    # Test with non-existent tag
    commits = service.get_commits_since_tag("non-existent-tag")
    assert commits == []


def test_get_latest_tag(git_repo):
    """Test getting latest tag."""
    service = GitService(str(git_repo))
    assert service.get_latest_tag() is None

    # Create a tag
    service.create_tag("v1.0.0", "Release v1.0.0")
    assert service.get_latest_tag() == "v1.0.0"

    # Create another tag
    service.create_tag("v1.1.0", "Release v1.1.0")
    assert service.get_latest_tag() == "v1.1.0"


def test_parse_conventional_commit(git_repo):
    """Test parsing conventional commit messages."""
    service = GitService(str(git_repo))

    # Test feature commit
    type_, scope, desc, breaking = service.parse_conventional_commit(
        "feat(api): add new endpoint"
    )
    assert type_ == "feat"
    assert scope == "api"
    assert desc == "add new endpoint"
    assert not breaking

    # Test breaking change with !
    type_, scope, desc, breaking = service.parse_conventional_commit(
        "feat!: breaking feature"
    )
    assert type_ == "feat"
    assert scope is None
    assert desc == "breaking feature"
    assert breaking

    # Test breaking change in body
    type_, scope, desc, breaking = service.parse_conventional_commit(
        "feat: feature\n\nBREAKING CHANGE: breaks stuff"
    )
    assert type_ == "feat"
    assert scope is None
    assert desc == "feature"
    assert breaking

    # Test non-conventional commit
    type_, scope, desc, breaking = service.parse_conventional_commit(
        "random commit message"
    )
    assert type_ == "other"
    assert scope is None
    assert desc == "random commit message"
    assert not breaking

    # Test all conventional types
    for type_ in GitService.CONVENTIONAL_TYPES:
        msg = f"{type_}: test message"
        parsed_type, _, _, _ = service.parse_conventional_commit(msg)
        assert parsed_type == type_


def test_create_change_from_commit(git_repo, sample_commits):
    """Test creating Change from GitCommit."""
    service = GitService(str(git_repo))
    commits = service.get_commits_since_tag()

    for commit in commits:
        change = service.create_change_from_commit(commit)
        assert isinstance(change, Change)
        assert change.commit_hash == commit.hash
        assert change.commit_message == commit.message
        assert change.author == commit.author
        assert not change.ai_enhanced
        assert isinstance(change.references, list)


def test_tag_operations(git_repo):
    """Test tag creation and pushing."""
    service = GitService(str(git_repo))

    # Test invalid tag name
    with pytest.raises(GitCommandError):
        service.create_tag("", "Empty tag name")

    # Test empty message
    with pytest.raises(GitCommandError):
        service.create_tag("v1.0.0", "")

    # Create valid tag
    service.create_tag("v1.0.0", "Release v1.0.0")
    assert service.get_latest_tag() == "v1.0.0"

    # Push tag (this will fail without a remote, which is expected)
    with pytest.raises(GitCommandError):
        service.push_tag("v1.0.0")

    # Push non-existent tag
    with pytest.raises(GitCommandError):
        service.push_tag("non-existent-tag")


def test_remote_operations(git_repo):
    """Test remote URL operations."""
    service = GitService(str(git_repo))

    # Test without remote
    assert service.get_remote_url() is None
    owner, repo = service.extract_repo_info()
    assert owner is None
    assert repo is None

    # Add HTTPS remote
    service._run_command("git remote add origin https://github.com/test/repo.git")
    assert service.get_remote_url() == "https://github.com/test/repo.git"
    owner, repo = service.extract_repo_info()
    assert owner == "test"
    assert repo == "repo"

    # Change to SSH remote
    service._run_command("git remote set-url origin git@github.com:test/repo.git")
    assert service.get_remote_url() == "git@github.com:test/repo.git"
    owner, repo = service.extract_repo_info()
    assert owner == "test"
    assert repo == "repo"


def test_error_handling(git_repo):
    """Test error handling."""
    service = GitService(str(git_repo))

    # Test invalid command
    with pytest.raises(GitCommandError):
        service._run_command("git invalid-command")

    # Test invalid tag
    with pytest.raises(GitCommandError):
        service.create_tag("", "Invalid tag")

    # Test invalid remote
    with pytest.raises(GitCommandError):
        service.push_tag("v1.0.0")

    # Test command with stderr output but success
    result = service._run_command("git status")
    assert isinstance(result, str)

    # Test command with both stdout and stderr
    service._run_command("git init")  # This often produces both stdout and stderr
