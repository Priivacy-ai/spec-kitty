# Retrospective Notes — tool-surface-contract-01KV2K2P

Running log of process/tooling observations during the implement-review loop, to fold into the final retrospective.

## Analysis findings to carry into implementation

- **A4 (MEDIUM, from analyze gate):** FR-016 / C-006 are prohibition requirements (no auto-install of plugin bundles, no marketplace publish). WP09 currently lacks an explicit negative-assertion test that would FAIL if such logic were introduced. → When implementing WP09, add a regression test asserting the projection never auto-installs / never publishes to a marketplace.
- Analyze verdict: `ready` (counts: critical 0, high 0, medium 1, low 4). LOW findings A1/A2/A3/A5 are descriptive/wording nits, no action required.

## Cross-lane merge conflicts on the shared registry (service.py)

- **`tool_surface/service.py` is a convergence point.** WP03 created it; WP04 (session_presence/native_config), WP05 (managed_skills), and WP06 (agent_profiles) each independently added imports, `--kind` tokens, a `build_providers()` entry, and a `build_registry()` definition. Because the four lanes were branched in parallel from the WP03 base, every pairwise merge conflicts on `service.py`.
- **Effect on WP08/WP09 claim:** `agent action implement WP08`/`WP09` auto-merges all 6 dependency lanes into the new lane; the auto-merge halts on the lane-e (WP05) `service.py` conflict and marks the WP `blocked`. Recovery: manually `git merge` each remaining dependency lane in the lane worktree, resolve `service.py` as a UNION (keep every provider/token/definition from all lanes), commit, then `move-task <WP> --to planned --force` and re-claim. For the second WP (lane-i) I reused the already-resolved `service.py` from the first lane's merge commits (`git checkout <lane-h-merge-commit> -- service.py`) to avoid re-resolving by hand. After the union merge, the full `tests/specify_cli/tool_surface/` suite (177 tests) passed — first time all 6 WPs' code coexisted.
- **Expect the SAME conflict at `spec-kitty merge` time** when lanes land into the mission branch sequentially. The canonical union resolution for `service.py` is: 6 providers (CommandSkills, SlashCommands, SessionPresence, NativeConfig, ManagedSkills, AgentProfiles); 10 `--kind` tokens (command-skill, command-file, context-file/context_file, hook, rule, native-config/native_config, doctrine-skill, agent-profile); `build_registry` registers all 8 definitions via the tuple+nested-loop form. → Upstream improvement: a registration mechanism that doesn't require every provider WP to edit one shared file (e.g. entry-point/decorator-based provider discovery) would eliminate this whole conflict class.

## Process

- **record-analysis requires a clean mission worktree.** An untracked file in `kitty-specs/<mission>/` (e.g. this `retro-notes.md`) triggers `DIRTY_WORKTREE` and blocks recording. Keep mission-dir scratch files committed (or outside the mission dir) so the analyze gate can run.

## Implementation debt to watch

- **WP09 plugin-bundle staging fidelity (non-blocking, reviewer-noted).** The `--kind plugin-manifest --fix` staging tree for the Claude target aggregates source surfaces across multiple tool keys, so it contains both `<profile>.md` and `<profile>.agent.md` agent files (claude supplies `.md`, copilot supplies `.agent.md`) plus `hooks/settings.json` and `config.toml`. Does NOT violate the FR-016/C-006 prohibition or the inert/declarative contract — purely a staging-fidelity quirk. → Future tightening: scope each target's bundle to that target's own surfaces.

- **Two `SurfaceFinding` classes (WP03).** WP01's `tool_surface/model.py::SurfaceFinding` (fields `…surface_kind…detail`) diverges from the JSON-schema-canonical `tool_surface/findings.py::SurfaceFinding` (fields `code/severity/message/tool_key/surface_id/path/repair_command/docs_ref/details`) that WP03 added. WP01's version now has ZERO production importers. WP03 correctly avoided mutating the frozen WP01 file, but this leaves a same-name duplicate in the package. → Follow-up cleanup (likely WP07 legacy refactor or a post-merge task): retire/rename `model.SurfaceFinding` so there is one canonical type. Confirmed acceptable for WP03 by review.

## Tooling / Environment

- **Pyright false positives on lane-worktree files (WP01).** After WP01 implementation, the IDE surfaced `reportMissingImports` diagnostics (e.g. `Import ".enums" could not be resolved`) for files under `src/specify_cli/tool_surface/`. These are FALSE POSITIVES: the new files live on the lane worktree branch (`.worktrees/tool-surface-contract-01KV2K2P-lane-a`), not in the main checkout the IDE indexes, so Pyright cannot resolve the intra-package imports. The implementing subagent confirmed `mypy --strict` passed cleanly (0 issues, 7 files) inside the worktree. Action: ignore IDE import diagnostics for in-flight lane work; trust the worktree-local mypy/ruff/pytest run.

- **Duplicated-suffix mission-branch wrong-compose (UPSTREAM BUG — root cause found).**
  - Symptom 1: `move-task --to for_review/approved` false-fail with "No implementation commits on lane branch"; required `--force`.
  - Symptom 2: `agent action review WP02` hard-failed generating the review prompt with `WPMetadata base_commit Value error: Invalid base_commit: 'unknown' (must be hex SHA)`.
  - **Root cause:** `src/specify_cli/lanes/branch_naming.py::mission_branch_name()` composes `kitty/mission-{strip_numeric_prefix(slug)}-{mid8(mission_id)}`. This mission's `mission_slug` (`tool-surface-contract-01KV2K2P`) ALREADY ends with the mid8 (`-01KV2K2P`), and `strip_numeric_prefix` only strips a leading `NNN-` prefix — not a trailing mid8 — so the function double-appends → `kitty/mission-tool-surface-contract-01KV2K2P-01KV2K2P`, a branch that was never created. The real coordination/lane base branch (created via the legacy no-mission_id path) is the single-suffix `kitty/mission-tool-surface-contract-01KV2K2P`.
  - **Downstream corruption:** the wrong name was persisted into `lanes.json::mission_branch`, every WP frontmatter `base_branch`, and `.kittify/workspaces/*-lane-*.json::base_branch`; `_rev_parse(<nonexistent branch>)` then wrote `base_commit: "unknown"`, which fails the hex-SHA validator on the review path.
  - **Data repair applied (faithful to git reality, not an invention):** corrected `mission_branch`/`base_branch` to the single-suffix branch and set real `base_commit` SHAs (lane-a `a91cb363…`, lane-b `512f149b…`, = each lane's merge-base with the mission branch) across lanes.json (coord branch), WP01/WP02 frontmatter (main checkout), and both workspace context JSONs.
  - **Upstream fix needed:** `mission_branch_name` (and `mission_branch_name_required`) must not append a mid8 the slug already carries — detect a trailing `-{mid8}` and skip the second append. Also `mission_branch_name` (with mission_id) vs the legacy no-id path disagree on the name for mid8-suffixed slugs, so the branch that gets *created* and the branch that gets *recorded* diverge. File against the #1860 wrong-compose class.
