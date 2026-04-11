---
work_package_id: WP06
title: ADR and documentation
dependencies:
- WP01
- WP02
- WP03
- WP04
requirement_refs:
- FR-001
- FR-004
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
agent: "claude:sonnet:python-implementer:implementer"
shell_pid: "88497"
history:
- at: '2026-04-11T06:22:58Z'
  actor: claude:/spec-kitty.tasks
  event: created
  note: Generated from DIRECTIVE_003 (Decision Documentation Requirement) and research.md.
authoritative_surface: architecture/
execution_mode: code_change
feature_slug: 082-stealth-gated-saas-sync-hardening
owned_files:
- architecture/ADR-saas-rollout-and-readiness.md
- architecture/README.md
priority: P3
tags: []
---

# WP06 — ADR and documentation

## Objective

Capture the architectural decisions made in this mission in a single ADR under `architecture/`, update the architecture index to reference it, and refresh any user-facing docs that currently describe the SaaS rollout gate as a single yes/no for all readiness. This WP discharges DIRECTIVE_003 (Decision Documentation Requirement) for the mission.

## Context

DIRECTIVE_003 (loaded from the charter context for this action) requires that material technical and governance decisions be captured with enough context that future contributors can understand why a path was chosen and what constraints must remain true. This mission has made several such decisions:

1. **Rollout gate and readiness evaluator are split into two abstractions.** The env var (`SPEC_KITTY_ENABLE_SAAS_SYNC`) controls *visibility* of the hosted surface; the `HostedReadiness` evaluator controls *per-prerequisite actionability* inside the gate. These are separate concerns and were deliberately not merged.
2. **Background daemon policy is a config key, not a CLI flag.** Operator preference for local resource use belongs in `~/.spec-kitty/config.toml`, not in per-invocation arguments.
3. **Tracker remains ungated.** `spec-kitty-tracker==0.3.0` is an external dependency and does not participate in rollout gating. Only the CLI and SaaS own that posture.
4. **Backwards-compatibility shims are retained.** The old `tracker/feature_flags.py` and `sync/feature_flags.py` continue to re-export the canonical symbols to avoid a flag day across every call site.
5. **Future migration paths are explicitly deferred.** Project-level override of `sync.background_daemon`, subdividing `MISSING_AUTH`, and collapsing the BC shims are all out-of-scope and documented as such.

This WP writes these decisions into a single ADR that lives in `architecture/`. Because the ADR describes *what shipped*, it must be written **after** the preceding four WPs have landed — a draft written too early will drift from the code and be wrong at merge time.

**Branch strategy**: Current branch at workflow start: main. Planning/base branch for this feature: main. Completed changes must merge into main. Execution worktrees are allocated per computed lane from `lanes.json`; this WP depends on WP01+WP02+WP03+WP04 and runs in its own lane (Lane D) after they all land.

## Files touched

| File | Action | Notes |
|---|---|---|
| `architecture/ADR-saas-rollout-and-readiness.md` | **create** | The new ADR. Pick the next available number from `architecture/README.md` and rename the file accordingly before committing (e.g., `ADR-0011-saas-rollout-and-readiness.md`). |
| `architecture/README.md` | **modify** | Add one index row referencing the new ADR. |

The `owned_files` in the frontmatter use the unnumbered filename as a placeholder. The implementing agent must rename the file to the next available `ADR-NNNN-` number before committing. Update both the filename and the frontmatter's `owned_files` entry to match.

## Subtasks

### T027 — Write the ADR

**Purpose**: Capture the mission's architectural decisions in the format `architecture/README.md` already uses.

**Steps**:

1. Read `architecture/README.md` to find:
   - The existing ADR numbering scheme (e.g., `ADR-0001-...`, `ADR-0002-...`)
   - The highest existing number; use N+1 for this ADR
   - The template or structural convention followed by the existing ADRs
2. Create `architecture/ADR-NNNN-saas-rollout-and-readiness.md` (substituting the real number) with the following sections:

   **Title**: "ADR-NNNN: SaaS Rollout Gate and Hosted Readiness Split"

   **Status**: Accepted (dated 2026-04-11 or the merge date)

   **Context**:
   - Summarize the stealth rollout posture: `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is the internal opt-in gate. Customers fail closed.
   - Note the pre-existing problem: `is_saas_sync_enabled()` was duplicated across `tracker/` and `sync/`, the CLI hid the tracker group correctly, but inside enabled mode every command did ad hoc preflight checks and emitted a single generic "gate error" message.
   - Cite the mission spec (`kitty-specs/082-stealth-gated-saas-sync-hardening/spec.md`) as the source of requirements.

   **Decision**:
   - State the five decisions from the Context section above, in full sentences.
   - For each decision, link to the relevant file (`src/specify_cli/saas/rollout.py`, `src/specify_cli/saas/readiness.py`, `src/specify_cli/sync/config.py`, `src/specify_cli/sync/daemon.py`).

   **Consequences**:
   - BC shims at `src/specify_cli/tracker/feature_flags.py` and `src/specify_cli/sync/feature_flags.py` continue to live; removing them is a future cleanup mission.
   - `HostedReadiness` becomes the single fan-in point for any new hosted-prereq — future missions add states here rather than sprinkling checks across commands.
   - Operators have a new config knob in `~/.spec-kitty/config.toml` under `[sync].background_daemon`.
   - The three daemon call sites (`dashboard/server.py`, `dashboard/handlers/api.py`, `sync/events.py`) now declare intent explicitly, and a CI grep guard prevents silent proliferation.
   - Project-level override of the daemon policy is deliberately deferred; the migration path is a `resolve_background_daemon_policy(repo_root)` helper that layers project config over user config.
   - The env-var gate itself is **not removed** in this mission; it remains the rollout posture for the current internal-testing window.

   **Alternatives Considered**:
   - Pull the rollout gate into each command as a per-command flag → rejected: would not give per-prerequisite messaging, would duplicate the env-var read in every command.
   - Single unified gate that covers both visibility and readiness → rejected: conflates stealth rollout with operational diagnostics; NFR-002 would be unachievable.
   - Add rollout logic to `spec-kitty-tracker==0.3.0` → explicitly rejected by spec C-002; tracker is a pinned external dependency and is not the owner of rollout posture.
   - Environment variable for daemon policy → rejected: overloads the env-var surface and confuses the rollout story.
   - Project-level daemon config in this mission → rejected as scope creep; documented as a future migration path.

   **References**:
   - `kitty-specs/082-stealth-gated-saas-sync-hardening/spec.md`
   - `kitty-specs/082-stealth-gated-saas-sync-hardening/plan.md`
   - `kitty-specs/082-stealth-gated-saas-sync-hardening/research.md` (R-001 through R-006)
   - `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md`
   - `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/hosted_readiness.md`
   - `kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/background_daemon_policy.md`

3. Match the existing ADR style (heading levels, code block conventions, link format). Do not introduce a new template.

**Files**: `architecture/ADR-NNNN-saas-rollout-and-readiness.md` (~180 lines of prose + code references)

**Validation**: The file exists, matches the repo's ADR conventions, and references the actual shipped files by path.

### T028 — Update `architecture/README.md` index

**Purpose**: Make the new ADR discoverable via the architecture index.

**Steps**:

1. Read `architecture/README.md` and find the ADR index (table, list, or whatever structure the repo uses).
2. Add one new row/entry for the new ADR following the existing format. Fields typically include: number, title, status, brief summary, date.
3. Preserve the ordering convention (alphabetical, numerical, chronological — match what the file already does).
4. Do **not** restructure the index or rewrite any existing entries.

**Files**: `architecture/README.md` (1 new line/row)

**Validation**: `rg "saas-rollout-and-readiness" architecture/README.md` returns exactly one match.

### T029 — Refresh user-facing docs if needed

**Purpose**: Point users at the new ADR if any existing doc describes SaaS sync in terms that the mission has now changed.

**Steps**:

1. Grep `docs/` for the following terms:
   - `SPEC_KITTY_ENABLE_SAAS_SYNC`
   - `saas sync` / `SaaS sync`
   - `tracker` (filter noise)
   - `background daemon` / `sync daemon`

2. For each hit, classify:
   - **Accurate after this mission** → leave untouched.
   - **Describes the single gate error but the reality is now per-prerequisite** → add a brief sentence pointing at the new ADR; do not rewrite the whole doc.
   - **Describes daemon auto-start without mentioning the new `[sync].background_daemon` key** → add one sentence referencing the new config key; link to the contract file if a user-facing reference already exists.

3. If there are **no hits that need updating**, document that fact in the commit message (`no user-facing docs required updates`) and proceed — this subtask is conditional.

4. Do **not** add new doc files in this WP. A follow-up user-guide mission can flesh out documentation once this change is in the wild.

**Files**: `docs/**.md` (zero or more minor edits, each < 5 lines)

**Validation**: `pytest -q` and `rg "SPEC_KITTY_ENABLE_SAAS_SYNC" docs/` both return expected results. If no doc edits were made, this subtask still passes — the grep is for verification, not required mutation.

**Note**: This subtask's owned-files list in the frontmatter does NOT include `docs/**.md` paths because the set is conditional. If T029 makes edits, add the specific touched files to the WP frontmatter's `owned_files` **before** committing so finalize-tasks validates correctly. If T029 makes no edits, leave the frontmatter unchanged.

## Test Strategy

This WP is pure documentation. The "tests" are:
- `rg` to verify the index entry exists and the ADR file is present
- `pytest -q` regression run to confirm no code regressed (should be a no-op since only docs changed)
- Manual read of the ADR against the research.md and the actual shipped code to confirm fidelity

## Definition of Done

- [ ] `architecture/ADR-NNNN-saas-rollout-and-readiness.md` exists with the correct next-available number and full content per T027.
- [ ] `architecture/README.md` has one new index entry referencing the ADR.
- [ ] Any `docs/` files that described the old behavior as a single gate error now point at the ADR (or the grep shows no such files existed).
- [ ] `pytest -q` still green.
- [ ] No source-code files modified (only `architecture/` and optionally `docs/`).
- [ ] `owned_files` in this WP's frontmatter updated to reflect any additional `docs/` edits made during T029.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| ADR drifts from what actually shipped | This WP runs **after** WP01–WP04. Reviewer must diff the ADR against the actual merged code before approving. |
| Wrong next-available ADR number | Read `architecture/README.md` at implementation time; do not trust the placeholder. If two ADRs land simultaneously in the same mission window, the second-to-merge may need a bump — the reviewer catches this during the final rebase. |
| `docs/` grep finds zero hits and the author incorrectly believes that means "skip T029" | T029 is explicitly allowed to be a no-op, but the implementer must **still grep and document** the search results. A grep with zero hits is a valid outcome, not a skip. |
| Adding an ADR file triggers some unrelated test that validates the architecture directory structure | Run `pytest -q` full suite before committing. If a structural test fails, investigate — may need to update the test to accept the new file. |

## Reviewer Guidance

- Read the ADR against `research.md` R-001 through R-006 — every decision recorded in research should be represented in the ADR.
- Spot-check the ADR against the actual file paths in `src/specify_cli/saas/`, `src/specify_cli/sync/config.py`, and `src/specify_cli/sync/daemon.py` to confirm nothing is aspirational.
- Verify the next-available ADR number is correct (no collision with other in-flight ADRs).
- If T029 made `docs/` edits, verify they are minimal and point-in-time (no speculative rewrites).
- Confirm the WP frontmatter's `owned_files` matches what was actually committed.

## Implementation command

```bash
spec-kitty agent action implement WP06 --agent <name>
```

## Activity Log

- 2026-04-11T09:34:25Z – claude:sonnet:python-implementer:implementer – shell_pid=88497 – Started implementation via action command
- 2026-04-11T09:44:24Z – claude:sonnet:python-implementer:implementer – shell_pid=88497 – ADR + README index + docs review complete. No docs/ updates needed (T029 grep returned zero hits).
- 2026-04-11T09:57:02Z – claude:sonnet:python-implementer:implementer – shell_pid=88497 – Review PASS. ✓ ADR landed at architecture/2.x/adr/2026-04-11-1-saas-rollout-and-readiness.md following repo naming convention. ✓ README index updated with Notable Recent ADRs table. ✓ docs/ grep returned zero hits — no user-facing docs needed updating. ✓ ADR captures all 6 decisions (R-001 through R-006): shared saas/ package, 6-state HostedReadiness with get_saas_base_url(), BackgroundDaemonPolicy config, intent-gated daemon, tracker stays ungated, env-var gate preserved. DIRECTIVE_003 (Decision Documentation Requirement) satisfied. All 6 WPs approved — ready for spec-kitty merge.
