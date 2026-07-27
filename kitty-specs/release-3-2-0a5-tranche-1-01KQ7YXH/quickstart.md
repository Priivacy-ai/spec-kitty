# Quickstart: 3.2.0a5 Tranche 1 Verification

End-to-end validation flow for the tranche. Run from the repository root
checkout (`/Users/robert/spec-kitty-dev/spec-kitty-20260427-190321-KGr7VE/spec-kitty`).

Each section maps to one or more contracts in [`contracts/`](./contracts/).

## Prerequisites

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260427-190321-KGr7VE/spec-kitty
git status --short              # should be clean (or only this mission's artifacts)
git branch --show-current       # release/3.2.0a5-tranche-1
uv run --version
uv run python -V                # 3.11+
uv run spec-kitty --version     # 3.2.0a5 after WP02
```

## 1. FR-002 — Upgrade post-state coherence

Contract: [`upgrade_post_state.contract.md`](./contracts/upgrade_post_state.contract.md)

```bash
# Set up a fresh tmp project, then:
spec-kitty upgrade --yes                                            # exits 0
yq '.spec_kitty.schema_version' .kittify/metadata.yaml              # prints 3
spec-kitty agent mission branch-context --json | jq -e '.result == "success"'
# No PROJECT_MIGRATION_NEEDED block.
```

## 2. FR-001 — `.python-version` and strict mypy

```bash
cat .python-version                                                 # 3.11
grep '^requires-python' pyproject.toml                              # >=3.11
uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py
# Exit 0, "Success: no issues found in 1 source file"
```

## 3. NFR-002 — Release metadata coherence

```bash
grep '^version' pyproject.toml                                      # 3.2.0a5
head -20 CHANGELOG.md | grep -E '^\#\# \[3\.2\.0a5\]'               # one match
head -20 CHANGELOG.md | grep -E '^\#\# \[Unreleased\]'              # one match (above 3.2.0a5)
PWHEADLESS=1 uv run --extra test python -m pytest tests/release/ -q
# All green
```

## 4. FR-003 — `/spec-kitty.checklist` removed from agent surface

Contract: [`checklist_surface_removed.contract.md`](./contracts/checklist_surface_removed.contract.md)

```bash
# Should print 0 for every line:
grep -rln "spec-kitty\.checklist" src/specify_cli/missions/ 2>/dev/null | wc -l
grep -rln "spec-kitty\.checklist" tests/specify_cli/regression/_twelve_agent_baseline/ 2>/dev/null | wc -l
grep -rln "spec-kitty\.checklist" tests/specify_cli/skills/__snapshots__/ 2>/dev/null | wc -l
grep -rln "/spec-kitty\.checklist" docs/ README.md 2>/dev/null | wc -l

# But the canonical requirements artifact still gets created:
PWHEADLESS=1 uv run --extra test python -m pytest \
  tests/specify_cli/skills/test_registry.py \
  tests/specify_cli/skills/test_command_renderer.py \
  tests/specify_cli/skills/test_installer.py \
  tests/missions/test_command_templates_canonical_path.py -q
```

## 5. FR-005 — `init` non-git message

Contract: [`init_non_git_message.contract.md`](./contracts/init_non_git_message.contract.md)

```bash
TMP=$(mktemp -d)
cd "$TMP"
spec-kitty init my-project 2>&1 | tee /tmp/init-out.txt
# Expect exactly one line containing both "not a git repository" and "git init"
grep -c "git init" /tmp/init-out.txt        # 1
test ! -d my-project/.git                   # init did NOT auto-init git
ls my-project/.kittify/                     # populated as expected
cd - >/dev/null
rm -rf "$TMP"
```

## 6. FR-006 — `--feature` hidden from help

Contract: [`feature_alias_hidden.contract.md`](./contracts/feature_alias_hidden.contract.md)

```bash
# Spot-check several CLI subcommand --help outputs:
spec-kitty --help               | grep -c -- "--feature"            # 0
spec-kitty agent --help         | grep -c -- "--feature"            # 0
spec-kitty agent mission --help | grep -c -- "--feature"            # 0
spec-kitty implement --help     | grep -c -- "--feature"            # 0
spec-kitty merge --help         | grep -c -- "--feature"            # 0

# But existing call sites still work (regression test exercises this):
PWHEADLESS=1 uv run --extra test python -m pytest \
  tests/specify_cli/cli/test_no_visible_feature_alias.py -q
```

## 7. FR-007 — Decision command shape consistency

Contract: [`decision_command_help.contract.md`](./contracts/decision_command_help.contract.md)

```bash
spec-kitty agent decision --help | head -20
# Subcommands: open / resolve / defer / cancel / verify

# Doc / help / snapshot consistency:
PWHEADLESS=1 uv run --extra test python -m pytest \
  tests/specify_cli/cli/test_decision_command_shape_consistency.py -q
```

## 8. FR-008 + FR-009 — Mission-create clean output and dedup

Contract: [`mission_create_clean_output.contract.md`](./contracts/mission_create_clean_output.contract.md)

```bash
# Drive a sample create against a tmp project:
TMP=$(mktemp -d)
cd "$TMP"
spec-kitty init demo
cd demo
spec-kitty agent mission create "demo-feature" \
  --friendly-name "Demo Feature" \
  --purpose-tldr "demo" \
  --purpose-context "demo context paragraph for verification only" \
  --json > /tmp/create.out 2> /tmp/create.err

# Assertions:
tail -1 /tmp/create.out | grep -q '^}$'                             # JSON closes cleanly
grep -c "Not authenticated, skipping sync" /tmp/create.out /tmp/create.err  # ≤ 1
grep -ci "error" /tmp/create.err                                    # 0 red error lines
cd /; rm -rf "$TMP"

# Plus the new e2e test:
PWHEADLESS=1 uv run --extra test python -m pytest \
  tests/e2e/test_mission_create_clean_output.py \
  tests/sync/test_diagnostic_dedup.py -q
```

## 9. Aggregate verification

```bash
PWHEADLESS=1 uv run --extra test python -m pytest \
  tests/release \
  tests/specify_cli/skills \
  tests/specify_cli/cli \
  tests/specify_cli/upgrade \
  tests/sync \
  tests/auth \
  tests/missions \
  tests/e2e \
  -q

uv run --extra lint mypy --strict src/specify_cli/mission_step_contracts/executor.py
uv run --extra lint ruff check .python-version pyproject.toml src/specify_cli tests
```

All green = tranche meets `start-here.md` "Done Criteria".
