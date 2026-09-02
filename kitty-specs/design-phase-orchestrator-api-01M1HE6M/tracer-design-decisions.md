# Tracer: Design Decisions — design-phase-orchestrator-api-01M1HE6M

Seeded at plan phase (2026-09-02). Appended during implementation; assessed at close.

## 1. FR-014 seam target module: `src/runtime/next/next_invocation_lifecycle.py`

**Decision**: extract `_pair_previous_lifecycle_record`, `_emit_mission_next_invoked`,
and `_write_issuance_lifecycle_record` from `src/specify_cli/cli/commands/next_cmd.py`
into a NEW module `src/runtime/next/next_invocation_lifecycle.py` — a single module with
all three functions (not split along the two persistence layers they touch), sitting at
the top level of `src/runtime/next/` alongside `runtime_bridge.py` and `decision.py`, NOT
under `src/runtime/next/_internal_runtime/`.

**Why this module and not the alternatives**:

- `CLAUDE.md`'s "Shared Package Boundary" section names
  `src/runtime/next/_internal_runtime/` as the canonical runtime home and
  `src/specify_cli/next/` as a deprecated shim. Confirmed against the actual tree:
  `src/runtime/next/` exists and contains `_internal_runtime/`.
- BUT `_internal_runtime/`'s own module docstrings (e.g. `lifecycle.py:1-11`) describe it
  as internalized `spec-kitty-runtime` 0.4.3 package internals — a closed set of DAG-engine
  re-exports (`next_step`, `provide_decision_answer`, `start_mission_run`). Grepping
  `src/runtime/next/_internal_runtime/` for `lifecycle_record`/`issuance` returns zero
  matches — no existing natural home there for issuance-lifecycle-record I/O.
- The real persistence primitives the three functions call already live correctly
  elsewhere: `specify_cli.invocation.lifecycle` (the issuance-lifecycle-record store,
  module docstring: "Profile-invocation lifecycle store (WP05 / issue #843)... written by
  `spec-kitty next`") and `specify_cli.mission_v1.events` (the separate
  `mission-events.jsonl` event log). These are TWO distinct persistence layers, but the
  three functions being extracted are next-invocation ORCHESTRATION around both — the seam
  is one module with three functions, matching how spec.md's Clarification 7 and FR-014
  always refer to them as a triad ("the shared next-invocation lifecycle/event-log seam").
- `src/runtime/next/` top-level modules (`decision.py`, `runtime_bridge.py`) already freely
  import `specify_cli.*` domain modules — `decision.py:188` already imports
  `specify_cli.mission_v1.events.read_events` (the read counterpart of the `emit_event`
  call `_emit_mission_next_invoked` needs), `runtime_bridge.py:319` and `decision.py:33`
  already import `specify_cli.mission_metadata`. This is direct precedent for placing the
  seam at the top level of `src/runtime/next/`, not inside `_internal_runtime/`.
- Not `src/specify_cli/orchestrator_api/`: the operator ruling (SPEC-FRESH2-001) explicitly
  rejected inlining into the orchestrator-api layer — "Inlining would put orchestrator-api
  code in reach of CLI-layer helpers... and would duplicate logic that then drifts from the
  CLI's own copy."
- Not a new top-level package: the charter's "Internal Runtime Boundary" section is
  explicit that mission-runtime behavior used by `spec-kitty next` lives inside this repo's
  existing runtime home; a new package needs its own ADR-level justification this mission
  does not need to invent.
- Placing the seam alongside `runtime_bridge.py`/`decision.py` also means `answer-decision`
  (FR-013/WP08) makes ONE set of imports from ONE package (`runtime.next`) for both the two
  engine calls it wraps AND the lifecycle/event-log seam, instead of reaching into two
  different layers for the same verb.

**Consequence**: `next_cmd.py`'s three call sites (`next_cmd.py:244`, `:251-258`, `:263-269`)
become thin callers of `runtime.next.next_invocation_lifecycle.{pair_previous_lifecycle_record,
emit_mission_next_invoked, write_issuance_lifecycle_record}` — a behaviour-preserving
refactor (WP02), covered by a shared regression test
(`tests/specify_cli/cli/commands/test_next_invocation_lifecycle_seam.py`) that WP02 writes
red-then-green against the CLI path and WP08 extends against the orchestrator-api
`answer-decision` path (SC-008).

## 2. `design-status` (FR-010) does not delegate to an existing DAG engine

Per spec Clarification 6 (already ruled on at spec phase, carried forward here so the
tasks-phase author does not re-derive it): `design-status` implements its own narrow,
side-effect-free reduction over on-disk artifact presence
(`spec.md`/`plan.md`/`tasks/`-finalization/`analysis-report.md`) and the
`decisions/index.json` ledger — NOT a delegation to
`runtime.next._internal_runtime.planner.resolve_next_workflow_action` (wrong output shape:
WP-loop `action`/`wp_id`/`prompt_file`, not design-phase `current_phase`/`next_action`/
`open_decisions`) or `decide_next`'s query path (side-effecting: `get_or_start_run`
materializes a runtime run, which a read-only status verb must not trigger).

## 3. `record-analysis` (FR-005/NFR-004) bypasses the unbounded dossier-sync trigger

Per NFR-004(b)'s own offered mitigation: rather than trusting `record_analysis`'s exit
behavior (SK-93: observed exiting 124 under an operator-imposed `bash timeout 300` wrapper
while the artifact had, in fact, already been written correctly), `record-analysis` either
calls `write_analysis_report`/`commit_for_mission` directly (skipping
`trigger_feature_dossier_sync_if_enabled`'s unbounded-hang exposure entirely) or wraps the
full `record_analysis` call in an explicit, enforced timeout. The choice between the two is
left to WP04's implementer (not frozen at plan time — an implementation-detail call, not an
architecture decision) as long as the artifact re-read + freshness correlation (NFR-004(a))
is the actual success signal either way. See plan.md section (j) for the full mechanism.

## 4. WP01 T002 — `next_cmd.py:425` type-suppression resolved by narrowing (2026-09-02)

**Resolution chosen: NARROW**, not justify-and-keep. Read
`write_paired_completion`'s signature (`src/specify_cli/invocation/lifecycle.py:315-322`):
its `phase` parameter is declared `phase: ProfileInvocationPhase`, where
`ProfileInvocationPhase = Literal["started", "completed", "failed"]`
(`src/specify_cli/invocation/record.py:241`). The local `phase` variable in
`_pair_previous_lifecycle_record` (`next_cmd.py:415-419`) was annotated plain `str` even
though both branches only ever assign it one of the literal string values `"completed"` /
`"failed"` — a strict subset of `ProfileInvocationPhase` — so the mismatch was a
type-annotation gap, not a genuine runtime incompatibility.

**Fix**: annotated the local variable with the function's own canonical type,
`phase: ProfileInvocationPhase = "completed"` (importing `ProfileInvocationPhase` from its
canonical source `specify_cli.invocation.record`, added to the function's existing local
import block alongside `write_paired_completion` et al.), and deleted the bare
`# type: ignore[arg-type]` comment on the `write_paired_completion(..., phase=phase, ...)`
call entirely. No behavioural change — the two assigned values are unchanged string
literals; only the declared type became precise enough for mypy to verify the call
without a suppression. This closes the class WP02 flagged (a public, module-level
function must not carry forward a private module's un-investigated suppression).

**Re-confirmed spot-check of `orchestrator_api/commands.py` / `envelope.py`** (plan.md
§ (g)'s own spot-check, re-run at WP01's actual implementation time since plan time has
passed): `envelope.py` read in full (210 lines) — zero `# noqa` / `# type: ignore`
anywhere, including `make_envelope`, `parse_and_validate_policy`, `policy_to_dict`, and
the `CONTRACT_VERSION` changelog block (lines 19-28). `commands.py`'s `start-review`
verb (lines 1379-1460, the exact precedent function cited in plan.md § (e) item 13) read
in full — also clean, no suppressions. **The spot-check still holds** — no intervening
commit introduced a suppression in either file's cited surface.
