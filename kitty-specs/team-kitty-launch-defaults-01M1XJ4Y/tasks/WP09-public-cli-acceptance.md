---
work_package_id: WP09
title: Public-CLI acceptance and gates
dependencies:
- WP08
requirement_refs:
- C-004
- FR-010
- NFR-001
- NFR-002
- NFR-005
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T041
- T042
- T043
- T044
- T045
- T046
- T047
phase: Phase 3 - Acceptance
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: debugger-debbie
authoritative_surface: tests/integration/
create_intent:
- tests/integration/test_launch_defaults_acceptance.py
- tests/integration/_hosted_stubs.py
execution_mode: code_change
model: ''
owned_files:
- tests/integration/test_launch_defaults_acceptance.py
- tests/integration/_hosted_stubs.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Public-CLI acceptance and gates

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `debugger-debbie`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Read Before Anything Else

- `docs/context/team-kitty.md` — the hosted model. "Sync" is a retired transport; the live thing is Zeitgeist. Never phrase code, docs, tests, or commit messages in sync vocabulary.
- `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/spec.md`, `plan.md` (Implementation Concern Map), `research.md`, `data-model.md`, `contracts/*.md`, `occurrence_map.yaml`.
- `.kittify/charter/charter.md` §Quality standing orders: red-first through the pre-existing entry point (DIRECTIVE_041), campsite-clean the surfaces you touch first, canonical sources only, terminology canon.
- Test policy in `CLAUDE.md`: `make test-fast` baseline plus the test files of every module you touch; `tests/architectural/` in full when you touch `core/env.py`, `tests/conftest.py`, or any registry.

## Objectives & Success Criteria

- `tests/integration/test_launch_defaults_acceptance.py` implements `contracts/acceptance.md` A1–A9 through the public `spec-kitty` subprocess against recording stubs, each case red on the base and green at head.
- `tests/integration/_hosted_stubs.py` provides threaded recording stubs for the SaaS (`GET /api/v1/sync/repo-admission/`, `POST /api/v1/live/capability/cli/`, OAuth token/device endpoints, `GET /api/v1/me`) and the relay (`POST /managed/control`), counting requests by path.
- A11: `tests/architectural/` in full at or below baselines, `make test-fast` green; counts recorded.

## Context & Constraints

- The moment path and what the stubs must answer: `docs/context/team-kitty.md` ("Sequence: one lane transition"), `contracts/moment-path.md`; wire shapes in `zeitgeist_client/transport.py` (`offer` posts `{schema_version, op, request_id, args}` with `Authorization` + `X-Zeitgeist-Capability`), `zeitgeist_client/resolution.py` (`SaasCapabilityGateway`: admission GET then mint POST; response fields `relay_url`, `relay_token`, `capability_credential`, `expires_at`).
- Existing subprocess-style tests to mirror: `tests/integration/test_spec_kitty_home_cli.py` (isolated `SPEC_KITTY_HOME`), `tests/e2e/` for real-repo flows; `tests/zeitgeist_client/test_resolution.py` fakes for in-process unit variants.
- Interactive hint (A1) needs a pty: use `pty`/`pexpect`-free stdlib approach (`os.openpty`) or mark the case with the repo's existing TTY marker; the JSON/non-TTY cases use plain subprocess.
- `NFR-002`: zero requests unauthenticated means the stubs must observe **no** connection at all, including readiness; assert on the stub's request log and on a socket-level counter.
- Owned-checkout flow: `spec-kitty implement WP01 --owned-checkout <path>` then `move-task --to for_review --owned-checkout <path>` in a throwaway mission fixture (see `tests/integration/test_owned_checkout_mark_status.py` for how to build one).
- Markers: `pytest.mark.git_repo`, `integration`, and the platform markers `tests/integration/` already uses; keep each case under the fast-tier budget or mark `slow` per `pytest.ini`.

## Subtasks & Detailed Guidance

### Subtask T041 – Recording stubs

- **Purpose**: One reusable, deterministic hosted double.
- **Steps**: `_hosted_stubs.py`: `class RecordingServer` (threaded `http.server`, random port, `requests: list[(method, path, body)]`, `start()/stop()` context manager); `SaasStub` answering admission `{admitted: true, team: {...}}` or `{admitted: false, reason: "no_match"}`, mint `201 {session_ref, deployment_id, repo_slug, kind, relay_url, relay_token, capability_credential, expires_at}` pointing at the relay stub, token endpoints for a canned session; `RelayStub` answering `202 {request_id, received_at}` to `event.publish` and recording `args`. Provide a fixture that writes a fake stored session under the test's `SPEC_KITTY_HOME` (reuse the session-writing helper from `tests/auth/`).
- **Files**: `tests/integration/_hosted_stubs.py` (new, ~150 lines).
- **Parallel?**: No.

### Subtask T042 – A1/A2 first run and login target

- **Steps**: A1: fresh home, `spec-kitty status` in a pty → completes, stderr has the hint once; second run none; `--json` run clean. A2: `spec-kitty auth login --headless` against the SaaS stub with `SPEC_KITTY_SAAS_URL` unset but the stub reachable — the packaged default is a real host, so this case instead asserts the printed target line names `https://team.spec-kitty.ai (packaged default)` and that the device-flow request is sent to the resolved target when `SPEC_KITTY_SAAS_URL` points at the stub (precedence witnessed separately in A3).
- **Files**: `tests/integration/test_launch_defaults_acceptance.py`.
- **Parallel?**: No.

### Subtask T043 – A3 precedence via `auth status`

- **Steps**: Matrix from `contracts/target-resolution.md` through `spec-kitty auth status` subprocess: assert URL and source text; split-brain case exits non-zero with both values.
- **Parallel?**: Yes.

### Subtask T044 – A4 owned-checkout moment

- **Steps**: Build the throwaway mission, sign in against the stubs, perform the owned-checkout move; assert exactly one `event.publish` with `kind == "WPStatusChanged"`; run the same move from a lane worktree and compare `attrs` (all keys equal except session id).
- **Parallel?**: Yes.

### Subtask T045 – A5/A6 zero egress and logout

- **Steps**: No session: run specify→plan→tasks→move-task→review in the fixture mission with the stubs listening; assert `len(stub.requests) == 0` for both stubs. Then sign in, observe requests, `auth logout`, repeat a move: zero new requests and the hint marker is absent.
- **Parallel?**: Yes.

### Subtask T046 – A7/A8 guidance and retired names

- **Steps**: Logged out: `spec-kitty tracker status` exits non-zero with sign-in guidance and no "not enabled" text; with `SPEC_KITTY_ENABLE_SAAS_SYNC=0/1`, `SPEC_KITTY_SYNC_DISABLE=1`, and a `[sync] server_url` in config, behavior is identical to the unset case and `auth status` reports the packaged default.
- **Parallel?**: Yes.

### Subtask T047 – Gates

- **Steps**: `PWHEADLESS=1 .venv/bin/python -m pytest tests/architectural/ -q` (full) and `make test-fast`; classify any red per the baseline-red gotcha — `tests/architectural/test_golden_count_ban.py` is already red on `main` (#3977, `tests/architectural` at 15 vs ceiling 14) and counts as pre-existing unless this mission adds un-annotated sites; paste counts into the Activity Log.
- **Parallel?**: No.

## Test Strategy

- This WP is the test strategy; keep each acceptance case independent and isolated (own `SPEC_KITTY_HOME`, own temp repo).

## Risks & Mitigations

- Flakiness from port reuse or slow subprocess startup: bind port 0, wait for readiness, generous but bounded timeouts; mark `timing`-sensitive cases per `docs/development/testing/testing-flakiness.md`.
- The packaged default is a real production host: never let a test reach it — every hosted case sets `SPEC_KITTY_SAAS_URL` to the stub except the pure "print the default" assertions, which make no network call.

## Review Guidance

- Every contract row A1–A9 maps to a named test; A11 counts recorded; no test contacts `team.spec-kitty.ai`.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP09 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP09 --to for_review`, from the workspace the implement command gave you.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- 2026-09-07T10:00:36Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
