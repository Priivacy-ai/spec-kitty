"""The single gate-selection authority (FR-016 / #2476) — consistency, singularity, floor.

``scripts/ci/gate_selection.py`` is the ONE importable authority that answers
"which shards/gates does a diff select". These guards prove:

* **Consistency** — its answers agree with the two hand-authored routing sources
  (the dorny filter block + the job ``if:`` gates) for representative diffs.
* **Singularity / parses-not-re-encodes** — it reads the *real on-disk* router
  YAML; mutating a temp copy of that YAML changes its answer, proving it PARSES
  rather than carrying a second hand-maintained routing map (the #2476 hazard).
  WP17 (completeness oracle) and WP18 (local pre-PR parity) import this same
  module — there is no second parser.
* **Fail-closed (FR-004 / T039)** — an unmapped ``src/**`` change forces run-all;
  ``docs``/``corpus`` are non-src and excluded from the unmatched loop.
* **Non-vacuity floor** — the parsed model is not empty.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ci.gate_selection import (
    DEFAULT_ROUTER_PATH,
    GateSelection,
    Router,
    load_router,
    select_gates,
)

pytestmark = pytest.mark.architectural


@pytest.fixture(scope="module")
def router() -> Router:
    return load_router()


def test_docs_only_diff_selects_zero_code_shards(router: Router) -> None:
    """NFR-002: a docs-only diff selects no code shards."""
    selection = select_gates(["docs/architecture/status-model.md"], router=router)
    assert selection.selected_code_shards == frozenset()
    assert not selection.unmatched_src


def test_corpus_only_diff_selects_zero_code_shards(router: Router) -> None:
    """Non-src corpus data selects no code shards and does not trip unmatched."""
    selection = select_gates(["packs/built-in/missions/foo.md"], router=router)
    assert selection.selected_code_shards == frozenset()
    assert not selection.unmatched_src


def test_src_group_diff_selects_its_shard_and_heavy_arch(router: Router) -> None:
    """A change confined to one src group selects that group's shard + the heavy battery."""
    selection = select_gates(["src/specify_cli/merge/executor.py"], router=router)
    assert selection.matched_groups == frozenset({"merge"})
    assert "tests-merge" in selection.selected_code_shards
    assert "architectural-heavy" in selection.selected_code_shards


def test_unmapped_src_change_forces_run_all_fail_closed(router: Router) -> None:
    """FR-004 / T039: a src/** change matched by no group forces run-all, never a silent skip."""
    selection = select_gates(["src/specify_cli/__unmapped_probe__/thing.py"], router=router)
    assert selection.unmatched_src is True
    # run-all: every code shard is selected, not a quiet zero.
    assert selection.selected_code_shards == router.code_shard_jobs
    assert selection.selected_code_shards


def test_docs_and_corpus_are_excluded_from_the_unmatched_loop(router: Router) -> None:
    """T039: data groups can never trip the fail-closed src catch-all."""
    for data_path in ("docs/x.md", "packs/y.md", "kitty-specs/m/spec.md"):
        assert select_gates([data_path], router=router).unmatched_src is False


def test_full_mode_runs_everything(router: Router) -> None:
    """FR-018/FR-019: full mode forces run-all even for a docs-only path set."""
    selection = select_gates(["docs/x.md"], router=router, mode="full")
    assert selection.selected_code_shards == router.code_shard_jobs


def test_fast_arch_gates_are_always_on_and_selected_even_for_docs(router: Router) -> None:
    """The fast always-on arch gates carry no filter group and always run."""
    assert {"terminology", "layer-rules"} <= router.always_on_jobs
    selection = select_gates(["docs/x.md"], router=router)
    assert {"terminology", "layer-rules"} <= selection.selected_jobs


def test_authority_is_consistent_with_the_two_hand_sources(router: Router) -> None:
    """Every selected code shard's gate references a matched (or run-all) src group.

    This ties the authority's answer back to the two hand-authored sources: a job
    is selected only because its ``if:`` (authority 2) references a group its
    globs (authority 1) matched — never from a private side-table.
    """
    selection = select_gates(["src/specify_cli/status/store.py"], router=router)
    for job in selection.selected_code_shards:
        gate_groups = router.job_gates[job]
        assert gate_groups & (selection.matched_groups | router.src_backed_groups)


def test_authority_parses_the_yaml_not_a_hardcoded_map(tmp_path: Path) -> None:
    """Singularity/anti-#2476: mutating the on-disk router changes the answer.

    If the authority re-encoded a second hand-maintained routing map instead of
    parsing, deleting a group from the YAML would not change its answer. Proving
    the answer tracks the file proves there is one authority: the file, parsed.
    """
    baseline = select_gates(["src/specify_cli/merge/x.py"])
    assert "tests-merge" in baseline.selected_code_shards

    # Remove the whole `merge` filter block from a temp copy → `merge` no longer matches.
    text = DEFAULT_ROUTER_PATH.read_text(encoding="utf-8")
    mutated = text.replace("            merge:\n              - 'src/specify_cli/merge/**'\n", "")
    assert mutated != text, "mutation fixture no longer matches the router — update it"
    router_copy = tmp_path / "ci-router.yml"
    router_copy.write_text(mutated, encoding="utf-8")

    mutated_router = load_router(router_copy)
    after = select_gates(["src/specify_cli/merge/x.py"], router=mutated_router)
    # merge/** now matches only the `any_src` probe → unmatched → run-all,
    # but crucially the `merge` group is no longer among matched groups.
    assert "merge" not in after.matched_groups
    assert after.unmatched_src is True


def test_non_vacuity_floor(router: Router) -> None:
    """The parsed model must be non-empty: real groups, code shards, and data groups.

    A content floor (not a cardinality count): the well-known code groups and the
    non-src data groups must be present, so the authority can never pass vacuously
    against an empty or truncated parse.
    """
    # Representative code groups must be present (content check, not a count).
    assert {"merge", "status", "cli", "charter", "kernel"} <= router.src_backed_groups
    # The non-src data groups must be present and classified as non-code.
    assert {"docs", "corpus"} <= (router.routing_groups - router.src_backed_groups)
    assert router.code_shard_jobs  # at least one code shard is wired


def test_gate_selection_returns_typed_result(router: Router) -> None:
    """The public API returns the documented dataclass shape for WP17/WP18."""
    selection = select_gates(["docs/x.md"], router=router)
    assert isinstance(selection, GateSelection)
    assert isinstance(selection.selected_jobs, frozenset)
    assert isinstance(selection.selected_code_shards, frozenset)
