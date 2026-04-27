# Tasks: CLI Upgrade Nag and Lazy Project Migration

**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN` (`mid8: 01KQ6YDN`)
**Branch**: `main` (planning base) → merges to `main`
**Plan**: [`plan.md`](plan.md)
**Spec**: [`spec.md`](spec.md)

This document is the canonical work-package breakdown for the mission. Per-WP prompts live in `tasks/WP##-*.md`. Implementation lanes are computed by `finalize-tasks`.

---

## Subtask Index (reference table — not a tracking surface)

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Create `compat/` package skeleton (no `__init__.py` exports yet — empty placeholder) | WP01 | — | [D] |
| T002 | Implement `LatestVersionProvider` Protocol + `LatestVersionResult` dataclass in `compat/provider.py` | WP01 | — | [D] |
| T003 | Implement `PyPIProvider` (httpx, 2s timeout, no redirects, 1MB body cap, version sanitisation) | WP01 | — | [D] |
| T004 | Implement `NoNetworkProvider` and `FakeLatestVersionProvider` (test double) | WP01 | — | [D] |
| T005 | Unit tests for all three providers with network mocked | WP01 | [D] |
| T006 | Implement `NagCacheRecord` dataclass + `NagCache` class in `compat/cache.py` | WP02 | — |
| T007 | Add 0o600 file mode + 0o700 parent dir mode + symlink-resistant lstat checks | WP02 | — |
| T008 | Implement throttle predicate with clock-skew handling and version-key invalidation | WP02 | — |
| T009 | Implement throttle/no-nag config loading (env > YAML > default; range-validated) | WP02 | — |
| T010 | Unit tests for cache with corrupt files, symlinks, oversized state, perm assertions | WP02 | [P] |
| T011 | Implement `InstallMethod` enum + detection chain in `compat/_detect/install_method.py` | WP03 | — |
| T012 | Implement `UpgradeHint` builder with sanitised commands per install method | WP03 | — |
| T013 | Unit tests for each install-method branch (pipx, pip-user, pip-system, brew, system, source, unknown) | WP03 | [P] |
| T014 | Implement `Safety` enum + `SAFETY_REGISTRY` seeded from `_EXEMPT_COMMANDS` baseline in `compat/safety.py` | WP04 | — |
| T015 | Implement `register_safety()` API (for mode predicates) and `classify(invocation)` with fail-closed default | WP04 | — |
| T016 | Architectural test: enumerate every typer command and assert unregistered commands are observably unsafe | WP04 | [P] |
| T017 | Create `compat/_adapters/version_checker.py` wrapping `core.version_checker` | WP05 | [P] |
| T018 | Create `compat/_adapters/gate.py` wrapping `migration.gate` | WP05 | [P] |
| T019 | Create `compat/_adapters/detector.py` wrapping `upgrade.detector` | WP05 | [P] |
| T020 | Architectural test: shim modules contain only delegation (no logic) | WP05 | [P] |
| T021 | Implement `Plan`, `Decision`, `CliStatus`, `ProjectStatus`, `MigrationStep`, `Fr023Case`, `Invocation` dataclasses in `compat/planner.py` | WP06 | — |
| T022 | Implement `messages.py` catalog (FR-023 case → human + JSON) with sanitisation | WP06 | — |
| T023 | Implement `decide()` table per data-model §2 | WP06 | — |
| T024 | Implement `plan(...)` entry point wiring providers, cache, safety, adapters; harden YAML load (256 KB cap, integer range) | WP06 | — |
| T025 | Wire `compat/__init__.py` public API (Plan, Decision, plan, classify, providers, NagCache, InstallMethod) | WP06 | — |
| T026 | Unit tests covering every Decision × FR-023 case + corrupt metadata, missing project, no-network | WP06 | [P] |
| T027 | Add `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA` to `migration/schema_version.py` (keep `REQUIRED_SCHEMA_VERSION` as deprecated alias) | WP07 | — |
| T028 | Update `migration/gate.py` to delegate to `compat.planner.plan(...)` (becomes a thin shim) | WP07 | — |
| T029 | Update existing schema-version tests to assert range semantics; preserve all migration tests (NFR-006) | WP07 | — |
| T030 | Update `cli/helpers.py` typer callback to call `compat.plan(...)` and render decision via `rich.Console` | WP08 | — |
| T031 | Implement nag rendering (single line) and block rendering (≤4 lines, exit codes 4/5/6) | WP08 | — |
| T032 | Suppress nag when `--json`, `--quiet`, no-TTY, or CI predicate holds | WP08 | — |
| T033 | Integration tests: safe matrix, unsafe matrix, CI determinism (zero outbound calls) | WP08 | [P] |
| T034 | Add `--cli`, `--project`, `--yes`, `--no-nag` flags to `cli/commands/upgrade.py`; `--yes` aliases `--force` | WP09 | — |
| T035 | Implement `--cli` mode: print install-method-specific guidance, succeed outside any project | WP09 | — |
| T036 | Implement `--project` mode: restrict behavior to current-project compatibility and migrations | WP09 | — |
| T037 | Implement `--dry-run --json` / `--json` per `contracts/compat-planner.json`; correct exit codes | WP09 | — |
| T038 | Integration tests for `upgrade` command across all 5 FR-023 cases (matches contract examples) | WP09 | [P] |
| T039 | Register dashboard mode-aware safety predicate (read-only safe; write/init/sync/repair unsafe) | WP10 | — |
| T040 | Register doctor mode-aware safety predicate (diagnostic safe; repair/fix unsafe) | WP10 | — |
| T041 | Integration tests for dashboard / doctor mode-split under schema mismatch | WP10 | [P] |
| T042 | Rewrite `docs/how-to/install-and-upgrade.md`: CLI vs project upgrade, all FR-023 cases worked, new flags, env vars, exit codes, link to JSON contract | WP11 | — |

---

## Work Packages

### WP01 — compat package foundation: LatestVersionProvider

**Goal**: Establish the `src/specify_cli/compat/` package with the network abstraction layer. This unblocks every later WP that consumes a "latest CLI version" signal.
**Priority**: P0 (foundation).
**Independent test**: `pytest tests/specify_cli/compat/test_provider_pypi.py tests/specify_cli/compat/test_provider_no_network.py` — all green; no real network calls (mocked via httpx).
**Estimated prompt size**: ~360 lines.

**Included subtasks**:
- [x] T001 Create `compat/` package skeleton (no `__init__.py` exports yet — empty placeholder) (WP01)
- [x] T002 Implement `LatestVersionProvider` Protocol + `LatestVersionResult` dataclass in `compat/provider.py` (WP01)
- [x] T003 Implement `PyPIProvider` (httpx, 2s timeout, no redirects, 1MB body cap, version sanitisation) (WP01)
- [x] T004 Implement `NoNetworkProvider` and `FakeLatestVersionProvider` (test double) (WP01)
- [x] T005 Unit tests for all three providers with network mocked (WP01)

**Implementation sketch**: Create `compat/__init__.py` (empty placeholder; WP06 will populate exports). Create `compat/provider.py` with `LatestVersionResult`, the `LatestVersionProvider` Protocol, and three implementations: `PyPIProvider`, `NoNetworkProvider`, `FakeLatestVersionProvider`. Sanitise parsed version strings. Mock httpx in tests with `respx` (preferred) or `pytest-httpx`.

**Parallel opportunities**: Tests can be written in parallel with implementation once interface is locked.
**Dependencies**: none.
**Risks**: dependency `respx` may not be in test deps — use `pytest-httpx` or stdlib `unittest.mock` if it isn't.
**Prompt**: [`tasks/WP01-compat-foundation-provider.md`](tasks/WP01-compat-foundation-provider.md)

---

### WP02 — NagCache with security properties

**Goal**: Per-user JSON cache that throttles the nag, invalidates on CLI version change, and resists symlink / permission attacks.
**Priority**: P0 (foundation).
**Independent test**: `pytest tests/specify_cli/compat/test_cache.py` — covers throttle, invalidation, perms, symlink rejection, oversized files, clock skew.
**Estimated prompt size**: ~360 lines.

**Included subtasks**:
- [ ] T006 Implement `NagCacheRecord` dataclass + `NagCache` class in `compat/cache.py` (WP02)
- [ ] T007 Add 0o600 file mode + 0o700 parent dir mode + symlink-resistant lstat checks (WP02)
- [ ] T008 Implement throttle predicate with clock-skew handling and version-key invalidation (WP02)
- [ ] T009 Implement throttle/no-nag config loading (env > YAML > default; range-validated) (WP02)
- [ ] T010 Unit tests for cache with corrupt files, symlinks, oversized state, perm assertions (WP02)

**Implementation sketch**: `NagCache.default()` resolves cache path via `platformdirs` if available, manual XDG fallback otherwise. `read()` returns `NagCacheRecord | None`; refuses symlinks, oversized files, mismatched ownership. `write(record)` opens with `O_CREAT|O_WRONLY|O_TRUNC` and mode `0o600`. Throttle predicate handles clock moving backwards (treat as expired). Config loader checks env var first, then YAML at `$XDG_CONFIG_HOME/spec-kitty/upgrade.yaml`.

**Parallel opportunities**: Tests + implementation parallelizable per subtask.
**Dependencies**: none (independent of WP01).
**Risks**: Windows perm semantics differ — POSIX-only mode set; on Windows, rely on per-user cache directory.
**Prompt**: [`tasks/WP02-nag-cache.md`](tasks/WP02-nag-cache.md)

---

### WP03 — Install-method detection + upgrade hint catalog

**Goal**: Detect how the user installed `spec-kitty-cli` and produce a sanitised, copy-pasteable upgrade hint per install method.
**Priority**: P0 (foundation).
**Independent test**: `pytest tests/specify_cli/compat/test_install_method.py` — covers all seven branches.
**Estimated prompt size**: ~290 lines.

**Included subtasks**:
- [ ] T011 Implement `InstallMethod` enum + detection chain in `compat/_detect/install_method.py` (WP03)
- [ ] T012 Implement `UpgradeHint` builder with sanitised commands per install method (WP03)
- [ ] T013 Unit tests for each install-method branch (pipx, pip-user, pip-system, brew, system, source, unknown) (WP03)

**Implementation sketch**: Detection chain per research §R-03. Each step inspects `sys.executable`, `importlib.metadata.distribution(...)`, or shells out (only for `brew --prefix` with 1s timeout). `UpgradeHint` builder maps `InstallMethod` → command (regex-sanitised) or multi-line note (for `source` / `unknown`).

**Parallel opportunities**: Each test branch independent.
**Dependencies**: none.
**Risks**: Test must mock `sys.executable` and `importlib.metadata` carefully.
**Prompt**: [`tasks/WP03-install-method-detection.md`](tasks/WP03-install-method-detection.md)

---

### WP04 — Safety registry with fail-closed default

**Goal**: Central `SAFETY_REGISTRY` seeded for known commands; `classify()` returns `Safety.SAFE | Safety.UNSAFE`; unregistered commands fail-closed (UNSAFE).
**Priority**: P0 (foundation).
**Independent test**: `pytest tests/specify_cli/compat/test_safety.py tests/architectural/test_safety_registry_completeness.py` — registry behavior + architectural test.
**Estimated prompt size**: ~310 lines.

**Included subtasks**:
- [ ] T014 Implement `Safety` enum + `SAFETY_REGISTRY` seeded from `_EXEMPT_COMMANDS` baseline in `compat/safety.py` (WP04)
- [ ] T015 Implement `register_safety()` API (for mode predicates) and `classify(invocation)` with fail-closed default (WP04)
- [ ] T016 Architectural test: enumerate every typer command and assert unregistered commands are observably unsafe (WP04)

**Implementation sketch**: Seed registry centrally — extends today's `{"upgrade", "init"}`. Safe baseline = `{upgrade, init, status, doctor, dashboard, --help, --version}` plus known read-only `agent` subcommands. `register_safety(command_path, predicate=None)` — predicate=None means flat-safe; predicate=callable means mode-aware. `classify(invocation)` looks up by `invocation.command_path`; unmatched → UNSAFE. Architectural test discovers all typer commands and checks each is either in the registry or treated unsafe.

**Parallel opportunities**: Tests parallel with implementation.
**Dependencies**: none. (Note: the planner package and the mode-predicate package consume this WP's output; neither is required to land first.)
**Risks**: Need to enumerate every `agent` subcommand carefully — can be lazy: registry only needs entries for *safe* commands; everything else is unsafe by default.
**Prompt**: [`tasks/WP04-safety-registry.md`](tasks/WP04-safety-registry.md)

---

### WP05 — Adapters wrapping existing modules

**Goal**: Wrap `core.version_checker`, `migration.gate`, and `upgrade.detector` as private adapters under `compat/_adapters/`. Existing imports keep working as thin shims; the planner consumes adapters.
**Priority**: P0 (foundation, parallel to WP01-04).
**Independent test**: `pytest tests/architectural/test_compat_shims.py` and any module-import smoke test.
**Estimated prompt size**: ~280 lines.

**Included subtasks**:
- [ ] T017 Create `compat/_adapters/version_checker.py` wrapping `core.version_checker` (WP05)
- [ ] T018 Create `compat/_adapters/gate.py` wrapping `migration.gate` (WP05)
- [ ] T019 Create `compat/_adapters/detector.py` wrapping `upgrade.detector` (WP05)
- [ ] T020 Architectural test: shim modules contain only delegation (no logic) (WP05)

**Implementation sketch**: Each adapter file in `compat/_adapters/` re-exports the public symbols of the corresponding existing module under a stable internal API. The existing modules remain unchanged in WP05; later WPs (WP07 for `migration.gate`) modify them to delegate. Architectural test asserts adapters are pure re-exports.

**Parallel opportunities**: All three adapters independent.
**Dependencies**: none.
**Risks**: Must not change behavior of existing modules in this WP — pure re-export only.
**Prompt**: [`tasks/WP05-compat-adapters.md`](tasks/WP05-compat-adapters.md)

---

### WP06 — Compatibility planner core (Plan, Decision, decide, plan)

**Goal**: The integration WP. Implement the planner core: dataclasses (Plan/Decision/CliStatus/ProjectStatus/MigrationStep/Invocation), the `decide()` table, the `plan(...)` entry point, the message catalog, and wire `compat/__init__.py` public API.
**Priority**: P0 (depends on WP01-05).
**Independent test**: `pytest tests/specify_cli/compat/test_planner.py tests/specify_cli/compat/test_messages.py`.
**Estimated prompt size**: ~520 lines.

**Included subtasks**:
- [ ] T021 Implement `Plan`, `Decision`, `CliStatus`, `ProjectStatus`, `MigrationStep`, `Fr023Case`, `Invocation` dataclasses in `compat/planner.py` (WP06)
- [ ] T022 Implement `messages.py` catalog (FR-023 case → human + JSON) with sanitisation (WP06)
- [ ] T023 Implement `decide()` table per data-model §2 (WP06)
- [ ] T024 Implement `plan(...)` entry point wiring providers, cache, safety, adapters; harden YAML load (256 KB cap, integer range) (WP06)
- [ ] T025 Wire `compat/__init__.py` public API (Plan, Decision, plan, classify, providers, NagCache, InstallMethod) (WP06)
- [ ] T026 Unit tests covering every Decision × FR-023 case + corrupt metadata, missing project, no-network (WP06)

**Implementation sketch**: Dataclasses match `data-model.md`. `messages.py` catalogs every FR-023 case with `render_human()` and `render_json()`. `decide()` follows the truth table from data-model §2. `plan()` builds CliStatus, ProjectStatus, classifies safety, calls `decide()`, builds rendered output. Test matrix covers every cell of the decision table, including the `dashboard --repair` mode case (uses safety predicate registered in WP04).

**Parallel opportunities**: Tests parallel with implementation; messages and dataclasses parallel.
**Dependencies**: WP01, WP02, WP03, WP04, WP05.
**Risks**: This is the WP most likely to need rework after CLI integration WPs surface real-world gaps. Keep `decide()` pure (no I/O) so tests stay fast.
**Prompt**: [`tasks/WP06-planner-core.md`](tasks/WP06-planner-core.md)

---

### WP07 — Schema range activation (MIN/MAX) + gate delegation

**Goal**: Activate the schema range in `migration/schema_version.py` (split `REQUIRED_SCHEMA_VERSION` into `MIN_SUPPORTED_SCHEMA` / `MAX_SUPPORTED_SCHEMA`) and convert `migration/gate.py` into a thin delegate to `compat.planner.plan(...)`.
**Priority**: P1 (depends on WP06).
**Independent test**: `pytest tests/specify_cli/migration/` — including any updated schema-version tests; existing migration test suite still passes (NFR-006).
**Estimated prompt size**: ~270 lines.

**Included subtasks**:
- [ ] T027 Add `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA` to `migration/schema_version.py` (keep `REQUIRED_SCHEMA_VERSION` as deprecated alias) (WP07)
- [ ] T028 Update `migration/gate.py` to delegate to `compat.planner.plan(...)` (becomes a thin shim) (WP07)
- [ ] T029 Update existing schema-version tests to assert range semantics; preserve all migration tests (NFR-006) (WP07)

**Implementation sketch**: Set `MIN_SUPPORTED_SCHEMA` and `MAX_SUPPORTED_SCHEMA` to values matching today's migration registry (read it; pick max as both min and max so the gate is a no-op until a future bump). Keep `REQUIRED_SCHEMA_VERSION` as `MIN_SUPPORTED_SCHEMA` for backward compat. `migration/gate.check_schema_version` becomes: build an `Invocation` from typer context, call `compat.plan(...)`, raise SystemExit with the exit code from the plan.

**Parallel opportunities**: schema_version.py and gate.py changes independent.
**Dependencies**: WP06.
**Risks**: RP-01 — must NOT block existing projects in this release. Set MIN = MAX = current schema so gate is effectively a no-op for now.
**Prompt**: [`tasks/WP07-schema-activation.md`](tasks/WP07-schema-activation.md)

---

### WP08 — CLI typer callback wired through planner + safe/unsafe matrix tests

**Goal**: Update `cli/helpers.py` so the typer callback consults `compat.plan(...)` and renders the result. Add the integration tests for the safe/unsafe matrix and CI determinism.
**Priority**: P1 (depends on WP06, WP07).
**Independent test**: `pytest tests/cli_gate/` — full safe matrix runs under schema mismatch; unsafe matrix blocks; CI mode makes zero outbound calls.
**Estimated prompt size**: ~430 lines.

**Included subtasks**:
- [ ] T030 Update `cli/helpers.py` typer callback to call `compat.plan(...)` and render decision via `rich.Console` (WP08)
- [ ] T031 Implement nag rendering (single line) and block rendering (≤4 lines, exit codes 4/5/6) (WP08)
- [ ] T032 Suppress nag when `--json`, `--quiet`, no-TTY, or CI predicate holds (WP08)
- [ ] T033 Integration tests: safe matrix, unsafe matrix, CI determinism (zero outbound calls) (WP08)

**Implementation sketch**: typer callback consults the planner once per invocation. If `decision == ALLOW`: pass through. If `ALLOW_WITH_NAG` and not suppressed: print `plan.rendered_human` to stderr (so it doesn't pollute stdout/JSON), then pass through. Block decisions: print to stderr, raise `SystemExit(plan.exit_code)`. Tests use a fixture project + injected `LatestVersionProvider` and `NagCache`.

**Parallel opportunities**: Three test files independent (`test_safe_commands.py`, `test_unsafe_commands.py`, `test_ci_determinism.py`).
**Dependencies**: WP06, WP07.
**Risks**: Typer callback timing — must run before subcommand dispatch. Inspect the existing `BannerGroup` and replicate the gate's invocation point.
**Prompt**: [`tasks/WP08-cli-callback-integration.md`](tasks/WP08-cli-callback-integration.md)

---

### WP09 — `spec-kitty upgrade` command surface (--cli, --project, --yes, --no-nag, --json)

**Goal**: Extend `cli/commands/upgrade.py` with the new flag set. `--cli` prints upgrade guidance even outside a project; `--project` restricts to current-project migrations; `--yes` aliases `--force`; `--no-nag` suppresses nag; `--json` and `--dry-run --json` emit the contract.
**Priority**: P1 (depends on WP06).
**Independent test**: `pytest tests/specify_cli/cli/commands/test_upgrade_command.py` — covers all five FR-023 cases and the contract examples.
**Estimated prompt size**: ~470 lines.

**Included subtasks**:
- [ ] T034 Add `--cli`, `--project`, `--yes`, `--no-nag` flags to `cli/commands/upgrade.py`; `--yes` aliases `--force` (WP09)
- [ ] T035 Implement `--cli` mode: print install-method-specific guidance, succeed outside any project (WP09)
- [ ] T036 Implement `--project` mode: restrict behavior to current-project compatibility and migrations (WP09)
- [ ] T037 Implement `--dry-run --json` / `--json` per `contracts/compat-planner.json`; correct exit codes (WP09)
- [ ] T038 Integration tests for `upgrade` command across all 5 FR-023 cases (matches contract examples) (WP09)

**Implementation sketch**: Existing `upgrade` command keeps its core flow (`--dry-run`, `--force`, `--target`, `--verbose`, `--no-worktrees`). New flags are additive. `--cli` short-circuits the project-side flow; `--project` short-circuits the CLI nag side; `--cli` + `--project` together is a usage error (`BLOCK_INCOMPATIBLE_FLAGS`, exit 2). `--yes` is wired to the existing `--force` confirmation behavior. JSON output is built from `Plan.rendered_json` (already shaped by the planner).

**Parallel opportunities**: Tests independent of code; subtasks otherwise sequential within `upgrade.py`.
**Dependencies**: WP06.
**Risks**: must not break existing `upgrade` callers — every existing flag must continue working unchanged (C-006).
**Prompt**: [`tasks/WP09-upgrade-command-surface.md`](tasks/WP09-upgrade-command-surface.md)

---

### WP10 — Mode-aware safety predicates for dashboard and doctor

**Goal**: Register the dashboard and doctor mode predicates in `SAFETY_REGISTRY` so that read-only modes are SAFE and write/repair modes are UNSAFE under schema mismatch.
**Priority**: P2 (depends on WP04, WP06).
**Independent test**: `pytest tests/cli_gate/test_dashboard_modes.py tests/cli_gate/test_doctor_modes.py`.
**Estimated prompt size**: ~250 lines.

**Included subtasks**:
- [ ] T039 Register dashboard mode-aware safety predicate (read-only safe; write/init/sync/repair unsafe) (WP10)
- [ ] T040 Register doctor mode-aware safety predicate (diagnostic safe; repair/fix unsafe) (WP10)
- [ ] T041 Integration tests for dashboard / doctor mode-split under schema mismatch (WP10)

**Implementation sketch**: Inspect existing flag schemas in `cli/commands/dashboard.py` and `cli/commands/doctor.py`. Build predicate functions that inspect `Invocation.raw_args` for write-mode flags (e.g. `--repair`, `--fix`, `--init`, `--sync`) and return `Safety.UNSAFE` when present, else `Safety.SAFE`. Register predicates via `compat.safety.register_safety("dashboard", predicate=...)`. Integration tests use the fixture-project gate.

**Parallel opportunities**: Tests parallel.
**Dependencies**: WP04, WP06.
**Risks**: If `dashboard` / `doctor` don't actually have distinct modes today, register them as flat-safe with a docstring noting the predicate hook is reserved for future modes.
**Prompt**: [`tasks/WP10-mode-aware-safety.md`](tasks/WP10-mode-aware-safety.md)

---

### WP11 — Documentation rewrite (docs/how-to/install-and-upgrade.md)

**Goal**: Make SC-008 land. Rewrite the install-and-upgrade how-to to explain "upgrade the CLI" vs "migrate this project", with worked examples for every FR-023 case, the new flags, the env vars, the exit codes, and a link to the JSON contract.
**Priority**: P3 (depends on WP08, WP09).
**Independent test**: manual review during mission acceptance; markdown lint clean.
**Estimated prompt size**: ~220 lines.

**Included subtasks**:
- [ ] T042 Rewrite `docs/how-to/install-and-upgrade.md`: CLI vs project upgrade, all FR-023 cases worked, new flags, env vars, exit codes, link to JSON contract (WP11)

**Implementation sketch**: Use the quickstart's structure as a starting point; adapt for end-user prose. Document `SPEC_KITTY_NO_NAG`, `SPEC_KITTY_NAG_THROTTLE_SECONDS`, exit codes 4/5/6/2, the `--cli` / `--project` / `--yes` / `--no-nag` flags, and link to `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json` for tooling consumers.

**Parallel opportunities**: standalone WP.
**Dependencies**: WP08, WP09 (so flags and env vars actually work when documented).
**Risks**: Drift from implementation if WP08/WP09 changes shape — last WP intentionally to minimize this.
**Prompt**: [`tasks/WP11-documentation.md`](tasks/WP11-documentation.md)

---

## Execution graph

```
WP01 ─┐
WP02 ─┤
WP03 ─┼─→ WP06 ─┬─→ WP07
WP04 ─┤         ├─→ WP08 ─┐
WP05 ─┘         ├─→ WP09 ─┴─→ WP11
                └─→ WP10
```

WP01–WP05 can run fully in parallel. WP06 is the integration WP. WP07–WP10 fan out from WP06; WP11 is a single doc WP at the end.

## MVP scope recommendation

If the user asks for an MVP slice instead of the full mission: **WP01 + WP02 + WP06 + WP07 + WP08** delivers the core nag + lazy gate (without the new `upgrade` flags, mode-aware safety, or doc rewrite). Everything else can ship in a follow-up.
