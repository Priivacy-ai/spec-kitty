# E2E Execution Findings — execution-context-unification-01KTPKST

**Purpose:** running trace of split-brain / resolver-inconsistency issues hit while executing THIS
mission end-to-end (specify → plan → tasks → analyze → implement → review → merge). Each entry is a
live dogfood instance of the class this mission drains. At closeout, this doubles as a **"did we fix
it?" acceptance checklist** — every OPEN finding must be either fixed (with the FR/IC that fixed it)
or explicitly deferred with rationale.

**Status legend:** 🔴 open · 🟡 worked-around · 🟢 fixed (cite FR/IC + commit) · ⚪ deferred

---

## F-001 — `decision open --mission <mid8>` resolves mid8 literally as slug 🔴

- **When:** plan step (2026-06-09), opening plan decisions via the Decision Moment Protocol.
- **Command:** `spec-kitty agent decision open --mission 01KTPKST --flow plan ...`
- **Symptom:** `ActionContextError: Mission directory not found: kitty-specs/01KTPKST. Check that '01KTPKST' is the correct mission slug.`
- **Root cause:** the `decision` command's `_resolve_repo_root_and_slug` → `resolve_feature_dir_for_mission`
  → `mission_runtime/resolution.py:_resolve_mission_slug` calls `resolve_mission_read_path(repo_root, slug, mid8)`
  but the mid8 (`01KTPKST`) is passed through as the *slug* and joined to `kitty-specs/` directly — no
  mid8→slug disambiguation on this path. Other commands (setup-plan, context resolve) accept `--mission 01KTPKST` fine.
- **Class:** read-path resolver inconsistency — the SAME selector resolves differently across surfaces.
  This is exactly the Cluster A divergence FR-002/FR-012 target (one resolution path; no per-surface
  re-derivation; no silent-or-wrong fallback).
- **Workaround:** 🟡 use the full `mission_slug` (`execution-context-unification-01KTPKST`) for `decision` commands.
- **Maps to:** FR-002 (route all surfaces through one resolver), FR-012 (`_find_feature_directory` /
  selector behaviour), IC-03 (read-path consolidation). C-CTX-1 / C-CTX-4 contracts.
- **Acceptance check (closeout):** `spec-kitty agent decision open --mission 01KTPKST ...` succeeds
  (mid8 resolves identically to the full slug), OR raises a *structured* MISSION_AMBIGUOUS_SELECTOR /
  unresolved error — never a wrong-but-plausible `kitty-specs/<mid8>` path.
- **Status:** 🔴 open (folded into IC-03 repro set).

## F-002 — `safe-commit` rejects directory args; requires explicit file paths 🟡

- **When:** plan step, committing Phase-1 artifacts (`contracts/`, `decisions/` passed as dirs).
- **Symptom:** "staging area contains unexpected paths" — files staged under the dir args were treated
  as not matching the requested paths; backstop aborted (cannot --force).
- **Root cause:** safe-commit path-match compares staged file paths against the literal requested paths;
  a directory argument does not match its contained files.
- **Class:** ergonomics / path-resolution mismatch (adjacent to the placement-resolution theme, FR-004).
  Not clearly the split-brain class, but logged here as an e2e friction point.
- **Workaround:** 🟡 enumerate explicit file paths (not directories) to `safe-commit`.
- **Maps to:** not a current FR. Candidate upstream gap if it recurs (file a ticket per the
  "missing/awkward CLI behaviour = log a gap" discipline).
- **Status:** 🟡 worked-around (monitor; file gap if it recurs in implement/merge).

## F-003 — `context resolve --action tasks` returns `current_branch: None` / `branch_matches_target: None` 🔴

- **When:** tasks step (2026-06-09), resolving context before WP generation.
- **Command:** `spec-kitty agent context resolve --action tasks --mission execution-context-unification-01KTPKST --json`
- **Symptom:** `current_branch: None`, `branch_matches_target: None` — yet `setup-plan` for the same
  mission minutes earlier returned `current_branch: fixups/code-engine-stabilization`,
  `branch_matches_target: true`, and `git branch --show-current` confirms the branch.
- **Class:** branch/ref derivation inconsistency — the SAME branch fact resolves differently across
  command surfaces (`context resolve` vs `setup-plan`). Directly the FR-012 `target_branch` /
  branch-derivation single-source concern and FR-001 BranchRefFragment.
- **Workaround:** 🟡 trust `git branch --show-current` + `setup-plan` payload; proceed (branch confirmed correct).
- **Maps to:** FR-001 (BranchRefFragment), FR-012 (single branch/ref derivation), FR-002 (one resolver).
  C-CTX-2 (CWD invariance) / C-CTX-3 (single derivation) contracts.
- **Acceptance check (closeout):** `context resolve --action tasks` returns the same `current_branch`
  and `branch_matches_target` as `setup-plan` for the same mission/CWD (parity across surfaces).
- **Status:** 🔴 open (folded into IC-02/IC-03 repro set).

## F-004 — `check-prerequisites --include-tasks` returns `feature_dir: None` (mission found, dir null) 🔴

- **When:** analyze step (2026-06-09), `check-prerequisites` before cross-artifact analysis.
- **Command:** `spec-kitty agent mission check-prerequisites --json --include-tasks --mission execution-context-unification-01KTPKST`
- **Symptom:** `feature_dir: None` even though `available_docs: ['plan.md','spec.md','tasks.md']` — i.e. the
  mission WAS located (docs enumerated) yet the resolved `feature_dir` came back null.
- **Class:** read-path resolver inconsistency (same family as F-001/F-003) — a surface enumerates the
  mission's docs but returns a null directory, so a caller threading `feature_dir` downstream would break.
- **Workaround:** 🟡 derive feature_dir from the known mission path; proceed.
- **Maps to:** FR-002 (one resolver), FR-012 (single derivation), IC-03. C-CTX-1.
- **Acceptance check (closeout):** `check-prerequisites` returns a non-null `feature_dir` whenever it can
  enumerate `available_docs` for the mission.
- **Status:** 🔴 open (folded into IC-03 repro set).

## F-005 — `record-analysis` dirty-tree guard fires correctly on flattened topology ✅ (premise confirmation, not a bug)

- **When:** analyze step, persisting the analysis report.
- **Observation:** `record-analysis` returned `DIRTY_WORKTREE` (legitimate pre-existing uncommitted
  changes) — **NOT** the #1814 coord-residue deadlock that paused mission 01KTNWFC. On the flattened
  single-branch topology the guard behaved as designed: it asked for a clean tree, no coord/primary split.
- **Significance:** this is positive evidence for the mission premise (C-001 flatten de-risks #1814). The
  #1814 deadlock is coord-residue-specific; flattening removes the residue surface.
- **Maps to:** SC-2, FR-004/FR-009 (the real fix lands in WP06 so it holds for coord topology too).
- **Status:** 🟢 premise confirmed (flattened). WP06 must still fix the coord-topology case (#1814).

## F-006 — `record-analysis` verdict counts severity keywords by substring, not structured findings 🔴

- **When:** analyze step (2026-06-09), persisting the analysis report.
- **Symptom:** `record-analysis` returned `verdict: blocked`, `issue_counts {critical:4, high:3, medium:2, low:7}`
  for a report whose structured findings table had **0 critical / 0 high** (1 medium-info + 5 low). The
  counts exactly equal the number of uppercase `CRITICAL`/`HIGH`/`MEDIUM`/`LOW` **substrings** in the report
  text — including prose like "no CRITICAL, no HIGH" and the metrics line "CRITICAL 0 · HIGH 0".
- **Root cause:** verdict/issue-count is derived by counting severity keyword occurrences in the report
  body rather than parsing the findings table's severity column. A report that *states it has no critical
  issues* is scored as having critical issues.
- **Class:** analysis-tooling defect (adjacent to the mission's `record-analysis` surface, already in scope
  via #1814). Causes false `blocked` verdicts → spurious implement-gating.
- **Workaround:** 🟡 author the report with severity words ONLY in the findings-table severity column;
  use lowercase / non-keyword phrasing ("no blocking issues", "0 blocking") in prose + metrics.
- **Maps to:** not a current FR — **file an upstream gap** (record-analysis should parse the structured
  findings table, or accept a structured `--findings` input, not substring-count prose). Candidate adjacent
  fold into this mission or a follow-up.
- **Acceptance check (closeout):** a report stating "no blocking issues" with a clean findings table
  records `verdict: clear` (or equivalent), not `blocked`.
- **Status:** 🔴 open (upstream gap to file; worked around for this mission's analysis).

## F-007 — `move-task` write path reads `genesis` from sparse lane worktree (read path reads primary) 🔴

- **When:** implement loop, WP01 (2026-06-09) — moving WP01 `in_progress → for_review`.
- **Symptom:** `move-task WP01 --to for_review` run **from the lane worktree CWD** fails `Illegal transition:
  genesis -> for_review`; the **same command from the primary-checkout CWD** succeeds (`in_progress -> for_review`).
- **Root cause:** lane worktrees sparse-checkout-exclude `kitty-specs/` (status lives on the canonical
  surface). The move-task **write/validation** path re-derives the current lane from the CWD-dependent
  (empty, in-worktree) surface → reads `genesis`; the **read** path correctly traverses to the primary
  authority → reads `in_progress`. Classic coord-vs-primary read/write split (F-001/F-003/F-004 family).
- **Workaround:** 🟡 run status transitions (`move-task`, `mark-status`) from the **primary checkout CWD**,
  not the lane worktree. (Implementer/reviewer subagents must do likewise until WP02 lands.)
- **Maps to:** FR-003/FR-008 (WP02 — fold the move-task write path onto the carried StatusSurfaceFragment);
  the WP01 status xfail flips green when WP02 lands. This is the regression the new dual-CWD ratchet catches.
- **Acceptance check (closeout):** `move-task`/`mark-status` produce identical results from the lane worktree
  and the primary checkout (WP01 parity assertion green).
- **Status:** 🔴 open (WP02 target; dogfooded live during WP01 implementation).

## F-008 — `test_runtime_lifecycle_action_parity` xfail has no owning WP (closeout gap) 🔴

- **When:** WP07 review (2026-06-10).
- **What:** the parity ratchet's `test_runtime_lifecycle_action_parity` (asserts `specify/plan/analyze/status`
  resolve as actions from both CWDs) is `xfail(strict=True)`. WP01's convergence map annotated it "converges in
  WP07", but that is inaccurate — flipping it requires adding `specify/plan/analyze/status` to
  `ActionName`/`ACTION_NAMES` in `src/mission_runtime/resolution.py` (resolver work). WP07 owns only `views.py`;
  **no remaining WP (WP08/WP11) owns `resolution.py`'s ACTION_NAMES**, so this xfail will not flip by itself.
- **Class:** convergence-bookkeeping / scope gap (the ratchet has one assertion no WP delivers).
- **Resolution (closeout):** either (a) a small closeout task extends `ACTION_NAMES` with the planning/analyze/
  status actions + flips the xfail, or (b) file it as a follow-up and correct the misleading "converges in WP07"
  annotation. Decide whether full lifecycle-action parity is in-scope for THIS mission or a follow-up.
- **Status:** 🟢 FIXED (closeout, commit `fb9e1a5` on lane-k) — added `specify/plan/analyze/status` to `ActionName`/`ACTION_NAMES` + the mission-level early-return set in `resolution.py`; removed the xfail. **Parity ratchet now fully green (21 passed, 0 xfailed) — FR-011 complete.**

---

## F-009 — post-merge `spec-kitty review` verdict: fail (4 findings) 🟡 → fan-out

- **When:** closeout, post-merge `spec-kitty review --mode post-merge` (2026-06-10). All 12 WPs `done`;
  WP-lane ✓, review-artifact ✓, issue-matrix (19 rows) ✓. Dead-code scan + BLE001 flagged 4:
  - **`retrospective/writer.py:legacy_record_path`** — only referenced intra-module (writer.py:80/530) + a
    test → genuinely should be **private** (`_legacy_record_path`) or de-exported. **Real minor finding.**
  - **`sync/owner.py:ReapResult`** + **`canonical_executable_scope`** — public API of owner.py consumed by
    tests + internally (reaper return type / singleton-key helper). Likely the dead-code scan's documented
    **"public-API-consumed-only-by-tests" false-positive**; de-export or annotate. **reducer-randy to adjudicate.**
  - **`cli/commands/_auth_doctor.py:236` BLE001** — `except Exception: # noqa: BLE001` with no reason.
    **Pre-existing (commit 38abeebf, #1297) — NOT a mission-touched file**; whole-repo scan artifact, out of mission scope.
- **Disposition:** report at `kitty-specs/execution-context-unification-01KTPKST/mission-review-report.md`.
  These feed the **fan-out deep-dive** (reducer-randy owns dead-code/export hygiene); remediation + the
  `legacy_record_path` privatization land via the aggregation under operator direction.
- **Status:** 🟡 surfaced; deferred to fan-out + operator (1 real privatization, 2 likely-false-positive, 1 pre-existing/out-of-scope).

## Closeout acceptance summary (fill at merge)

| ID | Status | Fixed by (FR/IC + commit) / deferral rationale |
|----|--------|------------------------------------------------|
| F-001 | 🟢 | FIXED — WP04 (`resolve_mission_read_path` canonicalizes mid8/ULID/slug to one dir; regression test) |
| F-002 | 🎫 | worked-around (explicit file paths, not dir args; `--to-branch` over the env-var infer) → **filed #1820** |
| F-003 | 🟢 | FIXED — WP04 (one read-path resolver; CWD-invariant). *Acceptance-wording correction:* the target was `target_branch` single-source (achieved); `context resolve` never carried `current_branch`/`branch_matches_target` keys, so the original "same as setup-plan" wording was inapt — the "None" symptom is gone. |
| F-004 | 🟢 | FIXED — WP04 (`check-prerequisites` resolves a non-null feature_dir via the consolidated primitive) |
| F-005 | 🟢 | premise confirmation (flattened); coord-topology fix shipped in WP06 (debby closeout: coord path genuinely exercised, not flattened-only) |
| F-006 | 🎫 | worked-around (record-analysis verdict substring-counts prose) → **filed #1819 (MEDIUM, recurring operator impact)** |
| F-007 | 🟢 | FIXED — WP02 (`_identity_for_request` consumes the canonical surface; CWD-invariant, no genesis misread) |
| F-008 | 🟢 | FIXED — closeout `fb9e1a5` (lifecycle actions resolvable; parity ratchet fully green) |
| F-009 | 🟢/🎫 | post-merge review: `legacy_record_path` **privatized** (fixed); `ReapResult`/`canonical_executable_scope` = scan false-positives (no action); BLE001 pre-existing #1297 (out of scope) |
| latent-drift | 🎫 | `MissionStatus.load` + `status_transition` not threaded onto carried `StatusSurfaceFragment` (correct today; defensive) → **filed #1821** |

**Net:** 7 fixed (F-001/003/004/005/007/008 + F-009 privatization), 3 follow-up tickets filed (#1819 record-analysis verdict / #1820 safe-commit ergonomics / #1821 fragment-threading), 2 confirmed false-positives, 1 pre-existing out-of-scope.

### Closeout narrative corrections (from the fan-out deep-dive; no code impact)
- **FR-013 — "5 dead symbols" was a stale (pre-#1614) premise.** WP09 deleted **2** genuinely-dead symbols; the other **3** (`StatusReadSource`, `EventLogWriteTarget`, `StatusContractError`) became **live facade internals** and were correctly **de-exported from `__all__`**, not deleted (deleting would break the live contract layer + tests). Do NOT re-delete.
- **NFR-005 — "LOC trends down" is not literally met.** The targeted collapses DID land (parser −120, status_service −23, reaper/lifecycle ≈ −40), but the doc-09 fragment value-objects + read-path consolidation add ~+650, so the squash-merge production diff is **net +1609 LOC**. This is genuine new value-object code, NOT surviving duplication (randy: zero duplicate mechanisms survived). The constraint should read "collapse duplication" (achieved), not "net subtraction".
