---
affected_files: []
cycle_number: 3
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-09T19:46:54Z'
reviewer_agent: user
wp_id: WP01
---

---
affected_files:
- tests/architectural/test_project_store_boundary.py
- tests/architectural/test_sync_writer_census.py
- tests/architectural/test_egress_consent_boundary.py
- tests/sync/test_project_consent_incident_baseline.py
cycle_number: 2
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command: PYTHONPATH=src .venv/bin/python '<independent collector mutant script recorded below>'
reviewed_at: '2026-08-09T19:46:00Z'
reviewer_agent: codex-core-wp01-review
wp_id: WP01
---

# WP01 Review Cycle 2 — Changes Requested

## Closure of cycle-1 findings

The reroll closes the path/ADR, live-control, typing, and reproducibility portions
of cycle 1:

- The ADR and fixture now pin
  `<runtime-root>/projects/<lowercase-hyphenated-uuid>/sync/sync.db` and the
  sibling `egress.lock`, and accurately state the narrow #3030 supersession.
- The positive controls now drive production `EventJournal`,
  `TeamspaceReceiver`, and `SqliteDeliveryLedger` paths.
- The exact four-file mypy command reports zero issues; Ruff check and format
  pass.
- With the corrected filename
  `tests/specify_cli/sync/test_local_commit_consent_3030.py`, the recorded
  warning-strict command independently reproduces `337 passed, 2 xfailed`.

The architecture-census portion of cycle-1 finding 3 is not closed. The new
collectors are more substantial, but executable counterexamples still bypass or
falsely trigger them.

## Blocking findings

### 1. SQLite alias and reachability classification are still not sound

`_StoreVisitor` recognizes module aliases (`import sqlite3 as _db`) and direct
import aliases, but not a constructor bound through an assignment. This real
collector specimen produces zero sites:

```python
import sqlite3
open_sync = sqlite3.connect

def live(path):
    return open_sync(path)
```

The reachability classifier is also not symbol-specific. It counts every call in
`src/` with the same tail name. An otherwise unreferenced mutant named `append`
was classified `LIVE_PAYLOAD_CONTROL` because the repository contains 3,370
unrelated calls whose attribute tail is `append`. The test only requires that
*some* current site be classified `DEAD_CODE`; it does not prove the individual
classification or reject this false live result.

Remediation: resolve constructor bindings through assignment/import aliases and
test that form through `scan_store_sites`. Replace global tail-name counts with
module/class-qualified call edges or another site-specific reachability proof.
Add both a dead function with a common method name and a live qualified caller as
opposite controls. Keep the now-correct per-call read-only validation.

### 2. The grant collector has both a false negative and a false positive

The semantic matcher recognizes keyword, mapping, and subscript shapes, but an
ordinary attribute persistence path is invisible:

```python
def remember(record, answer):
    record.granted = answer
```

Conversely, an unrelated API call is reported as a grant merely because it uses
the generic keyword `enabled`:

```python
def set_widget_mode(widget):
    return widget.configure(enabled=True)
```

The default scan is also restricted to four hand-picked files. A newly added
grant function in another `specify_cli/sync/` module is absent unless the test
author explicitly passes its path. Finally, `_call_targets` falls back to short
names across files/classes, so unrelated same-named functions can create false
call edges and mask the real authority graph.

Remediation: scan the hosted-sync source scope rather than a fixed four-file
tuple; recognize assignment/persistence through attributes and relevant update
forms; qualify call edges by resolved module/class binding; and distinguish
consent models/writers from unrelated `enabled` fields. Add independent
false-positive and false-negative mutants through the same default collector the
ratchet test invokes.

### 3. The sender and layout gates can be bypassed by file placement and control-flow masking

`_PROJECT_SENDER_FILES` is derived from the hard-coded sender matrix, so
`_scan_project_sinks()` never scans a newly added file. A POST in
`specify_cli/sync/brand_new_sender.py` is discovered only when its path is passed
explicitly; the production ratchet's default roots do not include it. This does
not meet T004's requirement that a newly added HTTP/requests/WebSocket project
write turn the gate red without first editing the inventory.

For files that are scanned, `canonical_attempt` is one function-wide boolean. The
following unconditional POST is accepted because the three required call names
occur anywhere in the function; no control-flow or data-flow relation to the sink
is required:

```python
def bypass(client, payload):
    ProjectSyncContext(payload["project_uuid"])
    DeliveryAttempt(payload)
    final_transport_eligible(payload)
    client.post("/events", json=payload)
```

The layout collector has the analogous syntax-only gap. A current writer whose
SQL is assembled with `"".join(("INS", "ERT INTO ..."))` produces no
`_LayoutWriteSite`. Its mutation test covers only a literal SQL string. Result
rows are improved, but the matrix still verifies a named result function only
exists; it does not prove that the named durable rows perform a result write.

Remediation: scan the whole hosted project-sender/current-writer scope by default;
bind every sink to its dominating final check and the same immutable context and
attempt; cover HTTPX/requests/WebSocket aliases; and make layout discovery robust
to the SQL construction forms actually permitted by the codebase (or guard the
write API structurally instead of attempting partial SQL evaluation). Mutants
must be placed in otherwise unseen files and must include decoy checks, alias
transports, and non-literal SQL. Validate result sites semantically, not by
function existence.

### 4. The reusable mutation harness itself accepts complexity-masked incident regressions

`mutation_violations()` checks for vocabulary anywhere in the specimen, not that
the relevant value controls the relevant operation. Both of these regressions
return no violations:

```python
def path(root, project_uuid):
    audit(project_uuid)
    return root / "sync.db"
```

```python
def send(client, body):
    final_transport_eligible(body)
    client.post(body)
```

The first restores a shared resolver while merely mentioning the UUID; the
second performs an unconditional transmit after an ignored check result. These
are direct false-clean results for two of T005's four required mutation classes.

Remediation: make the resolver detector prove that the UUID participates in the
returned canonical path, and make the transport detector prove that the final
eligibility result dominates/guards the sink. Add decoy-use and ignored-result
mutants as required bite tests. Apply equivalent relation-aware checks to the
cross-pair detector so later WPs cannot satisfy it with incidental vocabulary.

## Independent verification

- Corrected full warning-strict #3030/WP01 command: `337 passed, 2 xfailed`.
- Four WP files, warning-strict: `49 passed, 2 xfailed`.
- Documentation metadata gates: `677 passed`.
- Named lifecycle pre-review regression: `1 passed`; the existing #3130/#3237
  leak remains explicitly pinned by its owning guard.
- Strict focused mypy: `Success: no issues found in 4 source files`.
- Ruff check: `All checks passed`; Ruff format: `4 files already formatted`.
- `git diff --check`: pass.

## WP-level anti-pattern checklist

1. **Dead code — FAIL**: reachability is inferred from unrelated tail-name calls;
   the dead `append` mutant is labeled live.
2. **Synthetic-fixture test — FAIL**: live production positive controls are now
   sound, but the required mutation proof is false-clean under decoy vocabulary.
3. **Silent empty return — N/A**: no production path was added.
4. **FR coverage — FAIL**: FR-023/FR-026/FR-029 architecture guards admit the
   executable grant/store/sender/writer counterexamples above.
5. **Frozen surface — PASS**: no contract or production source was modified.
6. **Locked decision — PASS**: the ADR now matches the store-layout contract and
   final #3030 supersession ruling.
7. **Shared-file ownership — PASS**: all changed files are declared WP01-owned;
   no shared lane is recorded.
8. **Production fragility — N/A**: no production raise or handler path was added.

## Downstream impact

WP02 remains blocked on WP01. Do not claim the dependent package until the
default collectors, reachability proof, and mutation harness are independently
bite-tested against these counterexamples and WP01 is approved.
