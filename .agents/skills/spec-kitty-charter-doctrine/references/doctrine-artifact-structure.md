# Doctrine Artifact Structure

File layout, authority classes, and data flow for the charter subsystem.

---

## Directory Layout

```
.kittify/charter/
  charter.md                  # Authoritative governance document
  governance.yaml             # Derived: testing, quality, commits, performance, branching
  directives.yaml             # Derived: numbered rules with severity and scope
  references.yaml             # Derived: manifest of reference docs
  metadata.yaml               # Derived: extraction provenance (hash, timestamp, mode)
  context-state.json          # Runtime: tracks first-load state per action
  interview/
    answers.yaml              # Authoritative: captured interview responses
  library/
    *.md                      # Derived: doctrine reference documents
```

---

## Authority Classes

Each file has an authority class that determines how it should be treated.

| File | Authority | Meaning |
|------|-----------|---------|
| `charter.md` | **Authoritative** | Single source of truth for governance. Edit this file to change policy. |
| `interview/answers.yaml` | **Authoritative** | Captured interview input. Re-run interview or edit directly to change. |
| `governance.yaml` | **Derived** | Auto-generated from charter.md by sync. Do not edit directly. |
| `directives.yaml` | **Derived** | Auto-generated from charter.md by sync. Do not edit directly. |
| `references.yaml` | **Derived** | Auto-generated during charter generation. Do not edit directly. |
| `metadata.yaml` | **Derived** | Extraction provenance. Written by sync. Do not edit directly. |
| `context-state.json` | **Runtime** | Tracks which actions have loaded context. Safe to delete (resets first-load state). |
| `library/*.md` | **Derived** | Copied from doctrine templates during generation. Do not edit directly. |

**Rule:** Only edit files with **Authoritative** authority. All **Derived** files are
overwritten by sync or generate. Edits to derived files will be lost.

---

## Data Flow

```
Interview Answers (answers.yaml)
        |
        v
    [generate]  <-- doctrine templates + mission config
        |
        v
Charter (charter.md)  <-- authoritative source
        |
        v
      [sync]  <-- deterministic extraction
        |
        +---> governance.yaml
        +---> directives.yaml
        +---> metadata.yaml


Charter (charter.md)
        |
        v
    [context]  <-- reads governance.yaml + references.yaml
        |
        v
Agent Prompt Context  <-- injected into specify/plan/implement/review
```

**Key points:**

1. `generate` reads interview answers and produces `charter.md` plus
   all derived files (it triggers sync automatically).
2. `sync` reads `charter.md` and writes `governance.yaml`,
   `directives.yaml`, and `metadata.yaml`.
3. `context` reads the derived YAML files and renders governance text
   for injection into agent prompts.
4. Manual edits to `charter.md` require a `sync` to update derived files.

---

## governance.yaml Schema

Top-level keys and their purpose:

| Key | Type | Description |
|-----|------|-------------|
| `testing.min_coverage` | int | Minimum test coverage percentage (0 = not enforced) |
| `testing.tdd_required` | bool | Whether TDD is mandated |
| `testing.framework` | string | Test framework name (e.g., "pytest") |
| `testing.type_checking` | string | Type checking tool (e.g., "mypy") |
| `quality.linting` | string | Linting tool (e.g., "ruff") |
| `quality.pr_approvals` | int | Required PR approvals before merge |
| `quality.pre_commit_hooks` | bool | Whether pre-commit hooks are required |
| `commits.convention` | string | Commit message convention (e.g., "conventional") |
| `performance.cli_timeout_seconds` | float | Max CLI command duration |
| `performance.dashboard_max_wps` | int | Max WPs the dashboard can display |
| `branch_strategy.main_branch` | string | Name of the main branch |
| `branch_strategy.dev_branch` | string or null | Name of the dev branch |
| `branch_strategy.rules` | list | Branch naming and protection rules |
| `doctrine.selected_paradigms` | list | Active paradigm IDs |
| `doctrine.selected_directives` | list | Active directive IDs |
| `doctrine.available_tools` | list | Active tool IDs |
| `doctrine.template_set` | string or null | Doctrine template set |
| `enforcement` | dict | Enforcement policy by domain |

---

## directives.yaml Schema

Contains a list of numbered directives:

```yaml
directives:
  - id: "D001"
    title: "All PRs require tests"
    description: "Every pull request must include test coverage for new code."
    severity: "error"        # error | warn | info
    applies_to:              # workflow actions where this directive fires
      - "implement"
      - "review"
```

**Severity levels:**

| Severity | Runtime effect |
|----------|---------------|
| `error` | Blocks workflow progression |
| `warn` | Displayed as warning, does not block |
| `info` | Informational, logged only |

---

## metadata.yaml Schema

Extraction provenance written by sync:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | string | Schema version (currently "1.0.0") |
| `extracted_at` | string | ISO 8601 timestamp of last extraction |
| `charter_hash` | string | SHA-256 hash of charter.md at extraction time |
| `source_path` | string | Relative path to charter.md |
| `extraction_mode` | string | `deterministic` or `hybrid` |
| `sections_parsed.structured` | int | Sections parsed deterministically |
| `sections_parsed.ai_assisted` | int | Sections that required AI assistance |
| `sections_parsed.skipped` | int | Sections that could not be parsed |

---

## Git Tracking

| Path | Git status | Reason |
|------|------------|--------|
| `.kittify/charter/charter.md` | Tracked | Authoritative governance document, shared across team |
| `.kittify/charter/interview/answers.yaml` | Tracked | Authoritative interview input, shared across team |
| `.kittify/charter/governance.yaml` | Tracked | Derived but committed for CI/tool access without running sync |
| `.kittify/charter/directives.yaml` | Tracked | Derived but committed for CI/tool access |
| `.kittify/charter/references.yaml` | Tracked | Derived but committed for reference resolution |
| `.kittify/charter/metadata.yaml` | Tracked | Derived but committed for staleness detection |
| `.kittify/charter/context-state.json` | Ignored | Local runtime state, not shared |
| `.kittify/charter/library/*.md` | Tracked | Derived but committed for offline reference access |

---

## Governance Anti-Patterns

| Anti-Pattern | Why It Fails | Correct Approach |
|-------------|-------------|-----------------|
| Editing `governance.yaml` directly | Overwritten on next sync | Edit `charter.md`, then run `sync` |
| Editing `directives.yaml` directly | Overwritten on next sync | Edit `charter.md`, then run `sync` |
| Deleting `metadata.yaml` | Breaks staleness detection; next sync always runs | Let sync manage this file |
| Editing `library/*.md` files | Overwritten on next `generate` | Edit doctrine source templates upstream |
| Skipping `sync` after manual edits | Runtime reads stale governance config | Always run `sync` after editing `charter.md` |
| Assuming `.kittify/memory/` is current | Legacy path; only used as compatibility fallback | Use `.kittify/charter/` for all new projects |
