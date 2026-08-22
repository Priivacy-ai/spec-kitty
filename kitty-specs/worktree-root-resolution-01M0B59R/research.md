# Research: Worktree-Aware Root Resolution & Verdict Parity

Phase 0 output, **reframed 2026-08-18** after a post-plan adversarial squad (architect + reviewer + debugger) — including an **empirical run of the resolver family** — refuted the brief's clone-re-anchor grounding. No new dependencies (Supply-Chain N/A by inspection). The authoritative root-cause source is `docs/plans/investigations/write-path-topology-root-cause.md` (spike #3129).

## Decision 0 — The squad reframe (supersedes the original "single classifier" framing)

**Empirical resolver matrix (run on base):**

| Case | `resolve_canonical_root` | `find_repo_root` |
|------|--------------------------|------------------|
| primary | self | self |
| **standalone clone** | **self (NOT re-anchored)** | **self (NOT re-anchored)** |
| linked worktree | primary (re-anchored) | primary (re-anchored) |
| nested clone | self | **primary (re-anchored)** |

**Findings:**
- The "standalone clone re-anchored to an unrelated primary" bug **does not exist** — a clone's `.git` is a directory, so resolvers return the clone itself (the desired outcome). The clone/primary split is **undecidable** from local state (fresh clone ≡ upstream). → spec C-005; the classifier is an **identity guard**, not a clone/primary kind.
- The worktree→primary re-anchor is often **deliberate**: `_anchor_repair_root` (#2320 status-home) and the primary-read anchors `get_feature_target_branch`/`resolve_merge_target_branch`/`mission_runtime/resolution.py` (#3328). A global default-flip re-introduces the "merge into wrong branch" bug. → spec C-004, FR-008 must-not-flip inventory.
- The accepted remediation for this class (#3129 investigation) is a **fail-closed checkout-identity refusal (#3128)**, NOT a checkout-local write redirect. → spec C-003.

## Decision 1 — One checkout-identity guard with read/write intent

**Decision**: Add `core/checkout_identity.py` — `resolve_checkout_identity(cwd, intent)` returning ownership + `canonical_target`. In-scope write commands consult it and adopt the #3128 fail-closed refusal; deliberate primary reads declare `intent=PRIMARY_READ` and are never flipped.

**Rationale**: `get_main_repo_root` (`core/paths.py:483-493`) is the real primitive (~130 callers across ~40 files); flipping it globally would regress the deliberate anchors. Locality of change + single-canonical-authority → a small additive guard that named commands adopt, not a primitive rewrite.

**Alternatives**: (a) rewrite `resolve_canonical_root` per FR-001's literal wording — rejected: breaks 4 existing tests (`test_canonical_root_when_in_worktree.py`, `test_root_resolver.py`) that enforce the deliberate re-anchor as correct. (b) global default-flip on `get_main_repo_root` — rejected: regresses #3328.

## Decision 2 — Per-command fail-closed decisions (no blanket-REFUSE)

**Decision**: Pin each command's behavior explicitly; refusal is for the foreign-checkout write, not a blanket option an implementer can apply everywhere to go green.

**Rationale (squad)**: a blanket "REFUSE on every worktree" passes contract tests while making the commands unusable in the normal lane workflow. The classifier settled which commands are genuine:
- **Genuine red-able (confirmed #3129 members):** `doctor tool-surfaces --fix` (#2613 — per-checkout agent files, silently mutates primary's manifest; cleanest), `setup-plan` (#3124 — read-side false-green `branch_matches_target:true` from primary HEAD), `backfill-runtime-state` cutover guard (#3049 — verifies the same redirected path it wrote).
- **Keep, reconciled:** `intake` (#3540 — fail-closed identity check before shared-slot clobber), `doctor mission-state` (#3051/#3541 — preserve #2320 + identity awareness + manifest honesty), `find_repo_root` nested-clone boundary (#2610 — align with `resolve_canonical_root`).
- **Dropped (already correct):** `--owned-checkout` (#3449 — `resolve_ownership_claim`→`effective_root`→`create_time_target` already routes writes to the claimed checkout; it is the *fix* for the class). Recommend tracker wontfix.

## Decision 3 — Verdict-seam hoist: parser → `status`, gate → `lanes`-side leaf

**Decision**: Hoist `_parse_review_result_json` (`orchestrator_api/commands.py:1297`) into `status` (co-located with `ReviewResult`, `status/models.py:286`); hoist `_enforce_for_review_commit_gate` (`:1257`, uses `predict_lane_worktree` at `:1281`) into a `lanes`-side leaf with a **surface-neutral error contract** (return a decision; each surface renders its own failure).

**Rationale (squad)**: no shared-package-boundary violation (that boundary only forbids retired external imports). But the gate is entangled with the orchestrator envelope (`_fail` → `NoReturn`); a lift-and-shift would drag envelope semantics into the CLI. Parking the gate in `status` risks tightening the existing `status`↔`lanes` deferred-import cycle → put it in a `lanes` leaf. FR-011 requires **both** gate directions asserted (satisfied→pass, unsatisfied→fail) to prevent an always-pass-for-clone fake.

## Decision 4 — Audit residuals: value round-trip + new artifact-scoped drift test

**Decision**: Register `review_result` in the `status_event_row` shape (`audit/shape_registry.py:90-111`, verified absent). Add a **value-equality** round-trip property with a non-vacuous generator. Add a **new `status_event_row`-scoped** drift test.

**Rationale (squad)**: the existing `test_shape_registry_writer_parity.py` is `meta.json`-scoped and tautological (`writer_keys ⊆ audit_keys`, both from the same annotations) — registering `review_result` neither breaks it nor is helped by de-tautologizing it. The FR-014 residual is on a **different artifact**. The subset/key-presence round-trip is fakeable (a replay that keeps the key but corrupts the value passes; a generator emitting no `review_result` passes vacuously) → value-equality + guaranteed non-vacuous generator.

**Do NOT** touch the reducer projection (`reducer.py:210-215`, `407ea376c4` — C-001) or the repair-row preservation (`mission_state.py:1879`, `bec7c25273` — C-002); both **verified true** in code + ancestry. Each gets a **green sentinel** (NFR-004) so the red-first mandate is not satisfied by regressing them.

## Decision 5 — Review-cycle write-side kind-flip

**Decision**: Flip `review/cycle.py` write-side default off `WORK_PACKAGE_TASK` (`:71/76`); migrate `resolve_review_verdict_facts` (**`tasks_verdict_persistence.py:404`**, not in `cycle.py` — brief was loose) and re-verify `test_analysis_report_rehome`.

## Supply-Chain & Adversarial Evidence

- **Dependencies**: none added/upgraded/removed → registry/freshness/lifecycle/Node-LTS checks N/A by inspection (per `051-supply-chain-install-safety`), not silently skipped.
- **Adversarial evidence**: the post-plan squad IS the challenge pass. Contested finding dispositions:
  - "Clone-re-anchor is the root cause" → **CHANGED** (empirically refuted; reframed to invoking-location, C-005).
  - "Fix = checkout-local redirect" → **CHANGED** (→ #3128 fail-closed refusal, C-003).
  - "#3449 in scope" → **CHANGED** (dropped; already correct).
  - "#3051 is deliberate, drop it" → **RECONCILED** (keep #2320 target + add identity awareness).
  - C-001/C-002 already-fixed scoping → **ACCEPTED** (verified true; green sentinels added).
  No contested finding was silently dropped.

## Confirmed anchor table (for tasks)

| Concern | Anchor (verified) | FR |
|--------|-------------------|-----|
| get_main_repo_root primitive | `core/paths.py:483-493` (~130 callers) | FR-001 |
| identity guard home | NEW `core/checkout_identity.py` | FR-001 |
| must-not-flip anchors | `paths.py` get_feature_target_branch/resolve_merge_target_branch; `mission_runtime/resolution.py` | FR-008 |
| intake identity check | `cli/commands/intake.py:57-62/95-96/236-237` | FR-002 |
| tool-surfaces --fix | `_command_surface_doctor.py:755-773/776-812` + `tool_surface/repair.py` | FR-003 |
| mission-state | `_mission_state_doctor.py` + `migration/mission_state.py:504-535` (#2320 docstring) | FR-004/009 |
| backfill cutover guard | `migration/runtime_state_cutover.py` verify_backfill; `backfill_runtime_state.py:1438-1470` | FR-005 |
| setup-plan branch match | `agent/mission_setup_plan.py:914/934`; `mission_branch_context.py:99` | FR-006 |
| find_repo_root boundary | `task_utils/support.py:45,63-72`; `paths.py:254-265` vs rule 1 `:428-430` | FR-007 |
| emit --review-result-json | `cli/commands/agent/status.py:223-264/274/317-332` | FR-010/012 |
| parser + gate | `orchestrator_api/commands.py:1257/1281/1297/1399/1413` | FR-011/013 |
| shape registry | `audit/shape_registry.py:90-111` (row), `:53` (coord keys) | FR-014/016 |
| review-cycle kind | `review/cycle.py:71/76/179-197`; facts `tasks_verdict_persistence.py:404` | FR-017 |

## Existing tests: extend vs invert (squad-flagged)

- **INVERT/preserve carefully** (currently assert the re-anchor as correct — do NOT naively break): `tests/contract/test_canonical_root_when_in_worktree.py` (asserts emit-from-worktree → canonical/primary log, calls worktree-local "stale"), `tests/unit/workspace/test_root_resolver.py` (worktree → canonical). The fix adds identity *awareness*; it must not regress these deliberate-centralization contracts. Characterization tests (FR-008) pin them.
- **Extend**: `tests/audit/test_shape_registry_writer_parity.py` (add the NEW status_event_row-scoped test alongside — do not repurpose), `tests/integration/migration/test_audit_primary_anchor.py`, `tests/integration/test_sc008_topology_resolution.py`, `tests/coordination/test_verdict_dir_co_resolution.py`.
