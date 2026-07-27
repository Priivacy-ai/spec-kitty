# Phase 0 Research: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Purpose**: Resolve every engineering unknown for the seven core tracks before Phase 1 design.
**Method**: Five parallel code-surface investigations against `/private/tmp/311/spec-kitty` at HEAD (commit `f3d017f6`, the PR #555 merge baseline).
**Outcome**: Zero `[NEEDS CLARIFICATION]` markers remaining; all material technical decisions captured below.

---

## Track 1 — `init` coherence

### Current state

| Behavior | Where | Notes |
|----------|-------|-------|
| Auto `git init` | `src/specify_cli/cli/commands/init.py:547-560` calls `init_git_repo(project_path, quiet=True)` | Gated by `--no-git` flag (default: git ON) |
| Auto initial commit | `src/specify_cli/core/git_ops.py:104-128` `init_git_repo()` | Subprocess sequence: `git init` (line 112) → `git add .` (line 113) → `git commit -m "Initial commit from Specify template"` (lines 114-118) |
| Literal commit message | `src/specify_cli/core/git_ops.py:115` | Hardcoded `"Initial commit from Specify template"` |
| `.agents/skills/` seeding | `src/specify_cli/cli/commands/init.py:515-540` | Uses `skill_registry_per_agent.discover_skills()` and `install_skills_for_agent()`; per-agent install copies into `.codex/prompts/`, `.claude/skills/`, etc. The `.agents/skills/` shared root is referenced in `src/specify_cli/upgrade/skill_update.py:39` but not directly created by `init` per the agent's read. |
| Next-steps slash-command list | `src/specify_cli/cli/commands/init.py:641-650` | Lists `/spec-kitty.implement` at line 647 as the canonical execution step |
| `init` entry point | `src/specify_cli/cli/commands/init.py:261` (function `init`) | Registered via `register_init_command(app, ...)` at line 765 → `app.command("init")(init)` at line 793 |
| `--no-git` flag | `init.py:267` | Already exists; the new model flips its semantics — git init becomes opt-in |
| Existing tests | `tests/init/test_init_flow_integration.py`, `tests/init/test_init_minimal_integration.py`, `tests/init/test_charter_runtime_integration.py`, `tests/init/test_init_hybrid.py` | **Critical finding**: none of them lock the literal commit message or assert that `git init` is called. The init tests focus on `.gitignore` protection, project skeleton creation, and skill installation. **Safe to change git/commit behavior without breaking existing tests.** |

### Locked decision

- Default behavior of `init` is: **no `git init`, no commit, no `.agents/skills/`**, with **no opt-in escape hatch**.
- The `--no-git` flag is **removed** from the `init` command. It has no meaning under the new model. Users passing `--no-git` after this lands will get a typer "no such option" error. This is an intentional CLI surface change. Rationale: per spec D-1 / FR-001 / FR-002 / FR-007, init does not initialize git on behalf of the user under any flag combination, and keeping `--no-git` as a no-op would be a backward-compat shim that the project's CLAUDE.md explicitly forbids.
- There is **no `--git` opt-in flag**. An earlier draft of this research entertained that as an "escape hatch" for users who wanted the legacy behavior; reviewer feedback (P1) correctly flagged that as a contradiction of D-1. The escape hatch is removed.
- The literal string `"Initial commit from Specify template"` is removed from the production source tree. A test asserts its absence.
- Next-steps text is rewritten to name the canonical commands directly: `spec-kitty next` (loop) and `spec-kitty agent action implement` / `spec-kitty agent action review` (per-decision verbs). See the Track 6 section below for the canonical-path research.

### Rejected alternatives

- **Keep `init_git_repo()` and just remove the commit step**: rejected because the commit and the `git init` are coupled in the same function, and removing only one leaves an empty repo with no clear user benefit.
- **Add a `--git --commit` opt-in pair**: rejected because the spec forbids ANY opt-in path that re-enables git side effects from `init`. Per D-1, init is file-creation-only, no flag combination changes that.
- **Add a single `--git` opt-in flag**: rejected — same reason. (Earlier draft of this plan entertained this; reviewer feedback P1 correctly rejected it as a contradiction of D-1.)
- **Keep `--no-git` as a silent no-op for backward compat**: rejected because the project's CLAUDE.md explicitly forbids backward-compat shims and "renaming unused vars". The flag is removed entirely.

---

## Track 2 — Planning-artifact producer correctness

### Current state

| Surface | File:Lines | Behavior |
|---------|-----------|----------|
| Filter | `src/specify_cli/lanes/compute.py:254-276` | Branches on `manifest.execution_mode == ExecutionMode.PLANNING_ARTIFACT`. Planning-artifact WPs go into `planning_artifact_wps` list and are excluded from lane assignment. Code WPs flow into `code_wp_ids` and get lanes. |
| Lane data model | `src/specify_cli/lanes/models.py:72-89` | `ExecutionLane` is a frozen dataclass with `lane_id`, `wp_ids`, `write_scope`, `predicted_surfaces`, `depends_on_lanes`, `parallel_group`. |
| Manifest | `src/specify_cli/lanes/models.py:114-139` | `LanesManifest` carries `lanes: list[ExecutionLane]` and a separate `planning_artifact_wps: list[str]`. |
| Worktree path resolution | `src/specify_cli/lanes/branch_naming.py` (function `lane_branch_name(mission_slug, lane_id)`) and `src/specify_cli/workspace_context.py:121-143` (`ResolvedWorkspace.worktree_path`) | Lane branch name = `kitty/mission-<mission_slug>-<lane_id>`. Worktree path = `.worktrees/<mission_slug>-<lane_id>`. |
| Main repo path helper | `src/specify_cli/core/paths.py:200` `get_main_repo_root(current_path)` | Follows `.git` worktree pointers to locate the main checkout from a worktree. Already exists; usable directly. |
| Producer | `src/specify_cli/cli/commands/agent/mission.py:1796-1807` | `compute_lanes(...)` then `write_lanes_json(feature_dir, lanes_manifest)` |
| Persistence | `src/specify_cli/lanes/persistence.py:31-59` `write_lanes_json` | Writes to `kitty-specs/<mission_slug>/lanes.json`; atomic temp-rename. |
| Consumer special case | `src/specify_cli/context/resolver.py:174-182` | `if execution_mode == "planning_artifact": authoritative_ref = None; else: authoritative_ref = lane_branch_name(...)`. **This is the post-#555 type-branching that must be collapsed.** |
| Implement dispatch handling | `src/specify_cli/cli/commands/implement.py:38-52, 179-200` | `_get_wp_lane_from_event_log` reads event log for WP lane state; `_ensure_planning_artifacts_committed_git()` handles planning-artifact-specific git semantics. |
| Worktree create routing | `src/specify_cli/core/worktree.py:90-136` | `create_wp_workspace` routes by `execution_mode`: `PLANNING_ARTIFACT` → `create_planning_workspace()` (returns `repo_root` directly at line 135); else → git worktree. |
| Other planning_artifact references | `src/specify_cli/ownership/{models.py:29 (StrEnum value), workspace_strategy.py, validation.py, inference.py}` | The execution mode is defined in the ownership package; lane and downstream consumers reference it from there. |

### Locked decision

- **Stop filtering** at `compute.py:254-276`. Every WP is included in the lane assignment algorithm.
- **Canonical lane name**: `lane-planning`. This is a stable lane id for the planning workspace and is treated identically to `lane-a`/`lane-b` at the lane-contract boundary.
- **`lane-planning` resolves to the main repo checkout**, not a worktree. Enforced in `branch_naming.py` (returns the planning branch from `meta.json`, not a kitty-namespace branch) and `worktree.py`/`workspace_context.py` (returns `repo_root` from `paths.get_main_repo_root` instead of allocating a worktree).
- **Collapse the consumer special-case branch** in `context/resolver.py:174-182`. Lane lookup is uniform; lane-to-workspace resolution is the only place that branches on `lane_id == "lane-planning"`.
- **Keep `LanesManifest.planning_artifact_wps`** as a **derived view** for backward-compat with existing `lanes.json` files. Mark deprecated in docstring. Removing it is archaeology and out of scope (NG-1).

### Rejected alternatives

- **Model planning artifacts as lane-less but with a sentinel `lane = None`**: rejected because it requires every consumer to handle `lane is None` as a special case, which is exactly the type-branching D-2 forbids.
- **Create a real git worktree for `lane-planning`**: rejected because planning artifacts conceptually live in the planning workspace (the main checkout). Allocating a worktree would mean the planner has to context-switch into a worktree to read its own files, which makes no sense.
- **Remove `planning_artifact_wps` from the manifest entirely**: rejected as archaeology — historical `lanes.json` files in fresh clones would lose schema compatibility.

---

## Track 3 — Mission identity Phase 1

### Current state

**ADR**: `architecture/adrs/2026-04-09-1-mission-identity-uses-ulid-not-sequential-prefix.md` (accepted 2026-04-09, commit `b85116ed`).

**ADR mandates**:
1. Every new mission receives a `mission_id` at creation time.
2. `mission_id` is the immutable canonical machine-facing identifier.
3. `mission_number` is demoted to display-only metadata.
4. Identity format: **ULID** (Universally Unique Lexicographically Sortable Identifier).
5. Confirmation criterion: zero new missions without `mission_id`.

**Library**: `python-ulid>=3.0` already in `/private/tmp/311/spec-kitty/pyproject.toml:72`. Existing import at `src/specify_cli/sync/emitter.py:15` (`import ulid`). **No new dependency required.**

**Mission creation field set today** (`src/specify_cli/core/mission_creation.py:289-309`):
```python
meta.setdefault("mission_number", f"{feature_number:03d}")
meta.setdefault("slug", mission_slug_formatted)
meta.setdefault("mission_slug", mission_slug_formatted)
meta.setdefault("friendly_name", mission_slug.replace("-", " ").strip())
meta.setdefault("mission_type", mission or "software-dev")
meta.setdefault("target_branch", planning_branch)
meta.setdefault("created_at", datetime.now(timezone.utc).isoformat())
```

**No `mission_id` is written at creation today.** Some historical missions have been retro-fitted with one (e.g., 032 has `01KN2371WRE1E2BH9WR11MAGDG`); most do not.

**Numeric prefix allocator**: `src/specify_cli/core/worktree.py:163-207` `get_next_feature_number(repo_root) -> int`. Scans `kitty-specs/` and `.worktrees/` for `###-name` directories; returns `max(found) + 1`. Called by `create_mission_core()` (line 244 of mission_creation.py) and `create_feature_worktree()` (line 236 of worktree.py).

**Locking**: Mission creation has **no lock**. The status subsystem has `src/specify_cli/status/locking.py` with `feature_status_lock_path()` (lines 59-62) that uses `filelock.FileLock`, but it is acquired only for status events, not for `meta.json` writes.

**Machine-facing flows that currently identify missions by slug or numeric prefix**:
1. `cli/commands/implement.py:101-127` `detect_feature_context()` — extracts numeric prefix via regex `r"^(\d{3})-"` from mission slug.
2. `lanes/worktree_allocator.py:28-79` — looks up by `mission_slug` directly.
3. `sync/events.py:235-245` `emit_mission_created()` — payload includes `mission_slug` and `mission_number` but **not `mission_id`**.
4. `sync/emitter.py:425-449` — same payload.
5. `status/models.py:244` `LanesManifest.mission_slug` — primary identifier in the status manifest.
6. `status/models.py:177` `MissionSnapshot.mission_slug` — primary in status snapshots.
7. `mission_metadata.py:79-84` `MissionIdentity` dataclass — has `mission_slug`, `mission_number`, `mission_type` but **not `mission_id`**.
8. `mission_metadata.py:121-129` `resolve_mission_identity(feature_dir)` — reads `meta.json` and returns the above three fields.

### Locked decision

- **Mint a ULID `mission_id`** in `core/mission_creation.py:create_mission_core()` at creation time. Add as a `meta.setdefault("mission_id", str(ulid.ULID()))` line.
- **Persist** to `meta.json` alongside the existing field set.
- **Add `mission_id: str | None = None`** to `MissionIdentity` dataclass at `mission_metadata.py:79-84`. The `None` default is a legacy-tolerance hook for missions that predate the change — used **only** to allow `MissionIdentity` to load historical missions for human-display purposes per NG-1.
- **Add `mission_id` to `emit_mission_created()`** payload at `sync/events.py:235-245` and `sync/emitter.py:425-449`. Additive schema change.
- **Lock the create-write transaction** with the existing `feature_status_lock_path` pattern (from `status/locking.py`). ULID is collision-resistant by construction, so the lock is for write atomicity, not for identity uniqueness.
- **Mission 079 itself has no `mission_id` today** (verified). Track 3's first WP MUST add it to mission 079's own `meta.json` so 079 dogfoods the new identity model.

### Rejected alternatives

- **Use UUID4 instead of ULID**: rejected because the ADR explicitly mandates ULID for its lexicographic sortability and rough chronological ordering. ULID is also already in `pyproject.toml`.
- **Use a SHA-256 of `mission_slug + created_at`**: rejected because it does not satisfy collision resistance under concurrent creation (two clones could create with the same slug at the same instant).
- **Keep using `get_next_feature_number()` and just add a separate `mission_id` field**: this is exactly the chosen path. The numeric prefix allocator stays as a display-helper but is no longer the canonical identity allocator.
- **Backfill historical missions with `mission_id`**: rejected per NG-2.

---

## Track 4 — Tasks/finalize hotfix (narrow slice for #525)

### Current state

**Parser entry**: `src/specify_cli/core/dependency_parser.py:143-166` `parse_dependencies_from_tasks_md(tasks_content)`.

**Section splitter**: `_split_wp_sections()` at lines 39-59. Uses regex `_WP_SECTION_HEADER` to match `## WP##`, `## Work Package WP##`, or `### WP##` headers, then:
```python
for idx, match in enumerate(matches):
    wp_id = match.group(1)
    start = match.end()
    end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tasks_content)
    sections[wp_id] = tasks_content[start:end]
```
**Line 56 is the bug**: `else len(tasks_content)` slurps to EOF for the final WP section.

**Per-section dependency extraction**: `_parse_section_deps()` at lines 91-135 scans for **three explicit formats**:
1. Inline: `Depends on WP01, WP02` (lines 106-107)
2. Header-colon: `**Dependencies**: WP01, WP02` (lines 111-117)
3. Bullet list under `### Dependencies` heading (lines 120-133)

**Critical finding**: The parser does **NOT do prose inference**. The brief's wording ("infers dependencies from prose using regexes") is technically inaccurate. The actual failure mode is: trailing prose past the final WP gets included in the final section, and the explicit-format patterns (especially `Depends on WP##`) match within that trailing prose.

**Conflict / precedence handling**: `src/specify_cli/cli/commands/agent/tasks.py:1923-1937` (T004 "disagree-loud") raises an error when frontmatter `dependencies` differs from parsed `dependencies`. Lines 1962-1970 preserve frontmatter when parser finds nothing.

**Existing tests**: `tests/core/test_dependency_parser.py` — 21 test methods organized in 5 classes (TestInlineDependsOnFormat, TestInlineDependenciesColonFormat, TestBulletListFormat, TestMixedFormatsInSameFile, plus edge cases). None of them exercise trailing-prose past the final WP section.

### Locked decision

- **Bound `_split_wp_sections()`** so the final section ends at either:
  1. The next WP header (existing behavior — unchanged), OR
  2. A top-level `## ` markdown heading whose text is **not** a WP id (e.g., `## Notes`, `## Appendix`, `## References`), OR
  3. EOF (existing fallback — only when no other terminator is found).
- The bound regex stops at `^##\s` headings, NOT `^###\s` (sub-headings inside a WP section are preserved).
- **Precedence** (FR-302/FR-303) is implicitly satisfied because the parser already does not do prose inference. The "explicit declarations win" guarantee is enforced by `disagree-loud` and `preserve-existing` in `agent/tasks.py:1923-1970`. The plan adds an invariant comment in the parser docstring documenting this contract.
- **FR-304 regression test**: author a `tasks.md` with a final WP that declares `dependencies: []` (empty), followed by trailing prose `"This phase depends on WP01 being merged."` — assert the parser returns `WPN: []`, not `WPN: [WP01]`.

### Rejected alternatives

- **Require an explicit end-of-tasks marker** (e.g., `<!-- end-of-wps -->`): rejected because it would require migrating every existing `tasks.md` file in fresh clones — out of scope per NG-1.
- **Disable explicit-format detection entirely past the final WP**: rejected because this would change parser semantics globally; the heading-bound approach is more local and less invasive.
- **Implement the full manifest redesign**: explicitly out of scope per NG-3 / FR-305.

---

## Track 5 — Auth refresh race fix

### Current state

**File**: `src/specify_cli/sync/auth.py`.

**Credential file**: `~/.spec-kitty/credentials` (TOML format) at line 22. Lock file: `~/.spec-kitty/credentials.lock` at line 24.

**Lock type**: `filelock.FileLock` with 10-second timeout. Cross-process safe.

**Lock scope**: Per-I/O. `CredentialStore._acquire_lock()` (lines 38-40) is called inside `load()` (lines 42-51), `save()` (lines 53-92), and `clear()` (lines 94-101) — each releases immediately after the I/O.

**`refresh_tokens()`**: lines 324-394 of `auth.py`. Sequence:
1. Line 337: `get_refresh_token()` (acquires lock, reads, releases).
2. Line 345: HTTP POST to `/api/v1/token/refresh/` (**no lock held**).
3. Lines 349-351: On 401, calls `clear_credentials()` (acquires lock, deletes, releases) **without re-reading**.
4. Lines 384-392: On success, `save()` (acquires lock, writes, releases).

**This is the race**: the lock is released between step 1 and step 4. Process A and Process B can both read the same refresh token, then call the network independently. A wins (rotates the token); B's request becomes stale and returns 401; B clears credentials, kicking the user out.

**Refresh-token rotation parsing**: lines 360-362 of `auth.py`:
```python
new_access_token = data["access"]
new_refresh_token = data["refresh"]
```
The code accepts whatever `refresh` value the server returns (rotation is implicit) but does no explicit comparison.

**401 handling sites**:
1. `auth.py:349-351` — `refresh_tokens()` 401 → immediate clear (the bug).
2. `auth.py:420-430` — `obtain_ws_token()` 401 → `refresh_tokens()` then re-fetch access; if still gone, clear.
3. `tracker/saas_client.py:226-249` — **correct pattern**: refresh, then retry the same request, only clear if retry also returns 401.
4. `sync/batch.py:390-404` — 401 marks events failed with `auth_expired`; does not refresh.
5. `sync/client.py:136-146` — WebSocket 401 → refresh, then retry connection.

**Refresh call sites**: `auth.py:464` (`get_access_token` on expired access token), `auth.py:421` (WS 401 path), `client.py:141` (WebSocket connect retry), `saas_client.py:231` (HTTP request retry).

**Background sync**: `sync/background.py:315-335` `get_sync_service()` returns a daemon-threaded singleton timer (5-minute interval) that calls `auth.get_access_token()` from a background thread. This means **concurrent refresh between background and CLI is a real production code path**, not a theoretical race.

**Existing tests**: `tests/sync/test_auth.py` (392 lines) and `tests/agent/cli/commands/test_auth.py` (278 lines). **None test concurrent refresh, lock contention, 401 re-read, or token rotation.**

### Locked decision

- **Extend the FileLock scope** in `refresh_tokens()`. Acquire the lock at function entry, hold it across the network call and the persist step, release in `finally`.
- **Re-read on 401 under the lock**. Inside the locked transaction, on a 401:
  1. Re-read on-disk credentials.
  2. If `current_refresh_token != credentials_at_function_entry.refresh_token`, treat the 401 as **stale** and return cleanly without clearing.
  3. Otherwise, the 401 is authoritative; clear (still under the lock).
- **Reentrancy**: `filelock.FileLock` is reentrant per-thread by default. Inner `load()` / `save()` calls inside the locked transaction reacquire the lock as no-ops. Verify with a test.
- **httpx timeout < 10s file-lock timeout**: confirm in implementation; if not, set explicit httpx timeout to e.g. 8s.
- **Threading lock in background sync** (`sync/background.py`) is orthogonal and not changed.

### Rejected alternatives

- **Replace FileLock with a SQLite-based token store**: rejected as scope creep. The existing TOML + FileLock works; the bug is scope, not mechanism.
- **Treat all 401s as non-terminal**: rejected because legitimate revocation would never clear and the user would loop forever on broken tokens.
- **Clear credentials only after N consecutive 401s**: rejected as masking the real bug. The race is the issue; counting 401s is a workaround.

---

## Track 6 — Top-level `implement` de-emphasis

### Current state

**`spec-kitty implement` command**: `src/specify_cli/cli/commands/implement.py:389` docstring `"""Allocate or reuse the lane worktree for a work package."""`. Parameters: `wp_id`, `--mission`, `--feature` (deprecated), `--auto-commit`, `--json`, `--recover`, `--base`. **No deprecation marker on the command itself.**

**Places that teach top-level `spec-kitty implement` as canonical**:
1. **`init.py:641-650`** next-steps output. Line 647: `"   - [cyan]/spec-kitty.implement[/] - Execute implementation from /tasks/doing/"`. Note: this teaches the **slash command** `/spec-kitty.implement`, not the top-level CLI. Both are listed in this output, but the slash command is how new users are taught to drive implementation. The line itself stays, but its description should be updated to make clear it's the canonical path.
2. **`README.md:8-9`**: `\`spec\` -> \`plan\` -> \`tasks\` -> \`implement\` -> \`review\` -> \`merge\``. The `implement` here is ambiguous — could be the CLI or the slash command. New text should disambiguate to the slash-command path.
3. **`README.md:64-80`**: mermaid / ASCII diagram lists "⚡ Implement | Agent workflows" — same disambiguation needed.
4. **Slash-command source templates** under `src/specify_cli/missions/software-dev/command-templates/`:
   - `implement.md` lines 16-19 and 35-36 teach the slash command and reference top-level CLI invocation
   - `tasks.md` line 40 and lines 267-268: `"After tasks are generated, use \`spec-kitty implement WP##\` to create or reuse the execution workspace"` and `"No dependencies: \`spec-kitty implement WP01\`"`
   - `tasks-packages.md` lines 133-134: example commands `spec-kitty implement WP01` and `WP02`
   - `specify.md` line 145: `"Use \`spec-kitty implement WP##\` after task finalization"`
5. **Documentation under `docs/`** that names top-level `spec-kitty implement`:
   - `docs/explanation/{execution-lanes,git-workflow,spec-driven-development,kanban-workflow,multi-agent-orchestration,mission-system}.md`
   - `docs/how-to/{implement-work-package,parallel-development,handle-dependencies,recover-from-implementation-crash,sync-workspaces,diagnose-installation}.md`

### Second research pass — what is the canonical post-#555 workflow?

(Added after reviewer feedback P2 flagged the original Locked Decision as still routing the canonical path through legacy infrastructure with a slash prefix.)

The actual canonical post-#555 user workflow is **NOT** `/spec-kitty.implement` (slash) re-routed to the same legacy code. It is the **`spec-kitty next` loop** plus the **`spec-kitty agent action implement/review` per-decision verbs**:

| Surface | File:Lines | Role |
|---------|-----------|------|
| `spec-kitty next` (top-level command) | `src/specify_cli/cli/commands/next_cmd.py:24` (function `next_step`) | Loop entry. Agents call this repeatedly. Each call returns a JSON decision with `action` and `prompt_file`. Registered at `src/specify_cli/cli/commands/__init__.py:62` as `app.command(name="next")(next_cmd_module.next_step)`. |
| `spec-kitty agent action implement` | `src/specify_cli/cli/commands/agent/workflow.py:379` | Per-decision verb for implementation actions. Displays the WP prompt, manages lane state transitions (planned → claimed → in_progress), commits status updates. Registered as `app.add_typer(workflow.app, name="action")` in `agent/__init__.py:21`. **Note**: registered under name `action`, NOT `workflow`. |
| `spec-kitty agent action review` | `src/specify_cli/cli/commands/agent/workflow.py:1156` | Per-decision verb for review actions. Same shape as implement. |
| `spec-kitty implement` (top-level CLI) | `src/specify_cli/cli/commands/implement.py:389` | **Internal infrastructure**. `spec-kitty agent action implement` delegates workspace creation to this command under the hood. NOT a user-facing canonical surface in the new model. |

**Key finding**: The slash-command source template `src/specify_cli/missions/software-dev/command-templates/implement.md:159` already says `**Next step**: \`spec-kitty next --agent <name>\` will advance to review.` The slash-command templates already teach the right path. The gap is in `init.py` next-steps, `README.md`, `spec-kitty implement --help`, and the `docs/` getting-started prose — those still teach top-level `spec-kitty implement` as canonical.

**Important caveat**: `spec-kitty agent action implement` does internally call `spec-kitty implement` for workspace creation. This is an implementation detail, not a user-facing contract. The mission's job is to make sure no user is taught `spec-kitty implement` as a step they should invoke directly; the fact that the agent-facing wrapper happens to call into the legacy command is invisible to users.

### Locked decision

- **`init.py:641-650`**: rewrite the next-steps text to name `spec-kitty next --agent <name> --mission <slug>` as the canonical loop entry, and `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs. The text MUST NOT teach top-level `spec-kitty implement` as a user-facing CLI invocation.
- **`cli/commands/implement.py:389` docstring**: replace with text that marks the command as **internal infrastructure** (an implementation detail of `spec-kitty agent action implement`), not as a user-facing canonical path. Example: `"""Internal — allocate or reuse the lane worktree for a work package. This is an implementation detail of \`spec-kitty agent action implement\`. Users should invoke \`spec-kitty next --agent <name> --mission <slug>\` to drive a mission; agents should invoke \`spec-kitty agent action implement <WP> --agent <name>\` for per-WP work. This command remains as a compatibility surface for direct callers."""`
- **`README.md` canonical workflow line and mermaid diagram**: rewrite to name `spec-kitty next` as the canonical loop step and `spec-kitty agent action implement/review` as the per-decision verbs. Remove top-level `spec-kitty implement` from the canonical workflow line entirely.
- **`missions/software-dev/command-templates/{tasks,tasks-packages,specify,implement}.md`**: replace any remaining inline `spec-kitty implement WP##` examples with `spec-kitty agent action implement <WP> --agent <name>`. The slash-command file `/spec-kitty.implement` itself MAY stay as a slash command, but its body MUST resolve to `spec-kitty agent action implement` invocation, not to `spec-kitty implement` invocation.
- **`docs/` files**: update only canonical-path mentions in the first ~5 paragraphs of each file to name `spec-kitty next` and `spec-kitty agent action implement/review`. Troubleshooting / recovery / how-to-deeply contexts that describe `spec-kitty implement` as an internal detail are left alone.
- **Do NOT change `cli/commands/implement.py` execution behavior** (FR-505): the command still runs identically. Only the docstring changes. `spec-kitty agent action implement` continues to delegate to it for workspace creation; that delegation is an implementation detail, not a user-facing contract.

### Rejected alternatives

- **Delete `spec-kitty implement` command entirely**: rejected per FR-505 / D-4 (compatibility surface preserved).
- **Add a `--legacy` flag to `spec-kitty implement`**: rejected because the command isn't legacy-mode dependent — it's just no longer the **canonical path** for users. The de-emphasis is a doc/help/teaching change, not a runtime flag.
- **Print a deprecation banner when `spec-kitty implement` runs**: rejected because banners on every invocation would disrupt scripts that depend on the command. The compatibility surface stays silent.
- **Re-point `/spec-kitty.implement` slash command to the same `spec-kitty implement` legacy invocation under a slash prefix**: rejected per reviewer feedback P2. This would just rename the canonical path with a slash prefix while keeping the same execution surface; it does not de-emphasize anything. The slash command's body MUST resolve to `spec-kitty agent action implement`, which is the actual agent-facing wrapper.
- **Stabilize `spec-kitty implement` instead of de-emphasizing it**: rejected per spec D-4 / NG-7. Stabilization (#538/#540/#542) is intentionally deferred for `3.1.1`.

---

## Track 7 — Repo dogfood / version coherence

### Current state

| File | Line | Value |
|------|------|-------|
| `pyproject.toml` | 3 | `version = "3.1.1a3"` |
| `.kittify/metadata.yaml` | 6 | `version: 3.1.1a2` ⚠ **MISMATCH** |
| `CHANGELOG.md` | 10 | `## [Unreleased]` |
| `CHANGELOG.md` | 12 | `## [3.1.1a3] - 2026-04-07` |
| `CHANGELOG.md` | 24 | `## [3.1.1a2] - 2026-04-07` |
| `CHANGELOG.md` | 38 | `## [3.1.1a1] - 2026-04-07` |

**No `3.1.1` (stable) entry in CHANGELOG.md**. Format is Keep a Changelog with `### Added / ### Changed / ### Fixed` sub-sections.

**`.kittify/metadata.yaml` schema** (top-level keys):
```yaml
spec_kitty:
  version: <string>
  initialized_at: <ISO8601>
  last_upgraded_at: <ISO8601>
environment:
  python_version: <string>
  platform: <string>
  platform_version: <string>
migrations:
  applied: <list>
```

**Existing release infrastructure**:

| Module | Purpose |
|--------|---------|
| `src/specify_cli/release/version.py` (107 lines) | `propose_version(current, channel)` — pure function, computes next version per PEP 440 |
| `src/specify_cli/release/changelog.py` (233 lines) | `build_changelog_block(repo_root, since_tag=None)` — scans `kitty-specs/*/tasks/WP*.md` for accepted WPs and renders markdown |
| `src/specify_cli/release/payload.py` (124 lines) | `build_release_prep_payload(channel, repo_root)` — assembles version + changelog + structured inputs |
| `src/specify_cli/cli/commands/agent/release.py` (125 lines) | `spec-kitty agent release prep` — `--channel {alpha|beta|stable}`, `--repo`, `--json`. **Already exists.** |
| `scripts/release/validate_release.py` (389 lines) | `load_pyproject_version()`, `read_changelog()`, `changelog_has_entry(changelog, version)` (lines 179-194), `validate_version_progression()`, `ensure_tag_matches_version()` |

**`scripts/release/validate_release.py` does NOT validate `.kittify/metadata.yaml`.** This is the gap.

**CI integration**: `.github/workflows/release-readiness.yml` already calls `validate_release.py` in branch mode and emits a markdown summary; fails CI on validation failure.

**Dogfood command set existence check** (all confirmed present):
| Command | Source | Registration |
|---------|--------|--------------|
| `spec-kitty --version` | `src/specify_cli/__init__.py:92-94` | Callback option |
| `spec-kitty init` | `cli/commands/init.py:261, 793` | `register_init_command(app)` |
| `spec-kitty agent mission create` | `cli/commands/agent/mission.py` | `@app.command(name="create")` |
| `spec-kitty agent mission finalize-tasks` | `cli/commands/agent/mission.py` | `@app.command(name="finalize-tasks")` |
| `spec-kitty agent tasks status` | `cli/commands/agent/tasks.py:2424` | `@app.command(name="status")` |

### Locked decision

- **Bump `.kittify/metadata.yaml` version** to match `pyproject.toml`. Initially to `3.1.1a3`, then to `3.1.1` at the release cut.
- **Add `validate_metadata_yaml_version_sync(repo_root)`** to `scripts/release/validate_release.py`. Reads both files; asserts equal; reports mismatch with file paths and line numbers.
- **Wire the new check into `validate_release.py:main()`** in branch mode. CI picks it up automatically via the existing `.github/workflows/release-readiness.yml`.
- **CHANGELOG-presence check** (FR-606) is already implemented in `changelog_has_entry()`. Ensure it is called for the target version on every branch-mode validate (not only tag mode).
- **Structured draft artifact** (FR-605) is already implemented as `build_release_prep_payload()`. Add a test that asserts the payload structure for `channel="stable"` against the working repo.
- **No new CLI command needed**: `spec-kitty agent release prep` already exists. The plan reuses it.

### Rejected alternatives

- **Extract a separate `release/coherence.py` module**: deferred. If `validate_release.py` cannot host the new check cleanly, this becomes the fallback. Tracked as Risk R-7.1 in `plan.md`.
- **Add a `pre-commit` hook for version coherence**: rejected as out of scope for `3.1.1`. The CI gate is sufficient release-cut protection.
- **Auto-bump `.kittify/metadata.yaml` in CI when `pyproject.toml` changes**: rejected as auto-magic. The bump is an explicit WP and should be committed by a human/agent, not an automation.

---

## Cross-track summary

| Track | New deps | New files | Modified files | Tests |
|-------|----------|-----------|----------------|-------|
| 1 | none | 4 (4 new test files) | `init.py`, `git_ops.py` | 4 new + 1 extended |
| 2 | none | 4 (4 new test files) | `compute.py`, `models.py` (deprecation comment), `branch_naming.py`, `worktree.py`, `workspace_context.py`, `context/resolver.py`, `implement.py` (lookup change only) | 4 new |
| 3 | none (`python-ulid` already present) | 3 (3 new test files) + edit to mission 079's own `meta.json` | `mission_creation.py`, `mission_metadata.py`, `sync/events.py`, `sync/emitter.py` | 3 new |
| 4 | none | 0 (extends existing test file) | `dependency_parser.py` | 1 extension |
| 5 | none | 1 new test file | `sync/auth.py` | 1 new |
| 6 | none | 2 new test files + multiple template/doc edits | `init.py` (overlap with Track 1), `cli/commands/implement.py` (docstring only), `README.md`, mission templates, ~12 docs files (canonical-path mentions only) | 2 new |
| 7 | none | 3 new test files | `.kittify/metadata.yaml`, `pyproject.toml` (release-cut WP only), `scripts/release/validate_release.py`, possibly `release/coherence.py` (R-7.1) | 3 new |

**Total new test files**: 17. **Total modified production files**: ~22. **No new third-party dependencies.**

---

## Outstanding ambiguities

**None**. Phase 0 has resolved every engineering unknown. Phase 1 (data-model + contracts + quickstart) proceeds.
