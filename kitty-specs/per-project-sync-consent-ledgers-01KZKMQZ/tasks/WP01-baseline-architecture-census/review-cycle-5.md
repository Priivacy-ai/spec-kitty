---
affected_files: []
cycle_number: 5
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-09T21:07:34Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Cycle-4 Independent Review — Changes Requested

## What this reroll closes

The exact cycle-3 specimens now bite through the default collectors: the known
class-owned journal/ledger/target/queue/body floor is labeled live; the simple
SQLite alias rebind is excluded; `setattr(record, "granted", answer)` is found
while the consent-named widget remains excluded; the request-before-safe-rebind,
foreign-body/audit-header, project-name-rebind, join-built INSERT versus SELECT,
and all three previously supplied non-result-write specimens are rejected. The
tuple/header/rebound-owner T005 decoys also fail as required.

The earlier ADR, exact UUID layout and sibling lock, narrow #3030 supersession,
preserved consent/egress defenses, live EventJournal/receiver/ledger controls,
typing, lint, formatting, docs, lifecycle, and full #3030 regression closures
remain green.

The WP is still not approvable. Independent default-root counterexamples show
that the new analyzers continue to confuse incidental names/operations with
runtime relations, and the production census still labels a demonstrably live
function dead.

## Blocking findings

### 1. The production reachability census still marks live code dead, and store binding semantics remain unsound

`_qualified_call_counts()` only collects module-level import aliases. It does
not resolve the function-local imports used by live production callers. The
current scan reports exactly two `dead-code` sites; one is
`specify_cli/sync/queue.py::detect_legacy_rows_for_scope::sqlite_connect`.
That function is called from the live `_count_legacy_rows_for_scope()` preflight,
`_count_legacy_event_rows()` background gate, and `sync status` command through
function-local imports. A direct `rg` finds those calls, while the collector
reports `0 qualified source call(s)`. This is the same category of contradiction
that blocked cycle 3: a later WP cannot safely infer deletion ownership from this
disposition.

The store alias visitor is statement-order-aware but not Python-binding-aware.
Both of these safe programs are still reported as SQLite owners:

```python
import sqlite3

def safe(path):
    return path

open_sync = sqlite3.connect
def runtime_safe(path):
    return open_sync(path)
open_sync = safe
```

At runtime the function performs the late global lookup and calls `safe`, not
`sqlite3.connect`. Parameter shadowing is also misclassified:

```python
import sqlite3

def inspect(sqlite3, path):
    return sqlite3.connect(path)
```

Remediation: resolve live local-import/call edges, model function globals at
runtime rather than at definition traversal, and invalidate imported/module
bindings when parameters or assignments shadow them. Assert that every
production `dead-code` disposition has executable negative evidence; add the
three real `detect_legacy_rows_for_scope` entries as live controls.

### 2. Grant and sender call graphs remain alias-flow incomplete

`_import_bindings()` collects imports with `ast.walk()` and `_call_targets()`
uses those bindings without considering a later rebind. Under the default grant
collector, this safe caller is falsely reported as a grant `call-path`:

```python
from specify_cli.sync.writer import persist  # persist uses setattr(..., "granted", ...)

def safe(record, answer):
    return answer

persist = safe

def entry(record, answer):
    return persist(record, answer)
```

The exact widget exclusion and `setattr` discovery pass, but that does not make
the propagated grant entries sound.

The sender analyzer now invalidates a directly rebound alias and correctly finds
the call that precedes the rebind. It resolves only one alias hop, however, so a
live bypass disappears entirely:

```python
def alias_chain(client, payload):
    wire = client.post
    send = wire
    send("/events", json=payload)
```

The default sender scan returns no site for `alias_chain`. Remediation: use one
scope/order-aware binding environment for imports, local aliases, receiver
types, and calls; resolve aliases transitively with cycle protection; invalidate
them on rebind/shadowing; and add both counterexamples as positive/negative bite
controls.

### 3. The layout gate now ignores unresolved writes and retains stale SQL bindings

The exact join-built INSERT is found and the join-built SELECT is excluded, but
unknown SQL is now silently omitted. This new writer is invisible:

```python
def write(conn, payload, operation):
    sql = f"{operation} INTO event_outbox VALUES (?)"
    conn.execute(sql, (payload,))
```

The visitor also fails to invalidate a known SQL binding when reassigned to an
unresolved expression, so this safe/unknown call is falsely retained as the old
INSERT:

```python
sql = "INSERT INTO event_outbox VALUES (?)"
sql = build_query()
conn.execute(sql, (payload,))
```

This does not meet T004's requirement that a new current writer bypassing layout
authority be detected. Remediation: either gate the mutation API and separately
prove known reads, or represent unresolved execute-family operations explicitly
without calling them writes until their effect is established. In either model,
invalidate stale bindings on every assignment and make an unresolved potential
mutation fail the final/growth boundary rather than disappear.

### 4. All result categories still pass when identity and mutation are unrelated

The exact cycle-3 decoys now return false, but the predicates combine independent
`ast.walk()` facts rather than proving that the documented identity is written
to the documented result authority. Default-root replay (with the same durable
authority mapping used for production rows) returns `True` for all of these:

```python
def record(conn, event_id):
    audit(event_id)
    conn.execute(
        "INSERT INTO delivery_ledger(other) VALUES (?)",
        ("constant",),
    )
```

```python
def record(state, git_hash):
    audit(git_hash)
    state.unrelated = True
    save_sync_state(state)
```

```python
def record(report, result):
    audit(result)
    report.debug.append("unrelated")
```

The first merely sees the authority table and identity name in the same
function; the second sees any `state` attribute mutation plus any save plus an
incidental `git_hash`; the third sees any `result` read plus any nested report
append. Remediation: require the event/row/git/result identity to flow into the
specific recorded field/collection/write parameters, and assert the exact
documented success/failure result member rather than any mutation on the same
object.

### 5. T005 identity stability still misses attribute rebinding

The requested tuple component, audit-header/foreign-body, and local-name A→B
specimens now fail. `_stable_identity()` nevertheless treats an attribute dump
as stable without tracking mutation. This runtime cross-pair is false-clean:

```python
context = ProjectSyncContext(project_uuid=a.uuid)
a.uuid = b.uuid
attempt = DeliveryAttempt(
    context=context,
    journal_uuid=a.uuid,
    target_uuid=a.uuid,
    ledger_uuid=a.uuid,
)
```

`mutation_violations()` returns `()` because both sides have the same AST dump
`a.uuid`, even though the context captured A and the attempt reads B. Remediation:
accept only provably immutable/canonical identity expressions or version the
base object/attribute assignment state and reject mutable indirection. Add this
specimen beside the local-name rebound control.

## Independent verification

- Exact cycle-3/default-collector replay: all named specimens now bite.
- Deeper default-root replay: reproduced every blocker above.
- Production store classification: `82 live`, `14 legacy-migration`, `1 read-only`,
  `2 dead`; one dead entry is the live `detect_legacy_rows_for_scope` path.
- Focused four-file warning-strict suite: `58 passed, 2 xfailed`.
- Full 22-path WP01/#3030 warning-strict suite: `346 passed, 2 xfailed`.
- Documentation metadata plus isolated lifecycle: `678 passed`; the emitted
  `spec-kitty-sync-async-loop` remains the accepted #3130/#3237 pin.
- Strict focused mypy: `Success: no issues found in 4 source files`.
- Ruff check: `All checks passed`; Ruff format: `4 files already formatted`.
- `git diff --check`: pass; lane worktree clean.

## WP-level anti-pattern checklist

1. **Dead code — FAIL**: a demonstrably live production function is still labeled
   dead, and safe shadow/rebind cases are labeled SQLite owners.
2. **Synthetic-fixture test — FAIL**: the required T005 mutation detector remains
   false-clean for an executable A→B attribute-rebinding specimen.
3. **Silent empty return — N/A**: no production path was added.
4. **FR coverage — FAIL**: FR-023/FR-026/FR-029 enforcement misses live sender,
   layout, result, and identity variants and reports unsound grant/store evidence.
5. **Frozen surface — PASS**: no mission contract or production source changed.
6. **Locked decision — PASS**: ADR and exact project-store layout remain aligned
   with the mission's MUST/MUST NOT rulings.
7. **Shared-file ownership — PASS**: all changed files are WP01-owned and no shared
   lane ownership conflict is present.
8. **Production fragility — N/A**: no production raise or handler was added.

## Downstream impact

WP02 remains blocked. Do not use the current `dead-code` dispositions, propagated
grant entries, sender census, layout census, result matrix, or T005 identity
coherence as downstream proof until the counterexamples above are closed and
independently replayed.
