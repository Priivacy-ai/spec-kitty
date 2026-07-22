---
work_package_id: WP03
title: Color/synthesis-manifest hygiene via CliConsole (#2672)
dependencies: []
requirement_refs:
- C-004
- FR-007
tracker_refs: []
planning_base_branch: feat/landing-pass-campsite-followups
merge_target_branch: feat/landing-pass-campsite-followups
branch_strategy: Planning artifacts for this mission were generated on feat/landing-pass-campsite-followups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/landing-pass-campsite-followups unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
phase: Phase 1 - Test hygiene
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "3690324"
shell_pid_created_at: "1784158279.46"
history:
- at: '2026-07-15T22:32:40Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/charter/evidence/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- tests/charter/evidence/test_orchestrator.py
- src/specify_cli/cli/console.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Color/synthesis-manifest hygiene via CliConsole (#2672)

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

Make `tests/charter/evidence/test_orchestrator.py::test_dry_run_evidence_on_spec_kitty_repo`
(#2672) **deterministic** by eliminating two independent flakes it exhibits today:

- **(a) Color-sensitivity.** The test spawns a subprocess
  (`sys.executable -m specify_cli charter synthesize --adapter fixture --dry-run-evidence`)
  and asserts substrings such as `lang=python` / `lang=javascript` against `result.stdout`.
  In a color-enabled local shell the CLI emits ANSI SGR escapes that can splice into the
  token (e.g. `lang=` `\x1b[...m` `javascript`), so the substring match fails even though the
  detector committed to a language. The Claude Code harness exports `FORCE_COLOR=3`, so this
  is reproducible, not hypothetical.
- **(b) Real-file mutation.** With `--adapter fixture` the synthesize run rewrites the REAL
  `.kittify/charter/synthesis-manifest.yaml` in the repo root (`adapter_id: fresh-seed → fixture`),
  leaving the working tree dirty after the test — polluting `git status` and any concurrent
  scanner/sibling test.

**Done when:**
- The color assertion is ANSI-insensitive (matches regardless of whether the subprocess emitted color).
- `.kittify/charter/synthesis-manifest.yaml` is **byte-unchanged** after the test runs.
- The test passes in a color-enabled shell AND under `NO_COLOR`.
- No global `os.environ` mutation is used as the color mechanism (see Constraints).
- **Requirements**: FR-007, C-004.

## Context & Constraints

- **RED-FIRST (C-005).** Land the failing assertions of T020 before the fixes of T021/T022.
  Do not write the remediation first and back-fill a test.
- **Route through the `CliConsole` seam where it applies.** `src/specify_cli/cli/console.py`
  is the single CLI output seam. Its docstring is explicit: *"Determinism is a property of the
  object, not the environment"* — tests obtain colourless, substring-stable output via
  `CliConsole.set_plain(...)` / `CliConsole.set_all_plain(...)` on the shared singleton, **never**
  by mutating `os.environ` (env mutation leaks into subprocesses and sibling tests).
- **Subprocess nuance — confirm during implementation.** This test drives the CLI as a *child
  process*, so an in-process `set_plain()` call in the test does NOT reach the child. Two seam-aligned
  options, in preference order:
  1. If the `charter synthesize` command (or its entrypoint) honors a deterministic no-color mode
     driven by `CliConsole` — e.g. a `--no-color` flag, or the child reading `NO_COLOR` and calling
     `set_all_plain` at startup — drive that. Passing `NO_COLOR=1` in the **test-local** `env` dict
     already handed to `subprocess.run` (the test builds `env = os.environ.copy()`) is a *local* env
     for the child, NOT global process mutation, and is acceptable if the CLI honors it.
  2. If neither a flag nor an `NO_COLOR`-honoring startup path exists, strip ANSI from
     `result.stdout` before the substring assertions:
     `re.sub(r"\x1b\[[0-9;]*m", "", text)`.
  Confirm which mechanism the CLI actually supports before choosing — do not assume. Only touch
  `src/specify_cli/cli/console.py` if a genuine determinism affordance is missing; the test-side
  strip (option 2) may fully suffice, in which case `console.py` needs no change.
- **Isolate the manifest write.** Point the synthesize run at a temp manifest (e.g. run the
  subprocess in a `tmp_path` sandbox, or copy the real manifest aside and restore it in a
  fixture teardown) so the real `.kittify/charter/synthesis-manifest.yaml` is never mutated.
  Confirm the exact write site during implementation.
- Supporting docs: `.kittify/charter/charter.md`, `kitty-specs/landing-pass-campsite-followups-01KXKWD7/spec.md`
  (FR-007, C-004), `plan.md` (IC-03), `research.md`. Confirm the exact failing assertion and
  the manifest-write path against the live code before editing.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T020 – RED: reproduce both failure modes deterministically

- **Purpose**: Pin both defects with failing assertions before any fix (C-005).
- **Steps**:
  - Assert that the color check does **not** depend on raw ANSI-laden output — either add a
    color-insensitive comparison (compare against ANSI-stripped stdout) or an explicit assertion
    that the rendered token is matched color-insensitively. In a `FORCE_COLOR=3` shell this must
    reproduce the current break on the raw `assert "lang=python" in result.stdout ...` line.
  - Add a **structural** assertion that `.kittify/charter/synthesis-manifest.yaml` is byte-unchanged
    after the run: capture the file bytes (or its git-clean state) before invoking, and assert
    equality after. Confirm the current test mutates it (this assertion should be RED before T022).
- **Files**: `tests/charter/evidence/test_orchestrator.py`.
- **Parallel?**: Foundation for T021/T022 — do first within this WP.
- **Notes**: Keep the two failures independently observable so a reviewer can see each fix land.

### Subtask T021 – Make the color assertion ANSI-insensitive (CliConsole seam preferred)

- **Purpose**: The `lang=...` substring match must hold whether or not the child emitted color.
- **Steps**:
  - Inspect `src/specify_cli/cli/console.py` for the determinism seam (`set_plain`,
    `set_all_plain`, `no_color`). Determine whether the `charter synthesize` child honors a
    `--no-color` flag or an `NO_COLOR` env that triggers `set_all_plain` at startup.
  - **Prefer** driving that deterministic no-color path (flag, or `NO_COLOR=1` in the test-local
    `env` dict passed to `subprocess.run`). If none exists, strip ANSI in the test with
    `re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)` before matching.
  - Do **NOT** mutate global `os.environ` as the mechanism. The test already builds a local
    `env = os.environ.copy()`; adding keys there is local to the child and acceptable.
- **Files**: `tests/charter/evidence/test_orchestrator.py`; `src/specify_cli/cli/console.py`
  ONLY if a determinism affordance is genuinely missing.
- **Parallel?**: After T020.
- **Notes**: Do not over-touch `console.py`. If the test-side strip fully deterministically fixes
  the assertion, leave `console.py` untouched.

### Subtask T022 – Isolate the synthesis-manifest write to a tmp fixture

- **Purpose**: The test must never mutate the real repo manifest.
- **Steps**:
  - Confirm where `--adapter fixture --dry-run-evidence` writes the manifest (repo-root
    `.kittify/charter/synthesis-manifest.yaml`).
  - Redirect that write to a `tmp_path` sandbox: either run the subprocess with `cwd`/config
    pointing at a temp manifest, or copy the real manifest aside before the run and restore it in
    a fixture teardown so the on-disk bytes are identical afterward.
  - Verify the T020 byte-unchanged assertion is now GREEN.
- **Files**: `tests/charter/evidence/test_orchestrator.py`.
- **Parallel?**: After T020.
- **Notes**: Prefer redirecting the write over copy+restore if the command exposes a target path;
  copy+restore is an acceptable fallback. Ensure teardown runs even on assertion failure.

## Test Strategy

- Primary gate (color-enabled shell — do not unset color):

  ````bash
  uv run pytest tests/charter/evidence/test_orchestrator.py::test_dry_run_evidence_on_spec_kitty_repo -q
  ````

- Confirm no real-file mutation after the run:

  ````bash
  git status --porcelain .kittify/charter/synthesis-manifest.yaml
  ````

  Must print nothing (empty).

- Also confirm determinism under both color regimes:

  ````bash
  FORCE_COLOR=3 uv run pytest tests/charter/evidence/test_orchestrator.py -q
  NO_COLOR=1     uv run pytest tests/charter/evidence/test_orchestrator.py -q
  ````

- Lint/type gates on any touched source:

  ````bash
  uv run ruff check tests/charter/evidence/test_orchestrator.py src/specify_cli/cli/console.py
  uv run mypy src/specify_cli/cli/console.py
  ````

## Risks & Mitigations

- **Over-touching `console.py`.** Add a determinism affordance only if genuinely missing; the
  test-side ANSI strip may suffice. Adding an unused flag invites Sonar/dead-code findings.
- **Global env leakage.** Never mutate the real process `os.environ` for color control — it leaks
  into sibling tests and future subprocesses. Keep env changes on the test-local `env` dict only.
- **Teardown gaps.** If using copy+restore for the manifest, ensure restoration runs on failure
  (fixture `yield` / `finally`), or a red assertion will leave the tree dirty anyway.
- **False green.** Verify the RED (T020) genuinely fails on current `main` before applying fixes;
  a test that was never red proves nothing.

## Review Guidance

- Confirm **no real-file mutation**: `.kittify/charter/synthesis-manifest.yaml` byte-unchanged
  after the test (structural assertion present AND green).
- Confirm the color assertion is **ANSI-insensitive** and passes under `FORCE_COLOR=3`.
- Confirm **no global `os.environ` mutation** is used as the color mechanism; the `CliConsole`
  seam / no-color flag / local-env / ANSI-strip path is used instead.
- Confirm `console.py` was touched only if a determinism affordance was genuinely missing.
- Verify the RED-first ordering is visible in the Activity Log / diff.

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
- 2026-07-15T23:16:59Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Assigned agent via action command
- 2026-07-15T23:30:49Z – claude:sonnet:python-pedro:implementer – shell_pid=3622117 – Deterministic dry-run evidence test: (a) color-sensitivity fixed by driving NO_COLOR=1 in the subprocess's TEST-LOCAL env dict (Rich's Console already honors NO_COLOR at construction -- confirmed empirically, no console.py change needed) plus a defense-in-depth ANSI strip on stdout before substring matches; FORCE_COLOR=3 also forced in the local env to pin the worst-case harness scenario and prove NO_COLOR wins. (b) manifest-mutation: empirically confirmed the current --dry-run-evidence code path (synthesize.py) already exits before calling synthesize(), so the real .kittify/charter/synthesis-manifest.yaml is not mutated by this specific invocation today -- no CLI flag exists to redirect the manifest write target, so added a _synthesis_manifest_guard pytest fixture (snapshot/restore via try-finally) plus an eager byte-equality assertion as a regression guard against a future write regression. Validated green under default env, FORCE_COLOR=3, and NO_COLOR=1; ruff and mypy clean on touched files; git status of the real manifest empty after every run.
- 2026-07-15T23:31:22Z – claude:opus:reviewer-renata:reviewer – shell_pid=3690324 – Started review via action command
- 2026-07-15T23:41:26Z – user – shell_pid=3690324 – Review passed: color flake fixed RED->GREEN (empirically proven: FORCE_COLOR=3 raw stdout fails old assertion, test-local NO_COLOR=1 + ANSI-strip pass; no global os.environ mutation). Manifest-mutation is an honest regression guard -- verified the --dry-run-evidence path raises typer.Exit(0) at synthesize.py:343/324 before synthesize(), so no real mutation today; byte-equality assertion is non-vacuous over the real 286-byte manifest + try/finally fixture. git status of manifest empty; console.py inspected-only (untouched); ruff+mypy clean; scope limited to owned test file. Coord: initialized #2672 issue-matrix row (in-mission, evidence 7429768cd).
