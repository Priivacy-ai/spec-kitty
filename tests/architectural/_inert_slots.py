"""Checker behind ``test_no_inert_schema_slots`` — declared slots with no producer.

The *definition* this implements, its calibration anchors, and the withdrawn
self-annihilating earlier definition are all recorded in the docstring of
``tests/architectural/test_no_inert_schema_slots.py``. Read that first; this module
only encodes it.

The three rules that carry all the weight, restated because getting any of them
wrong silently empties the report:

1. A schema ``definitions/`` entry is **not** a slot — it is a ``$ref`` target. Only
   keys under a ``properties:`` mapping are slots, wherever that mapping appears
   (including inside a ``definitions/`` entry, whose properties *are* places data
   goes).
2. The generated schemas are **not** producers. They are the thing being checked.
3. A class-body annotated assignment is a *declaration*, not a production. Counting
   it as a producer would make every model field its own producer — the same
   by-construction vacuity as rule 2.

Reader/writer asymmetry falls out of the AST rules: ``cfg["x"] = v`` is a store
target and produces ``x``; ``cfg["x"]`` and ``cfg.get("x")`` are loads and produce
nothing.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from specify_cli.status.reducer import materialize_snapshot

__all__ = [
    "ALLOWLIST",
    "BASELINE_PATH",
    "COMPLETED_LANES",
    "DISPOSITIONS",
    "UNASSIGNED_OWNER",
    "Baseline",
    "BaselineEntry",
    "BaselineError",
    "InertSlot",
    "find_inert_slots",
    "load_baseline",
    "owner_is_complete",
    "ratchet",
    "unresolved_by_completed_owners",
]

#: Zero entries, permanently. A finding is a producer that was never wired or a
#: declaration that should be deleted; ``test_allowlist_is_empty`` pins this.
ALLOWLIST: frozenset[str] = frozenset()

_SRC = "src"
_DOCTRINE = "doctrine"
_SCHEMAS = "schemas"
_SCHEMA_GLOB = "*.schema.yaml"
_MODELS_FILENAME = "models.py"
_PROPERTIES_KEY = "properties"
_ARTEFACT_SUFFIXES = frozenset({".yaml", ".yml", ".json"})
_PYDANTIC_BASE = "BaseModel"
_PYDANTIC_CONFIG_FIELD = "model_config"


def _load_keys_verbatim(text: str) -> list[object]:
    """Parse YAML with every scalar left as its source token.

    ``safe_load`` applies YAML 1.1 implicit typing, which turns a key named ``on``
    into the boolean ``True`` — a slot named ``on`` would then be reported as
    ``True`` and, worse, would fail to match an artefact that authors the same key
    under a different spelling (``yes``, ``On``). Key harvesting wants the token.
    ``BaseLoader`` constructs strings only, so it is as safe as ``safe_load``.
    """
    return list(yaml.load_all(text, Loader=yaml.BaseLoader))


@dataclass(frozen=True)
class InertSlot:
    """A declared slot that nothing in the tree populates."""

    name: str
    declared_at: Path


# --------------------------------------------------------------------------- slots


def _iter_schema_slot_names(node: object) -> Iterator[str]:
    """Yield every key under a ``properties:`` mapping, at any depth.

    Definition *names* are never yielded: they are only reached as keys of
    ``definitions``, which this never harvests. The properties *inside* a
    definition are yielded — they are real places data goes.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == _PROPERTIES_KEY and isinstance(value, dict):
                yield from (str(name) for name in value)
            yield from _iter_schema_slot_names(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_schema_slot_names(item)


def _schema_slots(root: Path) -> Iterator[InertSlot]:
    schemas = root / _SRC / _DOCTRINE / _SCHEMAS
    for path in sorted(schemas.glob(_SCHEMA_GLOB)):
        for document in _load_keys_verbatim(path.read_text(encoding="utf-8")):
            for name in _iter_schema_slot_names(document):
                yield InertSlot(name=name, declared_at=path.relative_to(root))


def _pydantic_model_classes(tree: ast.Module) -> Iterator[ast.ClassDef]:
    """Yield classes that are Pydantic models, following in-file subclassing."""
    model_names: set[str] = {_PYDANTIC_BASE}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if any(_base_name(base) in model_names for base in node.bases):
            model_names.add(node.name)
            yield node


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _iter_model_field_names(tree: ast.Module) -> Iterator[str]:
    for class_def in _pydantic_model_classes(tree):
        for statement in class_def.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if not isinstance(statement.target, ast.Name):
                continue
            name = statement.target.id
            if name.startswith("_") or name == _PYDANTIC_CONFIG_FIELD:
                continue
            yield name


def _model_slots(root: Path) -> Iterator[InertSlot]:
    doctrine = root / _SRC / _DOCTRINE
    if not doctrine.is_dir():
        return
    for path in sorted(doctrine.rglob(_MODELS_FILENAME)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for name in _iter_model_field_names(tree):
            yield InertSlot(name=name, declared_at=path.relative_to(root))


# ----------------------------------------------------------------------- producers


def _iter_mapping_keys(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _iter_mapping_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_mapping_keys(item)


def _artefact_producers(root: Path) -> set[str]:
    """Keys carried by shipped doctrine artefacts — the dominant producer form here.

    Excludes ``src/doctrine/schemas/``: the generated schemas are what is being
    checked, and admitting them makes every schema property self-producing.
    """
    doctrine = root / _SRC / _DOCTRINE
    schemas = doctrine / _SCHEMAS
    produced: set[str] = set()
    if not doctrine.is_dir():
        return produced
    for path in sorted(doctrine.rglob("*")):
        if path.suffix not in _ARTEFACT_SUFFIXES or schemas in path.parents:
            continue
        for document in _load_keys_verbatim(path.read_text(encoding="utf-8")):
            produced.update(_iter_mapping_keys(document))
    return produced


def _target_names(target: ast.expr) -> Iterator[str]:
    """Names written by an assignment target — stores only, never loads."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, ast.Attribute):
        yield target.attr
    elif isinstance(target, ast.Subscript):
        key = target.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            yield key.value
    elif isinstance(target, ast.Starred):
        yield from _target_names(target.value)
    elif isinstance(target, ast.Tuple | ast.List):
        for element in target.elts:
            yield from _target_names(element)


def _declaration_nodes(tree: ast.Module) -> set[int]:
    """Class-body annotated assignments: declarations, not productions (rule 3)."""
    declared: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            declared.update(
                id(statement)
                for statement in node.body
                if isinstance(statement, ast.AnnAssign)
            )
    return declared


def _iter_code_producer_names(tree: ast.Module) -> Iterator[str]:
    declarations = _declaration_nodes(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                yield from _target_names(target)
        elif (
            isinstance(node, ast.AugAssign | ast.AnnAssign)
            and id(node) not in declarations
        ):
            # ``declarations`` only ever holds ``AnnAssign`` ids, so the membership
            # test is a no-op for ``AugAssign`` and the two branches are one rule.
            yield from _target_names(node.target)
        elif isinstance(node, ast.Call):
            yield from (kw.arg for kw in node.keywords if kw.arg is not None)
        elif isinstance(node, ast.Dict):
            yield from (
                key.value
                for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            )


def _code_producers(root: Path) -> set[str]:
    src = root / _SRC
    produced: set[str] = set()
    if not src.is_dir():
        return produced
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        produced.update(_iter_code_producer_names(tree))
    return produced


# ------------------------------------------------------------------------- the gate


def find_inert_slots(root: Path) -> list[InertSlot]:
    """Return every declared slot under *root* that no producer populates.

    Deterministic and sorted by ``(name, declared_at)``. Works against an arbitrary
    tree — the non-vacuity test points it at a planted ``tmp_path``, which is the
    only reason that test proves anything about the shipped-tree assertion.
    """
    slots = {*_schema_slots(root), *_model_slots(root)}
    producers = _artefact_producers(root) | _code_producers(root)
    inert = [
        slot
        for slot in slots
        if slot.name not in producers and slot.name not in ALLOWLIST
    ]
    return sorted(inert, key=lambda slot: (slot.name, str(slot.declared_at)))


# ------------------------------------------------- the frozen shrink-only baseline
#
# The baseline is NOT a second allowlist. An allowlist entry is permanently
# excused; a baseline entry is debt with a named owner, a required structural
# fix, and :func:`owner_is_complete` standing behind it. ``ALLOWLIST`` stays
# ``frozenset()`` — see the baseline file's header for the full distinction.

BASELINE_PATH = Path(__file__).with_name("_inert_slots_baseline.yaml")

#: Exactly three structural answers. There is deliberately no ``accepted``, no
#: ``wont-fix``, no ``by-design`` — "leave it alone" is not a disposition.
DISPOSITIONS = frozenset(
    {"wire-the-producer", "delete-the-declaration", "fix-the-lint-definition"}
)

UNASSIGNED_OWNER = "unassigned"
_MISSION_OWNER_PREFIX = "mission:"
_MISSIONS_DIR = "kitty-specs"
_EVENT_LOG = "status.events.jsonl"

#: A WP counts as complete at ``approved``, not only at ``done``. ``done`` lands
#: at merge, so a ``done``-only gate would fire on the mainline after the fact.
#: ``approved`` is the reviewer's sign-off — the actionable moment, and the exact
#: point at which an owner could otherwise walk away from its entries.
COMPLETED_LANES = frozenset({"approved", "done"})


class BaselineError(ValueError):
    """The baseline file is malformed. Fail loud: a silently-skipped entry is a hole."""


@dataclass(frozen=True)
class BaselineEntry:
    """One frozen finding: what it is, who must clear it, and how."""

    name: str
    declared_at: Path
    owner: str
    disposition: str
    note: str
    provisional: bool

    @property
    def slot(self) -> InertSlot:
        return InertSlot(name=self.name, declared_at=self.declared_at)


@dataclass(frozen=True)
class Baseline:
    """The parsed baseline file."""

    mission: str
    entries: tuple[BaselineEntry, ...]

    @property
    def slots(self) -> frozenset[InertSlot]:
        return frozenset(entry.slot for entry in self.entries)


def _require_str(raw: object, field: str, index: int) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise BaselineError(
            f"baseline entry {index}: {field!r} must be a non-empty string, "
            f"got {raw!r}. Quote YAML-ambiguous names such as 'on' and 'yes'."
        )
    return raw


def _parse_entry(raw: object, index: int) -> BaselineEntry:
    if not isinstance(raw, dict):
        raise BaselineError(f"baseline entry {index} is not a mapping: {raw!r}")
    disposition = _require_str(raw.get("disposition"), "disposition", index)
    if disposition not in DISPOSITIONS:
        raise BaselineError(
            f"baseline entry {index}: illegal disposition {disposition!r}. "
            f"Legal values are {sorted(DISPOSITIONS)} — there is no 'accepted'."
        )
    provisional = raw.get("provisional", False)
    if not isinstance(provisional, bool):
        raise BaselineError(
            f"baseline entry {index}: 'provisional' must be a bool, got {provisional!r}"
        )
    return BaselineEntry(
        name=_require_str(raw.get("name"), "name", index),
        declared_at=Path(_require_str(raw.get("declared_at"), "declared_at", index)),
        owner=_require_str(raw.get("owner"), "owner", index),
        disposition=disposition,
        note=_require_str(raw.get("note"), "note", index),
        provisional=provisional,
    )


def load_baseline(path: Path = BASELINE_PATH) -> Baseline:
    """Parse and validate the frozen baseline, raising on anything malformed."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise BaselineError(f"{path} does not contain a mapping")
    mission = _require_str(document.get("mission"), "mission", -1)
    raw_entries = document.get("entries")
    if not isinstance(raw_entries, list):
        raise BaselineError(f"{path}: 'entries' must be a list")
    entries = tuple(
        _parse_entry(raw, index) for index, raw in enumerate(raw_entries)
    )
    seen: set[InertSlot] = set()
    for entry in entries:
        if entry.slot in seen:
            raise BaselineError(
                f"duplicate baseline entry for {entry.name!r} at {entry.declared_at}"
            )
        seen.add(entry.slot)
    return Baseline(mission=mission, entries=entries)


def ratchet(
    found: list[InertSlot], baseline: Baseline
) -> tuple[list[InertSlot], list[BaselineEntry]]:
    """Split findings against the baseline into ``(new, cleared)``.

    ``new`` — findings absent from the baseline. Growth: the gate FAILS.
    ``cleared`` — baseline entries no longer found. Shrinkage: the gate WARNS and
    the entry should be deleted from the file.
    """
    frozen = baseline.slots
    new = [slot for slot in found if slot not in frozen]
    still_found = set(found)
    cleared = [entry for entry in baseline.entries if entry.slot not in still_found]
    return new, cleared


def _mission_work_packages(root: Path, mission_slug: str) -> dict[str, Any]:
    """Reduced WP states for *mission_slug*, or ``{}`` when it has no event log.

    Uses :func:`materialize_snapshot`, the read-only sibling of ``materialize``:
    a test must never write ``status.json`` into a mission directory as a side
    effect of reading it.
    """
    mission_dir = root / _MISSIONS_DIR / mission_slug
    if not (mission_dir / _EVENT_LOG).is_file():
        return {}
    states: dict[str, Any] = materialize_snapshot(mission_dir).work_packages
    return states


def owner_is_complete(owner: str, *, root: Path, mission: str) -> bool:
    """Has *owner* finished, such that its baseline entries should be gone?

    ``unassigned``      never complete — visible pressure, not a resting place.
    ``WP##``            a work package of *mission*; complete at ``approved``/``done``.
    ``mission:<slug>``  complete when the mission has work packages and all of
                        them are complete.
    """
    if owner == UNASSIGNED_OWNER:
        return False
    if owner.startswith(_MISSION_OWNER_PREFIX):
        slug = owner.removeprefix(_MISSION_OWNER_PREFIX)
        states = _mission_work_packages(root, slug)
        return bool(states) and all(
            state.get("lane") in COMPLETED_LANES for state in states.values()
        )
    state = _mission_work_packages(root, mission).get(owner)
    return state is not None and state.get("lane") in COMPLETED_LANES


def unresolved_by_completed_owners(
    found: list[InertSlot], baseline: Baseline, *, root: Path
) -> dict[str, list[BaselineEntry]]:
    """Baseline entries still present whose owner has already completed.

    This is the anti-weasel check. Without it the baseline is an allowlist with
    better manners: an owner could mark itself complete and leave its entries
    sitting here forever.
    """
    still_found = set(found)
    offenders: dict[str, list[BaselineEntry]] = {}
    completion: dict[str, bool] = {}
    for entry in baseline.entries:
        if entry.slot not in still_found:
            continue
        if entry.owner not in completion:
            completion[entry.owner] = owner_is_complete(
                entry.owner, root=root, mission=baseline.mission
            )
        if completion[entry.owner]:
            offenders.setdefault(entry.owner, []).append(entry)
    return offenders
