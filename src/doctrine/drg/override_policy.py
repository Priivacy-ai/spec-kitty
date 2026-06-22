"""Per-repo governance policy for built-in DRG node overrides.

The three-layer merge (:mod:`doctrine.drg.merge`) PERMITS a same-kind org node
to override a built-in node in place (recorded as an ``org_override`` conflict).
The merge does not *govern* whether a particular repo sanctions that override —
that is a per-repo policy decision expressed in
``.kittify/doctrine/replaceable-builtins.yaml`` and enforced by an architectural
test (``tests/architectural/test_builtin_override_policy.py``).

Schema (``replaceable-builtins.yaml``)::

    replaceable_builtins:
      - urn: directive:some-built-in
        reason: We replace this directive because ...

FAIL-CLOSED default: an absent file, an empty file, or a URN not listed means
the override is NOT permitted. This module owns parsing + the pure governance
predicates; the architectural test wires them to a live merge.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "ReplaceableBuiltin",
    "ReplaceableBuiltinsPolicy",
    "POLICY_RELPATH",
    "load_replaceable_builtins",
]

#: Repo-root-relative path of the allowlist file.
POLICY_RELPATH = Path(".kittify/doctrine/replaceable-builtins.yaml")

#: Top-level YAML key holding the list of allowlist entries.
_TOP_LEVEL_KEY = "replaceable_builtins"


@dataclass(frozen=True)
class ReplaceableBuiltin:
    """One allowlisted built-in URN permitted to be overridden by an org node.

    ``reason`` is the operator's governance justification. It MAY be empty for
    non-directive kinds, but a built-in *directive* override additionally
    requires a non-empty reason (enforced by the architectural test).
    """

    urn: str
    reason: str


@dataclass(frozen=True)
class ReplaceableBuiltinsPolicy:
    """The parsed allowlist plus pure governance predicates.

    FAIL-CLOSED: an absent file yields an empty policy in which every override
    is forbidden.
    """

    entries: tuple[ReplaceableBuiltin, ...]

    def is_allowed(self, urn: str) -> bool:
        """True iff *urn* is on the allowlist (fail-closed for unlisted URNs)."""
        return any(entry.urn == urn for entry in self.entries)

    def reason_for(self, urn: str) -> str | None:
        """Return the declared reason for *urn*, or ``None`` when not listed."""
        for entry in self.entries:
            if entry.urn == urn:
                return entry.reason
        return None


class OverridePolicyError(ValueError):
    """Raised when ``replaceable-builtins.yaml`` is present but malformed.

    A missing file is NOT an error (fail-closed empty policy); a present file
    whose shape violates the schema is, so a typo does not silently widen the
    allowlist.
    """


def _parse_entry(raw: Any, index: int) -> ReplaceableBuiltin:
    if not isinstance(raw, dict):
        raise OverridePolicyError(
            f"{POLICY_RELPATH}: entry #{index} must be a mapping with a "
            f"'urn' key, got {type(raw).__name__}"
        )
    urn = raw.get("urn")
    if not isinstance(urn, str) or not urn:
        raise OverridePolicyError(
            f"{POLICY_RELPATH}: entry #{index} is missing a non-empty 'urn'"
        )
    reason = raw.get("reason", "")
    if reason is None:
        reason = ""
    if not isinstance(reason, str):
        raise OverridePolicyError(
            f"{POLICY_RELPATH}: entry #{index} ('{urn}') has a non-string 'reason'"
        )
    return ReplaceableBuiltin(urn=urn, reason=reason)


def load_replaceable_builtins(repo_root: Path) -> ReplaceableBuiltinsPolicy:
    """Load the per-repo built-in-override allowlist (fail-closed).

    Reads ``<repo_root>/.kittify/doctrine/replaceable-builtins.yaml``. When the
    file is absent or empty, returns an empty policy that forbids every override.
    A present-but-malformed file raises :class:`OverridePolicyError` so a typo
    cannot silently disable governance.
    """
    policy_path = repo_root / POLICY_RELPATH
    if not policy_path.is_file():
        return ReplaceableBuiltinsPolicy(entries=())

    try:
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise OverridePolicyError(
            f"{POLICY_RELPATH}: YAML parse error: {exc}"
        ) from exc

    if data is None:
        return ReplaceableBuiltinsPolicy(entries=())
    if not isinstance(data, dict):
        raise OverridePolicyError(
            f"{POLICY_RELPATH}: top-level document must be a mapping with a "
            f"'{_TOP_LEVEL_KEY}' list"
        )

    raw_entries = data.get(_TOP_LEVEL_KEY, [])
    if raw_entries is None:
        raw_entries = []
    if not isinstance(raw_entries, list):
        raise OverridePolicyError(
            f"{POLICY_RELPATH}: '{_TOP_LEVEL_KEY}' must be a list"
        )

    entries = tuple(
        _parse_entry(raw, index) for index, raw in enumerate(raw_entries)
    )
    return ReplaceableBuiltinsPolicy(entries=entries)
