# Quickstart — tasks-py-degod-wave2-01KWH9EQ

Guard-running playbook for implementers and reviewers. Run from the repo root (or the
lane worktree — use the PRIMARY clone's `.venv`; verify via pytest, not bare imports).

## Before ANY fixture work

```bash
# venv must match uv.lock (typer pin) — golden --help fixtures are version-coupled
uv sync --frozen
python -c "import typer; print(typer.__version__)"   # must match uv.lock
```

## The parity guard (every WP, every commit)

```bash
PWHEADLESS=1 pytest \
  tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py \
  tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py \
  tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py \
  -q -p no:cacheprovider
# Expect 43 + 13 green, zero fixture edits (ratchet re-points per FR-012 excepted)
```

## Targeted family surface (declare per WP; coord harness mandatory for commit-router WPs)

```bash
PWHEADLESS=1 pytest tests/tasks/ tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider
```

## Arch gates this mission owns / touches

```bash
PWHEADLESS=1 pytest tests/architectural/test_tasks_command_surface.py -q      # new gates (once landed)
PWHEADLESS=1 pytest tests/architectural/test_untrusted_path_containment.py -q # #2306 fold (RED until the 1-line inventory fix)
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q      # pre-push, always
```

## Static gates (changed src+tests TOGETHER — Wave 1 lesson)

```bash
python -m mypy --strict src/specify_cli/cli/commands/agent/<changed>.py tests/specify_cli/cli/commands/agent/<changed_test>.py
ruff check src tests
```

## Seam interception spot-check (per relocated patched symbol)

```bash
# The patched attribute must BE the object production calls:
grep -n "_tasks\.<symbol>" src/specify_cli/cli/commands/agent/<family>.py   # routing present
grep -rn "patch(.*agent\.tasks\.<symbol>" tests/ | head                      # patch targets unchanged
```

## Boyscout census (FR-009)

```bash
# No tasks-domain path may appear here:
python -c "import json;print(json.load(open('tests/architectural/_gate_coverage_baseline.json'))['orphan_files'])"
```

## Watch-list

- Status bookkeeping commits on the PRIMARY checkout between WPs; coord-branch carries
  the mission artifacts (acceptance/issue matrices, review artifacts).
- Expect #2031 stale-assertion-analyzer false-positive storms at WP merges — cross-check
  against the seam checklist before acting.
- Any parity delta = revert the move; never adjust a fixture.
