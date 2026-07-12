"""
Path Validation Security Tests

Tests for validate_deliverables_path() to ensure:
- Directory traversal attacks are blocked
- Case-sensitivity bypasses are prevented
- Symlinks are resolved before validation
- Empty/whitespace paths are rejected
- Special paths (home, absolute) are rejected

Target: src/specify_cli/mission.py::validate_deliverables_path
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.mission import validate_deliverables_path

pytestmark = [pytest.mark.adversarial, pytest.mark.fast]


class TestDirectoryTraversal:
    """Test directory traversal attack prevention."""

    @pytest.mark.parametrize(
        "malicious_path,description",
        [
            ("../kitty-specs/", "Parent directory to kitty-specs"),
            ("../../../etc/passwd", "Deep traversal to system files"),
            ("./kitty-specs/", "Dot-slash to kitty-specs"),
            ("docs/../../kitty-specs/", "Nested traversal"),
            ("docs/../../../", "Traversal to root"),
            ("a/b/c/../../../../kitty-specs/", "Deep nested traversal"),
        ],
    )
    def test_traversal_rejected(self, malicious_path: str, description: str):
        """Directory traversal paths must be rejected."""
        is_valid, error = validate_deliverables_path(malicious_path)

        assert not is_valid, f"Path '{malicious_path}' should be rejected ({description})"
        assert error, f"Should provide error message for: {description}"
        # Error should mention traversal or invalid path
        assert any(keyword in error.lower() for keyword in ["traversal", "invalid", "not allowed", "kitty-specs"]), (
            f"Error message should explain rejection: {error}"
        )

    def test_valid_nested_path_allowed(self):
        """Valid nested paths without traversal should be allowed."""
        is_valid, error = validate_deliverables_path("docs/research/project/")

        assert is_valid, f"Valid nested path should be allowed: {error}"
        assert not error, "Should not have error for valid path"


class TestCaseSensitivityBypass:
    """Test case-sensitivity bypass prevention (macOS/Windows).

    The validator folds case in code (it does not rely on the host
    filesystem's case sensitivity), so these must be rejected
    unconditionally, on every platform.
    """

    @pytest.mark.parametrize(
        "case_variant",
        [
            "KITTY-SPECS/test/",
            "Kitty-Specs/test/",
            "KiTtY-SpEcS/test/",
            "kitty-SPECS/test/",
            "KITTY-specs/test/",
        ],
    )
    def test_case_variants_rejected(self, case_variant: str):
        """Case variants of kitty-specs should be rejected, regardless of filesystem."""
        is_valid, error = validate_deliverables_path(case_variant)

        assert not is_valid, f"Case variant '{case_variant}' should be rejected (in-code case-folding)"
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

    @pytest.mark.parametrize(
        "empty_path,description",
        [
            ("", "Empty string"),
            ("   ", "Whitespace only"),
            ("\t\t", "Tabs only"),
            ("\n", "Newline only"),
            ("///", "Slashes that normalize to empty"),
            ("/", "Single slash (root)"),
        ],
    )
    def test_empty_rejected(self, empty_path: str, description: str):
        """Empty/whitespace paths must be rejected with clear error."""
        is_valid, error = validate_deliverables_path(empty_path)

        assert not is_valid, f"'{description}' should be rejected"
        assert error, f"Should provide error message for: {description}"

    def test_path_with_only_dots_rejected(self):
        """Paths like '..' or '.' should be rejected."""
        for dot_path in ["..", ".", ".../", "../.."]:
            is_valid, error = validate_deliverables_path(dot_path)
            assert not is_valid, f"Dot path '{dot_path}' should be rejected"
            assert error, f"Should provide error message for: {dot_path}"

    def test_trailing_whitespace_handled(self):
        """Paths with trailing whitespace should be normalized and accepted.

        Positive case: 'docs/research/  ' has no traversal/absolute/reserved
        markers once the trailing whitespace is stripped, so it should be a
        valid path (not rejected, and not raise).
        """
        is_valid, error = validate_deliverables_path("docs/research/  ")

        assert is_valid, f"Trailing whitespace should be stripped and the path accepted: {error}"
        assert not error, "Should not have an error for a valid path with trailing whitespace"


class TestSymlinkAttacks:
    """Test symlink attack prevention.

    Symlinks can be used to bypass path checks:
    - Create symlink in allowed directory pointing to kitty-specs/
    - Path looks valid but resolves to forbidden location
    """

    @pytest.mark.requires_symlinks
    def test_symlink_to_kitty_specs_rejected(self, tmp_path: Path, symlink_factory, monkeypatch: pytest.MonkeyPatch):
        """Symlink pointing to kitty-specs/ should be rejected."""
        # The validator resolves relative to the current working directory,
        # so the project root for this test IS tmp_path.
        monkeypatch.chdir(tmp_path)

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

        is_valid, error = validate_deliverables_path(relative_path)

        assert not is_valid, "Symlink resolving into kitty-specs/ must be rejected"
        assert error, "Should provide error message for symlink-into-kitty-specs"

    @pytest.mark.requires_symlinks
    def test_symlink_escaping_project_root_rejected(
        self,
        tmp_path: Path,
        symlink_factory,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path_factory: pytest.TempPathFactory,
    ):
        """Symlink resolving outside the project root should be rejected."""
        # symlink_factory anchors links under this fixture's own tmp_path, so
        # tmp_path itself (not a subdirectory of it) must be the project root
        # for the symlink to actually land inside the chdir'd cwd.
        monkeypatch.chdir(tmp_path)

        # A directory in a genuinely unrelated tmp location (a sibling base
        # dir from tmp_path_factory, never a descendant of tmp_path).
        outside = tmp_path_factory.mktemp("outside-project-root")

        link = symlink_factory(outside, "docs/escape-link")
        if link is None:
            pytest.skip("Symlinks not supported on this platform")

        is_valid, error = validate_deliverables_path("docs/escape-link/payload/")

        assert not is_valid, "Symlink escaping the project root must be rejected"
        assert error, "Should provide error message for symlink-escaping-project-root"


class TestSpecialPaths:
    """Test special path pattern handling."""

    def test_home_directory_rejected(self):
        """Paths with ~ (home directory) should be rejected."""
        for home_path in ["~/research/", "~user/research/", "~/", "~"]:
            is_valid, error = validate_deliverables_path(home_path)
            assert not is_valid, f"Home path '{home_path}' should be rejected"
            assert error, f"Should provide error message for: {home_path}"

    def test_absolute_path_rejected(self):
        """Absolute paths should be rejected."""
        for abs_path in ["/nonexistent/research/", "/etc/passwd", "/home/user/", "C:\\Users\\test\\"]:
            is_valid, error = validate_deliverables_path(abs_path)
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
            assert not is_valid, "Null byte path should be rejected"
            assert error, "Should provide error message for null byte path"

    def test_project_root_rejected(self):
        """Bare './' (project root) should be rejected as ambiguous.

        Per ADR 7: "deliverables_path should not be at project root". This
        is a genuine malicious/ambiguous-input vector: it resolves to the
        project root itself, which is never a valid deliverables location.
        """
        is_valid, error = validate_deliverables_path("./")

        assert not is_valid, "Bare './' should be rejected as an ambiguous project-root reference"
        assert error, "Should provide error message for './'"


class TestUnicodePaths:
    """Test Unicode path handling."""

    def test_valid_unicode_accepted(self):
        """Valid Unicode paths should be accepted (positive case).

        None of these contain traversal, absolute, home, or reserved-path
        markers, so they must be treated the same as any other legitimate
        relative path.
        """
        valid_unicode = [
            "docs/研究/",
            "docs/исследование/",
            "docs/調査/",
            "docs/café/",
        ]
        for path in valid_unicode:
            is_valid, error = validate_deliverables_path(path)
            assert is_valid, f"Valid Unicode path should be accepted: {path} ({error})"
            assert not error, f"Should not have an error for valid Unicode path: {path}"

    def test_rtl_override_rejected(self):
        """Right-to-left override characters should be rejected.

        RTL override (U+202E) can be used to spoof paths so that
        'docs/<RTL-override>tset/' appears as 'docs/test/' visually.
        Built via chr() rather than embedding the raw override character in
        this source file, so the file itself stays visually unambiguous.
        """
        rtl_override = chr(0x202E)  # RIGHT-TO-LEFT OVERRIDE
        pop_directional = chr(0x202C)  # POP DIRECTIONAL FORMATTING
        rtl_paths = [
            f"docs/{rtl_override}/test/",
            f"docs/a{rtl_override}b{pop_directional}/",
        ]
        for rtl_path in rtl_paths:
            is_valid, error = validate_deliverables_path(rtl_path)
            assert not is_valid, f"RTL/bidi override path should be rejected: {rtl_path!r}"
            assert error, f"Should provide error message for: {rtl_path!r}"

    def test_unicode_normalization_consistent(self):
        """Unicode normalization should be consistent.

        NFC vs NFD can cause same-looking paths to differ:
        'café' (NFC) vs 'café' (NFD - e + combining acute)

        This is a consistency guard, not a rejection vector: neither form
        contains any forbidden marker, so both must be treated the same way
        (both valid) rather than diverging based on incidental byte layout.
        """
        nfc_path = "docs/caf" + chr(0x00E9) + "/"  # precomposed LATIN SMALL LETTER E WITH ACUTE
        nfd_path = "docs/cafe" + chr(0x0301) + "/"  # e + COMBINING ACUTE ACCENT (decomposed)

        nfc_valid, nfc_error = validate_deliverables_path(nfc_path)
        nfd_valid, nfd_error = validate_deliverables_path(nfd_path)

        assert nfc_valid, f"NFC unicode path should be valid: {nfc_error}"
        assert nfd_valid, f"NFD unicode path should be valid: {nfd_error}"
        assert nfc_valid == nfd_valid, "NFC and NFD variants must be handled consistently"
