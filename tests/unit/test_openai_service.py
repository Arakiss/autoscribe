from datetime import datetime
from unittest.mock import patch
import pytest
from openai import OpenAIError

from autoscribe.models.changelog import Change, Category, Version
from autoscribe.models.config import AutoScribeConfig
from autoscribe.services.openai import AIService


class MockMessage:
    @property
    def content(self):
        return "Enhanced description"

    @property
    def role(self):
        return "assistant"


class MockChoice:
    def __init__(self):
        self.message = MockMessage()
        self.finish_reason = "stop"
        self.index = 0


class MockCompletion:
    def __init__(self):
        self.id = "test"
        self.choices = [MockChoice()]
        self.model = "gpt-4"


class MockChat:
    def completions(self):
        return self

    def create(self, *args, **kwargs):
        return MockCompletion()


class MockModels:
    def list(self):
        return [{"id": "gpt-4"}]


class MockOpenAI:
    def __init__(self, api_key=None):
        if not api_key:
            raise OpenAIError("API key is required")
        self.api_key = api_key
        self.chat = MockChat()
        self.models = MockModels()


@pytest.fixture
def ai_service():
    """Create an AI service instance with mocked client."""
    config = AutoScribeConfig(ai_enabled=True, openai_api_key="test-key")
    with patch("openai.OpenAI", MockOpenAI):
        service = AIService(config)
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


def test_error_handling():
    """Test error handling in AI service."""
    # Test without API key
    config = AutoScribeConfig(ai_enabled=True, openai_api_key=None)
    service = AIService(config)
    assert not service.is_available()

    # Test with invalid API key
    class MockErrorClient:
        def __init__(self, api_key=None):
            raise OpenAIError("Invalid API key")

    with patch("openai.OpenAI", MockErrorClient):
        config = AutoScribeConfig(ai_enabled=True, openai_api_key="invalid-key")
        service = AIService(config)
        assert not service.is_available()

    # Test with disabled AI
    config = AutoScribeConfig(ai_enabled=False, openai_api_key="test-key")
    service = AIService(config)
    assert not service.is_available()