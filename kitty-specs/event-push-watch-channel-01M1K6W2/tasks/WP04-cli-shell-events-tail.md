---
work_package_id: WP04
title: CLI shell — events tail command, registration, docs, glossary
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-001
- FR-004
- FR-009
- FR-010
- FR-012
- NFR-003
- NFR-005
- C-001
- C-002
- C-003
- C-008
- C-009
planning_base_branch: feat/event-push-watch-channel-3841
merge_target_branch: feat/event-push-watch-channel-3841
branch_strategy: Planning artifacts for this mission were generated on feat/event-push-watch-channel-3841. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/event-push-watch-channel-3841 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-event-push-watch-channel-01M1K6W2
base_commit: c269cad808059ad513f3942fd24eec2de2ace0d6
created_at: '2026-09-03T15:11:36.214727+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
- T029
- T030
history: []
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/cli/commands/events.py
- tests/cli/test_events_tail.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/events.py
- src/specify_cli/cli/commands/__init__.py
- tests/cli/test_events_tail.py
- docs/api/cli-commands.md
- docs/context/system-events.md
- src/specify_cli/.contextive/system-events.yml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – CLI shell — events tail command, registration, docs, glossary

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Build the thin CLI shell that makes `spec-kitty events tail --mission <slug> --json` a real, user-facing command: a new `events` Typer command group wrapping WP01–WP03's core (`poll_once`, `validate_resume_cursor`, `tail_events`), registered alongside the existing command groups, with the resulting new command documented in the CLI reference and its new domain terms registered as glossary candidates.

## Context

- **C-001 scope lock**: this WP builds ONLY `spec-kitty events tail --mission <slug> --json` (Option 1). No daemon, no socket/SSE endpoint, no network listener, no fleet aggregation — even as a partial on-ramp. This is an operator decision (spec Clarifications §1), not open to re-scoping.
- **`--mission`, never `--feature*`** (C-003, charter Terminology Canon) — on every flag, help string, and error message this WP writes. Internal Python params may keep `feature_dir`/`feature` (existing convention in `store.py`/`lifecycle_events.py`).
- **`__all__` (C-007/C-002) does NOT apply** — `events.py` lands under `src/specify_cli/cli/commands/`, not `src/charter/`/`src/kernel/`.
- **Deterministic termination for CLI-shell tests (this WP is one of the two poll-loop WPs that must state this explicitly)**: every `CliRunner` invocation in this WP's tests passes ONLY `--once` or a small `--max-events N` — **never a bare unbounded `events tail` invocation**. `--once` calls `poll_once()` directly, once, with no generator and no sleep at all — this is why "exits 0 without blocking" (User Story 1 AC1) is trivially true. State this explicitly; do not leave it implicit.
- **Patch/mock target discipline (Gate Set's "`patch()` target validator" row)**: if any test in this WP patches `time.sleep` or `resolve_mission_handle`, the patch target MUST be the **importing module's** path — `specify_cli.cli.commands.events.resolve_mission_handle` (NOT `specify_cli.cli.selector_resolution.resolve_mission_handle`), and if `time.sleep` needs patching anywhere in a WP04 test that exercises the underlying poll loop, the target is `specify_cli.status.tail_reader.time.sleep` (the module that actually calls it), never the defining `time` module's own path.
- **Tail Envelope & Cursor Schema (plan.md's section of the same name) — carry these exact shapes, do not re-invent them**:
  - Pass-through envelope: the existing `StatusEvent` JSON dict unmodified, plus `tail_offset: int` and `tail_invariant: str` sibling keys.
  - Truncation signal: `{"type": "log_truncated", "reason": "size_shrink" | "content_mismatch", "detected_at_offset": <O>, "tail_offset": 0, "tail_invariant": "<EMPTY_DIGEST>"}`.
  - Resolve-failure/usage-error/resume-refused signal: **stderr ONLY, never on the stdout Tail-envelope stream** — codes `"mission_not_found"` (delegates to `resolve_mission_handle`'s own JSON-mode output), `"usage_error"` (FR-004's invariant-without-offset case), `"invalid_resume_offset"` (FR-013 structural), `"resume_content_mismatch"` (FR-013 content). Model: `agent_retrospect.py:593`/`:600`'s pattern — `_err_console.print_json(json.dumps({"error": <code>, "detail": <message>}))` + `raise typer.Exit(<n>)`, NOT `typer.BadParameter`. **Explicitly do NOT copy the `mission_not_found` branch around `agent_retrospect.py:408-419` as the model** — it prints via `_console.print_json` (the STDOUT console, `specify_cli.cli.console.console`), not `_err_console` (STDERR, `agent_retrospect.py:22`), and uses a different, richer schema. Copying it verbatim would leak onto stdout and use the wrong envelope shape.
- **The write-scope disjointness this WP must re-verify**: `docs/api/cli-commands.md` is ALSO touched by two concurrently-open PRs (#3842 at lines 540-548 inside `## spec-kitty charter list`, #3845 at lines 1112-1115 inside `## spec-kitty dispatch`, per plan.md's "Write-Scope Disjointness" section). This WP's own insertion point is the alphabetical slot between `## spec-kitty doctrine validate` and `## spec-kitty glossary`, ~1000-1600 lines from either PR's edit — no textual conflict is expected, but **this WP's implementer must re-diff `docs/api/cli-commands.md` immediately before generating/hand-scoping its own docs edit**, in case the alphabetical insertion point has shifted by merge time. Also note: `src/specify_cli/cli/commands/__init__.py` gets exactly one narrow import + `app.add_typer(...)` line, additive only, not a reorder.
- **Do not run `scripts/docs/build_cli_reference.py` as a subprocess** — it defaults to `uv run`, which re-syncs the environment and destroys a hand-built `.venv` (cost a prior mission four rebuilds, per AGENTS.md). Monkeypatch its `cmd_runner` to `(".venv/bin/spec-kitty",)` and call its own `main()` in-process; hand-scope the resulting diff to only the new `events`/`events tail` sections.
- **PR-shape recommendation (plan.md's PR Shape section)**: this mission ships as ONE PR (spec-kitty's default), but the plan judges the aggregate diff NOT trivially reviewable in one sitting given the genuine engineering weight, and recommends the pre-merge adversarial squad and WP-level reviews budget real time proportional to a small-subsystem review — WP-level review, including this WP's own, must NOT be compressed or skipped.
- **Terminology canon**: no `--feature*` aliases anywhere on the CLI surface.
- **Commit discipline**: conventional-commits, every message ends with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- **ATDD precision**: T021's failing-first test must fail against WP03's final commit precisely because `src/specify_cli/cli/commands/events.py` does not exist at all yet — a legitimate import-time failure (the CLI shell is entirely new in this WP, unlike WP02/WP03's more precise non-import failures).
- **Baseline-red methodology (NFR-005)**: before T021's red-first commit, run the exact targeted test path set from plan.md's "Baseline & Pre-existing Red" section against merge-base `db5014ab5`, quoting the baseline red WITH that path set.

## Subtasks

### Subtask T021: Failing-first CLI ATDD test for User Story 1 AC1

Create the NEW file `tests/cli/test_events_tail.py` and write ONE failing test, as its own commit, before `events.py` exists.

- The test drives `typer.testing.CliRunner` against `spec-kitty events tail --mission <slug> --json --once` targeting a pre-populated `status.events.jsonl` (N events, hand-written or via WP01's fixture helpers) and asserts: exit code `0`, exactly N lines on stdout, each a `json.loads`-able dict, and the events appear in file order.
- Run this against WP03's final commit first, to confirm the failure mode is a plain import-time `ModuleNotFoundError`/collection error for `specify_cli.cli.commands.events` — NOT a more specific assertion failure. This is deliberately a coarser RED than WP02/WP03's precise non-import failures, because the whole shell is new in this WP; state that explicitly in the commit message or a comment.
- Before this commit, run the exact targeted path set from plan.md's Baseline & Pre-existing Red section against merge-base `db5014ab5` and record the quoted baseline red for `tests/cli/ tests/specify_cli/cli/ -m fast` — this is the NFR-005 baseline this WP's own new red must be compared against, not a bare count.
- Mark the test `pytestmark = [pytest.mark.fast]` (mocked resolution — see T030 for the fixture split).
- Commit alone: `test(events): add failing ATDD test for events tail --once (US1 AC1)` + trailer.

### Subtask T022: Implement `src/specify_cli/cli/commands/events.py` — Typer app + flags

Create the NEW file `src/specify_cli/cli/commands/events.py`:

- `app = typer.Typer(help="Event log tailing commands")`.
- One command, `tail`, registered via `@app.command("tail")`, with the exact CLI surface from plan.md's CLI Surface section:
  - `--mission` (required, `str`) — no `--feature*` alias, ever (C-003).
  - `--json` (`bool`, default `True`) — accepted but currently a no-op: build NO `if not json_output: ...` branch, since no FR requires one and JSON is the only supported mode per Edge Cases. Do not add speculative surface for a human-readable mode that does not exist.
  - `--once` (`bool`, default `False`).
  - `--max-events` (`int | None`, default `None`).
  - `--from-offset` (`int | None`, default `None`).
  - `--from-invariant` (`str | None`, default `None`).
- Import WP01–WP03's core from `specify_cli.status.tail_reader` (`TailCursor`, `ResumeRefused`, `poll_once`, `validate_resume_cursor`, `tail_events`) — do not reimplement any of it here.
- Import `resolve_mission_handle` from `specify_cli.cli.selector_resolution` (`:183`) at module scope, so tests can patch `specify_cli.cli.commands.events.resolve_mission_handle` per the Context section's patch-target rule.
- Wire only the Typer scaffolding in this subtask (options, docstrings/help text); leave the dispatch body's logic to T023–T026.
- No test yet in this subtask beyond keeping T021's test collectible (still red on behavior until T026 lands the dispatch order).

### Subtask T023: FR-004 usage-error check — `--from-invariant` without `--from-offset`

Implement the first of the shell's four ordered checks (plan.md's "does exactly four things, none of them novel domain logic"):

- At the very top of `tail_command`, before any file/mission access: if `from_invariant is not None and from_offset is None`, emit the usage-error stderr envelope and exit non-zero, BEFORE any read begins.
- Error shape: `_err_console.print_json(json.dumps({"error": "usage_error", "detail": <message>}))` then `raise typer.Exit(<n>)` — model this on `agent_retrospect.py:593`/`:600`'s pattern exactly, not `typer.BadParameter`. Import `_err_console` the same way `agent_retrospect.py` does (the STDERR `CliConsole` instance, distinct from the STDOUT `_console`).
- Write a fast test (`tests/cli/test_events_tail.py`, `pytestmark = [pytest.mark.fast]`) asserting: non-zero exit, stdout is empty (no Tail envelope emitted for the invocation), and stderr's JSON body has `"error": "usage_error"`.
- Commit: `feat(events): reject --from-invariant without --from-offset before any read (FR-004)` + trailer.

### Subtask T024: FR-009 — resolve the mission via `resolve_mission_handle`

Wire the second of the shell's four ordered checks, immediately after T023's usage check:

- Call `resolve_mission_handle(mission, repo_root, json_mode=True)` (`src/specify_cli/cli/selector_resolution.py:183`) — zero new resolution code. On an unresolvable slug it already emits the JSON-mode `{"error": "mission_not_found", "handle": ...}` shape on stderr and raises `SystemExit(2)`; let that propagate as-is rather than re-wrapping it.
- Resolve `repo_root` the same way other command modules in `src/specify_cli/cli/commands/` do (do not invent a new repo-root-discovery mechanism).
- Write a fast test patching `specify_cli.cli.commands.events.resolve_mission_handle` (per the Context section's patch-target rule — NOT `specify_cli.cli.selector_resolution.resolve_mission_handle`) to raise `SystemExit(2)`, and asserting the CLI invocation exits non-zero with no stdout Tail envelope. Write a second fast test with a genuinely bad slug against a real (tmp-path) repo root, asserting the same `"mission_not_found"` stderr shape end-to-end without mocking resolution.
- Commit: `feat(events): resolve --mission via resolve_mission_handle, fail closed on bad slug (FR-009)` + trailer.

### Subtask T025: FR-013 — wire `validate_resume_cursor()` when `--from-offset` is supplied

Wire the third of the shell's four ordered checks, after mission resolution and only when `from_offset is not None`:

- Call `validate_resume_cursor(path, from_offset, from_invariant)` (WP02's function). Catch `ResumeRefused` and translate its `reason` field to the FR-013 stderr shape:
  - `reason in {"negative", "out_of_range", "misaligned"}` → `{"error": "invalid_resume_offset", "detail": ...}`.
  - `reason == "content_mismatch"` → `{"error": "resume_content_mismatch", "detail": ...}`.
- Same `_err_console.print_json` + `typer.Exit(<n>)` pattern as T023. Zero Tail envelopes are emitted for that invocation — `validate_resume_cursor()` must be called, and must raise, BEFORE any streaming/printing begins.
- Write two fast tests, each patching `validate_resume_cursor` (or exercising it directly against a crafted tmp-path file) to raise `ResumeRefused` with a structural reason and with `"content_mismatch"` respectively, asserting the two distinct error codes land on stderr and stdout stays empty.
- **Also required — the SUCCESS path (User Story 3 AC1's non-refusal branch), not only the refusal branches above.** Every test named so far across this WP (and WP02's T015) exercises only `validate_resume_cursor`'s REFUSAL branch; this is the mission's headline P2 resumability deliverable and needs its own positive-path CLI-level test, against a REAL tmp-path log (not a mocked `validate_resume_cursor`): write a log to a tmp-path mission directory, consume it far enough via a real `--once`/`poll_once()` call (or by hand-deriving the offset/invariant the same way the core does) to obtain a valid `(offset, invariant)` pair, append further events past that offset, then invoke `spec-kitty events tail --mission <slug> --json --from-offset <O> --from-invariant <hex> --max-events N` and assert: exit 0, and the emitted stdout lines are exactly the events at/after `O`, in order, with none duplicated and none of the pre-`O` events re-emitted.
- Commit: `feat(events): refuse invalid/content-mismatched resume offsets before streaming (FR-013)` + trailer.

### Subtask T026: Wire the four-thing dispatch order and drive the core

Assemble T023–T025's checks into the shell's full ordered dispatch, then drive the core:

1. FR-004 usage check (T023).
2. FR-009 mission resolve (T024).
3. FR-013 resume validation, only if `--from-offset` given (T025).
4. Drive the core:
   - `--once`: call `poll_once(path, cursor)` **directly, once** — no generator, no sleep at all. Print the resulting envelope(s) as one `json.dumps(...)` line per item via plain `print` (never Rich markup on stdout — matches `docs.py`'s existing `--json` convention) and exit 0.
   - Otherwise: iterate `tail_events(path, cursor, ...)`, wrapped in `itertools.islice(..., max_events)` when `--max-events` is given, printing one JSON line per yielded item the same way.
- The initial `cursor` for step 4 is `TailCursor(offset=from_offset or 0, content_invariant=<validated invariant from step 3, or EMPTY_DIGEST at offset 0>)` — do not re-derive the invariant independently of what step 3 already validated.
- Write a fast test exercising the full happy path end-to-end with `--once` against a real tmp-path log file with N pre-existing events (mocked resolution only), asserting exit 0 and exactly N JSON lines in file order — this closes out T021's ATDD test to GREEN.
- Commit: `feat(events): wire ordered dispatch and drive poll_once/tail_events (US1 AC1)` + trailer.

### Subtask T027: Register the events Typer app in `src/specify_cli/cli/commands/__init__.py`

Edit the EXISTING file `src/specify_cli/cli/commands/__init__.py`:

- Add one import line for the new `events` module (matching the existing import style for sibling command modules such as `docs`/`glossary`).
- Add one `app.add_typer(events_module.app, name="events")` call, inserted between the existing `docs` (~line 273) and `glossary` (~line 274) registrations.
- This is a narrow, ADDITIVE edit only — do not reorder any existing registration, do not touch any line outside the one import + one `add_typer` call.
- Write a fast test asserting `spec-kitty events tail --help` (or `spec-kitty events --help`) exits 0 and lists the `tail` subcommand — proof the registration actually wires the command into the real top-level app, not just that `events.py`'s own module-level `app` works in isolation.
- Commit: `feat(cli): register events command group (FR-001)` + trailer.

### Subtask T028: Regenerate `docs/api/cli-commands.md`

Edit the EXISTING file `docs/api/cli-commands.md`:

- Immediately before generating, re-diff the live file per the Context section's write-scope note above — confirm the alphabetical insertion point (`## spec-kitty doctrine validate` → `## spec-kitty glossary`) has not shifted since plan time, and confirm PR #3842/#3845's edit regions (lines 540-548 and 1112-1115 at plan time) have not moved into this WP's insertion zone.
- Do NOT run `scripts/docs/build_cli_reference.py` as a subprocess. Monkeypatch its `cmd_runner` to `(".venv/bin/spec-kitty",)` and call its own `main()` in-process (e.g. from a short one-off script or a REPL session, not committed), then hand-scope the resulting diff to ONLY the new `## spec-kitty events` / `## spec-kitty events tail` sections — discard any unrelated drift the full regen would otherwise pull in from other commands' help text.
- Verify `tests/architectural/test_docs_cli_reference_parity.py` passes against the hand-scoped diff.
- Commit alone: `docs(cli): document events tail command` + trailer (no test — this is a docs-only commit; it will be validated by the architectural parity test in T030's verification pass).

### Subtask T029: Glossary candidates + Contextive regeneration

Edit the EXISTING file `docs/context/system-events.md`:

- Add candidate entries for: **Tail cursor**, **resume token**, `log_truncated`, **Tail envelope** — each definition drawn from spec.md's Key Entities section (do not re-derive new wording; the spec's own phrasing is the source of truth).
- Each entry MUST explicitly cross-reference and distinguish itself from the existing canonical **Event Envelope** term (`event_id`/`event_type`/`aggregate_id`/`lamport_clock`/`payload`) — never silently reuse similar wording that could be mistaken for the same shape. State plainly, per entry, how it differs (e.g. "Tail envelope, unlike the canonical Event Envelope, is either a raw `StatusEvent` line or one of this command's own signal shapes — never the `event_id`/`lamport_clock` schema").
- Then run `python scripts/generate_contextive_glossaries.py generate` and commit the resulting `src/specify_cli/.contextive/system-events.yml` diff in the SAME commit as the markdown edit. **This is load-bearing, not optional polish** — omitting it fails `scripts/generate_contextive_glossaries.py check` on the next PR touching `src/specify_cli/**`. Verify no other `.contextive.yml`/`.contextive/*.yml` file changed as a side effect (plan.md's Contracts section confirms this edit only touches `src/specify_cli/.contextive/system-events.yml` — spot-check `git status` after running `generate`).
- Commit alone: `docs(glossary): register Tail cursor / resume token / log_truncated / Tail envelope candidates` + trailer.

### Subtask T030: Remaining CLI-shell tests, real-fixture coverage, FR-010, terminology guard

Round out `tests/cli/test_events_tail.py`:

- Fast/mocked-resolution tests (`pytestmark = [pytest.mark.fast]`, collected by `fast-tests-cli`): flag validation, exit codes, stderr JSON shapes for every error code (`usage_error`, `mission_not_found`, `invalid_resume_offset`, `resume_content_mismatch`) — mocking the core (`resolve_mission_handle`/`validate_resume_cursor`) is acceptable ONLY for these pure-flag-validation tests.
- At least one real-fixture test (`pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`, collected by `integration-tests-cli`) exercising the real core end-to-end against a tmp-path mission directory with a real `status.events.jsonl` — NOT an all-mocked core. If the fixture mints real mission directories in quick succession, freeze `ULID` generation and `now_utc_iso()` per ledger SK-147's pattern (C-009).
- An FR-010 no-write assertion test: spy on `Path.open` (assert no call opens `status.events.jsonl`/`status.json`/any mission artifact in a write mode — `"w"`, `"a"`, `"x"`, or any `"+"` variant) across every code path exercised in this WP's tests, including the error/refusal paths (usage error, mission-not-found, resume-refused) — prove no write syscall path is reachable through ANY code path, not just the happy path.
- Verify RED→GREEN for T021's original test and every test added since.
- Run `pytest tests/architectural/test_no_legacy_terminology.py` and confirm it stays green (no `--feature*` slip in any flag/help/error string this WP wrote).
- Commit: `test(events): round out CLI-shell coverage (FR-010, real-fixture, terminology guard)` + trailer.

## Definition of Done

| WP | Test file(s) | Marker(s) | CI job |
|---|---|---|---|
| WP04 | `tests/cli/test_events_tail.py` | `fast` (mocked resolution) | `fast-tests-cli` |
| WP04 | `tests/cli/test_events_tail.py` | `integration`+`git_repo` (real fixture) | `integration-tests-cli` |

- T021's RED verified against WP03's final commit — an import failure (`events.py` doesn't exist yet), quoted alongside the exact targeted baseline-red path set from plan.md's Baseline & Pre-existing Red section run against merge-base `db5014ab5`.
- GREEN on this WP's final commit — every test added by T021–T030 passes.
- Every stderr error shape (`mission_not_found`, `usage_error`, `invalid_resume_offset`, `resume_content_mismatch`) uses `_err_console`, never `_console` — verified by an explicit test per code, not by inspection alone.
- No `--feature*` slip anywhere in flags, help text, or error messages — verified by `tests/architectural/test_no_legacy_terminology.py` passing green.
- `docs/api/cli-commands.md` diff is hand-scoped to only the new `## spec-kitty events` / `## spec-kitty events tail` sections, after a live re-diff immediately before generating (not a full regen sweep).
- `src/specify_cli/.contextive/system-events.yml` is regenerated via `generate_contextive_glossaries.py generate` and committed alongside the `docs/context/system-events.md` glossary markdown edit, in the same commit.
- Every commit message follows conventional-commits and ends with the required `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailer.

## Risks

| Risk | Mitigation |
|---|---|
| CLI-shell test invokes `events tail` unbounded, hangs CI | Every test in `tests/cli/test_events_tail.py` passes `--once` or `--max-events N`; no other invocation shape exists anywhere in this WP's test suite. |
| `docs/api/cli-commands.md` regen pulls in unrelated drift | Monkeypatch `cmd_runner` to `(".venv/bin/spec-kitty",)`, call `main()` in-process (never as a subprocess), and hand-scope the committed diff to only the new `events`/`events tail` sections. |
| Glossary entries introduce term drift vs. the existing "Event Envelope" | Every new entry (Tail cursor, resume token, `log_truncated`, Tail envelope) explicitly cross-references and distinguishes itself from the canonical Event Envelope term, per the spec's own Key Entities instruction. |

## Reviewer Guidance

- Verify no `CliRunner` invocation anywhere in `tests/cli/test_events_tail.py` calls `events tail` without `--once` or `--max-events` — a bare unbounded invocation is a hang-CI defect, not a style nit.
- Verify the stderr/stdout console split is correct: every error/usage/refusal signal goes through `_err_console` on stderr, and no Tail envelope (pass-through or `log_truncated`) is ever printed to stderr — check each of the four error codes individually, not just one representative case.
- Verify the `docs/api/cli-commands.md` diff is scoped to only the new `## spec-kitty events` / `## spec-kitty events tail` sections — reject a diff that touches any pre-existing section's text, even incidentally (e.g. trailing-whitespace normalization elsewhere in the file).
- Verify the `src/specify_cli/.contextive/system-events.yml` regeneration lands in the SAME commit as the `docs/context/system-events.md` glossary markdown edit — a split across two commits (or a missing regen entirely) fails `generate_contextive_glossaries.py check` on the next PR touching `src/specify_cli/**` and must be rejected here, not discovered later.
- Confirm the FR-010 no-write test actually covers the error/refusal paths (usage error, mission-not-found, resume-refused), not only the happy `--once` path — a spy that only wraps the happy-path call would miss a write reachable only through error handling.
- Confirm `--json`'s no-op status: no `if not json_output: ...` branch should exist anywhere in `events.py` — flag this as scope creep if found, per plan.md's CLI Surface section.

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent claude
```
