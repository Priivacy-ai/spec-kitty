# Quickstart: Unified Charter Bundle and Read Chokepoint

**Mission**: `unified-charter-bundle-chokepoint-01KP5Q2G`
**Companion**: [plan.md](plan.md), [spec.md](spec.md), [data-model.md](data-model.md), [contracts/](contracts/)

Operational quickstart for contributors who need to implement, review, or verify a WP in this mission. Assumes you have the repo checked out at `/Users/robert/spec-kitty-dev/spec-kitty-charter-14-April/spec-kitty` (or the equivalent on your machine).

**v1.0.0 scope reminder**: this tranche covers the three files `src/charter/sync.py :: sync()` materializes — `governance.yaml`, `directives.yaml`, `metadata.yaml`. `references.yaml` and `context-state.json` are explicitly out of v1.0.0 scope. `.kittify/memory/` and `.kittify/AGENTS.md` symlinks in worktrees are documented-intentional and out of scope (C-011).

---

## Prerequisites

- Python 3.11+ on PATH (`python --version`).
- `git` on PATH with `--git-common-dir` support (git ≥2.5). Verify: `git rev-parse --git-common-dir` inside the repo returns `.git` or an absolute path.
- `pipx install --force --pip-args="--pre" spec-kitty-cli` — the CLI is installed globally via pipx.
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

## Out-of-scope carve-outs (do NOT edit)

These are listed here so the line numbers are unambiguous. Each carve-out is declared in the relevant WP2.3 occurrence artifact as `action: leave`.

- `src/specify_cli/core/worktree.py:478-532` — `.kittify/memory/` and `.kittify/AGENTS.md` symlink/copy/exclude block. C-011; documented-intentional per `src/specify_cli/templates/AGENTS.md:168-179`.
- `src/charter/compiler.py:169-196` — `write_compiled_charter()` produces `references.yaml`. C-012 (out of v1.0.0 manifest scope).
- `src/charter/context.py:385-398` — `context-state.json` lazy write path inside `build_charter_context()`. C-012. Note: the `build_charter_context` function's bundle-read path (~line 555) IS rewired in WP2.3; only the context-state write block at lines 385-398 is the carve-out.

---

## How to pick a WP

```bash
spec-kitty agent tasks status --feature unified-charter-bundle-chokepoint-01KP5Q2G
```

WPs are strictly sequential (C-007). The ready WP is always the lowest-numbered WP that is not yet merged and whose predecessors are all merged.

---

## Implementing a WP (standard loop)

1. **Read the WP section in `plan.md`**. Every WP has a "Scope" list and an "Acceptance gates" list that together are the full bar to pass.
2. **Read the relevant contract file(s)** under `contracts/` for any new typed surface.
3. **Author the occurrence artifact first** at `kitty-specs/.../occurrences/WP2.<n>.yaml`. Schema at `contracts/occurrence-artifact.schema.yaml`. **For WP2.3 specifically, include the three C-011/C-012 carve-outs as explicit `action: leave` entries.**
4. **Implement source changes** following the WP scope list.
5. **Add/update tests** per the WP's test list.
6. **Run the WP gates locally** before pushing (see "Running the gates locally" below).
7. **Open PR against `main`**. Link the WP tracking issue.

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
                    tests/charter/test_worktree_charter_via_canonical_root.py \
                    tests/init/test_fresh_clone_no_sync.py \
                    tests/test_dashboard/test_charter_chokepoint_regression.py

# WP2.4
PWHEADLESS=1 pytest tests/upgrade/test_unified_bundle_migration.py
```

### Type check

```bash
mypy --strict src/charter/ src/specify_cli/dashboard/ \
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

### C-011 carve-out check (run in any WP PR that touches `src/`)

```bash
# Verify the memory/AGENTS symlink block is unchanged vs pre-Phase-2 main
git diff main..HEAD -- src/specify_cli/core/worktree.py
# Expect: no changes in lines 478-532, OR no changes to this file at all.
```

---

## WP-specific quickstart recipes

### WP2.1 — Bundle manifest + architecture doc + bundle CLI

Smoke check after implementing:

```bash
# Manifest round-trips
python -c "from charter.bundle import CANONICAL_MANIFEST; print(CANONICAL_MANIFEST.schema_version, len(CANONICAL_MANIFEST.derived_files))"
# expect: 1.0.0 3

# CLI works and reports out-of-scope files as warnings
spec-kitty charter bundle validate --json | python -m json.tool
# expect: "result": "success", "bundle_compliant": true
# expect: "out_of_scope_files" lists references.yaml and context-state.json if present
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
# expect: prints absolute path to the main checkout

# Resolver works from a subdirectory (stdout is relative-to-cwd)
cd src/charter
python -c "
from pathlib import Path
from charter.resolution import resolve_canonical_repo_root
print(resolve_canonical_repo_root(Path.cwd()))
"
cd -
# expect: prints the SAME absolute path — subdirectory resolution correctly strips ../../.git

# Resolver works from a worktree (stdout is absolute)
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

# Resolver detects inside-.git case
python -c "
from pathlib import Path
from charter.resolution import resolve_canonical_repo_root, NotInsideRepositoryError
try:
    resolve_canonical_repo_root(Path('.git'))
    print('FAIL: should have raised')
except NotInsideRepositoryError as e:
    print(f'OK: {e}')
"

# SyncResult now has canonical_root
python -c "
from pathlib import Path
from charter.sync import ensure_charter_bundle_fresh
r = ensure_charter_bundle_fresh(Path.cwd())
print(r.canonical_root, r.files_written)
"
```

### WP2.3 — Reader cutover + dashboard regression proof

**Step A (MUST run first)**: Capture the dashboard baseline on pre-WP2.3 `main`.

```bash
# On a branch rooted at pre-WP2.3 main, BEFORE any source edit:
python kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/capture.py \
  > kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json
git add kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/
git commit -m "WP2.3: capture pre-cutover dashboard typed-contract baseline"
# Only now proceed with the reader rewire.
```

Smoke checks after implementing:

```bash
# Fresh-clone smoke test
rm -f .kittify/charter/governance.yaml .kittify/charter/directives.yaml \
      .kittify/charter/metadata.yaml
spec-kitty charter context --action specify --json >/dev/null
ls .kittify/charter/
# expect: governance.yaml, directives.yaml, metadata.yaml regenerate
# (charter.md, and possibly out-of-scope references.yaml/context-state.json, also present)

# Worktree reader transparency smoke test
# In a terminal inside a worktree (e.g., .worktrees/any-existing-worktree):
python -c "
from pathlib import Path
from charter.sync import ensure_charter_bundle_fresh
r = ensure_charter_bundle_fresh(Path.cwd())
print('canonical_root =', r.canonical_root)
# Expected: points at the MAIN checkout, not the worktree
"
ls -la .kittify/
# Expected inside a worktree: .kittify/memory -> ../../../.kittify/memory (symlink, unchanged)
#                             .kittify/AGENTS.md -> ../../../.kittify/AGENTS.md (symlink, unchanged)
# Expected inside a worktree: NO .kittify/charter/ directory
#   (worktree setup never created one; chokepoint writes to main checkout)

# AST-walk chokepoint-coverage test
PWHEADLESS=1 pytest tests/charter/test_chokepoint_coverage.py -v

# C-011 carve-out check
git diff main..HEAD -- src/specify_cli/core/worktree.py
# expect: empty diff, OR no edits to lines 478-532
```

### WP2.4 — Migration

Smoke check after implementing:

```bash
# Fixture matrix:
PWHEADLESS=1 pytest tests/upgrade/test_unified_bundle_migration.py -v

# Verify the migration registers:
python -c "
from specify_cli.upgrade.migrations import MigrationRegistry
r = MigrationRegistry.auto_discover()
ids = [m.migration_id for m in r.migrations]
assert 'm_3_2_3_unified_bundle' in ids, ids
print('registered')
"

# On a fixture project:
cd /path/to/fixture-project
spec-kitty upgrade --json | tee /tmp/migration-report.json
# Inspect: expect migration_id='m_3_2_3_unified_bundle', target_version='3.2.3',
#          applied=true/false, charter_present=true/false, bundle_validation object.
# No worktrees_scanned, symlinks_removed, gitignore_reconciled fields — those were
# removed from the schema after the 2026-04-14 design review.

# Re-apply is a no-op:
spec-kitty upgrade --json | python -c "
import json, sys
r = json.load(sys.stdin)
assert r['applied'] is False, r
print('no-op on second apply: OK')
"
```

---

## Common pitfalls

- **Editing `src/specify_cli/core/worktree.py`.** C-011 carve-out. Those symlinks are for project memory / agent instructions, NOT the charter bundle. If you find yourself editing lines 478-532, stop — you're reintroducing the bug the 2026-04-14 design review corrected. Canonical-root resolution (WP2.2) is the charter-visibility fix.
- **Adding `references.yaml` or `context-state.json` to the v1.0.0 manifest.** C-012 out of scope. `references.yaml` is produced by the compiler pipeline at `src/charter/compiler.py:169-196`; `context-state.json` is runtime state written lazily by `src/charter/context.py:385-398`. Neither is a `sync()`-produced derivative. Expanding manifest scope requires a new schema version in a later tranche.
- **Editing agent copies instead of source templates.** Never edit `.claude/`, `.codex/`, `.opencode/`, etc. Source templates live under `src/specify_cli/missions/*/command-templates/` and `src/specify_cli/skills/` (C-006).
- **Adding a fallback for `git rev-parse` failure.** Do not. Per C-001 / C-009, the resolver raises `GitCommonDirUnavailableError` loudly. Fix the operator's environment; do not mask the failure.
- **Assuming `git rev-parse --git-common-dir` returns an absolute path.** It does not in the common case — it returns a path relative to `cwd` (e.g., `.git` from the repo root, `../../.git` from `src/charter`, `.` from inside `.git/` itself). The resolver must resolve stdout against `cwd` explicitly. Absolute is only returned for linked worktrees.
- **Writing to `.kittify/charter/` inside a worktree.** The chokepoint writes to `canonical_root / ".kittify/charter/"` — the main checkout. Use `SyncResult.canonical_root` as the anchor when you need to reconstruct absolute paths.
- **Deduplicating `src/specify_cli/charter/`.** Out of scope (C-003). Lockstep-edit only.
- **Running the dashboard baseline capture after the reader rewire began.** The baseline must be captured on pre-WP2.3 code (D-6). Capturing afterwards defeats FR-014.
- **Having the migration scan worktrees.** Narrowed scope (spec FR-007 / D-14): migration does not scan or modify worktrees. If you write migration code that walks `.worktrees/`, stop — that's Phase 1 mental model, not post-design-review Phase 2.

---

## Where to get help

- **Spec ambiguity** → open a comment on the mission tracking issue ([#464](https://github.com/Priivacy-ai/spec-kitty/issues/464)).
- **Contract ambiguity** → update the relevant `contracts/*.md` under this mission and file the amendment in `spec.md` per DIRECTIVE_010.
- **Unexpected occurrence appearing during a WP** → add it to the WP's occurrence artifact explicitly (with `action: leave` and `rationale`) or fix it in-scope; do not ignore.
- **`git rev-parse --git-common-dir` misbehaving on a supported platform** → open a new issue; surface the behavior in `research.md §R-2` as an amendment and extend the fixture matrix in `tests/charter/test_canonical_root_resolution.py`.
