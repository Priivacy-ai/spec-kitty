# Command Contracts: deterministic write commands

CLI command contracts for the deterministic writers. All route through `write_target(kind)` + `commit_for_mission`; all emit the structured write-routing result (data-model I-W1/I-W2); all are idempotent (FR-012).

## `acceptance-verdict` (FR-001)
- **Inputs**: `--mission <handle>`, `--criterion <id>`, `--result <pass|fail|pending>`, `--verification-method <text>`, `--evidence <text?>`, `--actor <name>`, `--json`.
- **Behavior**: mutates the criterion row on `acceptance-matrix.json`, recomputes `overall_verdict` (never authored), preserves negative-invariant provenance, routes to COORD.
- **Also**: canonical `accept` persists the recomputed `overall_verdict` even with no negative invariants (I-A2; #2318 comment).
- **Output**: `{ok, kind:"ACCEPTANCE_MATRIX", destination_surface, row_or_entry_ref, overall_verdict}`.
- **Errors**: unknown criterion → actionable error; unroutable → zero-write refusal (I-W2).

## `issue-verdict` (FR-003)
- **Inputs**: `--mission <handle>`, `--issue <#ref>`, `--status <open|addressed|not_applicable|verified>`, `--wp <id?>`, `--evidence <text?>`, `--actor <name>`, `--json`.
- **Behavior**: mutates the row (keyed by `issue_ref`) on `issue-matrix.json`; migrates the mission from legacy `.md` on first write (FR-013); routes to COORD. No markdown render.
- **Output**: `{ok, kind:"ISSUE_MATRIX", destination_surface, row_or_entry_ref, migrated}`.

## `tracer-append` (FR-006)
- **Inputs**: `--mission <handle>`, `--category <tooling-friction|approach|design-decisions>`, `--entry <text>`, `--actor <name>` (required, non-empty), `--json`.
- **Behavior**: appends a dated attributed entry routed to the COORD surface via `commit_for_mission`; **zero** lane-branch `kitty-specs/` commit; idempotent on identical content; never uses the `read_dir(RETROSPECTIVE)` short-circuit.
- **Output**: `{ok, kind:"TRACER_FILE", destination_surface:"coord", row_or_entry_ref}`.
- **Errors**: empty `--actor` → actionable error (guard #2960).

## `issue-matrix migrate` (FR-013)
- **Inputs**: `--mission <handle?>` (omit for all missions), `--json`.
- **Behavior**: shared migration sub-module — converts legacy `issue-matrix.md` → `issue-matrix.json`; one-shot bulk swap-over when `--mission` omitted. Same sub-module backs failover-read + migrate-on-write.
- **Output**: `{ok, migrated_missions:[...], skipped:[...]}`.

## Discovery / gate behavior (FR-004, FR-005)
- `detect_issue_references(paths)` scans `spec.md`+`tasks/`+`plan.md`+`research.md`+`analysis-report.md`+`contracts/` (one shared canonical definition).
- A new merge-time issue-matrix completeness gate is added to `merge_gates.py`.
- Post-merge review + gates record Gate 4 `not_applicable` when zero canonical references exist; fail-closed when references exist.
