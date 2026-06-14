# Retrospective Notes — tool-surface-contract-01KV2K2P

Running log of process/tooling observations during the implement-review loop, to fold into the final retrospective.

## Analysis findings to carry into implementation

- **A4 (MEDIUM, from analyze gate):** FR-016 / C-006 are prohibition requirements (no auto-install of plugin bundles, no marketplace publish). WP09 currently lacks an explicit negative-assertion test that would FAIL if such logic were introduced. → When implementing WP09, add a regression test asserting the projection never auto-installs / never publishes to a marketplace.
- Analyze verdict: `ready` (counts: critical 0, high 0, medium 1, low 4). LOW findings A1/A2/A3/A5 are descriptive/wording nits, no action required.

## Process

- **record-analysis requires a clean mission worktree.** An untracked file in `kitty-specs/<mission>/` (e.g. this `retro-notes.md`) triggers `DIRTY_WORKTREE` and blocks recording. Keep mission-dir scratch files committed (or outside the mission dir) so the analyze gate can run.

## Tooling / Environment

- **Pyright false positives on lane-worktree files (WP01).** After WP01 implementation, the IDE surfaced `reportMissingImports` diagnostics (e.g. `Import ".enums" could not be resolved`) for files under `src/specify_cli/tool_surface/`. These are FALSE POSITIVES: the new files live on the lane worktree branch (`.worktrees/tool-surface-contract-01KV2K2P-lane-a`), not in the main checkout the IDE indexes, so Pyright cannot resolve the intra-package imports. The implementing subagent confirmed `mypy --strict` passed cleanly (0 issues, 7 files) inside the worktree. Action: ignore IDE import diagnostics for in-flight lane work; trust the worktree-local mypy/ruff/pytest run.

- **Duplicated-suffix base-ref bug.** `agent action implement`/`review` report the mission base branch as `kitty/mission-tool-surface-contract-01KV2K2P-01KV2K2P` (suffix doubled), which does NOT exist. The real base is `kitty/mission-tool-surface-contract-01KV2K2P`. Effect: `move-task --to for_review` / `--to approved` false-fail with "No implementation commits on lane branch" and require `--force` even though the lane commit is genuinely ahead of the correct base. Worth filing upstream so legitimate transitions aren't blocked for every WP/lane.
