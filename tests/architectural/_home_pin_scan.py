"""The ONE importable scanner for the ``SPEC_KITTY_HOME`` behaviour class (R1a, WP01).

Binding contract:
``kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/contracts/home-pin-scan-seam.md``.

Why one module
--------------
``tests/architectural/_sole_door_scan.py:13-27`` records the drift this module exists to prevent
as a **live incident**: Gates 4 and 5 each rolled an independent, drifting copy of the same
primitives, Gate 4's copy having already lost Gate 1's docstring rationale. Prose did not prevent
it there. The seam is mechanised by WP02's guard, not asserted here in prose.

What lives here, and what deliberately does not
-----------------------------------------------
Here: the un-narrowed walk, the mandatory byte pre-filter, a parser that **propagates**
``SyntaxError``, the binding resolver, the key-parameterised receiver-agnostic write-site finder,
the scope-chain silhouette attributor, :func:`discover`, the census/baseline generators, and the
shared vocabulary (:data:`MemberKey`, :class:`Member`, :class:`Exempt`, :data:`INERT_LIMBS`) that
three downstream packages bind to.

Not here: **no ``subprocess``, no git surface** — the window measurement lives in
``tests/architectural/_home_pin_gate.py`` and *imports* :func:`discover`. Collected tests import
this module under a 6-second budget on every PR (NFR-001).

``except SyntaxError`` is forbidden in this module (SC-013). It narrows the walk with nothing
firing and buys budget headroom, which is NFR-001's defeat wearing an exception handler. The
absence is AST-asserted against this module's own source, with a positive control.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from tests.architectural._ratchet_keys import ContentDescriptor, composite_key, enclosing_qualname

__all__ = [
    "MemberKey",
    "Kind",
    "HomePartition",
    "Member",
    "Exempt",
    "Attribution",
    "WriteSite",
    "WriteForm",
    "DuplicateMemberKeyError",
    "INERT_LIMBS",
    "NEEDLE",
    "HOME_KEY",
    "TMP_PATH",
    "TMP_PATH_HOME",
    "TMP_PATH_USER_HOME",
    "OWNER_PARAM_NAMES",
    "SILHOUETTE",
    "enumerate_py_files",
    "byte_prefilter",
    "parse_module",
    "find_except_handlers",
    "find_module_references",
    "find_write_sites",
    "collect_bindings",
    "module_level_bindings",
    "withitem_bound_names",
    "resolve_value",
    "value_sub_forms",
    "def_chain",
    "def_params",
    "def_kind",
    "normalise_params",
    "key_member",
    "member_key",
    "discover",
    "kind_distribution",
    "inert_hits",
    "literal_key_occurrences",
    "bindings_for_site",
    "ExemptSet",
    "Fragility",
    "fragility_register",
    "build_parser",
    "render_census",
    "render_baseline",
    "main",
]

#: Raw bytes the mandatory pre-filter looks for (FR-002) — and the module's canonical form of
#: the key.
#:
#: **The byte form is primary deliberately, and this is a recorded finding.** SC-002b asserts
#: that the population of **assignment-bound string constants valued** ``"SPEC_KITTY_HOME"``
#: across ``src/`` ∪ ``tests/`` is **0** (against 229 literal occurrences in 98 files). A module
#: constant written the obvious way — ``NEEDLE = "SPEC_KITTY_HOME"`` — would make this file the
#: **first** such binding in the repository and falsify that population in the very module that
#: ships its assertion: the FR-009 "the guard's own artefact lands inside the guard's own
#: population" shape, operating on SC-002b instead of on the walk. The pre-filter needs the bytes
#: and the literal-key matcher needs the text, so the bytes are held and the text derived.
NEEDLE_BYTES = b"SPEC_KITTY_HOME"

#: The environment variable whose pinning defines membership.
NEEDLE = NEEDLE_BYTES.decode("utf-8")

#: The path-qualified 3-tuple row identity: ``(rel_path, enclosing_qualname, token_line)``.
#: Formed **at the write site** from the already-parsed source (C-012(0)/(1)); the primitive
#: ``composite_key`` returns only the trailing 2-tuple, so the composition is spelled out
#: explicitly — comparing the two directly is a ``mypy --strict`` type error (C-012(0a)).
MemberKey = tuple[str, str, str]

#: The shape axis, read **at the keyed (outermost satisfying) def**, never at the innermost
#: (C-004). Retained only for the rename signature.
Kind = Literal["fixture", "test-body", "helper"]

#: The effect axis (FR-003), derived from ``HOME`` writes in the member's own scope chain.
#: Rule imported from ``research/m4_ablation_evidence/VERDICT.md:38-41``.
HomePartition = Literal["A", "B1", "B2", "other"]


@dataclass(frozen=True)
class Member:
    """One discovered member of the ``SPEC_KITTY_HOME`` behaviour class.

    ``key`` is the identity and the only field every set operation in the Mission runs over.
    ``lineno`` is **explicitly non-authoritative** (``_sole_door_scan.py:87-89``) — carried
    because ``normalized_token_line`` takes only four distinct values across the class, so
    without it a maintainer cannot reach the site. It is never part of ``key``.
    """

    key: MemberKey
    lineno: int
    home_partition: HomePartition
    relpath: str
    kind: Kind
    params: frozenset[str]
    resolved_value: str | None


@dataclass(frozen=True)
class Exempt:
    """One entry of ``E``, the enumerated exemption set (FR-004).

    ``E`` is typed ``tuple[Exempt, Exempt]`` at its declaration site so a third entry is a
    ``mypy --strict`` error rather than a one-line literal. ``why`` is prose and entitles nothing
    the type does not already grant.
    """

    key: MemberKey
    why: str


# ---------------------------------------------------------------------------
# T001 — the walk, the pre-filter, the parser
# ---------------------------------------------------------------------------


def enumerate_py_files(root: Path) -> list[Path]:
    """Every ``.py`` file under ``root``. **Never narrowed** — not by directory, not by filename.

    C-003 states that narrowing by directory or filename qualifies under neither carve-out form,
    and NFR-001 explicitly permits raising the budget but never narrowing the walk. SC-007 asserts
    this set against an ``rglob`` written inline in the test, with the count reported and not
    asserted.
    """
    return sorted(root.rglob("*.py"))


def byte_prefilter(paths: Iterable[Path]) -> list[Path]:
    """Files whose raw bytes contain ``b"SPEC_KITTY_HOME"``.

    **Mandatory, not an optimisation** (FR-002). Kept deliberately separate from the walk so the
    walk stays assertable while the parse set shrinks. Its over-selection premise — that the env
    key is a literal at the call site — is not assumed here: it ships as SC-002b's empty-set
    assertion with a positive control.
    """
    return [path for path in paths if NEEDLE_BYTES in path.read_bytes()]


def parse_module(path: Path) -> ast.Module:
    """Parse ``path``. **Propagates ``SyntaxError``** (SC-013).

    This is the only parser in the behaviour class: every consumer — including the positive
    controls in the test modules, which must parse a materialised synthetic source — routes
    through it, because ``ast.parse`` is banned in every module importing this one.
    """
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ---------------------------------------------------------------------------
# Self-assertion matchers (production matchers, exercised by positive controls)
# ---------------------------------------------------------------------------


def find_except_handlers(tree: ast.Module, *, exception: str) -> set[int]:
    """Line numbers of ``except <exception>`` handlers anywhere in ``tree``.

    Used to assert this module declares **zero** ``except SyntaxError`` handlers (SC-013). The
    same matcher runs over a synthetic module that *does* declare one, so the empty-set assertion
    is not its own proof (C-003 form (ii)).
    """
    hits: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        if exception in _exception_names(node.type):
            hits.add(node.lineno)
    return hits


def _exception_names(node: ast.expr) -> set[str]:
    """Bare/dotted/tuple exception names named by an ``except`` clause's type expression."""
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Tuple):
        return {name for element in node.elts for name in _exception_names(element)}
    return set()


def find_module_references(tree: ast.Module, *, names: frozenset[str]) -> set[tuple[str, int]]:
    """``(module_name, lineno)`` for every import of — or attribute access rooted at — ``names``.

    Backs the contract's "no ``subprocess`` and no git surface in this module" clause. Attribute
    roots are covered as well as imports so a re-export cannot smuggle the surface back in.
    """
    hits: set[tuple[str, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits |= {
                (alias.name.split(".")[0], node.lineno)
                for alias in node.names
                if alias.name.split(".")[0] in names
            }
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            root = node.module.split(".")[0]
            if root in names:
                hits.add((root, node.lineno))
        elif (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in names
        ):
            hits.add((node.value.id, node.lineno))
    return hits


# ---------------------------------------------------------------------------
# The inert SUB-FORM registry (T004)
# ---------------------------------------------------------------------------

#: Every sub-form whose real-tree population is **0**, by canonical id.
#:
#: **SUB-FORM, not limb** (FR-001): a *limb* is a whole clause of the predicate (the silhouette
#: limb, the write limb, the ``HOME`` enumeration); a *sub-form* is one shape within a limb. Any
#: entry here whose real-tree population is **non-zero is a REGISTRY DEFECT**, not a matcher
#: defect.
#:
#: **The ``HOME`` enumeration is deliberately NOT registered.** Measured it is the most heavily
#: populated limb in the classifier — 85 write sites in 50 files, with 13 of the 40 members
#: re-pinning ``HOME`` — and registering it would mandate a false empty-set assertion.
#:
#: **Delta against FR-007's table, stated so a reviewer can check it**: FR-007 publishes
#: **fourteen** classifier sub-forms; ``SC-002b`` is the one id here that is **not** in that
#: table, because its assignment-bound-``"SPEC_KITTY_HOME"``-constant assertion is a criterion in
#: its own right rather than a sub-form of the classifier. The delta is exactly one and it is
#: named.
INERT_LIMBS: frozenset[str] = frozenset(
    {
        "SKH-SETDEFAULT",
        "SKH-BARE-SETENV",
        "SKH-VAL-OSPATHJOIN",
        "SKH-VAL-PERCENT",
        "SKH-VAL-FORMAT",
        "SKH-VAL-CONCAT",
        "HOME-SETDEFAULT",
        "HOME-VAL-OSPATHJOIN",
        "HOME-VAL-PERCENT",
        "HOME-VAL-FORMAT",
        "HOME-VAL-CONCAT",
        "SCOPE-EXPLICIT",
        "PARTITION-OTHER",
        "WITHITEM-VALUE-REF",
        "SC-002b",
    }
)


# ---------------------------------------------------------------------------
# T002 — the binding resolver and the receiver-agnostic write-site finder
# ---------------------------------------------------------------------------

#: The second environment variable the walk resolves. It decides ``home_partition`` (FR-003),
#: never membership. **Its enumeration is a LIMB, not an inert sub-form** — 85 write sites in 50
#: files, 13 of the 40 members re-pinning it — so it is deliberately absent from
#: :data:`INERT_LIMBS`.
HOME_KEY = "HOME"

#: Symbolic stand-in for the per-test temporary directory in a resolved value. Values are
#: compared as strings against these symbols, so a synthetic tree and the real tree are
#: comparable without either one running.
TMP_PATH = "<tmp_path>"
#: The value that makes a write site a member.
TMP_PATH_HOME = f"{TMP_PATH}/home"
#: Partition B2's value (``research/m4_ablation_evidence/VERDICT.md:38-41``).
TMP_PATH_USER_HOME = f"{TMP_PATH}/user-home"

#: Parameter names counting as ``tmp_path`` for **both** the silhouette and value resolution
#: (FR-010). Without this limb the guard goes blind in proportion to R1b's adoption — the more
#: the owner is adopted, the more members become invisible — so the limb is correct to exist.
#:
#: **BUT IT MATCHES NOTHING TODAY, AND THAT IS STATED HERE RATHER THAN LEFT TO BE ASSUMED.**
#: FR-007's rule — *a limb matching nothing must be known to match nothing or it reads as
#: enforcement* — is applied by this package to fifteen ids in :data:`INERT_LIMBS`. This is the
#: sixteenth, and it is the one the rule was **not** applied to until review constructed it.
#: Measured over ``tests/``:
#:
#: * **``runtime_home``: population 0.** Removing it leaves ``discover()`` at 40 members with
#:   **symmetric difference 0**. Exactly one def in the tree declares the parameter —
#:   ``tests/audit/test_no_legacy_path_literals.py:80 _capture_nudge(module_name, runtime_home,
#:   *, argv)`` — and although it does enclose two ``SPEC_KITTY_HOME`` writes (``:94``, ``:112``)
#:   it is refused on **both** limbs: the chain union is ``{argv, module_name, runtime_home}`` so
#:   the silhouette fails for want of ``monkeypatch``, and the value resolves to ``<tmp_path>``
#:   (and to ``None`` at ``:112``), never ``<tmp_path>/home``. FR-010 cites this as "the live
#:   population-1 shape"; it is live as a *shape*, and population **0** as a member.
#: * **``canonical_home``: BOUND, and no longer population 0.** WP03 has landed the canonical
#:   owner, so the name is now declared by a real fixture at ``tests/conftest.py`` and the limb
#:   fires on the real tree. The entry was *provisional and unbound* when it shipped — the name
#:   was taken from FR-010's prose at a moment when no contract named the owner — and the
#:   closing obligation named here has since been discharged by **WP03/T012**, which parses the
#:   declared fixture name out of ``contracts/canonical-home-owner.md`` and asserts it is a
#:   member of this set (``tests/architectural/test_home_owner_behaviour.py``:
#:   ``test_the_declared_owner_name_is_a_member_of_owner_param_names``, with
#:   ``test_the_owner_alias_limb_actually_fires_on_the_owner_name`` constructing the effect
#:   rather than reading it). The operand is now outside this author's control, which is what
#:   closes the circularity: rename the owner and that test reds, instead of this limb going
#:   silently inert with every assertion in this package still green.
#:
#: Both entries are **kept**: deleting them would remove the limb R1b needs, and the defect was
#: never the limb — it was presenting an inert limb as a live one.
OWNER_PARAM_NAMES: frozenset[str] = frozenset({"tmp_path", "canonical_home", "runtime_home"})

#: The silhouette the enclosing scope chain's parameter UNION must contain — a superset test,
#: never arity-exact and never order-sensitive (C-004).
SILHOUETTE: frozenset[str] = frozenset({"tmp_path", "monkeypatch"})

#: The three write forms. Receiver-agnostic: ``setenv`` covers the attribute-receiver call, the
#: bare-name call and the ``with … as mp`` receiver alike, because it is tested **on the call**.
WriteForm = Literal["setenv", "environ-assign", "setdefault"]

_SETENV_NAMES: frozenset[str] = frozenset({"setenv"})
_SETDEFAULT_NAMES: frozenset[str] = frozenset({"setdefault"})
_UNWRAP_CALLS: frozenset[str] = frozenset({"str", "fspath"})


@dataclass(frozen=True)
class WriteSite:
    """One environment-variable write, in the receiver-agnostic three-form sense of §0.8."""

    lineno: int
    form: WriteForm
    key: str
    value: ast.expr
    bare_receiver: bool


def find_write_sites(tree: ast.Module, *, key: str) -> list[WriteSite]:
    """Every write of ``key`` in ``tree``. **One implementation, two keys; never a second finder.**

    Called with ``key="SPEC_KITTY_HOME"`` for membership and ``key="HOME"`` for
    ``home_partition``. The three forms are matched **on the call**, never on the receiver:
    ``setenv`` as an attribute *or* a bare name, ``os.environ[…] = `` / ``environ[…] = ``, and
    ``.setdefault(…, …)``.

    **Receiver-agnosticism is the load-bearing property**, and the bare-name case is what catches
    its loss: a receiver-*qualified* matcher drops ``:1165`` and biases the gate's ``r`` toward
    *proceed*. (The earlier claim that ``withitem`` receiver *binding* is what admits ``:1165``
    was measured FALSE and struck — removing that binding entirely still finds all 40 members.)
    """
    sites: list[WriteSite] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            site = _call_write_site(node, key)
        elif isinstance(node, ast.Assign):
            site = _assign_write_site(node, key)
        else:
            continue
        if site is not None:
            sites.append(site)
    return sorted(sites, key=lambda site: (site.lineno, site.form))


def _callee_name(func: ast.expr) -> tuple[str, bool] | None:
    """``(called name, is_bare_name)`` for an attribute or bare-name callee, else ``None``."""
    if isinstance(func, ast.Attribute):
        return (func.attr, False)
    if isinstance(func, ast.Name):
        return (func.id, True)
    return None


def _literal_key_matches(node: ast.expr, key: str) -> bool:
    """``True`` when ``node`` is the string literal ``key``.

    A non-literal key is deliberately not matched: the pre-filter's soundness premise is that the
    env key is a literal at the call site, and SC-002b is the executable check that falsifies it
    the day it stops being true — never a widening improvised here.
    """
    return isinstance(node, ast.Constant) and node.value == key


def _call_write_site(node: ast.Call, key: str) -> WriteSite | None:
    """``setenv`` / ``setdefault`` calls, receiver-agnostic, with a literal ``key`` first arg."""
    callee = _callee_name(node.func)
    if callee is None or len(node.args) < 2:
        return None
    name, bare = callee
    if name in _SETENV_NAMES:
        form: WriteForm = "setenv"
    elif name in _SETDEFAULT_NAMES:
        form = "setdefault"
    else:
        return None
    if not _literal_key_matches(node.args[0], key):
        return None
    return WriteSite(node.lineno, form, key, node.args[1], bare)


def _assign_write_site(node: ast.Assign, key: str) -> WriteSite | None:
    """``os.environ[key] = …`` / ``environ[key] = …``, receiver-agnostic on the mapping name."""
    for target in node.targets:
        if not isinstance(target, ast.Subscript):
            continue
        base = target.value
        if isinstance(base, ast.Attribute):
            base_name, bare = base.attr, False
        elif isinstance(base, ast.Name):
            base_name, bare = base.id, True
        else:
            continue
        if base_name != "environ" or not _literal_key_matches(target.slice, key):
            continue
        return WriteSite(node.lineno, "environ-assign", key, node.value, bare)
    return None


def collect_bindings(scope: ast.AST) -> dict[str, ast.expr]:
    """**Single-assignment** bindings inside ``scope``: ``name -> value expression``.

    A name bound more than once *within the scope* is dropped rather than guessed at — an
    ambiguous binding is unresolvable, and ``None`` never matches anything. Receivers bound by a
    ``with … as`` item bind here too, not only ``ast.Assign``.

    **``scope`` is a parameter, and that is load-bearing.** Collected file-wide, the single-
    assignment rule is wrong in the direction that loses members: measured, ``home = tmp_path /
    "home"`` recurs once per test function across ``tests/upgrade/test_compat.py``,
    ``tests/upgrade/migrations/test_m_0_6_7_ensure_missions.py`` and three sibling modules, so a
    file-wide count sees it "multiply assigned", drops the binding, and silently discovers **33
    members instead of 40**. Single assignment is a *local* property; :func:`discover` collects
    it over the write site's own outermost enclosing ``def``.
    """
    counts: dict[str, int] = {}
    values: dict[str, ast.expr] = {}
    for node in ast.walk(scope):
        for name, value in _binding_pairs(node):
            counts[name] = counts.get(name, 0) + 1
            values[name] = value
    return {name: value for name, value in values.items() if counts[name] == 1}


def module_level_bindings(tree: ast.Module) -> dict[str, ast.expr]:
    """Single-assignment bindings at module top level — never those nested inside a ``def``."""
    counts: dict[str, int] = {}
    values: dict[str, ast.expr] = {}
    for statement in tree.body:
        for name, value in _binding_pairs(statement):
            counts[name] = counts.get(name, 0) + 1
            values[name] = value
    return {name: value for name, value in values.items() if counts[name] == 1}


def _binding_pairs(node: ast.AST) -> list[tuple[str, ast.expr]]:
    """``(name, value)`` pairs a single node binds, for the three binding statements modelled."""
    if isinstance(node, ast.Assign):
        return [
            (target.id, node.value) for target in node.targets if isinstance(target, ast.Name)
        ]
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return [(node.target.id, node.value)] if isinstance(node.target, ast.Name) else []
    if isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
        return [(node.optional_vars.id, node.context_expr)]
    return []


def withitem_bound_names(tree: ast.Module) -> frozenset[str]:
    """Names bound by a ``with … as`` item — the receivers ``WITHITEM-VALUE-REF`` is about."""
    return frozenset(
        node.optional_vars.id
        for node in ast.walk(tree)
        if isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name)
    )


def resolve_value(node: ast.AST, bindings: Mapping[str, ast.AST]) -> str | None:
    """Resolve a value expression to a symbolic path string, or ``None`` when unresolvable.

    Eight forms, not four: unwraps ``str`` / ``Path`` / ``os.fspath`` / ``joinpath``, joins
    f-strings, and — added by FR-001's widening — resolves ``os.path.join``, ``%``-format,
    ``.format()`` and ``+`` concatenation. **``None`` is unresolvable and never matches
    anything**, which is asserted rather than assumed.
    """
    return _resolve(node, bindings, frozenset())


def _resolve(node: ast.AST, bindings: Mapping[str, ast.AST], seen: frozenset[str]) -> str | None:
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return _resolve_name(node, bindings, seen)
    if isinstance(node, ast.JoinedStr):
        return _resolve_joined(node, bindings, seen)
    if isinstance(node, ast.Call):
        return _resolve_call(node, bindings, seen)
    if isinstance(node, ast.BinOp):
        return _resolve_binop(node, bindings, seen)
    return None


def _resolve_name(
    node: ast.Name, bindings: Mapping[str, ast.AST], seen: frozenset[str]
) -> str | None:
    if node.id in OWNER_PARAM_NAMES:
        return TMP_PATH
    bound = bindings.get(node.id)
    if bound is None or node.id in seen:
        return None
    return _resolve(bound, bindings, seen | {node.id})


def _resolve_joined(
    node: ast.JoinedStr, bindings: Mapping[str, ast.AST], seen: frozenset[str]
) -> str | None:
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
            continue
        if not isinstance(value, ast.FormattedValue):
            return None
        resolved = _resolve(value.value, bindings, seen)
        if resolved is None:
            return None
        parts.append(resolved)
    return "".join(parts)


def _resolve_call(
    node: ast.Call, bindings: Mapping[str, ast.AST], seen: frozenset[str]
) -> str | None:
    callee = _callee_name(node.func)
    if callee is None:
        return None
    name = callee[0]
    if name in _UNWRAP_CALLS:
        return _resolve(node.args[0], bindings, seen) if node.args else None
    if name == "Path":
        return _join_path_parts(node.args, bindings, seen, base=None)
    if name == "joinpath" and isinstance(node.func, ast.Attribute):
        base = _resolve(node.func.value, bindings, seen)
        return None if base is None else _join_path_parts(node.args, bindings, seen, base=base)
    if name == "join" and isinstance(node.func, ast.Attribute) and _is_os_path(node.func.value):
        return _join_path_parts(node.args, bindings, seen, base=None)
    if name == "format" and isinstance(node.func, ast.Attribute):
        template = _resolve(node.func.value, bindings, seen)
        return _apply_braces(template, node.args, bindings, seen)
    return None


def _is_os_path(node: ast.expr) -> bool:
    """``True`` for the ``os.path`` (or bare ``path``) receiver of ``os.path.join``."""
    if isinstance(node, ast.Attribute):
        return node.attr == "path"
    return isinstance(node, ast.Name) and node.id == "path"


def _resolve_binop(
    node: ast.BinOp, bindings: Mapping[str, ast.AST], seen: frozenset[str]
) -> str | None:
    left = _resolve(node.left, bindings, seen)
    if left is None:
        return None
    if isinstance(node.op, ast.Div):
        right = _resolve(node.right, bindings, seen)
        return None if right is None else _path_join(left, right)
    if isinstance(node.op, ast.Add):
        right = _resolve(node.right, bindings, seen)
        return None if right is None else left + right
    if isinstance(node.op, ast.Mod):
        operands = node.right.elts if isinstance(node.right, ast.Tuple) else [node.right]
        return _apply_percent(left, operands, bindings, seen)
    return None


def _path_join(base: str, part: str) -> str:
    if part.startswith("/") or not base:
        return part
    return f"{base.rstrip('/')}/{part}"


def _join_path_parts(
    args: Sequence[ast.expr],
    bindings: Mapping[str, ast.AST],
    seen: frozenset[str],
    *,
    base: str | None,
) -> str | None:
    joined = base
    for arg in args:
        resolved = _resolve(arg, bindings, seen)
        if resolved is None:
            return None
        joined = resolved if joined is None else _path_join(joined, resolved)
    return joined


def _apply_braces(
    template: str | None,
    args: Sequence[ast.expr],
    bindings: Mapping[str, ast.AST],
    seen: frozenset[str],
) -> str | None:
    if template is None:
        return None
    result = template
    for arg in args:
        resolved = _resolve(arg, bindings, seen)
        if resolved is None or "{}" not in result:
            return None
        result = result.replace("{}", resolved, 1)
    return result


def _apply_percent(
    template: str,
    operands: Sequence[ast.expr],
    bindings: Mapping[str, ast.AST],
    seen: frozenset[str],
) -> str | None:
    result = template
    for operand in operands:
        resolved = _resolve(operand, bindings, seen)
        if resolved is None or "%s" not in result:
            return None
        result = result.replace("%s", resolved, 1)
    return result


def value_sub_forms(
    node: ast.expr, bindings: Mapping[str, ast.AST], *, withitem_names: frozenset[str]
) -> frozenset[str]:
    """Which widened value sub-forms a value expression uses, following its bindings.

    The tokens are the suffixes FR-007's table names — ``OSPATHJOIN`` / ``PERCENT`` / ``FORMAT``
    / ``CONCAT`` — plus ``WITHITEM-REF`` for a value referencing a ``with … as`` receiver. Each
    is measured at both keys, which is why the same function serves ``SKH-VAL-*`` and
    ``HOME-VAL-*``.
    """
    found: set[str] = set()
    for reachable in _reachable_nodes(node, bindings):
        if isinstance(reachable, ast.BinOp) and isinstance(reachable.op, ast.Mod):
            found.add("PERCENT")
        elif isinstance(reachable, ast.BinOp) and isinstance(reachable.op, ast.Add):
            found.add("CONCAT")
        elif isinstance(reachable, ast.Call) and isinstance(reachable.func, ast.Attribute):
            if reachable.func.attr == "format":
                found.add("FORMAT")
            elif reachable.func.attr == "join" and _is_os_path(reachable.func.value):
                found.add("OSPATHJOIN")
        elif isinstance(reachable, ast.Name) and reachable.id in withitem_names:
            found.add("WITHITEM-REF")
    return frozenset(found)


def _reachable_nodes(node: ast.expr, bindings: Mapping[str, ast.AST]) -> list[ast.AST]:
    """Every node of the value expression, expanded through its single-assignment bindings."""
    reached: list[ast.AST] = []
    pending: list[ast.AST] = [node]
    expanded: set[str] = set()
    while pending:
        current = pending.pop()
        for child in ast.walk(current):
            reached.append(child)
            if isinstance(child, ast.Name) and child.id not in expanded:
                bound = bindings.get(child.id)
                if bound is not None:
                    expanded.add(child.id)
                    pending.append(bound)
    return reached


# ---------------------------------------------------------------------------
# T003 — the keyer, discover(), and the identity/attribution separation
# ---------------------------------------------------------------------------

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


class DuplicateMemberKeyError(RuntimeError):
    """Two members produced a byte-identical :data:`MemberKey`.

    **The 3-tuple is not injective over the 191 walked write sites** — 190 distinct, one live
    collision class of two at ``tests/paths/test_runtime_root_spec_kitty_home.py:91,93``: one
    definition carrying the full silhouette, two ``setenv`` sites, one key, because
    ``normalized_token_line`` strips the string literals that distinguish them.

    **At MEMBER level the population is 0, and the earlier wording here overstated it.**
    Measured: 40 members, 40 distinct keys, **0 collision classes**. The two sites above are
    non-members only because they resolve to ``tmp_path/"one"`` and ``tmp_path/"two"`` — one
    string literal away from being two members with one key, in a file named
    ``test_runtime_root_spec_kitty_home.py``. So this exception guards a population-0 case whose
    counterexample is one edit away, which is exactly why it must raise rather than deduplicate;
    the positive control that proves it bites is real and ships in the limb tests.
    """


@dataclass(frozen=True)
class Attribution:
    """The result of the silhouette pass. **It carries no key** — see the note below.

    **Recorded deviation from the contract's public-surface listing, raised rather than silently
    repaired.** The contract lists ``key_member(site, chain) -> Member | None``, but a ``Member``
    carries ``relpath`` and a source-derived ``MemberKey`` and neither ``WriteSite`` nor the
    ``chain`` can supply them — while C-012(5) independently requires the key to be formed *at
    the boundary*, "never inside the write-site finder or the silhouette keyer". The two cannot
    both hold. C-012 is spec-normative, so the positional signature is kept exactly and the
    return type is narrowed to this attribution record; :func:`discover` composes the ``Member``
    (and its key, through the single builder :func:`member_key`) at the boundary.
    """

    lineno: int
    keyed_index: int
    kind: Kind
    params: frozenset[str]


def def_chain(tree: ast.Module, lineno: int) -> tuple[FunctionNode, ...]:
    """The enclosing ``def``/``async def`` chain containing ``lineno``, **outermost first**."""
    enclosing = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.lineno <= lineno <= (node.end_lineno or node.lineno)
    ]
    return tuple(sorted(enclosing, key=lambda node: node.lineno))


def def_params(node: FunctionNode) -> frozenset[str]:
    """A def's parameter names, leading ``self``/``cls`` stripped."""
    args = node.args
    positional = [arg.arg for arg in (*args.posonlyargs, *args.args)]
    if positional and positional[0] in {"self", "cls"}:
        positional = positional[1:]
    return frozenset(positional) | {arg.arg for arg in args.kwonlyargs}


def normalise_params(params: frozenset[str]) -> frozenset[str]:
    """FR-010: a parameter naming the canonical owner counts as ``tmp_path``."""
    return frozenset("tmp_path" if name in OWNER_PARAM_NAMES else name for name in params)


def def_kind(node: FunctionNode) -> Kind:
    """The SHAPE label, read at whichever def the caller attributes to."""
    if any(_decorator_name(item) == "fixture" for item in node.decorator_list):
        return "fixture"
    return "test-body" if node.name.startswith("test") else "helper"


def _decorator_name(node: ast.expr) -> str | None:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr
    return target.id if isinstance(target, ast.Name) else None


def key_member(site: WriteSite, chain: Sequence[ast.AST]) -> Attribution | None:
    """Attribute a write site to the **OUTERMOST** def whose accumulated silhouette is satisfied.

    **Identity and attribution are separate and they disagree** (C-012). This function does
    *attribution* only: the silhouette is evaluated over the **union of the enclosing chain's
    parameter sets** (leading ``self``/``cls`` stripped, superset test), and membership, ``kind``
    and the rename signature's parameter set are all read at the outermost def at which that
    union first satisfies the silhouette. **That def is NOT in the key** — the key's qualname
    component is the *innermost* write-site qualname, which is what the C-011 anchor matches
    (symmetric difference 0; keying at the attributed def gives 2, both at ``:1165``).

    C-004 is therefore mechanised by the ``kind`` **distribution** rather than by the key set:
    see :func:`kind_distribution`.
    """
    defs = tuple(node for node in chain if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    if not defs:
        return None
    accumulated: frozenset[str] = frozenset()
    for index, node in enumerate(defs):
        accumulated |= normalise_params(def_params(node))
        if accumulated >= SILHOUETTE:
            union = frozenset().union(*(normalise_params(def_params(d)) for d in defs))
            return Attribution(site.lineno, index, def_kind(node), union)
    return None


def member_key(relpath: str, source: str, lineno: int) -> MemberKey:
    """**The single key builder**, called at the boundary and nowhere else.

    ``MemberKey = (relpath_posix, *composite_key(source, lineno))``. The composition is spelled
    out because the types differ: the repository primitive returns ``tuple[str, str]``, so
    comparing it to a ``MemberKey`` is a ``mypy --strict`` type error, not merely a wrong
    assertion (C-012(0a)).

    ``source`` is the text :func:`discover` **already holds**, never a re-read: ``anchoring.py``
    ``:192-195`` swallows ``SyntaxError`` and returns ``"<module>"``, so re-reading would
    silently degrade a broken file and leave SC-013's guarantee holding only on the
    :func:`parse_module` path. ``composite_key_from_file`` is for the independent live
    recomputation only, where the file is known-parseable. Not re-reading also saves a measured
    0.19 s per pass.
    """
    return (relpath, *composite_key(source, lineno))


@dataclass(frozen=True)
class _SiteRecord:
    """One member site with everything both consumers of the pass need. Internal."""

    relpath: str
    source: str
    site: WriteSite
    chain: tuple[FunctionNode, ...]
    attribution: Attribution
    resolved_value: str
    home_partition: HomePartition


def _scan_records(root: Path, prefilter: bool) -> Iterator[_SiteRecord]:
    """The single pass both :func:`discover` and :func:`kind_distribution` consume."""
    paths = enumerate_py_files(root)
    for path in byte_prefilter(paths) if prefilter else paths:
        source = path.read_text(encoding="utf-8")
        tree = parse_module(path)
        module_bindings = module_level_bindings(tree)
        home_sites = find_write_sites(tree, key=HOME_KEY)
        relpath = path.relative_to(root).as_posix()
        for site in find_write_sites(tree, key=NEEDLE):
            record = _record_for(site, tree, module_bindings, home_sites, relpath, source)
            if record is not None:
                yield record


def _record_for(
    site: WriteSite,
    tree: ast.Module,
    module_bindings: Mapping[str, ast.expr],
    home_sites: Sequence[WriteSite],
    relpath: str,
    source: str,
) -> _SiteRecord | None:
    chain = def_chain(tree, site.lineno)
    attribution = key_member(site, chain)
    if attribution is None:
        return None
    bindings = bindings_for_site(tree, site, module_bindings)
    resolved = resolve_value(site.value, bindings)
    if resolved != TMP_PATH_HOME:
        return None
    partition = _home_partition(chain, home_sites, bindings)
    return _SiteRecord(relpath, source, site, chain, attribution, resolved, partition)


def _home_partition(
    chain: Sequence[FunctionNode],
    home_sites: Sequence[WriteSite],
    bindings: Mapping[str, ast.expr],
) -> HomePartition:
    """The EFFECT axis, over the member's **own scope chain** (FR-003).

    A member's scope chain lies entirely within one file, so every ``HOME`` write that can change
    its partition sits in the same file as its ``SPEC_KITTY_HOME`` write — a byte-hit file by
    construction. That is the pre-filter's soundness argument for the second variable, stated
    rather than assumed; widening the pre-filter is not permitted as a substitute for it.

    **The real-tree distribution (A=27 / B1=11 / B2=2 / other=0) is asserted in WP05/T023, not
    here.** It is a *census* claim: ``discovered == census u E``, and WP03's canonical owner and
    retained-pin probe are class members by construction, so ``discover(Path("tests"))`` returns
    40 before WP03 lands and 42 after. Only WP05 can see both ``discover()`` and ``E`` and
    subtract one from the other; a fixed distribution asserted in this package reds on a change
    the specification mandates. ``other`` keeps its population-0 assertion and its positive
    control here, because that is a *classifier* claim and does not move with ``E``.

    **Accepted residual risk (issue-5-delete-sync-transport, tracked at #119).** The
    sync-transport deletion removed every real-tree member the keyed/innermost readings could
    disagree about, so
    ``tests/architectural/test_home_pin_scan_limbs.py::test_kind_distribution_over_the_real_tree_mechanises_c004``
    can no longer red on attribution-depth drift over the real tree -- only its synthetic
    ``test_kind_distribution_mechanises_c004_at_the_keyed_def`` sibling still forces
    ``keyed != innermost``. Accepted because the real tree's discrimination arm is a byproduct of
    which members happen to exist, not something this package can restore by itself; reintroduce
    the directional assertion over the real tree if a future member again puts ``test-body`` and
    ``helper`` in disagreement.
    """
    outer = chain[0]
    start, end = outer.lineno, outer.end_lineno or outer.lineno
    inside = [site for site in home_sites if start <= site.lineno <= end]
    if not inside:
        return "A"
    last = max(inside, key=lambda site: site.lineno)
    value = resolve_value(last.value, bindings)
    if value == TMP_PATH_HOME:
        return "B1"
    return "B2" if value == TMP_PATH_USER_HOME else "other"


def discover(root: Path, *, prefilter: bool = True) -> set[Member]:
    """The whole pass: **both** variables resolved, ``home_partition`` attached, keys at the boundary.

    Root-parameterised (FR-009) so every guard behaviour is exercisable against a synthetic tree
    without editing a real test module, and prefilter-parameterised so OD-002 form (a) is one
    classifier called twice rather than two implementations agreeing with each other.

    **Asserts exactly-one over its own output** using the repository's D-1 rule
    (``assert_descriptor_unique_within_qualname`` / ``ContentDescriptor.occurrence``): if two
    members ever produce the same key the pass RAISES :class:`DuplicateMemberKeyError` rather
    than silently deduplicating.
    """
    keyed: list[tuple[MemberKey, _SiteRecord]] = [
        (member_key(record.relpath, record.source, record.site.lineno), record)
        for record in _scan_records(root, prefilter)
    ]
    _assert_exactly_one(keyed)
    return {
        Member(
            key=key,
            lineno=record.site.lineno,
            home_partition=record.home_partition,
            relpath=record.relpath,
            kind=record.attribution.kind,
            params=record.attribution.params,
            resolved_value=record.resolved_value,
        )
        for key, record in keyed
    }


def _assert_exactly_one(keyed: Sequence[tuple[MemberKey, _SiteRecord]]) -> None:
    """The D-1 "exactly-one, never ≥1" rule, applied **over discover's own output**.

    **Recorded deviation, raised rather than silently repaired.** C-012(5) names
    ``assert_descriptor_unique_within_qualname`` as the mechanism; applied literally — resolving
    each member's ``(qualname, token_substring)`` against its *file* — that primitive asserts a
    **different and measurably false** predicate. Measured on the real tree it raises at
    ``tests/cli/commands/test_sync_commands.py`` inside ``_isolated_home``, where three
    consecutive ``monkeypatch.setenv`` calls (``SPEC_KITTY_HOME``, ``HOME``, ``LOCALAPPDATA``)
    share one normalized token line because ``code_tokens_by_line`` strips string literals — and
    **only one of the three is a member**. Source-scoped uniqueness is therefore not the property
    C-012(5) asks for; the property is *"if two **members** ever produce the same key the guard
    reds rather than silently deduplicating"*, which is this check. ``ContentDescriptor`` is kept
    as the diagnostic vehicle so the failure is reported in the repository's own idiom.
    """
    counts: dict[MemberKey, list[int]] = {}
    for key, record in keyed:
        counts.setdefault(key, []).append(record.site.lineno)
    collisions = sorted((key, lines) for key, lines in counts.items() if len(lines) > 1)
    if not collisions:
        return
    detail = "; ".join(
        repr(
            ContentDescriptor(
                rel_path=key[0],
                qualname=key[1],
                token_substring=key[2],
                occurrence=len(lines),
                rationale=f"R1a home-pin member identity collision at lines {sorted(lines)}",
            )
        )
        for key, lines in collisions
    )
    raise DuplicateMemberKeyError(
        f"{len(collisions)} MemberKey collision class(es) among discovered members — a future "
        f"collision must red here rather than silently deduplicate (C-012(5)): {detail}"
    )


def kind_distribution(
    root: Path, *, at: Literal["keyed", "innermost"] = "keyed", prefilter: bool = True
) -> dict[str, int]:
    """The ``kind`` distribution at the **keyed** def or at the **innermost** def.

    C-012(4): **this mapping, not the key set, is how C-004 is mechanised.** Measured over the
    real tree the keyed reading is ``{fixture: 30, test-body: 10, helper: 0}`` and the innermost
    reading is ``{30, 9, 1}`` — exactly the withdrawn split. An implementer who attributes to the
    innermost def reds here, in this package, rather than failing SC-001 two packages downstream.
    """
    counts: dict[str, int] = {"fixture": 0, "test-body": 0, "helper": 0}
    for record in _scan_records(root, prefilter):
        node = record.chain[record.attribution.keyed_index] if at == "keyed" else record.chain[-1]
        counts[def_kind(node)] += 1
    return counts


# ---------------------------------------------------------------------------
# T004 — the inert SUB-FORM registry's production matchers
# ---------------------------------------------------------------------------

#: A parsed corpus: ``(relpath, tree)`` pairs.
Corpus = tuple[tuple[str, ast.Module], ...]

#: Ids whose published denominator is the **unfiltered** walk. FR-007 measures the ``HOME``
#: sub-forms over the **85** ``HOME`` sites in 50 files, not over the pre-filtered 52 in 29, so
#: their empty-set assertions run unfiltered — a pre-filtered emptiness would be a weaker claim
#: wearing the same green. The ``SPEC_KITTY_HOME`` ids and SC-002b are pre-filtered, where the
#: filter over-selects by construction (C-003 form (i)).
_UNFILTERED_IDS: frozenset[str] = frozenset(
    {
        "HOME-SETDEFAULT",
        "HOME-VAL-OSPATHJOIN",
        "HOME-VAL-PERCENT",
        "HOME-VAL-FORMAT",
        "HOME-VAL-CONCAT",
        "WITHITEM-VALUE-REF",
    }
)

#: ``id -> (env key, write form, required bare-receiver flag or None)``.
_WRITE_FORM_IDS: dict[str, tuple[str, WriteForm, bool | None]] = {
    "SKH-SETDEFAULT": (NEEDLE, "setdefault", None),
    "HOME-SETDEFAULT": (HOME_KEY, "setdefault", None),
    "SKH-BARE-SETENV": (NEEDLE, "setenv", True),
}

#: ``id -> (env key, value sub-form token)``.
_VALUE_SUB_FORM_IDS: dict[str, tuple[str, str]] = {
    "SKH-VAL-OSPATHJOIN": (NEEDLE, "OSPATHJOIN"),
    "SKH-VAL-PERCENT": (NEEDLE, "PERCENT"),
    "SKH-VAL-FORMAT": (NEEDLE, "FORMAT"),
    "SKH-VAL-CONCAT": (NEEDLE, "CONCAT"),
    "HOME-VAL-OSPATHJOIN": (HOME_KEY, "OSPATHJOIN"),
    "HOME-VAL-PERCENT": (HOME_KEY, "PERCENT"),
    "HOME-VAL-FORMAT": (HOME_KEY, "FORMAT"),
    "HOME-VAL-CONCAT": (HOME_KEY, "CONCAT"),
}


@lru_cache(maxsize=8)
def _corpus(root: Path, prefilter: bool) -> Corpus:
    """Parse ``root`` once per ``(root, prefilter)`` so fifteen registry checks share one walk.

    **Caveat for future consumers: the cache is keyed on the root PATH, not on its contents.**
    A caller that materialises a tree, scans it, then rewrites files under the **same** root
    within one process gets the first parse back. No live path reaches that today — every
    synthetic tree is a fresh ``tmp_path`` and the real tree is read-only during a run — so this
    is a documented boundary rather than a bug, and it is recorded because the natural way to
    write a "mutate and re-scan" test is exactly the way that would hit it. Use a distinct root
    per materialisation, which is what FR-009's root parameter is for.
    """
    paths = enumerate_py_files(root)
    selected = byte_prefilter(paths) if prefilter else paths
    return tuple((path.relative_to(root).as_posix(), parse_module(path)) for path in selected)


def inert_hits(limb_id: str, root: Path) -> set[tuple[str, int]]:
    """``(relpath, lineno)`` for every real occurrence of the inert sub-form ``limb_id``.

    **One production matcher, run twice**: over the real tree it must return the empty set, and
    over a materialised module containing the shape it must return exactly one hit. An empty-set
    assertion without that second run is its own proof — C-003 form (ii)'s named failure — and a
    control returning ``set()`` proves nothing.

    **Any id here whose real-tree population is non-zero is a REGISTRY DEFECT, not a matcher
    defect** (FR-001): it means the registry described something that does fire.
    """
    if limb_id not in INERT_LIMBS:
        raise KeyError(f"{limb_id!r} is not a registered inert sub-form")
    if limb_id == "PARTITION-OTHER":
        return {(m.relpath, m.lineno) for m in discover(root) if m.home_partition == "other"}
    corpus = _corpus(root, limb_id not in _UNFILTERED_IDS)
    if limb_id in _WRITE_FORM_IDS:
        key, form, bare = _WRITE_FORM_IDS[limb_id]
        return _write_form_hits(corpus, key=key, form=form, bare=bare)
    if limb_id in _VALUE_SUB_FORM_IDS:
        key, token = _VALUE_SUB_FORM_IDS[limb_id]
        return _value_sub_form_hits(corpus, key=key, token=token)
    if limb_id == "WITHITEM-VALUE-REF":
        return _value_sub_form_hits(corpus, key=NEEDLE, token="WITHITEM-REF") | _value_sub_form_hits(
            corpus, key=HOME_KEY, token="WITHITEM-REF"
        )
    if limb_id == "SCOPE-EXPLICIT":
        return _scope_explicit_hits(corpus)
    return _assignment_bound_key_hits(corpus)


def bindings_for_site(
    tree: ast.Module, site: WriteSite, module_bindings: Mapping[str, ast.expr]
) -> dict[str, ast.expr]:
    """Module-level bindings overlaid with the site's own outermost enclosing ``def`` scope.

    **One assembler, used by both consumers.** ``discover`` and the inert-registry matchers need
    identical binding scope; two copies of this two-line merge is exactly the drift shape
    ``_sole_door_scan.py:13-27`` records as a live incident, at the smallest possible scale.
    """
    chain = def_chain(tree, site.lineno)
    scope: ast.AST = chain[0] if chain else tree
    return {**module_bindings, **collect_bindings(scope)}


def _write_form_hits(
    corpus: Corpus, *, key: str, form: WriteForm, bare: bool | None
) -> set[tuple[str, int]]:
    hits: set[tuple[str, int]] = set()
    for relpath, tree in corpus:
        for site in find_write_sites(tree, key=key):
            if site.form != form or (bare is not None and site.bare_receiver != bare):
                continue
            hits.add((relpath, site.lineno))
    return hits


def _value_sub_form_hits(corpus: Corpus, *, key: str, token: str) -> set[tuple[str, int]]:
    hits: set[tuple[str, int]] = set()
    for relpath, tree in corpus:
        sites = find_write_sites(tree, key=key)
        if not sites:
            continue
        module_bindings = module_level_bindings(tree)
        names = withitem_bound_names(tree)
        for site in sites:
            bindings = bindings_for_site(tree, site, module_bindings)
            if token in value_sub_forms(site.value, bindings, withitem_names=names):
                hits.add((relpath, site.lineno))
    return hits


def _scope_explicit_hits(corpus: Corpus) -> set[tuple[str, int]]:
    """Pin-bearing fixtures carrying an explicit ``scope=``.

    Structurally unreachable, which is a stronger argument than the empirical one: under a
    predicate with no decorator requirement ``scope=`` is undefined for the test-body members,
    and a non-function-scoped fixture cannot request function-scoped ``tmp_path``.
    """
    hits: set[tuple[str, int]] = set()
    for relpath, tree in corpus:
        pin_lines = {site.lineno for site in find_write_sites(tree, key=NEEDLE)}
        if not pin_lines:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end = node.end_lineno or node.lineno
            if not any(node.lineno <= line <= end for line in pin_lines):
                continue
            if _has_explicit_scope(node):
                hits.add((relpath, node.lineno))
    return hits


def _has_explicit_scope(node: FunctionNode) -> bool:
    return any(
        isinstance(decorator, ast.Call)
        and _decorator_name(decorator) == "fixture"
        and any(keyword.arg == "scope" for keyword in decorator.keywords)
        for decorator in node.decorator_list
    )


def _assignment_bound_key_hits(corpus: Corpus) -> set[tuple[str, int]]:
    """SC-002b: assignment-bound string constants valued ``"SPEC_KITTY_HOME"``.

    The pre-filter's stated premise — that the env key is a literal at the call site — and the
    only check that can falsify it. Published alongside it: **229** literal ``ast.Constant``
    occurrences in 98 files. The 229 is what makes the 0 meaningful.
    """
    hits: set[tuple[str, int]] = set()
    for relpath, tree in corpus:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets, value = _assignment_targets(node)
            if value is None or not isinstance(value, ast.Constant) or value.value != NEEDLE:
                continue
            if any(isinstance(target, (ast.Name, ast.Attribute)) for target in targets):
                hits.add((relpath, node.lineno))
    return hits


def _assignment_targets(node: ast.AST) -> tuple[list[ast.expr], ast.expr | None]:
    if isinstance(node, ast.Assign):
        return (list(node.targets), node.value)
    if isinstance(node, ast.AnnAssign):
        return ([node.target], node.value)
    return ([], None)


def literal_key_occurrences(root: Path) -> set[tuple[str, int]]:
    """Every literal ``ast.Constant`` valued ``"SPEC_KITTY_HOME"`` — SC-002b's DENOMINATOR.

    A population of 0 with no denominator cannot be audited: it is indistinguishable from a
    matcher that sees nothing at all.
    """
    hits: set[tuple[str, int]] = set()
    for relpath, tree in _corpus(root, True):
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == NEEDLE:
                hits.add((relpath, node.lineno))
    return hits


# ---------------------------------------------------------------------------
# T005 — the census and baseline generators, and the one regeneration entry
# ---------------------------------------------------------------------------

GENERATED_BY = "tests/architectural/_home_pin_scan.py"
#: **FR-004(2): this must name the command that actually reproduces the artefact.**
#: It is emitted into BOTH artefacts' headers, so an omission here sends a maintainer down a path
#: that regenerates a census with ``E`` still in it — the failure T022 names — and an invented
#: flag sends them nowhere at all. ``test_the_shipped_regeneration_command_names_every_flag_it_needs``
#: PARSES this string against :func:`build_parser` rather than eyeballing it.
REGENERATION_COMMAND = (
    "python -m tests.architectural._home_pin_scan --root tests --frozen-at-sha <sha> "
    "--owed-to '#3121' --exempt-module tests.architectural._home_pin_exempt"
)
CENSUS_PATH = "tests/architectural/census/spec_kitty_home_pin_R1a.yaml"
BASELINE_PATH = "tests/architectural/spec_kitty_home_pin_baseline.yaml"
TOMBSTONE_MANIFEST_PATH = "tests/architectural/census/spec_kitty_home_pin_tombstones.yaml"
#: The invariant half of the census header's ``fragility_note``. The variable half is DERIVED
#: from :func:`fragility_register` — see :func:`_render_fragility_note`.
FRAGILITY_NOTE_BASE = (
    "Generated, never hand-edited. `frozen_at_sha` and `owed_to` are HEADER SCALARS, not row "
    "columns, and there is no `reason` column: rationale that would be a per-row reason belongs "
    "here. Direction is mechanised by the separate baseline artefact, never by this file. Rows "
    "exempted by `E` are NOT rows of this census -- they are hashed into the baseline's "
    "`exempt_set_sha256`, because with `E` inside the census `census u E` is a no-op union and "
    "`discovered == census u E` degenerates to `discovered == census`."
)

_OWED_TO_PATTERN = re.compile(r"^#[0-9]+$")

#: ``E`` is fixed-arity by type so a THIRD entry is a ``mypy --strict`` error and not a one-line
#: literal (FR-004 / SC-005). The empty alternative exists for exactly one reason: WP01 owns the
#: ``--exempt-module`` entry point and must demonstrate it **absent**, and it is the only other
#: arity this alias admits.
ExemptSet = tuple[Exempt, Exempt] | tuple[()]


@dataclass(frozen=True)
class Fragility:
    """One member whose class membership rests on something nothing defends.

    C-012(5)/§0.1b names this residual explicitly: the ``:1165`` member is held in the class by a
    ``monkeypatch`` parameter that is **declared and never referenced**, and ``ruff``'s relaxed
    ``ARG`` for ``tests/**`` will not defend it. A routine unused-argument cleanup would drop the
    member from the class **silently** — and with it the only real-tree witness for C-004's
    keyed-versus-innermost discrimination, which is why ``key_qualname_differs`` is carried here
    rather than left to be rediscovered.
    """

    key: MemberKey
    relpath: str
    lineno: int
    unused_silhouette_params: frozenset[str]
    keyed_qualname: str
    key_qualname_differs: bool


def fragility_register(root: Path, *, prefilter: bool = True) -> tuple[Fragility, ...]:
    """Every member held in the class by an unused silhouette parameter, sorted by key.

    A **subset** of ``discover()``'s output by construction, so it survives ``E`` growing the
    discovered population. Measured over ``tests/``: exactly one row, ``:1165``.
    """
    rows: list[Fragility] = []
    for record in _scan_records(root, prefilter):
        unused = _unused_silhouette_params(record.chain)
        if not unused:
            continue
        key = member_key(record.relpath, record.source, record.site.lineno)
        keyed = record.chain[record.attribution.keyed_index]
        keyed_qualname = enclosing_qualname(record.source, keyed.lineno)
        rows.append(
            Fragility(
                key=key,
                relpath=record.relpath,
                lineno=record.site.lineno,
                unused_silhouette_params=unused,
                keyed_qualname=keyed_qualname,
                key_qualname_differs=key[1] != keyed_qualname,
            )
        )
    return tuple(sorted(rows, key=lambda row: row.key))


def _unused_silhouette_params(chain: Sequence[FunctionNode]) -> frozenset[str]:
    """Silhouette-contributing parameters declared somewhere in ``chain`` and never referenced."""
    unused: set[str] = set()
    for node in chain:
        referenced = {inner.id for inner in ast.walk(node) if isinstance(inner, ast.Name)}
        for name in def_params(node):
            if normalise_params(frozenset({name})) & SILHOUETTE and name not in referenced:
                unused.add(name)
    return frozenset(unused)


def _render_fragility_note(fragility: Sequence[Fragility]) -> str:
    """T026(1): name the known-fragile rows **via the generator**, never as a hand-typed constant.

    This changes a VALUE and never a key, so the census header's asserted key set is untouched
    and nothing had to be added to carry it. The empty branch deliberately makes **no claim about
    the population** — a note that said "none" when the register simply was not supplied would be
    the same silent green this package was reopened to fix.
    """
    if not fragility:
        return (
            f"{FRAGILITY_NOTE_BASE} KNOWN-FRAGILE ROWS: not supplied to this generator call, so "
            "this census makes no claim about them; `main()` passes `fragility_register(root)`."
        )
    entries = "; ".join(
        f"{row.relpath}:{row.lineno} (held by unused "
        f"{', '.join(sorted(row.unused_silhouette_params))}"
        + (
            "; MemberKey qualname is the INNERMOST scope and differs from the keyed def "
            f"`{row.keyed_qualname}`, so this row is also C-004's only real-tree witness"
            if row.key_qualname_differs
            else ""
        )
        + ")"
        for row in fragility
    )
    return (
        f"{FRAGILITY_NOTE_BASE} KNOWN-FRAGILE ROWS, named by the generator: {entries}. Removing "
        "the unused parameter drops the row from the class with nothing red."
    )


def _sha256_of(payload: str) -> str:
    """The single checksum site in this module.

    ``# noqa: TID251`` is narrow and justified per ``pyproject.toml``'s own carve-out text: this
    is a content checksum over a KEY SET (FR-004(b)), not the charter hash over charter content,
    and ``charter.hasher.hash_content`` is a different algorithm over a different subject.
    """
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()  # noqa: TID251 — census key-set checksum, not the charter hash


def _key_set_payload(keys: Iterable[MemberKey]) -> str:
    """The **sorted, newline-joined** ``MemberKey`` triples — never the file bytes (plan §5)."""
    return "\n".join("\t".join(key) for key in sorted(keys))


def render_census(
    members: Iterable[Member], *, sha: str, owed_to: str, fragility: Sequence[Fragility] = ()
) -> str:
    """The frozen census: a header of scalars and one row per member, sorted by key.

    Row columns are exactly ``{key, lineno, kind, home_partition}``. ``frozen_at_sha`` and
    ``owed_to`` are **header scalars** — 40 rows times two columns held exactly two distinct
    values, which is the argument against a ``reason`` column relocated one level over.

    **``members`` must already have ``E`` subtracted.** This renderer does not know about ``E``
    and must not: FR-003 keeps the canonical owner out of the census, and :func:`main` is the one
    place that owns the subtraction. ``fragility`` is optional and OPTIONAL IS NOT "EMPTY" — the
    rendered note distinguishes "no fragile rows supplied" from "no fragile rows exist".
    """
    if not _OWED_TO_PATTERN.match(owed_to):
        raise ValueError(f"owed_to must match ^#[0-9]+$ and nothing else, got {owed_to!r}")
    document = {
        "header": {
            "generated_by": GENERATED_BY,
            "regeneration_command": REGENERATION_COMMAND,
            "frozen_at_sha": sha,
            "owed_to": owed_to,
            "fragility_note": _render_fragility_note(fragility),
        },
        "rows": [
            {
                "key": list(member.key),
                "lineno": member.lineno,
                "kind": member.kind,
                "home_partition": member.home_partition,
            }
            for member in sorted(members, key=lambda member: member.key)
        ],
    }
    return yaml.safe_dump(document, sort_keys=False, default_flow_style=False, allow_unicode=True)


def load_tombstone_keys(path: Path | str = TOMBSTONE_MANIFEST_PATH) -> frozenset[MemberKey]:
    """R1b's (#3121) adjudicated-away members, read from the checked-in tombstone manifest.

    The manifest is the auditable source of truth for tombstones: each entry carries the member's
    frozen 3-tuple ``key`` plus a recorded ``reason``/``evidence``. Absent or empty yields the empty
    set — the R1a state, in which the whole subsystem is a no-op. Keys are in the walk-root-relative
    space the census uses (``delivery/foo.py``), matching ``census`` keys and the baseline's own
    ``tombstones`` list. A wrong arity raises here rather than producing a tuple that silently
    compares unequal downstream.
    """
    manifest = Path(path)
    if not manifest.exists():
        return frozenset()
    document = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    keys: set[MemberKey] = set()
    for entry in document.get("tombstones", []):
        raw = entry["key"]
        if not isinstance(raw, list) or len(raw) != 3:
            raise SystemExit(f"tombstone manifest key must be a 3-element list, got {raw!r}")
        keys.add((str(raw[0]), str(raw[1]), str(raw[2])))
    return frozenset(keys)


def render_baseline(
    members: Iterable[Member],
    *,
    exempt: ExemptSet,
    tombstones: frozenset[MemberKey] = frozenset(),
) -> str:
    """The direction mechanism: a hash of the **sorted key set**, never of the file bytes.

    ``sha256(path.read_bytes())`` passes any "a hash exists" review and fails on day thirty: it
    changes under an ``owed_to`` re-point and under a comment edit, both of which leave the key
    set — the thing the ratchet compares — untouched. The tombstone list lives **here**, because
    FR-004(1) is "paths, named, not described" and putting it in the census header would collide
    with that header's asserted key set.

    R1b (#3121): ``tombstones`` are the adjudicated-away members (sourced from the manifest via
    :func:`load_tombstone_keys`). The hash is frozen over ``census_keys ∪ tombstones`` — so as a
    member is converged (leaves the census) and tombstoned, the union stays pinned to the freeze-time
    key set and the hash does not move. Empty tombstones (the R1a state) leave both the hash and the
    ``tombstones`` list identical to before this subsystem existed, so regeneration is byte-identical.
    """
    member_keys = {m.key for m in members}
    document = {
        "generated_by": GENERATED_BY,
        "regeneration_command": REGENERATION_COMMAND,
        "census_key_set_sha256": _sha256_of(_key_set_payload(member_keys | tombstones)),
        "exempt_set_sha256": _sha256_of(_key_set_payload(entry.key for entry in exempt)),
        "tombstones": [list(key) for key in sorted(tombstones)],
    }
    return yaml.safe_dump(document, sort_keys=False, default_flow_style=False, allow_unicode=True)


def build_parser() -> argparse.ArgumentParser:
    """The regeneration entry's argument parser, exposed so the shipped command can be PARSED.

    Separated from :func:`main` for one reason: ``REGENERATION_COMMAND`` is embedded in both
    artefacts' headers, and the only non-vacuous way to check it names real flags is to run it
    through the same parser the entry point uses.
    """
    parser = argparse.ArgumentParser(prog="_home_pin_scan", description="R1a home-pin regeneration")
    parser.add_argument("--root", type=Path, default=Path("tests"))
    parser.add_argument("--frozen-at-sha", required=True)
    parser.add_argument("--owed-to", default="#3121")
    parser.add_argument("--exempt-module", default=None)
    parser.add_argument("--census-out", type=Path, default=Path(CENSUS_PATH))
    parser.add_argument("--baseline-out", type=Path, default=Path(BASELINE_PATH))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """The ONE documented regeneration entry (FR-004(2)).

    ``--exempt-module`` defaults to ``None`` and is **imported here rather than at module level**
    so the import graph stays acyclic and WP01 never depends on WP03.

    **``E`` is subtracted from the census AND from the baseline's member set.** It previously fed
    only ``render_baseline``'s ``exempt=``, so the exempt entries stayed in the row set: with
    ``E`` inside the census, ``census u E`` is a **no-op union** and ``discovered == census u E``
    degenerates to ``discovered == census`` — the accounting reports success while checking
    nothing, and the canonical owner becomes a census row owed an adjudication under C-007's
    monotonic non-increase. The exempt entries belong in ``exempt_set_sha256``, never in a row.
    """
    import importlib

    args = build_parser().parse_args(argv)

    exempt: ExemptSet = ()
    if args.exempt_module is not None:
        entries = tuple(importlib.import_module(args.exempt_module).E)
        if len(entries) != 2:
            raise SystemExit(f"E must hold exactly two entries, {args.exempt_module} holds {len(entries)}")
        exempt = (entries[0], entries[1])

    exempt_keys = {entry.key for entry in exempt}
    census_members = {member for member in discover(args.root) if member.key not in exempt_keys}

    #: R1b (#3121): tombstones are the adjudicated-away members. Fail closed if any tombstoned key
    #: is still a live census member — a tombstone records an adjudication that removed the pin, so a
    #: tombstone over a pin still in the tree is exactly the "bought-off ratchet" the guard refuses
    #: (mirrors t024's :477 / t023's anti-abuse limb at generation time).
    tombstones = load_tombstone_keys()
    live_tombstones = tombstones & {member.key for member in census_members}
    if live_tombstones:
        raise SystemExit(
            "tombstone manifest names members whose pin is still in the tree (a tombstone requires a "
            f"real removal, not a hidden one): {sorted(live_tombstones)}"
        )

    args.census_out.parent.mkdir(parents=True, exist_ok=True)
    args.baseline_out.parent.mkdir(parents=True, exist_ok=True)
    args.census_out.write_text(
        render_census(
            census_members,
            sha=args.frozen_at_sha,
            owed_to=args.owed_to,
            fragility=fragility_register(args.root),
        ),
        encoding="utf-8",
    )
    args.baseline_out.write_text(
        render_baseline(census_members, exempt=exempt, tombstones=tombstones), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
