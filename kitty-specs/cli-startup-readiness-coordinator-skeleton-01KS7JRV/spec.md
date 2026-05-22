# CLI Startup Readiness Coordinator Skeleton

> Mission ID: `01KS7JRVSFFBWPD2XZ7B8162E6`
> Mission slug: `cli-startup-readiness-coordinator-skeleton-01KS7JRV`
> Target branch: `main`
> Mission type: software-dev
> Created: 2026-05-22

---

## Overview

The Spec Kitty CLI is preparing for a Teamspace launch in which any CLI invocation may need to surface readiness guidance: the operator may be logged out of a Teamspace-connected checkout, may be running a CLI version that is incompatible with the SaaS service, or may be invoking a hosted tracker command without auth. Today those checks are scattered across individual command handlers and the `_render_nag_if_needed()` helper inside `src/specify_cli/cli/helpers.py`. There is no single place that:

- composes readiness signals coherently,
- enforces the suppression contract (no human prompts on stdout, no prompts in `--json` / `--quiet` / `--help` / `--version` / non-TTY / CI),
- caches its result so subcommands can reuse it,
- and can be flipped from opt-in to default-on with a single, surgical change at launch.

Teamspace itself is still weeks from launch. Until then, all Teamspace-relevant behavior must remain dormant unless the operator has explicitly opted into hosted mode by setting `SPEC_KITTY_ENABLE_SAAS_SYNC=1`. Public default CLI behavior must continue to look local-first and must not mention Teamspace anywhere.

This mission introduces the central readiness coordinator referenced by Priivacy-ai/spec-kitty#1093 and the Workstream 1 deliverable in the program plan. It establishes a single seam (`src/specify_cli/readiness/coordinator.py`) that:

- gates every readiness signal on `is_saas_sync_enabled()` as its first check,
- composes (as stubs in this mission) feature-gate state, output policy, auth readiness, and upgrade readiness,
- stores a typed result on `ctx.obj` reusable by subcommands,
- routes the existing upgrade-nag call site so its behavior is preserved while downstream missions can extend it cleanly.

Auth readiness (Workstream 2), upgrade UX (Workstream 3), tracker readiness (Workstream 5), and docs (Workstream 6) are explicit downstream missions that plug into this seam. This mission delivers the seam itself; it does not implement those bodies.

---

## User Journeys

### Journey 1 — Public CLI user runs `spec-kitty --help` with hosted mode disabled

> "I just installed Spec Kitty. I run `spec-kitty --help` and I see local-first guidance. The product hasn't been launched to me yet."

**Actors:** Public CLI user (no Teamspace), CLI process
**Preconditions:** `SPEC_KITTY_ENABLE_SAAS_SYNC` is unset; the user has no Teamspace association.

After this mission:
1. The user runs `spec-kitty --help` (or `--version`, or `--json` on any command, or any plain invocation).
2. The root CLI callback fires the readiness coordinator.
3. The coordinator's first gate (`is_saas_sync_enabled()`) returns `False`. The coordinator immediately returns a no-op result with `enabled=False, ran=False` and touches nothing else: no network call, no disk read beyond what the gate itself needs, no output.
4. Nothing about Teamspace, hosted readiness, auth login, or upgrade nudges appears anywhere in stdout or stderr.
5. Existing pre-mission behavior (banner on plain invocation, the existing upgrade-nag when applicable to a non-Teamspace upgrade) is unchanged.

### Journey 2 — Internal/dev operator runs CLI with hosted mode enabled

> "I'm dogfooding Teamspace. I have `SPEC_KITTY_ENABLE_SAAS_SYNC=1` exported. I run multiple subcommands in one shell. The coordinator should run once per invocation, not many times, and subcommands should be able to read its result."

**Actors:** Internal/dev operator, CLI process, subcommand handlers
**Preconditions:** `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set.

After this mission:
1. The operator runs any `spec-kitty ...` command from a TTY.
2. The root callback fires the coordinator. The first gate returns `True`, so the coordinator proceeds.
3. The coordinator composes the (stubbed) readiness signals — feature-gate state, output policy, auth readiness stub, upgrade readiness wrapper — into a typed `ReadinessResult` and stores it on `ctx.obj` under a stable key.
4. Subcommand handlers that need readiness state read the cached result via a typed accessor (`get_readiness(ctx)`) without recomputing.
5. The coordinator runs exactly once per CLI invocation. An invariant test asserts this by counting calls inside a single root invocation.

### Journey 3 — JSON consumer runs a machine-output command with hosted mode enabled

> "I have a CI job that pipes `spec-kitty <cmd> --json` to `jq`. Even though I have `SPEC_KITTY_ENABLE_SAAS_SYNC=1` set for hosted-mode testing, prompts must never appear on stdout, and JSON must remain parseable."

**Actors:** CI / scripted consumer, CLI process
**Preconditions:** `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; `--json` (or `--quiet`) is in argv; stdout is non-TTY.

After this mission:
1. The coordinator runs and detects the active suppression conditions from the same signals `_should_suppress_nag()` uses today (`--json` / `--quiet` / `--help` / `--version` / `CI` env var / `SPEC_KITTY_NO_NAG` / non-TTY).
2. The coordinator records the suppression decision on the `ReadinessResult` and emits **no** human-facing output: no prompts, no nag lines, no Teamspace-labeled stderr noise.
3. stdout remains valid JSON for any subcommand that emits JSON.
4. The downstream nag call site, now routed through the coordinator, continues to honor its existing suppression behavior byte-for-byte.

### Journey 4 — Existing upgrade-nag continues to fire when appropriate

> "I'm a normal user (not Teamspace). I'm on an old CLI version. The existing upgrade nag has worked for me for months. After this mission lands, it should still fire under the same conditions, just routed through the coordinator."

**Actors:** Public CLI user with an outdated CLI, CLI process
**Preconditions:** `SPEC_KITTY_ENABLE_SAAS_SYNC` may be set or unset; suppression conditions are inactive; the compat planner returns `ALLOW_WITH_NAG`.

After this mission:
1. The user runs a normal command (e.g. `spec-kitty status`).
2. The coordinator fires from the root callback. Whether hosted mode is on or off, the coordinator orchestrates the existing nag rendering path.
3. The nag renders to stderr exactly as it does today: same wording, same `last_shown_at` cache update, same Rich-color handling based on stderr TTY-ness.
4. Existing CI-determinism tests under `tests/cli_gate/test_ci_determinism.py` continue to pass without modification.

### Journey 5 — Subcommand reads the cached readiness result

> "I'm writing a follow-up mission (auth readiness in WS2). I need to read the coordinator's verdict from inside my subcommand handler without re-running the coordinator. The accessor should be obvious and typed."

**Actors:** Future implementer of WS2 / WS3 / WS5
**Preconditions:** Coordinator has run once at root-callback time; subcommand handler is executing.

After this mission:
1. The subcommand handler calls `get_readiness(ctx)` from `specify_cli.readiness`.
2. The accessor returns the cached `ReadinessResult` if present, or a no-op default if the coordinator was suppressed or short-circuited.
3. The accessor never re-runs the coordinator and never raises if `ctx.obj` is missing — it returns a no-op default instead.

---

## Domain Language

| Term | Canonical meaning |
|---|---|
| **Readiness coordinator** | The single function (`evaluate_readiness(ctx)` in `src/specify_cli/readiness/coordinator.py`) called from the root CLI callback that composes feature-gate, output-policy, auth, and upgrade readiness signals and returns a typed `ReadinessResult`. |
| **ReadinessResult** | A small frozen dataclass returned by the coordinator. Carries enough fields for subcommands to know whether the coordinator ran, whether hosted mode was on, the output policy, the (stubbed) auth status, and a reference to the upgrade nag-planning result. |
| **Hosted mode** | The state of `SPEC_KITTY_ENABLE_SAAS_SYNC` being truthy, as decided by `specify_cli.saas.rollout.is_saas_sync_enabled()`. The coordinator's first gate. |
| **Suppression contract** | The rule that the CLI must emit no human-facing prompts or stderr noise when any of `--json`, `--quiet`, `--help`, `--version`, `CI=1`, `SPEC_KITTY_NO_NAG=1`, or non-TTY stdout is in effect. The coordinator records suppression on the `ReadinessResult` and gates all human output by it. |
| **Output policy** | The coordinator's record of the operative suppression conditions for this invocation. Three buckets: `interactive` (TTY, no suppression), `non_interactive` (non-TTY or CI), `machine_output` (`--json` / `--quiet`). |
| **Stub seam** | An import-and-typed-call-site that downstream missions will fill in. This mission imports `detect_logged_out_with_connected_teamspace` from `_auth_recovery` but does not call it; the call site is marked `# WS2: auth probe wiring`. |
| **Cached result** | The `ReadinessResult` stored on `ctx.obj` under the key `readiness` (when `ctx.obj` is a dict, which is the existing convention in `_render_nag_if_needed`). Read via `get_readiness(ctx)`. |
| **Nag passthrough** | The behavior in which the coordinator's invocation of the existing `_render_nag_if_needed()` call site is byte-for-byte equivalent to the pre-mission call from `callback()`. |

---

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | A new package `src/specify_cli/readiness/` exists and exports `evaluate_readiness(ctx) -> ReadinessResult`, `ReadinessResult`, and `get_readiness(ctx) -> ReadinessResult` from `src/specify_cli/readiness/__init__.py`. | Active |
| FR-002 | `evaluate_readiness(ctx)` is called exactly once from the root CLI `callback()` in `src/specify_cli/cli/helpers.py`, after output-suppression conditions are computable and before any human-facing output from the callback. | Active |
| FR-003 | The coordinator's first gate is `is_saas_sync_enabled()`. When it returns `False`, the coordinator returns a no-op `ReadinessResult` immediately, does no network I/O, performs no disk reads beyond what the gate itself does, and emits no stdout or stderr output. | Active |
| FR-004 | The coordinator records an `output_policy` field on `ReadinessResult` derived from the existing suppression conditions consulted by `_should_suppress_nag()` (TTY-ness, `CI`, `SPEC_KITTY_NO_NAG`, `--json`, `--quiet`, `--help`, `--version`). | Active |
| FR-005 | The coordinator composes an auth-readiness stub field on `ReadinessResult` whose value in this mission is the literal sentinel `not_checked`. The coordinator imports `specify_cli.cli.commands._auth_recovery.detect_logged_out_with_connected_teamspace` but does **not** call it; the import is marked with a `# WS2: auth probe wiring` comment so a follow-up mission can wire it in. | Active |
| FR-006 | The coordinator wraps the existing `_render_nag_if_needed(ctx)` invocation so that the call site is owned by the coordinator. The wrapper's behavior is byte-for-byte equivalent to the pre-mission inline call from `callback()`: same conditions for rendering, same stderr output, same nag-cache update, same exception swallowing. | Active |
| FR-007 | The coordinator stores its result on `ctx.obj`. If `ctx.obj` is `None`, the coordinator initializes it to `{}`. If `ctx.obj` is a dict, the result is stored under the key `readiness`. The coordinator never replaces a non-dict `ctx.obj`. | Active |
| FR-008 | `get_readiness(ctx)` reads the cached result from `ctx.obj` and returns it. If `ctx.obj` is `None`, not a dict, or missing the `readiness` key, `get_readiness` returns a no-op default `ReadinessResult` and does not re-run the coordinator. | Active |
| FR-009 | When the coordinator is invoked twice on the same `ctx` (defensive — e.g. subcommands accidentally re-invoke the root callback), the second invocation returns the cached result without re-evaluating any signals. | Active |
| FR-010 | The coordinator never raises on internal failure. Any exception inside `evaluate_readiness` is caught, logged at debug level if possible, and replaced with a no-op `ReadinessResult` so the CLI cannot crash because of readiness logic. (The wrapped nag passthrough preserves the existing nag's own exception-swallowing behavior.) | Active |
| FR-011 | With `SPEC_KITTY_ENABLE_SAAS_SYNC` unset, no string containing the case-insensitive substring `teamspace` is written to stdout or stderr by any of: `spec-kitty --help`, `spec-kitty --version`, `spec-kitty` (no args), `spec-kitty <cmd> --json`, `spec-kitty <cmd> --quiet`, the same with `CI=1` in env, the same with `sys.stdout.isatty()` returning `False`. | Active |
| FR-012 | New tests live under `tests/readiness/`, exercise the 7-row suppression matrix (interactive, `--json`, `--quiet`, `--help`, `--version`, CI, non-TTY), and assert the once-per-invocation caching invariant. Existing tests under `tests/cli_gate/test_ci_determinism.py` continue to pass without modification. | Active |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Coordinator overhead must not noticeably slow CLI startup. | The coordinator's added wall-clock cost when hosted mode is disabled must be ≤ 1ms p50 on a developer laptop (measured by `time.perf_counter_ns` around the call inside a unit test). When hosted mode is enabled, the coordinator's overhead beyond the existing nag-render path must be ≤ 2ms p50. | Active |
| NFR-002 | The coordinator must perform no network I/O in this mission. | Zero outbound HTTP/socket calls during `evaluate_readiness`. A test mocks `httpx`/`socket` and asserts no calls are made. | Active |
| NFR-003 | The coordinator must perform no disk reads beyond what `is_saas_sync_enabled()` and the existing wrapped nag call already do. | No new file-system reads added in this mission outside the nag passthrough. Verified by inspection during review; no test mock required. | Active |
| NFR-004 | The coordinator must be tested at ≥ 90% line coverage. | `pytest --cov=specify_cli/readiness` reports ≥ 90% line coverage for `src/specify_cli/readiness/`. | Active |
| NFR-005 | Type discipline: the coordinator must pass `mypy --strict` for the files it adds and the files it modifies. | `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` passes. | Active |

---

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | No new pip dependencies. The coordinator must be implemented entirely with the existing dependency set (`typer`, `rich`, stdlib). | Active |
| C-002 | Pre-launch hidden mode is law. The coordinator must no-op unless `is_saas_sync_enabled()` returns `True`. No exception. | Active |
| C-003 | The wire format and conditions of the existing upgrade-nag message must not change in this mission. Existing tests asserting the exact output continue to pass. | Active |
| C-004 | No SaaS DB, queue, or readiness-counter mutation in any path executed by this mission's code. | Active |
| C-005 | `_render_nag_if_needed()` must remain importable from `specify_cli.cli.helpers` at its current name. (Its `__all__` already exports it; removing it from `__all__` would break dependents we cannot see.) | Active |
| C-006 | `_auth_recovery.detect_logged_out_with_connected_teamspace` must not be exercised in this mission. It is imported as a typed seam only; an inline `# WS2: auth probe wiring` comment marks the stub. | Active |
| C-007 | All event producers (none expected this mission) must use canonical `spec_kitty_events` pydantic models. Hand-rolled event dicts are forbidden and CI-enforced via `scripts/lint_canonical_producers.py`. | Active |
| C-008 | `spec-kitty next` is the only entry point for advancing per-WP state. Backward rewinds require `force=True` and a non-empty `reason`. | Active |
| C-009 | The diff must be confined to: the new `src/specify_cli/readiness/` package, `src/specify_cli/cli/helpers.py` (the hook), and the new tests under `tests/readiness/`. No other files modified. | Active |
| C-010 | No direct push to `main`. Mission lands via PR. `unset GITHUB_TOKEN` before any `gh` write. | Active |

---

## Goals

- A single, named, importable readiness seam (`evaluate_readiness`) the rest of the program can target.
- Suppression contract enforced at the seam, not re-asserted by every command.
- Existing upgrade nag preserved byte-for-byte while becoming extensible.
- The mission's diff stays small enough to land on `main` without scope review on every file.

## Non-Goals

- Implementing the auth readiness body — the call to `detect_logged_out_with_connected_teamspace` and its renderer.
- Implementing the upgrade UX additions (snooze cadence, "Always keep me up to date", "Not now", "Never ask again", installer detection, auto-upgrade).
- Aligning the tracker registration / tracker readiness with the coordinator.
- Documentation rewrites for pre-launch hidden mode or launch mode.
- Flipping the default of `SPEC_KITTY_ENABLE_SAAS_SYNC` or the packaged SaaS URL.
- Any change to `spec-kitty-saas`, `spec-kitty-tracker`, `spec-kitty-events`, or `spec-kitty-end-to-end-testing`.

## Out-of-scope (defer to follow-ups)

- WS2: Auth readiness from any command (`spec-kitty#1094`). Lights up the stub seam.
- WS3: Upgrade readiness UX (`spec-kitty#1092`). Extends the nag passthrough into a snooze-aware renderer.
- WS4: SaaS compatibility metadata (`spec-kitty-saas#207`). Sister mission running in parallel; this mission does not depend on it.
- WS5: Tracker readiness alignment (`spec-kitty-tracker#18`).
- WS6: Docs (`spec-kitty#1095`).
- WS7: Deployed-dev canaries.

## Acceptance Criteria

1. `src/specify_cli/readiness/__init__.py`, `src/specify_cli/readiness/coordinator.py`, and a small typed `ReadinessResult` dataclass exist on the mission branch; `from specify_cli.readiness import evaluate_readiness, get_readiness, ReadinessResult` resolves cleanly.
2. `src/specify_cli/cli/helpers.py` `callback()` imports the coordinator and calls `evaluate_readiness(ctx)` before invoking the existing nag path; the existing nag invocation is owned by the coordinator (called from inside it, not duplicated). The change is minimal and grep-unambiguous in the diff.
3. With `SPEC_KITTY_ENABLE_SAAS_SYNC` unset, a parameterized 7-row test asserts that none of `--help`, `--version`, plain invocation, `--json`, `--quiet`, `CI=1`, non-TTY contain the substring `teamspace` (case-insensitive) in stdout or stderr.
4. With `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, a test asserts the coordinator runs exactly once per CLI invocation (the second invocation on the same `ctx` returns the cached result without re-evaluating any signals), and the result is reachable from a subcommand via `get_readiness(ctx)`.
5. Existing tests in `tests/cli_gate/test_ci_determinism.py` continue to pass on the mission branch with no modification.
6. `pytest -q tests/readiness/ tests/cli_gate/test_ci_determinism.py` is green on the mission branch.
7. `mypy --strict src/specify_cli/readiness/ src/specify_cli/cli/helpers.py` passes on the mission branch.
8. `scripts/lint_canonical_producers.py` (if invoked over the diff) reports no new violations.
9. `git diff main...HEAD --stat` shows changes confined to:
   - `src/specify_cli/readiness/__init__.py` (new)
   - `src/specify_cli/readiness/coordinator.py` (new)
   - `src/specify_cli/cli/helpers.py` (modified — single hook)
   - `tests/readiness/...` (new tests)
   - `kitty-specs/cli-startup-readiness-coordinator-skeleton-01KS7JRV/...` (mission artifacts)
10. With `SPEC_KITTY_ENABLE_SAAS_SYNC` unset, the existing upgrade-nag still fires under the same conditions as before (verified by re-running the existing CI-determinism tests unchanged).

## Assumptions

1. The existing `_should_suppress_nag()` helper accurately captures every active suppression condition; the coordinator can either delegate to it or re-derive the same booleans (this mission delegates to keep one source of truth).
2. The existing `_render_nag_if_needed()` function is safe to call from inside the coordinator with the same `ctx` it was called with from `callback()`. (Verified by reading the function.)
3. `ctx.obj` is either `None` or a dict at the time the coordinator runs. The current `_render_nag_if_needed()` already initializes `ctx.obj = {}` when needed; the coordinator follows the same pattern.
4. The coordinator runs from the root callback only. Subcommands that themselves declare a callback do not re-fire the root callback. Defensive once-per-ctx caching guards against unforeseen re-entry.
5. The mission's surface area is small enough that no charter ADR is required for the seam itself; the seam follows existing module-creation conventions (lower_snake package under `src/specify_cli/`).

## References

- Tracking issue: [Priivacy-ai/spec-kitty#1093](https://github.com/Priivacy-ai/spec-kitty/issues/1093)
- Program plan: `start-me-start-here.md` (Workstream 1)
- Mission workflow: `spec-kitty-mission-workflow.md`
- Existing helpers: `src/specify_cli/cli/helpers.py` (`_render_nag_if_needed`, `_should_suppress_nag`, `callback`)
- Existing auth-recovery surface: `src/specify_cli/cli/commands/_auth_recovery.py` (`detect_logged_out_with_connected_teamspace`)
- Existing SaaS rollout gate: `src/specify_cli/saas/rollout.py` (`is_saas_sync_enabled`, `SAAS_SYNC_ENV_VAR`)
