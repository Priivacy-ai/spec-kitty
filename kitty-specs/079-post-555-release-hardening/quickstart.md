# Quickstart: 3.1.1 Post-555 Release Hardening (Operator Validation Walkthrough)

**Mission**: `079-post-555-release-hardening`
**Audience**: The release operator (`@robertdouglass`) and any reviewer who needs to verify, by hand, that mission 079 is releasable as `3.1.1`.
**Prerequisite**: The full mission has been implemented and `tests/` is green under `PWHEADLESS=1 pytest tests/`.
**Working repo**: `/private/tmp/311/spec-kitty` at the proposed `3.1.1` release commit.

This walkthrough is the dogfood-acceptance gate (S-7 / V-7 from `spec.md`). Run it end-to-end before tagging `v3.1.1`.

---

## 0. Preflight (one-time setup)

```bash
# Confirm you are on the proposed release commit
cd /private/tmp/311/spec-kitty
git status
git log -1 --oneline

# Confirm the test suite is green
PWHEADLESS=1 pytest tests/ -q

# Confirm mypy is clean
mypy --strict src/specify_cli/

# Install a fresh build of the CLI from the working tree
pipx install --force --pip-args="--pre" /private/tmp/311/spec-kitty
spec-kitty --version
```

**Expected**: `spec-kitty --version` reports `3.1.1` (NOT `3.1.1aN`). If it reports an alpha suffix, the release-cut version bump WP has not been completed and you cannot proceed.

---

## 1. Track 1 — `init` coherence

```bash
# Pick a fresh empty directory
TS=$(date +%s)
TMPDIR_INIT=/tmp/spec-kitty-init-verify-$TS
mkdir -p $TMPDIR_INIT
cd $TMPDIR_INIT

# Run the new init
spec-kitty init demo --ai codex --non-interactive
```

**Expected output**:
- A "Next steps" panel that names `spec-kitty next --agent <agent> --mission <slug>` as the canonical loop entry.
- The panel names `spec-kitty agent action implement` / `spec-kitty agent action review` as the per-decision verbs the agent invokes.
- Slash-command names like `/spec-kitty.specify`, `/spec-kitty.plan`, `/spec-kitty.implement` MAY appear as references to the agent-runtime slash commands (this is fine — they are slash commands, not CLI invocations).
- The text MUST NOT contain a line that teaches top-level `spec-kitty implement WP##` as a user-facing CLI invocation.
- The text MUST NOT contain `Initial commit from Specify template`.

```bash
# Assert no .git/ was created
test -d demo/.git && echo "FAIL: .git/ exists" || echo "PASS: no .git/"

# Assert no .agents/skills/ was created
test -d demo/.agents/skills && echo "FAIL: .agents/skills/ exists" || echo "PASS: no .agents/skills/"

# Assert no commit was made (cd into demo/ if init created a subdir)
cd demo
if git log >/dev/null 2>&1; then
  echo "FAIL: git log succeeded — there is a git history"
else
  echo "PASS: no git history"
fi

# Assert .kittify/config.yaml exists
test -f .kittify/config.yaml && echo "PASS: .kittify/config.yaml" || echo "FAIL: missing config"

# Assert .codex/prompts/ has the slash-command files
ls .codex/prompts/spec-kitty.*.md && echo "PASS: per-agent slash commands" || echo "FAIL: missing slash commands"

# Cleanup
cd /tmp
rm -rf $TMPDIR_INIT
```

**Expected**: All assertions PASS.

### Edge case 1.A: re-running init in an already-initialized directory

```bash
TMPDIR_INIT=/tmp/spec-kitty-init-idempotent-$(date +%s)
mkdir -p $TMPDIR_INIT
cd $TMPDIR_INIT

spec-kitty init demo --ai codex --non-interactive
spec-kitty init demo --ai codex --non-interactive   # second run
echo "Second-run exit code: $?"
```

**Expected**: Either exit 0 with idempotent behavior OR a clear error message naming the conflict (no silent merge or overwrite).

### Edge case 1.B: init inside an existing git repo

```bash
TMPDIR_INIT=/tmp/spec-kitty-init-existing-repo-$(date +%s)
mkdir -p $TMPDIR_INIT
cd $TMPDIR_INIT
git init
echo "test" > README.md
git add README.md
git commit -m "user's own commit"
HEAD_BEFORE=$(git rev-parse HEAD)

spec-kitty init . --ai codex --non-interactive

HEAD_AFTER=$(git rev-parse HEAD)
[ "$HEAD_BEFORE" = "$HEAD_AFTER" ] && echo "PASS: HEAD unchanged" || echo "FAIL: HEAD changed"
```

**Expected**: `HEAD unchanged` PASS. The user's own commit is preserved.

---

## 2. Track 4 — Tasks/finalize hotfix

The fastest way to verify the parser bound is via a unit test, but the dogfood walkthrough exercises it via the full pipeline.

```bash
cd /private/tmp/311/spec-kitty

# Create a fresh test mission
spec-kitty agent mission create dogfood-track4 --json
```

Locate the new feature dir (the JSON output names it). Open `tasks.md` and author a final WP with explicit empty `dependencies:` followed by trailing prose containing `Depends on WP01`. (Or use a fixture file from `tests/fixtures/` if one exists.)

```bash
spec-kitty agent mission finalize-tasks --mission dogfood-track4
spec-kitty agent tasks status --mission dogfood-track4
```

**Expected**: The status panel shows the final WP with the empty `dependencies` it was authored with (NOT auto-injected from the trailing prose).

Cleanup:
```bash
rm -rf kitty-specs/0XX-dogfood-track4   # use the actual numbered slug
```

---

## 3. Track 2 — Planning-artifact producer correctness

Construct a mission whose plan generates a planning-artifact WP. The fastest path is to reuse an existing fixture under `tests/fixtures/` if one provides this shape.

```bash
cd /private/tmp/311/spec-kitty
spec-kitty agent mission create dogfood-track2 --json
```

Author a `tasks.md` with at least one code WP and at least one planning-artifact WP (the `execution_mode: planning_artifact` is determined by the WP's `owned_files` patterns — files under `kitty-specs/<slug>/` typically infer to `planning_artifact`).

```bash
spec-kitty agent mission finalize-tasks --mission dogfood-track2

# Inspect the lanes.json
cat kitty-specs/0XX-dogfood-track2/lanes.json | python -m json.tool
```

**Expected**:
- The `lanes` list contains an entry with `"lane_id": "lane-planning"`.
- The planning-artifact WP appears in that lane's `wp_ids`.
- Code WPs appear in `lane-a` / `lane-b` / etc.

```bash
# Run the canonical per-decision verb against the planning-artifact WP.
# Use the agent-facing wrapper, NOT top-level `spec-kitty implement` directly —
# the wrapper is the canonical user-facing surface per D-4.
spec-kitty agent action implement WP02 --mission dogfood-track2 --agent claude  # use the actual planning-artifact WP id
```

**Expected**:
- The command exits 0.
- It reports a workspace path equal to `/private/tmp/311/spec-kitty` (the main repo checkout), NOT a `.worktrees/dogfood-track2-lane-planning` directory.
- No `.worktrees/dogfood-track2-lane-planning/` exists on disk.

Optional compatibility check (to confirm the legacy command path still works):
```bash
spec-kitty implement WP02 --mission dogfood-track2  # legacy path; should still resolve identically
```
**Expected**: same outcome (exit 0, main repo checkout, no worktree). This validates FR-505.

Cleanup:
```bash
rm -rf kitty-specs/0XX-dogfood-track2
```

---

## 4. Track 3 — Mission identity Phase 1

```bash
cd /private/tmp/311/spec-kitty
spec-kitty agent mission create dogfood-track3 --json
```

Read the `mission_id` from the JSON output OR from `meta.json`:

```bash
cat kitty-specs/0XX-dogfood-track3/meta.json | python -c "import sys, json; print(json.load(sys.stdin).get('mission_id', '<MISSING>'))"
```

**Expected**: A non-empty string that parses as a valid ULID (26-character Crockford base32). Example: `01HXYZ0123456789ABCDEFGHJK`.

```bash
# Verify mission 079 (this mission) has its own mission_id (Track 3 dogfood)
cat kitty-specs/079-post-555-release-hardening/meta.json | python -c "import sys, json; print(json.load(sys.stdin).get('mission_id', '<MISSING>'))"
```

**Expected**: A non-empty ULID string. (Mission 079 dogfoods the new identity model — the first WP of Track 3 added it.)

### Edge case 3.A: concurrent creation does not collide

This is best validated via the unit test `tests/core/test_mission_creation_concurrent.py`. Run that test:
```bash
PWHEADLESS=1 pytest tests/core/test_mission_creation_concurrent.py -v
```

**Expected**: The test passes.

Cleanup:
```bash
rm -rf kitty-specs/0XX-dogfood-track3
```

---

## 5. Track 5 — Auth refresh race fix

This is best validated via the unit test, since reproducing the race by hand is tedious.

```bash
cd /private/tmp/311/spec-kitty
PWHEADLESS=1 pytest tests/sync/test_auth_concurrent_refresh.py -v
```

**Expected**: All tests pass deterministically. None of them flake.

If you want a manual sanity check, you can also run:
```bash
spec-kitty agent auth status
```
and confirm the command does not unexpectedly clear your real credentials. (But the unit test is the canonical proof.)

---

## 6. Track 6 — Top-level `implement` de-emphasis

```bash
spec-kitty implement --help
```

**Expected**: The help text marks the command as **internal infrastructure** (or "implementation detail of `spec-kitty agent action implement`"). The help text directs callers to `spec-kitty next` (the loop entry) and `spec-kitty agent action implement` (the per-WP verb).

```bash
# Confirm the canonical commands exist and respond to --help
spec-kitty next --help
spec-kitty agent action implement --help
spec-kitty agent action review --help
```

**Expected**: All three commands print their `--help` text successfully (exit 0). These are the canonical post-#555 user-facing commands.

```bash
# Confirm README.md does not name top-level implement in canonical workflow
grep -n '`implement`' /private/tmp/311/spec-kitty/README.md
grep -n 'spec-kitty implement' /private/tmp/311/spec-kitty/README.md
```

**Expected**: Neither grep returns a line in the canonical workflow section at the top of the README. Any remaining occurrences must be in compatibility-surface or troubleshooting context, not canonical-path context. The canonical workflow section MUST name `spec-kitty next` and `spec-kitty agent action implement/review`.

```bash
# Confirm the compatibility surface still runs (FR-505)
spec-kitty implement --help
echo "Exit code: $?"
```

**Expected**: Exit code 0. The command remains runnable for direct invokers.

### Bonus: re-run init and confirm the next-steps text

```bash
TMPDIR=/tmp/spec-kitty-init-impl-check-$(date +%s)
mkdir -p $TMPDIR && cd $TMPDIR
spec-kitty init demo --ai codex --non-interactive 2>&1 | tee init-out.txt

# The init output MUST name the canonical commands
grep -E "spec-kitty next|spec-kitty agent action implement|spec-kitty agent action review" init-out.txt
echo "---"

# The init output MUST NOT teach top-level `spec-kitty implement WP##` as canonical
grep -E "spec-kitty implement WP" init-out.txt
```

**Expected**:
- The first grep finds at least one line per canonical command.
- The second grep returns NO matches (the literal string `spec-kitty implement WP` does not appear in init's output).

Cleanup:
```bash
cd /tmp && rm -rf $TMPDIR
```

---

## 7. Track 7 — Repo dogfood / version coherence

```bash
cd /private/tmp/311/spec-kitty

# 7.1 — Version coherence between pyproject.toml and .kittify/metadata.yaml
PYPROJECT_VERSION=$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
METADATA_VERSION=$(python -c "import yaml; print(yaml.safe_load(open('.kittify/metadata.yaml'))['spec_kitty']['version'])")
echo "pyproject.toml: $PYPROJECT_VERSION"
echo ".kittify/metadata.yaml: $METADATA_VERSION"
[ "$PYPROJECT_VERSION" = "$METADATA_VERSION" ] && echo "PASS: versions match" || echo "FAIL: versions disagree"
[ "$PYPROJECT_VERSION" = "3.1.1" ] && echo "PASS: at 3.1.1" || echo "FAIL: not yet at 3.1.1"
```

**Expected**: Both PASS at the release commit.

```bash
# 7.2 — Run the validate_release.py script
python scripts/release/validate_release.py
echo "Exit code: $?"
```

**Expected**: Exit code 0. The script reports success on all gates: pyproject ↔ metadata.yaml sync, CHANGELOG.md entry presence, version progression.

```bash
# 7.3 — Deliberately introduce a mismatch in a scratch checkout and confirm validate_release fails
SCRATCH=/tmp/spec-kitty-scratch-$(date +%s)
git clone /private/tmp/311/spec-kitty $SCRATCH
cd $SCRATCH
sed -i.bak 's/version = "3.1.1"/version = "3.1.2"/' pyproject.toml
python scripts/release/validate_release.py
echo "Exit code: $?"
```

**Expected**: Exit code != 0. The error message names both `pyproject.toml` and `.kittify/metadata.yaml` and shows both version values.

```bash
# Cleanup
cd /tmp && rm -rf $SCRATCH
```

```bash
# 7.4 — Run the structured release-prep draft generator
cd /private/tmp/311/spec-kitty
spec-kitty agent release prep --channel stable --json | python -m json.tool
```

**Expected**: A JSON payload that includes a `proposed_changelog_block` field whose value is a non-empty markdown block whose header references `3.1.1`.

```bash
# 7.5 — Run the dogfood command set
spec-kitty --version
spec-kitty agent mission create dogfood-track7 --json
spec-kitty agent mission finalize-tasks --mission dogfood-track7
spec-kitty agent tasks status --mission dogfood-track7
```

**Expected**: Each command exits 0. None of them produce a version-skew error.

Cleanup:
```bash
rm -rf /private/tmp/311/spec-kitty/kitty-specs/0XX-dogfood-track7
```

```bash
# 7.6 — Test against a fresh clone (cold-cache dogfood)
COLD=/tmp/spec-kitty-cold-clone-$(date +%s)
git clone /private/tmp/311/spec-kitty $COLD
cd $COLD
pipx install --force --pip-args="--pre" .
spec-kitty --version
spec-kitty init demo --ai codex --non-interactive
cd /tmp && rm -rf $COLD
```

**Expected**: Every command in the cold-clone exits 0 with no version-skew error.

---

## 8. Scope audit (RG-8)

```bash
cd /private/tmp/311/spec-kitty
# Confirm mission 079 is the only kitty-specs/ directory modified by this mission
git log --oneline --name-only $(git merge-base main HEAD)..HEAD -- kitty-specs/ | grep -v "^[a-f0-9]" | sort -u
```

**Expected**: All listed paths are under `kitty-specs/079-post-555-release-hardening/` (no other historical missions touched).

```bash
# Confirm no #401 / SaaS contract surface area was added
git diff $(git merge-base main HEAD)..HEAD -- src/specify_cli/sync/ | grep -i "saas\|dashboard" | head
```

**Expected**: Empty (no new SaaS/dashboard surface area).

```bash
# Confirm no #538/#540/#542 stabilization (top-level implement code surface unchanged)
git diff $(git merge-base main HEAD)..HEAD -- src/specify_cli/cli/commands/implement.py
```

**Expected**: Diff shows only docstring / help-text changes, no behavior changes.

---

## 9. Release gate summary

| Gate | Verified by | Status |
|------|-------------|--------|
| RG-1 (init coherent) | §1 | [ ] |
| RG-2 (tasks finalize hotfix) | §2 | [ ] |
| RG-3 (planning-artifact canonical) | §3 | [ ] |
| RG-4 (mission identity safe) | §4 | [ ] |
| RG-5 (auth refresh fixed) | §5 | [ ] |
| RG-6 (implement de-emphasized) | §6 | [ ] |
| RG-7 (repo dogfoods cleanly) | §7 | [ ] |
| RG-8 (no scope leak) | §8 | [ ] |

When all eight boxes are checked, mission 079 is **releasable as 3.1.1**. The actual `git tag v3.1.1` and PyPI publish remain human actions, per the project `CLAUDE.md`.

---

## 10. Reset / cleanup after the walkthrough

```bash
# Remove any dogfood missions that survived
cd /private/tmp/311/spec-kitty
ls kitty-specs/ | grep dogfood- | xargs -I{} rm -rf kitty-specs/{}

# Confirm the working tree is clean
git status
```

**Expected**: Working tree clean. Mission 079's own files (in `kitty-specs/079-post-555-release-hardening/`) are committed; nothing else is touched.
