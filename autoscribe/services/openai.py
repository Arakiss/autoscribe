from typing import List, Optional
from openai import OpenAI, OpenAIError
from pydantic import BaseModel

from ..models.changelog import Change, Version
from ..models.config import AutoScribeConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)

class AIService:
    """Service for AI-powered changelog enhancements."""

    def __init__(self, config: AutoScribeConfig):
        """Initialize the AI service."""
        self.config = config
        self.client = None
        if config.ai_enabled and config.openai_api_key:
            try:
                self.client = OpenAI(api_key=config.openai_api_key)
                # Test connection with a minimal request
                self.client.models.list()
                logger.info("Successfully initialized OpenAI client")
            except OpenAIError as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
            except Exception as e:
                logger.error(f"Unexpected error initializing OpenAI client: {e}")
                self.client = None

    def enhance_change_description(self, change: Change) -> Change:
        """Enhance a change description using AI."""
        if not self.is_available():
            logger.debug("AI enhancement skipped: service not available")
            return change

        prompt = f"""
        Given this git commit:
        Type: {change.type}
        Scope: {change.scope or 'N/A'}
        Message: {change.commit_message}
        Breaking: {change.breaking}

        Rewrite it as a clear, user-friendly changelog entry that:
        1. Starts with a verb in present tense
        2. Is concise but descriptive
        3. Avoids technical jargon unless necessary
        4. Highlights breaking changes if any
        5. Maintains the original meaning

        Respond with ONLY the enhanced description, nothing else.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config.ai_model,
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in changelog entries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=100,
                n=1,
            )

            if response.choices and response.choices[0].message.content:
                enhanced_description = response.choices[0].message.content.strip()
                change.description = enhanced_description
                change.ai_enhanced = True
                logger.debug(f"Successfully enhanced change description for {change.type}")
            else:
                logger.warning("OpenAI returned empty response")

        except OpenAIError as e:
            logger.error(f"OpenAI API error enhancing description: {e}")
        except Exception as e:
            logger.error(f"Unexpected error enhancing description: {e}")

        return change

    def generate_version_summary(self, version: Version) -> Version:
        """Generate a summary for a version using AI."""
        if not self.is_available():
            logger.debug("Version summary generation skipped: service not available")
            return version

        changes_text = "\n".join(
            f"- {change.description} ({change.type})"
            for category in version.categories
            for change in category.changes
        )

        if not changes_text:
            logger.debug("No changes to summarize")
            version.summary = "No changes in this version."
            return version

        prompt = f"""
        Given these changes for version {version.number}:

        {changes_text}

        Generate a concise, user-friendly summary that:
        1. Highlights the most important changes
        2. Mentions breaking changes if any
        3. Provides context about the impact
        4. Uses clear, non-technical language
        5. Is no more than 2-3 sentences

        Respond with ONLY the summary, nothing else.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.config.ai_model,
                messages=[
                    {"role": "system", "content": "You are a technical writer specializing in release notes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150,
                n=1,
            )

            if response.choices and response.choices[0].message.content:
                version.summary = response.choices[0].message.content.strip()
                logger.debug(f"Successfully generated summary for version {version.number}")
            else:
                logger.warning("OpenAI returned empty response for version summary")
                version.summary = "No significant changes in this version."

        except OpenAIError as e:
            logger.error(f"OpenAI API error generating summary: {e}")
            version.summary = "No significant changes in this version."
        except Exception as e:
            logger.error(f"Unexpected error generating summary: {e}")
            version.summary = "No significant changes in this version."

        return version

    def enhance_changes(self, changes: List[Change]) -> List[Change]:
        """Enhance multiple changes in batch."""
        if not self.is_available():
            logger.debug("Batch enhancement skipped: service not available")
            return changes
        return [self.enhance_change_description(change) for change in changes]

    def is_available(self) -> bool:
        """Check if AI service is available and configured."""
        if not self.client or not self.config.ai_enabled or not self.config.openai_api_key:
            return False
        try:
            self.client.models.list()
            return True
        except:
            return False
