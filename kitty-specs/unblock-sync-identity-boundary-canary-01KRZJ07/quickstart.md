# Quickstart: Verifying the mission locally

**Mission**: `unblock-sync-identity-boundary-canary-01KRZJ07`
**Audience**: implementer or reviewer who wants to confirm the fixes work end-to-end.

## Prereqs

- Python 3.11+
- A local clone of `Priivacy-ai/spec-kitty` (this repo, at the mission's WP branch or merged into `main`).
- A local clone of `Priivacy-ai/spec-kitty-end-to-end-testing` (sibling, only required for WP04 / canary acceptance).
- `uv` or `pip` for installing the rc bump.

## Step 1 — Per-bug regression coverage (WP01–WP03)

From the repo root:

```bash
pytest tests/specify_cli/audit/test_detectors_row_family.py \
       tests/specify_cli/cli/commands/test_doctor_restart_daemon.py \
       tests/specify_cli/cli/commands/test_sync_status_check_paths.py \
       tests/specify_cli/sync/test_preflight_remediation_hints.py -v
```

All four files must pass; each contains the specific reproduction documented in its issue body (rc13 fails, post-fix passes).

## Step 2 — Cross-check the live CLI (smoke)

```bash
# Fresh project, no TeamSpace blocker on lifecycle rows
mkdir -p /tmp/sk-smoke/{home,repo} && cd /tmp/sk-smoke/repo
git init -q && git config user.email r@e && git config user.name r
SPEC_KITTY_HOME=/tmp/sk-smoke/home HOME=/tmp/sk-smoke/home \
  spec-kitty init --non-interactive --ai claude >/dev/null
git add -A && git commit -qm init
SPEC_KITTY_HOME=/tmp/sk-smoke/home HOME=/tmp/sk-smoke/home \
  spec-kitty agent mission create repro --mission-type software-dev --json >/dev/null
SPEC_KITTY_HOME=/tmp/sk-smoke/home HOME=/tmp/sk-smoke/home \
  spec-kitty doctor mission-state --audit --json \
  | python3 -c "import sys,json;print(sum(1 for m in json.load(sys.stdin).get('missions', []) for f in m['findings'] if f['code']=='FORBIDDEN_KEY'))"
# Expect: 0
```

```bash
# Path-rendering smoke: no ellipsis in piped capture
SPEC_KITTY_HOME=/tmp/sk-smoke/home HOME=/tmp/sk-smoke/home \
  spec-kitty sync status --check 2>/dev/null | grep -F '…' && echo "FAIL: ellipsis present" || echo "OK"
```

```bash
# doctor restart-daemon exists
spec-kitty doctor restart-daemon --help
# Expect: shows help text, no "No such command"
```

## Step 3 — Canary acceptance (WP04)

Operate in a sibling directory to this repo. (Adjust paths as needed for your setup.)

```bash
# 1. Clone or refresh the canary repo
cd ..
git clone https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git || (cd spec-kitty-end-to-end-testing && git pull)
cd spec-kitty-end-to-end-testing

# 2. Use a venv that has the rc bump (rc14 or newer) of spec-kitty-cli installed
python3 -m venv .venv && source .venv/bin/activate
pip install -e . spec-kitty-cli==<rc-bump-version>

# 3. Run the identity-boundary canary
pytest tests/identity_boundary/ -v --capture=no
```

Expected outcome:
- Scenarios 1, 2, and 4 — **PASS**.
- Scenario 3 — may still FAIL until `#43` lands in this canary repo. That is acceptable per mission constraint C-002.

## Step 4 — Capture evidence

Copy canary artifacts into this repo for archival:

```bash
cp -r artifacts/sync_identity_boundary/<rc-bump>/{latest,run-1}.json \
   /path/to/spec-kitty/kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/
```

Commit the evidence as part of the WP04 PR.

## Done criterion

The mission is accepted when:
1. All four regression test files pass.
2. The smoke checks in Step 2 succeed.
3. Canary scenarios 1, 2, and 4 are green; evidence under `canary-evidence/` shows the green run.
