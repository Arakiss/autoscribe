from datetime import datetime
from unittest.mock import patch

import pytest

from autoscribe.models.changelog import Category, Change, Version
from autoscribe.services.openai import AIService


@pytest.fixture
def ai_service(sample_config, mock_openai):
    """Create an AI service instance with mocked client."""
    with patch("openai.OpenAI", mock_openai):
        service = AIService(sample_config)
        return service


def test_is_available(ai_service):
    """Test AI service availability check."""
    assert ai_service.is_available()


def test_enhance_changes(ai_service):
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
    assert all(change.ai_enhanced for change in enhanced)
    assert all(change.description == "Enhanced description" for change in enhanced)


def test_generate_version_summary(ai_service):
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
    assert summarized.summary == "Enhanced description"


def test_error_handling(ai_service):
    """Test error handling."""
    # Test with invalid API key
    ai_service.config.openai_api_key = "invalid-key"
    assert not ai_service.is_available()

    # Test with disabled AI
    ai_service.config.ai_enabled = False
    assert not ai_service.is_available()

    # Test with no API key
    ai_service.config.openai_api_key = None
    assert not ai_service.is_available()
