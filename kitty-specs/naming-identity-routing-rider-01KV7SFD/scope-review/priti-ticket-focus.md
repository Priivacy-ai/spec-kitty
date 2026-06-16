# Scope Review — Planner Priti (adversarial, ticket-focus lens)

**Mission:** `naming-identity-routing-rider-01KV7SFD` · **Reviewer:** planner-priti · **Date:** 2026-06-16
**Verdict (one line):** **MIS-SCOPED.** The rider claims 6 tickets; 1 is already CLOSED and re-counted
as a phantom "tail", 1 (#1993) is mapped to a refactor the ticket does not ask for, 1 (#1900) is gated
on deferred work this mission excludes, and the only fully-sound items (#1888, #1971-tail) are
verify-and-close. Net: at most **2 of 6** are genuinely and correctly addressed.

Tracker queried read-only (`unset GITHUB_TOKEN; gh issue view`). No mutations performed.

---

## Per-ticket coverage truth-check

| Ticket | Real ask (verbatim-grounded) | State | Plan coverage | Verdict | Residual / defect |
|--------|------------------------------|-------|---------------|---------|-------------------|
| **#2000** | Route **3 named** `<slug>-<mid8>` **compose** sites — `core/mission_creation.py:321`, `core/worktree.py:367`, `core/worktree.py:370` — through `mission_dir_name()`/`worktree_dir_name()`/`worktree_path()` and **shrink the ratchet allow-list**. | OPEN | IC-04 routes "~2 static composes" but **names the WRONG files** (`lanes/recovery.py`, `core/vcs/detection.py`). The 3 real #2000 sites are **never mentioned** in spec/plan/research. | **PARTIAL / MIS-TARGETED** | The 3 actual allow-listed sites (verified live at those lines, and present in `_ALLOWED_SITES` of `test_no_worktree_name_guess.py:113-115`) are not in scope. Plan under-counts AND mis-files. These sites already call `mid8()` — the defect is the **compose**, needing `mission_dir_name`/`worktree_dir_name`, which the plan's "mid8 route" framing (IC-02) doesn't cover and IC-04 doesn't name. |
| **#1971** (tail) | Consolidate 3-way `locate_project_root` split-brain; redirect the `project_resolver`/`__init__` callers to `paths.locate_project_root`, **delete duplicate logic**. The body's *primary* ask is a real consolidation (the simple-walk variant silently ignores `SPECIFY_REPO_ROOT`/worktree). | OPEN | Research Decision 3 reclassifies it as "already a single-authority delegation chain → verify-and-close + regression test". | **PARTIAL (defensible)** | The ticket asks to **delete the duplicate logic / one authority**; the plan keeps all three (intentional shims) and only adds a convergence test. This is a reasonable disposition IF the shims are genuinely delegating — but the ticket's "silently ignore SPECIFY_REPO_ROOT" concern (project_resolver = simple walk) must be **proven false** by the test, not assumed. Disposition is "verify-and-close," but the ticket body asserts a *behavior split-brain*; the verdict must resolve that claim, not sidestep it. |
| **#1993** | Extract `resolve_lanes_dir(repo_root, mission_slug)` — the **coord-aware topology** `_lanes_feature_dir` resolution inside `implement()` (meta.json-existence fallback coord→primary) — so the 12-mock `TestImplementCoordTopologyLanesJson` becomes a zero-mock `tmp_path` test. | OPEN | IC-03 / Research Decision 4 describe a **different** seam: `resolve_lanes_dir(feature_dir)` = pure `feature_dir / "lanes.json"` join, "adopted across ~10 inline read sites." | **MISSING (mis-mapped, OVER-CLAIM)** | The ~10 "inline `feature_dir / "lanes.json"`" sites **do not exist** — every consumer already calls `require_lanes_json(feature_dir)` (path composition is already centralized in `lanes/persistence.py:43,78`). The plan invented a non-problem. The ticket's actual pain (12-mock topology fallback in `implement.py:974`) is **untouched**. Shipping IC-03 as planned would NOT close #1993 and would add a redundant wrapper. |
| **#1888** | finalize-tasks ownership validation accepts non-glob `owned_files` paths that don't exist (pattern-validated, never existence-checked). Warn/fail on zero-match literal paths. | OPEN (P1, bug) | FR-008 / IC-04: "verify current behavior correct + add missing regression test + close — no new build." | **MISSING (OVER-CLAIM)** | The ticket is a **confirmed bug** ("passed with no warning", evidence in mission 131 log item 17). `ownership/validation.py` confirms only glob-overlap/prefix checks — **no existence check exists**. "Verify-and-close, no new build" is the **wrong disposition**: this requires a real code change (add the literal-path existence check + warning). The planner dodged actual P1 work by mislabeling it verify-and-close. |
| **#1900** | Drain the **topology-ratchet** (`test_topology_resolution_boundary.py`) C-002 allow-list — migrate `coordination/status_transition.py` predicates + `merge.py:1114` + `preflight.py:86` — **only AFTER coordination-merge-stabilization lands**. Carries `triage:needs-revision`. | OPEN | FR-007 / IC-04: "route the static composes flagged by #2000, #1899-tail, **and #1900**." | **MISSING (severance fiction)** | (a) #1900 targets a **DIFFERENT ratchet** (`test_topology_resolution_boundary.py`), never mentioned in the plan. (b) Two of its three sites are **already migrated** (`preflight.py:97` uses `mission_branch_name_required`; `merge.py:1235` comment confirms FR-004 resolver). (c) The only remaining site (`status_transition.py`) is **write-side/coordination** — the exact zone C-005 defers (#1716). (d) The ticket is **explicitly gated** on coordination-merge-stabilization landing first. The plan cannot drain it without the deferred work. **Folding #1900 into this rider contradicts C-005.** |
| **#1899-tail** | — | **CLOSED (COMPLETED 2026-06-16)** | The plan repeatedly addresses "#1899-tail" as a live static-compose item (FR-007, IC-04, spec §Tracker). | **PHANTOM / DOUBLE-COUNT** | #1899 was closed by PR #2001 (merge `fcf9be595`, cli 3.2.0). Its closing comment states the residual is **"tracked separately as #2000."** So "#1899-tail" **is** #2000 — there is no independent tail. The mission claims 6 tickets but #1899-tail and #2000 are the **same residual counted twice**. |

---

## Over-claim summary

- **#1899-tail is a phantom.** Already CLOSED; its residual = #2000. Double-counted as a 6th ticket.
- **#1993 is mis-mapped.** Plan targets a non-existent "~10 inline lanes.json joins"; the real 12-mock
  topology fallback in `implement()` is untouched. As planned, IC-03 does NOT close #1993.
- **#1888 disposition is wrong.** A confirmed P1 bug labeled "verify-and-close, no new build." There is
  no existence check in `ownership/validation.py`; closing it needs a real fix, not a test.
- **#2000 mis-targeted.** Plan names the wrong files; the 3 actual allow-listed compose sites are absent
  from spec/plan/research.

## Deferred-set severability check (#1832 / #1716 / #1827 / #1619-builder / #1891)

- **#1900 secretly REQUIRES deferred work.** #1900's remaining live site is `coordination/status_transition.py`
  (write-side topology), and the ticket is gated on **coordination-merge-stabilization** (the #1716 coord
  topology zone) landing. The plan lists #1900 as in-scope (FR-007) while C-005 defers #1716. **The
  severance is a fiction for #1900** — you cannot drain that allow-list entry without the deferred coord
  work. Either drop #1900 from the addressed set (correct), or pull #1716 in (forbidden by C-005). The plan
  does neither; it claims #1900 while excluding its prerequisite.
- **#1832 / #1827 / #1619-builder / #1891:** no in-scope routing site requires these. Severance holds.
  (The IC-02 route-sites are read-path mid8 derivations independent of builder-hardening; #1827 merge-baseline
  and #1891 `--json` are orthogonal.)

## Foldable tickets the plan may have missed

- Tracker sweep of the naming/identity/mid8/lanes/worktree/topology space (open issues) found **no additional
  duplicate of #2000 or #1993** that should fold. #1878 (umbrella coord strangler), #1716, #1887, #1873,
  #1907 are correctly write-side/coord or tooling — **out of scope per C-005**, not missed folds.
- **Not a missed fold, but a correction:** #1899 should be moved from "addressed" to "already closed
  (verified)" in the issue-matrix; #2000 absorbs its residual.

## Bottom line per ticket

- **FULLY closed by scope:** none cleanly. (#1971-tail is the closest — a defensible verify-and-close — but
  only if the test actually disproves the SPECIFY_REPO_ROOT split-brain the ticket asserts.)
- **PARTIAL:** #2000 (right intent, wrong files/under-counted), #1971-tail (verify vs. delete tension).
- **MISSING / mis-disposed:** #1993 (mapped to a non-problem), #1888 (P1 bug mislabeled verify-and-close),
  #1900 (wrong ratchet + gated on deferred #1716 + mostly already done).
- **PHANTOM:** #1899-tail (closed; = #2000).
