# 2.x Doctrine and Constitution

The constitution is the single authoritative governance document for your project. It captures policy decisions -- testing standards, quality gates, branching rules, deployment constraints -- and feeds them into every workflow action. Agents never invent governance on the fly; they read what the constitution says and comply.

In 2.x, the constitution workflow is fully command-driven. You answer an interview, generate machine-readable config, and sync it whenever policy changes. The extracted config is injected into agent prompts automatically, so governance is enforced without manual intervention.

## The 3-Layer Model

Governance is organized into three layers. Only the first is human-edited; the rest are derived.

| Layer | File | Edited By |
|-------|------|-----------|
| 1. Constitution | `constitution.md` | Human (via interview or direct edit) |
| 2. Extracted Config | `governance.yaml`, `directives.yaml`, `metadata.yaml` | Auto-generated (never edit) |
| 3. Doctrine References | `library/*.md` | Auto-generated (never edit) |

The flow is always top-down: edit the constitution, then run sync to regenerate everything below it.

## Doctrine Artifact Model

2.x doctrine artifacts are repository-native and typed:

1. Directives: `src/doctrine/directives/*.directive.yaml`
2. Tactics: `src/doctrine/tactics/*.tactic.yaml`
3. Styleguides: `src/doctrine/styleguides/**/*.styleguide.yaml`
4. Toolguides: `src/doctrine/toolguides/*.toolguide.yaml`
5. Schemas: `src/doctrine/schemas/*.schema.yaml`
6. Mission assets/templates: `src/doctrine/missions/**`

Artifact integrity is enforced by:

1. `tests/doctrine/test_schema_validation.py`
2. `tests/doctrine/test_artifact_compliance.py`
3. `tests/doctrine/test_tactic_compliance.py`

## The Interview-Generate-Sync Workflow

The constitution flow is command-driven. The interview step is **required** — `generate` will
exit non-zero with an actionable error if `answers.yaml` is absent.

1. `spec-kitty constitution interview` — Capture project answers (paradigms, directives, tools)
2. `spec-kitty constitution generate --from-interview` — Compile bundle from answers + shipped doctrine
3. `spec-kitty constitution context --action <specify|plan|implement|review>` — Load governance context
4. `spec-kitty constitution status` — Check sync state
5. `spec-kitty constitution sync` — Re-extract YAML config files from `constitution.md`

**Validation behaviour:**

- Shipped doctrine catalog is validated at compile time; unrecognised IDs are reported as diagnostics
  but do not abort generation.
- Project-local support files (declared in `answers.yaml`) are accepted without catalog-ID validation.
  They supplement shipped doctrine and appear in `references.yaml` as `kind: local_support`.
- Local support files that overlap a shipped concept emit an additive conflict warning; both entries
  are kept.
- `governance.yaml`, `directives.yaml`, and `metadata.yaml` are emitted by `constitution sync`.
  `agents.yaml` is **not** emitted.

**Context bootstrap behaviour:**

- First call to `constitution context --action <action>` returns full governance context (depth 2).
- Subsequent calls for the same action return compact context (depth 1) by default.
- Bootstrap state is persisted in `.kittify/constitution/context-state.json`.
- An explicit `--depth` flag overrides the bootstrap auto-selection.

This cycle repeats whenever project policies evolve.

## Constitution Lifecycle

The constitution flow is command-driven through five subcommands:

| Command | Purpose |
|---------|---------|
| `spec-kitty constitution interview` | Capture policy decisions interactively (or `--defaults` for CI) |
| `spec-kitty constitution generate` | Produce YAML config and doctrine library from the constitution |
| `spec-kitty constitution context --action <action>` | Inject governance into a workflow step (specify, plan, implement, review) |
| `spec-kitty constitution status` | Show current sync state and detect drift |
| `spec-kitty constitution sync` | Re-derive all config from the constitution after manual edits |

The interview supports two profiles:

- **minimal** (8 questions) -- project intent, languages, testing, quality gates, review policy, performance targets, deployment constraints, and branching rules.
- **comprehensive** (11 questions) -- everything in minimal plus paradigm selection, doctrine references, and advanced tooling preferences.

Use `--defaults` for non-interactive bootstrapping or CI pipelines.

## Constitution Paths

Current bundle location:

1. `.kittify/constitution/constitution.md`
2. `.kittify/constitution/interview/answers.yaml`
3. `.kittify/constitution/references.yaml`
4. `.kittify/constitution/context-state.json` — first-load bootstrap tracking

Legacy compatibility is still handled for projects with older layout, but 2.x documentation treats `.kittify/constitution/` as canonical.

> **Note:** The `library/` subdirectory used in earlier builds has been removed.
> Shipped doctrine content is fetched at runtime from the packaged `src/doctrine/` tree;
> project-local support files are referenced via paths recorded in `references.yaml`.

## Available Directives and Paradigms

Directives are numbered project rules extracted from your constitution. Each has:

- **Severity** -- `error` (blocks workflow) or `warning` (advisory)
- **Action scope** -- which workflow actions the directive applies to (e.g., `implement`, `review`)

Paradigms are higher-level development philosophies your constitution can select:

- **TEST_FIRST** -- tests must be written before implementation code
- **LIBRARY_FIRST** -- prefer existing libraries over custom implementations
- **DOCS_ADJACENT** -- documentation lives alongside code, not in a separate tree

The constitution interview prompts you to select paradigms; they are then embedded in the governance config and referenced during `constitution context`.

## Runtime Template Resolution

When resolving templates and mission assets, 2.x uses ordered precedence:

1. Project override
2. Project legacy location
3. User-global mission-specific location
4. User-global location
5. Packaged doctrine mission defaults

Implementation references:

1. `src/specify_cli/runtime/resolver.py`
2. `src/specify_cli/runtime/home.py`

Primary implementation:

1. `src/specify_cli/cli/commands/constitution.py`
2. `src/specify_cli/constitution/compiler.py`
3. `src/specify_cli/constitution/context.py`

---

## Learn More

- **Step-by-step setup**: [How to Set Up Project Governance](../how-to/setup-governance.md) -- full walkthrough of interview, generate, and sync
- **Agent management**: [How to Manage Agents](../how-to/manage-agents.md) -- configure which agents receive governance context
- **Mission system**: [The Mission System Explained](../explanation/mission-system.md) -- how governance integrates with mission workflows
- **CLI reference**: [CLI Commands Reference](../reference/cli-commands.md) -- complete `constitution` subcommand details
