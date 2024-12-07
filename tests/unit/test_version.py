import pytest

from autoscribe.utils.version import Version, VersionType, extract_version, suggest_version_bump


def test_version_parsing():
    """Test version string parsing."""
    # Test basic version
    v = Version.parse("1.2.3")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease is None
    assert v.build is None

    # Test version with prerelease
    v = Version.parse("1.2.3-alpha.1")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease == "alpha.1"
    assert v.build is None

    # Test version with build metadata
    v = Version.parse("1.2.3+build.123")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease is None
    assert v.build == "build.123"

    # Test full version
    v = Version.parse("1.2.3-beta.2+build.123")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3
    assert v.prerelease == "beta.2"
    assert v.build == "build.123"


def test_invalid_version_parsing():
    """Test parsing invalid version strings."""
    invalid_versions = [
        "",
        "1",
        "1.2",
        "1.2.3.4",
        "v1.2.3",
        "1.2.3-",
        "1.2.3+",
        "1.2.a",
    ]

    for version in invalid_versions:
        with pytest.raises(ValueError):
            Version.parse(version)


def test_version_bumping():
    """Test version bumping."""
    v = Version.parse("1.2.3")

    # Test major bump
    v_major = v.bump(VersionType.MAJOR)
    assert str(v_major) == "2.0.0"

    # Test minor bump
    v_minor = v.bump(VersionType.MINOR)
    assert str(v_minor) == "1.3.0"

    # Test patch bump
    v_patch = v.bump(VersionType.PATCH)
    assert str(v_patch) == "1.2.4"


def test_version_comparison():
    """Test version comparison."""
    v1 = Version.parse("1.2.3")
    v2 = Version.parse("2.0.0")
    v3 = Version.parse("1.3.0")
    v4 = Version.parse("1.2.4")

    assert v1 < v2
    assert v1 < v3
    assert v1 < v4
    assert not v2 < v1
    assert not v3 < v1
    assert not v4 < v1


def test_version_string_representation():
    """Test version string representation."""
    versions = [
        ("1.2.3", "1.2.3"),
        ("1.2.3-alpha.1", "1.2.3-alpha.1"),
        ("1.2.3+build.123", "1.2.3+build.123"),
        ("1.2.3-beta.2+build.123", "1.2.3-beta.2+build.123"),
    ]

    for input_version, expected_output in versions:
        v = Version.parse(input_version)
        assert str(v) == expected_output


def test_extract_version():
    """Test version extraction from content."""
    content = '''
    [tool.poetry]
    name = "test"
    version = "1.2.3"
    description = "Test package"
    '''

    pattern = r'version = "([^"]+)"'
    version = extract_version(content, pattern)
    assert version == "1.2.3"

    # Test with non-matching pattern
    pattern = r'version = \[([^]]+)\]'
    version = extract_version(content, pattern)
    assert version is None


def test_suggest_version_bump():
    """Test version bump suggestions."""
    # Test breaking changes
    assert suggest_version_bump(breaking_changes=True, has_new_features=False) == VersionType.MAJOR
    assert suggest_version_bump(breaking_changes=True, has_new_features=True) == VersionType.MAJOR

    # Test new features
    assert suggest_version_bump(breaking_changes=False, has_new_features=True) == VersionType.MINOR

    # Test bug fixes
    assert suggest_version_bump(breaking_changes=False, has_new_features=False) == VersionType.PATCH
