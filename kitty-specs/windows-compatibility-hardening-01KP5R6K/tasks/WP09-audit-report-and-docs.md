---
work_package_id: WP09
title: Audit report + ADRs + docs + follow-ups
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
requirement_refs:
- FR-018
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T052
- T053
- T054
- T055
- T056
- T057
- T058
- T059
- T060
history:
- timestamp: '2026-04-14T10:41:03Z'
  actor: planner
  event: created
authoritative_surface: architecture/
execution_mode: planning_artifact
owned_files:
- architecture/2026-04-14-windows-compatibility-hardening.md
- architecture/adrs/2026-04-14-1-windows-auth-platform-split.md
- architecture/adrs/2026-04-14-2-windows-runtime-state-unification.md
- docs/explanation/windows-state.md
- CLAUDE.md
tags: []
---

# WP09 — Audit report + ADRs + docs + follow-ups

## Branch strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: per-lane `.worktrees/windows-compatibility-hardening-01KP5R6K-lane-<id>/`.
- Implement command: `spec-kitty agent action implement WP09 --agent <name>`. Begin only after WP01–WP08 are all merged to main.

## Objective

Run the second-pass repo-wide Windows audit per FR-018, classify every finding, and produce the permanent governance artifacts: a committed audit report, two ADRs (auth platform split + storage unification), a new `docs/explanation/windows-state.md` explainer, a `CLAUDE.md` update for the Windows state layout, and filed GitHub follow-up issues for any residuals. Verify close-out posture for GitHub issues #603 (Credential Manager removal) and #260 (worktree subdirectory incompatibility).

## Context

- **Spec IDs covered**: FR-018 (second-pass audit), FR-019 (docs including CLAUDE.md), SC-005 (audit report with every finding classified), SC-006 (#603 closeable), SC-007 (#260 closeable or scoped).
- **Research**: [`research.md` R-12](../research.md) audit methodology.
- **Charter alignment**: DIRECTIVE_003 Decision Documentation + DIRECTIVE_010 Specification Fidelity.

## Detailed subtasks

### T052 — Run repo-wide grep audit per FR-018 pattern list

**Purpose**: Capture every residual Windows-risk hit in the repo after WP01–WP08 have landed.

**Steps**:
1. From the repo root, run each pattern set listed in FR-018 and [`research.md` R-12](../research.md). Example commands (use `rg` / `grep -rn` per local preference):
   ```bash
   # Literals
   git grep -nE '~/\.kittify|~/\.spec-kitty|\.config/spec-kitty'
   # Platform calls
   git grep -nE 'import fcntl|import msvcrt|os\.symlink|os\.link|Path\.symlink_to'
   # Subprocess smells
   git grep -nE 'shell=True|sh -c|/bin/sh|"python3 |"python"|bare python'
   # Encoding
   git grep -nE 'open\([^,)]+\)[^,)]*$' | grep -v 'encoding='
   git grep -nE '\.decode\([^,)]*\)' | grep -v 'errors='
   # Windows idioms
   git grep -nE 'os\.name|sys\.platform|%APPDATA%|%LOCALAPPDATA%|powershell|cmd\.exe|PYTHONUTF8'
   # Hook/install
   git grep -nE 'pre-commit|hooks/|chmod|0o755|0o644'
   # Tests
   git grep -nE '@pytest\.mark\.skipif.*win|sys\.platform' -- 'tests/**'
   ```
2. Collect all raw hits into a scratch file (e.g. `/tmp/windows-audit-raw.txt`).
3. Keep this raw log for reference in the audit report.

**Validation**:
- Raw log exists with ≥ 50 lines of hits (or fewer if the codebase is already clean).

### T053 — Classify each finding

**Purpose**: Each hit is either safe, fixed, covered-by-CI, or follow-up.

**Steps**:
1. Read each hit in context (the surrounding code).
2. Assign one of four labels:
   - **Safe**: False positive (grep matched a comment, docstring, or intentionally-POSIX-only path).
   - **Fixed**: Addressed in WP01–WP08; cite the WP.
   - **CI-covered**: Behavior is correct but regression is prevented by a test in the curated Windows CI suite; cite the test.
   - **Follow-up**: Real Windows risk not covered by this mission; file a GitHub issue.
3. For each Follow-up, record a short note describing the risk and a proposed scope.

**Validation**:
- Classification table is exhaustive: every hit has a label.

### T054 — Write `architecture/2026-04-14-windows-compatibility-hardening.md`

**Purpose**: The canonical audit artifact (DIRECTIVE_003).

**Steps**:
1. Create `architecture/2026-04-14-windows-compatibility-hardening.md`.
2. Structure:
   ```markdown
   # Windows Compatibility Hardening — Audit Report (2026-04-14)

   **Mission**: windows-compatibility-hardening-01KP5R6K
   **Commit range**: <start-sha>..<end-sha>
   **Method**: second-pass repo-wide grep audit per FR-018 pattern list (see research.md R-12).

   ## Summary

   - Total raw hits: <N>
   - Safe (false positives): <N>
   - Fixed by this mission: <N>
   - Covered by new Windows CI: <N>
   - Filed as follow-up issues: <N>

   ## Closeable GitHub issues

   - #603 — Remove dependency on Windows Credential Manager: CLOSEABLE. Fixed by WP03. See ADR `2026-04-14-1-windows-auth-platform-split.md`.
   - #260 — <status per T060>

   ## Classification table

   | Hit | File:Line | Label | WP / Test / Follow-up | Note |
   |---|---|---|---|---|
   | ... |

   ## Follow-up issues filed

   - #<N1> — <title> — scope: <brief>
   - ...

   ## Whitelist (for the static audit test in tests/audit/test_no_legacy_path_literals.py)

   The following occurrences of `~/.kittify` / `~/.spec-kitty` are intentional
   (e.g., POSIX-only path under a `sys.platform != "win32"` branch, or
   documentation strings). They are listed here so the static test can
   whitelist them if needed.

   - <file:line>: <rationale>
   ```
3. Include a final "Residual risk" section summarizing anything unresolved.

**Validation**:
- File exists, is valid Markdown, and every classification-table row has all four columns populated.

### T055 — Write ADR: windows-auth-platform-split [P]

**Purpose**: Permanent decision record for Q1=A (hard split; no Credential Manager on Windows).

**Steps**:
1. Create `architecture/adrs/2026-04-14-1-windows-auth-platform-split.md`.
2. Follow the existing ADR format in `architecture/adrs/` (inspect a recent ADR for structure).
3. Minimum content:
   - **Title**, **Status** (Accepted), **Date**.
   - **Context**: #603 history, prior split/fallback logic, historical regressions.
   - **Decision**: Hard platform split. Windows uses encrypted file-backed store at `%LOCALAPPDATA%\spec-kitty\auth\`. `keychain.py` and `keyring` are not imported on the Windows runtime path; `keyring` is a non-Windows conditional dependency in `pyproject.toml`. No opt-in Credential Manager path.
   - **Consequences**: Packaging change (conditional marker); single Windows auth story; easier support; opt-in Credential Manager becomes a future feature if ever needed.
   - **References**: Spec FR-001, C-001; research R-04, R-11; WP03.

**Validation**:
- ADR file exists and follows the ADR template.

### T056 — Write ADR: windows-runtime-state-unification [P]

**Purpose**: Permanent decision record for Q3=C (unified `%LOCALAPPDATA%\spec-kitty\` root + one-direction destination-wins migration).

**Steps**:
1. Create `architecture/adrs/2026-04-14-2-windows-runtime-state-unification.md`.
2. Minimum content:
   - **Context**: Split roots (`~/.spec-kitty`, `~/.kittify`, `~/.config/spec-kitty`, `kernel.paths` `%LOCALAPPDATA%\kittify\`) were incoherent and confusing.
   - **Decision**: Single Windows root under `%LOCALAPPDATA%\spec-kitty\` for auth / tracker / sync / daemon / runtime cache. One-time, destination-wins, quarantine-on-conflict migration. POSIX layout unchanged. WSL treated as Linux.
   - **Consequences**: Migration complexity once; clean support story forever; no long-term dual-root steady state.
   - **References**: Spec FR-003..FR-008, C-002, C-005, C-006; research R-01..R-03; WP01, WP02, WP04, WP05.

**Validation**:
- ADR file exists.

### T057 — Write `docs/explanation/windows-state.md` [P]

**Purpose**: User-facing explainer of where Spec Kitty stores state on Windows.

**Steps**:
1. Create `docs/explanation/windows-state.md`.
2. Structure (Divio "explanation" type):
   ```markdown
   # Where Spec Kitty stores state on Windows

   Spec Kitty stores all per-user runtime state on Windows under a single root:

   ```
   %LOCALAPPDATA%\spec-kitty\
   ├── auth\         # encrypted credentials (file-backed)
   ├── tracker\      # tracker SQLite DB and related state
   ├── sync\         # sync queue and state
   ├── daemon\       # daemon PIDs and lock files
   └── cache\        # ephemeral runtime cache
   ```

   ## Why a single root?

   <explain coherence, support, migration benefits>

   ## Why not Windows Credential Manager?

   <explain #603 decision>

   ## First-run migration

   <explain legacy → canonical migration, destination-wins, quarantine>

   ## WSL

   WSL installs use the Linux storage layout (`~/.spec-kitty`) and are not
   affected by the Windows-specific layout.

   ## Encoding

   Spec Kitty forces UTF-8 on Windows stdout/stderr at startup. Set
   `PYTHONUTF8=1` in your environment as an extra safety measure.

   ## Troubleshooting

   <common issues + fixes>
   ```
3. Cross-link to the ADRs and the audit report.

**Validation**:
- File exists, renders cleanly in Markdown preview, cross-links resolve.

### T058 — Update `CLAUDE.md` with Windows state-layout section [P]

**Purpose**: Future contributors pick up the Windows story automatically (FR-019).

**Steps**:
1. Open `CLAUDE.md` at repo root.
2. Add a new section after "Merge & Preflight Patterns" (pick a stable anchor that isn't auto-generated):
   ```markdown
   ## Windows State Layout (0.12.0+)

   On Windows, Spec Kitty stores all per-user runtime state under a single root:

   - `%LOCALAPPDATA%\spec-kitty\` (via `platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)`)
   - Subdirectories: `auth/`, `tracker/`, `sync/`, `daemon/`, `cache/`

   Auth storage on Windows is the encrypted file-backed store. `keyring` is
   NOT a Windows dependency (see ADR `2026-04-14-1-windows-auth-platform-split.md`
   and #603).

   Migration from legacy locations (`~/.spec-kitty`, `~/.kittify`,
   `~/.config/spec-kitty`) happens once on first Windows run; see
   `src/specify_cli/paths/windows_migrate.py`.

   WSL is treated as Linux. Contributors working on Windows-specific code
   paths should add native CI coverage via `@pytest.mark.windows_ci` and
   the `ci-windows` workflow.

   See:
   - `docs/explanation/windows-state.md`
   - `architecture/2026-04-14-windows-compatibility-hardening.md`
   - `architecture/adrs/2026-04-14-1-windows-auth-platform-split.md`
   - `architecture/adrs/2026-04-14-2-windows-runtime-state-unification.md`
   ```
3. Do NOT remove or reorder any existing `CLAUDE.md` content.

**Validation**:
- Diff shows only addition; no unrelated changes.

### T059 — File GitHub follow-up issues for residuals [P]

**Purpose**: Every unresolved Windows risk from the audit has a durable ticket.

**Steps**:
1. For each Follow-up label from T053, file a GitHub issue against `Priivacy-ai/spec-kitty`:
   ```bash
   unset GITHUB_TOKEN && gh issue create \
     --repo Priivacy-ai/spec-kitty \
     --title "<concise title>" \
     --label windows \
     --body "<body including file:line reference, risk description, proposed scope, and link back to the audit report>"
   ```
2. Use `unset GITHUB_TOKEN` to ensure the keyring-authenticated token with full `repo` scope is used (per CLAUDE.md guidance).
3. Capture each new issue number and link it into the audit report's "Follow-up issues filed" section.
4. If there are zero follow-ups (ideal outcome), record that explicitly in the audit report: "No residual follow-ups identified."

**Validation**:
- Issue URLs in the audit report match the filed issues.

### T060 — Verify #603 closeable; verify #260 posture [P]

**Purpose**: Close out the open Windows-tagged issues that this mission was designed to address.

**Steps**:
1. For #603:
   - Verify by running `pip list` on a `windows-latest` runner (via WP07 CI) that `keyring` is absent.
   - Verify by reading the audit report that the "keyring on Windows" classification is zero hits.
   - Comment on #603 summarizing: hard split landed (ADR link), CI asserts keyring-absent (WP07), file-backed store is the Windows path (ADR link). Request closure.
   ```bash
   unset GITHUB_TOKEN && gh issue comment 603 \
     --repo Priivacy-ai/spec-kitty \
     --body "Closed by mission windows-compatibility-hardening. See <ADR URL> and <audit report URL>."
   ```
2. For #260:
   - Review the original report to determine what "worktree subdirectory incompatibility" meant in the original context.
   - Cross-check with WP08's worktree tests (`test_worktree_symlink_fallback.py`) — does the mission's coverage address the exact scenario reported?
   - If yes → comment on #260 requesting closure with test link.
   - If partially → file a follow-up issue (via T059) with the remaining scope, comment on #260 pointing at the follow-up.

**Validation**:
- #603 closeable comment posted.
- #260 has a concrete closure or follow-up posture, documented in the audit report under "Closeable GitHub issues."

## Definition of done

- [ ] All 9 subtasks complete.
- [ ] Audit report file committed and classification table exhaustive.
- [ ] Both ADR files committed.
- [ ] `docs/explanation/windows-state.md` committed.
- [ ] `CLAUDE.md` updated with Windows state layout section.
- [ ] All Follow-up issues filed with the `windows` label and linked from the audit report.
- [ ] #603 and #260 have closeable or scoped-follow-up comments.
- [ ] Commit message references FR-018, FR-019, SC-005, SC-006, SC-007.

## Risks

- **Grep produces a huge raw log**: Use a triage scratch file; classify in batches. Do not skip false positives — they need to be labeled "Safe" for the record.
- **GitHub permissions for issue filing / commenting**: If the executing agent doesn't have `repo` scope, issue operations will fail. Fall back to drafting the issue bodies in the audit report and requesting a maintainer to file them. Document any deferred filings.
- **#260 ambiguity**: The original report may describe a MCP-editor-specific tooling path. If the root cause is outside Spec Kitty (e.g., an editor-side symlink assumption), document that reality rather than force-closing.
- **CLAUDE.md merge conflicts**: `CLAUDE.md` is edited frequently on `main`. Land this WP on top of a fresh `main` to minimize conflict; resolve by appending to the new Windows section, not by rebasing across other section changes.

## Reviewer guidance

Focus on:
1. Does every raw grep hit appear in the classification table?
2. Are the ADRs self-contained and cross-linked?
3. Does `docs/explanation/windows-state.md` accurately describe what the code actually does?
4. Does the `CLAUDE.md` addition follow the existing section style (no emoji unless the existing sections use them)?
5. Does the `#603` comment include enough evidence (ADR + audit report + CI link) to justify closure?

Do NOT ask about:
- Individual WP internals — those are reviewed in their own PRs.
- Whether to add more CI — that's WP07 scope.
