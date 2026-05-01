"""Tests for the stale-assertion analyzer (WP01).

Covers: FR-001, FR-002, FR-003, FR-004, FR-022, NFR-001, NFR-002.

Uses synthetic git repositories built with tmp_path + subprocess.run(["git", "init"])
for deterministic, hermetic testing — zero network access.
"""

from __future__ import annotations

import importlib
import subprocess
import textwrap
import time
from pathlib import Path
from unittest import mock

import pytest

from specify_cli.post_merge import StaleAssertionReport, run_check
from specify_cli.post_merge.stale_assertions import (
    FP_CEILING,
    _scan_test_file,
)


# ---------------------------------------------------------------------------
# Synthetic git repo fixture helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> str:
    """Run a git command in cwd and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr}")
    return result.stdout.strip()


def _setup_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with user config."""
    _git(["init"], cwd=tmp_path)
    _git(["config", "user.email", "test@example.com"], cwd=tmp_path)
    _git(["config", "user.name", "Test User"], cwd=tmp_path)
    return tmp_path


def _commit(repo: Path, message: str = "commit") -> str:
    """Stage all changes and create a commit, returning the commit SHA."""
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-m", message, "--allow-empty"], cwd=repo)
    return _git(["rev-parse", "HEAD"], cwd=repo)


def _write(repo: Path, rel_path: str, content: str) -> Path:
    """Write file content to repo/rel_path, creating parent dirs."""
    path = repo / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))
    return path


# ---------------------------------------------------------------------------
# FR-001 + FR-003: renamed function flagged with high confidence
# ---------------------------------------------------------------------------


class TestRenamedFunctionFlaggedHighConfidence:
    """FR-001: structured report; FR-003: high confidence for renamed function."""

    def test_renamed_function_flagged_high_confidence(self, tmp_path: Path) -> None:
        repo = _setup_repo(tmp_path)

        # Base commit: function old_compute exists
        _write(
            repo,
            "src/math_utils.py",
            """\
            def old_compute(x):
                return x * 2
        """,
        )
        _write(
            repo,
            "tests/test_math_utils.py",
            """\
            from math_utils import old_compute

            def test_compute():
                assert old_compute(3) == 6
        """,
        )
        base_sha = _commit(repo, "base")

        # Head commit: function renamed to new_compute
        _write(
            repo,
            "src/math_utils.py",
            """\
            def new_compute(x):
                return x * 2
        """,
        )
        head_sha = _commit(repo, "rename")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        assert isinstance(report, StaleAssertionReport)
        assert len(report.findings) >= 1, f"Expected at least 1 finding, got {len(report.findings)}"

        high_findings = [f for f in report.findings if f.confidence == "high"]
        assert len(high_findings) >= 1, f"Expected at least one high-confidence finding, got: {report.findings}"

        symbol_names = {f.changed_symbol for f in high_findings}
        assert "old_compute" in symbol_names, f"Expected 'old_compute' in high-confidence findings, got: {symbol_names}"

    def test_report_has_required_fields(self, tmp_path: Path) -> None:
        """FR-001: report contains base_ref, head_ref, repo_root, findings, elapsed_seconds, etc."""
        repo = _setup_repo(tmp_path)
        _write(repo, "src/mod.py", "def foo(): pass\n")
        _write(repo, "tests/__init__.py", "")
        base_sha = _commit(repo, "base")

        _write(repo, "src/mod.py", "def bar(): pass\n")
        head_sha = _commit(repo, "rename foo -> bar")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        assert report.base_ref == base_sha
        assert report.head_ref == head_sha
        assert report.repo_root == repo
        assert isinstance(report.findings, list)
        assert isinstance(report.elapsed_seconds, float)
        assert report.elapsed_seconds >= 0.0
        assert isinstance(report.files_scanned, int)
        assert report.files_scanned >= 0
        assert isinstance(report.findings_per_100_loc, float)


# ---------------------------------------------------------------------------
# FR-001 + FR-002: changed string literal flagged with low confidence
# ---------------------------------------------------------------------------


class TestChangedStringLiteralFlaggedLowConfidence:
    """FR-002: AST-only scan; changed literal in assertion position → low confidence."""

    def test_changed_string_literal_flagged_low_confidence(self, tmp_path: Path) -> None:
        repo = _setup_repo(tmp_path)

        _write(
            repo,
            "src/messages.py",
            """\
            ERROR_MSG = "old error message"
        """,
        )
        _write(
            repo,
            "tests/test_messages.py",
            """\
            def test_error_message():
                assert result == "old error message"
        """,
        )
        base_sha = _commit(repo, "base")

        _write(
            repo,
            "src/messages.py",
            """\
            ERROR_MSG = "new error message"
        """,
        )
        head_sha = _commit(repo, "update message")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        low_findings = [f for f in report.findings if f.confidence == "low"]
        assert len(low_findings) >= 1, f"Expected at least one low-confidence finding for changed literal, got: {report.findings}"

        symbol_names = {f.changed_symbol for f in low_findings}
        assert "old error message" in symbol_names


# ---------------------------------------------------------------------------
# FR-002 worked examples: comments and inert uses must NOT be flagged
# ---------------------------------------------------------------------------


class TestFR002WorkedExamples:
    """FR-002: Only AST assertion-bearing positions are scanned — no raw text."""

    def test_string_literal_in_comment_not_flagged(self, tmp_path: Path) -> None:
        """A changed literal that appears only in a comment must NOT produce a finding."""
        repo = _setup_repo(tmp_path)

        _write(
            repo,
            "src/api.py",
            """\
            def get_endpoint():
                return "/old/path"
        """,
        )
        # The test file mentions "/old/path" only in a comment.
        _write(
            repo,
            "tests/test_api.py",
            """\
            def test_endpoint():
                # TODO: was checking for "/old/path" here
                assert True
        """,
        )
        base_sha = _commit(repo, "base")

        _write(
            repo,
            "src/api.py",
            """\
            def get_endpoint():
                return "/new/path"
        """,
        )
        head_sha = _commit(repo, "rename endpoint")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        # The string "/old/path" only appears in a comment → no finding.
        flagged_symbols = {f.changed_symbol for f in report.findings}
        assert "/old/path" not in flagged_symbols, "Literal in comment must NOT produce a finding (FR-002)"

    def test_unchanged_use_of_string_not_flagged(self, tmp_path: Path) -> None:
        """A literal that was NOT changed should not produce findings."""
        repo = _setup_repo(tmp_path)

        _write(
            repo,
            "src/config.py",
            """\
            OLD_KEY = "old_key"
            STABLE_KEY = "stable_key"
        """,
        )
        _write(
            repo,
            "tests/test_config.py",
            """\
            def test_stable():
                assert result == "stable_key"
        """,
        )
        base_sha = _commit(repo, "base")

        # Only OLD_KEY changes; STABLE_KEY stays the same.
        _write(
            repo,
            "src/config.py",
            """\
            NEW_KEY = "new_key"
            STABLE_KEY = "stable_key"
        """,
        )
        head_sha = _commit(repo, "rename OLD_KEY to NEW_KEY")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        flagged_symbols = {f.changed_symbol for f in report.findings}
        assert "stable_key" not in flagged_symbols, "Unchanged literal must NOT produce a finding (FR-002)"


# ---------------------------------------------------------------------------
# FR-002: analyzer must not import or execute any test file
# ---------------------------------------------------------------------------


class TestNoTestSuiteLoad:
    """FR-002: run_check() must not import or execute any test file."""

    def test_no_test_suite_load(self, tmp_path: Path) -> None:
        """The analyzer must not call importlib.import_module on test files."""
        repo = _setup_repo(tmp_path)

        _write(repo, "src/mod.py", "def foo(): pass\n")
        _write(
            repo,
            "tests/test_mod.py",
            """\
            def test_foo():
                assert foo() is None
        """,
        )
        base_sha = _commit(repo, "base")
        _write(repo, "src/mod.py", "def bar(): pass\n")
        head_sha = _commit(repo, "rename")

        import_calls: list[str] = []

        original_import = importlib.import_module

        def spy_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
            if "test" in name.lower():
                import_calls.append(name)
            return original_import(name, *args, **kwargs)

        with mock.patch("importlib.import_module", side_effect=spy_import):
            run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        assert import_calls == [], f"run_check must not import test modules, but imported: {import_calls}"


# ---------------------------------------------------------------------------
# FR-003: no finding may have confidence "definitely_stale"
# ---------------------------------------------------------------------------


class TestNoDefinitelyStaleConfidence:
    """FR-003: confidence values must only be 'high', 'medium', or 'low'."""

    def test_no_definitely_stale_confidence(self, tmp_path: Path) -> None:
        repo = _setup_repo(tmp_path)

        _write(
            repo,
            "src/service.py",
            """\
            def old_service():
                return "old"
        """,
        )
        _write(
            repo,
            "tests/test_service.py",
            """\
            def test_service():
                assert old_service() == "old"
                assert isinstance(old_service(), str)
                self.assertEqual(old_service(), "old")
        """,
        )
        base_sha = _commit(repo, "base")
        _write(
            repo,
            "src/service.py",
            """\
            def new_service():
                return "new"
        """,
        )
        head_sha = _commit(repo, "rename service")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        for finding in report.findings:
            assert finding.confidence != "definitely_stale", f"FR-003: finding must never have confidence 'definitely_stale', got {finding!r}"
            assert finding.confidence in ("high", "medium", "low"), f"FR-003: unexpected confidence value {finding.confidence!r}"


# ---------------------------------------------------------------------------
# FR-004 + importability
# ---------------------------------------------------------------------------


class TestMergeRunnerImportsLibraryDirectly:
    """FR-004: run_check is importable directly from specify_cli.post_merge."""

    def test_merge_runner_will_import_library_directly(self) -> None:
        """Assert run_check is importable from specify_cli.post_merge."""
        from specify_cli.post_merge import (  # noqa: F401
            StaleAssertionReport,
            run_check,
        )

        # Verify callable with correct signature.
        import inspect

        sig = inspect.signature(run_check)
        params = set(sig.parameters.keys())
        assert "base_ref" in params
        assert "head_ref" in params
        assert "repo_root" in params


# ---------------------------------------------------------------------------
# Internal helpers: scan_test_file
# ---------------------------------------------------------------------------


class TestScanTestFile:
    """Unit tests for the internal _scan_test_file helper."""

    def test_assert_statement_identifier_flagged(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_sample.py"
        test_file.write_text(
            textwrap.dedent("""\
            def test_it():
                assert old_func() == 42
        """)
        )

        from specify_cli.post_merge.stale_assertions import _SourceSymbol

        symbol = _SourceSymbol(
            name="old_func",
            kind="identifier",
            source_file=tmp_path / "src.py",
            source_line=1,
        )
        findings = _scan_test_file(test_file, [symbol])
        assert len(findings) >= 1
        assert findings[0].changed_symbol == "old_func"
        assert findings[0].confidence in ("high", "medium")

    def test_docstring_mention_not_flagged(self, tmp_path: Path) -> None:
        """A function name mentioned only in a docstring must not be flagged."""
        test_file = tmp_path / "test_docstring.py"
        test_file.write_text(
            textwrap.dedent("""\
            def test_something():
                \"\"\"Tests that old_func works correctly.\"\"\"
                assert True
        """)
        )

        from specify_cli.post_merge.stale_assertions import _SourceSymbol

        symbol = _SourceSymbol(
            name="old_func",
            kind="identifier",
            source_file=tmp_path / "src.py",
            source_line=1,
        )
        findings = _scan_test_file(test_file, [symbol])
        # Docstring is a Constant node but not in an assertion-bearing position.
        # The bare assert True does not reference old_func.
        assert not any(f.changed_symbol == "old_func" for f in findings), "Docstring mention of identifier must not be flagged"

    def test_syntax_error_returns_empty(self, tmp_path: Path) -> None:
        """A file with a SyntaxError must be skipped gracefully."""
        test_file = tmp_path / "broken_test.py"
        test_file.write_text("def test(: pass\n")  # deliberate syntax error

        from specify_cli.post_merge.stale_assertions import _SourceSymbol

        symbol = _SourceSymbol(
            name="anything",
            kind="identifier",
            source_file=tmp_path / "src.py",
            source_line=1,
        )
        # Should return empty list without raising.
        findings = _scan_test_file(test_file, [symbol])
        assert findings == []

    def test_unittest_style_assertion_flagged(self, tmp_path: Path) -> None:
        """unittest-style assertEqual is an assertion-bearing position."""
        test_file = tmp_path / "test_unittest.py"
        test_file.write_text(
            textwrap.dedent("""\
            import unittest

            class MyTest(unittest.TestCase):
                def test_it(self):
                    self.assertEqual(old_func(), 42)
        """)
        )

        from specify_cli.post_merge.stale_assertions import _SourceSymbol

        symbol = _SourceSymbol(
            name="old_func",
            kind="identifier",
            source_file=tmp_path / "src.py",
            source_line=1,
        )
        findings = _scan_test_file(test_file, [symbol])
        assert len(findings) >= 1
        assert findings[0].changed_symbol == "old_func"


# ---------------------------------------------------------------------------
# NFR-001: wall-clock benchmark (≤ 30 seconds on spec-kitty core itself)
# ---------------------------------------------------------------------------


class TestNFR001Benchmark:
    """NFR-001: run_check must complete within 30s on a real repository."""

    @pytest.mark.timeout(35)  # 5s grace beyond NFR-001 ceiling
    def test_runs_within_30s_on_synthetic_large_repo(self, tmp_path: Path) -> None:
        """Create a synthetic repo with many test files and verify wall clock < 30s."""
        repo = _setup_repo(tmp_path)

        # Create a source module.
        _write(repo, "src/__init__.py", "")
        _write(
            repo,
            "src/big_module.py",
            """\
            def function_a(): pass
            def function_b(): pass
        """,
        )

        # Create 100 test files to simulate a large test suite.
        tests_init = tmp_path / "tests"
        tests_init.mkdir(exist_ok=True)
        (tests_init / "__init__.py").write_text("")
        for i in range(100):
            (tests_init / f"test_file_{i:03d}.py").write_text(
                textwrap.dedent(f"""\
                    def test_{i}():
                        assert something_{i} == True
                """)
            )

        base_sha = _commit(repo, "base with large test suite")

        # Rename function_a → function_z.
        _write(
            repo,
            "src/big_module.py",
            """\
            def function_z(): pass
            def function_b(): pass
        """,
        )
        head_sha = _commit(repo, "rename function_a -> function_z")

        start = time.monotonic()
        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)
        elapsed = time.monotonic() - start

        assert elapsed < 30.0, f"NFR-001: run_check took {elapsed:.1f}s, must be < 30s"
        assert report.elapsed_seconds < 30.0, f"NFR-001: report.elapsed_seconds={report.elapsed_seconds:.1f}s, must be < 30s"


# ---------------------------------------------------------------------------
# NFR-002: false-positive ceiling (≤ 5 findings per 100 LOC)
# ---------------------------------------------------------------------------


class TestNFR002FPCeiling:
    """NFR-002: findings_per_100_loc must not exceed 5.0 on curated benchmark."""

    def test_fp_ceiling_under_5_per_100_loc_on_curated_benchmark(self, tmp_path: Path) -> None:
        """Curated benchmark: many functions renamed in a large module, few assertions.

        Design principle: the diff must have enough LOC changed relative to
        findings so that findings_per_100_loc ≤ 5.0.
        We rename 20 functions in a 200-line module, producing ~40 diff LOC,
        and write a test file with only 1 assertion referencing one of the
        renamed functions.  Ratio: 1 / 40 * 100 = 2.5 ≤ 5.0.
        """
        repo = _setup_repo(tmp_path)
        (tmp_path / "src").mkdir(exist_ok=True)
        (tmp_path / "tests").mkdir(exist_ok=True)
        (tmp_path / "tests" / "__init__.py").write_text("")

        # Base: 20 functions with old names + 180 other lines (docstrings).
        old_funcs = [f'def old_func_{i:02d}():\n    """Old function {i}."""\n    return {i}\n\n' for i in range(20)]
        # Add 100 helper lines that won't change.
        stable_funcs = [f"def stable_{i:02d}():\n    return {i * 10}\n\n" for i in range(50)]
        module_src = "".join(old_funcs) + "".join(stable_funcs)
        (tmp_path / "src" / "module.py").write_text(module_src)

        # Test file: only 1 assertion references old_func_00.
        test_src = textwrap.dedent("""\
            def test_old_func_00():
                assert old_func_00() == 0

            def test_stable_00():
                assert stable_00() == 0

            def test_stable_01():
                assert stable_01() == 10
        """)
        (tmp_path / "tests" / "test_module.py").write_text(test_src)

        base_sha = _commit(repo, "base: large module with old names")

        # Head: rename all 20 old_func_XX → new_func_XX (20 function renames = 40 diff LOC).
        new_funcs = [f'def new_func_{i:02d}():\n    """New function {i}."""\n    return {i}\n\n' for i in range(20)]
        new_module_src = "".join(new_funcs) + "".join(stable_funcs)
        (tmp_path / "src" / "module.py").write_text(new_module_src)
        head_sha = _commit(repo, "rename 20 functions: old_func_XX -> new_func_XX")

        report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        # Findings: only old_func_00 is referenced in assertions.
        # LOC changed: ~40 (20 removed lines + 20 added lines for function defs).
        # Ratio: 1 / 40 * 100 = 2.5 ≤ 5.0.
        assert report.findings_per_100_loc <= FP_CEILING, (
            f"NFR-002: findings_per_100_loc={report.findings_per_100_loc:.2f} "
            f"exceeds ceiling of {FP_CEILING}. "
            f"findings={len(report.findings)}, "
            f"elapsed={report.elapsed_seconds:.2f}s. "
            "FR-022 mandates narrowing scope before review."
        )

    def test_fr_022_fallback_warns_when_fp_exceeds_ceiling(self, tmp_path: Path) -> None:
        """FR-022: when FP ceiling is exceeded, a UserWarning must be emitted."""
        # Build a report with findings_per_100_loc > 5.0 by patching _count_diff_loc
        # to return a small number (1 LOC), making the ratio huge.
        repo = _setup_repo(tmp_path)

        _write(repo, "src/mod.py", "def alpha(): pass\ndef beta(): pass\n")
        _write(
            repo,
            "tests/test_mod.py",
            """\
            def test_alpha():
                assert alpha() is None
            def test_beta():
                assert beta() is None
        """,
        )
        base_sha = _commit(repo, "base")
        _write(repo, "src/mod.py", "def gamma(): pass\ndef delta(): pass\n")
        head_sha = _commit(repo, "rename both")

        # Patch _count_diff_loc to return 1 so ratio is artificially high.
        with (
            mock.patch(
                "specify_cli.post_merge.stale_assertions._count_diff_loc",
                return_value=1,
            ),
            pytest.warns(UserWarning, match="NFR-002 ceiling"),
        ):
            run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)


# ---------------------------------------------------------------------------
# T007: zero network calls assertion
# ---------------------------------------------------------------------------


class TestNoNetworkCalls:
    """NFR-005: run_check must not make any network calls."""

    def test_no_network_calls(self, tmp_path: Path) -> None:
        """run_check must not call urllib.request.urlopen."""
        import urllib.request

        repo = _setup_repo(tmp_path)
        _write(repo, "src/mod.py", "def foo(): pass\n")
        _write(repo, "tests/test_mod.py", "def test_foo(): assert foo() is None\n")
        base_sha = _commit(repo, "base")
        _write(repo, "src/mod.py", "def bar(): pass\n")
        head_sha = _commit(repo, "rename")

        def _no_network(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("run_check must not make network calls")

        with mock.patch.object(urllib.request, "urlopen", side_effect=_no_network):
            # Should complete without raising.
            report = run_check(base_ref=base_sha, head_ref=head_sha, repo_root=repo)

        assert isinstance(report, StaleAssertionReport)
