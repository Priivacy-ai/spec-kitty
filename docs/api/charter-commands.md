---
title: Charter CLI Reference
description: Full reference for all spec-kitty charter subcommands, verified against live --help output.
doc_status: active
updated: '2026-06-03'
related:
- docs/context/charter-overview.md
- docs/context/governance-files.md
---
# Charter CLI Reference

> **Note**: Examples use `uv run spec-kitty ...`, which is the source-checkout invocation. If
> Spec Kitty is installed on your PATH, the same flags work with `spec-kitty ...`.

This reference covers all `charter` subcommands. For a task-oriented walkthrough, see
[How to Synthesize and Maintain Doctrine](../guides/synthesize-doctrine.md).

---

## spec-kitty charter

**Synopsis**: `spec-kitty charter [OPTIONS] COMMAND [ARGS]...`

**Description**: Charter management commands.

| Subcommand | Description |
|---|---|
| `interview` | Capture charter interview answers for later generation |
| `generate` | Generate charter bundle from interview answers + doctrine references |
| `context` | Render charter context for a specific workflow action |
| `sync` | Sync charter.md to structured YAML config files |
| `status` | Display charter sync status plus synthesis/operator state |
| `synthesize` | Validate and promote agent-generated project-local doctrine artifacts |
| `resynthesize` | Regenerate a bounded set of project-local doctrine artifacts (partial resynthesis) |
| `lint` | Detect decay in charter artifacts via graph-native checks |
| `bundle` | Charter bundle validation commands |

---

## spec-kitty charter interview

**Synopsis**: `spec-kitty charter interview [OPTIONS]`

**Description**: Capture charter interview answers for later generation. Saves answers to
`.kittify/charter/interview/answers.yaml`.

| Flag | Description | Default |
|---|---|---|
| `--mission-type TEXT` | Mission type for charter defaults | `software-dev` |
| `--profile TEXT` | Interview profile: `minimal` or `comprehensive` | `minimal` |
| `--defaults` | Use deterministic defaults without prompts | — |
| `--selected-paradigms TEXT` | Comma-separated paradigm IDs override | — |
| `--selected-directives TEXT` | Comma-separated directive IDs override | — |
| `--available-tools TEXT` | Comma-separated tool IDs override | — |
| `--mission-slug TEXT` | Mission slug for Decision Moment paper trail (optional) | — |
| `--json` | Output JSON | — |

**Examples**:
```bash
# Interactive minimal interview
uv run spec-kitty charter interview

# Non-interactive with defaults
uv run spec-kitty charter interview --profile minimal --defaults --json

# Comprehensive profile
uv run spec-kitty charter interview --profile comprehensive
```

---

## spec-kitty charter generate

**Synopsis**: `spec-kitty charter generate [OPTIONS]`

**Description**: Generate charter bundle from interview answers + doctrine references. On success
in a git working tree, the generated charter commit inputs are auto-staged for the follow-up
`spec-kitty safe-commit` step. Requires a git working tree — exits non-zero
outside git repos with a `git init` remediation message. With `--from-interview`, missing
interview answers fail closed; use `--no-from-interview` to opt into defaults.

| Flag | Description | Default |
|---|---|---|
| `--mission-type TEXT` | Mission type for template-set defaults | — |
| `--template-set TEXT` | Override doctrine template set (must exist in packaged doctrine missions) | — |
| `--from-interview` / `--no-from-interview` | Load interview answers if present | `--from-interview` |
| `--profile TEXT` | Default profile when no interview is available | `minimal` |
| `--force`, `-f` | Overwrite existing charter bundle | — |
| `--json` | Output JSON | — |

**Examples**:
```bash
# Generate from interview answers
uv run spec-kitty charter generate --from-interview --json

# Force regenerate
uv run spec-kitty charter generate --from-interview --force --json

# Override template set
uv run spec-kitty charter generate --from-interview --template-set documentation-default
```

## spec-kitty charter synthesize

**Synopsis**: `spec-kitty charter synthesize [OPTIONS]`

**Description**: Validate and promote agent-generated project-local doctrine artifacts. Reads the
charter interview answers, resolves synthesis targets from the DRG + doctrine, and writes all
artifacts to `.kittify/doctrine/`.

On a fresh project where `.kittify/charter/generated/` is missing or empty, this command
materializes the minimal artifact set (directory marker and `PROVENANCE.md`) without running the
full adapter pipeline. The runtime falls back to built-in doctrine until a full synthesis run
completes.

| Flag | Description | Default |
|---|---|---|
| `--adapter TEXT` | Adapter to use: `generated` (validates agent-authored YAML under `.kittify/charter/generated/`) or `fixture` (offline/testing only) | `generated` |
| `--dry-run` | Stage and validate artifacts but do not promote to live tree | — |
| `--json` | Output JSON | — |
| `--skip-code-evidence` | Skip code-reading evidence collection | — |
| `--skip-corpus` | Skip best-practice corpus loading | — |
| `--dry-run-evidence` | Print evidence summary and exit without running synthesis | — |

**Examples**:
```bash
# Validate + promote generated artifacts
uv run spec-kitty charter synthesize

# Dry-run (preview without promoting)
uv run spec-kitty charter synthesize --dry-run

# Use fixture adapter (offline/testing)
uv run spec-kitty charter synthesize --adapter fixture
```

---

## spec-kitty charter resynthesize

**Synopsis**: `spec-kitty charter resynthesize [OPTIONS]`

**Description**: Regenerate a bounded set of project-local doctrine artifacts (partial
resynthesis). Uses a structured selector to identify the target set. Unrelated artifacts are
never touched.

Selector forms:
- `directive:PROJECT_001` — regenerate a specific project directive
- `tactic:how-we-apply-directive-003` — regenerate one tactic
- `directive:DIRECTIVE_003` — regenerate every artifact whose provenance references the built-in DIRECTIVE_003 URN
- `testing-philosophy` — regenerate all artifacts from that interview section

| Flag | Description | Default |
|---|---|---|
| `--topic TEXT` | Structured topic selector: `<kind>:<slug>` (project-local), `<drg-urn>` (built-in+project graph), or `<interview-section-label>` | — |
| `--list-topics` | List valid structured topic selectors and exit | — |
| `--adapter TEXT` | Adapter to use (`generated` or `fixture`) | `generated` |
| `--skip-code-evidence` | Skip code-reading evidence collection | — |
| `--skip-corpus` | Skip best-practice corpus loading | — |
| `--json` | Output JSON | — |

**Examples**:
```bash
# Resynthesize a single tactic
uv run spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003

# Resynthesize all artifacts referencing a built-in directive
uv run spec-kitty charter resynthesize --topic directive:DIRECTIVE_003

# List valid topic selectors
uv run spec-kitty charter resynthesize --list-topics
```

---

## spec-kitty charter status

**Synopsis**: `spec-kitty charter status [OPTIONS]`

**Description**: Display charter sync status plus synthesis/operator state.

| Flag | Description | Default |
|---|---|---|
| `--json` | Output JSON | — |
| `--provenance` | Include per-artifact provenance details | — |

**Examples**:
```bash
uv run spec-kitty charter status
uv run spec-kitty charter status --json
uv run spec-kitty charter status --provenance
```

---

## spec-kitty charter sync

**Synopsis**: `spec-kitty charter sync [OPTIONS]`

**Description**: Sync `charter.md` to structured YAML config files (`governance.yaml`,
`directives.yaml`, `metadata.yaml`). This is a different operation from `charter synthesize` —
sync updates the YAML config from prose; synthesize promotes DRG-backed doctrine artifacts.

Run sync after manually editing `charter.md`. Sync is idempotent.

Sync input is always `.kittify/charter/charter.md` as resolved by the project root. If that path
is a regular hand-authored file, its current markdown content is extracted. If it is a generated
copy, sync extracts the generated copy and does not refresh it from the upstream document. If it is
a symlink, sync follows the symlink for reads; the generated YAML files are still written into
`.kittify/charter/`, not beside the symlink target. `charter generate` refuses to overwrite a
symlinked `charter.md` before compilation, sync, gitignore updates, or staging; use symlinks only
for sync-only extraction or update the target directly. See
[Governance Files Reference](../context/governance-files.md#external-governance-documents) for the
source-of-truth model when a project also has a public constitution.

| Flag | Description | Default |
|---|---|---|
| `--force`, `-f` | Force sync even if not stale | — |
| `--json` | Output JSON | — |

**Examples**:
```bash
uv run spec-kitty charter sync
uv run spec-kitty charter sync --force --json
```

---

## spec-kitty charter lint

**Synopsis**: `spec-kitty charter lint [OPTIONS]`

**Description**: Detect decay in charter artifacts via graph-native checks. Checks for orphaned
artifacts, contradictions between directives, and staleness (provenance points to a deleted
or superseded built-in directive).

| Flag | Description | Default |
|---|---|---|
| `--mission TEXT` | Scope lint to a specific mission slug | — |
| `--orphans` | Run only orphan checks | — |
| `--contradictions` | Run only contradiction checks | — |
| `--stale` | Run only staleness checks | — |
| `--json` | Output findings as JSON | — |
| `--severity TEXT` | Minimum severity (`low`/`medium`/`high`/`critical`) | `low` |

**Examples**:
```bash
uv run spec-kitty charter lint
uv run spec-kitty charter lint --severity high
uv run spec-kitty charter lint --orphans --json
uv run spec-kitty charter lint --mission my-feature-slug
```

---

## spec-kitty charter context

**Synopsis**: `spec-kitty charter context [OPTIONS]`

**Description**: Render charter context for a specific workflow action. This is a runtime/debug
command for inspecting what governance context an agent would receive. It is not part of the
synthesis pipeline.

| Flag | Description | Default |
|---|---|---|
| `--action TEXT` | Workflow action (`specify`, `plan`, `implement`, `review`) | **required** |
| `--mark-loaded` / `--no-mark-loaded` | Persist first-load state | `--mark-loaded` |
| `--json` | Output JSON | — |

**Examples**:
```bash
# Render context for the implement action
uv run spec-kitty charter context --action implement --json

# Render without persisting first-load state (for debugging)
uv run spec-kitty charter context --action specify --no-mark-loaded --json
```

---

## spec-kitty charter bundle validate

**Synopsis**: `spec-kitty charter bundle validate [OPTIONS]`

**Description**: Validate the charter bundle against CharterBundleManifest v1.0.0. Verifies
that all required files are present, correctly structured, and consistent.

| Flag | Description | Default |
|---|---|---|
| `--json` | Emit structured JSON to stdout instead of a human-readable report | — |

**Examples**:
```bash
uv run spec-kitty charter bundle validate
uv run spec-kitty charter bundle validate --json
```

---

## See Also

- [How Charter Works](../context/charter-overview.md)
- [How to Synthesize and Maintain Doctrine](../guides/synthesize-doctrine.md)
- [Governance Files Reference](../context/governance-files.md)
