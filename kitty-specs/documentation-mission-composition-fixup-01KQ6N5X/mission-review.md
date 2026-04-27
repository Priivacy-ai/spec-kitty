# Mission Review — Documentation Mission Composition Fix-up (#502 fix-up)

**Reviewer**: claude:opus-4.7:mission-reviewer (post-merge mission-review)
**Date**: 2026-04-27
**Mission**: `documentation-mission-composition-fixup-01KQ6N5X` (mission_number 102)
**Predecessor**: `documentation-mission-composition-rewrite-01KQ5M1Y` (#502 original) merged at `1c03e2f4d6db6861610cbe4cc9ae340414a5bd8f`
**Baseline (predecessor merge commit)**: `1c03e2f4d6db6861610cbe4cc9ae340414a5bd8f`
**HEAD (fix-up merge commit)**: `b2394a8264ead954902c67d72b9ef15acb366922`
**Work packages**: WP01, WP02, WP03 (all approved on review cycle 0)

---

## Git timeline summary

- 32 commits since predecessor merge (`1c03e2f4..HEAD`).
- Diff stat: 27 files changed, 2371 insertions(+), 58 deletions(-).
- All file changes confined to: 7 new templates under `src/specify_cli/missions/documentation/templates/`, one new test file (`tests/specify_cli/test_documentation_prompt_resolution.py`), one edited test file (`tests/integration/test_documentation_runtime_walk.py`), an edited `quickstart.md` and a new `evidence/smoke-v2.md` under the predecessor's mission folder, plus the fix-up mission's own planning artifacts. **Zero substrate edits** (verified by name-only diff filter on `mission-runtime.yaml`, `runtime_bridge.py`, `executor.py`, step contracts, action bundles, `graph.yaml`).

---

## Per-Finding Closure Matrix

| ID | Finding (predecessor verdict) | Claim | Evidence | Verdict |
|---|---|---|---|---|
| **F-1** | Prompts not shipped — every documentation step returned `prompt_file=None`. | 7 governance-prose templates ship; parametrized resolution test pins the contract. | All 7 files exist (line counts: discover 55, audit 56, design 59, generate 57, validate 59, publish 57, accept 34 — all ≥10). Filenames exactly match `mission-runtime.yaml` `prompt_template:` declarations (lines 24, 31, 38, 45, 52, 59, 65). Adversarial read of `discover.md` confirms governance prose for the host LLM (objective, expected outputs, gate artifact, doctrine references, definition of done) — not boilerplate or implementation code. The 7-parameter `test_prompt_template_exists_and_is_nonempty` PASSES (7/7). | **CLOSED** |
| **F-2** | Dogfood smoke never dispatched — `kind: query`, no invocation records. | `evidence/smoke-v2.md` proves real composed-action issuance with paired trail records. | `next-issue.json` shows `kind == "step"`, `step_id == "discover"`, `mission == "documentation"`. Trail directory `<TMP_REPO>/.kittify/events/profile-invocations/` contains 5 paired `started`+`completed` JSONL records (one per `discover` sub-step: `bootstrap`, `capture_documentation_needs`, `validate_scope`, `write_spec`, `commit_spec`); every `started` carries `action: "discover"`, every `completed` carries `outcome: "done"`. Run advanced `discover → audit` (`next-advance.json` `mission_state == "audit"`). Commands use `uv run --project "$SPEC_KITTY_REPO" --python 3.13` exclusively. Temp repo lived at `/var/folders/.../docs-smoke-v2-XXXXXX/repo` — outside the spec-kitty source tree. Grep for substantive `--directory` returns only the inline warning. | **CLOSED** |
| **F-3** | Integration walk advanced only one action. | New `test_full_advancement_through_six_actions` drives all 6 advances via `decide_next_via_runtime`. | `grep -n "test_full_advancement_through_six_actions"` matches at line 560. Test body iterates `_DOCUMENTATION_WALK = [(discover, spec.md), (audit, gap-analysis.md), (design, plan.md), (generate, docs/index.md), (validate, audit-report.md), (publish, release.md)]`, authors each gate artifact before reporting `--result success`, asserts `decision_kind != "blocked"` and that the action joined `completed_steps` after every iteration. Final loop cross-checks the trail dir and asserts paired `started`+`completed` records exist for every advancing action. Live run: PASSED in 16s. | **CLOSED** |
| **F-4** | Guard test bypassed dispatch — called `_check_composed_action_guard()` directly. | `test_missing_artifact_blocks_with_structured_failure` refactored to call `decide_next_via_runtime` and assert `Decision.kind == "blocked"`. | Lines 410-502: scaffolds feature_dir with `meta.json` only (no `spec.md`), issues `discover`, drives `--result success`, asserts (a) `decision_kind == "blocked"`, (b) `decision.guard_failures` non-empty and contains `"spec.md"`, (c) snapshot `completed_steps == []` AND `issued_step_id == "discover"` both before and after (no advancement). Helper-level `test_unknown_documentation_action_fails_closed` retained at lines 510-540 with explanatory docstring referencing FR-006 / D6 (the bridge does not accept arbitrary action input, so the unknown-action default cannot be exercised through dispatch). Both tests PASS in the regression run. | **CLOSED** |
| **F-5** | Quickstart asserted `d["issued_step_id"]` — the `Decision` schema uses `step_id` / `preview_step`, raising `KeyError`. | `quickstart.md` rewritten to use `d.get("step_id") or d.get("preview_step")`. | `grep "issued_step_id" quickstart.md` returns no matches. The Python snippet at lines 64-72 reads `step = d.get("step_id") or d.get("preview_step")`. Adversarial check: I ran the snippet against a synthetic `next.json` with `kind: "query"` / `preview_step: "discover"` and against an issued-step variant with `kind: "step"` / `step_id: "discover"`; both parse without exception. Diff size: 38 lines changed (≤50 per C-004). `--project` reminder and `--directory` #735 warning preserved verbatim. | **CLOSED** |

---

## FR Coverage Matrix

| FR | Requirement | Evidence | Status |
|---|---|---|---|
| FR-001 | 7 templates ship at `src/specify_cli/missions/documentation/templates/`, governance-prose. | All 7 files present, ≥10 lines each, governance prose verified by adversarial read of `discover.md`. | PASS |
| FR-002 | `_build_prompt_safe` returns non-null `prompt_file` for every documentation step. | `tests/specify_cli/test_documentation_prompt_resolution.py` — 7 parametrized PASSes. The integration walk's full-advancement test additionally exercises `decide_next_via_runtime` end-to-end through all 6 advancing actions; each non-blocked decision implies non-null prompt resolution. | PASS |
| FR-003 | Integration walk includes a 6-action dispatch test. | `test_full_advancement_through_six_actions` at line 560; live PASS. | PASS |
| FR-004 | Trail-record assertion verifies paired `started`/`done` for every advancing action. | T10 assertion block at lines 656-702: builds `paired_actions` set from trail JSONL, asserts `expected_actions - paired_actions == set()`. PASS. | PASS |
| FR-005 | Missing-artifact test asserts via `decide_next_via_runtime` with structured blocked decision. | `test_missing_artifact_blocks_with_structured_failure` at line 410. Three surfaces asserted (kind, guard_failures, snapshot equality). PASS. | PASS |
| FR-006 | Unknown-action helper-level test retained with explanatory docstring. | `test_unknown_documentation_action_fails_closed` at line 510 with D6-referencing docstring. PASS. | PASS |
| FR-007 | `quickstart.md` JSON field references match `Decision` schema (`step_id` / `preview_step`, never `issued_step_id`). | `grep issued_step_id quickstart.md` empty. Snippet uses `.get("step_id") or .get("preview_step")`. PASS. | PASS |
| FR-008 | New `evidence/smoke-v2.md` shows action issuance + paired trail records. | `next-issue.json` has `kind: "step"`, `step_id: "discover"`. 5 paired trail JSONL files with `action: "discover"`, `outcome: "done"`. | PASS |
| FR-009 | Smoke uses `uv --project`, temp repo outside spec-kitty tree. | All `uv run` invocations in smoke-v2 use `--project "$SPEC_KITTY_REPO"`. Temp repo path `/var/folders/.../docs-smoke-v2-XXXXXX/repo` — outside spec-kitty. Zero substantive `--directory` (only inline warning). | PASS |
| FR-010 | All predecessor regression suites green. | The full 9-suite regression command (131 tests) PASSED in 30.9s. | PASS |

---

## Predecessor Regression Status (NFR-002)

```
$ uv run --python 3.13 --extra test pytest \
    tests/specify_cli/next/test_runtime_bridge_composition.py \
    tests/specify_cli/next/test_runtime_bridge_research_composition.py \
    tests/integration/test_research_runtime_walk.py \
    tests/specify_cli/next/test_runtime_bridge_documentation_composition.py \
    tests/specify_cli/test_documentation_drg_nodes.py \
    tests/specify_cli/test_documentation_template_resolution.py \
    tests/specify_cli/mission_step_contracts/test_documentation_composition.py \
    tests/specify_cli/test_documentation_prompt_resolution.py \
    tests/integration/test_documentation_runtime_walk.py -q --timeout=180

  ============================= 131 passed in 30.92s =============================
```

100% pass. Zero new findings, zero regressions.

---

## Lint Status (NFR-003 / NFR-004)

| Tool | Target | Result |
|---|---|---|
| `ruff check` | `src/specify_cli/missions/documentation/templates/`, new test file, edited integration walk | All checks passed! |
| `mypy --strict` | new test file, edited integration walk | Success: no issues found in 2 source files |

---

## Constraint Trace

| ID | Constraint | Verification | Status |
|---|---|---|---|
| C-001 | No edits to predecessor's runtime sidecar / contracts / action bundles / DRG / `runtime_bridge.py` / `executor.py`. | `git diff --name-only 1c03e2f4..HEAD` filtered against the substrate path globs returns ZERO matches (`NO SUBSTRATE EDITS`). `git show b2394a8 --stat` for those paths is empty. | PASS |
| C-002 | All predecessor constraints (C-001..C-010) preserved. | Trivially preserved because substrate is untouched. C-007 forbidden-symbol grep on `tests/integration/test_documentation_runtime_walk.py` returns only the docstring listing (no real `mock.patch` targets). | PASS |
| C-003 | New evidence file named `smoke-v2.md`; both files preserved. | Predecessor `smoke.md` retained (referenced from smoke-v2.md line 9 and line 20-22). New file at correct path. | PASS |
| C-004 | Quickstart diff ≤ 50 lines, confined to JSON field refs and command-output prose. | Diff stat: 38 lines (within budget). Edits confined to the Python check block, the issuance command lines, and the surrounding "Expected outcomes" prose. No structural changes. | PASS |
| C-005 | No edits to predecessor's `mission-review.md`. New report at `…fixup-01KQ6N5X/mission-review.md`. | `git log 1c03e2f4..HEAD -- …rewrite-01KQ5M1Y/mission-review.md` shows only commit `93cb7479` (the predecessor reviewer's own report committed AFTER the rewrite merged but BEFORE this fix-up began — not a fix-up edit). This file (the new fix-up review report) lands at the correct path. | PASS |

---

## Drift / Risk Findings

- **No drift detected.** Every changed path maps cleanly to a finding closure (F-1..F-5), the mission's planning artifacts (kitty-specs/documentation-mission-composition-fixup-01KQ6N5X/…), or expected predecessor-mission additions (smoke-v2.md, quickstart.md edit). The dossier snapshot under the predecessor's `.kittify/dossiers/` is a snapshot regeneration during normal mission lifecycle (66 lines diff, status-only metadata) and is not substrate.
- **No risk findings.** The fix-up adheres to its scope statement: substrate is untouched, mocks remain absent from the integration walk, lint/typing are clean, and the smoke evidence is genuine (not a transcript of `kind: query` papered over with claimed PASS).

---

## Final Verdict

**PASS**

### Verdict rationale

All 5 review findings are genuinely closed, not just claimed-closed:

- F-1: Templates ship with substantive governance prose; resolution test PASSES across all 7 step ids.
- F-2: smoke-v2.md captures `kind: "step"`, `step_id: "discover"`, and 5 paired `started`+`completed` trail records under `<TMP_REPO>/.kittify/events/profile-invocations/` — real action issuance, not a query transcript. Temp repo is outside spec-kitty and `--project` is used uniformly.
- F-3: The 6-action walk is a real iteration through `decide_next_via_runtime`, not a comment listing actions. Live test PASSES; per-action paired trail records are asserted as a set difference.
- F-4: The dispatch-level guard test calls `decide_next_via_runtime` (not the helper) and asserts kind/failures/snapshot-equality. Helper-level coverage retained per D6 with an explanatory docstring.
- F-5: Quickstart snippet uses tolerant `.get(...)` accessors; verified executable against synthetic JSON without `KeyError`.

Predecessor regression suite (9 files, 131 tests) PASSES at 100%. Lint and mypy --strict clean on changed files. C-001 substrate-immutability constraint trivially holds: the diff against `1c03e2f4` shows zero substrate edits. No new HIGH/CRITICAL findings.

NFR-005 hard gate (real action issuance in smoke evidence) is satisfied with multi-line confirmation: `kind: "step"`, `action: "discover"`, `outcome: "done"`, paired records present.

### Open items (non-blocking)

- The five paired trail records all carry `action: "discover"` (one per sub-step of the discover step contract), not one per top-level documentation action. This matches the dispatch architecture: a single composed action expands into multiple step-contract sub-steps, each producing its own paired record. The smoke captures only the first action's full sub-step trail — but the integration walk's `test_full_advancement_through_six_actions` asserts the per-action trail-record set across all 6 advancing actions, so the dispatch contract is exercised at a higher fidelity in tests than in the smoke. No remediation required; calling out for clarity.
- The mypy `cast` carve-out in `executor.py` (#805) and the Python pin (Phase 7) remain out of scope as declared in the spec — not a fix-up gap.

---

*End of review.*
