from datetime import datetime
from unittest.mock import MagicMock

import pytest

from autoscribe.core.changelog import ChangelogService
from autoscribe.core.git import GitCommit, GitService
from autoscribe.models.changelog import Category, Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.openai import AIService


@pytest.fixture
def config():
    """Create a test configuration."""
    return AutoScribeConfig(
        output="CHANGELOG.md",
        categories=["Added", "Changed", "Fixed"],
    )


@pytest.fixture
def git_service():
    """Create a mock git service."""
    service = MagicMock(spec=GitService)
    service.get_latest_tag.return_value = "v1.0.0"
    service.get_commits_since_tag.return_value = [
        GitCommit(
            hash="abc123",
            message="feat: add feature",
            author="Test User",
            date=datetime.now(),
        ),
        GitCommit(
            hash="def456",
            message="fix: fix bug",
            author="Test User",
            date=datetime.now(),
        ),
    ]
    service.create_change_from_commit.side_effect = lambda commit: Change(
        description=commit.message.split(": ")[1],
        commit_hash=commit.hash,
        commit_message=commit.message,
        author=commit.author,
        type=commit.message.split(": ")[0],
    )
    return service


@pytest.fixture
def ai_service():
    """Create a mock AI service."""
    service = MagicMock(spec=AIService)
    service.is_available.return_value = True
    service.enhance_changes.side_effect = lambda changes: [
        Change(
            description=f"Enhanced: {change.description}",
            commit_hash=change.commit_hash,
            commit_message=change.commit_message,
            author=change.author,
            type=change.type,
            ai_enhanced=True,
        )
        for change in changes
    ]
    service.generate_version_summary.side_effect = lambda version: Version(
        number=version.number,
        date=version.date,
        categories=version.categories,
        summary="AI generated summary",
        breaking_changes=version.breaking_changes,
    )
    return service


@pytest.fixture
def changelog_service(config, git_service, ai_service):
    """Create a changelog service instance."""
    return ChangelogService(config, git_service, ai_service)


def test_load_or_create_changelog(tmp_path, config, git_service):
    """Test loading or creating a changelog."""
    # Test creating new changelog
    service = ChangelogService(config, git_service)
    assert service.changelog is not None
    assert len(service.changelog.versions) == 0

    # Test loading existing changelog
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text("""# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2024-01-01

### Added
- Initial release
""")

    config.output = changelog_path
    service = ChangelogService(config, git_service)
    assert service.changelog is not None
    # TODO: Implement changelog parsing
    assert len(service.changelog.versions) == 0


def test_categorize_changes(changelog_service):
    """Test change categorization."""
    changes = [
        Change(
            description="add feature",
            commit_hash="abc123",
            commit_message="feat: add feature",
            author="Test User",
            type="feat",
        ),
        Change(
            description="fix bug",
            commit_hash="def456",
            commit_message="fix: fix bug",
            author="Test User",
            type="fix",
        ),
        Change(
            description="breaking change",
            commit_hash="ghi789",
            commit_message="feat!: breaking change",
            author="Test User",
            type="feat",
            breaking=True,
        ),
    ]

    categorized = changelog_service._categorize_changes(changes)

    assert "Added" in categorized
    assert "Fixed" in categorized
    assert "Changed" in categorized
    assert len(categorized["Added"]) == 1
    assert len(categorized["Fixed"]) == 1
    assert len(categorized["Changed"]) == 1  # Breaking change
    assert categorized["Changed"][0].breaking is True


def test_generate_version(changelog_service):
    """Test version generation."""
    version = changelog_service.generate_version("1.1.0")

    assert version.number == "1.1.0"
    assert isinstance(version.date, datetime)
    assert len(version.categories) == 2  # Added and Fixed from our mock commits
    assert version.summary == "AI generated summary"  # From mock AI service
    assert not version.breaking_changes

    # Test without AI service
    service = ChangelogService(
        changelog_service.config,
        changelog_service.git_service,
        ai_service=None,
    )
    version = service.generate_version("1.1.0")
    assert version.summary is None


def test_save_changelog(tmp_path, config, git_service):
    """Test saving changelog to file."""
    output_path = tmp_path / "CHANGELOG.md"
    config.output = output_path

    service = ChangelogService(config, git_service)
    version = Version(
        number="1.0.0",
        date=datetime(2024, 1, 1),
        categories=[
            Category(
                name="Added",
                changes=[
                    Change(
                        description="Initial release",
                        commit_hash="abc123",
                        commit_message="feat: initial release",
                        author="Test User",
                        type="feat",
                    ),
                ],
            ),
        ],
    )
    service.add_version(version)

    assert output_path.exists()
    content = output_path.read_text()
    assert "# Changelog" in content
    assert "## [1.0.0] - 2024-01-01" in content
    assert "### Added" in content
    assert "- Initial release" in content


def test_version_management(changelog_service):
    """Test version management methods."""
    version1 = Version(number="1.0.0", date=datetime(2024, 1, 1))
    version2 = Version(number="1.1.0", date=datetime(2024, 1, 2))
    unreleased = Version(number="Unreleased", date=datetime(2024, 1, 3))

    changelog_service.add_version(version1)
    assert changelog_service.get_version("1.0.0") == version1
    assert changelog_service.get_latest_version() == version1

    changelog_service.add_version(version2)
    assert changelog_service.get_latest_version() == version2

    changelog_service.add_version(unreleased)
    assert changelog_service.get_unreleased_changes() == unreleased
