"""Unit tests for the shard-registry default fallback (FR-011, #2671).

Mission ``landing-pass-campsite-followups-01KXKWD7`` WP01. Before this WP,
``ShardRegistry.shard_for()`` returned ``None`` for any under-root file that
was not registered in a group's explicit ``dir_assignment`` /
``file_assignment`` maps — that miss meant ``tests/conftest.py``'s
``pytest_collection_modifyitems`` hook applied no ``arch_shard_N`` marker,
which in turn failed the GC-1 completeness gate
(``tests/architectural/test_arch_shard_marker_completeness.py``) and the
zero-gate-orphan gate
(``tests/architectural/test_gate_coverage.py::test_no_new_orphan_surfaces``)
whenever a contributor added a new ``tests/architectural/*.py`` file without
hand-editing ``tests/_arch_shard_map.py``. This has recurred 3+ times (see
that module's header comments).

This module exercises the fix directly against an isolated
``ShardRegistry()`` (never the shared default registry, per
``ShardRegistry``'s own docstring guidance for registration/lookup tests):
a per-group opt-in (``default_fallback=True``), root-gated, deterministic
hash-bucket fallback that only fires on an explicit-assignment miss.
"""

from __future__ import annotations

import pytest

from tests._shard_registry import ShardGroup, ShardRegistry

# Pure-logic unit tests (no subprocess/git/filesystem) — the `fast` marker keeps
# them in the `fast-tests-core-misc` gate's selection so this root-level file is
# not a zero-gate orphan (mirrors the sibling `tests/test_worker_home_isolation.py`).
pytestmark = [pytest.mark.fast]


def _make_registry(*, default_fallback: bool) -> tuple[ShardRegistry, ShardGroup]:
    """Build an isolated registry with one ``arch_like`` group registered."""
    registry = ShardRegistry()
    group = ShardGroup(
        group="arch_like",
        roots=("tests/architectural",),
        shard_count=3,
        marker_prefix="arch_shard",
        file_assignment={"tests/architectural/test_known_file.py": 2},
        default_fallback=default_fallback,
    )
    registry.register(group)
    return registry, group


def test_unregistered_under_root_file_resolves_to_none_without_fallback() -> None:
    """Pre-fix / opt-out parity: no fallback means an unregistered file is None."""
    registry, _ = _make_registry(default_fallback=False)

    result = registry.shard_for(
        "arch_like", "tests/architectural/test_brand_new_guard.py"
    )

    assert result is None


def test_unregistered_under_root_file_gets_fallback_shard_when_opted_in() -> None:
    """The behavior this WP adds: opt-in fallback covers an unregistered file."""
    registry, group = _make_registry(default_fallback=True)

    result = registry.shard_for(
        "arch_like", "tests/architectural/test_brand_new_guard.py"
    )

    assert result is not None
    assert 1 <= result <= group.shard_count


def test_out_of_root_path_stays_none_even_with_fallback_opted_in() -> None:
    """Root membership is a hard gate — out-of-root paths never get a shard."""
    registry, _ = _make_registry(default_fallback=True)

    result = registry.shard_for("arch_like", "src/specify_cli/foo.py")

    assert result is None


def test_explicit_file_assignment_still_wins_over_fallback() -> None:
    """An explicit ``file_assignment`` entry resolves to its declared shard."""
    registry, _ = _make_registry(default_fallback=True)

    result = registry.shard_for(
        "arch_like", "tests/architectural/test_known_file.py"
    )

    assert result == 2


def test_fallback_is_deterministic_across_repeated_calls() -> None:
    """Same relpath must resolve to the same shard on every call."""
    registry, _ = _make_registry(default_fallback=True)
    relpath = "tests/architectural/test_repeat_lookup.py"

    first = registry.shard_for("arch_like", relpath)
    second = registry.shard_for("arch_like", relpath)

    assert first == second


def test_fallback_spreads_across_shards_by_hash_bucket_not_lightest_shard() -> None:
    """Distinct unregistered paths must not all collapse onto one shard.

    A "lightest shard" fallback would pile every unregistered file onto a
    single shard; the hash-bucket fallback must spread them out instead. With
    a handful of distinct probe paths against ``shard_count=3``, requiring at
    least two distinct shard values is enough to rule out the degenerate
    "always shard 1" (or any single fixed shard) implementation without
    depending on a specific hash value.
    """
    registry, _ = _make_registry(default_fallback=True)
    probe_paths = [
        f"tests/architectural/test_probe_{i}.py" for i in range(8)
    ]

    shards = {registry.shard_for("arch_like", path) for path in probe_paths}

    assert len(shards) > 1


def test_next_group_parity_returns_none_for_unregistered_path_by_default() -> None:
    """A group that omits ``default_fallback`` (as ``next`` does) stays None."""
    registry = ShardRegistry()
    next_like = ShardGroup(
        group="next_like",
        roots=("tests/next",),
        shard_count=4,
        marker_prefix="next_shard",
        file_assignment={},
    )
    registry.register(next_like)

    result = registry.shard_for("next_like", "tests/next/test_unregistered.py")

    assert result is None
    assert next_like.default_fallback is False
