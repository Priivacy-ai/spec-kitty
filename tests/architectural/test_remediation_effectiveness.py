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


def _seed_project(repo_root: Path, *, previously_generated: bool) -> None:
    """Minimal project shape the fixtures share.

    ``previously_generated`` reproduces the config a successful
    ``charter generate`` leaves behind -- crucially the ``charter:`` pointer.
    This is NOT cosmetic. An earlier revision of this module seeded only the
    pointer-less shape, and that gap hid a critical defect: a proposed
    remediation moved the unparseable charter.yaml aside and then died in
    ``provision_mission_type_activations`` resolving that very pointer, leaving
    the project with NO charter.yaml. Every case is therefore driven in BOTH
    shapes -- a remediation that only works on a never-generated project is not
    a remediation for the state real operators are in.
    """
    (repo_root / ".kittify").mkdir(parents=True, exist_ok=True)
    config = "activated_directives: []\n"
    if previously_generated:
        config += (
            "mission_type_activations:\n- software-dev\n"
            "charter: .kittify/charter/charter.yaml\n"
        )
    (repo_root / ".kittify" / "config.yaml").write_text(config, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=repo_root, check=True)


def _fixture_charter_yaml_absent(repo_root: Path, *, previously_generated: bool = False) -> None:
    """F1 -- no charter at all: ``charter_source: missing`` / ``synced_bundle: missing``."""
    _seed_project(repo_root, previously_generated=previously_generated)
    (repo_root / _CHARTER_DIR).mkdir(parents=True, exist_ok=True)


def _fixture_charter_yaml_unparseable(repo_root: Path, *, previously_generated: bool = False) -> None:
    """F2 -- present but broken: ``charter_source: invalid`` / ``synced_bundle: stale``."""
    _seed_project(repo_root, previously_generated=previously_generated)
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


#: (layer, fixture, expected non-passing state, previously_generated). Both
#: layers are driven for the fixture because ``synced_bundle`` is a structural
#: echo of ``charter_source`` (single-entry ``_BUNDLE_FILES``) -- a fix that
#: clears one but not the other still leaves the operator blocked. Both config
#: shapes are driven because a remediation that only works on a never-generated
#: project is not a remediation (see ``_seed_project``).
#:
#: ``charter_source: invalid`` / ``synced_bundle: stale`` are absent on purpose:
#: they emit no remediation, and are covered by
#: ``test_states_with_no_effective_remediation_offer_no_command`` below.
_CASES = [
    ("charter_source", "missing", False),
    ("synced_bundle", "missing", False),
]


@pytest.mark.parametrize(("layer", "expected_state", "previously_generated"), _CASES)
def test_remediation_clears_the_state_that_emitted_it(
    tmp_path: Path,
    layer: str,
    expected_state: str,
    previously_generated: bool,
) -> None:
    _fixture_charter_yaml_absent(tmp_path, previously_generated=previously_generated)

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
        f"remediation `{command}` for {layer}={expected_state} "
        f"(previously_generated={previously_generated}) exited {completed.returncode}\n"
        f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    after = _layer_state(tmp_path, layer)
    assert after == "fresh", (
        f"remediation `{command}` exited 0 but left {layer} in state {after!r}, "
        "not 'fresh' -- the operator would still be blocked"
    )


@pytest.mark.parametrize("previously_generated", [False, True])
@pytest.mark.parametrize(("layer", "expected_state"), [
    ("charter_source", "invalid"),
    ("synced_bundle", "stale"),
])
def test_states_with_no_effective_remediation_offer_no_command(
    tmp_path: Path,
    layer: str,
    expected_state: str,
    previously_generated: bool,
) -> None:
    """An unrepairable state must show NO command, not a command that cannot work.

    No write path in this codebase can repair an unparseable ``charter.yaml``
    (every one round-trip-parses it). Moving the file aside first looks like the
    answer and is not: with a ``charter:`` pointer in config.yaml -- which every
    previously-generated project has -- generation dies AFTER the move and the
    operator is left with no charter.yaml at all. Showing no command is strictly
    better than that, so this pins the exemption rather than a remediation.
    """
    _fixture_charter_yaml_unparseable(tmp_path, previously_generated=previously_generated)

    assert _layer_state(tmp_path, layer) == expected_state
    assert _layer_remediation(tmp_path, layer) is None, (
        f"{layer}={expected_state} offers a command, but no command can clear it; "
        "an ineffective remediation is worse than none"
    )
    detail = getattr(compute_freshness(tmp_path), layer).detail
    if layer == "charter_source":
        assert detail, "an exempt state must still explain itself to the operator"


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
    """Non-vacuity: the oracle's own assertion must FAIL on a useless remediation.

    This exercises the assertion, it does not merely set up the conditions for
    it. An earlier revision of this test stopped after checking that
    ``charter status`` exits 0 and changes nothing, and its docstring claimed to
    "prove this module fails" such a remediation -- which it did not; both
    reviewers of PR #3585 flagged the gap independently. The assertion block is
    now run for real inside ``pytest.raises``.

    ``charter status`` is the right stand-in: it exits 0 and reports, exactly
    the shape of the #2831 defect (a reporter offered as a repair).
    """
    _fixture_charter_yaml_absent(tmp_path, previously_generated=True)
    assert _layer_state(tmp_path, "charter_source") == "missing"

    completed = _run_remediation(tmp_path, "spec-kitty charter status")
    assert completed.returncode == 0, "precondition: charter status is expected to exit 0"

    # The oracle's own check, run against a deliberately ineffective command.
    with pytest.raises(AssertionError, match="not 'fresh'"):
        after = _layer_state(tmp_path, "charter_source")
        assert after == "fresh", (
            f"remediation `spec-kitty charter status` exited 0 but left "
            f"charter_source in state {after!r}, not 'fresh' -- the operator "
            "would still be blocked"
        )


@pytest.mark.parametrize("layer", ["charter_source", "synced_bundle"])
def test_absent_charter_with_dangling_pointer_offers_no_command(
    tmp_path: Path, layer: str
) -> None:
    """A previously-generated project whose charter.yaml vanished gets NO command.

    `charter generate` cannot run here: `.kittify/config.yaml` still carries a
    `charter:` pointer, and `pack_manager.resolve_activation_write_target` fails
    loud by design on a dangling one (INV-5 / #2530), so generation dies before
    writing anything. The documented recovery, `spec-kitty upgrade`, is
    interactive and so cannot be handed over as a runnable remediation either.

    Naming a command that exits non-zero here is precisely the #2831 defect, so
    the honest output is none -- pinned separately from the never-generated
    shape above, which `charter generate` genuinely does clear.
    """
    _fixture_charter_yaml_absent(tmp_path, previously_generated=True)

    assert _layer_state(tmp_path, layer) == "missing"
    assert _layer_remediation(tmp_path, layer) is None, (
        "a dangling charter: pointer makes `charter generate` fail closed; "
        "offering it would hand the operator a command that cannot work"
    )
