# Parity Contract — tasks-py-degod-wave2-01KWH9EQ

The executable contract for this pure-parity mission (spec C-003). Four layers; ALL must
hold at every commit of every WP.

## Layer 1 — Contract harnesses (pre-existing, unmodified)

- `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py` — 27 cases
  (10 byte-exact `--help` fixtures; JSON legs shape-checked via `_shape()`).
- `tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py` — 16 cases
  incl. T004 (move_task coord skip-exit-0 + wrong-leg detector) and T005
  (mark_status/map_requirements refuse-exit-1) — the #2300 divergence pins (C-001).
- The ONLY sanctioned edit: FR-012 ratchet re-points (below). Expected-output fixtures
  are never adjusted to absorb a diff; a parity delta reverts the move.

## Layer 2 — Byte-freeze suite (NEW, committed before any routing change)

- `tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py` +
  `fixtures/tasks_cli/json/byte_contracts.json`.
- One case per emission site (13 total; site→subcommand map in research.md D3), each
  asserting `result.stdout == expected_stdout` (byte equality; never `len()==N`).
- Cases must cover: the compact success legs, the compact error legs (trigger conditions
  per D3), and the `status --json` indent=2 leg.
- Fixtures use production-shaped mission data (real-format slugs/ULIDs), not
  placeholders.
- Commit order (C-003 parity-ATDD): the suite lands GREEN against the pre-change tree in
  its own commit BEFORE the first Stream A/Stream B production change.

## Layer 3 — Ratchet re-point rule (FR-012) — post-tasks squad hardened

- `_BRANCH_COVERAGE_FLOORS` / `_mutating_function_line_ranges()` in the coord harness
  resolve `move_task`/`status`/`map_requirements` by name from `tasks.py`'s AST, the
  coverage session is single-file (`include=[tasks.py]`), and
  `_branch_coverage_by_function` returns **100.0 when `total == 0`** — a naive re-point
  is therefore VACUOUSLY GREEN (measures nothing, passes every floor).
- WP05 performs the one-time plumbing rewrite: a `{floored_name: (module, qualname)}`
  map feeding both the per-function AST resolution and a multi-file `include=` set, with
  the vacuous `else 100.0` arm replaced by a hard failure (`total == 0` on a floored
  function = plumbing bug). WP06/WP07 each ADD their relocated module to the map/include.
- **Acceptance evidence per re-point**: a demonstrated RED fire of the re-pointed entry
  (locally lowered floor or dropped scenario, output pasted, restored) — never a
  recorded percentage. Exactly 100.0 on a function with known branches = review-reject.
- **Diff-scope rule**: `git diff` on the coord harness may touch ONLY the floors mapping,
  `_mutating_function_line_ranges`, and the include/analyze wiring. Any edit to
  `_run_all_scenarios`, floor VALUES, or assertion bodies is out-of-scope and rejected.
- Forbidden: deleting the ratchet, lowering a floor, leaving it measuring the thinned
  wrapper, or leaving the vacuous fallback alive. Re-pointing is expressly NOT fixture
  adjustment.
- Label note: harness case labels T004/T005 (skip-arm / refuse-arm) are the coord
  harness's internal names — never to be confused with this mission's WP01 subtasks.

## Layer 4 — Seam interception checks (NFR-002)

- **One committed checklist for the whole mission**:
  `kitty-specs/tasks-py-degod-wave2-01KWH9EQ/seam-checklist.md`, columns
  `symbol | tasks.py binding (line) | routed-via-_tasks? | interception/identity test id |
  monkeypatch sites swept`. WP02 creates it; every family WP appends its rows. Free-form
  Activity-Log prose is not the checklist.
- Binding (leg a) is proven by parametrized `is`-identity tests over the FULL move-set
  (cheap, non-fakeable — no spot-checking); interception (leg c) by sentinel-patch tests
  through the `_tasks.<attr>` route for the defensively-patched symbols.
- "The ~370 tests pass" alone is NOT acceptance evidence for this layer.

## Acceptance evidence per WP

1. 43/43 harness + 13/13 byte-freeze green (unmodified fixtures).
2. Targeted family tests + coord harness (for commit-router WPs) green.
3. Seam checklist ticked with interception evidence.
4. `mypy --strict` on changed src+tests together + `ruff` — zero findings.
5. LOC ceiling ratcheted down to the new `tasks.py` size.
