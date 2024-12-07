"""Git service for interacting with git repositories."""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import os

from ..models.changelog import Change


@dataclass
class GitCommit:
    """Git commit information."""

    hash: str
    message: str
    author: str
    date: datetime


class GitService:
    """Service for interacting with git repositories."""

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize the git service."""
        self.repo_path = repo_path
        self.cwd = repo_path or os.getcwd()

    def _run_command(self, command: str) -> str:
        """Run a git command and return its output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Error running git command: {str(e)}")

    def get_commits_since_tag(self, tag: Optional[str] = None) -> List[GitCommit]:
        """Get all commits since the specified tag."""
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
        except Exception:
            return []

    def get_latest_tag(self) -> Optional[str]:
        """Get the latest tag from the repository."""
        try:
            return self._run_command("git describe --tags --abbrev=0")
        except Exception:
            return None

    def parse_conventional_commit(self, message: str) -> Tuple[str, Optional[str], str, bool]:
        """Parse a conventional commit message."""
        # Regular expression for conventional commits
        pattern = r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<description>[^\n]+)(?:\n\n(?P<body>.+))?$"
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
        """Create a Change object from a GitCommit."""
        type_, scope, description, breaking = self.parse_conventional_commit(commit.message)
        return Change(
            description=description,
            commit_hash=commit.hash,
            commit_message=commit.message,
            author=commit.author,
            type=type_,
            scope=scope,
            breaking=breaking,
        )

    def create_tag(self, tag: str, message: str) -> None:
        """Create an annotated tag."""
        self._run_command(f'git tag -a {tag} -m "{message}"')

    def push_tag(self, tag: str) -> None:
        """Push a tag to the remote repository."""
        self._run_command(f"git push origin {tag}")

    def get_remote_url(self) -> Optional[str]:
        """Get the remote repository URL."""
        try:
            return self._run_command("git remote get-url origin")
        except Exception:
            return None

    def extract_repo_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract owner and repo name from remote URL."""
        url = self.get_remote_url()
        if not url:
            return None, None

        # Match HTTPS URL format
        https_match = re.match(r"https://github\.com/([^/]+)/([^.]+)\.git", url)
        if https_match:
            return https_match.group(1), https_match.group(2)

        # Match SSH URL format
        ssh_match = re.match(r"git@github\.com:([^/]+)/([^.]+)\.git", url)
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)

        return None, None
