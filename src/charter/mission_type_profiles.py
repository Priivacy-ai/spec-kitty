"""Mission-type-scoped governance profile loader and resolver.

Mission-type profiles are built-in doctrine-side YAML files at
``src/doctrine/missions/<mission_type>/governance-profile.yaml``.  Each
profile declares the default selections and activations for missions of
that type.  The charter resolver reads ``meta.json mission_type``, picks
the matching profile, and unions its declarations with project + org
selections.

The four canonical mission types are:

* ``software-dev``
* ``documentation``
* ``research``
* ``plan``

Profiles for other mission_type values are not part of the built-in profile set; the resolver
hard-fails (``UnknownMissionTypeError``) when ``meta.json mission_type``
matches no built-in profile AND the project charter has not declared its
own ``selected_<kind>`` overrides.  Silent fallback to
``software-dev-default`` is explicitly forbidden by FR-011 / journey 4 of
the ``charter-mediated-doctrine-selection-01KRTZCA`` mission.

See:

* ``kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/mission-type-profile.md``
  for the on-disk and runtime contract.
* ``kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/data-model.md`` §6
  for the Pydantic shape.
* ``tests/missions/test_mission_type_profile_resolution.py`` for the
  14-assertion ATDD acceptance spec.

Layer rule
----------
``src/charter/`` MUST NOT import from ``specify_cli`` (C-001, hard ratchet
pinned by ``tests/architectural/test_layer_rules.py``).  This module
stays self-contained accordingly; imports from ``doctrine`` are allowed
(charter -> doctrine is the canonical dependency direction).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from charter.activations import ActivationEntry

__all__ = [
    "CANONICAL_MISSION_TYPES",
    "GovernancePayload",
    "MissionTypeProfile",
    "UnknownMissionTypeError",
    "existing_mission_types",
    "load_profile",
    "resolve_action_sequence",
    "resolve_mission_type_governance",
]


# ---------------------------------------------------------------------------
# Canonical mission types
# ---------------------------------------------------------------------------

#: The four canonical mission types that MUST each ship a governance
#: profile.  Pinned by
#: ``tests/missions/test_mission_type_profile_resolution.py``.
CANONICAL_MISSION_TYPES: tuple[str, ...] = (
    "software-dev",
    "documentation",
    "research",
    "plan",
)


# ``src/charter/mission_type_profiles.py`` lives 2 dirs deep inside ``src/``,
# so ``parents[2]`` points at the repository ``src/`` directory.  We compose
# the doctrine root from there to keep the resolution layer-rule-clean
# (charter -> doctrine is the canonical direction; no ``specify_cli`` import).
_DOCTRINE_MISSIONS_ROOT: Path = Path(__file__).resolve().parents[1] / "doctrine" / "missions"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class MissionTypeProfile(BaseModel):
    """Mission-type-scoped governance profile.

    Mirrors the shape documented in data-model.md §6 and
    contracts/mission-type-profile.md.  ``extra="forbid"`` so typos in
    the YAML surface immediately rather than silently rendering empty
    selections.
    """

    model_config = ConfigDict(extra="forbid")

    mission_type: str
    template_set: str | None = None
    selected_directives: list[str] = Field(default_factory=list)
    selected_tactics: list[str] = Field(default_factory=list)
    selected_paradigms: list[str] = Field(default_factory=list)
    selected_styleguides: list[str] = Field(default_factory=list)
    selected_toolguides: list[str] = Field(default_factory=list)
    selected_procedures: list[str] = Field(default_factory=list)
    selected_agent_profiles: list[str] = Field(default_factory=list)
    selected_mission_step_contracts: list[str] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    activations: list[ActivationEntry] = Field(default_factory=list)


@dataclass(frozen=True)
class GovernancePayload:
    """Rendered governance payload for a mission-type-resolved context.

    Carries the rendered prompt text plus the resolved ``mission_type``
    so callers (and the ATDD test) can sanity-check that the resolver
    routed to the correct profile.
    """

    text: str
    mission_type: str


class UnknownMissionTypeError(ValueError):
    """Raised when ``meta.json mission_type`` matches no activated mission type.

    The hard-fail behaviour is the FR-011 / journey 4 contract: there
    MUST NOT be a silent ``software-dev-default`` fallback for
    non-software missions.  The message MUST contain the unknown
    ``mission_type`` verbatim so operators can diagnose typos or missing
    profile files.

    FR-009: The message MUST also list the registered (activated) mission
    type IDs so operators know what values are valid.

    Attributes
    ----------
    mission_type_id:
        The unknown mission type ID that was looked up.
    registered_ids:
        Sorted list of activated mission type IDs at the time of the error.
    """

    def __init__(
        self,
        mission_type_id: str,
        registered_ids: list[str] | None = None,
    ) -> None:
        self.mission_type_id = mission_type_id
        self.registered_ids: list[str] = registered_ids if registered_ids is not None else []
        if self.registered_ids:
            ids_str = ", ".join(self.registered_ids)
            message = (
                f"Unknown mission type {mission_type_id!r}. "
                f"Registered types: {ids_str}."
            )
        else:
            message = (
                f"Unknown mission type {mission_type_id!r}. "
                "No registered mission types are available."
            )
        super().__init__(message)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def load_profile(mission_type: str) -> MissionTypeProfile | None:
    """Load the built-in governance profile for ``mission_type``.

    Reads ``src/doctrine/missions/<mission_type>/governance-profile.yaml``
    and validates it against :class:`MissionTypeProfile`.

    Returns
    -------
    MissionTypeProfile | None
        ``None`` when the profile file does not exist (caller decides
        hard-fail policy via :func:`resolve_mission_type_governance`).  A parsed
        :class:`MissionTypeProfile` otherwise.

    Raises
    ------
    pydantic.ValidationError
        When the YAML is structurally malformed.
    ValueError
        When the YAML's top-level ``mission_type`` field does not match
        the parent directory name.  This catches accidental
        misroutings (e.g. a file under ``documentation/`` declaring
        ``mission_type: software-dev``) early at load time.
    """
    profile_path = _DOCTRINE_MISSIONS_ROOT / mission_type / "governance-profile.yaml"
    if not profile_path.exists():
        return None

    data = YAML(typ="safe").load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(
            f"Mission-type profile at {profile_path} must be a YAML mapping; "
            f"got {type(data).__name__}."
        )

    profile = MissionTypeProfile.model_validate(data)

    if profile.mission_type != mission_type:
        raise ValueError(
            f"Mission-type profile at {profile_path} declares "
            f"mission_type={profile.mission_type!r} but lives under directory "
            f"{mission_type!r}. The two MUST agree or the resolver would route "
            f"missions to the wrong profile."
        )

    return profile


# ---------------------------------------------------------------------------
# Charter API functions
# ---------------------------------------------------------------------------


def existing_mission_types(repo_root: Path) -> list[str]:
    """Return sorted, deduplicated IDs of activated mission types for the project.

    Only types that are explicitly activated in the project charter are returned.
    Non-activated types are excluded regardless of their presence in the doctrine
    layer.

    Reads ``.kittify/config.yaml`` via :class:`~charter.pack_context.PackContext`
    to obtain the activation set.  When the config file is absent or the
    ``mission_type_activations`` key is missing, all four built-in types are
    returned (new-project / pre-migration fallback handled by
    :meth:`~charter.pack_context.PackContext.from_config`).

    FR-018: This function is the **single source of truth** for
    "what mission types are activated".  Do not duplicate this logic elsewhere.

    Parameters
    ----------
    repo_root:
        Repository root containing ``.kittify/config.yaml``.

    Returns
    -------
    list[str]
        Sorted, deduplicated activated mission type IDs.
    """
    try:
        from charter.pack_context import PackContext  # noqa: PLC0415 — lazy; avoids circular
    except ImportError:
        # PackContext is provided by WP06 (charter.pack_context).  When that
        # module is not yet available (parallel WP development before merge),
        # fall back to the canonical built-in set so existing callers do not
        # hard-fail.
        return sorted(CANONICAL_MISSION_TYPES)

    pack_context = PackContext.from_config(repo_root)
    return sorted(pack_context.activated_mission_types)


def resolve_action_sequence(
    mission_type_id: str,
    repo_root: Path,
) -> list[str]:
    """Return the live action sequence for the given mission type.

    Reads the :class:`~doctrine.missions.mission_type_repository.MissionTypeRepository`
    through the built-in → org → project DRG chain.  Called fresh at each
    invocation; not cached across calls (FR-007: ≤100ms budget applies).

    Parameters
    ----------
    mission_type_id:
        The mission type ID to resolve (e.g. ``"software-dev"``).
    repo_root:
        Repository root used to determine which mission types are activated.

    Returns
    -------
    list[str]
        Ordered action sequence (e.g. ``["specify", "plan", "tasks",
        "implement", "review"]``).

    Raises
    ------
    UnknownMissionTypeError
        When ``mission_type_id`` is not in
        :func:`existing_mission_types(repo_root) <existing_mission_types>`.
        The exception carries the sorted list of activated IDs in
        ``registered_ids``.
    """
    registered = existing_mission_types(repo_root)
    if mission_type_id not in registered:
        raise UnknownMissionTypeError(mission_type_id, registered_ids=registered)

    from doctrine.missions.mission_type_repository import MissionTypeRepository  # noqa: PLC0415

    repo = MissionTypeRepository.default()
    mission_type = repo.get(mission_type_id)
    if mission_type is None:
        # The type is activated but has no YAML definition in the built-in
        # doctrine bundle.  This is a configuration inconsistency; report it
        # clearly rather than returning an empty sequence.
        raise UnknownMissionTypeError(mission_type_id, registered_ids=registered)

    # Resolve extends: chain (single level — top-level extends only)
    if mission_type.extends is not None:
        parent = repo.get(mission_type.extends)
        if parent is not None and not mission_type.action_sequence:
            return list(parent.action_sequence)

    return list(mission_type.action_sequence)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


def resolve_mission_type_governance(repo_root: Path, feature_dir: Path) -> GovernancePayload:
    """Resolve the governance payload for the mission at ``feature_dir``.

    Reads ``feature_dir / "meta.json"``, looks up its ``mission_type``,
    loads the matching built-in profile, and renders a
    :class:`GovernancePayload` carrying the rendered text plus the
    resolved ``mission_type``.

    Hard-fail policy (FR-011)
    -------------------------
    Raises :class:`UnknownMissionTypeError` when:

    * ``meta.json`` is missing the ``mission_type`` key, OR
    * ``meta.json mission_type`` matches no built-in profile AND the
      project charter declares no ``selected_<kind>`` overrides of its
      own.

    Silent fallback to ``software-dev-default`` is explicitly forbidden.

    Parameters
    ----------
    repo_root:
        Repository root for the project under resolution.  Used to look
        up project-level overrides at
        ``.kittify/charter/governance.yaml``.
    feature_dir:
        The mission's ``kitty-specs/<mission-slug>/`` directory.  Its
        ``meta.json`` is the source of truth for ``mission_type``.

    Returns
    -------
    GovernancePayload
        ``payload.text`` is the rendered governance text.  ``payload.mission_type``
        equals the ``meta.json mission_type`` value.

    Raises
    ------
    UnknownMissionTypeError
        Per the hard-fail policy above.  Message MUST contain the
        unknown ``mission_type`` verbatim (pinned by
        ``test_resolve_governance_hard_fails_for_unknown_mission_type``).
    FileNotFoundError
        When ``meta.json`` itself does not exist (callers MUST stage
        the mission's metadata before resolving governance).
    """
    meta_path = feature_dir / "meta.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"meta.json at {meta_path} is not valid JSON: {exc}"
        ) from exc

    mission_type = meta.get("mission_type")
    if not mission_type:
        raise ValueError(
            f"meta.json at {meta_path} is missing the 'mission_type' key. "
            "Every mission MUST declare its mission_type so the charter "
            "resolver can route it to the matching governance profile."
        )

    registered = existing_mission_types(repo_root)
    profile = load_profile(mission_type)
    project_has_overrides = _project_has_doctrine_overrides(repo_root)

    if mission_type not in registered and not project_has_overrides:
        raise UnknownMissionTypeError(mission_type, registered_ids=registered)

    rendered = _render_profile_payload(profile, mission_type)
    return GovernancePayload(text=rendered, mission_type=mission_type)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


_PROJECT_GOVERNANCE_PATH: tuple[str, ...] = (".kittify", "charter", "governance.yaml")


def _project_has_doctrine_overrides(repo_root: Path) -> bool:
    """Return ``True`` iff the project charter declares any selection.

    A project "has overrides" when its
    ``.kittify/charter/governance.yaml`` carries a ``doctrine:`` block
    with at least one non-empty ``selected_<kind>`` list.  This is
    consulted by :func:`resolve_mission_type_governance` to decide whether an
    unknown ``mission_type`` should hard-fail (no overrides) or merely
    skip the missing profile (overrides present).

    Best-effort: any I/O or parse failure collapses to ``False`` so a
    malformed governance file never silences the hard-fail contract.
    """
    governance_yaml = repo_root.joinpath(*_PROJECT_GOVERNANCE_PATH)
    if not governance_yaml.exists():
        return False
    try:
        data = YAML(typ="safe").load(governance_yaml.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — best-effort governance probe
        return False
    if not isinstance(data, dict):
        return False
    doctrine = data.get("doctrine")
    if not isinstance(doctrine, dict):
        return False
    for key, value in doctrine.items():
        if not key.startswith("selected_"):
            continue
        if isinstance(value, list) and value:
            return True
    return False


def _render_profile_payload(
    profile: MissionTypeProfile | None,
    mission_type: str,
) -> str:
    """Render a textual governance payload for ``profile``.

    The renderer is intentionally compact — it lists the mission_type,
    the resolved ``template_set`` (if any), and the per-kind selections.
    The ATDD contract only requires:

    * The payload MUST NOT contain ``software-dev-default`` when the
      mission_type is not ``software-dev``.
    * The payload object MUST expose ``.mission_type`` matching the
      ``meta.json mission_type``.

    Richer formatting (full doctrine-text expansion, fetch stanzas,
    section bodies) is the responsibility of
    :func:`charter.context.build_charter_context` and the existing
    renderers in ``src/charter/context_renderers/``; this resolver
    surfaces a stable summary that downstream tooling can splice into
    its broader prompt.
    """
    lines: list[str] = []
    lines.append(f"Mission-Type Governance Profile: {mission_type}")
    if profile is None:
        lines.append("  - No built-in profile; project overrides apply.")
        return "\n".join(lines) + "\n"

    if profile.template_set is not None:
        lines.append(f"  template_set: {profile.template_set}")
    else:
        lines.append("  template_set: (none — mission resolves its own)")

    kind_fields: tuple[tuple[str, list[str]], ...] = (
        ("selected_directives", profile.selected_directives),
        ("selected_tactics", profile.selected_tactics),
        ("selected_paradigms", profile.selected_paradigms),
        ("selected_styleguides", profile.selected_styleguides),
        ("selected_toolguides", profile.selected_toolguides),
        ("selected_procedures", profile.selected_procedures),
        ("selected_agent_profiles", profile.selected_agent_profiles),
        ("selected_mission_step_contracts", profile.selected_mission_step_contracts),
    )
    for field_name, ids in kind_fields:
        if ids:
            lines.append(f"  {field_name}: {', '.join(ids)}")
        else:
            lines.append(f"  {field_name}: (none)")

    if profile.available_tools:
        lines.append(f"  available_tools: {', '.join(profile.available_tools)}")
    if profile.activations:
        lines.append(f"  activations: {len(profile.activations)} entries")

    return "\n".join(lines) + "\n"
