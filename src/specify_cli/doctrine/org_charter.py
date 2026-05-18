"""Org-layer charter composition policy (WP09 / Mission B WP06).

This module defines the :class:`OrgCharterPolicy` Pydantic model and the
loader / merger that produce a merged policy across all configured org
doctrine packs.  It also exposes :func:`apply_org_charter_pre_fill`,
which non-destructively pre-fills the project-level charter interview
answers YAML with org-level defaults.

Architectural note
------------------
``specify_cli`` is the highest layer and may freely import from
``charter``.  The :func:`apply_org_charter_pre_fill` orchestration lives
here, where it is permitted to (a) reach into ``specify_cli.doctrine.config``
for the pack registry and (b) call into the pure ``charter`` data helper
that performs the YAML side-effect.

The pure side-effect (writing to ``answers.yaml``) is implemented in
``charter.interview.apply_org_charter_pre_fill_to_answers``.  That charter
helper accepts the merged policy data as plain Python (dict + list) so it
never imports from this layer — the WP07 ``_resolve_org_root`` pattern.

Public API
----------
- :class:`GovernancePolicy` — single governance policy entry
- :class:`OrgCharterPolicy` — top-level schema for ``org-charter.yaml``
- :class:`MissingDoctrinePackError` — raised when a configured pack's
  ``local_path`` is missing on disk (FR-015)
- :func:`load_org_charter_policy` — load policy from a single pack root
- :func:`load_org_charter_policies` — load and merge across all packs
- :func:`apply_org_charter_pre_fill` — pre-fill interview answers on disk
- :func:`apply_org_charter_to_interview` — pre-fill an in-memory
  ``CharterInterview`` before the interactive prompt loop (FR-026)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from charter.activations import ActivationEntry

__all__ = [
    "GovernancePolicy",
    "OrgCharterPolicy",
    "MissingDoctrinePackError",
    "REQUIRED_KIND_FIELDS",
    "load_org_charter_policy",
    "load_org_charter_policies",
    "apply_org_charter_pre_fill",
    "apply_org_charter_to_interview",
]


# ---------------------------------------------------------------------------
# Constants — the canonical list of artifact kinds an org pack can mandate.
#
# Naming parity rule (Mission B WP01 + WP06): every entry here corresponds
# to a ``selected_<kind>`` field on :class:`charter.schemas.DoctrineSelectionConfig`
# and a ``required_<kind>`` field on :class:`OrgCharterPolicy`.  The
# byte-identical parity is pinned by
# ``tests/architectural/test_artifact_selection_completeness.py``.
# ---------------------------------------------------------------------------


#: Artifact-kind suffixes (plural) for which an org pack may declare a
#: ``required_<kind>`` list.  Order matches the mission's selection-schema
#: ordering and is used by the union loop in
#: :func:`apply_org_charter_to_interview` and the merge loop in
#: :func:`load_org_charter_policies`.
REQUIRED_KIND_FIELDS: tuple[str, ...] = (
    "directives",
    "tactics",
    "paradigms",
    "styleguides",
    "toolguides",
    "procedures",
    "agent_profiles",
    "mission_step_contracts",
)


# ---------------------------------------------------------------------------
# Schema models
# ---------------------------------------------------------------------------


class GovernancePolicy(BaseModel):
    """A single governance policy entry.

    Enforcement is *advisory-only* in this mission — only the literal
    string ``"advisory"`` is honoured today.  Other values parse and
    surface as advisories (see ``pack_validator._validate_org_charter``).
    """

    model_config = ConfigDict(extra="forbid")

    field: str
    value: str | bool
    enforcement: str = "advisory"


class OrgCharterPolicy(BaseModel):
    """Top-level model for ``org-charter.yaml``.

    Empty instance (the default constructor) represents *no org policy*
    and is used as the zero-effect fallback when no packs configure
    ``org-charter.yaml``.

    Mission B WP06 extends this model with one ``required_<kind>`` list
    per :data:`REQUIRED_KIND_FIELDS` entry.  Each list mirrors the
    matching ``selected_<kind>`` field on
    :class:`charter.schemas.DoctrineSelectionConfig` (parity pinned by
    ``tests/architectural/test_artifact_selection_completeness.py``).
    Empty defaults preserve NFR-005 backward compatibility — existing
    ``org-charter.yaml`` files that only declare ``required_directives``
    parse unchanged.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    org_name: str | None = None
    interview_defaults: dict[str, str | bool] = Field(default_factory=dict)
    required_directives: list[str] = Field(default_factory=list)
    required_tactics: list[str] = Field(default_factory=list)
    required_paradigms: list[str] = Field(default_factory=list)
    required_styleguides: list[str] = Field(default_factory=list)
    required_toolguides: list[str] = Field(default_factory=list)
    required_procedures: list[str] = Field(default_factory=list)
    required_agent_profiles: list[str] = Field(default_factory=list)
    required_mission_step_contracts: list[str] = Field(default_factory=list)
    governance_policies: list[GovernancePolicy] = Field(default_factory=list)
    activations: list[ActivationEntry] = Field(default_factory=list)
    """Org-pack-level activation registry (FR-008 / WP06 T028).  Each pack
    may ship its own activations list; the cross-pack merge concatenates
    them and deduplicates on the 4-tuple identity
    ``(activation_context, doctrine_pack_id, artifact_id, artifact_kind)``
    keeping the *last* occurrence (declaration-order precedence)."""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class MissingDoctrinePackError(RuntimeError):
    """Raised when a configured doctrine pack's ``local_path`` is missing.

    Per FR-015 (Mission B WP06), the consumer cannot silently degrade
    when an org pack referenced by ``.kittify/config.yaml`` has not been
    fetched (or the path is a typo).  Context resolution MUST fail loudly
    with the pack name and the missing path so the operator can either
    run ``spec-kitty doctrine fetch --pack <name>`` or remove the entry
    from the config.

    The exception message is also rendered into the bootstrap charter
    context text as a hard-error diagnostic (see
    :mod:`charter.context._missing_pack_diagnostic`) so callers that do
    not catch the exception still surface the error in the prompt body.
    """

    def __init__(self, pack_name: str, local_path: Path) -> None:
        self.pack_name = pack_name
        self.local_path = Path(local_path)
        super().__init__(
            f"Doctrine pack `{pack_name}` configured at "
            f"`{self.local_path}` does not exist on disk. Run "
            f"`spec-kitty doctrine fetch --pack {pack_name}` to populate it, "
            f"or remove the pack from .kittify/config.yaml."
        )


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _yaml() -> YAML:
    y = YAML(typ="safe")
    return y


def load_org_charter_policy(pack_path: Path) -> OrgCharterPolicy | None:
    """Load ``org-charter.yaml`` from a single pack root.

    Returns ``None`` when the file is absent or unreadable.  Raises
    :class:`pydantic.ValidationError` (re-raised) when the file exists but
    fails schema validation — callers that want resilience should catch.
    """
    charter_path = pack_path / "org-charter.yaml"
    if not charter_path.exists():
        return None
    try:
        text = charter_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.strip():
        return None
    try:
        data = _yaml().load(text)
    except Exception:  # noqa: BLE001 — YAML parse failures degrade to None
        return None
    if not isinstance(data, dict):
        return None
    return OrgCharterPolicy.model_validate(data)


def _activation_identity_key(entry: ActivationEntry) -> tuple[str, str, str, str]:
    """Return the dedup identity key for an :class:`ActivationEntry`.

    Per data-model.md §5, the identity tuple for activation de-dup is
    ``(activation_context, doctrine_pack_id, artifact_id, artifact_kind)``.
    ``activation_context`` is itself a ``dict[str, str]`` — we serialise
    it with sorted keys so structurally equal contexts produce identical
    hash keys regardless of insertion order.
    """
    return (
        json.dumps(entry.activation_context, sort_keys=True),
        entry.doctrine_pack_id,
        entry.artifact_id,
        entry.artifact_kind or "",
    )


def load_org_charter_policies(repo_root: Path) -> OrgCharterPolicy:
    """Load and merge ``org-charter.yaml`` across all configured packs.

    Merge semantics (declaration order, last pack wins on collisions):

    * ``schema_version`` — last non-empty value wins.
    * ``org_name`` — last non-empty value wins.
    * ``interview_defaults`` — dict update; later packs overwrite earlier.
    * ``required_<kind>`` (all 8 in :data:`REQUIRED_KIND_FIELDS`) — union,
      preserving first-seen order across packs.
    * ``governance_policies`` — concatenated, deduplicated by
      ``(field, value)`` keeping the *last* occurrence.
    * ``activations`` — concatenated, deduplicated on the 4-tuple
      ``(activation_context, doctrine_pack_id, artifact_id, artifact_kind)``
      keeping the *last* occurrence (per data-model.md §5 / FR-008).

    Returns an *empty* :class:`OrgCharterPolicy` (all defaults) when no
    packs are configured or none ship an ``org-charter.yaml``.
    """
    # Lazy import avoids a circular module load at package-init time.
    from specify_cli.doctrine.config import load_pack_registry

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        return OrgCharterPolicy()

    merged_interview_defaults: dict[str, str | bool] = {}
    merged_required: dict[str, list[str]] = {kind: [] for kind in REQUIRED_KIND_FIELDS}
    merged_governance: list[GovernancePolicy] = []
    activation_dedup: dict[tuple[str, str, str, str], ActivationEntry] = {}
    schema_version: str | None = None
    org_name: str | None = None

    for pack in registry.packs:
        try:
            policy = load_org_charter_policy(pack.local_path)
        except Exception:  # noqa: BLE001, S112 — malformed pack policy is skipped
            continue
        if policy is None:
            continue
        if policy.schema_version:
            schema_version = policy.schema_version
        if policy.org_name:
            org_name = policy.org_name
        merged_interview_defaults.update(policy.interview_defaults)
        for kind in REQUIRED_KIND_FIELDS:
            for item in getattr(policy, f"required_{kind}"):
                if item not in merged_required[kind]:
                    merged_required[kind].append(item)
        merged_governance.extend(policy.governance_policies)
        for entry in policy.activations:
            activation_dedup[_activation_identity_key(entry)] = entry

    # Dedupe governance policies by (field, value), keeping the LAST entry.
    seen: dict[tuple[str, str | bool], GovernancePolicy] = {}
    for gp in merged_governance:
        seen[(gp.field, gp.value)] = gp
    deduped_governance = list(seen.values())

    return OrgCharterPolicy(
        schema_version=schema_version or "1",
        org_name=org_name,
        interview_defaults=merged_interview_defaults,
        required_directives=merged_required["directives"],
        required_tactics=merged_required["tactics"],
        required_paradigms=merged_required["paradigms"],
        required_styleguides=merged_required["styleguides"],
        required_toolguides=merged_required["toolguides"],
        required_procedures=merged_required["procedures"],
        required_agent_profiles=merged_required["agent_profiles"],
        required_mission_step_contracts=merged_required["mission_step_contracts"],
        governance_policies=deduped_governance,
        activations=list(activation_dedup.values()),
    )


# ---------------------------------------------------------------------------
# Interview pre-fill
# ---------------------------------------------------------------------------


def _policy_has_any_required(policy: OrgCharterPolicy) -> bool:
    """Return True when *policy* declares at least one ``required_<kind>``."""
    return any(getattr(policy, f"required_{kind}") for kind in REQUIRED_KIND_FIELDS)


def apply_org_charter_pre_fill(repo_root: Path) -> list[str]:
    """Non-destructively pre-fill interview answers from org charter policies.

    Returns a list of human-readable messages describing what was
    pre-filled.  Returns an empty list when:

    * no org packs are configured;
    * none of the configured packs ship an ``org-charter.yaml``;
    * the merged policy has neither ``interview_defaults`` nor any
      ``required_<kind>`` lists to apply.

    The actual side-effect on ``answers.yaml`` is delegated to the
    ``charter`` layer (which cannot import ``specify_cli``) so the
    dependency direction is preserved.
    """
    from specify_cli.doctrine.config import load_pack_registry

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        return []

    merged_policy = load_org_charter_policies(repo_root)
    if (
        not merged_policy.interview_defaults
        and not _policy_has_any_required(merged_policy)
    ):
        return []

    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"

    # The pure data helper lives in the charter layer.
    from charter.interview import apply_org_charter_pre_fill_to_answers

    result: list[str] = apply_org_charter_pre_fill_to_answers(
        answers_path=answers_path,
        interview_defaults=dict(merged_policy.interview_defaults),
        required_directives=list(merged_policy.required_directives),
    )
    return result


def apply_org_charter_to_interview(
    interview_data: Any,
    repo_root: Path,
) -> list[str]:
    """Pre-fill an in-memory ``CharterInterview`` with org charter defaults.

    Mutates ``interview_data.answers`` and ``interview_data.selected_<kind>``
    in place for every kind in :data:`REQUIRED_KIND_FIELDS`.  Behaviour is
    non-destructive:

    * Sets a key in ``interview_data.answers`` only when it is missing,
      so the interactive prompt then shows the org default as its starting
      value and the operator can confirm or override it (FR-026).
    * Appends entries from each ``required_<kind>`` to
      ``interview_data.selected_<kind>`` only when not already present
      (union-preserving-first-seen-order).
    * Initialises ``selected_<kind>`` to an empty list when the interview
      object does not already declare the attribute — keeps pre-fill safe
      for legacy interview objects that predate the Mission B schema.

    Returns a list of human-readable messages describing what was applied.
    Returns ``[]`` when no org packs are configured, none ship an
    ``org-charter.yaml``, or the merged policy contributes nothing.
    """
    from specify_cli.doctrine.config import load_pack_registry

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        return []

    merged_policy = load_org_charter_policies(repo_root)
    if (
        not merged_policy.interview_defaults
        and not _policy_has_any_required(merged_policy)
    ):
        return []

    messages: list[str] = []

    prefilled = 0
    for key, value in merged_policy.interview_defaults.items():
        if key not in interview_data.answers:
            interview_data.answers[key] = str(value)
            prefilled += 1

    for kind in REQUIRED_KIND_FIELDS:
        required_list: list[str] = list(getattr(merged_policy, f"required_{kind}"))
        if not required_list:
            continue
        # Initialise the selection attribute defensively — legacy interview
        # shapes may not declare every Mission-B-added selection field.
        if not hasattr(interview_data, f"selected_{kind}") or getattr(
            interview_data, f"selected_{kind}"
        ) is None:
            try:
                setattr(interview_data, f"selected_{kind}", [])
            except (AttributeError, TypeError):
                # Frozen dataclass that refuses re-binding; skip this kind.
                continue
        selected_list = getattr(interview_data, f"selected_{kind}")
        new_required = [d for d in required_list if d not in selected_list]
        if new_required:
            selected_list.extend(new_required)
            label = "directive(s)" if kind == "directives" else f"{kind}"
            messages.append(
                f"Pre-selected {len(new_required)} {label} from org charter "
                f"required_{kind}."
            )

    if prefilled:
        messages.append(
            f"Pre-filled {prefilled} interview default(s) from org charter."
        )

    return messages


# ---------------------------------------------------------------------------
# JSON block helper (consumed by org_charter_loader)
# ---------------------------------------------------------------------------


def org_charter_to_json_block(policy: OrgCharterPolicy) -> dict[str, Any]:
    """Return the ``{"present": ..., "packs": [...]}`` block for one policy.

    This mirrors the shape produced by
    :func:`specify_cli.doctrine.org_charter_loader.load_org_charter_json_block`
    for a single pack.  Callers that need cross-pack aggregation should
    use the loader directly.
    """
    governance_dump: list[dict[str, Any]] = []
    for gp in policy.governance_policies:
        entry = gp.model_dump()
        entry["source"] = "org"
        governance_dump.append(entry)
    return {
        "pack_name": policy.org_name or "",
        "governance_policies": governance_dump,
        "required_directives": list(policy.required_directives),
    }
