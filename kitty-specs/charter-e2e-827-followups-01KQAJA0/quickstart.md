# Quickstart — Verifying Charter E2E #827 Follow-ups (Tranche A)

Reproducible end-to-end verification walkthrough for [spec.md](spec.md) / [plan.md](plan.md).

All commands run from the repository root checkout:

```bash
cd /private/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260428-192343-wKMuqI/spec-kitty
```

## 1. Sync environment

This step is what FR-002 documents as the **pre-review/pre-PR sync command**. Run it once at the start.

```bash
uv sync --frozen
```

Expected: installed `spec-kitty-events` and `spec-kitty-tracker` versions match `uv.lock` exactly.

## 2. Run the full mission verification matrix (NFR-003)

Runs in any order; listed in the same order as the spec for clarity. All seven invocations must pass on the merging branch before opening the PR.

```bash
uv lock --check
PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q
uv run pytest tests/contract/test_cross_repo_consumers.py -q
uv run pytest tests/next -q
uv run pytest tests/specify_cli/cli/commands/agent -q
uv run pytest tests/integration -k 'dossier or move_task or dirty or transition' -q
uv run pytest tests/integration -k 'specify or plan or auto_commit or mission' -q
```

Plus the new architectural test introduced by this mission:

```bash
uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q
```

## 3. Per-issue spot checks

### #848 — drift check works in both directions

Confirm the drift check passes on a clean install:

```bash
uv sync --frozen
uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q     # PASS expected
```

Synthetically induce drift and confirm the check fires:

```bash
# In a throwaway shell (do NOT commit this):
uv pip install spec-kitty-events==<wrong-version>     # any version that disagrees with uv.lock
uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q     # FAIL expected
# Confirm the failure message names spec-kitty-events AND prints `uv sync --frozen`.
uv sync --frozen      # restore
```

### #844 — charter E2E rejects null prompt

The standard run validates the green path:

```bash
PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q     # PASS expected
```

Optional: temporarily monkey-patch the runtime to emit a `kind=step` envelope with `prompt_file=None`, run the test, confirm it fails with a message naming the missing prompt and the violating decision. Revert the patch.

### #845 — dossier snapshot does not self-block

```bash
uv run pytest tests/integration/test_dossier_snapshot_no_self_block.py -q     # PASS expected
```

Manual repro:

```bash
# Create a synthetic mission (or use an existing one) whose worktree has nothing else dirty.
spec-kitty agent mission create "snap-smoke" --json
# Trigger any command that writes the dossier snapshot for that mission.
# Then immediately try a transition:
spec-kitty agent tasks move-task WP01 --to claimed --mission snap-smoke ...
# Expected: success. Without this fix, this would fail with a self-inflicted dirty-state error.
```

### #846 — specify/plan commit boundary

```bash
uv run pytest tests/integration/test_specify_plan_commit_boundary.py -q     # PASS expected
```

Manual repro:

```bash
# 1. Create a fresh mission and DO NOT populate spec.md.
spec-kitty agent mission create "boundary-smoke" --json
# Inspect git log: there should be a scaffold commit (existing behavior) but no "spec ready" auto-commit.
git log --oneline -5

# 2. Try to advance:
spec-kitty agent mission setup-plan --mission boundary-smoke --json
# Expected: phase_complete=false, blocked_reason mentions "substantive content".

# 3. Populate spec.md with at least one real FR row, then re-run setup-plan:
# (edit kitty-specs/<dir>/spec.md to add a Functional Requirements table with FR-001)
spec-kitty agent mission setup-plan --mission boundary-smoke --json
# Expected: phase_complete=true; setup-plan auto-committed plan.md.
```

## 4. Static & type checks

```bash
uv run mypy --strict src/specify_cli
# Expected: no new type errors introduced by this mission.
```

The project's existing coverage gate continues to apply on new code. New test files added by this mission cover their own logic; new production code paths are covered by the corresponding regression tests above.

## 5. PR closeout (FR-016 mechanical check)

Before opening the PR, confirm the body includes:

- `Closes #844`, `Closes #845`, `Closes #846`, `Closes #848` (each on its own line, GitHub-recognized syntax).
- A note that **#847 is closed and intentionally out of scope** for this tranche.
- A note that **#827 remains open** unless the broader epic acceptance is fully complete.
- A note that **PR #855 was superseded by PR #864 and was not merged**; it was consulted only as historical reference for #844.

## 6. Post-merge sanity

After merge into `main`, on a fresh clone:

```bash
git clone <repo> spec-kitty-fresh
cd spec-kitty-fresh
uv sync --frozen
uv run pytest tests/architectural/test_uv_lock_pin_drift.py -q
PWHEADLESS=1 uv run pytest tests/e2e/test_charter_epic_golden_path.py -q
```

Expected: both pass with no manual setup beyond `uv sync --frozen`.

## What this quickstart deliberately does NOT cover

Per Constraint C-003 / Out-of-Scope section in [spec.md](spec.md), this mission does **not** verify or touch:

- #822 stabilization backlog issues.
- The merge engine, lane state machine, worktree creation flow, or status state machine.
- Dependency-management policy beyond the FR-001 / FR-002 drift detector.
- PR #855 (closed/superseded; reference-only).
