---
work_package_id: WP01
title: 'Parity floor: byte-freeze suite + LOC ceiling gate'
dependencies: []
requirement_refs:
- FR-005
- FR-011
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation (parity floor)
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "297729"
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/agent/
create_intent:
- tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py
- tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json
- tests/architectural/test_tasks_command_surface.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py
- tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json
- tests/architectural/test_tasks_command_surface.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 – Parity floor: byte-freeze suite + LOC ceiling gate

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.

---

## Objectives & Success Criteria

Land the mission's parity floor BEFORE any production code moves (spec C-003, parity-ATDD):

1. **Byte-freeze suite**: 13 byte-exact stdout cases — one per JSON emission site of
   `src/specify_cli/cli/commands/agent/tasks.py` — green against the UNTOUCHED tree.
2. **LOC ceiling gate**: `tests/architectural/test_tasks_command_surface.py` asserting
   `tasks.py` ≤ 4569 LOC, with a self-mutation proof (DIRECTIVE_043 non-vacuity).
3. Zero production changes in this WP. `git diff src/` must be empty.

Success = FR-005 pre-step + FR-011 initial ceiling delivered; every later WP is guarded.

## Context & Constraints

Read FIRST (all in `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/`):
- `contracts/parity-contract.md` — Layer 2 defines this suite's contract.
- `contracts/gate-contracts.md` — Gate 2 defines the LOC ceiling form + ratchet protocol.
- `research.md` D3 (site→subcommand map with trigger conditions) and D4 (harness design)
  — your emission-site inventory. D2 explains byte semantics ("compact" = default
  separators `(', ', ': ')`, NOT `separators=(',',':')`).
- `tracers/tooling-friction.md` — the typer/venv trap is real; T001 exists because a
  drifted venv produces wrong fixture bytes that CI then rejects.

Charter: `.kittify/charter/charter.md` (Testing Requirements — targeted surfaces;
realistic production-shaped test data is a standing order).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T001 – Pin venv to uv.lock; verify typer version

- **Purpose**: Byte fixtures frozen against a drifted typer/rich are poisoned (Wave 1 trap).
- **Steps**: `uv sync --frozen`; then `python -c "import typer, rich; print(typer.__version__, rich.__version__)"` and compare against `uv.lock`. Record both versions in the Activity Log.
- **Files**: none (environment only).

### Subtask T002 – Identify/prepare production-shaped fixture scenarios

- **Purpose**: Each emission site needs a CLI invocation that deterministically reaches it.
- **Steps**:
  1. Study how `test_tasks_cli_contract.py` builds its fixture project (repo/mission scaffolding, `fixtures/tasks_cli/json/envelopes.json` argv patterns) — reuse its fixtures/conftest machinery wherever possible; do NOT build a parallel scaffold if the existing one reaches the site.
  2. For each row of the research.md D3 table, determine the argv + repo state that triggers the site (success legs: `list-tasks --json`, `map-requirements --json`, `validate-workflow <id> --json`, `list-dependents <wp> --json`, `status --json`, `add-history … --json`; error legs: missing `--mission` (508), generic error (559), mark-status no-IDs (2477), map-requirements unknown-WP (3349), malformed ref (3474), unknown spec IDs (3488), stale refs (3585)).
  3. Use production-shaped data: real-format mission slugs (`<slug>-<mid8>` with a valid ULID prefix), real WP ids (`WP01`), realistic file contents — never `foo`/`bar` placeholders.
- **Notes**: If a site proves unreachable through the public CLI without unreasonable state (document which), pin it with a focused unit test on the emitting helper capturing stdout via `capsys` — record the deviation in the Activity Log and the tracer. Every one of the 13 sites MUST end up byte-pinned by one mechanism or the other.

### Subtask T003 – Author `byte_contracts.json` — 12 compact cases

- **Purpose**: The byte-level contract the shape-checked harness never provided.
- **Steps**: Create `tests/specify_cli/cli/commands/agent/fixtures/tasks_cli/json/byte_contracts.json`: `{ "<case-name>": {"argv": [...], "exit_code": N, "expected_stdout": "<exact bytes incl. trailing newline>", "site": "tasks.py:<line> <subcommand>/<leg>"} }`. Freeze `expected_stdout` from an actual run on the untouched tree (write a tiny throwaway freeze script or run the runner in a REPL; do NOT hand-compose JSON strings).
- **Files**: the fixture file (new).
- **Notes**: Where output embeds absolute paths/timestamps, prefer scenarios that avoid them; if unavoidable, normalize via a documented placeholder substitution in the test (keep it byte-deterministic). CT5 guard: byte equality only — no `len()==N` assertions anywhere in this suite.

### Subtask T004 – Add the status indent=2 byte case

- **Purpose**: Pins the `_StatusRender` leg (tasks.py:1222–1235, printed at :4117) that WP04 collapses.
- **Steps**: One more fixture entry: `status --json` on the fixture mission; `expected_stdout` is the indented JSON exactly as emitted today.

### Subtask T005 – Write `test_tasks_json_bytes.py`

- **Purpose**: The runner asserting byte equality for all 13 cases.
- **Steps**:
  1. Mirror the CliRunner setup of `test_tasks_cli_contract.py` (in-process `typer.testing.CliRunner`, same app import).
  2. Parametrize over `byte_contracts.json`; assert `result.exit_code == spec["exit_code"]` and `result.stdout == spec["expected_stdout"]`.
  3. `pytestmark = [pytest.mark.fast]` plus whatever the sibling contract test carries (match it exactly — gate-visibility, FR-009).
- **Files**: `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py` (new, ~120–180 lines).
- **Validation**: `PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py -q` → 13 passed on the untouched tree.

### Subtask T006 – Land the LOC ceiling gate @4569 + self-mutation proof [P]

- **Purpose**: The anti-regrowth ratchet every later WP lowers (gate-contracts.md Gate 2).
- **Steps**:
  1. New `tests/architectural/test_tasks_command_surface.py` with an extracted check function `def _loc_of(source: str) -> int` and `_CEILING = 4569`; the gate reads `src/specify_cli/cli/commands/agent/tasks.py` and asserts `_loc_of(text) <= _CEILING` with the remediation message from gate-contracts.md.
  2. Self-mutation test: feed a synthetic string of `_CEILING + 1` lines to the check and assert the comparison fails (test the extracted function — never mutate the live file).
  3. Markers: match the conventions of existing `tests/architectural/` files (they are selected by the `git_repo or integration or architectural` CI shard + `fast` where applicable — copy a neighbor's pytestmark).
  4. Leave an explicit `# _CEILING ratchet-down protocol` comment citing FR-011: each relocation WP lowers `_CEILING` to the achieved size in the same commit; final `min(achieved, 1400)`; >1400 = operator escalation.
- **Files**: `tests/architectural/test_tasks_command_surface.py` (new; the AST dumps gate is added to this same file by WP09 — leave a placeholder comment naming that).
- **Parallel?**: independent of T002–T005.

## Test Strategy

Targeted surface for this WP (declare in the review):
```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py \
  tests/architectural/test_tasks_command_surface.py \
  tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py -q -p no:cacheprovider
python -m mypy --strict tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py tests/architectural/test_tasks_command_surface.py src/specify_cli/cli/commands/agent/tasks.py
ruff check tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py tests/architectural/test_tasks_command_surface.py
```

## Risks & Mitigations

- **Poisoned fixtures from venv drift** → T001 first, versions logged.
- **Nondeterministic output (paths/timestamps)** → prefer avoiding scenarios; documented normalization otherwise.
- **A site unreachable via CLI** → helper-level capsys pin + tracer note (never silently skip a site).
- **Gate theater** → the self-mutation test is mandatory; the gate tests the extracted function, not a mock of it.

## Review Guidance

- Verify `git diff src/` is EMPTY (this WP is tests-only).
- Verify all 13 sites of research.md D3 are pinned (count fixture entries + any helper-level pins; 13 total, no gaps).
- Verify byte assertions (`==` on full stdout), zero `len()==N` patterns.
- Run the self-mutation test; comment out the ceiling assert locally and confirm the theater test still guards.
- Verify markers make both new files CI-gate-visible (FR-009 census will list them).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append at the END. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
- 2026-07-02T13:38:05Z – claude:fable:python-pedro:implementer – shell_pid=268505 – Assigned agent via action command
- 2026-07-02T13:54:38Z – claude:fable:python-pedro:implementer – shell_pid=268505 – Ready for review: 13/13 byte cases (coverage-verified site execution, 2-pass deterministic freeze) + LOC gate @4569 w/ self-mutation proof + live red-fire demo; mypy --strict clean (new tests + tasks.py), ruff clean (diff-scoped sweep exit 0); git diff src/ empty
- 2026-07-02T13:57:00Z – claude:fable:python-pedro:implementer – shell_pid=268505 – T001: venv verified against uv.lock, NO drift — typer 0.24.2, rich 15.0.0, click 8.3.3 (installed == uv.lock); safe to freeze fixtures. `uv sync --frozen` not run (primary-checkout venv not this WP's to mutate); versions verified via importlib.metadata instead.
- 2026-07-02T13:58:00Z – claude:fable:python-pedro:implementer – shell_pid=268505 – T002–T004: all 13 D3 sites reached via the PUBLIC CLI (in-process CliRunner + tests/mocked_env.setup_mocked_env; ZERO helper-level capsys deviations needed). Fixture mission production-shaped: slug checkout-latency-audit-01KWG4RZ, mission_id 01KWG4RZ8Q3TCEH2M5N7P9RSTV (valid 26-char Crockford ULID), WP01/WP02 with real spec/tasks content. Freeze script ran each case under coverage.py (include=tasks.py) asserting the target emission line executed, ran the WHOLE freeze twice and diffed (byte-identical) before writing byte_contracts.json. Determinism deviation (documented in-suite): list-tasks embeds str(task_file) absolute paths — tmp root normalized to `<TMP>` placeholder at freeze AND assert time (the only stdout transformation). Parity notes frozen as-is: list-dependents emits "depends_on": ["[]"] (extract_scalar quirk on empty YAML list) and status by_lane shows `genesis` for event-less WPs — current-tree behavior, pinned not fixed (parity floor).
- 2026-07-02T13:59:00Z – claude:fable:python-pedro:implementer – shell_pid=268505 – T005–T006: test_tasks_json_bytes.py (pytestmark = pytest.mark.fast, matching sibling contract test exactly) asserts full-stdout byte equality + exit codes for all 13 cases plus a 13-count/keying completeness test; zero len()==N patterns (CT5). tests/architectural/test_tasks_command_surface.py (pytestmark = [architectural, fast]) lands Gate 2: _loc_of extracted check, _CEILING=4569, ratchet-down protocol comment citing FR-011 (min(achieved,1400); >1400 = blocked + operator escalation), WP09 Gate-1 placeholder comment, self-mutation theater test (_CEILING+1 synthetic source fires) + exact-boundary test + target-exists sanity. Live red-fire demo: ceiling temporarily 4568 → gate FAILED with the gate-contracts remediation message (4569 <= 4568), restored. Validation: 45/45 targeted suite green (14 byte + 4 gate + 27 sibling contract, unmodified fixtures); marker gates green (convention+correctness+census, 9 passed); mypy --strict on both new files + src tasks.py together: Success, 0 issues; ruff diff-scoped sweep exit 0. Commit 3f89130bf on lane-a (tests-only; git diff src/ empty).
- 2026-07-02T13:57:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=297729 – Started review via action command
- 2026-07-02T14:04:10Z – user – shell_pid=297729 – Review passed (reviewer-renata, opus): 8/8 criteria; 45 tests + live red-fire of the LOC gate verified by the reviewer; approval recorded by orchestrator after fixing the unrelated issue-matrix Gate-4 hygiene gap
