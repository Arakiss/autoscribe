"""Command-line interface for AutoScribe."""

import os
import sys
from pathlib import Path
from typing import cast

import click
import toml
from click import Context

from ..core.changelog import ChangelogService
from ..core.git import GitService
from ..models.config import AutoScribeConfig
from ..services.github import GitHubService
from ..services.openai import AIService
from ..utils.logging import get_logger

logger = get_logger(__name__)


def load_config(config_path: Path | None = None) -> AutoScribeConfig:
    """Load configuration from file or environment."""
    if config_path and config_path.exists():
        with open(config_path) as f:
            config_data = toml.load(f)
            return AutoScribeConfig(**config_data.get("tool", {}).get("autoscribe", {}))

    return AutoScribeConfig(
        github_token=os.getenv("GITHUB_TOKEN"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


def setup_services(
    config: AutoScribeConfig,
) -> tuple[GitService, ChangelogService, AIService | None, GitHubService | None]:
    """Set up required services."""
    git_service = GitService()
    ai_service = None
    github_service = None

    if config.ai_enabled:
        try:
            ai_service = AIService(config)
            if not ai_service.is_available():
                logger.warning("AI service is enabled but not available")
                ai_service = None
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            ai_service = None

    if config.github_release:
        try:
            github_service = GitHubService(config)
            if not github_service.is_available():
                logger.warning("GitHub release is enabled but service not available")
                github_service = None
        except Exception as e:
            logger.error(f"Failed to initialize GitHub service: {e}")
            github_service = None

    changelog_service = ChangelogService(config, git_service, ai_service)
    return git_service, changelog_service, ai_service, github_service


@click.group()
@click.version_option(prog_name="autoscribe")
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration file",
)
@click.pass_context
def cli(ctx: Context, config: Path | None = None):
    """AutoScribe - Automated changelog generation and management."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.option(
    "-v",
    "--version",
    type=str,
    help="Version number to generate",
)
@click.option(
    "--ai/--no-ai",
    default=None,
    help="Enable/disable AI enhancement",
)
@click.option(
    "--github-release/--no-github-release",
    default=None,
    help="Enable/disable GitHub release creation",
)
@click.pass_context
def generate(
    ctx: Context,
    version: str | None = None,
    ai: bool | None = None,
    github_release: bool | None = None,
):
    """Generate a new changelog version."""
    config = cast(AutoScribeConfig, ctx.obj["config"])

    # Override config with CLI options
    if ai is not None:
        config.ai_enabled = ai
    if github_release is not None:
        config.github_release = github_release

    try:
        git_service, changelog_service, ai_service, github_service = setup_services(config)

        # Generate version
        if version is None:
            logger.error("Version number is required")
            sys.exit(1)

        new_version = changelog_service.generate_version(version)
        if not new_version:
            logger.error("Failed to generate version")
            sys.exit(1)

        # Add version to changelog
        changelog_service.add_version(new_version)
        changelog_service._save_changelog()

        # Create GitHub release if enabled
        if github_service and github_service.is_available():
            # Extract owner and repo from remote URL
            owner, repo = git_service.extract_repo_info()
            if not owner or not repo:
                logger.error("Failed to extract repository information")
                sys.exit(1)

            success, url = github_service.create_release(
                owner=owner,
                repo=repo,
                tag_name=f"v{new_version.number}",
                name=f"Release {new_version.number}",
                body=changelog_service.render_version(new_version),
            )
            if success:
                logger.info(f"Created GitHub release: {url}")
            else:
                logger.error(f"Failed to create GitHub release: {url}")

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def init(ctx: Context):
    """Initialize AutoScribe configuration."""
    config = ctx.obj["config"]

    try:
        # Create changelog file if it doesn't exist
        if not config.output.exists():
            config.output.parent.mkdir(parents=True, exist_ok=True)
            config.output.touch()
            logger.info(f"Created changelog file at {config.output}")

        # Create configuration file if it doesn't exist
        config_file = Path("pyproject.toml")
        if not config_file.exists():
            config_file.write_text(
                "[tool.autoscribe]\n"
                'output = "CHANGELOG.md"\n'
                'version_file = "pyproject.toml"\n'
                'version_pattern = "version = \'{version}\'"\n'
                "github_release = true\n"
                "ai_enabled = true\n"
                'ai_model = "gpt-4"\n'
            )
            logger.info("Initialized configuration in pyproject.toml")
        else:
            # Update existing configuration
            config_data = toml.load(config_file)
            config_data.setdefault("tool", {}).setdefault("autoscribe", {}).update(
                {
                    "output": str(config.output),
                    "version_file": str(config.version_file),
                    "version_pattern": config.version_pattern,
                    "github_release": config.github_release,
                    "ai_enabled": config.ai_enabled,
                    "ai_model": config.ai_model,
                }
            )
            config_file.write_text(toml.dumps(config_data))
            logger.info("Updated configuration in pyproject.toml")

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
