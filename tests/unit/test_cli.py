from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from autoscribe.cli.main import cli
from autoscribe.core.changelog import ChangelogService
from autoscribe.core.git import GitService
from autoscribe.models.changelog import Category, Change, Version
from autoscribe.services.github import GitHubService
from autoscribe.services.openai import AIService


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_services():
    """Create mock services."""
    git_service = MagicMock(spec=GitService)
    changelog_service = MagicMock(spec=ChangelogService)
    github_service = MagicMock(spec=GitHubService)
    ai_service = MagicMock(spec=AIService)

    # Configure git service
    git_service.get_latest_tag.return_value = "v1.0.0"
    git_service.extract_repo_info.return_value = ("test-owner", "test-repo")

    # Configure changelog service
    version = Version(
        number="1.1.0",
        categories=[
            Category(
                name="Added",
                changes=[
                    Change(
                        description="add feature",
                        commit_hash="abc123",
                        commit_message="feat: add feature",
                        author="Test User",
                        type="feat",
                    ),
                ],
            ),
        ],
    )
    changelog_service.generate_version.return_value = version

    return {
        "git": git_service,
        "changelog": changelog_service,
        "github": github_service,
        "ai": ai_service,
    }


def test_version_command(runner):
    """Test version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "autoscribe" in result.output


@patch("autoscribe.cli.main.GitService")
@patch("autoscribe.cli.main.ChangelogService")
@patch("autoscribe.cli.main.GitHubService")
@patch("autoscribe.cli.main.AIService")
def test_generate_command(
    mock_ai_cls, mock_github_cls, mock_changelog_cls, mock_git_cls, runner, mock_services
):
    """Test generate command."""
    # Configure mocks
    mock_git_cls.return_value = mock_services["git"]
    mock_changelog_cls.return_value = mock_services["changelog"]
    mock_github_cls.return_value = mock_services["github"]
    mock_ai_cls.return_value = mock_services["ai"]

    # Test basic generation
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 0
    mock_services["changelog"].generate_version.assert_called_once()
    mock_services["changelog"].add_version.assert_called_once()

    # Test with version
    result = runner.invoke(cli, ["generate", "--version", "2.0.0"])
    assert result.exit_code == 0
    mock_services["changelog"].generate_version.assert_called_with("2.0.0")

    # Test with AI
    result = runner.invoke(cli, ["generate", "--ai"])
    assert result.exit_code == 0
    assert mock_ai_cls.called

    # Test with GitHub release
    result = runner.invoke(cli, ["generate", "--github-release"])
    assert result.exit_code == 0
    assert mock_services["github"].create_release.called


@patch("autoscribe.cli.main.GitService")
@patch("autoscribe.cli.main.ChangelogService")
def test_init_command(mock_changelog_cls, mock_git_cls, runner, mock_services, tmp_path):
    """Test init command."""
    mock_git_cls.return_value = mock_services["git"]
    mock_changelog_cls.return_value = mock_services["changelog"]

    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        # Test basic init
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert Path(td, "CHANGELOG.md").exists()
        assert Path(td, ".autoscribe.toml").exists()

        # Test with custom output
        result = runner.invoke(cli, ["init", "--output", "docs/CHANGELOG.md"])
        assert result.exit_code == 0
        assert Path(td, "docs/CHANGELOG.md").exists()


def test_config_validation(runner, tmp_path):
    """Test configuration validation."""
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        # Test invalid config
        config_path = Path(td, ".autoscribe.toml")
        config_path.write_text("""
            [tool.autoscribe]
            invalid = true
        """)

        result = runner.invoke(cli, ["generate"])
        assert result.exit_code != 0
        assert "Generation failed" in result.output


@patch("autoscribe.cli.main.GitService")
@patch("autoscribe.cli.main.ChangelogService")
def test_error_handling(mock_changelog_cls, mock_git_cls, runner, mock_services):
    """Test error handling."""
    mock_git_cls.return_value = mock_services["git"]
    mock_changelog_cls.return_value = mock_services["changelog"]

    # Test git error
    mock_services["git"].get_latest_tag.side_effect = RuntimeError("Git error")
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code != 0
    assert "Error" in result.output

    # Test changelog error
    mock_services["changelog"].generate_version.side_effect = RuntimeError("Changelog error")
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_help_command(runner):
    """Test help command."""
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Commands:" in result.output

    # Test command help
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--version" in result.output
