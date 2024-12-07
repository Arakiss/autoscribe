from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from autoscribe.core.changelog import ChangelogService
from autoscribe.core.git import GitService
from autoscribe.models.changelog import Category, Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.openai import AIService


def test_changelog_service_initialization(git_repo, sample_config):
    """Test ChangelogService initialization."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)
    assert service.config == sample_config
    assert service.git_service == git_service
    assert service.ai_service is None


def test_generate_version_without_ai(git_repo, sample_commits):
    """Test version generation without AI enhancement."""
    config = AutoScribeConfig(ai_enabled=False)
    git_service = GitService(str(git_repo))
    service = ChangelogService(config, git_service)

    version = service.generate_version("1.0.0")
    assert isinstance(version, Version)
    assert version.number == "1.0.0"
    assert len(version.categories) > 0
    assert version.summary is None


def test_generate_version_with_ai(git_repo, sample_commits, mock_openai):
    """Test version generation with AI enhancement."""
    config = AutoScribeConfig(ai_enabled=True, openai_api_key="test-key")
    git_service = GitService(str(git_repo))
    with patch("openai.OpenAI", mock_openai):
        ai_service = AIService(config)
        service = ChangelogService(config, git_service, ai_service)

        version = service.generate_version("1.0.0")
        assert isinstance(version, Version)
        assert version.number == "1.0.0"
        assert version.summary == "Enhanced description"
        assert any(change.ai_enhanced for category in version.categories for change in category.changes)


def test_add_version(git_repo, sample_config):
    """Test adding a version to the changelog."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)

    version = Version(
        number="1.0.0",
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
    assert service.get_version("1.0.0") == version
    assert service.get_latest_version() == version


def test_version_management(git_repo, sample_config):
    """Test version management methods."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)

    version1 = Version(number="1.0.0", date=datetime(2024, 1, 1))
    version2 = Version(number="1.1.0", date=datetime(2024, 1, 2))
    unreleased = Version(number="Unreleased", date=datetime(2024, 1, 3))

    service.add_version(version1)
    assert service.get_version("1.0.0") == version1
    assert service.get_latest_version() == version1

    service.add_version(version2)
    assert service.get_latest_version() == version2

    service.add_version(unreleased)
    assert service.get_unreleased_changes() == unreleased


def test_changelog_file_creation(git_repo, sample_config, tmp_path):
    """Test changelog file creation."""
    output_path = tmp_path / "CHANGELOG.md"
    config = AutoScribeConfig(
        output=output_path,
        version_file=tmp_path / "pyproject.toml",
    )

    git_service = GitService(str(git_repo))
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
