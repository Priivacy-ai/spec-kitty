# Tooling-Friction Trace — coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V

**Purpose:** a running log of spec-kitty tooling friction encountered while running this
mission (a coordination-topology, dogfooding mission). Seeded at spec→plan; **append
during the implement loop**; reviewed afterward to assess the state of the tooling.
Each entry: what blocked, where, witnessed evidence, disposition.

> Format per entry: `[date] [phase] SYMPTOM — anchor — disposition (fixed PR#/ticket#/workaround/open)`

---

## Seeded during spec → plan (2026-06-26)

1. **[specify] `spec-kitty specify` refuses to run inside a git worktree.** Attempting to
   scaffold the mission from an isolated `git worktree` returned
   `{"error": "Cannot create missions from inside a worktree. Run from the project root checkout."}`.
   **Witnessed live.** Rational guard (planning belongs in a root checkout), but it forced a
   detour: no idle full clone with an `upstream` remote + a working `.venv` was available
   (the `-runtime`/`-events`/`-design` siblings lack `upstream`/venv or are mid-flight), so I
   created a **fresh dedicated clone** (`spec-kitty-coord-residuals`) and ran the
   doctrine-qol `.venv`'s `spec-kitty` binary from it. Disposition: **workaround** (fresh
   clone). Possible gap: the guard's remediation text ("Run from the project root checkout")
   doesn't help when no suitable root checkout exists — consider a `--allow-worktree` or a
   "create a planning clone" helper. **OPEN (candidate gap).**

2. **[specify/plan] coord-topology placement is non-obvious for a planning-stage mission.**
   The scaffold defaulted `topology: coord`, created a `kitty/mission-…` coordination branch,
   and `spec-commit`/`plan` wrote artifacts to the **placement ref** (and `plan.md` into a
   `.worktrees/<slug>-coord/` worktree) — so on the working branch `spec.md`/`issue-matrix.md`
   show as **untracked** even though they are committed on the placement ref. Correct
   behavior, but the working-tree view is misleading at planning time (no `-coord` execution
   has started). Disposition: **workaround/understood** — verified artifacts via
   `git show kitty/mission-…:…`. Candidate doc-gap: clarify planning-stage placement in the
   specify/plan output. **OPEN (minor).**

3. **[plan] `plan` blocks until Technical Context is substantive — good, but the block fires
   only on re-run.** First `plan` call scaffolded the template and returned `blocked`
   (`Language/Version … placeholder`); authoring + re-run returned `success`. Disposition:
   **expected** (the substantive-spec/plan guards are working as designed). No gap — recorded
   for the friction baseline.

4. **[tasks] Coord-topology scaffold split the planning surface → `finalize-tasks`/`map-requirements` blocked.** `specify` defaulted the mission to `topology: coord` and created a coordination branch + `-coord` worktree **at planning time** — contrary to the SK rule "planning happens in the main checkout, no worktrees during planning." Consequence: `spec-commit`/`plan`/`map-requirements` wrote the tasks artifacts to the **coord branch/worktree**, but `finalize-tasks --validate-only` read `tasks_dir` from the **primary** checkout (empty) → `Unmapped functional requirements: FR-001..FR-011`, even after `map-requirements --batch` reported `success`+`committed`. **Witnessed live.** This is the exact #2185/#2186 planning-surface split-brain class the mission targets — dogfooded. Disposition: **workaround = flatten** (drop `coordination_branch`, `topology=flat`, bring artifacts onto the primary branch, retire the coord worktree) → validation passed (5 WPs). Candidate gap: `specify`/`plan` should not create a coord topology for a not-yet-implementing mission, or `finalize` must read the same surface the writers used. **OPEN (candidate gap, #2185/#2186-adjacent).**

5. **[env] Version-mismatched binary compounded the surface confusion.** I was running the **doctrine-qol clone's `.venv` binary (spec-kitty 3.2.2, on `feat/doctrine-qol-2083`)** against the fresh clone's newer `upstream/main` tree. Per operator suggestion, installed SK into the fresh clone's **own `.venv` (3.2.3, version-matched)** via `uv venv && uv pip install -e .`. Disposition: **fixed** — the version-matched binary + the flatten together produced a clean `finalize`. Lesson: a separate-clone mission needs its **own** `.venv`; don't drive it with another clone's editable install.

## Appended during implement (2026-06-27)

6. **[rebase/preflight] Rebase onto post-implement-loop `upstream/main` was clean; FR-011 preflight DISPROVED its own premise.** The 10 planning commits touch only the new mission dir → `git rebase upstream/main` applied with zero conflicts (10 ahead / 0 behind). But the FR-011 assumption ("the sibling deposits the #2185 pins in `_DIR_READ_KNOWN_RESIDUALS`; STOP if absent") was **false on the merged base**: the set holds only `show_kanban_status` (#2187) + `tasks_cli` (#2167); the ratchet vocabulary is structurally blind to `lanes.json`/LANE_STATE, so the #2185 cluster has ZERO pins and never can. Verified by reading the gate's COVERAGE-LIMIT comment, not trusting the label. Disposition: **caught at the analyze gate (BLOCKED, F1)** — the planning-vs-merged-base drift surfaced LATE (post-tasks), not at plan time. Lesson: the analyze gate is a real safety net for base-reality drift, but it fires after the WP layer already encodes the wrong premise.

7. **[tasks] In-place WP-reframe STRUGGLED; canonical regeneration was the fix.** Hand-patching `tasks.md` + 5 WP files + the dependency graph + re-running finalize cost ~233K tokens and recorded the analyze report 3× — a clear thrash signal, and it cut against canonical-sources discipline. Disposition (operator course-correction): **keep the reframe in spec/plan (durable), DELETE the WP layer, regenerate via `/spec-kitty.tasks` from the validated spec/plan.** Payoff: clean canonical WPs (analyze `ready`, disjoint owned_files, contiguous T-ids) + it auto-fixed a real gap the hand-patch left (`agent_utils/status.py:132` unrouted). Lesson: when a planner thrashes patching generated artifacts, regenerate them canonically — don't surgically patch the WP layer or the dependency graph.

8. **[implement/flat-mission] `agent action implement` on a flat mission still allocates a lane worktree + emits a cross-lane rebase hint.** `topology: flat`, yet the claim created `.worktrees/…-lane-a` ("shared by WP01") and `move-task --to for_review` printed a `cd …-lane-e && git rebase …-lane-a` propagation hint. Unlike the implement-loop sibling (stale lane base → forced flat-on-branch), lane-a here was FRESH (HEAD carried the regen + corrected spec, only status-bookkeeping commits behind) → used the canonical isolated lane flow. Disposition: **OK so far** — watch the cross-lane propagation + the eventual merge-to-mission-branch for the documented flat-friction. **OPEN (watch).**

9. **[env] pipx reinstall resolves to the pyenv shim, not the pipx bin.** `pipx install --force .` from the merged checkout reinstalled `spec-kitty-cli 3.2.3`, but `which spec-kitty` → `~/.pyenv/shims/spec-kitty` (not `~/.local/bin`). Versions matched so behavior was correct, but the shim-vs-pipx resolution is a latent footgun if they diverge. Disposition: **noted** (version-matched, no action).

10. **[implement/analyze gate] Every `mark-status` re-stales the analyze report → forced re-analyze before the NEXT WP claim.** Marking WP01's 9 subtasks done edited `tasks.md` (checkbox `[ ]`→`[x]`); the implement gate hashes `tasks.md` wholesale, so the recorded `analysis-report.md` went `stale_analysis_report` and `agent action implement WP02` refused until `/spec-kitty.analyze` was re-run. The re-run was purely mechanical — same content, same `ready` / 2-low verdict, only the hash moved. Disposition: **workaround = re-run analyze per WP** (will recur WP02→WP05 — a per-WP friction tax). Candidate gap: the staleness check should ignore checkbox-only (subtask-status) diffs in `tasks.md`, or hash the substantive spec/plan/WP content rather than the mutable progress checkboxes. **OPEN (candidate gap).**

11. **[implement/auto-commit-off] The claim writes `vcs_locked_at` into `meta.json`, then refuses to proceed because that write left the tree dirty.** `agent action implement WP02` blocked at "Resolve execution workspace" with `Planning artifacts not committed: meta.json, tasks/WP01-*.md` (auto-commit disabled). The dirty content was benign tooling churn — `meta.json` gained `vcs`/`vcs_locked_at` lock fields (written by the claim itself) + the WP01 file gained reviewer-renata's review-passed activity-log entry. Disposition: **workaround = hand-commit the bookkeeping, then re-claim.** This is a self-inflicted dirty-tree block: the claim's own vcs-lock write trips its own not-committed guard. Candidate gap: auto-commit-off claims should stage their own vcs-lock write (or exempt it from the guard). **OPEN (candidate gap — self-inflicted dirty-tree).**

<!-- append during implement: each routed site, any guard that blocks a legitimate edit,
     the rebase-onto-post-implement-loop-main step, pin-drain ratchet behavior, FR-009 fixture. -->

## Close-out assessment (2026-06-27)

Mission landed clean (5/5 WPs first-pass approved, full `tests/architectural/` 559 passed). The friction this mission surfaced is **general spec-kitty tooling debt**, not mission-specific — recommend filing (or folding into #2017):
- **#10 stale-analysis-per-mark-status** + **#11 self-inflicted vcs-lock dirty-tree** — a per-WP friction TAX: every WP claim required (a) committing the claim's own vcs-lock churn and (b) re-recording the analyze report (mechanical, content unchanged). Hit 5×. Candidate fixes recorded in entries 10/11. **File as a tooling-friction issue.**
- **#8 flat-mission lane allocation** — a `topology: flat` mission still allocated lane worktrees (lane-a..e) + emitted cross-lane rebase hints; worked because lanes were fresh, but the flat/lane impedance mismatch persists.
- **#2017 move-task-from-lane status-desync** — `move-task --to approved` from a lane worktree returned `Illegal transition planned->approved` on ALL 5 approvals; the primary-checkout fallback (authoritative event log) worked every time. Reliable workaround, real guard friction (feeds #2017).
Disposition: none blocked progress; all have documented workarounds. The candidate gaps are worth an upstream tooling-friction ticket.
