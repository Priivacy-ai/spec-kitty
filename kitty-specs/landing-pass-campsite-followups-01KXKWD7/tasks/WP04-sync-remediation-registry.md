---
work_package_id: WP04
title: Sync remediation registry + guard (#2674)
dependencies: []
requirement_refs:
- FR-008
- FR-009
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T030
- T031
- T032
- T033
phase: Phase 1 - Sync hardening
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3692082"
shell_pid_created_at: "1784158296.51"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/sync/preflight.py
- tests/specify_cli/sync/test_preflight_remediation_hints.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Sync remediation registry + guard (#2674)

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
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Single-source **every** sync-preflight remediation sentence and point the command-name
guard at the FULL registry so inline-built commands are validated to resolve — closing
#2674's duplication gap and coverage gap **together**, with byte-identical rendered output.

**Done means:**

- Every remediation sentence emitted by `src/specify_cli/sync/preflight.py` lives in exactly
  ONE named module constant. No sentence is duplicated between the `_REMEDIATION_HINTS` dict
  and the inline `_build_remediation_lines()` builder.
- A module-level `ALL_REMEDIATION_TEXTS` collection is the canonical registry of every
  remediation text.
- The command-resolution guard iterates `ALL_REMEDIATION_TEXTS` (not just the dict), so a typo
  in an inline-only command (`orphan-daemons`, `sync migrate`, `auth login`) now fails the guard.
- **Rendered output is BYTE-IDENTICAL to today** — both the mismatch-hint dict values and the
  `_build_remediation_lines()` bullets render exactly the same strings as before.
- The RED test from T030 fails against the current (narrow) guard and passes once the guard is
  widened; the whole file is green at close.
- `ruff` and `mypy` clean on the touched surface. No new `# noqa` / `# type: ignore`.

## Context & Constraints

**RED-FIRST is binding (C-005).** Write the failing test before touching production code.

Load the mission spec + plan: `kitty-specs/landing-pass-campsite-followups-01KXKWD7/spec.md`,
`plan.md` (see **IC-04**), and `research-notes-csf-2670.md` for the full duplication/coverage trace.
Governance: `.kittify/charter/charter.md`.

**The duplication (S1192 / grep-invisible):** In `src/specify_cli/sync/preflight.py`, two
surfaces emit remediation prose:

- `_REMEDIATION_HINTS` — the dict at ~line 107, keyed by `MismatchField`, consumed by
  `_build_mismatches()` to populate `OwnerMismatch.remediation_hint`.
- `_build_remediation_lines()` — the inline bullet builder at ~lines 289–335, consumed by
  `PreflightResult.render()`.

Only `_RESTART_DAEMON_REMEDY` (~:101) is already hoisted and shared. The remaining two
overlapping sentences are **duplicated**:

- `daemon_server_url` — dict form ~:111-114 vs inline bullet ~:309-312. Semantically identical,
  but the line-wrapping differs, so a naive `grep`/Sonar S1192 pass does **not** flag them.
- `daemon_team_or_user` — dict form ~:115-119 vs inline bullet ~:313-318. Same story.

**The coverage gap:** three commands live ONLY inside `_build_remediation_lines()` and are
never guard-validated:

- `spec-kitty doctor orphan-daemons` (~:321)
- `spec-kitty sync migrate` (~:326)
- `spec-kitty auth login` (the standalone auth-required bullet, ~:332)

The guard tests `test_no_unknown_commands_in_hints` / `test_every_hint_command_resolves_under_help`
(in `tests/specify_cli/sync/test_preflight_remediation_hints.py`, ~lines 118 and 182) iterate
ONLY `_REMEDIATION_HINTS.items()`. So a typo in an inline-only command ships **green** — the
guard never sees those command strings.

**Whack-a-field trap (explicit):** hoisting the two duplicated literals WITHOUT widening the
guard leaves the three inline-only commands unvalidated — the mission's coverage gap stays
open. This WP is **incomplete** unless the guard scans the registry. Do both halves.

**Behavior-preservation constraint:** the two `server_url`/`team_or_user` sentences are already
semantically identical across the two surfaces (only the source line-wrap differs). Concatenated,
they produce the same runtime string. Hoisting them to a shared constant is therefore
behavior-preserving — but you MUST confirm the rendered bytes are unchanged (see Test Strategy).
Note the two surfaces differ in one detail: the inline bullet builder prepends `"  • "` to each
line, while the dict values carry no bullet prefix. The shared constant must hold the **sentence
only**; the bullet builder keeps prepending `"  • "`.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T030 – RED: prove the current guard misses inline-only typos

- **Purpose**: Lock in the coverage gap as a failing test before fixing it. Demonstrates the
  current guard does NOT catch a mistyped inline-only command.
- **Steps**:
  1. In `tests/specify_cli/sync/test_preflight_remediation_hints.py`, add a test that asserts
     the guard SHOULD reject **any** unresolvable command emitted by `_build_remediation_lines()`,
     not just commands in `_REMEDIATION_HINTS`.
  2. Construct a realistic `PreflightResult` (or call `_build_remediation_lines()` directly) with
     `orphan_count > 0`, `legacy_rows > 0`, and `auth_required and not auth_present` so all three
     inline-only bullets render.
  3. Extract the command tokens from the rendered bullets and assert each resolves under
     `--help` (reuse the existing resolution helper the file already uses for the dict commands).
  4. Demonstrate the gap: e.g. parametrically/temporarily show that a typo such as
     `orphan-daemon` (missing the trailing `s`) would pass the **existing** dict-only guard —
     the new assertion over the full registry must be the thing that catches it.
- **Files**: `tests/specify_cli/sync/test_preflight_remediation_hints.py`.
- **Parallel?**: No — the same test file is edited again in T033.
- **Notes**: This test MUST be RED against the current production code (guard iterates only the
  dict). Do not adjust production first. Capture the red output in the Activity Log.

### Subtask T031 – Hoist every remedy sentence to named constants

- **Purpose**: Establish the single canonical source for every remediation sentence.
- **Steps**:
  1. Beside `_RESTART_DAEMON_REMEDY` (~:101), add named module constants for each remaining
     remedy sentence:
     - `_SERVER_URL_REMEDY` — the `daemon_server_url` sentence.
     - `_TEAM_OR_USER_REMEDY` — the `daemon_team_or_user` sentence.
     - `_ORPHAN_REMEDY` — the orphan-cleanup sentence, with a `{count}` placeholder.
     - `_SYNC_MIGRATE_REMEDY` — the legacy-migration sentence, with a `{rows}` placeholder.
     - `_AUTH_LOGIN_REMEDY` — the standalone auth-required sentence.
  2. For the two placeholder constants, keep the placeholder names aligned with how the inline
     builder formats today (`orphan_count` → `{count}`, `legacy_rows` → `{rows}`) so the rendered
     text is unchanged after `.format(...)`.
  3. Expose a module-level `ALL_REMEDIATION_TEXTS` collection (e.g. a tuple/frozenset) holding
     every remediation text constant — this is the canonical registry the guard will scan.
     Include `_RESTART_DAEMON_REMEDY` too.
- **Files**: `src/specify_cli/sync/preflight.py`.
- **Parallel?**: No.
- **Notes**: The constant strings must be the **exact** sentence bytes rendered today — copy the
  wrapped literal content verbatim (the two overlapping sentences already match across surfaces;
  pick either wrap, they concatenate to the same runtime string). The `ALL_REMEDIATION_TEXTS`
  entries hold the sentence text (with `{count}`/`{rows}` placeholders intact for the
  parametrized ones — the guard extracts command tokens, which are placeholder-free).

### Subtask T032 – Point both surfaces at the constants (byte-identical)

- **Purpose**: Eliminate the duplication so each sentence exists once.
- **Steps**:
  1. Make `_REMEDIATION_HINTS` reference the constants:
     `"daemon_server_url": _SERVER_URL_REMEDY`, `"daemon_team_or_user": _TEAM_OR_USER_REMEDY`,
     and keep the four restart-class fields on `_RESTART_DAEMON_REMEDY`.
  2. Make `_build_remediation_lines()` reference the same constants. The bullet builder just
     prepends `"  • "`: e.g. `remediation_lines.append(f"  • {_SERVER_URL_REMEDY}")`,
     `f"  • {_TEAM_OR_USER_REMEDY}"`,
     `f"  • {_ORPHAN_REMEDY.format(count=orphan_count)}"`,
     `f"  • {_SYNC_MIGRATE_REMEDY.format(rows=legacy_rows)}"`,
     `f"  • {_AUTH_LOGIN_REMEDY}"`.
  3. **Rendered output MUST be BYTE-IDENTICAL to today** — the mismatch-hint dict values and the
     rendered bullets must produce the exact same strings as before this WP.
- **Files**: `src/specify_cli/sync/preflight.py`.
- **Parallel?**: No.
- **Notes**: No duplicated remediation literal may remain in the module. Update the surrounding
  explanatory comments (~:91-121, ~:202-217) so they describe the shared constants rather than
  the old duplicated phrasing — but do not alter the emitted sentences.

### Subtask T033 – Widen the guard to scan the full registry

- **Purpose**: Close the coverage gap so inline-only commands are validated.
- **Steps**:
  1. Rewrite the command-resolution guard(s) in
     `tests/specify_cli/sync/test_preflight_remediation_hints.py` to iterate
     `ALL_REMEDIATION_TEXTS` (not just `_REMEDIATION_HINTS.items()`).
  2. For each remediation text, extract every `spec-kitty ...` command token and verify it
     resolves under `--help`, reusing the existing resolution helper.
  3. Confirm the mistyped-inline test from T030 now behaves correctly: it goes **red** on a typo
     in any inline-only command and **green** when the command is spelled correctly.
  4. Ensure the two guard names referenced in the mission (`test_no_unknown_commands_in_hints`,
     `test_every_hint_command_resolves_under_help`) either both scan the registry or the T030
     replacement supersedes them — do not leave a dict-only guard behind that re-narrows coverage.
- **Files**: `tests/specify_cli/sync/test_preflight_remediation_hints.py`.
- **Parallel?**: No.
- **Notes**: The registry now includes commands that only ever appeared inline
  (`doctor orphan-daemons`, `sync migrate`, `auth login`) plus the restart/auth commands. All
  must resolve under `--help`.

## Test Strategy

- Run: `uv run pytest tests/specify_cli/sync/test_preflight_remediation_hints.py -q`
- Byte-identical proof: assert the rendered strings match a snapshot of the pre-change output —
  e.g. capture the current dict values and the current `_build_remediation_lines()` output for a
  fully-populated failure set BEFORE editing production, then assert equality after. This is the
  guard that hoisting stayed behavior-preserving.
- Also fix the stale module docstring if present at ~:16-18 — it references `auth switch`, but the
  actual remedy uses `auth logout` then `auth login`. Correct it to match the emitted commands.
- Whole-suite sanity for the package: `uv run pytest tests/specify_cli/sync/ -q`.
- Gates: `uv run ruff check src/specify_cli/sync/preflight.py tests/specify_cli/sync/test_preflight_remediation_hints.py`
  and `uv run mypy src/specify_cli/sync/preflight.py` — zero issues, zero warnings.

## Risks & Mitigations

- **Rendered-output drift (highest risk).** The two `server_url`/`team_or_user` sentences are
  already identical across surfaces, so hoisting is behavior-preserving — but a stray character
  in the constant would change operator-facing output. Mitigation: snapshot-before / assert-after
  equality in the test file.
- **NFR-004 line budget.** The refusal block is bounded to ≤ 25 visible lines. Hoisting does not
  add lines — same sentences, same bullets. Do not introduce extra bullets.
- **Placeholder mismatch.** `{count}`/`{rows}` must format to the same digits/pluralization the
  inline builder produced. Mitigation: reuse the exact `.format(...)` arg names and surrounding
  text.
- **Re-narrowing regression.** Leaving a second dict-only guard in place would silently re-open
  the gap. Mitigation: T033 explicitly reconciles both guard names against the registry.

## Review Guidance

- **Verify the guard now scans the full registry** (`ALL_REMEDIATION_TEXTS`), not just
  `_REMEDIATION_HINTS` — the inline-only commands (`doctor orphan-daemons`, `sync migrate`,
  `auth login`) are validated to resolve under `--help`.
- **No duplicated remediation literal remains** in `preflight.py` — every sentence resolves to a
  single named constant.
- **No rendered-output change** — confirm the byte-identical snapshot assertion is present and
  passing; the operator-facing refusal block is unchanged.
- Confirm the T030 RED test genuinely failed against the pre-fix guard (check Activity Log for
  the captured red run) and passes now.
- `ruff`/`mypy` clean; no suppression comments added.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Why this matters**: The acceptance system reads the LAST activity log entry as the current
state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-15T22:32:40Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
- 2026-07-15T23:17:07Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Assigned agent via action command
- 2026-07-15T23:30:50Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Single-sourced every sync-preflight remediation sentence into named constants (_SERVER_URL_REMEDY, _TEAM_OR_USER_REMEDY, _ORPHAN_REMEDY, _SYNC_MIGRATE_REMEDY, _AUTH_LOGIN_REMEDY) plus ALL_REMEDIATION_TEXTS registry; both _REMEDIATION_HINTS and _build_remediation_lines() reference the constants with byte-identical rendered output (verified by snapshot test); widened the command-resolution guard to scan the full registry so inline-only commands (doctor orphan-daemons, sync migrate, auth login) are now validated. RED-first: test_full_registry_guard_resolves_inline_only_commands failed with AttributeError before T031, passes after. ruff+mypy clean on preflight.py; full sync suite (57 tests) green.
- 2026-07-15T23:31:39Z – claude:opus:reviewer-renata:reviewer – shell_pid=3692082 – Started review via action command
- 2026-07-15T23:40:07Z – user – shell_pid=3692082 – Review passed: RED-first C-005 empirically verified (new test file fails against base with ImportError: ALL_REMEDIATION_TEXTS absent; base guards were dict-only). Guard now scans full ALL_REMEDIATION_TEXTS registry; 3 inline-only commands (doctor orphan-daemons, sync migrate, auth login) present + resolve under --help (whack-a-field avoided). Byte-identical proven via literal-snapshot test independent of constants. No duplicated remedy literal remains; no new noqa/type-ignore; ruff+mypy clean; 7/7 tests green; WP commit touches only 2 owned files.
