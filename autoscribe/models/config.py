"""Configuration model for AutoScribe."""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AutoScribeConfig(BaseModel):
    """Configuration for AutoScribe."""

    output: Path = Field(default=Path("CHANGELOG.md"))
    version_file: Path = Field(default=Path("pyproject.toml"))
    version_pattern: str = Field(default="version = '{version}'")
    categories: List[str] = Field(
        default=[
            "Added",
            "Changed",
            "Deprecated",
            "Removed",
            "Fixed",
            "Security",
        ]
    )
    github_release: bool = Field(default=True)
    github_token: Optional[str] = Field(default=None)
    ai_enabled: bool = Field(default=True)
    ai_model: str = Field(default="gpt-4o-mini")
    openai_api_key: Optional[str] = Field(default=None)

    @field_validator("categories")
    def validate_categories(cls, v: List[str]) -> List[str]:
        """Validate changelog categories."""
        valid_categories = {
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
        }
        for category in v:
            if category not in valid_categories:
                raise ValueError(f"Invalid category: {category}")
        return v

    @field_validator("ai_model")
    def validate_ai_model(cls, v: str) -> str:
        """Validate AI model."""
        valid_models = {
            "gpt-4o-mini",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        }
        if v not in valid_models:
            raise ValueError(f"Invalid AI model: {v}")
        return v

    @model_validator(mode="after")
    def resolve_env_vars(self) -> "AutoScribeConfig":
        """Resolve environment variables in configuration values."""
        if self.github_token and self.github_token.startswith("env:"):
            env_var = self.github_token[4:]
            self.github_token = os.getenv(env_var)

        if self.openai_api_key and self.openai_api_key.startswith("env:"):
            env_var = self.openai_api_key[4:]
            self.openai_api_key = os.getenv(env_var)

        return self

    @field_validator("output", "version_file")
    def resolve_paths(cls, v: Path) -> Path:
        """Resolve paths to absolute paths."""
        return v.resolve()

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True
        extra = "forbid"
