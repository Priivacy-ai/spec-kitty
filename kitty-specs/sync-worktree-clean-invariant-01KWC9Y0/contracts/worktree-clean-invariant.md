# Contract: Worktree-Clean Invariant (INV-1)

## Covered command surface

The invariant applies to every command in this set (the parametrized test enumerates it):

- status-event emission (the `EventEmitter` emit path)
- `sync status` (incl. `--check`), `sync pull`, `sync push`, `sync run`
- background dossier sync trigger
- lifecycle SaaS fan-out handler
- `tracker status`, `tracker map list`
- dashboard daemon tick

## Guarantee

```
GIVEN a clean checkout with SPEC_KITTY_ENABLE_SAAS_SYNC=1 and auth present
  AND snap = `git status --porcelain`  AND cfg = (content + mtime) of .kittify/config.yaml
WHEN any covered command runs to completion (success OR handled failure)
THEN `git status --porcelain` == snap          (byte-identical)
  AND .kittify/config.yaml == cfg               (unchanged)
```

Also holds when SaaS sync is disabled or unauthenticated (FR-008): no partial writes.

## Non-goals / boundaries

- The invariant is enforced by REMOVING writes, never by allowlisting (C-001). The `record-analysis` allowlist MUST NOT grow to include `config.yaml`.
- Write-authorized commands (`init`, explicit bind/apply) are OUT of the covered set — they may persist.

## Regression guard (paired contract)

```
GIVEN a checkout with a genuine uncommitted source edit
WHEN `record-analysis` runs
THEN it still exits non-zero with error_code DIRTY_WORKTREE   (FR-007 / SC-004)
AND the allowlist used by the guard does NOT contain .kittify/config.yaml
```

## Extensibility guard

```
GIVEN a NEW read/background command is added to the covered set
WHEN it violates INV-1 (dirties the tree)
THEN the parametrized test FAILS before merge   (FR-006 / AS-7)
```
