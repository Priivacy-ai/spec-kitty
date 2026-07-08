# Quickstart / Validation — Read-Surface SSOT Completion

How to verify the mission end-to-end once implemented. All commands from the repo root.

## 1. #2404 — accept reads what accept wrote (the headline, SC-003)

On a **coord-topology** mission with a valid `mid8`:

```bash
# Fill the acceptance matrix and commit it via each write path, then read it back via accept.
# EXPECT: the matrix lands on the COORDINATION surface every time and accept sees the real edits.
spec-kitty spec-commit --mission <coord-mission> kitty-specs/<coord-mission>/acceptance-matrix.json
spec-kitty agent mission finalize-tasks --mission <coord-mission>   # batches acceptance-matrix under TASKS_INDEX
spec-kitty accept --mission <coord-mission>                          # residual commit + read-back
```

Automated proof: the IC-03 integration test asserts, on a coord fixture, that a matrix written via
`spec-commit` / `finalize` / `accept`-residual all resolve to the coordination ref and are read back by
`_check_lane_gates` — no stale copy. A regression that reintroduces a single-`kind`-per-batch commit fails
`contracts/partition-aware-commit-seam.md`'s INV-C1 red-first test.

## 2. Thread A — feature_dir reads on the seam + ratchet at floor 2

```bash
# The coord_authority gate must be at floor 2 (was 7); the 2 status-write false-negatives reclassified.
PWHEADLESS=1 uv run pytest tests/architectural/test_resolution_authority_gates.py -q
# Live split re-check (should read 32 total; write count reflects FR-003 reclassification):
uv run python -c "import sys; sys.path.insert(0,'tests/architectural'); \
from test_resolution_authority_gates import scan_coord_authority_call_sites as s; \
from pathlib import Path; x=s(Path('src')); print('total', len(x))"
```

EXPECT: gate green at floor 2; no lifecycle read re-derives the feature dir off a raw resolver;
`orchestrator_api/commands.py:1451` raises fail-closed instead of `CommitTarget(ref=current_branch)`.

## 3. Thread B — inline meta reads drained behind the new ratchet

```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_inline_meta_read_gate.py -q
```

EXPECT: green at the pinned floor; a planted inline `json.loads(<meta>)` goes RED; a mass-allow-list attempt
trips the routed-count floor. Deferred `m_0_13_*` sites are allow-list entries carrying a filed issue.

## 4. Thread D — #1716 closeout

```bash
unset GITHUB_TOKEN
gh api repos/Priivacy-ai/spec-kitty/issues/1716/sub_issues --jq '[.[]|select(.state=="open")|.number]'
# EXPECT (pre-close): [2088, 2100]. After both close + #2462 merged → close #1716.
```

## 5. Whole-suite gates

```bash
PWHEADLESS=1 uv run pytest tests/architectural/ -q          # both ratchets + partition guard green
ruff check . && uv run mypy src/                            # zero issues; complexity ≤15
pytest tests/architectural/test_no_legacy_terminology.py    # if any prose/doctrine touched
```

## Dependency reminder (C-003)

Threads A/C consume the `PlacementSeam` + partition-aware commit context from PR #2462. Do not *implement*
IC-01/IC-02/IC-04 until #2462 merges to `upstream/main`; rebase `design/read-surface-ssot-closeout` onto the
merged base first. Threads B (non-collision files) and D (#2088 close) can proceed independently.
