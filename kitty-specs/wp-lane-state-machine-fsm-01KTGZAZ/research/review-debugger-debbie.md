# Adversarial review — debugger-debbie (opus, falsification-first)

**Change:** `fix/status-genesis-lane-bootstrap` @ `a43aa6a06`.
**Verdict:** **DEFECTS-FOUND (1 MEDIUM + 2 LOW).** The four core intent claims all held under falsification.

## Attacks (concrete repros, PYTHONPATH=src; targeted tests only)

**Attack 1 — non-display invariant (can genesis leak into snapshot/board/kanban/progress?): HELD.** Constructed an event log with a `genesis->planned` seed; `materialize` produced no genesis. Structural proof: zero edges INTO genesis, so a persisted event can never set a WP's current lane to genesis. Two inert leak surfaces (LOW/cosmetic): (a) `reducer` builds `summary = {lane.value: 0 for lane in Lane}` → every snapshot carries `"genesis": 0` (fixtures updated to match; always 0); (b) `get_all_lane_values()` now includes genesis → `task_metadata_validation.py:232` would accept `lane: genesis` in WP frontmatter and print genesis in its "must be one of …" error (frontmatter lane is retired/non-authoritative; harmless but leaks the non-display lane into a user-facing message).

**Attack 2 — derivation correctness / import cycle: HELD, exact.** Derived set == old set ∪ {genesis->planned, genesis->canceled}: EXACT MATCH, 0 missing/0 extra (29 = 27 + 2). Importing `transitions` first in a fresh interpreter loads fine (deferred wp_state import).

**Attack 3 — clobber-fix regressions.** 3a non-coord missions: HELD (filtering only in `coord_branch_for_commit != target_branch` branch). 3b empty-changeset on coord re-finalize: LOW risk — after filtering the two status files, if all remaining artifacts are byte-identical, `git commit` exits 1 ("nothing to commit") → finalize Exit(1). Only on a redundant re-finalize where nothing but status changed. Not data loss.

**Attack 4 — genesis transition guards.** `genesis->blocked` rejected (sensible). `genesis->planned` allowed without force (bootstrap passes force=True redundantly). `genesis->canceled` allowed. "Stuck in genesis" after mid-finalize crash: recoverable — `bootstrap_canonical_state` is idempotent and re-seeds.

**Attack 5 — backward compat.** HELD for seeded WPs (legacy planned-first log derives correctly). Surfaced the one behavioral break: a WP absent from a non-empty log derives `genesis` (was `planned`) — affects unseeded WPs and WPs appended to `tasks/` after finalize already ran.

## Confirmed defect
**MEDIUM (UX/robustness) — unseeded `implement` fails with a cryptic, un-actionable error + dangling worktree.** `_derive_from_lane → GENESIS` + `work_package_lifecycle.py::start_implementation_status` PLANNED branch emits a batch that derives `from_lane=genesis` → `TransitionError: Illegal transition: genesis -> claimed`. In `implement.py` the workspace/worktree is allocated (line ~916) BEFORE `start_implementation_status` (~920); the error is caught and printed verbatim with Exit(1) — no hint to run finalize-tasks, dangling worktree left. Read-layer (`wp_lane_actor_from_events`) still defaults unseeded → PLANNED, so the call enters the PLANNED branch and only fails inside the batch. Fix: detect genesis in `start_implementation_status` and raise `WorkPackageStartRejected("run finalize-tasks")` BEFORE workspace allocation; make `wp_lane_actor_from_events` return genesis so read/write agree.

Quality: `ruff` clean on all 7 changed source files; targeted tests green (153 passed).
