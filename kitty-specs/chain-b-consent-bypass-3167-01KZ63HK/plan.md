# Implementation Plan: retire the dead queue-backed event drain

**Branch**: `feat/chain-b-consent-bypass-3167` | **Date**: 2026-08-04 | **Spec**: `./spec.md`
**Input**: `./spec.md` (re-specified after the post-specify squad — see `./analysis-report.md`)

## Summary

Delete `batch_sync` and `sync_all_queued_events` from `src/specify_cli/sync/batch.py` together with the
private helpers that exist only to serve them, remove the now-inert `E15` egress-allowlist entry, and
clean the autouse fixture that blinded the `tests/sync` cone to the gate those senders carried. No
behaviour change on any live path: the senders have no production caller.

### The manifest is a script, not a paragraph

**REVISED 2026-08-04 after the post-plan squad.** The first version of this table was derived with
`git grep -w <bare name>` and got two buckets wrong **in opposite directions**, because a bare grep
cannot distinguish (a) a call from a mention in a comment or docstring, nor (b) this module's symbol
from a **different module's same-named symbol**. Concretely: `_sleep_before_final_sync_retry` was filed
as a deletion candidate although `batch.py:684,:700` call it on the live `run_final_sync_with_retries`
chain — deleting it would have broken a production daemon path — while `_current_team_slug` and
`_body_mentions_missing_private_team` were filed as production-alive on the strength of hits that are
**different symbols entirely** (`EventEmitter._current_team_slug` at `sync/emitter.py:870`;
`body_transport.py`'s own definition).

The remedy is `scripts/verify_batch_retirement_3167.py` — a committed, re-runnable closure that resolves references
**module-qualified** (including the relative `from .batch import` form that sibling modules use) and
classifies every external reference as `CODE` / `STR-TARGET` / `PROSE`. Two implementers running it get
the same set. Its own diagnostic is controlled: `run_final_sync_with_retries`, `BatchEventResult`,
`BatchSyncResult` must resolve to `sync/background.py` and `categorize_error` to `sync/diagnose.py`; if
they come back with no production reference, the resolver is broken rather than the code being dead.

```
$ .venv/bin/python scripts/verify_batch_retirement_3167.py
TOTALS  dead=33 (first=24 second=9)  alive=21
code-coupled test files: 7      prose-only test files: 19
```

| Quantity | Value | How |
|---|---|---|
| Production callers of the two senders | **0** | 3 matches outside `batch.py`, all comments (`sync/__init__.py:61`, `background.py:494`, `:580`) |
| Dynamic reachability | **none found** | sole entry point `spec-kitty = "specify_cli:main"` (`pyproject.toml:131`); zero `getattr`/`import_module` on either name |
| Declared symbols in `batch.py` | **54** | 43 callables/classes + 11 constants, AST-enumerated |
| **First tier — delete now** | **24** | no external reference of any kind |
| **Second tier — dead in `src/`, held only by tests** | **9** | incl. `_current_team_slug`, `_is_checkout_sync_enabled_for_batch`, `_parse_error_response`, `_parse_event_results`, `_shrink_events_for_retry`, and the two `*_DECOMPRESSED_BYTES_*` constants |
| **Alive — must survive** | **21** | the whole `run_final_sync_with_retries` final-sync chain (incl. `_sleep_before_final_sync_retry`), both result classes, and the four API-alive report helpers |
| Test files **code-coupled** to a dead symbol | **7** | real work |
| Test files referencing one only **in prose** | **19** | no code work; correct the prose where it misleads |

**Also dead and not covered by the first attempt:** module constants and module-level imports. The
closure now enumerates constants; `ruff` F401 will surface the orphaned imports (`gzip`, `requests`,
`urlparse`, `OfflineQueue`, `batch_partition`, `validate_outbound_payload` and others).

The spec's edge case governs the second tier: *"A retained helper turns out to be reachable only from a
deleted sender → it is dead too; enumerate and state it rather than leaving an orphan."*

## Technical Context

**Language/Version**: Python 3.11 (`requires-python = ">=3.11"`); venv is 3.11.15
**Primary Dependencies**: none added or removed. This is a deletion.
**Storage**: none touched. **No schema change** — the `queue` table (`sync/queue.py:651`) is not modified;
per spec `C-003` in the previous draft and confirmed here, identity/schema work is a separate mission.
**Testing**: `.venv/bin/python -m pytest`, pytest 9.0.3, `pytest-timeout` + `xdist` present only in that
venv. Sweeps redirected to a file with the `N passed` line quoted; `-ra` so `^ERROR ` lines are actually
emitted (the squad found `-rf` suppresses them, making the standing `grep -c '^ERROR '` return 0 on a
run with 5 errors).
**Target Platform**: Linux (CI also runs Windows; nothing here is platform-specific)
**Project Type**: single project
**Performance Goals**: N/A — deletion. The only performance-adjacent note: omitting `--cov` roughly
halves the sync shard's wall time, which is how a run that was not the intended selection is spotted.
**Constraints**: `tests/sync` and `tests/cli` must never sweep concurrently. **This mission sweeps only
`tests/sync` and `tests/architectural`** — the `tests/cli` file once thought affected is prose-only, so
the second cone is not opened and that hazard is not engaged.
**Scale/Scope**: 1 production file modified, 1 architectural allowlist entry + 1 ratchet baseline count
corrected, 1 test fixture seam removed, **33 symbols** deleted across two tiers plus orphaned imports,
**7** code-coupled test files dispositioned at node-id granularity (~126 nodes, of which ~82 sit inside
files that survive as splits), 19 prose-only references corrected where misleading.

## Charter Check

*GATE: passed. Re-checked after the concern map below.*

| Charter requirement | Status | Note |
|---|---|---|
| Single canonical authority | **Pass, and advanced** | Removes a second, ungated sender for a question the live drain already answers on the declared seam. |
| Architectural alignment | **Pass** | Discharges the recorded precondition at `sync/emitter.py:2441-2443` by removing the thing that could be restored. Requires removing the `E15` allowlist entry, whose own suite reds on an inert entry. |
| ATDD-first / red-first (C-011) | **Pass, with a stated exception register** | `spec.md`'s register enumerates which requirements can be red-first and which are already true at baseline and therefore land as regression guards. Deletion-absence assertions are genuinely red-before/green-after. |
| Tests for new functionality (DIR-005) | **Pass** | No new functionality. New assertions are absence and non-regression. |
| Pre-existing failure reporting (DIR-013) | **Pass** | Baseline committed in `analysis-report.md` §4: 2376 passed / 19 skipped / 5 errors, input 2395, zero `FAILED`, all 5 leak-guard teardown errors, none attributable. |
| Terminology Canon | **Pass, and advanced** | IC-05 disambiguates "the drain", the overload that caused this mission's own false finding. |
| Complexity ceiling 15 | **N/A** | No function gains complexity; 33 symbols are removed. |
| `__all__` convention (C-007) | **Check in IC-01** | The senders are already absent from `specify_cli.sync`'s lazy map, so the public API must not change at all. |
| Dead-symbol gate | **Does NOT apply — corrected** | `tests/architectural/test_no_dead_symbols.py` keys on modules declaring `__all__`; `sync/batch.py` declares none, so **nothing reds on stranded privates**. The previous plan cited this as the forcing function for the second tier and was wrong. The second tier is justified on charter single-authority grounds plus the committed manifest, and the mission lands its own per-name absence assertion. The golden-count ratchet lives in `test_golden_count_ban.py`, not that file. |
| Ratchet baselines | **Check in IC-05** | `tests/architectural/_baselines.yaml:385` `egress_allowlist_files: 28` → **27**. The ratchet is shrink-only, so a stale count reds nothing and silently leaves the ceiling one higher than reality. |

## Project Structure

### Documentation (this mission)

```
kitty-specs/chain-b-consent-bypass-3167-01KZ63HK/
├── spec.md                     # re-specified: retirement
├── research.md                 # Phase 0, with two wrong findings marked inline
├── analysis-report.md          # squad findings, adjudication, committed baseline
├── data-model.md               # entity/seam map (retained; its gate inventory is still accurate)
├── plan.md                     # this file
├── issue-matrix.json           # rows for #3167, #3030, #3130
├── research/
│   ├── evidence-log.csv
│   └── source-register.csv
├── contracts/                  # IC-01's deletion manifest lands here
└── tasks/                      # Phase 2
```

### Source Code (repository root)

```
src/specify_cli/sync/
├── batch.py            # THE deletion: 2 senders + 18 first-tier + up to 8 second-tier helpers
├── runtime.py          # comment only at :106 (C-001) — no behaviour change
├── consent.py          # NOT touched (its write-on-read defect is filed, not fixed here)
└── __init__.py         # verify the public API is unchanged; the senders were already absent

tests/
├── sync/
│   ├── conftest.py                              # the blinding autouse fixture at :221
│   ├── test_batch_sync.py                       # largest consumer of the dead senders
│   ├── test_batch_error_surfacing.py
│   ├── test_batch_retry_hygiene.py
│   ├── test_batch_400_no_details_poison_2736.py
│   ├── test_integration.py
│   ├── test_offline_replay.py
│   ├── test_issue_598_hang_fixes.py
│   └── test_no_queue_drain_constructed_3030.py  # MUST still pass; never weakened (NFR-004)
├── architectural/
│   ├── test_egress_consent_boundary.py          # remove the E15 entry
│   ├── test_batch_split_single_authority.py     # tests a second-tier helper
│   └── test_no_dead_symbols.py                  # the gate that forces the second tier
```

**Structure Decision**: single project, no new modules, no new packages. The only structural change is
subtractive.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| ~~The mission sweeps two mutually-exclusive test cones~~ **WITHDRAWN** | — | The justification was `tests/cli/commands/test_sync_now_empty_selection_t005.py`, whose only tie is a **docstring sentence** — it imports nothing from `sync.batch`. All 7 code-coupled test files are in `tests/sync` and `tests/architectural`. **The mission does not need to sweep `tests/cli`**, so C-003's hazard is not engaged and no second cone is opened. |
| The mission opens `tests/architectural/` | The `E15` allowlist entry goes inert on deletion and its own consistency suite reds on an inert entry; and one code-coupled test (`test_batch_split_single_authority.py`) lives there | Leaving the entry is not available: `test_every_listed_file_still_holds_a_sink` reds on an entry holding no transmit primitive. This adds M5a to cross-mission hazard **H4** and requires landing before M1's architectural window. |
| The `E15` removal and the first-tier deletion must be **one atomic commit** | The two allowlist assertions are bidirectionally coupled: `test_no_unlisted_file_holds_an_egress_sink` reds if `E15` goes while any sink remains, and `test_every_listed_file_still_holds_a_sink` reds if `E15` survives after the sinks go | A commit boundary between them is red in one direction or the other. `batch.py`'s three transmit primitives (`requests.get` at `:223`, `requests.post` at `:1125`, `request_with_stdlib_fallback_sync` at `:1212,:1282`) are all inside first-tier symbols, so a *complete* first-tier deletion leaves zero — but a partial one does not. **Partial deletion is not a valid intermediate state.** |

## Implementation Concern Map

> Concerns are not work packages. `tasks` translates these into executable WPs.


**REVISED after the post-plan squad.** Three structural corrections: the old IC-02 and IC-03 are
**merged** (there is no green intermediate state between retiring the tests and deleting the code — the
moment the senders go, the code-coupled tests break at import, and if the tests go first the source
still references nothing removed); the enforcing gate previously cited for the second tier **does not
apply** to this file; and the disposition unit is the **node id**, not the file.

### IC-01 — Freeze the deletion manifest

- **Purpose**: make the deletion reviewable against a committed, re-runnable artifact instead of a
  re-derived argument.
- **Relevant requirements**: FR-002, NFR-001, NFR-002
- **Affected surfaces**: `scripts/verify_batch_retirement_3167.py` (committed), `contracts/deletion-manifest.md` (its
  output, frozen); read-only over `src/specify_cli/sync/batch.py`, `sync/__init__.py`, `pyproject.toml`
- **Sequencing/depends-on**: none — first
- **Risks**: the closure must be **diagnostic-controlled** — if `run_final_sync_with_retries`,
  `BatchEventResult`, `BatchSyncResult` do not resolve to `sync/background.py` and `categorize_error` to
  `sync/diagnose.py`, the resolver is broken, not the code dead. That control is what caught the
  relative-import bug. **NFR-001 needs a definition, not just a number**: "senders" = top-level symbols
  in `batch.py` from which a `requests.*` or `request_with_stdlib_fallback_sync` call is transitively
  reachable. Baseline count is computed by the same script; SC-001 prints both numbers.

### IC-02 — Retire the dead surface and its coverage, atomically

- **Purpose**: delete the 24 first-tier symbols, the 9 second-tier symbols, the orphaned imports and
  constants, **and** the test nodes that only covered them — in one commit, because no intermediate
  state is green.
- **Relevant requirements**: FR-001, FR-003, FR-004, NFR-001, NFR-002, SC-004
- **Affected surfaces**: `src/specify_cli/sync/batch.py`; the **7 code-coupled** test files —
  `tests/sync/test_batch_sync.py`, `test_batch_error_surfacing.py`, `test_batch_retry_hygiene.py`,
  `test_batch_400_no_details_poison_2736.py`, `test_integration.py`, `test_offline_replay.py`, and
  `tests/architectural/test_batch_split_single_authority.py`
- **Sequencing/depends-on**: IC-01
- **Risks — this is the mission's sharp edge.** Five of the seven files need a **SPLIT**, not a
  retirement; whole-file deletion is the coverage-loss event:

  | File | Shape | Must survive |
  |---|---|---|
  | `test_batch_sync.py` (1489 lines, 40 tests, 46 refs) | **split**, ~37 retire | `TestBatchSyncResult` (2 nodes) and `test_oversized_batch_error_classifies_without_unknown` — they cover the retained `BatchSyncResult` and `categorize_error` |
  | `test_batch_error_surfacing.py` (54 nodes) | **split**, ~26 retire | ~28 nodes: `TestCategorizeError`, `TestFormatSyncSummary`, `TestFailureReport`, `TestProcessBatchResults`, `TestBatchSyncResultProperties`, `TestBatchEventResult` — all on production-alive surface |
  | `test_integration.py` | **split**, 7 retire | `TestLamportClockReconciliation` (2) — pure `sync.clock` |
  | `test_offline_replay.py` | **split**, ~11 retire | `TestQueueEventsOffline` (2) + `TestQueueSizeLimit` (2) — pure `OfflineQueue`, which stays live |
  | `test_batch_split_single_authority.py` | **split** | **T018's AST single-authority sweep plus its non-vacuity control must survive verbatim** — it pins `owner/repo#2755` across all of `src/`, independently of `batch.py`. Only T017 retires. |
  | `test_batch_retry_hygiene.py` (6 nodes) | **retire whole** | name the survivor: `tests/delivery/test_ledger.py::test_batch_transient_does_not_flip_per_event_rejection` |
  | `test_batch_400_no_details_poison_2736.py` (2 nodes) | **retire whole** | name the survivor: `tests/delivery/test_poison_batch_2736.py`; **first confirm** `tests/delivery/test_receivers.py` actually pins the 400-*with*-details branch |

  Per operator decision, **`core/batch_partition.py::split_in_half` is kept** as a zero-consumer
  canonical leaf and a follow-up is filed; it is not folded into this deletion.
  **Requirement-bearing nodes needing an explicit verdict, not bulk retirement:**
  `TestHistoricalMissionStateGuard` (`test_batch_sync.py:173`) — the per-event forbidden-key check
  exists nowhere else; the live analogue `enforce_teamspace_mission_state_ready` is entry-time and a
  daemon dispatch does not traverse it. State whether the per-event check is still owed and **file the
  gap if it is**. The 4 ingress tests at `test_batch_sync.py:1305-1413` pin per-batch `/me` rehydrate
  and negative-cache behaviour reachable only through `batch_sync`; if the claim is "covered at
  `body_transport.py`", that claim must be checked, not asserted.
- **Correction to the previous plan**: `tests/architectural/test_no_dead_symbols.py` was cited as the
  gate forcing the second tier. It is not — it keys on modules declaring `__all__`, and `batch.py`
  declares none. The golden-count ratchet is `tests/architectural/test_golden_count_ban.py`, not that
  file. So **nothing reds on stranded privates**: the second tier is justified on charter
  single-authority grounds and by the committed manifest, and the mission lands its own per-name
  absence assertion rather than leaning on a gate that does not fire.

### IC-03 — Unblind the cone

- **Purpose**: stop the autouse fixture patching a name production no longer consults, and make a
  mis-targeted patch loud.
- **Relevant requirements**: FR-005, FR-006, SC-005
- **Affected surfaces**: `tests/sync/conftest.py:278-283` **only**
- **Sequencing/depends-on**: IC-02
- **Risks**: the fixture makes **three** patches, not one. Remove the `specify_cli.sync.batch.…` seam;
  the `specify_cli.sync.runtime.…` seam stays (C-001 keeps `runtime.py:106`, and `runtime.py:37` imports
  the name, so dropping its `raising=False` resolves rather than errors). **`EventEmitter._project_consents_to_capture`
  at `:284-287` is explicitly OUT OF SCOPE** — it is the grant the cone actually depends on, and FR-006
  must not be read as licence over the whole block. The fixture is autouse over ~106 files, not the 20
  previously stated, and removing the `batch` seam is a **behavioural no-op** for all of them. SC-005
  as written proves *resolvability*, not *consultation*: satisfy it with a negative-control test showing
  a wrong patch target reds.

### IC-04 — Measure and attribute

- **Purpose**: verify the `tests/sync` and `tests/architectural` cones against the committed baseline,
  attributing every difference.
- **Relevant requirements**: NFR-003, NFR-004, SC-003, SC-006
- **Affected surfaces**: no source; sweeps plus a committed comparison artifact
- **Sequencing/depends-on**: IC-03
- **Risks**: ~126 test nodes disappear, so a per-node-id comparison must distinguish **absent** from
  **present-but-flipped** — only the latter is interesting, and a bulk sentence hides it. Cheap honest
  shape: capture `--collect-only -q` node lists pre/post (~2 min, catches every collection-level change),
  iterate on the 7 coupled files plus `test_no_dead_symbols.py` and `test_egress_consent_boundary.py`,
  and run the full `-n0 -ra` cone **once** at the end (~215 s). `-ra` not `-rf`, so `^ERROR ` lines are
  actually emitted. `pgrep -af 'run_sync[_]daemon'` before each measurement; reaps in a **script file**
  with the bracket class in `pgrep` form too. `--dist loadfile` only if parallelising, never bare
  `--dist load`. **NFR-004 is not a baseline property and must not be filed as a regression guard**: once
  the names no longer exist, `test_no_queue_drain_constructed_3030.py` passes *vacuously*. Add the
  positive control its sibling already has — a synthetic source string containing
  `from .batch import batch_sync` that the scanner must still flag — and remove the now-vacuous
  `_DEFINING_MODULE` self-exclusion. **That**, not the deletion, is the strengthening NFR-004 promises.
  Expect the leak-guard observation set to move; attribute per node id, and if a pinned leak stops
  reproducing *as a consequence*, un-pin it and record the attribution (C-004/C-005) rather than leaving
  a pin the guard reds on.

### IC-05 — Correct the record

- **Purpose**: remove the inert `E15` allowance and its stale baseline count, annotate the auto-start
  boundary, and disambiguate "the drain".
- **Relevant requirements**: FR-007, FR-008, FR-009, SC-007
- **Affected surfaces**: `tests/architectural/test_egress_consent_boundary.py:577-586`;
  `tests/architectural/_baselines.yaml:385`; `src/specify_cli/sync/runtime.py:106`;
  `docs/context/` glossary; prose in `batch.py` and `runtime.py`
- **Sequencing/depends-on**: the `E15` removal is **part of IC-02's atomic commit**, not a later step
  (see Complexity Tracking). The rest is independent.
- **Corrected after the WP01 review**: this concern previously named `sync/__init__.py` as in-scope prose,
  but **no work package owns that file**, so whoever touched it would be editing outside their declared
  write scope. It is therefore **out of scope** — consistent with the operator's FR-009 decision to limit
  in-place naming to files this mission already opens — and it joins the FR-009 residual filed in T019.
- **Risks**: `_baselines.yaml:385` `egress_allowlist_files: 28` must go to **27**, with its
  justification prose updated (12 + 1 + 14 = 27). The ratchet is shrink-only — growth fails, shrinkage
  merely warns — so leaving it stale **reds nothing** and silently keeps the ceiling one higher than
  reality, i.e. one free future unconsented-egress file. Per operator decision, **FR-009 is scoped to a
  glossary entry plus in-place naming only in files this mission already opens**; the other 13 files
  (`emitter.py` alone has 11 occurrences) are declared out of scope and filed. The `runtime.py:106`
  comment must **not** claim the publish gate covers every path — a started runtime emits a `build_id`
  in a `pong` that gate never sees, classified not-project-data at
  `test_egress_consent_boundary.py:567-575`. Point at that per-sender enumeration.

### IC-06 — Close the tracker honestly

- **Purpose**: disposition `#3167` and file the residuals as issues rather than absorbing them.
- **Relevant requirements**: FR-010, SC-008
- **Affected surfaces**: `issue-matrix.json`; GitHub issues
- **Sequencing/depends-on**: IC-01 for the evidence
- **Risks**: `#3167`'s row is `in-mission`, which is **rejected on the `done` transition** — it must
  reach a terminal verdict. A `deferred-with-followup` verdict is only honest once the follow-up issue
  actually exists. The register is **8** residuals to FILE: the register's six *File* rows (row 7, revocation-between-selection-and-POST, is dispositioned **Fold** and must NOT be filed) plus `split_in_half`'s
  zero-consumer status and FR-009's 13 out-of-scope files. Cite foreign issues as `owner/repo#NNNN`,
  this mission's own bare, per the carve-out the squad forced.
