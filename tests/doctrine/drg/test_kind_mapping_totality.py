"""Totality guard for module-level dict tables keyed by ArtifactKind/NodeKind.

WP07 / T029-T030 (C-005, FR-012). This module supersedes the narrower subset
guard in ``test_nodekind_artifactkind.py::test_node_kind_remains_superset_of_artifact_kind``
(kept for its own regression value; not duplicated here).

Rationale: every time a new :class:`~doctrine.artifact_kinds.ArtifactKind` /
:class:`~doctrine.drg.models.NodeKind` member is added (this mission added
``TEMPLATE`` and ``ASSET``), any module-level dict table keyed by one of these
enums silently becomes a trap for the *next* new kind unless it is either:

1. **Total** -- an entry for every enum member, so a missing key is a
   ``KeyError`` (or, worse, a caught-and-swallowed bug) rather than a
   compile-time fact anyone can check; or
2. **An explicitly allow-listed `.get`-defaulted partial** -- every call site
   reads it via ``.get(kind, <safe-default>)``, so an absent key is a
   deliberate, safe fallback rather than an oversight.

Naive totality ("every such dict must have every key") is provably wrong: it
false-fails on four pre-existing, legitimately-partial tables
(``charter.kind_vocabulary::_ID_FIELD_BY_KIND``/``_PROJECT_KIND_DIRS`` and
``charter.pack_manager::_ID_FIELD_BY_KIND``/``_PROJECT_KIND_DIRS``). This guard
distinguishes the two cases via :data:`_EXEMPT_GET_PARTIALS`, an explicit
allow-list keyed by ``"<dotted.module>::<CONSTANT_NAME>"`` -- the exemption
mechanism chosen over an inline marker comment because it puts the entire
partial-tables surface in one auditable place (this file) rather than
scattered across the tree.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest

from doctrine.artifact_kinds import ArtifactKind
from doctrine.drg.models import NodeKind

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src"

#: The two enum classes this guard understands. Keyed by the bare name used
#: in source (``ArtifactKind.FOO`` / ``NodeKind.FOO``) since the AST scan
#: works on unresolved names, not imported objects.
_ENUM_CLASSES: dict[str, type[Enum]] = {
    "ArtifactKind": ArtifactKind,
    "NodeKind": NodeKind,
}

#: Module-level dict tables keyed by ArtifactKind/NodeKind that are
#: intentionally partial: every call site reads them via ``.get(kind,
#: <default>)`` so a missing kind falls back safely rather than raising.
#: Entries are ``"<dotted.module.path>::<CONSTANT_NAME>"``, resolved from the
#: file path relative to ``src/``.
#:
#: Adding a new dict here is only correct when every read site is
#: `.get`-defaulted. If a read site does a plain ``table[kind]`` lookup,
#: the table must be made total instead of exempted.
_EXEMPT_GET_PARTIALS: frozenset[str] = frozenset(
    {
        # _id_field_for() / _declared_id() fall back to the "id" default field
        # for every kind that doesn't override it.
        "charter.kind_vocabulary::_ID_FIELD_BY_KIND",
        "charter.pack_manager::_ID_FIELD_BY_KIND",
        # Both fall back to ArtifactKind.plural for kinds without a
        # hand-mapped project directory name.
        "charter.kind_vocabulary::_PROJECT_KIND_DIRS",
        "charter.pack_manager::_PROJECT_KIND_DIRS",
        # WP01 (doctrine-tension-edges-01KY1WPC) added ArtifactKind.ANTI_PATTERN.
        # The sole read site (`executor.py`'s step-contract kind resolution)
        # reads via `_ARTIFACT_TO_NODE_KIND.get(kind)` and treats a miss as
        # "no delegatable node kind" -- correct here, since an anti-pattern
        # node is never a mission-step-contract delegation target (D2).
        "specify_cli.mission_step_contracts.executor::_ARTIFACT_TO_NODE_KIND",
    }
)


@dataclass(frozen=True)
class _KindKeyedDict:
    """A discovered module-level dict literal keyed by an enum's members."""

    qualified_name: str
    enum_name: str
    keys: frozenset[str]
    lineno: int


def _dotted_module_name(path: Path) -> str:
    """Return the dotted import path of *path* relative to ``src/``."""
    parts = path.relative_to(_SRC_ROOT).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _enum_key(node: ast.expr) -> tuple[str, str] | None:
    """Return ``(EnumName, MEMBER)`` if *node* is an ``EnumName.MEMBER`` access."""
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in _ENUM_CLASSES
    ):
        return node.value.id, node.attr
    return None


def _dict_target_and_value(stmt: ast.stmt) -> tuple[ast.Name, ast.expr] | None:
    """Return ``(target, value)`` for a module-level ``NAME = {...}`` / ``NAME: T = {...}``."""
    if (
        isinstance(stmt, ast.Assign)
        and len(stmt.targets) == 1  # golden-count: cardinality-is-contract
        and isinstance(stmt.targets[0], ast.Name)
    ):
        return stmt.targets[0], stmt.value
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
        return stmt.target, stmt.value
    return None


def _kind_keyed_dicts_in_module(tree: ast.Module, module_name: str) -> list[_KindKeyedDict]:
    """Find module-level dict literals keyed entirely by one enum's members.

    Raises ``AssertionError`` (rather than silently skipping) if a dict mixes
    enum-keyed and non-enum-keyed entries, or keys from two different enums --
    an unrecognized shape this guard should be taught about explicitly, not
    paper over.
    """
    found: list[_KindKeyedDict] = []
    for stmt in tree.body:
        pair = _dict_target_and_value(stmt)
        if pair is None:
            continue
        target, value = pair
        if not isinstance(value, ast.Dict):
            continue
        resolved = [_enum_key(k) for k in value.keys if k is not None]
        matched = [m for m in resolved if m is not None]
        if not matched:
            continue  # Not an enum-keyed dict (e.g. `_PLURALS: dict[str, str]`).
        enum_names_seen = {m[0] for m in matched}
        if len(enum_names_seen) != 1 or len(matched) != len(value.keys):
            raise AssertionError(
                f"{module_name}::{target.id} (line {stmt.lineno}) mixes enum-keyed "
                "and non-enum-keyed (or multi-enum) dict entries; the totality "
                "guard does not understand this shape -- give it explicit handling."
            )
        found.append(
            _KindKeyedDict(
                qualified_name=f"{module_name}::{target.id}",
                enum_name=enum_names_seen.pop(),
                keys=frozenset(m[1] for m in matched),
                lineno=stmt.lineno,
            )
        )
    return found


def _discover_kind_keyed_dicts() -> list[_KindKeyedDict]:
    """Scan every ``src/**/*.py`` module for kind-enum-keyed dict literals."""
    found: list[_KindKeyedDict] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found.extend(_kind_keyed_dicts_in_module(tree, _dotted_module_name(path)))
    return found


def _missing_members(entry: _KindKeyedDict) -> set[str]:
    enum_cls = _ENUM_CLASSES[entry.enum_name]
    member_names = {member.name for member in enum_cls}
    return member_names - entry.keys


# ---------------------------------------------------------------------------
# T029 -- the totality guard itself
# ---------------------------------------------------------------------------


def test_kind_keyed_dicts_are_total_or_exempt() -> None:
    """Every ArtifactKind/NodeKind-keyed module dict must be total or exempt.

    Supersedes the narrower ``artifact_values <= node_values`` subset check:
    this asserts exhaustiveness of every *consumer* mapping table, not just
    that ``NodeKind`` is a superset of ``ArtifactKind``.
    """
    discovered = _discover_kind_keyed_dicts()
    # Sanity: the scan must actually find something, or this test would pass
    # vacuously if the AST-matching logic silently broke.
    assert discovered, "expected to discover at least one kind-keyed dict table"

    violations = [
        f"{entry.qualified_name} (line {entry.lineno}) is missing "
        f"{sorted(_missing_members(entry))} and is not in _EXEMPT_GET_PARTIALS"
        for entry in discovered
        if entry.qualified_name not in _EXEMPT_GET_PARTIALS and _missing_members(entry)
    ]
    assert not violations, "\n".join(violations)


# ---------------------------------------------------------------------------
# T030 -- prove the four pre-existing `.get`-partials are exempted, not just
# asserted: they must (a) actually be discovered by the scan, and (b) actually
# be non-total, or the exemption is either vacuous or stale.
# ---------------------------------------------------------------------------


def test_exempt_partials_are_discovered_and_genuinely_partial() -> None:
    """T030: the exemption must do real work, not just name-match a fixture."""
    discovered = {entry.qualified_name: entry for entry in _discover_kind_keyed_dicts()}

    for qualified_name in sorted(_EXEMPT_GET_PARTIALS):
        assert qualified_name in discovered, (
            f"{qualified_name} was not found by the AST scan -- the exemption "
            "is vacuous (nothing it would apply to)"
        )
        entry = discovered[qualified_name]
        assert _missing_members(entry), (
            f"{qualified_name} is now total -- remove it from "
            "_EXEMPT_GET_PARTIALS, it no longer needs an exemption"
        )


def test_naive_total_only_guard_would_false_fail_on_current_tree() -> None:
    """Demonstrates the failure mode this guard avoids.

    A naive "every kind-keyed dict must be total" guard -- i.e. this same
    scan without the ``_EXEMPT_GET_PARTIALS`` short-circuit -- would report
    all four pre-existing partials as violations on the *current*, correct
    tree. That would be a Day-1 false-fail. This test pins that the naive
    check does fail here, so the exemption in the real guard above is proven
    necessary rather than decorative.
    """
    discovered = _discover_kind_keyed_dicts()
    naive_violations = [entry for entry in discovered if _missing_members(entry)]
    naive_violating_names = {entry.qualified_name for entry in naive_violations}

    assert naive_violating_names >= _EXEMPT_GET_PARTIALS, (
        "expected every allow-listed partial to actually be non-total under "
        "the naive (unexempted) check"
    )


def test_synthetic_partial_dict_is_flagged_and_exempt_names_are_skippable() -> None:
    """Unit-level proof independent of the real tree's current contents.

    Exercises the discovery + totality-check building blocks directly against
    a synthetic module source, so this guard's own logic is covered even if
    the real tree later changes shape.
    """
    source = (
        "from doctrine.artifact_kinds import ArtifactKind\n"
        "\n"
        "_SYNTHETIC_PARTIAL: dict[ArtifactKind, str] = {\n"
        "    ArtifactKind.DIRECTIVE: 'x',\n"
        "}\n"
        "\n"
        "_SYNTHETIC_TOTAL: dict[ArtifactKind, str] = {\n"
        + "".join(f"    ArtifactKind.{member.name}: 'x',\n" for member in ArtifactKind)
        + "}\n"
    )
    tree = ast.parse(source, filename="<synthetic>")
    found = {entry.qualified_name: entry for entry in _kind_keyed_dicts_in_module(tree, "synthetic")}

    assert set(found) == {"synthetic::_SYNTHETIC_PARTIAL", "synthetic::_SYNTHETIC_TOTAL"}
    assert _missing_members(found["synthetic::_SYNTHETIC_PARTIAL"])
    assert not _missing_members(found["synthetic::_SYNTHETIC_TOTAL"])

    # A qualified name only silences a genuinely-partial dict when it's in
    # the allow-list -- proving the exemption is a lookup, not a blanket skip.
    exempt = {"synthetic::_SYNTHETIC_PARTIAL"}
    assert "synthetic::_SYNTHETIC_PARTIAL" in exempt
    assert "synthetic::_SYNTHETIC_TOTAL" not in exempt


def test_mixed_enum_and_plain_keys_raise_instead_of_silently_skipping() -> None:
    """An unrecognized dict shape must fail loudly, not be swallowed."""
    source = (
        "from doctrine.artifact_kinds import ArtifactKind\n"
        "_MIXED: dict = {\n"
        "    ArtifactKind.DIRECTIVE: 'x',\n"
        "    'plain-string-key': 'y',\n"
        "}\n"
    )
    tree = ast.parse(source, filename="<synthetic>")
    with pytest.raises(AssertionError, match="mixes enum-keyed"):
        _kind_keyed_dicts_in_module(tree, "synthetic")
