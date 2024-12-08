"""Service for interacting with OpenAI API."""

from openai import APIError, AuthenticationError, OpenAI, OpenAIError

from ..models.changelog import Change, Version
from ..models.config import AutoScribeConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


class AIService:
    """Service for interacting with OpenAI API."""

    def __init__(self, config: AutoScribeConfig):
        """Initialize the AI service."""
        self.config = config
        self._client: OpenAI | None = None
        if config.ai_enabled and config.openai_api_key:
            try:
                self._client = OpenAI(api_key=config.openai_api_key)
                # Test connection
                if self._client is not None:
                    self._client.models.list()
                    logger.info("Successfully initialized OpenAI client")
            except OpenAIError as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self._client = None
            except Exception as e:
                logger.error(f"Unexpected error initializing OpenAI client: {e}")
                self._client = None

    def enhance_changes(self, changes: list[Change]) -> list[Change]:
        """Enhance change descriptions with AI."""
        if not self.is_available():
            return changes

        try:
            if self._client is None:
                return changes

            enhanced_changes = []
            for change in changes:
                prompt = (
                    "Given the following commit message, please provide a more descriptive "
                    "and user-friendly explanation of the changes:\n\n"
                    f"Message: {change.commit_message}\n"
                    f"Description: {change.description}\n\n"
                    "Please provide a concise, clear description that explains the "
                    "purpose and impact of this change."
                )

                response = self._client.chat.completions.create(
                    model=self.config.ai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that explains code changes."
                        },
                        {"role": "user", "content": prompt},
                    ],
                )

                content = response.choices[0].message.content
                if content is None:
                    logger.warning("Received empty response from OpenAI")
                    continue

                enhanced_description = content.strip()
                enhanced_changes.append(
                    Change(
                        description=enhanced_description,
                        commit_hash=change.commit_hash,
                        commit_message=change.commit_message,
                        author=change.author,
                        type=change.type,
                        scope=change.scope,
                        breaking=change.breaking,
                        ai_enhanced=True,
                        references=change.references,
                    )
                )

            return enhanced_changes
        except OpenAIError as e:
            logger.error(f"Failed to enhance changes: {e}")
            return changes
        except Exception as e:
            logger.error(f"Unexpected error enhancing changes: {e}")
            return changes

    def generate_version_summary(self, version: Version) -> Version:
        """Generate a summary for the version using AI."""
        if not self.is_available():
            return version

        try:
            if self._client is None:
                return version

            # Create a prompt with the version information
            changes_text = ""
            for category in version.categories:
                if not category.changes:
                    continue
                changes_text += f"\n{category.name}:\n"
                for change in category.changes:
                    changes_text += f"- {change.description}\n"

            prompt = (
                "Please provide a concise summary of the following changes "
                "for a release:\n\n"
                f"Version: {version.number}\n"
                f"Changes:{changes_text}\n\n"
                "Please provide a high-level overview that captures the main themes "
                "and significant changes in this release."
            )

            response = self._client.chat.completions.create(
                model=self.config.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes software releases."
                    },
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            if content is None:
                logger.warning("Received empty response from OpenAI")
                return version

            version.summary = content.strip()
            return version
        except OpenAIError as e:
            logger.error(f"Failed to generate version summary: {e}")
            return version
        except Exception as e:
            logger.error(f"Unexpected error generating version summary: {e}")
            return version

    def is_available(self) -> bool:
        """Check if the AI service is available."""
        if not self.config.ai_enabled or not self.config.openai_api_key:
            return False
        if not self._client:
            return False
        try:
            self._client.models.list()
            return True
        except (APIError, AuthenticationError):
            return False
