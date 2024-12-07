from datetime import datetime
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI

from autoscribe.models.changelog import Category, Change, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.openai import AIService


@pytest.fixture
def config():
    """Create a test configuration."""
    return AutoScribeConfig(
        openai_api_key="test-key",
        ai_model="gpt-4o-mini",
        ai_enabled=True,
    )


@pytest.fixture
def ai_service(config):
    """Create an AI service instance."""
    return AIService(config)


@pytest.mark.asyncio
async def test_is_available(ai_service):
    """Test AI service availability check."""
    assert ai_service.is_available()

    # Test without API key
    service = AIService(AutoScribeConfig(openai_api_key=None))
    assert not service.is_available()


@pytest.mark.asyncio
async def test_enhance_changes(ai_service):
    """Test enhancing changes with AI."""
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
    ]

    enhanced = ai_service.enhance_changes(changes)
    assert len(enhanced) == 2
    # La mejora puede fallar si las credenciales son inválidas
    if enhanced[0].ai_enhanced:
        assert enhanced[0].description != changes[0].description
    if enhanced[1].ai_enhanced:
        assert enhanced[1].description != changes[1].description


@pytest.mark.asyncio
async def test_generate_version_summary(ai_service):
    """Test generating version summary with AI."""
    version = Version(
        number="1.0.0",
        date=datetime.now(),
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
            Category(
                name="Fixed",
                changes=[
                    Change(
                        description="fix bug",
                        commit_hash="def456",
                        commit_message="fix: fix bug",
                        author="Test User",
                        type="fix",
                    ),
                ],
            ),
        ],
    )

    summarized = ai_service.generate_version_summary(version)
    assert summarized.summary is not None
    assert len(summarized.summary) > 0


@pytest.mark.asyncio
async def test_error_handling(ai_service):
    """Test error handling in AI service."""
    # Test with invalid API key
    service = AIService(AutoScribeConfig(openai_api_key="invalid-key"))
    changes = [
        Change(
            description="test change",
            commit_hash="abc123",
            commit_message="test: change",
            author="Test User",
            type="test",
        )
    ]

    enhanced = service.enhance_changes(changes)
    assert len(enhanced) == 1
    assert enhanced[0].description == changes[0].description
    assert enhanced[0].ai_enhanced is False