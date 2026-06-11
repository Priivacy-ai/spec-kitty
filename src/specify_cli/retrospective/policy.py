"""RetrospectivePolicy resolver with source attribution and malformed-input handling.

Public API:
    RetrospectivePermissions — granular boolean permission flags
    RetrospectivePolicy      — top-level policy dataclass (schema_version=1 contract)
    PolicyResolutionError    — structured error for malformed config / charter input
    default_policy()         — factory returning built-in defaults
    resolve_policy()         — reads charter + config + env observation, returns (policy, source_map)

Source-of-truth spec: kitty-specs/retrospective-default-policy-01KS049J/data-model.md
Contract:             kitty-specs/retrospective-default-policy-01KS049J/contracts/retrospective-policy.schema.json
FR refs: FR-001, FR-002, FR-003, FR-004, FR-015, FR-024
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ruamel.yaml import YAML as _YAML
from ruamel.yaml.error import YAMLError as _YAMLError

from specify_cli.retrospective.deprecation import (
    _DOCS_URL,
    REPLACEMENT_KEYS,
    warn_env_var_deprecated,
)

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Charter path constant (shared with mode.py — do not introduce a second value)
# ---------------------------------------------------------------------------

_CHARTER_REL: Path = Path(".kittify") / "charter" / "charter.md"
_CONFIG_REL: Path = Path(".kittify") / "config.yaml"

# ---------------------------------------------------------------------------
# Valid enum values
# ---------------------------------------------------------------------------

_VALID_TIMING: frozenset[str] = frozenset({"post_completion", "before_completion"})
_VALID_FAILURE_POLICY: frozenset[str] = frozenset({"warn", "block"})
_VALID_APPLY_PROPOSALS: frozenset[str] = frozenset({"require_human", "low_risk_auto"})
_VALID_PRECEDENCE: frozenset[str] = frozenset({"charter", "config"})
_VALID_GENERATOR: frozenset[str] = frozenset({"python"})

# Top-level policy fields that accept enum values (for validation)
_ENUM_FIELDS: dict[str, frozenset[str]] = {
    "timing": _VALID_TIMING,
    "failure_policy": _VALID_FAILURE_POLICY,
    "apply_proposals": _VALID_APPLY_PROPOSALS,
    "precedence": _VALID_PRECEDENCE,
    "generator": _VALID_GENERATOR,
}

# All known top-level keys in a retrospective block
_KNOWN_KEYS: frozenset[str] = frozenset(
    {
        "enabled",
        "timing",
        "failure_policy",
        "write_record",
        "generate_proposals",
        "apply_proposals",
        "permissions",
        "precedence",
        "generator",
        "strict_keys",
    }
)

# All known permission sub-keys
_KNOWN_PERMISSION_KEYS: frozenset[str] = frozenset(
    {
        "write_record",
        "inspect_mission_artifacts",
        "propose_glossary_changes",
        "propose_drg_changes",
        "propose_doctrine_changes",
        "apply_low_risk_changes",
        "apply_structural_changes",
    }
)


# ---------------------------------------------------------------------------
# PolicyResolutionError (T004)
# ---------------------------------------------------------------------------


class PolicyResolutionError(Exception):
    """Structured error for malformed policy input.

    Attributes:
        source:  Where the malformed data was found (e.g. ".kittify/config.yaml").
        reason:  Machine-readable failure code (see data-model.md § FR-024).
        detail:  Human-readable elaboration — parser message, bad key list, etc.
    """

    def __init__(self, source: str, reason: str, detail: str) -> None:
        self.source = source
        self.reason = reason
        self.detail = detail
        super().__init__(f"[{reason}] in {source}: {detail}")


# ---------------------------------------------------------------------------
# Permission + policy dataclasses (T001)
# ---------------------------------------------------------------------------


@dataclass
class RetrospectivePermissions:
    """Granular per-capability permission flags for the retrospective generator.

    All flags default to safe, conservative values.  ``apply_structural_changes``
    MUST remain ``False`` in the built-in default (C-005 invariant).  Operators
    may explicitly opt in via ``.kittify/config.yaml``; the default factory never
    sets it ``True``.
    """

    write_record: bool = True
    inspect_mission_artifacts: bool = True
    propose_glossary_changes: bool = True
    propose_drg_changes: bool = True
    propose_doctrine_changes: bool = True
    apply_low_risk_changes: bool = False
    apply_structural_changes: bool = False


@dataclass
class RetrospectivePolicy:
    """Resolved, runtime-effective retrospective policy.

    Constructed by :func:`resolve_policy` or :func:`default_policy`.  Consumers
    should treat the ``precedence`` field as metadata about *how* the policy was
    resolved, not as a runtime directive (precedence logic lives in the resolver).

    Fields match ``contracts/retrospective-policy.schema.json`` field-for-field.
    """

    enabled: bool = True
    timing: Literal["post_completion", "before_completion"] = "post_completion"
    failure_policy: Literal["warn", "block"] = "warn"
    write_record: bool = True
    generate_proposals: bool = True
    apply_proposals: Literal["require_human", "low_risk_auto"] = "require_human"
    permissions: RetrospectivePermissions = field(
        default_factory=RetrospectivePermissions
    )
    precedence: Literal["charter", "config"] | None = None
    generator: Literal["python"] = "python"


# ---------------------------------------------------------------------------
# default_policy factory (T001)
# ---------------------------------------------------------------------------


def default_policy() -> RetrospectivePolicy:
    """Return a fresh :class:`RetrospectivePolicy` pre-loaded with built-in defaults.

    The built-in defaults are defined by FR-002:
    - ``enabled=True`` (opt-out must be explicit)
    - ``timing="post_completion"``
    - ``failure_policy="warn"`` (never blocks by default)
    - ``write_record=True``
    - ``generate_proposals=True``
    - ``apply_proposals="require_human"``
    - ``permissions.apply_structural_changes=False`` (C-005 invariant)
    """
    return RetrospectivePolicy(
        enabled=True,
        timing="post_completion",
        failure_policy="warn",
        write_record=True,
        generate_proposals=True,
        apply_proposals="require_human",
        permissions=RetrospectivePermissions(
            write_record=True,
            inspect_mission_artifacts=True,
            propose_glossary_changes=True,
            propose_drg_changes=True,
            propose_doctrine_changes=True,
            apply_low_risk_changes=False,
            apply_structural_changes=False,
        ),
    )


def _default_source_map() -> dict[str, str]:
    """Return a source_map with every leaf key pointing to ``"<default>"``."""
    return {
        "enabled": "<default>",
        "timing": "<default>",
        "failure_policy": "<default>",
        "write_record": "<default>",
        "generate_proposals": "<default>",
        "apply_proposals": "<default>",
        "permissions.write_record": "<default>",
        "permissions.inspect_mission_artifacts": "<default>",
        "permissions.propose_glossary_changes": "<default>",
        "permissions.propose_drg_changes": "<default>",
        "permissions.propose_doctrine_changes": "<default>",
        "permissions.apply_low_risk_changes": "<default>",
        "permissions.apply_structural_changes": "<default>",
        "precedence": "<default>",
        "generator": "<default>",
    }


# ---------------------------------------------------------------------------
# Internal block loaders (T004 helpers)
# ---------------------------------------------------------------------------


def _load_charter_retrospective_block(
    repo_root: Path,
) -> tuple[dict[str, object] | None, str | None, PolicyResolutionError | None]:
    """Parse the charter YAML frontmatter and extract the ``retrospective:`` block.

    Returns:
        ``(block, charter_path_str, error)``
        - ``block`` is the raw dict if found, or ``None`` if absent.
        - ``charter_path_str`` is the relative path string used as source key.
        - ``error`` is set when the charter is present but malformed.
    """
    charter_path = repo_root / _CHARTER_REL
    source_str = str(_CHARTER_REL)

    if not charter_path.exists():
        return None, source_str, None

    raw = charter_path.read_text(encoding="utf-8")

    if not raw.startswith("---"):
        # No frontmatter; not malformed — treat as no retrospective block.
        return None, source_str, None

    lines = raw.splitlines()
    close_idx: int | None = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            close_idx = i
            break

    if close_idx is None:
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_yaml",
            detail=f"Charter at {charter_path} has an unclosed YAML frontmatter block.",
        )
        return None, source_str, err

    frontmatter_text = "\n".join(lines[1:close_idx])

    try:
        yaml = _YAML(typ="safe")
        data = yaml.load(frontmatter_text)
    except (_YAMLError, Exception) as exc:  # noqa: BLE001
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_yaml",
            detail=str(exc),
        )
        return None, source_str, err

    if data is None:
        return None, source_str, None

    if not isinstance(data, dict):
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_type_for_retrospective_block",
            detail=f"Charter frontmatter is not a YAML mapping; got {type(data).__name__}.",
        )
        return None, source_str, err

    retro_block = data.get("retrospective")
    if retro_block is None:
        return None, source_str, None

    if not isinstance(retro_block, dict):
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_type_for_retrospective_block",
            detail=(
                f"Charter frontmatter 'retrospective:' value must be a mapping; "
                f"got {type(retro_block).__name__}."
            ),
        )
        return None, source_str, err

    return retro_block, source_str, None


def _load_config_retrospective_block(
    repo_root: Path,
) -> tuple[dict[str, object] | None, PolicyResolutionError | None]:
    """Parse ``.kittify/config.yaml`` and extract the ``retrospective:`` block.

    Returns:
        ``(block, error)``
        - ``block`` is the raw dict if found, or ``None`` if absent.
        - ``error`` is set when the config exists but is malformed.
    """
    config_path = repo_root / _CONFIG_REL
    source_str = str(_CONFIG_REL)

    if not config_path.exists():
        return None, None

    raw = config_path.read_text(encoding="utf-8")

    try:
        yaml = _YAML(typ="safe")
        data = yaml.load(raw)
    except (_YAMLError, Exception) as exc:  # noqa: BLE001
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_yaml",
            detail=str(exc),
        )
        return None, err

    if data is None:
        return None, None

    if not isinstance(data, dict):
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_type_for_retrospective_block",
            detail=f"Config root is not a YAML mapping; got {type(data).__name__}.",
        )
        return None, err

    retro_block = data.get("retrospective")
    if retro_block is None:
        return None, None

    if not isinstance(retro_block, dict):
        err = PolicyResolutionError(
            source=source_str,
            reason="invalid_type_for_retrospective_block",
            detail=(
                f".kittify/config.yaml 'retrospective:' value must be a mapping; "
                f"got {type(retro_block).__name__}."
            ),
        )
        return None, err

    return retro_block, None


# ---------------------------------------------------------------------------
# Block application helpers
# ---------------------------------------------------------------------------


def _validate_enum(
    key: str, value: object, source: str
) -> PolicyResolutionError | None:
    """Return a PolicyResolutionError if ``value`` is not valid for ``key``."""
    valid_set = _ENUM_FIELDS.get(key)
    if valid_set is None:
        return None  # not an enum field
    if not isinstance(value, str) or value not in valid_set:
        return PolicyResolutionError(
            source=source,
            reason="invalid_enum",
            detail=f"{key}: got {value!r}, expected one of {sorted(valid_set)}",
        )
    return None


def _apply_block_to_policy(
    policy: RetrospectivePolicy,
    source_map: dict[str, str],
    block: dict[str, object],
    source_label_prefix: str,
    strict_keys: bool,
    keys_to_apply: frozenset[str] | None,
) -> PolicyResolutionError | None:
    """Apply the fields from ``block`` onto ``policy`` in-place.

    Args:
        policy: The policy object to mutate.
        source_map: The source attribution dict to update.
        block: The raw ``retrospective:`` dict from charter or config.
        source_label_prefix: Prefix for source attribution strings, e.g.
            ``".kittify/charter/charter.md:retrospective"`` or
            ``".kittify/config.yaml#retrospective"``.
        strict_keys: If True, unknown keys raise ``PolicyResolutionError``.
        keys_to_apply: If set, only apply keys present in this set (used for
            precedence-delegation logic).  ``None`` means apply all valid keys.

    Returns:
        The first ``PolicyResolutionError`` encountered, or ``None``.
    """
    unknown_keys = []
    for raw_key, raw_value in block.items():
        key = str(raw_key)

        # Skip meta-keys that don't map directly to policy fields
        if key == "strict_keys":
            continue

        if key not in _KNOWN_KEYS:
            unknown_keys.append(key)
            if strict_keys:
                continue  # collect all unknown, then raise at end
            else:
                _log.warning(
                    "Unknown key %r in retrospective block from %s — ignored.",
                    key,
                    source_label_prefix,
                )
                continue

        if keys_to_apply is not None and key not in keys_to_apply:
            continue  # this key should not be applied from this source

        if key == "permissions":
            if not isinstance(raw_value, dict):
                return PolicyResolutionError(
                    source=source_label_prefix,
                    reason="invalid_type_for_retrospective_block",
                    detail=(
                        f"'permissions' must be a mapping; got {type(raw_value).__name__}."
                    ),
                )
            perm_error = _apply_permissions_block(
                policy.permissions,
                source_map,
                raw_value,
                source_label_prefix,
                strict_keys,
                keys_to_apply=None,
            )
            if perm_error is not None:
                return perm_error
            continue

        # Validate enum fields
        enum_error = _validate_enum(key, raw_value, source_label_prefix)
        if enum_error is not None:
            return enum_error

        # Apply the field
        _set_policy_field(policy, source_map, key, raw_value, source_label_prefix)

    if strict_keys and unknown_keys:
        return PolicyResolutionError(
            source=source_label_prefix,
            reason="unknown_key",
            detail=f"Unknown keys in retrospective block: {sorted(unknown_keys)}",
        )

    return None


def _apply_permissions_block(
    perms: RetrospectivePermissions,
    source_map: dict[str, str],
    block: dict[str, object],
    source_label_prefix: str,
    strict_keys: bool,
    keys_to_apply: frozenset[str] | None,
) -> PolicyResolutionError | None:
    """Apply permission sub-fields from ``block`` onto ``perms`` in-place."""
    unknown_keys = []
    for raw_key, raw_value in block.items():
        perm_key = str(raw_key)
        if perm_key not in _KNOWN_PERMISSION_KEYS:
            unknown_keys.append(perm_key)
            if strict_keys:
                continue
            else:
                _log.warning(
                    "Unknown permission key %r in retrospective block from %s — ignored.",
                    perm_key,
                    source_label_prefix,
                )
                continue

        leaf_key = f"permissions.{perm_key}"
        if keys_to_apply is not None and leaf_key not in keys_to_apply:
            continue

        if not isinstance(raw_value, bool):
            return PolicyResolutionError(
                source=source_label_prefix,
                reason="invalid_enum",
                detail=(
                    f"permissions.{perm_key}: expected boolean, got {type(raw_value).__name__}."
                ),
            )
        setattr(perms, perm_key, raw_value)
        source_map[leaf_key] = f"{source_label_prefix}.permissions.{perm_key}"

    if strict_keys and unknown_keys:
        return PolicyResolutionError(
            source=source_label_prefix,
            reason="unknown_key",
            detail=f"Unknown permission keys in retrospective block: {sorted(unknown_keys)}",
        )
    return None


def _set_policy_field(
    policy: RetrospectivePolicy,
    source_map: dict[str, str],
    key: str,
    value: object,
    source_label_prefix: str,
) -> None:
    """Set a top-level (non-permissions) policy field and update source_map."""
    setattr(policy, key, value)
    source_map[key] = f"{source_label_prefix}.{key}"


# ---------------------------------------------------------------------------
# Precedence strategy helpers (extracted to keep resolve_policy under C901 limit)
# ---------------------------------------------------------------------------


def _apply_blocks_config_precedence(
    policy: RetrospectivePolicy,
    source_map: dict[str, str],
    charter_block: dict[str, object] | None,
    config_block: dict[str, object] | None,
    charter_prefix: str,
    config_prefix: str,
    strict_keys: bool,
) -> None:
    """Apply charter + config under ``precedence: config`` delegation (T003).

    Config is applied first (fills in defaults), then charter overrides what it
    explicitly set.  Result: charter wins for its own explicit fields; config wins
    for fields charter did not set.
    """
    if config_block is not None:
        err = _apply_block_to_policy(
            policy, source_map, config_block, config_prefix,
            strict_keys=strict_keys, keys_to_apply=None,
        )
        if err is not None:
            raise err

    if charter_block is not None:
        err = _apply_block_to_policy(
            policy, source_map, charter_block, charter_prefix,
            strict_keys=strict_keys, keys_to_apply=None,
        )
        if err is not None:
            raise err


def _apply_blocks_charter_precedence(
    policy: RetrospectivePolicy,
    source_map: dict[str, str],
    charter_block: dict[str, object] | None,
    config_block: dict[str, object] | None,
    charter_prefix: str,
    config_prefix: str,
    strict_keys: bool,
) -> None:
    """Apply charter + config under default (charter-wins) precedence (T002).

    Charter is applied first; config only fills fields charter did NOT set.
    """
    charter_set_keys: frozenset[str] = frozenset()

    if charter_block is not None:
        err = _apply_block_to_policy(
            policy, source_map, charter_block, charter_prefix,
            strict_keys=strict_keys, keys_to_apply=None,
        )
        if err is not None:
            raise err
        charter_set_keys = _top_level_keys_in_block(charter_block)

    if config_block is not None:
        config_eligible = _KNOWN_KEYS - charter_set_keys - {"strict_keys"}
        config_leaf_eligible = _expand_eligible_to_leaf_keys(config_eligible)
        err = _apply_block_to_policy(
            policy, source_map, config_block, config_prefix,
            strict_keys=strict_keys, keys_to_apply=config_leaf_eligible,
        )
        if err is not None:
            raise err


# ---------------------------------------------------------------------------
# resolve_policy — main public function (T002, T003, T004, T005)
# ---------------------------------------------------------------------------


def resolve_policy(
    repo_root: Path,
    *,
    env: Mapping[str, str] | None = None,
) -> tuple[RetrospectivePolicy, dict[str, str]]:
    """Resolve the effective :class:`RetrospectivePolicy` for the given project.

    Resolution order (first authoritative source wins per field):

    1. Charter frontmatter ``retrospective:`` block.
    2. ``.kittify/config.yaml`` ``retrospective:`` block — but ONLY if:
       - The charter is absent or did not set that field, OR
       - The charter explicitly set ``retrospective.precedence: config`` (then
         config wins for fields present in config that charter did NOT set;
         charter's own explicit values are never overridden by config).
    3. Built-in defaults.

    Env-var observation (T005 / FR-015):
       ``SPEC_KITTY_RETROSPECTIVE`` and ``SPEC_KITTY_MODE`` are *observed* but
       NEVER override durable charter or config.  When observed (and their
       corresponding field came only from ``<default>``), the source_map records
       the env var name so operators can see the env was present.  The actual
       deprecation warning emission is WP06's responsibility.

    Args:
        repo_root: Absolute path to the project root.
        env: Optional environment mapping override (for testing).

    Returns:
        ``(policy, source_map)`` where ``source_map`` is a flat ``dict[str, str]``
        mapping every leaf policy field to its authoritative source string.

    Raises:
        PolicyResolutionError: If charter or config is malformed.  The return
            value is still ``(default_policy(), source_map_with_sentinel)``
            for callers that want to continue on the happy path; the caller is
            responsible for catching this and routing per failure policy.
    """
    effective_env: Mapping[str, str] = env if env is not None else os.environ

    policy = default_policy()
    source_map = _default_source_map()

    # ------------------------------------------------------------------
    # Step 1: Load charter block
    # ------------------------------------------------------------------
    charter_block, charter_source_str, charter_error = _load_charter_retrospective_block(
        repo_root
    )

    if charter_error is not None:
        _mark_source_map_error(source_map, charter_source_str or str(_CHARTER_REL))
        raise charter_error

    # ------------------------------------------------------------------
    # Step 2: Load config block
    # ------------------------------------------------------------------
    config_block, config_error = _load_config_retrospective_block(repo_root)

    if config_error is not None:
        _mark_source_map_error(source_map, str(_CONFIG_REL))
        raise config_error

    # ------------------------------------------------------------------
    # Step 3: Determine precedence and apply blocks
    # ------------------------------------------------------------------
    precedence: str | None = None
    if charter_block is not None:
        precedence_raw = charter_block.get("precedence")
        if isinstance(precedence_raw, str) and precedence_raw in _VALID_PRECEDENCE:
            precedence = precedence_raw

    strict_keys = _resolve_strict_keys(charter_block, config_block)
    charter_prefix = f"{charter_source_str}:retrospective"
    config_prefix = ".kittify/config.yaml#retrospective"

    if precedence == "config":
        _apply_blocks_config_precedence(
            policy, source_map, charter_block, config_block,
            charter_prefix, config_prefix, strict_keys,
        )
    else:
        _apply_blocks_charter_precedence(
            policy, source_map, charter_block, config_block,
            charter_prefix, config_prefix, strict_keys,
        )

    # ------------------------------------------------------------------
    # Step 4: Env-var observation (T005 / FR-015) — never override
    # Env vars are observed (source_map records their presence) but do NOT
    # override durable charter or config values.  A deprecation warning is
    # emitted once per process for each set env var (NFR-006 / FR-015).
    # ------------------------------------------------------------------
    retro_env = effective_env.get("SPEC_KITTY_RETROSPECTIVE", "").strip()
    if retro_env:
        if source_map.get("enabled") == "<default>":
            source_map["enabled"] = "<env:SPEC_KITTY_RETROSPECTIVE>"
        warn_env_var_deprecated(
            "SPEC_KITTY_RETROSPECTIVE",
            REPLACEMENT_KEYS["SPEC_KITTY_RETROSPECTIVE"],
            _DOCS_URL,
        )

    mode_env = effective_env.get("SPEC_KITTY_MODE", "").strip()
    if mode_env:
        if source_map.get("timing") == "<default>":
            source_map["timing"] = "<env:SPEC_KITTY_MODE>"
        if source_map.get("failure_policy") == "<default>":
            source_map["failure_policy"] = "<env:SPEC_KITTY_MODE>"
        warn_env_var_deprecated(
            "SPEC_KITTY_MODE",
            REPLACEMENT_KEYS["SPEC_KITTY_MODE"],
            _DOCS_URL,
        )

    return policy, source_map


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------


def _mark_source_map_error(source_map: dict[str, str], source: str) -> None:  # noqa: ARG001
    """Replace all ``<default>`` entries with ``<resolution_error>``."""
    for key in source_map:
        if source_map[key] == "<default>":
            source_map[key] = "<resolution_error>"


def _resolve_strict_keys(
    charter_block: dict[str, object] | None,
    config_block: dict[str, object] | None,
) -> bool:
    """Return True if strict_keys mode is active (from either block)."""
    for block in (charter_block, config_block):
        if block is not None:
            val = block.get("strict_keys")
            if val is True:
                return True
    return False


def _top_level_keys_in_block(block: dict[str, object]) -> frozenset[str]:
    """Return the top-level policy keys explicitly set in ``block``."""
    return frozenset(str(k) for k in block if str(k) != "strict_keys")


def _expand_eligible_to_leaf_keys(top_level_eligible: frozenset[str]) -> frozenset[str]:
    """Expand 'permissions' in the eligible set to its leaf keys.

    For the ``_apply_block_to_policy`` ``keys_to_apply`` parameter, we need both
    the top-level key (``"permissions"``) AND the leaf permission keys
    (``"permissions.write_record"``, etc.) to be included so that the function
    can pass permission sub-blocks through correctly.
    """
    expanded: set[str] = set(top_level_eligible)
    if "permissions" in expanded:
        for perm_key in _KNOWN_PERMISSION_KEYS:
            expanded.add(f"permissions.{perm_key}")
    return frozenset(expanded)
