---
work_package_id: WP11
title: Golden-count inventory + recurrence guard
dependencies:
- WP07
requirement_refs:
- FR-014
- FR-016
- NFR-002
tracker_refs:
- '2076'
planning_base_branch: feat/test-suite-friction-remediation
merge_target_branch: feat/test-suite-friction-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/test-suite-friction-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/test-suite-friction-remediation unless the human explicitly redirects the landing branch.
subtasks:
- T048
- T049
- T050
- T051
- T052
- T053
- T054
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_golden_count_ban.py
create_intent:
- tests/architectural/test_golden_count_ban.py
- golden-count-inventory.md
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_golden_count_ban.py
role: implementer
tags: []
shell_pid: "3199451"
shell_pid_created_at: "1783957741.51"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md) FR-014 +
[data-model.md](../data-model.md) E-10, [plan.md](../plan.md) §IC-14 + the "New-guard-file DoD" directive,
and WP07 (`tests/status/test_models.py`) — the exemplar conversion pattern this sweep follows. This WP
depends on WP07 so the exemplar exists first.

## Objective

Solve the golden-count friction across the **batch-owned CLEAN directories** (~773 convert-candidates) and
guard against regrowth — convert-sites inside Lane-0/A/B-owned directories are **OUT OF SCOPE** for this
mission (ledgered + deferred, see T051): (1) build an AST **inventory** of `len(<collection>) == <int>` in
`tests/`, classified `keep` (cardinality *is* the contract) vs `convert` (a set/frozenset-equality expresses
it better); (2) write a **recurrence guard** that fails on a NEW un-annotated golden-count assertion; (3)
establish the `convert`-set **baseline** and emit an inventory artifact **partitioned BY DIRECTORY** so the
batch WPs (WP12–WP14) burn down the clean-dir slices.

## Context

- ~2102 `len(...) == int` assertions exist across ~646 files; only a subset are brittle golden counts. The
  clean-directory convert-candidate volume for this mission's batches is ~773 sites (WP12–WP14 own disjoint
  directories; see their prompts).
- Escape hatch: `# golden-count: cardinality-is-contract` marks a legitimate cardinality assertion the guard
  must not flag.
- **New-guard-file DoD applies** — this adds `tests/architectural/test_golden_count_ban.py`.

## Subtask guidance

- **T048 — AST inventory.** Walk `tests/` for `ast.Compare` of `len(<collection>) == <int>`. Classify each:
  `keep` if cardinality is the genuine contract, `convert` if a set/dict/frozenset-equality is the real
  contract. Record file, line, enclosing qualname, classification.
- **T049 — recurrence guard.** Write `test_golden_count_ban.py`: scan `tests/` and fail on any NEW
  un-annotated golden-count assertion (i.e. one not in the accepted baseline and lacking the
  `# golden-count: cardinality-is-contract` escape hatch). Keep the predicate precise — annotated and
  genuine-cardinality sites pass.
- **T050 — red-first regression.** A fixture with a fresh un-annotated `len(x) == 3` **fails** the guard; an
  annotated one **passes**.
- **T051 — baseline + inventory artifact.** Establish the `convert`-set baseline count. Emit
  `golden-count-inventory.md` under the feature_dir (a committed mission artifact, not a `tests/` owned file)
  partitioning the convert-set **BY DIRECTORY**, so WP12/WP13/WP14 can pull their owned-dir slices. If the
  inventory reveals convert-sites inside a **partially-owned** dir (owned by another WP), note them for the
  owning WP — do NOT assign them to a batch. Additionally emit a third **"deferred (owned-file dir)"**
  partition listing every convert-site inside a Lane-0/A/B-owned directory that is excluded from this
  mission's batches (`specify_cli` is the largest bucket); file/reference follow-up **#2625**. These are
  grandfathered into the baseline **deliberately and ledgered**, NOT silently.
- **T052 — new-guard-file DoD.** Register `test_golden_count_ban.py` in `tests/_arch_shard_map.py` **in the
  current `SHARD_GROUPS`-dict idiom** (the seam does not exist yet — WP16 is the downstream serial dependent
  that introduces `register()`). **WP16 (downstream serial dependent) is the sole owner/reconciler of
  `tests/_arch_shard_map.py` + the gate-coverage baselines: WP11 registers `test_golden_count_ban.py` in the
  current idiom and re-freezes; WP16 carries that registration forward into the `register()` seam.** This is
  a serial handoff, NOT a cross-lane trivial-merge append to flag in the PR. Re-freeze both gate-coverage
  baselines: gc3b `tests/architectural/_gate_coverage_baseline.json` (`--update-baseline`) and gc2b
  `tests/architectural/baselines/*.txt` (`--freeze-baselines`). The residual must negate every
  `next_shard`/`arch_shard` marker. **The gc3b JSON is a "last-writer regenerates" artifact, not a textual
  merge** — WP11 regenerates it here; WP16, then WP17 (the terminus), regenerate it downstream. **Note:**
  WP15 (gc2b scope-to-orphan) lands early to relieve this burden — if WP15 is already merged, the gc2b
  refreeze may be a no-op; keep the refreeze as the fallback.
- **T053 — DoD.** `.venv/bin/python -m pytest tests/architectural/test_golden_count_ban.py -q` green on the
  real tree.
- **T054 — gates + tracer.** `ruff`/`mypy` clean; append tracer catalog rows.

## Branch Strategy

Lane C anchor. Branches from WP07's tip (exemplar dependency); merges into
`feat/test-suite-friction-remediation`. WP12/WP13/WP14 depend on this WP's inventory artifact + baseline.

## Definition of Done (non-fakeable — NFR-002)

- [ ] AST inventory built and classified (`keep` vs `convert`), emitted as
      `../golden-count-inventory.md` partitioned BY DIRECTORY, **including a third "deferred (owned-file dir)"
      partition** listing every excluded Lane-0/A/B-owned-dir convert-site (`specify_cli` the largest bucket),
      referencing follow-up **#2625** — deliberately ledgered, not silently grandfathered.
- [ ] `test_golden_count_ban.py` fails on a fresh un-annotated `len==int` fixture and passes an annotated one.
- [ ] The `convert`-set baseline established (a number the batches strictly decrease).
- [ ] `test_golden_count_ban.py` registered in `tests/_arch_shard_map.py` in the current `SHARD_GROUPS`-dict
      idiom (WP16, the downstream serial dependent, carries it forward into the `register()` seam) AND both
      gate-coverage baselines re-frozen (gc3b `--update-baseline`, gc2b `--freeze-baselines`); residual
      negates every `next_shard`/`arch_shard` marker.
- [ ] Guard green on the real tree; `ruff` + `mypy` clean.
- [ ] **Tracer (FR-016):** append catalog rows for the golden-count ratchet (invariant-vs-shape, CaaCS
      churn, verdict) to `../tracer-design-decisions.md` + friction log.

## Risks

- **Boil-the-ocean** — bounded by the baseline (measurable per-WP) + guard (no regrowth). The batches only
  convert; keep-classified sites stay.
- **Guard false positives** on genuine cardinality assertions — the escape-hatch annotation keeps it precise.
- **`_arch_shard_map.py` handoff to WP16** — WP16 depends serially on WP11, so WP11's registration lands
  upstream and WP16 carries it forward into the `register()` seam. WP16 is the sole owner/reconciler; this is
  not a cross-lane merge to resolve in the PR.

## Reviewer guidance

- Confirm the guard is red-first proven and the escape hatch works.
- Confirm the inventory artifact is directory-partitioned and the baseline is a concrete decreasing number.
- Confirm the `_arch_shard_map.py` registration uses the current `SHARD_GROUPS`-dict idiom (WP16 carries it
  forward into the `register()` seam downstream) and that WP16 is left as the sole owner/reconciler.

## Activity Log

- 2026-07-13T15:04:48Z – claude:sonnet:python-pedro:implementer – shell_pid=3048275 – Assigned agent via action command
- 2026-07-13T15:37:52Z – user – shell_pid=3048275 – Claiming (retroactive: lane worktree already had committed implementation)
- 2026-07-13T15:38:08Z – user – shell_pid=3048275 – Implementing
- 2026-07-13T15:43:29Z – claude:sonnet:python-pedro:implementer – shell_pid=3048275 – Ready for review: AST inventory (2034 sites, 1030 keep/1004 convert) + recurrence guard (per-dir ceiling ratchet) + directory-partitioned golden-count-inventory.md incl. #2625 deferred partition; gc3b/gc2b re-frozen; test_golden_count_ban.py registered in _arch_shard_map.py shard_3 (WP16 carries forward into register() seam).
- 2026-07-13T15:49:09Z – claude:opus:reviewer-renata:reviewer – shell_pid=3199451 – Started review via action command
- 2026-07-13T15:59:25Z – user – shell_pid=3199451 – Review passed (reviewer-renata/opus): non-vacuous per-dir ceiling guard, #2625-deferred ledger, new-guard-file DoD complete
