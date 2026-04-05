# 2.x Implementation Mapping

| Field | Value |
|---|---|
| Status | Draft |
| Date | 2026-03-04 |
| Last Updated | 2026-03-25 |
| Scope | Maps C4 architecture views and doctrine stack to current codebase |
| Parent | [System Landscape](../00_landscape/README.md) |
| Related ADRs | `2026-03-25-1-glossary-type-ownership` |

## Purpose

Bridge the gap between the architecture documentation (C4 levels 0–3) and the
actual codebase. This document answers: "Where does each architectural concept
live in the source tree today?"

This is **not** a code inventory — it maps domain responsibilities to modules,
explains the doctrine stack layer model, and identifies where the current
implementation aligns with or diverges from the target architecture.

---

## Level 0 — System Landscape → Codebase Modules

The landscape defines 8 domain containers. All 8 exist in the current codebase
as Python modules within a single-process CLI application.

| Landscape Container | Primary Codebase Location | Package | Notes |
|---|---|---|---|
| **Control Plane** | `src/specify_cli/cli/` | `specify_cli` | Typer-based CLI. Single user entry point for all commands. |
| **Kitty-core** | `src/specify_cli/core/`, `mission.py`, `mission_v1/`, `missions/`, `next/`, `template/`, `runtime/` | `specify_cli` | Planning pipeline (specify→plan→tasks) and next-action loop. |
| **Event Store** | `src/specify_cli/status/` | `specify_cli` | JSONL event logs (`store.py`), reducer (`reducer.py`), WP frontmatter, `meta.json`. Filesystem-only today. |
| **Orchestration** | `src/specify_cli/orchestrator/`, `orchestrator_api/`, `merge/`, `sync/`, `tracker/` | `specify_cli` | Lifecycle engine, worktree management, merge execution, tracker projection. |
| **Dashboard** | `src/specify_cli/dashboard/` | `specify_cli` | Playwright-based local browser kanban. Read-only against Event Store. |
| **Agent Tool Connectors** | `src/doctrine/missions/*/command-templates/` → deployed as `.claude/`, `.codex/`, `.amazonq/`, etc. | `doctrine` (source), `specify_cli` (deployment) | Current connector is a rendered markdown prompt template. One "adapter" per agent (12 agents). Source templates relocated to `doctrine/missions/` in feature 054; migration is complete. |
| **Skills Installer** | `src/specify_cli/skills/` | `specify_cli` | Deployment bridge introduced in feature 055. `SkillRegistry` discovers canonical skills from `src/doctrine/skills/`; `ManagedSkillManifest` tracks installed files by hash for drift detection; `installer.py` and `verifier.py` deploy skills into agent directories alongside command templates during `spec-kitty init`. |
| **Doctrine** | `src/doctrine/` (artifacts) + `src/doctrine/skills/` (canonical skill packs) | `doctrine` (standalone package, own `pyproject.toml`) | YAML artifacts, JSON Schema validation, Pydantic models, repository pattern. Includes 6 shipped skill packs in `doctrine/skills/` (e.g., `spec-kitty-runtime-next`, `spec-kitty-charter-doctrine`). Zero dependency on `specify_cli`. |
| **Charter** | `src/charter/` | `charter` (standalone package) | Interview flow, compiler, action context resolver with depth semantics and action index intersection. Produces `.kittify/charter/` bundles. Context bootstrap injects governance at every execution boundary. |

### Key structural observation

The `doctrine` and `charter` packages are **standalone Python packages**
registered in `pyproject.toml`. All other containers are modules within
the `specify_cli` monolith. The separation of `doctrine` and `charter`
from `specify_cli` is architecturally deliberate:

- `doctrine` — zero external dependencies, pure knowledge library
- `charter` — consumes `doctrine` and limited `specify_cli.runtime` utilities;
  produces the governance artifacts that agents consume at execution boundaries
- `specify_cli` — control plane, lifecycle, and orchestration; uses both

All other container boundaries are module-level conventions enforced by code
review, not by packaging.

---

## Level 1 — System Context → Boundary Mapping

| External Actor | Current Boundary Surface | Implementation |
|---|---|---|
| **Human In Charge** | CLI commands, interview prompts | `src/specify_cli/cli/commands/` (Typer command groups) |
| **Human In Charge** (read) | Dashboard kanban | `src/specify_cli/dashboard/server.py` → local browser |
| **Agent Tools** | Command template prompts | `.claude/commands/`, `.codex/prompts/`, etc. (12 agent directories) |
| **External Trackers** | Optional status projection | `src/specify_cli/sync/`, `src/specify_cli/tracker/` (feature-gated) |
| **Project Repository** | Filesystem read/write | `kitty-specs/`, `.kittify/`, `status.events.jsonl`, WP frontmatter |

### Boundary rule compliance

| Boundary Rule | Current State |
|---|---|
| Host-owned authority is non-negotiable | ✅ All state mutations go through `status/emit.py` — agents cannot bypass |
| Agent Tools are external | ✅ Agents receive rendered prompts; they do not call `specify_cli` directly |
| Dashboard is read-only | ✅ `dashboard/` reads frontmatter/events only; no write path exists |
| Tracker integration is optional | ✅ Sync/tracker modules are feature-gated; system works without them |
| Repository is canonical state | ✅ All persistence is filesystem-based; no external state authority |

---

## Level 2 — Container Collaboration → Code Paths

### Loop A: Planning (User → Kitty-core → Event Store)

```
User runs: spec-kitty specify / plan / tasks
  → src/specify_cli/cli/commands/ (Control Plane)
  → src/specify_cli/core/ + next/ + mission.py (Kitty-core)
  → src/specify_cli/status/emit.py (Event Store write)
  → kitty-specs/<feature>/ artifacts written to filesystem
```

### Loop B: Execution Coordination (Orchestration ↔ Event Store → Connectors)

```
User runs: spec-kitty implement WP01
  → src/specify_cli/cli/commands/ (Control Plane)
  → src/specify_cli/orchestrator/ (Orchestration)
  → src/specify_cli/status/store.py (Event Store read — WP state)
  → src/doctrine/missions/*/command-templates/implement.md (Connector)
  → Agent executes work (external)
  → src/specify_cli/status/emit.py (Event Store write — lifecycle event)
```

### Loop C: Governance (User → Charter → Doctrine)

```
User runs: spec-kitty charter interview / generate
  → src/specify_cli/cli/commands/ (Control Plane)
  → src/charter/interview.py (Charter interview)
  → src/charter/compiler.py (Charter compiler)
  → src/charter/reference_resolver.py (transitive DFS: directive → tactic → styleguide/toolguide)
  → src/doctrine/service.py → per-artifact repositories (Doctrine read)
  → .kittify/charter/ (compiled governance bundle)
```

### Loop C': Action Context Bootstrap (Agent → Charter → Doctrine)

```
Agent calls: spec-kitty charter context --action implement
  → src/charter/context.py (Action Context Resolver)
  → Load action index: src/doctrine/missions/software-dev/actions/implement/index.yaml
  → Two-stage intersection: action index ∩ project selections (references.yaml)
  → src/doctrine/service.py (DoctrineService) → fetch directive/tactic content by depth
  → Load action guidelines: src/doctrine/missions/software-dev/actions/implement/guidelines.md
  → Render CharterContextResult (governance text injected into agent prompt)
  → Persist context-state.json (first-load tracking for depth semantics)
```

This sub-loop runs at every execution boundary (Principle 5). First invocation
returns depth-2 (full bootstrap); subsequent calls return depth-1 (compact).

### Loop D: Visibility (Dashboard ← Event Store)

```
User runs: spec-kitty dashboard
  → src/specify_cli/dashboard/server.py (starts local server)
  → src/specify_cli/dashboard/scanner.py (reads kitty-specs/ frontmatter)
  → Browser renders kanban (read-only)
```

### Loop E: External Projection (Orchestration → Tracker)

```
Orchestration lifecycle event triggers:
  → src/specify_cli/sync/ (sync coordinator)
  → src/specify_cli/tracker/ (tracker connector gateway)
  → External tracker API (optional, feature-gated)
```

---

## Level 3 — Components → Modules

| Component (from C4 Level 3) | Module(s) | Key Files |
|---|---|---|
| **Command Router** | `cli/` | `cli/__init__.py`, command group registration |
| **Workflow Command Set** | `cli/commands/` | `specify.py`, `plan.py`, `tasks.py`, `implement.py`, `review.py`, `merge.py`. Canon terminology: `--mission-type` is the flag for mission-type selection (renamed from `--mission` in 5 type-selection commands, 2026-03-25; old `--mission` alias raises hard error). `--mission` remains the slug selector on all other commands. `--feature` is a hidden deprecated alias everywhere. |
| **Status Mutation Command Set** | `cli/commands/` | `status.py`, lane transition commands |
| **Governance Command Set** | `cli/commands/` | `charter.py` |
| **Next Loop Coordinator** | `next/` | `next/__init__.py` — per-agent action sequencing |
| **Mission Discovery and Resolution** | `core/`, `mission.py`, `mission_v1/` | Mission context detection, asset loading |
| **Runtime Asset Lifecycle Coordinator** | `runtime/` | Bootstrap, tier selection, compatibility |
| **Tiered Template Resolution Pipeline** | `template/` | Prompt/template resolution by configured precedence |
| **Mission Context Detection** | `core/` | Active mission detection |
| **Event Semantics Reducer** | `status/reducer.py` | Deterministic event→snapshot materialization |
| **Persistence Layer** | `status/store.py` | JSONL append/read, corruption detection |
| **Lifecycle Command Gateway** | `status/emit.py` | `emit_status_transition()` — single entry point for state changes |
| **WP Lifecycle Engine** | `status/transitions.py` | 16-pair transition matrix, guard conditions |
| **Target-Line Router** | `status/phase.py`, `core/` | Phase resolution, target branch routing |
| **Sync Runtime Coordinator** | `sync/` | Sync lifecycle, projection scheduling |
| **Tracker Connector Gateway** | `tracker/` | External tracker API adapters |
| **Kanban View** | `dashboard/` | `server.py`, `scanner.py`, `templates/`, `static/` |
| **Doctrine Catalog Loader** | `doctrine/service.py` | `DoctrineService` — lazy aggregation facade |
| **Schema Validation Gate** | `doctrine/*/validation.py`, `doctrine/schemas/` | JSON Schema + Pydantic validation |
| **Glossary Hook Coordinator** | `doctrine/missions/glossary_hook.py`, `specify_cli/glossary/` | Glossary checks during mission execution |
| **Charter Interview Flow** | `charter/interview.py` | Guided Q&A for governance capture |
| **Charter Compiler** | `charter/compiler.py` | Doctrine→charter bundle compilation |
| **Action Context Resolver** | `charter/context.py`, `resolver.py`, `reference_resolver.py` | Action-scoped governance context with depth semantics (1=compact, 2=bootstrap, 3=extended) and two-stage intersection (action index ∩ project selections) |
| **Action Index** | `doctrine/missions/*/actions/*/index.yaml` | Per-action directive/tactic/styleguide/toolguide selection — loaded by `doctrine/missions/action_index.py` |
| **Execution Dispatch** | `doctrine/missions/*/command-templates/implement.md` | Prompt rendering for agent dispatch (source relocated from `specify_cli/missions/` in feature 054) |
| **Agent Adapters** | `.claude/`, `.codex/`, `.amazonq/`, etc. | Per-agent command templates (12 agents) |
| **Path Resolver** | `src/kernel/paths.py` | `get_kittify_home()`, `get_package_asset_root()` — zero-dependency path resolution shared across all packages (moved from `specify_cli.runtime.home` in WP09, 2026-03-25; re-export shim at `specify_cli/runtime/home.py` preserves backward compatibility). **Dependency note (Windows):** `kernel` is stdlib-only on Linux/macOS. On Windows, `platformdirs` is imported lazily in `kernel/paths.py` for platform-appropriate home directory resolution. This is the only sanctioned third-party import in `kernel/`. |
| **Glossary Runner Registry** | `src/kernel/glossary_runner.py` | `GlossaryRunnerProtocol`, `register()`, `get_runner()` — plugin registry allowing `doctrine` to register its runner without creating a `specify_cli` import dependency. Resolves DIV-5 (architecture/2.x/adr/2026-03-25-1-glossary-type-ownership.md). |

### Tiered Template Resolution Pipeline

Template resolution uses a 5-tier precedence chain implemented in
`src/specify_cli/runtime/resolver.py`. The resolver checks each tier in order
and returns the first file that exists:

| Tier | Label | Path Pattern | Semantics |
|---|---|---|---|
| 1 | **Project Override** | `.kittify/overrides/{templates,command-templates}/{name}` | Highest precedence. User's explicit project-level override. |
| 2 | **Legacy** (deprecated) | `.kittify/{templates,command-templates}/{name}` | Pre-migration project files. Emits deprecation warning or one-time "run `spec-kitty migrate`" nudge. Will be removed in next major version. |
| 3 | **Global Mission-Specific** | `~/.kittify/missions/{mission}/{templates,command-templates}/{name}` | User-global, scoped to a specific mission type. Populated by `spec-kitty migrate` / `ensure_runtime`. |
| 4 | **Global Non-Mission** | `~/.kittify/{templates,command-templates}/{name}` | User-global, cross-mission. |
| 5 | **Package Default** | `doctrine/missions/{mission}/{templates,command-templates}/{name}` | Lowest precedence. Bundled with the `doctrine` package. Resolved via `kernel.paths.get_package_asset_root()`. |

**Special cases:**
- `resolve_mission()` uses a 4-tier variant — it skips tier 4 (Global Non-Mission) because missions are inherently mission-scoped.
- Tier 2 (Legacy) shows a one-time stderr nudge when the global runtime is already configured.
- If no tier provides the asset, `FileNotFoundError` is raised.

---

## Doctrine Stack: Layer Model

The Doctrine container is organized as a layered knowledge stack. Each layer
serves a distinct governance purpose, and the reference directions between
layers are strictly defined.

### Artifact Type Layers

| Layer | Artifact Type | Location | Count (shipped) | Purpose |
|---|---|---|---|---|
| **Mental Models** | Paradigm | `src/doctrine/paradigms/` | 1 (`test-first`) | High-level approaches that frame *how you think about a problem*. Not executable. |
| **Rules** | Directive | `src/doctrine/directives/` | 27 (001–026 + test-first) | Enforceable governance rules. `enforcement: required\|advisory`. |
| **Procedures** | Tactic | `src/doctrine/tactics/` | 4 | Step-by-step execution procedures. Agent-consumable. |
| **Output Shapes** | Styleguide | `src/doctrine/styleguides/` | shipped set | Define *what output looks like* — formatting, naming, structure. |
| **Tool Contracts** | Toolguide | `src/doctrine/toolguides/` | shipped set | Define *how tools are used* — config, invocation, constraints. |
| **Execution Identity** | Agent Profile | `src/doctrine/agent_profiles/shipped/` | 7 (architect, curator, designer, implementer, planner, researcher, reviewer) | Agent capabilities, constraints, collaboration contracts. Injected by `SkillRegistry` at `init` time. |
| **Deployable Governance Packs** | Skill | `src/doctrine/skills/` | 8 (charter-doctrine, git-workflow, glossary-context, mission-system, orchestrator-api-operator, runtime-next, runtime-review, setup-doctor) | Self-contained governance bundles (SKILL.md + optional references/scripts/assets) deployed to agent directories during `spec-kitty init` by `specify_cli/skills/`. |
| **Process Templates** | Mission Template | `src/doctrine/missions/` | 3 types (software-dev, documentation, research) + plan | Define the SDD process stages for different mission types. Also carries per-action governance indexes. |
| **Process Templates** | Expected Artifacts Manifest | `src/doctrine/missions/*/expected-artifacts.yaml` | 3 (software-dev, documentation, research) | Per-step, class-tagged (`input`, `output`, `workflow`, `evidence`), blocking-semantics artifact requirements consumed by dossier `ManifestRegistry` via `MissionRepository.get_expected_artifacts()`. |

### Reference Direction Rules

```
Paradigm ──tactic_refs──→ Tactic       (approach justifies tactics)
Directive ──tactic_refs──→ Tactic      (rule selects procedures)
Tactic ──references──→ Tactic          (step consults related procedure)
Tactic ──references──→ Styleguide      (step consults output shape)
Tactic ──references──→ Toolguide       (step consults tool contract)
Tactic ──references──→ Directive       (step references governing rule)
Any ──opposed_by──→ Any                (contradiction / tension documentation)
```

**Leaf nodes:** Styleguides and Toolguides are terminal — they are referenced
*by* tactics but carry no outward references.

**DAG constraint:** Tactic-to-tactic references must form a directed acyclic
graph. Cycles are detected by `test_tactic_reference_graph_has_no_cycles` in
`tests/doctrine/test_directive_consistency.py`.

**Contradiction semantics:** `opposed_by` does **not** mean "superseded". Both
artifacts remain valid. The field documents a known tension so agents can
surface it when both are simultaneously active (e.g., Directive 024 Locality of
Change vs. Directive 025 Boy Scout Rule).

### Repository Implementation Pattern

Every artifact type follows an identical internal structure:

```
src/doctrine/<artifact_type>/
  ├── __init__.py          # Exports
  ├── models.py            # Pydantic model (e.g., Directive, Tactic, Paradigm)
  ├── repository.py        # Two-source YAML loader (shipped + project)
  ├── validation.py        # Schema validation — delegates to SchemaUtilities
  └── shipped/             # Built-in artifacts (YAML files)
      ├── 001-xxx.<type>.yaml
      └── ...
```

### Shared Utilities (`src/doctrine/shared/`)

Cross-cutting infrastructure used by all artifact subpackages:

| Module | Purpose |
|---|---|
| `schema_utils.py` | `SchemaUtilities.load_schema(name)` — single cached schema loader replacing six near-identical per-type functions |
| `exceptions.py` | `DoctrineArtifactLoadError` — fail-open signal for corrupt/unreadable artifact files; `DoctrineResolutionCycleError` — raised when a cycle is detected in the reference graph |

**Why shared utilities matter:** Before `shared/`, each `validation.py` duplicated identical schema-loading logic (importlib.resources lookup + filesystem fallback + LRU cache). The `shared/` module eliminates that duplication and provides a single place to evolve the loading strategy.

**Two-source loading** is the key design pattern:

1. **Shipped artifacts** are bundled with the `doctrine` Python package in
   `shipped/` directories. These are the defaults that come with Spec Kitty.
2. **Project artifacts** live in the user's project (e.g.,
   `.kittify/doctrine/directives/`). They can override shipped artifacts via
   field-level merge or add entirely new ones.

The `DoctrineService` (`src/doctrine/service.py`) is the aggregation facade —
it lazily instantiates all per-type repositories and is the single entry point
for all consumers (Charter compiler, Connectors, Kitty-core).

### Schema Validation

Each artifact type has a corresponding JSON Schema file in
`src/doctrine/schemas/`:

| Schema File | Validates |
|---|---|
| `paradigm.schema.yaml` | Paradigm artifacts (includes `tactic_refs`, `opposed_by`, `contradiction` definition) |
| `directive.schema.yaml` | Directive artifacts (includes `tactic_refs`, `opposed_by`) |
| `tactic.schema.yaml` | Tactic artifacts (includes `steps`, `references`, `opposed_by`) |
| `styleguide.schema.yaml` | Styleguide artifacts |
| `toolguide.schema.yaml` | Toolguide artifacts |
| `agent-profile.schema.yaml` | Agent Profile artifacts (capabilities, constraints) |
| `mission.schema.yaml` | Mission template definition |

Validation is enforced in tests (`tests/doctrine/`) and through the
Schema Validation Gate component. Schemas use `additionalProperties: false`
on paradigm and tactic types, meaning any new field requires both a schema
update and a valid fixture update.

---

## Doctrine Stack: As-Is vs. Vision

### What exists and works today

| Capability | Status | Evidence |
|---|---|---|
| All 7 artifact types with Pydantic models, repositories, validation | ✅ Complete | `src/doctrine/*/models.py`, `repository.py`, `validation.py` |
| JSON Schema validation for all types | ✅ Complete | `src/doctrine/schemas/*.schema.yaml` |
| Two-source loading (shipped + project override) | ✅ Complete | `repository.py` field-level merge on each type |
| Cross-artifact references (`tactic_refs`, `references[]`) | ✅ Complete | Wired with test coverage (40 doctrine tests) |
| `opposed_by` contradiction modeling | ✅ Complete | Schema + data on paradigm, directive, tactic |
| DAG cycle detection — shipped artifacts | ✅ Complete | `test_tactic_reference_graph_has_no_cycles` in `tests/doctrine/test_directive_consistency.py` |
| Cycle detection at resolution boundary (raises `DoctrineResolutionCycleError`) | ✅ Complete | `src/charter/reference_resolver.py` `_Walker`; `tests/doctrine/test_cycle_detection.py` |
| Shared schema loading (`SchemaUtilities`) | ✅ Complete | `src/doctrine/shared/schema_utils.py`; replaces 6 duplicated per-type loaders |
| Domain exceptions (`DoctrineArtifactLoadError`, `DoctrineResolutionCycleError`) | ✅ Complete | `src/doctrine/shared/exceptions.py` |
| `DoctrineService` aggregation facade | ✅ Complete | `src/doctrine/service.py` |
| Charter compiler consumes Doctrine | ✅ Complete | `src/charter/compiler.py` |
| Command templates as connector implementation | ✅ Complete | 12-agent template system via migrations |
| Transitive reference resolution (directive → tactic → styleguide/toolguide) | ✅ Complete | `src/charter/reference_resolver.py` (feature 054) |
| Action-scoped governance injection with depth semantics | ✅ Complete | `src/charter/context.py` + `src/doctrine/missions/*/actions/*/index.yaml` (feature 054) |
| Per-action guidelines extraction from templates | ✅ Complete | `src/doctrine/missions/software-dev/actions/*/guidelines.md` (feature 054) |
| ArtifactKind canonical enum | ✅ Complete | `src/doctrine/artifact_kinds.py` (feature 054, WP09-WP10) |
| MissionRepository package relocation | ✅ Complete | `src/doctrine/missions/` is the authoritative source for all mission assets (YAML, command templates, content templates, expected-artifacts). `src/specify_cli/missions/` retains only Python code modules (`primitives.py`, `glossary_hook.py`, `.contextive.yml`) for the glossary subsystem per ADR 2026-03-25-1. |
| Skills Pack canonical distribution | ✅ Complete | `src/specify_cli/skills/` — `SkillRegistry`, `ManagedSkillManifest`, installer, verifier. 6 canonical skills in `src/doctrine/skills/`. Deployed to agent directories during `spec-kitty init` (feature 055). |
| Agent Profile shaping connector behavior | ✅ Complete | Models, repository, schema, profile-aware resolution wired in `resolver.py`; workflow profile injection at execution boundary enabled (feature 055). |
| `kernel` zero-dependency floor (`paths`, `glossary_runner`, `glossary_types`) | ✅ Complete | `src/kernel/` — `paths.py`, `glossary_runner.py`, `glossary_types.py`. Backward-compat re-export shim at `specify_cli/runtime/home.py`. DIV-5 (glossary runner boundary) resolved. ADR: `2026-03-25-1-glossary-type-ownership`. |
| `--mission-type` flag on type-selection commands | ✅ Complete | 5 commands renamed from `--mission` to `--mission-type` (2026-03-25). Old `--mission` alias on those commands raises `typer.Exit(1)`. `--mission` (slug selector) and `--feature` (hidden deprecated alias) unchanged on all other commands. |

### What is emerging or aspirational

| Capability | Status | Gap Description |
|---|---|---|
| Glossary integration at execution boundary | 🟡 Partial | `glossary_hook.py` exists; full Glossary Hook Coordinator loop is early-stage |
| Slimmed agent templates (governance-free) | 🟡 Partial | Bootstrap section added to templates. Residual inline governance prose not yet stripped. Migration `m_2_0_2` pending. |
| Mission templates as first-class doctrine artifacts | 🟡 Partial | Templates relocated to `src/doctrine/missions/` (feature 054). Action indexes operational. Formal `MissionTemplateRepository` deferred. |
| Explicit per-agent connector adapters | 🟡 Partial | 12-agent command template system is the seed. Architecture envisions SDK/shell/remote adapters (Phase 2). |
| Non-software-dev mission parity | 🟡 Partial | `documentation`, `plan`, `research` missions have action directories but thinner indexes than `software-dev`. |
| Event Store behind interface contract | 🟡 Partial | `store.py`/`reducer.py` provide the interface pattern. Not yet formally abstracted for alternative backends (Phase 3). |
| Control Plane as swappable surface | 🔴 Conceptual | CLI is tightly coupled. No interface abstraction exists yet for TUI/web alternatives |
| Dashboard as independent read surface | 🟡 Partial | Functionally independent. Reads filesystem directly rather than through Event Store interface |

---

## Divergence Notes

Areas where the current implementation does not yet match the target
architecture:

1. **CLI mixes Control Plane and Orchestration:** Some CLI commands directly
   invoke lifecycle mutations rather than routing through a clean Control Plane →
   Orchestration interface. The boundary is module-level convention, not enforced
   by an interface contract.

2. **Kitty-core and Orchestration share filesystem paths:** Both can write
   to `kitty-specs/` directly. The landscape says they should both go through
   the Event Store interface contract.

3. **Connector concept is implicit:** The current "adapter" is a rendered
   markdown template. There is no formal `Connector` interface that alternative
   dispatch mechanisms (SDK, shell, remote API) could implement.

4. **Dashboard reads filesystem directly:** Rather than querying through
   the Event Store interface, `dashboard/scanner.py` reads WP frontmatter files
   directly. This works but bypasses the Event Store abstraction.

These are not bugs — they reflect the natural state of a system evolving toward
its target architecture. The landscape document establishes where the boundaries
*should* be, and the gap between as-is and target architecture guides future
refactoring priorities.

---

## Traceability

- System Landscape: `../00_landscape/README.md`
- Architectural Principles: `../00_landscape/README.md#architectural-principles`
- System Context: `../01_context/README.md`
- Container View: `../02_containers/README.md`
- Component View: `../03_components/README.md`
- Doctrine Stack Domain Model: `../03_components/README.md#doctrine-stack-domain-model`
- Doctrine governance ADR: `../adr/2026-02-23-1-doctrine-artifact-governance-model.md`
