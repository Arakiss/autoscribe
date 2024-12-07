"""Command-line interface for AutoScribe."""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
import toml
from dotenv import load_dotenv

from ..core.changelog import ChangelogService
from ..core.git import GitService
from ..models.config import AutoScribeConfig
from ..services.github import GitHubService
from ..services.openai import AIService
from ..utils.logging import setup_logger
from .. import __version__

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logger()


def load_config(config_path: Optional[str] = None) -> AutoScribeConfig:
    """Load configuration from file or defaults."""
    try:
        if config_path:
            with open(config_path) as f:
                config_data = toml.load(f)
                if "tool" not in config_data or "autoscribe" not in config_data["tool"]:
                    raise click.ClickException("Invalid configuration file format")
                return AutoScribeConfig(**config_data["tool"]["autoscribe"])
        
        # Try to load from default location
        default_config = Path(".autoscribe.toml")
        if default_config.exists():
            with open(default_config) as f:
                config_data = toml.load(f)
                if "tool" in config_data and "autoscribe" in config_data["tool"]:
                    return AutoScribeConfig(**config_data["tool"]["autoscribe"])
        
        return AutoScribeConfig()
    except Exception as e:
        raise click.ClickException(f"Configuration error: {e}")


def initialize_services(
    config: AutoScribeConfig,
) -> Tuple[GitService, Optional[AIService], Optional[GitHubService]]:
    """Initialize required services."""
    try:
        # Initialize Git service
        git_service = GitService()
        if not git_service:
            raise click.ClickException("Failed to initialize Git service")

        # Initialize AI service if enabled
        ai_service = None
        if config.ai_enabled:
            ai_service = AIService(config)
            if not ai_service.is_available():
                logger.warning("AI service is enabled but not available")

        # Initialize GitHub service if enabled
        github_service = None
        if config.github_release:
            github_service = GitHubService(config)
            if not github_service.is_available():
                logger.warning("GitHub release is enabled but service not available")

        return git_service, ai_service, github_service
    except Exception as e:
        raise click.ClickException(f"Service initialization failed: {e}")


@click.group()
@click.version_option(version=__version__, prog_name="autoscribe")
def cli():
    """AutoScribe - Intelligent changelog automation powered by AI."""
    pass


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Configuration file path",
)
def init(output: Optional[str], config: Optional[str]):
    """Initialize AutoScribe in the current directory."""
    try:
        # Load or create config
        config_obj = load_config(config)
        if output:
            config_obj.output = Path(output)

        # Create output directory if needed
        output_dir = config_obj.output.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create empty changelog
        with open(config_obj.output, "w") as f:
            f.write("""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

""")

        # Create config file if it doesn't exist
        if not Path(".autoscribe.toml").exists():
            with open(".autoscribe.toml", "w") as f:
                f.write("""[tool.autoscribe]
output = "CHANGELOG.md"
version_file = "pyproject.toml"
version_pattern = "version = '{version}'"
categories = [
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security"
]
github_release = true
github_token = "env:GITHUB_TOKEN"
ai_enabled = true
ai_model = "gpt-4o-mini"
openai_api_key = "env:OPENAI_API_KEY"
""")

        click.echo("✨ AutoScribe initialized successfully!")

    except Exception as e:
        raise click.ClickException(f"Initialization failed: {e}")


@cli.command()
@click.option(
    "--version",
    "-v",
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
    help="Create GitHub release",
)
@click.option(
    "--draft/--no-draft",
    default=False,
    help="Create draft release",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Configuration file path",
)
def generate(
    version: Optional[str],
    ai: Optional[bool],
    github_release: Optional[bool],
    draft: bool,
    config: Optional[str],
):
    """Generate changelog entries."""
    try:
        # Load configuration
        config_obj = load_config(config)

        # Override config with CLI options
        if ai is not None:
            config_obj.ai_enabled = ai
        if github_release is not None:
            config_obj.github_release = github_release

        # Initialize services
        git_service, ai_service, github_service = initialize_services(config_obj)

        # Initialize changelog service
        changelog_service = ChangelogService(config_obj, git_service, ai_service)

        # Get version number if not provided
        if not version:
            latest_tag = git_service.get_latest_tag()
            if not latest_tag:
                raise click.ClickException("No version specified and no tags found")
            # TODO: Implement version bump suggestion based on changes
            version = "1.0.0" if not latest_tag else latest_tag.lstrip("v")

        # Generate version
        new_version = changelog_service.generate_version(version)
        changelog_service.add_version(new_version)

        # Create GitHub release if enabled
        if config_obj.github_release and github_service and github_service.is_available():
            owner, repo = git_service.extract_repo_info()
            if not owner or not repo:
                logger.warning("Could not determine GitHub repository info")
            else:
                success, url = github_service.create_release(
                    owner=owner,
                    repo=repo,
                    tag_name=f"v{new_version.number}",
                    name=f"v{new_version.number}",
                    body=changelog_service.render_version(new_version),
                    draft=draft,
                )
                if success:
                    click.echo(f"🚀 Created GitHub release: {url}")
                else:
                    logger.warning("Failed to create GitHub release")

        click.echo(f"✨ Generated changelog for version {new_version.number}")

    except Exception as e:
        raise click.ClickException(f"Generation failed: {e}")


def main():
    """Main entry point."""
    try:
        cli()
    except click.ClickException as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
