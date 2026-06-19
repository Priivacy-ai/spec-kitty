# Quickstart / Verification: Untrusted-Path Containment Hardening

How a reviewer confirms the mission's invariant holds.

## 1. Legitimate inputs are unaffected (NFR-003)

```bash
PWHEADLESS=1 python -m pytest tests/status/ tests/specify_cli/cli/commands/test_merge.py -p no:cacheprovider -q
```
Expect: all pre-existing tests pass; no legitimate slug rejected.

## 2. Traversal slug fails closed — both sources (SC-001)

Craft (a) a `status.events.jsonl` with `"mission_slug": "../../../../tmp/evil"` AND (b) a `meta.json` with the same hostile slug and an empty event slug (to exercise the IC-05 `meta.json` fallback), then drive each audited command (status read, `status materialize`, merge bookkeeping). Expect:
- read sinks → resolver returns `None`, at most one WARNING per distinct slug, no read outside the root;
- write sinks → output under `feature_dir.name`, no `mkdir`/write outside `.kittify/derived/`.

The negative tests encode this per sink (incl. the meta.json fallback):
```bash
PWHEADLESS=1 python -m pytest tests/status/ -k "traversal or fail_closed or slug or meta_json" -p no:cacheprovider -q
```

## 3. Symlink-escape rejected AND symlinked-root accepted (SC-002)

The store.py resolver tests plant a symlink under a trusted root pointing outside it and assert rejection (`None`), proving `resolve()`-containment — AND a positive case where the trusted/temp root is itself a symlink (macOS `/tmp`→`/private/tmp`) proving a legitimate slug is ACCEPTED (no false reject, NFR-003):
```bash
PWHEADLESS=1 python -m pytest tests/status/ tests/specify_cli/cli/commands/test_merge.py -k "symlink" -p no:cacheprovider -q
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

## 8. Performance (NFR-002) — inspection, not benchmark

NFR-002 is satisfied by code inspection: the validation path adds only
`assert_safe_path_segment` (character-count linear) and the single `resolve()`
already required for containment — no new `open`/`stat`/disk reads. No wall-time
benchmark gate is required; confirm by reviewing the diff for absence of new I/O
in the validation path.
