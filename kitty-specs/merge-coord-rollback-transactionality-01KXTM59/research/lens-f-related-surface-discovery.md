# Lens F — Related-Surface / Work-Graph Discovery

**Mission:** merge-coord-rollback-transactionality-01KXTM59
**Targets:** #2786 (swallowed coord-`done`-revert → silent split-brain) + #2367 (merge blocked by coord-worktree tool-churn + non-transactional rollback of coord status writes)
**Lens owner:** Planner Priti (read-only, pre-spec). **Date:** 2026-07-18
**Directives applied:** work-decomposition, dependency-mapping, task-sequencing, risk-identification, prioritisation (Eisenhower), Directive 003 (Decision Documentation — each call grounded in evidence below).

---

## 0. Anchor facts (target issues)

| # | State | Priority | Assignee | Core ask |
|---|-------|----------|----------|----------|
| **2786** | OPEN | **P0** (labelled) | stijn-dejongh (HiC) | On `_revert_coord_done_commit` failure, write a **durable reconcile marker** (merge-state field / `doctor`-detectable flag) instead of only `logger.warning`. Optionally raise to abort rollback. Issue type = **Bug**. |
| **2367** | OPEN | **P0** | stijn-dejongh (HiC) | (A) auto-commit VCS-lock at claim; (B) make merge rollback **transactional over the coord worktree's `status.events.jsonl` / `status.json`**. Base-divergence symlink note (adjacent). |

- **#2711 is CLOSED** — fixed by **PR #2785** (`fix(merge): #2709 squash provenance reconciliation + #2711 rollback/resume coherence`), **merged 2026-07-18 (today)**. #2786 is the *residual revert-failure edge* the #2711 fix left best-effort. This mission's branch sits **on top of** the merged #2711 work (main-worktree log shows the #2709/#2711 commits as ancestors).
- Code surface confirmed live: `src/specify_cli/merge/executor.py:458 def _revert_coord_done_commit`, called at `executor.py:535`. Coord-touching merge modules: `executor.py`, `done_bookkeeping.py`, `bookkeeping_projection.py`, `resolve.py`, `state.py`, `git_probes.py`.
- **Neither #2786 nor #2367 has a native sub-issue parent wired** (`trackedInIssues` empty on both). Tracker-hygiene gap the spec should close (native sub-issue parenting per `docs/guides/manage-issue-tracker.md`).

---

## 1. Sibling / related open issues (relation to this mission)

| # | Title (short) | Type/Prio | State | Relation |
|---|---------------|-----------|-------|----------|
| **2367** | merge blocked by coord worktree: VCS-lock at claim + non-transactional coord-status rollback | workflow/reliability/git, **P0** | OPEN | **FOLD-IN (Mechanism B) / same-class (Mechanism A).** B ("make merge rollback transactional over coord status writes") is *the same seam* as 2786. A (auto-commit VCS-lock at claim) is a different, claim-time seam. |
| **2711** | rollback/resume leave committed `done` opposed to reverted working status | reliability/git, P0/P1 | **CLOSED** | **Direct parent defect** (closed by PR #2785 today). 2786 is its residual edge. Not fold — already fixed; cite as lineage + rebase baseline. |
| **1826** | coord worktree falls behind its own branch mid-merge (safe_commit backstop) | reliability/git | **CLOSED** | Same neighborhood, **distinct mechanism** (behind-HEAD after update-ref). Cite as prior-art; not in scope. |
| **1795** | **Epic:** Parallel-lane git mechanics & event-log merge semantics | epic/reliability/git | OPEN | **Parent-epic candidate (best fit)** — merge git-mechanics + event-log coherence is exactly this class. |
| **2017** | **Epic:** Workflow guards that block legitimate actions / lack depth | epic/workflow/reliability | OPEN | **Parent-epic candidate for 2367** — 2367 self-declares "New scoped child of #2017". Guard-depth framing. |
| **2160** | **Epic:** Coord topology: unify artifact authority for task/status surfaces | epic/reliability, **P0** | OPEN | Dependency/neighbor — owns *authority* of the `status.*` files this mission must roll back. Coordinate, don't collide. |
| **1619 / 1666** | Epics: unify execution context / execution-state domain redesign | epic, **P0** | OPEN | Broad domain redesign; out-of-scope umbrellas. This mission is a tactical slice under them, not a fold. |
| **1878** | Umbrella: coordination placement/identity strangler (post-3.2.0) | epic, P2 | OPEN | Umbrella neighbor; out-of-scope. |
| **2745** | terminus gaps / orphaned coordination_branch (no `--skip-lanes`) | workflow/reliability/git, P1 | OPEN | Same-class, **defer** — different command (accept/close/terminus), not merge-rollback. |
| **2626** | lane-transition auto-commit crashes when lane worktree missing | workflow/reliability, P1 | OPEN | Same-class (auto-commit resilience), **defer** — implement/lane path, not merge rollback. |
| **2549** | move-task --force commits placement status.* to lane branch | workflow/reliability/git, P1 | OPEN | Same-class (coord/lane status-write partition), **defer** — move-task, not merge. |
| **2570** | multi-lane implement loop: allocator serialized behind uncommitted frontmatter | workflow/reliability | OPEN | Same-class (uncommitted tool-churn blocks action), **defer** — implement loop, not merge. |
| **2300** | unify coord+protected skip-vs-refuse across move-task/mark-status | workflow/reliability, P1 | OPEN | Neighbor (guard behavior unify); out-of-scope. |
| **2739** | spec-commit / commit-router refusals + under-committed scaffold | workflow/reliability/git, P1 | OPEN | Neighbor (commit-router on coord/protected); out-of-scope. |
| **2618** | unify flatten_mission() single seam (doctor --fix vs close) | reliability/tech-debt, P1 | OPEN | Neighbor (doctor-repair seam this mission's marker may feed); out-of-scope, note only. |
| **2334** | cross-worktree planning-artifact duplication (hand-synced N copies) | workflow/tech-debt, P2 | OPEN | Neighbor (coord-worktree copy drift); 2367 cites it. Out-of-scope. |
| **2144** | guarantee every Teamspace-bound event has SQLite/git durability | design-spike/reliability, P2 | OPEN | Neighbor (durability arch); the reconcile-marker's durability aligns philosophically. Out-of-scope. |
| **2533 / 2683** | PR-bound redundant coord topology / research-plan split authority | workflow/git, P1 / — | OPEN | Coord-topology cousins; out-of-scope. |

---

## 2. Parent epic(s) + graph recommendation

- **No sub-issue edges are wired today** on #2786 or #2367 — the spec should add them.
- **Recommended parenting:**
  - **#2786 → #1795** ("Parallel-lane git mechanics & event-log merge semantics"): the durable-reconcile-marker + transactional-merge-rollback is squarely merge git-mechanics / event-log coherence.
  - **#2367 → #1795** for Mechanism B (merge-rollback transactionality) and **#2017** for Mechanism A (guard/auto-commit depth). If a single parent is required for tracker cleanliness, **#1795** covers the fold seam both issues share.
  - Keep #1619/#1666/#1878/#2160 as **context epics**, not parents (they are domain-redesign umbrellas; over-parenting there dilutes signal — charter's single-canonical-authority principle favors the tightest true owner, #1795).
- This mission's own tickets/WPs sit **under this mission's `meta.json`** and roll up to **#1795**; #2786 is the primary tracker issue, #2367-Mechanism-B the fold-in.

---

## 3. In-flight collision check — **VERDICT: NO active collision**

- **PR #2785 (sibling mission `merge-squash-provenance-and-rollback-coherence-01KXRRB7`) is MERGED (today).** That mission owned `_revert_coord_done_commit` and the merge executor; it is **done**, not in-flight. This mission builds directly on it.
- **Lingering (not colliding):** the sibling's coord worktree `.worktrees/merge-squash-provenance-and-rollback-coherence-01KXRRB7-coord` still exists and its branch `kitty/mission-merge-squash-...-01KXRRB7` is checked out there. Housekeeping only — no divergent edits to the shared file.
- **#2367 is assigned to the HiC (stijn-dejongh)** but **no open PR and no agent branch references #2367** (the three PRs matching "2367" are unrelated merged upgrade/guard PRs). **No active agent session is on it.** Safe to fold Mechanism B here with operator confirmation.
- **No open PR touches `merge/executor.py`** in this class. Open PRs (#2766, #2612, #2492, #2606…) are review-handoff / lane-recovery / dashboard work on other surfaces.
- **Freshness caution (risk):** the fix lands on code merged **today** (PR #2785). Rebase this mission's branch onto the post-#2785 baseline before implementation, or the reconcile-marker will collide with the just-landed Option-A revert helper.
- Adjacent local spec `merge-base-diff-ssot-01KX44SD` exists and maps to #2367's base-divergence symlink Note — route that Note there, not into this mission.

---

## 4. Fold-in vs defer vs out-of-scope (recommendation)

**FOLD-IN (this mission can CLOSE / partially close as the shared-seam fix):**
- **#2786** — primary target (durable reconcile marker on revert failure).
- **#2367 Mechanism B** — "make merge rollback transactional over coord `status.events.jsonl`/`status.json`" is the *same transactional-merge-rollback seam*. Fold; on close, split #2367 or check off B. **Requires operator sign-off** (#2367 is HiC-assigned, P0).

**SAME-CLASS BUT DEFER (tracked follow-up, different command/seam):**
- **#2367 Mechanism A** (auto-commit VCS-lock at claim) — claim-time, not merge-rollback. Adjacent WP or separate ticket.
- **#2626** (lane auto-commit / missing worktree), **#2549** (move-task lane-branch pollution), **#2570** (allocator uncommitted frontmatter), **#2745** (terminus/orphaned coord_branch). All coord/lane transactional-write cousins on *non-merge* commands.

**OUT-OF-SCOPE (dependency / context, do not fold):**
- Epics #1795, #2017, #2160, #1619, #1666, #1878 (parent/context).
- #2334, #2144, #2618, #2300, #2739, #2683, #2533 (neighbor seams: copy drift, durability, flatten unify, skip-vs-refuse, commit-router, topology derivation).
- #2367 base-divergence symlink Note → route to `merge-base-diff-ssot-01KX44SD`.
- Closed lineage #2711 / #1826 → cite as prior-art, not scope.
