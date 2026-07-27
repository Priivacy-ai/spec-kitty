# Contract: Tracker binding_ref report-only on read paths

## C-TB-1 — Read-like tracker ops do not persist binding_ref

For `status`, `sync_pull`, `sync_push`, `sync_run`, `map_list` (`tracker/saas_service.py`):

```
WHEN the server response carries a new/changed binding_ref
THEN the method MUST NOT call save_tracker_config (no .kittify/config.yaml write)
AND  it surfaces the available upgrade as a result field:  pending_binding_upgrade=<ref>
```

When the server returns no `binding_ref`, or it matches the stored one, the method is a no-op (unchanged behavior).

## C-TB-2 — Persistence only at an explicit boundary

```
WHEN the operator runs an explicit `tracker bind` / apply-style command
THEN save_tracker_config persists binding_ref to .kittify/config.yaml   (write-authorized)
```

So an intentional binding upgrade still works; it just no longer happens as a side effect of reading.

## C-TB-3 — Surface shape

- `pending_binding_upgrade` is returned on the result object/dict of the read method.
- An optional, non-fatal one-line notice MAY inform the operator an upgrade is available and how to apply it. The notice MUST NOT write any tracked file.
