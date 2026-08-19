# Post-tasks adversarial squad — convergent findings

Point-cut: post-tasks (anti-laziness + decomposition-realism) over the 12 subagent-authored WP
prompts. Two lenses (reviewer-renata, planner-priti). Both verdicts: **conditionally ready — the
chain/lane structure, subtask coverage (25/25 one home each), FR mapping, and freeze-first discipline
for the three C901 monsters are sound; a small set of prompt fixes before dispatch.**

| # | Sev | Lens | Finding | Disposition |
|---|-----|------|---------|-------------|
| Rn-1 | HIGH | renata | WP07 splits the shared render+`issues` helpers (`_render_per_project_store`/`_render_consent_readability`/`_render_tracker_egress`) BEFORE the `status`/`doctor` full-render goldens exist (frozen in WP09/WP10, downstream) — the mission's own freeze-first thesis diluted at its riskiest seam. | **FOLDED** — the `status` + `doctor` full-render goldens move to **WP02** (seams exist pre-extraction; stub network/daemon). WP09/WP10 now *verify* the WP02 golden stays green across the restructure (not freeze). WP07 gains a DoD line that the split keeps those goldens byte-green. |
| Pr-1 | MED | priti | Census artifact path drift — WP12 owns `docs/plans/code-quality/sync-env-census.md` but FR-007/plan-IC-06/contract-item-6/T024 said `research/env-census.md` (a `kitty-specs/` path lanes cannot write). | **FOLDED** — reconciled FR-007 + plan + contract + tasks.md to `docs/plans/code-quality/sync-env-census.md` (the correct, lane-writable location). |
| Rn-2 | MED | renata | `_resolve_gated_receiver` (L799) split across WP07 (admission wrapper) + WP08 (exec half) with an under-specified seam boundary — drop-a-branch hazard. | **FOLDED** — WP07 names the residual it leaves behind; WP08 references it by name; both carry the cross-WP DoD "behavior byte-identical, admission-assert AND receiver-resolution both reached, verified vs the now/dispatch golden." |
| Rn-3 / Pr-2 | MED | renata + priti | The writer-census + arch-gate baseline files (`_baselines.yaml`, `_golden_count_baseline.json`, `test_sync_writer_census.py`) are edited by WP04–08 (per-writer 1:1 key swap) + WP12 but are in no WP's `owned_files`. | **FOLDED** — WP04–08 + WP12 carry the explicit "small, individually-justified out-of-map edit" authorization note (the sanctioned escape hatch; avoids a re-finalize). Implementers confirm at runtime whether a grant-writer actually relocates (if none does, the census half is moot; the baseline re-pin half stands). |
| Rn-4 | MED | renata | The `diagnose` full-report golden freeze (contract item 6 / guard #6) is orphaned — no WP owns it. | **FOLDED** — WP02 annotates that `diagnose` renders its full report **inline** and is never extracted, so it is consciously left at the two cheap `--json` arms (`{available:false}`/`{total:0}`); the populated-queue render is out of the decomposition's blast radius. |
| Rn-5 / Pr-3 | LOW | renata + priti | The `cmd_*.py` "remaining-shell-split WP" (plan guard #3) has no WP — superseded by guard #2 (`@app.command` stays in `sync.py`). Nothing verifies the ~19 non-monster command bodies are ≤15 post-extraction. | **FOLDED** — plan annotated that guard #3's `cmd_*.py` is superseded; WP12 gains an assertion that no non-monster command body exceeds complexity 15 after its helpers extract. |
| Rn-6 | LOW | renata | Cross-batch cosmetic drift (branch_strategy prose; stale census path in contract/plan). | Reconciled with Pr-1; frontmatter is uniform (verified). |

**Positive confirmations (renata):** freeze-before-extract is ordered AND commit-order-checked for all
three monsters (T017→T018, T019→T020, T021→T022, each requiring golden green pre AND post, non-`--json`-only);
zero-behavior-change is a HARD co-gate (golden + ~60 patch-tests) in every extraction DoD, never "should
pass"; `# noqa: C901` retirement is non-gameable (`ruff --select C901` ≤15 + grep-proof pure cores);
the env var is `SPEC_KITTY_ENABLE_SAAS_SYNC` everywhere (Pd-1 fully propagated); late-bound seam +
1:1 census-swap rules consistent; all guards land in a subtask/DoD; all 12 prompts 166–236 lines, ≤4
subtasks, profile-load present. **priti:** chain order sound (WP02→WP03 dep; WP07 before WP09/WP10),
no duplicate new-module ownership, honest serial critical path.

No contested finding dropped. None re-slices the WPs — all are prompt-text / metadata reconciliations.
