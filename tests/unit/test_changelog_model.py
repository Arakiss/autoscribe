from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from autoscribe.models.changelog import Category, Change, Changelog, Version


def test_change_model():
    """Test Change model."""
    # Test valid change
    change = Change(
        description="Add new feature",
        commit_hash="abc123",
        commit_message="feat: add new feature",
        author="Test User",
        type="feat",
        scope="api",
        breaking=False,
        ai_enhanced=True,
        references=["#123", "#124"],
    )

    assert change.description == "Add new feature"
    assert change.commit_hash == "abc123"
    assert change.commit_message == "feat: add new feature"
    assert change.author == "Test User"
    assert change.type == "feat"
    assert change.scope == "api"
    assert change.breaking is False
    assert change.ai_enhanced is True
    assert change.references == ["#123", "#124"]

    # Test required fields
    with pytest.raises(ValidationError):
        Change()

    # Test optional fields
    change = Change(
        description="Fix bug",
        commit_hash="def456",
        commit_message="fix: resolve issue",
        author="Test User",
        type="fix",
    )

    assert change.scope is None
    assert change.breaking is False
    assert change.ai_enhanced is False
    assert change.references == []


def test_category_model():
    """Test Category model."""
    # Test valid category
    changes = [
        Change(
            description="Add feature A",
            commit_hash="abc123",
            commit_message="feat: add feature A",
            author="Test User",
            type="feat",
        ),
        Change(
            description="Add feature B",
            commit_hash="def456",
            commit_message="feat: add feature B",
            author="Test User",
            type="feat",
        ),
    ]

    category = Category(
        name="Added",
        changes=changes,
    )

    assert category.name == "Added"
    assert len(category.changes) == 2
    assert all(isinstance(change, Change) for change in category.changes)

    # Test required fields
    with pytest.raises(ValidationError):
        Category()

    # Test invalid category name
    with pytest.raises(ValidationError):
        Category(name="Invalid")

    # Test all valid categories
    valid_categories = ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]
    for name in valid_categories:
        category = Category(name=name)
        assert category.name == name
        assert category.changes == []


def test_version_model():
    """Test Version model."""
    # Test valid version
    now = datetime.now()
    categories = [
        Category(
            name="Added",
            changes=[
                Change(
                    description="Add feature",
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
                    description="Fix bug",
                    commit_hash="def456",
                    commit_message="fix: fix bug",
                    author="Test User",
                    type="fix",
                ),
            ],
        ),
    ]

    version = Version(
        number="1.0.0",
        date=now,
        categories=categories,
        summary="Version summary",
        breaking_changes=True,
        yanked=True,
        compare_url="https://github.com/user/repo/compare/v0.9.0...v1.0.0",
    )

    assert version.number == "1.0.0"
    assert version.date == now
    assert len(version.categories) == 2
    assert version.summary == "Version summary"
    assert version.breaking_changes is True
    assert version.yanked is True
    assert version.compare_url == "https://github.com/user/repo/compare/v0.9.0...v1.0.0"

    # Test required fields
    with pytest.raises(ValidationError):
        Version()

    # Test defaults
    version = Version(number="1.0.0")
    assert isinstance(version.date, datetime)
    assert version.categories == []
    assert version.summary is None
    assert version.breaking_changes is False
    assert version.yanked is False
    assert version.compare_url is None


def test_changelog_model():
    """Test Changelog model."""
    # Test valid changelog
    now = datetime.now()
    version = Version(
        number="1.0.0",
        date=now,
        categories=[
            Category(
                name="Added",
                changes=[
                    Change(
                        description="Add feature",
                        commit_hash="abc123",
                        commit_message="feat: add feature",
                        author="Test User",
                        type="feat",
                    ),
                ],
            ),
        ],
    )

    changelog = Changelog(
        versions=[version],
        title="Test Changelog",
        description="Test description",
        last_updated=now,
    )

    assert len(changelog.versions) == 1
    assert changelog.title == "Test Changelog"
    assert changelog.description == "Test description"
    assert changelog.last_updated == now

    # Test defaults
    changelog = Changelog()
    assert changelog.versions == []
    assert changelog.title == "Changelog"
    assert "Keep a Changelog" in changelog.description
    assert "Semantic Versioning" in changelog.description
    assert isinstance(changelog.last_updated, datetime)


def test_changelog_methods():
    """Test Changelog methods."""
    changelog = Changelog()
    now = datetime.now()

    # Test add_version
    version1 = Version(number="1.0.0", date=now - timedelta(days=1))
    version2 = Version(number="1.1.0", date=now)

    changelog.add_version(version1)
    assert len(changelog.versions) == 1
    assert changelog.versions[0].number == "1.0.0"

    changelog.add_version(version2)
    assert len(changelog.versions) == 2
    assert changelog.versions[0].number == "1.1.0"  # Latest version first

    # Test get_version
    assert changelog.get_version("1.0.0") == version1
    assert changelog.get_version("1.1.0") == version2
    assert changelog.get_version("2.0.0") is None

    # Test get_latest_version
    assert changelog.get_latest_version() == version2

    # Test get_unreleased_changes
    unreleased = Version(number="Unreleased", date=now)
    changelog.add_version(unreleased)
    assert changelog.get_unreleased_changes() == unreleased

    # Test empty changelog
    empty_changelog = Changelog()
    assert empty_changelog.get_latest_version() is None
    assert empty_changelog.get_unreleased_changes() is None
