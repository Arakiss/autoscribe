import json
from typing import Optional, Tuple, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..models.config import AutoScribeConfig


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, config: AutoScribeConfig):
        """Initialize the GitHub service."""
        self.config = config
        self.base_url = "https://api.github.com"

    def _make_request(
        self, endpoint: str, method: str = "GET", data: Optional[dict] = None
    ) -> Tuple[bool, Any]:
        """Make a request to the GitHub API."""
        if not self.config.github_token:
            raise ValueError("GitHub token is required but not provided")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {self.config.github_token}",
            "User-Agent": "AutoScribe",
        }
        
        if method in ("POST", "PATCH", "PUT") and data:
            headers["Content-Type"] = "application/json"

        try:
            request = Request(
                url,
                headers=headers,
                method=method,
                data=json.dumps(data).encode() if data else None,
            )
            with urlopen(request) as response:
                if response.status == 204:
                    return True, None
                    
                response_data = json.loads(response.read().decode('utf-8'))
                if response.status in (200, 201):
                    return True, response_data
                return False, response_data.get("message", "Unknown error")
        except HTTPError as e:
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                return False, error_data.get("message", "Not Found")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return False, str(e)
        except URLError as e:
            return False, f"Connection error: {str(e.reason)}"
        except Exception as e:
            return False, str(e)

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
        endpoint = f"repos/{owner}/{repo}/releases"
        data = {
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }

        success, response = self._make_request(endpoint, "POST", data)
        if success and isinstance(response, dict):
            return True, response.get("html_url", "")
        return False, str(response) if response else "Failed to create release"

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
        endpoint = f"repos/{owner}/{repo}/releases/{release_id}"
        data = {
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }

        success, response = self._make_request(endpoint, "PATCH", data)
        if success and isinstance(response, dict):
            return True, response.get("html_url", "")
        return False, str(response) if response else "Failed to update release"

    def get_release_by_tag(
        self, owner: str, repo: str, tag: str
    ) -> Tuple[bool, Optional[dict]]:
        """Get a release by its tag name."""
        endpoint = f"repos/{owner}/{repo}/releases/tags/{tag}"
        success, response = self._make_request(endpoint)
        if success and isinstance(response, dict):
            return True, response
        return False, None

    def delete_release(self, owner: str, repo: str, release_id: int) -> bool:
        """Delete a release from GitHub."""
        endpoint = f"repos/{owner}/{repo}/releases/{release_id}"
        success, _ = self._make_request(endpoint, "DELETE")
        return success

    def is_available(self) -> bool:
        """Check if GitHub service is available and configured."""
        return bool(self.config.github_release and self.config.github_token)
