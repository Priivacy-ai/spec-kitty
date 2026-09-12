# Quickstart: Annoying Bugs Sweep Verification

Run from the repository root on `fix/annoying-bugs-sweep`.

## 1. Record the baseline

```bash
git merge-base HEAD upstream/main
```

Run each new P0 node against that base with `PYTHONPATH=<base-worktree>/src` and record the expected
failure in the mission evidence. Do not repair pre-existing mainline reds.

## 2. Birth-cutover slice

```bash
PWHEADLESS=1 pytest tests/unit/migration/test_backfill_runtime_state.py -q
PWHEADLESS=1 pytest tests/integration/test_migration_backfill.py -q
PWHEADLESS=1 pytest tests/regression/test_birth_cutover.py -q
```

Confirm mixed terminal/non-terminal WPs retain their lanes, claim slots match legacy values, every
writing caller is covered, and a second run is idempotent.

## 3. Dead-code slice

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/review/test_dead_code_baseline.py -q
```

Confirm injected `FileNotFoundError` and a non-Python/non-`src` fixture produce structured
undeterminable findings, while the supported POSIX fixture preserves its symbol set.

## 4. Doctrine and help slices

```bash
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q
PWHEADLESS=1 pytest tests/architectural/ -q
```

Also run the focused skill-pack and profile-invocation help tests selected by the implementation
WPs. Verify source doctrine only; do not edit generated agent directories.

## 5. Static checks

```bash
ruff check <touched-python-paths>
mypy <touched-python-paths>
```

Record targeted test node IDs, baseline-red evidence, tracker links, and any Sonar hotspot review
still required in the PR body.

