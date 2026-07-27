---
verdict: approved
reviewer: reviewer-renata
cycle: 1
---

# WP02 — Store + backfill MissionTopology in meta.json — Review Cycle 1

**Verdict: APPROVED.** FR-002 (mint at create) and FR-003 (backfill + doctor)
implemented to the DoD, contract-pinned, gates green, scope clean. Both
adversarial mutation-checks were executed live and confirm non-fakeability.

## Per-criterion findings

### 1. FR-002 mint (`mission_creation.py`) — PASS
- Mint block (6.6) lands after `coordination_branch` is set and before
  `write_meta`, exactly as the prompt's verified ground truth requires.
- Uses **WP01's `classify_topology`** (`from mission_runtime import classify_topology`)
  — NOT a re-implemented 2×2 grid (C-003 satisfied). `has_lanes=False` is
  hardcoded at create with an explanatory comment (a fresh create has no
  `lanes.json`).
- Stores `meta["topology"] = topology.value` (enum stable string) and
  `meta.setdefault("flattened", False)` — `flattened` is a separate boolean
  provenance flag, never a topology value (R3 respected).
- Test (`test_mission_creation_topology.py`) drives `create_mission_core`
  end-to-end in a tmp git repo (not a fabricated dict): coord create →
  `topology=="coord"`+`flattened==false`; no-coord create → `single_branch`.
  **Asserts only the two create-reachable cells; does NOT assert an impossible
  create-time LANES** (R6 respected). Adversarial check #1 satisfied.

### 2. FR-003 backfill (`migration/backfill_topology.py`) — PASS
- Structurally mirrors `backfill_identity.py`: `TopologyBackfillResult`
  dataclass with wrote/skip/error action vocabulary, `backfill_mission_topology`,
  `backfill_topology_repo` (kitty-specs walk + `--mission` scoping), canonical
  sorted-key JSON (`json.dumps(..., indent=2, ensure_ascii=False, sort_keys=True)
  + "\n"`), and the same `json.JSONDecodeError/OSError/ValueError` corrupt-meta
  guard. Not a hand-rolled framework (canonical-sources discipline satisfied).
- Idempotent: a valid stored `topology` ⇒ `skip`, never overwritten.
- **Idempotence is PROVEN by byte-equality, not just asserted "skip":**
  `test_backfill_idempotent_second_run_skips` captures `_bytes(meta_path)` after
  the first run and asserts the file is byte-identical after the second.
  `ensure_topology` second-read test does the same on the shim path.
- **Mutation-check (RUN LIVE):** I patched `backfill_mission_topology` to drop
  the skip-on-present guard and always re-derive+write. Result:
  `test_backfill_idempotent_second_run_skips` AND
  `test_backfill_never_overwrites_existing_value` both went RED
  (`assert 'wrote' == 'skip'`). Restored after. The idempotence/never-overwrite
  contract is genuinely pinned, not vacuous (R4 satisfied).
- `test_backfill_never_overwrites_existing_value` stores `single_branch` while
  the signals (`coordination_branch` present) would derive `coord` — would fail
  if backfill overwrote. Exact non-fakeability anchor.
- 4-cell coverage via `@parametrize` reaches all four enum values including the
  lanes-bearing cells (`lanes`, `lanes_with_coord`), which the create path
  cannot reach.

### 3. FR-003 CLI (`migrate_cmd.py`) — PASS
- `@app.command(name="backfill-topology")` mirrors `backfill-identity`:
  `--json`/`--dry-run`/`--mission SLUG`, `locate_project_root()` guard,
  wrote/skip/error partition, JSON payload `{dry_run, summary, results}`,
  `raise typer.Exit(1)` iff any error.
- Tests (`test_backfill_topology_cli.py`) via `CliRunner`: exit 0 clean, exit 1
  corrupt, stable JSON shape (key sets pinned), dry-run writes nothing,
  idempotent 2nd run all-skip, `--mission` scoping leaves other missions
  untouched.

### 4. FR-003 doctor (`doctor.py`) — PASS
- `@app.command(name="topology")` + `_read_stored_topology` / `_collect_topology_rows`
  / `_print_topology_human` minimal render helpers. **Reads the STORED value
  (`meta.get("topology")`) — does NOT re-infer.** Reports `null` for
  un-backfilled, `null`+error reason for corrupt meta.
- **C-008 confirmed:** the doctor.py diff is ONLY the new `topology` subcommand +
  its three minimal helpers. No coord-recovery de-godding (#2059), no module
  split, no edits to `identity` or other subcommands. Verified at the commit
  level — WP02's commit touches doctor.py only for this addition.
- **Mutation-check (RUN LIVE):** I patched `_read_stored_topology` to re-derive
  and persist a missing topology. Result: `test_does_not_re_infer` AND
  `test_reports_stored_and_null` both went RED (`assert 'coord' is None`,
  `'topology' in persisted`). Restored after. The read-only / non-re-inference
  contract is genuinely pinned.

### 5. Compute-once-then-persist shim — PASS
- `ensure_topology` reads `meta.json`; valid stored `topology` ⇒ return, no
  write; absent ⇒ derive once via `classify_topology`, persist + default
  `flattened`, return. No perpetual re-inference arm (R1/C-004 respected).
- `test_ensure_topology_second_read_idempotent` proves the second read does NOT
  re-write via byte comparison. Existing `flattened` flag preserved.

### 6. Non-fakeability — PASS
Both live mutation-checks (overwriting backfill, re-inferring doctor) produce
red tests. The 4-cell parametrize would fail on a wrong `classify_topology`
result. No vacuous "it ran" assertions found — every test pins a concrete
contract (byte-equality, enum identity, JSON key sets, exit codes).

### 7. Gates — PASS
- `ruff check` on all four owned files + four test files: **All checks passed.**
- `ruff --select C901` (complexity ≤15): **All checks passed.**
- `mypy` on the four owned source files: **Success: no issues found.**
- 29 WP02 tests pass (`pytest -q`, 25.97s).
- No suppressions added by WP02 (the `# noqa` lines in `mission_creation.py` /
  `migrate_cmd.py` are pre-existing, in unchanged regions).
- S1192: backfill module hoists keys to `_TOPOLOGY_KEY`/`_FLATTENED_KEY`/
  `_COORDINATION_BRANCH_KEY`. The 5 `"topology"` literals in doctor.py are
  report-payload dict keys within the single new subcommand cluster (same
  pattern as the `identity` precedent); ruff passes clean. Non-blocking
  stylistic observation at most.

### 8. Scope / boundaries — PASS
- WP02's commit `9fbe17c69` touches EXACTLY the four owned files
  (`mission_creation.py`, `backfill_topology.py` [new], `migrate_cmd.py`,
  `doctor.py`) + their four test files — nothing else.
- The other files in the lane diff (`context.py`, `commit_router.py`,
  `implement.py`, `orchestrator_api/commands.py`, `artifacts.py`,
  `mission_runtime/__init__.py`, the two resolver tests) are WP01's commit
  `cec75f2b6` and WP00's ratchet commit `37e4e0a7e`, inherited via the lane
  base (lane-c branches from WP01's tip per the WP02→WP01 dependency). NOT WP02
  edits. No touch to `resolution.py` / `runtime_bridge.py` / `mission.py`.

## Dogfood note (informational, not a lane defect)
THIS mission's primary `meta.json` carries `topology: lanes`, `flattened: false`
(committed on primary, outside the lane diff). Per the orchestrator's note, this
is expected and correctly not part of WP02's lane diff. Not flagged.

## Lane-base divergence
lane-c is on the stale pre-#2081 mission branch; WP02's owned files are
verified identical between lane base and feat/, and the WP02 commit is
self-contained (only owned files). `--force` move is for this known-benign
divergence only — no fake-approval, no lane rebase needed.

**RESULTING LANE: approved.**
