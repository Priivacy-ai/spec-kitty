---
affected_files: []
cycle_number: 4
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-09T20:32:21Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Cycle-3 Independent Review — Changes Requested

## What this reroll closes

The five exact cycle-2 bite specimens now fail through the collectors' default
temporary-source roots:

- assigned and transitively assigned SQLite constructor aliases are discovered;
- an unreferenced common-name function is dead while a qualified imported caller
  makes its target live;
- an unseen grant module exposes attribute and mapping-update persistence without
  treating the exact unrelated `widget.configure(enabled=True)` specimen as a
  grant;
- unseen and aliased HTTP senders with the prior ignored-check decoy are
  violations, and join-built SQL is discovered;
- an empty named result function is rejected, and the exact UUID-decoy,
  ignored-final-gate, and unrelated-context cross-pair specimens are rejected.

The earlier ADR, exact layout/lock, #3030 wording, live EventJournal/receiver/
ledger controls, typing, lint, and reproducibility closures also remain green.

The implementation is nevertheless not approvable. The new relation-aware
collectors still misclassify the production tree and accept executable
complexity-masked variants of the same incident boundaries.

## Blocking findings

### 1. Qualified reachability labels most live production store owners as dead

`_qualified_call_counts()` resolves module functions and direct constructors,
but it does not resolve ordinary instance-method calls such as
`journal.append(...)`, `ledger.record_success(...)`, or `queue.queue_event(...)`.
The current production scan therefore reports 64 `dead-code` sites. These include
the production paths exercised by WP01's own live controls:

- `EventJournal.append` and `EventJournal._connect`;
- `SqliteDeliveryLedger._record` and its transaction/constructor sites;
- `SqliteDeliveryTargetRegistry` writers;
- most `OfflineQueue` and `OfflineBodyUploadQueue` writers.

This directly contradicts T002's requirement to classify each occurrence and
the review instruction to trace live offenders from public entry points. The
ratchet only asserts that *some* disposition is dead and never verifies that its
known live floor is classified live, so the false-dead majority remains green.

Remediation: resolve receiver types and `self`/instance method edges sufficiently
to classify every current offender, or attach explicit, executable public-entry
evidence per qualified symbol. Assert every `_KNOWN_LIVE_FLOOR` item is live and
add representative instance-method reachability controls for journal, ledger,
target, queue, and body queue. Do not infer deletion ownership from a zero count
until that proof exists.

### 2. The store and grant collectors remain flow-insensitive and produce false positives/negatives

Constructor aliases are accumulated but never invalidated. This safe program is
reported as a direct SQLite open because `open_sync` remains in
`sqlite_constructors` after rebinding:

```python
import sqlite3

def safe(path):
    return path

open_sync = sqlite3.connect
open_sync = safe

def inspect(path):
    return open_sync(path)
```

The grant domain filter similarly depends on name tokens. An unrelated
`configure_project_sync_widget()` calling `widget.configure(enabled=True)` is
reported as consent authority merely because its qualname contains
`project_sync`. Conversely, `setattr(record, "granted", answer)` remains an
undiscovered grant persistence shape.

Remediation: make alias tracking scope- and order-aware, invalidating bindings on
reassignment. Bind grant fields to actual consent models/writers or typed/domain
receivers rather than qualname substrings, and cover `setattr`/equivalent allowed
persistence shapes. Add false-positive controls for rebinding and consent-named
non-authority helpers, plus false-negative controls through the default scan.

### 3. Sender, layout, and result semantics are still satisfied by incidental evidence

`_SinkFunctionAnalyzer` gathers aliases and bindings with `ast.walk()` before it
analyzes statement order. A network call through `wire = client.post` disappears
if `wire` is rebound to a safe function *after* the call. Its coherence test also
accepts the checked attempt anywhere in any request argument, so this foreign
payload is marked canonical merely because the attempt appears in an audit
header:

```python
context = ProjectSyncContext(payload["project_uuid"])
attempt = DeliveryAttempt(context, payload)
if final_transport_eligible(attempt):
    client.post(
        "/events",
        json=foreign_payload,
        headers={"X-Audit": str(attempt)},
    )
```

The layout fallback now turns every unresolved `execute(query)` into a `DYNAMIC`
writer. A dynamic `SELECT` read is therefore inventoried as a layout writer. This
avoids a write false negative by making unrelated reads false positives rather
than determining whether the operation mutates state.

The new result predicate is also syntactic rather than semantic. Independent
mutants show all of these false positives:

- `DURABLE`: executing `CREATE TEMP TABLE unrelated(x)`;
- `IN_MEMORY`: assigning `scratch = payload` and returning it;
- `DURABLE_FILE`: `json.dump(payload, stream)` where `stream` is not a durable
  result authority.

Remediation: analyze aliases in execution order; tie final eligibility to the
actual transmitted body/context rather than any ancillary argument; distinguish
unknown read operations from writes (or gate the mutation API instead of partial
SQL evaluation); and prove each named result site mutates the documented result
authority/table/file/state with the event/attempt identity. Add these exact
negative controls.

### 4. T005's relation checks still accept value-rebinding and decoy-data regressions

The exact previous decoys are fixed, but the predicates compare syntax/name
presence rather than stable values. All three specimens below return no
violations:

```python
def path(root, project_uuid):
    return root / "projects" / (audit(project_uuid), "shared")[1] / "sync" / "sync.db"
```

The UUID occurs in the returned component's syntax, but the actual owner is the
constant `shared`.

```python
def send(client, body, foreign):
    if final_transport_eligible(body):
        client.post(
            "/events",
            json=foreign,
            headers={"X-Audit": str(body)},
        )
```

The checked object is only incidental header data; different bytes are sent.

```python
project = a.uuid
context = ProjectSyncContext(project_uuid=project)
project = b.uuid
attempt = DeliveryAttempt(
    context=context,
    journal_uuid=project,
    target_uuid=project,
    ledger_uuid=project,
)
```

AST dumps of the identifier `project` match, but the context captured A before
the variable was rebound and the attempt pairs B.

Remediation: constrain accepted resolver components to a direct canonical UUID
normalization expression; model assignment/version order or reject mutable
indirection in coherent context construction; and bind the checked attempt's
payload identity to the actual HTTP/WebSocket body, excluding ancillary headers,
logging, and metadata. Add the three specimens above as bite tests.

## Independent verification

- Default-collector replay of every exact cycle-2 specimen: pass (each now bites
  as intended).
- Focused four-file warning-strict suite: `54 passed, 2 xfailed`.
- Full 22-path WP01/#3030 warning-strict suite: `342 passed, 2 xfailed`.
- Documentation metadata plus isolated lifecycle: `678 passed`; the lifecycle
  residual remains the accepted #3130/#3237 pin.
- Strict focused mypy: `Success: no issues found in 4 source files`.
- Ruff check: `All checks passed`; Ruff format: `4 files already formatted`.
- `git diff --check`: pass.

## WP-level anti-pattern checklist

1. **Dead code — FAIL**: 64 current sites are classified dead, including live
   journal, ledger, target, queue, and body paths.
2. **Synthetic-fixture test — FAIL**: live positive controls remain sound, but
   the required T005 detector returns false-clean for three relation-preserving
   syntax decoys with different runtime values/bytes.
3. **Silent empty return — N/A**: no production path was added.
4. **FR coverage — FAIL**: FR-023/FR-026/FR-029 enforcement admits or falsely
   reports the executable counterexamples above.
5. **Frozen surface — PASS**: no mission contract or production source changed.
6. **Locked decision — PASS**: ADR and exact project-store layout remain aligned.
7. **Shared-file ownership — PASS**: changed files are WP01-owned and the lane is
   not shared.
8. **Production fragility — N/A**: no production raise or handler was added.

## Downstream impact

WP02 remains blocked. Do not use the current dead/live dispositions, sender
coherence flag, result classification, or T005 relation predicates as downstream
proof until the false-dead production census and executable masks above are
closed and independently reviewed.
