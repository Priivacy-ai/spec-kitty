---
work_package_id: WP06
title: Codex Plugin Bundle Projector
dependencies:
- WP04
requirement_refs:
- FR-025
- FR-026
- FR-027
- FR-028
- FR-029
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
- T026
- T027
agent: claude
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: src/specify_cli/tool_surface/bundles/
create_intent:
- src/specify_cli/tool_surface/bundles/codex.py
- tests/specify_cli/tool_surface/test_plugin_build_codex.py
execution_mode: code_change
owned_files:
- src/specify_cli/tool_surface/bundles/codex.py
- tests/specify_cli/tool_surface/test_plugin_build_codex.py
role: Senior Python Engineer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load engineer
```

---

## Objective

Implement `spec-kitty plugin build --target codex` that generates a Codex plugin bundle at `dist/spec-kitty-plugins/codex/` with a schema-valid `.codex-plugin/plugin.json` (no `hooks` key, no `agents` key per Codex spec), canonical skills in `skills/`, and a `marketplace.json` for repo-local install via Codex marketplace.

---

## Context

The Codex plugin format (confirmed in research.md R-02) differs from Claude Code in key ways:
- Manifest at `.codex-plugin/plugin.json` (NOT `.claude-plugin/plugin.json`)
- Does NOT support an `agents` component (Codex custom agents are separate `.codex/agents/*.toml` files)
- Does NOT support a `hooks` key in the plugin manifest
- Skills distribution: `skills/` directory with the same SKILL.md format used by `.agents/skills/`
- Marketplace install: `codex plugin marketplace add` or repo-local via `.agents/plugins/marketplace.json`

Read `contracts/plugin-manifest-codex.md` for the authoritative schema. The schema differs materially from the Claude Code contract.

Shared utilities from `_builder.py` (created in WP04) can be reused here. Do not duplicate the skill-copy logic.

---

## Subtask Guidance

### T024 — Scaffold `--target codex` path; generate `.codex-plugin/plugin.json`

Extend `ClaudeBundleProjector`'s dispatch in `plugin.py` to handle `--target codex`:

```python
elif target == "codex":
    from specify_cli.tool_surface.bundles.codex import CodexBundleProjector
    CodexBundleProjector(output_dir).build(skip_validate=skip_validate)
```

Create `src/specify_cli/tool_surface/bundles/codex.py` with `CodexBundleProjector`:

```python
class CodexBundleProjector:
    def __init__(self, output_dir: Path) -> None:
        self.bundle_dir = output_dir / "codex"

    def build(self, *, skip_validate: bool = False) -> Path:
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        self._generate_plugin_json()
        self._copy_skills()
        self._generate_marketplace_json()
        self._validate(skip=skip_validate)
        return self.bundle_dir
```

`_generate_plugin_json()` must produce:
```json
{
  "name": "spec-kitty",
  "displayName": "Spec Kitty",
  "version": "3.2.0",
  "description": "Spec-Driven Development toolkit.",
  "author": {"name": "Priivacy AI"},
  "components": {
    "skills": "skills/"
  }
}
```

The `components` dict must NOT include `"agents"` or `"hooks"`. Write to `.codex-plugin/plugin.json` inside `self.bundle_dir`.

### T025 — Validate Codex plugin.json: no `hooks`, no `agents`, all required fields

Add a `_validate_manifest(manifest: dict) -> None` method:

```python
def _validate_manifest(self, manifest: dict) -> None:
    FORBIDDEN_KEYS = {"hooks", "agents"}
    REQUIRED_KEYS = {"name", "displayName", "version", "description"}
    found_forbidden = FORBIDDEN_KEYS & set(manifest)
    if found_forbidden:
        raise BuildError(
            f"Codex plugin.json must NOT contain: {sorted(found_forbidden)}"
        )
    missing_required = REQUIRED_KEYS - set(manifest)
    if missing_required:
        raise BuildError(
            f"Codex plugin.json missing required fields: {sorted(missing_required)}"
        )
```

Call this before writing the manifest to disk. Also verify that `manifest["components"]` does not include `"agents"` or `"hooks"` sub-keys.

This validation must also run as a unit test assertion (see WP08/WP09 for test coverage).

### T026 — Copy command-skill set to `skills/` in Codex bundle

Reuse the skill-copy utility from `_builder.py` (created in WP04). The skills directory structure is identical between Claude and Codex bundles:
```
dist/spec-kitty-plugins/codex/skills/spec-kitty.<cmd>/SKILL.md
```

```python
def _copy_skills(self) -> int:
    from specify_cli.tool_surface.bundles._builder import copy_skills_to_bundle
    return copy_skills_to_bundle(self.bundle_dir)
```

The `copy_skills_to_bundle()` helper in `_builder.py` handles the doctrine source discovery and copy. Do NOT duplicate this logic — import from `_builder`.

If a `hooks/` directory exists in the doctrine source, include it by filesystem presence only (copy if present, no error if absent). Do NOT add `"hooks"` to `plugin.json` even if the directory is copied.

### T027 — Generate `marketplace.json` for repo-local Codex install

Two marketplace.json formats exist for Codex:
1. **User-global marketplace** (via `codex plugin marketplace add <url>`)
2. **Repo-local marketplace** (via `.agents/plugins/marketplace.json` in the project)

Generate the repo-local format since it enables team-wide plugin install via the project's git repo:

```json
{
  "name": "spec-kitty-codex-plugins",
  "plugins": [
    {
      "name": "spec-kitty",
      "source": {
        "source": "local",
        "path": "."
      },
      "description": "Spec Kitty — Spec-Driven Development for Codex",
      "skills": "skills/"
    }
  ]
}
```

Write to `dist/spec-kitty-plugins/codex/marketplace.json`. Also write a copy to `.agents/plugins/marketplace.json` in the project root so teams can git-commit it and have Codex auto-discover the plugin.

Document this in a `# Codex Plugin Install` comment block at the top of the generated `marketplace.json`:
```json
// Install: codex plugin marketplace add .agents/plugins/marketplace.json
// Or:      codex plugin install dist/spec-kitty-plugins/codex
```
Note: JSON does not support comments — write the install instructions to stdout at end of build, not into the JSON file.

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `main` (local only)
- **Depends on**: WP04 (plugin build command and shared `_builder.py`)

WP06 can run in parallel with WP05 (independent targets, different output dirs).

To start work: `spec-kitty agent action implement WP06 --agent claude`

---

## Definition of Done

- [ ] `spec-kitty plugin build --target codex` command exists and runs
- [ ] `.codex-plugin/plugin.json` generated with valid schema
- [ ] `"hooks"` and `"agents"` keys ABSENT from Codex `plugin.json`
- [ ] All required fields (`name`, `displayName`, `version`, `description`) present
- [ ] `skills/` populated from doctrine source (same as Claude bundle, same `copy_skills_to_bundle()` helper)
- [ ] `marketplace.json` generated for repo-local install
- [ ] `ruff check` and `mypy --strict` pass on `codex.py`
- [ ] `test_plugin_build_codex.py` asserts no forbidden keys and ≥15 skills

---

## Risks

- Codex plugin schema may change after the plugin format GA — build must be re-validated against current Codex docs
- `copy_skills_to_bundle()` helper from `_builder.py` must be available before this WP starts — coordinate merge order with WP04
- `.agents/plugins/marketplace.json` may conflict with other marketplace entries if the user already has one — read-before-write and merge rather than overwrite
