---
work_package_id: "WP05"
title: "Vibe CLI Surface (init, verify, gitignore)"
subtasks:
  - T023
  - T024
  - T025
  - T026
  - T027
dependencies:
  - WP04
planning_base_branch: "main"
merge_target_branch: "main"
branch_strategy: "lane-worktree"
execution_mode: "code_change"
owned_files:
  - "src/specify_cli/cli/commands/init.py"
  - "src/specify_cli/cli/commands/verify.py"
  - "src/specify_cli/gitignore_manager.py"
  - "tests/specify_cli/cli/commands/test_init_vibe.py"
  - "tests/specify_cli/cli/commands/test_verify_vibe.py"
  - "tests/specify_cli/cli/commands/test_agent_config_vibe.py"
authoritative_surface: "src/specify_cli/cli/commands/"
requirement_refs:
  - FR-001
  - FR-003
  - FR-009
  - FR-010
history:
  - at: "2026-04-14T00:00:00+00:00"
    actor: "planner"
    event: "created"
---

# WP05 — Vibe CLI Surface

## Objective

Make `vibe` a first-class CLI citizen end-to-end. `spec-kitty init --ai vibe --non-interactive` succeeds on a clean project and leaves it in a state where `spec-kitty next --agent vibe` can drive the workflow; `spec-kitty verify-setup --check-tools` detects the `vibe` binary; `.gitignore` protects the Vibe runtime directory; `spec-kitty agent config add/remove vibe` round-trips correctly.

## Context

WP04 added `vibe` to every registry and wired the runtime to route codex + vibe to `command_installer.install`. This WP makes the user-visible CLI surfaces cooperate. Most edits are small — the `--ai` flag validation and the verify-setup detection both use the registries WP04 updated.

Vibe install commands for reference:
- `curl -LsSf https://mistral.ai/vibe/install.sh | bash`
- `uv tool install mistral-vibe`

Project-local Vibe runtime state (per Mistral docs): `.vibe/`. Protect this directory in `.gitignore`.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane from `lanes.json` after `finalize-tasks`. Depends on WP04.

## Implementation

### Subtask T023 — Edit `cli/commands/init.py`

- `--ai` validation: no code change needed if `AI_CHOICES` is the canonical source. Confirm by grepping the current init for hardcoded agent lists; if any exist, drive them from `AI_CHOICES`.
- When the selected agent is `vibe`, the existing runtime installer path (WP04) will route to `command_installer.install`. No special-casing in init.
- Printed next-steps: add a branch that, when `agent_key == "vibe"`, prints instructions like:

  ```
  Next steps for Mistral Vibe:
    1. Install Vibe if you haven't already:
         curl -LsSf https://mistral.ai/vibe/install.sh | bash
       or
         uv tool install mistral-vibe
    2. Launch Vibe in this project:
         vibe
    3. Inside Vibe, invoke your first workflow:
         /spec-kitty.specify <describe what you want to build>
  ```

  Use the existing next-steps helper pattern (search for `"Next steps"` or similar in init.py to find the style Spec Kitty already uses for other agents). Match indentation, punctuation, and Rich styling.

### Subtask T024 — Edit `cli/commands/verify.py` [P]

Confirm `verify-setup --check-tools` iterates over `AGENT_TOOL_REQUIREMENTS`. Since WP04 added `vibe` to that registry, verify-setup should already pick it up.

If any code path has an explicit agent-key allowlist for tool detection, add `vibe`. Match the existing output format (icon, name, version line, path line) exactly — no new columns, no new formatting.

Add a helper if needed that converts the registry tuple into the detection record. Prefer reusing any existing helper.

### Subtask T025 — Edit `gitignore_manager.py` [P]

Find the existing agent-protection helper (likely a constant or function like `PROTECTED_AGENT_DIRS` or `_agent_gitignore_patterns`). Add entries for Vibe:

- `.vibe/` — project-local Vibe runtime state (config, cache, session logs)

Do not add `.agents/` — that's the skills root and may be intentionally committed (it contains our generated skill packages). Confirm existing agents' patterns before choosing what to protect.

If the current helper uses the `AGENT_DIRS` constant from `agent_utils/directories.py`, make sure WP04's edits to that constant didn't accidentally break the codex protection (codex no longer has a command dir to protect, so its absence from `AGENT_DIRS` is correct and should not produce a missing `.codex/` gitignore entry — but double-check existing projects don't regress).

### Subtask T026 — Integration test: `init --ai vibe --non-interactive`

Create `tests/specify_cli/cli/commands/test_init_vibe.py`:

- **End-to-end init**: use `typer.testing.CliRunner` or Spec Kitty's existing test harness. Run `spec-kitty init --ai vibe --non-interactive` in a tmpdir.
- Assert exit code 0.
- Assert `.kittify/config.yaml` exists and `load_agent_config` returns an `AgentConfig` with `"vibe"` in `available`.
- Assert `.agents/skills/spec-kitty.specify/SKILL.md` exists (and spot-check 2-3 other canonical commands).
- Assert `.kittify/skills-manifest.json` exists and `manifest_store.load` returns 16 entries all with `agents == ("vibe",)`.
- Assert `.gitignore` exists and contains a line matching `.vibe/` or `.vibe`.
- Assert the printed next-steps include the Vibe install command and the launch instruction.

- **Idempotent init**: run `init --ai vibe` twice; the second run succeeds and does not duplicate manifest entries or corrupt files.

- **No-Vibe-binary is fine**: don't require `vibe` on `PATH` for this test. Init doesn't shell out to vibe.

### Subtask T027 — Integration tests: verify-setup + agent config

Create `tests/specify_cli/cli/commands/test_verify_vibe.py`:

- **Detects vibe on PATH**: patch `shutil.which` (or the equivalent Spec Kitty helper) to return `/usr/local/bin/vibe`. Run `verify-setup --check-tools`. Assert the output lists Vibe as present with the mocked path.
- **Reports vibe missing**: patch `shutil.which` to return `None`. Run `verify-setup --check-tools`. Assert Vibe is listed as missing and the install URL from `AGENT_TOOL_REQUIREMENTS["vibe"]` appears.

Create `tests/specify_cli/cli/commands/test_agent_config_vibe.py`:

- **Add vibe**: starting from a config with `agents.available=[]`, run `spec-kitty agent config add vibe`. Assert config now has `vibe`, and that skill packages and manifest were created (reuse WP03 test fixtures if helpful).
- **Remove vibe**: starting from a config with `agents.available=["vibe"]` and the manifest populated, run `spec-kitty agent config remove vibe`. Assert manifest is empty, `.agents/skills/spec-kitty.*/` is gone, config no longer lists vibe.
- **Remove vibe while codex also configured**: start from both configured. Run `spec-kitty agent config remove vibe`. Assert manifest entries still exist with `agents == ("codex",)`, the skill packages remain byte-identical on disk.

## Definition of Done

- [ ] `spec-kitty init --ai vibe --non-interactive` exits 0 on a clean tmpdir.
- [ ] Manifest, skill packages, config.yaml, and gitignore are all correct after init.
- [ ] `verify-setup --check-tools` detects `vibe` when on PATH and reports it missing otherwise.
- [ ] `agent config add/remove vibe` round-trips correctly including the codex-coexistence path.
- [ ] All new tests pass: `pytest tests/specify_cli/cli/commands/test_init_vibe.py tests/specify_cli/cli/commands/test_verify_vibe.py tests/specify_cli/cli/commands/test_agent_config_vibe.py`.
- [ ] `ruff check src/specify_cli/cli/commands/ src/specify_cli/gitignore_manager.py` passes.
- [ ] No changes outside `owned_files`.

## Risks

- **Next-steps wording drift.** The printed instructions will be quoted in issue templates and user tutorials. Keep the wording stable across minor versions; changes here mean doc changes in WP07.
- **Gitignore collisions.** If a user already has `.vibe/` in their gitignore, the protection helper should detect and skip (or merge) rather than duplicate. Reuse the existing helper semantics.
- **Test fragility around Rich output.** Asserting on Rich-formatted next-steps is brittle. Prefer asserting on substring matches (e.g., `"mistral-vibe" in output` and `"/spec-kitty.specify" in output`) over full-string equality.

## Reviewer Guidance

- Actually run `spec-kitty init --ai vibe --non-interactive` in a throwaway directory and inspect the printed output. Confirm it looks correct *for a user reading it for the first time*, not just *to someone who already knows the workflow*.
- Diff the gitignore produced for a codex-only project before and after this mission. The codex-related protection lines should be effectively unchanged (codex no longer has a command dir to protect; see WP04).
- Confirm `AGENT_TOOL_REQUIREMENTS["vibe"]` points to a stable Mistral URL. Prefer the GitHub repo URL over a blog post URL.

## Command to run implementation

```bash
spec-kitty agent action implement WP05 --agent <name>
```
