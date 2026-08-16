---
affected_files: []
cycle_number: 1
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-09T18:57:18Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Review Cycle 1 — Changes Requested

## Blocking findings

### 1. The ADR and reusable fixture contradict the canonical store-layout contract

`contracts/project-sync-store-layout.md:12` pins the concrete output as
`<runtime-root>/projects/<lowercase-hyphenated-uuid>/sync/sync.db`. The ADR instead
declares `<runtime-root>/projects/<project-uuid>/sync.db`
(`docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md:47-53`), and
`IncidentProject.planned_store_path()` repeats that incompatible shape
(`tests/sync/test_project_consent_incident_baseline.py:35-37`). This fails the
mandatory contract round-trip check and would hand WP02 the wrong path.

Remediation: make the ADR and fixture use the contract's exact `/sync/sync.db`
shape, and add an assertion over the complete expected path (not only `A != B`).
Keep the sibling `egress.lock` relationship consistent with the same contract.

### 2. The evidence harness positive controls are synthetic, not live-path evidence

`test_store_open_and_exact_byte_spies_have_same_path_positive_controls()` calls
`sqlite3.connect()` and `ExactByteTransportSpy` directly
(`tests/sync/test_project_consent_incident_baseline.py:193-208`). The differential
counter test likewise increments the counter directly (`:211-218`). These tests
still pass if every production journal, queue, dispatcher, and sender path is
deleted, so they do not satisfy T005's requirement that each spy/counter observe
an ordinary current write on the same production path.

Remediation: drive representative existing public entry points through the real
current journal/layout, sender/transport, and result-write seams while the probes
are installed. Assert the exact opened path/bytes and the A/B differential from
those production calls. Keep synthetic specimens for detector self-tests, but do
not use them as the positive-control evidence.

### 3. The architecture censuses can pass while missing the regressions they claim to guard

Several independent holes make the current gates vacuous:

- `_StoreVisitor` recognizes only `sqlite3.connect` and a bare `connect`. It misses
  aliased constructors such as `_sqlite3.connect`; the scoped run proves this by
  warning that three still-live, unchanged symbols disappeared from the census
  (`_count_legacy_body_uploads_for_mission`, `_emit_status_check_json`, and
  `status`). A shrink warning is not valid when the code did not shrink.
- `classify_store_site()` has no path that can return `DEAD_CODE`, and every scanned
  `specify_cli/` site falls through to `LIVE_PAYLOAD_CONTROL`. Therefore
  `assert ... is not SiteCategory.DEAD_CODE` is true by construction rather than a
  reachability classification (`test_project_store_boundary.py:137-154,292-304`).
- `final_project_store_violations()` permits every method whose qualname merely
  starts with `ProjectSyncStore`, and permits every migration connection if the
  file contains `mode=ro` or `immutable=1` anywhere. A writable second connection
  in that file would be silently blessed (`:274-289`).
- The consent census only recognizes calls whose callee already has one of eight
  hard-coded names. `_GRANT_INPUT_CENSUS` and `_NON_GRANT_INPUTS` are literals
  asserted against literals, not a census of callable grant-return/persistence
  paths (`test_sync_writer_census.py:24-34,125-159,196-213`). A differently named
  function returning `ConsentDecision(granted=True)` or persisting `enabled=True`
  is invisible.
- The sender and layout inventories only assert that two hard-coded sets contain
  symbols that exist. `_attempt_context_violations()` is run only on in-memory
  snippets, never on the production scan. Consequently a new current writer, or a
  new sink in an already allowlisted sender file without
  `ProjectSyncContext`/`DeliveryAttempt`/final recheck, does not fail these new
  tests (`test_egress_consent_boundary.py:1425-1524`). Some alleged result sites
  are not result writes at all; for example
  `SaasClient._refuse_unless_project_consents` is a pre-I/O refusal check.

Remediation: make each census discover the relevant source-tree occurrence class,
classify every discovered site with reachability and owning-WP evidence, and add
negative mutations through the real collection path. Detect import aliases and
connection constructors; validate read-only mode per connection site; bind final
allowances to the exact `unit_of_work`/migration contract; discover grant-return
and persistence shapes; and map each sender to an actual request-start and durable
result-write site. A newly added real writer/sender/grant path must make the gate
red without first editing the expected set.

### 4. The ADR misstates the #3030 decision that this mission supersedes

The ADR says #3030 "allowed unconditional local capture" and that this principle
remains (`docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md:145-151`). The
final #3030 specification says the opposite: FR-002 denies unconsented capture,
NFR-005 was amended to require write-path gating, and C-006 states that a
non-consenting project's events never reach the journal
(`kitty-specs/journal-project-consent-3030-01KYKWQS/spec.md:232,259,272`). WP01
explicitly requires the new ADR to record this narrow supersession.

Remediation: state that this mission supersedes #3030's final consent-gated
capture decision by allowing local capture only into the UUID-owned store with
sealed epochs, while preserving #3030's egress defenses. Use the mission's
canonical "Human-in-Charge" term in the scope exclusion.

### 5. The declared strict type gate fails

The charter requires new code to pass strict mypy. The focused command

```text
.venv/bin/mypy tests/architectural/test_project_store_boundary.py tests/architectural/test_sync_writer_census.py tests/sync/test_project_consent_incident_baseline.py tests/architectural/test_egress_consent_boundary.py
```

fails with six errors: incompatible `visit_AsyncFunctionDef` assignments in
three visitors, `AST.lineno`, an `Any` return from the SQLite spy, and
`ast.walk(expr | None)`.

Remediation: fix the typing without blanket suppressions and rerun the focused
mypy command to zero errors.

### 6. The review evidence is not reproducible from the transition note

The transition note reports `337 passed, 2 expected xfailed` but records no exact
pytest command. The closest contract-derived reconstruction (the new files,
egress boundary, and every `consent*3030.py` suite) produced `334 passed, 2
xfailed, 1 warning`; the warning is the real census miss described above. The
pre-review gate also recorded `no_coverage` because pytest was not importable in
that gate environment.

Remediation: record exact base/final commands and outputs. The final scoped run
must be warning-free except for the two explicitly documented #3113 xfails, and
the pre-review coverage gate must run in an environment where its authorities are
available. Preserve the red/green commit trail, but make every reported count
independently reproducible.

## WP-level anti-pattern checklist

1. **Dead code — N/A for production / FAIL for census proof**: no production code
   was added, but the dead-code classification branch is unreachable.
2. **Synthetic-fixture test — FAIL**: the required positive controls invoke only
   test helpers and literals, not production paths.
3. **Silent empty return — N/A**: no production path was added.
4. **FR coverage — FAIL**: the static/literal checks do not exercise the live
   architecture behaviors named by the WP's requirement references.
5. **Frozen surface — PASS**: no mission contract or declared frozen source was
   modified by the WP diff.
6. **Locked decision — FAIL**: the ADR and fixture contradict the exact canonical
   layout and the final #3030 capture decision.
7. **Shared-file ownership — PASS**: the changed files are declared WP01-owned and
   the lane topology reports no shared lane.
8. **Production fragility — N/A**: no production `raise` or handler path was added.

## Downstream impact

WP02 depends on WP01. Do not claim WP02 against this evidence package. If a WP02
workspace has already been allocated, rebase/recreate it after WP01 is corrected,
re-reviewed, and approved so it receives the corrected path contract and census
APIs.
