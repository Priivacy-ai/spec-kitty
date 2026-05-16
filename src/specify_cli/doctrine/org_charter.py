"""Org-layer charter composition policy (WP09).

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
- :func:`load_org_charter_policy` — load policy from a single pack root
- :func:`load_org_charter_policies` — load and merge across all packs
- :func:`apply_org_charter_pre_fill` — pre-fill interview answers on disk
- :func:`apply_org_charter_to_interview` — pre-fill an in-memory
  ``CharterInterview`` before the interactive prompt loop (FR-026)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

__all__ = [
    "GovernancePolicy",
    "OrgCharterPolicy",
    "load_org_charter_policy",
    "load_org_charter_policies",
    "apply_org_charter_pre_fill",
]


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
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1"
    org_name: str | None = None
    interview_defaults: dict[str, str | bool] = Field(default_factory=dict)
    required_directives: list[str] = Field(default_factory=list)
    governance_policies: list[GovernancePolicy] = Field(default_factory=list)


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


def load_org_charter_policies(repo_root: Path) -> OrgCharterPolicy:
    """Load and merge ``org-charter.yaml`` across all configured packs.

    Merge semantics (declaration order, last pack wins on collisions):

    * ``schema_version`` — last non-empty value wins.
    * ``org_name`` — last non-empty value wins.
    * ``interview_defaults`` — dict update; later packs overwrite earlier.
    * ``required_directives`` — union, preserving first-seen order.
    * ``governance_policies`` — concatenated, deduplicated by
      ``(field, value)`` keeping the *last* occurrence.

    Returns an *empty* :class:`OrgCharterPolicy` (all defaults) when no
    packs are configured or none ship an ``org-charter.yaml``.
    """
    # Lazy import avoids a circular module load at package-init time.
    from specify_cli.doctrine.config import load_pack_registry

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        return OrgCharterPolicy()

    merged_interview_defaults: dict[str, str | bool] = {}
    merged_required_directives: list[str] = []
    merged_governance: list[GovernancePolicy] = []
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
        for rd in policy.required_directives:
            if rd not in merged_required_directives:
                merged_required_directives.append(rd)
        merged_governance.extend(policy.governance_policies)

    # Dedupe governance policies by (field, value), keeping the LAST entry.
    seen: dict[tuple[str, str | bool], GovernancePolicy] = {}
    for gp in merged_governance:
        seen[(gp.field, gp.value)] = gp
    deduped_governance = list(seen.values())

    return OrgCharterPolicy(
        schema_version=schema_version or "1",
        org_name=org_name,
        interview_defaults=merged_interview_defaults,
        required_directives=merged_required_directives,
        governance_policies=deduped_governance,
    )


# ---------------------------------------------------------------------------
# Interview pre-fill
# ---------------------------------------------------------------------------


def apply_org_charter_pre_fill(repo_root: Path) -> list[str]:
    """Non-destructively pre-fill interview answers from org charter policies.

    Returns a list of human-readable messages describing what was
    pre-filled.  Returns an empty list when:

    * no org packs are configured;
    * none of the configured packs ship an ``org-charter.yaml``;
    * the merged policy has neither ``interview_defaults`` nor
      ``required_directives`` to apply.

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
        and not merged_policy.required_directives
    ):
        return []

    answers_path = repo_root / ".kittify" / "charter" / "interview" / "answers.yaml"

    # The pure data helper lives in the charter layer.
    from charter.interview import apply_org_charter_pre_fill_to_answers

    return apply_org_charter_pre_fill_to_answers(
        answers_path=answers_path,
        interview_defaults=dict(merged_policy.interview_defaults),
        required_directives=list(merged_policy.required_directives),
    )


def apply_org_charter_to_interview(
    interview_data: Any,
    repo_root: Path,
) -> list[str]:
    """Pre-fill an in-memory ``CharterInterview`` with org charter defaults.

    Mutates ``interview_data.answers`` and ``interview_data.selected_directives``
    in place (the dataclass is frozen for attribute rebinding, but the dict
    and list values are mutable). Behaviour is non-destructive:

    * Sets a key in ``interview_data.answers`` only when it is missing,
      so the interactive prompt then shows the org default as its starting
      value and the operator can confirm or override it (FR-026).
    * Appends entries from ``required_directives`` to
      ``interview_data.selected_directives`` only when not already present.

    Returns a list of human-readable messages describing what was applied.
    Returns ``[]`` when no org packs are configured, none ship an
    ``org-charter.yaml``, or the merged policy contributes nothing.
    """
    from specify_cli.doctrine.config import load_pack_registry

    registry = load_pack_registry(repo_root)
    if not registry.packs:
        return []

    merged_policy = load_org_charter_policies(repo_root)
    if not merged_policy.interview_defaults and not merged_policy.required_directives:
        return []

    messages: list[str] = []

    prefilled = 0
    for key, value in merged_policy.interview_defaults.items():
        if key not in interview_data.answers:
            interview_data.answers[key] = str(value)
            prefilled += 1

    new_required = [
        d
        for d in merged_policy.required_directives
        if d not in interview_data.selected_directives
    ]
    if new_required:
        interview_data.selected_directives.extend(new_required)
        messages.append(
            f"Pre-selected {len(new_required)} directive(s) from org charter "
            "required_directives."
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
