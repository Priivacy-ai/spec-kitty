---
work_package_id: WP04
title: Claude Code Plugin Build Command
dependencies: []
requirement_refs:
- FR-017
- FR-018
- FR-019
- FR-020
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
- T018
- T019
agent: claude
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: src/specify_cli/tool_surface/bundles/
create_intent:
- src/specify_cli/cli/commands/plugin.py
- src/specify_cli/tool_surface/bundles/_builder.py
- tests/specify_cli/tool_surface/test_plugin_build_claude.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/plugin.py
- src/specify_cli/tool_surface/bundles/claude.py
- src/specify_cli/tool_surface/bundles/_builder.py
- tests/specify_cli/tool_surface/test_plugin_build_claude.py
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

Implement `spec-kitty plugin build --target claude-code` that generates a complete, `claude plugin validate --strict`-passing plugin bundle at `dist/spec-kitty-plugins/claude-code/`. The bundle must contain a real `plugin.json` (version from `importlib.metadata`), all ≥15 canonical command skills, and all built-in agent profiles.

This WP is foundational for WP05 (runtime bootstrap + CI gate). WP06 (Codex plugin) mirrors this structure.

---

## Context

The plugin manifest contract is at `kitty-specs/agent-profile-projection-plugin-production-01KV3NGS/contracts/plugin-manifest-claude.md`. Read it before writing any code.

Key facts from research (research.md R-01):
- Claude Code plugin manifest lives at `.claude-plugin/plugin.json` within the bundle directory
- Required fields: `name`, `displayName`, `version` (semver), `description`, `author`, and component-pointer arrays
- `claude plugin validate --strict` is the canonical validation tool — if it is not installed, skip validation but emit a clear warning
- Plugin agents (`agents/`) appear in Claude's `/agents` panel alongside project and user agents
- Skills (`skills/`) use the same SKILL.md format already in `.agents/skills/spec-kitty.<cmd>/SKILL.md`

The `PluginBundleProvider` in `src/specify_cli/tool_surface/providers/plugin_bundle.py` already exists but only stages bundles, does not build production artifacts. The new `spec-kitty plugin build` command calls a new `ClaudeBundleProjector` that does the real build.

---

## Subtask Guidance

### T015 — Scaffold `spec-kitty plugin build --target <target>` CLI command

In `src/specify_cli/cli/commands/plugin.py`, add a `build` subcommand:

```python
@plugin_app.command("build")
def plugin_build(
    target: str = typer.Option(..., "--target", help="Plugin target (claude-code, codex)"),
    output_dir: Path = typer.Option(Path("dist/spec-kitty-plugins"), "--output-dir"),
    skip_validate: bool = typer.Option(False, "--skip-validate"),
) -> None:
    """Build a Spec Kitty plugin bundle for a specific target harness."""
```

Dispatch on `target`:
- `"claude-code"` → call `ClaudeBundleProjector(output_dir).build(skip_validate=skip_validate)`
- `"codex"` → call `CodexBundleProjector(...)` (WP06)
- Other → raise `typer.BadParameter(f"Unknown target: {target!r}")`

Create `src/specify_cli/tool_surface/bundles/claude.py` with `ClaudeBundleProjector` class. The `build()` method orchestrates the 4 build steps (plugin.json, skills, agents, validate).

Create `src/specify_cli/tool_surface/bundles/_builder.py` with shared utilities (path helpers, manifest serialization) that both Claude and Codex projectors can import.

### T016 — Generate `plugin.json` with real version metadata; validate semver

In `ClaudeBundleProjector.build()`:

```python
import importlib.metadata
import json

def _generate_plugin_json(self, bundle_dir: Path) -> None:
    version = importlib.metadata.version("spec-kitty-cli")
    # Top-level component keys per contracts/plugin-manifest-claude.md
    # (NOT nested under "components" — claude-plugin format uses top-level skill/agents/hooks)
    manifest: dict[str, object] = {
        "name": "spec-kitty",
        "displayName": "Spec Kitty",
        "version": version,
        "description": "Spec-Driven Development toolkit — spec, plan, implement, review, merge.",
        "author": {"name": "Priivacy AI", "url": "https://github.com/Priivacy-ai/spec-kitty"},
        "skills": "skills/",
        "agents": "agents/",
    }
    # Conditionally add hooks pointer only if hooks/hooks.json is non-empty
    hooks_json = bundle_dir / "hooks" / "hooks.json"
    if hooks_json.exists() and hooks_json.stat().st_size > 2:
        manifest["hooks"] = "hooks/hooks.json"
    plugin_dir = bundle_dir / ".claude-plugin"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
```

Validate semver: the version string from `importlib.metadata` must match `^\d+\.\d+\.\d+`. If it doesn't (e.g., dev installs return `0.0.0+dev`), emit a warning but do NOT abort — the validator will catch it.

Per the plugin-manifest-claude.md contract: the `components` key must use the exact paths that exist in the bundle. Do not hardcode paths that won't be created in T017/T018.

### T017 — Copy canonical command-skill set (≥15 skills) to `skills/` in bundle

Skills are rendered by the existing `command_installer` infrastructure — use it, do NOT copy raw doctrine `prompt.md` files directly.

```python
from specify_cli.skills.command_installer import CANONICAL_COMMANDS, install_skills_for_agent

def _copy_skills(self, bundle_dir: Path, project_root: Path) -> int:
    """Render and copy command skills to bundle using the canonical installer. Returns skill count."""
    skills_dst = bundle_dir / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for command in CANONICAL_COMMANDS:
        skill_dir = skills_dst / f"spec-kitty.{command}"
        skill_dir.mkdir(parents=True, exist_ok=True)
        # Use command_renderer to render the canonical SKILL.md content
        from specify_cli.skills import command_renderer
        content = command_renderer.render(command, agent_key="codex")  # neutral render
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        count += 1
    if count < 15:
        raise BuildError(f"Expected ≥15 skills, found {count} in CANONICAL_COMMANDS.")
    return count
```

**Why not copy from doctrine source?** The doctrine source has `prompt.md` files that contain template placeholders. The installed `SKILL.md` files are rendered copies. Use `command_renderer.render()` to get the rendered output, not the raw source.

### T018 — Copy built-in agent profile Markdown files to `agents/` in bundle

Built-in agent profiles ship with the package under a path resolvable via `get_package_asset_root()` or similar. Locate this function in `src/specify_cli/runtime/home.py`.

```python
def _copy_agents(self, bundle_dir: Path) -> int:
    """Copy built-in agent profiles to bundle agents/ dir. Returns agent count."""
    from specify_cli.runtime.home import get_package_asset_root
    profiles_src = get_package_asset_root() / "agent_profiles"
    agents_dst = bundle_dir / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for profile_md in sorted(profiles_src.glob("*.md")):
        shutil.copy2(profile_md, agents_dst / profile_md.name)
        count += 1
    return count
```

If `profiles_src` does not exist (no built-in profiles shipped yet), log a warning and continue with `count=0`. Per FR-019, the bundle MUST include built-in profiles; if none are available at build time, this is a build warning that requires follow-up before shipping.

Also create a minimal `hooks/hooks.json` file (empty JSON object `{}`) to establish the directory structure for potential future hooks, but do NOT add the `hooks` pointer to `plugin.json` unless hooks content is non-trivial.

### T019 — Run `claude plugin validate --strict`; surface errors clearly

```python
def _validate(self, bundle_dir: Path, *, skip: bool) -> None:
    if skip:
        typer.echo("⚠  Skipping claude plugin validate (--skip-validate passed).")
        return
    try:
        result = subprocess.run(
            ["claude", "plugin", "validate", "--strict", str(bundle_dir)],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        typer.echo("⚠  claude CLI not found — skipping validation. Install claude CLI to validate.")
        return
    if result.returncode != 0:
        typer.echo("❌  claude plugin validate --strict FAILED:")
        typer.echo(result.stdout)
        typer.echo(result.stderr)
        raise typer.Exit(code=1)
    typer.echo("✔  claude plugin validate --strict passed.")
```

The validate step is the LAST step in `build()`. If it fails, the build is considered failed and the bundle directory is left in place for inspection (do not delete on failure).

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `main` (local only)
- **No dependency on WP01-03** (parallel track)

To start work: `spec-kitty agent action implement WP04 --agent claude`

---

## Definition of Done

- [ ] `spec-kitty plugin build --target claude-code` command exists and runs
- [ ] `plugin.json` generated with real version from `importlib.metadata`
- [ ] `skills/` contains ≥15 command skills from doctrine source
- [ ] `agents/` copied from built-in profiles (may be empty if none ship yet)
- [ ] `claude plugin validate --strict` runs and passes (or warns if CLI absent)
- [ ] `--skip-validate` flag skips validation without error
- [ ] `ruff check` and `mypy --strict` pass on all changed modules
- [ ] `test_plugin_build_claude.py` covers the build steps (T017 count assertion, semver check)

---

## Risks

- `importlib.metadata.version("spec-kitty-cli")` may fail in editable installs — handle `PackageNotFoundError` and fall back to reading `pyproject.toml` version
- Doctrine source path may differ in installed vs. editable modes — use `get_package_asset_root()` consistently
- `claude plugin validate --strict` interface may have changed in newer CLI versions — pin the CI test to a specific version
- Complexity ceiling is 15 (ruff C901) — split `build()` into `_generate_plugin_json`, `_copy_skills`, `_copy_agents`, `_validate` helpers
