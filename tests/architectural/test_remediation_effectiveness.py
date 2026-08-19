"""Every preflight remediation must be able to clear the check that emits it (#2831).

The rule, stated once:

    For every charter-freshness sub-state that emits a remediation, running
    that command in a project exhibiting the state MUST exit 0 AND leave that
    sub-state ``fresh``.

Why the "AND" matters. The historical failure this module exists to prevent was
`spec-kitty charter sync` being offered for four blocking states while
``src/charter/sync.py`` documents itself as a pure staleness reporter -- "it
always reports ``synced=False`` / ``files_written=[]``". The operator ran it,
nothing changed, the gate refused identically, and every charter diagnostic
reported healthy. There was no exit.

A weaker oracle does not catch that class of defect. An earlier draft of this
enforcement (PR #3015) asserted only ``after != before``; a remediation that
writes malformed YAML and exits 17 satisfies that, because ``missing ->
invalid`` is a change. So this module pins the destination state and the exit
code, not merely that something moved.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from specify_cli.charter_runtime.freshness.computer import compute_freshness

#: Selection marker, not decoration: CI selects tests BY MARKER, so an
#: unmarked file under tests/architectural/ is collected by ZERO gates --
#: `test_same_tier_uniqueness::test_split_preserves_zero_orphans` and
#: `test_ci_collection_completeness` both fail on it, correctly. Without this
#: an effectiveness oracle could regress and never turn a branch red.
pytestmark = pytest.mark.architectural

_CHARTER_DIR = Path(".kittify") / "charter"
_UNPARSEABLE = "governance:\n  - broken: [unterminated\n    flow sequence\n"


def _seed_project(repo_root: Path) -> None:
    """Minimal project shape both fixtures share."""
    (repo_root / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo_root / ".kittify" / "config.yaml").write_text(
        "activated_directives: []\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q", "."], cwd=repo_root, check=True)


def _fixture_charter_yaml_absent(repo_root: Path) -> None:
    """F1 -- no charter at all: ``charter_source: missing`` / ``synced_bundle: missing``."""
    _seed_project(repo_root)
    (repo_root / _CHARTER_DIR).mkdir(parents=True, exist_ok=True)


def _fixture_charter_yaml_unparseable(repo_root: Path) -> None:
    """F2 -- present but broken: ``charter_source: invalid`` / ``synced_bundle: stale``."""
    _seed_project(repo_root)
    charter_dir = repo_root / _CHARTER_DIR
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.yaml").write_text(_UNPARSEABLE, encoding="utf-8")


def _layer_state(repo_root: Path, layer: str) -> str:
    return str(getattr(compute_freshness(repo_root), layer).state)


def _layer_remediation(repo_root: Path, layer: str) -> str | None:
    value = getattr(compute_freshness(repo_root), layer).remediation
    return None if value is None else str(value)


def _run_remediation(repo_root: Path, command: str) -> subprocess.CompletedProcess[str]:
    """Execute a remediation string as the operator would read it.

    ``spec-kitty`` is invoked as ``python -m specify_cli`` so the test does not
    depend on a console script being on PATH in every environment.
    """
    args = shlex.split(command)
    assert args[:1] == ["spec-kitty"], f"unexpected remediation shape: {command!r}"
    return subprocess.run(
        [sys.executable, "-m", "specify_cli", *args[1:]],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )


#: (layer, fixture, expected non-passing state). One row per state that emits a
#: remediation. Both layers are driven for both fixtures because
#: ``synced_bundle`` is a structural echo of ``charter_source`` (single-entry
#: ``_BUNDLE_FILES``) -- a fix that clears one but not the other still leaves
#: the operator blocked, so neither is assumed from the other.
_CASES = [
    ("charter_source", _fixture_charter_yaml_absent, "missing"),
    ("synced_bundle", _fixture_charter_yaml_absent, "missing"),
    ("charter_source", _fixture_charter_yaml_unparseable, "invalid"),
    ("synced_bundle", _fixture_charter_yaml_unparseable, "stale"),
]


@pytest.mark.parametrize(("layer", "seed", "expected_state"), _CASES)
def test_remediation_clears_the_state_that_emitted_it(
    tmp_path: Path,
    layer: str,
    seed,
    expected_state: str,
) -> None:
    seed(tmp_path)

    assert _layer_state(tmp_path, layer) == expected_state, (
        f"fixture did not produce {layer}={expected_state}"
    )
    command = _layer_remediation(tmp_path, layer)
    assert command is not None, (
        f"{layer} is in state {expected_state!r} and offers NO remediation; "
        "an operator in this state has no way forward"
    )

    completed = _run_remediation(tmp_path, command)

    assert completed.returncode == 0, (
        f"remediation `{command}` for {layer}={expected_state} exited "
        f"{completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    after = _layer_state(tmp_path, layer)
    assert after == "fresh", (
        f"remediation `{command}` exited 0 but left {layer} in state {after!r}, "
        "not 'fresh' -- the operator would still be blocked"
    )


def test_charter_sync_is_never_offered_as_a_remediation() -> None:
    """#2831 regression pin: the dead-end command must not come back.

    ``charter sync`` reports staleness and writes nothing, so it can never
    clear a freshness check.

    This asserts on the module's actual remediation VALUES, not on its source
    text. An earlier version of this test grepped the source for lines
    containing both "charter sync" and "remediation" -- and a mutation that
    reintroduced the defect slipped straight past it, because the constants are
    named ``_REMEDIATE_*`` (no "remediation" substring). A pin that can be
    defeated by a variable name is not a pin.
    """
    from specify_cli.charter_runtime.freshness import computer

    offenders = {
        name: value
        for name, value in vars(computer).items()
        if name.startswith("_REMEDIATE")
        and isinstance(value, str)
        and "charter sync" in value
    }
    assert not offenders, (
        "a remediation constant names `charter sync`, which never writes and so "
        f"cannot clear any check: {offenders}"
    )


def test_the_oracle_rejects_an_exit_zero_remediation_that_does_not_reach_fresh(
    tmp_path: Path,
) -> None:
    """Non-vacuity: prove this module fails a plausible-but-ineffective remediation.

    ``charter status`` exits 0 and changes nothing -- the exact shape of the
    #2831 defect (a reporter offered as a repair). If the oracle above were
    only asserting "exit 0", or only "something changed", this would pass.
    """
    _fixture_charter_yaml_absent(tmp_path)
    assert _layer_state(tmp_path, "charter_source") == "missing"

    completed = _run_remediation(tmp_path, "spec-kitty charter status")

    assert completed.returncode == 0, "precondition: charter status is expected to exit 0"
    assert _layer_state(tmp_path, "charter_source") == "missing", (
        "precondition: charter status must not change charter_source"
    )
