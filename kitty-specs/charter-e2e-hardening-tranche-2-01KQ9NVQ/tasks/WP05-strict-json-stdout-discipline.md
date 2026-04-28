---
work_package_id: WP05
title: Strict --json Stdout Discipline (#842)
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: fix/charter-e2e-827-tranche-2
merge_target_branch: fix/charter-e2e-827-tranche-2
branch_strategy: Planning artifacts for this feature were generated on fix/charter-e2e-827-tranche-2. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-e2e-827-tranche-2 unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
agent: claude
history:
- at: '2026-04-28T09:36:40Z'
  actor: spec-kitty.tasks
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/
execution_mode: code_change
mission_slug: charter-e2e-hardening-tranche-2-01KQ9NVQ
model: claude-sonnet-4-6
owned_files:
- src/specify_cli/auth/**
- src/specify_cli/events/sync.py
- src/specify_cli/events/sync_client.py
- tests/specify_cli/test_json_output_discipline.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Run `/ad-hoc-profile-load implementer-ivan` before reading further.

## Objective

Make every `--json` command emit exactly one JSON document on stdout. Route SaaS sync / auth / background diagnostics to stderr or into a structured `warnings` field inside the JSON envelope. Add a per-command strict-parse test covering the four `--json` paths the strict E2E exercises.

Closes (with strict E2E gate): `#842`. Satisfies: `FR-005`, `NFR-006`.

## Context

- **Spec FR-005**: exactly one JSON document on stdout; SaaS diagnostics go to stderr or envelope.
- **Research R3** (`research.md`): identifies emission sites (likely `src/specify_cli/auth/` or `src/specify_cli/events/sync*`).
- **Brief**: `start-here.md` "JSON mode must be strict and machine-safe" section.
- **Important**: deterministic E2E does NOT enable `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. SaaS-touching tests gate behind that env var.

## Branch Strategy

- Mission planning/base branch: `fix/charter-e2e-827-tranche-2`
- Mission merge target: `fix/charter-e2e-827-tranche-2`
- Execution worktree: assigned by `finalize-tasks`. Enter via `spec-kitty agent action implement WP05 --agent <name>`.

## Subtasks

### T020 — Audit SaaS sync / auth / background diagnostic emission sites

**Purpose**: Find every place that prints diagnostics to stdout while a `--json` command is rendering.

**Steps**:
1. Read research R3 file:line refs.
2. `git grep -n "print(" src/specify_cli/auth src/specify_cli/events` (and similar locations).
3. `git grep -n "stdout" src/specify_cli` for explicit stdout writes outside the JSON serializer.
4. Look for `rich.print` / `console.print` calls that default to stdout.
5. Identify which of the four E2E `--json` paths (`charter generate`, `charter bundle validate`, `charter synthesize`, `next`) trigger which emission sites.
6. Record findings in a short audit note (commit message or PR description).

**Files**: read-only sweep across `src/specify_cli/`, `src/charter/`.

### T021 — Route diagnostics to stderr or structured warnings envelope

**Purpose**: Eliminate stdout leaks. Choose per-site whether to route to stderr or fold into the JSON envelope's `warnings` field.

**Steps**:
1. For SaaS sync / auth diagnostics that are operationally important: route to stderr (so logs/diagnostics still land in CI) AND/OR fold into the JSON envelope's optional `warnings` array.
2. For purely informational background output: route to stderr; do not pollute envelope.
3. Avoid suppressing diagnostics entirely — they are useful when SaaS sync IS enabled. Just don't put them on stdout.
4. If a shared "json mode" decorator / context exists in the typer app, prefer changes there. Otherwise fix per-emission-site.

**Files** (likely candidates, confirm with research):
- `src/specify_cli/auth/...` (auth diagnostics)
- `src/specify_cli/events/sync.py` and `sync_client.py` (SaaS sync warnings)

### T022 — Add per-command strict-parse test

**Purpose**: Lock strict stdout discipline with a regression test that fails on any future leak.

**Steps**:
1. Create `tests/specify_cli/test_json_output_discipline.py`.
2. For each of the four commands (`charter generate --json`, `charter bundle validate --json`, `charter synthesize --adapter fixture --dry-run --json`, `next --json`), add a test that:
   - Sets up a fresh project (use the existing fresh-project fixture).
   - Invokes the command via subprocess; captures stdout and stderr separately.
   - Parses stdout with strict full-stream `json.loads(stdout)`. Any trailing non-whitespace fails the test.
   - Asserts stderr is either empty or contains only documented diagnostic markers.
3. Tests must run with `SPEC_KITTY_ENABLE_SAAS_SYNC` unset (the deterministic offline path).
4. Each test references the corresponding contract file in `kitty-specs/<mission>/contracts/` for the expected envelope shape (loose shape check, not full schema validation).

**File**: `tests/specify_cli/test_json_output_discipline.py` (new).

### T023 — Verify SaaS-touching tests still pass

**Purpose**: Ensure the routing change doesn't break tests that intentionally check SaaS sync output.

**Steps**:
1. Identify SaaS-related test files: `git grep -l SPEC_KITTY_ENABLE_SAAS_SYNC tests/`.
2. Run them: `uv run pytest <those-files> -q`.
3. If any test fails because it asserted stdout content that now goes to stderr, update the assertion to read from stderr (or from envelope `warnings`).

### T024 — Verify charter/next/specify_cli test trees regression-free

**Steps**:
1. Run `uv run pytest tests/charter tests/next tests/specify_cli -q`. Must exit 0.
2. Run `uv run mypy --strict src/specify_cli` and `uv run ruff check src tests`.

## Test Strategy

- **Per-fix regression coverage**: T022 covers all four `--json` paths (NFR-006).
- **Targeted gates**: `tests/charter`, `tests/next`, `tests/specify_cli`.

## Definition of Done

- [ ] Audit complete; emission sites documented in commit message or PR.
- [ ] All identified leaks routed to stderr or envelope.
- [ ] T022 strict-parse test exists and passes.
- [ ] No regression in SaaS-touching tests (assertions updated where they tolerated broken stdout).
- [ ] `mypy --strict` passes; ruff passes.
- [ ] Owned files only.

## Coordination Notes

- Per-command JSON envelope cleanup that requires editing a charter or next module is owned by that command's WP (WP03, WP04, WP06). This WP owns shared SaaS sync / auth diagnostic plumbing and the new test file.
- If audit surfaces a leak inside a command file owned by another WP, file a coordination note and let that WP fix it. Do not edit other WPs' owned files.

## Risks

- **Audit balloon**: more leak sites than expected. **Mitigation**: stop, list them, decide whether to handle here or hand off to per-command WPs.
- **stderr suppression in test environments**: ensure the strict test captures stderr separately and does not let pytest swallow it.

## Reviewer Guidance

- Run the four `--json` commands manually, confirm each emits exactly one JSON document on stdout.
- Confirm `tests/specify_cli/test_json_output_discipline.py` exists and runs in `<5 seconds`.
- Confirm SaaS-touching tests still pass.

## Implementation command

```bash
spec-kitty agent action implement WP05 --agent <your-agent-key>
```
