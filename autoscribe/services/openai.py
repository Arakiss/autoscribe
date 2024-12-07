from typing import List, Optional

from openai import OpenAI
from pydantic import BaseModel

from ..models.changelog import Change, Version
from ..models.config import AutoScribeConfig


class AIService:
    """Service for AI-powered changelog enhancements."""

    def __init__(self, config: AutoScribeConfig):
        """Initialize the AI service."""
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key) if config.ai_enabled else None

    def enhance_change_description(self, change: Change) -> Change:
        """Enhance a change description using AI."""
        if not self.config.ai_enabled or not self.client:
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

        except Exception as e:
            # Log error but keep original description
            print(f"Error enhancing change description: {e}")

        return change

    def generate_version_summary(self, version: Version) -> Version:
        """Generate a summary for a version using AI."""
        if not self.config.ai_enabled or not self.client:
            return version

        changes_text = "\n".join(
            f"- {change.description} ({change.type})"
            for category in version.categories
            for change in category.changes
        )

        if not changes_text:
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
            else:
                version.summary = "No significant changes in this version."

        except Exception as e:
            print(f"Error generating version summary: {e}")
            version.summary = "No significant changes in this version."

        return version

    def enhance_changes(self, changes: List[Change]) -> List[Change]:
        """Enhance multiple changes in batch."""
        return [self.enhance_change_description(change) for change in changes]

    def is_available(self) -> bool:
        """Check if AI service is available and configured."""
        return bool(self.config.ai_enabled and self.client and self.config.openai_api_key)
