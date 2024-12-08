from typing import Any, cast

from github import BadCredentialsException, Github, GithubException
from github.Repository import Repository

from ..models.config import AutoScribeConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, config: AutoScribeConfig):
        """Initialize the GitHub service."""
        self.config = config
        self._github: Github | None = None
        if config.github_token:
            try:
                self._github = Github(config.github_token)
                # Test connection
                if self._github is not None:
                    # Store login to verify credentials
                    login = self._github.get_user().login
                    logger.info(f"Successfully initialized GitHub client for user {login}")
            except GithubException as e:
                logger.error(f"Failed to initialize GitHub client: {e}")
                self._github = None
            except Exception as e:
                logger.error(f"Unexpected error initializing GitHub client: {e}")
                self._github = None

    def create_release(
        self,
        owner: str,
        repo: str,
        tag_name: str,
        name: str,
        body: str,
        draft: bool = False,
        prerelease: bool = False,
    ) -> tuple[bool, str]:
        """Create a new release on GitHub."""
        if not self.is_available():
            return False, "GitHub token is required but not provided or invalid"

        try:
            if self._github is None:
                return False, "GitHub client is not initialized"
            repository = cast(Repository, self._github.get_repo(f"{owner}/{repo}"))
            release = repository.create_git_release(
                tag=tag_name,
                name=name,
                message=body,
                draft=draft,
                prerelease=prerelease,
            )
            return True, release.html_url
        except GithubException as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def update_release(
        self,
        owner: str,
        repo: str,
        release_id: int,
        tag_name: str,
        name: str,
        body: str,
        draft: bool = False,
        prerelease: bool = False,
    ) -> tuple[bool, str]:
        """Update an existing release on GitHub."""
        if not self.is_available():
            return False, "GitHub token is required but not provided or invalid"

        try:
            if self._github is None:
                return False, "GitHub client is not initialized"
            repository = cast(Repository, self._github.get_repo(f"{owner}/{repo}"))
            release = repository.get_release(release_id)
            release.update_release(
                tag_name=tag_name,
                name=name,
                message=body,
                draft=draft,
                prerelease=prerelease,
            )
            return True, release.html_url
        except GithubException as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def get_release_by_tag(
        self, owner: str, repo: str, tag: str
    ) -> tuple[bool, dict[str, Any] | None]:
        """Get a release by its tag name."""
        if not self.is_available():
            return False, None

        try:
            if self._github is None:
                return False, None
            repository = cast(Repository, self._github.get_repo(f"{owner}/{repo}"))
            # First try to get the release directly
            try:
                release = repository.get_release(tag)
            except GithubException:
                # If not found, try to get all releases and find by tag
                releases = repository.get_releases()
                try:
                    release = next(r for r in releases if r.tag_name == tag)
                except StopIteration:
                    return False, None

            return True, {
                "id": release.id,
                "html_url": release.html_url,
                "tag_name": release.tag_name,
                "name": release.title,
                "body": release.body,
                "draft": release.draft,
                "prerelease": release.prerelease,
                "created_at": release.created_at,
                "published_at": release.published_at,
            }
        except GithubException:
            return False, None
        except Exception:
            return False, None

    def delete_release(
        self, owner: str, repo: str, release_id: int
    ) -> tuple[bool, str | None]:
        """Delete a release by its ID."""
        if not self.is_available():
            return False, "GitHub token is required but not provided or invalid"

        try:
            if self._github is None:
                return False, "GitHub client is not initialized"
            repository = cast(Repository, self._github.get_repo(f"{owner}/{repo}"))
            release = repository.get_release(release_id)
            release.delete_release()
            return True, None
        except GithubException as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def is_available(self) -> bool:
        """Check if the GitHub service is available."""
        if not self.config.github_release or not self.config.github_token:
            return False
        if not self._github:
            return False
        try:
            # Verify credentials by getting the authenticated user
            user = self._github.get_user()
            return bool(user.login)
        except (GithubException, BadCredentialsException):
            return False
