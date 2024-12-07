from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Change(BaseModel):
    """Represents a single change in the changelog."""

    description: str = Field(..., description="User-friendly description of the change")
    commit_hash: str = Field(..., description="Git commit hash")
    commit_message: str = Field(..., description="Original commit message")
    author: str = Field(..., description="Change author")
    type: str = Field(..., description="Type of change (e.g., feat, fix)")
    scope: Optional[str] = Field(None, description="Scope of the change")
    breaking: bool = Field(False, description="Whether this is a breaking change")
    ai_enhanced: bool = Field(False, description="Whether AI enhanced the description")
    references: List[str] = Field(default_factory=list, description="Related issue/PR references")


class Category(BaseModel):
    """Represents a category of changes following Keep a Changelog."""

    name: Literal[
        "Added",
        "Changed",
        "Deprecated",
        "Removed",
        "Fixed",
        "Security",
        "Documentation",
        "Performance",
        "Testing",
        "Build",
        "CI",
    ] = Field(..., description="Keep a Changelog standard category")
    changes: List[Change] = Field(default_factory=list, description="Changes in this category")


class Version(BaseModel):
    """Represents a version in the changelog."""

    number: str = Field(..., description="Version number (following SemVer)")
    date: datetime = Field(default_factory=datetime.now, description="Release date (YYYY-MM-DD)")
    categories: List[Category] = Field(default_factory=list, description="Change categories")
    summary: Optional[str] = Field(None, description="AI-generated version summary")
    breaking_changes: bool = Field(False, description="Whether this version contains breaking changes")
    yanked: bool = Field(False, description="Whether this version was yanked")
    compare_url: Optional[str] = Field(None, description="URL to compare with previous version")


class Changelog(BaseModel):
    """Represents the complete changelog following Keep a Changelog format."""

    versions: List[Version] = Field(default_factory=list, description="List of versions")
    title: str = Field(default="Changelog", description="Changelog title")
    description: str = Field(
        default=(
            "All notable changes to this project will be documented in this file.\n\n"
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),\n"
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)."
        ),
        description="Keep a Changelog standard description"
    )
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    def add_version(self, version: Version) -> None:
        """Add a new version to the changelog, maintaining reverse chronological order."""
        self.versions.insert(0, version)  # Always insert at the beginning for latest first
        self.last_updated = datetime.now()

    def get_version(self, version_number: str) -> Optional[Version]:
        """Get a specific version by number."""
        for version in self.versions:
            if version.number == version_number:
                return version
        return None

    def get_latest_version(self) -> Optional[Version]:
        """Get the latest version (excluding unreleased)."""
        for version in self.versions:
            if version.number != "Unreleased":
                return version
        return None

    def get_unreleased_changes(self) -> Optional[Version]:
        """Get unreleased changes if they exist."""
        return self.get_version("Unreleased")
