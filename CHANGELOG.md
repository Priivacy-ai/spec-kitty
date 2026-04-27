# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to the Spec Kitty CLI and templates are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Fixed

### Removed

## [3.2.0a5] — 2026-04-27

### Fixed

- Fix `spec-kitty upgrade` silently leaving projects in PROJECT_MIGRATION_NEEDED state by stamping `schema_version` after metadata save (#705, WP01).
- `spec-kitty init` in a non-git directory now prints an actionable "run `git init`" message (#636, WP05).
- Suppress misleading "shutdown / final-sync" red error lines after a successful `spec-kitty agent mission create --json` payload (#735, WP06).
- Deduplicate "Not authenticated, skipping sync" / "token refresh failed" diagnostics to at most once per CLI invocation (#717, WP06).
- Fix `read_events()` raising `KeyError('wp_id')` on `DecisionPointOpened` / `DecisionPointResolved` events that share `status.events.jsonl` with lane-transition events. Restores `finalize-tasks` / `materialize` / dashboard for any mission that uses the Decision Moment Protocol (#830, WP08).

### Changed

- Loosen `.python-version` from a hard `3.13` pin to `3.11` (the floor declared by `pyproject.toml`) and restore `mypy --strict` cleanliness on `mission_step_contracts/executor.py` (#805, WP03).

### Removed

- Retire the deprecated `/spec-kitty.checklist` command surface from every supported agent's rendered output. The canonical requirements checklist at `kitty-specs/<mission>/checklists/requirements.md` is unaffected (#815, supersedes #635, WP04).

### Internal

- Add regression tests confirming `--feature` aliases stay hidden from `--help` while remaining accepted (#790, WP07).
- Add regression test confirming `spec-kitty agent decision` command shape stays consistent across docs / help / skill snapshots (#774, WP07).

### Added

- **Frontend Freddy agent profile** — browser-side implementer specialising in HTML/CSS/JavaScript/TypeScript, component frameworks (React, Vue, Svelte), WCAG 2.1 accessibility, Core Web Vitals performance, and frontend testing (vitest, Playwright). Specialises from `implementer-ivan`. Self-review protocol enforces lint, type-check, unit/component tests, e2e smoke, axe accessibility gate, and bundle budget. Avoidance boundary explicitly names Node Norris's server-side domain.
- **Node Norris agent profile** — server-side Node.js implementer specialising in HTTP APIs (Express/Fastify/NestJS), async/Promise discipline, streaming, npm security (`npm audit`), and integration testing (supertest). Specialises from `implementer-ivan`. Avoidance boundary explicitly names Frontend Freddy's browser-rendering domain. The two profiles are mutually exclusive by design.
- **BDD paradigm** (`behaviour-driven-development`) — encodes BDD as a three-phase collaboration practice: Discovery (Three Amigos conversations), Formulation (Given/When/Then specifications), and Automation (executable living documentation). References `DIRECTIVE_034` and `DIRECTIVE_037`.
- **BDD Scenario Lifecycle procedure** (`bdd-scenario-lifecycle`) — covers the Formulation → Automation → Maintenance phases that follow an Example Mapping Workshop. Toolchain-agnostic (Cucumber-JVM, Cucumber-JS, Behave, SpecFlow). Encodes four anti-patterns: imperative Gherkin, rubber-stamp scenarios, shared mutable state, and orphaned step definitions.
- **New tactics:**
  - `reference-architectural-patterns` — structured selection of named reference patterns (Layered, Hexagonal, Event-Driven, CQRS, Microservices, Modular Monolith) scored against coupling, scalability, and operational complexity constraints.
  - `development-bdd` — architecture-level BDD tactic for expressing observable behavioral contracts at system boundaries before implementation; distinct from the existing `behavior-driven-development` technique tactic.
  - `bug-fixing-checklist` — language-agnostic test-first defect resolution: write a reproduction test before touching production code.
  - `test-readability-clarity-check` — dual-perspective reconstruction check: read only tests, reconstruct system understanding, compare against spec to surface documentation gaps.
  - `code-documentation-analysis` — brownfield boundary discovery by extracting and clustering domain terminology from code and documentation artifacts. Contributes foundational analysis tactics toward the brownfield investigation skill described in [#666](https://github.com/Priivacy-ai/spec-kitty/issues/666).
  - `terminology-extraction-mapping` — systematic extraction and relationship mapping of domain terms across multiple sources to produce a maintainable glossary. Complementary artifact to the bounded-context linguistic discovery approach targeted by [#666](https://github.com/Priivacy-ai/spec-kitty/issues/666).
- **Tactic directory normalization** — shipped tactics reorganised into four category subdirectories: `testing/` (15 tactics), `analysis/` (14), `communication/` (7), `architecture/` (14). Cross-cutting tactics remain in the `shipped/` root. The existing `rglob` loader requires no changes.
- **`tasks-finalize` command skill** — added to `CANONICAL_COMMANDS` in the agent skills pipeline and deployed to `.agents/skills/spec-kitty.tasks-finalize/`. Closes the gap where this command was missing from Codex/Vibe skill packages.

### Changed

- **Profile enrichment** — four existing profiles updated with additive tactic and paradigm references:
  - `implementer-ivan`: `bug-fixing-checklist` tactic reference (propagates to all specialist profiles via `resolve_profile()` union merge).
  - `reviewer-renata`: `test-readability-clarity-check` and `bdd-scenario-lifecycle` tactic references; `behaviour-driven-development` paradigm in context sources.
  - `architect-alphonso`: `development-bdd` tactic reference; BDD paradigm, example-mapping-workshop, and bdd-scenario-lifecycle in additional context sources.
  - `java-jenny`: `behavior-driven-development` and `bdd-scenario-lifecycle` tactic references; `bdd-scenarios` self-review step (Cucumber-JVM + Serenity BDD gate).
- **`behavior-driven-development` tactic enriched** — extended `notes` with a toolchain landscape section (Cucumber family, Playwright, Selenium, Serenity BDD, custom DSLs; source: `patterns.sddevelopment.be/primers/toolchain-and-automation/bdd`); three new `failure_modes` (rubber-stamp scenarios, shared mutable state between scenarios, orphaned step definitions); cross-references to the new BDD paradigm and procedure.
- **`tactic-references` union-merged in `resolve_profile()`** — `tactic-references` added to `_LIST_FIELDS` in `src/doctrine/agent_profiles/repository.py`. Specialist profiles now inherit base-profile tactic references via `_union_merge` at resolution time rather than overriding them.
- **Tactic compliance test extended** — `test_tactic_compliance.py` `ARTIFACT_DIRS` now includes `procedure` and `paradigm` types, enabling cross-type reference validation for tactics that reference procedures or paradigms.
- **Shared package boundary cutover** (mission `shared-package-boundary-cutover-01KQ22DS`) — `spec-kitty-runtime` is no longer a dependency of `spec-kitty-cli`. The CLI now owns its own runtime internally under `src/specify_cli/next/_internal_runtime/`; `spec-kitty next` works from a clean install of `spec-kitty-cli` alone. `spec-kitty-events` and `spec-kitty-tracker` are external PyPI dependencies consumed via their public import surfaces (`spec_kitty_events`, `spec_kitty_tracker`). The vendored events tree under `src/specify_cli/spec_kitty_events/` has been removed (~23 kLoC). Developers who relied on editable cross-package overrides should consult [`docs/development/local-overrides.md`](docs/development/local-overrides.md); operators upgrading from a pre-cutover release should consult [`docs/migration/shared-package-boundary-cutover.md`](docs/migration/shared-package-boundary-cutover.md). Decision rationale recorded in [ADR 2026-04-25-1](architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md).

### Removed

- **`constraints.txt`** — the file existed solely to paper over a transitive pin conflict with the retired `spec-kitty-runtime` package and is no longer needed.

### Fixed

- `spec-kitty agent config list/status` now checks global command roots for slash-command agents instead of reporting missing project-local command directories after `init`.
- `spec-kitty agent config add/sync --create-missing` no longer recreates retired project-local command directories for globally managed slash-command agents.
- `spec-kitty agent config remove/sync` now removes only the managed command surface for project-local agent directories, preserving unrelated files such as `.github/workflows/`.

### Added — Documentation mission composition rewrite (#502, #461, Phase 6 WP6.4)

- Documentation mission now runs on the StepContractExecutor composition substrate, mirroring research (#504) and software-dev (#503). The runtime resolves the new composed step contracts ahead of the legacy `mission.yaml` workflow via the existing `_resolve_runtime_template_in_root` precedence — no loader changes were required.
- New runtime sidecar templates: `src/specify_cli/missions/documentation/mission-runtime.yaml` and `src/doctrine/missions/documentation/mission-runtime.yaml`.
- Six shipped step contracts under `src/doctrine/mission_step_contracts/shipped/documentation-{discover,audit,design,generate,validate,publish}.step-contract.yaml`.
- Six action doctrine bundles under `src/doctrine/missions/documentation/actions/{discover,audit,design,generate,validate,publish}/` (governance guidelines + directive/tactic indices).
- DRG action nodes and edges for `action:documentation/{discover,audit,design,generate,validate,publish}` in `src/doctrine/graph.yaml`.
- Composition wiring in `src/specify_cli/next/runtime_bridge.py`: `_COMPOSED_ACTIONS_BY_MISSION["documentation"]` and a fail-closed guard branch in `_check_composed_action_guard()` raising a structured error for unknown documentation actions. `src/specify_cli/mission_step_contracts/executor.py` adds six `_ACTION_PROFILE_DEFAULTS` entries (`researcher-robbie` for discover/audit, `architect-alphonso` for design, `implementer-ivan` for generate, `reviewer-renata` for validate/publish).
- Real-runtime integration walk at `tests/integration/test_documentation_runtime_walk.py` proving SC-001 / SC-003 / SC-004 from a freshly initialized temp repo.

#### Backward compatibility

- The legacy `src/specify_cli/missions/documentation/mission.yaml` and `src/doctrine/missions/documentation/mission.yaml` files remain on disk for backward reference. Existing documentation-mission projects that authored against the legacy workflow continue to work; runtime template resolution prefers the new `mission-runtime.yaml` ahead of the legacy file via the existing precedence in `_resolve_runtime_template_in_root` (no loader changes in this PR).

### Added

- **Upgrade compatibility planner** — `spec-kitty upgrade` now separates CLI
  update guidance from current-project schema compatibility. New flags
  `--cli`, `--project`, `--yes`, and `--no-nag` support CLI-only guidance,
  project-only migrations, non-interactive confirmation, and explicit nag
  suppression. `spec-kitty upgrade --dry-run --json` emits the stable
  compatibility-plan contract for automation.
- **Host-surface parity matrix** at `docs/host-surface-parity.md` — authoritative record of how each of the 15 supported host surfaces teaches the advise/ask/do governance-injection contract. Closes the remaining `#496` host-surface breadth rollout.
- **Mode of work runtime derivation** — every `advise`, `ask`, `do` invocation now records its `mode_of_work` (`advisory`, `task_execution`, `mission_step`, `query`) on the `started` event. Derivation is from the CLI entry command.
- **Correlation links** — `spec-kitty profile-invocation complete` accepts `--artifact <path>` (repeatable) and `--commit <sha>` (singular); each appends an additive event to the invocation JSONL for single-file request→artifact/commit correlation.
- **SaaS read-model policy** at `src/specify_cli/invocation/projection_policy.py` — typed module mapping `(mode, event)` to projection rules. Documented in `docs/trail-model.md`.
- **Tier 2 SaaS projection decision** — decisively documented as deferred in `docs/trail-model.md`. Tier 2 evidence stays local-only in 3.2.x.
- **README Governance layer subsection** — entry point for operators discovering the advise/ask/do surface.
- **Decision Moment Ledger (V1)** — new `spec-kitty agent decision` subgroup with five
  subcommands: `open`, `resolve`, `defer`, `cancel`, `verify`. Mints ULID `decision_id`s
  at interview ask-time, writes paper trail under `kitty-specs/<mission>/decisions/`
  (`index.json` + `DM-<id>.md`), and appends `DecisionPointOpened(interview)` /
  `DecisionPointResolved(interview)` events to `status.events.jsonl`. Local-only;
  no SaaS sync required.
- **Charter integration** — `spec-kitty charter interview` now calls `decision open`
  before each question and the appropriate terminal command after each answer.
  `answers.yaml` behavior is unchanged.
- **Specify + Plan template updates** — `specify.md` and `plan.md` source templates
  gain a Decision Moment Protocol section instructing the LLM to call decision
  subcommands at ask/resolution time and write `<!-- decision_id: <id> -->` anchors
  for deferred decisions.
- **`decision verify` gate** — scans `spec.md` / `plan.md` for
  `[NEEDS CLARIFICATION: ...] <!-- decision_id: <id> -->` sentinels and
  cross-checks against the decisions index. Exits non-zero on drift
  (`DEFERRED_WITHOUT_MARKER`, `MARKER_WITHOUT_DECISION`, `STALE_MARKER`).
- **Widen Mode (#758)** — `spec-kitty agent decision widen` + `resolve --from-widen`
  lifecycle. Writes `widen-pending.jsonl`, emits `DecisionPointWidened` events,
  integrates with charter/specify/plan widen affordances. Surfaces decision
  write-back errors explicitly instead of silently suppressing them.

### Changed

- Project schema compatibility is now enforced by the centralized compat
  planner. Out-of-date CLI notices are passive and throttled; incompatible
  project schemas block unsafe commands with exit codes 4, 5, or 6 and exact
  remediation guidance.
- `spec-kitty profile-invocation complete --evidence` is now mode-gated: rejected on `advisory` / `query` invocations with `InvalidModeForEvidenceError`. Rejection occurs before any write; the invocation stays open.
- `_propagate_one` consults the new projection policy after the sync-gate and authentication lookup. Existing `task_execution` / `mission_step` projection behaviour is preserved exactly.
- Dashboard user-visible wording: the mission selector, current-mission header, overview heading, analysis heading, and empty-state prompt now read "Mission Run" / "mission" instead of "Feature". Backend identifiers (CSS classes, HTML IDs, cookie keys, API route segments, JSON field names) are unchanged.
- **`spec-kitty-events` bumped to `==4.0.0`** — vendored copy at
  `src/specify_cli/spec_kitty_events/` refreshed. Introduces
  `DecisionPointOpenedInterviewPayload`, `DecisionPointResolvedInterviewPayload`,
  `OriginSurface.PLANNING_INTERVIEW` (`origin_surface: planning_interview`),
  `OriginFlow` enum (values `specify`, `plan`), `DecisionPointWidened`, and
  `TerminalOutcome` enum.
- **`[tool.uv.sources]`** redirects `spec-kitty-events` to `../spec-kitty-events/`
  in editable mode for monorepo development. Dev-only; ignored by pip / PyPI.

### Deferred

- `spec-kitty explain` (issue #534) remains deferred to Phase 5 pending DRG glossary addressability (#499, #759).

### Out of scope (tracked separately)

- SaaS sync projection for widened decisions — tracked in spec-kitty-saas#110, #111.
- Tasks-phase interview support — future mission.

### Migration notes

**No operator action required for routine upgrade.** The trail model is additive:

- Pre-mission invocation records (no `mode_of_work`) continue to accept `--evidence` and project under legacy `task_execution` rules.
- Existing SaaS dashboards see no change for `task_execution` / `mission_step` traffic.
- New advisory events now appear in the SaaS timeline as minimal entries without body — this is a deliberate behaviour change documented in the SaaS Read-Model Policy table.

### Added (Phase 4 trail follow-on)

- `docs/trail-model.md`: Formal operator documentation for the Phase 4 trail contract,
  mode-of-work taxonomy, tier promotion rules, SaaS projection policy, intake positioning,
  and explain deferral (WP04).
- "Governance context injection" section in `.agents/skills/spec-kitty.advise/SKILL.md`
  for Codex/Vibe hosts, enabling Tier 1 trail recording without host-side SaaS auth (WP03).
- "Standalone invocations (outside missions)" section in
  `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` for Claude Code and gstack hosts,
  covering when to open an invocation record outside the mission workflow (WP04).
- End-to-end invocation integration tests in
  `tests/specify_cli/invocation/test_invocation_e2e.py` covering Tier 1 JSONL write,
  complete-event append, local-only list read, and sync-gate suppression (WP05).

### Fixed

- `propagator.py` (`_propagate_one`): Invocation events are now suppressed when
  `effective_sync_enabled = False`, even when the user is authenticated. Previously,
  sync-disabled checkouts could still emit SaaS events if a WebSocket client was
  connected (WP01).
- `executor.complete_invocation` now calls `promote_to_evidence()` when the
  `--evidence` flag is supplied, enabling correct Tier 2 artifact promotion (WP03).

### Changed

- Issue #496: Priority-surface slice complete in 3.2.x (Claude Code via
  `spec-kitty-runtime-next` doctrine skill, Codex CLI via SKILL.md governance context
  injection). Remaining 9 surfaces tracked in #496 for a follow-on patch or Phase 5.
- Issue #534: `spec-kitty explain` explicitly deferred to Phase 5 (requires DRG
  glossary addressability, issue #499). A partial implementation without glossary
  citations would be misleading.

## [3.2.0a4] - 2026-04-21

### Added

- **Mutation-aware test suites** — kill-the-survivor passes for `doctrine.resolver`, `doctrine.agent_profiles`, `doctrine.missions`, `doctrine.shared`, and `specify_cli.compat.registry`. Achieves 75–85 % kill rates per module; residuals documented as trampoline-equivalent, unloadable, or functionally equivalent in `docs/development/mutation-testing-findings.md`.
- `_OPTIONAL_KEYS` / `_ALL_KNOWN_KEYS` constants in `specify_cli.compat.registry._validate_entry` — unknown YAML keys now raise `RegistrySchemaError` before `ShimEntry(**entry)` can raise `TypeError`.
- `model_dump(mode="json")` on WP frontmatter serialization in `finalize_tasks` — prevents `Path` objects from reaching YAML serialization.

### Added

## [3.2.0a3] - 2026-04-21

### Fixed

- Release publish no longer hard-fails when the private `SPEC_KITTY_SAAS_READ_TOKEN` secret is absent. The pipeline still enforces runtime drift and exact wheel installability, and it runs the SaaS consumer-contract check whenever the private compatibility reference can actually be fetched.

## [3.2.0a2] - 2026-04-21

### Changed

- `spec-kitty-runtime` is now pinned to `0.4.4`, matching the corrected published runtime line rather than the broken `0.4.3` metadata.
- Release readiness and tag-time publish pipelines now verify shared-package drift, candidate-wheel installability with plain `pip`, and candidate compatibility against the SaaS consumer contract before publish.

### Removed

- Temporary `tool.uv.override-dependencies` masking for `spec-kitty-events`. Release validation now requires the published runtime metadata to resolve cleanly without local overrides.

## [3.2.0a1] - 2026-04-20

### Added

- **Mutation testing** — `mutmut` 3.5.0 added to `[project.optional-dependencies.test]` and configured in `[tool.mutmut]` as a **local-only** quality gate. Includes a curated doctrine set: `tactic:mutation-testing-workflow`, `styleguide:mutation-aware-test-design`, and language-specific toolguides for Python (`mutmut`) and TypeScript (`stryker`), all anchored to `DIRECTIVE_034` in the DRG graph. ADR `2026-04-20-1-mutation-testing-as-local-only-quality-gate.md` records the decision, the sandbox constraints, and the two-marker exclusion taxonomy.
- **`non_sandbox` / `flaky` pytest markers** — registered in `pytest.ini` and `pyproject.toml[tool.pytest.ini_options].markers`. Per-file `--ignore=` entries for sandbox-incompatible tests have been migrated to module-level `pytestmark` declarations; `[tool.mutmut].pytest_add_cli_args` now deselects via `-m "not non_sandbox and not flaky ..."`. Directory-level ignores remain only where tests fail during pytest *collection* (import errors that markers cannot intercept). 1 test is currently marked `flaky` as debt to be root-caused.
- **`docs/how-to/run-mutation-tests.md`** — Contributor how-to covering local `mutmut run` invocation, the kill-the-survivor workflow, equivalent-mutant suppression, and the `non_sandbox` / `flaky` marker taxonomy.
- Charter synthesizer now has a real harness-owned operator path: the new generated-artifact adapter reads agent-authored YAML from `.kittify/charter/generated/` and promotes validated doctrine into the live `.kittify/doctrine/` tree.
- `spec-kitty charter resynthesize --list-topics` now lists valid project-artifact selectors, DRG URNs, and interview-section selectors, including hyphenated aliases for section names.
- `spec-kitty charter status --provenance` now reports synthesis generation state, evidence summary, manifest health, and per-artifact provenance visibility alongside the older charter sync surface.
- ADR `2026-04-19-6-harness-owned-generated-artifact-charter-handoff.md` now records the host-side charter handoff contract: exact file layout, identity rules, and CLI sequence.
- **`architecture/2.x/06_migration_and_shim_rules.md`** — Authoritative compatibility shim lifecycle
  rulebook covering 4 rule families: schema/version gating, bundle/runtime migration authoring contract,
  shim lifecycle (with copy-paste template), and removal plans/registry contract. Required reading for
  all future extraction missions (#615).
- **`architecture/2.x/shim-registry.yaml`** — Machine-readable registry of all known compatibility
  shims. Starts empty (zero-shim baseline confirmed at mission-615 start). Future shims must be
  registered here before merging. Validated by `spec-kitty doctor shim-registry` (#615).
- **`spec-kitty doctor shim-registry`** — New CI enforcement subcommand that classifies each
  registered shim as `pending`, `overdue`, `grandfathered`, or `removed`. Exits 1 when any shim
  is overdue; exits 2 on configuration error. Supports `--json` for machine-readable CI output (#615).

### Changed

- `spec-kitty charter synthesize` and `spec-kitty charter resynthesize` now default to the generated-artifact adapter. `--adapter fixture` remains available only for deterministic offline regression runs.
- `spec-kitty charter synthesize --dry-run` is now a real stage-and-validate pass: it writes the staged artifact set, runs project DRG validation and neutrality gating, and only skips the final promote step.
- Shared contract-library pins now align with the current released pair consumed across the CLI and SaaS surfaces: `spec-kitty-events==3.2.0` and `spec-kitty-tracker==0.4.2`.
- Release pipeline now generates and attaches a CycloneDX SBOM (`sbom.cdx.json`) to every GitHub Release. The SBOM is an environment-snapshot of the fully resolved dependency tree at build time, making it straightforward for enterprise users to ingest the inventory into tools like Dependency-Track for continuous CVE monitoring without rescanning the package themselves.

### Fixed

- Directive provenance now records canonical URNs (`directive:PROJECT_<NNN>`) instead of slug-based placeholders, which restores correct directive filenames, provenance reload, and `directive:PROJECT_<NNN>` resynthesis.
- Bounded resynthesis now preserves evidence inputs end-to-end, so regenerated provenance entries keep the correct `evidence_bundle_hash` and `corpus_snapshot_id`.
- Generated-artifact synthesis errors now point to the exact expected file path and exact expected artifact id, which makes harness handoff mistakes easier to diagnose.
- Charter neutrality lint now scans mission `templates/` directories in addition to `command-templates/`, so banned terms in generic mission prompt files are caught by the default repo scan (#653 tripwire).
- Bump `requests` floor to `>=2.33.0` (CVE-2026-25645).
- Bump `pytest` floor to `>=9.0.3` (CVE-2025-71176).
- Pin `pygments>=2.20.0` explicitly to resolve CVE-2026-4539 in the transitive dependency pulled in via `rich`.
- `auth refresh` now treats `HTTP 401` responses with `invalid_grant` or `session_invalid` error codes identically to `HTTP 400`, and clears the locally stored session on server-side refresh rejection so `auth status` no longer reports stale credentials as authenticated.

### Removed

- **`specify_cli.charter` compatibility shim** — The re-export shim at `src/specify_cli/charter/` has been
  removed. External code importing `specify_cli.charter.*` must migrate to the canonical package:
  `from charter import <name>`. See
  [architecture/2.x/05_ownership_map.md](architecture/2.x/05_ownership_map.md) for the full
  charter slice entry and the reference exemplar pattern. Closes #611.

## [3.1.6] - 2026-04-20

### Fixed

- `spec-kitty agent action implement` now exposes and forwards
  `--acknowledge-not-bulk-edit` to the underlying workspace-allocation command,
  allowing non-bulk-edit missions to suppress false-positive bulk-edit inference
  warnings during workspace creation.

### Docs

- Spec Kitty's internal maintainer charter now records the ownership boundary
  for user-authored custom commands, custom skills, and project overrides, with
  an explicit proof trail showing that package-owned mutation flows must preserve
  files whose ownership is not proven by managed-path or manifest data.

## [3.1.5] - 2026-04-16

### Changed

- Keep `main` on the stable `3.x` release line. Release docs, install guidance,
  and README messaging now point new users at `3.1.x` on GitHub Releases and PyPI,
  while keeping `1.x-maintenance` explicitly maintenance-only.

### Fixed

- Make `spec-kitty upgrade` auto-commit safely through the charter rename migration.
  The `safe_commit` backstop now disables rename collapsing during its staged-path
  probe, and upgrade auto-commit expands changed directories into concrete paths
  before validating the staging area. This closes the false-positive abort reported
  in [#643](https://github.com/Priivacy-ai/spec-kitty/issues/643).
- Remove pytest/junit prompt bias from charter defaults, plan templates, and doctrine
  guidance. Packaged defaults now start from neutral selections, language inference
  flows through explicit repo signals, and language-scoped doctrine artifacts remain
  available when no active language filter is provided.

### Docs

- Align README and user-facing release docs around swim-lane terminology and the
  `3.1.x` stable release line.

## [3.1.4] - 2026-04-15

### Fixed

- Make `/spec-kitty.plan` stop instructing agents to update imaginary
  agent-specific context files or hunt for non-existent `agent context update`
  commands. Planning now stays focused on the actual mission artifacts it owns.
- Clarify `/spec-kitty.specify` mission-handle timing and non-blocking charter
  behavior so creation-time flows do not assume a mission already exists or stop
  on missing charter state.
- Tighten generated `/spec-kitty.implement`, `/spec-kitty.review`, and
  `/spec-kitty.merge` wrappers so they use the canonical `--mission <handle>`
  language and explicitly avoid redundant context rediscovery, including
  separate charter loads.

## [3.1.3] - 2026-04-15

### Fixed

- Make `/spec-kitty.charter` use an LLM-led interview by default, with better
  repo-scan guidance for greenfield/bootstrap repos, explicit doctrine-gap
  handling, natural-language questioning, depth scaling, and commit-after-generate
  behavior.
- Preserve explicit empty `selected_paradigms`, `selected_directives`, and
  `available_tools` during charter compilation instead of broadening them to
  packaged defaults.

### Docs

- Add ADR recording that explicit empty charter selections must remain empty and
  must not silently expand to shipped defaults.

## [3.1.2] - 2026-04-15

### Fixed — CI recovery & release readiness

- **`release-readiness` workflow now filters `windows_ci` tests** on the Linux runner. The job was running the full suite with no marker filter, failing 10 Windows-only tests (auth file-fallback, kernel paths, sync daemon paths, tracker credentials, migrate messaging, keyring packaging, lock contention, Windows home path). Those tests continue to run on the native `ci-windows.yml` job.
- **Kiro agent registration completed**: added `.kiro/` to `gitignore_manager.AGENT_DIRECTORIES`, regenerated 11 canonical command baselines under `tests/specify_cli/regression/_twelve_agent_baseline/kiro/`, and updated the four count constants that had drifted after PR #626 (13 slash-command agents, 15 `AGENT_DIRECTORIES` entries).
- **Auth test fixtures aligned with the hardened HTTP transport** introduced in `Harden SaaS auth and restore build sync emission`. Tests for `AuthorizationCodeFlow`, `TokenRefreshFlow`, `WebSocketTokenProvisioner`, and the browser-login/refresh-transport integration paths now patch `PublicHttpClient` in each flow module's own namespace (matching the production call graph) instead of raw `httpx.AsyncClient`. Network-error paths raise `NetworkError` from the client mock rather than `httpx.ConnectError` to match the new `except NetworkError` contract.
- **`ResolutionTier` unified across `doctrine.resolver` and `specify_cli.runtime.resolver`**. `specify_cli.runtime.resolver` is now a thin re-export shim, as its own docstring had claimed. Tests assert tier equivalence via `.name` to stay robust against `pytestarch`'s filesystem-walk loader, which can load the same source file under alternate module names during `pytest --import-mode=importlib`.
- **Post-`unified-charter-bundle-chokepoint` test fixture hardening**: three pre-existing tests (`test_local_support_declarations_end_to_end`, `test_template_prompt_bootstrap_context_first_load`, `test_all_pass_with_healthy_setup`) now `git init` their tmp directories to satisfy the new `resolve_canonical_repo_root` precondition that calls `git rev-parse --git-common-dir`.
- **Codex / Vibe Agent Skills migration test alignment**: five tests that pre-dated mission 083 were updated to assert the new `.agents/skills/spec-kitty.<cmd>/SKILL.md` layout rather than the retired `.codex/prompts/` layout. Invariants preserved (direct `spec-kitty agent action` CLI calls, per-agent argument handling, agent assets generation); only the probe path changed to match the post-083 architecture.
- **Contract handoff fixture** updated to include `BuildRegistered` and `BuildHeartbeat` event types added on the emitter side by the SaaS-auth hardening.
- **Miscellaneous tails**: redacted a dev-machine path literal in an architecture review doc (caught by `test_command_template_cleanliness`); fixed `test_rewrite_shims.py::test_result_counts` to use two slash-command agents since codex is no longer one; marked `test_home_unit.py::TestGetKittifyHomeWindows::test_windows_default_path` `windows_ci` since DRIFT-3 of the Windows Compatibility Hardening mission made `get_kittify_home()` delegate to `specify_cli.paths.get_runtime_root().base`, which the monkeypatch-based simulation no longer drives reliably on non-Windows runners.
- **Kiro regenerated baselines** for all 12 canonical commands, closing the `tests/specify_cli/regression/test_twelve_agent_parity.py` baseline-missing cluster introduced by PR #626.

### Added

- **Unified charter bundle manifest v1.0.0** at `src/charter/bundle.py` declaring the three `sync()`-produced derivatives (`governance.yaml`, `directives.yaml`, `metadata.yaml`) as the authoritative bundle contract. `references.yaml` and `context-state.json` are explicitly out of v1.0.0 scope; they are produced by other pipelines.
- **Canonical-root resolver** at `src/charter/resolution.py` (`resolve_canonical_repo_root()`). Readers running inside a git worktree now transparently observe the main-checkout charter bundle without per-worktree materialisation. Closes Priivacy-ai/spec-kitty#339.
- **`spec-kitty charter bundle validate [--json]`** CLI surface for operator and CI bundle-health checks.
- **Migration `m_3_2_3_unified_bundle`** advances 3.x projects to the unified bundle layout. On a populated project it validates the bundle against the v1.0.0 manifest, invokes `ensure_charter_bundle_fresh()` to regenerate any missing derivatives, and emits a structured JSON report (see `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/migration-report.schema.json`). Idempotent — the second apply against an already-upgraded project is a clean no-op. Refs Priivacy-ai/spec-kitty#464, #479.

### Changed

- **`SyncResult` extended with `canonical_root: Path`** — `files_written` remains a list of file names relative to `canonical_root / .kittify/charter/`. Existing readers were rewired in lockstep; no compatibility shim.
- **`ensure_charter_bundle_fresh()` is now the sole chokepoint** for readers of `governance.yaml`, `directives.yaml`, and `metadata.yaml`. Direct reads of those files are forbidden and are enforced by an AST-walk coverage test (`tests/charter/test_chokepoint_coverage.py`). Refs Priivacy-ai/spec-kitty#461, #464.

### Unchanged (explicitly)

- **`.kittify/memory/` and `.kittify/AGENTS.md` symlinks in worktrees** remain as-is — they provide project-memory and agent-instructions sharing, documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179`. They are NOT part of the charter bundle; the canonical-root resolver fixes the worktree charter-visibility story without touching `src/specify_cli/core/worktree.py` (C-011).
- **Files under `.kittify/charter/` that are not v1.0.0 manifest files** (`references.yaml`, `context-state.json`, `interview/answers.yaml`, `library/*.md`) are unchanged. The migration lists them under `bundle_validation.unexpected` for operator visibility but does not delete, move, or rewrite them (C-012).
- **Project `.gitignore` is not reconciled** by the migration. The v1.0.0 manifest's required entries already match the repository `.gitignore` verbatim; the migration performs no read or write against `.gitignore` (D-12).

### Refs

- EPIC: Priivacy-ai/spec-kitty#461 (Charter as Synthesis & Doctrine Reference Graph).
- Phase 2 tracking: Priivacy-ai/spec-kitty#464.
- Closes on merge: Priivacy-ai/spec-kitty#339, #451.

### Fixed

- **`mission merge` no longer silently loses content when the repository carries legacy sparse-checkout state** — the stash/merge/stash-pop cascade used by the merge driver previously recorded phantom deletions for paths filtered out by a sparse-checkout pattern, and the subsequent housekeeping commit silently reverted content the preceding merge had introduced. Merge and `agent action implement` now run a sparse-checkout preflight and fail closed unless the operator passes `--allow-sparse-checkout`, `safe_commit` now aborts commits whose staging area contains paths outside the intended scope, and `mission merge` performs a post-merge refresh and invariant check before leaving the integration branch. Closes Priivacy-ai/spec-kitty#588.
- **`move-task --to approved` and `--to planned` on a lane-worktree review no longer require `--force` when the only untracked content is `.spec-kitty/`** — the review-lock uncommitted-changes guard now treats the execution lane's own `.spec-kitty/` scratch directory as expected content rather than an unexplained untracked path, so operators stop being trained to pass `--force` reflexively. Closes Priivacy-ai/spec-kitty#589.
- **Retry guidance emitted by the uncommitted-changes guard now names the actual target lane** rather than hardcoded `for_review`, so operators see the transition they were attempting instead of a misleading default.

### Added

- **`spec-kitty doctor sparse-checkout --fix`** — detection and one-command migration for repositories upgraded from pre-3.0 spec-kitty that still carry `core.sparseCheckout=true` and a `.git/info/sparse-checkout` pattern file. The fix removes the git-config entry, clears the pattern file, and verifies post-fix state.
- **`--allow-sparse-checkout` flag on `mission merge` and `agent action implement`** — explicit escape hatch for users with intentional sparse configurations. Use of the flag emits a `WARNING`-level structured log record (`spec_kitty.override.sparse_checkout`) at the CLI layer. Durable cross-repo audit event support is tracked as Priivacy-ai/spec-kitty#617.
- **Commit-time backstop inside `safe_commit`** — fail-closed check that aborts commits whose staging area contains paths outside the intended scope, independent of the preflight. This is the universal defence that catches sparse-stash-pop phantom-deletion cascades regardless of which command initiated them.
- **Per-worktree `.spec-kitty/` exclude entry** — every lane worktree now receives a local git exclude entry for `.spec-kitty/` at worktree creation, so lane scratch content stays invisible to the working-tree guard even in worktrees initialised before the fix.
- **Session-scoped sparse-checkout warning** at review-lock and task-command entry points — surfaces detected legacy sparse-checkout state once per process before an operator wastes a commit cycle, without blocking.
- **ADR `2026-04-14-1-sparse-checkout-defense-in-depth`** — documents the four-layer hybrid defence (merge/implement preflight, `safe_commit` backstop, session warning, `doctor --fix`) and the alternatives considered.

### Recovery for users already affected

If a prior `mission merge` landed on your target branch with a silent content
reversion (symptoms: a follow-up `chore: record done transitions` commit that
deleted content merged in the preceding commit), restore the content from the
merge commit that introduced it:

```bash
# Identify the merge commit
git log --merges --oneline -- <affected-file>

# Restore content from that merge
git checkout <merge-sha> -- <affected-file> [...]

# Commit the restoration
git add <affected-file> [...]
git commit -m "fix: restore content reverted by phantom-deletion bug"
```

Then run the migration to prevent recurrence:

```bash
spec-kitty doctor sparse-checkout --fix
```

Root-cause diagnostic trail: [Priivacy-ai/spec-kitty#588 (comment)](https://github.com/Priivacy-ai/spec-kitty/issues/588#issuecomment-4242179946).

## [3.1.2a4] - 2026-04-14

### Added

- **Kiro CLI as first-class agent** — `spec-kitty init --ai kiro` registers the Kiro CLI (Amazon Q Developer CLI's rebrand) with its own `.kiro/prompts/` directory and `kiro-cli` binary check. Legacy `--ai q` (→ `.amazonq/prompts/`) remains supported for backwards compatibility. README and `docs/reference/supported-agents.md` now document the shell-quoting requirement for `$ARGUMENTS` pass-through (see kirodotdev/Kiro#4141). Closes #246.

### Fixed

- **`diff-coverage` CI job no longer fails with "no merge base"** — the base-branch fetch was passing `--depth=1` after `actions/checkout@v6` had already fetched full history, which truncated `origin/<base>` back to a single commit and broke `diff-cover`'s merge-base computation. Dropped `--depth=1`.
- **`test_mission_v1_guards_unit.py::test_registry_keys` now matches the guard registry** — synchronised the `EXPECTED_GUARDS` set with the `occurrence_map_complete` guard added in #616.

## [3.1.2a3] - 2026-04-12

### Fixed

- **Merge-time numbering lock and retry safety** — `mission_number` assignment now acquires a file lock before scanning existing prefixes, MergeState uses `mission_id` as its canonical key, and interrupted merges no longer risk duplicate or skipped numbers on retry. Closes #601.
- **CLI no longer hangs 15–20 min when offline queue is full and session expired** — the offline queue drain path now respects a bounded timeout instead of blocking indefinitely on expired-session retries. Closes #598, #602.
- **Sonar readiness and parser findings addressed** — actionable maintenance issues flagged by SonarCloud (code smells, complexity, minor bugs) are resolved. Closes #599, #600.

## [3.1.2a2] - 2026-04-11

### Added

- **Hosted readiness control surfaces** — the CLI now exposes the canonical SaaS rollout/readiness module, a six-state hosted readiness evaluator, and a background-daemon policy/intent model that keeps stealth rollout behavior explicit while making enabled-mode failures actionable.

### Changed

- **Tracker command classification is corrected for first-run flows** — `tracker discover` no longer requires an existing mission binding, `tracker providers` remains available as static output without hosted prerequisites, and hosted/manual-daemon checks are applied according to command intent rather than indiscriminately.
- **Tracker dependency advances to the hardened hosted-discovery release line** — the CLI now targets `spec-kitty-tracker==0.4.1`, aligning the prerelease with the published runtime validation and canonical discovery contract shipped in the tracker SDK.

### Fixed

- **Background-daemon policy no longer blocks local-provider sync flows** — local tracker providers continue to execute direct sync operations even when hosted SaaS daemon startup is set to manual.

## [3.1.2a1] - 2026-04-10

### Added

- **Browser-mediated CLI auth preview** — `spec-kitty auth login` now supports browser-based OAuth with Device Authorization Flow fallback, centralized token management, secure storage, and WebSocket token provisioning against the SaaS contract.

### Changed

- **Human CLI auth now flows through the new auth subsystem** — HTTP transport, sync runtime, and tracker SaaS callers now refresh through the shared token manager instead of the legacy password/JWT credential path.

### Fixed

- **Browser auth CI coverage gaps** — test dependencies and stale tracker refresh patch targets were corrected so the new auth stack passes the core and integration suites reliably in CI.

## [3.1.1] - 2026-04-09

### Added

- **Semantic status-event merge driver** — `kitty-specs/**/status.events.jsonl` now uses a Spec Kitty merge driver that unions append-only event logs by `event_id`, rejects conflicting payloads, and fails closed when merged WPs do not reach `done` in the canonical event log.
- **Forward-safe mission identity** — newly created missions now mint a ULID `mission_id` at creation time, persist it to `meta.json`, and emit it through mission-created event payloads.
- **Release hygiene guardrail** — release validation now enforces `pyproject.toml` and `.kittify/metadata.yaml` version sync before a cut can proceed.

### Changed

- **`spec-kitty init` now produces a minimal file scaffold** — init no longer initializes git, creates bootstrap commits, or seeds `.agents/skills/`. The generated next steps now point users at `spec-kitty next` plus `spec-kitty agent action implement/review` as the canonical workflow.
- **Planning-artifact WPs are first-class lane-owned items** — the canonical planning lane is now `lane-planning`, and it resolves to the main repository checkout instead of an ad hoc special-case path.
- **Top-level `implement` is de-emphasized** — onboarding and command docs now treat `spec-kitty implement` as internal infrastructure rather than the primary user-facing flow.

### Fixed

- **Merge conflict recovery for `status.events.jsonl`** — append-only status events are no longer silently dropped during merge conflict resolution, and fresh repositories now self-heal the local git merge-driver config when running merge flows. Closes #574.
- **Planning/query consistency after PR #555** — mixed planning/code review-context resolution no longer crashes when a dependency resolves to the repo-root workspace, and fresh-run query mode now returns `run_id: null` instead of leaking a deleted temporary run id.
- **Dependency parser trailing-prose bleed** — the final WP section is now bounded at non-WP `##` headings so trailing prose does not get misread as dependency declarations.
- **Concurrent auth refresh race** — stale 401 responses during token rotation no longer wipe valid shared credentials from active CLI sessions.

## [3.1.1a3] - 2026-04-07

### Added

- **Global slash command installation** — all 16 spec-kitty slash commands are now installed globally to `~/.<agent-dir>/` (e.g. `~/.claude/commands/`, `~/.gemini/commands/`, `~/.codex/prompts/`, etc.) at every CLI startup, for all 13 supported agents. No `spec-kitty init` or per-project `spec-kitty upgrade` is required for commands to be available. Commands update automatically when the CLI is upgraded.
- **Migration `3.1.2_globalize_commands`** — removes existing per-project `spec-kitty.*` command files from `.claude/commands/`, `.gemini/commands/`, and equivalent directories in all configured agents. Runs automatically on `spec-kitty upgrade`.
- **ADR `2026-04-07-1-global-slash-command-installation`** — documents the decision to install commands globally, the full 13-agent table with global roots, and the rationale.

### Changed

- `spec-kitty init` no longer writes per-project command files. Commands are managed exclusively by the global startup hook.

## [3.1.1a2] - 2026-04-07

### Fixed

- **`spec-kitty init` / any CLI command no longer dirties the git repo** — every CLI invocation that touched status was unconditionally rewriting `kitty-specs/*/status.json`, even when nothing had changed, leaving ~60 files modified in `git status`. Root cause: `materialize()` stamped a fresh `datetime.now(UTC)` into `materialized_at` on every call. Fixed in `reducer.py` (3.1.1a1): `materialized_at` is now derived deterministically from the last event's `at` timestamp (or `""` for features with no events), and a content-equality guard skips the write when the file is already up to date. Closes #524.

### Added

- **Migration `3.1.1_normalize_status_json`** — one-shot upgrade migration that normalises all existing `kitty-specs/*/status.json` files to the new deterministic format. Runs automatically on `spec-kitty upgrade` for any project where the committed files still carry old wall-clock timestamps or the legacy `feature_slug` field. After the migration the skip-write guard in `materialize()` keeps all status snapshots stable indefinitely.

### Changed

- **`StatusSnapshot` and `ProgressResult` serialisation no longer emits `feature_slug`** — `with_tracked_mission_slug_aliases` previously injected a redundant `feature_slug` alias into every serialised snapshot. Now only `mission_slug` is written. Reading still accepts both keys for backward compat with existing files.

## [3.1.1a1] - 2026-04-07

### Added

- **Typed `WPMetadata` Pydantic model** (`src/specify_cli/status/wp_metadata.py`) — immutable, validated work package metadata with `update()` builder API; replaces all raw `frontmatter.get()` dict access across consumer files. Closes #410.
- **`Lane` enum state machine** — valid lane transitions enforced at the type level; all runtime consumers migrated from string comparisons to `Lane` enum values.
- **Typed dashboard API contracts** (`src/specify_cli/dashboard/handlers/api.py`) — Pydantic response models replace untyped dicts.
- **RE2 shim** (`src/kernel/_safe_re.py`) — `types.ModuleType`-based shim backed by `google-re2`; exposes the full `re` API and mitigates Sonar DOS hotspot findings. `google-re2>=1.1` added as a core runtime dependency.
- **CI status-layer test stages** — new `fast-tests-status` and `integration-tests-status` jobs run the `tests/status/` and `tests/specify_cli/status/` suites in parallel with existing core/doctrine jobs; their coverage outputs feed the `diff-coverage` gate.
- **`WPMetadata.display_title` property** — safe fallback for missing or empty WP titles.

### Changed

- All `frontmatter.get()` calls outside `frontmatter.py` migrated to typed `WPMetadata` access. Migration scripts retain raw dict access annotated `# MIGRATION-ONLY`.
- `WPMetadata.title` is now optional; WP read errors propagate gracefully via `read_wp_frontmatter()`.
- `OwnershipManifest.from_frontmatter()` accepts `WPMetadata` directly.
- `diff-coverage` job wired to consume `coverage-kernel.xml`, `coverage-fast-status.xml`, and `coverage-integration-status.xml` in both enforced (critical-path 90%) and advisory (full-diff) steps.
- GitHub Actions upgraded to Node.js 24 compatible versions (`actions/checkout@v6`, `actions/setup-python@v6`, `actions/setup-node@v6`, `actions/upload-artifact@v7`, `actions/download-artifact@v8`) across all workflow files.

### Fixed

- `ValidationError` caught in phase-1 status mirror (`status/emit.py`) — prevents NoneType crashes on malformed WP files.
- Ruff and mypy violations cleaned up in all files touched by the migration.
- Sonar false-positive NOSONAR suppressions added in `arbiter.py` and `dashboard/handlers/api.py`.
- WP03 validation report (mission 068) decision corrected from `close_with_evidence` to `tighten_workflow` to reflect the CI logic additions; `test_tighten_workflow_passes_large_pr_sample` implemented to verify the advisory-only contract.

## [3.1.0] - 2026-04-07

### Added

- **Planning pipeline integrity (mission 069)** — four structural fixes eliminating fragilities discovered during mission 068:
  - **Dirty-git reads fix (WP01)** — `materialize()` now derives `materialized_at` from the last event timestamp (deterministic) and skips the write when content is byte-identical. `materialize_if_stale()` returns a read-only `reduce()` call. All read-only commands leave zero modified files in `git status`. Fixes #524.
  - **Structured WP manifest — `wps.yaml` (WP02, WP03, WP04)** — new `src/specify_cli/core/wps_manifest.py` with Pydantic model, YAML loader, and `generate_tasks_md_from_manifest()`. JSON Schema at `src/specify_cli/schemas/wps.schema.json`. When `wps.yaml` is present, `finalize-tasks` derives dependencies exclusively from the manifest; `tasks.md` is regenerated as a derived artifact. `/spec-kitty.tasks-outline` and `/spec-kitty.tasks-packages` templates updated to produce/consume `wps.yaml`. Migration `m_3_2_0_update_planning_templates` propagates changes to existing installations. Fixes #525.
  - **`spec-kitty next` query mode (WP05)** — bare `spec-kitty next` (no `--result`) enters query mode: returns current step with `[QUERY — no result provided, state not advanced]` prefix without advancing the state machine. Prevents ghost completions when agents call `next` while disoriented. Fixes #526.
  - **Slug validator digit-prefix support (WP06)** — `KEBAB_CASE_PATTERN` updated to accept `NNN-*` slugs following spec-kitty's own naming convention. Fixes #527.

## [3.1.0a8] - 2026-04-07

### Added

- **Post-merge reliability and release hardening (mission 068)** — 5 work packages closing the workflow-stabilization track:
  - **Stale-assertion analyzer (WP01)** — new `src/specify_cli/post_merge/` package: stdlib `ast`-based tool that detects test assertions likely invalidated by merged source changes. CLI: `spec-kitty agent tests stale-check --base <ref> --head <ref> [--json]`. Integrated into the merge runner. No new dependencies, no network calls.
  - **Merge strategy + safe-commit + linear-history hint (WP02)** — `MergeStrategy` enum (MERGE/SQUASH/REBASE) in new `src/specify_cli/merge/config.py` with `--strategy` CLI flag (resolves: flag → `.kittify/config.yaml` → squash default). `safe_commit()` called after `_mark_wp_merged_done` before worktree removal (FR-019). Linear-history rejection hint guides users past protected-branch push failures. Closes #456.
  - **Diff-coverage policy validation (WP03)** — validation report confirms the enforce/advisory split already satisfies the policy intent. CI step names tightened to `diff-coverage (critical-path, enforced)` and `diff-coverage (full-diff, advisory)`. Closes #455.
  - **Release-prep CLI (WP04)** — new `src/specify_cli/release/` package: `propose_version()`, `build_changelog_block()`, `ReleasePrepPayload`. CLI: `spec-kitty agent release prep --channel {alpha,beta,stable} [--json]`. Zero network calls. Closes #457.
  - **Recovery extension + mission close (WP05)** — `scan_recovery_state()` extended with `consult_status_events=True` to detect merged-and-deleted WPs via event log; new `RecoveryState.ready_to_start_from_target` field. `spec-kitty implement` gains `--base <ref>` flag for explicit worktree branching. Closes #415.

### Fixed

- **`implement --base` Typer pattern** — changed to Annotated pattern, fixing test isolation failures where direct Python calls received `OptionInfo` objects instead of `None`
- **`implement` console capsys isolation** — `_json_safe_output` wrapper now resets `console._file = None` in `finally` to prevent "I/O operation on closed file" when tests run in sequence with pytest capsys
- **Replay parity test** — corrected `reduced.mission_key == "replay-mission"` (was wrong field name and wrong value)

## [3.1.0a7] - 2026-04-06

### Added

- **Runtime recovery and audit safety (mission 067)** -- 6 work packages delivering resilience and audit infrastructure:
  - **Merge resume recovery (WP01)** -- `spec-kitty merge --resume` recovers from interrupted merges with persistent state tracking in `.kittify/merge-state.json`
  - **Implementation crash recovery (WP02)** -- `spec-kitty implement --recover` restores execution context after agent crashes, rebuilding worktree state and resuming from last known checkpoint
  - **Stale-claim doctor checks (WP03)** -- `spec-kitty doctor` detects orphaned claims, stale locks, and zombie worktrees with structured diagnostic output
  - **Audit-mode scope relaxation (WP04)** -- ownership validation supports `scope: codebase-wide` for audit/cutover WPs; new `validate_audit_coverage()` warns on uncovered audit targets
  - **Shim-to-canonical migration (WP05)** -- all `spec-kitty agent shim <action>` calls replaced with direct `spec-kitty agent action <action>` across 48 agent command files
  - **Finalize-tasks audit wiring (WP06)** -- `validate_audit_coverage()` integrated into finalize-tasks ownership validation pipeline as a soft warning check

### Fixed

- **Agent command files** -- regenerated all 48 agent command files to use canonical `spec-kitty agent action` instead of deprecated `spec-kitty agent shim`
- **Post-merge test regressions** -- fixed 4 stale test assertions after mission 067 merge (implement template content, merge resume behavior, --recover flag default)

## [3.1.0a6] - 2026-04-06

### Added

- **Review loop stabilization (mission 066)** — new `src/specify_cli/review/` module with 6 submodules:
  - `artifacts.py` — persisted review-cycle artifacts at `kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md` with YAML frontmatter. Replaces ephemeral `.git/spec-kitty/feedback/` storage. Backward-compatible `feedback://` pointer resolution retained (#432, #433).
  - `fix_prompt.py` — focused fix-mode prompt generation from review-cycle artifacts. Rejected WPs get ~40-line targeted prompts instead of replaying 400-500 line full WP prompts (#430).
  - `dirty_classifier.py` — dirty-state classification for review handoff. Partitions `git status --porcelain` output into blocking (WP-owned files) vs benign (status artifacts, other WP files, metadata). External reviewers no longer need `--force` for unrelated dirtiness (#439).
  - `baseline.py` — baseline test capture at implement time via `pytest --junitxml` + JUnit XML parsing. Review prompts include "Baseline Context" section distinguishing pre-existing failures from regressions. Configurable `review.test_command` for non-pytest projects (#444).
  - `lock.py` — concurrent review serialization via `.spec-kitty/review-lock.json`. Stale lock detection via PID check. Opt-in env-var isolation for projects that configure `review.concurrent_isolation` in config.yaml (#440).
  - `arbiter.py` — structured arbiter checklist with 5 standard rationale categories (pre-existing failure, wrong context, cross-scope, infra/environmental, custom). Override detection on forward `--force` from planned after rejection event. Decisions persisted in review-cycle artifact frontmatter (#441).
- **147 new tests** across the review module (avg 93% coverage, range 91-99%)
- **Implement-review skill update** — parallel sprint pattern, merge/conflict resolution guide, dead-code detection warning, post-merge validation steps
- **Tasks template handoff** — `/spec-kitty.tasks` now offers to invoke `/spec-kitty-implement-review` skill at completion for automated full-sprint execution

### Fixed

- **ReviewLock wired into live command path** — `ReviewLock.acquire()` called in `workflow.py review()` after workspace resolution; `ReviewLock.release()` called in `tasks.py move-task` on review completion
- **Removed dead `wp_prompt_path` parameter** from `generate_fix_prompt()` and all callers

## [3.1.0a5] - 2026-04-06

### Fixed

- **Dependency parsing in finalize-tasks** — new shared parser (`core/dependency_parser.py`) recognizes inline, colon-header, and bullet-list dependency formats. Both `agent mission finalize-tasks` and `agent tasks finalize-tasks` use the same parser. Non-empty disagreement between tasks.md and WP frontmatter triggers a diagnostic error instead of silently overwriting (#406).
- **validate-only is genuinely non-mutating** — all file writes gated behind `if not validate_only`. JSON output reports `would_modify`/`unchanged`/`preserved` without touching disk (#417).
- **Lane computation completeness** — every executable WP must appear in `lanes.json` or lane computation fails with a diagnostic error. Missing ownership manifests are a hard failure. Planning-artifact WPs surfaced in diagnostic summary. Zero-match globs and `src/**` fallback emit warnings (#422).
- **Parallelism collapse reporting** — new `CollapseReport` records every union-find merge with rule name and evidence. Rule 3 (surface heuristics) now gated on `_are_disjoint()` — WPs with provably disjoint owned files are not collapsed by keyword matches alone (#423).
- **Pipe-table mark-status support** — column-aware parser recognizes `[P]` in Parallel column (not corrupted), updates Status column or appends one. Checkbox format remains canonical for new generation (#438).
- **Agent command guidance** — all error messages, shim templates, and command-template examples now use `--mission` consistently. Five `require_explicit_feature()` callers fixed from `--feature` to `--mission`. Error messages include complete copy-pasteable example commands (#434).
- **Full --feature → --mission sweep** — 12 typer.Option declarations, 4 argparse declarations, 11 error messages, and 5 docstrings updated. `--mission` is the primary displayed flag name; `--feature` retained as hidden backward-compatibility alias (#448).

### Added

- `src/specify_cli/core/dependency_parser.py` — canonical shared dependency parser
- `CollapseEvent` and `CollapseReport` data models in `lanes/models.py`
- `LaneComputationError` exception for diagnostic lane failures
- `validate_glob_matches()` in ownership validation
- `planning_artifact_wps` field on `LanesManifest`
- Charter regression vigilance rules for `--mission` terminology canon

## [3.1.0a4] - 2026-04-06

### Fixed

- **Mission-era host surface cleanup** — removed remaining feature-era host command references from shipped templates, agent-facing prompts, and smoke-test scaffolding so new missions no longer regenerate `create-feature`, `feature_slug`, or `--feature` guidance on canonical paths.
- **Runtime mission metadata normalization** — mission resolution now prefers canonical `mission_type` metadata and rehydrates mission identity consistently in diagnostics, verification, and rebuild-state migrations.
- **Release-readiness regressions after host cutover** — updated cross-cutting, orchestrator, parity, body-sync, gitignore-isolation, and e2e smoke coverage to validate the mission-era CLI and contract instead of the removed feature-era host surface.

## [3.1.0a3] - 2026-04-05

### Fixed

- **Doctrine artifact discovery in subdirectories** — all 7 doctrine repositories now use `rglob()` instead of `glob()`, so artifacts in subdirectories of `shipped/` are no longer silently skipped (#396).
- **Dashboard `/api/features` empty response** — `StatusEvent.from_dict()` now accepts both `feature_slug` and `mission_slug` field names and normalizes the legacy `in_review` lane to `for_review`.
- **Stale `patch()` targets caught at lint time** — new `scripts/check_patch_targets.py` validates every `@patch()` target string resolves, added as an `[ENFORCED]` CI lint step (#394).
- **Architectural layer coverage guards** — meta-tests fail when a `src/` package has no layer assignment or a defined layer matches no module (#395).
- **Sonar reliability bugs** — resolved 7 findings: unreachable code (S1763), identical branches (S3923), premature async task GC (S7502), always-true condition (S2583), tautological assertion (S3981), CSS shorthand override (S4657), parameter shadowing (S1226).
- **Async task GC in event emitter** — `asyncio.ensure_future()` results held in `_pending_tasks` set with done-callback cleanup, preventing premature garbage collection.
- **`check-readiness` CI gate unblocked** — post-release version bump missed after tagging v3.1.0a2 (#408).

### Changed

- **CI test parallelization** — `fast-tests` and `integration-tests` split into `doctrine` + `core` phases running in parallel (#397).
- **`--mission-run` as canonical CLI flag** — added as alias for `--feature` across all CLI commands. `--feature` remains accepted as legacy alias.
- **Node.js 20 → 22** in CI workflows (current LTS).
- **Mutation testing CI job disabled** — too slow to run reliably.
- **Ruff max line length** increased from 120 to 164.
- **Defunct `tests/legacy` references removed**.

### Added

- **RTK search tooling toolguide** — new shipped doctrine artifact documenting RTK interception patterns and correct search tooling for worktree sessions.
- **`last_updated` field** on Toolguide model and schema.
- **Integration tests for nested artifact discovery** — 281-line test suite covering all 8 doctrine repository types.
- **`integration` pytest marker** registered in `pyproject.toml`.

## [3.1.0a2] - 2026-04-05

### Changed

- **Prerelease publishing is now first-class** — tag-mode release validation accepts matching prerelease tags such as `v3.1.0a0`, GitHub Releases are marked as prereleases automatically for those tags, and maintainer docs now document the end-to-end prerelease PyPI/GitHub publish path.
- **Rebased doctrine-stack work onto `main`'s execution architecture** — carry forward the doctrine, constitution, and template-repository work from PR #305 into PR #348 while preserving `main`'s context, ownership, event-log, merge-engine, and shim foundations instead of reviving deleted subsystems.
- **Kernel established as the shared dependency floor** — `src/kernel/` now owns shared path, atomic-write, and glossary-boundary primitives; doctrine no longer reaches back into `specify_cli`, and the package boundary is documented by ADRs and enforced by architectural tests.
- **Constitution now acts as the local routing layer for governance assets** — project-local mission path construction flows through `ProjectMissionPaths`, while doctrine-backed mission/template access is routed through `MissionTemplateRepository` and constitution-facing resolvers instead of scattered path assembly.
- **Mission terminology split clarified as the architectural answer to issue #241** — a direct `--feature` → `--mission` rename would have collided with the existing mission-type concept, so the branch now separates `mission type` (`--mission-type`) from `mission run` (`--mission-run`) and keeps legacy `--feature` compatibility where required during the deprecation window.
- **CI flows extended for the new package layout** — quality workflows now cover doctrine and kernel explicitly, including dedicated kernel coverage enforcement and updated readiness/release paths.
- **Fork-safe SonarCloud targeting via repository variables** — CI now resolves SonarCloud settings from `SONAR_ORGANIZATION`, `SONAR_PROJECT_KEY`, and optional `SONAR_HOST_URL`, with upstream-safe defaults and a fallback project-key convention of `<organization>_<repo-name>` when `SONAR_PROJECT_KEY` is unset.

### Fixed

- **Dashboard loading regressions on shared mission installs** — repaired the shared dashboard JavaScript syntax error, made feature scanning tolerate unreadable legacy event logs, hardened `/api/features` error handling, and marked the scanner regressions as part of the `fast` suite so CI/Sonar coverage reflects the new branches.
- **Narrow exception handlers in doctrine repositories** — Replace 21 bare `except Exception` handlers across `src/doctrine/` with specific exception tuples (`YAMLError`, `ValidationError`, `OSError`, `ModuleNotFoundError`, `TypeError`, `UnicodeDecodeError`) matching actual failure modes. Addresses PR #305 review finding M1.
- **Fix `spec-kitty --help` crash** — Add missing `Optional` import to `workflow.py` and `tasks.py`. `from __future__ import annotations` defers annotation evaluation; Typer's `eval()` of `Optional[str]` annotations raised `NameError` at app construction time.
- **Address PR #305 architectural review gaps in the rebased branch** — resolve the core review findings by removing doctrine→`specify_cli` dependency leakage, bringing doctrine into CI coverage, lifting shared glossary/path primitives into kernel, and documenting the resulting boundary in the architecture corpus.

### Documentation

- **Doctrine inclusion assessment** — `docs/development/doctrine-inclusion-assessment.md` evaluates the current state of the three Doctrine+Kitty merger pillars (agent profiles ~80%, mission type customization ~45%, ad-hoc experimentation ~25%) with gap analysis, dependency violation status, and phased recommendations.
- **Doctrine skills README** — `src/doctrine/skills/README.md` documents the skills-vs-mission-composition boundary, the iterative context loading pattern, and the skill inventory. Captures the architectural distinction from the PR #305 review.
- **Updated skill: spec-kitty-runtime-next** — new "Doctrine-Aware Step Execution" section teaches agents to load agent profiles at init, apply action-scoped constitution context at step boundaries, and pull specific tactics/directives on demand instead of dumping all doctrine upfront.
- **Updated skill: spec-kitty-constitution-doctrine** — new "Programmatic Doctrine Access", "Doctrine Artifact Kinds", and "Iterative Context Loading Pattern" sections document `DoctrineService` entry points, explain all 8 artifact kinds (directives, tactics, paradigms, styleguides, toolguides, procedures, agent profiles, step contracts) with access patterns, and teach the anti-pattern of upfront context dumps.
- **Updated skill: spec-kitty-mission-system** — new "Doctrine Composition Layer" section documents `MissionStepContract`, `Procedure`, and action index artifacts as the structured primitives backing mission behavior.
- **New skill: ad-hoc-profile-load** — teaches agents how to load a profile on demand for interactive sessions outside the mission loop: resolve by ID or task context, adopt identity/boundaries/governance scope, maintain role throughout the session, and persist to tool context.
- **Recorded the remaining follow-on work after the PR #305 -> PR #348 transition** — the compiler-backed mission-bundle follow-up remains relevant, the skills-vs-mission-composition boundary still needs to stay explicit, constitution-local routing should expand beyond mission-path centralization, issue #241 still has compatibility/documentation cleanup left on older `--feature`-based surfaces, and residual runtime/test debt remains outside this rebase-focused integration.

## [3.0.3] - 2026-04-01

### Added

- **Ticket-first mission origin binding** (feature 061): Service-layer workflow for starting a mission from an existing Jira or Linear ticket. Adds `search_origin_candidates()`, `bind_mission_origin()`, and `start_mission_from_ticket()` in `tracker/origin.py`. Persists durable `origin_ticket` provenance in `meta.json` with 7-field validation. Emits `MissionOriginBound` observational telemetry event. SaaS-first write ordering ensures local metadata never runs ahead of the authoritative control plane.
- **Reusable feature-creation API**: Extracted `create_feature_core()` from the CLI command into `core/feature_creation.py` — a stable, programmatic API returning `FeatureCreationResult` with domain exceptions instead of `typer.Exit()`.
- **SaaS tracker client extensions**: `search_issues()` and `bind_mission_origin()` transport methods on `SaaSTrackerClient` with full retry, auth refresh, and error handling.

## [3.0.2] - 2026-04-01

### Fixed

- **Missing prompt-driven slash commands**: `rewrite_agent_shims()` (3.0.0 migration step 6) deleted 9 prompt-driven template files (specify, plan, tasks, etc.) leaving only 7 CLI shims. Now regenerates all 16 command files per the hybrid architecture (feature 058). Added `m_3_0_2` migration to restore prompt files for already-affected projects.
- **Event log not created at feature birth**: `status.events.jsonl` was only bootstrapped during `finalize-tasks`, causing `CanonicalStatusNotFoundError` when the dashboard scanned features in the specify/plan phase. Now initialized when `create-feature` runs.
- **Dashboard scanner crash on pre-finalization features**: `_count_wps_by_lane()` and `_process_wp_file()` propagate `CanonicalStatusNotFoundError` (hard-fail contract); callers `scan_all_features()` and `scan_feature_kanban()` catch at feature level with actionable error messages.
- **Stale `/spec-kitty.clarify` references**: Removed 14 remaining references to the deleted clarify command across kitty-specs checklists, coverage tables, and `pyproject.toml`.
- **Missing `.gitignore` entries**: Added `.kittify/workspaces/` and `.kittify/merge-state.json` to match `state_contract.py` expectations.

## [3.0.1] - 2026-03-31

### Fixed

- **Canonical status hard cutover completed.** Work-package lane state is now consistently sourced from `status.events.jsonl` across active CLI commands, packaged task tooling, templates, docs, and standalone helpers. Frontmatter lane fallbacks and `lane=` body-log writes are removed from active 3.0 flows.
- **Canonical bootstrap and hard-fail behavior hardened.** `finalize-tasks` now seeds canonical `planned` state for generated WPs, while runtime commands fail explicitly when canonical status is missing instead of silently reconstructing it from abandoned frontmatter state.
- **Release automation updated for 3.x.** GitHub release validation, maintainer docs, and workflow tag handling now use semantic `vX.Y.Z` tags generically, so `v3.0.1` publishes correctly to GitHub Releases and PyPI.

## [3.0.0] - 2026-03-30

### Breaking Changes

- **Event log is sole authority for mutable WP state.** Frontmatter `lane`, `review_status`, `reviewed_by`, and `progress` fields are no longer written or read at runtime. Status is read from `status.events.jsonl` via the reducer.
- **`feature_detection.py` deleted.** All commands require explicit `--feature <slug>` in multi-feature repos. No branch scanning, no env var detection, no cwd walking.
- **Legacy worktree file filtering removed.** `planning_artifact` WPs work in-repo; `code_change` WPs use standard full worktrees.
- **Command templates restored as hybrid.** Planning commands (specify, plan, tasks, etc.) install as full prompts; execution commands (implement, review, merge, etc.) install as thin CLI-dispatch shims.

### Added

- **MissionContext** — opaque token-based bound identity for all workflow commands (`src/specify_cli/context/`)
- **WP Ownership Manifest** — `execution_mode`, `owned_files`, `authoritative_surface` per WP (`src/specify_cli/ownership/`)
- **Lane-weighted progress** — `planned=0.0`, `in_progress=0.3`, `for_review=0.6`, `done=1.0` (`src/specify_cli/status/progress.py`)
- **`spec-kitty materialize`** command for CI/debugging regeneration of derived views
- **Dedicated merge workspace** at `.kittify/runtime/merge/` with per-mission state and atomic lock
- **Merge conflict auto-resolution** for event logs (append-merge) and metadata (take-theirs)
- **Thin agent shims** for CLI-driven commands with `spec-kitty agent shim <command>` entrypoints
- **Schema version gate** (disabled until 3.0.0 migration ships to consumers)
- **One-shot migration framework** — `backfill_identity`, `backfill_ownership`, `rebuild_state`, `strip_frontmatter`
- **`--validate-only`** flag on `finalize-tasks`
- **`spec-kitty next`** hint in `tasks status` output
- **Integration Verification** section in WP prompt template
- **Doctor `command-files`** check — detects stale/missing/wrong-type agent command files
- **Version markers** in generated command files (`<!-- spec-kitty-command-version: X.Y.Z -->`)
- **Migration `m_2_1_4`** — unconditionally enforces correct hybrid command file state

### Removed

- `feature_detection.py` (668 lines) — replaced by MissionContext tokens
- `status/legacy_bridge.py`, `status/phase.py`, `status/reconcile.py`, `status/migrate.py`
- `merge/executor.py`, `merge/forecast.py`, `merge/status_resolver.py`
- `core/agent_context.py` — tech-stack parsing no longer needed
- ~56 command template files (replaced by 9 canonical prompts + 7 thin shims)
- Sparse checkout policy enforcement
- Frontmatter lane/review_status read/write throughout codebase
- Dual-write (event log + frontmatter) behavior

### Fixed

- "planning repository" → "project root checkout" terminology (migration included)
- Template path references removed from agent prompts (agents no longer search for `.kittify/missions/` files)
- Workflow `implement`/`review` now emit status events (was silently failing)
- Merge reconciliation marks ALL ancestor WPs as done (not just effective tips)
- `require_explicit_feature()` lists available features in error message
- YAML parse errors in frontmatter now logged as warnings (not silently swallowed)
- Merge engine uses `git reset --hard` on detached HEAD (not `git checkout` which fails when branch is checked out elsewhere)
- Migration backup covers `kitty-specs/` and `.gitignore` (not just `.kittify/`)
- `rebuild_state.py` uses max timestamp (not last file line) for terminal state
- Merge lock uses atomic `open('x')` (not TOCTOU `exists()` + `write_text()`)
- `merge --resume` errors when multiple paused merges exist (not silently picks first)

## [2.1.4] - 2026-03-27

### Added

**Enforce correct command file state**: Version markers and migration to guarantee all agent command files are always in the correct state.

- `<!-- spec-kitty-command-version: X.Y.Z -->` marker added as the first line of every generated command file (both full prompts and thin shims)
- Migration `m_2_1_4_enforce_command_file_state` unconditionally writes all 16 command files per configured agent; idempotent on subsequent runs when version markers match
- `spec-kitty doctor command-files` subcommand checks all agent command files for missing files, stale version markers, and wrong file type (full prompt vs thin shim)

## [2.1.3] - 2026-03-27

### 🐛 Fixed

**Preserve explicit WP args in workflow prompts**: Slash-command arguments passed to `/spec-kitty.implement` and `/spec-kitty.review` are now forwarded into the resolver-first flow instead of being silently dropped. Agents receiving explicit WP selectors (e.g., `WP03`, `--base WP01`) will correctly pass them to `spec-kitty agent context resolve` via `--wp-id` and `--base` flags.

- `implement.md` and `review.md` mission templates now include an `{ARGS}` placeholder with conditional forwarding instructions
- Public slash-command docs updated: `/spec-kitty.implement` documents `[--base WP_ID]` support; `/spec-kitty.review` is now WP-only (removed stale "or prompt path" syntax)
- Regression tests added across Markdown and TOML agent formats to ensure argument placeholders survive rendering

## [2.1.2] - 2026-03-23

### 🔧 Improved

**Skills audit and expansion**: All 6 distributed skills audited, command-verified, and expanded with full architecture documentation. Skills now document internal systems (glossary pipeline, constitution extraction, runtime DAG, git workflow boundary) so agents can operate effectively.

- setup-doctor: Fixed wrong CLI commands (`verify` → `verify-setup`, `status` → `agent tasks status`), added `--remove-orphaned` safety warning
- runtime-review: Added discovery step, `--feature` flags, empty-lane guidance
- glossary-context: Added 5-layer middleware pipeline, extraction methods, checkpoint/resume, step config
- constitution-doctrine: Added extraction rules, governance.yaml schema, interview profiles, answers.yaml schema
- runtime-next: Added decision algorithm, WP iteration logic, 6 guard primitives, agent loop pattern
- orchestrator-api: Added JSON output examples, error code catalog, idempotency behavior, preflight details

### ✨ Added

**2 new skills**: `spec-kitty-mission-system` (explains missions, 4 types, template resolution, guards) and `spec-kitty-git-workflow` (documents Python vs agent git operation boundary).

**Reusable skill update utility**: `src/specify_cli/upgrade/skill_update.py` for finding and patching skill files across all 13 agent skill roots.

**10 upgrade migrations** for consumer projects: 6 skill fixes, 1 release skill removal, 2 new skill installations, 1 glossary skill expansion.

**Documentation parity sprint (Feature 056)**: DocFX build now includes all 4 Divio categories (was only building 1x/ and 2x/). 5 new user guides distilled from skills, 4 existing docs expanded, 22 fact-check corrections across 20 files.

### 🐛 Fixed

**DocFX build gap**: 56 docs files (tutorials, how-to, reference, explanation) were in the repo but excluded from the docs.spec-kitty.ai build. Now included via updated `docfx.json`.

**8-lane state machine documentation**: All docs updated from outdated 4-lane model (planned/doing/for_review/done) to correct 8-lane model (planned/claimed/in_progress/for_review/approved/done/blocked/canceled) with 24 allowed transitions.

**CLI reference completeness**: Added 12 missing commands to cli-commands.md, 7 missing subcommands to agent-subcommands.md. Fixed `spec-kitty sync` (documented as flat command, actually a group with 6 subcommands).

### 🧹 Maintenance

- Removed `release` skill from distribution (spec-kitty development only, not for consumers)
- Removed obsolete `docs/how-to/upgrade-to-0-11-0.md`
- Fixed all cross-reference links in new docs (0 new DocFX build warnings)

## [2.1.1] - 2026-03-21

### 🐛 Fixed

- **Bundled doctrine payload in wheels**: the PyPI wheel now includes the full `doctrine/` package tree, including the canonical skill pack under `doctrine/skills/`, so `spec-kitty init` and `spec-kitty upgrade` can install managed skills for shipped builds.
- **2.1.0 repair migration**: added `2.1.1_repair_skill_pack` so projects that already upgraded on broken `2.1.0` wheels reinstall the canonical managed skill pack on `spec-kitty upgrade`.
- **Release verification guard**: the release workflow now fails if the built wheel omits doctrine files or bundled skills, and distribution tests now assert that a wheel-installed `spec-kitty init` produces the managed skill manifest and installed skill files.

## [2.1.0] - 2026-03-21

### ✅ Added

- **Agent Skills Pack (`#330`)**: added canonical bundled skills, registry/installer/verification flow, manifest support, and upgrade migration `m_2_0_11_install_skills`.
- **Structured requirement mapping (`#329`)**: added requirement-to-work-package mapping support with CLI integration for tracing delivery intent into execution planning.

### 🔧 Changed

- **Deterministic planning branch intent (`#328`)**: `specify` and `plan` commands now inject explicit target-branch metadata into templates to reduce ambiguity in downstream execution.
- **Primary release line promotion**: `2.x` becomes the stable `main` line, with GitHub Releases and PyPI publication starting at `2.1.0`.

### ⚠️ Deprecated

- **`1.x` overall**: the former `1.x` line is now deprecated and moves to `1.x-maintenance` for critical fixes only. No new `1.x` PyPI releases are planned.

### 🗑️ Removed

- **Public `/spec-kitty.clarify` slash command (`#322`)**: removed the legacy clarify command, template, and migration path in favor of the current planning/discovery flow.

## [2.0.11] - 2026-03-20

### 📄 Documentation

- **2.x release metadata refresh**: updated the README's current-release banner so the branch advertises the active GitHub-only 2.x release line instead of the initial `v2.0.0` placeholder.

## [2.0.10] - 2026-03-20

### ✅ Added

- **Project-level `auto_commit` setting (`#321`)**: repos can now configure automatic commit behavior directly in project config.
- **Sync queue resilience and diagnostics (`#320`)**: offline queue now supports FIFO eviction, coalescing, configurable caps, and sync doctor coverage for failure recovery.

### 🐛 Fixed

- **Merge target resolution (`#272`)**: merge target branch is now resolved from feature `meta.json`, preventing merges from targeting the wrong branch.
- **Acceptance and state persistence hardening (`#319`)**: state writes are now centralized around canonical metadata/state handling to reduce drift across acceptance, mission, and status flows.
- **Feature context fallback restored**: ambiguous agent/task resolution now falls back to the latest incomplete feature instead of stopping on a stale explicit-selection error.
- **Upgrade downgrade protection**: `spec-kitty upgrade` now refuses older targets instead of silently rewriting project metadata backwards.
- **Migration discovery fail-fast**: broken `m_*.py` modules now fail discovery immediately instead of being skipped with a stderr warning.
- **Upgrade metadata durability**: successful and failed migration records are now persisted immediately so retries can resume from an accurate state after mid-run failures.
- **Safe auto-commit stash isolation**: `safe_commit()` now restores only the stash entry it created, preventing unrelated user stashes from being popped during upgrade/status auto-commits.
- **Embedded task script compatibility**: copied `.kittify/scripts/tasks` helpers now fall back cleanly when the host `specify_cli` install is older than the copied templates.

### 🔧 Changed

- **State architecture cleanup phase 2 (`#319`)**: consolidated atomic-write and state-contract handling across runtime, acceptance, and feature metadata paths.
- **Test and quality isolation follow-ups**: retained the refactors that separated policy/test churn from release-critical behavior on the 2.x line.

## [2.0.9] - 2026-03-15

### ✅ Added

- **Mutation testing CI integration (feat #047)**: mutmut toolchain setup, CI integration, and targeted kill sessions for `status/` reducer and transitions.
- **Agentic mutation testing remediation workflow**: GitHub Agentic Workflow (gh-aw) replaces the legacy Claude workflow for mutation testing remediation.
- **SonarCloud integration**: added SonarCloud config; `develop` branch recognized as 2.x-equivalent in CI quality gates.
- **Architecture corpus restructure**: versioned architecture docs under `architecture/1.x/` and `architecture/2.x/`, 45 ADRs, glossary contexts across 10 bounded domains, Contextive integration, and stakeholder persona definitions.
- **`meta.json` schema example in specify template**: documents `"target_branch"` and `"vcs"` as required explicit fields.

### 🐛 Fixed

- **Post-rebase quality fixes**: resolved unmatched `)` syntax error, `gap_analysis_path` undefined name (F821), `timezone` → `UTC` reference, unused `type: ignore` comments, and `toml` import-untyped mypy errors.
- **Test isolation**: moved misplaced test package; fixed 3 test failures and Pydantic V1 deprecation warnings.
- **Sync offline queue**: redirect offline queue warning to stderr instead of stdout.
- **CI branch detection**: `develop` now recognized as a 2.x branch for branch-contract guards.

### 🔧 Changed

- **Ruff lint compliance**: full ruff clean pass across `src/` and `tests/`; added ruff lint config to `pyproject.toml`.
- **Documentation site updates**: 2.x docs site refresh with Contextive IDE integration guide.
- **Test suite restructuring**: migrated to vertical-slice layout; redesigned CI quality workflow; annotated suite with fast/slow/git_repo markers; deleted tests/legacy/ after extracting unique behaviours.

## [2.0.8] - 2026-03-11

### 🐛 Fixed

- **Dashboard approved lane**: WPs with `lane: "approved"` no longer silently fall back to the "planned" column. Added "Approved" as a 5th kanban column between For Review and Done, with `claimed`→planned and `in_progress`→doing lane normalization in the scanner.
- **Slim FEATURE_CONTEXT_UNRESOLVED payload**: reduced error payload size for LLM consumption to stay within agent context budgets.

## [2.0.7] - 2026-03-11

### ✅ Added

- **Mutation testing CI integration (feat #047)**: mutmut toolchain setup, CI integration, and targeted kill sessions for `status/` reducer and transitions (#275).
- **Agentic mutation testing remediation workflow**: GitHub Agentic Workflow (gh-aw) replaces the legacy Claude workflow for mutation testing remediation.
- **SonarCloud integration**: added SonarCloud config; `develop` branch recognized as 2.x-equivalent in CI quality gates.
- **Architecture corpus restructure**: versioned architecture docs under `architecture/1.x/` and `architecture/2.x/`, 45 ADRs, glossary contexts across 10 bounded domains, Contextive integration, and stakeholder persona definitions.
- **Google Antigravity as first-class agent (#266)**: added Google Antigravity to the supported agent roster with directory, templates, and migration coverage.
- **Commands own workflow context (#261)**: commands now carry their own workflow context rather than relying on ambient state.
- **Tracker snapshot publish payload (feat #048)**: resource routing in publish path (WP01) and batch API contract for tracker snapshot publish (WP02).

### 🐛 Fixed

- **Stale overrides from upgrade version-skew (#285)**: `classify_asset()` now compares project `.kittify/` files against immutable package-bundled defaults (`get_package_asset_root()`) instead of the mutable `~/.kittify/` directory. This prevents old managed templates from being misclassified as user customizations and permanently shadowing newer templates in `.kittify/overrides/` during upgrades.
- **New `SUPERSEDED` disposition**: managed files that differ from the current package default are now correctly classified as `SUPERSEDED` (removed) rather than `CUSTOMIZED` (moved to overrides). Only files with no package counterpart are treated as genuine user customizations.
- **Repair migration for already-affected users**: new `2.0.7_fix_stale_overrides` migration scans `.kittify/overrides/` for files byte-identical to current package defaults and removes them. Genuine user customizations are preserved.
- **Constitution: resolve_doctrine_root fallback for pip-installed users (#278)**: `resolve_doctrine_root()` no longer crashes when the `doctrine` package directory is missing from pip wheels; falls back to `specify_cli` package root.
- **Merge: worktree/branch cleanup when feature is already integrated (#271)**: `spec-kitty merge` now runs worktree removal and branch deletion when all WP branches are already merged, instead of exiting with "Nothing to merge" and leaving cleanup to the user.
- **Post-rebase quality fixes (#273)**: resolved unmatched `)` syntax error, `gap_analysis_path` undefined name (F821), `timezone` → `UTC` reference, unused `type: ignore` comments, and `toml` import-untyped mypy errors.
- **Test isolation**: moved misplaced test package; fixed 3 test failures and Pydantic V1 deprecation warnings.
- **Sync offline queue**: redirect offline queue warning to stderr instead of stdout.
- **CI branch detection**: `develop` now recognized as a 2.x branch for branch-contract guards.
- **Tracker publish path normalization (feat #048)**: normalize provider in publish path and document auth token resolution.

### 🔧 Changed

- **Ruff lint compliance**: full ruff clean pass across `src/` and `tests/`; added ruff lint config to `pyproject.toml`.
- **Documentation site updates**: 2.x docs site refresh with Contextive IDE integration guide.

## [2.0.6] - 2026-03-10

### 🐛 Fixed

- **Upgrade consistency sweep**: added a new `2.0.6_consistency_sweep` migration that backfills missing or blank feature `meta.json`, infers `target_branch` from feature docs or the repo primary branch, reconstructs missing `status.events.jsonl`, regenerates `status.json` and generated `tasks.md` status blocks, normalizes legacy WP frontmatter lane aliases/quoting, rewrites stale prompt paths, and archives orphan empty `status.json` snapshots before rebuilding canonical state.
- **Worktree upgrade coverage**: `spec-kitty upgrade` now upgrades worktrees that have `kitty-specs/` or legacy `.specify/` state even when `.kittify/` has not been created yet.
- **Detector false positives**: runtime-managed 2.x installs no longer trip legacy project-local mission migrations, and the constitution migration only flags the legacy `.kittify/memory/constitution.md` path.
- **Target-branch backfill correctness**: the `0.13.8_target_branch` migration now uses repo-aware branch inference instead of the obsolete hardcoded Feature 025 exception.

## [2.0.5] - 2026-03-10

### ✅ Added

- **Namespace-aware artifact body sync (Feature 047)**: Full offline-first pipeline for pushing spec artifact bodies (markdown content) to the SaaS backend, including `NamespaceRef` typed identifiers, `OfflineBodyUploadQueue` SQLite persistence, body upload preparation and filtering, HTTP transport with response classification, dossier pipeline orchestration with partial failure handling, background sync queue drain, and end-to-end diagnostics/logging.

### 🐛 Fixed

- **Init default directory (`#258`)**: `spec-kitty init` now defaults to the current directory when project name is omitted on the 2.x line.
- **Sync integration**: Completed namespace artifact body sync wiring for end-to-end operation.

### 📄 Documentation

- **Connector auth binding ADR**: Added architectural decision record for connector authentication binding and installation model gap analysis.
- **Command-owned action context ADR**: Defined command-owned action context pattern.

## [2.0.4] - 2026-03-06

### 🐛 Fixed

- **Upgrade JSON machine-parseability hardening (`#254`)**: `spec-kitty upgrade --json` now emits raw JSON output without Rich console wrapping.
- **Upgrade migration status consistency (`#256`)**: non-applicable migrations are reported as `skipped` instead of incorrectly marked as applied.

### 🔧 Changed

- **Contract hardening closeout (`#213`-`#218`)**: merged deterministic branch/runtime contracts, typed artifact-path payloads, merge/preflight JSON enrichment, and banner suppression in agent contexts.
- **Codex/Copilot slash-flow reliability (`#128`)**: integrated slash-command output stability improvements via deterministic JSON/banners/template alignment.
- **Worktree/preflight stability (`#226`)**: released preflight and command-contract hardening on the 2.x line for end-to-end spec→implement→review runs.

## [2.0.2] - 2026-02-27

### ✅ Added

- **Flag-gated tracker command group**: added `spec-kitty tracker ...` commands behind `SPEC_KITTY_ENABLE_SAAS_SYNC`, including provider listing, bind/unbind, mapping, local sync pull/push/run, and snapshot publish.
- **Tracker host-local persistence + credentials support**: added CLI-owned tracker SQLite cache/checkpoints and provider credential handling consistent with existing Spec Kitty host persistence patterns.

### 🔧 Changed

- **Dependency floor hardening for 2.x installs**: added explicit lower bounds for previously unbounded core CLI direct dependencies to reduce resolver drift in fresh environments.
- **Workflow review lane guard**: review start now requires a valid `for_review` lane state before progressing.

## [2.0.1] - 2026-02-26

### 🐛 Fixed

- **Main bias fix**: `resolve_primary_branch()` now checks the current branch before the hardcoded `[main, master, develop]` list. Repos on non-standard primary branches (e.g., `2.x`) no longer get blocked by `spec-kitty specify`.
- `create_feature()` records the current branch as `target_branch` in `meta.json` instead of guessing via heuristics. Added `--target-branch` CLI option for explicit override.
- `guards.py` uses `resolve_primary_branch()` instead of hardcoded `{"main", "master"}` set.
- `merge-feature --target` auto-detects from `meta.json` when not specified.
- Template references to "main" replaced with "target branch" throughout command templates.

### 🔧 Changed

- **Dashboard `--open` flag**: Browser auto-open is now disabled by default. Pass `--open` to open the dashboard URL in your browser. Prevents browser windows from spawning during tests or CI.
- Consolidated 3 ad-hoc branch-check functions into `_show_branch_context()` for consistent branch banners across all planning commands.

## [2.0.0] - 2026-02-22

### 🔧 Changed

- Start semantic versioning for `2.x` GitHub-only releases using `v2.<minor>.<patch>` tags.
- `2.x` release automation now publishes GitHub Releases only (no PyPI publish step).

### 🐛 Fixed

- `spec-kitty next` no longer short-circuits `--result failed|blocked` in the CLI bridge; both now flow through `spec-kitty-runtime` `next_step(...)`, preserving canonical runtime lifecycle behavior and run metadata.
- Runtime mission template selection for `next` now follows deterministic precedence tiers (`explicit`, `env`, `project override`, `project legacy`, `user global`, `project config`, `builtin`) when resolving `mission-runtime.yaml`.
- `--answer --json` integration coverage now exercises a real pending-decision success path (runtime `requires_inputs`) instead of fake decision IDs.
- Added replay-parity integration coverage in `spec-kitty` against `spec-kitty-events` canonical fixture stream (`mission-next-replay-full-lifecycle`).
- **WP prompt tracking reliability**: removed stale `kitty-specs/**/tasks/*.md` from tracked `.gitignore`, migrated existing projects away from that rule, and hardened workflow status commits to fail loudly if claim commits cannot be written.

## [2.0.0a5] - 2026-02-14

### 🐛 Fixed

**Backported orchestrator deadlock fixes from v0.15.3**:

- **Orchestrator deadlock**: Fixed false "No progress possible" detection when WP tasks raise exceptions or complete but leave WPs in intermediate states (IMPLEMENTATION/REVIEW). The orchestrator now properly marks failed WPs as FAILED and restarts orphaned WPs, preventing deadlock cascades. (Backport of #137 by @tannn)
- **Exception handling**: Task exceptions now properly mark WPs as FAILED with error details, allowing dependent WPs to recognize failure instead of blocking indefinitely
- **WP restart logic**: Added restart counter to prevent infinite restart loops if WP repeatedly fails to advance state. Restarts are now capped at `max_retries` (default: 3)
- **State recovery**: Improved detection of interrupted implementations (IMPLEMENTATION status without `implementation_completed` timestamp) to automatically reset and retry

### 🧹 Maintenance

- **Test coverage**: Added 8 new orchestrator tests covering exception handling, restart scenarios, deadlock detection, and state persistence
- **Test quality**: Reorganized test suite with proper markers (`@pytest.mark.orchestrator_exception_handling`, `@pytest.mark.orchestrator_deadlock_detection`) and class grouping following project conventions

## [2.0.0a4] - 2026-02-13

### 🐛 Fixed

**Backported v0.15.2 hotfix from main branch**:

- **Branch detection**: Replaced single `rev-parse --abbrev-ref HEAD` with dual-strategy
  approach (`git branch --show-current` primary, `rev-parse` fallback). Fixes unborn branch
  detection and detached HEAD handling. Updated all inline callers in tasks.py, workflow.py,
  and vcs/git.py.

- **Subprocess encoding safety**: Added `encoding="utf-8", errors="replace"` to all ~135
  `subprocess.run(text=True)` calls across 36 files. Prevents crashes on non-UTF-8 git output (Windows, locale mismatches).

- **Pre-commit hook safety**: Removed `set -e` from encoding check hook, expanded Python
  interpreter detection (loops through python3/python/py with smoke test), fixed exit code
  handling to distinguish encoding errors (exit 2) from execution failures.

- **Init fail-fast**: `spec-kitty init` now raises RuntimeError immediately after git init
  failure instead of falling through to "project ready" success message.

- **PowerShell templates**: Added PowerShell equivalent blocks to implement.md templates
  for software-dev, research, and documentation missions.

## [2.0.0a3] - 2026-02-11

### 🐛 Fixed

**Complete Bug #119 cherry-pick**:
- Fixed missing update to `scripts/tasks/acceptance_support.py` (root-level test helper)
- This file was missed in the original Bug #119 cherry-pick, causing test failures
- Now all acceptance_support.py copies correctly exclude 'done' lane from assignee requirement

## [2.0.0a2] - 2026-02-11

### 🐛 Fixed

**Cherry-picked 7 critical bug fixes from v0.15.0 (main branch)**:

- **Bug #95**: Enforce kebab-case validation for feature slugs
  - Rejects slugs with spaces, underscores, uppercase, or leading numbers
  - Prevents invalid directory structures and broken workflow commands
  - Added 8 comprehensive validation tests

- **Bug #120**: Use local git exclude for worktree ignores
  - Worktree-specific ignores now written to `.git/info/exclude` instead of `.gitignore`
  - Prevents `.gitignore` pollution when merging worktrees
  - VCS abstraction layer handles legacy worktree filtering consistently

- **Bug #117**: Improve dashboard lifecycle and error diagnostics
  - Dashboard process detection no longer reports false failures
  - Distinguishes between health check timeout (process running) vs actual failure
  - Provides specific error messages for missing metadata, port conflicts, permission errors

- **Bug #124**: Unify branch resolution, stop implicit master fallback
  - Respects user's current branch instead of auto-checkout
  - Shows notification when current branch differs from feature target
  - No more surprise checkouts during `spec-kitty implement` or `move-task`
  - Consistent branch resolution across all commands

- **Bug #119**: Relax strict assignee gate in acceptance validation
  - Assignee now optional for completed work packages in 'done' lane
  - Strict validation still enforces assignee for 'doing' and 'for_review'
  - Required fields (lane, agent, shell_pid) still mandatory

- **Bug #122**: Prevent staged files from leaking into status commits
  - New `safe_commit()` helper explicitly stages only intended files
  - Status commits no longer capture unrelated staged changes
  - Preserves user's staging area across workflow operations

- **Bug #123**: Call lane transition before status update (atomic state)
  - Lane transitions now happen BEFORE internal state updates
  - Prevents inconsistent state when operations fail mid-transition
  - Applies to orchestrator implementation and review phases

All fixes include comprehensive test coverage (54+ new tests) and maintain backward compatibility.

## [0.13.26] - 2026-02-04

### 🛠️ Refactored

**Consolidated workflow implement workspace creation**:
- `spec-kitty agent workflow implement` now delegates workspace creation to `spec-kitty implement` when needed
- Removes duplicated worktree setup in the agent command
- Prevents agents from creating worktrees from inside another worktree

### 🐛 Fixed

**Clearer recovery guidance for multi-parent merge failures**:
- When auto-merge fails, instructions now show concrete recovery steps
- Explicitly warns there is no `spec-kitty agent workflow merge` command
- Points agents to the correct `spec-kitty agent feature merge` command

## [0.13.25] - 2026-02-04

### 🐛 Fixed

**`spec-kitty upgrade` not bumping version when no migrations needed**:
- When `spec-kitty upgrade` found no applicable migrations, it returned early without updating the version in `.kittify/metadata.yaml`
- This left the project stuck at its old version (e.g., 0.13.21) even though the CLI was newer (0.13.24)
- The dashboard then blocked with a version mismatch error
- Fixed both `upgrade.py` (CLI command path) and `runner.py` (programmatic path) to stamp the version even when no migrations are needed

## [0.13.24] - 2026-02-04

### 🔧 Improved

**Review workflow shows git context for reviewers**:
- `spec-kitty agent workflow review` now displays the WP's branch name, base branch, and commit count
- Reviewers see exactly which commits belong to the WP vs inherited history
- Provides ready-to-use `git log <base>..HEAD` and `git diff <base>..HEAD` commands
- Base branch auto-detected from WP dependencies (tries dependency branches first, then main/2.x)
- Prevents reviewers from accidentally diffing against the wrong base (e.g., `main` instead of `2.x`)

## [0.13.20] - 2026-01-30

### 🐛 Fixed

**Merged Single-Parent Dependency Workflow Gap** (ADR-18):
- Fixed `spec-kitty implement` failing when single-parent dependency has been merged to target branch
- Issue: WP01 merged to 2.x → WP02 can't implement (looks for non-existent WP01 workspace branch)
- Root cause: Implement command didn't distinguish between in-progress vs merged dependencies
- Solution: Auto-detect when dependency lane is "done" and branch from target branch instead
- Behavior:
  - If `base_wp.lane == "done"`: Branch from target branch (e.g., 2.x) - merged work already there
  - If `base_wp.lane != "done"`: Branch from workspace branch (e.g., 025-feature-WP01) - work in progress
- Eliminates need for manual frontmatter editing (remove dependencies, update base_branch)
- Complements ADR-15 (multi-parent all-done suggestion) for single-parent case
- **Impact**: Critical fix for normal workspace-per-WP workflow where dependencies complete before dependents start
- **Technical Story**: Feature 025-cli-event-log-integration WP02/WP08 blocked on merged WP01

## [0.13.7] - 2026-01-27

### 🐛 Fixed

**Activity Log Parser Failing on Hyphenated Agent Names** ([#111](https://github.com/Priivacy-ai/spec-kitty/pull/111)):
- Fixed `activity_entries()` regex in `tasks_support.py` to handle hyphenated agent names
- Parser was using `[^–-]+?` pattern which treated hyphens as field separators
- Agent names like `cursor-agent`, `claude-reviewer`, `cursor-reviewer` now parse correctly
- Acceptance validation no longer fails with "Activity Log missing entry for lane=done" for hyphenated agents
- Changed pattern to `\S+(?:\s+\S+)*?` (matches non-whitespace), aligning with `task_helpers.py`
- Added comprehensive test suite with 11 test cases covering hyphenated names, backward compatibility, and edge cases
- **Contributors**: Rodrigo D. L. (bruj0)

**Workflow Completion Instructions Missing Git Commit Step** ([#104](https://github.com/Priivacy-ai/spec-kitty/pull/104)):
- Fixed agents not committing implementation files before marking tasks done
- Issue caused cascading failures where dependent work packages started from empty branches
  - WP02 worktree had HTML + CSS ✅
  - WP03 worktree had HTML only (missing WP02's CSS) ❌
  - WP04 worktree had HTML only (missing CSS and JS from WP02 and WP03) ❌
- Root cause: "WHEN YOU'RE DONE" instructions in `workflow implement` command didn't include git commit step
- Fix: Added explicit git commit instruction as step 1 in completion checklist
- Updated both in-prompt instructions (shown twice) and terminal output summary
- Added warning: "The move-task command will FAIL if you have uncommitted changes! Commit all implementation files BEFORE moving to for_review. Dependent work packages need your committed changes."
- **Impact**: Critical fix for multi-agent parallel development workflows using workspace-per-WP model (v0.11.0+)
- **Contributors**: Jerome Lacube

**Dashboard Command Template Generating Python Code Instead of Running CLI** ([#94](https://github.com/Priivacy-ai/spec-kitty/issues/94), [#99](https://github.com/Priivacy-ai/spec-kitty/pull/99)):
- Fixed `/spec-kitty.dashboard` command template to use `spec-kitty dashboard` CLI command
- Removed outdated Python code that manually checked dashboard status and opened browsers
- Dashboard now properly:
  - Starts automatically if not running
  - Opens in default browser
  - Handles worktree detection automatically
- Updated all three dashboard template files:
  - `.kittify/missions/software-dev/command-templates/dashboard.md`
  - `src/specify_cli/missions/software-dev/command-templates/dashboard.md`
  - `src/specify_cli/templates/command-templates/dashboard.md`
- Reduced template code from ~264 lines to ~47 lines
- **Contributors**: Jerome Lacube

## [0.13.6] - 2026-01-27

### 🐛 Fixed

**Critical JSON Mode Corruption Fix** (Release Blocker):
- Fixed JSON output corruption in `spec-kitty implement --json` mode (GitHub Issue #72 follow-up)
  - **Bug**: Warning messages from empty branch detection were written to stdout, corrupting JSON output
  - **Impact**: Automated workflows using `--json` flag would fail with JSON parse errors
  - **Fix**: Changed warning messages to use `file=sys.stderr` to separate warnings from JSON output
  - **File**: `src/specify_cli/core/multi_parent_merge.py:142-144`
  - **Tests**: Updated 5 tests in `test_multi_parent_merge_empty_branches.py` to check stderr instead of stdout

**Missing Migration Fix** (Existing Users Affected):
- Fixed missing migration for commit workflow section (GitHub Issue #72 follow-up)
  - **Bug**: New projects got commit workflow section in implement.md, but existing projects didn't after upgrade
  - **Impact**: Existing users remained vulnerable to agents forgetting to commit work
  - **Fix**: Created migration `m_0_13_5_add_commit_workflow_to_templates.py` to update all agent templates
  - **Coverage**: Updates both software-dev and documentation mission templates for all 12 agents
  - **Migration**: Automatically runs on `spec-kitty upgrade` for projects missing commit workflow

**Subprocess Error Handling** (Defensive Programming):
- Added timeout and error handling to multi-parent merge git commands
  - **Bug**: Git commands in empty branch detection lacked timeout parameters and try/except blocks
  - **Impact**: Function could hang forever or crash on git errors (corrupted repo, permission issues)
  - **Fix**: Added 10-second timeouts and exception handling to all git subprocess calls
  - **File**: `src/specify_cli/core/multi_parent_merge.py:117-144`
  - **Errors handled**: TimeoutExpired (>10s git commands), general exceptions with warning

### Added
- Git commit validation for "done" status transitions - prevents completing WPs with uncommitted changes
- Empty branch detection in merge-base creation - warns when dependencies have no commits
- Git commit workflow section in documentation mission template (consistency with software-dev/research)
- Comprehensive troubleshooting guide for empty branch recovery in the legacy workspace-model documentation
- Migration to add commit workflow section to existing projects (`m_0_13_5_add_commit_workflow_to_templates.py`)

### Changed
- `move-task --to done` now validates git status (same checks as "for_review")
- Use `--force` flag to bypass validation (not recommended)
- Warning messages in multi-parent merge now output to stderr instead of stdout (preserves JSON output integrity)

### Fixed (Non-Critical)
- WP agents can no longer mark tasks as "done" without committing implementation files
- Multi-parent merge-bases no longer silently accept empty dependency branches
- Documentation mission now instructs agents to commit work before review
- Stale WP detection now correctly detects default branch name (main/master/develop) instead of hardcoding "main"
  - **Bug**: Fresh worktrees incorrectly flagged as stale when repository used non-standard default branch
  - **Root Cause**: Code hardcoded "main" as default branch; when `git merge-base HEAD main` failed, it fell through to using parent branch's old commit timestamp
  - **Fix**: Added `get_default_branch()` helper to dynamically detect default branch via origin HEAD or local branch existence
  - **Impact**: Prevents false staleness warnings for fresh worktrees in repos using "master", "develop", or other default branches

## [0.13.5] - 2026-01-26

### 🐛 Fixed

**Fixed /spec-kitty.clarify Command Template**:
- Fixed broken placeholder in clarify template that prevented agents from running clarification workflow
  - **Bug**: Template contained `(Missing script command for sh)` placeholder instead of actual command
  - **Impact**: Agents couldn't get feature context, invented non-existent commands like `spec-kitty agent feature get-active --json`
  - **Fix**: Replaced manual detection logic with `spec-kitty agent feature check-prerequisites --json --paths-only`
  - **Consistency**: Now matches pattern used in specify.md, plan.md, and tasks.md templates
  - Migration `m_0_13_5_fix_clarify_template.py` automatically updates all 12 agent directories on upgrade
  - Source template: `src/specify_cli/missions/software-dev/command-templates/clarify.md`

**Testing**:
- Added comprehensive test suite with 34 tests covering all scenarios
  - Parametrized tests for all 12 agents (claude, copilot, gemini, cursor, qwen, opencode, windsurf, codex, kilocode, auggie, roo, q)
  - Tests for detection, application, agent config respect, idempotency, dry-run
  - Template content validation (ensures no broken placeholders, matches tasks.md pattern)
  - End-to-end integration test verifying migration actually runs and fixes templates

## [0.13.4] - 2026-01-26

### 🐛 Fixed

**Critical Dependency Validation Fix**:
- Fixed `spec-kitty agent workflow implement` not validating WP dependencies before creating workspaces
  - **Bug**: WP with single dependency could create workspace without `--base` flag
  - **Impact**: Workspace branched from main instead of dependency branch (silent correctness bug)
  - **Fix**: Added shared validation utility that errors when single dependency but no `--base` provided
  - **Example**: `WP06` depends on `WP04` → command now errors and suggests `--base WP04`
  - Created `src/specify_cli/core/implement_validation.py` with `validate_and_resolve_base()`
  - Agent commands now delegate to top-level commands (no more legacy script calls)

**Fixed Broken Agent Commands**:
- Fixed `spec-kitty agent feature accept` calling non-existent `scripts/tasks/tasks_cli.py`
  - Now delegates to top-level `accept()` command
- Fixed `spec-kitty agent feature merge` calling non-existent `scripts/tasks/tasks_cli.py`
  - Now delegates to top-level `merge()` command
  - Parameter mapping: `keep_branch` → `delete_branch` (inverted logic)

**Critical Merge Workflow Fix**:
- Fixed merge failing when main branch lacks upstream tracking (Issue reported post-0.13.2 release)
  - 0.13.2 only checked if remote EXISTS, but not if branch TRACKS it
  - Added `has_tracking_branch()` function to check upstream tracking
  - Merge now skips pull if: (1) no remote OR (2) no upstream tracking
  - Affects users with local-only repos or repos where main doesn't track origin/main

**Testing & Prevention**:
- Added 22 new tests for dependency validation and agent command wrappers
  - Unit tests: `test_implement_validation.py` (11 tests)
  - Integration tests: `test_agent_command_wrappers.py` (11 tests)
- Added `TestMigrationRegistryCompleteness` test (prevents 0.13.2-style release blocker)
  - Verifies all m_*.py migration files are imported in __init__.py
  - Prevents silent bugs where migrations exist but never run
- Added integration tests for merge with untracked branches
- Added unit tests for `has_tracking_branch()` function

**Documentation**:
- Added `src/specify_cli/cli/commands/agent/README.md` (wrapper pattern documentation)
  - Dependency validation best practices
  - Parameter mapping guidelines
  - Common pitfalls and examples
- Updated RELEASE_CHECKLIST.md with mandatory migration registry verification

## [0.13.2] - 2026-01-26

### 🐛 Fixed

**Critical Windows Compatibility Issues**:
- Fixed UTF-8 encoding errors causing Windows crashes (Issue #101)
  - Added `encoding='utf-8'` to all `write_text()` and `read_text()` calls
  - Affected files: feature.py, worktree.py, agent_context.py, doc_generators.py, gap_analysis.py
  - Completes PR #100 which missed several locations
- Fixed hardcoded `python3` breaking Windows installations (Issue #105)
  - Replaced with `sys.executable` in Python code (feature.py)
  - Added dynamic Python detection in git hooks (tries python3, falls back to python)
  - Windows users no longer need to create python3 hardlinks/aliases

**Workflow Improvements**:
- Added `--base` parameter to `spec-kitty agent workflow implement` (Issue #96)
  - Enables agents to create dependent WP worktrees via workflow command
  - Provides feature parity with top-level `spec-kitty implement` command
  - Example: `spec-kitty agent workflow implement WP02 --base WP01 --agent claude`

**Template and Documentation Fixes**:
- Fixed broken `/spec-kitty.clarify` skill (Issue #106)
  - Removed unresolved `{SCRIPT}` and `{ARGS}` placeholders
  - Replaced with auto-detection instructions for feature paths
- Fixed outdated template path references (Issue #102)
  - Updated 6 references from `.kittify/templates/` to `src/specify_cli/missions/`
  - Templates now reference correct bundled locations
- Fixed upgrade version detection for modern projects (Issue #108)
  - Added detection for versions 0.7.0-0.13.0
  - Prevents unnecessary migrations on modern projects
- Regenerated all 12 agent constitution templates (Issue #97)
  - All agents now correctly suggest `/spec-kitty.specify` as next step (not `/spec-kitty.plan`)

### 📚 Documentation

- Added GitHub CLI authentication troubleshooting to CLAUDE.md
  - Documents `unset GITHUB_TOKEN` technique for organization repos

**Issues Closed**: #96, #97, #101, #102, #105, #106, #108, #103 (not a bug), #107 (not a bug)

## [0.13.1] - 2026-01-25

### ✨ Added

**Adversarial Test Suite for 0.13.0 Release**:
- **Distribution tests**: Validate PyPI user experience without SPEC_KITTY_TEMPLATE_ROOT bypass (prevents 0.10.8-style packaging failures)
- **Path validation security tests**: Test directory traversal, symlink attacks, case-sensitivity bypasses, and path injection prevention
- **CSV schema attack tests**: Validate handling of formula injection, encoding errors, duplicate columns, and empty files
- **Git state detection tests**: Verify accuracy of uncommitted work, merge state, and branch divergence detection
- **Migration robustness tests**: Test UTF-8 encoding, idempotency, and partial/corrupted file handling
- **Multi-parent merge tests**: Validate dependency-order merging and conflict resolution
- **Context & config tests**: Test non-interactive modes, agent configuration, and workspace validation

**Test Infrastructure**:
- New `tests/adversarial/` directory with shared fixtures and attack vectors
- `@pytest.mark.distribution` and `@pytest.mark.slow` markers for CI optimization
- Session-scoped `wheel_install` fixture for efficient testing
- Platform-specific skip conditions for cross-platform compatibility

### 📚 Documentation

**Testing**:
- Comprehensive adversarial test documentation in feature 024 spec
- Attack vector catalog with prevention strategies
- CI integration guidance for slow/distribution tests

## [0.13.0] - 2026-01-25

### ✨ Added

**Deterministic CSV Schema Enforcement for Research Missions**:
- **Canonical schema documentation**: Research CSV schemas now documented in all 12 agent implement.md templates
- **Two schemas enforced**:
  - `evidence-log.csv`: `timestamp,source_type,citation,key_finding,confidence,notes`
  - `source-register.csv`: `source_id,citation,url,accessed_date,relevance,status`
- **Schema visibility**: Agents see schemas before editing (in "Research CSV Schemas" section with examples)
- **Detection migration**: `m_0_13_0_research_csv_schema_check.py` scans existing features for schema mismatches (informational only, no auto-fix)
- **Template propagation**: `m_0_13_0_update_research_implement_templates.py` updates all agent templates with schema documentation
- **Reusable validator**: `src/specify_cli/validators/csv_schema.py` provides `CSVSchemaValidation` dataclass for exact schema matching
- **Exported constants**: `EVIDENCE_REQUIRED_COLUMNS` and `SOURCE_REGISTER_REQUIRED_COLUMNS` now importable from `research.py`
- **ADR #8**: Documents architecture decision for documentation-based enforcement vs runtime enforcement/auto-migration

**Problem Solved**: Agents were modifying CSV schemas during implementation, creating different schemas in parallel WPs, causing merge conflicts and validation failures at review time.

**Solution Approach**: Document schemas where agents can see them (prevention) rather than runtime enforcement or auto-migration (data loss risk).

**Fully Non-Interactive Init Support**:
- Added `--non-interactive` / `--yes` and `SPEC_KITTY_NON_INTERACTIVE` to disable prompts
- Added `--agent-strategy`, `--preferred-implementer`, and `--preferred-reviewer` to expose all selection options via CLI
- Non-interactive mode now avoids arrow-key menus and requires `--force` for non-empty `--here` directories
- Updated documentation for automation and CI usage

### 🐛 Fixed

**Windows UTF-8 Encoding Crashes**:
- Fixed all `write_text()` calls to include `encoding='utf-8'` parameter
- Affects feature creation, worktree setup, gap analysis, doc generators, agent context, and test fixtures
- Windows users can now create features without charmap encoding errors
- Fixes #101, incorporates PR #100

**Constitution Template Workflow**:
- Fixed incorrect next-step suggestion after creating constitution
- Now correctly suggests `/spec-kitty.specify` instead of `/spec-kitty.plan`
- Propagated fix to all 12 agent directories via migration
- Fixes #97 (inspired by PR #98)

**Research Mission Detection**:
- Fixed `spec-kitty mission current` to show feature-level missions
- Now auto-detects feature from current directory (kitty-specs or worktree)
- Added `--feature` flag for explicit feature specification
- No longer always defaults to software-dev for research features
- Fixes #93

### 🎉 Closed

**Agent Configuration Feature**:
- Closed #51 as completed (already implemented in v0.12.0)
- Feature: `spec-kitty agent config add/remove/list`

### 📚 Documentation

**Release Management**:
- Added `RELEASE_CHECKLIST.md` - Comprehensive release preparation checklist with version-specific sections for research missions, agent management, and workspace-per-WP changes

### Migration Notes

**For users with existing research features**:
1. Run `spec-kitty upgrade` to trigger detection migration
2. See informational report with schema diffs and migration tips
3. Use LLM agent to help migrate data:
   - Read canonical schema in `.claude/commands/spec-kitty.implement.md`
   - Create new CSV with correct headers
   - Map old columns → new columns
   - Replace old file and commit to main

**For new research features (0.13.0+)**:
- Templates already have correct schemas
- Agents see schema documentation before editing
- Follow append-only pattern to avoid overwrites
- Validation passes at review

## [0.12.1] - 2026-01-24

### 🐛 Fixed

**kitty-specs/ in .gitignore Blocking Feature Creation**:
- Fixed issue where users with `kitty-specs/` in their `.gitignore` couldn't create features
- Error manifested as: "Issue Detected: The spec-kitty agent feature create-feature command failed to commit because .gitignore contains kitty-specs/"
- New migration `m_0_12_1_remove_kitty_specs_from_gitignore` automatically removes blocking entries
- Only removes patterns that block the entire `kitty-specs/` directory
- Preserves worktree-specific patterns like `kitty-specs/**/tasks/*.md` (used to prevent merge conflicts)

### Migration Notes

**For users experiencing this bug:**
1. Run `spec-kitty upgrade` to apply the fix automatically
2. Or manually remove `kitty-specs/` from your `.gitignore`

The migration will detect and remove entries like:
- `kitty-specs`
- `kitty-specs/`
- `/kitty-specs`
- `/kitty-specs/`

It will NOT remove specific subpath patterns that are intentionally used in worktrees.

## [0.12.0] - 2026-01-23

### ✨ Added

**Config-Driven Agent Management** (Feature 022):
- **Single source of truth**: `.kittify/config.yaml` now controls which agents are configured
- **New CLI commands**: `spec-kitty agent config list|add|remove|status|sync`
  - `list`: Show configured agents
  - `add <agents...>`: Add agents to configuration
  - `remove <agents...>`: Remove agents from configuration
  - `status`: Show configured vs orphaned agents
  - `sync`: Synchronize filesystem with configuration
- **Migrations respect config**: `get_agent_dirs_for_project()` helper only processes configured agents
- **Orphan detection**: Identifies agent directories not in config (from manual deletions)
- **ADR #6**: Documents architectural decision for config-driven approach

**Smarter Feature Merge with Pre-flight** (Feature 017):
- **Pre-flight validation**: Checks all WP worktrees for uncommitted changes, missing worktrees, and target branch divergence before any merge starts
- **Conflict forecasting**: `--dry-run` predicts which files will conflict and classifies them as auto-resolvable (status files) or manual
- **Smart merge order**: WPs merged in dependency order based on frontmatter `dependencies` field
- **Status file auto-resolution**: Conflicts in WP prompt files (`kitty-specs/*/tasks/*.md`) automatically resolved by taking advanced lane status
- **Merge state persistence**: Progress saved to `.kittify/merge-state.json` for recovery
- **Resume/abort flags**: `--resume` continues interrupted merges, `--abort` clears state and starts fresh
- **Auto-cleanup**: Worktrees and branches removed after successful merge (configurable with `--keep-worktree`, `--keep-branch`)

### 📚 Documentation

**Merge Preflight Documentation** (Feature 018):
- Added `docs/how-to/merge-feature.md` - Complete merge workflow guide with pre-flight, dry-run, strategies, and cleanup options
- Added `docs/how-to/troubleshoot-merge.md` - Comprehensive troubleshooting guide with error reference table
- Updated CLAUDE.md with Merge & Preflight Patterns section documenting MergeState dataclass and public API

**Agent Management Documentation Sprint** (Feature 023):
- Added `docs/how-to/manage-agents.md` - Complete guide to adding, removing, and managing AI agent integrations
- Added `docs/how-to/upgrade-to-0-12-0.md` - Migration guide for config-driven agent management
- Updated `docs/reference/cli-commands.md` with comprehensive `agent config` subcommand documentation
- Updated `docs/reference/agent-subcommands.md`, `docs/reference/configuration.md`, `docs/reference/supported-agents.md` with accurate cross-references
- Updated `docs/how-to/install-spec-kitty.md` with agent configuration guidance

### 🐛 Fixed

**Merge Resume Bug**:
- Fixed `merge_workspace_per_wp()` missing `resume_state` parameter causing `TypeError` when using `--resume`

**Agent Workflow Output Truncation** (GitHub Codex compatibility):
- Fixed workflow commands (`implement`, `review`) outputting 300+ lines which got truncated by agents like GitHub Codex
- Prompts now written to temp file with concise 15-line summary to stdout
- Added directive language (`▶▶▶ NEXT STEP: Read the full prompt file now:`) so agents automatically read the file
- Agents no longer miss work package requirements due to output truncation

**False Staleness for Newly-Created Worktrees**:
- Fixed stale detection flagging new worktrees as stale immediately
- Previously, `git log -1` returned parent branch's commit time (could be hours old)
- Now checks if branch has commits since diverging from main
- Worktrees with no new commits are NOT flagged as stale (agent just started)

## [0.11.1] - 2026-01-16

### 🐛 Fixed

**Merge Template Improvements**:
- Added explicit preflight validation code using `python3 -c` with `validate_worktree_location()`
- Added clear visual "⛔ Location Pre-flight Check (CRITICAL)" section to prevent agents running merge from wrong location
- Fixed contradictory instructions in software-dev mission merge template (was incorrectly saying "run from main")
- Fixed empty Python code block in research mission merge template that confused agents
- Added workspace-per-WP model (0.11.0+) documentation vs legacy pattern in worktree strategy section

**Documentation Accuracy** (Feature 014):
- Rewrote `multi-agent-orchestration.md` for the 0.11.0+ isolated-WP worktree model:
  - Planning happens in main repo (not worktrees)
  - Each WP gets its own worktree (not shared)
  - Removed references to non-existent scripts
  - Updated lane tracking to frontmatter (not directories)
  - Added parallelization patterns and status monitoring
- Fixed the legacy isolated-worktree guide merge command syntax (runs from worktree without feature argument)
- Fixed `documentation-mission.md` broken source links
- Fixed `reference/README.md` - replaced outdated "Planned Content" with actual content links
- Fixed `kanban-workflow.md` - clarified `/spec-kitty.accept` works on features, not individual WPs

### 📚 Added

**Comprehensive End-User Documentation** (Feature 014):
- Complete Divio 4-type documentation suite:
  - **Tutorials**: Getting Started, Your First Feature, Claude Code Integration, Claude Code Workflow, Multi-Agent Workflow, Missions Overview
  - **How-To Guides**: 14 task-oriented guides covering installation, specifications, planning, implementation, review, dependencies, parallel development, dashboard usage, and migration
  - **Reference**: CLI Commands, Slash Commands, Agent Subcommands, Configuration, Environment Variables, File Structure, Missions, Supported Agents
  - **Explanations**: Spec-Driven Development, Divio Documentation, legacy isolated worktree model, Git Worktrees, Mission System, Kanban Workflow, AI Agent Architecture, Documentation Mission, Multi-Agent Orchestration
- Cross-references between all documentation types
- DocFX-compatible structure with `toc.yml` navigation

## [0.11.0] - 2026-01-12

### 🚨 BREAKING CHANGES - Workspace Model Changed (Feature 010)

**Old (0.10.x)**: One worktree per feature
- `/spec-kitty.specify` created `.worktrees/###-feature/`
- All WPs worked in same worktree
- Sequential development (one agent at a time)

**New (0.11.0)**: One worktree per work package
- Planning commands (specify, plan, tasks) work in main repository (NO worktree created)
- `spec-kitty implement WP##` creates `.worktrees/###-feature-WP##/`
- Each WP has isolated worktree with dedicated branch
- Enables parallel multi-agent development

### ⚠️ Migration Required

**You MUST complete or delete all in-progress features before upgrading to 0.11.0.**

Check for legacy worktrees:
```bash
spec-kitty list-legacy-features
```

See [docs/upgrading-to-0-11-0.md](docs/upgrading-to-0-11-0.md) for complete migration guide.

### 🔒 Security (IMPORTANT) - Feature 011

- **Comprehensive adversarial review framework**
  - Expanded review template from 3 bullets (109 lines) to 12 scrutiny categories (505 lines)
  - **Security scrutiny now mandatory**: 10 detailed security subsections
  - **Mandatory verification**: 7 security grep commands must be run on EVERY review
  - **Automatic rejection** if any security check fails
  - **Impact**: All future features will have security-first reviews

### ✨ Added

**Legacy isolated-WP worktree features (010)**:
- **New command**: `spec-kitty implement WP## [--base WPXX]` - Create workspace for work package
  - `--base` flag branches from another WP's branch (for dependencies)
  - Automatically moves WP from `planned` → `doing` lane
- **New command**: `spec-kitty agent feature finalize-tasks` - Finalize WP generation
  - Parses dependencies from tasks.md
  - Generates `dependencies: []` field in WP frontmatter
  - Validates dependency graph (cycle detection, invalid references)
- **Dependency tracking**: WP frontmatter includes `dependencies: []` field
- **Dependency graph utilities**: `src/specify_cli/core/dependency_graph.py`
- **Review warnings**: Alert when dependent WPs need rebase

**Constitution Features (011)**:
- **Interactive constitution command** (Phase-based discovery)
  - 4-phase discovery workflow (Technical, Quality, Tribal Knowledge, Governance)
  - Two paths: Minimal (Phase 1 only) or Comprehensive (all phases)
  - Skip options for each phase
  - Truly optional - all commands work without constitution

### ♻️ Refactored - Feature 011

- **Template source relocation** (Safe dogfooding - Critical)
  - Moved ALL template sources from `.kittify/` to `src/specify_cli/`
  - Updated template manager to load from package resources
  - Removed `.kittify/*` force-includes from `pyproject.toml`
  - **Impact**: Developers can now safely dogfood without packaging risk

- **Mission-specific constitutions removed**
  - Single project-level constitution model (`.kittify/memory/constitution.md`)
  - Migration removes mission constitutions from user projects

### 🐛 Fixed - Feature 011

- **Windows dashboard ERR_EMPTY_RESPONSE** (#71)
  - Replaced POSIX-only signal handling with cross-platform psutil
  - Added `psutil>=5.9.0` dependency
  - Dashboard now works on Windows 10/11

- **Upgrade migration failures** (#70)
  - Fixed multiple migrations to handle missing files gracefully
  - All migrations now idempotent
  - Upgrade path from 0.6.4 → 0.10.12 completes without intervention

### 🐛 Fixed - Feature 012

- **`/spec-kitty.status` template instructed agents to run Python code**
  - AI agents cannot execute arbitrary Python - they use CLI tools
  - Updated template to use CLI command as primary method
  - Python API now documented as alternative for Jupyter/scripts

### 📖 Documentation - Feature 010

- **New docs**: legacy isolated-worktree workflow guide with examples
- **New docs**: `docs/upgrading-to-0-11-0.md` - Migration instructions

### 🎯 Why These Changes?

**Feature 010 (Workspace-per-WP)**:
- Enables parallel multi-agent development
- Better isolation per work package
- Explicit dependencies with validation
- Scalability for large features (10+ WPs)

**Feature 011 (Constitution & Packaging Safety)**:
- Safe dogfooding (no packaging contamination)
- Cross-platform dashboard support
- Optional, interactive constitution setup
- Smooth upgrade migrations

## [0.10.13] - 2026-01-12

### 🐛 Fixed

- **CRITICAL: Missing migration in PyPI v0.10.12 package**
  - Migration `m_0_10_12_constitution_cleanup.py` was missing from PyPI package uploaded on 2026-01-07
  - File existed in source repository but was not included in distributed wheel
  - Caused constitution cleanup to not run during upgrades from v0.10.11
  - v0.10.13 includes the missing migration file
  - Users who installed v0.10.12 should run `spec-kitty upgrade` again after upgrading to v0.10.13
  - **Root cause**: PyPI package was built before migration file was committed to repository
  - **Prevention**: Added migration file count verification to release workflow

### ♻️ Improved

- **Release workflow hardening**
  - Added verification step to count migration files in built wheel
  - Release now fails if migration count doesn't match source repository
  - Prevents future packaging bugs where files are missing from distribution

### 📋 Migration for v0.10.12 Users

If you installed v0.10.12 from PyPI and upgraded from v0.10.11:
```bash
pip install --upgrade spec-kitty-cli
spec-kitty upgrade  # Run again to apply missing migration 0.10.12
```

The migration will remove mission-specific constitution directories:
- `.kittify/missions/software-dev/constitution/` → removed
- `.kittify/missions/research/constitution/` → removed
- Single project-level constitution: `.kittify/memory/constitution.md` (kept)

## [0.10.12] - 2026-01-12

### 🔒 Security (IMPORTANT)

- **Comprehensive adversarial review framework**
  - Expanded review template from 3 bullets (109 lines) to 12 scrutiny categories (505 lines)
  - **Security scrutiny now mandatory**: 10 detailed security subsections
  - **Mandatory verification**: 7 security grep commands must be run on EVERY review
  - **Automatic rejection** if any security check fails
  - **Impact**: All future features will have security-first reviews
  - **Rationale**: Prevents systematic quality issues (TODOs in prod, mocked implementations, security vulnerabilities)
  - See spec footnote and commit `61d7d01` for complete rationale

### 🐛 Fixed

- **Windows dashboard ERR_EMPTY_RESPONSE** (#71)
  - Replaced POSIX-only signal handling with cross-platform psutil library
  - `signal.SIGKILL` and `signal.SIGTERM` don't exist on Windows
  - Added `psutil>=5.9.0` dependency for cross-platform process management
  - Refactored `src/specify_cli/dashboard/lifecycle.py`:
    * `os.kill(pid, 0)` → `psutil.Process(pid).is_running()`
    * `signal.SIGKILL` → `psutil.Process(pid).kill()` (6 locations)
    * `signal.SIGTERM` → `psutil.Process(pid).terminate()` with timeout
  - Added proper exception handling (NoSuchProcess, AccessDenied, TimeoutExpired)
  - Dashboard now starts, serves HTML, and stops cleanly on Windows 10/11
  - All 41 dashboard tests passing

- **Upgrade migration failures** (#70)
  - Fixed `m_0_7_3_update_scripts.py` to handle missing bash scripts gracefully
  - Fixed `m_0_10_6_workflow_simplification.py` to copy templates before validation
  - Fixed `m_0_10_2_update_slash_commands.py` to explicitly remove legacy .toml files
  - Fixed `m_0_10_0_python_only.py` to explicitly remove `.kittify/scripts/tasks/`
  - Created `m_0_10_12_constitution_cleanup.py` to remove mission constitutions
  - All migrations now idempotent (safe to run multiple times)
  - Upgrade path from 0.6.4 → 0.10.12 now completes without manual intervention

- **Upgrade migration parameter mismatch** (#68 follow-up)
  - Fixed `m_0_10_9_repair_templates.py` migration calling `generate_agent_assets()` with wrong parameter name
  - Changed `ai=ai_config` to `agent_key=ai_config` to match function signature

### ♻️ Refactored

- **Template source relocation** (Safe dogfooding - Critical)
  - Moved ALL template sources from `.kittify/` to `src/specify_cli/`
  - Templates: `.kittify/templates/` → `src/specify_cli/templates/`
  - Missions: `.kittify/missions/` → `src/specify_cli/missions/`
  - Scripts: `.kittify/scripts/` → `src/specify_cli/scripts/`
  - Updated `src/specify_cli/template/manager.py` to load from `src/` not `.kittify/`
  - Removed ALL `.kittify/*` force-includes from `pyproject.toml`
  - **Impact**: Spec-kitty developers can now safely dogfood spec-kitty without risk of packaging their filled-in constitutions
  - **Verification**: Building wheel produces ZERO `.kittify/` or `memory/constitution.md` entries
  - Package now only contains `src/specify_cli/` (proper Python packaging)

- **Mission-specific constitutions removed**
  - Removed `mission.constitution_dir` property from `src/specify_cli/mission.py`
  - Removed constitution scanning from `src/specify_cli/manifest.py`
  - Deleted all `missions/*/constitution/` directories
  - **Impact**: Single project-level constitution model (`.kittify/memory/constitution.md`)
  - **Migration**: `m_0_10_12_constitution_cleanup.py` removes mission constitutions from user projects
  - Eliminates confusion about which constitution applies

## [0.10.11] - 2026-01-07

### 🐛 Fixed

- **Upgrade migration parameter mismatch** (#68 follow-up)
  - Fixed `m_0_10_9_repair_templates.py` migration calling `generate_agent_assets()` with wrong parameter name
  - Changed `ai=ai_config` to `agent_key=ai_config` to match function signature
  - Corrected parameter order to match function definition
  - **Root cause**: Migration was using deprecated parameter name, blocking users from upgrading to 0.10.11
  - **Impact**: Users unable to run `spec-kitty upgrade` to get template fixes from 0.10.11

## [0.10.11] - 2026-01-07

### 🐛 Fixed

- **Deprecated script references in mission templates** (#68)
  - Fixed `.kittify/missions/software-dev/templates/task-prompt-template.md` to use workflow commands instead of deprecated `python3 .kittify/scripts/tasks/tasks_cli.py`
  - Fixed `.kittify/templates/task-prompt-template.md` with same update
  - Fixed `.kittify/missions/software-dev/command-templates/tasks.md` to reference workflow commands
  - Updated `.kittify/templates/POWERSHELL_SYNTAX.md` to document spec-kitty CLI instead of obsolete PowerShell scripts
  - **Root cause**: Migration 0.10.9 fixed agent command templates but missed mission-specific templates
  - **Impact**: Agents were executing users' local `cli.py` files instead of spec-kitty CLI on Windows

### ✨ Added

- **Template compliance tests** - Prevent deprecated script references
  - `test_no_deprecated_script_references()` - Detects old `.kittify/scripts/` paths in templates
  - `test_templates_use_spec_kitty_cli()` - Ensures templates reference spec-kitty CLI commands
  - Tests run on all mission templates and global templates
  - Prevents regression of issue #68

## [0.10.10] - 2026-01-06

### 🐛 Fixed

- **Windows UTF-8 encoding error in agent commands** (#66)
  - Fixed `'charmap' codec can't encode characters` error on Windows
  - `spec-kitty agent feature create-feature` now works correctly on Windows
  - Added UTF-8 stdout/stderr reconfiguration in main() entry point
  - Handles Unicode characters in git output and error messages
  - Gracefully falls back for Python < 3.7

## [0.10.9] - 2026-01-06

### 🐛 Fixed

- **CRITICAL: Wrong templates bundled in PyPI packages** (#62, #63, #64)
  - Fixed pyproject.toml to bundle .kittify/templates/ instead of outdated /templates/
  - Removed outdated /templates/ directory entirely to prevent confusion
  - All PyPI installations now receive correct Python CLI templates
  - No more bash script references in command templates
  - Migration 0.10.0 now handles missing templates gracefully
  - Added package bundling validation tests to prevent regression

- **Template divergence eliminated**
  - 10 of 13 command templates were outdated in /templates/
  - implement.md was 199 lines longer in old location (277 vs 78 lines)
  - Git hooks were missing (1 vs 3)
  - claudeignore-template was missing

- **All 12 AI agent integrations fixed**
  - Claude Code, GitHub Copilot, Cursor, Gemini, Qwen Code, OpenCode, Windsurf,
    GitHub Codex, Kilocode, Augment Code, Roo Cline, Amazon Q
  - All agents now receive correct Python CLI slash commands

### ✨ Added

- **`spec-kitty repair` command** - Standalone command to repair broken templates
  - Detects bash/PowerShell script references in slash commands
  - Automatically regenerates templates from correct source
  - Provides detailed feedback about repairs performed
  - Can be run with `--dry-run` to preview changes

- **Repair migration (0.10.9_repair_templates)** - Automatically fixes broken installations
  - Detects projects with broken template references
  - Regenerates all agent slash commands from correct templates
  - Runs automatically during `spec-kitty upgrade`
  - Verifies repair was successful

- **Package bundling validation tests** - Prevents future regressions
  - Validates correct templates are bundled in sdist and wheel
  - Checks for bash script references before release
  - Tests importlib.resources accessibility

### 📚 Migration & Upgrade Path

**For users with broken installations (issues #62, #63, #64):**

1. **Upgrade spec-kitty package:**
   ```bash
   pip install --upgrade spec-kitty-cli
   spec-kitty --version  # Should show 0.10.9
   ```

2. **Run upgrade to apply repair migration:**
   ```bash
   cd /path/to/your/project
   spec-kitty upgrade
   ```
   This will automatically detect and fix broken templates.

3. **Alternative: Use dedicated repair command:**
   ```bash
   spec-kitty repair
   ```
   Provides detailed feedback about what's being fixed.

4. **Verify repair:**
   ```bash
   # Check for bash script references (should return nothing)
   grep -r "scripts/bash" .claude/commands/
   ```

**For new projects:**
- Automatically get correct templates from package
- No action needed

**For existing healthy projects:**
- Run `spec-kitty upgrade` to stay current
- No breaking changes

### 🔒 Breaking Changes

None - Fully backwards compatible. Existing projects will upgrade smoothly.

## [0.10.8] - 2025-12-30

### 🐛 Fixed

- **Critical: Constitution not copied to worktrees** (#46)
  - Moved `memory/` directory from root to `.kittify/memory/` where code expects it
  - Removed broken circular symlinks (`.kittify/memory` → `../../../.kittify/memory`)
  - Fixed `.kittify/AGENTS.md` to be real file instead of broken symlink
  - Fixed worktree.py symlink handling (check for symlink before trying rmtree)
  - Added migration to automatically fix existing projects
  - Worktrees now correctly access constitution from main repo

- **Migration system** (v0.10.8_fix_memory_structure)
  - Automatically moves `memory/` to `.kittify/memory/` in existing projects
  - Removes broken symlinks and creates proper structure
  - Updates worktrees to use correct paths
  - Handles both Unix symlinks and Windows file copies

### 🔧 Changed

- **Directory structure standardization**
  - `memory/` → `.kittify/memory/` (matches `.kittify/scripts/`, `.kittify/templates/`)
  - `.kittify/AGENTS.md` is now a real file (not symlink)
  - All `.kittify/` resources now follow consistent pattern

## [0.10.7] - 2025-12-30

### 🐛 Fixed

- **Critical: Copilot initialization bug** (#53, fixes #61, #50)
  - Fixed NameError when running `spec-kitty init --ai copilot`
  - Changed `commands_dir` to `command_templates_dir` in asset_generator.py
  - Unblocks all users trying to initialize projects with Copilot

- **Critical: Dashboard contracts and checklists missing** (#59, fixes #52)
  - Restored contracts and checklists handlers that were lost in Nov 11 dashboard refactoring
  - Added generic `_handle_artifact_directory()` helper method
  - Both contracts and checklists now display correctly in dashboard
  - Fixed frontend to use full filepath instead of filename only

- **Critical: Windows UTF-8 encoding errors** (#56)
  - Added explicit `encoding='utf-8'` to read_text() calls
  - Fixes dashboard diagnostics showing "undefined" on Windows
  - Affects manifest.py and migration files
  - Windows defaults to cp1252, causing UnicodeDecodeError with UTF-8 content

- **Plan.md location validation** (#60)
  - Improved validation messaging in plan.md template
  - Added prominent ⚠️ STOP header for AI agents
  - Clearer examples of correct vs wrong worktree locations
  - Template-only change (no code modifications)

### 🔄 Closed

- PR #58 - Obsolete (PowerShell scripts deleted in v0.10.0)
- PR #57 - Obsolete (PowerShell scripts deleted in v0.10.0)
- PR #49 - Superseded by #59 (better architecture)
- PR #43 - Obsolete (PowerShell scripts deleted in v0.10.0)

## [0.10.6] - 2025-12-18

### ✨ Added

- **Workflow commands for simplified agent experience**
  - New `spec-kitty agent workflow implement [WP_ID]` command
  - New `spec-kitty agent workflow review [WP_ID]` command
  - Commands display full WP prompt directly to agents (no file navigation)
  - Auto-detect first planned/for_review WP when no ID provided
  - Auto-move WP to "doing" lane before displaying prompt
  - Show "WHEN YOU'RE DONE" instructions at top of output
  - Display source file path for easy re-reading
  - Prevents race conditions (two agents picking same WP)

### 🔧 Changed

- **Slash command template simplification**
  - implement.md: 78 lines → 11 lines (calls workflow command)
  - review.md: 72 lines → 11 lines (calls workflow command)
  - Templates now just run workflow commands instead of complex instructions
  - Agents see prompts immediately without navigation confusion

- **Consistent lane management**
  - Both implement and review workflows move WP to "doing" at start
  - Prevents ambiguity about which lane means "actively working"
  - Review workflow now supports auto-detect (no argument needed)

### 🐛 Fixed

- **Worktree path resolution**
  - Fixed `_find_first_planned_wp()` to work correctly in worktrees
  - Fixed `_find_first_for_review_wp()` to work correctly in worktrees
  - Auto-detect now finds WPs in worktree's kitty-specs/, not main repo

- **Legacy subdirectory cleanup**
  - Migrated features 007 and 010 from old subdirectory structure to flat structure
  - Moved 15 WP files from `tasks/done/phase-*/` to flat `tasks/`
  - All features now use proper flat structure with frontmatter-only lanes

## [0.9.4] - 2025-12-17

### 📚 Documentation & Validation

- **Prevent agent-created subdirectories in tasks/**
  - Added explicit warnings to tasks/README.md
  - Updated AGENTS.md with flat structure requirements
  - Updated /spec-kitty.tasks template to forbid subdirectories
  - Added runtime validation in check-prerequisites.sh
  - Blocks execution if phase-*, component-*, or any subdirectories found
  - Clear error messages with examples of correct vs wrong paths

This prevents Claude agents from creating organizational subdirectories like `tasks/phase-1/`, `tasks/backend/`, etc.

## [0.9.3] - 2025-12-17

### 🐛 Fixed

- **Critical symlink detection fix**
  - Now checks `is_symlink()` BEFORE `exists()` (exists() returns False for broken symlinks!)
  - Properly removes both working and broken symlinks from worktrees
  - Fixes remaining test failures in worktree cleanup migration
  - Handles all symlink scenarios correctly

This completes the fix for symlink removal in worktree cleanup.

## [0.9.2] - 2025-12-17

### 🐛 Fixed

- **Symlink handling in worktree cleanup**
  - Migration now properly detects and removes symlinks to command directories
  - Uses `unlink()` for symlinks instead of `shutil.rmtree()`
  - Fixes "Cannot call rmtree on a symbolic link" error during upgrade
  - Handles both symlinks and regular directories correctly

This fixes the upgrade failure when worktrees have symlinked agent command directories.

## [0.9.1] - 2025-12-17

### 🔧 Bug Fixes & Improvements

This release fixes critical issues found in v0.9.0 and adds version checking to prevent compatibility problems.

### 🆕 Added

- **Version compatibility checking**
  - CLI now checks for version mismatches between installed spec-kitty-cli and project version
  - Hard error with explicit instructions when versions don't match
  - Special critical warning for v0.9.0+ upgrade explaining breaking changes
  - Shows detailed before/after directory structure comparison
  - Version checks in all CLI commands and bash scripts
  - Graceful handling of legacy projects without metadata

- **Programmatic frontmatter management**
  - New `specify_cli.frontmatter` module for consistent YAML operations
  - Uses ruamel.yaml for absolute formatting consistency
  - No more manual YAML editing by LLMs or scripts
  - Prevents quoted vs unquoted value inconsistencies

### 🐛 Fixed

- **Migration improvements**
  - v0.9.0 migration now finds ALL markdown files (not just WP*.md)
  - Detects and removes empty lane subdirectories
  - Uses shutil.rmtree() for robust directory removal
  - Better detection of legacy format

- **Complete lane migration (v0.9.1)**
  - Migrates files missed by v0.9.0 (phase-*.md, task-*.md, etc.)
  - Removes ALL agent command directories from worktrees (.codex/prompts/, .gemini/commands/, etc.)
  - Removes .kittify/scripts/ from worktrees (inherit from main repo)
  - Normalizes all frontmatter to consistent YAML format
  - Fixes issue where worktrees had old command templates referencing deprecated scripts

- **Flat structure in new features**
  - Fixed create-new-feature.sh to create flat tasks/ directory (not subdirectories)
  - Updated README.md documentation to reflect v0.9.0+ structure
  - New features now work correctly with frontmatter-only lanes from day one

- **Lane validation**
  - tasks_cli.py update command now validates lane values
  - Rejects invalid lanes before processing
  - Clear error messages for invalid input

### 🔧 Changed

- Added `ruamel.yaml>=0.18.0` dependency for consistent YAML handling
- Updated success messages to reflect flat structure

### 🚀 Migration

If you upgraded to v0.9.0 and still have issues, run `spec-kitty upgrade` again to apply v0.9.1 fixes:
- Completes any remaining lane migrations
- Cleans up worktree command directories
- Normalizes all frontmatter for consistency

## [0.9.0] - 2025-12-17

### 🎯 Major Release: Frontmatter-Only Lane Management

This release fundamentally changes how Spec Kitty manages work package lanes, eliminating directory-based lane tracking in favor of a simpler, conflict-free frontmatter-only system.

### ⚠️ Breaking Changes

- **Lane system completely redesigned**
  - Work packages now live in a flat `kitty-specs/<feature>/tasks/` directory
  - Lane status determined **solely by `lane:` frontmatter field** (no more subdirectories)
  - Old system: `tasks/planned/WP01.md`, `tasks/doing/WP02.md` ❌
  - New system: `tasks/WP01.md` with `lane: "planned"` ✅

- **Command renamed: `move` → `update`**
  - Legacy `tasks_cli.py move` command removed
  - Use `tasks_cli.py update <feature> <WP> <lane>` instead
  - Semantic clarity: command updates metadata, doesn't move files
  - Legacy format detection: `update` command refuses to work on old directory-based structure

- **Direct frontmatter editing now supported**
  - You can now directly edit the `lane:` field in WP frontmatter
  - Previous "DO NOT EDIT" warnings removed from all templates
  - System recognizes manual lane changes immediately
  - No file movement required for lane transitions

### 🆕 Added

- **Migration command: `spec-kitty upgrade`**
  - Automatically migrates features from directory-based to frontmatter-only format
  - Preserves all lane assignments during migration
  - Idempotent: safe to run multiple times
  - Cleans up empty lane subdirectories after migration
  - Migrates both main repo and worktree features

- **Legacy format detection**
  - `is_legacy_format()` function detects old directory-based structure
  - CLI commands display helpful warnings when legacy format detected
  - Dashboard shows migration prompt for legacy features
  - Non-blocking: legacy features remain functional until migrated

- **Enhanced status command**
  - Better formatted output with lane grouping
  - Auto-detects feature from branch/worktree when not specified
  - Shows work packages organized by current lane
  - Works with both legacy and new formats

### 🔧 Changed

- **Work package location logic**
  - `locate_work_package()` now searches flat `tasks/` directory first
  - Falls back to legacy subdirectory search for backwards compatibility
  - Exact WP ID matching (WP04 won't match WP04b)

- **Lane extraction utilities**
  - New `get_lane_from_frontmatter()` function extracts lane from YAML
  - Defaults to "planned" when `lane:` field missing
  - Validates lane values against allowed set
  - Available in both `task_helpers.py` and `tasks_support.py`

- **Dashboard scanner updates**
  - Reads lane from frontmatter instead of directory location
  - Displays legacy format warnings
  - Works seamlessly with both formats during transition

- **Activity log behavior**
  - Lane transitions still append activity log entries
  - Captures agent, shell PID, and timestamp
  - No file movement logged (because no movement occurs)

### 📚 Documentation

- **Updated all templates**
  - `.kittify/templates/task-prompt-template.md` - Removed "DO NOT EDIT" warnings
  - `.kittify/templates/tasks-template.md` - Updated for flat structure
  - `.kittify/templates/AGENTS.md` - New lane management instructions
  - `tasks/README.md` - Rewritten for flat directory layout

- **Updated mission templates**
  - All mission-specific templates updated (software-dev, research)
  - Command templates updated (`implement.md`, `review.md`, `merge.md`)
  - Examples updated to show new workflow

- **Updated main documentation**
  - `README.md` - Updated quick start examples
  - `docs/quickstart.md` - New lane management workflow
  - `docs/multi-agent-orchestration.md` - Updated collaboration examples
  - All `examples/` updated with new commands

### 🧪 Testing

- 286 tests passing (0 failures)
- New tests for frontmatter-only lane system
- Legacy format detection tests
- Migration command tests
- Dual-format compatibility tests

### 🚀 Migration Guide

**For existing projects:**

1. **Back up your work** (commit changes, push to remote)
2. **Run migration**: `spec-kitty upgrade`
3. **Verify**: `spec-kitty status --feature <your-feature>`
4. **Update workflows**: Replace `move` with `update` in scripts/docs

**Key benefits of upgrading:**

- ✅ No file conflicts during lane changes (especially in worktrees)
- ✅ Direct editing of `lane:` field supported
- ✅ Better multi-agent compatibility
- ✅ Simpler mental model (one directory, not four)
- ✅ Fewer git operations per lane change

**Legacy format still works** - You can continue using old directory structure until ready to migrate. All commands detect format automatically.

### 🐛 Fixed

- File conflicts during simultaneous lane changes by multiple agents
- Git staging issues with lane transitions
- Race conditions in worktree-based parallel development
- Lane mismatch validation errors (no longer possible with frontmatter-only)

### 🔗 Related

- Feature implementation: `007-frontmatter-only-lane`
- All 6 work packages completed and reviewed
- Comprehensive test coverage added

---

## [0.8.2] - 2025-12-17

### Added

- **Task lane management documentation** - Added clear instructions to AGENTS.md and task templates warning agents never to manually edit the `lane:` YAML field
  - Lane is determined by directory location, not YAML field
  - Editing `lane:` without moving the file creates a mismatch that breaks the system
  - All templates now include YAML comment: `# DO NOT EDIT - use: workflow commands` (legacy note)
  - Added "Task Lane Management Rule" section to project AGENTS.md

## [0.8.1] - 2025-12-17

### Fixed

- **Work package move race conditions** - Multiple agents can now work on different WPs simultaneously without blocking each other
  - Conflict detection now only blocks on changes to the same WP, not unrelated WP files
  - Agents working on WP05 no longer block moves of WP04

- **Exact WP ID matching** - `WP04` no longer incorrectly matches `WP04b`
  - Changed from prefix matching to exact boundary matching
  - Pattern now requires WP ID to be followed by `-`, `_`, `.`, or end of filename

- **Cleanup no longer leaves staged deletions** - Stale copy cleanup uses filesystem delete instead of `git rm`
  - Prevents orphaned staged deletions from blocking subsequent operations
  - Automatically unstages any previously staged changes to cleaned files

## [0.8.0] - 2025-12-15

### Breaking Changes

- **Mission system refactored to per-feature model**
  - Missions are now selected during `/spec-kitty.specify` instead of `spec-kitty init`
  - Each feature stores its mission in `meta.json` (field: `"mission": "software-dev"`)
  - `.kittify/active-mission` symlink/file is no longer used
  - Run `spec-kitty upgrade` to clean up existing projects

- **Removed commands**
  - `spec-kitty mission switch` - Missions are now per-feature, not per-project
  - Running this command now shows a helpful error message explaining the new workflow

- **Removed flags**
  - `--mission` flag from `spec-kitty init` - Use `/spec-kitty.specify` instead
  - Flag is hidden but shows deprecation warning if used

### Added

- **Mission inference during `/spec-kitty.specify`** - LLM analyzes feature description and suggests appropriate mission:
  - "Build a REST API" → suggests `software-dev`
  - "Research best practices" → suggests `research`
  - User confirms or overrides the suggestion
  - Explicit `--mission` flag bypasses inference

- **Per-feature mission storage** - Selected mission stored in feature's `meta.json`:
  - All downstream commands read mission from feature context
  - Legacy features without mission field default to `software-dev`

- **Mission discovery** - New `discover_missions()` function returns all available missions with source indicators

- **Updated `spec-kitty mission list`** - Shows source column (project/built-in) for each mission

- **Migration for v0.8.0** - `spec-kitty upgrade` removes obsolete `.kittify/active-mission` file

- **AGENTS.md worktree fix** - New worktrees get AGENTS.md symlink, and `spec-kitty upgrade` fixes existing worktrees

### Changed

- All downstream commands (`/spec-kitty.plan`, `/spec-kitty.tasks`, `/spec-kitty.implement`, `/spec-kitty.review`, `/spec-kitty.accept`) now read mission from feature's `meta.json`
- `create-new-feature.sh` accepts `--mission <key>` parameter to set mission in meta.json
- Common bash/PowerShell scripts updated to resolve mission from feature directory
- `spec-kitty mission current` shows current default mission (for informational purposes)
- Dashboard template now includes dynamic AGENTS.md path discovery instructions

### Deprecated

- `set_active_mission()` function - Shows deprecation warning, will be removed in future version

### Migration Guide

1. Run `spec-kitty upgrade` to remove `.kittify/active-mission`
2. Existing features without `mission` field will use `software-dev` by default
3. New features will have mission set during `/spec-kitty.specify`

## [0.7.4] - 2025-12-14

### Added

- **Script Update Migration** – `spec-kitty upgrade` now updates project scripts:
  - Copies latest `create-new-feature.sh` from package to project
  - Fixes worktree feature numbering bug in existing projects
  - Previously, projects kept old scripts from when they were initialized

## [0.7.3] - 2025-12-14

### Fixed

- **Duplicate Feature Numbers with Worktrees** – Script now scans both `kitty-specs/` AND `.worktrees/` for existing feature numbers:
  - Previously only scanned `kitty-specs/` which was empty when using worktrees
  - This caused new features to get `001` even when `001-*` worktree already existed
  - Now correctly finds highest number across both locations

## [0.7.2] - 2025-12-14

### Fixed

- **Duplicate Slash Commands in Worktrees (Corrected)** – Fixed the fix from v0.7.1:
  - v0.7.1 incorrectly removed commands from main repo (broke `/` commands there)
  - v0.7.2 removes commands from **worktrees** instead (they inherit from main repo)
  - Claude Code traverses UP, so worktrees find main repo's `.claude/commands/`
  - Main repo keeps commands, worktrees don't need their own copy

## [0.7.1] - 2025-12-14 [YANKED]

### Fixed

- ~~Duplicate Slash Commands in Worktrees~~ – **Incorrect fix, replaced by v0.7.2**

## [0.7.0] - 2025-12-14

### Added

- **`spec-kitty upgrade` Command** – Automatically migrate existing projects to current version:
  - Detects project version via metadata or directory structure heuristics
  - Applies all necessary migrations in order (0.2.0 → 0.6.7)
  - Auto-upgrades worktrees alongside main project
  - Supports `--dry-run`, `--verbose`, `--json`, `--target`, `--no-worktrees` options
  - Tracks applied migrations in `.kittify/metadata.yaml`
  - Idempotent - safe to run multiple times

- **Migration System** – Five automatic migrations for project structure updates:
  - `0.2.0`: `.specify/` → `.kittify/` directory rename
  - `0.4.8`: Add all 12 agent directories to `.gitignore`
  - `0.5.0`: Install encoding validation git hooks
  - `0.6.5`: `commands/` → `command-templates/` rename
  - `0.6.7`: Ensure software-dev and research missions are present

- **Broken Mission Detection** – `VersionDetector.detect_broken_mission_system()` identifies corrupted mission.yaml files

- **Migration Registry Validation** – Duplicate migration IDs and missing required fields now raise `ValueError`

### Fixed

- **Test Timeout in Dashboard CLI Tests** – Reduced port cleanup from 763 ports to 8 specific test ports
- **Playwright Window Handling** – Tests now open new windows (not tabs) and close properly on exit

## [0.6.7] - 2025-12-13

### Fixed

- **Missing software-dev Mission in PyPI Package** – Fixed build configuration to include all missions:
  - Added explicit sdist include patterns to pyproject.toml
  - The `software-dev` mission was missing from v0.6.5 and v0.6.6 wheel builds
  - Root cause: `force-include` only applied to wheel target, not sdist (wheel was built from sdist)
  - Now both `software-dev` and `research` missions are correctly packaged

## [0.6.6] - 2025-12-13

### Fixed

- **Test Suite Updated for 12 Agent Directories** – All tests now expect 12 agents (added `.github/copilot/`):
  - Updated `test_init_flow.py`, `test_gitignore_management.py`, `test_gitignore_manager_simple.py`
  - Updated `tests/unit/test_gitignore_manager.py` to expect 12 agents
  - Fixed template manager tests to use new `.kittify/` source paths

### Changed

- **Template Source Paths** – Tests now use correct `.kittify/templates/command-templates/` paths

## [0.6.5] - 2025-12-13

### Added

- **Pre-commit Git Hooks** – Automatic protection against committing agent directories:
  - Blocks commits containing `.claude/`, `.codex/`, `.gemini/`, etc.
  - Warns about `.github/copilot/` (nested in `.github/` which is usually committed)
  - Installed automatically during `spec-kitty init`

- **GitHub Copilot Directory Protection** – Added `.github/copilot/` as 12th protected agent directory

- **.claudeignore Generation** – Optimizes Claude Code token usage by excluding templates

### Fixed

- **Worktree Constitution Symlinks** – Feature worktrees now share constitution via symlink
- **Git Hooks Installation Timing** – Hooks now install after `.git/` is created

## [0.6.4] - 2025-11-26

### Fixed

- **Agent Commands Missing in Worktrees** – Slash commands now work in all feature worktrees for all AI agents:
  - `create-new-feature.sh` now symlinks agent command directories from main repo to worktrees
  - Supports all 12 agent types: Claude, Gemini, Copilot, Cursor, Qwen, OpenCode, Windsurf, Codex, KiloCode, Auggie, Roo, Amazon Q
  - Fixes `/spec-kitty.research`, `/spec-kitty.plan`, and all other slash commands in worktrees
  - Existing worktrees get symlinks added when reused (backward compatible)
  - Root cause: worktrees are separate working directories that don't share `.claude/commands/` etc.

## [0.6.3] - 2025-11-25

### Fixed

- **Mission Directory Not Copied During Init** – Projects initialized with `spec-kitty init` now correctly receive mission templates:
  - Fixed `copy_specify_base_from_package()` to look at correct path `specify_cli/missions` (matching pyproject.toml)
  - Previously looked at wrong paths: `.kittify/missions` and `template_data/missions`
  - `software-dev` mission was missing from initialized projects, breaking `/spec-kitty.plan` and other commands
  - Root cause: pyproject.toml packages missions to `specify_cli/missions` but code looked elsewhere

## [0.6.2] - 2025-11-18

### Fixed

- **PowerShell Wrapper Parameter Handling** – Windows lane transitions now work correctly:
  - Fixed legacy `tasks-move-to-lane.ps1` to properly parse named PowerShell parameters
  - Translates Spec Kitty's named params (`-FeatureName`, `-TaskId`, `-TargetLane`) to `tasks_cli.py` positional args
  - Resolves `unrecognized arguments` error that broke `/spec-kitty.review` on Windows
  - Maintains backward compatibility with positional argument usage
  - Fixes #34

## [0.6.1] - 2025-11-18

### Fixed

- **Untracked Task File Moves** – Task move workflow now handles untracked files:
  - Added `is_file_tracked()` helper to detect if file is in git index
  - Move command automatically stages untracked source files before moving
  - Fixes `/spec-kitty.implement` failures when `/spec-kitty.tasks` doesn't commit
  - Provides clear feedback: `[spec-kitty] Added untracked file: ...`
  - Defensive fix works with both existing untracked files and future workflows

## [0.6.0] - 2025-11-16

### Fixed

- **Dashboard Constitution Tracking** – Feature-level constitution.md files now tracked and displayed:
  - Added constitution to scanner artifact list
  - Constitution appears in overview with ⚖️ icon
  - Frontend properly detects constitution.exists property

- **Dashboard Modification Detection** – Dashboard now detects file modifications, not just existence:
  - Scanner returns {exists, mtime, size} for each artifact instead of boolean
  - Frontend updated to use .exists property with optional chaining
  - Overview auto-reloads when artifacts change during polling
  - No manual refresh required to see new/modified files

- **Dashboard Project Constitution Endpoint** – Project constitution now loads in dashboard:
  - Added /api/constitution endpoint to serve .kittify/memory/constitution.md
  - Sidebar Constitution link now displays file content instead of "not found"
  - Separate from feature-level constitution tracking

- **Work Package Conflict Detection Too Strict** – Moving WP no longer blocked by unrelated WP changes:
  - Conflict detection now scoped to same work package ID only
  - Moving WP04 no longer fails if WP06/WP08 have uncommitted changes
  - Reduces false positives from ~90% to ~5%
  - Agents don't need --force for unrelated work packages
  - Still catches real conflicts (same WP in multiple lanes)

- **Accept Command Over-Questioning** – Acceptance workflow now auto-detects instead of asking:
  - Feature slug auto-detected from git branch
  - Mode defaults to 'local' (most common)
  - Validation commands searched in git log
  - Only asks user if auto-detection fails
  - Reduces user questions from 3-4 to 0 in typical case

- **Init Command Blocking on Optional Tools** – Project init no longer fails on missing agent tools:
  - Changed from red error + exit(1) to yellow warning + continue
  - Gemini CLI and other tools are optional
  - Users can install tools later without re-init
  - --ignore-agent-tools flag still available but rarely needed

- **Encoding Normalization Incomplete** – Unicode smart quotes now properly normalized to ASCII:
  - Added character mapping for 12 common Unicode characters
  - Smart quotes (U+2018/U+2019) → ASCII apostrophe
  - Em/en dashes → hyphens
  - Ellipsis, bullets, nbsp → ASCII equivalents
  - --normalize-encoding now produces true ASCII output

### Changed

- **Mission Display Simplified** – Reduced verbose mission card to single line:
  - Removed domain label, version number, path display
  - Removed redundant refresh button (auto-updates every second)
  - Changed from card layout to inline text: "Mission: {name}"
  - Cleaner, less cluttered header

### Added

- **Mission System Architecture** – Complete mission-based workflow system (feature 005):
  - Guards module for pre-flight validation
  - Pydantic mission schema validation
  - Mission CLI commands (list, current, switch, info)
  - Research mission templates and citation validators
  - Path convention validation
  - Dashboard mission display
  - Comprehensive integration tests

## [0.5.3] - 2025-11-15

### Fixed

- **Dashboard Orphaned Process Cleanup** – Fixed dashboard startup failures caused by orphaned test processes:
  - Dashboard now detects and cleans up orphaned processes when health check fails due to project path mismatch
  - Added retry logic after successful orphan cleanup
  - Orphan cleanup triggers on health check failure (not just port exhaustion)
  - Eliminates false "Unable to start dashboard" errors when orphaned test dashboards occupy ports

- **Dashboard Subprocess Import Failure** – Fixed ModuleNotFoundError in complex Python environments:
  - Dashboard subprocess now always inserts spec-kitty path at sys.path[0]
  - Fixes import failures when user's PYTHONPATH or .pth files contain spec-kitty path at lower priority
  - Ensures correct spec-kitty installation takes precedence over environment paths
  - Resolves "ModuleNotFoundError: No module named 'specify_cli.dashboard'" in subprocesses

### Changed

- **Test Suite Cleanup Improvements** – Enhanced dashboard test cleanup to prevent orphaned processes:
  - Module-level cleanup fixture kills all orphaned dashboards before and after test runs
  - Expanded cleanup port range from 9992-9999 to 9237-10000 (covers default and test ranges)
  - Added `kill_all_spec_kitty_dashboards()` helper using pgrep/pkill
  - Two-tier cleanup strategy: module-level (all processes) + function-level (specific ports)

### Added

- **Testing Guidelines for Agents** (`docs/testing-guidelines.md`) – Comprehensive testing best practices:
  - Required cleanup patterns for dashboard tests (pytest fixtures, autouse fixtures)
  - Anti-patterns to avoid (cleanup in test body, shared directories, no exception handling)
  - Impact analysis of orphaned processes on local development and CI/CD
  - Examples of proper test isolation and resource management

### Changed

- **Command Consolidation** – Merged `spec-kitty check` and `spec-kitty diagnostics` into `spec-kitty verify-setup`:
  - Removed redundant `spec-kitty check` and `spec-kitty diagnostics` commands
  - Tool checking now integrated into `verify-setup` with `--check-tools` flag (default: enabled)
  - Diagnostics mode with dashboard health available via `--diagnostics` flag
  - Removed ASCII banner from verify-setup for cleaner output
  - Simplifies CLI interface - single command for all environment verification
  - JSON output includes tool availability when `--check-tools` is enabled

### Removed

- **`spec-kitty check` command** – Functionality moved to `verify-setup --check-tools`
  - Migration: Use `spec-kitty verify-setup` instead of `spec-kitty check`
  - Tool checking enabled by default, disable with `--check-tools=false`
- **`spec-kitty diagnostics` command** – Functionality moved to `verify-setup --diagnostics`
  - Migration: Use `spec-kitty verify-setup --diagnostics` instead of `spec-kitty diagnostics`
  - Shows Rich panel-based output with dashboard health, observations, and issues

## [0.5.2] - 2025-11-14

### Fixed

- **Dashboard Startup Race Condition** – Fixed root cause of dashboard health check timing out prematurely:
  - Increased health check timeout from 10 to 20 seconds with exponential backoff
  - Retry pattern: 10×100ms, 40×250ms, 20×500ms for adaptive performance
  - Removed workaround fallback check that was masking the real issue
  - Eliminated false "Unable to start dashboard" errors on slower systems

### Changed

- **Dashboard Health Check Strategy** – Improved reliability with exponential backoff:
  - Quick initial checks (100ms) for fast systems
  - Gradual slowdown (250ms then 500ms) for slower systems
  - Total timeout increased to ~20 seconds for adequate startup time
  - Cleaner error handling without port-scanning fallback

### Added

- **Symlinked kitty-specs Test Coverage** – New test validates dashboard works with worktree structure:
  - Tests scenario from bug report (symlinked `kitty-specs/` to `.worktrees/`)
  - Ensures dashboard starts correctly with symlinked directories
  - Prevents regression of false error reporting

## [0.5.1] - 2025-11-14

### Added

- **Task Metadata Validation Guardrail** – Prevents workflow failures when file locations don't match frontmatter:
  - Auto-detects lane mismatches (file in `for_review/` but `lane: "planned"`)
  - CLI command: `spec-kitty validate-tasks --fix`
  - Integrated into `/spec-kitty.review` workflow (auto-runs before review)
  - Adds activity log entries documenting all repairs
  - Validates required fields (work_package_id, lane) and formats
- **Task Metadata Validation Module** (`src/specify_cli/task_metadata_validation.py`) – Core validation:
  - `detect_lane_mismatch()` - Finds directory/frontmatter inconsistencies
  - `repair_lane_mismatch()` - Auto-fixes with audit trail
  - `validate_task_metadata()` - Comprehensive field validation
  - `scan_all_tasks_for_mismatches()` - Feature-wide scanning

### Changed

- **Version Reading** – Now reads dynamically from package metadata instead of hardcoded value:
  - Uses `importlib.metadata.version()` to get actual installed version
  - `spec-kitty --version` always shows correct version
  - No manual updates needed in `__init__.py`
- **Review Workflow** – Added automatic task metadata validation before review:
  - Runs `spec-kitty validate-tasks --fix` automatically
  - Prevents agents getting stuck on lane mismatches
  - Documented in `.claude/commands/spec-kitty.review.md`

### Fixed

- **Dashboard CLI False Error** – CLI no longer reports "Unable to start dashboard" when dashboard actually started successfully. Added fallback verification to check if dashboard is accessible before reporting failure. Handles race condition where health check times out but server is functional.
- **Review Workflow Blocking** – Review command no longer fails when file locations don't match frontmatter metadata. Auto-validation repairs inconsistencies before review.
- **Hardcoded Version** – `spec-kitty --version` now reads from package metadata, always shows correct installed version.

### Documentation

- **task-metadata-validation.md** (350 lines) – Auto-repair workflow:
  - Lane mismatch detection and repair
  - CLI usage examples
  - Python API reference
  - Integration with review workflow

### Testing

- Added version detection tests to prevent future hardcoded version bugs
- Task metadata validation tested with real frontmatter/directory mismatches
- All tests passing (13/13)

## [0.5.0] - 2025-11-13

### Added

- **Encoding Validation Guardrail** – Comprehensive 5-layer defense system to prevent Windows-1252 characters from crashing the dashboard:
  - **Layer 1**: Dashboard auto-fixes encoding errors on read (server-side resilience)
  - **Layer 2**: Character sanitization module with 15+ problematic character mappings
  - **Layer 3**: CLI command `spec-kitty validate-encoding` with `--fix` flag
  - **Layer 4**: Pre-commit hook that blocks commits with encoding errors
  - **Layer 5**: Enhanced AGENTS.md with real crash examples and character blacklist
- **Plan Validation Guardrail** – Prevents agents from skipping the planning phase:
  - Detects 11 template markers in plan.md (threshold: 5+ markers = unfilled)
  - Blocks `/spec-kitty.research` command when plan is unfilled
  - Blocks `/spec-kitty.tasks` via check-prerequisites.sh
  - Clear error messages with remediation steps
- **Character Sanitization Module** (`src/specify_cli/text_sanitization.py`) – Core module for encoding fixes:
  - Maps smart quotes (`' ' " "`) → ASCII (`' "`)
  - Maps plus-minus (`±`) → `+/-`, multiplication (`×`) → `x`, degree (`°`) → `degrees`
  - Supports dry-run mode and automatic backup creation
  - Directory-wide sanitization with glob patterns
- **Plan Validation Module** (`src/specify_cli/plan_validation.py`) – Template detection:
  - Configurable threshold (default: 5 markers)
  - Line-precise error reporting
  - Strict and lenient validation modes

### Changed

- **Version Reading** – Now reads dynamically from package metadata instead of hardcoded value:
  - Uses `importlib.metadata.version()` to get actual installed version
  - `spec-kitty --version` always shows correct version
  - No manual updates needed in `__init__.py`
- **Review Workflow** – Added automatic task metadata validation before review:
  - Runs `spec-kitty validate-tasks --fix` automatically
  - Prevents agents getting stuck on lane mismatches
  - Documented in `.claude/commands/spec-kitty.review.md`
- **Dashboard Scanner** – Now resilient to encoding errors:
  - Auto-fixes files on read with backup creation
  - Creates error cards instead of crashing on bad files
  - Logs encoding issues with clear error messages
- **Research Command** – Added plan validation gate before allowing research artifact creation
- **Prerequisites Check Script** – Added bash-based plan validation (35 lines)
- **AGENTS.md Template** – Enhanced with encoding warnings:
  - Real crash examples from production
  - Explicit character blacklist with Unicode codepoints
  - Auto-fix workflow documentation

### Fixed

- **Dashboard Blank Page Issue** – Dashboard no longer crashes when markdown files contain Windows-1252 smart quotes, ±, ×, ° symbols. Auto-fix sanitizes files on first read.
- **Agents Skipping Planning** – Research and tasks commands now blocked until plan.md is properly filled out (not just template).
- **Review Workflow Blocking** – Review command no longer fails when file locations don't match frontmatter metadata. Auto-validation repairs inconsistencies before review.
- **Hardcoded Version** – `spec-kitty --version` now reads from package metadata, always shows correct installed version.

### Documentation

- **encoding-validation.md** (554 lines) – Complete guide covering:
  - Problem description with real examples
  - 5-layer architecture explanation
  - Testing procedures and troubleshooting
  - Migration guide for existing projects
  - API reference and performance considerations
- **plan-validation-guardrail.md** (202 lines) – Implementation details:
  - Problem and solution overview
  - Configuration instructions
  - Testing procedures
  - Benefits and future enhancements
- **task-metadata-validation.md** (350 lines) – Auto-repair workflow:
  - Lane mismatch detection and repair
  - CLI usage examples
  - Python API reference
  - Integration with review workflow
- **TESTING_REQUIREMENTS_ENCODING_AND_PLAN_VALIDATION.md** (1056 lines) – Functional test specifications:
  - 35+ test cases across 6 test suites
  - Coverage targets (85-95%)
  - Performance requirements
  - Edge case testing requirements

### Testing

- Added 7 unit tests for plan validation (all passing)
- Verified on real project (battleship): fixed 9 files with encoding issues
- Dashboard now loads successfully after encoding fixes
- Character mapping tests: smart quotes, ±, ×, ° all converted correctly

## [0.4.13] - 2025-11-13

### Fixed

- **CRITICAL: verify-setup ImportError (Issue #28)** – Fixed ImportError in `verify-setup` command caused by incorrect import statement in `verify_enhanced.py`. Changed `from . import detect_feature_slug, AcceptanceError` to `from .acceptance import detect_feature_slug, AcceptanceError`. This was a blocking bug that prevented users from running the diagnostic command.

## [0.4.12] - 2025-11-13

### Added

- **Version Flag** – Added `--version` and `-v` flags to display installed spec-kitty-cli version.
- **Dashboard Health Diagnostics** – Enhanced `spec-kitty diagnostics` to detect dashboard startup failures, test if dashboard can start, and report specific errors. Now catches issues like corrupted files, health check timeouts, and background process failures.

### Changed

- **Diagnostics Output** – Added Dashboard Health panel showing startup test results, PID tracking status, and specific failure reasons.

## [0.4.11] - 2025-11-13

### Fixed

- **PowerShell Python Quoting Bug (Issue #26)** – Fixed SyntaxError in PowerShell scripts caused by double-quote conflicts in embedded Python code. Changed all Python strings in `common.ps1` to use single quotes to avoid PowerShell string parsing conflicts.

### Added

- **PowerShell Syntax Guide** – Created comprehensive `templates/POWERSHELL_SYNTAX.md` with bash vs PowerShell syntax comparison table, common mistakes, and debugging tips for AI agents.
- **Conditional PowerShell Reference** – Enhanced `agent-file-template.md` to conditionally include PowerShell syntax reminders only for PowerShell projects, keeping bash contexts clean.

### Changed

- **AI Agent Context** – PowerShell-specific guidance now provided via separate reference document instead of cluttering bash-focused templates.

Fixes #26
Addresses #27

## [0.4.10] - 2025-11-13

### Fixed

- **CRITICAL: Missing missions directory in PyPI package** – Added `.kittify/missions/` to `pyproject.toml` force-include list. Previous release (0.4.9) was missing this directory, causing "Active mission directory not found" errors for all fresh installations.

## [0.4.9] - 2025-11-13

### Added

- **Diagnostics CLI Command** – New `spec-kitty diagnostics` command with human-readable and JSON output for comprehensive project health checks.
- **Dashboard Process Tracking** – Dashboard now stores process PID in `.dashboard` metadata file for reliable cleanup and monitoring.
- **Feature Collision Detection** – Added explicit warnings when creating features with duplicate names that would overwrite existing work.
- **LLM Context Documentation** – Enhanced all 13 command templates with location pre-flight checks, file discovery sections, and workflow context to prevent agents from getting lost.

### Changed

- **Dashboard Lifecycle** – Enhanced `ensure_dashboard_running()` to automatically clean up orphaned dashboard processes on initialization, preventing port exhaustion.
- **Feature Creation Warnings** – `create-new-feature.sh` now warns when git is disabled or features already exist, with clear JSON indicators for LLM agents.
- **Import Safety** – Fixed `detect_feature_slug` import path in diagnostics module to use correct module location.
- **Worktree Documentation** – Updated WORKTREE_MODEL.md to accurately describe `.kittify/` as a complete copy (not symlink) with disk space implications documented.

### Fixed

- **CRITICAL: Dashboard Process Orphan Leak** – Fixed critical bug where background dashboard processes were orphaned and accumulated until all ports were exhausted. Complete fix includes:
  - PIDs are captured and stored in `.dashboard` file (commit b8c7394)
  - Orphaned processes with .dashboard files are automatically cleaned up on next init
  - HTTP shutdown failures fall back to SIGTERM/SIGKILL with PID tracking
  - Port range cleanup scans for orphaned dashboards without .dashboard files (commit 11340a4)
  - Safe fingerprinting via health check API prevents killing unrelated services
  - Automatic retry with cleanup when port exhaustion detected
  - Failed startup processes are cleaned up (no orphans from Ctrl+C during health check)
  - Multi-project scenarios remain fully isolated (per-project PIDs, safe port sweeps)
  - Handles all orphan types: with metadata, without metadata, deleted temp projects
  - Prevents "Could not find free port" errors after repeated uses

- **Import Path Bug** – Fixed `detect_feature_slug` import in `src/specify_cli/dashboard/diagnostics.py` to import from `specify_cli.acceptance` instead of package root.

- **Worktree Documentation Accuracy** – Corrected WORKTREE_MODEL.md which incorrectly stated `.kittify/` was symlinked; it's actually a complete copy due to git worktree behavior.

### LLM Context Improvements

All command templates enhanced with consistent context patterns:
- **Location Pre-flight Checks**: pwd/git branch verification with expected outputs and correction steps
- **File Discovery**: Lists what files {SCRIPT} provides, output locations, and available context
- **Workflow Context**: Documents before/after commands and feature lifecycle integration

Templates updated:
- merge.md: CRITICAL safety check preventing merges from wrong location
- clarify.md, research.md, analyze.md: HIGH priority core workflow commands
- specify.md, checklist.md: Entry point and utility commands
- constitution.md, dashboard.md: Project-level and monitoring commands

### Testing

- ✅ Dashboard comprehensive test suite (34 tests, 100% coverage)
- ✅ All CLI commands validated
- ✅ Import paths verified
- ✅ Worktree behavior confirmed across test scenarios
- ✅ LLM context patterns applied consistently

### Security

- Dashboard process cleanup prevents resource exhaustion attacks
- Explicit warnings when creating duplicate features prevent silent data overwrite
- Git disabled warnings ensure users know when version control is unavailable

### Backward Compatibility

All changes are fully backward compatible:
- PID storage is optional (old `.dashboard` files still work)
- Feature collision detection is advisory (doesn't block creation)
- LLM context additions don't change command behavior
- Dashboard cleanup is automatic (users don't need to do anything)

## [0.4.12] - 2025-11-11

### Added

- **Core Service Modules** – Introduced `specify_cli.core.git_ops`, `project_resolver`, and `tool_checker` packages to host git utilities, project discovery, and tool validation logic with clean public APIs.
- **Test Coverage** – Added dedicated suites (`tests/specify_cli/test_core/test_git_ops.py`, `test_project_resolver.py`, `test_tool_checker.py`) covering subprocess helpers, path resolution, and tool validation flows.

### Changed

- **CLI Import Surface** – `src/specify_cli/__init__.py` now imports git, resolver, and tool helpers from the new core modules, slimming the monolith and sharing the implementations across commands.
- **Versioning Compliance** – `pyproject.toml` bumped to v0.4.12 to capture the core-service extraction and accompanying behavior changes.

## [0.4.11] - 2025-11-11

### Added

- **Template Test Suite** – New `tests/test_template/` coverage exercises template manager, renderer, and agent asset generator flows to guard the init experience.

### Changed

- **Template System Extraction** – Moved template discovery, rendering, and asset generation logic out of `src/specify_cli/__init__.py` into dedicated `specify_cli.template` modules with shared frontmatter parsing.
- **Dashboard Reuse** – Updated the dashboard scanner to consume the shared frontmatter parser so Kanban metadata stays in sync with CLI-generated commands.

## [0.4.10] - 2025-11-11

### Added

- **Core Modules** – Introduced `specify_cli.core.config` and `specify_cli.core.utils` to centralize constants, shared helpers, and exports for downstream packages.
- **CLI UI Package** – Moved `StepTracker`, arrow-key selection, and related utilities into `specify_cli.cli.ui`, enabling reuse across commands.
- **Test Coverage** – Added dedicated unit suites for the new core modules and CLI UI interactions (12 new tests).

### Changed

- **Package Structure** – Created foundational package directories for `core/`, `cli/`, `template/`, and `dashboard/`, including structured `__init__.py` exports.
- **Init Command Dependencies** – Updated `src/specify_cli/__init__.py` to consume the extracted modules, reducing monolith size and improving readability.
- **File Utilities** – Replaced ad-hoc directory creation/removal with safe helper functions to prevent duplication across commands.

## [0.4.8] - 2025-11-10

### Added

- **GitignoreManager Module** – New centralized system for managing .gitignore entries for AI agent directories, replacing fragmented approach.
- **Comprehensive Agent Protection** – Auto-protect ALL 12 AI agent directories (.claude/, .codex/, .opencode/, etc.) in .gitignore during init, not just selected ones.
- **Duplicate Detection** – Smart duplicate detection prevents .gitignore pollution when running init multiple times.
- **Cross-Platform Support** – Line ending preservation ensures .gitignore works correctly on Windows, macOS, and Linux.

### Changed

- **init Command Behavior** – Now automatically protects all AI agent directories instead of just selected ones, ensuring no sensitive data is accidentally committed.
- **Error Messages** – Improved error messages for permission issues with clear remediation steps (e.g., "Run: chmod u+w .gitignore").

### Fixed

- **Dashboard Markdown Rendering** – Fixed issue where .md files in Research and Contracts tabs were not rendered, now properly displays formatted markdown content.
- **Dashboard CSV Display** – Fixed CSV files not rendering in dashboard, now displays as formatted tables with proper styling and hover effects.

### Security

- **Agent Directory Protection** – All 12 known AI agent directories are now automatically added to .gitignore during init, preventing accidental commit of API keys, auth tokens, and other sensitive data.
- **Special .github/ Handling** – Added warning for .github/ directory which is used both by GitHub Copilot and GitHub Actions, reminding users to review before committing.

### Removed

- **Legacy Functions** – Removed `handle_codex_security()` and `ensure_gitignore_entries()` functions, replaced by comprehensive GitignoreManager class.

## [0.4.7] - 2025-11-07

### Added

- **Dashboard Diagnostics Page** – New diagnostics page showing real-time environment analysis, artifact location mismatches, and actionable recommendations.
- **CLI verify-setup Command** – New `spec-kitty verify-setup` command for comprehensive environment diagnostics in the terminal.
- **Worktree-Aware Resolution** – Added `resolve_worktree_aware_feature_dir()` function that intelligently detects and prefers worktree locations.
- **Agent Location Checks** – Standardized "CRITICAL: Location Requirement" sections in command templates with bash verification scripts.
- **Test Coverage** – Added comprehensive test suite for gitignore management and Codex security features with 9 test cases covering all edge cases.

### Changed

- **Command Templates** – Enhanced plan.md and tasks.md with explicit worktree location requirements and verification scripts.
- **Error Messages** – Improved bash script errors with visual indicators (❌ ERROR, 🔧 TO FIX, 💡 TIP) and exact fix commands.
- **Research Command** – Updated to use worktree-aware feature directory resolution.
- **Refactored Codex Security** – Extracted Codex credential protection logic into a dedicated `handle_codex_security()` function for better maintainability and testability.

### Fixed

- **Artifact Location Mismatch** – Fixed issue where agents create artifacts in wrong location, preventing them from appearing in dashboard.

## [0.4.5] - 2025-11-06

### Added

- **Agent Guidance** – Bundled a shared `AGENTS.md` ruleset that is copied into `.kittify/` so every generated command has a canonical place to point agents for path/encoding/git expectations.
- **Encoding Toolkit** – Introduced `scripts/validate_encoding.py` and new documentation to scan/fix Windows-1252 artifacts, plus a non-interactive init guide in `docs/non-interactive-init.md`.
- **Dashboard Assets** – Split the inline dashboard UI into static CSS/JS files and committed them with the release.

### Changed

- **CLI Help & Docs** – Expanded `spec-kitty init`, `research`, `check`, `accept`, and `merge` help text and refreshed README/index links to render correctly on PyPI.
- **Dashboard Runtime** – Hardened the dashboard server/CLI handshake with health checks, token-gated shutdown, and more resilient worktree detection.
- **Mission Handling** – Improved mission activation to fall back gracefully when symlinks are unavailable (e.g., Windows w/out dev mode) and aligned shell helpers with the new logic.

### Security

- **Codex Guardrails** – Automatically append `.codex/` to `.gitignore`, warn if `auth.json` is tracked, and reiterate the `CODEX_HOME` workflow to keep API credentials out of source control.

## [0.4.6] - 2025-11-06

### Fixed

- **PyYAML Dependency** – Added `pyyaml` to the core dependency list so mission loading works in clean environments (CI no longer fails installing the package).
- **PyPI README Links** – Restored absolute documentation links to keep images and references working on PyPI.

## [0.4.4] - 2025-11-06

### Security

- **Credential Cleanup** – Removed the committed `.codex` directory (OpenAI credentials) from the entire Git history and regenerated sanitized release assets.
- **Token Rotation** – Documented that all compromised keys were revoked and environments refreshed before reissuing packages.

### Changed

- **Release Artifacts** – Rebuilt GitHub release bundles and PyPI distributions from the cleaned history to ensure no secrets are present in published archives.

## [0.3.2] - 2025-11-03

### Added

- **Automated PyPI Release Pipeline** – Tag-triggered GitHub Actions workflow automatically builds, validates, and publishes releases to PyPI using `PYPI_API_TOKEN` secret, eliminating manual publish steps.
- **Release Validation Tooling** – `scripts/release/validate_release.py` CLI enforces semantic version progression, changelog completeness, and version/tag alignment in both branch and tag modes with actionable error messages.
- **Release Readiness Guardrails** – Pull request workflow validates version bumps, changelog entries, and test passage before merge; nightly scheduled checks monitor drift.
- **Comprehensive Release Documentation** – Complete maintainer guides covering secret management, branch protection, troubleshooting, and step-by-step release workflows.
- **Changelog Extraction** – `scripts/release/extract_changelog.py` automatically extracts version-specific release notes for GitHub Releases.
- **Release Test Suite** – 4 pytest tests validate branch mode, tag mode, changelog parsing, and version regression detection.

### Changed

- **GitHub Actions Workflows** – Updated `release.yml` with pinned dependency versions, proper workflow ordering (PyPI publish before GitHub Release), and checksums stored in `dist/SHA256SUMS.txt`.
- **Workflow Reliability** – Fixed heredoc syntax error in `protect-main.yml` that was causing exit code 127 failures.

### Security

- **Secret Hygiene** – PyPI credentials exclusively stored in GitHub Actions secrets with rotation guidance; no tokens in repository or logs; workflows sanitize outputs.
- **Workflow Permissions** – Explicit least-privilege permissions in all workflows (contents:write, id-token:write for releases; contents:read for guards).

## [0.3.1] - 2025-11-03

### Changed

- **Worktree-Aware Merge Flow** – `/spec-kitty merge` now detects when it is invoked from a Git worktree, runs the actual merge steps from the primary repository checkout, and surfaces clearer guidance when the target checkout is dirty.

### Documentation

- **Merge Workflow Guidance** – Updated templates and Claude workflow docs to describe the primary-repo hand-off during merges and reinforce the feature-worktree best practice.

## [0.3.0] - 2025-11-02

### Added

- **pip Installation Instructions** – All documentation now includes pip installation commands alongside uv, making Spec Kitty accessible to users who prefer traditional Python package management.
- **Multiple Installation Methods** – Documented three installation paths: PyPI (stable), GitHub (development), and one-time usage (pipx/uvx).

### Changed

- **Documentation Consistency** – Updated README.md, docs/index.md, docs/installation.md, and docs/quickstart.md to provide both pip and uv commands throughout.
- **Installation Recommendations** – PyPI installation now marked as recommended for stable releases, with GitHub source for development versions.

### Fixed

- **Packaging Issues** – Removed duplicate `.kittify` force-include that caused "Duplicate filename in local headers" errors on PyPI.
- **Test Dependencies** – Added `pip install -e .[test]` to workflows to ensure all project dependencies available for tests.

## [0.2.20] - 2025-11-02

### Added

- **Automated PyPI Release Pipeline** – Tag-triggered GitHub Actions workflow automatically builds, validates, and publishes releases to PyPI using `PYPI_API_TOKEN` secret, eliminating manual publish steps.
- **Release Validation Tooling** – `scripts/release/validate_release.py` CLI enforces semantic version progression, changelog completeness, and version/tag alignment in both branch and tag modes with actionable error messages.
- **Release Readiness Guardrails** – Pull request workflow validates version bumps, changelog entries, and test passage before merge; protect-main workflow blocks direct pushes to main branch.
- **Comprehensive Release Documentation** – Complete maintainer guides covering secret management, branch protection, troubleshooting, and step-by-step release workflows in README, docs, and inline help.
- **Enhanced PyPI Metadata** – Added project URLs (repository, issues, docs, changelog), keywords, classifiers, and license information to improve PyPI discoverability and presentation.
- **Changelog Extraction** – `scripts/release/extract_changelog.py` automatically extracts version-specific release notes for GitHub Releases.
- **Release Test Suite** – 4 pytest tests validate branch mode, tag mode, changelog parsing, and version regression detection.

### Changed

- **GitHub Actions Workflows** – Replaced legacy release workflow with modern PyPI automation supporting validation, building, checksums, GitHub Releases, and secure publishing.
- **Documentation Structure** – Added dedicated releases section to docs with readiness checklist, workflow references, and troubleshooting guides; updated table of contents.

### Security

- **Secret Hygiene** – PyPI credentials exclusively stored in GitHub Actions secrets with rotation guidance; no tokens in repository or logs; workflows sanitize outputs.
- **Workflow Permissions** – Explicit least-privilege permissions in all workflows (contents:write, id-token:write for releases; contents:read for guards).

## [0.2.3] - 2025-10-29

### Added

- **Mission system assets** – Bundled Software Dev Kitty and Deep Research Kitty mission definitions (commands, templates, constitutions) directly in the CLI package so `spec-kitty init` can hydrate missions without a network call.

### Changed

- Synced mission templates between the repository and packaged wheel to keep `/spec-kitty.*` commands consistent across `--ai` choices.

## [0.2.2] - 2025-10-29

### Added

- **Phase 0 Research command** – `spec-kitty research` (and `/spec-kitty.research`) scaffolds `research.md`, `data-model.md`, and CSV evidence logs using mission-aware templates so Deep Research Kitty teams can execute discovery workflows without leaving the guided process.
- **Mission templates for research** – Deep Research Kitty now ships reusable templates for research decisions, data models, and evidence capture packaged inside the Python wheel.

### Changed

- Updated `spec-kitty init` guidance, plan command instructions, and README workflow to include the new research phase between planning and task generation.

## [0.2.1] - 2025-10-29

### Added

- **Mission picker in init** - `spec-kitty init` now prompts for a mission (or accepts `--mission`) so projects start with Software Dev Kitty, Deep Research Kitty, or another bundled mission and record the choice in `.kittify/active-mission`.

### Changed

- Highlight the active mission in the post-init guidance while keeping the Codex export step as the final instruction.

## [0.2.0] - 2025-10-28

### Added

- **New `/spec-kitty.merge` command** - Completes the workflow by merging features into main branch and cleaning up worktrees automatically. Supports multiple merge strategies (merge, squash, rebase), optional push to origin, and configurable cleanup of worktrees and branches.
- **Worktree Strategy documentation** - Added comprehensive guide to the opinionated worktree approach for parallel feature development.
- **Dashboard screenshots** - Added dashboard-kanban.png and dashboard-overview.png showcasing the real-time kanban board.
- **Real-Time Dashboard section** - Added prominent dashboard documentation "above the fold" in README with screenshots and feature highlights.
- **Mission management CLI** - `spec-kitty mission list|current|switch|info` for inspecting and activating domain-specific missions inside a project.
- **Deep Research Kitty mission** - Research-focused templates (spec, plan, tasks, findings, prompts) and command guardrails for evidence-driven work.
- **Mission packaging** - Missions are now bundled in release archives and Python wheels so project initialization copies `.kittify/missions` automatically.

### Changed

- Updated command list in init output to show workflow order and include merge command.
- Updated `/spec-kitty.accept` description to clarify it verifies (not merges) features.
- Reordered slash commands documentation to reflect actual execution workflow.
- Updated maintainers to reflect fork ownership.
- Updated all repository references from `spec-kitty/spec-kitty` to `Priivacy-ai/spec-kitty`.
- Updated installation instructions to use GitHub repository URL instead of local directory.

### Fixed

- Removed invalid `multiple=True` parameter from `typer.Option()` in accept command that caused TypeError on CLI startup.
- Fixed "nine articles" claim in spec-driven.md to "core articles" (only 6 are documented).

### Removed

- Removed SECURITY.md (GitHub-specific security policies).
- Removed CODE_OF_CONDUCT.md (GitHub-specific contact information).
- Removed video overview section from README (outdated content).
- Removed plant emoji (🌱) branding from all documentation and code.
- Replaced logo_small.webp and logo_large.webp with actual spec-kitty cat logo.

## [0.1.3] - 2025-10-28

### Fixed

- Removed invalid `multiple=True` parameter from `typer.Option()` in accept command that caused TypeError on CLI startup.

## [0.1.2] - 2025-10-28

### Changed

- Rebranded the CLI command prefix from `speckitty` to `spec-kitty`, including package metadata and documentation references.
- Migrated template directories from `.specify` to `.kittify` and feature storage from `/specs` to `/kitty-specs` to avoid namespace conflicts with Spec Kit.
- Updated environment variables, helper scripts, and dashboards to align with the new `.kittify` and `kitty-specs` conventions.

## [0.1.1] - 2025-10-07

### Added

- New `/spec-kitty.accept` command (and `spec-kitty accept`) for feature-level acceptance: validates kanban state, frontmatter metadata, and artifacts; records acceptance metadata in `meta.json`; prints merge/cleanup instructions; and supports PR or local workflows across every agent.
- Acceptance helper scripts (`accept-feature.sh` / `.ps1`) and expanded `tasks_cli` utilities (`status`, `verify`, `accept`) for automation and integration with AI agents.
- Worktree-aware bootstrap workflow now defaults to creating per-feature worktrees, enabling parallel feature development with isolated sandboxes.
- Implementation prompts now require operating inside the feature’s worktree and rely on the lane helper scripts for moves/metadata, eliminating `git mv` conflicts; the dashboard also surfaces active/expected worktree paths.

### Changed

- `/spec-kitty.specify`, `/spec-kitty.plan`, and `/spec-kitty.clarify` now run fully conversational interviews—asking one question at a time, tracking internal coverage without rendering markdown tables, and only proceeding once summaries are confirmed—while continuing to resolve helper scripts via the `.kittify/scripts/...` paths.
- Added proportionality guidance so discovery, planning, and clarification depth scales with feature complexity (e.g., lightweight tic-tac-toe flows vs. an operating system build).
- `/spec-kitty.tasks` now produces both `tasks.md` and the kanban prompt files in one pass; the separate `/spec-kitty.task-prompts` command has been removed.
- Tasks are grouped into at most ten work packages with bundled prompts, reducing file churn and making prompt generation LLM-friendly.
- Both shell and PowerShell feature bootstrap scripts now stop with guidance to return `WAITING_FOR_DISCOVERY_INPUT` when invoked without a confirmed feature description, aligning with the new discovery workflow.

## [0.1.0] - 2025-10-07

### Changed

- `/spec-kitty.specify` and `/spec-kitty.plan` now enforce mandatory discovery interviews, pausing until you answer their question sets before any files are written.
- `/spec-kitty.implement` now enforces the kanban workflow (planned → doing → for_review) with blocking validation, new helper scripts, and a task workflow quick reference.
- Removed the legacy `specify` entrypoint; the CLI is now invoked exclusively via `spec-kitty`.
- Updated installation instructions and scripts to use the new `spec-kitty-cli` package name and command.
- Simplified local template overrides to use the `SPEC_KITTY_TEMPLATE_ROOT` environment variable only.

## [0.0.20] - 2025-10-07

### Changed

- Renamed the primary CLI entrypoint to `spec-kitty` and temporarily exposed a legacy `specify` alias for backwards compatibility.
- Refreshed documentation, scripts, and examples to use the `spec-kitty` command by default.

## [0.0.19] - 2025-10-07

### Changed

- Rebranded the project as Spec Kitty, updating CLI defaults, docs, and scripts while acknowledging the original GitHub Spec Kit lineage.
- Renamed all slash-command prefixes and generated artifact names from `/speckit.*` to `/spec-kitty.*` to match the new branding.

### Added

- Refreshed CLI banner text and tagline to reflect spec-kitty branding.

## [0.0.18] - 2025-10-06

### Added

- Support for using `.` as a shorthand for current directory in `spec-kitty init .` command, equivalent to `--here` flag but more intuitive for users.
- Use the `/spec-kitty.` command prefix to easily discover Spec Kitty-related commands.
- Refactor the prompts and templates to simplify their capabilities and how they are tracked. No more polluting things with tests when they are not needed.
- Ensure that tasks are created per user story (simplifies testing and validation).
- Add support for Visual Studio Code prompt shortcuts and automatic script execution.
- Allow `spec-kitty init` to bootstrap multiple AI assistants in one run (interactive multi-select or comma-separated `--ai` value).
- When running from a local checkout, `spec-kitty init` now copies templates directly instead of downloading release archives, so new commands are immediately available.

### Changed

- All command files now prefixed with `spec-kitty.` (e.g., `spec-kitty.specify.md`, `spec-kitty.plan.md`) for better discoverability and differentiation in IDE/CLI command palettes and file explorers
