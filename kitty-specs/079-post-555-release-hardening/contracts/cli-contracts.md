# CLI Contracts: 3.1.1 Post-555 Release Hardening

**Mission**: `079-post-555-release-hardening`
**Purpose**: Per-track CLI behavior contracts. These are the user-facing command surfaces that the implementation MUST satisfy. Each contract maps to one or more FRs in `spec.md`.

This is a **CLI contract** document, not a REST/OpenAPI spec, because this mission's external surface is a CLI tool. The contracts below describe inputs, outputs, exit codes, side effects, and absences (what the command MUST NOT do).

---

## Track 1 — `spec-kitty init`

### Contract C1.1: `spec-kitty init <name> --ai <agent> --non-interactive` against an empty directory

**Maps to**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-008

**Inputs**:
- `<name>`: string, valid filesystem name
- `--ai <agent>`: one of the 12 supported agents
- `--non-interactive`: present
- Working directory: an empty directory the user has cd'd into, OR a parent directory under which `<name>` will be created

**Side effects (REQUIRED)**:
- Create `<target_dir>/.kittify/config.yaml` with the selected agent set.
- Create `<target_dir>/.kittify/metadata.yaml` with the current spec-kitty version.
- Create the per-agent slash-command files under the agent's directory (e.g., `.codex/prompts/spec-kitty.*.md` for `--ai codex`).
- Print next-step guidance to stdout that names `spec-kitty next` (the loop) and `spec-kitty agent action implement` / `spec-kitty agent action review` (the per-decision verbs).

**Side effects (FORBIDDEN)**:
- MUST NOT create `<target_dir>/.git/` under any flag combination. There is no `--git` opt-in.
- MUST NOT run `git init`, `git add`, or `git commit` under any flag combination.
- MUST NOT produce any commit, including any commit titled `"Initial commit from Specify template"` or any equivalent, under any flag combination.
- MUST NOT create `<target_dir>/.agents/skills/` or its contents.
- MUST NOT name top-level `spec-kitty implement` as the canonical implementation entrypoint in any printed text.
- MUST NOT accept the `--no-git` flag (the flag is removed in 3.1.1; passing it MUST produce a typer "no such option" error).

**Output to stdout**:
- A "Next steps" panel that names `spec-kitty next --agent <agent> --mission <slug>` as the canonical loop entry, and names `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs the agent invokes. The panel MUST NOT contain a line that names `spec-kitty implement` (the top-level CLI command) as a canonical user-facing command.

**Exit code**: 0 on success.

---

### Contract C1.2: `spec-kitty init` re-run in an already-initialized directory

**Maps to**: FR-006

**Inputs**: Same as C1.1, but the target directory already contains `.kittify/config.yaml` from a prior `init`.

**Acceptable behaviors** (one of):
- **Idempotent**: exit 0, produce no changes, print a clear message that the directory is already initialized.
- **Fail-fast**: exit non-zero with a clear error message naming the conflict (e.g., `Error: <target_dir>/.kittify/config.yaml already exists. Run \`spec-kitty upgrade\` to migrate or delete the directory and re-run.`).

**Forbidden**:
- Silent merge or overwrite of existing state.

---

### Contract C1.3: `spec-kitty init` invoked inside an existing git repository

**Maps to**: FR-007

**Inputs**: Same as C1.1, but the working directory (or a parent of it) is inside an existing git working tree.

**Side effects (REQUIRED)**:
- Same as C1.1 — file creation only.

**Side effects (FORBIDDEN)**:
- MUST NOT call `git init`, `git add`, `git commit`, `git checkout`, or any git-state-mutating command.
- MUST NOT touch the existing git tree's HEAD, branches, or staged state.
- MUST NOT modify `.gitignore` of the parent repo unless the new files would otherwise be untracked and the project explicitly opts into `.gitignore` management (NOT enabled by default).

---

### Contract C1.4: `spec-kitty init --help`

**Maps to**: FR-008

**Output to stdout**:
- The help text MUST describe the new model accurately:
  - No git initialization (and no `--git` opt-in flag)
  - No automatic commit
  - The `--no-git` flag from pre-3.1.1 versions is removed
  - Next-step guidance names `spec-kitty next` and `spec-kitty agent action implement/review`

**Exit code**: 0.

---

## Track 2 — `spec-kitty agent mission finalize-tasks` (planning-artifact producer)

### Contract C2.1: Lane assignment for a feature with planning-artifact WPs

**Maps to**: FR-101, FR-102, FR-103, FR-104

**Inputs**:
- `--mission <slug>`: a mission whose `tasks.md` declares at least one planning-artifact WP and at least one code WP.

**Behavior**:
- `compute_lanes()` MUST return a `LanesManifest` whose `lanes` list includes a lane with `lane_id == "lane-planning"` containing all planning-artifact WPs.
- The lane assignment for code WPs MUST be unaffected by this change.
- `LanesManifest.planning_artifact_wps` MAY remain as a derived view (for backward-compat), but MUST be derivable from the lane assignments.

**Side effects (REQUIRED)**:
- Write `kitty-specs/<mission_slug>/lanes.json` containing the new manifest.

**Side effects (FORBIDDEN)**:
- MUST NOT skip planning-artifact WPs from the lane assignment loop.
- MUST NOT call `git worktree add` for the `lane-planning` lane.

---

### Contract C2.2: `spec-kitty implement WP##` for a planning-artifact WP

**Maps to**: FR-105 (consumer uniformity)

**Inputs**:
- `WP##`: a planning-artifact work package id from a finalize-tasks-completed mission.
- `--mission <slug>`: the mission slug.

**Behavior**:
- The command MUST resolve the WP's lane via the uniform lane lookup (no `if execution_mode == "planning_artifact"` branch in `context/resolver.py`).
- The lane lookup MUST return the `lane-planning` lane.
- The resolved workspace path MUST be the main repo checkout (`paths.get_main_repo_root()`), NOT a `.worktrees/...` directory.
- The command MUST exit 0 with a clear "workspace = main repo checkout" indication.

**Side effects (FORBIDDEN)**:
- MUST NOT create a `.worktrees/<mission_slug>-lane-planning` directory.
- MUST NOT branch on a `planning_artifact` WP-type sentinel at the lane-contract boundary.

---

## Track 3 — `spec-kitty agent mission create` (identity hardening)

### Contract C3.1: `spec-kitty agent mission create <slug> --json`

**Maps to**: FR-201, FR-204, FR-205

**Inputs**:
- `<slug>`: a kebab-case unnumbered slug
- `--json`: present

**Behavior**:
- The command MUST mint a ULID `mission_id` at creation time.
- The command MUST persist `mission_id` in `kitty-specs/<numbered_slug>/meta.json`.
- The command MUST NOT use the `get_next_feature_number()` scan as the source of canonical identity (it MAY continue to be used to compute the display-friendly numeric prefix).
- The output JSON MUST include `mission_id` as a top-level field.

**Output (stdout, JSON)**:
```json
{
  "result": "success",
  "mission_id": "<ulid string>",
  "mission_slug": "<###-slug>",
  "mission_number": "<###>",
  "...": "..."
}
```

**Concurrency**:
- Two concurrent invocations of this command from two checkouts of the same repository MUST NOT produce colliding `mission_id` values. (ULID collision resistance is sufficient — no explicit lock is required for uniqueness, but the `meta.json` write SHOULD use the existing `feature_status_lock_path` for write atomicity.)

---

## Track 4 — `spec-kitty agent mission finalize-tasks` (parser hotfix)

### Contract C4.1: Bounded final WP section

**Maps to**: FR-301, FR-302, FR-303, FR-304

**Inputs**:
- A `tasks.md` file authored by an operator that contains:
  - A final WP section (`## WP##` or `## Work Package WP##`)
  - Trailing prose after the final WP section that mentions other WPs in `Depends on WP##` form
  - The final WP carries an explicit `dependencies:` declaration in its frontmatter

**Behavior**:
- The dependency parser MUST bound the final WP section so that the trailing prose is NOT included in the final WP's body.
- The bound MUST trigger at: (a) the next WP header, (b) a top-level `## ` markdown heading whose text is not a WP id, or (c) EOF.
- Sub-headings (`### `) inside the WP section MUST NOT trigger the bound.
- The explicit `dependencies:` declaration MUST be preserved verbatim in the finalized manifest.

**Forbidden**:
- MUST NOT inject WPs from trailing prose into the final WP's parsed dependencies.
- MUST NOT overwrite explicit `dependencies:` declarations with parser-derived values.

---

## Track 5 — Auth refresh

### Contract C5.1: `refresh_tokens()` lock contract

**Maps to**: FR-401, FR-402, FR-403, FR-404

**Behavior** (internal — not a user-facing CLI command, but a contract for the function):
- `auth.refresh_tokens()` MUST acquire the cross-process `filelock.FileLock` at function entry.
- The lock MUST be held for the FULL transaction: read on-disk credentials → HTTP POST to `/token/refresh/` → parse response → persist new credentials (or handle failure).
- The lock MUST be released in a `finally` block.
- On 401 from the refresh endpoint:
  - The function MUST re-read on-disk credentials under the held lock.
  - If the on-disk refresh token differs from the value read at function entry, the 401 is **stale**: exit cleanly without clearing.
  - If the on-disk refresh token is unchanged, the 401 is **terminal**: clear credentials (under the held lock) and raise `AuthenticationError`.
- Inner `load()` / `save()` calls inside the locked transaction reacquire the lock as no-ops (reentrancy).

**User-facing observable behavior** (under contention):
- Two concurrent CLI invocations that race a refresh, where one rotates the refresh token successfully and the other races, MUST result in the user remaining logged in. The losing process MUST observe the rotated token on its re-read and exit cleanly.

---

## Track 6 — Top-level `spec-kitty implement` and canonical-path teach-out

### Contract C6.1: `spec-kitty implement --help`

**Maps to**: FR-503

**Output to stdout**:
- The help text MUST mark `spec-kitty implement` as **internal infrastructure** — an implementation detail of `spec-kitty agent action implement`, not a user-facing canonical path.
- The help text MUST direct callers to `spec-kitty next` for the loop and `spec-kitty agent action implement` for the per-WP verb.

**Example acceptable docstring**:
> `Internal — allocate or reuse the lane worktree for a work package. This is an implementation detail of \`spec-kitty agent action implement\` and is not a canonical user-facing command. Users should invoke \`spec-kitty next --agent <name> --mission <slug>\` to drive a mission; agents should invoke \`spec-kitty agent action implement <WP> --agent <name>\` for per-WP work. This command remains as a compatibility surface for direct callers.`

---

### Contract C6.2: `spec-kitty implement WP##` (compatibility execution)

**Maps to**: FR-505

**Behavior**:
- The command MUST still run for direct invokers.
- The command MUST allocate or reuse the lane worktree exactly as it does today.
- The command MUST NOT print a deprecation banner on every invocation (banners on every run are forbidden by R-6 in plan.md).

**Exit code**: 0 on success, non-zero on error (unchanged behavior).

---

### Contract C6.3: `spec-kitty init` next-steps output (overlap with Track 1)

**Maps to**: FR-501, FR-502 (init's printed output) and FR-504 (the slash-command guidance shipped by init)

**Output to stdout**:
- The next-steps panel MUST NOT name top-level `spec-kitty implement` as a canonical user-facing path.
- The next-steps panel MUST direct users at the `spec-kitty next` loop and the `spec-kitty agent action implement` / `spec-kitty agent action review` per-decision verbs (the actual post-#555 canonical user workflow per D-4).

---

### Contract C6.4: `README.md` canonical workflow text

**Maps to**: FR-502

**Static content rule**:
- `README.md` lines 8-9 (the canonical workflow line) MUST NOT name `\`implement\`` as a step in a way that implies top-level `spec-kitty implement` is the canonical command-line invocation.
- The mermaid / ASCII diagram (lines 64-80) MUST NOT name top-level `spec-kitty implement` as a step.

---

## Track 7 — Release-hygiene CLI surface

### Contract C7.1: `scripts/release/validate_release.py` in branch mode

**Maps to**: FR-601, FR-602, FR-606

**Behavior**:
- The script MUST validate that `pyproject.toml` `[project].version` equals `.kittify/metadata.yaml` `spec_kitty.version`.
- If the two versions disagree, the script MUST exit non-zero and emit a clear error message that names both files and both values.
- The script MUST also call `changelog_has_entry(changelog, target_version)` and fail the cut if the entry is missing.

**Exit code**: 0 if all gates pass; non-zero (1 by convention) on any failure.

**Error message format** (example):
```
ERROR: Version mismatch
  pyproject.toml          line 3:  3.1.1
  .kittify/metadata.yaml  line 6:  3.1.1a3
Both files must report the same version before the release can be cut.
```

---

### Contract C7.2: `spec-kitty agent release prep --channel stable --json`

**Maps to**: FR-605

**Behavior**:
- The command MUST produce a structured JSON payload representing the proposed release prep.
- The payload MUST include a `proposed_changelog_block` field whose value is a non-empty markdown block whose header references the target version (e.g., starts with `## [3.1.1`).
- The payload MUST NOT mutate any file in the working tree (it is a draft generator, not a mutator).

**Exit code**: 0 on success.

---

### Contract C7.3: Dogfood command set against `/private/tmp/311/spec-kitty`

**Maps to**: FR-603, FR-604

**Behavior**:
- A fresh shell, with the CLI installed from the release commit, MUST be able to run each of the following commands and observe exit code 0 with no error rooted in version skew:
  1. `spec-kitty --version`
  2. `spec-kitty init demo --ai codex --non-interactive` (against a fresh empty directory under `/tmp/`)
  3. `spec-kitty agent mission create dogfood --json` (against `/private/tmp/311/spec-kitty`)
  4. `spec-kitty agent mission finalize-tasks --mission dogfood` (against `/private/tmp/311/spec-kitty`)
  5. `spec-kitty agent tasks status --mission dogfood` (against `/private/tmp/311/spec-kitty`)

**Acceptance**: All five commands exit 0 and produce no error output naming version mismatch.

---

## Out-of-band contracts

The following contracts are listed for completeness but are NOT enforced as CLI behavior — they are documentation / scope assertions:

- **FR-206** (no historical mission identity backfill): asserted via PR review, not via CLI behavior.
- **FR-305** (no full manifest redesign): asserted via PR review, not via CLI behavior.
- **FR-506** (no #538/#540/#542 stabilization): asserted via PR review, not via CLI behavior.
