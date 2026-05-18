# Slice F — Multi-Context Extensibility + Strategic Remediations

**Mission ID:** `01KRX5C8MQRGG7WJW1YK53DTF5`
**Mission slug:** `slice-f-multi-context-extensibility-01KRX5C8`
**Mid8:** `01KRX5C8`
**Mission type:** `software-dev`
**Planning / merge target:** `feat/org-doctrine-layer` (stacks on Mission B's `feat/org-doctrine-layer`, then a single upstream PR carries the whole charter/doctrine baseline)
**Parent epic:** Priivacy-ai/spec-kitty#1111 — *3.2.0 release work: Charter / Doctrine enhancement and remediation*
**Slice:** F — Multi-context extensibility (doctrine + workflow)
**Predecessor mission:** Mission B (`charter-mediated-doctrine-selection-01KRTZCA`, merged at `4aa6b6f`)

---

## Overview

This mission opens spec-kitty's architecture along three previously-implicit axes that today calcify around the single-project / single-workflow assumption, AND closes a structured set of quality-protecting gaps surfaced by the post-merge architectural review of Mission B. The two halves are bundled deliberately: the remediations each close a failure mode the new Slice F surfaces would multiply, so landing them in the same mission protects Slice F's quality from day one.

The three axes (each from a #1111 child ticket):
1. **Three-layer DRG resolution** (shipped → organisation → project), per #832, builds on Mission B's selection layer (8-kind plural parity, union semantics, mission identity model) and #469 phase-7 schema versioning + provenance (already in `main`).
2. **Cross-repo / monorepo charter visibility**, per #522 + ADR-8 (finalisation), introduces `CharterScope` so per-package or shared-root charter resolution is no longer hardcoded to repo root.
3. **Composable workflow sequencing**, per #682, promotes the mission action sequence (`specify → plan → tasks → implement → review → merge`) from hardcoded constant to a first-class artifact at `src/doctrine/workflows/<id>.workflow.yaml`, parallel to how agent profiles, tactics, and step contracts already work.

The five absorbed remediations (each addresses a finding from the architect-alphonso debrief at `work/remediation-mission-debrief.md`; verbatim extracts are embedded inline below where they encode load-bearing rationale):
1. **DRIFT-1 alias clean removal** — delete `resolve_governance` alias from `src/charter/resolver.py` and `src/charter/__init__.py` exports; tests use canonical `resolve_project_governance`. No `DeprecationWarning`, no sunset docstring (HiC §5a.1).
2. **HIGH-2 ratchet burn-down model** — `tests/architectural/_baselines.yaml` + meta-test that fails on growth, warns on shrinkage; refactor `test_no_dead_modules._ALLOWLIST` into per-category frozensets; concrete Cat-7 shrinkage from 10 → 7 (HiC §5a.2 binding).
3. **MED-3 symbol-level dead-code gate** — extend `test_no_dead_modules` to walk `__all__` declarations; require `__all__` on `src/charter/` and `src/kernel/` modules.
4. **HIGH-1 catalog-miss CLI visibility** — install `logging.captureWarnings(True)` + Rich-aware log handler at CLI bootstrap; subprocess-based test asserts a typo'd charter produces operator-visible stderr.
5. **LOW-3 contract round-trip backstop** — `tests/contract/test_example_round_trip.py` walks `kitty-specs/*/contracts/*.md`, lifts YAML codeblocks tagged with `pydantic_model:` frontmatter, asserts `expect: valid|invalid` matches Pydantic parse outcome.

Explicitly descoped from this mission (each gets a separate disposition; see Constraints C-005, and acceptance criteria AC-12, AC-13):
- **HIGH-3 auth.transport unwired security module** — produce ADR + GitHub ticket only; **no** source-code change. Deletion is Robert's (lead maintainer) call, per HiC §5a.3.
- **HIGH-4 policy.audit unwired compliance module** — separate mission post-Slice F.
- **MED-1 deployed-skill drift** — separate mission.
- **Most of MED-4 orphans** — bundled into Cat-7 shrinkage (WP01) or deferred.

---

## User Scenarios & Testing

### Scenario 1 — Organisation-tier doctrine, primary actor: enterprise spec-kitty operator

**Trigger:** an operator at an organisation that maintains proprietary governance artefacts (custom missions, compliance frameworks, internal artifact kinds) configures `.kittify/config.yaml` to load an org-DRG fragment from a local path, URL, or packaged dependency.

**Happy path:**
- `spec-kitty charter status` reports all three layers (shipped, org, project) and which are present.
- `spec-kitty charter lint` validates shipped + org + project together; reports per-layer issues with named-source provenance (`source: built-in`, `source: org:<pack-name>`, `source: project`).
- `build_charter_context` resolves through all three layers; rendered artifact stanzas carry provenance metadata so an agent prompt can be inspected for which layer contributed each rule.

**Exception path:** the org pack's `local_path` does not exist (operator removed the directory or never fetched it). The runtime hard-fails with a named-source error mirroring Mission B FR-015's missing-pack policy: error message includes the pack name, the configured path, and remediation hint (`spec-kitty doctrine fetch --pack <name>` OR `remove the entry from .kittify/config.yaml`). **No silent fallback.**

**Rule (must always hold):** organisation-tier DRG cannot override `shipped` invariants (the layer rule from Mission A: kernel ← doctrine ← charter ← specify_cli must remain enforced regardless of which org pack is loaded).

### Scenario 2 — Monorepo charter scoping, primary actor: monorepo team lead

**Trigger:** a team operating a monorepo with multiple packages, each with its own charter (`packages/auth/.kittify/charter/charter.md`, `packages/web/.kittify/charter/charter.md`), runs `spec-kitty charter status` from `packages/auth/some/deep/dir/`.

**Happy path:** the command resolves the *nearest enclosing charter* (the `packages/auth/` one) and reports its status. `spec-kitty charter context --action specify` returns governance for that scope. `build_charter_context(repo_root, feature_dir, scope=<resolved>)` plumbs scope through the rendering pipeline.

**Exception path:** the monorepo configuration is malformed (e.g. two `.kittify/charter/` directories at incompatible nesting depths). The runtime reports the conflict explicitly with both paths.

**Rule (must always hold):** single-project repositories (no monorepo configuration) behave identically to today — `CharterScope` defaults resolve to the repo root, and not a single existing test changes behaviour or assertion.

### Scenario 3 — Composable workflow, primary actor: a team with a non-default workflow

**Trigger:** a team whose actual integration flow requires an additional `design-review` step between `plan` and `tasks` authors `src/doctrine/workflows/our-team-design-first.workflow.yaml` declaring the new sequence, then sets `meta.json: {"workflow_id": "our-team-design-first", ...}` on a new mission.

**Happy path:** `spec-kitty next --agent <name> --mission <handle>` returns commands per the new sequence (`specify → plan → design-review → tasks → ...`) without code changes. The action-name → next-step mapping is read from the workflow YAML.

**Exception path:** a mission's `meta.json` references a `workflow_id` that doesn't exist. Hard-fail with the unknown id named and the directory of available workflows hinted.

**Rule (must always hold):** missions without `workflow_id` (every Mission A / B / C-1 etc. mission predating this work) default to `software-dev-default`, which produces a byte-identical sequence to today's hardcoded behaviour.

### Scenario 4 — DRIFT-1 alias removal, primary actor: any future maintainer

**Trigger:** a maintainer reading or extending charter resolver code.

**Happy path:** `from charter import resolve_project_governance` is the only way to invoke project-governance resolution. `from charter import resolve_governance` raises `ImportError` because the symbol has been deleted.

**Rule (must always hold per HiC §5a.1):** no `DeprecationWarning` is emitted because no alias exists — clean removal, not a deprecation grace period.

### Scenario 5 — Catalog-miss visibility, primary actor: spec-kitty operator with a typo'd charter

**Trigger:** an operator declares `selected_styleguides: [caveman-comemnts]` (typo) in the project charter, then runs `spec-kitty agent action implement WP01`.

**Happy path:** the prompt still builds (catalog-miss is non-fatal) BUT the operator sees an explicit warning line on stderr identifying the missing kind+id, the inferred cause (typo / missing / schema_validation_suspected), and a suggestion (closest match: `caveman-comments`). The warning is visible in normal terminal output, not buried under Rich-formatted output or swallowed by an absent log handler.

**Rule (must always hold):** the warning is reachable via at least one of `warnings.warn` OR `_LOGGER.warning` configured through `logging.captureWarnings(True)` + a Rich-aware handler; pytest's warning capture is NOT the only way to see it.

### Scenario 6 — Ratchet honest-baseline enforcement, primary actor: CI

**Trigger:** a contributor adds a new module under `src/charter/` and forgets to wire it into a live caller. They commit and push.

**Happy path:** CI's `test_no_dead_modules` fails because the new module is module-level orphan. The contributor fixes the wiring (preferred) OR adds the module to the appropriate `_ALLOWLIST` category with a justification comment AND increments the corresponding baseline in `tests/architectural/_baselines.yaml`. The baseline edit is reviewable in the PR diff, making allowlist growth visible.

**Rule (must always hold per HiC §5a.2 binding):** allowlist growth is reviewable; allowlist shrinkage warns (informational) but never blocks; per-major-release Cat-7 must shrink by ≥2 entries; target Cat-7 = 0 by 4.0.

---

## Domain Language

(canonical terms; promoted from `candidate` to `canonical` in `glossary/contexts/doctrine.md` as a pre-acceptance gate per C-010)

| Term | Definition | Notes |
|---|---|---|
| Three-layer DRG | The Doctrine Reference Graph resolved by overlaying shipped → organisation → project tiers. The organisation tier is introduced by this mission. | Selection-layer equivalent already canonical from Mission B. |
| Organisation tier (org tier / org pack) | A configured layer of doctrine artefacts between shipped and project, owned by an organisation rather than the spec-kitty project. May be sourced from a local path, URL, or packaged dependency. | Conflict policy mirrors Mission B FR-015 missing-pack hard-fail. |
| CharterScope | The runtime abstraction that resolves "which charter applies to this filesystem path" given a configured monorepo layout. Default = single-project (repo root). | Per #522 / ADR-8. |
| Workflow sequence | The ordered list of actions a mission moves through (today: `specify → plan → tasks → implement → review → merge`). Promoted to a first-class YAML artifact by this mission. | Default: `software-dev-default` (byte-stable with today). |
| Workflow ID | The `meta.json` field that selects which workflow sequence a mission uses. Optional; absence defaults to `software-dev-default`. | Per #682. |
| Ratchet baseline | A per-test entry in `tests/architectural/_baselines.yaml` recording the last-known allowlist size for a mutable architectural ratchet. CI fails on growth above baseline. | New convention. |
| Cat-7 grandfathered orphans | The `test_no_dead_modules._ALLOWLIST` Category 7: modules with zero non-test callers, allowlisted with explicit `TODO(triage):` comments for HiC review. Target = 0 by 4.0. | Currently 10 entries at predecessor HEAD. |
| Symbol-level dead code | A public name (function, class, module-level constant) declared in `__all__` that no other `src/` module imports. Currently invisible to `test_no_dead_modules` (module-level granularity). | New invariant added by this mission. |
| Catalog miss | Renderer state when a charter-selected artifact ID (styleguide, toolguide, etc.) does not resolve to a loaded artifact in any layer. Currently emits a `CharterCatalogMissWarning`. | Canonical from Mission B remediation. |
| `__all__` declaration convention | Modules under `src/charter/` and `src/kernel/` MUST declare `__all__` so the symbol-level dead-code gate can walk them. | New, charter-pinned per C-007. |

---

## Functional Requirements

### Slice F core — Axis 1: Three-layer DRG resolution (#832)

| ID | Description | Status |
|---|---|---|
| FR-001 | The runtime SHALL load and merge organisation-tier DRG fragments between shipped and project layers, producing a single resolved DRG that preserves per-artefact provenance (`source` field on every resolved artifact). | Approved |
| FR-002 | `spec-kitty charter status` SHALL report the presence/absence and freshness of each of the three DRG layers (shipped, organisation, project). | Approved |
| FR-003 | `spec-kitty charter lint` SHALL lint all configured DRG layers in a single invocation; per-layer findings include the layer's source name. | Approved |
| FR-004 | When an organisation pack's configured `local_path` does not exist on disk, the runtime SHALL raise a hard-fail error naming the pack and path, mirroring the Mission B FR-015 missing-pack policy. **No silent fallback.** | Approved |
| FR-005 | Organisation-tier DRG resolution SHALL NOT override the layer-direction invariant from Mission A (`kernel ← doctrine ← charter ← specify_cli`); any org pack that imports across the layer boundary fails to load with a named-violation error. | Approved |
| FR-006 | Operator UX: `spec-kitty doctrine org init` SHALL scaffold a minimal org pack skeleton at the path the operator specifies; `spec-kitty doctrine org validate` SHALL validate an org pack's structure independently of the rest of the system. | Approved |
| FR-007 | `spec-kitty doctor doctrine` SHALL surface org-layer state (configured packs, fetched/missing status, collision warnings) in its Selections section. | Approved |

### Slice F core — Axis 2: Cross-repo / monorepo charter visibility (#522 / ADR-8)

| ID | Description | Status |
|---|---|---|
| FR-008 | `architecture/adrs/<date>-N-monorepo-charter-scope.md` (ADR-8) SHALL land documenting the architectural design for monorepo charter scoping (per-package vs shared-root, configuration hints, conflict policy). | Approved |
| FR-009 | A `CharterScope` abstraction SHALL exist at the charter layer and SHALL resolve "which charter applies to this filesystem path" given a configured monorepo layout. | Approved |
| FR-010 | `build_charter_context(repo_root, feature_dir, scope=...)` SHALL accept an optional `scope` parameter; when not provided, behaviour is byte-identical to today's `build_charter_context(repo_root, feature_dir)`. | Approved |
| FR-011 | Single-project repositories (no monorepo configuration in `.kittify/config.yaml`) SHALL behave identically to today; the existing 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged. | Approved |

### Slice F core — Axis 3: Composable workflow sequencing (#682)

| ID | Description | Status |
|---|---|---|
| FR-012 | Workflow sequence SHALL exist as a first-class artifact at `src/doctrine/workflows/<workflow-id>.workflow.yaml`, parallel to how agent profiles, tactics, and step contracts already work. The schema is validated by a Pydantic model. | Approved |
| FR-013 | A mission's `meta.json` SHALL accept an optional `workflow_id` field. When present, `spec-kitty next` consumes the resolved workflow's action sequence. When absent, the default `software-dev-default` workflow is used. | Approved |
| FR-014 | The `software-dev-default` workflow SHALL produce a byte-identical action sequence to today's hardcoded sequence (`specify → plan → tasks → implement → review → merge`); back-compat is asserted by a contract test. | Approved |
| FR-015 | An unknown `workflow_id` SHALL hard-fail with an error naming the unknown id and the directory of available workflows. **No silent fallback to `software-dev-default`.** | Approved |

### Absorbed remediation — DRIFT-1 alias clean removal

| ID | Description | Status |
|---|---|---|
| FR-100 | The alias `resolve_governance = resolve_project_governance` in `src/charter/resolver.py` SHALL be deleted in this mission (per HiC §5a.1 — clean removal, no `DeprecationWarning`, no sunset docstring). | Approved |
| FR-101 | The `resolve_governance` export from `src/charter/__init__.py` SHALL be removed. | Approved |
| FR-102 | All test fixtures currently importing `resolve_governance` (notably `tests/charter/test_resolver.py:14`) SHALL be migrated to import `resolve_project_governance`. | Approved |
| FR-103 | After deletion, `from charter import resolve_governance` SHALL raise `ImportError`; this is asserted by a regression test. | Approved |

### Absorbed remediation — HIGH-2 ratchet burn-down model

| ID | Description | Status |
|---|---|---|
| FR-110 | `tests/architectural/_baselines.yaml` SHALL exist with per-test baseline sizes for every mutable allowlist. Initial entries: `test_no_dead_modules` (per-category sizes), `test_migration_chain_integrity._KNOWN_LINE_JUMPS`, `test_runtime_charter_doctrine_boundary._BASELINE_ALLOWLIST`, `test_auth_transport_singleton._ALLOWED_DIRECT_HTTPX_FILES`, `test_compat_shims._ADAPTER_FILES`. | Approved |
| FR-111 | `tests/architectural/test_ratchet_baselines.py` SHALL fail when any ratchet's current size exceeds the baseline (growth-fails) and SHALL warn (informational, non-fatal) when the current size is below baseline (shrinkage-encouraging). | Approved |
| FR-112 | `test_no_dead_modules._ALLOWLIST` SHALL be refactored into per-category frozensets (one per documented category from the Process Gap 2 doc) so growth in Cat-7 is distinguishable from growth in auto-discovery categories. | Approved |
| FR-113 | In the same PR that lands FR-110/111/112, Cat-7 SHALL shrink from 10 entries to at most 7 entries; the concrete deletion is `doctrine.templates.repository` (Mission 057's `CentralTemplateRepository`, 3+ years orphaned, no consumer) and at least one of the WIRE-OR-DELETE orphans from the debrief MED-4 table. | Approved |

### Absorbed remediation — MED-3 symbol-level dead-code gate

| ID | Description | Status |
|---|---|---|
| FR-120 | `test_no_dead_modules` SHALL be extended to walk `__all__` declarations: every name in a module's `__all__` MUST appear in another `src/` file's import. | Approved |
| FR-121 | Every module under `src/charter/` and `src/kernel/` SHALL declare `__all__`. This is the only scope of the convention in this mission; expansion to other subpackages is a future-mission concern. | Approved |
| FR-122 | The symbol-level gate SHALL coexist with the existing module-level check; both must pass. | Approved |

### Catalog-miss CLI UX (REFRAMED at WP05 cycle 1 — see RISK-3 misdiagnosis note below)

**Reframing note (2026-05-18, post WP05 cycle-1 review):** the Mission B post-merge review's HIGH-1 finding asserted that catalog-miss warnings were "silently dropped because no log handler installed". WP05's ATDD red→green discipline surfaced that this was a **misdiagnosis**: Python 3.2+'s `logging.lastResort` handler already routes WARNING records to stderr, and Python's warnings machinery writes `warnings.warn(...)` to stderr by default. The warnings WERE visible at the operator surface all along. WP05's bootstrap therefore does NOT "fix RISK-3" — it adds **deterministic Rich-formatted output** (double-space-separated WARNING + colorized when stderr is a TTY) for improved scanability, especially valuable under Slice F's multiplied catalog sources (org-DRG, monorepo, custom workflows). This is a cosmetic-UX improvement, not an architectural fix.

| ID | Description | Status |
|---|---|---|
| FR-130 | The spec-kitty CLI bootstrap SHALL call `logging.captureWarnings(True)` so `warnings.warn(...)` flows through the logging subsystem (enabling the FR-131 handler to format both warning paths uniformly). | Approved |
| FR-131 | The spec-kitty CLI bootstrap SHALL install a Rich-aware `logging.Handler` that routes `WARNING+` log records through Rich's `Console` to the operator's stderr, producing deterministic Rich-formatted output (level prefix + double-space separator + TTY-aware coloring). Both `warnings.warn` and `_LOGGER.warning` paths converge on this single formatted surface. | Approved |
| FR-132 | A subprocess-based test `tests/integration/test_catalog_miss_cli_visibility.py` SHALL run the spec-kitty CLI with a typo'd charter (`selected_styleguides: [does-not-exist]`) and assert the catalog-miss warning appears in captured stderr **in Rich-formatted form specifically** (e.g., assertion targets the double-space separator + level prefix that `RichHandler` uniquely produces — NOT just raw warning text, which Python's defaults would also emit). The test MUST run via subprocess (not pytest's in-process capture) AND its assertion MUST fail at the WP's planning-base commit (proving the bootstrap is load-bearing for the asserted contract). | Approved |

### Absorbed remediation — LOW-3 contract round-trip backstop

| ID | Description | Status |
|---|---|---|
| FR-140 | `tests/contract/test_example_round_trip.py` SHALL walk every `kitty-specs/<mission>/contracts/*.md` file, lift fenced YAML codeblocks tagged with `pydantic_model: <ModuleName.ClassName>` and `expect: valid|invalid` frontmatter, attempt to parse each via the named model, and assert the outcome matches `expect`. | Approved |
| FR-141 | The contract round-trip test SHALL ship with an allowlist of known-bad legacy contracts (from missions predating this convention) that warn rather than fail; the allowlist participates in the FR-110 baseline so it shrinks over time. | Approved |

### Descoped — Auth-transport ADR + ticket (per HiC §5a.3)

| ID | Description | Status |
|---|---|---|
| FR-200 | `architecture/adrs/<date>-N-delete-specify-cli-auth-transport.md` SHALL be created documenting: (a) the dead-code finding (`specify_cli.auth.transport` has zero callers, verified by `rg "from specify_cli.auth.transport" src/specify_cli/` returning 0 matches); (b) the audit evidence (alternate HTTP paths in sync/tracker subsystems, the C4 contradiction with `test_auth_transport_singleton` passing vacuously); (c) the architect's DELETE recommendation; (d) the deferral rationale (auth-caution per HiC §5a.3). The ADR SHALL reserve a "deleted in commit X" field explicitly for Robert (lead maintainer) to fill at execution. | Approved |
| FR-201 | A GitHub ticket SHALL be opened against `Priivacy-ai/spec-kitty` with the same evidence as FR-200, labelled for Robert's queue. The ticket title SHALL make the SaaS auth-caution constraint explicit. | Approved |
| FR-202 | This mission SHALL NOT modify `src/specify_cli/auth/transport.py` or `tests/architectural/test_auth_transport_singleton.py`. Deletion is Robert's call to execute in a separate PR. | Approved |

### Closing

| ID | Description | Status |
|---|---|---|
| FR-300 | `tests/architectural/README.md` SHALL exist, documenting the 5-axis architectural model (Layer direction × Surface completeness × Closed-vocabulary integrity × Lifecycle presence × Dependency hygiene) from the post-merge ratchet coherence audit, and listing every gate with its axis. | Approved |
| FR-301 | The forward-staged migrations convention (chain target may lead `pyproject.toml`; the bump is a separate release step) SHALL be documented in `src/specify_cli/upgrade/migrations/README.md` (preferred per architect's preference) OR in `CLAUDE.md` PyPI Release section. | Approved |
| FR-302 | All Mission C domain-language terms in the §"Domain Language" table SHALL be promoted to `Status: canonical` in `glossary/contexts/doctrine.md`. | Approved |
| FR-303 | The project charter (`.kittify/charter/charter.md`) SHALL be amended to add: (a) the binding burn-down policy (per C-006), (b) the `__all__` declaration convention (per C-007), and (c) the ATDD-first discipline note (per C-011), so future missions inherit the convention. | Approved |
| FR-304 | Every commit landing an ATDD acceptance test SHALL declare in its commit message which user scenario / acceptance criterion the test covers AND record the expected red→green transition (the commit that turns the test green is identified by SHA-or-WP in the implementing WP's frontmatter). | Approved |

---

## Non-Functional Requirements

| ID | Description | Threshold |
|---|---|---|
| NFR-001 | Backward compatibility for single-project repositories: every existing test in `tests/specify_cli/next/test_wp_prompt_governance_contract.py` passes unchanged. | 23/23 pass at mission close (no fixture edits). |
| NFR-002 | Latency budget: `build_charter_context` end-to-end build time (measured by `tests/architectural/test_wp_prompt_build_latency.py`) does not regress more than 20% from the Mission B baseline. | Mean elapsed ≤ 1.2 × baseline; hard cap 8 s (existing budget). |
| NFR-003 | Layer rule preservation: `src/charter/` continues to import nothing from `src/specify_cli/`; the new org-DRG modules, `CharterScope`, and workflow registry all sit in the correct layer per existing `test_layer_rules.py`. | `test_layer_rules.py` 9/9 pass at mission close. |
| NFR-004 | Glossary canonical promotion is a pre-acceptance gate: the validator (`spec-kitty glossary check` or equivalent) passes with zero residual `candidate`-status entries among the terms in §"Domain Language". | Validator exit 0; manual inspection: every domain-language term shows `Status: canonical`. |
| NFR-005 | All new and existing architectural ratchets pass on HEAD at mission close, including the new FR-110/111 meta-test and FR-120/121 symbol-level gate. | `pytest tests/architectural/ -v` exit 0; warnings allowed only for documented patch-skips per the migration chain gate's `_KNOWN_PATCH_SKIPS`. |
| NFR-006 | The catalog-miss visibility test (FR-132) runs via subprocess (`subprocess.run([...])`), not via pytest's in-process warning capture. The assertion targets Rich-specific formatting (level prefix + double-space separator) which the bootstrap's `RichHandler` uniquely produces; raw Python defaults would not match this assertion. This proves the bootstrap is load-bearing (real ATDD red→green per C-011), not merely cosmetic-decoration. | Test calls `subprocess.run` with a real spec-kitty CLI invocation; assertion targets Rich-formatted output bytes; test MUST fail at planning-base commit (proving red→green). |
| NFR-007 | Mission closure is gated on `spec-kitty.analyze` passing with 0 CRITICAL and 0 HIGH findings. MEDIUM findings are reviewed but may be merged with documented follow-up. | Analyze report at `kitty-specs/<mission>/analysis-report.md` shows verdict: READY FOR IMPLEMENTATION at mission close (post all WPs). |
| NFR-008 | ATDD coverage: every user scenario in §"User Scenarios & Testing" (Scenarios 1–6) AND every acceptance criterion that maps to operator-observable behaviour (AC-1, AC-2, AC-3, AC-4, AC-5, AC-7, AC-8, AC-9, AC-10) MUST have at least one failing-first ATDD acceptance test committed BEFORE its implementing WP starts coding. The test must be red on the WP's planning base commit and green on the WP's final commit (red→green transition asserted by the reviewer per the discipline in §"Development Discipline: ATDD-First"). | Coverage tracking spreadsheet at `kitty-specs/<mission>/atdd-coverage.md` (created at plan time) lists every Scenario/AC and the test file that pins it; coverage ≥ 90% of in-scope ACs (the 10% slack handles ACs that are pure-documentation deliverables — AC-12 ADR existence, AC-13 GitHub ticket existence, AC-14 README existence, AC-15 doc presence, AC-16 charter amendment, where existence assertions ARE the ATDD test). |

---

## Constraints

| ID | Description | Source |
|---|---|---|
| C-001 | Layer rule (Mission A): `kernel ← doctrine ← charter ← specify_cli`. No new code in this mission may violate this; the org-DRG loader and CharterScope and workflow registry all live in `src/charter/`. | ADR 2026-03-27-1; pytestarch via `test_layer_rules.py`. |
| C-002 | Forward-only: this mission does not retrofit historical missions to populate `workflow_id` or migrate prior `_BASELINE_ALLOWLIST` decisions. Existing missions continue to work with default behaviour. | Architect preference, debrief §5 Q6 (deferred to Mission C planning, confirmed forward-only here). |
| C-003 | **HiC §5a.1 (binding): DRIFT-1 alias clean removal.** No `DeprecationWarning`, no sunset docstring. Verbatim HiC rationale: *"Do it now, if possible. The 3.2.0 scope will include various changes to the charter/doctrine [layer] already, it seems best to go full monty, rather than leaving confusing paths in place. Our overuse of 'eventual deprecation' and shimming has bit us before, lets avoid that and do the move cleanly. User impact is limited anyway, as most of the internal system is a black-box for them."* | HiC, 2026-05-18. |
| C-004 | **HiC §5a.2 (binding): Burn-down policy is charter-pinned, not advisory.** The four sub-rules (allowlist shrink-only-except-via-documented-exception; Cat-7 shrinks ≥2/major release; pure-shim files target 0 by 4.0; `__all__` required on `src/charter/` + `src/kernel/`) become charter sections in this mission (FR-303). | HiC, 2026-05-18. |
| C-005 | **HiC §5a.3 (binding): HIGH-3 auth.transport descoped — Mission C produces ADR + ticket only.** Verbatim HiC rationale: *"Delete, but explicitly create an ADR for it, which is to be updated mentioning the code that is deleted, and the commit in which it happened. In general: we want to be extremely careful with auth-path cleanup as Robert (lead maintainer) has indicated the SaaS platform has had recent auth-related challenges. It would be best to highlight this, add our research / evidence and recommendations, but leave the decision and clean-up action to Robert. (descope from our proposed mission scope, but create a ticket with our findings)."* No source-code change to `src/specify_cli/auth/transport.py` or `test_auth_transport_singleton.py`. | HiC, 2026-05-18. |
| C-006 | Cat-7 burn-down target trajectory (binding per C-004): each major release shrinks Cat-7 by ≥2 entries. Target: 0 by 4.0. Mission C contributes 10 → 7. | C-004 derivative. |
| C-007 | `__all__` declaration convention (binding per C-004): every module under `src/charter/` and `src/kernel/` MUST declare `__all__`. Modules added by this mission MUST comply; existing modules without `__all__` are migrated as part of FR-121. | C-004 derivative. |
| C-008 | Backward compat for missions without `workflow_id`: the default `software-dev-default` workflow MUST produce a byte-identical action sequence to today's hardcoded behaviour. **No silent semantic drift** between hardcoded and default-via-YAML paths. | FR-014 derivative. |
| C-009 | Org-DRG schema MUST reuse Mission B's 8-kind plural-naming parity and union semantics (DoctrineSelectionConfig.selected_<kind> / OrgCharterPolicy.required_<kind> shapes). Any divergence requires written rationale + glossary update. | Predecessor mission compatibility. |
| C-010 | Glossary canonical promotion is a pre-acceptance gate: all 10 Mission C domain-language terms in §"Domain Language" MUST be promoted from `candidate` to `canonical` BEFORE the mission is accepted. | Architect convention (mirrors Mission B C-007). |
| C-011 | **ATDD-first discipline (binding for this mission):** every implementation WP follows the red-green-refactor cycle. The WP cannot start coding until at least one failing-first ATDD test exists that pins the user-observable behaviour the WP delivers. The ATDD test is committed as a separate commit (often the first commit of the lane) BEFORE any implementation commits in the same lane. The reviewer verifies red→green: the test was red on the WP's `planning_base_branch` commit AND green on the WP's final `for_review` commit. Coverage scope is defined by NFR-008. Refactor steps inside a WP MUST keep the test green. This mirrors Mission B's pattern (where the 7-file ATDD spec at `bd95f1f5` was the canonical executable contract that all implementation WPs turned green). | Mission B precedent; charter amendment per FR-303(c) so future missions inherit. |

---

## Success Criteria

(measurable, technology-agnostic, user-focused)

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | An organisation operator can configure an org pack, run `spec-kitty charter status`, and see all three DRG layers reported with their freshness state in under 2 seconds. | Manual end-to-end fixture test; wall-clock measurement. |
| SC-002 | A monorepo team running `spec-kitty charter status` from any subdirectory of a configured monorepo sees the nearest-enclosing charter reported, with zero ambiguity. | Integration test with two-package fixture monorepo. |
| SC-003 | A team author can add a non-default workflow (e.g. extra `design-review` step), select it in `meta.json`, and `spec-kitty next` honours the new sequence on the very next command, without restarting the session or rebuilding any cache. | Integration test asserting `spec-kitty next` output matches the new sequence. |
| SC-004 | A spec-kitty operator with a typo'd charter sees the catalog-miss warning in **Rich-formatted** terminal output (level prefix + double-space separator + TTY-aware coloring). Python's defaults emit visible-but-plain output regardless; the bootstrap upgrades this to deterministic Rich format for scanability under Slice F's multiplied catalog sources. | Subprocess test (FR-132) with Rich-format-specific assertion. |
| SC-005 | A reviewer evaluating a PR that adds an allowlist entry can see the corresponding `_baselines.yaml` change in the same diff, enabling explicit conversation about whether growth is justified. | Existence of `_baselines.yaml` + meta-test (FR-110/111). |
| SC-006 | A spec-kitty contributor adding a public class to an existing module receives CI failure if they don't add a caller, mirroring the WP08 cycle-1 lesson at sub-module granularity. | Symbol-level dead-code gate (FR-120). |
| SC-007 | An auditor reviewing the spec-kitty test suite can read `tests/architectural/README.md` and understand the 5-axis architectural model in under 10 minutes. | Documentation presence (FR-300). |

---

## Assumptions

1. The `feat/org-doctrine-layer` branch state at mission start (HEAD `b28a13da`, rebased onto `origin/main` post `5d5c0ca1`) is the predecessor baseline. Slice F WPs stack on top; eventual upstream PR merges the whole branch.
2. Mission B's selection-layer parity (8 kinds, plural naming, union semantics) is the contract Slice F's org-DRG must honour. Changes to the kind set would force a separate alignment mission.
3. The org-DRG source mechanism (local path / URL / packaged dependency) defaults to local path in this mission. URL and package sources are deferred to a follow-up mission unless WP06 implementation surfaces them as trivial extensions.
4. No external workflow consumers (out-of-tree) currently exist for the `resolve_governance` alias, per HiC §5a.1 framing ("User impact is limited anyway, as most of the internal system is a black-box for them").
5. The 5 deferred open questions from the debrief (§5 Q4, Q5, Q6, Q7) are confirmed in §"Open Questions" below; the WP-zero plan run re-surfaces them with the planner.
6. Robert's auth-transport audit will happen in a separate PR on Robert's timeline. Mission C ships the ADR + ticket; deletion is not Mission C's responsibility.

---

## Key Entities

(data shapes introduced or extended by this mission; full schemas land in `data-model.md` at plan time)

| Entity | Purpose | Notes |
|---|---|---|
| `OrgDRGFragment` | A loaded organisation-tier DRG fragment with provenance metadata. | New. |
| `OrgDRGConflict` | A typed conflict report between shipped/org/project layers. | New. |
| `CharterScope` | The runtime resolver for "which charter applies to this path" in monorepos. | New per #522 / ADR-8. |
| `WorkflowSequence` | A first-class artifact representing a mission's action sequence. | New per #682. |
| `RatchetBaseline` | A per-test entry in `_baselines.yaml` recording last-known allowlist sizes. | New. |
| `CatalogMissEvent` | Structured-log payload for the FR-131 logging handler when a catalog miss fires. | New (extends existing `CharterCatalogMissWarning`). |
| `MissionTypeProfile` | Existing (Mission B). | Unchanged; referenced for the workflow-vs-mission-type-profile relationship in WP10. |
| `DoctrineSelectionConfig.selected_<kind>` / `OrgCharterPolicy.required_<kind>` | Existing (Mission B). | Unchanged; the org-DRG schema reuses this 8-kind parity per C-009. |

---

## Development Discipline: ATDD-First (Red-Green-Refactor)

This mission adopts **ATDD-first** discipline (binding per C-011). The pattern is the one Mission B successfully ran — the 7-file ATDD spec committed at `bd95f1f5` was the canonical executable contract; each implementation WP was scored by which ATDD assertions it turned green. Mission C scales this pattern across 4 lanes and 12 WPs.

### The cycle

For each user scenario / acceptance criterion in scope (per NFR-008):

1. **RED (test-first).** Author the acceptance test that pins the operator-observable behaviour. Commit it as a separate commit (often the first commit of the lane, or a dedicated ATDD WP at the start of the lane). The test MUST fail on the WP's `planning_base_branch` because the production code doesn't exist yet — that's the contract.
2. **GREEN (minimum code to pass).** The implementing WP writes just enough production code to turn the named test green. No gold-plating; no extra surfaces; no defensive scaffolding for hypothetical future requirements (per the project guideline).
3. **REFACTOR (with the test as safety net).** If the implementation needs cleanup, do it as separate commits within the same WP, re-running the test after each change. The test stays green throughout.

### Lane-level ATDD landing

Each lane lands its ATDD tests in a single early commit (or a single early WP) that the implementation WPs then turn green:

- **Lane A (architectural rigor):** ATDD tests for ratchet baseline (FR-111), symbol-level dead-code (FR-120), contract round-trip (FR-140). Landed at the start of Lane A; the corresponding implementation WPs (WP01, WP02, WP03 per the proposed structure) turn each test green in turn.
- **Lane B (independent remediations):** ATDD tests for alias deletion regression (FR-103) and catalog-miss CLI visibility (FR-132). Landed at the start of Lane B; WP04 turns the alias test green; WP05 turns the visibility test green.
- **Lane C (org-DRG):** ATDD tests for Scenario 1 (org-DRG end-to-end with fixture org pack), FR-002/003/004/005, AC-1. Landed at the start of Lane C; WP06/WP07/WP08 turn each test green in turn.
- **Lane D (monorepo + workflows + closing):** ATDD tests for Scenario 2 (monorepo CharterScope), Scenario 3 (composable workflow), FR-008..015, AC-3, AC-4. Landed at the start of Lane D; WP09/WP10/WP11 turn each test green. WP12 (closing) adds the cross-axis integration tests AND the binding tests for the existence-only ACs (AC-12, AC-13, AC-14, AC-15, AC-16).

### Reviewer obligation

When a WP moves to `for_review`, the reviewer MUST validate the red→green transition:

```bash
# Confirm the test was RED on the WP's planning base:
git checkout <wp.planning_base_branch>
pytest <test_path>::<test_name>  # MUST FAIL

# Confirm the test is GREEN on the WP's final commit:
git checkout <wp_branch>
pytest <test_path>::<test_name>  # MUST PASS
```

If the test was already green on the planning base (no red phase), the WP did not follow ATDD discipline — the reviewer rejects with feedback to either rebase the WP onto a commit predating the test OR demonstrate the test exercises new production code paths.

### Coverage tracking

A coverage spreadsheet at `kitty-specs/<mission>/atdd-coverage.md` (authored at `/spec-kitty.plan` time) lists every in-scope Scenario / AC and the test file + test name that pins it. The planner populates the spreadsheet from the FR/Scenario/AC tables; each row gets filled in as WPs land. NFR-008's threshold is ≥ 90% in-scope ACs covered (the 10% slack covers documentation-only deliverables — AC-12 ADR existence, AC-13 GitHub ticket existence, AC-14 README existence, AC-15 doc presence, AC-16 charter amendment — where the existence assertion IS the ATDD test).

### Out of scope for ATDD

The following deliverables are NOT subject to red→green discipline (they ship a pure-documentation artefact whose existence is the test):

- AC-12 (ADR-N-delete-auth-transport.md exists)
- AC-13 (GitHub ticket open)
- AC-14 (tests/architectural/README.md documents 5-axis model)
- AC-15 (forward-staged migrations convention documented)
- AC-16 (charter amendments)

For these, the WP's review confirms the file/issue exists with the required content; no failing-first phase applies.

### Why this matters here

Mission B taught two lessons that this discipline directly addresses:
- **WP08 cycle-1 dead code** (zero live callers despite 14 passing tests) — caught only when the cycle-1 reviewer explicitly grepped. ATDD-first plus red→green verification would have caught it at cycle-1 dispatch because the integration test (which a reviewer can re-run) would have been already-green on the planning base.
- **WP01 singular/plural drift** (contract example contradicted implementation) — caught only when WP05's implementer read the contract independently. An ATDD test asserting the contract example parses cleanly would have failed at WP01 dispatch.

Both classes of failure recur where there's no failing-first executable spec to validate the WP's contract.

---

## Open Questions

(deferred from architect-alphonso debrief §5; to be re-surfaced at `/spec-kitty.plan` time)

1. **Q4 — Skill deployment ownership** (debrief §5): does Mission C take responsibility for redeploying skills to `~/.claude/skills/`, or limit to surfacing drift? — Architect's preference: surface, don't overwrite. Bundled with the deferred "operator-surface hygiene" mission (per descoping); Mission C does NOT do this.
2. **Q5 — Glossary orphans #8 + #9 WIRE-or-DELETE** (debrief §5): `specify_cli.glossary.prompts` and `specify_cli.glossary.rendering` — wire into glossary conflict resolution, or delete? — Deferred to triage mission per descoping; one of these MAY be the FR-113 Cat-7 reduction candidate (architect's call at planning time).
3. **Q6 — Forward-only scope for WP06 (now org-DRG WP)**: should the org-DRG schema retrofit historical risk decisions? — Architect's preference: forward-only (C-002).
4. **Q7 — Forward-staging convention destination**: lands in `CLAUDE.md` PyPI Release section OR `src/specify_cli/upgrade/migrations/README.md`? — Architect's preference: migrations README (FR-301 default).
5. **NEW — Org-DRG source mechanism prioritisation**: this mission ships local-path support; URL and packaged-dependency support are gated on WP06 implementation review.
6. **NEW — Workflow back-compat default permanence**: pre-`workflow_id` missions default to `software-dev-default` indefinitely, or does the default deprecate after one minor (parallel to the C-003 "no eventual deprecation" stance)? Architect's preference: permanent default — workflow_id is opt-in, not migration-required.

---

## Acceptance Criteria (binding, gate for mission close)

When this mission ships, the following MUST hold. Each criterion maps to one or more FRs/NFRs/Cs above.

| AC | Criterion | Covers |
|---|---|---|
| AC-1 | Three-layer DRG operational end-to-end: an org-configured DRG fragment merges with shipped and project layers; `charter lint` lints all three; `build_charter_context` resolves through all three with provenance. | FR-001–005 |
| AC-2 | Org-pack operator UX shipped: `doctrine org init` scaffolds; `doctrine org validate` validates; `doctor doctrine` surfaces org state. | FR-006, FR-007 |
| AC-3 | ADR-8 lands and a `CharterScope` abstraction exists; single-project repos behave identically (NFR-001); monorepo configuration unblocks per-package scoping. | FR-008–011, NFR-001 |
| AC-4 | Workflow sequences are first-class: at least one non-default workflow YAML exists (test fixture), and a fixture mission using it produces a `spec-kitty next` flow that differs from default at the documented step. | FR-012–015 |
| AC-5 | `resolve_governance` alias is DELETED. `from charter import resolve_governance` raises `ImportError`; all test fixtures import the canonical name. | FR-100–103, C-003 |
| AC-6 | `tests/architectural/_baselines.yaml` exists with per-category baselines for every mutable allowlist; `test_ratchet_baselines.py` fails on growth, warns on shrinkage. | FR-110–112, C-004, C-006 |
| AC-7 | `test_no_dead_modules._ALLOWLIST` Category 7 is at most 7 entries (down from 10). Concrete shrinkage proves the burn-down model works in the same PR. | FR-113, C-006 |
| AC-8 | Symbol-level dead-code gate (`__all__` walk) passes; every `src/charter/` and `src/kernel/` module declares `__all__`. | FR-120–122, C-007 |
| AC-9 | `tests/integration/test_catalog_miss_cli_visibility.py` exists and passes; a subprocess CLI run with a typo'd charter produces operator-visible warning output. | FR-130–132, NFR-006 |
| AC-10 | `tests/contract/test_example_round_trip.py` exists and passes against all current `kitty-specs/*/contracts/*.md` examples (with documented allowlist for legacy contracts per FR-141). | FR-140, FR-141 |
| AC-11 | All 10 Mission C domain-language terms are promoted from `candidate` to `canonical` in `glossary/contexts/doctrine.md`. | FR-302, C-010, NFR-004 |
| AC-12 | `architecture/adrs/<date>-N-delete-specify-cli-auth-transport.md` exists documenting the dead-code finding, audit evidence, DELETE recommendation, and deferral rationale (auth-caution per HiC §5a.3). The ADR reserves a "deleted in commit X" field for Robert. | FR-200, C-005 |
| AC-13 | A GitHub ticket is open against `Priivacy-ai/spec-kitty` with the same evidence, labelled for Robert's queue. **No source code change** to `src/specify_cli/auth/transport.py` in this mission. | FR-201, FR-202, C-005 |
| AC-14 | `tests/architectural/README.md` documents the 5-axis architectural model and lists every gate with its axis. | FR-300 |
| AC-15 | Forward-staged migrations convention documented (either `src/specify_cli/upgrade/migrations/README.md` or `CLAUDE.md` PyPI Release section). | FR-301 |
| AC-16 | Project charter (`.kittify/charter/charter.md`) amended with binding burn-down policy and `__all__` declaration convention. | FR-303, C-004, C-006, C-007 |
| AC-17 | Pre-existing 23 `test_wp_prompt_governance_contract.py` pass unchanged; latency NFR-002 passes; layer rules NFR-003 passes; full architectural sweep NFR-005 passes. | NFR-001, NFR-002, NFR-003, NFR-005 |
| AC-18 | `/spec-kitty.analyze` report at mission close shows verdict READY FOR IMPLEMENTATION with 0 CRITICAL and 0 HIGH findings. | NFR-007 |

---

## Verbatim references (architect-alphonso, post-merge architectural review of Mission B at HEAD `6ae8d449`)

The following extracts are embedded verbatim because they encode load-bearing rationale that informs the absorbed remediations above. The `work/` directory is gitignored; these extracts are reproduced inline so this spec is self-contained.

### From `work/remediation-mission-debrief.md` §2 HIGH-1 (catalog-miss visibility)

> The structured `_LOGGER.warning(...)` is silently dropped under normal CLI invocation because the spec-kitty CLI installs **no log handler**. Verified at HEAD: `rg "logging.captureWarnings|logging.basicConfig|configure_logging|setup_logging" src/specify_cli/` returns **0 matches**. Python's default Warning filter is `default` (one warning per location), so a charter with 5 typo'd IDs surfaces each warning exactly once per process — and only if the operator's stderr isn't being suppressed or interleaved with Rich-managed output.

### From `work/remediation-mission-debrief.md` §2 HIGH-2 (ratchet burn-down)

> Five architectural ratchets carry mutable allowlists:
> - `test_no_dead_modules._ALLOWLIST` (101 entries, Cat 7 = 10 grandfathered orphans).
> - `test_migration_chain_integrity._KNOWN_LINE_JUMPS` (4 entries).
> - `test_runtime_charter_doctrine_boundary._BASELINE_ALLOWLIST` (0 entries today, capped at 2 by C-004).
> - `test_auth_transport_singleton._ALLOWED_DIRECT_HTTPX_FILES` (2 entries).
> - `test_compat_shims._ADAPTER_FILES` (3 entries — pure shims).
>
> None has a CI-enforced monotonic-shrinkage rule.

### From `work/ratchet-coherence-audit.md` §4 Gap-A6 (proposed remediation pattern)

> requires either a checked-in baseline file with last-known sizes, or a `git log`-driven "size at $main" comparator. The cleanest fix is the baseline file: `tests/architectural/_baselines.yaml` with `{test_no_dead_modules: 101, test_runtime_charter_doctrine_boundary: 0, ...}`; a meta-test asserts current ≤ baseline. PRs that legitimately grow must edit the baseline, which makes growth reviewable.

### From `work/remediation-mission-debrief.md` §2 MED-3 (symbol-level dead code)

> `test_no_dead_modules` (lines 273-485 of the implementation) scans at file-level: a module passes if ANY OTHER `src/` file imports ANY name from it. A subtler failure mode — a live module exposing a public class with zero callers — is invisible. ... Walk `__all__` if declared, and assert every name in `__all__` appears in another file's import.

### From `work/ratchet-coherence-audit.md` §3 (the 5-axis architectural model)

> The five axes are **orthogonal and complete**. Reading the gates collectively gives a faithful one-page architecture description:
>
> > *spec-kitty is a strictly layered system (kernel ← doctrine ← charter ← specify_cli) with mediated boundaries (charter mediates doctrine access; auth.transport mediates HTTP; emitter-adapter mediates cross-cutting events). Surfaces declared as facades or schemas must match implementation reality (parity). Operator-authored vocabularies are closed and SSOT-pinned. Every shipped module has a runtime caller; every released version has a migration path. Dependency manifests are exact and exclude retired packages. Process artifacts (markers, safety, compat shims) follow uniform conventions.*

### HiC adjudication record (2026-05-18)

> **§5a.1 — DRIFT-1 alias sunset:** "Do it now, if possible. The 3.2.0 scope will include various changes to the charter/doctrine seems already, it seems best to go full monty, rather than leaving confusing paths in place. Our overuse of 'eventual deprecation' and shimming has bit us before, lets avoid that and do the move cleanly. User impact is limited anyway, as most of the internal system is a black-box for them."
>
> **§5a.2 — Mission C burn-down targets:** "binding" — burn-down policies become charter rules, not advisory notes.
>
> **§5a.3 — HIGH-3 auth.transport:** "Delete, but explicitly create an ADR for it, which is to be updated mentioning the code that is deleted, and the commit in which it happened. In general we want to be extremely careful with auth-path cleanup as Robert (lead maintainer) has indicated the SaaS platform has had recent auth-related challenges. It would be best to highlight this, add our research / evidence and recommendations, but leave the decision and clean-up action to Robert. (descope from our proposed mission scope, but create a ticket with our findings)."

---

## Decision Markers

(none — all decisions confirmed in advance via HiC adjudication at 2026-05-18; if planning surfaces deferred decisions, they will be added here per the Decision Moment Protocol.)
