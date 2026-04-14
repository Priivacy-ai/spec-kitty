# Data Model: Agent Skills Support for Codex and Vibe

**Feature**: 083-agent-skills-codex-vibe
**Status**: Phase 1 design

## Entities

### SkillPackage *(on-disk artifact)*

A directory produced by the renderer and written by the installer.

| Field | Type | Description |
|-------|------|-------------|
| `directory` | `Path` | `<repo>/.agents/skills/spec-kitty.<command>/` |
| `skill_md` | `Path` | `<directory>/SKILL.md` — required |
| `body_files` | `list[Path]` | Optional supplementary files referenced from `SKILL.md` (none in the initial release; reserved for future commands that embed long references) |

Invariants:
- Directory name matches `spec-kitty.<command>` where `<command>` is one of the 16 canonical commands.
- `SKILL.md` is always present and has YAML frontmatter with at least `name` and `description`.
- Directory lives under `.agents/skills/` (project-local); global installation is out of scope for this release.

### RenderedSkill *(in-memory)*

The renderer's return type. Deliberately separate from on-disk state so tests can assert byte-for-byte output without writing to disk.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | `spec-kitty.<command>` |
| `frontmatter` | `dict[str, Any]` | Parsed and ready to serialize. Keys in insertion-order sorted for determinism. |
| `body` | `str` | The transformed markdown body. The `## User Input` block has already been rewritten. |
| `source_template` | `Path` | Absolute path to the source `command-templates/<command>.md` |
| `source_hash` | `str` | SHA-256 of the source template content at render time |
| `agent_key` | `Literal["codex", "vibe"]` | The agent this rendering was produced for |
| `spec_kitty_version` | `str` | CLI version string the renderer ran under |

Invariants:
- `frontmatter["name"] == name`.
- `frontmatter["description"]` is non-empty.
- `body` does not contain the literal token `$ARGUMENTS` anywhere.
- Serializing `(frontmatter, body)` to `SKILL.md` is pure: same input, byte-identical output.

### SkillsManifest *(persisted at `.kittify/command-skills-manifest.json`)*

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | `int` | `1` for the initial release |
| `entries` | `list[ManifestEntry]` | One entry per installed skill package |

Stored with sorted keys and trailing newline for minimal git diffs.

### ManifestEntry

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Relative to repo root, POSIX-style (`.agents/skills/spec-kitty.specify/SKILL.md`) |
| `content_hash` | `str` | SHA-256 of the `SKILL.md` content as written |
| `agents` | `list[str]` | Sorted list of agent keys that installed this entry (e.g., `["codex", "vibe"]`) |
| `installed_at` | `str` | ISO-8601 UTC timestamp at which the entry was first written |
| `spec_kitty_version` | `str` | CLI version that wrote the entry |

Invariants:
- `path` is always normalized POSIX; `Path(path)` resolves inside `.agents/skills/`.
- `agents` is sorted ASCII-ascending and contains no duplicates.
- `content_hash` is recomputed on every write; drift between on-disk content and `content_hash` is a doctor-reportable error.
- When the installer removes the last agent from `agents`, the entry is removed from `entries` and the file is physically deleted.

State transitions for an entry:
```
(not in manifest)
     │ install(agent)
     ▼
{path, hash, agents=[agent]}
     │ install(other_agent)
     ▼
{path, hash, agents=[agent, other_agent]}
     │ remove(agent)
     ▼
{path, hash, agents=[other_agent]}
     │ remove(other_agent)
     ▼
(not in manifest + file deleted)
```

### LegacyCodexPrompt *(migration-only)*

Used exclusively by `m_3_2_0_codex_to_skills.py`; not persisted.

| Field | Type | Description |
|-------|------|-------------|
| `path` | `Path` | Absolute path under `.codex/prompts/` |
| `current_hash` | `str` | SHA-256 of the file's current content |
| `previous_version_hash` | `str` | The hash the previous Spec Kitty renderer would have produced for this canonical command |
| `status` | `Literal["owned_unedited", "owned_edited", "third_party"]` | Classification used to decide migration action |

Classification rule:
- `current_hash == previous_version_hash` and filename matches `spec-kitty.*.md` → `owned_unedited` → delete after new skill is installed.
- `current_hash != previous_version_hash` but filename matches `spec-kitty.*.md` → `owned_edited` → preserve and notify user.
- Filename does not match `spec-kitty.*.md` → `third_party` → ignore entirely.

## Relationships

```
CommandTemplate (src/specify_cli/missions/*/command-templates/*.md)
    │
    │ read by renderer
    ▼
RenderedSkill (in-memory, per agent_key in {codex, vibe})
    │
    │ written by installer
    ▼
SkillPackage on disk (.agents/skills/spec-kitty.<command>/)
    │
    │ recorded by installer
    ▼
ManifestEntry ──► SkillsManifest (.kittify/command-skills-manifest.json)
```

Migration path:
```
LegacyCodexPrompt (classify)
    ├─ owned_unedited → delete file; call installer(codex) for the canonical command
    ├─ owned_edited   → keep file; call installer(codex); print notice
    └─ third_party    → leave untouched
```

## Validation rules

- No two `ManifestEntry` records share a `path`.
- For every `ManifestEntry.path`, the canonical command segment must match one of the 16 known commands; entries for unknown commands are rejected at load time with a doctor-reportable error.
- `agents` values must be in the set `{"codex", "vibe"}` for entries produced by this mission. Future agents added to this pipeline will extend the set; the validator accepts any value present in `AGENT_SKILL_CONFIG` with class `SKILL_CLASS_SHARED`.
- Manifest load must be resilient to unknown future top-level fields (ignore with a warning) but strict about known fields (reject on type mismatch).
