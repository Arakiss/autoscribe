from unittest.mock import patch

from autoscribe.core.changelog import ChangelogService
from autoscribe.core.git import GitService
from autoscribe.models.changelog import Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.openai import AIService


def test_changelog_service_initialization(sample_config, git_repo):
    """Test ChangelogService initialization."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)
    assert service.config == sample_config
    assert service.git_service == git_service
    assert service.ai_service is None


def test_generate_version_without_ai(sample_config, git_repo, sample_commits):
    """Test version generation without AI enhancement."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)

    version = service.generate_version("1.0.0")
    assert isinstance(version, Version)
    assert version.number == "1.0.0"
    assert len(version.categories) > 0


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


def test_add_version(sample_config, git_repo, sample_commits):
    """Test adding a version to the changelog."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)

    version = service.generate_version("1.0.0")
    service.add_version(version)

    assert sample_config.output.exists()
    assert "# Changelog" in sample_config.output.read_text()
    assert "## 1.0.0" in sample_config.output.read_text()


def test_version_management(sample_config, git_repo, sample_commits):
    """Test version management."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)

    # Generate and add first version
    version1 = service.generate_version("1.0.0")
    service.add_version(version1)

    # Generate and add second version
    version2 = service.generate_version("1.1.0")
    service.add_version(version2)

    content = sample_config.output.read_text()
    assert "## 1.1.0" in content
    assert "## 1.0.0" in content
    assert content.index("## 1.1.0") < content.index("## 1.0.0")


def test_changelog_file_creation(sample_config, git_repo, sample_commits):
    """Test changelog file creation."""
    git_service = GitService(str(git_repo))
    service = ChangelogService(sample_config, git_service)

    # Generate and add version
    version = service.generate_version("1.0.0")
    service.add_version(version)

    # Check file creation
    assert sample_config.output.exists()
    content = sample_config.output.read_text()
    assert "# Changelog" in content
    assert "## 1.0.0" in content
