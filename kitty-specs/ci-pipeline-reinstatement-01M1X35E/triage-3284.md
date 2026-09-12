# Base-red triage record — #3284 (WP03, FR-002 / SC-008)

**Mission:** `ci-pipeline-reinstatement-01M1X35E` · **WP:** WP03 · **Profile:** python-pedro (implementer)
**Governing:** FR-002, SC-008; `contracts/p1-census-oracle.md`; DIR-034 (test-first / stable
entry point), DIR-041 (tests as scaffold — never delete/silence a valid red), DIR-043 (close the
defect class by construction); Charter Red-Main Discipline (SO#9) + Pre-existing-Failure-Reporting.
**Census oracle consumed:** `tests/architectural/_p1_census_oracle.py` (WP02, merged into lane-c) —
`authorize_drop`, `is_dead`, `is_known_live`, `census_dead_surfaces`.

Lane base HEAD: `f86f9297b9` (post-#3921, WP01 governance-map + WP02 census merged).
Planning/coord base: `cf8b9fb6ea`.

---

## T013 — Red-first reproduction of #3284 on the post-#3921 base

#3284 was filed as **"main full suite: 23 untracked failures + 2 errors"**. The canonical suite
(`spec.md:30`) is `pytest -n auto`. Per the CLAUDE.md baseline-red gotcha, the historical set is
**re-derived live** — #3921 landed fixes, so the current set differs from the historical 23.

### Commands run (exact)

| # | Command | Result |
|---|---------|--------|
| R1 | `pytest tests/ -q --collect-only` | **39098 collected, 0 collection errors** (the #3284 "2 errors" were collection-time and are now clean) |
| R2 | `pytest tests/ -n auto --dist loadfile -m "not stress and not timing" -q` | ran to ~39008/39055; **no failure among the mission_v1 / owned surfaces**; tail did not bootstrap-terminate cleanly (see Hangs) |
| R3 | 9 owned `tests/missions/test_mission_v1_*` files, isolated | **275 passed** |
| R4 | `pytest tests/missions/ -q` (full retained dir) | **573 passed** |
| R5 | Per-directory sweep, hard `timeout`, `-n 4`, `--timeout=120`, `-m "not stress and not timing"` | **8 reliable base reds in isolation + 2 hang dirs** (enumerated below) |

Environment for every run: `PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=<worktree>/src`
against the shared `.venv` (Python 3.11.15) — `PYTHONPATH` forced so the lane's `src/` is under
test, not the sibling checkout (MEMORY: global-spec-kitty-resolves-different-checkout).

### The historical #3284 set (23 failures + 2 errors) is RESOLVED by #3921

Grounding identified the **`tests/missions/test_mission_v1_*` files as the candidate dead-import
drops** — behavioral tests over `specify_cli.mission_v1`. On the post-#3921 base:

- **Collection is clean** — 0 errors (down from the historical 2).
- **The candidate suite is fully green** — 275/275 owned, 573/573 for the whole `tests/missions/`.
- The census pins **`specify_cli.mission_v1` LIVE** (`census.json`: `importer-count:>0`); the oracle
  independently confirms **17 static importers** (`runtime/next/{decision,runtime_bridge_composition,
  next_invocation_lifecycle}.py`, `review/gate_registry.py`, `skills/manifest_store.py`, …).

The 23 historical reds are therefore **not reproducible** on this base — #3921 wired `mission_v1`
back in as a live surface, turning the "dead-import" failures green. This IS the red-first evidence:
the observable precondition (the #3284 base state) is captured before any drop/fix.

### Residual base reds re-derived live (NOT part of #3284; NOT in WP03's owned partition)

The isolated per-directory sweep (R5) surfaced **8 reds + 2 hang dirs**. Every one is **outside**
`owned_files` and **none exercises `mission_v1`**. Attribution per the baseline-red gotcha:

| # | Node id | Symptom | Attribution | Disposition (WP03) |
|---|---------|---------|-------------|--------------------|
| B1 | `tests/agent/test_doc_generators.py::test_sphinx_generation_end_to_end` | `GeneratorResult(✗ Failed, 0 files, 3 errors)` | **Env** — sphinx toolchain missing (category-2). Pre-existing. | out-of-scope; coordinate (tooling) |
| B2 | `tests/architectural/test_golden_count_ban.py::test_convert_sites_do_not_exceed_frozen_baseline` | `15 un-annotated convert sites in tests/architectural exceeds frozen baseline 14` (+1) | **Gate baseline** — the +1 site lands in `tests/architectural` (WP02 census-oracle test additions). WP02/WP16 territory. | out-of-scope; coordinate WP16 (baseline demotion) — Risks note forbids faking a baseline swap here |
| B3 | `tests/architectural/test_archive_root_byte_identical.py::test_no_preexisting_archived_file_was_modified` | 21+ `D kitty-ops/01M0A*.jsonl` deletions vs the test's frozen ref | **Cross-branch/pre-existing** — `git diff cf8b9fb6ea..HEAD -- kitty-ops/` is EMPTY; the mission never touched `kitty-ops/`. | out-of-scope; not mission-caused |
| B4 | `tests/audit/test_no_legacy_agent_profiles_path.py::test_no_legacy_agent_profiles_path_literals_in_active_codebase` | legacy `agent-profiles` path literal in `docs/development/how-to/manage-issue-tracker.md` | **Pre-existing docs content** — file last authored by `03db1a5fd1` (pre-mission); mission touch is a merge commit only. | out-of-scope; pre-existing |
| B5 | `tests/docs/test_docs_seo.py::...[docs/development/how-to/manage-issue-tracker.md]` | description length 194 > band 50–180 | **Pre-existing docs content** — same file as B4. | out-of-scope; pre-existing |
| B6 | `tests/docs/test_description_length_gate.py::test_live_tree_is_clean` | 1 violation: same file, 194 chars | **Pre-existing docs content** — same file as B4. | out-of-scope; pre-existing |
| B7 | `tests/integration/test_owned_checkout_mark_status.py::test_owned_preflight_refuses_before_effects[sync-OWNED_SYNC_UNSUPPORTED]` | `KeyError: 'error_code'` on the `sync` parametrization | **Env/retired-sync** — sync transport retired in The Convergence; parametrization is not a `mission_v1` path. | out-of-scope; coordinate (owning subsystem) |
| B8 | `tests/specify_cli/test_gitignore_contract.py::test_charter_synthesis_artifacts_are_trackable` | `load_pack_registry(...)` under `LegacyOrgPackDoctrineKeyWarning` (`.kittify/config.yaml` legacy `doctrine.org.packs` key) | **Pre-existing repo config** — repo-wide config uses the legacy key (warns on every `spec-kitty` invocation). | out-of-scope; pre-existing config |
| H1 | `tests/review/` (whole dir) | hard `timeout` (exit 124) | **#3283 bootstrap/hang** — WP04 territory. | out-of-scope; coordinate WP04 (#3283) |
| H2 | `tests/runtime/` (whole dir) | hard `timeout` (exit 124) | **#3283 bootstrap/hang** — WP04 territory. | out-of-scope; coordinate WP04 (#3283) |

None of B1–B8/H1–H2 is a #3284 red, and none is in `owned_files`
(`tests/missions/test_mission_v1_*`). Per the WP03 **ownership note (DIR-024)** — a fix touching
`src/**` or a test outside `owned_files` requires orchestrator coordination, not a silent edit —
these are recorded and handed off, never green-washed (Charter SO#9). They are pre-existing /
environmental / other-WP baseline reds independent of the #3284 mission_v1 red class.

---

## T014–T016 — Per-red disposition of the #3284 candidate set (drop-or-fix, non-fakeable)

WP03's owned partition is the **9 `tests/missions/test_mission_v1_*` files** — the candidate
"dead-import drops." Each is triaged against the WP02 census. **The census REFUSES every drop**
because the subject src surface `specify_cli.mission_v1` is **census-LIVE** — dropping any of them
would be the exact P1 loophole (a live regression buried as "dead").

| Owned candidate file (subject: `specify_cli.mission_v1*`) | Census verdict on subject | `authorize_drop` | Disposition |
|---|---|---|---|
| `test_mission_v1_compat_unit.py` | LIVE (17 importers) | REFUSED | **RETAIN** (not a drop) — green |
| `test_mission_v1_events_unit.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_mission_v1_guards_unit.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_mission_v1_runner_unit.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_mission_v1_schema_unit.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_e2e_mission_v1_integration.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_mission_guards_integration.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_mission_loading_integration.py` | LIVE | REFUSED | **RETAIN** — green |
| `test_mission_software_dev_integration.py` | LIVE | REFUSED | **RETAIN** — green |

**Drops: 0. Fixes (live regression, in owned partition): 0** — the candidate suite is already green
on the post-#3921 base. An empty drop-set is a **valid** outcome here precisely because every
candidate surface is independently evidenced as **live** (SC-008 / DoD: an empty drop-set is valid
only if every candidate red is drop-evidenced-or-passing — here they all pass over a live surface).

### Non-fakeable evidence — the census machine-blocks the P1 loophole

Verified empirically against `tests/architectural/_p1_census_oracle.py`:

```
is_known_live("specify_cli.mission_v1")            -> True   (static_importer_count = 17)
authorize_drop("specify_cli.mission_v1")           -> REFUSED: UnevidencedDeadError
    (mission_v1 is recorded LIVE in census.json, never dead)
authorize_drop("specify_cli.mission_v1", census=<tampered: mission_v1 marked dead>)
                                                   -> REFUSED: LiveSurfaceNotDroppableError
    (known-live guard is tamper-proof: even a doctored census cannot authorize the drop)
authorize_drop("tests.missions.test_mission_v1_compat_unit")
                                                   -> REFUSED: SubjectNotSrcSurfaceError
    (subject rule: the census never judges a test file's own always-zero importer count)
census_dead_surfaces() -> ('specify_cli.sync','specify_cli.delivery','specify_cli.saas',
                           'specify_cli.event_journal','specify_cli.egress','websockets')
    (non-vacuous, DIR-043 — the only census-dead surfaces are the 6 retired subsystems,
     none of which any owned mission_v1 test imports)
```

This closes the defect class by construction (DIR-043): no future agent can relabel the live
`mission_v1` tests "dead" to drop them — `authorize_drop` refuses under both the real and a tampered
census. Guard test: `tests/missions/test_mission_v1_compat_unit.py::TestWP03CensusNonFakeableGuard`.

---

## T017 — Base green + no leave-red (verification)

- **Owned candidate suite:** `pytest tests/missions/test_mission_v1_*` → **275 passed** (isolated).
- **Full retained mission suite:** `pytest tests/missions/ -q` → **573 passed, 0 failed** (before the
  guard); **578 passed** after adding `TestWP03CensusNonFakeableGuard` (+5).
- **Retained suite + census oracle + guard:** `pytest tests/missions/
  tests/architectural/test_p1_census_oracle.py -q` → **593 passed, 0 failed** (final green proof).
- **Static gates:** `ruff check` clean; `mypy` clean on all WP03-added lines (the file's remaining
  untyped-def findings are its pre-existing baseline at lines ≤330, outside the WP03 partition).
- **#3284 red class (mission_v1 dead-imports + 2 collection errors):** resolved — 0 untracked
  failures remain in the class; collection clean.
- **No third disposition:** every #3284 candidate is RETAINED-live-green (0 drops, 0 in-partition
  fixes); nothing is tracked-and-left-red. The 8 residual base reds + 2 hangs (B1–B8, H1–H2) are
  **not** #3284 reds and **not** in the owned partition — recorded and handed off for coordination,
  never silenced (DIR-041, Charter SO#9).

**Honesty note (DIR-034/DIR-041):** the #3284 red class was already fixed upstream by #3921, so the
WP03 deliverable is (a) the red-first reproduction proving the class is resolved, and (b) the
permanent, non-fakeable census guard that keeps it closed. No synthetic pytest red was fabricated —
DIR-041 forbids inventing a red where the defect class is genuinely already closed.
