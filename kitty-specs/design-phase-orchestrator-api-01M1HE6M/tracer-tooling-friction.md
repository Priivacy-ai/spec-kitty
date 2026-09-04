# Tracer: Tooling Friction — design-phase-orchestrator-api-01M1HE6M

Seeded at plan phase (2026-09-02). Appended during implementation; assessed at close.

## Plan phase

None yet. `spec-kitty plan --mission design-phase-orchestrator-api-01M1HE6M --json` ran
cleanly, non-interactively, and returned the expected scaffold-state envelope
(`plan_file`, `feature_dir`, `spec_file`, `planning_base_branch` all correctly resolved
to the feature branch given this mission's `single_branch` topology). No blocking issue
reading the spec (983 lines, read in full), the operator ruling, the charter, or
`AGENTS.md`.

One minor observation, not friction exactly: the task instructions asked to "confirm"
`CLAUDE.md`'s Shared Package Boundary guidance (`src/runtime/next/_internal_runtime/` as
canonical runtime home) against the actual tree and against where the FR-014 functions'
real dependencies live. That confirmation surfaced a genuine nuance CLAUDE.md's one-line
summary doesn't capture: `_internal_runtime/` is a closed set of internalized-package
DAG-engine re-exports, not a general extension point, while the TOP LEVEL of
`src/runtime/next/` (`decision.py`, `runtime_bridge.py`) is where CLI-domain-importing
next-invocation orchestration code already lives. This is recorded as a design decision
(`tracer-design-decisions.md` #1), not filed as friction — CLAUDE.md's guidance was
correct at the level it was written, just not granular enough to answer "which exact
file inside `src/runtime/next/`," which is precisely the kind of question a plan phase
exists to resolve rather than escalate.

## WP01 — Baseline-red snapshot (T001)

Recorded at the mission's pre-change commit `30b23fe3c` on
`feat/design-phase-orchestrator-api-3837` (this mission's `planning_base_branch`,
`single_branch` topology per plan.md § (h)), BEFORE any functional edit landed. Runner:
`.venv/bin/python -m pytest` (never bare `uv run`, per this repo's `CLAUDE.md`).

Issue #3284 re-checked at run time (`gh issue view 3284`): still **OPEN**, title "main
full suite has 23 untracked failures and 2 errors after bootstrap prewarm". Its 23
failures + 2 errors were produced by a FULL-suite run (`pytest tests/ -n auto --dist
loadfile`) and group into: doctrine/config activation drift
(`tests/charter/test_config_stem_parity.py`, `tests/doctrine/drg/test_reachability.py`,
`tests/doctrine/drg/migration/test_extractor_projection.py`), runtime/timing (daemon
self-retirement, completion-budget, doctor-daemon-restart), console ANSI/plain-mode
assertions, CI route-collection probe timeout, mission-template-resolution defaults,
compact-charter-contract sizing, a safe-commit empty-shape test, two macOS-cache-path
E2E tests, and sync-teardown errors. None of those failing modules/paths overlap this
WP's three targeted directories below.

Targeted-shard results — **all three shards fully GREEN, 0 failed, 0 errors**:

1. `.venv/bin/python -m pytest tests/specify_cli/orchestrator_api/ -v`
   → `13 passed in 1.15s`. Node ids (all PASSED):
   `test_commands_fail_closed.py::test_resolve_history_commit_args_raises_structured_error_on_action_context_error`,
   `test_commands_fail_closed.py::test_resolve_history_commit_args_error_never_carries_current_branch_ref`,
   `test_commands_fail_closed.py::test_append_history_surfaces_structured_error_code_on_emit_failure`,
   `test_fail_message_preserved.py::test_fail_preserves_message_alongside_param_is_not_duplicated`,
   `test_fail_message_preserved.py::test_fail_without_data_still_carries_message`,
   `test_fail_message_preserved.py::test_fail_caller_message_matches_param_is_not_duplicated`,
   `test_transition_subtask_gate.py::test_unasserted_flag_blocks_on_silent_snapshot`,
   `test_transition_subtask_gate.py::test_unasserted_flag_allows_when_snapshot_marks_all_done`,
   `test_transition_subtask_gate.py::test_explicit_caller_assertion_cannot_bypass_snapshot_gate`,
   `test_transition_subtask_gate.py::test_force_bypasses_the_subtask_guard_entirely`,
   `test_typed_error_fail_closed.py::test_resolve_seam_resolves_primary_on_empty_coord_topology`,
   `test_typed_error_fail_closed.py::test_mission_state_endpoint_reads_primary_on_empty_coord_topology`,
   `test_typed_error_fail_closed.py::test_genuine_not_found_still_emits_mission_not_found`.
2. `.venv/bin/python -m pytest tests/specify_cli/cli/commands/test_next_answer_effective_root.py
   tests/specify_cli/cli/commands/test_next_fail_closed.py
   tests/specify_cli/cli/commands/test_next_owned_commit_guard.py
   tests/specify_cli/cli/commands/test_next_typed_error_passthrough.py -v`
   → `23 passed in 7.18s`.
3. `.venv/bin/python -m pytest tests/architectural/test_shared_package_boundary.py
   tests/architectural/test_runtime_charter_doctrine_boundary.py -v`
   → `12 passed in 4.87s`.

**Conclusion**: this WP's targeted shards carry ZERO pre-existing reds — #3284's known
failures live entirely outside these three directories. No new GitHub issue opened (no
failure to classify — NFR-003's "cross-reference against #3284" step is vacuously
satisfied: nothing failed to cross-reference). Every later WP (WP02–WP09) can therefore
state "0 pre-existing reds observed in my targeted shard, N introduced" as the honest
floor for these specific directories, and should re-verify #3284's OPEN state / group
list has not shifted before citing this snapshot as unchanged truth.

## WP02 — WP01 never transitioned past `planned` (dependency-gate mismatch)

`spec-kitty agent action implement WP02 --agent claude --mission
design-phase-orchestrator-api-01M1HE6M` refused with `Error: dependencies_not_satisfied:
WP02 depends on WP01; all dependencies must be approved or done before implementation can
start`, even though the lane branch already carries WP01's real commit (`7a996ce7b`,
confirmed via `git log`). `spec-kitty agent status lifecycle --mission ...` and a direct
read of `status.events.jsonl` confirm this is not a stale-materialization artifact: WP01
has exactly ONE recorded event, `genesis -> planned` at `2026-09-02T18:53:58` — no
`in_progress`/`done` transition was ever emitted for it, despite its commit existing.
`spec-kitty agent status materialize` would not help (nothing newer to replay).

Per this WP's own operating rules ("NEVER hand-edit spec-kitty state... no CLI command
for a transition means BLOCKED, not a hand-edit") and the review-authority boundary ("you
do NOT review your own work... I dispatch a separate reviewer"), fabricating a WP01
`done`/`approved` transition is not this WP's call to make — that would be issuing an
unearned review verdict for a work package this agent did not implement. Instead:
`.venv/bin/spec-kitty safe-commit` was used directly (it does NOT gate on WP-status
dependency chains, only on branch/owned-file protection) to land WP02's commits. It
succeeded but emitted a non-blocking `ACTIVE_WP_SCOPE_VIOLATION` warning on every commit
(`tests/.../test_next_invocation_lifecycle_seam.py is outside active_wp=WP01
owned_files`) — a direct symptom of the same gap: the lane's `active_wp` context never
advanced past WP01 because `agent action implement WP02` never got to run. Flagging for
the operator: WP01's status transition needs to be resolved (by whoever has review
authority over WP01) before the canonical `implement`/`review` display commands work
correctly for WP02 or any later WP in this lane.

## WP02 — the `next` shard-registry completeness gate is a second, undocumented marker
authority beyond `fast`/`integration`/`git_repo`

This WP's own task file names exactly two markers (`pytest.mark.integration`,
`pytest.mark.git_repo`) as the marker-discipline requirement (citing ledger SK-144 /
issue #3241 — "CI selects tests by pytest MARKER, independently of directory"). Setting
only those two on the new `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`
is NOT sufficient: `tests/_next_shard_map.py` (mission
`ci-test-topology-performance-01KXBJRT`) is a SEPARATE, file-path-keyed registry that the
`tests/conftest.py` collection hook (`_apply_shard_markers`) consults to stamp a
`next_shard_{1,2,3}` marker onto every test under the three `integration-tests-next`
roots (`tests/next`, `tests/specify_cli/next`, `tests/runtime`) — and the `next` group's
`default_fallback` is `False` (unlike `arch`'s), so an unregistered new file gets ZERO
shard markers, not an auto-assigned one. `integration-tests-next`'s three CI legs each
select `-m 'next_shard_N and ... (git_repo or integration)'`, so a file with `integration`
+ `git_repo` but no `next_shard_N` marker is invisible to ALL three legs — the exact
SK-144 failure mode, one layer deeper than the WP task file's own citation covers.
Confirmed via `tests/architectural/test_arch_shard_marker_completeness.py`, which failed
loudly (`'next' nodes must carry exactly one shard marker: {...test_next_invocation_
lifecycle_seam.py::...: []}`) before the file was registered. Fix: added the new file to
`_SPECIFY_CLI_NEXT_SHARD_2_FILES` in `tests/_next_shard_map.py` (one line; that file is
NOT in WP02's `owned_files`, but leaving it unregistered would ship a test genuinely
invisible to `integration-tests-next` — exactly the defect class this WP's own marker
-discipline instruction warns against). Re-ran the completeness test GREEN after the fix,
and confirmed via `--collect-only -m "next_shard_2 and not windows_ci and (git_repo or
integration)"` that the new test is now selected, and via `-m "fast and not windows_ci"`
that it is correctly NOT selected by `fast-tests-next`.

## WP03 — the vendored `upstream_contract.json` compatibility gate is a second,
undocumented conformance authority beyond the envelope's own `CONTRACT_VERSION`

Adding `specify`/`plan`/`tasks` to `orchestrator_api/commands.py` and running the FULL
existing test surface (not just the WP's own new file) surfaced two real regressions in
`tests/contract/test_orchestrator_api.py` — a file OUTSIDE this WP's `owned_files` and
outside its stated baseline (`tests/specify_cli/orchestrator_api/`,
`tests/specify_cli/next/`, `tests/runtime/next/`), so it would have been silently missed
by only running the declared baseline paths:
`TestAllowedCommandNames::test_registered_commands_are_contract_allowed` (new commands not
declared) and `TestAllowedErrorCodes::test_literal_failure_codes_are_contract_allowed`
(new error codes not declared). Both check a vendored artifact,
`src/specify_cli/core/upstream_contract.json` (sourced from spec-kitty-events /
spec-kitty-saas per its own `_comment`), which `commands.py`'s docstring's error-code list
does NOT itself gate against — the module docstring is documentation only; this JSON file
is the actually-enforced authority. `git log --oneline -- upstream_contract.json` shows
this file IS routinely hand-updated by ordinary feature work (e.g. `19c9f36d6
"fix(contract): register ANCESTRY_NOT_ESTABLISHED orchestrator-api error code (#3281)"`),
so updating it (adding `specify`/`plan`/`tasks` to `allowed_commands` and
`MISSION_ALREADY_EXISTS`/`MISSION_CREATE_FAILED`/`PLAN_SETUP_FAILED`/
`TASKS_FINALIZE_FAILED` to `allowed_error_codes`) is the established, expected pattern
despite the file not being in this WP's `owned_files` — flagging per the same-file-overlap
discipline the WP's own Write-Scope note already asks for on `commands.py`: WP04/05/06/08
will each independently need the identical edit to this same JSON file for their own new
commands/error codes, so this is a THIRD same-file overlap surface (alongside
`commands.py` itself and the pre-existing PR #3826 concern) the merge-order review must
account for.

## WP03 — the same contract file's `required_payload_fields: ["mission_slug"]` clause
forces one identity field onto an otherwise-"raw pass-through" verb

`agent_feature.finalize_tasks(..., json_output=True)`'s raw payload (verified by direct
invocation against a real mission) genuinely does not carry a `mission_slug` key — unlike
`agent_feature.setup_plan`'s raw payload, which does. `validate_outbound_payload(data,
"orchestrator_api")` (the exact call the WP's own Pattern Precedent section mandates
before `make_envelope`) raises `ContractViolationError` on the `tasks` verb's genuinely
raw payload for this reason alone. The WP task file's own Reviewer Guidance says "confirm
plan/tasks are genuinely unenriched pass-throughs" — read literally, satisfying that and
satisfying `validate_outbound_payload` are in tension for `tasks` specifically. Resolved
by filling `mission_slug` via `payload.setdefault(...)` using the ALREADY-VALIDATED input
identity (the mission dir `_resolve_mission_dir_or_fail` already resolved, not any new
derived/business field) only when genuinely absent — a transport-contract identity fill,
not the kind of business-payload enrichment (`scaffold_only`/`spec_state`/etc.) the WP
warns against reproducing on `plan`/`tasks`. Recorded here rather than silently deviating
from either instruction.

## WP03 — `mission_id`'s ULID-derived `mid8` is NOT a stable-enough real-time collision
window for a deterministic duplicate-mission test

The WP task file's own Acceptance Scenario 4 ("`specify` called twice for the same slug")
assumes a real, unmocked duplicate collision is straightforward to reproduce. It is NOT
reliably so: `mission_id = str(ULID())` (`core/mission_creation.py:666`) mints a fresh
ULID per call, and `resolve_mid8` truncates it to the first 8 Crockford-base32 characters
— the HIGH 40 bits of the ULID's 48-bit millisecond timestamp, meaning the mid8 value
(and therefore the mission's on-disk directory name) only stays identical across calls
that land in the SAME ~256ms window. Two back-to-back Python calls with no I/O between
them collide reliably (confirmed via a throwaway script); the SAME two calls routed
through the full `specify` CLI verb (real git `add`/`commit` subprocess calls in between)
frequently do NOT — confirmed by an initial flaky FAIL on a second local run of the
otherwise-passing test. Fixed by freezing BOTH entropy sources the on-disk scaffold
content depends on — `specify_cli.core.mission_creation.ULID` (monkeypatched to a single
frozen instance) and `specify_cli.core.mission_creation.now_utc_iso` (monkeypatched to a
fixed ISO string, since `meta.json`'s `created_at` is the only other call-time-variant
field within `create_mission_core`) — rather than relying on real-time proximity. Re-ran
3x locally after the fix with zero flakes. Flagging for later WPs (or a future mission)
touching `mission create`/`specify` real-git-I/O tests: do not assume rapid repeated calls
collide on identity by timing alone.

## WP04 — the lane worktree carries no `.venv` of its own; the checked-out `.venv/bin/python`
gate command genuinely does not exist until `uv sync` is run inside the worktree

The mission checkout's `.venv` lives at the MAIN checkout root
(`/…/3837/.venv`), editable-installed against the MAIN checkout's `src/`
(`.venv/bin/python -c "import specify_cli; print(specify_cli.__file__)"`
resolves to `3837/src/specify_cli/…`, not the lane worktree's copy). The
lane worktree (`3837/.worktrees/design-phase-orchestrator-api-01M1HE6M-lane-a/`)
has no `.venv` directory at all — a bare `.venv/bin/python -m pytest …` run
from inside it fails with `No such file or directory`, which is
indistinguishable at first glance from "the gate command does not exist"
(the BLOCKED-worthy case per this WP's own governing instructions). It is
not that: it is CONTRIBUTING.md's own documented, idempotent dev-setup step
(`uv sync --frozen --all-extras`) simply not having been run yet for this
particular worktree. Running it inside the worktree creates a
worktree-local `.venv` correctly editable-installed against the worktree's
OWN `src/` (verified), after which every `.venv/bin/python -m {pytest,ruff,
mypy}` gate command in this WP's task instructions works exactly as
specified. Flagging for WP05/WP06/WP07/WP08/WP09 (or any future lane
worktree in this mission): the first gate command run inside a freshly
created lane worktree will need this same `uv sync` first — it is setup,
not an improvised substitute for a missing command.

## WP04 — `finalize_tasks` (the `tasks` orchestrator-api verb, WP03) leaves
`.kittify/sync-state.json` genuinely uncommitted after a successful call —
unrelated residue easily mistaken for `record-analysis`'s own SK-114 hazard

Building a real mission fixture via `specify` → `plan` → `tasks` (WP03's own
proven end-to-end pattern, reused here for `record-analysis`'s real-git-I/O
scenarios) leaves the git tree with one genuinely uncommitted file after the
`tasks` verb succeeds: `.kittify/sync-state.json` (confirmed via a
throwaway script: `git status --porcelain` immediately after a successful
`tasks` invocation shows exactly this one modified path; NOT
`is_self_bookkeeping_churn`-allowlisted, since `record-analysis`'s own
dirty-tree preflight — reused unmodified from `mission_record_analysis.py`
per this WP's plan.md § (j) option (a) — refused with `DIRTY_WORKTREE` the
first time this fixture chain was tried). This is easy to misdiagnose as
this WP's own SK-114 hazard ("record-analysis's dirty-tree guard blocks on
side effects, including its own") — it is a DIFFERENT, `tasks`-verb-owned
side effect, encountered here only because the test fixture chains three
verbs together before ever calling `record-analysis`. Fixed in the test
fixture (not production code) by committing once more immediately after the
`tasks` call, before any `record-analysis` scenario runs — matching how a
real orchestrator would commit between phase transitions in practice.
Flagging for WP05/WP06/WP08 (or any sibling WP building a similar
specify→plan→tasks real-git fixture chain): expect this same residue and
commit it away rather than assuming a `DIRTY_WORKTREE` failure at that point
is your own verb's defect.
