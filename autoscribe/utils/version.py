import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class VersionType(str, Enum):
    """Types of version changes."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class Version:
    """Semantic version representation."""

    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """Convert version to string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """Parse a version string into a Version object."""
        pattern = r"""
            ^
            (?P<major>0|[1-9]\d*)
            \.
            (?P<minor>0|[1-9]\d*)
            \.
            (?P<patch>0|[1-9]\d*)
            (?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)
                (?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?
            (?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?
            $
        """
        match = re.match(pattern, version_string.strip(), re.VERBOSE)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    def bump(self, version_type: VersionType) -> "Version":
        """Create a new Version with the specified component bumped."""
        if version_type == VersionType.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif version_type == VersionType.MINOR:
            return Version(self.major, self.minor + 1, 0)
        else:  # PATCH
            return Version(self.major, self.minor, self.patch + 1)

    def _compare_prerelease(self, other: Optional[str]) -> int:
        """Compare prerelease strings."""
        if self.prerelease is None and other is None:
            return 0
        if self.prerelease is None:
            return 1  # No prerelease is greater than any prerelease
        if other is None:
            return -1
        return -1 if self.prerelease < other else (1 if self.prerelease > other else 0)

    def __lt__(self, other: "Version") -> bool:
        """Compare versions following SemVer 2.0.0 rules."""
        if not isinstance(other, Version):
            return NotImplemented
        
        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        
        # Compare prereleases
        return self._compare_prerelease(other.prerelease) < 0


def extract_version(content: str, pattern: str) -> Optional[str]:
    """Extract version from content using pattern."""
    match = re.search(pattern, content)
    return match.group(1) if match else None


def update_version_in_file(
    file_path: str, new_version: str, pattern: str
) -> Tuple[bool, str]:
    """Update version in a file."""
    try:
        with open(file_path, "r") as f:
            content = f.read()

        # Create pattern that captures the version part
        version_pattern = pattern.format(version="([^'\"]+)")
        replacement = pattern.format(version=new_version)

        if not re.search(version_pattern, content):
            return False, f"Version pattern not found in {file_path}"

        updated_content = re.sub(version_pattern, replacement, content)

        with open(file_path, "w") as f:
            f.write(updated_content)

        return True, f"Updated version to {new_version} in {file_path}"

    except Exception as e:
        return False, f"Failed to update version: {str(e)}"


def suggest_version_bump(breaking_changes: bool, has_new_features: bool) -> VersionType:
    """Suggest version bump type based on changes."""
    if breaking_changes:
        return VersionType.MAJOR
    elif has_new_features:
        return VersionType.MINOR
    else:
        return VersionType.PATCH
