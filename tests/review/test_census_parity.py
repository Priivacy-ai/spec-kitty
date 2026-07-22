"""Pin the two live copies of the census-narrowing logic to identical output.

``GateCoverageScopeSource.scope_breakdown`` (``scope_source.py``) and
``pre_review_gate.derive_test_scope`` are two live copies of the same
census-narrowing derivation (the pre_review_gate copy's retirement is a tracked
follow-up). For NFR-001 they MUST produce byte-identical scope for the same
changed set. This test drives a shared corpus — spanning a per-shard group, an
empty-cone composite dir, and a catch-all-only excluded file — through BOTH
paths and asserts identical :class:`ScopeResult`, converting any silent
divergence into a red build.
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.review import pre_review_gate
from specify_cli.review.pre_review_gate import ScopeResult, derive_test_scope
from specify_cli.review.scope_source import GateCoverageScopeSource

# Hermetic, offline override maps covering all three narrowing shapes:
#  - ``status`` — per-shard group carrying its own ``tests/**`` glob
#  - ``git``    — composite (src-only) group whose dir has an EMPTY cone
#  - ``core_misc`` — the ``src/**`` catch-all (excluded regardless of shape)
_GROUPS: dict[str, tuple[str, ...]] = {
    "status": ("src/specify_cli/status/**", "tests/status/**"),
    "git": ("src/specify_cli/git/**",),
    "core_misc": ("src/**",),
}
_ROUTING: dict[str, pre_review_gate._CompositeRoute] = {
    "git": (None, None, ()),  # empty cone_roots -> empty-cone composite dir
}

_CORPUS: tuple[str, ...] = (
    "src/specify_cli/status/emit.py",  # per-shard tests/** direct target
    "src/specify_cli/git/foo.py",  # composite dir with no cone_roots (empty cone)
    "src/kernel/foo.py",  # catch-all only -> excluded
)


def _derive_scope_result(tmp_path: Path) -> ScopeResult:
    return derive_test_scope(
        _CORPUS,
        repo_root=tmp_path,
        filter_groups=_GROUPS,
        composite_routing=_ROUTING,
    )


def _source_scope_result(tmp_path: Path) -> ScopeResult:
    source = GateCoverageScopeSource(
        repo_root=tmp_path,
        filter_groups_override=_GROUPS,
        composite_routing_override=_ROUTING,
    )
    return pre_review_gate._scope_result_from_source(source, _CORPUS)


def test_census_forks_agree_on_the_full_scope_result(tmp_path: Path) -> None:
    """Both live census copies emit an identical ``ScopeResult`` for the corpus."""
    derived = _derive_scope_result(tmp_path)
    via_source = _source_scope_result(tmp_path)

    # Field-by-field equality (frozen dataclass __eq__), not "targets match" alone —
    # the shard/composite/excluded breakdown must also agree (NFR-001).
    assert via_source == derived


def test_corpus_actually_exercises_each_narrowing_shape(tmp_path: Path) -> None:
    """Guard: the corpus must keep hitting all three shapes, or the pin is hollow."""
    derived = _derive_scope_result(tmp_path)

    assert derived.matched_shard_groups == ("status",)
    assert derived.test_targets == ("tests/status",)
    assert derived.matched_composite_dirs == ("git",)
    assert derived.empty_cone_composite_dirs == ("git",)
    assert derived.excluded_scope_files == ("src/kernel/foo.py",)
