"""Load and validate the Contract Registry YAML (#2441 / FR-001, FR-002).

This is the generalisation of the shim-registry chain
(:mod:`specify_cli.compat.registry`) into a **Contract Registry**: a modeled,
owned artifact for shared contracts + their declared consumer set + their
retirement obligations. Where ``ShimEntry`` models exactly one kind of shared
contract — the ``fallback_name`` (compat) re-export — a :class:`ContractRecord`
models ``kind ∈ {fallback_name, retired_literal}``, carries the **declared
consumer set** that ``ShimEntry`` lacked (``consumers.scan_roots`` +
``exemptions`` + optional ``test_shards`` / ``call_sites``), and anchors on
**content, never on ``file:line``** (DIR-041 / NFR-003).

``ShimEntry`` becomes the ``kind == "fallback_name"`` projection of this model:
its ``legacy_path`` is a dotted-``symbol`` anchor, its ``canonical_import`` is
``replaced_by``, and its release window is ``retirement``.

The shape mirrors ``compat/registry.py`` deliberately: same ``ruamel.yaml``
safe-load, same "collect all errors then raise" validation strategy, same
frozen-dataclass typed projection, same ``resolve_*_path`` +
``load_registry`` + ``validate_registry`` function set — so the two registries
read as one family and the later fold (C-001 follow-up) is mechanical.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from packaging.version import InvalidVersion, Version
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from specify_cli.contracts.anchoring import (
    FORBIDDEN_POSITIONAL_FIELDS,
    is_file_line_anchor,
)

_DOTTED_NAME = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[a-z]\d+)?$")
_TRACKER = re.compile(r"^(#\d+|https?://.+)$")

_ALLOWED_KINDS = frozenset({"fallback_name", "retired_literal"})
_ALLOWED_STATUSES = frozenset({"active", "deprecated", "retired"})
_ALLOWED_ENFORCEMENT = frozenset({"advisory", "enforcing"})

_REQUIRED_KEYS = frozenset(
    {
        "id",
        "kind",
        "anchor",
        "status",
        "owner",
        "replaced_by",
        "retirement",
        "consumers",
        "verification",
    }
)
_OPTIONAL_KEYS = frozenset({"notes"})
_ALL_KNOWN_KEYS = _REQUIRED_KEYS | _OPTIONAL_KEYS

_RETIREMENT_REQUIRED = frozenset({"introduced_in", "removal_target", "tracker_issue"})
_CONSUMERS_REQUIRED = frozenset({"scan_roots", "exemptions"})
_CONSUMERS_OPTIONAL = frozenset({"test_shards", "call_sites"})
_CONSUMERS_KNOWN = _CONSUMERS_REQUIRED | _CONSUMERS_OPTIONAL


# The Contract Registry is a docs-scoped sibling of ``docs/migrations/
# shim-registry.yaml`` (design §3.4 + C-001): it runs on the arch pole's
# docs-only trim exactly like the shim registry and ``test_no_legacy_*`` family.
_CONTRACT_REGISTRY_PATH: tuple[str, ...] = ("docs", "contracts", "contract-registry.yaml")


def resolve_contract_registry_path(repo_root: Path) -> Path:
    """Return the canonical ``docs/contracts/contract-registry.yaml`` path.

    The path is returned whether or not it exists so callers raise a
    forward-correct :class:`FileNotFoundError` naming the canonical home,
    mirroring :func:`specify_cli.compat.registry.resolve_shim_registry_path`.
    """
    return repo_root.joinpath(*_CONTRACT_REGISTRY_PATH)


@dataclasses.dataclass(frozen=True)
class ContractAnchor:
    """The content-addressed identity of a shared contract (never ``file:line``).

    Exactly one arm is populated per record:

    * ``symbol`` — a dotted Python name, for ``kind == "fallback_name"``
      (and, in a later WP, ``signature``).
    * ``literals`` — one or more reconstructed fixed strings, for
      ``kind == "retired_literal"``. Each literal is stored in the manifest
      either as a plain ``value:`` OR as a ``fragments:`` list the loader joins
      (the fragment form is the generalised self-flag defence: a record for a
      forbidden term can name that term without the manifest itself tripping the
      very sweep it models — mirroring ``test_no_legacy_terminology.py``'s
      ``"cere" + "mony"`` construction).
    """

    symbol: str | None
    literals: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class ContractRetirement:
    introduced_in: str
    removal_target: str
    tracker_issue: str


@dataclasses.dataclass(frozen=True)
class ContractConsumers:
    """The DECLARED consumer set — the missing piece ``ShimEntry`` never had."""

    scan_roots: tuple[str, ...]
    exemptions: tuple[str, ...]
    test_shards: tuple[str, ...] = ()
    call_sites: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ContractVerification:
    enforcement: str


@dataclasses.dataclass(frozen=True)
class ContractRecord:
    id: str
    kind: str
    anchor: ContractAnchor
    status: str
    owner: str
    replaced_by: str
    retirement: ContractRetirement
    consumers: ContractConsumers
    verification: ContractVerification
    notes: str | None = None


@dataclasses.dataclass(frozen=True)
class ContractRegistryReport:
    """Result of ``spec-kitty doctor contracts`` — a validated registry snapshot."""

    records: list[ContractRecord]
    registry_path: Path

    @property
    def record_count(self) -> int:
        return len(self.records)

    @property
    def advisory_count(self) -> int:
        return sum(1 for r in self.records if r.verification.enforcement == "advisory")

    @property
    def enforcing_count(self) -> int:
        return sum(1 for r in self.records if r.verification.enforcement == "enforcing")


class ContractRegistrySchemaError(Exception):
    """Raised when the Contract Registry YAML fails schema validation."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_registry(repo_root: Path) -> list[ContractRecord]:
    """Load, validate, and project the registry into typed records.

    Raises :class:`FileNotFoundError` when the manifest is absent and
    :class:`ContractRegistrySchemaError` on any parse or schema failure.
    """
    registry_path = resolve_contract_registry_path(repo_root)
    if not registry_path.exists():
        raise FileNotFoundError(f"Contract registry not found at {registry_path}")
    yaml = YAML(typ="safe")
    try:
        with registry_path.open() as fp:
            data = yaml.load(fp)
    except YAMLError as exc:
        raise ContractRegistrySchemaError([f"YAML parse error: {exc}"]) from exc
    validate_registry(data)
    return [_build_record(entry) for entry in data["contracts"]]


def check_contract_registry(repo_root: Path) -> ContractRegistryReport:
    """Load + validate the registry and return a report (the doctor engine).

    Structural validity is the ONLY enforcing gate in v1 (spec FR-002 / NFR-002):
    a malformed record — or one that reintroduces ``file:line`` anchoring — raises
    :class:`ContractRegistrySchemaError` here and the command exits non-zero.
    """
    registry_path = resolve_contract_registry_path(repo_root)
    records = load_registry(repo_root)
    return ContractRegistryReport(records=records, registry_path=registry_path)


# ---------------------------------------------------------------------------
# Typed projection (only reached after validation passes)
# ---------------------------------------------------------------------------


def _reconstruct_literal(entry: object) -> str:
    """Join a validated literal entry (``value:`` or ``fragments:``) to a string."""
    assert isinstance(entry, dict)
    if "value" in entry:
        value = entry["value"]
        assert isinstance(value, str)
        return value
    fragments = entry["fragments"]
    assert isinstance(fragments, list)
    return "".join(str(part) for part in fragments)


def _build_anchor(anchor: dict[str, object]) -> ContractAnchor:
    symbol = anchor.get("symbol")
    literals_raw = anchor.get("literals")
    literals: tuple[str, ...] = ()
    if isinstance(literals_raw, list):
        literals = tuple(_reconstruct_literal(item) for item in literals_raw)
    return ContractAnchor(
        symbol=symbol if isinstance(symbol, str) else None,
        literals=literals,
    )


def _str_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _build_record(entry: dict[str, object]) -> ContractRecord:
    anchor = entry["anchor"]
    retirement = entry["retirement"]
    consumers = entry["consumers"]
    verification = entry["verification"]
    assert isinstance(anchor, dict)
    assert isinstance(retirement, dict)
    assert isinstance(consumers, dict)
    assert isinstance(verification, dict)
    notes = entry.get("notes")
    return ContractRecord(
        id=str(entry["id"]),
        kind=str(entry["kind"]),
        anchor=_build_anchor(anchor),
        status=str(entry["status"]),
        owner=str(entry["owner"]),
        replaced_by=str(entry["replaced_by"]),
        retirement=ContractRetirement(
            introduced_in=str(retirement["introduced_in"]),
            removal_target=str(retirement["removal_target"]),
            tracker_issue=str(retirement["tracker_issue"]),
        ),
        consumers=ContractConsumers(
            scan_roots=_str_tuple(consumers["scan_roots"]),
            exemptions=_str_tuple(consumers["exemptions"]),
            test_shards=_str_tuple(consumers.get("test_shards")),
            call_sites=_str_tuple(consumers.get("call_sites")),
        ),
        verification=ContractVerification(enforcement=str(verification["enforcement"])),
        notes=notes if isinstance(notes, str) else None,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _reject_positional_anchors(prefix: str, obj: object, errors: list[str]) -> None:
    """Recursively reject any ``file:line`` positional anchor (NFR-003 / DIR-041).

    The registry must not become the rot it replaces. Two shapes are rejected
    ANYWHERE in a record: a forbidden field name (``file`` / ``line`` / ...),
    and a string value shaped like ``path/to/file.py:42``.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key in FORBIDDEN_POSITIONAL_FIELDS:
                errors.append(
                    f"{prefix}.{key}: positional 'file:line' anchoring is forbidden "
                    f"(NFR-003/DIR-041) — anchor on a dotted symbol or a fixed literal"
                )
            _reject_positional_anchors(f"{prefix}.{key}", value, errors)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _reject_positional_anchors(f"{prefix}[{i}]", item, errors)
    elif isinstance(obj, str) and is_file_line_anchor(obj):
        errors.append(
            f"{prefix}: value {obj!r} is a positional 'file:line' anchor, which is "
            f"forbidden (NFR-003/DIR-041) — anchor on content, never a line number"
        )


def _validate_literal_entry(prefix: str, entry: object, errors: list[str]) -> None:
    if not isinstance(entry, dict):
        errors.append(f"{prefix}: each literal must be a mapping with 'value' or 'fragments'")
        return
    has_value = "value" in entry
    has_fragments = "fragments" in entry
    if has_value == has_fragments:
        errors.append(f"{prefix}: exactly one of 'value' or 'fragments' is required")
        return
    if has_value:
        val = entry["value"]
        if not isinstance(val, str) or not val:
            errors.append(f"{prefix}.value: must be a non-empty string")
        return
    frags = entry["fragments"]
    if not isinstance(frags, list) or not frags:
        errors.append(f"{prefix}.fragments: must be a non-empty list of strings")
        return
    if any(not isinstance(part, str) for part in frags):
        errors.append(f"{prefix}.fragments: every fragment must be a string")
        return
    joined = "".join(frags)
    if not joined:
        errors.append(f"{prefix}.fragments: joined value must be non-empty")
    elif is_file_line_anchor(joined):
        # WP01-review gap: a file:line split across fragments (e.g.
        # ["src/foo.py", ":42"]) reconstructs to "src/foo.py:42" and slips past
        # the per-fragment DIR-041 guard, which only inspects each benign
        # fragment in isolation. Reject the reconstructed positional anchor here,
        # at the join seam, before any consumer (loader/driver) anchors on it.
        errors.append(
            f"{prefix}.fragments: joined value {joined!r} is a positional "
            f"'file:line' anchor, which is forbidden (NFR-003/DIR-041) — "
            f"fragments must not reconstruct a line number"
        )


def _validate_anchor(i: int, kind: object, anchor: object, errors: list[str]) -> None:
    p = f"contracts[{i}].anchor"
    if not isinstance(anchor, dict):
        errors.append(f"{p}: must be a mapping")
        return
    if kind == "fallback_name":
        symbol = anchor.get("symbol")
        if not isinstance(symbol, str) or not _DOTTED_NAME.match(symbol):
            errors.append(f"{p}.symbol: must be a dotted identifier for kind 'fallback_name'")
        if "literals" in anchor:
            errors.append(f"{p}: kind 'fallback_name' uses 'symbol', not 'literals'")
    elif kind == "retired_literal":
        literals = anchor.get("literals")
        if not isinstance(literals, list) or not literals:
            errors.append(f"{p}.literals: must be a non-empty list for kind 'retired_literal'")
        else:
            for j, item in enumerate(literals):
                _validate_literal_entry(f"{p}.literals[{j}]", item, errors)
        if "symbol" in anchor:
            errors.append(f"{p}: kind 'retired_literal' uses 'literals', not 'symbol'")


def _validate_retirement(i: int, retirement: object, errors: list[str]) -> None:
    p = f"contracts[{i}].retirement"
    if not isinstance(retirement, dict):
        errors.append(f"{p}: must be a mapping")
        return
    for key in sorted(_RETIREMENT_REQUIRED - set(retirement)):
        errors.append(f"{p}.{key}: required field is missing")
    intro = retirement.get("introduced_in")
    removal = retirement.get("removal_target")
    for field, val in (("introduced_in", intro), ("removal_target", removal)):
        if not isinstance(val, str) or not _SEMVER.match(val):
            errors.append(f"{p}.{field}: must be a semver string like '3.4.0'")
    if isinstance(intro, str) and isinstance(removal, str) and _SEMVER.match(intro) and _SEMVER.match(removal):
        try:
            if Version(removal) < Version(intro):
                errors.append(f"{p}.removal_target: must be >= introduced_in")
        except InvalidVersion:
            errors.append(f"{p}: version strings are not valid semver")
    ti = retirement.get("tracker_issue")
    if not isinstance(ti, str) or not _TRACKER.match(ti):
        errors.append(f"{p}.tracker_issue: must be '#123' or a URL")


def _validate_str_list(prefix: str, value: object, errors: list[str], *, allow_empty: bool) -> None:
    if not isinstance(value, list):
        errors.append(f"{prefix}: must be a list of strings")
        return
    if not value and not allow_empty:
        errors.append(f"{prefix}: must not be empty")
    if any(not isinstance(item, str) for item in value):
        errors.append(f"{prefix}: every item must be a string")


def _validate_consumers(i: int, consumers: object, errors: list[str]) -> None:
    p = f"contracts[{i}].consumers"
    if not isinstance(consumers, dict):
        errors.append(f"{p}: must be a mapping")
        return
    for key in sorted(set(consumers) - _CONSUMERS_KNOWN):
        errors.append(f"{p}.{key}: unknown field")
    for key in sorted(_CONSUMERS_REQUIRED - set(consumers)):
        errors.append(f"{p}.{key}: required field is missing")
    if "scan_roots" in consumers:
        _validate_str_list(f"{p}.scan_roots", consumers["scan_roots"], errors, allow_empty=False)
    if "exemptions" in consumers:
        _validate_str_list(f"{p}.exemptions", consumers["exemptions"], errors, allow_empty=True)
    for opt in ("test_shards", "call_sites"):
        if opt in consumers:
            _validate_str_list(f"{p}.{opt}", consumers[opt], errors, allow_empty=True)


def _validate_verification(i: int, verification: object, errors: list[str]) -> None:
    p = f"contracts[{i}].verification"
    if not isinstance(verification, dict):
        errors.append(f"{p}: must be a mapping")
        return
    enforcement = verification.get("enforcement")
    if enforcement not in _ALLOWED_ENFORCEMENT:
        errors.append(f"{p}.enforcement: must be one of {sorted(_ALLOWED_ENFORCEMENT)}")


def _validate_scalar_fields(i: int, entry: dict[str, object], seen_ids: set[str], errors: list[str]) -> None:
    p = f"contracts[{i}]"
    rid = entry.get("id")
    if not isinstance(rid, str) or not rid:
        errors.append(f"{p}.id: must be a non-empty string")
    elif rid in seen_ids:
        errors.append(f"{p}.id: duplicate value '{rid}'")
    else:
        seen_ids.add(rid)

    if entry.get("kind") not in _ALLOWED_KINDS:
        errors.append(f"{p}.kind: must be one of {sorted(_ALLOWED_KINDS)}")
    if entry.get("status") not in _ALLOWED_STATUSES:
        errors.append(f"{p}.status: must be one of {sorted(_ALLOWED_STATUSES)}")
    for field in ("owner", "replaced_by"):
        val = entry.get(field)
        if not isinstance(val, str) or not val:
            errors.append(f"{p}.{field}: must be a non-empty string")
    notes = entry.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append(f"{p}.notes: if present, must be a string")


def _validate_entry(i: int, entry: object, seen_ids: set[str], errors: list[str]) -> None:
    if not isinstance(entry, dict):
        errors.append(f"contracts[{i}]: must be a mapping")
        return

    for key in sorted(set(entry) - _ALL_KNOWN_KEYS):
        errors.append(f"contracts[{i}].{key}: unknown field")
    missing = _REQUIRED_KEYS - set(entry)
    for key in sorted(missing):
        errors.append(f"contracts[{i}].{key}: required field is missing")

    # DIR-041 guard runs over whatever IS present, regardless of missing keys.
    _reject_positional_anchors(f"contracts[{i}]", entry, errors)
    if missing:
        return

    _validate_scalar_fields(i, entry, seen_ids, errors)
    _validate_anchor(i, entry.get("kind"), entry["anchor"], errors)
    _validate_retirement(i, entry["retirement"], errors)
    _validate_consumers(i, entry["consumers"], errors)
    _validate_verification(i, entry["verification"], errors)


def validate_registry(data: object) -> None:
    """Validate the whole manifest, collecting every error before raising."""
    if not isinstance(data, dict) or "contracts" not in data:
        raise ContractRegistrySchemaError(["top-level: must be a mapping with a 'contracts' key"])
    if not isinstance(data["contracts"], list):
        raise ContractRegistrySchemaError(["top-level.contracts: must be a list"])

    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, entry in enumerate(data["contracts"]):
        _validate_entry(i, entry, seen_ids, errors)

    if errors:
        raise ContractRegistrySchemaError(errors)
