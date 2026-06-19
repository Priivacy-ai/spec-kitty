# Quickstart / Verification: Untrusted-Path Containment Hardening

How a reviewer confirms the mission's invariant holds.

## 1. Legitimate inputs are unaffected (NFR-003)

```bash
PWHEADLESS=1 python -m pytest tests/status/ tests/specify_cli/cli/commands/test_merge.py -p no:cacheprovider -q
```
Expect: all pre-existing tests pass; no legitimate slug rejected.

## 2. Traversal slug fails closed (SC-001)

Craft a `status.events.jsonl` with `"mission_slug": "../../../../tmp/evil"`, then drive each audited command (status read, `status materialize`, merge bookkeeping). Expect:
- read sinks → resolver returns `None`, one WARNING, no read outside the root;
- write sinks → output under `feature_dir.name`, no `mkdir`/write outside `.kittify/derived/`.

The negative tests encode this per sink:
```bash
PWHEADLESS=1 python -m pytest tests/status/ -k "traversal or fail_closed or slug" -p no:cacheprovider -q
```

## 3. Symlink-escape is rejected (SC-002)

The resolver tests plant a symlink under a trusted root pointing outside it and assert rejection (`ValueError` / `None`), proving `resolve()`-containment:
```bash
PWHEADLESS=1 python -m pytest tests/status/ -k "symlink" tests/specify_cli/cli/commands/test_merge.py -k "symlink" -p no:cacheprovider -q
```

## 4. Guards are not fake (SC-004)

For any guard, neutralize it (e.g. make the validator a no-op) and re-run its test — at least one test must FAIL. Restore.

## 5. Regression guard (FR-005)

```bash
PWHEADLESS=1 python -m pytest tests/architectural/ -k "untrusted or path_containment or slug" -p no:cacheprovider -q
```
A new unvalidated join on an audited surface fails this guard.

## 6. Audit completeness (SC-003)

Open the IC-02 audit record (`data-model.md` audit table populated during implement): every untrusted→FS sink in `src/specify_cli` has a disposition (fixed / not-reachable-documented); none blank.

## 7. Gates

```bash
ruff check .
mypy src/specify_cli/status/store.py src/specify_cli/status/aggregate.py src/specify_cli/core/paths.py
```
Expect: zero issues. (Loopback hotspots in `core/loopback_http.py` are documented, not changed — C-001.)
