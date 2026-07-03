"""Architectural gates for the ``agent tasks`` command surface (``tasks.py``).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` — contract:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/gate-contracts.md``.

Gate 2 — whole-file LOC ceiling (FR-011, NFR-004, SC-001)
---------------------------------------------------------
``src/specify_cli/cli/commands/agent/tasks.py`` is the repository's worst
god-module hotspot. This gate pins its size so the wave-2 relocation WPs can
only shrink it — regrowth is a RED test, not a review judgment call.

Form: a plain scalar ceiling over ``len(source.splitlines())``. The CT1
``composite_key`` carry-forward is deliberately N/A here — that convention
exists for line-keyed allowlist entries that drift with benign edits; a
whole-file scalar ceiling has no per-line keys (research.md D5, DIRECTIVE_041).

Non-vacuity (DIRECTIVE_043 / spec C-006): the self-mutation test drives the
SAME extracted check function (``_loc_of``) with a synthetic source one line
over the ceiling and requires the comparison to fail — proving the gate is
wired to fire, without ever mutating the live file.

Gate 1 — AST 0-inline-dumps (FR-007, SC-002)
--------------------------------------------
Every ``.py`` under the ``src/specify_cli/cli/commands/agent/`` directory glob
(all current AND future siblings — closing move-next-door evasion) is AST-parsed
and swept for inline ``json.dumps`` in all four evasion forms:

1. attribute call — ``json.dumps(...)`` under ``import json``;
2. module alias — ``_json.dumps(...)`` under ``import json as _json``;
3. from-import — ``dumps(...)`` / ``d(...)`` under ``from json import dumps
   [as d]``;
4. local rebinding — ``x = json.dumps`` (or ``x = dumps``, including chains)
   plus calls of the bound name.

AST call/assign-node inspection is inherently immune to docstring/string
mentions (research.md D6). ``src/specify_cli/agent_tasks_ports.py`` — the ONE
sanctioned ``json.dumps`` home (the ``RealRender`` adapter every command routes
through) — is deliberately OUTSIDE the glob.

Allowlist honesty note (FR-007 / C-006): gate-contracts.md Gate 1 predicted an
empty allowlist at ship time; that prediction held for the mission's remit (the
``tasks*.py`` family surface ships at 0 sites — asserted below), but the WP09
sweep found nine PRE-EXISTING non-tasks siblings (``status.py``,
``mission_finalize.py``, …) carrying inline-dumps sites that predate this
mission and belong to the #2289–#2293 unshim cluster's surface, not this
mission's owned files. Rewriting them here would violate the mission's
ownership fence, so they are enrolled via the contract's own exception
mechanism: repo-relative paths, shrink-only (count ratchet + stale-entry
eviction below). No ``tasks*.py`` path may ever join the allowlist.

Non-vacuity (DIRECTIVE_043 / C-006): one theater test PER evasion form drives
the SAME detector (``_json_dumps_offenders``) with a synthetic offender source
and requires a non-empty report.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TASKS_PY = _REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "agent" / "tasks.py"

# _CEILING ratchet-down protocol (FR-011):
# * Starts at 4569 — the exact size of tasks.py when this gate landed (WP01).
# * WP02 (shared-helpers move to ``tasks_shared.py``) ratcheted 4569 → 4017.
# * WP03 (coord routers move to ``tasks_command_adapters.py``) 4017 → 3927.
# * WP04 (render-seam unification: status Render subclass deleted, compact
#   emission sites routed through ``Render.json_envelope``) 3927 → 3926.
# * WP05 (move_task family — ``_do_move_task`` + 23 ``_mt_*`` + ``_MoveTaskState``
#   + ``_default_move_task_ports`` — moved to ``tasks_move_task.py``; +11 lines
#   of strict-mypy explicit ``as`` re-export forms + rationale comments for the
#   D7 seam symbols the relocated bodies route via ``_tasks.<attr>`` and the
#   two helpers ``tests/agent`` imports from ``tasks``) 3926 → 3046.
# * WP06 (map_requirements family — ``_do_map_requirements`` + 11 ``_mr_*`` +
#   ``_MapReqState`` + ``_default_map_requirements_ports`` — moved to
#   ``tasks_map_requirements.py``; ``plan_mapping`` kept as an explicit ``as``
#   re-export for its sentinel seam; ``SPEC_MD_FILENAME`` stays tasks.py-owned,
#   routed via ``_tasks.<attr>``) 3046 → 2524.
# * WP07 (status family — ``_do_status`` + 14 ``_st_*`` + ``_StatusState`` +
#   ``_default_status_ports`` — moved to ``tasks_status_cmd.py``;
#   ``build_status_view`` kept as an explicit ``as`` re-export for its sentinel
#   seam; ``get_status_read_root`` kept for its D7 patch seam) 2524 → 1979.
# * WP08 (mark_status + finalize families — ``_do_mark_status`` + 9 ``_ms_*``
#   + ``_MarkStatusState`` + ``_default_mark_status_ports`` moved to
#   ``tasks_mark_status.py``; ``_do_finalize_tasks`` + 4 ``_ft_*`` +
#   ``_FinalizeState`` + ``_default_finalize_ports`` moved to
#   ``tasks_finalize.py`` — ALL five command families now out of tasks.py;
#   ``bootstrap_canonical_state`` / ``_normalize_task_id_input`` kept as
#   explicit ``as`` re-exports for their patch/import seams;
#   ``_resolve_inline_subtasks`` stays tasks.py-resident, routed via
#   ``_tasks.<attr>``; +12 lines of strict-mypy explicit ``as`` re-export
#   forms + rationale for ``resolve_feature_dir_for_mission`` /
#   ``emit_history_added`` — dual direct-use + routed-seam symbols) 1979 →
#   1470.
# * WP09 (final registration-shim sweep — the twelve straggler helpers moved
#   to their family modules: 6 → ``tasks_move_task`` (arbiter override pair,
#   #2155 bundle partition, coord event-path probe, event-field shaper,
#   reviewer detector), 4 → ``tasks_status_cmd`` (stall threshold, HiC marker,
#   staleness shapers), 1 → ``tasks_map_requirements`` (kind-aware tasks/ read
#   resolver), 1 → ``tasks_mark_status`` (inline-Subtasks resolver); each kept
#   as an explicit ``as`` re-export patch seam; dead import residue
#   (``candidate_feature_dir_for_mission``, ``EVENTS_FILENAME``, the
#   ``TaskIdResult`` vocabulary, ``_persist_inline_subtask_status``) dropped
#   with zero-external-reference evidence) 1470 → 1206.
# * Each relocation WP lowers _CEILING to the achieved tasks.py size IN THE
#   SAME COMMIT as the move (never a follow-up commit).
# * FINAL (WP09, FR-011): achieved = 1206; _CEILING = min(1206, 1400) = 1206.
#   Delta from the 4569 WP01 baseline: −3363 lines (−73.6%). Full ratchet
#   history: 4569 → 4017 → 3927 → 3926 → 3046 → 2524 → 1979 → 1470 → 1206 → 1205.
# * degod-follow-ups (constructor-DI collapse of the three coord-router
#   subclasses into a single ``seam_coord_router`` re-export): the three-symbol
#   ``tasks_command_adapters`` re-export block collapsed to one, achieved = 1205;
#   ratcheted _CEILING 1206 → 1205 in the same commit (relocation-ratchet rule).
#   What remains is exactly the IC-07 registration-shim taxonomy: the 9
#   ``@app.command`` wrappers (4 of them the deliberately-retained small
#   bodies: list_tasks / add_history / validate_workflow / list_dependents),
#   the ``app``/``console`` setup, the explicit ``as`` re-export seam surface
#   (~40 patched symbols, research.md D7), and ``__all__``.
# * If the honest final size had exceeded 1400: the WP moves to `blocked`, the
#   delta-from-4569 analysis goes to the Activity Log + a #2305 comment, and
#   the operator decides — never a self-certified higher ceiling.
_CEILING = 1205

# Standing mission-cap backstop (FR-011, squad HIGH): a ceiling above 1400 is
# an operator escalation, never a self-certified re-baseline — mechanically
# enforced so any future edit raising _CEILING past the cap is a RED collection
# error in its own right. The only path past 1400 is the blocked+escalate arm.
assert _CEILING <= 1400, (
    "ceiling above the mission cap is an operator escalation (FR-011), "
    "never self-certified"
)


def _loc_of(source: str) -> int:
    """Return the line count the ceiling is measured against.

    Extracted so the non-vacuity test can drive the exact enforcement path
    with synthetic source instead of mutating the live file.
    """
    return len(source.splitlines())


def test_tasks_py_stays_under_loc_ceiling() -> None:
    """Gate 2: ``tasks.py`` never grows past the ratcheted ceiling."""
    source = _TASKS_PY.read_text(encoding="utf-8")
    loc = _loc_of(source)
    assert loc <= _CEILING, (
        f"src/specify_cli/cli/commands/agent/tasks.py is {loc} lines, over the "
        f"ratcheted ceiling of {_CEILING}. Add behavior to sibling modules, not "
        "the registration shim. Relocation WPs must LOWER _CEILING to the "
        "achieved size in the same commit (see kitty-specs/"
        "tasks-py-degod-wave2-01KWH9EQ/contracts/gate-contracts.md Gate 2)."
    )


def test_tasks_py_gate_target_exists() -> None:
    """Sanity: the gated file exists — a rename/move cannot green the gate vacuously."""
    assert _TASKS_PY.is_file(), (
        f"LOC-ceiling gate target missing: {_TASKS_PY}. If tasks.py moved, "
        "re-point _TASKS_PY in the same commit — never delete this gate."
    )


def test_loc_ceiling_gate_fires_on_oversized_source() -> None:
    """DIRECTIVE_043 non-vacuity: a source of ``_CEILING + 1`` lines must fail.

    Drives the extracted ``_loc_of`` check (the exact function the live gate
    uses) with synthetic oversized source — the detector must report a LOC
    over the ceiling, proving the comparison is not gate theater.
    """
    oversized = "\n".join(f"x = {n}" for n in range(_CEILING + 1))
    assert _loc_of(oversized) == _CEILING + 1
    assert not _loc_of(oversized) <= _CEILING


def test_loc_ceiling_boundary_is_exact() -> None:
    """The ceiling is inclusive: exactly ``_CEILING`` lines passes, +1 fails."""
    at_ceiling = "\n".join("pass" for _ in range(_CEILING))
    assert _loc_of(at_ceiling) <= _CEILING
    assert not _loc_of(at_ceiling + "\npass") <= _CEILING


# ---------------------------------------------------------------------------
# Gate 1 — AST 0-inline-dumps over the command-surface directory glob
# (FR-007, SC-002; gate-contracts.md Gate 1)
# ---------------------------------------------------------------------------

_AGENT_COMMANDS_DIR = _REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "agent"

# NOTE: ``src/specify_cli/agent_tasks_ports.py`` is OUTSIDE this glob BY
# DESIGN — it is the one sanctioned ``json.dumps`` home (``RealRender``, the
# Render adapter every command's ``--json`` envelope routes through). Moving an
# emission site there means routing it through ``Render.json_envelope``, which
# is exactly the remediation this gate demands.

# Shrink-only exception set (FR-007 / C-006). These nine files carry
# PRE-EXISTING inline-dumps sites that predate mission
# tasks-py-degod-wave2-01KWH9EQ and belong to the #2289–#2293 unshim cluster's
# surface (NOT this mission's owned files — see the module docstring's
# allowlist honesty note). Contract semantics:
# * SHRINK-ONLY: entries may only be removed (count ratchet below); a file
#   cleaned of inline dumps MUST leave the set (stale-entry eviction below).
# * No ``tasks*.py`` path may ever join (the de-godded family surface ships
#   and stays at 0 sites — SC-002).
_DUMPS_ALLOWLIST: frozenset[str] = frozenset(
    {
        "src/specify_cli/cli/commands/agent/config.py",
        "src/specify_cli/cli/commands/agent/context.py",
        "src/specify_cli/cli/commands/agent/mission_accept_merge.py",
        "src/specify_cli/cli/commands/agent/mission_finalize.py",
        "src/specify_cli/cli/commands/agent/mission_parsing.py",
        "src/specify_cli/cli/commands/agent/release.py",
        "src/specify_cli/cli/commands/agent/status.py",
        "src/specify_cli/cli/commands/agent/tests.py",
        "src/specify_cli/cli/commands/agent/workflow.py",
    }
)

#: Ship-time size of ``_DUMPS_ALLOWLIST`` — the shrink-only high-water mark.
_DUMPS_ALLOWLIST_CEILING = 9

_DUMPS_REMEDIATION = (
    "route through ports.render.json_envelope — see "
    "kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/"
)

#: Predicate deciding whether an expression resolves to ``json.dumps``.
_DumpsReferencePredicate = Callable[[ast.expr], bool]


def _collect_json_import_bindings(tree: ast.Module) -> tuple[set[str], set[str]]:
    """(names bound to the ``json`` module, names bound to ``dumps``) imports."""
    json_module_aliases: set[str] = set()
    dumps_bindings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            json_module_aliases.update(
                alias.asname or "json" for alias in node.names if alias.name == "json"
            )
        elif isinstance(node, ast.ImportFrom) and node.module == "json":
            dumps_bindings.update(
                alias.asname or "dumps" for alias in node.names if alias.name == "dumps"
            )
    return json_module_aliases, dumps_bindings


def _absorb_rebinding_chains(
    tree: ast.Module,
    dumps_bindings: set[str],
    is_dumps_reference: _DumpsReferencePredicate,
) -> None:
    """Fixed point over rebinding chains (``a = json.dumps; b = a; b(...)``)."""
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and is_dumps_reference(node.value):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id not in dumps_bindings:
                        dumps_bindings.add(target.id)
                        changed = True


def _json_dumps_offenders(source: str, rel_path: str) -> list[str]:
    """Report every inline ``json.dumps`` usage in ``source`` (all four forms).

    Returns ``"<rel_path>:<line> (<form>)"`` strings. AST node inspection —
    docstrings/comments/string literals can never trip it. Detected forms
    (gate-contracts.md Gate 1):

    1. ``ast.Call`` on ``Attribute(value=Name(id=<json-alias>), attr="dumps")``
       — covering ``import json`` AND ``import json as <alias>``;
    2. ``from json import dumps`` (+ ``as <alias>``) and calls to that name;
    3. name-rebinding — any assignment whose RHS resolves to ``json.dumps`` /
       an imported ``dumps`` (chains included), and calls to the bound name.
    """
    tree = ast.parse(source)
    json_module_aliases, dumps_bindings = _collect_json_import_bindings(tree)

    def _is_dumps_reference(expr: ast.expr) -> bool:
        if isinstance(expr, ast.Attribute) and expr.attr == "dumps":
            return isinstance(expr.value, ast.Name) and expr.value.id in json_module_aliases
        return isinstance(expr, ast.Name) and expr.id in dumps_bindings

    _absorb_rebinding_chains(tree, dumps_bindings, _is_dumps_reference)

    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_dumps_reference(node.func):
            form = (
                "json.dumps attribute call"
                if isinstance(node.func, ast.Attribute)
                else "bound-name dumps call"
            )
            offenders.append(f"{rel_path}:{node.lineno} ({form})")
        elif isinstance(node, ast.Assign) and _is_dumps_reference(node.value):
            offenders.append(f"{rel_path}:{node.lineno} (json.dumps rebinding assignment)")
    return sorted(offenders)


def _iter_agent_command_files() -> list[Path]:
    """Every ``.py`` under the command-surface directory (future-proof rglob)."""
    return sorted(
        path
        for path in _AGENT_COMMANDS_DIR.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def test_no_inline_json_dumps_outside_allowlist() -> None:
    """Gate 1: 0 non-allowlisted inline ``json.dumps`` across ALL siblings."""
    assert _AGENT_COMMANDS_DIR.is_dir(), (
        f"AST dumps-gate target directory missing: {_AGENT_COMMANDS_DIR}. If the "
        "command surface moved, re-point _AGENT_COMMANDS_DIR in the same commit "
        "— never delete this gate."
    )
    violations: list[str] = []
    for path in _iter_agent_command_files():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel in _DUMPS_ALLOWLIST:
            continue
        violations.extend(_json_dumps_offenders(path.read_text(encoding="utf-8"), rel))
    assert not violations, (
        "Inline json.dumps in the agent command surface — "
        f"{_DUMPS_REMEDIATION}:\n  " + "\n  ".join(violations)
    )


def test_dumps_allowlist_is_shrink_only() -> None:
    """The exception set only shrinks, and the tasks family can never join it."""
    assert len(_DUMPS_ALLOWLIST) <= _DUMPS_ALLOWLIST_CEILING, (
        f"_DUMPS_ALLOWLIST grew to {len(_DUMPS_ALLOWLIST)} entries (ceiling "
        f"{_DUMPS_ALLOWLIST_CEILING}). The set is SHRINK-ONLY: fix the new site "
        f"({_DUMPS_REMEDIATION}) instead of allowlisting it."
    )
    prefix = "src/specify_cli/cli/commands/agent/"
    for rel in sorted(_DUMPS_ALLOWLIST):
        assert rel.startswith(prefix), (
            f"_DUMPS_ALLOWLIST entry {rel!r} is outside the gated directory — "
            "entries must be repo-relative paths under the glob."
        )
        assert not Path(rel).name.startswith("tasks"), (
            f"_DUMPS_ALLOWLIST entry {rel!r} is a tasks-family module — the "
            "de-godded family surface ships at 0 inline-dumps sites (SC-002) "
            f"and may never be allowlisted; {_DUMPS_REMEDIATION}."
        )


def test_dumps_allowlist_has_no_stale_entries() -> None:
    """Shrink pressure: an allowlisted file cleaned of inline dumps must leave."""
    for rel in sorted(_DUMPS_ALLOWLIST):
        path = _REPO_ROOT / rel
        assert path.is_file(), (
            f"_DUMPS_ALLOWLIST entry {rel!r} does not exist — remove the stale "
            "entry (shrink-only)."
        )
        assert _json_dumps_offenders(path.read_text(encoding="utf-8"), rel), (
            f"{rel} no longer contains inline json.dumps — REMOVE it from "
            "_DUMPS_ALLOWLIST in the same commit (shrink-only ratchet)."
        )


# --- Gate 1 non-vacuity: one theater test PER evasion form (C-006) ---------


def test_dumps_gate_fires_on_attribute_call() -> None:
    """Form 1: ``json.dumps(...)`` under plain ``import json``."""
    offenders = _json_dumps_offenders(
        "import json\n\n\ndef emit(payload: dict) -> None:\n    print(json.dumps(payload))\n",
        "theater.py",
    )
    assert offenders == ["theater.py:5 (json.dumps attribute call)"]


def test_dumps_gate_fires_on_module_alias() -> None:
    """Form 2: ``_json.dumps(...)`` under ``import json as _json``."""
    offenders = _json_dumps_offenders(
        "import json as _json\n\n\ndef emit(payload: dict) -> None:\n    print(_json.dumps(payload))\n",
        "theater.py",
    )
    assert offenders == ["theater.py:5 (json.dumps attribute call)"]


def test_dumps_gate_fires_on_from_import() -> None:
    """Form 3: ``from json import dumps [as alias]`` and calls to that name."""
    plain = _json_dumps_offenders(
        "from json import dumps\n\nprint(dumps({}))\n", "theater.py"
    )
    assert plain == ["theater.py:3 (bound-name dumps call)"]
    aliased = _json_dumps_offenders(
        "from json import dumps as _d\n\nprint(_d({}))\n", "theater.py"
    )
    assert aliased == ["theater.py:3 (bound-name dumps call)"]


def test_dumps_gate_fires_on_rebinding() -> None:
    """Form 4: rebinding assignments (chains included) AND calls of the name."""
    offenders = _json_dumps_offenders(
        "import json\n\n_dump = json.dumps\n_alias = _dump\nprint(_alias({}))\n",
        "theater.py",
    )
    assert offenders == [
        "theater.py:3 (json.dumps rebinding assignment)",
        "theater.py:4 (json.dumps rebinding assignment)",
        "theater.py:5 (bound-name dumps call)",
    ]


def test_dumps_gate_is_string_immune() -> None:
    """Docstring/string mentions never trip the AST detector (D6)."""
    offenders = _json_dumps_offenders(
        '"""Mentions json.dumps(payload) in prose."""\n\nNOTE = "json.dumps"\n',
        "theater.py",
    )
    assert offenders == []
