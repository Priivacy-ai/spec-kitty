# Charter Command Map

Complete CLI reference for `spec-kitty charter` subcommands.

---

## interview

Capture charter interview answers for later generation.

```bash
spec-kitty charter interview --mission software-dev [--profile minimal|comprehensive] [--defaults] [--json]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--mission` | TEXT | `software-dev` | Mission key for charter defaults |
| `--profile` | TEXT | `minimal` | Interview profile: `minimal` or `comprehensive` |
| `--defaults` | FLAG | off | Use deterministic defaults without prompts |
| `--selected-paradigms` | TEXT | none | Comma-separated paradigm ID overrides |
| `--selected-directives` | TEXT | none | Comma-separated directive ID overrides |
| `--available-tools` | TEXT | none | Comma-separated tool ID overrides |
| `--json` | FLAG | off | Output JSON |

**Output file:** `.kittify/charter/interview/answers.yaml`

**JSON output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if interview completed |
| `interview_path` | string | Relative path to answers file |
| `mission` | string | Mission key used |
| `profile` | string | Profile used (minimal or comprehensive) |
| `selected_paradigms` | list | Active paradigm IDs |
| `selected_directives` | list | Active directive IDs |
| `available_tools` | list | Active tool IDs |

**Profiles:**

- `minimal` -- Asks a reduced set of essential questions. Use for fast bootstrapping.
- `comprehensive` -- Asks all questions. Use for thorough policy capture.

---

## generate

Generate the charter bundle from interview answers and doctrine references.

```bash
spec-kitty charter generate [--mission TEXT] [--force] [--from-interview] [--json]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--mission` | TEXT | from interview | Override mission key |
| `--force` | FLAG | off | Overwrite existing charter |
| `--from-interview / --no-from-interview` | FLAG | on | Load interview answers if present |
| `--profile` | TEXT | `minimal` | Default profile when no interview is available |
| `--json` | FLAG | off | Output JSON |

**Output files:**

- `.kittify/charter/charter.md` -- The charter document
- `.kittify/charter/governance.yaml` -- Extracted governance config
- `.kittify/charter/directives.yaml` -- Extracted directives
- `.kittify/charter/metadata.yaml` -- Extraction provenance
- `.kittify/charter/references.yaml` -- Reference doc manifest
- `.kittify/charter/library/*.md` -- Referenced doctrine documents

**JSON output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if generation completed |
| `charter_path` | string | Relative path to charter.md |
| `interview_source` | string | `interview` or `defaults` |
| `mission` | string | Mission key used |
| `template_set` | string | Doctrine template set applied |
| `selected_paradigms` | list | Active paradigm IDs |
| `selected_directives` | list | Active directive IDs |
| `available_tools` | list | Active tool IDs |
| `references_count` | int | Number of reference docs written |
| `files_written` | list | All files written during generation |
| `diagnostics` | list | Warning or info messages from compilation |

**Notes:**

- Generation automatically triggers sync, so extracted YAML is always current.
- If `--from-interview` is true (default) but no interview file exists, generation falls back to defaults for the specified mission and profile.
- Use `--force` when re-generating over an existing charter.

---

## context

Render charter context for a specific workflow action.

```bash
spec-kitty charter context --action specify|plan|implement|review [--json]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--action` | TEXT | required | Workflow action (specify, plan, implement, review) |
| `--mark-loaded / --no-mark-loaded` | FLAG | on | Persist first-load state |
| `--json` | FLAG | off | Output JSON |

**JSON output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if context was built |
| `action` | string | Normalized action name |
| `mode` | string | `bootstrap`, `compact`, or `missing` |
| `first_load` | bool | True if this is the first load for this action |
| `references_count` | int | Number of reference docs available |
| `text` | string | Rendered governance context text |

**Context modes:**

- `bootstrap` -- First load for a bootstrap action. Returns full policy summary and reference doc list.
- `compact` -- Subsequent load. Returns resolved paradigms, directives, and tools only.
- `missing` -- No charter file exists. Returns instructions to create one.

**State tracking:** First-load state is persisted in `.kittify/charter/context-state.json`. Pass `--no-mark-loaded` to query context without updating state.

---

## sync

Sync charter.md to structured YAML config files.

```bash
spec-kitty charter sync [--force] [--json]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--force` | FLAG | off | Force sync even if charter is not stale |
| `--json` | FLAG | off | Output JSON |

**Output files (written to `.kittify/charter/`):**

| File | Content |
|------|---------|
| `governance.yaml` | Testing, quality, commit, performance, branch strategy config |
| `directives.yaml` | Numbered rules with severity and scope |
| `metadata.yaml` | Extraction provenance (hash, timestamp, extraction mode) |

**JSON output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if sync ran (false if skipped or errored) |
| `stale_before` | bool | True if charter was stale before sync |
| `files_written` | list | YAML file names written |
| `extraction_mode` | string | `deterministic` or `hybrid` |
| `error` | string or null | Error message if sync failed |

**Staleness detection:** Sync compares the SHA-256 hash of `charter.md` against the hash stored in `metadata.yaml`. If they match and `--force` is not set, sync is skipped.

---

## status

Display charter sync status.

```bash
spec-kitty charter status [--json]
```

**Flags:**

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--json` | FLAG | off | Output JSON |

**JSON output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `charter_path` | string | Relative path to charter.md |
| `status` | string | `synced` or `stale` |
| `current_hash` | string | SHA-256 hash of current charter.md |
| `stored_hash` | string | Hash from last sync (from metadata.yaml) |
| `last_sync` | string or null | ISO timestamp of last successful sync |
| `library_docs` | int | Number of library documents |
| `files` | list | Per-file existence and size info |

---

## Common Workflows

**Bootstrap a new project with deterministic defaults:**

```bash
spec-kitty charter interview --mission-type software-dev --profile minimal --defaults --json
spec-kitty charter generate --from-interview --json
```

This is a CLI fallback. For agent-mediated `/spec-kitty.charter`, prefer a chat
interview and write `answers.yaml` directly before generation.

**Full interactive CLI setup:**

```bash
spec-kitty charter interview --mission-type software-dev --profile comprehensive
spec-kitty charter generate --from-interview
```

**Update after manual charter edits:**

```bash
spec-kitty charter sync --json
spec-kitty charter status --json
```

**Inspect governance for one workflow action (debugging only):**

```bash
spec-kitty charter context --action implement --json --no-mark-loaded
```

**Force regeneration:**

```bash
spec-kitty charter generate --from-interview --force --json
```

Do not chain all four action-context calls after generation. That dumps large
bootstrap payloads into the agent context and consumes first-load state before
the real workflow reaches those actions.
