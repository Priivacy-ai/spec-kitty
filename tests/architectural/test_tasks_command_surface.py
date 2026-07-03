"""Architectural gates for the ``agent tasks`` command surface (``tasks.py``).

Mission ``tasks-py-degod-wave2-01KWH9EQ`` — contract:
``kitty-specs/tasks-py-degod-wave2-01KWH9EQ/contracts/gate-contracts.md``.

File-size enforcement is deliberately NOT here (operator ruling,
2026-07-03): raw LOC/size metrics are Sonar's job (S104 / the quality
gate), and a hard-coded line ceiling turns every legitimate edit into
test friction. The anti-regrowth guidance for the registration shim
lives in tasks.py's header comment; the SEMANTIC gate below is what the
suite owns.

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
