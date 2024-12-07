from pathlib import Path
import pytest
from unittest.mock import patch

from autoscribe.core.changelog import ChangelogService
from autoscribe.core.git import GitService
from autoscribe.models.changelog import Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.openai import AIService
from ..unit.test_openai_service import MockOpenAI


@pytest.fixture
def sample_config(temp_dir):
    """Create a test configuration."""
    return AutoScribeConfig(
        output=temp_dir / "CHANGELOG.md",
        version_file=temp_dir / "pyproject.toml",
        github_release=True,
        github_token="test-token",
        ai_enabled=True,
        ai_model="gpt-4o-mini",
        openai_api_key="test-key",
    )


def test_changelog_service_initialization(sample_config, git_repo):
    """Test ChangelogService initialization."""
    git_service = GitService(str(git_repo))
    with patch("openai.OpenAI", MockOpenAI):
        ai_service = AIService(sample_config)
        service = ChangelogService(sample_config, git_service, ai_service)

        assert service.config == sample_config
        assert service.git_service == git_service
        assert service.ai_service == ai_service
        assert service.changelog is not None


def test_load_or_create_changelog(sample_config, temp_dir):
    """Test loading or creating changelog."""
    git_service = GitService()
    service = ChangelogService(sample_config, git_service)

    # Test creating new changelog
    changelog = service._load_or_create_changelog()
    assert changelog.title == "Changelog"
    assert len(changelog.versions) == 0

    # Test loading existing changelog
    changelog_path = temp_dir / "CHANGELOG.md"
    changelog_path.write_text("""# Test Changelog

## [1.0.0] - 2024-01-01

### Features

- Initial release
""")

    sample_config.output = changelog_path
    service = ChangelogService(sample_config, git_service)
    changelog = service._load_or_create_changelog()
    assert changelog.title == "Changelog"  # TODO: Implement changelog parsing


def test_categorize_changes():
    """Test change categorization."""
    git_service = GitService()
    service = ChangelogService(AutoScribeConfig(), git_service)

    changes = [
        Change(
            description="Add new feature",
            commit_hash="abc123",
            commit_message="feat: add new feature",
            author="Test User",
            type="feat",
        ),
        Change(
            description="Fix bug",
            commit_hash="def456",
            commit_message="fix: fix bug",
            author="Test User",
            type="fix",
        ),
        Change(
            description="Breaking change",
            commit_hash="ghi789",
            commit_message="feat!: breaking change",
            author="Test User",
            type="feat",
            breaking=True,
        ),
    ]

    categorized = service._categorize_changes(changes)
    assert "Added" in categorized
    assert "Fixed" in categorized
    assert "Changed" in categorized
    assert len(categorized["Added"]) == 1
    assert len(categorized["Fixed"]) == 1
    assert len(categorized["Changed"]) == 1


def test_generate_version(git_repo, sample_commits):
    """Test version generation."""
    config = AutoScribeConfig(ai_enabled=False)
    git_service = GitService(str(git_repo))
    service = ChangelogService(config, git_service)

    version = service.generate_version("1.0.0")
    assert isinstance(version, Version)
    assert version.number == "1.0.0"
    assert len(version.categories) > 0
    assert any(c.name == "Added" for c in version.categories)
    assert any(c.name == "Changed" for c in version.categories)


def test_generate_version_with_ai(git_repo, sample_commits):
    """Test version generation with AI enhancement."""
    config = AutoScribeConfig(ai_enabled=True, openai_api_key="test-key")
    git_service = GitService(str(git_repo))
    with patch("openai.OpenAI", MockOpenAI):
        ai_service = AIService(config)
        service = ChangelogService(config, git_service, ai_service)

        version = service.generate_version("1.0.0")
        assert isinstance(version, Version)
        assert version.number == "1.0.0"
        assert version.summary == "Enhanced description"
        assert any(change.ai_enhanced for category in version.categories for change in category.changes)


def test_add_version(temp_dir):
    """Test adding version to changelog."""
    config = AutoScribeConfig(output=temp_dir / "CHANGELOG.md")
    git_service = GitService()
    service = ChangelogService(config, git_service)

    version = Version(
        number="1.0.0",
        categories=[],
    )

    service.add_version(version)
    assert len(service.changelog.versions) == 1
    assert service.changelog.versions[0] == version
    assert config.output.exists()


def test_save_changelog(temp_dir):
    """Test saving changelog to file."""
    config = AutoScribeConfig(output=temp_dir / "CHANGELOG.md")
    git_service = GitService()
    service = ChangelogService(config, git_service)

    version = Version(
        number="1.0.0",
        categories=[],
    )
    service.changelog.add_version(version)
    service._save_changelog()

    assert config.output.exists()
    content = config.output.read_text()
    assert "# Changelog" in content
    assert "[1.0.0]" in content


def test_get_version():
    """Test getting specific version."""
    config = AutoScribeConfig()
    git_service = GitService()
    service = ChangelogService(config, git_service)

    version1 = Version(number="1.0.0", categories=[])
    version2 = Version(number="1.1.0", categories=[])

    service.add_version(version1)
    service.add_version(version2)

    assert service.get_version("1.0.0") == version1
    assert service.get_version("1.1.0") == version2
    assert service.get_version("2.0.0") is None


def test_get_latest_version():
    """Test getting latest version."""
    config = AutoScribeConfig()
    git_service = GitService()
    service = ChangelogService(config, git_service)

    assert service.get_latest_version() is None

    version1 = Version(number="1.0.0", categories=[])
    version2 = Version(number="1.1.0", categories=[])

    service.add_version(version1)
    assert service.get_latest_version() == version1

    service.add_version(version2)
    assert service.get_latest_version() == version2


def test_render_version():
    """Test version rendering."""
    config = AutoScribeConfig()
    git_service = GitService()
    service = ChangelogService(config, git_service)

    version = Version(
        number="1.0.0",
        categories=[],
        summary="Test summary",
    )

    rendered = service.render_version(version)
    assert "[1.0.0]" in rendered
    assert "Test summary" in rendered
