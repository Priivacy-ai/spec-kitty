---
affected_files: []
cycle_number: 1
mission_slug: sync-cli-degod-wave4-01M0B0MX
reproduction_command:
reviewed_at: '2026-08-19T00:23:12Z'
reviewer_agent: user
wp_id: WP09
---

# WP09 Review — REJECT (one blocker, otherwise excellent)

Reviewer: reviewer-renata. Applied: DIR-005 (tests for new functionality), DIR-006
(mypy --strict), DIR-007 (docstrings), DIR-013 (pre-existing-failure reporting), Code
Review Checklist, tactics code-review-incremental + test-scaffolding-as-design-smell +
delete-the-assertion-not-the-test. Terminology Canon grepped (clean — no `feature`/`--feature`).

## Verdict: REJECT — one NEW architectural-gate regression introduced by WP09

The A-1 restructure itself is **impeccable** (see "What passed" below). The single blocker
is a **net-new dead-symbol gate failure** that WP09 introduces.

### BLOCKER — 3 new public symbols in `__all__` are dead per the symbol-level gate (FR-303)

`tests/architectural/test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`
is **RED**, and beyond the known pre-existing `specify_cli.sync.sync_ports::default_ports`
residue (WP03 → tracked for WP12), it now also flags **three NEW WP09 symbols**:

```
- specify_cli.sync.sync_status_core::build_status_rows
- specify_cli.sync.sync_status_core::build_boundary_sections
- specify_cli.sync.sync_status_core::build_orphan_detail_lines
```

These are declared in `sync_status_core.__all__` (lines 425-437) but **no other `src/` file
imports them** — verified: `grep -rn 'build_status_rows|build_boundary_sections|
build_orphan_detail_lines' src/ | grep -v sync_status_core.py` is empty. `sync.py` imports
only `StatusFacts`, `StatusRow`, `StatusView`, `BoundarySections`, `BoundaryVerdict`,
`build_status_view`, `evaluate_boundary_coherence`, `derive_auth_recovery_pending`
(sync.py:4102-4121). The three flagged functions are consumed **only internally** by
`build_status_view` (same module) and by the new unit tests — test imports do not satisfy
the gate. Since `sync_status_core.py` does not exist at the base (`0a154bd200~1`), all three
are unambiguously **new** and attributable to WP09.

This violates the WP09 Definition of Done ("`ruff`/`mypy --strict` clean … architectural
guards green") and the reviewer check "confirm WP09 didn't add a NEW dead symbol."

**Fix (preferred, gate fix-option 2 — trivial):** remove the three internal-only helpers
from `__all__` in `sync_status_core.py`. They stay in the module as callable internals; the
unit tests import them by explicit name, which does **not** require `__all__` membership, so
`test_sync_status_render.py` stays green. Keep in `__all__` only the true external surface
(`build_status_view`, `evaluate_boundary_coherence`, `derive_auth_recovery_pending`, and the
dataclasses `StatusFacts`/`StatusRow`/`StatusView`/`BoundarySections`/`BoundaryVerdict`).

Alternative (gate fix-option 4) if you deliberately want them exported: add allowlist
entries in `_SYMBOL_ALLOWLIST` with a rationale + tracker ticket — but option 2 is cleaner
and keeps the public API honest.

**Re-verify after the fix:**
```
SPEC_KITTY_ENABLE_SAAS_SYNC=1 PWHEADLESS=1 SPEC_KITTY_SYNC_DISABLE=1 PYTHONPATH=$WT/src \
  python -m pytest tests/architectural/test_no_dead_symbols.py \
    tests/characterization/test_sync_status_render.py -q -p no:cacheprovider
```
`default_ports` will remain red (known WP12 residue) — that alone is acceptable; the three
`sync_status_core::*` entries must be **gone**.

## What passed (do NOT touch — this is a clean, high-quality restructure)

- **Byte-identical pre/post (load-bearing):** captured full `sync status` + `sync status
  --check` render with the WP02 stubs at base `0a154bd200~1` vs HEAD, tmpdir-normalized —
  **identical SHA256** (`d6e7d8e…`, 4987 bytes each). Zero observable change: row order,
  colors, boundary block, exit codes all preserved.
- **WP02 goldens green & un-weakened:** `test_status_full_human_render_frozen`,
  `test_status_check_json_incoherent_exit_2`, `test_status_check_json_coherent_exit_0` pass;
  `test_sync_cli_safe.py` is NOT in the WP09 diff (byte-unchanged). Commit touches exactly the
  3 intended files — no `_baselines.yaml`, no census baseline, no DIR-041 ratchet.
- **A-1 restructure complete:** ALL I/O hoisted into `_gather_status_facts`
  (`_check_server_connection`, `scan_sync_daemons`/`get_sync_daemon_status`, runtime-open,
  token-read, owner/orphan reads, `build_boundary_failure_set`). No I/O call between the
  core-call and render in the shell body (grep-verified).
- **Core is I/O-free:** grep for `Console|print(|scan_sync_daemons|_check_server_connection|
  sqlite|open(|requests|httpx|get_token` in `sync_status_core.py` hits docstrings only.
- **Boundary reused not re-implemented (DIRECTIVE_044):** shell feeds
  `_build_boundary_check_failures(failure_set=facts.failure_set, …)` output as `base_failures`
  to `evaluate_boundary_coherence`, which only layers the 3 environmental lines + 0/2 exit.
- **Complexity ≤15, noqa deleted:** `def status(` has no `# noqa: C901` (base at 3137 did);
  `ruff check --select C901` clean; status cc=7 (mccabe) / 10 (radon), core max = 10. No
  hidden branchy helper >15.
- **30 core tests non-fakeable:** direct stub facts, exact `(label,value)` tuples + exact
  exit codes, every branch (queue empty/nonzero, saas on/off, auth ok/fail, daemon present/
  absent, last-sync valid/unparseable/never, ping/singleton ok/orphans/scan-fail, mismatch
  present/absent, stranded tag, coherent/incoherent verdict, auth-required arms).
- **Late-bind (INV-4):** `test_sync_no_early_bind`, `test_sync_writer_census`,
  `test_sync_two_authority` all green; render stubs still intercept post-move.
- **mypy/ruff:** `mypy --strict sync_status_core.py` and `mypy sync.py` clean; `ruff check`
  on all 3 files clean; no new `# noqa`/`# type: ignore`.
- **No other new failures:** `tests/cli/commands -k sync` = 225 passed.
