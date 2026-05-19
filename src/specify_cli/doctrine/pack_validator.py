"""Pack-layout validation for org doctrine packs.

See ``kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/pack-layout.md``
for the normative contract enforced here.

Validation performs (in order):

1. **Directory existence**.
2. **Per-artifact schema validation** against the relevant Pydantic model.
3. **ID uniqueness** within each artifact type directory.
4. **DRG extension validation** when ``drg/`` is present: every URN referenced
   by a fragment edge must resolve to a node in ``shipped ∪ pack-artifacts``
   and no extension may modify an existing shipped node's ``kind``.
5. **Optional advisory checks**: shipped-ID collisions and duplicate DRG edges.
6. **Optional org-charter.yaml schema validation** (gracefully skipped when
   the ``specify_cli.doctrine.org_charter`` module is not yet shipped —
   WP09 owns that file).

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
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single issue surfaced by :func:`validate_pack`."""

    severity: str  # "error" | "advisory"
    artifact_type: str  # "directives", "drg", "org-charter", ...
    artifact_id: str | None
    file: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "artifact_type": self.artifact_type,
            "artifact_id": self.artifact_id,
            "file": self.file,
            "message": self.message,
        }


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
    from doctrine.mission_step_contracts.models import MissionStepContract
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
            )
        )
        return ValidationResult(ok=False, errors=errors, advisories=advisories)

    registry = _artifact_schema_registry()

    # Collect all artifact IDs present in this pack (used by DRG and advisory).
    pack_artifact_urns: set[str] = set()
    pack_artifact_ids_per_type: dict[str, set[str]] = {}

    for plural, (glob, schema_cls) in registry.items():
        type_dir = pack_dir / plural
        if not type_dir.is_dir():
            continue
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
                    )
                )
                continue
            assert data is not None  # mypy
            artifact_id = data.get("id")
            try:
                schema_cls.model_validate(data)
            except ValidationError as exc:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type=plural,
                        artifact_id=str(artifact_id) if artifact_id else None,
                        file=str(yaml_file),
                        message=f"schema validation failed: {exc.errors()[0].get('msg', exc)}",
                    )
                )
                continue
            # Duplicate ID detection (only after schema accepts the file).
            if not isinstance(artifact_id, str) or not artifact_id:
                # Should be unreachable post-schema; keep as defensive guard.
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
                    )
                )
                continue
            seen_ids[artifact_id] = yaml_file
            pack_artifact_ids_per_type.setdefault(plural, set()).add(artifact_id)
            # Build URN for DRG cross-checks. URN-kind mapping uses the
            # singular form (drop trailing 's' or convert ``agent_profiles``
            # → ``agent_profile``).
            urn_kind = _plural_to_urn_kind(plural)
            if urn_kind is not None:
                pack_artifact_urns.add(f"{urn_kind}:{artifact_id}")

    # DRG validation (only if drg/ exists).
    drg_dir = pack_dir / "drg"
    if drg_dir.is_dir():
        drg_errors, drg_advisories = _validate_drg(drg_dir, pack_artifact_urns)
        errors.extend(drg_errors)
        advisories.extend(drg_advisories)

    # Advisory: shipped-ID collisions.
    advisories.extend(
        _shipped_id_collision_advisories(pack_artifact_ids_per_type)
    )

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
    * load the shipped DRG (best-effort — missing shipped graph is treated
      as an empty node set so the validator still runs in stripped test
      environments);
    * verify every fragment edge references a URN in
      ``shipped ∪ pack_artifact_urns``;
    * verify no fragment node overrides a shipped node's ``kind``;
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

    # Load shipped graph (best-effort).
    shipped_urns: set[str] = set()
    shipped_kinds: dict[str, str] = {}
    try:
        from charter.catalog import resolve_doctrine_root

        shipped_graph = load_graph(resolve_doctrine_root() / "graph.yaml")
        shipped_urns = {n.urn for n in shipped_graph.nodes}
        shipped_kinds = {n.urn: n.kind.value for n in shipped_graph.nodes}
    except (ModuleNotFoundError, DRGLoadError, OSError):
        # Test environments may strip the shipped graph; carry on with an
        # empty shipped set so dangling-edge detection still operates over
        # the pack's own URNs.
        pass

    known_urns = shipped_urns | pack_artifact_urns
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

        # Nodes: must not change shipped node kinds.
        for node in graph.nodes:
            shipped_kind = shipped_kinds.get(node.urn)
            if shipped_kind is not None and shipped_kind != node.kind.value:
                errors.append(
                    ValidationIssue(
                        severity="error",
                        artifact_type="drg",
                        artifact_id=node.urn,
                        file=str(fragment),
                        message=(
                            f"node {node.urn} attempts to change shipped kind "
                            f"{shipped_kind!r} → {node.kind.value!r}"
                        ),
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
                                f"not in shipped or pack artifact set"
                            ),
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
                    )
                )
            else:
                seen_edges[key] = fragment

    return errors, advisories


# ---------------------------------------------------------------------------
# Advisory: shipped-ID collisions
# ---------------------------------------------------------------------------


def _shipped_id_collision_advisories(
    pack_artifact_ids_per_type: dict[str, set[str]],
) -> list[ValidationIssue]:
    """Emit one advisory per pack ID that already exists in shipped doctrine."""
    advisories: list[ValidationIssue] = []
    try:
        from charter.catalog import resolve_doctrine_root
    except ModuleNotFoundError:  # pragma: no cover
        return advisories

    try:
        shipped_root = resolve_doctrine_root()
    except (RuntimeError, OSError):  # pragma: no cover - defensive
        return advisories

    registry = _artifact_schema_registry()
    for plural, pack_ids in pack_artifact_ids_per_type.items():
        glob, _schema = registry[plural]
        shipped_dir = shipped_root / plural / "built-in"
        if not shipped_dir.is_dir():
            continue
        shipped_ids: set[str] = set()
        parser = _yaml_parser()
        for shipped_file in shipped_dir.rglob(glob):
            try:
                data = parser.load(shipped_file)
            except (YAMLError, OSError):
                continue
            if isinstance(data, dict) and isinstance(data.get("id"), str):
                shipped_ids.add(data["id"])
        for collision in sorted(pack_ids & shipped_ids):
            advisories.append(
                ValidationIssue(
                    severity="advisory",
                    artifact_type=plural,
                    artifact_id=collision,
                    file=str(shipped_dir),
                    message=(
                        f"artifact id {collision!r} overrides a shipped "
                        f"{plural[:-1] if plural.endswith('s') else plural}"
                    ),
                )
            )
    return advisories


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
        from specify_cli.doctrine.org_charter import (  # type: ignore[attr-defined]
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
    # (could exist in another pack or in shipped — still worth surfacing).
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
                        f"or in shipped doctrine)"
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
        ⚠ advisory: artifact id 'DIR-003' overrides a shipped directive
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
        print(f"✗ {issue.file} [{prefix}] — Error: {issue.message}")

    for issue in result.advisories:
        prefix = f"{issue.artifact_type}"
        if issue.artifact_id:
            prefix += f"/{issue.artifact_id}"
        print(f"⚠ advisory [{prefix}]: {issue.message}")

    summary = (
        f"Pack validation: {len(result.errors)} error"
        f"{'s' if len(result.errors) != 1 else ''}, "
        f"{len(result.advisories)} advisor"
        f"{'ies' if len(result.advisories) != 1 else 'y'}"
    )
    print(summary)
