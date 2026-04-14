# Quickstart: Unified Charter Bundle and Read Chokepoint

**Mission**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Companion**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [contracts/](contracts/)

Operational quickstart for contributors who need to implement, review, or verify a WP in this mission. Assumes you have the repo checked out at `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty` (or the equivalent on your machine).

---

## Prerequisites

- Python 3.11+ on PATH (`python --version`).
- `git` on PATH with `--git-common-dir` support (git ≥2.5). Verify: `git rev-parse --git-common-dir` inside the repo returns `.git` or an absolute path.
- `pipx install --force --pip-args="--pre" spec-kitty-cli` — the CLI is installed globally via pipx (per user's machine note).
- `pytest` and `mypy` available via the project's dev install (`pip install -e ".[dev]"` or equivalent).

---

## Orientation: where things live

| Purpose | Path |
| --- | --- |
| Spec | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/spec.md` |
| Plan | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/plan.md` |
| Research | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/research.md` |
| Data model | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/data-model.md` |
| Contracts | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/` |
| Occurrence artifacts (per WP) | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml` |
| Mission-level occurrence index | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml` |
| Dashboard baseline | `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json` |
| Canonical package | `src/charter/` |
| Duplicate (lockstep) package | `src/specify_cli/charter/` |
| Migrations | `src/specify_cli/upgrade/migrations/` |
| Verifier script | `scripts/verify_occurrences.py` (reused from Phase 1) |

---

## How to pick a WP

```bash
# Check mission status and which WPs are ready
spec-kitty agent tasks status --feature unified-charter-bundle-chokepoint-01KP5Q2G
```

WPs are strictly sequential (C-007). The ready WP is always the lowest-numbered WP that is not yet merged and whose predecessors are all merged.

---

## Implementing a WP (standard loop)

1. **Read the WP section in `plan.md`**. Every WP has a "Scope" list and an "Acceptance gates" list that together are the full bar to pass.
2. **Read the relevant contract file(s) under `contracts/`** for any new typed surface (manifest, resolver, chokepoint, migration report, CLI).
3. **Author the occurrence artifact first** at `kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml` — this doubles as your design doc for the WP. Schema at `contracts/occurrence-artifact.schema.yaml`.
4. **Implement source changes** following the WP scope list.
5. **Add/update tests** per the WP's test list.
6. **Run the WP gates locally** before pushing (see "Running the gates locally" below).
7. **Open PR against `main`**. PR body should link the WP tracking issue (see plan.md header).

---

## Running the gates locally

### Core test suite

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty
PWHEADLESS=1 pytest tests/
```

Scope to the new tests a WP introduces:

```bash
# WP2.1
PWHEADLESS=1 pytest tests/charter/test_bundle_manifest_model.py

# WP2.2
PWHEADLESS=1 pytest tests/charter/test_canonical_root_resolution.py \
                    tests/charter/test_chokepoint_overhead.py \
                    tests/charter/test_resolution_overhead.py

# WP2.3
PWHEADLESS=1 pytest tests/charter/test_chokepoint_coverage.py \
                    tests/charter/test_bundle_contract.py \
                    tests/init/test_fresh_clone_no_sync.py \
                    tests/core/test_worktree_no_charter_materialization.py \
                    tests/test_dashboard/test_charter_chokepoint_regression.py

# WP2.4
PWHEADLESS=1 pytest tests/upgrade/test_unified_bundle_migration.py
```

### Type check

```bash
mypy --strict src/charter/ src/specify_cli/core/worktree.py \
              src/specify_cli/dashboard/ \
              src/specify_cli/cli/commands/charter.py \
              src/specify_cli/upgrade/migrations/
```

### Occurrence verifier

```bash
python scripts/verify_occurrences.py \
  kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/WP2.<n>.yaml
```

### Mission-level verifier (run before the final WP merges)

```bash
python scripts/verify_occurrences.py \
  kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/occurrences/index.yaml
```

---

## WP-specific quickstart recipes

### WP2.1 — Bundle manifest + architecture doc + bundle CLI

Smoke check after implementing:

```bash
# Manifest round-trips
python -c "from charter.bundle import CANONICAL_MANIFEST; print(CANONICAL_MANIFEST.schema_version)"

# CLI works
spec-kitty charter bundle validate --json | python -m json.tool
# expect: "result": "success", "bundle_compliant": true
```

### WP2.2 — Canonical-root resolver + chokepoint plumbing

Smoke check after implementing:

```bash
# Resolver works from main checkout
python -c "
from pathlib import Path
from charter.resolution import resolve_canonical_repo_root
print(resolve_canonical_repo_root(Path.cwd()))
"

# Resolver works from a worktree
git worktree add /tmp/skp-resolver-test -b tmp/resolver-test
cd /tmp/skp-resolver-test
python -c "
from pathlib import Path
from charter.resolution import resolve_canonical_repo_root
print(resolve_canonical_repo_root(Path.cwd()))
"
# expect: prints the main checkout path, NOT /tmp/skp-resolver-test
cd -
git worktree remove /tmp/skp-resolver-test

# SyncResult now has canonical_root
python -c "
from pathlib import Path
from charter.sync import ensure_charter_bundle_fresh
r = ensure_charter_bundle_fresh(Path.cwd())
print(r.canonical_root, r.files_written)
"
```

### WP2.3 — Reader cutover + worktree excision + dashboard regression proof

**Step A (MUST run first)**: Capture the dashboard baseline on pre-WP2.3 `main`.

```bash
# On a branch rooted at pre-WP2.3 main, before any source edit:
python kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py \
  > kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json
git add kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/
git commit -m "WP2.3: capture pre-cutover dashboard typed-contract baseline"
# Only now proceed with the reader rewire.
```

Smoke checks after implementing:

```bash
# Fresh-clone smoke test
rm -rf .kittify/charter/governance.yaml .kittify/charter/directives.yaml \
       .kittify/charter/metadata.yaml .kittify/charter/references.yaml \
       .kittify/charter/context-state.json
spec-kitty charter context --action specify --json
# expect: exits 0; the removed files regenerate without running `charter sync`

# Worktree no-symlink smoke test
spec-kitty next --agent claude --mission unified-charter-bundle-chokepoint-01KP5Q2G 2>/dev/null || true
ls -la .worktrees/*/
# expect: NO .kittify/memory symlink or copy present; no charter-path entries in
# `git status` inside the worktree.

# AST-walk chokepoint-coverage test
PWHEADLESS=1 pytest tests/charter/test_chokepoint_coverage.py -v
```

### WP2.4 — Migration

Smoke check after implementing:

```bash
# Against the FR-013 reference fixture (assembled by the test suite):
PWHEADLESS=1 pytest tests/upgrade/test_unified_bundle_migration.py -v

# On a real project (dry-run mode not specified in contract; real apply):
# First verify the migration registers:
python -c "
from specify_cli.upgrade.migrations import MigrationRegistry
r = MigrationRegistry.auto_discover()
ids = [m.migration_id for m in r.migrations]
assert 'm_3_2_3_unified_bundle' in ids, ids
print('registered')
"

# Then on a fixture project:
cd /path/to/fixture-project
spec-kitty upgrade --json | tee /tmp/migration-report.json
# Inspect the report per contracts/migration-report.schema.json
# Re-apply should be a no-op:
spec-kitty upgrade --json | python -c "import json, sys; r = json.load(sys.stdin); assert r['applied'] is False, r"
```

---

## Common pitfalls

- **Editing agent copies instead of source templates.** Never edit `.claude/`, `.codex/`, `.opencode/`, etc. under the project's agent directories. Source templates live under `src/specify_cli/missions/*/command-templates/` and `src/specify_cli/skills/` (C-006). Agent copies re-flow on `spec-kitty upgrade`.
- **Adding a fallback for `git rev-parse` failure.** Do not. Per C-001 / C-009, the resolver raises `GitCommonDirUnavailableError` loudly. Fix the operator's environment; do not mask the failure.
- **Writing to `.kittify/charter/` inside a worktree.** The chokepoint writes to `canonical_root / ".kittify/charter/"` — the main checkout. A reader that hand-constructs a write path from `Path.cwd() / ".kittify/charter/"` will silently write into the worktree and be wrong. Use `SyncResult.canonical_root` as the anchor.
- **Deduplicating `src/specify_cli/charter/`.** Out of scope for this tranche (C-003). If a live reader in the duplicate package is surfaced during WP2.3 occurrence classification, rewire it in lockstep; do not delete the package.
- **Running the dashboard baseline capture after the reader rewire began.** The baseline must be captured on pre-WP2.3 code (D-6). Capturing afterwards bakes the post-cutover shape in as the reference and defeats FR-014.
- **Overlooking `ProcedureStep` kind of issues from Phase 1.** Phase 2 does not touch the doctrine artifacts directly, but lockstep edits to the duplicate `src/specify_cli/charter/` package can land a one-sided change that the AST-walk test catches — treat verifier failures there as serious, not as flakiness.

---

## Where to get help

- **Spec ambiguity** → open a comment on the mission tracking issue ([#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)).
- **Contract ambiguity** → update the relevant `contracts/*.md` under this mission and file the amendment in `spec.md` per DIRECTIVE_010.
- **Unexpected occurrence appearing during a WP** → add it to the WP's occurrence artifact explicitly (with `action: leave` and `rationale`) or fix it in-scope; do not ignore.
- **`git rev-parse --git-common-dir` misbehaving** → open a new issue; surface the behavior in `research.md §R-2` as an amendment.
