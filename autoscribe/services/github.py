import json
from typing import Optional, Tuple, Any, Dict
from github import Github, GithubException, Auth
from ..models.config import AutoScribeConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)

class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, config: AutoScribeConfig):
        """Initialize the GitHub service."""
        self.config = config
        self._github = None
        if config.github_token:
            try:
                self._github = Github(config.github_token)
                # Test connection
                self._github.get_user().login
                logger.info("Successfully initialized GitHub client")
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
    ) -> Tuple[bool, str]:
        """Create a new release on GitHub."""
        if not self.is_available():
            return False, "GitHub token is required but not provided or invalid"

        try:
            repository = self._github.get_repo(f"{owner}/{repo}")
            release = repository.create_git_release(
                tag=tag_name,
                name=name,
                message=body,
                draft=draft,
                prerelease=prerelease
            )
            logger.info(f"Created release {tag_name} for {owner}/{repo}")
            return True, release.html_url
        except GithubException as e:
            error_msg = e.data.get("message", str(e))
            logger.error(f"Failed to create release: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected error creating release: {e}")
            return False, str(e)

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
    ) -> Tuple[bool, str]:
        """Update an existing release on GitHub."""
        if not self.is_available():
            return False, "GitHub token is required but not provided or invalid"

        try:
            repository = self._github.get_repo(f"{owner}/{repo}")
            release = repository.get_release(release_id)
            release.update_release(
                name=name,
                message=body,
                draft=draft,
                prerelease=prerelease
            )
            logger.info(f"Updated release {release_id} for {owner}/{repo}")
            return True, release.html_url
        except GithubException as e:
            error_msg = e.data.get("message", str(e))
            logger.error(f"Failed to update release: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected error updating release: {e}")
            return False, str(e)

    def get_release_by_tag(
        self, owner: str, repo: str, tag: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Get a release by its tag name."""
        if not self.is_available():
            return False, None

        try:
            repository = self._github.get_repo(f"{owner}/{repo}")
            release = repository.get_release(tag)
            release_data = {
                "id": release.id,
                "tag_name": release.tag_name,
                "name": release.title,
                "html_url": release.html_url,
                "body": release.body,
                "draft": release.draft,
                "prerelease": release.prerelease,
                "created_at": release.created_at,
                "published_at": release.published_at,
            }
            logger.debug(f"Retrieved release {tag} for {owner}/{repo}")
            return True, release_data
        except GithubException as e:
            error_msg = e.data.get("message", str(e))
            logger.error(f"Failed to get release: {error_msg}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error getting release: {e}")
            return False, None

    def delete_release(
        self, owner: str, repo: str, release_id: int
    ) -> Tuple[bool, Optional[str]]:
        """Delete a release from GitHub."""
        if not self.is_available():
            return False, "GitHub token is required but not provided or invalid"

        try:
            repository = self._github.get_repo(f"{owner}/{repo}")
            release = repository.get_release(release_id)
            release.delete_release()
            logger.info(f"Deleted release {release_id} from {owner}/{repo}")
            return True, None
        except GithubException as e:
            error_msg = e.data.get("message", str(e))
            logger.error(f"Failed to delete release: {error_msg}")
            return False, error_msg
        except Exception as e:
            logger.error(f"Unexpected error deleting release: {e}")
            return False, str(e)

    def is_available(self) -> bool:
        """Check if GitHub service is available and configured."""
        if not self.config.github_release or not self.config.github_token:
            return False
        if not self._github:
            return False
        try:
            self._github.get_user().login
            return True
        except:
            return False
