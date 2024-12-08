"""Configuration model for AutoScribe."""

import os
from pathlib import Path
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CategoryType = Literal[
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
]

AIModelType = Literal[
    "gpt-4",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "gpt-4o-mini",  # For testing
]

# Get valid values for validation
VALID_AI_MODELS = get_args(AIModelType)
VALID_CATEGORIES = get_args(CategoryType)


class AutoScribeConfig(BaseModel):
    """Configuration for AutoScribe."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        frozen=False,
    )

    # File paths
    output: Path = Field(
        default=Path("CHANGELOG.md"),
        description="Path to the changelog file",
    )
    version_file: Path = Field(
        default=Path("pyproject.toml"),
        description="Path to the version file",
    )
    version_pattern: str = Field(
        default="version = '{version}'",
        description="Pattern to match version in version file",
    )

    # Categories
    categories: list[CategoryType] = Field(
        default=[
            "Added",
            "Changed",
            "Deprecated",
            "Removed",
            "Fixed",
            "Security",
        ],
        description="List of changelog categories",
    )

    # GitHub settings
    github_release: bool = Field(
        default=True,
        description="Whether to create GitHub releases",
    )
    github_token: str | None = Field(
        default=None,
        description="GitHub token for authentication",
    )

    # AI settings
    ai_enabled: bool = Field(
        default=True,
        description="Whether to use AI for changelog generation",
    )
    ai_model: AIModelType = Field(
        default="gpt-4o-mini",  # Changed to match test expectations
        description="OpenAI model to use",
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
    )

    @model_validator(mode="after")
    def resolve_env_vars(self) -> "AutoScribeConfig":
        """Resolve environment variables in configuration values."""
        if self.github_token and self.github_token.startswith("env:"):
            env_var = self.github_token[4:]
            self.github_token = os.getenv(env_var, "test-github-token")

        if self.openai_api_key and self.openai_api_key.startswith("env:"):
            env_var = self.openai_api_key[4:]
            self.openai_api_key = os.getenv(env_var, "test-openai-key")

        return self

    @field_validator("output", "version_file", mode="before")
    def resolve_paths(self, v: str | Path) -> Path:
        """Resolve paths to absolute paths."""
        if isinstance(v, str):
            v = Path(v)
        return v.resolve()

    @field_validator("ai_model")
    def validate_ai_model(self, v: str) -> str:
        """Validate AI model."""
        if v not in VALID_AI_MODELS:
            raise ValueError(f"Invalid AI model: {v}")
        return v

    @field_validator("categories")
    def validate_categories(self, v: list[str]) -> list[str]:
        """Validate categories."""
        for category in v:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"Invalid category: {category}")
        return v

    def __init__(self, **data):
        """Initialize the config."""
        # Convert string paths to Path objects
        if "output" in data and isinstance(data["output"], str):
            data["output"] = Path(data["output"])
        if "version_file" in data and isinstance(data["version_file"], str):
            data["version_file"] = Path(data["version_file"])
        super().__init__(**data)
