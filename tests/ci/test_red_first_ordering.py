"""Unit tests for red-first re-run ordering (mission ci-flake-report-workflow, WP05).

Pins, red-first, the behaviors FR-018 requires from
``scripts/ci/collect_failed_nodeids.py``:

- Parsing failing nodeids from a pytest terminal log (``FAILED <nodeid>``
  lines) and from a JUnit XML report.
- The pytest lastfailed-cache seed shape (``.pytest_cache/v/cache/lastfailed``).
- Ordering selection: persisted ∩ current -> priority-first, order preserved;
  removed/renamed nodeids dropped; empty persisted list -> empty selection
  (normal order).
- The defensive no-raise contract: corrupt/absent input degrades to "no
  prior failures", never an exception -- this is an ergonomics optimization,
  never a correctness gate (FR-018's own note).

``scripts/ci`` is not an importable package (mirrors
``tests/ci/test_flake_report_core.py``), so the module is loaded by file
path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "ci" / "collect_failed_nodeids.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("collect_failed_nodeids", _SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot build an import spec for {_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CFN: Any = _load_module()


# ---------------------------------------------------------------------------
# parse_failed_nodeids_from_output
# ---------------------------------------------------------------------------


def test_parse_failed_nodeids_from_output_extracts_failed_lines() -> None:
    log = (
        "============ FAILURES ============\n"
        "FAILED tests/ci/test_foo.py::test_bar - AssertionError: boom\n"
        "FAILED tests/ci/test_foo.py::TestClass::test_baz\n"
        "1 passed, 2 failed in 0.42s\n"
    )
    assert CFN.parse_failed_nodeids_from_output(log) == [
        "tests/ci/test_foo.py::test_bar",
        "tests/ci/test_foo.py::TestClass::test_baz",
    ]


def test_parse_failed_nodeids_from_output_deduplicates_preserving_order() -> None:
    log = (
        "FAILED tests/ci/test_foo.py::test_bar\n"
        "FAILED tests/ci/test_foo.py::test_qux\n"
        "FAILED tests/ci/test_foo.py::test_bar\n"
    )
    assert CFN.parse_failed_nodeids_from_output(log) == [
        "tests/ci/test_foo.py::test_bar",
        "tests/ci/test_foo.py::test_qux",
    ]


def test_parse_failed_nodeids_from_output_empty_input_yields_empty_list() -> None:
    assert CFN.parse_failed_nodeids_from_output("") == []


def test_parse_failed_nodeids_from_output_no_failures_yields_empty_list() -> None:
    log = "5 passed in 1.23s\n"
    assert CFN.parse_failed_nodeids_from_output(log) == []


def test_parse_failed_nodeids_from_output_ignores_failed_inside_other_text() -> None:
    # Not anchored at line start -- must not match mid-line mentions of "FAILED".
    log = "the previous step FAILED tests/ci/test_foo.py::test_bar for infra reasons\n"
    assert CFN.parse_failed_nodeids_from_output(log) == []


# ---------------------------------------------------------------------------
# parse_failed_nodeids_from_junit
# ---------------------------------------------------------------------------

_JUNIT_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" failures="2" errors="0">
    <testcase classname="tests.ci.test_foo" name="test_bar" time="0.01">
      <failure message="AssertionError">boom</failure>
    </testcase>
    <testcase classname="tests.ci.test_foo.TestClass" name="test_baz" time="0.02">
      <error message="RuntimeError">kaboom</error>
    </testcase>
    <testcase classname="tests.ci.test_foo" name="test_ok" time="0.01" />
  </testsuite>
</testsuites>
"""


def test_parse_failed_nodeids_from_junit_extracts_failure_and_error_testcases(tmp_path: Path) -> None:
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(_JUNIT_XML, encoding="utf-8")
    assert CFN.parse_failed_nodeids_from_junit(xml_path) == [
        "tests/ci/test_foo.py::test_bar",
        "tests/ci/test_foo.py::TestClass::test_baz",
    ]


def test_parse_failed_nodeids_from_junit_missing_file_returns_empty(tmp_path: Path) -> None:
    assert CFN.parse_failed_nodeids_from_junit(tmp_path / "does-not-exist.xml") == []


def test_parse_failed_nodeids_from_junit_corrupt_xml_returns_empty(tmp_path: Path) -> None:
    xml_path = tmp_path / "corrupt.xml"
    xml_path.write_text("<testsuites><testsuite><testcase", encoding="utf-8")
    assert CFN.parse_failed_nodeids_from_junit(xml_path) == []


def test_parse_failed_nodeids_from_junit_no_classname_uses_bare_name(tmp_path: Path) -> None:
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        '<testsuites><testsuite><testcase classname="" name="test_bare">'
        "<failure>boom</failure></testcase></testsuite></testsuites>",
        encoding="utf-8",
    )
    assert CFN.parse_failed_nodeids_from_junit(xml_path) == ["test_bare"]


# ---------------------------------------------------------------------------
# write_persisted_nodeids / read_persisted_nodeids
# ---------------------------------------------------------------------------


def test_write_then_read_persisted_nodeids_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "flake-lastfailed" / "3596"
    CFN.write_persisted_nodeids(path, ["tests/ci/test_foo.py::test_b", "tests/ci/test_foo.py::test_a"])
    # Sorted for deterministic output (NFR-004-style byte-stability).
    assert CFN.read_persisted_nodeids(path) == [
        "tests/ci/test_foo.py::test_a",
        "tests/ci/test_foo.py::test_b",
    ]


def test_write_persisted_nodeids_deduplicates(tmp_path: Path) -> None:
    path = tmp_path / "lastfailed"
    CFN.write_persisted_nodeids(path, ["tests/x.py::test_a", "tests/x.py::test_a", "  "])
    assert CFN.read_persisted_nodeids(path) == ["tests/x.py::test_a"]


def test_write_persisted_nodeids_empty_writes_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "lastfailed"
    CFN.write_persisted_nodeids(path, [])
    assert path.is_file()
    assert CFN.read_persisted_nodeids(path) == []


def test_read_persisted_nodeids_missing_file_returns_empty(tmp_path: Path) -> None:
    assert CFN.read_persisted_nodeids(tmp_path / "does-not-exist") == []


def test_read_persisted_nodeids_corrupt_content_never_raises(tmp_path: Path) -> None:
    path = tmp_path / "lastfailed"
    path.write_bytes(b"\xff\xfe\x00\x01not-utf8")
    assert CFN.read_persisted_nodeids(path) == []


def test_write_persisted_nodeids_unwritable_parent_never_raises(tmp_path: Path) -> None:
    # Parent path collides with an existing FILE (not a dir), so mkdir must fail --
    # write_persisted_nodeids must swallow that rather than propagate.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    target = blocker / "nested" / "lastfailed"
    CFN.write_persisted_nodeids(target, ["tests/x.py::test_a"])  # must not raise
    assert not target.exists()


# ---------------------------------------------------------------------------
# select_priority_nodeids
# ---------------------------------------------------------------------------


def test_select_priority_nodeids_intersects_preserving_persisted_order() -> None:
    persisted = ["tests/a.py::test_z", "tests/a.py::test_y", "tests/a.py::test_x"]
    current = ["tests/a.py::test_x", "tests/a.py::test_y", "tests/a.py::test_w"]
    assert CFN.select_priority_nodeids(persisted, current) == [
        "tests/a.py::test_y",
        "tests/a.py::test_x",
    ]


def test_select_priority_nodeids_drops_removed_or_renamed_nodeids() -> None:
    persisted = ["tests/a.py::test_removed", "tests/a.py::test_kept"]
    current = ["tests/a.py::test_kept", "tests/a.py::test_new"]
    assert CFN.select_priority_nodeids(persisted, current) == ["tests/a.py::test_kept"]


def test_select_priority_nodeids_empty_persisted_yields_normal_order() -> None:
    assert CFN.select_priority_nodeids([], ["tests/a.py::test_x"]) == []


def test_select_priority_nodeids_no_overlap_yields_empty() -> None:
    persisted = ["tests/a.py::test_gone"]
    current = ["tests/a.py::test_new"]
    assert CFN.select_priority_nodeids(persisted, current) == []


# ---------------------------------------------------------------------------
# build_lastfailed_cache / write_lastfailed_cache
# ---------------------------------------------------------------------------


def test_build_lastfailed_cache_matches_pytest_shape() -> None:
    payload = CFN.build_lastfailed_cache(["tests/a.py::test_x", "tests/a.py::test_y"])
    assert payload == {"tests/a.py::test_x": True, "tests/a.py::test_y": True}


def test_build_lastfailed_cache_empty_yields_empty_dict() -> None:
    assert CFN.build_lastfailed_cache([]) == {}


def test_build_lastfailed_cache_ignores_blank_entries() -> None:
    assert CFN.build_lastfailed_cache(["tests/a.py::test_x", "  ", ""]) == {"tests/a.py::test_x": True}


def test_write_lastfailed_cache_writes_pytest_native_location(tmp_path: Path) -> None:
    cache_dir = tmp_path / ".pytest_cache"
    target = CFN.write_lastfailed_cache(cache_dir, ["tests/a.py::test_x"])
    assert target == cache_dir / "v" / "cache" / "lastfailed"
    assert target.is_file()

    import json

    assert json.loads(target.read_text(encoding="utf-8")) == {"tests/a.py::test_x": True}


def test_write_lastfailed_cache_empty_nodeids_writes_empty_object(tmp_path: Path) -> None:
    cache_dir = tmp_path / ".pytest_cache"
    target = CFN.write_lastfailed_cache(cache_dir, [])

    import json

    assert json.loads(target.read_text(encoding="utf-8")) == {}


def test_write_lastfailed_cache_unwritable_dir_never_raises(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    cache_dir = blocker / "nested" / ".pytest_cache"
    target = CFN.write_lastfailed_cache(cache_dir, ["tests/a.py::test_x"])  # must not raise
    assert not target.exists()


# ---------------------------------------------------------------------------
# End-to-end: persisted file -> selection -> seeded cache (the T019 wiring,
# minus the actual `pytest --ff` subprocess).
# ---------------------------------------------------------------------------


def test_end_to_end_persist_select_seed_round_trip(tmp_path: Path) -> None:
    persisted_path = tmp_path / "flake-lastfailed" / "3596"
    CFN.write_persisted_nodeids(persisted_path, ["tests/a.py::test_flaky", "tests/a.py::test_gone_now"])

    current_collected = ["tests/a.py::test_flaky", "tests/a.py::test_new", "tests/a.py::test_stable"]
    persisted = CFN.read_persisted_nodeids(persisted_path)
    priority = CFN.select_priority_nodeids(persisted, current_collected)
    assert priority == ["tests/a.py::test_flaky"]

    cache_dir = tmp_path / ".pytest_cache"
    target = CFN.write_lastfailed_cache(cache_dir, priority)

    import json

    assert json.loads(target.read_text(encoding="utf-8")) == {"tests/a.py::test_flaky": True}


def test_end_to_end_no_prior_failures_is_a_noop() -> None:
    """FR-018: no prior red -> no-op normal ordering (empty priority set)."""
    persisted = CFN.read_persisted_nodeids(Path("/nonexistent/flake-lastfailed/9999"))
    assert persisted == []
    priority = CFN.select_priority_nodeids(persisted, ["tests/a.py::test_x"])
    assert priority == []
    assert CFN.build_lastfailed_cache(priority) == {}


# ---------------------------------------------------------------------------
# CLI (main()) -- collect + seed subcommands, defensive no-raise contract
# ---------------------------------------------------------------------------


def test_cli_collect_from_output_persists_nodeids(tmp_path: Path) -> None:
    log_path = tmp_path / "pytest-output.log"
    log_path.write_text("FAILED tests/a.py::test_x\nFAILED tests/a.py::test_y\n", encoding="utf-8")
    out_path = tmp_path / "flake-lastfailed" / "42"

    exit_code = CFN.main(["collect", "--from-output", str(log_path), "--out", str(out_path)])

    assert exit_code == 0
    assert CFN.read_persisted_nodeids(out_path) == ["tests/a.py::test_x", "tests/a.py::test_y"]


def test_cli_collect_from_junit_persists_nodeids(tmp_path: Path) -> None:
    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(_JUNIT_XML, encoding="utf-8")
    out_path = tmp_path / "flake-lastfailed" / "42"

    exit_code = CFN.main(["collect", "--junit-xml", str(xml_path), "--out", str(out_path)])

    assert exit_code == 0
    assert CFN.read_persisted_nodeids(out_path) == [
        "tests/ci/test_foo.py::TestClass::test_baz",
        "tests/ci/test_foo.py::test_bar",
    ]


def test_cli_collect_with_no_sources_persists_empty(tmp_path: Path) -> None:
    out_path = tmp_path / "flake-lastfailed" / "42"
    exit_code = CFN.main(["collect", "--out", str(out_path)])
    assert exit_code == 0
    assert CFN.read_persisted_nodeids(out_path) == []


def test_cli_seed_writes_lastfailed_cache_from_persisted_file(tmp_path: Path) -> None:
    persisted_path = tmp_path / "flake-lastfailed" / "42"
    CFN.write_persisted_nodeids(persisted_path, ["tests/a.py::test_x"])
    cache_dir = tmp_path / ".pytest_cache"

    exit_code = CFN.main(["seed", "--persisted", str(persisted_path), "--cache-dir", str(cache_dir)])

    assert exit_code == 0
    target = cache_dir / "v" / "cache" / "lastfailed"

    import json

    assert json.loads(target.read_text(encoding="utf-8")) == {"tests/a.py::test_x": True}


def test_cli_seed_with_missing_persisted_file_is_a_noop(tmp_path: Path) -> None:
    """FR-018: no prior red run -> seed step is a harmless no-op, never an error."""
    cache_dir = tmp_path / ".pytest_cache"
    exit_code = CFN.main(
        ["seed", "--persisted", str(tmp_path / "does-not-exist"), "--cache-dir", str(cache_dir)]
    )
    assert exit_code == 0
    target = cache_dir / "v" / "cache" / "lastfailed"

    import json

    assert json.loads(target.read_text(encoding="utf-8")) == {}


def test_cli_never_raises_on_unexpected_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI's own defensive contract: an unexpected exception is swallowed, exit 0."""

    def _boom(_args: Any) -> int:
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr(CFN, "_cmd_collect", _boom)
    exit_code = CFN.main(["collect", "--out", str(tmp_path / "out")])
    assert exit_code == 0
