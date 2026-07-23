"""WP03 (mission ``scopesource-gate-followup-01KY6S9P``) — ``source_identity``
field round-trip + the B1 parse-after-teardown lifecycle fix (FR-008/FR-009).

**T013** pins ``BaselineTestResult.source_identity``: present + round-tripped
by ``to_dict``/``from_dict``, and defaulted to ``"unknown"`` for a
straddling-upgrade artifact captured before the field existed (US1 AS4) --
never a ``KeyError``.

**T016** is the B1 red-first DIRECT capture unit test (post-plan-squad M-B1):
it drives ``capture_baseline`` with a REAL git repo + REAL ``DeclaredCommandScopeSource``
whose declared command writes a **worktree-relative** ``--junitxml`` artifact
(the exact bug surface -- ``GateCoverageScopeSource``'s absolute tempfile
JUnit is unaffected either way, data-model.md sec. 5). Before T014's fix,
``_capture_baseline_via_scope_source`` parses AFTER the baseline worktree is
torn down (``baseline.py:522`` at base), which loses both the worktree
itself and the process-cwd-relative artifact path -- so the parsed baseline
never recovers the script's real per-test failure identity: it degrades to
the generic whole-run synthetic placeholder (``scope_source._whole_run_failure``),
and ``source_identity`` never gets recorded as anything but the field's own
default, ``"unknown"``. This IS a genuine bug repro (not migration-red): the
workflow-routed path is dormant on the base commit (nothing on the base
branch drives the scope-source capture path end-to-end), so only a DIRECT
call like this one exercises it.

Confirmed RED on base commit (pre-T014, post-T013) via
``PYTHONPATH=$(pwd)/src pytest tests/review/test_baseline_lifecycle.py -q``:
``test_declared_command_worktree_relative_artifact_survives_to_parse``
failed on both assertions --
``result.failures[0].test == "<declared-command>"`` (the synthetic
whole-run placeholder, not the real ``tests.test_thing.test_boom`` JUnit
identity) and ``result.source_identity == "unknown"`` (not
``"DeclaredCommandScopeSource/junit_xml"``) -- exactly the lifecycle
asymmetry the mission's B1 finding describes. GREEN once T014 lands the
parse-before-teardown fix.
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from specify_cli.review.baseline import BaselineTestResult, capture_baseline
from specify_cli.review.scope_source import resolve_scope_source, DeclaredCommandScopeSource

pytestmark = pytest.mark.git_repo


# ---------------------------------------------------------------------------
# T013 -- source_identity round-trip + legacy-artifact default
# ---------------------------------------------------------------------------


def _make_result(**overrides: object) -> BaselineTestResult:
    defaults: dict[str, object] = {
        "wp_id": "WP03",
        "captured_at": "2026-07-23T10:00:00Z",
        "base_branch": "main",
        "base_commit": "abc1234def",
        "test_runner": "pytest",
        "total": 1,
        "passed": 0,
        "failed": 1,
        "skipped": 0,
        "failures": (),
    }
    defaults.update(overrides)
    return BaselineTestResult(**defaults)


class TestSourceIdentityField:
    """T013 -- ``BaselineTestResult.source_identity`` (FR-009)."""

    def test_default_is_unknown(self) -> None:
        result = _make_result()
        assert result.source_identity == "unknown"

    def test_to_dict_emits_source_identity(self) -> None:
        result = _make_result(source_identity="GateCoverageScopeSource/junit_xml")
        data = result.to_dict()
        assert data["source_identity"] == "GateCoverageScopeSource/junit_xml"

    def test_round_trip_through_save_and_load_preserves_source_identity(self, tmp_path: Path) -> None:
        result = _make_result(source_identity="DeclaredCommandScopeSource/junit_xml")
        path = tmp_path / "baseline-tests.json"
        result.save(path)

        loaded = BaselineTestResult.load(path)

        assert loaded is not None
        assert loaded.source_identity == "DeclaredCommandScopeSource/junit_xml"

    def test_from_dict_legacy_artifact_without_source_identity_key_defaults_to_unknown(self) -> None:
        """A straddling-upgrade artifact captured before this field existed
        carries no ``source_identity`` key at all -- ``from_dict`` must
        degrade to ``"unknown"``, never raise ``KeyError`` (US1 AS4)."""
        legacy_dict = {
            "wp_id": "WP01",
            "captured_at": "2026-01-01T00:00:00Z",
            "base_branch": "main",
            "base_commit": "deadbeef0",
            "test_runner": "pytest",
            "total": 3,
            "passed": 3,
            "failed": 0,
            "skipped": 0,
            "failures": [],
        }

        result = BaselineTestResult.from_dict(legacy_dict)

        assert result.source_identity == "unknown"


# ---------------------------------------------------------------------------
# T016 -- B1 red-first DIRECT capture unit test
# ---------------------------------------------------------------------------

_WRITE_JUNIT_SCRIPT = textwrap.dedent(
    """\
    import sys
    from pathlib import Path

    JUNIT_XML = (
        '<?xml version="1.0" encoding="utf-8"?>\\n'
        '<testsuites>\\n'
        '  <testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0">\\n'
        '    <testcase classname="tests.test_thing" name="test_boom" '
        'file="tests/test_thing.py" line="3">\\n'
        '      <failure message="AssertionError: boom">AssertionError: boom</failure>\\n'
        '    </testcase>\\n'
        '  </testsuite>\\n'
        '</testsuites>\\n'
    )

    # Worktree-relative -- written against the process's OWN cwd, which the
    # baseline capture path invokes with cwd=<tmp_worktree> (the B1 bug
    # surface: this file lives INSIDE the baseline worktree, not beside it).
    Path("results.xml").write_text(JUNIT_XML, encoding="utf-8")
    sys.exit(1)
    """
)


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def _write_file(repo: Path, relative_path: str, content: str) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _git_commit_all(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)


def _build_declared_command_repo(tmp_path: Path) -> Path:
    """A real throwaway git repo whose ``review.test_command`` runs a
    committed script that writes a **worktree-relative** ``--junitxml``
    artifact and exits non-zero -- the exact ``DeclaredCommandScopeSource``
    shape B1 targets (data-model.md sec. 1/5). The script must be COMMITTED
    (not just present in the working tree) because the baseline worktree is
    a fresh ``git worktree add <tmp> main --detach`` checkout of ``main``'s
    history, not a copy of the working tree.
    """
    repo = tmp_path / "declared-command-repo"
    _init_git_repo(repo)
    _write_file(repo, "write_junit.py", _WRITE_JUNIT_SCRIPT)
    test_command = f"{sys.executable} write_junit.py --junitxml=results.xml"
    _write_file(
        repo,
        ".kittify/config.yaml",
        f"review:\n  test_command: {test_command!r}\n",
    )
    _git_commit_all(repo, "base commit with declared test command")
    return repo


class TestB1ParseBeforeTeardown:
    """T016 -- direct ``capture_baseline`` unit test, real git, real
    ``DeclaredCommandScopeSource``, worktree-relative artifact."""

    def test_declared_command_worktree_relative_artifact_survives_to_parse(self, tmp_path: Path) -> None:
        repo = _build_declared_command_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "scopesource-gate-followup-01KY6S9P"
        wp_slug = "WP03-baseline-lifecycle-identity"

        scope_source = resolve_scope_source(repo)
        assert isinstance(scope_source, DeclaredCommandScopeSource), (
            "fixture must route to the portable, non-pytest source -- the "
            "one B1 targets -- not the internal GateCoverageScopeSource"
        )

        result = capture_baseline(
            worktree_path=repo,
            base_branch="main",
            wp_id="WP03",
            mission_slug="scopesource-gate-followup-01KY6S9P",
            feature_dir=feature_dir,
            wp_slug=wp_slug,
            scope_source=scope_source,
        )

        assert result is not None
        assert result.failed == 1, result.failures
        # The B1 assertion: the parsed failure must be the REAL JUnit
        # identity the script wrote, not the generic whole-run synthetic
        # placeholder a lost/unresolvable artifact degrades to.
        assert result.failures[0].test == "tests.test_thing.test_boom"
        assert result.failures[0].file == "tests/test_thing.py:3"
        # The identity recorded must reflect that the artifact really was
        # parsed as JUnit -- not "unknown" (T014 wires this at the same
        # point the parse happens, via scope_source_identity()).
        assert result.source_identity == "DeclaredCommandScopeSource/junit_xml"

    def test_shared_namespace_matches_head_run_identity_derivation(self, tmp_path: Path) -> None:
        """The baseline failure identity must be derivable through the SAME
        ``scope_source.parse_results`` a head run would use on an identical
        raw result -- proving baseline and head share one namespace rather
        than each deriving their own ad hoc token (NFR-005)."""
        from specify_cli.review.scope_source import RawRunResult

        repo = _build_declared_command_repo(tmp_path)
        feature_dir = tmp_path / "kitty-specs" / "scopesource-gate-followup-01KY6S9P"

        scope_source = resolve_scope_source(repo)
        result = capture_baseline(
            worktree_path=repo,
            base_branch="main",
            wp_id="WP03",
            mission_slug="scopesource-gate-followup-01KY6S9P",
            feature_dir=feature_dir,
            wp_slug="WP03-baseline-lifecycle-identity-shared",
            scope_source=scope_source,
        )
        assert result is not None

        # Simulate a head run producing an IDENTICAL raw result (same
        # committed script's JUnit shape) against a fresh instance of the
        # same source, and confirm parse_results() yields the same identity
        # namespace the baseline recorded -- proving both sides derive
        # identities through the shared parser, not two independent ones.
        head_source = resolve_scope_source(repo)
        head_artifact = tmp_path / "head-junit.xml"
        head_artifact.write_text(
            (
                '<?xml version="1.0" encoding="utf-8"?>\n'
                '<testsuites>\n'
                '  <testsuite name="pytest" tests="1" failures="1" errors="0" skipped="0">\n'
                '    <testcase classname="tests.test_thing" name="test_boom" '
                'file="tests/test_thing.py" line="3">\n'
                '      <failure message="AssertionError: boom">AssertionError: boom</failure>\n'
                '    </testcase>\n'
                '  </testsuite>\n'
                '</testsuites>\n'
            ),
            encoding="utf-8",
        )
        raw = RawRunResult(returncode=1, stdout="", stderr="", output_artifact_path=head_artifact)
        head_failures = head_source.parse_results(raw)

        assert len(head_failures) == 1
        assert head_failures[0].test == result.failures[0].test
