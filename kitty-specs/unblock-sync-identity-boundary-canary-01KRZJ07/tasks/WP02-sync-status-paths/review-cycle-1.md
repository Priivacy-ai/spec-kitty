---
affected_files: []
cycle_number: 1
mission_slug: unblock-sync-identity-boundary-canary-01KRZJ07
reproduction_command:
reviewed_at: '2026-05-19T10:54:09Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP02
---

# WP02 Re-implementation Feedback — B-1 Contract Drift (from WP04 canary verification)

## Status

**WP02's current implementation broke a cross-repo contract** with the sibling canary's `status_parser.py` (in `Priivacy-ai/spec-kitty-end-to-end-testing`). The fix needs to land in **this** repo because C-001 forbids edits to the sibling.

## What WP04 found

When WP04 ran the canary against a CLI built from WP01+WP02+WP03, **all four scenarios failed at the parse step** with:

```
ValueError: missing required string field 'active_queue.Path'
  at src/spec_kitty_e2e/identity_boundary/status_parser.py:328
```

The canary couldn't even reach the assertion stage on any scenario — the parser fails before checking the actual content.

## Root cause

The sibling canary's `status_parser.py` expects this output shape:

```
Active queue:
  Path: <path>
  …other indented child rows…
Legacy queue:
  Path: <path>
  …
```

I.e. it walks rows of the `"Active queue:"` section looking for a child row whose **key is `"Path"`** (indented under the section header).

WP02 currently emits:

```
[Rich Table:]
  Active queue:    (empty value)
  …
  Legacy queue:    (empty value)
  …

[Outside the table:]
Active queue path: <path>
Legacy queue path: <path>
```

The path is rendered **outside the table** with a different top-level key (`"Active queue path"` instead of `"Path"`). The parser cannot find `_row(active_queue, "Path")` and raises.

## Required fix (for WP02 re-implementation)

Preserve the parser-expected key/structure while still avoiding Rich's ellipsis truncation. Concretely:

1. **Keep the `"Active queue:"` / `"Legacy queue:"` section headers** in the Rich Table (they already are — don't touch).
2. **Change the outside-table path row labels** from `"Active queue path"` and `"Legacy queue path"` to a format the parser will treat as a `Path` child of the preceding section.
   - The most direct option: emit the path row as a plain `Console.print(f"  Path: {value}")` line immediately after the corresponding `Active queue:` / `Legacy queue:` section header in the Table, but **outside** the Table mechanism so width-driven ellipsis cannot truncate it.
   - Validate against the parser's actual indentation/key heuristic — read `/tmp/canary-repo/src/spec_kitty_e2e/identity_boundary/status_parser.py` (cloned by WP04 to `/tmp/canary-repo/`) to confirm. The parser is the contract; conform to it.
3. **Rendering order matters**: each `Path` line must appear immediately after its section header so the parser correctly attributes it.
4. **Apply the same fix to every other path-bearing row** that the parser inspects (executable path, source path, etc.) so the entire boundary view re-parses cleanly.

## What must NOT change

- The structural goal of FR-005 still holds: paths render verbatim, single-line, no ellipsis. The Table is still bypassed for path values; we just match the parser's key/indent convention while doing so.
- Field names on `ForegroundIdentity` / `DaemonOwnerRecord` MUST NOT be renamed (C-004 still in force).
- JSON contract (`sync status --check --json`) MUST stay byte-identical.

## Tests to add / update

1. **Update existing test** `tests/specify_cli/cli/commands/test_sync_status_check_paths.py`:
   - Expect the path row to render with key `"Path"` and indent style matching the parser's contract.
   - Long-path test: still asserts no `…` ellipsis.
   - JSON parity test: unchanged.
2. **Add a new parser-compat test** (in the same file or a peer):
   - Replicate the canary parser's expectation in a small in-tree fixture (do NOT depend on the sibling repo).
   - Parse `sync status --check` text output and assert it contains `Path: <verbatim path>` under each section header.
   - This test would have caught B-1 if it had existed.

## Validation before handing back to for_review

- All 4 existing WP02 tests + the new parser-compat test pass.
- Manual smoke: pipe `sync status --check` to a file, then grep for `^  Path: ` (or whatever indent the parser actually wants) — confirm the full canonical path is present.
- mypy --strict + ruff clean.

## Why this is being routed back

This is a real cross-repo contract drift that lane-b's review couldn't have caught — the lane-b reviewer correctly verified WP02 against `contracts/sync-status-check-rendering.md` and `test_sync_status_check_paths.py`, both of which are silent on the canary parser's expectations. WP04 surfaced the gap. Fixing it now (instead of after merge) keeps the mission's done criterion (scenarios 1, 2, 4 green) reachable on the canary re-run.

## Reference

- Full diagnostic: `kitty-specs/unblock-sync-identity-boundary-canary-01KRZJ07/canary-evidence/RUNBOOK.md` §9.
- Canary parser source (clone exists at `/tmp/canary-repo/`): `src/spec_kitty_e2e/identity_boundary/status_parser.py`.

Cycle: 1/3.
