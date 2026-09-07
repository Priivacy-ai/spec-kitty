# WP04 review feedback — round 1

**Reviewer**: reviewer-renata (claude-fable-5-1) · **Lane**: lane-d `9ca89428b` on base `596396b7d` · **Verdict**: REJECT (one Major finding; everything else Met or Minor)

## Verified Met (no action)

- Polarity (C-004 / Q8): `GuardContext.dependency_ready: bool | None = None` (`models.py:911`); `PlannedState`/`ClaimedState.guard_for` refuse only on `is False` (`wp_state.py:318,345`); `None`/`True` pass; guards never read `ctx.force`; no `is not True` slipped in anywhere in `src/`. Probe pins for `lanes/recovery.py:78` and `agent/tasks_transition_core.py:337` present and green.
- RED proof (SC-005): reproduced independently in a scratch worktree at `596396b7d` with a standalone repro — `Failed: DID NOT RAISE <class 'specify_cli.status.emit.TransitionError'>`; the same repro passes on the lane.
- In-lock resolution (FR-013): all four doors (flat single, flat batch, txn single, txn batch) run lock → `_reduce_write_surface` → `_derive_from_lane(snapshot=)` → `_resolve_dependency_readiness` → `prepare_transition`; flat shells use `canonical_feature_dir`, txn shells use `txn.feature_dir` for the snapshot and `identity.feature_dir` for the WP file. Shells never pass `None`. Coord-surface tests (both stale directions + order pin) and the cross-thread TOCTOU test are sound.
- Batch design: ONE verdict per batch is correct — both batch doors refuse a multi-WP batch with `TypeError` before the lock (`emit.py::_check_batch_request_identity`, `status_transition.py::_prepare_batch_in_transaction`); reviewer-probed a two-WP batch: `TypeError: emit_status_transition_batch only supports one feature/mission/wp per batch`. A same-WP batch cannot change its own dependencies' lanes, so the verdict holds for every member.
- NFR-004: `test_emit_reads_log_once` / `test_batch_emit_reads_log_once_for_the_whole_batch` green and unchanged; declared deps read via raw `read_frontmatter`, not `read_wp_frontmatter`. Legacy mission with no `tasks/` dir still emits (reviewer-probed: `planned->claimed` emitted).
- Replay purity (C-005 / NFR-002): reducer AST scan (with non-vacuity check) + now-dep-illegal history replays/audits clean.
- FR-014 demotion: the six sites are comments-only diffs; `dependency_readiness_for_wp` reused via lazy import.
- Scope/quality: out-of-map edits minimal and logged; `ruff check` clean on the changed set; C901 clean; mypy clean on the six status files; `coordination/status_transition.py` still exactly 4 pre-existing mypy errors (lines 160/188/197/755 — none in the diff hunks). `ruff format --check`: new/changed source files clean; `wp_state.py`, `test_wp_state.py`, `test_transition_context.py` were already format-red on the base (pre-existing, not this diff). The single new `# noqa: PLC0415` is the repo's established lazy-import idiom (417 precedents in `src/`) with an inline cycle rationale — acceptable.
- Tests: blast radius `tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/lanes tests/unit/status` → 2170 passed, 2 skipped; `tests/specify_cli/cli/commands/agent` → 1901 passed, 1 skipped, 2 xfailed; five architectural gates → 65 passed; touched test files + NFR-004 pins → 207 passed.

## Findings

### 1. MAJOR — the guard's declared-deps reader rejects the legacy string form that the FR-014 single source accepts, and the refusal fires on every edge with no `force` escape

- **Where**: `src/specify_cli/status/emit.py:342-348` (`_coerce_declared_dependencies`), called from `_declared_dependencies` (`emit.py:323-339`) on every shell emit regardless of the target lane.
- **What is wrong**: `WPMetadata` (`src/specify_cli/status/wp_metadata.py:305-314`, the parser behind `parse_wp_dependencies`, i.e. what every FR-014 pre-flight site uses) deliberately coerces the legacy string forms `dependencies: "[]"` → `[]` and `dependencies: "WP01, WP02"` → `["WP01", "WP02"]`. `_coerce_declared_dependencies` raises `TransitionError("... malformed `dependencies` value ...")` for exactly those forms. Because the raise happens in the shell BEFORE `validate_transition`, it (a) applies to every edge, not just the two guarded ones, and (b) cannot be bypassed by `force` + reason. Net effect: for any WP whose prompt file carries the legacy string form, the FSM write path is locked out entirely — no claim, no `→blocked`, no `→for_review`, not even a forced `→canceled`.
- **Evidence (reviewer probes on the lane)**:
  - `dependencies: "[]"` → `planned->claimed` REFUSED: `Cannot resolve the declared dependencies of WP02: ... declares a malformed dependencies value ('[]')`; `parse_wp_dependencies` on the same file → `[]`.
  - `dependencies: WP01` (bare scalar) → `planned->canceled` with `force=True, reason=...` REFUSED; `planned->blocked` REFUSED; `parse_wp_dependencies` on the same file → `['WP01']`.
  - Real files in this repository today: `kitty-specs/062-fix-doctrine-migration-test-failures/tasks/WP07-targeted-coverage-ci-split.md` (lane `planned`), `WP10-centralize-doctrine-path-constants.md`, `WP11-dashboard-js-terminology-clean-break.md` (lane `claimed`) all carry `dependencies: "[]"`. After WP04 none of them can move through the shells.
- **Why it matters**: FR-014 requires gating semantics to stay single-sourced; here the *inputs* to that single source diverge between pre-flight and guard, so a WP the pre-flight reports as ready is refused by the write path with a message that names no dependency and admits no override. This is a regression on the write path the mission exists to harden.
- **Satisfies**:
  1. Normalise with the SAME legacy coercion `WPMetadata` uses — e.g. extract that coercion in `wp_metadata.py` into a small shared pure helper and call it from `_coerce_declared_dependencies` (do not duplicate the rules). Only a value that WPMetadata would also reject may remain fail-closed.
  2. Add tests in `TestVerdictHelpers` for `"[]"`, `"WP01, WP02"` and bare `WP01` forms (expected: `()`, `("WP01","WP02")`, `("WP01",)`), and one shell-level test proving a WP file with `dependencies: "[]"` can still be claimed.
  3. Re-run the same probe on the three `062-...` files (read-only: `_declared_dependencies(Path("kitty-specs/062-fix-doctrine-migration-test-failures"), "WP07")` must not raise).

### 2. MINOR — fail-closed on a genuinely unparseable WP file blocks non-guarded edges and is not `force`-bypassable

- **Where**: same site as Finding 1 (`emit.py:323-348`); the verdict is resolved unconditionally before `prepare_transition`.
- **What is wrong**: for a WP whose frontmatter is truly unparseable, the design refuses `→blocked`, `→canceled`, `→for_review` etc. — edges the dependency guard has no opinion on — and the operator has no `force` escape because the error is raised outside `validate_transition`. The existing emit path tolerates the same file (the phase-1 mirror at `emit.py:527-531` logs and skips). The design note argues "the same file already fails the pre-flight sites", but the pre-flight sites only run on the claim path.
- **Satisfies (recommended, implementer's choice of shape)**: either (a) resolve/raise readiness only when the requested target resolves to `claimed`/`in_progress`, or (b) map the read failure to `dependency_ready=False` (with the failure reason logged/attached) so the guard refuses the two entry edges, `force` + reason still bypasses, and every other edge is unaffected. Add a test that a WP with unreadable frontmatter can still be force-canceled. If you keep strict fail-closed for the entry edges, say so in `design-notes/WP04-guard.md`.

### 3. MINOR — RED-proof artifact is not reproducible from the committed test file

- **Where**: `tests/status/test_dependency_guard.py:34` imports `specify_cli.status.dependency_verdict`, which does not exist on the base, so the committed file errors at collection on `596396b7d` (`ModuleNotFoundError`). The Activity Log states the RED run produced `DID NOT RAISE`; that must have been an earlier revision of the file.
- **Satisfies**: no code change required (C-009: red-first repros are transitional). Amend the Activity Log line to say the RED run used a pre-`dependency_verdict` revision of the test, or note the reviewer's standalone repro shape (seed WP01+WP02 planned, drive WP01 to `in_progress` via the flat shell, claim WP02 → must raise).

### 4. NOTE (no action in this WP) — US4-6 "not re-gated"

`implement.py:1869` calls `_ensure_wp_claim_preconditions` unconditionally, so `implement` re-invoked on an `in_progress` WP whose dependency regressed is refused by the pre-flight before the lifecycle no-op is reached. This is pre-existing on the base (the WP04 diff at that site is comments-only) and FR-014 says the sites are "left in place", so the lifecycle-level pin `test_start_implementation_resume_is_not_regated_when_dependency_regresses` is an acceptable proof that the *guard* cannot re-gate a resume. T025.2 asked for the CLI-level variant in `tests/specify_cli/cli/commands/`; that would be RED because of the pre-flight, and the design note records the deviation honestly. Carry to the caller-migration mission.

### 5. NOTE — contract §2 deviation (refusal message carries no dependency ids)

Recorded in `design-notes/WP04-guard.md` §4; `data-model.md` §6 types the field as a bare `bool | None`, so the guard cannot name the ids. Accepted; if Finding 2 is resolved via shape (b), consider surfacing `DependencyReadiness.unsatisfied` in the shell's refusal for operators.

## Re-review checklist

- [ ] Finding 1 fixed with shared coercion + tests; the three `062-...` WP files resolve without raising.
- [ ] Finding 2 addressed (either shape) or explicitly recorded as a deliberate policy in the design note.
- [ ] Activity Log amended for Finding 3.
- [ ] Re-run: blast radius (`tests/status tests/specify_cli/status tests/specify_cli/coordination tests/specify_cli/lanes tests/unit/status`, `-n 3 --dist loadfile`), `tests/specify_cli/cli/commands/agent`, the five gates, NFR-004 pins; `ruff check`, C901, mypy on the six status files.
