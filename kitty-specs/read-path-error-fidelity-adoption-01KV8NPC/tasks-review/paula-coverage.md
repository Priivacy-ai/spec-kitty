# Paula Patterns — Adversarial Coverage Review (post-tasks)

**Mission:** `read-path-error-fidelity-adoption-01KV8NPC`
**Reviewer:** paula-patterns (profile-loaded; architecture-scout lens — coverage + missed paths + anti-laziness)
**HEAD reviewed:** `6fee06d33` (branch `feat/read-path-error-fidelity`)
**Scope:** 9 WP prompts + tasks.md + spec.md + plan.md + call-site-inventory + debbie-reverify-missed + synthesis.
**Method:** every FR mapped to a WP and re-checked subtask-by-subtask; every C1–C17 + M1–M6 traced to a WP or a conscious deferral; the seven disease patterns re-grepped against `src/` on HEAD and each hit reconciled.

---

## Verdict (tight)

- **One uncovered surface: M5** (`decision.py:415-425`, `cmd_verify`) — debbie dispositioned it **FOLD → IC-B/WP04**, but **WP04 does not cover it**. WP04 fixes `cmd_open`'s path and asserts "verify still works", but never touches the rider-added primary-only `load_meta` pre-read (`:421`) NOR the second **uncaught** `resolve_mission_read_path` raise at `:425`. This is a **SHOULD-FIX** (the recurring-shape blind spot the operator asked me to hunt).
- **No FR is dropped.** All 12 FRs map to a WP and each WP's subtasks deliver the FR's actual requirement (FR-006 is consciously narrowed by D-5, recorded; FR-011 is cross-cutting/verification-by-deletion, recorded).
- **M4** (`workflow.py:2030-2054`, `_find_first_for_review_wp` parent-walk re-deriver) — debbie dispositioned **FOLD → IC-E/WP05**, but **WP05 does not cover it** either. Lower blast radius than M5 (review-mode helper, not operator-facing fidelity), but it is a **SHOULD-FIX** drop against debbie's own disposition.
- **Unowned disease-pattern hits: 1 hard (M5/`decision.py:425` uncaught `resolve_mission_read_path`) + 1 soft (M4 re-deriver) + 1 latent shape (`agent/tasks.py:4047` `resolve_mid8(..., mission_id=None)` — a 4th instance of the empty-seed shape, not in any inventory).** Everything else is owned or in debbie's verified benign-by-design catalog.

---

## 1. FR → WP coverage matrix

| FR | Requirement (one-line) | WP | Subtasks | Fully covered? | Note |
|----|------------------------|----|----------|----------------|------|
| FR-001 | Typed-error pass-through (no `MISSION_NOT_FOUND` collapse) | WP02 (+WP09) | T008–T012, T038 / T039–T040 | **YES** | next family + M1 + orchestrator. See NIT-1 (second raise `:3134`). |
| FR-002 | `next` typed diagnostics (code + checked paths + read-path remediation) | WP02 | T007, T011 | **YES** | emitter mirrors QueryModeValidationError; folds #1911. |
| FR-003 | `decision open` single authority (delete escape-walk) | WP04 | T020–T023 | **PARTIAL** | `cmd_open` covered; **`cmd_verify` (C7/M5) under-covered** — see BLOCKER-adjacent SHOULD-FIX-1. |
| FR-004 | `setup-plan` exact-one auto-select; >1 structured error | WP03 | T013–T014 | **YES** | auto-select in `setup_plan` only, not the shared helper. Good boundary call. |
| FR-005 | `is_committed` primary-target-branch leg | WP03 | T015–T016 | **YES** | topology-true coord-worktree-with-mission-dir fixture mandated (NFR-002 trap called out). |
| FR-006 | `_commit_to_branch` no silent swallow / report hash | WP03 | T017–T018 | **YES (narrowed by D-5)** | hard-failure swallow already fixed on HEAD; residual = hash + no-op classification. Conscious, recorded. |
| FR-007 | Submodule root unification (`resolve_canonical_root`) | WP06 | T029–T031 | **YES** | mirrors `locate_project_root`; equivalence test over 3 topologies. Strong. |
| FR-008 | `agent action implement` single resolution path (#1832) | WP05 | T024–T025 | **YES** | consume claim's context; verification-by-deletion of the re-resolution. |
| FR-009 | ExecutionContext factory + freeze + build-invariant | WP01 | T001–T006, T037 | **YES** | D-2 supersession (target_branch, not branch_name) correctly carried into the prompt; the single most likely contract mistake is explicitly guard-railed. |
| FR-010 | Charter status side-effect-free + JSON-safe | WP07 | T032–T034 | **YES** | scoped to the #1914 no-op slice; dead `# noqa: BLE001` removal mandated. |
| FR-011 | Single-authority adoption across the named set | WP05/WP09 (+ cross-cut) | T025, T042 + verification-by-deletion across WP02/03/04/05 | **YES** | cross-cutting; satisfied by deletion. M5 gap weakens it on the `decision verify` leg (SHOULD-FIX-1). |
| FR-012 | #1827 re-test-first (verified-already-fixed) | WP08 | T035–T036 | **YES** | test-only; falsification guard mandated. D-3 honors live-evidence discipline. |

**No FR is unmapped or silently dropped.** The only partial is FR-003/FR-011 on the `decision verify` leg (M5).

---

## 2. Call-site C1–C17 → WP coverage

| C# | Surface | Disposition | Owned by | Covered? |
|----|---------|-------------|----------|----------|
| C1 | `runtime_bridge.py:3128` query_current_state flatten | bypass-to-fix | WP02 (T008) | YES |
| C2 | `runtime_bridge.py:3265` answer_decision flatten | bypass-to-fix | WP02 (T009) | YES |
| C3 | `next_cmd.py:355` _find_mission_slug flatten | bypass-to-fix | WP02 (T010) | YES |
| C4 | `next_cmd.py:374-408` emitter sink | fragment-adopt | WP02 (T011) | YES |
| C5 | `agent/context.py:135/156` (reference) | route-through (no change) | — | N/A (the GOOD citizen) |
| C6 | `decision.py:86-109` cmd_open escape-walk | bypass-to-fix | WP04 (T021-T022) | YES |
| C7 | `decision.py:408/425` cmd_verify shared helper | compose/parse | WP04 (T023) | **PARTIAL — see SHOULD-FIX-1** |
| C8 | `setup-plan` hard `--mission` | bypass-to-fix | WP03 (T014) | YES |
| C9 | `is_committed` surface-blind | bypass-to-fix | WP03 (T016) | YES |
| C10 | `is_committed` caller (setup-plan) | fragment-adopt | WP03 (T016) | YES |
| C11 | `_commit_to_branch` swallow | bypass-to-fix | WP03 (T018) | YES (narrowed) |
| C12 | `resolve_canonical_root` submodule | bypass-to-fix | WP06 (T030) | YES |
| C13 | `locate_project_root` (correct sibling) | already correct | — | N/A (must AGREE; WP06 T031) |
| C14 | `agent action implement` re-resolve | fragment-adopt | WP05 (T025) | YES |
| C15 | `finalize-tasks` fail-closed pre-read | fragment-adopt | WP03 (T019) | YES |
| C16 | `ExecutionContext` mutable | bypass-to-fix | WP01 (T003-T005) | YES |
| C17 | charter status side-effects | bypass-to-fix | WP07 (T033) | YES |

**Every C1–C17 is owned or is a conscious reference/no-change (C5, C13).** No unowned C-site.

---

## 3. Missed-surface M1–M6 → WP coverage

| M# | Surface | file:line (HEAD verified) | Debbie disposition | Actually in a WP? | Status |
|----|---------|---------------------------|--------------------|--------------------|--------|
| M1 | `context mission-resolve` flatten → FeatureNotFoundError | **`context/resolver.py:164`** | fold → IC-02 | **YES — WP02 owns `resolver.py`, T038 cites `:164`** | COVERED (see NIT-2 on the doc cite) |
| M2 | orchestrator-api flatten ×8 endpoints | `orchestrator_api/commands.py:263-266` + 8 sites | fold → IC-02 | YES — WP09 T040 | COVERED |
| M3 | orchestrator empty-mid8 → fail-closed suppressed | `orchestrator_api/commands.py:261` | fold (read-path SAFETY) | YES — WP09 T042 | COVERED |
| M4 | `_find_first_for_review_wp` parent-walk re-deriver | `workflow.py:2030-2054` | **FOLD → IC-E (WP05)** | **NO — WP05 only covers C14 `:1341/:1377-1381` + #1993** | **DROPPED → SHOULD-FIX-2** |
| M5 | `cmd_verify` primary-only pre-read + uncaught `:425` | `decision.py:415-425` | **FOLD → IC-B (WP04)** | **NO — WP04 T023 only "confirms verify unaffected"; does not delete the `:421` pre-read nor wrap the `:425` raise** | **DROPPED → SHOULD-FIX-1** |
| M6 | `agent/context.py` primary-only pre-read | `agent/context.py:72-93` | DOCUMENT, no WP (benign) | N/A — conscious doc-only | CORRECTLY DEFERRED |

---

## 4. Recurring-shape audit (operator's lens #3 — the load-bearing one)

Debbie flagged a recurring naming-rider shape: **3 consumers** do a primary-only `load_meta` pre-read seeding `mission_id` before the resolver, which can suppress the coord-aware fail-closed guard. I re-grepped `src/` for `load_meta(...)` feeding `resolve_mid8` in command consumers. **Exactly three** sites exist, matching debbie:

| Site | file:line | Debbie ID | Owned? |
|------|-----------|-----------|--------|
| `orchestrator_api/commands.py:261` | `resolve_mid8(slug, mission_id=None)` after no real-id resolution | **M3** | **WP09 (T042)** ✅ |
| `decision.py:421` | `_meta = load_meta(_primary_dir)` → `:424` resolve_mid8 → `:425` uncaught read-path | **M5** | **WP04 — NOT covered** ❌ |
| `agent/context.py:73` | `_meta = load_meta(_primary_dir)` → `:82` resolve_mid8 | **M6** | benign, doc-only ✅ |

**So of the three recurring-shape consumers: M3 owned, M6 consciously deferred, M5 DROPPED.** This is precisely the blind spot the operator pointed at. M5 is NOT benign like M6 — debbie's own re-verify says M5 is "**Reachable** (uncaught raise on coord-deleted, like #8)": `decision verify` on a coord-deleted topology raises an **uncaught** `StatusReadPathNotFound`/`ActionContextError` traceback at `:425` exactly as `cmd_open` did before WP04. WP04 deletes the crash on the `open` path but leaves the **same crash class live on the `verify` path**, even though `cmd_verify` is in WP04's owned file and debbie explicitly folded M5 there.

**Bonus latent instance (NOT in any inventory):** `agent/tasks.py:4047` does `resolve_mid8(mission_slug, mission_id=None)` — a **4th** empty-mid8 seed of the same shape as M3. It is not the `load_meta` pre-read variant and was not flagged by debbie, but it is the identical empty-identity-seed pattern that M3 calls a read-path-safety risk. Flagging as NIT-3 (verify-or-document, not necessarily in-scope).

---

## 5. Disease-pattern grep reconciliation (every hit owned or consciously out-of-scope)

`except ActionContextError` (8 hits):
- `runtime_bridge.py:3128`, `:3265` → WP02 ✅
- `context/resolver.py:164` → WP02 (M1) ✅
- `agent/context.py:156` → C5 reference (correct, no change) ✅
- `implement.py:560`, `agent/mission.py:725` → debbie benign-by-design catalog (conservative `return None` placement helpers) ✅
- `agent/workflow.py:975` → benign (target-branch resolve, routes correctly per C14 §3) ✅
- `mission_runtime/resolution.py:262` → the resolver itself (source of fidelity) ✅

`except StatusReadPathNotFound` (13 hits):
- `next_cmd.py:355` → WP02 ✅; `orchestrator_api/commands.py:265` → WP09 ✅
- `agent/context.py:88` → correct translation (M6 benign) ✅
- `agent/mission.py:1266` → routes the typed code (in WP03's owned file; canon path) ✅
- `status/aggregate.py:339/470`, `coordination/status_transition.py:221`, `mission_type.py:443`, `merge.py:1396`, `resolution.py:129/430/664` → debbie benign-by-design catalog (translate-and-preserve or resolver source) ✅

`resolve_canonical_root` consumers: `assert_initialized.py:94` (the live guard — fixed transitively by WP06), `root_resolver.py:95`, and the **write-side** `status/emit.py:420` / `work_package_lifecycle.py:85` / `coordination/status_transition.py:155` → these are the **#1716 / Mission B write-side** surfaces, **consciously DEFERRED** (D-1, synthesis §5). ✅ No read-path consumer is unowned.

`is_committed` consumer: only `agent/mission.py:2116` → WP03 ✅.

`MISSION_NOT_FOUND` raises: all in WP02/WP09 owned files or in distinct subsystems (`decisions/`, `mission.py`, `mission_v1`, `retrospect.py`, `doctor.py`) that are **not** the resolver-flatten disease (they are genuine not-found in other bounded contexts). ✅

`.parent.parent` / parent-walk: `workflow.py:798/825` (feedback_root — orthogonal), and **`workflow.py:2047-2054`** = **M4 re-deriver (DROPPED, SHOULD-FIX-2)**.

---

## Findings

### SHOULD-FIX-1 (recurring-shape blind spot — the priority finding)
**M5 / `decision.py:415-425` (`cmd_verify`) is dropped from WP04 despite debbie folding it into IC-B.**
WP04 T023 only says "confirm `cmd_verify` unaffected" and "exercise it after the helper change". But `cmd_verify` does NOT share the escape-walk fix — it has its **own** rider-added primary-only `load_meta(_primary_dir)` pre-read (`decision.py:421`) seeding `resolve_mid8` (`:424`) and its **own uncaught** `resolve_mission_read_path` at `:425`. On a coord-deleted/coord-only topology this raises an uncaught traceback — the **identical #8 crash class** WP04 is deleting on `cmd_open`. Leaving it makes FR-003/FR-011 "single authority" half-true: `open` is structured, `verify` still crashes raw, and the primary-only pre-read still suppresses the coord-aware guard (the M3/M5/M6 shape).
**Fix:** add a WP04 subtask to (a) drop the `:421` primary-only pre-read (or route identity through the WP01 factory boundary like M3/WP09), and (b) wrap `:425` in a structured typed-error translation mirroring `cmd_open`'s T022. Add a coord-topology `decision verify` test (Case D) that fails on HEAD with the uncaught traceback.

### SHOULD-FIX-2 (disposition drop)
**M4 / `workflow.py:2030-2054` (`_find_first_for_review_wp`) is dropped from WP05 despite debbie folding it into IC-E.**
WP05 covers only C14 (`:1341/:1377-1381`) and #1993; the parent-walk re-deriver at `:2047-2054` (`candidate_feature_dir_for_mission` composed by hand against a manual `current`-walk) is untouched. Lower blast radius (review-mode helper, not operator-facing fidelity) — but it is a re-derivation bypass debbie explicitly assigned to IC-E, and WP05 is its rightful owner (`workflow.py` is owned by WP05). Leaving it means FR-011 "no per-command second authority" is not fully true on the review surface.
**Fix:** add a WP05 subtask to route `_find_first_for_review_wp` through the canonical surface (consume the resolver's feature_dir instead of the manual parent-walk), or — if it is genuinely a fallback that must stay — record it as a **conscious deferral** in tasks.md so the disposition drift is intentional, not silent.

### NIT-1 (second raise site not addressed)
`runtime_bridge.py:3134` is a **second** `MissionNotFoundError(mission_slug)` raise inside `query_current_state` (the "resolved-but-not-on-disk" branch), distinct from the `:3130` flatten WP02 T008 targets. It is arguably a correct `MISSION_NOT_FOUND` (path resolved but absent), so likely fine — but WP02 T008 only cites `:3128-3130`. The implementer should consciously decide whether `:3134` stays `MISSION_NOT_FOUND` (defensible) and the prompt should say so, so it is not edited by accident or missed by a reviewer expecting a single raise.

### NIT-2 (doc cite drift — M1 file)
plan.md (IC-02, line ~120), tasks.md (T038, line 119), and the synthesis (§6 table) all cite M1 as **`context/mission_resolver.py:164`**. The actual disease (the `except ActionContextError` → `FeatureNotFoundError("…Check that the mission slug is correct.")` flatten debbie live-confirmed) is in **`context/resolver.py:164`** — a *different file* in the same package. **WP02's `owned_files` and T038 body correctly target `resolver.py`**, so implementation is unaffected — but the three prose cites are wrong and will mislead a reviewer/future agent. `mission_resolver.py:163` does call `resolve_mid8` but does NOT contain the flatten. Fix the three doc cites to `resolver.py:164`.

### NIT-3 (latent 4th empty-seed instance)
`agent/tasks.py:4047` `resolve_mid8(mission_slug, mission_id=None)` is a 4th instance of the empty-mid8 seed pattern M3 calls a read-path-safety risk. Not flagged by debbie, not in any inventory. Likely benign (tasks-finalize context) but should be verified-or-documented so the "callers MUST NOT seed empty identity" boundary contract (D-6) is enforced consistently, not just at M3.

### NIT-4 (pre-existing noqa interaction)
`query_current_state` (WP02's edit target) carries `# noqa: C901` at `runtime_bridge.py:3103`. WP02's NFR-004 mandates "no suppressions" and complexity ≤15. The prompt should note the implementer must either keep the function ≤15 after editing (and remove the pre-existing noqa) or consciously leave the inherited noqa — otherwise the boy-scout/no-suppression rule is ambiguous on a function the WP already touches.

---

## Unowned disease-pattern hit count (operator's ask)

**3 unowned hits of substance:**
1. `decision.py:425` uncaught `resolve_mission_read_path` (M5) — **hard, read-path crash, SHOULD-FIX-1.**
2. `workflow.py:2047-2054` parent-walk re-deriver (M4) — **soft, SHOULD-FIX-2.**
3. `agent/tasks.py:4047` empty-mid8 seed — **latent, NIT-3 (verify-or-document).**

Everything else (C1–C17, M1/M2/M3/M6, all 8 `except ActionContextError`, all 13 `except StatusReadPathNotFound`, all `resolve_canonical_root`/`is_committed` consumers) is **owned by a WP or in debbie's verified benign-by-design catalog or consciously deferred to Mission B / #1716**.
