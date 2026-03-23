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

The typical governance workflow follows three steps:

1. **Interview** -- answer questions about your project's policies (testing, deployment, quality gates). This produces `answers.yaml` and a draft `constitution.md`.
2. **Generate** -- derive machine-readable config (`governance.yaml`, `directives.yaml`) and doctrine library files from the constitution. This step is deterministic: same constitution always produces the same output.
3. **Sync** -- after manually editing the constitution, re-derive all config to pick up changes. The `metadata.yaml` file tracks the constitution hash so drift detection can warn you when config is stale.

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

| Path | Contents |
|------|----------|
| `.kittify/constitution/constitution.md` | The authoritative policy document |
| `.kittify/constitution/interview/answers.yaml` | Structured interview responses |
| `.kittify/constitution/references.yaml` | Doctrine reference selections |
| `.kittify/constitution/library/*.md` | Generated guidance documents |

Legacy compatibility is still handled for projects with older layout, but 2.x documentation treats `.kittify/constitution/` as canonical.

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
