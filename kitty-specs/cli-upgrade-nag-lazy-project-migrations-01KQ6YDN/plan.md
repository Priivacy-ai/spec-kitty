# Implementation Plan: CLI Upgrade Nag and Lazy Project Migration

**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN` (`mid8: 01KQ6YDN`)
**Branch**: `main` (planning base) → merges to `main`
**Date**: 2026-04-27
**Spec**: [`spec.md`](spec.md)
**Research**: [`research.md`](research.md)
**Data model**: [`data-model.md`](data-model.md)
**Contracts**: [`contracts/`](contracts/)
**Quickstart**: [`quickstart.md`](quickstart.md)

---

## Summary

Build a single internal **compatibility planner** (`src/specify_cli/compat/`) that produces a structured plan describing CLI freshness, current-project schema status, and the safe/unsafe decision for the invoked command. CLI surfaces (typer callback for the gate, `spec-kitty upgrade` for action, `--json` for automation) consume that plan; they don't recompute compatibility independently. A throttled, per-user **nag cache** drives the passive CLI-update message; a pluggable **`LatestVersionProvider`** keeps planner logic testable without network. Existing modules — `core.version_checker`, `migration.gate`, `upgrade.detector` — are wrapped as private adapters under `compat/` so the diff stays bounded and old import paths keep working as thin shims.

The mission ships in the `spec-kitty` repository only. No SaaS, no global registry, no per-machine project enumeration, no silent self-update.

## Engineering Alignment (locked decisions)

These are the answers to the planning questions, recorded so the implementer can act without re-asking. Per DIRECTIVE_003, the rationale is recorded with each.

1. **Compatibility planner placement (Option A from planning).** Introduce a new package `src/specify_cli/compat/`. Existing modules become private adapters; their public symbols continue to work as shims that re-export from `compat/`. Call sites migrate at their own pace. *Why:* satisfies C-008/FR-024 with minimal blast radius and preserves NFR-006 (existing migration tests must still pass).

2. **Latest-version source default (Option A from planning).** `httpx.get("https://pypi.org/pypi/spec-kitty-cli/json", timeout=2.0, follow_redirects=False)`, parse `info.version`, response capped at 1 MB. Provider is exposed as a `LatestVersionProvider` Protocol; tests inject `FakeLatestVersionProvider`. CI / non-interactive mode uses `NoNetworkLatestVersionProvider`. *Why:* httpx is already a runtime dependency, the JSON shape is stable, and abstraction makes NFR-005 trivially testable.

3. **Safety registration (Option A from planning, with refinement).** A central, pre-seeded `SAFETY_REGISTRY` lives in `src/specify_cli/compat/safety.py`. Known commands are seeded centrally (no mechanical edit of every CLI module in the first PR). Commands that need mode-aware predicates (`dashboard`, `doctor`) register a small predicate function near the command itself. **Anything not in the registry is treated as unsafe under schema mismatch.** *Why:* fail-closed bias matches the spec's safety contract; central seeding avoids a wide refactor PR; per-command predicates only show up where they actually matter.

## Technical Context

| Field | Value |
|---|---|
| Language / version | Python 3.11+ (existing spec-kitty baseline). |
| Primary dependencies | `typer`, `rich`, `ruamel.yaml`, `httpx` (already in `pyproject.toml`). No new mandatory dep (C-009). |
| Storage | Filesystem only. Per-user nag cache JSON; per-project `.kittify/metadata.yaml`. |
| Testing | `pytest`, `mypy --strict`, integration tests for CLI commands. 90%+ coverage for new code (charter policy). |
| Target platform | macOS / Linux / Windows terminal; both interactive shells and CI / non-interactive runners. |
| Project type | Single-package Python CLI. |
| Performance goal | < 100 ms additional startup overhead when nag cache is fresh (NFR-001); ≤ 2 s network timeout (NFR-002). |
| Constraints | No SaaS / hosted-auth / sync deps (NFR-008); no project writes from non-`upgrade` startup paths (NFR-003); deterministic CI (NFR-004). |
| Scale / scope | Per-user, per-current-project. Explicitly NOT cross-project (FR-021). |

## Charter Check

The charter policy summary for this project (loaded via `spec-kitty charter context --action plan`):

- typer (CLI framework) — **honored**. Planner does not introduce a parallel CLI surface.
- rich (console output) — **honored**. Nag and block messages render via `rich.Console`.
- ruamel.yaml (YAML parsing) — **honored**. `.kittify/metadata.yaml` continues to be parsed via the existing safe-load helpers in `migration.schema_version`.
- pytest (testing framework) — **honored**.
- mypy --strict (type checking) — **honored**. New `compat/` package will be `mypy --strict` clean from day 1.
- Coverage 90%+ for new code — **target**. Planner unit tests + CLI integration tests will hit this.
- Integration tests for CLI commands — **target**. New CLI flags (`--cli`, `--project`, `--yes`, `--no-nag`) and the gate's block path are integration-tested.

**Action doctrine for plan**:
- DIRECTIVE_003 (Decision Documentation Requirement) — *applied*: Engineering Alignment section above + ADR draft in §"ADR Pointers" below.
- DIRECTIVE_010 (Specification Fidelity Requirement) — *applied*: every artifact in this mission traces to the FRs/NFRs/SCs in `spec.md`. Deviations must be re-specified before implementation.

**Charter Check verdict: PASS.** No charter violations. No `[NEEDS CLARIFICATION]` entries open.

## Project Structure

### Documentation (this feature)

```
kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/
├── spec.md
├── plan.md                    (this file)
├── research.md                (Phase 0)
├── data-model.md              (Phase 1)
├── quickstart.md              (Phase 1)
├── contracts/
│   └── compat-planner.json    (JSON schema for `spec-kitty upgrade … --json`)
├── checklists/
│   ├── requirements.md
│   └── security.md
└── tasks/                     (created by /spec-kitty.tasks; NOT by this command)
```

### Source code layout

New package and the existing surfaces it touches:

```
src/specify_cli/
├── compat/                          # NEW: single source of truth for compatibility decisions
│   ├── __init__.py                  # public API: plan(), Decision, Plan, Safety
│   ├── planner.py                   # plan(invocation, project, cli, *, network=True) -> Plan
│   ├── safety.py                    # SAFETY_REGISTRY, register_safety(), classify(invocation) -> Safety
│   ├── provider.py                  # LatestVersionProvider Protocol + PyPIProvider, FakeProvider, NoNetworkProvider
│   ├── cache.py                     # NagCache: read/write per-user JSON; perms 0600; symlink-resistant
│   ├── messages.py                  # Stable message catalog keyed by FR-023 case
│   ├── _adapters/                   # Private adapters wrapping existing modules
│   │   ├── version_checker.py       # wraps src/specify_cli/core/version_checker.py
│   │   ├── gate.py                  # wraps src/specify_cli/migration/gate.py
│   │   └── detector.py              # wraps src/specify_cli/upgrade/detector.py
│   └── _detect/
│       └── install_method.py        # detects pipx | pip-user | pip-system | brew | system-package | source | unknown
│
├── cli/
│   ├── helpers.py                   # MODIFIED: typer callback consults compat.planner instead of migration.gate
│   └── commands/
│       └── upgrade.py               # MODIFIED: adds --cli, --project, --yes, --no-nag; routes to compat.planner
│
├── core/
│   └── version_checker.py           # KEPT: now a thin shim re-exporting from compat._adapters.version_checker
│
├── migration/
│   ├── gate.py                      # KEPT: now a thin shim that calls into compat.planner
│   └── schema_version.py            # MODIFIED: REQUIRED_SCHEMA_VERSION activated; adds MIN_SCHEMA / MAX_SCHEMA pair
│
└── upgrade/
    ├── detector.py                  # KEPT: now a thin shim re-exporting from compat._adapters.detector
    └── runner.py                    # MODIFIED: routes blocking decisions through compat.planner
```

### Test layout

```
tests/specify_cli/compat/
├── test_planner.py                 # unit: every FR-023 case + edge cases
├── test_safety.py                  # unit: registry behavior, fail-closed semantics, mode predicates
├── test_provider_pypi.py           # unit: HTTP mocking, malformed payload, downgrade payload, redirect-rejection
├── test_provider_no_network.py     # unit: confirms zero requests
├── test_cache.py                   # unit: 0600 perms, symlink resistance, version-key invalidation, clock skew
├── test_install_method.py          # unit: detection per platform
└── test_messages.py                # unit: catalog ⇄ JSON tokens

tests/specify_cli/cli/commands/
└── test_upgrade_command.py         # integration: --dry-run, --json, --cli, --project, --yes, --no-nag, exit codes

tests/cli_gate/
├── test_safe_commands.py           # integration: safe matrix runnable under schema mismatch (SC-006)
├── test_unsafe_commands.py         # integration: unsafe matrix blocked under schema mismatch
├── test_dashboard_modes.py         # integration: read-only mode safe, write/init/sync/repair mode unsafe
├── test_doctor_modes.py            # integration: diagnostic mode safe, repair/fix mode unsafe
└── test_ci_determinism.py          # integration: zero outbound calls when CI=1 / no-TTY (SC-005)

tests/cross_cutting/versioning/     # PRESERVED: existing tests must continue to pass (NFR-006)
```

**Structure decision**: single Python package, no new top-level dirs. The `compat/` package is the only new module path. Adapters live as private `_adapters/` to discourage external callers.

## Phase 0 — Research summary

See [`research.md`](research.md). Key resolutions:

- R-01: PyPI JSON endpoint is the authoritative source for "latest CLI version" — chosen over GitHub Releases and `pip index` for stability and zero-subprocess latency.
- R-02: `platformdirs.user_cache_dir("spec-kitty")` is acceptable to use as cache location (`platformdirs` is already a transitive of existing deps; if not, fall back to manual XDG resolution per A-001 — research confirms the resolution path).
- R-03: Install-method detection algorithm: walk `sys.executable` path, check `pipx --version`, check `brew --prefix`, check `pip show -f spec-kitty-cli` for `INSTALLER` metadata. Fallback hierarchy documented in research.
- R-04: Safe-load semantics for `.kittify/metadata.yaml` already exist via `migration.schema_version.get_project_schema_version`; we reuse them and add bounded-size guards.
- R-05: Activation strategy for `REQUIRED_SCHEMA_VERSION` (currently `None`): split into `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA`. See research §R-05 for migration ordering.
- R-06: Throttle window default 24 h. Configuration surface: `~/.config/spec-kitty/upgrade.yaml` (key: `nag.throttle_seconds`) **and** env var `SPEC_KITTY_NAG_THROTTLE_SECONDS`. Env wins.
- R-07: CI / non-interactive predicate: `os.environ.get("CI")` is truthy OR `not sys.stdout.isatty()` OR `os.environ.get("SPEC_KITTY_NO_NAG")` is truthy OR `--no-nag` flag is present.
- R-08: Exit codes for blocked unsafe commands: `4` for "project migration needed", `5` for "project too new for CLI", `6` for "project metadata corrupt". `--dry-run` always exits `0` regardless of plan content (signal is in payload).

## Phase 1 — Design & contracts summary

See [`data-model.md`](data-model.md) for the entity definitions and state machine, [`contracts/compat-planner.json`](contracts/compat-planner.json) for the stable JSON schema, and [`quickstart.md`](quickstart.md) for end-to-end usage examples a planner / reviewer can run.

Key design points:

- **`Plan`** is a single immutable dataclass returned by `compat.planner.plan(...)`. Every CLI surface that decides "block / nag / proceed" reads from this dataclass.
- **`Decision`** is an enum: `ALLOW`, `ALLOW_WITH_NAG`, `BLOCK_PROJECT_MIGRATION`, `BLOCK_CLI_UPGRADE`, `BLOCK_PROJECT_CORRUPT`, `BLOCK_INCOMPATIBLE_FLAGS`. Every decision is mapped to exactly one FR-023 case + one stable JSON token.
- **`Safety`** is `SAFE | UNSAFE`. Mode-aware commands (`dashboard`, `doctor`) register a predicate `(invocation_args) -> Safety`.
- **`SAFETY_REGISTRY`** is seeded centrally (one place) from a known-command list; new commands inherit `UNSAFE` until classified (fail-closed per Q3 refinement).
- **Nag cache** records `{cli_version_key, latest_version, fetched_at_iso, last_shown_at_iso}`. Writing uses `os.O_CREAT | os.O_WRONLY | os.O_TRUNC` with mode `0o600` and refuses to follow symlinks.
- **JSON contract** for `spec-kitty upgrade --json` and `--dry-run --json` is defined in `contracts/compat-planner.json` (JSON Schema Draft 2020-12) and is held stable across patch releases.

## Implementation phasing (NOT for /spec-kitty.tasks; informational only)

The implementer (`/spec-kitty.tasks` then `/spec-kitty.implement`) will likely organize work into these slices. They are *informational* — `/spec-kitty.tasks` decides the actual WP graph.

1. **Foundations** — create `compat/` package skeleton; move adapters; `LatestVersionProvider` protocol + `NoNetworkProvider`; nag cache with full security properties; tests for cache and provider in isolation.
2. **Planner** — implement `plan(...)` and `Decision` enum; safety registry seeded with the safe-command list (extends existing `_EXEMPT_COMMANDS`); shim `migration/gate.py` and `core/version_checker.py` to delegate.
3. **CLI surfaces** — wire `cli/helpers.py` typer callback to consult planner; add `--cli`, `--project`, `--yes`, `--no-nag` to `upgrade`; emit JSON per contract; correct exit codes.
4. **Schema activation** — set `MIN_SUPPORTED_SCHEMA` / `MAX_SUPPORTED_SCHEMA` and remove the `REQUIRED_SCHEMA_VERSION = None` early-return in the gate (now handled by planner).
5. **Mode-aware safety** — register `dashboard`-mode and `doctor`-mode predicates; integration tests for mode split.
6. **Documentation** — update `docs/how-to/install-and-upgrade.md` to explain CLI vs project upgrade (SC-008).
7. **CI determinism + security tests** — net-mock + perm-check tests; ensure NFR-005 / NFR-008 / SC-005 enforced architecturally.

## Risks (Premortem)

| ID | Risk | Mitigation |
|---|---|---|
| RP-01 | Activating `REQUIRED_SCHEMA_VERSION` (currently `None`) blocks every existing project until it migrates. | Activate as a `MIN..MAX` *range* sized to include schemas users actually have today; ship the migration that bumps to the new minimum *before* the gate flips. Document in CHANGELOG. |
| RP-02 | The nag prints during scripted `--json` consumption and corrupts machine-parseable output. | Nag is suppressed entirely when `--json` (or `--quiet`) is in argv, and when stdout is not a TTY by default. Quietness is part of A-007. |
| RP-03 | `pipx upgrade` hint is wrong because the user installed via `pip --user`. | Install-method detection includes a `pip show … INSTALLER` check before falling through to `unknown`. Tests cover the four common install patterns. |
| RP-04 | The shims in `core/version_checker.py` and `migration/gate.py` drift from the planner over time. | Shim modules contain a single import line + delegation; CI architectural test asserts no logic in shim modules beyond delegation. |
| RP-05 | A new CLI command added later forgets to register safety, so the planner blocks it. | This is **the desired behavior** (fail-closed). Doc + test guard: "If you add a new command, register it in `compat.safety.SAFETY_REGISTRY` or it will be unsafe under schema mismatch." |
| RP-06 | Network call in CI sneaks past the predicate (e.g. `pytest` itself isn't `CI=1`). | Predicate is union of CI env var ∪ no-TTY ∪ explicit opt-out. Tests assert zero outbound requests when *any* of these holds. The provider abstraction makes the test trivial. |
| RP-07 | Cache file written with world-readable permissions on Windows. | Cache code uses `os.open(..., 0o600)` on POSIX; on Windows, sets ACL via `pathlib` + best-effort fallback documented in code. Test skips on Windows but file location is per-user already. |
| RP-08 | A hostile latest-version JSON response includes ANSI escapes that paint a fake "ALL OK" message in the user's terminal. | Provider sanitises the version string against a strict regex (`^[\d.]+([a-zA-Z0-9.-]+)?$`); planner only embeds the sanitised string. Test covers ANSI/escape payloads. |

## ADR pointers (deferred; created during implementation)

The implementer should draft these ADRs as they finalize each decision (per DIRECTIVE_003):

- **ADR-A**: Compatibility planner is the single authority for safe/unsafe decisions (locks Q1 + Q3).
- **ADR-B**: `LatestVersionProvider` protocol + `PyPIProvider` default (locks Q2).
- **ADR-C**: Activation of `REQUIRED_SCHEMA_VERSION` (split into MIN/MAX, ordering with the bump migration).

## Out of scope for this plan

(Re-stating spec §"Out Of Scope" so it cannot be lost during task breakdown.)

- Global project registry; upgrade-all-projects workflow.
- Forced CLI self-update during normal command startup.
- Full reinstall of Spec Kitty itself.
- SaaS / tracker / sync / hosted-auth changes.
- Changes to `spec-kitty-saas`, `spec-kitty-tracker`, or any other repository.
- New telemetry from the upgrade path.

## Branch contract (reminder)

- Current branch at plan time: **main**
- Planning/base branch: **main**
- Final merge target: **main**
- `branch_matches_target`: **true**

## Complexity Tracking

No charter violations. Table empty by design.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|

## Next command

`/spec-kitty.tasks` — the user must invoke explicitly. This plan does **not** generate `tasks.md` or any `tasks/` subdirectory.
