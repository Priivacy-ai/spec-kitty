# Tracker Readiness Alignment (CLI side)

Mission slug: `tracker-readiness-alignment-01KS7PZ7`
Issue: [Priivacy-ai/spec-kitty-tracker#18](https://github.com/Priivacy-ai/spec-kitty-tracker/issues/18) (Workstream 5 of `Priivacy-ai/spec-kitty#1091`)

## Embedded mission brief

> **Title.** Align tracker hosted/auth readiness with the central CLI coordinator; preserve local/offline tracker; tracker stays hidden pre-launch.
>
> **Problem statement.** Hosted tracker commands currently have their own auth/readiness wording divergent from the rest of the CLI. With the readiness coordinator now central, hosted tracker auth/readiness failures must route through the shared readiness language (same remediation, same suppression rules). Local/offline tracker flows must not require hosted auth and must remain usable without `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Tracker commands must remain registered only when hosted mode is enabled (pre-launch hidden).
>
> **Acceptance criteria (from WS5 + issue #18):**
>
> 1. Tracker command registration in `spec-kitty` remains hidden when `is_saas_sync_enabled()` is false. (Verify behavior unchanged; add explicit test if missing.)
> 2. Hosted tracker auth/readiness failures route through the shared `ReadinessResult` / coordinator language. The remediation message is `spec-kitty auth login` (same wording the auth probe uses for the connected-Teamspace case).
> 3. Local/offline tracker flows do not require hosted auth and do not invoke the hosted-readiness probe.
> 4. Tracker SDK in `spec-kitty-tracker` exposes a clear hosted-vs-local mode distinction so the CLI can route correctly.
> 5. Suppression rules from the central coordinator apply to hosted tracker readiness output too: no human prompts in `--json`, `--quiet`, `--help`, `--version`, CI, non-TTY. Stable stderr in non-interactive hosted command paths.
> 6. Contract tests cover: hosted tracker + no auth → shared `spec-kitty auth login` guidance; local tracker + no auth → no hosted auth requirement; hosted tracker + JSON → stdout JSON intact, no stderr noise from the readiness layer; hosted tracker + non-TTY → single-line stderr.
> 7. No mutation of shared SaaS state to make tests pass.

## In-scope (this repo)

- `src/specify_cli/cli/commands/tracker.py` — gate `_check_readiness` output through the coordinator output policy; emit a single-line stable stderr for the non-interactive auth-missing case.
- `tests/agent/cli/commands/test_tracker.py` + sibling files — contract tests for the AC matrix.

## Out of scope

- Auth probe internals (Mission C — `spec-kitty#1094`).
- Upgrade UX (Mission D — `spec-kitty#1092`).
- Docs (Mission F — `spec-kitty#1095`).
- SaaS-side or events-package changes.
- The tracker SDK's hosted-vs-local mode distinction (AC#4) — that lives in the sibling `spec-kitty-tracker` mission.

## Operating rules carried forward

- No SaaS DB / queue / readiness counter mutation.
- `spec-kitty next` is the only entry point for advancing per-WP state.
- All event producers use canonical pydantic models.
- No new pip dependencies.
- `unset GITHUB_TOKEN` before `gh` writes.
- Tracker remains hidden pre-launch unless `is_saas_sync_enabled()` is true.

## Functional requirements (FR)

- **FR-001** Tracker command group MUST remain absent from the root `--help` when `SPEC_KITTY_ENABLE_SAAS_SYNC` is unset (regression coverage).
- **FR-002** Direct invocation of any tracker subcommand when the flag is unset MUST exit 1 with the existing `saas_sync_disabled_message()` (defense-in-depth gate).
- **FR-003** When the central coordinator's `OutputPolicy` is `MACHINE_OUTPUT` (`--json` / `--quiet` in argv) the readiness renderer in `tracker.py` MUST NOT write anything to stdout; failure is reported via a single line on stderr ending with `Run \`spec-kitty auth login\`.`.
- **FR-004** When the coordinator's `OutputPolicy` is `NON_INTERACTIVE` (help/version/CI/non-TTY) the readiness renderer MUST emit a single, stable, machine-parseable line on stderr of the form `spec-kitty tracker: readiness=<state> next=spec-kitty-auth-login`.
- **FR-005** When the coordinator's `OutputPolicy` is `INTERACTIVE`, the existing two-line message+next_action human format is preserved verbatim.
- **FR-006** Local tracker bindings (`beads`, `fp`) MUST NOT trigger the hosted readiness probe (existing `_is_local_binding()` short-circuit covered by explicit regression test).
- **FR-007** The remediation string `Run \`spec-kitty auth login\`.` MUST be sourced from `specify_cli.saas.readiness._WORDING[ReadinessState.MISSING_AUTH]` (single source of truth); a regression test asserts this.

## Acceptance test matrix

| Scenario | Output policy | Expected stdout | Expected stderr | Exit |
|---|---|---|---|---|
| Hosted on, no auth, interactive | INTERACTIVE | (empty) | 2-line msg+next_action | 1 |
| Hosted on, no auth, `--json` | MACHINE_OUTPUT | (empty) | single line ending `Run \`spec-kitty auth login\`.` | 1 |
| Hosted on, no auth, CI / non-TTY | NON_INTERACTIVE | (empty) | `spec-kitty tracker: readiness=missing_auth next=spec-kitty-auth-login` | 1 |
| Hosted off, any | n/a | (empty) | `Hosted SaaS sync is not enabled...` | 1 |
| Hosted on, local binding, no auth | INTERACTIVE | (depends on command) | (no readiness output) | 0 |
| Tracker registration with flag off | n/a | (no `tracker` in help) | (empty) | 0 |

## Non-functional requirements

- **NFR-001** Zero new dependencies.
- **NFR-002** Zero new network I/O on the readiness path.
- **NFR-003** Coordinator-derived `OutputPolicy` lookup must be lazy (no import-time cycles).

## Analyze / Renata / mission-review notes

Captured directly in this spec because the parallel-mission environment made the
`/spec-kitty.analyze` and `/spec-kitty.next` loops impractical (sister missions
repeatedly reset HEAD on the shared main checkout; see notes below).

- **Analyze**: no spec/plan/tasks contradictions found. The only drift-class
  hazard is "duplicating the remediation string"; that is guarded by the
  `test_ws5_remediation_string_matches_saas_readiness_source` regression test
  pulling directly from the saas-readiness `_WORDING` dict.
- **Renata pass**: scope discipline — only `cli/commands/tracker.py` and three
  test files touched. No event producers introduced. No `status.events.jsonl`
  edits. No SaaS DB / queue / readiness counter mutations. No new pip deps.
  Coordinator import is lazy. `_render_readiness_failure` only consumes the
  public `get_readiness` / `OutputPolicy` surfaces (not internals).
- **Mission-review**: every FR in this spec is exercised by a test. The
  pre-existing `test_status_readiness_missing_auth_message` test and the two
  parameterised matrices in `test_tracker_status.py` / `test_tracker_discover.py`
  were updated to force `INTERACTIVE` policy so they continue to validate the
  canonical 2-line wording; the new NON_INTERACTIVE / MACHINE_OUTPUT formats
  are covered separately in `test_tracker.py::test_ws5_*`.

## Subagent execution notes

This mission ran from a private worktree
(`.worktrees/tracker-readiness-alignment-01KS7PZ7`) because sister missions in
the parent workspace were concurrently resetting HEAD on the shared `spec-kitty`
checkout, which silently discarded uncommitted work and renamed branches
between commands. The worktree is the only safe parallel-execution shape on
this repo per `spec-kitty-mission-workflow.md §"Parallelization safety"`.
