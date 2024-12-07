from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.changelog import Category, Change, Changelog, Version
from ..models.config import AutoScribeConfig
from ..services.openai import AIService
from .git import GitService


class ChangelogService:
    """Service for managing changelog generation and updates."""

    TYPE_TO_CATEGORY = {
        # Added: for new features
        "feat": "Added",
        "feature": "Added",
        # Changed: for changes in existing functionality
        "change": "Changed",
        "refactor": "Changed",
        "perf": "Changed",
        "style": "Changed",
        # Deprecated: for soon-to-be removed features
        "deprecate": "Deprecated",
        # Removed: for now removed features
        "remove": "Removed",
        # Fixed: for any bug fixes
        "fix": "Fixed",
        "bugfix": "Fixed",
        # Security: in case of vulnerabilities
        "security": "Security",
        # Documentation changes
        "docs": "Documentation",
        # Testing changes
        "test": "Testing",
        # Build system changes
        "build": "Build",
        # CI changes
        "ci": "CI",
        # Other changes
        "chore": "Changed",
        "revert": "Changed",
    }

    def __init__(
        self,
        config: AutoScribeConfig,
        git_service: GitService,
        ai_service: Optional[AIService] = None,
    ):
        """Initialize the changelog service."""
        self.config = config
        self.git_service = git_service
        self.ai_service = ai_service
        self.changelog = self._load_or_create_changelog()

    def _load_or_create_changelog(self) -> Changelog:
        """Load existing changelog or create a new one."""
        output_path = Path(self.config.output)
        if output_path.exists():
            # TODO: Implement changelog parsing from file
            return Changelog()
        return Changelog()

    def _categorize_changes(self, changes: List[Change]) -> Dict[str, List[Change]]:
        """Categorize changes based on their type following Keep a Changelog."""
        categories: Dict[str, List[Change]] = {cat: [] for cat in self.config.categories}

        for change in changes:
            if change.breaking:
                # Breaking changes go into Changed category with a BREAKING CHANGE prefix
                categories["Changed"].append(change)
                continue
            
            # Get category from type mapping, fallback to Changed if not found
            category = self.TYPE_TO_CATEGORY.get(change.type, "Changed")
            # Only add to category if it's configured
            if category in categories:
                categories[category].append(change)

        return {k: v for k, v in categories.items() if v}

    def generate_version(self, version_number: str) -> Version:
        """Generate a new version entry."""
        # Get commits since last tag
        last_tag = self.git_service.get_latest_tag()
        commits = self.git_service.get_commits_since_tag(last_tag)

        # Create changes from commits
        changes = [self.git_service.create_change_from_commit(commit) for commit in commits]

        # Enhance changes with AI if available
        if self.ai_service and self.ai_service.is_available():
            changes = self.ai_service.enhance_changes(changes)

        # Categorize changes
        categorized_changes = self._categorize_changes(changes)

        # Create version object
        version = Version(
            number=version_number,
            date=datetime.now(),
            categories=[
                Category(name=name, changes=changes)
                for name, changes in categorized_changes.items()
            ],
            breaking_changes=any(change.breaking for change in changes),
        )

        # Generate summary with AI if available
        if self.ai_service and self.ai_service.is_available():
            version = self.ai_service.generate_version_summary(version)

        return version

    def add_version(self, version: Version) -> None:
        """Add a new version to the changelog."""
        self.changelog.add_version(version)
        self._save_changelog()

    def _save_changelog(self) -> None:
        """Save the changelog to file in Keep a Changelog format."""
        output = "# Changelog\n\n"
        output += "All notable changes to this project will be documented in this file.\n\n"
        output += "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
        output += "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"

        for version in self.changelog.versions:
            output += self.render_version(version)
            output += "\n"

        with open(self.config.output, "w") as f:
            f.write(output)

    def get_version(self, version_number: str) -> Optional[Version]:
        """Get a specific version from the changelog."""
        return self.changelog.get_version(version_number)

    def get_latest_version(self) -> Optional[Version]:
        """Get the latest version from the changelog."""
        return self.changelog.get_latest_version()

    def render_version(self, version: Version) -> str:
        """Render a single version entry in Keep a Changelog format."""
        output = f"## [{version.number}] - {version.date.strftime('%Y-%m-%d')}\n\n"

        if version.summary:
            output += f"{version.summary}\n\n"

        if version.breaking_changes:
            output += "### ⚠️ BREAKING CHANGES\n\n"

        for category in version.categories:
            if not category.changes:
                continue
                
            output += f"### {category.name}\n\n"
            for change in category.changes:
                prefix = "BREAKING CHANGE: " if change.breaking else ""
                scope = f"**{change.scope}**: " if change.scope else ""
                output += f"- {prefix}{scope}{change.description}\n"
            output += "\n"

        return output

    def get_unreleased_changes(self) -> Optional[Version]:
        """Get the unreleased changes."""
        return self.changelog.get_version("Unreleased")
