# Implementation Plan — Slice F: Multi-Context Extensibility + Strategic Remediations

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Mission ID: `01KRX5C8MQRGG7WJW1YK53DTF5`
> Spec: [spec.md](spec.md) | Data model: [data-model.md](data-model.md) | Contracts: [contracts/](contracts/) | ATDD coverage: [atdd-coverage.md](atdd-coverage.md) | Quickstart: [quickstart.md](quickstart.md)
> Branch: `feat/org-doctrine-layer` → `feat/org-doctrine-layer` (stacks on Mission B at `4aa6b6f`; a single upstream PR carries the whole charter/doctrine baseline)
> Mission type: software-dev
> Predecessor: `charter-mediated-doctrine-selection-01KRTZCA` (Mission B)

---

## Summary

Slice F opens spec-kitty's architecture along three axes — three-layer DRG resolution (shipped → organisation → project), monorepo charter scoping (`CharterScope`), and composable workflow sequencing — and lands five absorbed remediations the post-Mission-B architectural review surfaced (DRIFT-1 alias clean removal, ratchet burn-down model, symbol-level dead-code gate, catalog-miss CLI visibility, contract round-trip backstop). Bundling the remediations protects the new surfaces from day-one quality regression. Auth-transport cleanup is descoped to the lead maintainer per HiC §5a.3; this mission produces only the ADR + ticket.

The mission decomposes into **12 WPs across 4 lanes** with **ATDD-first discipline (C-011, NFR-008)**: each lane opens with a failing-first WP that lands the canonical executable contract; subsequent WPs in the lane turn those tests green. Lane A blocks Lane C/D so new modules cannot grandfather themselves into the burn-down baseline (RR-1).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: ruamel.yaml (frontmatter parsing), pydantic v2 (selection + DRG + workflow schemas), typer (CLI surfaces), rich (operator output + the new Rich-aware log handler), pytest (architectural + integration + contract tests), packaging (semver comparisons used in `test_migration_chain_integrity`)
**Storage**: Filesystem only — YAML for selection / org-DRG / workflow artifacts (extending the existing `.kittify/doctrine/` and `src/doctrine/` trees); JSONL for the lane event log (untouched); a new YAML at `tests/architectural/_baselines.yaml`
**Testing**: pytest with the **ATDD-first discipline (C-011)** — the WP cannot start coding until at least one failing-first acceptance test exists that pins the user-observable behaviour the WP delivers. The reviewer enforces red→green per the protocol in spec §"Development Discipline: ATDD-First".
**Target Platform**: cross-platform CLI (Linux, macOS, Windows 10+) — no change from baseline.
**Project Type**: single project (CLI + supporting libraries under `src/`).
**Performance Goals**: NFR-002 inherited — `build_charter_context` end-to-end ≤ 1.2× Mission B baseline; hard cap 8 s (existing budget pinned by `tests/architectural/test_wp_prompt_build_latency.py`).
**Constraints**: NFR-001 (23/23 governance-contract fixtures unchanged), NFR-003 (layer rules unaltered), NFR-005 (full architectural sweep green), NFR-006 (subprocess test for catalog-miss visibility), NFR-007 (`/spec-kitty.analyze` 0 CRITICAL / 0 HIGH at mission close).
**Scale/Scope**: ~25 source files touched across `src/charter/`, `src/specify_cli/cli/commands/`, `src/specify_cli/next/`, `src/specify_cli/__main__.py`, plus ~10 new test files, 1 ADR, 1 GitHub ticket, and 4 charter / README / migrations-README amendments.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Project charter principles ([`.kittify/charter/charter.md`](../../.kittify/charter/charter.md)) and Slice F compliance:

| Charter principle | Slice F position | Status |
|---|---|---|
| **Python 3.11+, ruamel.yaml, pydantic, typer, rich, pytest, mypy --strict** | All Slice F modules conform; new workflow / DRG schemas are pydantic v2; new CLI surfaces are typer subcommands; new log handler routes through the existing Rich Console | ✅ |
| **90%+ test coverage, mypy --strict, integration tests for CLI, unit tests for core logic** | Every new module + CLI surface ships with unit + integration coverage. The ATDD-first discipline (C-011) forces test-before-code, which structurally produces tests; coverage is asserted at mission close (NFR-008) | ✅ |
| **CLI operations < 2 s for typical projects** | New org-DRG load adds bounded I/O (one YAML per layer); CharterScope resolution is O(depth) up the path tree (≤ ~5 segments in practice); workflow registry is a one-shot YAML load. Latency NFR-002 caps regression at 20% | ✅ |
| **Cross-platform** | All new paths use `pathlib.Path`; subprocess test (FR-132) uses `sys.executable -m specify_cli` to stay portable | ✅ |
| **Shared-package boundary (events / tracker external; runtime CLI-internal)** | Slice F touches only `src/charter/`, `src/specify_cli/cli/`, `src/specify_cli/next/_internal_runtime/`, and tests. No new external deps; `pyproject.toml` shape unchanged | ✅ |
| **Internal runtime boundary (CLI does not depend on `spec-kitty-runtime`)** | Workflow registry lives in `src/specify_cli/next/_internal_runtime/workflow_registry.py`. No re-introduction of standalone runtime package | ✅ |
| **Layer rule (`kernel ← doctrine ← charter ← specify_cli`)** | Org-DRG loader lives in `src/charter/drg.py` extensions; CharterScope lives in `src/charter/scope.py`; workflow registry lives in `src/specify_cli/next/_internal_runtime/` (correct layer — runtime is the right home for runtime sequencing). All consumers route through the existing facade or via `specify_cli.next` (no `from doctrine.*` direct from runtime) — pinned by `test_runtime_charter_doctrine_boundary.py` (C-001, NFR-003) | ✅ |
| **Branch-and-release strategy (3.x active on main; feat branches stack)** | Slice F stacks on `feat/org-doctrine-layer` per Mission B precedent; eventual upstream PR carries the whole baseline | ✅ |
| **Auth-caution (Robert / SaaS lead maintainer)** | HiC §5a.3 honoured — auth-transport is descoped to ADR + ticket only; no source change. C-005 binds | ✅ |
| **New charter amendments (added by THIS mission per FR-303)** | (a) Burn-down policy (per C-004/C-006), (b) `__all__` declaration convention (per C-007), (c) ATDD-first discipline note (per C-011). All three land in WP12 after the load-bearing work proves the conventions are honest | ✅ (charter is the inheritor, not the gate, here) |

No charter violations. The Charter Check passes without complexity-tracking entries.

## Project Structure

```
kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/
├── spec.md                  # source of truth
├── plan.md                  # THIS file
├── research.md              # see also work/ratchet-coherence-audit.md (gitignored) for the 5-axis model
├── data-model.md            # new data shapes
├── quickstart.md            # 3-recipe operator quickstart
├── contracts/               # 6 contract files (see Phase 1 below)
│   ├── org-drg-schema.md
│   ├── charter-scope-resolution.md
│   ├── workflow-sequence-schema.md
│   ├── ratchet-baseline-format.md
│   ├── catalog-miss-cli-visibility.md
│   └── contract-round-trip-frontmatter.md
├── atdd-coverage.md         # canonical executable contract
├── decisions/               # Decision-Moment artifacts (DM-01KRX6N0YAFBY7MTJC0CN3D3E4 already in place)
└── tasks.md / tasks/        # written by /spec-kitty.tasks
```

### Source-code surfaces touched

```
src/charter/
├── drg.py                              # EXTEND — org-layer fragment loader, merge, conflict reporting
├── scope.py                            # NEW — CharterScope abstraction (FR-009)
├── context.py                          # EXTEND — accept scope= param (FR-010); thread per-layer provenance
├── resolver.py                         # EDIT — DELETE the resolve_governance alias (FR-100/C-003)
├── __init__.py                         # EDIT — remove resolve_governance from exports (FR-101)
├── activations.py / *.py               # EXTEND — declare __all__ across every src/charter/ module (FR-121/C-007)
└── _catalog_miss.py                    # NO CHANGE (logging surface already in place; visibility lands at CLI bootstrap)

src/kernel/
└── *.py                                # EXTEND — declare __all__ across every src/kernel/ module (FR-121/C-007)

src/doctrine/workflows/                 # NEW DIRECTORY (FR-012)
├── software-dev-default.workflow.yaml  # byte-stable today's hardcoded sequence (FR-014/C-008)
└── _fixtures/                          # test fixture workflow (e.g. our-team-design-first.workflow.yaml)

src/specify_cli/__main__.py             # EXTEND — install logging.captureWarnings(True) + Rich-aware handler (FR-130/FR-131)
src/specify_cli/cli/commands/
├── doctrine.py                         # EXTEND — `doctrine org init`, `doctrine org validate` (FR-006)
├── doctor.py                           # EXTEND — surface org-DRG layer state (FR-007)
└── ...                                 # no other CLI subcommands altered

src/specify_cli/next/_internal_runtime/
├── workflow_registry.py                # NEW — load + cache workflow YAMLs (FR-012, FR-015)
├── workflow_schema.py                  # NEW — pydantic WorkflowSequence + ActionStep models
└── planner.py                          # EXTEND — consume workflow_id from meta.json (FR-013)

src/specify_cli/next/prompt_builder.py  # EXTEND — pass scope= through build_charter_context call (FR-010)

src/specify_cli/glossary/
├── prompts.py                          # DELETE (Q5 / DM-01KRX6N0YAFBY7MTJC0CN3D3E4)
└── rendering.py                        # DELETE (Q5 / DM-01KRX6N0YAFBY7MTJC0CN3D3E4)

src/doctrine/templates/repository.py    # DELETE — CentralTemplateRepository, never wired (FR-113)
```

### Test surfaces added or extended

```
tests/architectural/
├── _baselines.yaml                     # NEW — per-test, per-category ratchet baselines (FR-110)
├── test_ratchet_baselines.py           # NEW — meta-test: fail on growth, warn on shrinkage (FR-111)
├── test_no_dead_modules.py             # REFACTOR — per-category frozensets (FR-112); Cat-7 shrinks 10 → 7 (FR-113)
├── test_no_dead_symbols.py             # NEW or extend — __all__ walk (FR-120)
├── test_all_declarations_required.py   # NEW — every src/charter/* and src/kernel/* declares __all__ (FR-121)
└── README.md                           # NEW — 5-axis architectural model (FR-300)

tests/contract/
└── test_example_round_trip.py          # NEW — frontmatter walker over kitty-specs/*/contracts/*.md (FR-140, FR-141)

tests/integration/
├── test_catalog_miss_cli_visibility.py # NEW — subprocess test for FR-132 (NFR-006)
├── test_three_layer_drg_end_to_end.py  # NEW — Scenario 1 ATDD (FR-001 ... FR-005)
├── test_monorepo_charter_scope.py      # NEW — Scenario 2 ATDD (FR-008 ... FR-011)
└── test_workflow_sequence_runtime.py   # NEW — Scenario 3 ATDD (FR-012 ... FR-015)

tests/charter/
├── test_resolver.py                    # EDIT — migrate to canonical resolve_project_governance (FR-102)
├── test_alias_deleted_regression.py    # NEW — ImportError assertion (FR-103)
├── test_org_drg_loader.py              # NEW — org-DRG schema + merge + provenance unit tests
└── test_charter_scope.py               # NEW — CharterScope unit tests (single-project + monorepo fixtures)

tests/specify_cli/next/
└── test_workflow_registry.py           # NEW — workflow YAML load + unknown-id hard-fail (FR-015)
```

**Structure Decision**: Slice F preserves the existing single-project layout. New modules slot into established subpackages (`charter/`, `next/_internal_runtime/`, `cli/commands/`); the only new directory is `src/doctrine/workflows/` for the workflow sequence artifacts and `tests/architectural/_baselines.yaml`.

---

## 1. Architectural Design

### 1.1 Axis 1 — Three-layer DRG resolution (FR-001 .. FR-007)

Mission B added the **selection** layer of three-layer governance (the `selected_<kind>` / `required_<kind>` parity, the activation registry, mission-type profiles). Slice F adds the **DRG** layer — the graph of doctrine relationships overlaid as shipped → org → project.

- **Loader.** `src/charter/drg.py` gains an `OrgDRGFragment` loader (`load_org_drg(repo_root) -> list[OrgDRGFragment]`) that resolves each configured org pack's DRG-fragment YAML (`<pack>/drg/fragment.yaml`) into a typed structure with provenance.
- **Merge.** A new `merge_three_layers(shipped, org_fragments, project) -> DRGGraph` overlays the layers in order. Org fragments can ADD edges and nodes; they CANNOT override shipped invariants. Conflicting overrides produce an `OrgDRGConflict` and hard-fail per FR-004.
- **Provenance.** Every resolved node and edge carries a `source` field (`built-in`, `org:<pack-name>`, `project`). The renderer in `charter/context.py` threads provenance into the prompt body so the operator-visible stanzas can be inspected for which layer contributed each rule (Scenario 1 happy path).
- **Validator extension.** `spec-kitty charter lint` invokes the three-layer loader; per-layer findings include the named source (FR-003).
- **Layer rule preservation (NFR-003).** Org-DRG loaders live under `src/charter/`; they import doctrine surfaces directly (charter is allowed). The layer invariant `kernel ← doctrine ← charter ← specify_cli` is unaltered.

### 1.2 Axis 2 — Cross-repo / monorepo charter scoping (FR-008 .. FR-011)

`CharterScope` is the runtime resolver for "which charter applies to this filesystem path".

- **Default (single-project).** `CharterScope.default(repo_root)` resolves to the repo root; behaviour byte-identical to today (NFR-001 — the 23 governance-contract fixtures pass unchanged).
- **Monorepo mode.** When `.kittify/config.yaml` declares a `charter_scopes:` list (e.g. `[{root: "packages/auth"}, {root: "packages/web"}]`), `CharterScope.resolve(feature_dir)` walks upward from `feature_dir` and returns the nearest enclosing charter root. Conflicting nested charters raise `CharterScopeConflict` (Scenario 2 exception path).
- **API extension.** `build_charter_context(repo_root, feature_dir, scope=None)` accepts an optional `scope`. When `None` (default), behaviour is byte-identical to today's `build_charter_context(repo_root, feature_dir)` — this is the NFR-001 contract.
- **ADR-8.** `architecture/adrs/2026-05-18-1-monorepo-charter-scope.md` documents the design (FR-008). The current spec already declares the architectural intent; ADR-8 is the finalised, project-ratified version.

### 1.3 Axis 3 — Composable workflow sequencing (FR-012 .. FR-015)

The mission action sequence (`specify → plan → tasks → implement → review → merge`) is today hardcoded inside `prompt_builder.py` / `_internal_runtime/planner.py`. Slice F promotes it to a first-class artifact.

- **Artifact.** `src/doctrine/workflows/<id>.workflow.yaml` — pydantic-validated, declares `workflow_id`, `description`, an `actions: list[ActionStep]` graph with `next: list[str]` edges, and a `version`. Default workflow lives at `src/doctrine/workflows/software-dev-default.workflow.yaml`.
- **Selection.** A mission's `meta.json` accepts an optional `workflow_id: str | None`. `None` (default) resolves to `software-dev-default`. The selection is **opt-in, not migration-required** (NEW-2 resolution).
- **Registry.** `src/specify_cli/next/_internal_runtime/workflow_registry.py` exposes `get_workflow(workflow_id) -> WorkflowSequence`. Unknown IDs hard-fail (FR-015 — no silent fallback).
- **Byte-stability (C-008).** `software-dev-default` produces a byte-identical action sequence to today's hardcoded behaviour. Pinned by a contract test that asserts: for every `(current_action, next_action)` pair the hardcoded sequence produced, the loaded default workflow produces the same pair.
- **Runtime integration.** `prompt_builder.build_prompt` and `_internal_runtime/planner.plan_next` look up the workflow once at mission start (cached per mission run) and resolve the next action from the workflow's action graph rather than the hardcoded sequence.

### 1.4 Remediation 1 — DRIFT-1 alias clean removal (FR-100 .. FR-103, C-003)

Per **HiC §5a.1 (binding)** — clean removal, no `DeprecationWarning`, no sunset docstring.

- Delete `resolve_governance = resolve_project_governance` and its module-level docstring at `src/charter/resolver.py:325-326`.
- Remove `resolve_governance` from both the `from .resolver import (...)` block (line 73) and the `__all__` list (line 124) in `src/charter/__init__.py`.
- Update `tests/charter/test_resolver.py` (and any other test fixture using the legacy name — `rg "resolve_governance" tests/` will enumerate them; the audit identified `tests/charter/test_resolver.py:14`).
- Land regression test `tests/charter/test_alias_deleted_regression.py` asserting `from charter import resolve_governance` raises `ImportError`.

The architect's full-monty rationale (HiC verbatim in C-003): preventing "confusing paths in place". User impact is structurally limited (Assumption 4).

### 1.5 Remediation 2 — Ratchet burn-down model (FR-110 .. FR-113, C-004/C-006)

Per **HiC §5a.2 (binding)** — burn-down policies are charter-pinned, not advisory.

- **`tests/architectural/_baselines.yaml`.** Per-test, per-category baselines for every mutable allowlist (see [`contracts/ratchet-baseline-format.md`](contracts/ratchet-baseline-format.md)).
- **`tests/architectural/test_ratchet_baselines.py`.** Meta-test: imports each gated test module, inspects allowlist size, compares against the baseline. **FAIL** on growth; **WARN** (informational, non-fatal) on shrinkage so the baseline gets edited downward in the same PR.
- **`test_no_dead_modules._ALLOWLIST` refactor.** Today's monolithic 101-entry frozenset breaks into per-category frozensets (one per documented category 1-7); the meta-test tracks Cat-7 separately so an auto-discovered migration in Cat-1 cannot disguise a Cat-7 regression.
- **Cat-7 shrinkage 10 → 7.** Three concrete deletions in the same PR:
  1. `doctrine.templates.repository` — Mission 057's `CentralTemplateRepository`, 3+ years orphaned, no consumer (architect's DELETE recommendation in MED-4 #1).
  2. `specify_cli.glossary.prompts` — 3+ years orphaned (Q5 / [DM-01KRX6N0YAFBY7MTJC0CN3D3E4](decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md)).
  3. `specify_cli.glossary.rendering` — same disposition.

### 1.6 Remediation 3 — Symbol-level dead-code gate (FR-120 .. FR-122, C-007)

- Extend `test_no_dead_modules` (or ship sibling `test_no_dead_symbols.py`) to walk every name declared in `__all__` and assert at least one `from <module> import <name>` site exists somewhere in `src/`.
- Require `__all__` on every module under `src/charter/` and `src/kernel/`. The new gate `test_all_declarations_required.py` walks both subpackages and asserts the declaration is present.
- Coexist with the module-level check; both must pass (FR-122).

### 1.7 Remediation 4 — Catalog-miss CLI visibility (FR-130 .. FR-132, NFR-006)

The structured `_LOGGER.warning(...)` path in `charter._catalog_miss` is silently dropped today because the CLI installs no log handler (architect's HEAD-verified finding HIGH-1).

- **Bootstrap.** `src/specify_cli/__main__.py` (or the typer app's startup hook) calls `logging.captureWarnings(True)` so `warnings.warn(...)` reaches the logging subsystem (FR-130).
- **Handler.** A Rich-aware `logging.Handler` routes `WARNING+` records through the existing Rich `Console` instance to the operator's stderr (FR-131). Per RR-6, the handler defers to the existing Console rather than instantiating a new one — no Rich double-init.
- **Subprocess test.** `tests/integration/test_catalog_miss_cli_visibility.py` runs the spec-kitty CLI via `subprocess.run` with a typo'd charter (`selected_styleguides: [does-not-exist]`) and asserts the catalog-miss warning text appears in captured stderr. The subprocess requirement (NFR-006) proves visibility under real operator conditions — pytest's in-process warning capture does not.

### 1.8 Remediation 5 — Contract round-trip backstop (FR-140 .. FR-141)

- `tests/contract/test_example_round_trip.py` walks every `kitty-specs/<mission>/contracts/*.md`, lifts fenced YAML codeblocks whose frontmatter carries `pydantic_model: <ModuleName.ClassName>` and `expect: valid|invalid`, imports the named model, attempts `model_validate(yaml.safe_load(...))`, and asserts the outcome matches `expect` (see [`contracts/contract-round-trip-frontmatter.md`](contracts/contract-round-trip-frontmatter.md)).
- Legacy contracts (missions predating the convention) participate via an allowlist in `tests/architectural/_baselines.yaml`: they warn instead of fail. The allowlist size is a ratchet that shrinks over time (FR-141).

### 1.9 Descoped — Auth-transport ADR + ticket (FR-200 .. FR-202, C-005)

Per **HiC §5a.3 (binding)** — descoped. Mission C produces:

- `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` documenting the dead-code finding (zero callers verified at `6ae8d449`), the audit evidence, the DELETE recommendation, and the deferral rationale. The ADR reserves a "deleted in commit X" field for Robert to fill.
- A GitHub ticket against `Priivacy-ai/spec-kitty` with the same evidence, labelled for Robert's queue. Title makes the SaaS auth-caution constraint explicit.

**NO source change** to `src/specify_cli/auth/transport.py` or `tests/architectural/test_auth_transport_singleton.py`. Deletion is Robert's call (C-005).

---

## 2. Component Changes (with paths + symbol names)

### 2.1 `src/charter/drg.py` — three-layer extension

- Add `OrgDRGFragment` (pydantic v2) — see [data-model.md §2](data-model.md#2-orgdrgfragment-fr-001).
- Add `OrgDRGConflict` typed exception — see [data-model.md §3](data-model.md#3-orgdrgconflict-fr-004).
- Add `load_org_drg(repo_root: Path) -> list[OrgDRGFragment]`.
- Add `merge_three_layers(shipped: DRGGraph, org_fragments: list[OrgDRGFragment], project: DRGGraph | None) -> DRGGraph`.
- Extend the existing `merge_layers` call site signature OR add `merge_three_layers` as the new public API; the existing 2-layer signature stays for backward compat.

### 2.2 `src/charter/scope.py` — NEW (CharterScope abstraction)

- `CharterScope` dataclass: `root: Path`, `name: str | None`.
- `CharterScope.default(repo_root: Path) -> CharterScope`.
- `CharterScope.resolve(repo_root: Path, feature_dir: Path) -> CharterScope` — reads `.kittify/config.yaml`'s optional `charter_scopes:` list and returns the nearest-enclosing scope; raises `CharterScopeConflict` on malformed configuration.

### 2.3 `src/charter/context.py` — `scope=` parameter (FR-010)

- `build_charter_context(repo_root, *, scope: CharterScope | None = None, ...)`. When `scope is None`, behaviour is byte-identical to today's `build_charter_context(repo_root)` — NFR-001 binding.
- Thread per-layer provenance into the `_render_*` helpers so the rendered prompt body carries `source: built-in | org:<pack> | project` per stanza (Axis 1 / FR-001).

### 2.4 `src/charter/resolver.py` — DRIFT-1 alias deletion (FR-100, C-003)

- Delete `resolve_governance = resolve_project_governance` at line 325-326.
- Delete the "Deprecated alias" docstring at line 198.

### 2.5 `src/charter/__init__.py` — export cleanup (FR-101)

- Remove `resolve_governance` from the `from .resolver import (...)` block (line 73).
- Remove `resolve_governance` from `__all__` (line 124).

### 2.6 `src/charter/*.py` and `src/kernel/*.py` — `__all__` declarations (FR-121, C-007)

- Every module declares `__all__`. The `test_all_declarations_required.py` gate walks both subpackages and asserts presence. Scope is intentionally limited to charter + kernel; expansion to other subpackages is a future-mission concern (FR-121 explicit scope statement).

### 2.7 `src/doctrine/workflows/` — NEW directory (FR-012)

- `software-dev-default.workflow.yaml` — declares the existing six-step sequence; pinned byte-stable.
- `_fixtures/our-team-design-first.workflow.yaml` — test-fixture workflow with an extra `design-review` step between `plan` and `tasks`. Used by AC-4 / Scenario 3 ATDD.

### 2.8 `src/specify_cli/next/_internal_runtime/workflow_registry.py` — NEW (FR-012, FR-015)

- `WorkflowSequence` pydantic model — see [data-model.md §5](data-model.md#5-workflowsequence-fr-012).
- `get_workflow(workflow_id: str) -> WorkflowSequence` — loads, caches, hard-fails on unknown id.
- Search precedence: `src/doctrine/workflows/<id>.workflow.yaml` first, then `src/doctrine/workflows/_fixtures/<id>.workflow.yaml` (test fixtures), then the operator-side override at `.kittify/workflows/<id>.workflow.yaml` (extension-ready; not load-bearing this mission).

### 2.9 `src/specify_cli/next/_internal_runtime/planner.py` — workflow consumption (FR-013, FR-014)

- The existing `plan_next` already takes a `MissionTemplate`. Slice F adds a thin resolver: when the mission's `meta.json` carries `workflow_id`, the planner consults the workflow registry to determine the action graph; when absent, it falls back to `software-dev-default`. **No silent fallback for unknown IDs** (FR-015).

### 2.10 `src/specify_cli/next/prompt_builder.py` — scope plumbing (FR-010)

- The `build_prompt` call site to `build_charter_context` accepts `scope=CharterScope.resolve(repo_root, feature_dir)`. For single-project repos, `CharterScope.resolve` returns `CharterScope.default(repo_root)` — byte-identical to today's call.

### 2.11 `src/specify_cli/__main__.py` — logging bootstrap (FR-130, FR-131)

- Add `logging.captureWarnings(True)` at module import (or at typer app startup).
- Install a Rich-aware `logging.Handler` that routes `WARNING+` records through the existing Rich `Console` instance to stderr. See [`contracts/catalog-miss-cli-visibility.md`](contracts/catalog-miss-cli-visibility.md).

### 2.12 `src/specify_cli/cli/commands/doctrine.py` — org pack UX (FR-006)

- `spec-kitty doctrine org init <path>` — scaffolds a minimal org pack skeleton (`drg/fragment.yaml`, `org-charter.yaml`, README) at the operator-specified path.
- `spec-kitty doctrine org validate <path>` — validates an org pack's structure independently (DRG schema + org-charter schema).

### 2.13 `src/specify_cli/cli/commands/doctor.py` — org-DRG visibility (FR-007)

- Add an "Organisation Layer" subsection to `doctor doctrine` listing: configured packs, fetched/missing status (mirrors the FR-015 hard-fail policy from Mission B), collision warnings from `merge_three_layers`.

### 2.14 Deletions (Q5 / DM-01KRX6N0YAFBY7MTJC0CN3D3E4 / FR-113)

Three concrete Cat-7 deletions to satisfy the burn-down in the same PR that introduces the meta-test (FR-113):

- `src/doctrine/templates/repository.py` (CentralTemplateRepository, never wired) — plus `tests/doctrine/templates/test_repository.py` if it exists.
- `src/specify_cli/glossary/prompts.py` — plus `tests/agent/glossary/test_prompts.py`.
- `src/specify_cli/glossary/rendering.py` — plus `tests/agent/glossary/test_rendering.py`.

---

## 3. ATDD Landing Plan (per lane)

Per **C-011 (binding for this mission)** and NFR-008, each lane opens with a failing-first WP that lands the canonical executable contracts the lane's implementation WPs turn green. See [`atdd-coverage.md`](atdd-coverage.md) for the canonical per-test mapping.

| Lane | Opening ATDD WP | Tests landed RED | Implementation WPs turn them GREEN |
|---|---|---|---|
| **A** (architectural rigor) | WP01 — opens with the meta-test (`test_ratchet_baselines.py`) + symbol-walk skeleton + the contract round-trip test, ALL initially red because baselines file / `__all__` declarations / round-trip frontmatter are missing | `test_ratchet_baselines.py`, `test_no_dead_symbols.py`, `test_all_declarations_required.py`, `test_example_round_trip.py` | WP01 turns the baselines test green (after refactor + Cat-7 shrinkage). WP02 turns the symbol-walk + `__all__`-required tests green. WP03 turns the round-trip test green by adding frontmatter to existing contracts and the allowlist. |
| **B** (independent remediations) | WP04 — opens with `test_alias_deleted_regression.py` (red because the alias still exists) AND WP05 opens with `test_catalog_miss_cli_visibility.py` (red because no log handler) | `test_alias_deleted_regression.py`, `test_catalog_miss_cli_visibility.py` | WP04 deletes the alias → regression test green. WP05 installs the handler → visibility test green. |
| **C** (org-DRG) | WP06 — opens with `test_three_layer_drg_end_to_end.py` (Scenario 1), `test_charter_status_reports_three_layers.py` (FR-002), `test_charter_lint_lints_all_layers.py` (FR-003), `test_org_pack_missing_path_hard_fails.py` (FR-004), `test_org_drg_cannot_override_shipped_invariants.py` (FR-005), `test_org_drg_round_trip_schema.py` (FR-001 via FR-140 frontmatter) | All red because the org-DRG loader, merge, and validator extension do not yet exist | WP06 turns the loader / merge / conflict tests green. WP07 turns `build_charter_context` provenance + doctor visibility green. WP08 turns the operator UX (init/validate) tests green. |
| **D** (monorepo + workflows + closing) | WP09 — opens with `test_monorepo_charter_scope.py` (Scenario 2) and the `CharterScope` unit tests; WP10 opens with `test_workflow_registry.py` (FR-012, FR-015); WP11 opens with `test_workflow_sequence_runtime.py` (Scenario 3, FR-013, FR-014) | All red because `CharterScope`, the workflow YAML loader, and the planner-integration do not yet exist | WP09 turns CharterScope tests green; ADR-8 lands. WP10 turns the registry tests green; `software-dev-default.workflow.yaml` lands byte-stable. WP11 turns the runtime-integration green; meta.json.workflow_id is honoured. WP12 turns the existence-only ACs (AC-12 through AC-16) green by landing the ADR + ticket + READMEs + charter amendments. |

Each WP's frontmatter records the ATDD test paths it turns green AND the SHA-or-WP of the red commit (per FR-304).

---

## 4. Sequencing & Risks

### 4.1 Lane dependency graph

```
                    Lane A (architectural rigor)
                    WP01 → WP02 → WP03  (must finish before Lane C/D START)
                          │
                          │  unblocks (RR-1)
                          ▼
                    Lane B (independent remediations)
                    WP04, WP05  (parallel, independent of A; can also wait if reviewer prefers serialising)
                          │
                          ▼
                    Lane C (org-DRG)
                    WP06 → WP07 → WP08
                          │
                          ▼
                    Lane D (monorepo + workflows + closing)
                    WP09 → WP10 → WP11 → WP12
```

- **Lane A MUST finish before Lane C/D start** so new modules in Lane C/D cannot grandfather themselves into the Cat-7 baseline (RR-1). The Cat-7 budget that Lane A pins at 7 is the budget Lane C/D must respect.
- **Lane B is independent.** WP04 + WP05 can start at mission claim. (The proposal §4 originally put Lane B parallel to A; the WP listing in plan.md preserves that.)
- **Within Lane C**, WP06 (loader + merge + conflict) precedes WP07 (`build_charter_context` integration) precedes WP08 (operator UX).
- **Within Lane D**, WP09 (CharterScope) precedes WP10 (workflow registry) precedes WP11 (runtime integration) precedes WP12 (closing).

### 4.2 Risk register

| # | Risk | P | I | Mitigation |
|---|---|---|---|---|
| RR-1 | Slice F's new modules grandfather themselves into `_ALLOWLIST` before WP01 lands | HIGH | MED | WP01 lands first in Lane A. Lane C/D MUST NOT start until WP01 is merged into the mission branch. ATDD-first means the burn-down meta-test is in place before any new modules ship. |
| RR-2 | Org-DRG schema conflicts with Mission B's selection-layer parity | MED | HIGH | C-009 binds — schema reuses 8-kind plural-naming union semantics; any divergence requires written rationale + glossary update. WP06's ATDD includes `test_org_drg_kind_parity_with_selection_schema.py`. |
| RR-3 | ADR-8 design reveals deeper assumptions baked into single-project layout | MED | MED | WP09 is time-boxed; CharterScope ships with `default()` returning the single-project shape (NFR-001 is the regression guard). If implementation surfaces a > 5-file blast radius, scope WP09 to ADR + minimum seam only. |
| RR-4 | Composable workflows break the 23 governance-contract fixtures | LOW | HIGH | C-008 binds — `software-dev-default` is byte-stable to today's hardcoded sequence. Pinned by `test_workflow_software_dev_default_is_byte_stable.py`. NFR-001 is the regression guard. |
| RR-5 | DRIFT-1 alias removal breaks an out-of-tree consumer | LOW | LOW | Assumption 4 documents no out-of-tree consumers exist. HiC accepted user impact in §5a.1. |
| RR-6 | CLI logging bootstrap collides with the existing Rich console | MED | LOW | The Rich-aware handler defers to the existing Console instance rather than instantiating a new one (architect's WP05 implementation note). |
| RR-7 | Contract round-trip gate flags pre-existing inconsistencies in legacy `kitty-specs/*/contracts/*.md` | MED | MED | FR-141 ships a legacy allowlist participating in the FR-110 baseline. Initial run is a discovery exercise; existing inconsistencies are either fixed in WP03 or filed as follow-up tickets and added to the allowlist. |
| RR-8 | Lane B WP04 + WP05 commit on the shared lane workspace concurrently and trip parallel-staging collision | LOW | LOW | Lane B WPs are sequential within the lane by design. |
| RR-9 | Workflow YAML schema gets too rigid and prevents future extension (e.g. parallel branches in the action graph) | LOW | MED | WP10's schema includes a `version` field; future extensions can ship as `version: 2` workflows the registry routes to a v2 parser. |
| RR-10 | Org-DRG fixture missing in tests directory because `_fixtures/` is not standard for org packs | LOW | LOW | WP06 creates `tests/architectural/_fixtures/org_packs/example_org/` with the canonical fragment YAML; reused across Lane C tests. |

### 4.3 Lane assignment hint for finalize-tasks

- **Lane A** — `slice-f-lane-a` — WP01, WP02, WP03 (sequential)
- **Lane B** — `slice-f-lane-b` — WP04, WP05 (sequential within lane)
- **Lane C** — `slice-f-lane-c` — WP06, WP07, WP08 (sequential)
- **Lane D** — `slice-f-lane-d` — WP09, WP10, WP11, WP12 (sequential)

4 lanes total. Lane B can run in parallel to Lane A; Lane C/D wait on Lane A completion.

---

## 5. Test Strategy

### 5.1 ATDD-first canonical executable spec (C-011, NFR-008)

The lane-opening WPs (WP01, WP04, WP05, WP06, WP09, WP10, WP11) each land their ATDD test files as separate **first** commits in the lane. The test files are committed RED — they fail on the lane's planning base commit because the production code does not yet exist. The lane's implementation WPs then turn each test green in dependency order. The reviewer enforces red→green per spec §"Reviewer obligation".

The canonical coverage table is at [`atdd-coverage.md`](atdd-coverage.md). NFR-008 sets the threshold at ≥ 90% in-scope ACs; the 10% slack absorbs the existence-only ACs (AC-12 ADR, AC-13 ticket, AC-14 README, AC-15 doc presence, AC-16 charter amendment) where the existence assertion IS the test.

### 5.2 Regression guards (NFR-001, NFR-002, NFR-003, NFR-005)

The following test surfaces MUST remain green throughout the mission:

- `tests/specify_cli/next/test_wp_prompt_governance_contract.py` — 23/23 (NFR-001)
- `tests/architectural/test_layer_rules.py` — unchanged pass (NFR-003)
- `tests/architectural/test_wp_prompt_build_latency.py` — within 1.2× baseline (NFR-002)
- `tests/architectural/` — full sweep at mission close (NFR-005)

### 5.3 Architectural sweep at mission close (NFR-005, NFR-007)

WP12 runs:

```bash
PWHEADLESS=1 pytest tests/architectural/ -v
spec-kitty analyze
```

NFR-005 requires exit 0 on the full sweep. NFR-007 requires `/spec-kitty.analyze` to report verdict `READY FOR IMPLEMENTATION` with 0 CRITICAL and 0 HIGH findings.

### 5.4 Backward compatibility tests

Per axis:

- **Axis 1.** `build_charter_context()` with no org pack configured produces output byte-identical to the Mission B baseline (`tests/architectural/test_three_layer_drg_no_org_layer_byte_stable.py`).
- **Axis 2.** `build_charter_context(repo_root, feature_dir)` (no `scope=`) is byte-identical to today (NFR-001).
- **Axis 3.** A mission's `meta.json` without `workflow_id` produces the same `spec-kitty next` actions as today's hardcoded sequence (`test_workflow_software_dev_default_is_byte_stable.py`, C-008).

### 5.5 Marker discipline

All new tests declare appropriate pytest marks per `test_pytest_marker_convention.py`. Subprocess tests (FR-132) declare `@pytest.mark.integration` and NOT `@pytest.mark.fast` (per `test_pytest_marker_correctness.py`).

### 5.6 Frontmatter discipline (FR-140 dogfooding)

Slice F's own contract YAML examples (the 6 contracts in [`contracts/`](contracts/)) ship with `pydantic_model: <module.Class>` and `expect: valid|invalid` frontmatter. The round-trip gate exercises them at WP03 acceptance — Slice F is the first mission to dogfood the convention end-to-end.

---

## 6. Plan-Time Decisions

The six open questions in spec §"Open Questions" plus two architect-side calls resolved during planning:

| Decision | Resolution | Rationale |
|---|---|---|
| **Q4** — Skill deployment ownership (debrief §5 Q4) | Surface, don't overwrite. Mission C does NOT add a skill-deployment migration | Deferred to the "operator-surface hygiene" mission per spec §Open-Questions item 1; aligns with architect's preference and bundled MED-1 descoping |
| **Q5** — Glossary orphans #8 + #9 disposition | **DELETE** both `specify_cli.glossary.prompts` and `specify_cli.glossary.rendering` (and their tests) | [DM-01KRX6N0YAFBY7MTJC0CN3D3E4](decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md) — 3+ years orphaned, no operator demand, cleanest Cat-7 burn-down, mirrors HiC §5a.1 "no eventual deprecation" stance. Contributes 2 entries to FR-113's 10 → 7 shrinkage (combined with `doctrine.templates.repository` deletion = 3 entries removed) |
| **Q6** — Forward-only scope (WP06) | Forward-only | C-002 binds; historical risk decisions stay as-is |
| **Q7** — Forward-staging convention destination | `src/specify_cli/upgrade/migrations/README.md` | Per FR-301 default; that's where new contributors land first |
| **NEW-1** — Org-DRG source mechanism | **Local-path only in this mission**. URL and packaged-dependency support deferred to follow-up | Local-path is the minimum viable mechanism that closes FR-001 .. FR-007; URL/package support adds non-trivial dependency surface and is gated on WP06 implementation review per Assumption 3 |
| **NEW-2** — Workflow back-compat default permanence | **Permanent default** — `workflow_id` is opt-in, not migration-required | Mirrors C-003's "no eventual deprecation" stance from the alias decision; consistent with FR-013's "absent ⇒ default" semantics |
| **ARCH-1** (architect-side) — Workflow registry location | `src/specify_cli/next/_internal_runtime/workflow_registry.py` | The workflow consumer is `prompt_builder` + `planner`, both runtime-layer. The registry is runtime-internal, not a doctrine artifact (the YAML files ARE doctrine artifacts under `src/doctrine/workflows/`, but the loader is runtime). Preserves the layer rule (NFR-003) |
| **ARCH-2** (architect-side) — `__all__` scope | `src/charter/` + `src/kernel/` only (FR-121 explicit) | Wider scope (e.g. `src/specify_cli/`) is a future-mission concern. This mission proves the convention works at the two boundary subpackages; expansion is mechanical once the convention is charter-pinned (C-007) |

---

## 7. References

- Spec: [spec.md](spec.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/](contracts/)
- ATDD coverage: [atdd-coverage.md](atdd-coverage.md)
- Quickstart: [quickstart.md](quickstart.md)
- Decision artifacts: [decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md](decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md)
- Predecessor mission plan: [../charter-mediated-doctrine-selection-01KRTZCA/plan.md](../charter-mediated-doctrine-selection-01KRTZCA/plan.md)
- Architect debriefs (gitignored): `work/remediation-mission-debrief.md`, `work/ratchet-coherence-audit.md`, `work/mission-c-slice-f-scope-proposal.md`
- Project charter: [`.kittify/charter/charter.md`](../../.kittify/charter/charter.md)
