from pathlib import Path

import pytest
from pydantic import ValidationError

from autoscribe.models.config import AutoScribeConfig


def test_default_config():
    """Test default configuration values."""
    config = AutoScribeConfig()

    assert isinstance(config.output, Path)
    assert config.output.name == "CHANGELOG.md"
    assert isinstance(config.version_file, Path)
    assert config.version_file.name == "pyproject.toml"
    assert config.version_pattern == "version = '{version}'"
    assert config.categories == [
        "Added",
        "Changed",
        "Deprecated",
        "Removed",
        "Fixed",
        "Security",
    ]
    assert config.github_release is True
    assert config.github_token is None
    assert config.ai_enabled is True
    assert config.ai_model == "gpt-4o-mini"
    assert config.openai_api_key is None


def test_custom_config():
    """Test custom configuration values."""
    config = AutoScribeConfig(
        output="docs/CHANGELOG.md",
        version_file="VERSION",
        version_pattern=r"__version__ = '{version}'",
        categories=["Added", "Changed", "Removed"],
        github_release=False,
        github_token="test-token",
        ai_enabled=False,
        ai_model="gpt-3.5-turbo",
        openai_api_key="test-key",
    )

    assert config.output == Path("docs/CHANGELOG.md").resolve()
    assert config.version_file == Path("VERSION").resolve()
    assert config.version_pattern == r"__version__ = '{version}'"
    assert config.categories == ["Added", "Changed", "Removed"]
    assert config.github_release is False
    assert config.github_token == "test-token"
    assert config.ai_enabled is False
    assert config.ai_model == "gpt-3.5-turbo"
    assert config.openai_api_key == "test-key"


def test_invalid_config():
    """Test invalid configuration values."""
    # Test invalid category
    with pytest.raises(ValidationError):
        AutoScribeConfig(categories=["Invalid"])

    # Test invalid AI model
    with pytest.raises(ValidationError):
        AutoScribeConfig(ai_model="invalid-model")


def test_env_var_resolution(env_vars):
    """Test environment variable resolution."""
    config = AutoScribeConfig(
        github_token="env:GITHUB_TOKEN",
        openai_api_key="env:OPENAI_API_KEY",
    )

    assert config.github_token == "test-github-token"
    assert config.openai_api_key == "test-openai-key"


def test_path_resolution(temp_dir):
    """Test path resolution."""
    config = AutoScribeConfig(
        output=temp_dir / "CHANGELOG.md",
        version_file=temp_dir / "pyproject.toml",
    )

    assert config.output == (temp_dir / "CHANGELOG.md").resolve()
    assert config.version_file == (temp_dir / "pyproject.toml").resolve()


def test_string_path_conversion():
    """Test string to path conversion."""
    config = AutoScribeConfig(
        output="CHANGELOG.md",
        version_file="pyproject.toml",
    )

    assert isinstance(config.output, Path)
    assert isinstance(config.version_file, Path)


def test_extra_fields():
    """Test extra fields are forbidden."""
    with pytest.raises(ValidationError):
        AutoScribeConfig(
            extra_field="value",
        )


def test_validate_assignment():
    """Test assignment validation."""
    config = AutoScribeConfig()

    # Test valid category assignment
    config.categories = ["Added", "Changed"]
    assert config.categories == ["Added", "Changed"]

    # Test invalid category assignment
    with pytest.raises(ValidationError):
        config.categories = ["Invalid"]

    # Test valid AI model assignment
    config.ai_model = "gpt-3.5-turbo"
    assert config.ai_model == "gpt-3.5-turbo"

    # Test invalid AI model assignment
    with pytest.raises(ValidationError):
        config.ai_model = "invalid-model"
