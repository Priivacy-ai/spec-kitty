---
work_package_id: WP03
title: Honest remediation text and flag discoverability
dependencies:
- WP01
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-008
- NFR-002
- NFR-003
planning_base_branch: fix/accept-path-remediation-honesty-3730
merge_target_branch: fix/accept-path-remediation-honesty-3730
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-remediation-honesty-3730. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-remediation-honesty-3730 unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
phase: Phase 1 - Implementation
history:
- timestamp: '2026-08-25T00:00:00Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: src/specify_cli/validators/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/validators/paths.py
- src/specify_cli/cli/commands/accept.py
- tests/agent/test_validators_unit.py
- tests/specify_cli/cli/commands/**
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Make `format_errors()`'s strict-mode failure text honest about what "required" means in this
run's mode, and lead the operator to `--lenient` as a legitimate alternative — both in the
failure text itself and in `--lenient`'s `--help` string. This is the mission's namesake
defect (#3730). Depends on WP01+WP02 landing first so the wording describes the post-dedup,
resolved-path world, not the pre-fix one.

## Context

Today, `format_errors()` (`src/specify_cli/validators/paths.py`) ends with the unconditional
line:

```python
lines.append("These directories are required by the active mission. Create them before continuing.")
```

This asserts an unconditional requirement that `accept --lenient` immediately disproves — it
accepts the mission without creating the directories. The message never mentions `--lenient`,
and `accept.py`'s `--lenient` `typer.Option` help string (`"Skip strict metadata validation"`,
`:643`) never mentions path conventions, so an operator with a legitimately different repo
layout has no discoverable path off the failure short of reading source.

**Design (combining three of #3730's four candidate directions, per the tracer's settled
decision — implement exactly as specified, not re-derived)**:

- `format_errors()` gets **no new parameter**. There are exactly two call sites for
  `format_errors()` in the whole codebase — `PathValidationError.__init__` (reached only via
  `validate_mission_paths(..., strict=True)`) and `evaluate_path_conventions`'s
  `if strict_metadata:` branch (the function's *other* branch calls `format_warnings()`
  instead, never `format_errors()`) — both already reachable only when the caller is in the
  strict/blocking branch. Since `format_errors()` is by construction only ever invoked in the
  strict/blocking context, a mode-signal boolean parameter would be a compile-time-constant
  argument at every call site — an untested, unreachable `False` branch the charter's Sonar
  Expectations forbid. Instead, the new `--lenient`-pointer wording is added
  **unconditionally** to `format_errors()`'s existing trailing prose — no new parameter, no
  branch, no dead/untested code.
- Replace the unconditional line above with new fixed wording — unconditional in the sense of
  "always this text" (no branch on mode, since `format_errors()` is itself only ever reached
  from strict mode) but honest in content: it (a) does not claim an unconditional requirement,
  and (b) names `--lenient` as a remedy **before** the `mkdir -p` suggestion, with `mkdir -p`
  explicitly marked secondary/optional. Follow spec's own AC4 wording pattern: state the
  `--lenient` pointer first, then "... or, if you want to adopt the convention:
  `mkdir -p ...`" for each suggestion already present in `self.suggestions`. Example shape
  (adapt wording, keep the order and the honesty properties):
  > "Run `accept --lenient` to treat these as warnings instead of blocking errors — or, if you
  > want to adopt the convention, create them: `mkdir -p <path>`"
- `suggest_directory_creation`'s list content and `format_warnings()`'s consumption of it are
  **untouched** — WP3 only changes the trailing prose `format_errors()` appends after the
  shared `suggestions` list, never the list itself. This is the explicit, checkable guard
  against #2330 (out of scope): #2330's complaint is specifically about the `--lenient`
  warning print (i.e. `format_warnings()`'s output), which this mission does not touch.
- `accept.py:643`'s `--lenient` `typer.Option(..., help="Skip strict metadata validation")` is
  widened to also name path-convention enforcement explicitly (FR-006 / SC-003's `--help`
  requirement).

**Terminology canon (NFR-003)**: the new `format_errors()` trailing prose and the widened
`--lenient` help string use "Mission"/"mission" only, never "feature"/"feature*" (per
`AGENTS.md`'s Terminology Canon). Independently enforced by
`tests/architectural/test_no_legacy_terminology.py` (runs in the always-on `arch-adversarial`
job, not `core_misc`).

## ⚡ Subtask T010: Rewrite `format_errors()`'s trailing prose

**Purpose**: FR-004/FR-005 — make the "required" claim accurate for the run's mode and name
`--lenient` before `mkdir -p`, per AC4's ordering requirement.

**Required section order** (this is the concrete fix — implement this order directly, do not
discover it via T012's test failing first): today, `format_errors()` builds `lines` as
`"Path Convention Errors:"` → per-`self.warnings` lines → (if `self.suggestions`) a blank
line, `"Required Actions:"`, and the per-suggestion `mkdir -p`/`touch` lines → a final blank
line → the unconditional `"These directories are required..."` sentence. Appending new
`--lenient` wording only at that same trailing position (i.e. literally "replacing the two
trailing lines" in place) renders it **after** `"Required Actions:"`'s `mkdir -p` lines,
failing T012's own `output.index("--lenient") < output.index("mkdir -p")` assertion. The
required fix is a genuine reorder, not a text swap: the new `--lenient`-pointer sentence must
be appended to `lines` **immediately after the per-`self.warnings` loop and BEFORE** the
`if self.suggestions:` / `"Required Actions:"` block runs. The `"Required Actions:"` block
itself is not deleted or edited in content — it still renders after the per-warning lines,
now simply after the new sentence instead of being the first thing to appear post-warnings.

**Steps**:
1. In `src/specify_cli/validators/paths.py`, `PathValidationResult.format_errors()`, locate
   the `for warning in self.warnings: lines.append(...)` loop, the `if self.suggestions:` /
   `"Required Actions:"` block that currently follows it, and the two trailing lines after
   that block:
   ```python
   lines.append("")
   lines.append("These directories are required by the active mission. Create them before continuing.")
   ```
2. Delete the two trailing lines above entirely — do not keep this wording anywhere else in
   the method.
3. Immediately after the `for warning in self.warnings:` loop's closing line and **before**
   the `if self.suggestions:` block, insert a blank line then the new `--lenient`-pointer
   sentence(s). The new wording must:
   - Not assert an unconditional "required" claim — avoid phrasing like "are required"
     standing alone; frame it as required *for strict acceptance*, or similar mode-scoped
     language.
   - Name `--lenient` (or an unambiguous equivalent pointer, e.g. `accept --lenient`) as a
     remedy. Because this text is now inserted before the `if self.suggestions:` block runs,
     it is structurally guaranteed to render before any `mkdir -p` text the "Required
     Actions:" block later appends — this ordering is now a direct consequence of insertion
     position, not a claim to verify after the fact.
   - Mark the upcoming `"Required Actions:"` / `mkdir -p` suggestions (rendered immediately
     after this sentence, unchanged in content) as the secondary/optional path — e.g. "Run
     `accept --lenient` to treat these as warnings instead of blocking errors — or, if you
     want to adopt the convention, see the commands below:" (adapt wording; keep the ordering
     and honesty properties).
   - Use "Mission"/"mission" terminology only (NFR-003) — no "feature"/"feature*" wording.
4. Do **not** add a new parameter to `format_errors()`. Do not touch `format_warnings()` or
   `suggest_directory_creation` in this subtask.
5. Confirm the resulting rendered order is: `"Path Convention Errors:"` → per-warning lines →
   the new `--lenient`-first sentence → (if `self.suggestions`) `"Required Actions:"` and its
   `mkdir -p`/`touch` lines. Since the new sentence is now structurally positioned before the
   suggestions block by construction, T012's order assertion is a confirmation of this design,
   not a discovery mechanism for it.

**Files**: `src/specify_cli/validators/paths.py`.

**Validation**: T012's string-order and string-content assertions; manual read of the
rendered `format_errors()` output for a realistic fixture.

---

## ⚡ Subtask T011: Widen `--lenient`'s `--help` string in `accept.py`

**Purpose**: FR-006 / SC-003 — give `--help` a second, independent discovery path to the same
information as the failure text.

**Steps**:
1. In `src/specify_cli/cli/commands/accept.py`, locate the `--lenient` option definition
   (around `:643`):
   ```python
   lenient: bool = typer.Option(False, "--lenient", help="Skip strict metadata validation"),
   ```
2. Widen the `help=` string to also mention path-convention enforcement explicitly — e.g.
   `"Skip strict metadata validation and downgrade missing path-convention checks to
   warnings"` (adjust wording; the assertion this must satisfy is that the string contains
   "path", per T012). Use "Mission"/"mission" terminology if referencing the mission at all
   (NFR-003) — no "feature"/"feature*" wording.
3. Do not change the flag's name, default, or behavior — only its help text (spec's Non-Goals:
   "Renaming or reworking the `--lenient` flag itself... only its `--help` text and its
   discoverability from the failure output are in scope").

**Files**: `src/specify_cli/cli/commands/accept.py`.

**Validation**: T012's `--help` assertion test.

---

## ⚡ Subtask T012: Write the WP3 revert tests + #2330 non-regression re-run

**Purpose**: Red-first proof for FR-004/FR-005/FR-006 (User Story 3, all five Acceptance
Scenarios) plus the explicit #2330 non-regression guard.

**Steps**:
1. **String-order + content test**: on `format_errors()`'s output for a missing declared path
   in strict mode, assert:
   - The string `"--lenient"` appears in the output.
   - It appears **before** any `mkdir -p` occurrence (string-order assertion, per AC4) — use
     `output.index("--lenient") < output.index("mkdir -p")` or equivalent.
   - The output does **not** contain the unconditional phrase "are required by the active
     mission" (or any equivalent unconditional-requirement phrasing that survived from the
     old text) standing alone without mode-scoping.
2. **`--help` test**: invoke `spec-kitty accept --help` (e.g. via `CliRunner` from
   `typer.testing`) and assert the `--lenient` help string mentions "path" (path-convention
   wording).
3. **#2330 non-regression guard**: re-run the existing pinned
   `test_lenient_path_convention_warning_is_rendered_in_console` test (from
   `tests/specify_cli/cli/commands/test_accept_warnings_render.py`) **unmodified** — confirm
   `format_warnings()`'s output is byte-for-byte unaffected by WP3's change to
   `format_errors()`. This is not a new test to write; it's confirmation the existing pinned
   test still passes with zero edits after T010/T011 land.
4. Run the two new tests against pre-T010/T011 code first to confirm genuinely red, then
   implement T010/T011 and re-run to confirm green. Re-run the pinned test at both points to
   confirm it was green throughout (never touched).

**Files**: `tests/agent/test_validators_unit.py`, `tests/specify_cli/cli/commands/`.

**Validation**: `pytest <chosen files> -v` — the two new tests red before T010/T011, green
after; the pinned #2330 guard test green at both points, unmodified.

## Definition of Done

- T010-T012 all recorded via `spec-kitty agent tasks mark-status <Txxx> --status done`
  (event-sourced status).
- T012's two new tests are red against pre-T010/T011 code and green after (NFR-001).
- The three SC-005 pinned tests remain green, **unmodified**, including specifically
  `test_lenient_path_convention_warning_is_rendered_in_console` as the explicit #2330 guard
  (NFR-002).
- `format_warnings()`'s output and `suggest_directory_creation`'s list content are
  byte-for-byte unchanged by this WP (verified by the pinned lenient-render test staying
  green, unmodified).
- `--lenient`'s existing downgrade-to-warning behavior for missing paths is unchanged
  (FR-008) — verified by the same pinned test plus manual confirmation the flag's semantics
  were not touched, only its help text and `format_errors()`'s prose.
- All new/changed operator-facing strings use "Mission"/"mission" only (NFR-003) —
  `tests/architectural/test_no_legacy_terminology.py` stays green (runs via `arch-adversarial`,
  not blocked on a local run being required, but worth a local check if feasible).
- Full baseline re-run: `pytest tests/specify_cli/acceptance/ tests/specify_cli/cli/commands/test_accept_warnings_render.py tests/agent/test_validators_unit.py tests/characterization/test_trio_json_envelope.py -q`
  completes with 0 failed (per plan.md's "Baseline honesty" section), in addition to the three
  SC-005 pinned tests above.
- `ruff`/`mypy` clean on touched files.

## Risks

- **Ordering fragility**: the "`--lenient` before `mkdir -p`" requirement is a plain
  string-index assertion — a future edit to `format_errors()`'s section ordering (e.g. moving
  "Required Actions:" earlier) could silently break this without an obviously-related diff.
  Mitigation: T012's order assertion is the guard; keep it as a direct index comparison, not a
  looser "both present" check.
- **#2330 scope creep risk**: it would be easy to "fix" `format_warnings()`'s wording too while
  touching this file, since it shares the same `suggestions` list. This is explicitly
  out-of-scope (spec.md Edge Cases, Non-Goals) — resist the temptation; `format_warnings()`
  must remain byte-for-byte unchanged.
- **owned_files overlaps (full accounting, re-derived from `wps.yaml` live)**: this WP's
  `owned_files` overlap with both WP01 and WP02 (no overlap with WP04 — WP04's single owned
  file is under `tests/specify_cli/acceptance/**`, a glob this WP does not own). Deliberate —
  WP01→WP02→WP03→WP04 is a strict linear chain, never concurrent; the no-overlap convention
  for parallel-write collisions does not apply:
  - **WP01** on `src/specify_cli/validators/paths.py` (both WPs edit this file) and on
    `tests/agent/test_validators_unit.py` (both WPs' test coverage lives here — WP01's
    T003/T004 and WP03's T012).
  - **WP02** on `src/specify_cli/cli/commands/accept.py` (both WPs edit this file) and on the
    `tests/specify_cli/cli/commands/**` glob (both WPs' test coverage lives here — WP02's T009
    and WP03's T012).

## Reviewer Guidance

- Confirm `format_errors()` received **no new parameter** — the design explicitly forbids
  this (compile-time-constant boolean argument = untested dead branch, forbidden by the
  charter's Sonar Expectations).
- Confirm the string-order assertion genuinely reflects the rendered output a real operator
  would see — read the full `format_errors()` output for a realistic fixture, not just the
  test's isolated substrings.
- Confirm `format_warnings()` and `suggest_directory_creation` were not touched at all (diff
  review) — this is the concrete #2330 guard (C-002 also relevant: no change to what's
  enforced).
- Confirm the widened `--lenient` help string does not change the flag's name, default, or
  parsing behavior — only its `help=` text.
- Confirm NFR-003 terminology compliance on every new/changed string introduced by this WP.

---

Run `spec-kitty agent action implement WP03 --agent claude` to begin implementation.
