---
work_package_id: WP12
title: Install / upgrade / uninstall lifecycle
dependencies: []
requirement_refs:
- FR-017
- FR-018
- FR-019
- NFR-003
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
- T039
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "10955"
history:
- actor: planner
  at: '2026-05-21T06:52:04Z'
  action: wp_authored
  notes: Initial authorship by tasks phase.
agent_profile: curator-carla
authoritative_surface: docs/how-to/
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- docs/how-to/install-macos.md
- docs/how-to/install-linux.md
- docs/how-to/install-windows.md
- docs/how-to/upgrade-cli.md
- docs/how-to/upgrade-project.md
- docs/how-to/uninstall.md
- docs/explanation/pip-vs-pipx-vs-uv.md
- docs/reference/init-lifecycle.md
- docs/reference/upgrade-lifecycle.md
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

## Objective

Author the full install / upgrade / uninstall lifecycle documentation: 9-cell (tool × OS) matrix coverage, init/upgrade lifecycle references, pip-vs-pipx-vs-uv explanation, and uninstall+rollback flow.

## Context

- FR-017, FR-018, FR-019, NFR-003.
- PyPI package: `spec-kitty-cli` (per `CLAUDE.md` §"PyPI Release"); CLI entry point: `spec-kitty = "specify_cli:main"`.
- Three tools (pip, pipx, uv tool) × three OSes (macOS, Linux, Windows).
- Verification command everywhere: `spec-kitty --version`.

## Subtasks

### T035 — Install how-tos (3 pages)

Create `docs/how-to/install-macos.md`, `docs/how-to/install-linux.md`, `docs/how-to/install-windows.md`. Each page covers:

- **pip in a venv** — `python -m venv .venv && source .venv/bin/activate && pip install spec-kitty-cli` (PowerShell variant on Windows).
- **pipx (recommended for global tool install)** — `pipx install spec-kitty-cli`.
- **uv tool** — `uv tool install spec-kitty-cli`.
- **Verification** — `spec-kitty --version` should print the package version.
- **PATH** — note where the binary lands (`~/.local/bin/`, `%USERPROFILE%\.local\bin\`, `~/.cargo/bin/` for uv, etc.); guidance for fixing PATH on each OS.
- **PowerShell vs CMD** (Windows only) — note `py` launcher vs `python3`.

### T036 — Upgrade how-tos (2 pages)

- `docs/how-to/upgrade-cli.md` — `pipx upgrade spec-kitty-cli`, `uv tool upgrade spec-kitty-cli`, `pip install --upgrade spec-kitty-cli` (venv).
- `docs/how-to/upgrade-project.md` — `spec-kitty upgrade` in a project; describe the lifecycle from `CLAUDE.md` §"Agent Management Best Practices" (config-aware migrations, `agent config sync`).

### T037 — Uninstall + rollback

`docs/how-to/uninstall.md` covers:

- Uninstall CLI (`pipx uninstall spec-kitty-cli`, `uv tool uninstall spec-kitty-cli`, `pip uninstall spec-kitty-cli`).
- Remove generated project files (review `.kittify/`, `.claude/`, etc.; archive `kitty-specs/` if desired).
- Rollback from a failed upgrade — show `git restore`, `pipx install --force` with previous version.

### T038 — Pip vs pipx vs uv explanation

`docs/explanation/pip-vs-pipx-vs-uv.md` compares the three tools across:

- Global tool install vs venv.
- Speed and reproducibility.
- macOS / Linux / Windows quirks.
- Recommendation: pipx or uv tool for end users; pip in venv for contributors.

### T039 — Init / upgrade lifecycle reference

- `docs/reference/init-lifecycle.md` — what `spec-kitty init` creates, idempotent behaviour, non-interactive init, supported host selection (cite `CLAUDE.md` §"Agent Management Best Practices").
- `docs/reference/upgrade-lifecycle.md` — what `spec-kitty upgrade` changes, when project upgrade is required after CLI upgrade, how to review generated file changes.

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Lane: `E`. First and only WP in lane E.

## Test Strategy

- Reviewer gate.
- Cell-coverage check in publication checklist (WP14): every (tool × OS) cell has install/upgrade/uninstall/verification commands.

## Definition of Done

- [ ] All 9 new files in `owned_files` exist.
- [ ] Every (tool × OS) cell has all four commands (install/upgrade/uninstall/verification).
- [ ] PATH / PowerShell / py-launcher notes present.
- [ ] No files outside `owned_files` modified.

## Risks

- **Command shapes drift across PyPI versions** — Mitigation: cite the PyPI distribution name verbatim; verification command is `spec-kitty --version`.
- **Cross-platform testing not possible from a single environment** — Mitigation: cite the cell as "documented from upstream `pipx`/`uv`/`pip` docs" and label any cell that wasn't smoke-tested locally.

## Reviewer Guidance

- Confirm 9 cells × 4 commands matrix.
- Confirm Windows page has PowerShell examples and `py` launcher note.
- Confirm uninstall page covers project files, not just CLI.

## Implement command

```bash
spec-kitty agent action implement WP12 --agent claude
```

## Activity Log

- 2026-05-21T08:59:11Z – claude:opus-4-7:curator-carla:implementer – shell_pid=6649 – Started implementation via action command
- 2026-05-21T09:05:03Z – claude:opus-4-7:curator-carla:implementer – shell_pid=6649 – WP12 ready: 9 lifecycle pages covering pip/pipx/uv × macOS/Linux/Windows; init+upgrade reference; uninstall+rollback.
- 2026-05-21T09:05:27Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=10955 – Started review via action command
- 2026-05-21T09:06:50Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=10955 – Renata review: pass. 9 lifecycle pages; 3 tools × 3 OSes covered; PowerShell + py launcher noted; PyPI name correct; uninstall+rollback documented.
- 2026-05-21T09:27:27Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=10955 – Moved to done
