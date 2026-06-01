"""Org-layer advisory checkers — `OrgOverridesBuiltinChecker` and `OrgCharterDeviationChecker`.

WP07 T036 + T047 of mission ``layered-doctrine-org-layer-01KRNPEE``.

Both checkers emit ``low`` severity findings — the org layer is informational
to the project charter, never a hard gate.  Findings carry the
``org_layer`` category so operators can filter them.

These checkers degrade silently when no org pack is configured or when the
optional ``specify_cli.doctrine.org_charter`` module (owned by WP09) has not
yet shipped — they simply return an empty finding list.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.charter_runtime.lint.findings import LintFinding

if TYPE_CHECKING:
    from charter.pack_context import PackContext


_OVERRIDABLE_ARTIFACT_TYPES: tuple[str, ...] = (
    "directives",
    "tactics",
    "styleguides",
    "toolguides",
    "paradigms",
    "procedures",
    "agent_profiles",
    "mission_step_contracts",
)


def _find_repo_root_from_drg(drg: Any) -> Path | None:
    """Best-effort resolution of the repo root from the merged DRG.

    The charter lint engine does not pass ``repo_root`` to checkers; we use
    the current working directory as a fallback because the engine itself
    is rooted there.  Callers that need a different root should invoke the
    checker directly.
    """
    _ = drg  # drg carries no repo-root metadata today
    cwd = Path.cwd()
    if (cwd / ".kittify").exists():
        return cwd
    for parent in cwd.parents:
        if (parent / ".kittify").exists():
            return parent
    return None


class OrgOverridesBuiltinChecker:
    """Advisory: the org layer overrides a built-in artifact.

    Walks every configured org pack and reports any artifact ID whose
    on-disk provenance resolves to ``"org"`` *and* whose ID also exists in
    the built-in doctrine repository.  These overrides are advisory — they
    are a legitimate org-policy lever — but operators should know that the
    built-in version has been shadowed.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root_override = repo_root

    def run(self, drg: Any, feature_scope: str | None = None) -> list[LintFinding]:
        _ = drg, feature_scope
        repo_root = self._repo_root_override or _find_repo_root_from_drg(drg)
        if repo_root is None:
            return []

        try:
            from specify_cli.doctrine.config import load_pack_registry
        except ImportError:
            return []

        registry = load_pack_registry(repo_root)
        if not registry.packs:
            return []

        # Build a service with org layer applied so provenance is populated.
        service = _build_service_with_org_layer(repo_root, registry)
        if service is None:
            return []

        # Build a built-in-only baseline to detect which IDs exist in built-in.
        built_in_only = _build_built_in_only_service(repo_root)
        if built_in_only is None:
            return []

        findings: list[LintFinding] = []
        for artifact_type in _OVERRIDABLE_ARTIFACT_TYPES:
            org_repo = getattr(service, artifact_type, None)
            built_in_repo = getattr(built_in_only, artifact_type, None)
            if org_repo is None or built_in_repo is None:
                continue
            try:
                items = org_repo.list_all()
            except Exception:  # noqa: BLE001, S112 — degrade silently on bad pack
                continue
            for item in items:
                item_id = getattr(item, "id", None)
                if not isinstance(item_id, str):
                    continue
                try:
                    provenance = org_repo.get_provenance(item_id)
                except Exception:  # noqa: BLE001, S112 — provenance is advisory only
                    continue
                if provenance != "org":
                    continue
                try:
                    builtin_match = built_in_repo.get(item_id)
                except Exception:  # noqa: BLE001
                    builtin_match = None
                if builtin_match is None:
                    continue
                findings.append(
                    LintFinding(
                        category="org_layer",
                        type="org_overrides_builtin",
                        id=f"{artifact_type}:{item_id}",
                        severity="low",
                        message=(
                            f"org layer overrides built-in {artifact_type[:-1]} "
                            f"{item_id!r}"
                        ),
                        remediation_hint=(
                            "Verify the override is intentional; remove the org pack "
                            "copy if the built-in artifact already meets policy."
                        ),
                    )
                )
        return findings


class OrgCharterDeviationChecker:
    """Advisory: project charter deviates from an org charter governance policy.

    Reads the merged ``org-charter.yaml`` policies via
    :func:`specify_cli.doctrine.org_charter.load_org_charter_policies` (owned
    by WP09).  When the module is not yet shipped, the check returns ``[]``.
    """

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root_override = repo_root

    def run(self, drg: Any, feature_scope: str | None = None) -> list[LintFinding]:
        _ = drg, feature_scope
        repo_root = self._repo_root_override or _find_repo_root_from_drg(drg)
        if repo_root is None:
            return []

        # Optional dependency on WP09's module.  When absent, advisory is a no-op.
        try:
            from specify_cli.doctrine.org_charter import (  # type: ignore[attr-defined]
                load_org_charter_policies,
            )
        except ImportError:
            return []

        _pack_ctx = None
        try:
            from charter.invocation_context import ProjectContext  # noqa: PLC0415

            _ctx = ProjectContext.from_repo(repo_root)
            _pack_ctx = _ctx.require_pack_context()
        except Exception:  # noqa: BLE001 — activation filter is best-effort
            pass

        try:
            policies = load_org_charter_policies(repo_root, pack_context=_pack_ctx)
        except Exception:  # noqa: BLE001
            return []
        governance_policies = list(getattr(policies, "governance_policies", []) or [])
        if not governance_policies:
            return []

        project_values = _load_project_charter_fields(repo_root)
        findings: list[LintFinding] = []
        for policy in governance_policies:
            field = getattr(policy, "field", None)
            expected = getattr(policy, "value", None)
            if not isinstance(field, str):
                continue
            project_val = project_values.get(field)
            if project_val is None:
                continue
            if str(project_val) == str(expected):
                continue
            findings.append(
                LintFinding(
                    category="org_layer",
                    type="org_charter_deviation",
                    id=f"governance:{field}",
                    severity="low",
                    message=(
                        f"project charter field {field!r} = {project_val!r}; "
                        f"org charter recommends {expected!r}"
                    ),
                    remediation_hint=(
                        "Reconcile via charter interview, or document an explicit "
                        "deviation in the project charter."
                    ),
                )
            )
        return findings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_service_with_org_layer(
    repo_root: Path,
    registry: Any,
    pack_context: PackContext | None = None,
) -> Any:
    """Construct a ``DoctrineService`` rooted at built-in + project + configured org packs.

    When *pack_context* is supplied, the returned service is wrapped in
    :class:`charter.resolver.DoctrineService` for activation filtering
    (Pattern B + C).
    """
    try:
        from charter._doctrine_paths import resolve_project_root
        from charter.catalog import resolve_doctrine_root
        from doctrine.service import DoctrineService
    except ImportError:
        return None

    doctrine_root = resolve_doctrine_root()
    project_root = resolve_project_root(repo_root)
    org_roots = [p.local_path for p in registry.packs if p.local_path.exists()]
    if not org_roots:
        return None
    inner = DoctrineService(
        built_in_root=doctrine_root,
        project_root=project_root,
        org_roots=org_roots,
    )
    if pack_context is not None:
        try:
            from charter.resolver import DoctrineService as ActivationDoctrineService  # noqa: PLC0415
            return ActivationDoctrineService(inner, pack_context=pack_context)
        except ImportError:
            pass
    return inner


def _build_built_in_only_service(
    repo_root: Path,
    pack_context: PackContext | None = None,
) -> Any:
    """Construct a ``DoctrineService`` rooted at built-in + project only (no org).

    When *pack_context* is supplied, the returned service is wrapped in
    :class:`charter.resolver.DoctrineService` for activation filtering.
    """
    try:
        from charter._doctrine_paths import resolve_project_root
        from charter.catalog import resolve_doctrine_root
        from doctrine.service import DoctrineService
    except ImportError:
        return None

    doctrine_root = resolve_doctrine_root()
    project_root = resolve_project_root(repo_root)
    inner = DoctrineService(built_in_root=doctrine_root, project_root=project_root)
    if pack_context is not None:
        try:
            from charter.resolver import DoctrineService as ActivationDoctrineService  # noqa: PLC0415
            return ActivationDoctrineService(inner, pack_context=pack_context)
        except ImportError:
            pass
    return inner


def _load_project_charter_fields(repo_root: Path) -> dict[str, Any]:
    """Read ``.kittify/charter/interview/answers.yaml`` and return a flat field map.

    Returns an empty dict if the file is absent or unreadable — the calling
    advisory check will then emit no findings.
    """
    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"
    if not answers_path.exists():
        return {}
    try:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        data = yaml.load(answers_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(data, dict):
        return {}
    # Some interview-answer files nest fields under "answers" — surface both shapes.
    nested = data.get("answers")
    flat: dict[str, Any] = {}
    if isinstance(nested, dict):
        flat.update(nested)
    for key, value in data.items():
        if key == "answers":
            continue
        flat.setdefault(key, value)
    return flat
