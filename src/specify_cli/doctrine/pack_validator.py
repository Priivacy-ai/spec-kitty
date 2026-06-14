"""Pack-layout validation for org doctrine packs.

See ``kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/pack-layout.md``
for the normative contract enforced here.

Validation performs (in order):

1. **Directory existence**.
2. **Per-artifact schema validation** against the relevant Pydantic model.
3. **ID uniqueness** within each artifact type directory.
4. **DRG extension validation** when ``drg/`` is present: every URN referenced
   by a fragment edge must resolve to a node in ``built-in ∪ pack-artifacts``
   and no extension may modify an existing built-in node's ``kind``.
5. **Intent-aware collision checks** (FR-011..FR-013, mission
   ``charter-ux-and-org-pack-vocabulary-01KSAF14``): consult each pack
   artifact's ``enhances`` / ``overrides`` fields and emit one of the
   following categories per the precedence table in
   ``kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/pack-validator-advisory.md``:

   * ``intent_conflict`` ERROR — both fields declared.
   * ``unknown_target`` ERROR — declared target ID is not a built-in.
   * ``same_id_collision`` ADVISORY (reworded) — same-ID collision with no declared intent.

6. **Optional duplicate DRG edge advisories**.
7. **Optional org-charter.yaml schema validation** (gracefully skipped when
   the ``specify_cli.doctrine.org_charter`` module is not yet shipped —
   WP09 owns that file).

Issue ``category`` values surfaced via ``ValidationIssue.category``:
``schema_invalid``, ``duplicate_id``, ``drg_dangling_edge``, ``drg_kind_drift``,
``duplicate_drg_edge``, ``same_id_collision``, ``unknown_target``,
``intent_conflict``, plus structural categories for the ``pack`` and
``org-charter`` artifact types.

The public surface is intentionally small:

* :class:`ValidationIssue`
* :class:`ValidationResult`
* :func:`validate_pack`
* :func:`render_validation_result`
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_pack",
    "render_validation_result",
]


# ---------------------------------------------------------------------------
# Plural artifact kinds that carry the augmentation vocabulary.
#
# FR-030 single-source: derived from
# ``doctrine.drg.org_pack_loader.augmentation_plural_kinds()`` rather than a
# second hand-synced table. Adding an augmentation-eligible kind is a one-line
# change at that single source and both the loader auto-emitter and this
# validator pick it up. Coverage is the full augmentation-eligible set:
# the original five (tactics, styleguides, paradigms, procedures,
# agent_profiles) plus the newly-covered kinds (directives, toolguides,
# mission_step_contracts, mission_types — FR-028, FR-032).
# ---------------------------------------------------------------------------

from doctrine.drg.org_pack_loader import augmentation_plural_kinds

_AUGMENTATION_PLURAL_KINDS: frozenset[str] = augmentation_plural_kinds()
FragmentIntent = dict[str, dict[str, tuple[dict[str, str], Path]]]


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single issue surfaced by :func:`validate_pack`.

    The ``category`` field classifies the issue (FR-012, FR-013 — mission
    ``charter-ux-and-org-pack-vocabulary-01KSAF14``). Valid values:

    * ``schema_invalid`` — schema validation error.
    * ``duplicate_id`` — two artifacts share the same ID within a kind.
    * ``drg_dangling_edge`` — a fragment edge references an unknown URN.
    * ``drg_kind_drift`` — a fragment attempts to change a built-in node's kind.
    * ``duplicate_drg_edge`` — same edge declared in two fragments.
    * ``same_id_collision`` — pack ID matches a built-in with no declared intent.
    * ``unknown_target`` — declared ``enhances`` / ``overrides`` target is not a built-in.
    * ``intent_conflict`` — both ``enhances`` and ``overrides`` declared on one artifact.
    * ``not_found`` / ``parse_error`` / ``advisory`` — structural categories.
    """

    severity: str  # "error" | "advisory"
    artifact_type: str  # "directives", "drg", "org-charter", ...
    artifact_id: str | None
    file: str
    message: str
    category: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "file": self.file,
            "message": self.message,
        }
        if self.category is not None:
            payload["category"] = self.category
        return payload


@dataclass
class ValidationResult:
    """Aggregate outcome of pack validation."""

    ok: bool
    errors: list[ValidationIssue] = field(default_factory=list)
    advisories: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": [issue.to_dict() for issue in self.errors],
            "advisories": [issue.to_dict() for issue in self.advisories],
        }


# ---------------------------------------------------------------------------
# Artifact-type registry
# ---------------------------------------------------------------------------


def _artifact_schema_registry() -> dict[str, tuple[str, type[BaseModel]]]:
    """Map plural directory name → ``(glob_pattern, pydantic_model)``.

    Imported lazily to avoid loading the heavy doctrine package at module
    import time (keeps ``--help`` snappy).
    """
    from doctrine.agent_profiles.profile import AgentProfile
    from doctrine.directives.models import Directive
    from doctrine.missions.step_contracts import MissionStepContract
    from doctrine.paradigms.models import Paradigm
    from doctrine.procedures.models import Procedure
    from doctrine.styleguides.models import Styleguide
    from doctrine.tactics.models import Tactic
    from doctrine.toolguides.models import Toolguide

    return {
        "directives": ("*.directive.yaml", Directive),
        "tactics": ("*.tactic.yaml", Tactic),
        "styleguides": ("*.styleguide.yaml", Styleguide),
        "toolguides": ("*.toolguide.yaml", Toolguide),
        "paradigms": ("*.paradigm.yaml", Paradigm),
        "procedures": ("*.procedure.yaml", Procedure),
        "agent_profiles": ("*.agent.yaml", AgentProfile),
        "mission_step_contracts": ("*.step-contract.yaml", MissionStepContract),
    }


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------


def _yaml_parser() -> YAML:
    return YAML(typ="safe")


def _scan_files(directory: Path, glob: str) -> list[Path]:
    """Return sorted files matching *glob*; recursive for styleguides."""
    if directory.name == "styleguides":
        return sorted(directory.rglob(glob))
    return sorted(directory.glob(glob))


def _safe_load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Parse *path* as YAML.  Returns ``(data, error_msg)``."""
    try:
        data = _yaml_parser().load(path)
    except (YAMLError, OSError) as exc:
        return None, f"YAML parse error: {exc}"
    if data is None:
        return None, "empty YAML document"
    if not isinstance(data, dict):
        return None, "expected a YAML mapping at top level"
    return data, None


# ---------------------------------------------------------------------------
# Per-directory artifact scan (extracted to keep ``validate_pack`` simple)
# ---------------------------------------------------------------------------


def _scan_artifact_directory(  # noqa: PLR0913 — small helper kept private to this module
    *,
    plural: str,
    type_dir: Path,
    glob: str,
    schema_cls: type[BaseModel],
    errors: list[ValidationIssue],
    pack_artifact_urns: set[str],
    pack_artifact_ids_per_type: dict[str, set[str]],
    pack_artifacts_data: dict[str, dict[str, tuple[dict[str, Any], Path]]],
) -> None:
    """Walk one artifact-type directory and update the shared collectors.

    Side-effects only: appends to ``errors``, mutates the URN /
    ID-per-type / raw-data collectors. Extracted from
    :func:`validate_pack` so the entry point stays under ruff's C901 limit.
    """
    seen_ids: dict[str, Path] = {}
    for yaml_file in _scan_files(type_dir, glob):
        data, parse_err = _safe_load(yaml_file)
        if parse_err is not None:
            errors.append(
                ValidationIssue(
                    severity="error",
                    artifact_type=plural,
                    artifact_id=None,
                    file=str(yaml_file),
                    message=parse_err,
                    category="parse_error",
                )
            )
            continue
        assert data is not None  # mypy
        artifact_id = data.get("id")
        # FR-011 (WP06): when both `overrides` and `enhances` are declared
        # in the raw YAML, route the issue through the intent-aware pass
        # (it emits `intent_conflict`) instead of the generic
        # `schema_invalid` from the Pydantic cross-field validator.
        both_intent_fields_set = (
            isinstance(data.get("overrides"), str)
            and bool(data.get("overrides"))
            and isinstance(data.get("enhances"), str)
            and bool(data.get("enhances"))
        )
        if (
            isinstance(artifact_id, str)
            and artifact_id
            and plural in _AUGMENTATION_PLURAL_KINDS
        ):
            pack_artifacts_data.setdefault(plural, {}).setdefault(
                artifact_id, (data, yaml_file)
            )
            if both_intent_fields_set:
                # The intent-aware pass owns the error. Track the ID so
                # downstream checks still see it as a known artifact.
                pack_artifact_ids_per_type.setdefault(plural, set()).add(
                    artifact_id
                )
                seen_ids[artifact_id] = yaml_file
                urn_kind = _plural_to_urn_kind(plural)
                if urn_kind is not None:
                    pack_artifact_urns.add(f"{urn_kind}:{artifact_id}")
                continue
        try:
            schema_cls.model_validate(data)
        except ValidationError as exc:
            errors.append(
                ValidationIssue(
                    severity="error",
                    artifact_type=plural,
                    artifact_id=str(artifact_id) if artifact_id else None,
                    file=str(yaml_file),
                    message=(
                        f"schema validation failed: "
                        f"{exc.errors()[0].get('msg', exc)}"
                    ),
                    category="schema_invalid",
                )
            )
            continue
        if not isinstance(artifact_id, str) or not artifact_id:
            # Defensive guard: schema enforces non-empty string ids.
            continue
        if artifact_id in seen_ids:
            errors.append(
                ValidationIssue(
                    severity="error",
                    artifact_type=plural,
                    artifact_id=artifact_id,
                    file=str(yaml_file),
                    message=(
                        f"duplicate id '{artifact_id}' "
                        f"(also defined in {seen_ids[artifact_id].name})"
                    ),
                    category="duplicate_id",
                )
            )
            continue
        seen_ids[artifact_id] = yaml_file
        pack_artifact_ids_per_type.setdefault(plural, set()).add(artifact_id)
        pack_artifacts_data.setdefault(plural, {}).setdefault(
            artifact_id, (data, yaml_file)
        )
        urn_kind = _plural_to_urn_kind(plural)
        if urn_kind is not None:
            pack_artifact_urns.add(f"{urn_kind}:{artifact_id}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def validate_pack(pack_dir: Path) -> ValidationResult:
    """Validate a doctrine pack directory.

    Returns a :class:`ValidationResult` with ``ok=False`` if any error was
    found.  Advisories do not affect ``ok``.
    """
    errors: list[ValidationIssue] = []
    advisories: list[ValidationIssue] = []

    if not pack_dir.exists() or not pack_dir.is_dir():
        errors.append(
            ValidationIssue(
                severity="error",
                artifact_type="pack",
                artifact_id=None,
                file=str(pack_dir),
                message=f"pack directory not found: {pack_dir}",
                category="not_found",
            )
        )
        return ValidationResult(ok=False, errors=errors, advisories=advisories)

    registry = _artifact_schema_registry()

    # Collect all artifact IDs present in this pack (used by DRG and advisory).
    pack_artifact_urns: set[str] = set()
    pack_artifact_ids_per_type: dict[str, set[str]] = {}
    # Capture raw per-artifact YAML data keyed by ``(plural, id) -> (data, file)``
    # so the intent-aware collision pass can inspect ``enhances`` / ``overrides``
    # fields (FR-011..FR-013, WP06 T037).
    pack_artifacts_data: dict[str, dict[str, tuple[dict[str, Any], Path]]] = {}

    for plural, (glob, schema_cls) in registry.items():
        type_dir = pack_dir / plural
        if not type_dir.is_dir():
            continue
        _scan_artifact_directory(
            plural=plural,
            type_dir=type_dir,
            glob=glob,
            schema_cls=schema_cls,
            errors=errors,
            pack_artifact_urns=pack_artifact_urns,
            pack_artifact_ids_per_type=pack_artifact_ids_per_type,
            pack_artifacts_data=pack_artifacts_data,
        )

    # DRG validation (only if drg/ exists).
    drg_dir = pack_dir / "drg"
    if drg_dir.is_dir():
        drg_errors, drg_advisories = _validate_drg(drg_dir, pack_artifact_urns)
        errors.extend(drg_errors)
        advisories.extend(drg_advisories)

    # FR-011..FR-013 (WP06 T037): intent-aware collision messages. This replaces
    # the legacy unconditional ``_built_in_id_collision_advisories`` pass.
    # FR-028 hard cutover retired ``enhances``/``overrides`` inline fields on
    # tactics and styleguides.  Pre-collect DRG fragment intent so the
    # field-based pass can suppress same-ID advisories for artifacts whose
    # intent is declared via DRG edges instead of inline fields.
    built_in_ids_per_kind = _load_built_in_ids_per_kind()
    fragment_intent: FragmentIntent = {}
    if drg_dir.is_dir():
        fragment_intent = _collect_fragment_edge_intent(drg_dir)
    intent_errors, intent_advisories = _intent_aware_collision_messages(
        pack_artifacts_data,
        built_in_ids_per_kind,
        fragment_intent=fragment_intent,
    )
    errors.extend(intent_errors)
    advisories.extend(intent_advisories)

    # FR-031 (T016): apply the SAME intent-aware precedence to augmentation
    # relationships authored as DRG **fragment edges** — the authoring surface
    # for the newly-covered kinds (directives, toolguides, mission step
    # contracts, mission types), which under the locked fragment-only model
    # (data-model §3) cannot carry the legacy ``enhances`` / ``overrides``
    # fields. Reading fragment edges gives the new kinds parity with the
    # original five: declared intent suppresses the same-ID advisory, an
    # unknown target hard-errors, and both relations on one source ->
    # ``intent_conflict``.
    if drg_dir.is_dir():
        frag_errors, frag_advisories = _intent_aware_collision_messages_from_edges(
            fragment_intent,
            built_in_ids_per_kind,
            pack_artifacts_data,
        )
        errors.extend(frag_errors)
        advisories.extend(frag_advisories)

    # T044: validate optional org-charter.yaml (best-effort — module may be
    # absent in early-mission states before WP09 ships).
    advisories_or_errors = _validate_org_charter(
        pack_dir, pack_artifact_ids_per_type.get("directives", set())
    )
    for issue in advisories_or_errors:
        if issue.severity == "error":
            errors.append(issue)
        else:
            advisories.append(issue)

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        advisories=advisories,
    )


# ---------------------------------------------------------------------------
# DRG validation
# ---------------------------------------------------------------------------


def _plural_to_urn_kind(plural: str) -> str | None:
    """Return the DRG ``NodeKind`` string matching this artifact plural."""
    mapping = {
        "directives": "directive",
        "tactics": "tactic",
        "styleguides": "styleguide",
        "toolguides": "toolguide",
        "paradigms": "paradigm",
        "procedures": "procedure",
        "agent_profiles": "agent_profile",
        "mission_step_contracts": "mission_step_contract",
    }
    return mapping.get(plural)


def _validate_drg(
    drg_dir: Path,
    pack_artifact_urns: set[str],
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    """Validate the pack's DRG extension fragments.

    Performs:

    * load all ``*.graph.yaml`` fragments;
    * load the built-in DRG (best-effort — missing built-in graph is treated
      as an empty node set so the validator still runs in stripped test
      environments);
    * verify every fragment edge references a URN in
      ``built-in ∪ pack_artifact_urns``;
    * verify no fragment node overrides a built-in node's ``kind``;
    * advisory for duplicate edges across fragments.
    """
    errors: list[ValidationIssue] = []
    advisories: list[ValidationIssue] = []

    try:
        from doctrine.drg.loader import DRGLoadError, load_graph
    except ModuleNotFoundError:  # pragma: no cover - doctrine package always present
        return errors, advisories

    fragments = sorted(drg_dir.glob("*.graph.yaml"))
    if not fragments:
        return errors, advisories

    # Load built-in graph (best-effort).
    built_in_urns: set[str] = set()
    built_in_kinds: dict[str, str] = {}
    try:
        from charter.catalog import resolve_doctrine_root

        built_in_graph = load_graph(resolve_doctrine_root() / "graph.yaml")
        built_in_urns = {n.urn for n in built_in_graph.nodes}
        built_in_kinds = {n.urn: n.kind.value for n in built_in_graph.nodes}
    except (ModuleNotFoundError, DRGLoadError, OSError):
        # Test environments may strip the built-in graph; carry on with an
        # empty built-in set so dangling-edge detection still operates over
        # the pack's own URNs.
        pass

    known_urns = built_in_urns | pack_artifact_urns
    seen_edges: dict[tuple[str, str, str], Path] = {}

    for fragment in fragments:
        try:
            graph = load_graph(fragment)
        except DRGLoadError as exc:
            errors.append(
                ValidationIssue(
                    severity="error",
                    artifact_type="drg",
                    artifact_id=None,
                    file=str(fragment),
                    message=f"failed to load DRG fragment: {exc}",
                )
            )
            continue

        # Nodes: must not change built-in node kinds.
        for node in graph.nodes:
            built_in_kind = built_in_kinds.get(node.urn)
            if built_in_kind is not None and built_in_kind != node.kind.value:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type="drg",
                        artifact_id=node.urn,
                        file=str(fragment),
                        message=(
                            f"node {node.urn} attempts to change built-in kind "
                            f"{built_in_kind!r} → {node.kind.value!r}"
                        ),
                        category="drg_kind_drift",
                    )
                )
            # Adding new nodes is fine; track them as known URNs.
            known_urns.add(node.urn)

        # Edges: source and target must resolve.
        for edge in graph.edges:
            for role, urn in (("source", edge.source), ("target", edge.target)):
                if urn not in known_urns:
                    errors.append(
                        ValidationIssue(
                            severity="error",
                            artifact_type="drg",
                            artifact_id=urn,
                            file=str(fragment),
                            message=(
                                f"dangling DRG edge — {role} URN {urn!r} "
                                f"not in built-in or pack artifact set"
                            ),
                            category="drg_dangling_edge",
                        )
                    )
            key = (edge.source, edge.target, edge.relation.value)
            if key in seen_edges:
                advisories.append(
                    ValidationIssue(
                        severity="advisory",
                        artifact_type="drg",
                        artifact_id=None,
                        file=str(fragment),
                        message=(
                            f"duplicate edge "
                            f"({edge.source} -[{edge.relation.value}]-> {edge.target}) "
                            f"already present in {seen_edges[key].name}"
                        ),
                        category="duplicate_drg_edge",
                    )
                )
            else:
                seen_edges[key] = fragment

    return errors, advisories


# ---------------------------------------------------------------------------
# Built-in ID lookup (shared by intent-aware collision pass, WP06 T037)
# ---------------------------------------------------------------------------


def _kind_singular(plural: str) -> str:
    """Return the singular form of an artifact plural for human-facing messages."""
    if plural == "agent_profiles":
        return "agent_profile"
    if plural == "mission_step_contracts":
        return "mission_step_contract"
    return plural[:-1] if plural.endswith("s") else plural


def _load_built_in_ids_per_kind() -> dict[str, set[str]]:
    """Return the set of built-in artifact IDs per plural directory.

    Best-effort: when the built-in doctrine root cannot be located (stripped
    test environment), returns an empty mapping. Callers must treat absent
    entries as "no known built-ins for this kind", which downgrades the
    intent-aware pass to a no-op for that kind.
    """
    ids_per_kind: dict[str, set[str]] = {}
    try:
        from charter.catalog import resolve_doctrine_root
    except ModuleNotFoundError:  # pragma: no cover - doctrine always present
        return ids_per_kind

    try:
        built_in_root = resolve_doctrine_root()
    except (RuntimeError, OSError):  # pragma: no cover - defensive
        return ids_per_kind

    registry = _artifact_schema_registry()
    parser = _yaml_parser()
    for plural, (glob, _schema) in registry.items():
        built_in_dir = built_in_root / plural / "built-in"
        if not built_in_dir.is_dir():
            continue
        collected: set[str] = set()
        for built_in_file in built_in_dir.rglob(glob):
            try:
                data = parser.load(built_in_file)
            except (YAMLError, OSError):
                continue
            if isinstance(data, dict) and isinstance(data.get("id"), str):
                collected.add(data["id"])
        if collected:
            ids_per_kind[plural] = collected
    return ids_per_kind


# ---------------------------------------------------------------------------
# Intent-aware collision pass (FR-011..FR-013, WP06 T037)
# ---------------------------------------------------------------------------


def _intent_aware_collision_messages(
    pack_artifacts: dict[str, dict[str, tuple[dict[str, Any], Path]]],
    built_in_ids_per_kind: dict[str, set[str]],
    fragment_intent: FragmentIntent | None = None,
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    """Emit intent-aware errors and advisories for pack artifacts.

    Implements the precedence table from
    ``kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/pack-validator-advisory.md``:

    1. Both ``overrides`` and ``enhances`` set -> ``intent_conflict`` ERROR.
    2. ``overrides`` references unknown built-in ID -> ``unknown_target`` ERROR.
    3. ``enhances`` references unknown built-in ID -> ``unknown_target`` ERROR.
    4. Either field declared and target valid -> suppress advisory.
    5. Neither declared, ID matches built-in -> ``same_id_collision`` ADVISORY (reworded).
       Exception: if ``fragment_intent`` carries a valid declared intent via DRG
       edge (FR-028 migration path for kinds where inline fields are retired), the
       advisory is suppressed here to maintain parity.
    6. Neither declared, no built-in collision -> nothing.

    Returns ``(errors, advisories)``.
    """
    errors: list[ValidationIssue] = []
    advisories: list[ValidationIssue] = []

    for plural in sorted(pack_artifacts):
        artifacts = pack_artifacts[plural]
        built_ins = built_in_ids_per_kind.get(plural, set())
        singular = _kind_singular(plural)
        for art_id in sorted(artifacts):
            data, source_file = artifacts[art_id]
            overrides_field = data.get("overrides")
            enhances_field = data.get("enhances")
            overrides_set = isinstance(overrides_field, str) and overrides_field
            enhances_set = isinstance(enhances_field, str) and enhances_field

            # 1. Both declared -> intent_conflict ERROR. The Pydantic model's
            #    validator typically catches this at schema time, but we
            #    duplicate the check here so the same precedence applies even
            #    when the schema layer is bypassed or skipped.
            if overrides_set and enhances_set:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type=plural,
                        artifact_id=art_id,
                        file=str(source_file),
                        message=(
                            f"overrides and enhances are mutually exclusive on "
                            f"{singular} {art_id}"
                        ),
                        category="intent_conflict",
                    )
                )
                continue

            # 2. overrides target unknown -> unknown_target ERROR.
            if overrides_set and overrides_field not in built_ins:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type=plural,
                        artifact_id=art_id,
                        file=str(source_file),
                        message=(
                            f"{singular} {art_id} declares overrides: "
                            f"{overrides_field}, but no built-in {singular} "
                            f"with that id exists"
                        ),
                        category="unknown_target",
                    )
                )
                continue

            # 3. enhances target unknown -> unknown_target ERROR.
            if enhances_set and enhances_field not in built_ins:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type=plural,
                        artifact_id=art_id,
                        file=str(source_file),
                        message=(
                            f"{singular} {art_id} declares enhances: "
                            f"{enhances_field}, but no built-in {singular} "
                            f"with that id exists"
                        ),
                        category="unknown_target",
                    )
                )
                continue

            # 4. Either declared and target valid -> suppress advisory.
            if overrides_set or enhances_set:
                continue

            # 5. Neither declared and ID matches built-in -> reworded advisory.
            if art_id in built_ins:
                # FR-028 migration path: inline fields retired on some kinds;
                # check DRG fragment edges as the authoritative intent source.
                if fragment_intent is not None:
                    edge_record = (fragment_intent.get(plural) or {}).get(art_id)
                    if edge_record is not None:
                        intent_map = edge_record[0] if isinstance(edge_record, tuple) else edge_record
                        edge_enhances = intent_map.get("enhances") if isinstance(intent_map, dict) else None
                        edge_overrides = intent_map.get("overrides") if isinstance(intent_map, dict) else None
                        if edge_enhances == art_id or edge_overrides == art_id:
                            continue  # valid declared intent via DRG edge suppresses advisory
                advisories.append(
                    ValidationIssue(
                        severity="advisory",
                        artifact_type=plural,
                        artifact_id=art_id,
                        file=str(source_file),
                        message=(
                            f"artifact id {art_id!r} will field-merge into the "
                            f"built-in {singular} — declare "
                            f"'enhances: {art_id}' to suppress this advisory, "
                            f"or 'overrides: {art_id}' to declare a full replacement"
                        ),
                        category="same_id_collision",
                    )
                )

            # 6. Neither declared and no built-in collision -> no message.

    return errors, advisories


# ---------------------------------------------------------------------------
# Fragment-edge intent pass (FR-031, T016) — parity for the newly-covered kinds
# ---------------------------------------------------------------------------


def _urn_to_plural(urn: str) -> tuple[str, str] | None:
    """Split a ``kind:id`` URN into ``(plural_dir, artifact_id)``.

    Returns ``None`` when the URN is malformed or its singular kind has no
    plural directory in the augmentation-eligible set.
    """
    singular, sep, artifact_id = urn.partition(":")
    if not sep or not singular or not artifact_id:
        return None
    plural = _SINGULAR_TO_PLURAL_AUGMENTATION.get(singular)
    if plural is None:
        return None
    return plural, artifact_id


def _collect_fragment_edge_intent(
    drg_dir: Path,
) -> FragmentIntent:
    """Read augmentation/lineage intent from DRG fragment edges.

    Returns ``{plural: {artifact_id: (intent, fragment_path)}}`` where
    *intent* maps the declared relation name (``enhances`` / ``overrides``) to
    its target artifact id. ``specializes_from`` is a lineage relation, not an
    augmentation-collision intent, so it is intentionally not folded into the
    same-ID/unknown-target precedence here (it neither suppresses nor conflicts
    with augmentation intent). Best-effort: unparseable fragments are skipped
    (``_validate_drg`` surfaces those load errors).
    """
    from doctrine.drg.models import Relation

    try:
        from doctrine.drg.loader import DRGLoadError, load_graph
    except ModuleNotFoundError:  # pragma: no cover - doctrine always present
        return {}

    augmentation_relations = {Relation.ENHANCES.value, Relation.OVERRIDES.value}
    intent: dict[str, dict[str, tuple[dict[str, str], Path]]] = {}
    for fragment in sorted(drg_dir.glob("*.graph.yaml")):
        try:
            graph = load_graph(fragment)
        except DRGLoadError:
            continue
        for edge in graph.edges:
            relation = edge.relation.value
            if relation not in augmentation_relations:
                continue
            source = _urn_to_plural(edge.source)
            target = _urn_to_plural(edge.target)
            if source is None or target is None:
                continue
            plural, art_id = source
            if plural not in _AUGMENTATION_PLURAL_KINDS:
                continue
            record = intent.setdefault(plural, {}).setdefault(art_id, ({}, fragment))[0]
            record[relation] = target[1]
    return intent


def _intent_aware_collision_messages_from_edges(
    fragment_intent: FragmentIntent,
    built_in_ids_per_kind: dict[str, set[str]],
    field_artifacts: dict[str, dict[str, tuple[dict[str, Any], Path]]],
) -> tuple[list[ValidationIssue], list[ValidationIssue]]:
    """Apply the intent-aware precedence to fragment-authored augmentation edges.

    Mirrors :func:`_intent_aware_collision_messages` but sources intent from
    fragment edges. Artifacts already covered by the field-based pass
    (*field_artifacts*) are skipped to avoid duplicate diagnostics.

    Precedence (parity with the original five, FR-031):

    1. both ``enhances`` and ``overrides`` declared for one source ->
       ``intent_conflict`` ERROR.
    2. target not a known built-in -> ``unknown_target`` ERROR.
    3. valid intent declared -> suppress the same-ID advisory (no message).
    """
    errors: list[ValidationIssue] = []
    advisories: list[ValidationIssue] = []

    for plural in sorted(fragment_intent):
        built_ins = built_in_ids_per_kind.get(plural, set())
        singular = _kind_singular(plural)
        field_ids = set(field_artifacts.get(plural, {}))
        for art_id in sorted(fragment_intent[plural]):
            if art_id in field_ids:
                # Skip when the field-based path declared intent via inline
                # fields — it owns the advisory for that artifact.
                # Also skip when the artifact ID does NOT collide with a
                # built-in: no advisory was produced by the field-based path
                # and processing the edge here would produce a spurious
                # ``unknown_target`` error for self-referential augmentation
                # edges that declare intent on non-built-in IDs.
                #
                # FR-028 retired ``enhances``/``overrides`` inline fields on
                # tactics and styleguides. For those artifacts the field-based
                # path produces a ``same_id_collision`` advisory (no inline
                # intent) even though the edge-based path carries the correct
                # declared intent.  We must NOT skip those artifacts so the
                # edge-based path can suppress the advisory.
                field_data = field_artifacts.get(plural, {}).get(art_id)
                has_field_intent = False
                if field_data is not None:
                    raw_data = field_data[0]
                    has_field_intent = bool(
                        raw_data.get("enhances") or raw_data.get("overrides")
                    )
                has_builtin_collision = art_id in built_ins
                if has_field_intent or not has_builtin_collision:
                    continue  # field-based path handles it, or no collision exists
                # Fall through: built-in collision exists but inline intent was
                # retired (FR-028); edge-based path takes over.
            record, fragment = fragment_intent[plural][art_id]
            overrides_target = record.get("overrides")
            enhances_target = record.get("enhances")

            if overrides_target and enhances_target:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type=plural,
                        artifact_id=art_id,
                        file=str(fragment),
                        message=(
                            f"overrides and enhances are mutually exclusive on "
                            f"{singular} {art_id} (declared via DRG fragment edges)"
                        ),
                        category="intent_conflict",
                    )
                )
                continue

            for relation, target in (
                ("overrides", overrides_target),
                ("enhances", enhances_target),
            ):
                if target and target not in built_ins:
                    errors.append(
                        ValidationIssue(
                            severity="error",
                            artifact_type=plural,
                            artifact_id=art_id,
                            file=str(fragment),
                            message=(
                                f"{singular} {art_id} declares {relation}: "
                                f"{target} (via DRG fragment edge), but no "
                                f"built-in {singular} with that id exists"
                            ),
                            category="unknown_target",
                        )
                    )
            # Valid declared intent suppresses the same-ID advisory: emit nothing.

    return errors, advisories


#: Singular URN kind -> plural directory, restricted to augmentation-eligible
#: kinds. Derived from the single source in ``org_pack_loader`` (FR-030) so the
#: fragment-edge intent pass never re-declares the kind set.
def _build_singular_to_plural() -> dict[str, str]:
    from doctrine.drg.org_pack_loader import AUGMENTATION_ELIGIBLE_KINDS

    return dict(AUGMENTATION_ELIGIBLE_KINDS)


_SINGULAR_TO_PLURAL_AUGMENTATION: dict[str, str] = _build_singular_to_plural()


# ---------------------------------------------------------------------------
# org-charter.yaml validation (T044)
# ---------------------------------------------------------------------------


def _validate_org_charter(
    pack_dir: Path,
    pack_directive_ids: set[str],
) -> list[ValidationIssue]:
    """Validate optional ``pack_dir/org-charter.yaml``.

    Gracefully degrades when ``specify_cli.doctrine.org_charter`` is not
    available (WP09 ships that module).
    """
    issues: list[ValidationIssue] = []
    charter_path = pack_dir / "org-charter.yaml"
    if not charter_path.exists():
        return issues

    # Lazy import — WP09 has not necessarily shipped yet.
    try:
        from specify_cli.doctrine.org_charter import (
            OrgCharterPolicy,
        )
    except ModuleNotFoundError:
        # The model is not yet available; surface a single advisory so the
        # operator knows validation was partial but the file is recognised.
        issues.append(
            ValidationIssue(
                severity="advisory",
                artifact_type="org-charter",
                artifact_id=None,
                file=str(charter_path),
                message=(
                    "org-charter.yaml present but OrgCharterPolicy model "
                    "is not installed; skipping schema validation"
                ),
            )
        )
        return issues
    except ImportError:  # pragma: no cover - identical to ModuleNotFoundError
        return issues

    data, parse_err = _safe_load(charter_path)
    if parse_err is not None:
        issues.append(
            ValidationIssue(
                severity="error",
                artifact_type="org-charter",
                artifact_id=None,
                file=str(charter_path),
                message=parse_err,
            )
        )
        return issues
    assert data is not None
    try:
        policy = OrgCharterPolicy.model_validate(data)
    except ValidationError as exc:
        issues.append(
            ValidationIssue(
                severity="error",
                artifact_type="org-charter",
                artifact_id=None,
                file=str(charter_path),
                message=f"org-charter schema validation failed: {exc.errors()[0].get('msg', exc)}",
            )
        )
        return issues

    # Advisory: unknown enforcement values on governance policies.
    for gp in getattr(policy, "governance_policies", []) or []:
        enforcement = getattr(gp, "enforcement", None)
        if enforcement is not None and str(enforcement) != "advisory":
            issues.append(
                ValidationIssue(
                    severity="advisory",
                    artifact_type="org-charter",
                    artifact_id=getattr(gp, "field", None),
                    file=str(charter_path),
                    message=(
                        f"governance policy uses non-advisory enforcement "
                        f"{enforcement!r}; only 'advisory' is recognised today"
                    ),
                )
            )

    # Advisory: required_directives referencing IDs not in this pack
    # (could exist in another pack or in built-in — still worth surfacing).
    required = getattr(policy, "required_directives", []) or []
    for required_id in required:
        if required_id not in pack_directive_ids:
            issues.append(
                ValidationIssue(
                    severity="advisory",
                    artifact_type="org-charter",
                    artifact_id=required_id,
                    file=str(charter_path),
                    message=(
                        f"required_directive {required_id!r} not found in "
                        f"this pack's directives/ (may exist in another pack "
                        f"or in built-in doctrine)"
                    ),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_validation_result(
    result: ValidationResult,
    *,
    json_output: bool = False,
) -> None:
    """Render *result* to stdout.

    Human format::

        ✓ pack/directives/foo.directive.yaml — OK
        ✗ pack/directives/bar.directive.yaml — Error: missing required field 'title'
        ⚠ advisory: artifact id 'DIR-003' overrides a built-in directive
        Pack validation: 1 error, 1 advisory

    JSON format::

        {"ok": false, "errors": [...], "advisories": [...]}
    """
    if json_output:
        print(json.dumps(result.to_dict(), sort_keys=True))
        return

    for issue in result.errors:
        prefix = f"{issue.artifact_type}"
        if issue.artifact_id:
            prefix += f"/{issue.artifact_id}"
        category_suffix = f" ({issue.category})" if issue.category else ""
        print(f"✗ {issue.file} [{prefix}]{category_suffix} — Error: {issue.message}")

    for issue in result.advisories:
        prefix = f"{issue.artifact_type}"
        if issue.artifact_id:
            prefix += f"/{issue.artifact_id}"
        category_suffix = f" ({issue.category})" if issue.category else ""
        print(f"⚠ advisory [{prefix}]{category_suffix}: {issue.message}")

    summary = (
        f"Pack validation: {len(result.errors)} error"
        f"{'s' if len(result.errors) != 1 else ''}, "
        f"{len(result.advisories)} advisor"
        f"{'ies' if len(result.advisories) != 1 else 'y'}"
    )
    print(summary)
