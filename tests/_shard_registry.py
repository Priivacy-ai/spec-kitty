"""Explicit shard-registry seam — ``register()`` / ``all_groups()`` (FR-011, #2621).

Mission ``test-suite-friction-remediation-01KXDKBX`` WP16. Before this seam,
``tests/_arch_shard_map.py`` owned a module-level ``SHARD_GROUPS`` dict and
``tests/_next_shard_map.py`` mutated it directly (``SHARD_GROUPS["next"] =
ShardGroup(...)``) as an import-time side effect (a ``# noqa: F401``
import-for-side-effect line in ``tests/conftest.py`` was the only thing that
made the mutation happen). Two failure modes fell out of that shape:

1. A dropped import of ``_next_shard_map`` silently left the entire
   ``tests/next`` universe unmarked — nothing failed loudly at the point of
   the missing import, only (eventually, and confusingly) at whatever guard
   happened to notice.
2. A missing/typo'd group name surfaced as a bare ``KeyError`` wherever code
   did ``SHARD_GROUPS[group]`` — no guidance on which group was missing or
   why.

This module replaces the shared dict with an explicit, idempotent
:class:`ShardRegistry`: row-owner modules (``tests/_arch_shard_map.py``,
``tests/_next_shard_map.py``) call module-level :func:`register` at import
time instead of mutating a dict; consumers (``tests/conftest.py``'s
collection hook, the completeness guard in
``tests/architectural/test_arch_shard_marker_completeness.py``) call
:func:`all_groups` / :func:`get_group` instead of indexing a dict directly.
:data:`EXPECTED_GROUPS` is the manifest of group names that MUST be
registered — the completeness guard asserts every manifest entry resolves via
:func:`get_group`, which raises :class:`ShardGroupNotRegisteredError` (never a
bare ``KeyError``) naming the missing group.

Row-owner modules stay separate (``arch`` and ``next`` are two independent
modules registering into this one seam) — this module holds no group-specific
data of its own, only the registry mechanism and the ``ShardGroup`` shape.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ShardGroup:
    """One row of the shard registry (data-model E1).

    ``dir_assignment`` / ``file_assignment`` are kept as two separate maps
    (rather than one merged dict) purely for :meth:`ShardRegistry.shard_for`'s
    lookup efficiency — a handful of whole-directory prefixes checked first,
    then an ``O(1)`` exact-file lookup. :attr:`assignment` is the public,
    merged ``relpath/dirpath -> shard_idx`` view the data model describes.

    :attr:`default_fallback` is an opt-in, per-group auto-cover switch
    (FR-011, #2671): when ``True``, an under-root path that misses both
    ``dir_assignment`` and ``file_assignment`` is assigned a deterministic
    hash-bucket shard instead of resolving to ``None``. Defaults to
    ``False`` so every existing ``ShardGroup(...)`` construction site keeps
    its current behavior unchanged; a group opts in explicitly (see the
    ``arch`` row in ``tests/_arch_shard_map.py``).
    """

    group: str
    roots: tuple[str, ...]
    shard_count: int
    marker_prefix: str
    dir_assignment: dict[str, int] = field(default_factory=dict)
    file_assignment: dict[str, int] = field(default_factory=dict)
    default_fallback: bool = False

    @property
    def assignment(self) -> dict[str, int]:
        """Merged ``relpath/dirpath -> shard_idx`` map (data-model E1 field)."""
        return {**self.dir_assignment, **self.file_assignment}


def _under_roots(normalized: str, roots: tuple[str, ...]) -> bool:
    """True when *normalized* is one of *roots* or nested under one of them.

    Shared root-membership test (FR-011, #2671) — the same shape used for
    ``dir_assignment`` prefix matching in :meth:`ShardRegistry.shard_for`,
    reused as the hard gate for the opt-in default-fallback branch so a
    fallback shard is never assigned outside a group's declared roots.
    """
    return any(normalized == root or normalized.startswith(f"{root}/") for root in roots)


class ShardGroupNotRegisteredError(LookupError):
    """A requested shard group has no registered :class:`ShardGroup`.

    Deliberately never a bare ``KeyError`` (contract anti-goal) — the message
    names the missing group so the completeness guard fails diagnosably
    instead of surfacing an unexplained lookup failure.
    """


# The manifest of group names that MUST be registered before the
# completeness guard / conftest collection hook run. Adding a new shard
# group means adding its name here AND calling `register()` from its
# row-owner module (a new sibling of `tests/_arch_shard_map.py` /
# `tests/_next_shard_map.py`).
EXPECTED_GROUPS: frozenset[str] = frozenset({"arch", "next"})


class ShardRegistry:
    """An idempotent, order-independent shard-group registry.

    Row-owner modules call :meth:`register` at import time; consumers call
    :meth:`all_groups` / :meth:`get_group` / :meth:`shard_for` — never reach
    into a shared dict directly. Instantiable so tests can exercise
    registration/lookup semantics (including the "group not registered"
    diagnosable-failure path) against an isolated registry instead of
    mutating the shared module-level default.
    """

    def __init__(self) -> None:
        self._groups: dict[str, ShardGroup] = {}

    def register(self, group: ShardGroup) -> None:
        """Register *group*.

        Idempotent: re-registering the identical ``ShardGroup`` for a key
        already present is a no-op (safe against a module being imported more
        than once). Registering a DIFFERENT ``ShardGroup`` under an
        already-used key is rejected — that is a genuine duplicate-key
        collision, not a harmless re-import.
        """
        existing = self._groups.get(group.group)
        if existing is not None and existing != group:
            raise ValueError(
                f"shard group `{group.group}` is already registered with a "
                "different definition — duplicate-key registration rejected"
            )
        self._groups[group.group] = group

    def all_groups(self) -> dict[str, ShardGroup]:
        """Return a copy of the registered ``group name -> ShardGroup`` map."""
        return dict(self._groups)

    def get_group(self, name: str) -> ShardGroup:
        """Return the registered group named *name*, diagnosably.

        Raises :class:`ShardGroupNotRegisteredError` (never a bare
        ``KeyError``) naming the missing group when it is not registered.
        """
        try:
            return self._groups[name]
        except KeyError:
            raise ShardGroupNotRegisteredError(
                f"group `{name}` not registered"
            ) from None

    def shard_for(self, group: str, relpath: str) -> int | None:
        """Return the ``<marker_prefix>_N`` shard number for *relpath*.

        ``None`` when *group* is not registered, or *relpath* falls outside
        that group's assignment — identical resolution semantics to the
        pre-seam ``tests/_arch_shard_map.shard_for()``: whole-directory roots
        checked first, then an exact-file match. *relpath* is a
        repo-root-relative path using ``/`` separators (as produced by
        pytest's own nodeid/relpath reporting).

        When both explicit lookups miss and *group*'s
        :attr:`ShardGroup.default_fallback` is ``True``, an under-root
        *relpath* is assigned a deterministic hash-bucket shard instead of
        ``None`` (FR-011, #2671) — the auto-cover safety net that keeps a
        newly-added, not-yet-registered file from silently escaping every
        ``arch_shard_N`` marker. The fallback never fires outside the
        group's ``roots`` (a hard gate, same root-membership test used for
        ``dir_assignment``), and explicit ``dir_assignment`` /
        ``file_assignment`` entries always win because they are checked
        first.
        """
        spec = self._groups.get(group)
        if spec is None:
            return None
        normalized = relpath.replace("\\", "/")
        for dirpath, shard in spec.dir_assignment.items():
            if normalized == dirpath or normalized.startswith(f"{dirpath}/"):
                return shard
        explicit = spec.file_assignment.get(normalized)
        if explicit is not None:
            return explicit
        if spec.default_fallback and _under_roots(normalized, spec.roots):
            # Deterministic, non-cryptographic bucket hash — spreads
            # unregistered files across shards instead of piling them onto
            # one "lightest shard" (see T003 review guidance).
            digest = hashlib.sha1(normalized.encode())
            return int(digest.hexdigest(), 16) % spec.shard_count + 1
        return None


# The single, module-level default registry every row-owner module
# (`tests/_arch_shard_map.py`, `tests/_next_shard_map.py`) and every consumer
# (`tests/conftest.py`'s collection hook, the completeness guard) shares.
# Tests proving the diagnosable-failure / isolated-registration semantics
# construct their own `ShardRegistry()` instead of reaching into this one.
_REGISTRY = ShardRegistry()


def register(group: ShardGroup) -> None:
    """Register *group* into the shared default registry."""
    _REGISTRY.register(group)


def all_groups() -> dict[str, ShardGroup]:
    """Return the shared default registry's registered groups."""
    return _REGISTRY.all_groups()


def get_group(name: str) -> ShardGroup:
    """Return the shared default registry's group named *name*, diagnosably."""
    return _REGISTRY.get_group(name)


def shard_for(group: str, relpath: str) -> int | None:
    """Shard lookup against the shared default registry."""
    return _REGISTRY.shard_for(group, relpath)
