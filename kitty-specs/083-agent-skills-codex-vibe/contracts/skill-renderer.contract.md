# Contract: Command-Skill Renderer and Installer

**Feature**: 083-agent-skills-codex-vibe
**Modules**: `src/specify_cli/skills/command_renderer.py`, `src/specify_cli/skills/command_installer.py`, `src/specify_cli/skills/manifest_store.py`
**Status**: Phase 1 contract (to be realized in implementation)

This contract defines the inputs, outputs, invariants, and error conditions for the three new modules introduced by feature 083. It is the single source of truth against which unit and integration tests are written.

## Scope

The renderer and installer in this contract are **scoped to Codex and Vibe only**. They do not touch the command-file rendering pipeline used by the twelve command-layer agents. That pipeline remains byte-identical per NFR-005.

## Module: `command_renderer`

### `render(template_path, agent_key, spec_kitty_version) -> RenderedSkill`

**Inputs**:
- `template_path: Path` — absolute path to a `command-templates/<command>.md` file.
- `agent_key: Literal["codex", "vibe"]` — the agent this rendering is produced for. The renderer may return slightly different frontmatter by agent (but in practice the initial release produces identical frontmatter for both; see §Frontmatter below).
- `spec_kitty_version: str` — the current CLI version string, captured in the returned record for auditability.

**Returns**: a `RenderedSkill` (see `data-model.md`).

**Behavior**:
1. Read `template_path` as UTF-8 text. Record SHA-256 of the raw content as `source_hash`.
2. Identify the `## User Input` section: the markdown heading `## User Input` through (exclusive) the next markdown heading at the same or shallower level.
3. **Replace** the identified section with a fixed-shape instruction block that tells the model to treat the invocation turn's free-form content as User Input. The replacement shape is:

   ```markdown
   ## User Input

   The content of the user's message that invoked this skill (everything after the skill invocation token, e.g. after `/spec-kitty.<command>` or `$spec-kitty.<command>`) is the User Input referenced elsewhere in these instructions.

   You **MUST** consider this user input before proceeding (if not empty).
   ```

   The exact text is locked by a snapshot test; it must not drift without an intentional update.

4. Scan the resulting body for the literal token `$ARGUMENTS`. Any occurrence raises `SkillRenderError` with the template path, 1-indexed line number, and the offending line's text. This guards against future template edits silently regressing Codex/Vibe output.
5. Build the frontmatter (see §Frontmatter) and return a `RenderedSkill`.

**Invariants**:
- Pure function: same `(template_path, agent_key, spec_kitty_version)` returns byte-identical `frontmatter` + `body`.
- The returned `body` does not contain `$ARGUMENTS`.
- `RenderedSkill.name == "spec-kitty." + <command>`.

**Errors**:
- `SkillRenderError("template_not_found", path=...)` — `template_path` does not exist or is not readable.
- `SkillRenderError("user_input_block_missing", path=...)` — the template does not contain a `## User Input` section. (All 16 canonical templates have one today; this error guards against template drift.)
- `SkillRenderError("stray_arguments_token", path=..., line=..., excerpt=...)` — a `$ARGUMENTS` token survived transformation, i.e. existed outside the `## User Input` section.
- `SkillRenderError("unsupported_agent", agent_key=...)` — `agent_key` is not in `{"codex", "vibe"}`.

### Frontmatter

The initial release emits the same frontmatter for both `codex` and `vibe`:

```yaml
---
name: spec-kitty.<command>
description: <first sentence of the template's "Purpose" heading, trimmed to ≤140 chars; fallback to the command name if absent>
user-invocable: true
---
```

Notes:
- `allowed-tools` is intentionally omitted (null). Both agents accept its absence.
- `license` and `compatibility` (Vibe-specific optional fields) are intentionally omitted to keep a single frontmatter shape across agents.
- Keys are emitted in the order shown above for diff-stability.

If an agent's frontmatter requirements diverge in a future release, this contract grows an agent-keyed overlay dict. The renderer is designed to accommodate that without changing its public signature.

## Module: `command_installer`

### `install(repo_root, agent_key) -> InstallReport`

**Inputs**:
- `repo_root: Path` — absolute path to the project root (the directory containing `.kittify/`).
- `agent_key: Literal["codex", "vibe"]`.

**Returns**: an `InstallReport` dataclass with counts of `added`, `already_installed` (idempotent hits), `reused_shared` (existing entry, added this agent to its `agents` list), and `errors`.

**Behavior**:
1. Load `manifest_store.load(repo_root)`. Treat missing file as empty manifest.
2. For each of the 16 canonical commands:
   - Call `command_renderer.render(...)` to get a `RenderedSkill`.
   - Compute the install path `<repo>/.agents/skills/spec-kitty.<command>/SKILL.md`.
   - If the manifest already has an entry for this path and the on-disk hash matches the manifest hash: add `agent_key` to the entry's `agents` list (if not already present). Counted as `reused_shared` or `already_installed`.
   - Otherwise: write the file (creating parent directories as needed), record a new manifest entry with `agents=[agent_key]`, `content_hash=<sha256 of written bytes>`, `installed_at=<now UTC>`, `spec_kitty_version=<current>`. Counted as `added`.
3. Call `manifest_store.save(repo_root, manifest)`.

**Invariants**:
- Idempotent: running `install` twice for the same `agent_key` on the same `repo_root` with the same CLI version produces identical on-disk state and an identical manifest.
- Third-party safety: no file outside the manifest is touched. Specifically, the installer never deletes, never overwrites, and never renames files that are not in the manifest.
- Atomic-per-file: each write uses the standard "write to temp + rename" pattern so a crashed install leaves at most one in-progress file behind.

**Errors**:
- Bubble up any `SkillRenderError` from the renderer with additional context (which command was being installed).
- `InstallerError("manifest_parse_failed")` — manifest exists but is corrupt. Operator must resolve (doctor can help).
- `InstallerError("unexpected_collision", path=...)` — a path in the manifest exists on disk with a hash that does not match the manifest **and** we are not currently installing this entry. Drift must be resolved before proceeding.

### `remove(repo_root, agent_key) -> RemoveReport`

**Inputs**: same `repo_root`, `agent_key`.

**Returns**: a `RemoveReport` with counts of `deref` (agent dropped from an entry), `deleted` (entry became empty, file removed), and `kept` (entry still has other agents).

**Behavior**:
1. Load the manifest.
2. For every entry whose `agents` contains `agent_key`: drop `agent_key` from `agents`.
3. If an entry's `agents` is now empty: physically delete the file. If the parent `spec-kitty.<command>/` directory is empty after the file deletion, remove the directory. Remove the entry from `manifest.entries`.
4. Save the manifest.

**Invariants**:
- Third-party safety: only files listed in the manifest are ever deleted. Never recursively delete anything under `.agents/skills/` that we didn't install.
- Reference counting is load-bearing: an entry retained because another agent still needs it must be left byte-identical.

**Errors**:
- `InstallerError("manifest_entry_not_found", agent_key=...)` — `agent_key` is not referenced by any entry. In practice the CLI would still report success (nothing to do); this error is reserved for programmatic callers that expect changes.
- `InstallerError("file_mutation_detected", path=...)` — entry's on-disk hash differs from the manifest hash. Abort removal for that entry and surface via doctor.

### `verify(repo_root) -> VerifyReport`

**Returns**: a `VerifyReport` with three lists:
- `drift`: manifest entries whose on-disk SHA-256 no longer matches the stored hash.
- `orphans`: files under `.agents/skills/spec-kitty.*/` that are not in the manifest.
- `gaps`: manifest entries whose files are missing from disk.

**Behavior**: read-only. Never mutates the manifest or filesystem. Used by `spec-kitty doctor` and `spec-kitty verify-setup`.

## Module: `manifest_store`

### `load(repo_root) -> SkillsManifest`

- Reads `.kittify/skills-manifest.json`. Returns an empty manifest (`schema_version=1`, `entries=[]`) if the file does not exist.
- Rejects manifests whose `schema_version` is not `1` with `ManifestError("unsupported_schema_version")`.
- Rejects manifests that fail the JSON schema (`contracts/skills-manifest.schema.json`) with `ManifestError("schema_validation_failed", details=...)`.
- Tolerates unknown top-level fields (logs a warning and drops them at save time, unless `strict=True`).

### `save(repo_root, manifest) -> None`

- Writes `.kittify/skills-manifest.json` with sorted keys, 2-space indent, and a trailing newline.
- `entries` are sorted by `path` before write, for deterministic diffs.
- Uses temp-file + rename for atomic replacement.

### `fingerprint(content_bytes) -> str`

- Returns the SHA-256 hex digest used everywhere in this module.
- Kept as a helper so tests can assert hash behavior without touching disk.

## Interaction with existing modules

- `src/specify_cli/core/config.py` — `AGENT_COMMAND_CONFIG` loses its `"codex"` entry. `AGENT_SKILL_CONFIG` gains an entry for `"vibe"` with class `SKILL_CLASS_SHARED` and `skill_roots: [".agents/skills/"]`. `AI_CHOICES` gains `"vibe": "Mistral Vibe"`.
- `src/specify_cli/agent_utils/directories.py` — `AGENT_DIRS` loses the `(".codex", "prompts")` tuple and gains an entry for vibe (if the registry is used for operations other than command-file writing; otherwise it only loses codex's entry). `AGENT_DIR_TO_KEY` is updated correspondingly.
- `src/specify_cli/runtime/agent_commands.py` — for `agent_key in {"codex", "vibe"}`, call `command_installer.install(repo_root, agent_key)` instead of the command-file rendering path. For all other agents, behavior is unchanged.
- `src/specify_cli/cli/commands/agent/config.py` — `remove` calls `command_installer.remove(repo_root, agent_key)` for codex/vibe. For other agents, behavior is unchanged.
- `src/specify_cli/gitignore_manager.py` — adds `.vibe/` (and any documented vibe runtime-state paths) to the protected-pattern set, behind the shared helper that already handles agent-specific protections.
- `src/specify_cli/upgrade/migrations/m_3_2_0_codex_to_skills.py` (new) — uses `command_installer.install(repo_root, "codex")` and the LegacyCodexPrompt classification rules from `data-model.md` to produce a zero-touch upgrade.

## Testing contract

Every function documented above must have direct unit tests. In addition, the following end-to-end properties must be asserted:

1. **Determinism (NFR-004)**: rendering the same 16 templates twice produces byte-identical output. Snapshot test.
2. **Additive install (FR-006)**: seeding `.agents/skills/` with three third-party directories and then running `install("codex")` and `install("vibe")` leaves those directories byte-identical.
3. **Selective remove (FR-008)**: after `install("codex")` + `install("vibe")`, calling `remove("codex")` keeps every file on disk with `content_hash` unchanged and the manifest entries' `agents=["vibe"]`.
4. **Reference-counted delete (NFR-002)**: after `install("codex")` + `install("vibe")` + `remove("codex")` + `remove("vibe")`, every entry and every file Spec Kitty wrote is gone; third-party directories remain byte-identical.
5. **Twelve-agent parity (NFR-005)**: snapshot the rendered command-file output for the twelve non-migrated agents on pre-mission `main` and assert zero diff at mission end.
6. **Zero-touch migration (NFR-003)**: starting from a fixture that mirrors a pre-mission project with `.codex/prompts/spec-kitty.*.md`, `spec-kitty upgrade` alone produces working Codex integration with `.agents/skills/` populated and the manifest correctly recorded.
