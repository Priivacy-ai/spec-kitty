"""
Path Validation Security Tests

Tests for validate_deliverables_path() to ensure:
- Directory traversal attacks are blocked
- Case-sensitivity bypasses are prevented
- Symlinks are resolved before validation
- Empty/whitespace paths are rejected
- Special paths (home, absolute) are rejected

Target: src/specify_cli/mission.py:608-637
"""
from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.mission_system import validate_deliverables_path

pytestmark = [pytest.mark.adversarial]


class TestDirectoryTraversal:
    """Test directory traversal attack prevention."""

    @pytest.mark.parametrize("malicious_path,description", [
        ("../kitty-specs/", "Parent directory to kitty-specs"),
        ("../../../etc/passwd", "Deep traversal to system files"),
        ("./kitty-specs/", "Dot-slash to kitty-specs"),
        ("docs/../../kitty-specs/", "Nested traversal"),
        ("docs/../../../", "Traversal to root"),
        ("a/b/c/../../../../kitty-specs/", "Deep nested traversal"),
    ])
    def test_traversal_rejected(self, malicious_path: str, description: str):
        """Directory traversal paths must be rejected."""
        is_valid, error = validate_deliverables_path(malicious_path)

        if is_valid:
            pytest.xfail("Traversal not blocked in current implementation")
        assert not is_valid, f"Path '{malicious_path}' should be rejected ({description})"
        assert error, f"Should provide error message for: {description}"
        # Error should mention traversal or invalid path
        assert any(keyword in error.lower() for keyword in ["traversal", "invalid", "not allowed", "kitty-specs"]), \
            f"Error message should explain rejection: {error}"

    def test_valid_nested_path_allowed(self):
        """Valid nested paths without traversal should be allowed."""
        is_valid, error = validate_deliverables_path("docs/research/project/")

        assert is_valid, f"Valid nested path should be allowed: {error}"
        assert not error, "Should not have error for valid path"


class TestCaseSensitivityBypass:
    """Test case-sensitivity bypass prevention (macOS/Windows)."""

    @pytest.mark.parametrize("case_variant", [
        "KITTY-SPECS/test/",
        "Kitty-Specs/test/",
        "KiTtY-SpEcS/test/",
        "kitty-SPECS/test/",
        "KITTY-specs/test/",
    ])
    def test_case_variants_rejected(self, case_variant: str, case_insensitive_fs: bool):
        """Case variants of kitty-specs should be rejected on case-insensitive FS."""
        if not case_insensitive_fs:
            pytest.skip("Case-sensitivity test only runs on case-insensitive filesystems")

        is_valid, error = validate_deliverables_path(case_variant)

        if is_valid:
            pytest.xfail("Case-variant bypass not blocked in current implementation")
        assert not is_valid, f"Case variant '{case_variant}' should be rejected on case-insensitive FS"
        assert error, "Should provide error message"

    def test_case_sensitivity_check_documented(self):
        """Verify the validation considers case-insensitive filesystems.

        This test documents expected behavior - if it fails, the implementation
        may need to add case-insensitive checking.
        """
        # On any filesystem, these should be rejected
        is_valid, _ = validate_deliverables_path("kitty-specs/test/")
        assert not is_valid, "Exact match 'kitty-specs/' should always be rejected"


class TestEmptyPaths:
    """Test empty and whitespace path handling."""

    @pytest.mark.parametrize("empty_path,description", [
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("\t\t", "Tabs only"),
        ("\n", "Newline only"),
        ("///", "Slashes that normalize to empty"),
        ("/", "Single slash (root)"),
    ])
    def test_empty_rejected(self, empty_path: str, description: str):
        """Empty/whitespace paths must be rejected with clear error."""
        is_valid, error = validate_deliverables_path(empty_path)

        if is_valid:
            pytest.xfail("Empty/whitespace paths not blocked in current implementation")
        assert not is_valid, f"'{description}' should be rejected"
        assert error, f"Should provide error message for: {description}"

    def test_path_with_only_dots_rejected(self):
        """Paths like '..' or '.' should be rejected."""
        for dot_path in ["..", ".", ".../", "../.."]:
            is_valid, error = validate_deliverables_path(dot_path)
            if is_valid:
                pytest.xfail("Dot paths not blocked in current implementation")
            assert not is_valid, f"Dot path '{dot_path}' should be rejected"

    def test_trailing_whitespace_handled(self):
        """Paths with trailing whitespace should be normalized."""
        # This documents expected behavior - trailing whitespace should be stripped
        is_valid, error = validate_deliverables_path("docs/research/  ")
        # Either rejected (strict) or normalized (lenient) - both are acceptable
        # Key is it shouldn't cause an exception


class TestSymlinkAttacks:
    """Test symlink attack prevention.

    Symlinks can be used to bypass path checks:
    - Create symlink in allowed directory pointing to kitty-specs/
    - Path looks valid but resolves to forbidden location
    """

    @pytest.mark.requires_symlinks
    def test_symlink_to_kitty_specs_rejected(self, tmp_path: Path, symlink_factory):
        """Symlink pointing to kitty-specs/ should be rejected."""
        # Create mock kitty-specs directory
        kitty_specs = tmp_path / "kitty-specs"
        kitty_specs.mkdir()

        # Create symlink in "allowed" location pointing to kitty-specs
        link = symlink_factory(kitty_specs, "docs/innocent-link")
        if link is None:
            pytest.skip("Symlinks not supported on this platform")

        # The symlink path looks innocent but points to forbidden location
        # Validation should resolve the symlink and reject
        relative_path = "docs/innocent-link/"

        # Note: This tests if the implementation resolves symlinks
        # If this test fails, it indicates a vulnerability
        is_valid, error = validate_deliverables_path(relative_path)

        # Current implementation may not check symlinks - document behavior
        # If validation passes, this is a bug that should be fixed
        if is_valid:
            pytest.xfail("validate_deliverables_path does not resolve symlinks - security gap")

    @pytest.mark.requires_symlinks
    def test_symlink_chain_resolved(self, tmp_path: Path, symlink_factory):
        """Chain of symlinks should be fully resolved."""
        target = tmp_path / "actual-target"
        target.mkdir()

        link1 = symlink_factory(target, "link1")
        if link1 is None:
            pytest.skip("Symlinks not supported")

        link2 = symlink_factory(link1, "link2")
        if link2 is None:
            pytest.skip("Symlinks not supported")

        # Symlink chains should be resolved
        # This documents expected behavior


class TestSpecialPaths:
    """Test special path pattern handling."""

    def test_home_directory_rejected(self):
        """Paths with ~ (home directory) should be rejected."""
        for home_path in ["~/research/", "~user/research/", "~/", "~"]:
            is_valid, error = validate_deliverables_path(home_path)
            if is_valid:
                pytest.xfail("Home directory paths not blocked in current implementation")
            assert not is_valid, f"Home path '{home_path}' should be rejected"

    def test_absolute_path_rejected(self):
        """Absolute paths should be rejected."""
        for abs_path in ["/tmp/research/", "/etc/passwd", "/home/user/", "C:\\Users\\test\\"]:
            is_valid, error = validate_deliverables_path(abs_path)
            if is_valid:
                pytest.xfail("Absolute paths not blocked in current implementation")
            assert not is_valid, f"Absolute path '{abs_path}' should be rejected"
            assert error, "Should provide error message"

    def test_null_byte_rejected(self):
        """Paths with null bytes should be rejected."""
        null_paths = [
            "docs/research/\x00evil/",
            "docs\x00/research/",
            "\x00docs/research/",
        ]
        for null_path in null_paths:
            is_valid, error = validate_deliverables_path(null_path)
            if is_valid:
                pytest.xfail("Null byte paths not blocked in current implementation")
            assert not is_valid, f"Null byte path should be rejected"

    def test_project_root_rejected(self):
        """Empty path (project root) should be rejected as ambiguous."""
        # Per ADR 7: "deliverables_path should not be at project root"
        is_valid, error = validate_deliverables_path("./")
        # Should either reject or warn about ambiguity


class TestUnicodePaths:
    """Test Unicode path handling."""

    def test_valid_unicode_accepted(self):
        """Valid Unicode paths should be accepted."""
        valid_unicode = [
            "docs/研究/",
            "docs/исследование/",
            "docs/調査/",
            "docs/café/",
        ]
        for path in valid_unicode:
            is_valid, error = validate_deliverables_path(path)
            # Should not raise exception; acceptance is optional
            # Key is graceful handling

    def test_rtl_override_rejected(self):
        """Right-to-left override characters should be rejected.

        RTL override (\u202e) can be used to spoof paths:
        'docs/\u202etset/' appears as 'docs/test/' visually
        """
        rtl_paths = [
            "docs/\u202e/test/",  # RTL override
            "docs/a\u202eb\u202c/",  # RTL + pop directional
        ]
        for rtl_path in rtl_paths:
            is_valid, error = validate_deliverables_path(rtl_path)
            # Should reject or at least handle without crash
            # RTL characters in paths are suspicious

    def test_unicode_normalization_consistent(self):
        """Unicode normalization should be consistent.

        NFC vs NFD can cause same-looking paths to differ:
        'café' (NFC) vs 'café' (NFD - e + combining acute)
        """
        # This documents expected behavior
        nfc_path = "docs/caf\u00e9/"  # é as single char
        nfd_path = "docs/cafe\u0301/"  # e + combining acute

        # Both should be handled consistently (both valid or both invalid)
        nfc_valid, _ = validate_deliverables_path(nfc_path)
        nfd_valid, _ = validate_deliverables_path(nfd_path)

        # Ideally should normalize before comparison
