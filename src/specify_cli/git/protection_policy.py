"""Boundary-resolved protected-branch configuration carrier (FR-004/006/007/008).

This module is the **sole sanctioned source** of the resolved protection set.
Every caller that needs to decide "is this ref protected?" must go through
:class:`ProtectionPolicy` — specifically its :meth:`ProtectionPolicy.resolve`
class method — rather than reading ``.kittify/config.yaml`` or calling git
directly for this purpose.

Design basis
------------
ADR ``docs/adr/3.x/2026-06-21-1-protected-branch-config-boundary-resolved-value.md``
and design squad research ``protected-branch-carrier-decision.md`` establish the
standalone-value-object shape.  The existing ``core.commit_guard.evaluate`` /
``ProtectionState`` seam is *reused unchanged*; this module only resolves the
**input** that is fed into it.

Resolution rules (from ``contracts/protection-config.md``)
----------------------------------------------------------
+--------------------------------------------------+----------------------------------------------+
| ``.kittify/config.yaml`` state                   | ``protected_branches`` resolved as           |
+==================================================+==============================================+
| No ``protection:`` block (key absent)            | ``{main, master}`` ∪ {remote default branch} |
+--------------------------------------------------+----------------------------------------------+
| ``protection.protected_branches: [a, b]``        | ``{a, b}`` exactly — no name-default union   |
+--------------------------------------------------+----------------------------------------------+
| ``protection.protected_branches: []``            | ``frozenset()`` — nothing protected          |
+--------------------------------------------------+----------------------------------------------+
| Malformed value (non-list under the key)         | Raises :class:`ProtectionConfigError`        |
+--------------------------------------------------+----------------------------------------------+

The operator hatch ``SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`` (FR-006) is
resolved onto ``operator_hatch_active``; when active, :meth:`is_protected`
returns ``False`` for every ref.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HATCH_ENV_VAR = "SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS"
_DEFAULT_PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master"})


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class ProtectionConfigError(RuntimeError):
    """Raised when ``.kittify/config.yaml`` has a malformed ``protection:`` block.

    Fail-closed: a malformed value is never silently replaced by a default.
    """


# ---------------------------------------------------------------------------
# Value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProtectionPolicy:
    """Frozen, boundary-resolved carrier for the protection decision inputs.

    Constructed exclusively via :meth:`resolve` — the ONLY sanctioned producer.
    After construction, no further git/filesystem/env reads are needed for
    protection decisions (NFR-003).

    Attributes:
        protected_branches: Resolved set of branch names that must not receive
            direct spec-kitty status commits.  The contents depend on the
            ``.kittify`` config state; see module docstring for the resolution
            table.
        operator_hatch_active: ``True`` when the operator escape hatch
            ``SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS`` is set to a truthy
            value (``"1"``, ``"true"``, or ``"yes"``).  When active,
            :meth:`is_protected` always returns ``False``.
    """

    protected_branches: frozenset[str]
    operator_hatch_active: bool

    # ------------------------------------------------------------------
    # Constructor / resolver
    # ------------------------------------------------------------------

    @classmethod
    def resolve(cls, repo_root: Path) -> ProtectionPolicy:
        """Resolve the protection policy for *repo_root*.

        This is the ONLY sanctioned function that reads git/filesystem/env for
        the protection set (FR-007, NFR-003).  All I/O is confined here; the
        returned value is frozen and I/O-free.

        Args:
            repo_root: Repository root (the directory that contains ``.kittify/``).

        Returns:
            A frozen :class:`ProtectionPolicy` with the resolved protection set
            and hatch state.

        Raises:
            :class:`ProtectionConfigError`: The ``protection.protected_branches``
                value exists but is not a list.
        """
        operator_hatch_active = _resolve_hatch()
        protected = _resolve_protected_branches(repo_root)
        return cls(
            protected_branches=protected,
            operator_hatch_active=operator_hatch_active,
        )

    # ------------------------------------------------------------------
    # Decision method
    # ------------------------------------------------------------------

    def is_protected(self, ref: str) -> bool:
        """Return ``True`` iff *ref* is in the protected set and the hatch is off.

        This folds the duplicated ``not hatch and ref in protected`` idiom that
        previously appeared at ≥3 callsites.

        Args:
            ref: A short branch name (e.g. ``"main"``).  Must NOT be
                fully-qualified (``refs/heads/…``).

        Returns:
            ``True`` when *ref* is protected; ``False`` when the hatch is active
            or *ref* is not in the protected set.
        """
        return ref in self.protected_branches and not self.operator_hatch_active


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_hatch() -> bool:
    """Return ``True`` when the operator escape hatch env var is truthy."""
    return os.environ.get(_HATCH_ENV_VAR, "").lower() in ("1", "true", "yes")


def _load_kittify_config(repo_root: Path) -> dict:  # type: ignore[type-arg]
    """Load ``.kittify/config.yaml`` and return its parsed content.

    Returns an empty dict when the file does not exist (normal for non-SK
    repos or repos without a ``protection:`` block).
    """
    config_file = repo_root / ".kittify" / "config.yaml"
    if not config_file.exists():
        return {}

    yaml = YAML()
    yaml.preserve_quotes = True
    try:
        with open(config_file, encoding="utf-8") as fh:
            return yaml.load(fh) or {}
    except Exception as exc:
        raise ProtectionConfigError(
            f"Failed to parse {config_file}: {exc}"
        ) from exc


def _resolve_protected_branches(repo_root: Path) -> frozenset[str]:
    """Resolve the protected-branch set from ``.kittify`` config and git state.

    Implements the four-row resolution table from ``contracts/protection-config.md``.
    The remote-default augmentation is applied ONLY on the absent-key path.
    """
    data = _load_kittify_config(repo_root)
    protection_block = data.get("protection")

    if protection_block is None or not isinstance(protection_block, dict):
        # Key absent entirely → default {main, master} ∪ {remote default}
        return _default_branches_with_remote(repo_root)

    raw_value = protection_block.get("protected_branches")

    if raw_value is None:
        # ``protection:`` block exists but key is absent → treat as absent
        return _default_branches_with_remote(repo_root)

    if not isinstance(raw_value, list):
        raise ProtectionConfigError(
            f"protection.protected_branches in .kittify/config.yaml must be a list, "
            f"got {type(raw_value).__name__}: {raw_value!r}"
        )

    # Explicit list (possibly empty) → exactly that set; no remote union
    return frozenset(str(b) for b in raw_value)


def _default_branches_with_remote(repo_root: Path) -> frozenset[str]:
    """Return ``{main, master}`` augmented with the remote default branch.

    Preserves the byte-identical default behaviour of the pre-refactor
    ``protected_branches()`` function (NFR-004).
    """
    branches = set(_DEFAULT_PROTECTED_BRANCHES)
    remote_default = _remote_default_branch(repo_root)
    if remote_default:
        branches.add(remote_default)
    return frozenset(branches)


def _remote_default_branch(repo_root: Path) -> str | None:
    """Return the remote default branch name, or ``None`` if unavailable.

    Mirrors the logic in ``git/commit_helpers._remote_default_branch``; this
    copy is intentional so the resolver is self-contained (FR-007).
    """
    import subprocess  # local import keeps module-level deps minimal

    def _run(args: list[str]) -> str | None:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    symbolic_ref = _run(["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"])
    if symbolic_ref and "/" in symbolic_ref:
        return symbolic_ref.rsplit("/", 1)[1]

    remote_show = _run(["remote", "show", "origin"])
    if remote_show:
        for line in remote_show.splitlines():
            if "HEAD branch:" in line:
                return line.rsplit(":", 1)[1].strip() or None
    return None
