"""Proof that ``tests/e2e``'s tmp_path release fires on pass and holds on fail (#80).

Two layers:

* decision units cover the ``_call_report_passed`` predicate's branches in
  milliseconds (the fixture body itself cannot be invoked directly);
* an integration layer launches real nested pytest runs against generated
  child files, loading ``tests/e2e/conftest.py`` as a plugin, and asserts the
  filesystem outcome — including a control run *without* the plugin, proving
  the release is caused by this conftest and not by pytest itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.e2e.conftest import _call_report_passed

_REPO_ROOT = Path(__file__).resolve().parents[2]

_PASS_CHILD = """
def test_child_pass(tmp_path):
    (tmp_path / "sentinel.txt").write_text("x", encoding="utf-8")
    assert (tmp_path / "sentinel.txt").is_file()
"""

_FAIL_CHILD = """
def test_child_fail(tmp_path):
    (tmp_path / "sentinel.txt").write_text("x", encoding="utf-8")
    assert False, "deliberate failure so teardown must retain tmp_path"
"""


def _node_with_call_report(passed: bool | None) -> SimpleNamespace:
    node = SimpleNamespace()
    if passed is not None:
        node._e2e_rep_call = SimpleNamespace(passed=passed)
    return node


def test_predicate_reads_a_passed_call_report() -> None:
    assert _call_report_passed(_node_with_call_report(True))


def test_predicate_rejects_a_failed_call_report() -> None:
    assert not _call_report_passed(_node_with_call_report(False))


def test_predicate_is_false_without_any_call_report() -> None:
    assert not _call_report_passed(_node_with_call_report(None))


def _write_child(directory: Path, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    child = directory / "test_child.py"
    child.write_text(body, encoding="utf-8")
    (directory / "pytest.ini").touch()
    return child


def _run_nested_pytest(child: Path, scratch: Path, *, with_e2e_conftest: bool) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(child),
        "--basetemp",
        str(scratch / "bt"),
        "--rootdir",
        str(scratch),
        "-c",
        str(scratch / "pytest.ini"),
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    if with_e2e_conftest:
        command.extend(["-p", "tests.e2e.conftest"])
    env = {key: value for key, value in os.environ.items() if not key.startswith(("SPEC_KITTY_", "PYTEST_XDIST"))}
    pythonpath_parts = [str(_REPO_ROOT / "src"), str(_REPO_ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return subprocess.run(command, capture_output=True, text=True, env=env, cwd=str(scratch), timeout=180)


@pytest.mark.slow
def test_passed_nested_tmp_tree_is_released_by_the_e2e_conftest(tmp_path: Path) -> None:
    child = _write_child(tmp_path / "case-pass", _PASS_CHILD)
    completed = _run_nested_pytest(child, tmp_path / "case-pass", with_e2e_conftest=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not (tmp_path / "case-pass" / "bt" / "test_child_pass0").exists()


@pytest.mark.slow
def test_without_the_e2e_conftest_a_passed_tree_is_retained(tmp_path: Path) -> None:
    """Control limb: the release above is caused by this repository's conftest."""
    case = tmp_path / "case-control"
    child = _write_child(case, _PASS_CHILD)
    completed = _run_nested_pytest(child, case, with_e2e_conftest=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (case / "bt" / "test_child_pass0" / "sentinel.txt").is_file()


@pytest.mark.slow
def test_failed_nested_tmp_tree_is_retained_for_diagnosis(tmp_path: Path) -> None:
    case = tmp_path / "case-fail"
    child = _write_child(case, _FAIL_CHILD)
    completed = _run_nested_pytest(child, case, with_e2e_conftest=True)
    assert completed.returncode != 0
    assert "deliberate failure" in completed.stdout
    assert (case / "bt" / "test_child_fail0" / "sentinel.txt").is_file()
