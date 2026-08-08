"""Mechanism-keyed gate: refuse a ``patch()`` that mutates a *shared* module object.

Originated in mission ``sync-sleep-count-3136-01KZ9B5A`` (FR-005, FR-010
condition ii, SC-007). ``unittest.mock._get_target`` splits a target on the
**last** dot and imports the left half, so ``patch("{mod}.attr")`` mutates
whatever ``{mod}`` resolves to. When that object is a module the naming module
does not own — the stdlib ``time`` reached through some other first-party
module, say — the recorder handed to the test is **process-global**, and any
concurrent caller of the same shared attribute changes the test's verdict. That
is the defect class, whatever it is spelled. This file is idiom-independent: it
does not assume or verify any particular fix (a module-local alias, an instance
attribute, or anything else) — it only asks whether a shared-object patch is
read by a count/equality assertion, and freezes today's known offenders in a
shrink-only baseline.

``{mod}`` there is a **brace placeholder, and deliberately so** — it is not a
module path and cannot be mined. ``scripts/check_patch_targets.py`` extracts
targets with a regex over *raw source*, so it reads this docstring and cannot
tell prose from a live call; a concrete dotted path spelled here, even purely as
an illustration, is imported for real and exits 1 in an ``[ENFORCED]`` CI job.
Keep the placeholder: the regex stops dead at the ``{``. The same shape guards
``tests/architectural/test_patch_seam_census_control.py``, which binds its seam
to a name and interpolates it for exactly this reason.

**This gate resolves imports.** It is not a pure text scan: the patch-target
verdicts come from :func:`scripts.check_patch_targets.resolve_patch_target`,
which imports the penultimate segment, and the census this gate consumes
resolves ``asname``-aliased imports to the same callee as the plain form. Any
inline description claiming this file performs no call-graph resolution is
wrong — correct it rather than working around it, because a misleading
self-description is precisely what produced the mission this gate originated
in (``tests/sync/tracker/test_saas_client.py``'s docstring once asserted a
patch bound something it did not).

Split from ``tests/sync/_leak_guard.py`` — one concept, two enforcement points
--------------------------------------------------------------------------
``tests/sync/_leak_guard.py`` snapshots a watched global's **value** across a
test node and reports **teardown residue** at runtime (``_WATCHED_GLOBALS``,
whose ``_WatchedGlobal(module_path, attr_path, description)`` vocabulary the
baseline rows below reuse); **this gate is a static AST reader over test source
that never runs a test**, so it sees patches the leak guard cannot and knows
nothing about residue. Without that distinction the next author adds
``time.sleep`` to ``_WATCHED_GLOBALS`` and gets a guard that structurally cannot
fire — ``time.sleep`` is correctly absent there because ``patch``'s own teardown
restores it. One authority for the vocabulary, two enforcement points; not two
registries of the same kind.

The predicate has two halves, and both are enforced in code
----------------------------------------------------------
* **Mechanism half** — the target's penultimate segment resolves to a module
  whose ``__name__`` differs from the dotted path (reach-through), or to a module
  that is not first-party (foreign). Measured over ``tests/sync/`` this alone
  flags 270 sites, including all 131 ``…saas_client.httpx.Client`` sites.
* **Read half** — the mock the site binds is read by a **count or equality
  assertion** in the same test node. A ``side_effect=`` *assignment* drives a
  mock but asserts nothing, so it is deliberately not a read.

The mechanism half alone would demand a 131-row baseline for ``httpx.Client``
and be unshippable; the read half alone would flag ordinary own-module patches.
Both halves are required, so the read-side condition is code, not a docstring.

The predicate itself is **not reimplemented here**. It is consumed from
``scripts/patch_seam_census.py`` (WP03), which owns the single resolver and the
single verdict vocabulary. A second implementation would be the duplicate
authority the charter's canonical-sources standing order forbids.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.check_patch_targets import PatchTargetOutcome  # noqa: E402
from scripts.patch_seam_census import (  # noqa: E402
    PATCH_FORMS,
    CensusResult,
    PatchSite,
    default_first_party_roots,
    run_census,
)

pytestmark = [pytest.mark.architectural]

# ---------------------------------------------------------------------------
# Scope declarations. Every one of these is a *decision*, not a fact, so each is
# named at module scope and echoed into the report an arm prints — the same
# discipline `patch_seam_census.py` applies to `first_party_roots` and
# `seam_module`. A scope decision that exists only inside a comparison is
# unauditable, and this mission exists because a count was pinned to the wrong
# world.
# ---------------------------------------------------------------------------

#: The enforced scope (R-2). `tests/cli` is excluded by C-001, not by oversight.
ENFORCED_SCOPE: Final = Path("tests/sync")

#: The seam this mission's R-1 fix installs.
SEAM_MODULE: Final = "specify_cli.tracker.saas_client"

#: Files SC-007 item 1 requires the gate to have actually opened. A count floor
#: ("scanned >= 22") is satisfied by globbing any 22 files and never opening
#: `tests/sync/tracker/` at all, which is why this is a named set.
REQUIRED_SCANNED_FILES: Final = frozenset(
    {
        "tests/sync/tracker/test_saas_client.py",
        "tests/sync/tracker/test_saas_client_origin.py",
        "tests/sync/test_final_sync_diagnostics.py",
        "tests/sync/test_git_metadata.py",
    }
)

#: Verdicts that make the patched object *shared* — the mechanism half.
#: `own_module` is deliberately absent: patching a module's own attribute is the
#: correct idiom, and post-FR-012 every `saas_client` sleep patch is one.
MECHANISM_VERDICTS: Final = frozenset(
    {PatchTargetOutcome.REACH_THROUGH.value, PatchTargetOutcome.FOREIGN.value}
)

#: Exactly three structural answers, modelled on `_inert_slots.py`'s
#: `DISPOSITIONS`. There is deliberately no `accepted`, no `wont-fix`, no
#: `by-design`: a row may be fixed, rewritten, or reclassified as a gate defect
#: — "leave it alone" is not a disposition.
DISPOSITIONS: Final = frozenset(
    {
        "route-through-a-module-local-alias",
        "assert-on-an-owned-observable",
        "fix-the-gate-predicate",
    }
)

#: Zero entries, permanently — pinned by `test_the_allowlist_is_empty`. The
#: BASELINE is the mutable surface; an allowlist entry would be permanently
#: excused, whereas a baseline row is debt with a named owner and a required
#: structural fix standing behind it.
ALLOWLIST: frozenset[str] = frozenset()

_BASELINE_KEY: Final = "test_shared_module_object_patches"
_BASELINE_COUNT_SUBKEY: Final = "flagged_sites"
_BASELINES_PATH: Final = Path(__file__).with_name("_baselines.yaml")

_UNASSIGNED_OWNER: Final = "unassigned"


# ---------------------------------------------------------------------------
# Baseline loading. The published module-scope frozenset is what
# `test_ratchet_baselines.py` introspects with `len()`; it must exist at module
# scope and nowhere else, because `_import_module_attr` takes `getattr` then
# `len` and can read nothing computed inside a test function.
# ---------------------------------------------------------------------------


def _load_baseline_section() -> dict[str, Any]:
    """The `_baselines.yaml` section this gate owns."""
    data = yaml.safe_load(_BASELINES_PATH.read_text(encoding="utf-8"))
    section = data[_BASELINE_KEY]
    if not isinstance(section, dict):
        raise TypeError(
            f"`_baselines.yaml::{_BASELINE_KEY}` must be a mapping carrying "
            f"`{_BASELINE_COUNT_SUBKEY}` plus the `rows` list."
        )
    return section


def _row_key(row: dict[str, Any]) -> str:
    """The identity of one frozen row: `site | target | assertion-form`.

    A triple rather than a bare `file:line`, so the row cannot be widened by
    restatement — repointing an existing row at a different target or a weaker
    assertion form mints a *new* key and shows up as a set difference.
    """
    return f"{row['site']} | {row['module_path']}.{row['attr_path']} | {row['assertion_form']}"


def _baseline_rows() -> list[dict[str, Any]]:
    rows = _load_baseline_section()["rows"]
    return [dict(row) for row in rows]


#: The frozen shrink-only residue, as row identities. Published at module scope
#: **because that is the only shape the charter ratchet can read**:
#: `test_ratchet_baselines._import_module_attr` does `import_module` then
#: `getattr` then `len`, so a dict, a list, a local, or a value computed inside a
#: test function cannot be registered.
BASELINE_SITES: frozenset[str] = frozenset(_row_key(row) for row in _baseline_rows())


# ---------------------------------------------------------------------------
# The gate itself
# ---------------------------------------------------------------------------


def _census(paths: Sequence[Path]) -> CensusResult:
    """One analysis pass over *paths*, using WP03's analyzer and resolver."""
    return run_census(
        paths,
        default_first_party_roots(_REPO_ROOT),
        frozenset(PATCH_FORMS),
        SEAM_MODULE,
    )


def _read_keys(result: CensusResult) -> set[tuple[str, str, str]]:
    """`(file, node, mock)` triples read by a count-or-equality **assertion**.

    Built from ``result.assertions`` and deliberately **not** from
    ``result.drives``. That is a **declared scoping decision**, not a claim that
    a ``side_effect=`` drive is harmless: FR-005 scopes this gate to sites whose
    mock is *read by an assertion*, and a drive asserts nothing, so it is out of
    that scope. T032 directed the exclusion, and folding drives in adds 33 rows
    to the baseline — 3 of them the ``mock_http_cls`` sites in
    ``test_origin_integration.py``, the only ``httpx.Client`` sites with any
    read-side form at all.

    **A drive absolutely can corrupt a verdict, and an earlier revision of this
    docstring wrongly said it could not.** ``test_git_metadata.py:522`` is
    ``patch("…git_metadata.time.monotonic", side_effect=[1.0, 10.0])`` — an
    *exhaustible* sequence on a process-global attribute. A concurrent caller
    consuming one element raises ``StopIteration`` and reds the test for a reason
    that has nothing to do with the code under test. That is the same flake class
    ``RL-016`` records for WP02's guard. It is a real, uncovered sub-class, filed
    as ``RL-034``, not a reason to widen this predicate.

    **Known limitation of the join, so "22" is not read as exhaustive.** The key
    is ``(file, node_id, mock_name)``, so a mock asserted in a *different* node
    than the one that patches it — passed to a helper, or bound by a fixture — is
    invisible to this half. WP02's own guard is exactly that shape: its
    ``_dual_recorder_window`` context manager patches, and ``_report`` reads.
    """
    return {(a.file, a.node_id, a.mock_name) for a in result.assertions}


def flagged_sites(result: CensusResult) -> list[PatchSite]:
    """Sites failing **both** halves of the predicate, in file order."""
    reads = _read_keys(result)
    return [
        site
        for site in result.sites
        if site.verdict in MECHANISM_VERDICTS
        and site.binds
        and (site.file, site.node_id, site.binds) in reads
    ]


def _assertion_form(result: CensusResult, site: PatchSite) -> str:
    forms = sorted(
        {
            a.assertion_form
            for a in result.assertions
            if (a.file, a.node_id, a.mock_name) == (site.file, site.node_id, site.binds)
        }
    )
    return "+".join(forms)


def _flagged_keys(result: CensusResult) -> frozenset[str]:
    return frozenset(
        f"{site.file}:{site.line} | {site.target} | {_assertion_form(result, site)}"
        for site in flagged_sites(result)
    )


# ---------------------------------------------------------------------------
# SC-007 item 1 — name what was scanned, do not merely count it
# ---------------------------------------------------------------------------


def test_the_gate_names_the_files_it_opened() -> None:
    """SC-007 item 1: the scanned set is *named*, and contains the four files.

    A `scanned_files >= 22` floor is satisfied by globbing any 22 files under
    `tests/` while never opening `tests/sync/tracker/` — the squad's named cheat.
    Set containment over named paths cannot be satisfied that way.
    """
    result = _census([ENFORCED_SCOPE])
    opened = frozenset(site.file for site in result.sites)
    print(f"[WP05 gate] enforced_scope={ENFORCED_SCOPE}")
    print(f"[WP05 gate] files_scanned={result.files_scanned}")
    print(f"[WP05 gate] files_with_patch_sites={len(opened)}")
    for name in sorted(REQUIRED_SCANNED_FILES):
        print(f"[WP05 gate] opened: {name}")

    assert opened >= REQUIRED_SCANNED_FILES, (
        "The gate did not open the files SC-007 item 1 names. Missing: "
        f"{sorted(REQUIRED_SCANNED_FILES - opened)}. A gate that reports a count "
        "floor without opening `tests/sync/tracker/` measures nothing about this "
        "mission's defect class."
    )


# ---------------------------------------------------------------------------
# SC-007 item 3 — self-mutation arms
#
# Each writes a synthetic module carrying a form that is ABSENT from the tree
# today and requires the gate to flag it. A gate that globbed the wrong tree,
# lost its read-side half, or keyed on the literal string `time.sleep` fails
# these and passes everything else, which is the whole point.
# ---------------------------------------------------------------------------

_SYNTHETIC_DECORATOR_SLEEP = '''
"""Form absent post-FR-012: a decorator patch of the pre-fix seam, count-read."""
from unittest.mock import patch


@patch("specify_cli.tracker.saas_client.time.sleep")
def test_synthetic(mock_sleep):
    assert mock_sleep.call_count == 1
'''

_SYNTHETIC_SUBPROCESS_RUN = '''
"""Mechanism, not `time.sleep`: the same predicate must catch `subprocess.run`."""
from unittest.mock import patch


@patch("specify_cli.sync.git_metadata.subprocess.run")
def test_synthetic(mock_run):
    assert mock_run.call_count == 1
'''

_SYNTHETIC_CONTEXT_MANAGER_SIDE_EFFECT = '''
"""The two blind spots: a context-manager patch AND a `side_effect=` sink."""
from unittest.mock import patch


def test_synthetic():
    recorded = []
    with patch(
        "specify_cli.tracker.saas_client.time.monotonic", side_effect=recorded.append
    ):
        pass
    assert recorded == [1.0, 2.0]
'''


def _write_synthetic(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _flagged_targets(path: Path) -> frozenset[str]:
    result = _census([path])
    return frozenset(site.target for site in flagged_sites(result))


@pytest.mark.parametrize(
    ("name", "source", "expected_target"),
    [
        (
            "syn_decorator.py",
            _SYNTHETIC_DECORATOR_SLEEP,
            f"{SEAM_MODULE}.time.sleep",
        ),
        (
            "syn_subprocess.py",
            _SYNTHETIC_SUBPROCESS_RUN,
            "specify_cli.sync.git_metadata.subprocess.run",
        ),
        (
            "syn_contextmanager.py",
            _SYNTHETIC_CONTEXT_MANAGER_SIDE_EFFECT,
            f"{SEAM_MODULE}.time.monotonic",
        ),
    ],
    ids=["decorator-sleep", "subprocess-run-mechanism", "contextmanager-side-effect"],
)
def test_the_gate_flags_a_form_absent_from_the_tree(
    tmp_path: Path, name: str, source: str, expected_target: str
) -> None:
    """SC-007 item 3: three self-mutation arms, three absent forms.

    `subprocess.run` is the load-bearing one: it proves the predicate is keyed on
    the **mechanism** (a shared module object reached through a first-party one)
    rather than on the string `time.sleep`, so one rule closes `time`, `secrets`,
    `subprocess`, `random` and `os` together.
    """
    path = _write_synthetic(tmp_path, name, source)
    flagged = _flagged_targets(path)
    print(f"[WP05 gate] self-mutation {name}: flagged={sorted(flagged)}")

    assert flagged == frozenset({expected_target}), (
        f"The gate did not flag the synthetic form in {name}. Expected exactly "
        f"{{{expected_target!r}}}, observed {sorted(flagged)}. A gate that misses "
        "a form absent from the tree is vacuous on the forms it has never seen."
    )


# ---------------------------------------------------------------------------
# SC-007 item 5 — the frozen shrink-only baseline
#
# The owner helpers come from `_inert_slots.py`: it already owns the vocabulary
# for "has this owner finished?" and reimplementing it here would be a second
# authority for the same question.
# ---------------------------------------------------------------------------

from tests.architectural._inert_slots import (  # noqa: E402
    owner_exists,
    owner_is_complete,
)

_MISSION_SLUG: Final = "sync-sleep-count-3136-01KZ9B5A"


def test_the_allowlist_is_empty() -> None:
    """The allowlist never grows; the baseline is the only mutable surface.

    Copied from `test_no_inert_schema_slots.test_allowlist_is_empty`. An
    allowlist entry is permanently excused and carries no owner; a baseline row
    is debt that a shrink-only ratchet, a named owner and an owner-completion arm
    all stand behind. Keeping the allowlist provably empty is what stops the
    weaker construct being reached for.
    """
    assert frozenset() == ALLOWLIST, (
        f"`ALLOWLIST` must stay empty; found {sorted(ALLOWLIST)}. A site that "
        "cannot be fixed now belongs in the baseline with an owner, not here."
    )


def test_the_baseline_equals_the_gate_flagged_set() -> None:
    """Set equality, printing the symmetric difference — never a count.

    Equal counts over unequal sets is a hand-maintained list that has drifted.
    Worse in one direction than the other: a baseline row with **no**
    corresponding flagged site is frozen in forever, because the ratchet is
    shrink-only and nothing can ever remove it. A count-only check passes on
    exactly that baseline; set equality is the only arm that catches it.
    """
    result = _census([ENFORCED_SCOPE])
    observed = _flagged_keys(result)
    print(f"[WP05 gate] flagged sites={len(observed)}  baseline rows={len(BASELINE_SITES)}")
    for key in sorted(observed):
        print(f"[WP05 gate] flagged: {key}")

    missing_from_baseline = sorted(observed - BASELINE_SITES)
    frozen_without_a_site = sorted(BASELINE_SITES - observed)
    assert observed == BASELINE_SITES, (
        "The frozen baseline and the gate's flagged set disagree.\n"
        f"  Flagged but not frozen (NEW in-class assertion — fix it, do not add a row):\n"
        f"    {missing_from_baseline}\n"
        f"  Frozen but not flagged (a row nothing can ever remove — delete it):\n"
        f"    {frozen_without_a_site}"
    )


def test_every_baseline_row_carries_a_closed_vocabulary_disposition() -> None:
    """A row may be fixed, rewritten, or reclassified — never excused."""
    observed = frozenset(row["disposition"] for row in _baseline_rows())
    print(f"[WP05 gate] dispositions in use: {sorted(observed)}")

    assert observed <= DISPOSITIONS, (
        f"Baseline rows carry disposition(s) outside the closed vocabulary: "
        f"{sorted(observed - DISPOSITIONS)}. There is deliberately no `accepted`, "
        "no `wont-fix` and no `by-design`."
    )


def test_every_baseline_row_carries_the_full_identity_triple() -> None:
    """`file:line` + target + assertion form, so a row cannot be widened.

    Without the triple a row reads as "this file is excused" and can be silently
    repointed at a different, weaker assertion at the same line.
    """
    required = frozenset(
        {
            "site",
            "module_path",
            "resolved_module",
            "attr_path",
            "verdict",
            "assertion_form",
            "binds",
            "node_id",
            "owner",
            "disposition",
        }
    )
    incomplete = sorted(
        row.get("site", "<no site>")
        for row in _baseline_rows()
        if not required <= frozenset(row)
    )
    assert incomplete == [], (
        f"Baseline row(s) missing required fields: {incomplete}. Every row is a "
        "`file:line` + patch target + assertion-form triple plus its owner and "
        "disposition, so the baseline cannot be widened by restatement."
    )


def test_every_named_owner_resolves() -> None:
    """`WP42` and `mission:typo` read as "never complete" exactly like `unassigned`.

    Copied from `test_no_inert_schema_slots.test_every_named_owner_resolves`: an
    owner that does not exist is indistinguishable from live debt, so a typo
    parks a row here forever while looking like work someone is doing.
    """
    unresolved = sorted(
        f"{row['site']} -> {row['owner']}"
        for row in _baseline_rows()
        if not owner_exists(row["owner"], root=_REPO_ROOT, mission=_MISSION_SLUG)
    )
    assert unresolved == [], (
        f"Baseline row(s) name an owner that resolves to nothing: {unresolved}."
    )


def _rows_surviving_their_owner(rows: Sequence[dict[str, Any]]) -> list[str]:
    return sorted(
        f"{row['site']} -> {row['owner']}"
        for row in rows
        if owner_is_complete(row["owner"], root=_REPO_ROOT, mission=_MISSION_SLUG)
    )


def test_a_baseline_entry_does_not_survive_its_owner() -> None:
    """The anti-weasel arm: a row fails the moment its named owner completes.

    This is what stops a frozen baseline becoming permanent, and it is strictly
    stronger than a tracker ticket. Its twin below is not optional: every row
    here is `unassigned` today (see the baseline header for why that is the
    honest owner rather than this mission), and `unassigned` is never complete —
    so this assertion would pass without exercising anything at all.
    """
    survivors = _rows_surviving_their_owner(_baseline_rows())
    assert survivors == [], (
        f"Baseline row(s) outlived the work that was supposed to remove them: "
        f"{survivors}. Either the fix landed and the row should go, or the owner "
        "completed without doing it."
    )


def test_the_owner_completion_arm_fires_for_a_completed_owner() -> None:
    """Anti-weasel twin for the arm above — it must be able to red.

    A completed owner is injected into a synthetic row set. If the arm cannot
    catch it, the arm is passing because nothing ever completes rather than
    because nothing has outlived its owner.
    """
    completed = _completed_owner()
    synthetic = [{"site": "tests/sync/synthetic.py:1", "owner": completed}]
    survivors = _rows_surviving_their_owner(synthetic)
    print(f"[WP05 gate] anti-weasel twin: injected completed owner={completed!r}")

    assert survivors == [f"tests/sync/synthetic.py:1 -> {completed}"], (
        "The owner-completion arm did not fire for an owner that has completed, "
        f"so it cannot fail for a real row either. Observed: {survivors}."
    )


def _completed_owner() -> str:
    """A real owner token that `owner_is_complete` answers True for.

    Derived from the event log rather than hardcoded: a hardcoded WP id stops
    being complete the moment the mission is renumbered, and the twin would then
    silently stop testing anything.
    """
    from tests.architectural._inert_slots import (  # noqa: PLC0415
        COMPLETED_LANES,
        _mission_work_packages,
    )

    states = _mission_work_packages(_REPO_ROOT, _MISSION_SLUG)
    for wp_id, state in sorted(states.items()):
        if state.get("lane") in COMPLETED_LANES:
            return wp_id
    pytest.skip(
        "No work package in this mission has reached a completed lane yet, so the "
        "anti-weasel twin has nothing real to inject. This skip is itself a "
        "signal: re-run once a dependency is approved."
    )


def test_the_baseline_size_is_registered_with_the_charter_ratchet() -> None:
    """The registration arm — BLOCKER-3 made impossible to reintroduce.

    An unregistered key is read by no comparison and its growth fails nothing;
    two of the twelve pre-existing keys have sat inert for exactly that reason
    with the suite green. This arm pins the recorded integer to the live size, so
    the registration cannot drift into a number nobody compares against anything.
    """
    recorded = _load_baseline_section()[_BASELINE_COUNT_SUBKEY]
    live = len(BASELINE_SITES)
    print(f"[WP05 gate] recorded={recorded} live={live}")

    assert recorded == live, (  # golden-count: cardinality-is-contract
        f"`_baselines.yaml::{_BASELINE_KEY}.{_BASELINE_COUNT_SUBKEY}` records "
        f"{recorded} but the module publishes {live} rows. The ratchet compares "
        "the recorded integer against `len(BASELINE_SITES)`, so a stale integer "
        "silently widens or narrows what the ratchet is guarding."
    )
