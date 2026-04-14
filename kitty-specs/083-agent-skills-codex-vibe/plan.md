# Implementation Plan: Agent Skills Support for Codex and Vibe

**Branch**: `main` (planning and target) | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/083-agent-skills-codex-vibe/spec.md`
**Source**: GitHub issue [#624](https://github.com/Priivacy-ai/spec-kitty/issues/624)

## Summary

Deliver Mistral Vibe as a fully supported Spec Kitty coding agent in the next release, and in the same release retire the deprecated `.codex/prompts/` integration by serving Codex through a new Agent Skills rendering pipeline. The pipeline is **deliberately scoped to Codex and Vibe only** — P0 research (see `research.md`) showed that moving every agent's commands into the skills layer would lose deterministic argument substitution on Codex and potentially on Vibe, and would degrade TUI autocomplete UX on opencode. The twelve agents that today have a working command layer with `$ARGUMENTS` / `{{args}}` substitution keep their current command-file pipeline untouched. A central JSON ownership manifest at `.kittify/skills-manifest.json` tracks every skill package Spec Kitty writes into `.agents/skills/` so that additive installation, selective removal, and zero-touch Codex upgrade all hold without clobbering third-party skill entries.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty runtime).
**Primary Dependencies**: `ruamel.yaml` (existing) for `SKILL.md` frontmatter, `typer` + `rich` (existing) for CLI surfaces, stdlib `hashlib` for manifest content hashes, stdlib `json` for manifest persistence. No new third-party dependencies.
**Storage**: Filesystem only. Agent Skills packages written to project-local `.agents/skills/spec-kitty.<command>/`. Ownership recorded in `.kittify/skills-manifest.json`. No DB changes.
**Testing**: `pytest` — unit tests for the renderer and manifest, integration tests that drive `spec-kitty init --ai vibe --non-interactive` and `spec-kitty upgrade` against fixture projects, snapshot tests for skill-package bytes and for the untouched twelve-agent command output, shared-root coexistence tests that seed `.agents/skills/` with third-party files and assert byte-identity before/after Spec Kitty operations.
**Target Platform**: macOS and Linux (developer workstations) plus Windows where already supported. No new platform requirements; Vibe install instructions match what Mistral publishes.
**Project Type**: Single-package Python CLI with generated configuration/template assets. New modules slot into `src/specify_cli/skills/` and `src/specify_cli/upgrade/migrations/`.
**Performance Goals**: NFR-001 — install/upgrade/remove Vibe or Codex in under 3 seconds on a clean project on CI hardware, excluding network. The renderer is pure and deterministic (NFR-004).
**Constraints**:
- Shared-root coexistence: three-plus simultaneously installed shared-root agents with byte-identical third-party files before and after any Spec Kitty operation (NFR-002).
- Zero-touch Codex upgrade: no manual steps between pre- and post-mission releases (NFR-003).
- Byte-identical output for the other twelve agents (NFR-005).
**Scale/Scope**: 16 canonical `/spec-kitty.*` commands × 2 agents = 32 rendered skill packages per initialized project. One migration for existing Codex users. Documentation and README updates.

## Charter Check

No `.kittify/charter/charter.md` is present in this repository. The Charter Check gate is **skipped** for this mission, consistent with the specify-phase determination. If a charter is added later the plan will be re-evaluated.

## Project Structure

### Documentation (this feature)

```
kitty-specs/083-agent-skills-codex-vibe/
├── spec.md              # Specification (already written)
├── plan.md              # This file
├── research.md          # Phase 0 output (extensive, with citations)
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── skills-manifest.schema.json
│   └── skill-renderer.contract.md
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks/               # Populated by /spec-kitty.tasks (not this command)
```

### Source Code (repository root)

```
src/specify_cli/
├── core/
│   └── config.py                        # edit: add `vibe`; drop `.codex/prompts` command entry; mark codex as skills-rendered
├── agent_utils/
│   └── directories.py                   # edit: add `.agents/skills/` entry for vibe; drop `.codex` prompt dir from AGENT_DIRS for codex
├── skills/
│   ├── paths.py                         # existing; unchanged unless we surface vibe-specific helpers
│   ├── manifest.py                      # existing; extend with command-skill ownership entries
│   ├── command_renderer.py              # NEW — renders command-templates/*.md as SKILL.md packages for Codex + Vibe
│   ├── command_installer.py             # NEW — writes/removes Spec-Kitty-owned command-skill packages into .agents/skills/ with manifest bookkeeping
│   └── manifest_store.py                # NEW — load/save/diff .kittify/skills-manifest.json with content hashes
├── runtime/
│   └── agent_commands.py                # edit: route codex and vibe through command_installer; skip legacy .codex/prompts path
├── cli/commands/
│   ├── init.py                          # edit: accept --ai vibe; install command-skill packages for vibe
│   ├── verify.py                        # edit: detect `vibe` binary
│   └── agent/config.py                  # edit: vibe add/remove/list/status/sync works; remove honours manifest
├── gitignore_manager.py                 # edit: protect project-local .vibe/ runtime state
├── upgrade/
│   └── migrations/
│       └── m_3_2_0_codex_to_skills.py   # NEW — remove Spec-Kitty-owned files from .codex/prompts/, install command-skill packages for codex, record manifest entries
└── missions/*/command-templates/*.md    # unchanged source; the renderer reads these and transforms the User-Input block for skills output

tests/specify_cli/
├── skills/
│   ├── test_command_renderer.py         # NEW — snapshot + determinism tests
│   ├── test_command_installer.py        # NEW — additive install, selective remove, third-party byte-identity
│   └── test_manifest_store.py           # NEW — hash, drift detection, round-trip
├── cli/commands/
│   ├── test_init_vibe.py                # NEW — init --ai vibe --non-interactive
│   ├── test_verify_vibe.py              # NEW — vibe binary detection
│   └── test_agent_config_vibe.py        # NEW — add/remove/sync for vibe
├── upgrade/
│   └── test_m_3_2_0_codex_to_skills.py  # NEW — migration integration test against fixtures
└── regression/
    └── test_twelve_agent_parity.py      # NEW — snapshot pre-mission command output for the 12 unchanged agents; assert zero diff
```

**Structure Decision**: Single-project Python CLI. The new work lives in three new modules under `src/specify_cli/skills/` (`command_renderer.py`, `command_installer.py`, `manifest_store.py`) plus one new migration. Every other edit is narrow — a line in a registry, a routing branch in an installer, a regex in a detector. The command-template source files are **not rewritten**; the renderer reads them unchanged and transforms the `## User Input` block on the way out for the skills pipeline only. This keeps the twelve non-migrated agents byte-identical.

## Engineering Alignment

The mission commits to these decisions, which are load-bearing for both the design and the tests that must prove it:

1. **Scope of the new renderer.** The Agent Skills renderer is scoped to Codex and Vibe only. The twelve command-layer agents (claude, copilot, gemini, cursor, qwen, opencode, windsurf, kilocode, auggie, roo, q, antigravity) retain their existing command-file rendering unchanged. This is a *correctness* choice, not a scope-reduction choice — moving them would break argument substitution on opencode and degrade autocomplete UX. NFR-005 locks this in with a zero-diff snapshot regression test.
2. **Argument delivery for Codex and Vibe skills.** The skill body does **not** rely on literal `$ARGUMENTS` pre-substitution. The renderer rewrites the `## User Input` block (and any other inline `$ARGUMENTS` references inside that block) to an explicit instruction telling the model to treat the invocation turn's content as the user input. This matches how Codex Agent Skills actually deliver input today (per research) and keeps us robust if Vibe formalizes different semantics later. Any command-template content outside the `## User Input` block that references `$ARGUMENTS` is flagged at render time as an error so we can't accidentally ship an un-substituted placeholder to a skills-only agent.
3. **Ownership manifest.** `.kittify/skills-manifest.json` is the single source of truth for which files under `.agents/skills/` belong to Spec Kitty. Each entry records the relative path, the SHA-256 content hash at write time, and the agent keys the entry was installed on behalf of. The manifest is written after a successful install, updated on upgrade, and used by `agent config remove` to compute selective deletion.
4. **Shared-root coexistence semantics.** When multiple shared-root agents (codex, vibe, plus any existing shared-root agent) are configured, Spec Kitty maintains *exactly one* copy of each canonical skill package in `.agents/skills/`. The manifest's `agents` field records every agent that depends on that entry. Removing one agent drops that agent from the list; the package is physically deleted only when the list becomes empty. Third-party subdirectories (not in the manifest) are never touched.
5. **Legacy Codex cleanup.** The upgrade migration enumerates files under `.codex/prompts/` that match the set of names Spec Kitty would have written in the prior release (`spec-kitty.*.md`). It deletes only those files. Any non-Spec-Kitty files under `.codex/prompts/` are preserved untouched. If the user has edited a Spec-Kitty-owned prompt file in place — detectable because the file's hash does not match the hash the prior Spec Kitty version would have produced — the migration preserves the file and prints a notice listing the divergent paths. No silent discard.
6. **TUI autocomplete preserved.** The 12 agents retaining command-file rendering keep their autocomplete UX as today. Codex and Vibe get autocomplete through their native skills surface (Codex: `$skill-name` and `/skills`; Vibe: skills appear in the slash-command autocomplete menu per Mistral docs). opencode is explicitly kept on command-file rendering because its skills layer is model-loaded on demand and does not surface in autocomplete.
7. **Branch contract.** Planning and target branch is `main`. Every CLI notice and commit the mission produces refers to the real branch from `meta.json`, never a hardcoded `main`.

## Phase 0: Outline & Research

### Unknowns entering this phase

1. Exact Codex `SKILL.md` frontmatter field requirements.
2. Exact Vibe `SKILL.md` frontmatter field requirements.
3. Whether a single `SKILL.md` body can satisfy both agents without per-agent overlays.
4. How user input reaches the skill body on each agent's runtime (substitution vs turn content).
5. Whether moving to skills affects TUI autocomplete for any agent.
6. Whether opencode's skills layer is a viable target for our slash-command UX.

### Findings

All six unknowns were resolved. Full transcripts, quotes, and citations live in `research.md`. Summary here for plan readability:

- **Codex** — Agent Skills require `name` + `description` in `SKILL.md` frontmatter; invocation is `$skill-name <free-form text>`; the free-form text becomes turn content, **not** a substituted placeholder. `.codex/prompts` is deprecated.
- **Vibe** — `SKILL.md` with `name`, `description`, optional `license`, `compatibility`, `user-invocable`, `allowed-tools`. Official docs do **not** commit to any `$ARGUMENTS`-style substitution. Skills appear in the slash-command autocomplete menu.
- **Single body, two agents.** A `SKILL.md` with `name`, `description`, and optional `allowed-tools` satisfies both.
- **Argument delivery is not uniform across agents.** Codex skills: turn content. opencode skills: model-loaded via skill tool, not user-invoked slash commands, and have an open upstream bug about argument delivery. Claude skills: merged with commands — `$ARGUMENTS` works, positional ambiguous per Anthropic's own open issue. Gemini: commands with `{{args}}`, skills not the primary surface.
- **Autocomplete impact.** Moving the eleven command-layer agents would regress UX on opencode specifically. Keeping them on command-file rendering preserves current autocomplete UX everywhere.

### Decisions (with alternatives considered)

- **Decision**: Scope the skills renderer to Codex + Vibe. **Rationale**: avoids argument-delivery regression on opencode and preserves deterministic `$ARGUMENTS` semantics for the twelve agents that support it. **Alternatives considered**: unified skills-only pipeline (rejected — breaks argument substitution on Codex, degrades opencode UX); per-agent overlays inside a unified pipeline (rejected — increases complexity without solving the Codex substitution problem).
- **Decision**: Rewrite the `## User Input` block during rendering to instruct the model to read turn content. **Rationale**: the only mechanism that works on Codex today and is safe against Vibe's undocumented substitution semantics. **Alternatives considered**: emit literal `$ARGUMENTS` and hope Vibe substitutes (rejected — not documented by Mistral); inject arguments via an env-var wrapper (rejected — new runtime dependency outside the agents we integrate with).
- **Decision**: Central JSON ownership manifest with content hashes (Q1 option A). **Rationale**: clean uninstall in shared-root scenarios, drift detection for doctor, matches our existing `.kittify/` pattern. **Alternatives considered**: per-package sentinel files (rejected — litters skill dirs); naming-prefix-only convention (rejected — brittle under user-authored skill collisions).
- **Decision**: `agents` array per manifest entry for reference-counted cleanup. **Rationale**: required to make NFR-002 (three simultaneous shared-root agents) hold correctly. **Alternatives considered**: per-agent subdirectories under `.agents/skills/` (rejected — both Codex and Vibe use a flat discovery model).

## Phase 1: Design & Contracts

### Data model

See `data-model.md` for full entity definitions. Summary:

- **SkillPackage** — on-disk directory at `.agents/skills/spec-kitty.<command>/` with a `SKILL.md` and optional body files.
- **SkillsManifest** — parsed representation of `.kittify/skills-manifest.json`. Contains `schema_version: 1` and a list of `ManifestEntry`.
- **ManifestEntry** — one record per installed skill package: `path` (relative to repo root), `content_hash` (SHA-256), `agents` (sorted list of agent keys), `installed_at` (ISO-8601 UTC), `spec_kitty_version` (CLI version string at write time).
- **RenderedSkill** — in-memory record holding frontmatter dict + body string; returned from the renderer so tests can assert byte-for-byte output without touching disk.
- **LegacyCodexPrompt** — used only by the upgrade migration: path and hash of each Spec-Kitty-owned file discovered under `.codex/prompts/`.

### Contracts

- `contracts/skills-manifest.schema.json` — JSON schema for `.kittify/skills-manifest.json`. Versioned via `schema_version: 1`.
- `contracts/skill-renderer.contract.md` — Python-level contract for `command_renderer.render()` and `command_installer.install() / remove() / verify()`, documenting inputs, outputs, error conditions, and the User-Input block transformation rule.

### Command renderer behavior (informative)

Inputs: `command-templates/<command>.md` path, agent key (`codex` or `vibe`), mission key, Spec Kitty version string.

Output: a `RenderedSkill` with:
- Frontmatter: `name: spec-kitty.<command>`, `description: <first sentence of Purpose heading or a fallback>`, `user-invocable: true`, `allowed-tools: null` (field omitted when null so both agents accept the file).
- Body: the template's content with the `## User Input` block replaced by an explicit instruction that reads, approximately: *"When this skill is invoked, treat the user's most recent message content (excluding the skill-invocation token) as the User Input referenced elsewhere in these instructions."* Exact wording finalized during implementation and locked by snapshot test.
- Any inline `$ARGUMENTS` token outside the User-Input block raises `SkillRenderError` with the template path and line number — a guard against template edits silently breaking Codex/Vibe output.

The renderer is **pure**: same inputs produce byte-identical outputs (NFR-004).

### Command installer behavior (informative)

`install(repo_root, agent_key)`:
1. Load `.kittify/skills-manifest.json` (empty if absent).
2. For each canonical command, call `command_renderer.render(template, agent_key, ...)`.
3. For each rendered skill: compute relative install path (`.agents/skills/spec-kitty.<command>/SKILL.md`). If the manifest already lists this path and on-disk content matches the manifest hash, just add `agent_key` to the entry's `agents` list (idempotent). Otherwise write the file, record the new entry with `agent_key` in `agents`, update the manifest.
4. Persist the manifest with sorted keys + trailing newline (minimal git diffs).

`remove(repo_root, agent_key)`:
1. Load the manifest.
2. For every entry whose `agents` list contains `agent_key`, drop `agent_key` from the list.
3. If the resulting list is empty, physically delete the file and its parent `spec-kitty.<command>/` directory (only when that directory contains no other files — third-party co-tenants stay). Remove the entry from the manifest.
4. Persist.

`verify(repo_root)` (used by doctor and verify-setup):
1. For each manifest entry, compute current file SHA-256 and compare against stored hash. Report drift.
2. For every file under `.agents/skills/spec-kitty.*/` not in the manifest, report as orphan.
3. Return a structured result the CLI formats.

### Migration behavior (informative)

`m_3_2_0_codex_to_skills.py` runs during `spec-kitty upgrade` on any project where `codex` is in `agents.available`:

1. Discover `.codex/prompts/spec-kitty.*.md` files.
2. For each, compute current hash and compare to the known hash produced by the previous Spec Kitty version's renderer. Mark matches as "owned and unedited"; mismatches as "owned but edited".
3. Run the installer for `codex` to write the new skill packages into `.agents/skills/` and record them in the manifest.
4. Delete "owned and unedited" files. Preserve "owned but edited" files and print a notice: *"Preserved user-edited files in .codex/prompts/: <list>. Your Codex integration now reads from .agents/skills/; review and port your edits if still needed."*
5. Non-Spec-Kitty files in `.codex/prompts/` are never touched.
6. Remove `.codex/prompts/` only if it becomes empty. Do not remove `.codex/` itself.

### Quickstart

`quickstart.md` walks a reader through: installing Vibe, running `spec-kitty init --ai vibe`, verifying with `spec-kitty verify-setup --check-tools`, launching Vibe in the project, invoking `/spec-kitty.specify`, and the same flow from the perspective of an existing Codex user running `spec-kitty upgrade`.

### Agent context update

At implementation close, the agent context file (`CLAUDE.md` or equivalent) gains a short entry noting the new `src/specify_cli/skills/command_*.py` modules and the manifest location, following the same structure as existing entries.

### Re-evaluation of gates after design

- **Spec quality gates** — all pass; see `checklists/requirements.md`.
- **Charter gates** — skipped (no charter file).
- **Cross-WP blast radius** — contained to new `skills/command_*` modules, one migration, and narrow edits in `config.py`, `directories.py`, `init.py`, `verify.py`, `gitignore_manager.py`, `runtime/agent_commands.py`, `cli/commands/agent/config.py`. Existing command-file rendering for the twelve non-migrated agents is untouched in source.
- **Testability** — every FR and NFR maps to a concrete test fixture or snapshot.

## Testing Strategy

- **Unit**: renderer determinism (same template → byte-identical output), manifest round-trip (load → save → load is identity), ownership accounting (add/remove ref counts), user-input-block transformation (snapshot), guard against stray `$ARGUMENTS` outside the User-Input block.
- **Integration**: `init --ai vibe --non-interactive` on an empty tmpdir, `agent config add/remove` with shared-root coexistence, `upgrade` against a fixture project seeded with pre-mission `.codex/prompts/spec-kitty.*.md` files (both untouched and user-edited variants).
- **Regression**: snapshot of every command-file output for the twelve non-migrated agents captured at mission start and asserted byte-identical at mission end.
- **Coexistence**: seed `.agents/skills/` with three third-party skill directories, configure multiple shared-root agents, run add/remove cycles, assert third-party files are byte-identical before and after every step.
- **Doctor**: mutate a Spec-Kitty-owned skill on disk, run doctor, assert drift is reported with the correct path.

## Risks & Mitigations

- **Risk**: Vibe's substitution semantics differ from our assumption after release. **Mitigation**: we already assume no substitution — the worst case is that Vibe *also* substitutes, which is additive and harmless.
- **Risk**: Codex changes required `SKILL.md` frontmatter fields between mission start and release. **Mitigation**: frontmatter builder is one function with a small field set; CI lints generated `SKILL.md` against published schemas.
- **Risk**: User's `.codex/prompts/` contains a Spec-Kitty-named file they authored themselves. **Mitigation**: hash comparison against the previous Spec Kitty version's known renderer output identifies those as "owned but edited" and we preserve them.
- **Risk**: `.agents/skills/` populated by an unknown tool that races with our installer. **Mitigation**: the installer only reads/writes paths in (or destined for) its own manifest; it never enumerates peer directories for deletion.
- **Risk**: Migrations drift when tested only on clean fixtures. **Mitigation**: migration test matrix covers clean project, Spec-Kitty-only prompts, mixed ownership, user-edited Spec-Kitty files, and third-party-populated `.agents/skills/`.

## Branch Contract (restated before /spec-kitty.tasks)

- Current branch: `main`
- Planning/base branch: `main`
- Final merge target: `main`
- Branch matches target: ✅

Run `/spec-kitty.tasks` next to decompose this plan into work packages.

---

## Plan-Phase Outputs

Generated in this phase:
- `plan.md` (this file)
- `research.md` (extensive P0 findings with full per-agent citations)
- `data-model.md` (entity definitions)
- `quickstart.md` (user-facing walkthrough)
- `contracts/skills-manifest.schema.json`
- `contracts/skill-renderer.contract.md`
