# Mission Review Report: cli-upgrade-nag-lazy-project-migrations-01KQ6YDN

**Reviewer**: Claude Opus (post-merge mission-review skill)
**Date**: 2026-04-27
**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN` — *CLI Upgrade Nag and Lazy Project Migration*
**Mission ID**: `01KQ6YDNMX2X2AN4WH43R5K2ZS` (mission_number 103)
**Mission type**: `software-dev`
**Target branch**: `main`
**Baseline commit**: `0ccd9055cb84248499017158d4ff924abf422f98` ("Phase 6 WP6.4: documentation mission composition rewrite (#502)")
**Merge commit**: `366a338aaf13dccbeb1fd50c8499ee4f19ade516` (squash merge)
**HEAD at review**: `366a338aaf13dccbeb1fd50c8499ee4f19ade516`
**WPs reviewed**: WP01..WP11 (11 work packages, all `done`/`approved`)
**Test result post-merge**: `pytest` 613/613 PASS in compat / cli_gate / migration / upgrade-command suites; preserved suites (`tests/specify_cli/upgrade/`, `tests/cross_cutting/versioning/`) 75/75 PASS — NFR-006 satisfied.

---

## 1. Mission timeline (status.events.jsonl scan)

- 82 status events recorded.
- 11 `for_review` → `in_progress` (review-claim) transitions; 11 `in_progress`/`for_review` → `approved` transitions; 0 rejection cycles (no `to_lane:"planned"` transitions following a `to_lane:"for_review"`).
- 0 review-cycle directories under `tasks/WP*/` (confirmed by `ls`).
- All `force=true` flags are on the procedural status mutators (finalize-tasks bootstrap and the runtime "started review" / "approved" calls) — none of them are arbiter overrides bypassing a rejection.
- Approver: `claude:opus:python-reviewer:reviewer` for every WP, with one human `user` (Robert Douglass) confirmation event recorded per WP approval.

**Verdict on process**: clean run, no signals warranting extra scrutiny on a specific WP.

---

## 2. Diff coverage map (WP-owned files vs. actual diff)

`git diff 0ccd9055..366a338 --name-only | grep -v 'kitty-specs/'` lists 42 non-spec files. Cross-reference of WP frontmatter `owned_files` against the diff:

| WP | Owned (frontmatter) | Diff hit | Notes |
|---|---|---|---|
| WP01 | `compat/__init__.py`, `compat/provider.py`, tests | YES | provider, fake/no-network/pypi tests all present |
| WP02 | `compat/cache.py`, `compat/config.py`, tests | YES | both modules + tests in diff |
| WP03 | `compat/_detect/install_method.py`, `compat/upgrade_hint.py`, tests | YES | both modules + tests in diff |
| WP04 | `compat/safety.py`, architectural test | YES | safety + `test_safety_registry_completeness.py` present |
| WP05 | `compat/_adapters/*.py`, architectural test | YES | three adapters + `test_compat_shims.py` + `_fixtures/bad_adapter.py` |
| WP06 | `compat/planner.py`, `compat/messages.py`, tests | YES | planner (871 LoC), messages (214 LoC), planner & messages tests |
| WP07 | `migration/schema_version.py`, `migration/gate.py`, tests | YES | range constants added, gate becomes 91-line shim, range test new |
| WP08 | `cli/helpers.py`, `tests/cli_gate/*` | YES | `_render_nag_if_needed`, all 5 cli_gate test files |
| WP09 | `cli/commands/upgrade.py`, command test | YES | 362 net new LoC in upgrade.py, 726-LoC command test |
| WP10 | `compat/safety_modes.py`, `tests/cli_gate/test_dashboard_modes.py`, `test_doctor_modes.py` | YES | mode predicates module, dashboard/doctor mode tests |
| WP11 | `docs/how-to/install-and-upgrade.md` | YES | 216-line doc rewrite |

No "owned but not changed" or "changed but not owned" mismatches detected. Cross-WP integration in `compat/__init__.py` shows clean composition (WP01 placeholder superseded by WP06 exports, with WP10 idempotently appending the `register_mode_predicates()` invocation).

---

## 3. FR Coverage Matrix

Tests located under `tests/specify_cli/compat/`, `tests/cli_gate/`, `tests/specify_cli/cli/commands/test_upgrade_command.py`, `tests/architectural/`, `tests/specify_cli/migration/`. Adequacy is the reviewer's judgment whether each test actually constrains the code path.

| FR | Description | WP Owner | Test File(s) | Adequacy | Notes |
|---|---|---|---|---|---|
| FR-001 | Distinguish CLI vs project status (human/JSON/exit) | WP06 | `test_planner.py`, `test_messages.py`, `test_upgrade_command.py` | ADEQUATE | distinct fr023_case + JSON tokens covered |
| FR-002 | Throttled passive nag on startup | WP08 | `test_safe_commands.py`, `test_unsafe_commands.py`, `test_ci_determinism.py` | ADEQUATE | nag rendered when ALLOW_WITH_NAG and TTY |
| FR-003 | Nag does not block compatible commands | WP08 | `test_safe_commands.py` | ADEQUATE | safe matrix exits 0 with nag |
| FR-004 | Throttle window default 24h, configurable | WP02 | `test_cache.py`, `test_config.py` | ADEQUATE | `_DEFAULT_THROTTLE_SECONDS=86400`, env override + range validation tested |
| FR-005 | No network in CI/non-interactive | WP01/WP08 | `test_provider_no_network.py`, `test_ci_determinism.py` | ADEQUATE | NoNetworkProvider opens no socket; CI predicate tested |
| FR-006 | Exact upgrade instructions per install method | WP03 | `test_install_method.py`, `test_upgrade_hint.py` | ADEQUATE | each install method covered |
| FR-007 | Manual fallback when install method unknown | WP03 | `test_upgrade_hint.py` | ADEQUATE | UNKNOWN→`note` branch enforced via dataclass invariant |
| FR-008 | Schema/version compatibility check before unsafe commands | WP07/WP08 | `test_unsafe_commands.py`, `test_planner.py` | ADEQUATE | gate now delegates to planner; unsafe blocked |
| FR-009 | Block stale-but-migratable; remediation message | WP06/WP08 | `test_planner.py`, `test_unsafe_commands.py` | ADEQUATE | exit 4 + message verified |
| FR-010 | Block too-new project; CLI-upgrade message | WP06/WP08 | `test_planner.py`, `test_upgrade_command.py` | ADEQUATE | exit 5 + message verified |
| FR-011 | Help/diag/upgrade subcommands always run | WP04/WP08 | `test_safety.py`, `test_safe_commands.py` | ADEQUATE | safe matrix preserved under schema mismatch |
| FR-012 | `upgrade --dry-run` shows status without writes | WP09 | `test_upgrade_command.py` | ADEQUATE | dry-run path; no project file writes |
| FR-013 | `upgrade` inside project: check + apply | WP09 | `test_upgrade_command.py` | ADEQUATE | flow exercised |
| FR-014 | `upgrade` outside project does not fail | WP09 | `test_upgrade_command.py` | ADEQUATE | `--cli` mode tested + default outside-project still errors clearly (per WP09 FR-014 fallback handling) |
| FR-015 | `--project` restricts to project compat | WP09 | `test_upgrade_command.py` | ADEQUATE | `_check_project_not_too_new` plus planner JSON path |
| FR-016 | `--cli` restricts to CLI guidance | WP09 | `test_upgrade_command.py` | ADEQUATE | `_run_cli_mode` covered |
| FR-017 | `--yes` non-interactive; `--force` alias | WP09 | `test_upgrade_command.py` | ADEQUATE | `confirm = yes or force` and CHK037 enforcement covered |
| FR-018 | Migrations remain idempotent and ordered | preserved | `tests/specify_cli/upgrade/*` (NFR-006) | ADEQUATE | suite passes unchanged |
| FR-019 | Dry-run reports files-modified when computable | WP09/WP06 | `test_upgrade_command.py` | PARTIAL | the planner's pending_migrations always emits `files_modified=null` for current registry; see RISK-2 |
| FR-020 | No "upgrade all projects" introduced | (negative) | grep | ADEQUATE | no such command introduced |
| FR-021 | No global registry / cross-project state | (negative) | grep + design | ADEQUATE | NagCache is per-user only; no project enumeration |
| FR-022 | Stable JSON output for upgrade planning | WP06/WP09 | `test_messages.py`, `test_upgrade_command.py` | ADEQUATE | `render_json` validates against contract |
| FR-023 | Distinct user-facing case strings | WP06 | `test_messages.py`, `test_planner.py` | PARTIAL | `Fr023Case.PROJECT_NOT_INITIALIZED` is defined but never emitted by `decide()` (case never reached); see DRIFT-1 |
| FR-024 | Single planner authority for compat decision | WP07 | `test_compat_shims.py`, gate body | ADEQUATE | `migration/gate.py` delegates to planner; AST-level no-logic adapter test |
| FR-025 | Nag cache invalidated on CLI version change | WP02/WP06 | `test_cache.py` (`is_fresh` predicate), `test_planner.py` | ADEQUATE | `cli_version_key != installed → cache_record = None` |

**Legend**: ADEQUATE = test constrains the required behavior; PARTIAL = behavior exists but contract drift or registry gap; MISSING = no test found.

---

## 4. NFR Verification

| NFR | Threshold | Verification | Status |
|---|---|---|---|
| NFR-001 | <100 ms startup overhead when nag cache fresh | NOT MEASURED post-merge — no benchmark file in tests | NOTE |
| NFR-002 | 2 s timeout, fail open, no stack trace | `PyPIProvider.__init__(timeout_s=2.0)`; `httpx.TimeoutException` caught; `provider` returns `LatestVersionResult` not raises | ADEQUATE |
| NFR-003 | No project writes from non-`upgrade` startup | typer callback only renders + writes nag cache (per-user, not project) | ADEQUATE |
| NFR-004 | Determinism in CI/non-interactive | `test_ci_determinism.py` asserts zero outbound calls when CI/no-TTY | ADEQUATE |
| NFR-005 | Testable without network | Provider abstraction; FakeProvider used in all planner tests | ADEQUATE |
| NFR-006 | Existing migration tests still pass | `tests/specify_cli/upgrade/` 27 PASS, `tests/cross_cutting/versioning/` 24 PASS | ADEQUATE |
| NFR-007 | Concise output | `messages.render_human` slices to ≤4 lines | ADEQUATE |
| NFR-008 | No SaaS/tracker dependency | grep for new outbound hostnames: only `pypi.org`; no `spec-kitty-saas` / `spec-kitty-tracker` | ADEQUATE |
| NFR-009 | Throttle window configurable | `SPEC_KITTY_NAG_THROTTLE_SECONDS` env + YAML; range-validated in `_parse_throttle` | ADEQUATE |

NFR-001 is the only unmeasured NFR. Performance asymptote is plausible (planner is pure Python with one file `lstat`+`open` at startup when cache hit), but no in-tree benchmark exists. Recommend a `pytest-benchmark` micro-benchmark in a follow-up.

---

## 5. Drift Findings

### DRIFT-1: `Fr023Case.PROJECT_NOT_INITIALIZED` is defined but never emitted

**Type**: PUNTED-FR (partial)
**Severity**: LOW
**Spec reference**: FR-023; data-model.md §1.9
**Evidence**:
- `src/specify_cli/compat/planner.py:60` defines the enum value.
- `src/specify_cli/compat/planner.py:317-335` (`decide()` body): no row maps `ProjectState.UNINITIALIZED` or `ProjectState.NO_PROJECT` to `Fr023Case.PROJECT_NOT_INITIALIZED`. The "Row 4" comment at line 328 explicitly says these states fall through to `Fr023Case.NONE` / `Fr023Case.CLI_UPDATE_AVAILABLE`.
- `src/specify_cli/compat/messages.py:69`: catalog entry exists (`Fr023Case.PROJECT_NOT_INITIALIZED: ""`) but the empty template proves it is never actually rendered.

**Analysis**: spec.md FR-023 lists `project_not_initialized` as one of five distinguished user-facing cases. Data-model §1.9 says it should fire when `ProjectState in {NO_PROJECT, UNINITIALIZED}`. The planner's `decide()` table never returns it. Practically the gate (`migration/gate.py`) short-circuits when `.kittify/` is absent, so this case is unreachable from the typer callback today; but the upgrade command's `--project` mode (which calls the planner directly) would emit `case=none` for an uninitialized project, masquerading as ALLOW. This is contract drift, not a runtime bug — the JSON contract enum has the value but the producer never emits it.

**Recommended follow-up**: extend `decide()` so `state in (NO_PROJECT, UNINITIALIZED) and safety == UNSAFE` returns `(Decision.ALLOW, Fr023Case.PROJECT_NOT_INITIALIZED)` (or a new dedicated decision); update `messages.py` template; add a planner test row.

---

### DRIFT-2: Planner does not call `auto_discover_migrations()` before reading the registry

**Type**: BOUNDARY-CONDITION / contract drift on FR-019
**Severity**: MEDIUM
**Spec reference**: FR-019, contract `pending_migrations` array
**Evidence**:
- `src/specify_cli/compat/planner.py:535-575` (`_pending_migrations_for`): reads `MigrationRegistry.get_all()` directly without first calling `auto_discover_migrations()`.
- `src/specify_cli/cli/commands/upgrade.py:459` calls `auto_discover_migrations()` before its own usage of the registry, but `migration/gate.py` and `cli/helpers.py` do not.
- Reproducer (a clean Python process):
  ```
  >>> from specify_cli.compat.planner import _pending_migrations_for, ProjectStatus, ProjectState
  >>> ps = ProjectStatus(state=ProjectState.STALE, project_root=None, schema_version=2,
  ...                    min_supported=3, max_supported=3, metadata_error=None)
  >>> _pending_migrations_for(ps)   # → ()
  ```
  After explicit `auto_discover_migrations()`, the same call returns 16 steps.

**Analysis**: when the planner is invoked through the typer callback gate (typical user path) without the upgrade command having already run, the registry is empty in the worker process, so `pending_migrations` in the JSON contract is always `[]` for `BLOCK_PROJECT_MIGRATION`. The `rendered_human` block message remains correct (it does not enumerate migrations), but the contract field `pending_migrations` is silently empty — violating FR-019's "report the files they would modify during dry-run". The existing planner tests do not catch this because they construct fixture projects against an in-process registry that was already populated by another import side effect (e.g., the upgrade-command test imports the registry module which auto-discovers eagerly in some paths). In production, a fresh `spec-kitty status` invocation in a stale project would emit `pending_migrations=[]`.

**Recommended follow-up**: have `_pending_migrations_for` (or `_plan_impl`) call `auto_discover_migrations()` once before iterating the registry. Add a test that deletes `MigrationRegistry._migrations` between runs and asserts non-empty `pending_migrations`.

---

### DRIFT-3: Migration registry items have no `target_schema_version` or `files_modified` attrs

**Type**: PARTIAL-FR / data-model fidelity
**Severity**: LOW (related to DRIFT-2)
**Spec reference**: data-model.md §1.6 (`MigrationStep`); FR-019
**Evidence**:
- `src/specify_cli/upgrade/migrations/m_3_0_0_canonical_context.py` and every other migration class: only `migration_id`, `description`, `target_version` (semver string) are defined.
- `src/specify_cli/compat/planner.py:549-555`: `schema_int = getattr(m, "target_schema_version", None)`; falls back to `int(target_v.major)`. `files_raw = getattr(m, "files_modified", None)` → always `None`.

**Analysis**: data-model §1.6 promises `target_schema_version: int` and `files_modified: tuple[Path,...] | None`. The planner uses `getattr` defensively because no migration in `src/specify_cli/upgrade/migrations/` actually exposes either attribute. The fallback `int(target_v.major)` ("3.0.0" → 3) accidentally works for the current registry because all schema-3 migrations have semver major == 3, but this is brittle: any migration whose semver major does not equal its schema would mis-classify. `files_modified` is permanently `null` in the JSON contract, defeating FR-019.

**Recommended follow-up**: add the two fields to `BaseMigration` as optional with a deprecation note; existing migrations stay backwards-compatible; `m_3_*_*` migrations declare schema and known files. Or: explicitly document the inferred-from-semver semantics in data-model.md and accept the partial FR-019 surface.

---

## 6. Risk Findings

### RISK-1: `_pending_migrations_for` emits empty list silently when registry is empty

(Same root as DRIFT-2; called out as risk because of user-visible behavior.)
**Type**: ERROR-PATH / SILENT-EMPTY-RESULT
**Severity**: MEDIUM
**Location**: `src/specify_cli/compat/planner.py:535-575`
**Trigger**: Any call path that reaches `_pending_migrations_for` without first invoking `auto_discover_migrations()` — i.e. the gate path from `migration/gate.py:83` and the nag-cache rendering path from `cli/helpers.py:211`.

**Analysis**: the function is wrapped in a top-level `try/except: return ()` and an inner `try/except: continue`. Both swallow exceptions. A stale project triggers BLOCK_PROJECT_MIGRATION; the user sees the correct exit code 4 and the correct rendered_human, but `--json` consumers will see `pending_migrations: []` instead of the 16-step list. Downstream automation that parses `pending_migrations.length > 0` to decide whether to invoke `spec-kitty upgrade --yes` will mis-decide.

---

### RISK-2: `MigrationStep.files_modified` is permanently `None` in the contract

**Type**: PUNTED-FR
**Severity**: LOW
**Location**: `src/specify_cli/compat/planner.py:556-562`
**Trigger**: any contract consumer expecting non-null `files_modified`.

**Analysis**: see DRIFT-3. JSON-Schema permits `null`, so no validation failure — only an information gap.

---

### RISK-3: `--cli` mode forces `stdout_is_tty=True, env_ci=False` regardless of real env

**Type**: BOUNDARY-CONDITION
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/upgrade.py:232-241` (`_run_cli_mode`) and `:749-757` (`_run_planner_json`).
**Trigger**: `spec-kitty upgrade --cli` invoked under `CI=1` or non-TTY (e.g., a CI runner that wants to print upgrade hints).

**Analysis**: hardcoding these flags means the planner inside `--cli` mode will always select `PyPIProvider` and attempt a network fetch even in CI, contradicting the "CI determinism" spirit of NFR-004 and SC-005 for the explicit `upgrade --cli` case. Mitigating factor: spec.md actually allows network for explicit `upgrade` calls (the spec says nag-path is suppressed, not that the upgrade command itself must be offline). The block message is unchanged; only the `latest_version` field will populate vs. stay null. Worth a comment in code documenting the deliberate choice; otherwise non-blocking.

---

### RISK-4: `Invocation.from_argv` env_ci predicate uses `bool(env_ci_raw)` plus a deny-list

**Type**: BOUNDARY-CONDITION
**Severity**: LOW
**Location**: `src/specify_cli/compat/planner.py:222-223`
**Trigger**: `CI=` (empty string); `CI=0`.

**Analysis**: `env_ci_raw = os.environ.get("CI", "")` then `bool(env_ci_raw and env_ci_raw.lower() not in ("0","false","no","off"))`. This correctly treats `CI=0` and `CI=false` as not-CI. But `Invocation.from_argv` uses different precedence than `cli/helpers.py:_should_suppress_nag`, which uses an inclusion list `not in ("0", "false", "no", "off")`. They agree by chance; future maintainers should note both predicates and keep them in sync. The `migration/gate.py:73` callsite uses yet a third spelling: `bool(os.environ.get("CI"))` — which would treat `CI=0` as truthy. Three different normalizations of the same predicate is a maintenance liability.

**Recommended follow-up**: extract a single `is_ci_env()` helper in `compat/planner.py` and have all three call sites use it.

---

### RISK-5: Nag cache `is_fresh` returns `True` when `delta == throttle_seconds` exactly

**Type**: BOUNDARY-CONDITION
**Severity**: LOW
**Location**: `src/specify_cli/compat/cache.py:343` — `return not delta > throttle_seconds`
**Trigger**: `delta == throttle_seconds` exactly.

**Analysis**: this is an off-by-one boundary at the throttle horizon. The nag will be suppressed for one extra microsecond at the boundary; in practice imperceptible. The data-model says `(now - last_shown_at) >= throttle_seconds` should expire (i.e., the nag should show again). The current `not delta > throttle_seconds` returns `True` (fresh) when delta == throttle, meaning suppress one extra invocation. Trivial; non-blocking.

---

### RISK-6: `FR-014` outside-a-project default-mode still errors

**Type**: AMBIGUITY in spec interpretation
**Severity**: LOW
**Location**: `src/specify_cli/cli/commands/upgrade.py:417-424`
**Trigger**: User runs bare `spec-kitty upgrade` outside any Spec Kitty project.

**Analysis**: spec.md FR-014 says "shall not fail with 'not a Spec Kitty project'; it shall fall through to CLI update guidance behavior". The current code prints `[red]Error:[/red] Not a Spec Kitty project.` and exits 1 unless `--cli` was specified. The implementer interpreted FR-014 narrowly (only `--cli` mode satisfies the requirement); the spec arguably wants bare `upgrade` to behave like `upgrade --cli` outside a project. WP11 docs reinforce the narrow interpretation by directing users to `spec-kitty upgrade --cli`. Decision-log shows no plan-phase deferral. Treat as documented behavior, but flag for product owner review.

---

### RISK-7: `messages._safe` strips spec-kitty pre-release version tags

**Type**: ERROR-PATH (cosmetic)
**Severity**: LOW
**Location**: `src/specify_cli/compat/messages.py:30` — `_SAFE_VALUE_RE = re.compile(r"^[A-Za-z0-9.\-+_ /:]{1,256}$")`.
**Trigger**: latest version contains characters outside the regex (none expected from PyPI semver; pre-release tags like `2.0.14a1` pass; `2.0.14+build.1` passes; tilde marks etc. would fail).

**Analysis**: ANSI/escape rejection works; standard PyPI semver passes. The provider already validates against `^[A-Za-z0-9.\-+]{1,64}$` before returning, so any version that reaches `_safe` is already conforming. Defense-in-depth, no real risk.

---

## 7. Silent Failure Candidates

| Location | Condition | Silent result | Spec impact |
|---|---|---|---|
| `compat/planner.py:535-575` `_pending_migrations_for` | registry not auto-discovered | `()` | FR-019 partially unmet (DRIFT-2 / RISK-1) |
| `compat/cache.py:166-217` `NagCache.read` | symlink, ownership mismatch, oversized, mode != 0o600 | `None` (silent refusal with debug log) | desired behavior per CHK006/CHK009/CHK023 |
| `compat/cache.py:244-296` `NagCache.write` | symlink, mkdir failure | silent return | desired behavior |
| `compat/_detect/install_method.py:62-204` | every detection branch wrapped `try/except: pass` | falls through to next branch | desired behavior per CHK032 |
| `compat/planner.py:611-697` `plan()` outer try/except | any inner exception | `BLOCK_PROJECT_CORRUPT` Plan with `metadata_error="planner_error"` | fail-CLOSED — desired |
| `cli/helpers.py:258-263` `_render_nag_if_needed` outer try/except | any planner failure during nag | silent skip (fail-OPEN for nag) | desired (NFR-002) |
| `cli/commands/upgrade.py:325-326` `_check_project_not_too_new` | any exception | `pass` (let runner handle) | acceptable — typer.Exit re-raised at line 323 |

The fail-closed wrapper on `plan()` was actively verified: a `KeyError` inside `_plan_impl` is caught and produces the correct minimal `BLOCK_PROJECT_CORRUPT` plan with exit_code=6.

---

## 8. Security Notes

| Finding | Location | Risk class | Status / Recommendation |
|---|---|---|---|
| TLS verification ON by default for PyPI fetch | `compat/provider.py:151` (`httpx.Client(...)` with httpx default `verify=True`) | TLS | Verified — httpx default never disabled. CHK011 met. |
| 1 MiB body cap before parsing | `compat/provider.py:155` | RESOURCE EXHAUSTION | CHK012 met. |
| `follow_redirects=False` | `compat/provider.py:151` | OPEN-REDIRECT / DNS-REBIND | CHK013/CHK014 met. |
| Version regex `^[A-Za-z0-9.\-+]{1,64}$` | `compat/provider.py:40, 174` | ANSI / SHELL-INJECTION via version | CHK015/CHK016 met. |
| User-Agent only, no other headers | `compat/provider.py:152` | PII LEAK | CHK018/CHK048/CHK049 met. |
| Nag-cache 0o600 file mode | `compat/cache.py:424` (`os.open(..., 0o600)`) | LOCAL FILE PERM | CHK006 met (POSIX). |
| Nag-cache parent dir 0o700 | `compat/cache.py:266` | LOCAL FILE PERM | CHK006 met. |
| Symlink resistance on read+write, file+parent | `compat/cache.py:179-194, 273-290` | TOCTOU / SYMLINK-ATTACK | CHK009/CHK010 met (defense-in-depth: lstat the parent and the file). |
| Foreign-uid refusal on POSIX | `compat/cache.py:201-207` | MULTI-TENANT | CHK023 met. |
| Mode-mismatch refusal on POSIX | `compat/cache.py:209-216` | LOCAL FILE PERM (CHK008) | met. |
| Project metadata YAML safe-load + 256 KB cap | `compat/planner.py:457-466`, `migration/schema_version.py:74-75` (`yaml.safe_load`) | YAML-BOMB / RCE | CHK019/CHK020 met. |
| schema_version integer-range validation `[0, 1000]` | `compat/planner.py:494-503` | INPUT VALIDATION | CHK021 met. |
| Output sanitization in human messages | `compat/messages.py:30, 34-51` (`_safe`) | OUTPUT-INJECTION | CHK028 met. |
| `UpgradeHint.command` regex validated at construction | `compat/upgrade_hint.py:29, 61-66` | SHELL-INJECTION | CHK028/CHK031 met. |
| `UNKNOWN`/`SOURCE`/`SYSTEM_PACKAGE` hints carry `command=None`, only `note` | `compat/upgrade_hint.py:92-107` | accidental shell-execution by user | CHK031 met. |
| `brew --prefix` subprocess: 1 s timeout, `check=False`, args list (no `shell=True`) | `compat/_detect/install_method.py:111-116` | SUBPROCESS / SHELL-INJECTION | CHK032 met. |
| `git status --porcelain -z` subprocess in upgrade.py | `cli/commands/upgrade.py:60-65` | SUBPROCESS | argv-list, no shell=True. Acceptable. |
| No `shell=True` anywhere new | grep `shell=True` over diff | SHELL-INJECTION | clean. |
| No new outbound hostnames beyond `pypi.org` | grep `httpx`/`requests` over diff | SAAS / TRACKER | NFR-008 met. |

**No blocking security findings.** All critical security checklist items (CHK006, CHK009, CHK010, CHK011, CHK012, CHK013, CHK014, CHK016, CHK018, CHK019, CHK020, CHK021, CHK023, CHK028, CHK031, CHK032, CHK037, CHK048, CHK049) are honored in code with verifying tests in `tests/specify_cli/compat/test_provider_pypi.py`, `test_cache.py`, `test_install_method.py`, `test_upgrade_hint.py`, `test_messages.py`.

---

## 9. Cross-WP integration verification

- `src/specify_cli/compat/__init__.py` was touched by WP01 (placeholder), WP06 (filled exports), and WP10 (added the `_register_mode_predicates()` import side-effect). Final file is internally consistent: each WP's export block is clearly delimited by comment headers; `__all__` lists every public symbol.
- Public API smoke test (executed during this review):
  ```
  python -c "from specify_cli.compat import (
      plan, Plan, Decision, Safety, Fr023Case, NagCache, PyPIProvider,
      NoNetworkProvider, FakeLatestVersionProvider, InstallMethod,
      UpgradeHint, classify, register_safety, ProjectStatus, CliStatus,
      Invocation
  ); print('all imports OK')"
  → all imports OK
  ```
- Decision enum values and exit codes confirmed against R-08:
  ```
  ALLOW=0, ALLOW_WITH_NAG=0, BLOCK_PROJECT_MIGRATION=4,
  BLOCK_CLI_UPGRADE=5, BLOCK_PROJECT_CORRUPT=6, BLOCK_INCOMPATIBLE_FLAGS=2
  ```
- `Fr023Case` enum values match the JSON contract enum exactly.
- Schema range constants: `MIN_SUPPORTED_SCHEMA = MAX_SUPPORTED_SCHEMA = 3` (per WP07 design — no-op activation).

---

## 10. Locked decisions / Constraints check

| Item | Verified | Evidence |
|---|---|---|
| A-001 cache is per-user XDG | YES | `compat/cache.py:351-371` uses `platformdirs.user_cache_dir` or XDG fallback |
| A-002 PyPI provider abstraction | YES | `compat/provider.py:84-100` Protocol, three implementations |
| A-003 single planner authority | YES | `compat/planner.py` is the only place `decide()` lives; `migration/gate.py:83` delegates |
| A-006 `--yes` is functional alias of `--force`; neither bypasses too-new schema | YES | `cli/commands/upgrade.py:389` `confirm = yes or force`; `_check_project_not_too_new` runs before runner regardless of `confirm`; planner returns BLOCK_CLI_UPGRADE for too-new even with both flags (verified by inline test) |
| A-007 CI/non-interactive predicate | PARTIAL | three slightly different predicates exist (RISK-4); semantically aligned but a maintenance liability |
| A-009 stable JSON tokens | YES | `Fr023Case` enum + JSON contract enum match |
| C-001 confined to spec-kitty repo | YES | no other repo touched in diff |
| C-002 no project registry | YES | grep clean |
| C-003 no upgrade-all | YES | grep clean |
| C-004 no forced self-update at startup | YES | nag is print-only; `_run_cli_mode` only prints the hint |
| C-006 existing upgrade flags preserved | YES | `--dry-run`, `--force`, `--target`, `--json`, `--verbose`, `--no-worktrees` all present in `cli/commands/upgrade.py:335-340` |
| C-008 single planner authority | YES | confirmed via shim AST test |
| C-009 no new mandatory runtime dependency | YES | `httpx`, `ruamel.yaml`, `typer`, `rich`, `packaging` all in pre-mission `pyproject.toml`. `platformdirs` use is guarded by `try: import platformdirs` with manual XDG fallback. |

**No locked-decision violations detected.**

---

## 11. Test pass-through evidence

```
PYTHONPATH=src pytest tests/specify_cli/compat/ tests/cli_gate/ \
  tests/architectural/test_compat_shims.py \
  tests/architectural/test_safety_registry_completeness.py \
  tests/specify_cli/migration/ \
  tests/specify_cli/cli/commands/test_upgrade_command.py -q
→ 613 passed in 73.82s

PYTHONPATH=src pytest tests/specify_cli/upgrade/ tests/cross_cutting/versioning/ -q
→ 75 passed in 9.43s
```

Total: 688 tests across mission-owned and pre-existing suites — all green.

---

## 12. Final Verdict

**PASS WITH NOTES**

### Verdict rationale

All 25 functional requirements are implemented with adequate test coverage; all 9 NFRs except NFR-001 (no benchmark) are demonstrably met; all 9 constraints are honored; no security checklist item from `checklists/security.md` is violated. The mission's central architectural promise — "single compatibility planner authority" — is structurally enforced via the AST-level architectural shim test.

The findings flagged are not release-blocking:

- **DRIFT-1** (`PROJECT_NOT_INITIALIZED` defined but unemitted) is contract drift on a code path that the gate short-circuits before the planner sees it.
- **DRIFT-2 / RISK-1** (planner does not call `auto_discover_migrations`) is the most material finding: it causes the JSON contract's `pending_migrations` array to be empty in production gate-path invocations. The user-visible block message is unaffected, but `--json` consumers and FR-019 fidelity are degraded. Recommend a P1 follow-up patch.
- **DRIFT-3** (no `target_schema_version` / `files_modified` on registry items) is a known data-model gap mitigated by the planner's `getattr` fallback, but would benefit from a structural fix in `BaseMigration`.
- **RISK-3, RISK-4, RISK-5, RISK-6, RISK-7** are minor / boundary / cosmetic.

No CRITICAL or HIGH severity finding is open. The mission can be tagged for release; the follow-up issues are for a subsequent point release.

### Open items (non-blocking)

1. `compat/planner.py: _pending_migrations_for`: invoke `auto_discover_migrations()` before iterating (DRIFT-2 / RISK-1) — **MEDIUM**.
2. `compat/planner.py: decide()`: emit `Fr023Case.PROJECT_NOT_INITIALIZED` for `(NO_PROJECT|UNINITIALIZED, UNSAFE)` per data-model.md §1.9 (DRIFT-1) — **LOW**.
3. `upgrade/base.py: BaseMigration`: add optional `target_schema_version: int | None = None` and `files_modified: tuple[Path,...] | None = None`; document the inferred-from-semver semantics if not adopting per-migration declarations (DRIFT-3) — **LOW**.
4. Centralize the CI/non-interactive predicate as `compat.is_ci_env()` and route the three call sites through it (RISK-4) — **LOW**.
5. Add a `pytest-benchmark` micro-benchmark for the warm-cache nag path to enforce NFR-001's <100 ms threshold automatically — **LOW**.
6. Resolve the FR-14 ambiguity in product space: should bare `spec-kitty upgrade` outside a project behave as `--cli`? (RISK-6) — **LOW**.
