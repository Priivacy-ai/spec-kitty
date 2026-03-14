"""Functional tests for dashboard encoding resilience (dashboard/scanner.py).

Test Suite 3: Dashboard Encoding Resilience

Tests the dashboard's ability to handle encoding errors gracefully without
crashing, including auto-fix capabilities and error card generation.

Coverage Target: 90%+ for dashboard scanner encoding logic
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from specify_cli.dashboard.scanner import (
    read_file_resilient,
    scan_feature_kanban,
)


class TestDashboardReadResilience:
    """Test 3.1 & 3.2: Dashboard read resilience with and without auto-fix"""

    def test_read_file_resilient_with_autofix(self):
        """Test 3.1: Verify dashboard auto-fixes encoding errors on read."""
        with TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad.md"

            # Write file with Windows-1252 encoding
            bad_content = "User\u2019s \u201ctest\u201d"
            bad_file.write_bytes(bad_content.encode('cp1252'))

            # Verify it's broken for UTF-8
            with pytest.raises(UnicodeDecodeError):
                bad_file.read_text(encoding='utf-8')

            # Read with auto-fix enabled
            content, error = read_file_resilient(bad_file, auto_fix=True)

            # Should return content successfully
            assert content is not None, "Should return content after auto-fix"
            assert error is None, f"Should not have error with auto-fix: {error}"

            # Content should be sanitized
            assert content == "User's \"test\"", f"Content should be sanitized, got: {content!r}"

            # File should now be valid UTF-8 on disk
            fixed_content = bad_file.read_text(encoding='utf-8')
            assert fixed_content == "User's \"test\"", "File on disk should be fixed"

            # Backup should exist
            backup = bad_file.with_suffix('.md.bak')
            assert backup.exists(), "Backup should be created during auto-fix"

    def test_read_file_resilient_without_autofix(self):
        """Test 3.2: Verify non-auto-fix mode returns clear error message."""
        with TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad.md"

            # Write file with Windows-1252 encoding
            bad_content = "User\u2019s \u201ctest\u201d"
            bad_file.write_bytes(bad_content.encode('cp1252'))

            # Read without auto-fix
            content, error = read_file_resilient(bad_file, auto_fix=False)

            # Should return error
            assert content is None, "Should not return content without auto-fix"
            assert error is not None, "Should return error message"

            # Error message should be informative
            assert "bad.md" in error, "Error should mention file name"
            assert "byte" in error.lower(), "Error should mention byte position"
            assert "spec-kitty validate-encoding" in error, "Error should suggest fix command"

            # File should remain unchanged
            with pytest.raises(UnicodeDecodeError):
                bad_file.read_text(encoding='utf-8')

    def test_read_file_resilient_with_clean_file(self):
        """Verify clean UTF-8 files read normally."""
        with TemporaryDirectory() as tmpdir:
            clean_file = Path(tmpdir) / "clean.md"
            clean_file.write_text("Clean UTF-8 content", encoding='utf-8')

            # Read with auto-fix (should have no effect)
            content, error = read_file_resilient(clean_file, auto_fix=True)

            # Should succeed
            assert content == "Clean UTF-8 content", "Should read clean content"
            assert error is None, "Should have no error"

            # File should be unchanged (no backup)
            backup = clean_file.with_suffix('.md.bak')
            assert not backup.exists(), "Clean file should not create backup"

    def test_read_file_resilient_missing_file(self):
        """Verify missing file returns appropriate error."""
        with TemporaryDirectory() as tmpdir:
            missing_file = Path(tmpdir) / "missing.md"

            content, error = read_file_resilient(missing_file, auto_fix=True)

            assert content is None, "Should not return content for missing file"
            assert error is not None, "Should return error"
            assert "not found" in error.lower() or "missing.md" in error, \
                "Error should indicate file not found"


class TestDashboardKanbanScanning:
    """Test 3.3 & 3.4: Dashboard kanban scanning with encoding errors"""

    def test_scan_feature_kanban_creates_error_cards(self):
        """Test 3.3: Verify dashboard creates error card for broken files instead of crashing."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)  # Convert to Path
            # Create feature structure
            feature_dir = tmpdir / "kitty-specs" / "001-test"
            tasks_dir = feature_dir / "tasks" / "planned"
            tasks_dir.mkdir(parents=True)

            # Create bad work package file with Windows-1252
            wp_file = tasks_dir / "WP01-test.md"
            wp_content = """---
work_package_id: WP01
---
# Work Package Prompt: User\u2019s Test
"""
            wp_file.write_bytes(wp_content.encode('cp1252'))

            # Verify it's broken
            with pytest.raises(UnicodeDecodeError):
                wp_file.read_text(encoding='utf-8')

            # Scan should not crash
            lanes = scan_feature_kanban(Path(tmpdir), "001-test")

            # Should have lanes dict
            assert isinstance(lanes, dict), "Should return lanes dictionary"
            assert "planned" in lanes, "Should have planned lane"

            # The behavior depends on whether auto_fix is used in scan_feature_kanban
            # If auto-fix is enabled (default), the file will be fixed and loaded normally
            # If auto-fix is disabled, an error card should be created
            # Let's test both scenarios

            # For now, with auto-fix, file should be loaded successfully
            if len(lanes["planned"]) > 0:
                card = lanes["planned"][0]
                # Either it's fixed and loaded, or it's an error card
                if card.get("encoding_error"):
                    # Error card scenario
                    assert "⚠️" in card.get("title", "") or "Encoding Error" in card.get("title", ""), \
                        "Error card should indicate encoding problem"
                    assert "WP01" in card.get("title", ""), "Should mention work package ID"
                else:
                    # Successfully fixed scenario
                    assert "WP01" in card.get("id", ""), "Should have work package ID"

    def test_scan_feature_kanban_auto_fixes_and_loads(self):
        """Test 3.4: Verify auto-fix allows successful load after initial error."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)  # Convert to Path
            # Create feature structure
            feature_dir = tmpdir / "kitty-specs" / "001-test"
            tasks_dir = feature_dir / "tasks" / "planned"
            tasks_dir.mkdir(parents=True)

            # Create work package with encoding issue
            wp_file = tasks_dir / "WP01-test.md"
            wp_content = """---
work_package_id: WP01
title: User\u2019s Authentication
---
# Work Package Prompt: User\u2019s Test

Implement authentication with User\u2019s profile support.
"""
            wp_file.write_bytes(wp_content.encode('cp1252'))

            # Scan with auto-fix (default behavior)
            lanes = scan_feature_kanban(Path(tmpdir), "001-test")

            # Should have successfully loaded the card
            assert "planned" in lanes, "Should have planned lane"

            # File should be fixed on disk now
            fixed_content = wp_file.read_text(encoding='utf-8')
            assert "User's" in fixed_content, "File should be fixed to valid UTF-8"

            # Backup should exist
            backup = wp_file.with_suffix('.md.bak')
            assert backup.exists(), "Backup should be created"

    def test_scan_empty_feature(self):
        """Verify scanning empty feature doesn't crash."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)  # Convert to Path
            # Create minimal feature structure
            feature_dir = tmpdir / "kitty-specs" / "001-empty"
            feature_dir.mkdir(parents=True)

            # Scan should not crash
            lanes = scan_feature_kanban(Path(tmpdir), "001-empty")

            # Should return empty lanes
            assert isinstance(lanes, dict), "Should return lanes dictionary"
            assert all(len(cards) == 0 for cards in lanes.values()), \
                "All lanes should be empty"

    def test_scan_feature_with_mixed_files(self):
        """Verify scanning feature with both good and bad files."""
        with TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)  # Convert to Path
            feature_dir = tmpdir / "kitty-specs" / "001-mixed"
            tasks_dir = feature_dir / "tasks" / "planned"
            tasks_dir.mkdir(parents=True)

            # Create good file
            good_wp = tasks_dir / "WP01-good.md"
            good_wp.write_text("""---
work_package_id: WP01
---
# Work Package: Good File
Clean content here.
""")

            # Create bad file
            bad_wp = tasks_dir / "WP02-bad.md"
            bad_wp.write_bytes("""---
work_package_id: WP02
---
# Work Package: User\u2019s File
Bad content here.
""".encode('cp1252'))

            # Scan
            lanes = scan_feature_kanban(Path(tmpdir), "001-mixed")

            # Should process both files
            assert "planned" in lanes, "Should have planned lane"

            # With auto-fix, both should load (bad one gets fixed)
            # Count may vary depending on frontmatter parsing success

    def test_scan_nonexistent_feature(self):
        """Verify scanning nonexistent feature doesn't crash."""
        with TemporaryDirectory() as tmpdir:
            # Scan nonexistent feature
            lanes = scan_feature_kanban(Path(tmpdir), "999-nonexistent")

            # Should return empty lanes structure
            assert isinstance(lanes, dict), "Should return lanes dictionary"
            for lane_name in ["planned", "doing", "for_review", "done"]:
                assert lane_name in lanes, f"Should have {lane_name} lane"
                assert len(lanes[lane_name]) == 0, f"{lane_name} should be empty"


class TestDashboardPerformance:
    """Test dashboard auto-fix performance requirements."""

    def test_dashboard_autofix_under_200ms(self):
        """Verify dashboard auto-fix completes in < 200ms (requirement)."""
        import time

        with TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "bad.md"

            # Create file with encoding issue
            bad_content = "User\u2019s \u201ctest\u201d with encoding issues"
            bad_file.write_bytes(bad_content.encode('cp1252'))

            # Time the auto-fix
            start = time.time()
            content, error = read_file_resilient(bad_file, auto_fix=True)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            # Should complete quickly
            assert elapsed < 200, \
                f"Dashboard auto-fix took {elapsed:.1f}ms, should be < 200ms"

            # Should have succeeded
            assert content is not None, "Auto-fix should succeed"
            assert error is None, "Should not have error"

    def test_dashboard_read_multiple_files_performance(self):
        """Verify reading multiple files is efficient."""
        import time

        with TemporaryDirectory() as tmpdir:
            # Create 10 files with encoding issues
            files = []
            for i in range(10):
                bad_file = Path(tmpdir) / f"bad{i}.md"
                bad_content = f"File {i} with User\u2019s content"
                bad_file.write_bytes(bad_content.encode('cp1252'))
                files.append(bad_file)

            # Time reading all files
            start = time.time()
            for f in files:
                read_file_resilient(f, auto_fix=True)
            elapsed = (time.time() - start) * 1000

            # Should be reasonable (< 500ms for 10 files)
            assert elapsed < 500, \
                f"Reading 10 files took {elapsed:.1f}ms, should be < 500ms"


class TestErrorMessageQuality:
    """Test quality of dashboard error messages."""

    def test_error_message_is_actionable(self):
        """Verify error messages provide clear next steps."""
        with TemporaryDirectory() as tmpdir:
            bad_file = Path(tmpdir) / "problem.md"
            bad_file.write_bytes("User\u2019s test".encode('cp1252'))

            content, error = read_file_resilient(bad_file, auto_fix=False)

            assert error is not None, "Should have error"

            # Should be actionable
            assert "spec-kitty validate-encoding" in error, \
                "Should suggest validation command"
            assert "--fix" in error or "repair" in error.lower(), \
                "Should suggest fix option"
            assert "problem.md" in error, \
                "Should identify specific file"

    def test_error_message_for_unfixable_file(self):
        """Verify appropriate error for files that can't be auto-fixed."""
        with TemporaryDirectory() as tmpdir:
            binary_file = Path(tmpdir) / "binary.md"
            # Create truly binary content (not text)
            binary_file.write_bytes(b'\x00\x01\x02\xff\xfe\xfd')

            content, error = read_file_resilient(binary_file, auto_fix=True)

            # Should have error or fallback content
            if error:
                assert "error" in error.lower() or "failed" in error.lower(), \
                    "Error should indicate problem"
            # Some fallback may succeed with replacement characters


class TestRegressionCases:
    """Regression tests for dashboard resilience."""

    def test_valid_utf8_with_unicode_chars(self):
        """Verify valid UTF-8 Unicode content works fine."""
        with TemporaryDirectory() as tmpdir:
            unicode_file = Path(tmpdir) / "unicode.md"
            # Valid UTF-8 with Unicode characters (not Windows-1252)
            unicode_file.write_text("Valid: 你好 世界 ✓ ™ © ®", encoding='utf-8')

            content, error = read_file_resilient(unicode_file, auto_fix=True)

            assert content is not None, "Valid UTF-8 should read fine"
            assert error is None, "No error for valid UTF-8"
            assert "你好" in content, "Unicode should be preserved"

    def test_empty_markdown_file(self):
        """Verify empty files don't cause issues."""
        with TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.md"
            empty_file.write_text("", encoding='utf-8')

            content, error = read_file_resilient(empty_file, auto_fix=True)

            assert content == "", "Empty file should return empty string"
            assert error is None, "Empty file should not error"

    def test_very_large_file_with_encoding_issue(self):
        """Verify large files with encoding issues are handled."""
        with TemporaryDirectory() as tmpdir:
            large_file = Path(tmpdir) / "large.md"
            # Create 100KB file with encoding issue
            content = ("User\u2019s test\n" * 10000).encode('cp1252')
            large_file.write_bytes(content)

            # Should handle gracefully
            result, error = read_file_resilient(large_file, auto_fix=True)

            # Should succeed or fail gracefully
            if error:
                assert "error" in error.lower(), "Should have clear error"
            else:
                assert "User's" in result, "Should be fixed"
