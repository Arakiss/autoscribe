"""Git service for interacting with git repositories."""

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..models.changelog import Change


class GitError(Exception):
    """Base exception for git operations."""
    pass


class GitInitError(GitError):
    """Exception raised when git repository initialization fails."""
    pass


class GitCommandError(GitError):
    """Exception raised when a git command fails."""
    pass


@dataclass
class GitCommit:
    """Git commit information."""

    hash: str
    message: str
    author: str
    date: datetime


class GitService:
    """Service for interacting with Git repositories."""

    CONVENTIONAL_TYPES = {
        "feat": "Features",
        "fix": "Bug Fixes",
        "docs": "Documentation",
        "style": "Style",
        "refactor": "Code Refactoring",
        "perf": "Performance",
        "test": "Tests",
        "build": "Build",
        "ci": "CI",
        "chore": "Chores",
        "revert": "Reverts",
    }

    def __init__(self, repo_path: str | Path | None = None):
        """Initialize the git service.

        Args:
            repo_path: Path to the git repository. If None, uses current directory.

        Raises:
            GitInitError: If the path is not a valid git repository.
        """
        self.repo_path = str(repo_path) if repo_path else os.getcwd()
        self.cwd = self.repo_path

        # Validate git repository
        try:
            self._run_command("git rev-parse --git-dir")
        except GitCommandError as e:
            raise GitInitError(f"Not a git repository: {self.repo_path}") from e

    def _run_command(self, command: str) -> str:
        """Run a git command and return its output.

        Args:
            command: Git command to execute.

        Returns:
            Command output as string.

        Raises:
            GitCommandError: If the command fails.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stderr and not result.stdout:
                raise subprocess.CalledProcessError(
                    returncode=1,
                    cmd=command,
                    output=result.stdout,
                    stderr=result.stderr
                )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitCommandError(f"Git command failed: {e.stderr}") from e
        except Exception as e:
            raise GitCommandError(f"Error running git command: {str(e)}") from e

    def get_commits_since_tag(self, tag: str | None = None) -> list[GitCommit]:
        """Get all commits since the specified tag.

        Args:
            tag: Git tag to get commits since. If None, gets all commits.

        Returns:
            List of commits.
        """
        format_str = "%H|%s|%an|%aI"
        if tag:
            command = f'git log {tag}..HEAD --format="{format_str}"'
        else:
            command = f'git log --format="{format_str}"'

        try:
            output = self._run_command(command)
            commits = []
            for line in output.split("\n"):
                if not line:
                    continue
                hash_, message, author, date_str = line.split("|")
                commits.append(
                    GitCommit(
                        hash=hash_,
                        message=message,
                        author=author,
                        date=datetime.fromisoformat(date_str),
                    )
                )
            return commits
        except GitCommandError:
            return []

    def get_latest_tag(self) -> str | None:
        """Get the latest tag from the repository.

        Returns:
            Latest tag or None if no tags exist.
        """
        try:
            # Get all tags sorted by version number (v1.2.3 format)
            tags = self._run_command("git tag -l 'v*'").split("\n")
            if not tags or not tags[0]:
                return None
            # Sort tags by version components
            return sorted(tags, key=lambda t: [int(n) for n in t[1:].split(".")], reverse=True)[0]
        except (GitCommandError, ValueError):
            return None

    def parse_conventional_commit(self, message: str) -> tuple[str, str | None, str, bool]:
        """Parse a conventional commit message.

        Args:
            message: Commit message to parse.

        Returns:
            Tuple of (type, scope, description, breaking).
        """
        # Regular expression for conventional commits
        pattern = (
            r"^(?P<type>" +
            "|".join(self.CONVENTIONAL_TYPES.keys()) +
            r")(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<description>[^\n]+)"
            r"(?:\n\n(?P<body>.+))?$"
        )
        match = re.match(pattern, message, re.DOTALL)

        if not match:
            return "other", None, message, False

        type_ = match.group("type")
        scope = match.group("scope")
        description = match.group("description")
        breaking = bool(match.group("breaking"))

        # Check for breaking changes in body
        body = match.group("body")
        if body and "BREAKING CHANGE:" in body:
            breaking = True

        return type_, scope, description, breaking

    def create_change_from_commit(self, commit: GitCommit) -> Change:
        """Create a Change object from a GitCommit.

        Args:
            commit: Git commit to convert.

        Returns:
            Change object.
        """
        type_, scope, description, breaking = self.parse_conventional_commit(commit.message)
        return Change(
            description=description,
            commit_hash=commit.hash,
            commit_message=commit.message,
            author=commit.author,
            type=type_,
            scope=scope,
            breaking=breaking,
            ai_enhanced=False,
            references=[],  # Extract references from commit message if needed
        )

    def create_tag(self, tag: str, message: str) -> None:
        """Create an annotated tag.

        Args:
            tag: Tag name.
            message: Tag message.

        Raises:
            GitCommandError: If tag creation fails.
        """
        if not tag or not message:
            raise GitCommandError("Tag name and message are required")
        self._run_command(f'git tag -a {tag} -m "{message}"')

    def push_tag(self, tag: str) -> None:
        """Push a tag to the remote repository.

        Args:
            tag: Tag name to push.

        Raises:
            GitCommandError: If tag push fails.
        """
        if not tag:
            raise GitCommandError("Tag name is required")
        self._run_command(f"git push origin {tag}")

    def get_remote_url(self) -> str | None:
        """Get the remote repository URL.

        Returns:
            Remote URL or None if no remote exists.
        """
        try:
            return self._run_command("git remote get-url origin")
        except GitCommandError:
            return None

    def extract_repo_info(self) -> tuple[str | None, str | None]:
        """Extract owner and repository name from remote URL.

        Returns:
            Tuple of (owner, repo) or (None, None) if not found.
        """
        url = self.get_remote_url()
        if not url:
            return None, None

        # Match GitHub HTTPS or SSH URL patterns
        https_pattern = r"https://github\.com/([^/]+)/([^/.]+)(?:\.git)?"
        ssh_pattern = r"git@github\.com:([^/]+)/([^/.]+)(?:\.git)?"

        for pattern in [https_pattern, ssh_pattern]:
            match = re.match(pattern, url)
            if match:
                return match.group(1), match.group(2)

        return None, None
