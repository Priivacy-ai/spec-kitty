---
work_package_id: WP02
title: RC Install and Boundary Verification
dependencies:
- WP01
requirement_refs:
- C-001
- C-005
- FR-003
- FR-004
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "62266"
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP02-rc-install.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer
```

Read the entire prompt before acting.

---

## Objective

Install the latest post-rc15 `spec-kitty-cli` prerelease and verify that the auth-boundary modules (`specify_cli.sync.owner` and `specify_cli.sync.preflight`) import cleanly from the installed environment.

**Hard gate**: If the latest published prerelease is still `v3.2.0rc15`, STOP and report. Do not cut an RC autonomously — that requires explicit operator instruction per CLAUDE.md.

**Constraint C-005**: The installed CLI must trace to a commit at or after `cc5e1ca983adff4a45489ce7afe11ad3a3a26e30`.

---

## Context

Working directory: `/Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS`

Environment invariant: all CLI commands that touch hosted auth/SaaS must be run with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.

CLI install paths:
- Binary: `/Users/robert/.local/bin/spec-kitty`
- Python env: `/Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python`

---

## Subtask T007: Determine Latest Prerelease RC Tag

**Purpose**: Find the highest published prerelease tag from GitHub releases and PyPI.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty

# Check GitHub releases
LATEST_RC=$(gh release list --repo Priivacy-ai/spec-kitty --limit 10 \
  --json tagName,isPrerelease \
  --jq '.[] | select(.isPrerelease) | .tagName' | head -1)
echo "Latest prerelease tag on GitHub: $LATEST_RC"

# Cross-check PyPI
python3 -m pip index versions spec-kitty-cli 2>/dev/null | head -5 || true

# Also check git tags
git fetch --tags origin
git tag --sort=-creatordate | grep rc | head -5
```

Record the exact tag string (e.g., `v3.2.0rc16`).

---

## Subtask T008: Gate — Stop if Latest Is Still rc15

**Purpose**: Only proceed if a post-rc15 RC exists.

```python
if LATEST_RC == "v3.2.0rc15":
    print("""
GATE BLOCKED: Latest published prerelease is still v3.2.0rc15.
Both #1141 and #1182 are closed per WP01, but no new RC has been cut yet.
Options:
  (a) Wait for the release author to cut rc16 and re-run WP02.
  (b) Ask the operator explicitly: "Should I cut rc16 from the fix SHA?"
      Only cut if operator confirms. Follow CLAUDE.md release workflow.
Do not proceed to T009 until a post-rc15 RC is available.
""")
    exit(1)
```

If a post-rc15 RC exists (e.g., `v3.2.0rc16`): strip the `v` prefix for pip install: `RC_VERSION="3.2.0rc16"`.

**If operator instructs to cut rc16**, follow this workflow (ONLY with explicit instruction):
```bash
# In spec-kitty repo:
# 1. Bump version in pyproject.toml: version = "3.2.0rc16"
# 2. Add CHANGELOG.md entry
# 3. Check .kittify/metadata.yaml for version field and update if present
# 4. Commit: git commit -am "chore: bump to 3.2.0rc16"
# 5. Tag: git tag -a v3.2.0rc16 -m "Release v3.2.0rc16 - Fix #1141 + #1182"
# 6. Push: git push origin main && git push origin v3.2.0rc16
# 7. Monitor: gh run list --workflow=release.yml --repo Priivacy-ai/spec-kitty --limit 3
# 8. Verify release: gh release view v3.2.0rc16 --repo Priivacy-ai/spec-kitty
```

---

## Subtask T009: Kill Orphan Sync Daemons

**Purpose**: Prevent stale daemon state from contaminating the new RC install.

```bash
pkill -9 -f run_sync_daemon 2>/dev/null || true
sleep 2
# Verify no daemon processes remain
ps aux | grep run_sync_daemon | grep -v grep || echo "No daemon processes found"
```

---

## Subtask T010: Install Post-rc15 RC via pipx

**Purpose**: Install the new RC from PyPI into the pipx-managed environment.

```bash
pipx install --force "spec-kitty-cli==${RC_VERSION}" \
  --pip-args="--pre" \
  --python python3

# Verify the pipx venv exists at the expected path
ls -la /Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python
ls -la /Users/robert/.local/bin/spec-kitty
```

**Expected**: Both paths exist after install.

---

## Subtask T011: Verify Installed Version

**Purpose**: Confirm the installed binary reports the expected version.

```bash
/Users/robert/.local/bin/spec-kitty --version
```

**Expected**: Output contains `v${RC_VERSION}` (e.g., `v3.2.0rc16`).

Also confirm the SHA lineage:
```bash
# The installed package's dist-info should reference the build SHA
# Cross-check: the tag v3.2.0rc16 should point to a commit AFTER cc5e1ca9
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty
git log --oneline cc5e1ca9..$(git rev-parse v3.2.0rc16^{commit}) 2>/dev/null | head -10 || \
  echo "Confirm tag SHA is at or after cc5e1ca983adff4a45489ce7afe11ad3a3a26e30"
```

---

## Subtask T012: Verify Auth-Boundary Imports

**Purpose**: Confirm the auth-boundary modules are present and importable, and that `sync status --check` exposes the identity-boundary fields the canary harness parses.

```bash
SPEC_KITTY_PY=/Users/robert/.local/pipx/venvs/spec-kitty-cli/bin/python

"$SPEC_KITTY_PY" -c "
import specify_cli.sync.owner
import specify_cli.sync.preflight
print('boundary imports ok')
"

# Also run the live sync-status check
SPEC_KITTY_BIN=/Users/robert/.local/bin/spec-kitty
SPEC_KITTY_ENABLE_SAAS_SYNC=1 "$SPEC_KITTY_BIN" sync status --check --json | python3 -m json.tool
SPEC_KITTY_ENABLE_SAAS_SYNC=1 "$SPEC_KITTY_BIN" sync status --check
```

**Expected**:
- `"boundary imports ok"` printed
- `sync status --check --json` output contains the following keys (used by the canary harness):
  - `owner_match` (bool): daemon record matches current auth identity
  - `auth_status` (string): `"authenticated"` or similar
  - `queue_count` (int): number of queued events in offline queue
  - `daemon_pid` (int or null): PID of running sync daemon, if any
  - Any additional identity-boundary rows added by #1115 (e.g., `identity_mismatch_detected`, `stale_owner_count`)
- If any of these keys are absent, the canary harness will likely fail to parse the output — report which keys are missing.

---

## Definition of Done

- [ ] T007: Latest prerelease RC tag identified and recorded
- [ ] T008: Gate passed (latest tag is NOT rc15)
- [ ] T009: No orphan sync daemon processes running
- [ ] T010: `spec-kitty-cli==${RC_VERSION}` installed via pipx
- [ ] T011: `spec-kitty --version` reports expected RC version
- [ ] T012: `specify_cli.sync.owner` and `specify_cli.sync.preflight` import cleanly; `sync status --check --json` succeeds

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Latest RC is still rc15 | Gate in T008; stop and report |
| pipx path mismatch (rc13 regression) | Verify both binary and Python env paths explicitly |
| `sync status --check` fails | Check if `SPEC_KITTY_ENABLE_SAAS_SYNC=1` is set |
| RC SHA is before cc5e1ca9 | Verify with git lineage check |

---

## Reviewer Guidance

- Confirm T008 gate ran before T009-T012
- Verify the installed version string matches the expected RC
- The `sync status --check --json` output must show identity-boundary fields

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP02 --agent claude` to start this WP.

## Activity Log

- 2026-05-20T05:21:02Z – claude:sonnet-4-6:implementer:implementer – shell_pid=61730 – Started implementation via action command
- 2026-05-20T05:21:44Z – claude:sonnet-4-6:implementer:implementer – shell_pid=61730 – Gate BLOCKED: latest RC is v3.2.0rc15 (no new RC). T007-T008 done. T009-T012 deferred pending rc16.
- 2026-05-20T05:21:51Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=62266 – Started review via action command
- 2026-05-20T05:22:24Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=62266 – Review passed: T007 live gh call confirmed rc15=latest, T008 gate correctly blocked. Deferred subtasks documented.
