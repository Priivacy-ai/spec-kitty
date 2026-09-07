# Contract: Run-State Store Hardening (WP05)

**Owner**: `src/runtime/next/` (`_internal_runtime/engine.py`, `runtime_bridge_io.py`, `decision.py`) · **Sequencing**: no dependency on WP01–WP04; merges FIRST (Q10 rider, `01M1V8HS2Q04T2VS1DCKHV2E1C`) to free the four files shared with Mission B
**Requirements**: FR-015, FR-016, FR-017, SC-006 · **Constraint**: C-003 (083 identity) · **Deferred**: Q9 (`01M1V8J842E7CJR6MGZ0MW3DQF`) index migration shape + legacy key

## 1. Index — `.kittify/runtime/feature-runs.json` (FR-016)

```jsonc
// after WP05
{
  "<mission_id ULID>": { "run_id": "…", "run_dir": "…", "mission_type": "software-dev", "mission_slug": "<display only>" },
  "legacy-<slug>":     { … }   // ONLY if Q9 adopts the precedent; never used for a mission that has a mission_id
}
```

- Lookup in `_load_or_start_run` (`runtime_bridge_io.py:611-660`) is `index.get(mission_id)`; `mission_slug` is never a lookup key (`:618` today).
- **Loud missing-state**: if an entry exists and `run_dir/state.json` is absent ⇒ raise a `StructuredError` subclass (e.g. `RunStateMissing(mission_id, run_id, run_dir)`) with a recovery hint; never fall through to "start a new run" (`:617-627` today).
- Migration shape (in-place rekey on first touch vs one-shot) and the legacy key: **Q9, decided in WP05's design note**; either shape must be idempotent and must not lose any existing entry.

## 2. Cursor + journal atomicity (FR-015) — `_internal_runtime/engine.py`

```python
def _write_snapshot(run_dir: Path, snapshot: MissionRunSnapshot) -> None:
    target = run_dir / "state.json"
    tmp = target.with_suffix(".json.tmp")            # same directory ⇒ same filesystem
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(snapshot.model_dump(mode="json"), fh, indent=2, sort_keys=True, default=str)
        fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, target)                            # atomic on POSIX and NTFS
```
(the `reducer.materialize` precedent, ~6 lines). `_append_event` (`:110-119`) hardens with the same discipline or an atomic-append helper; no L1 involvement (run journal is per-run, single-writer).

## 3. Pure progress read (FR-017) — `decision.py:369-377`

`from specify_cli.status import materialize_snapshot` replaces `materialize`; the surrounding `try/except: pass` becomes a logged fallback (no silent swallow — Sonar rule, CLAUDE.md).

## 4. Tests (RED-first then unit)

| Case | Expected | RED on main? |
|---|---|---|
| two missions, equal slug, distinct `mission_id` | distinct runs | yes (`:618`) |
| kill between old-truncate and new-write of `state.json` (simulated by raising inside the write) | old file intact or new complete; never partial | yes |
| progress query on a mission with tracked `status.json` | bytes identical before/after | yes (`materialize` writes) |
| index entry present, `state.json` deleted | structured error, no new run created | yes (silent fresh run) |
| index migration (per Q9) run twice | idempotent, no entry lost | pin |

## 5. Ledger note

WP05 stays inside already-ledgered runtime subpackages; if any lazy reach into `specify_cli` is removed, the same PR updates `_RUNTIME_ALLOWED_SPECIFY_CLI` / the doctrine-scan baseline (`test_runtime_ledger_has_no_stale_entries`).
