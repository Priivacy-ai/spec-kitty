---
affected_files: []
cycle_number: 1
mission_slug: charter-preflight-remediation-01KYG9WK
reproduction_command:
reviewed_at: '2026-07-27T08:58:55Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

# WP03 review — cycle 1

## Verdict: REJECTED — the pinned floors and the exemption declaration can both be silently gamed

WP03's backfill removal, exemption wiring, and operator-message work are all correct and well
evidenced (see "Full verification performed" below). The rejection is narrowly scoped to
`tests/architectural/test_remediation_effectiveness.py`'s new pinning/keying mechanism, which has
two confirmed, empirically-demonstrated gaps.

---

## Required change 1 — pin the total, not just the two halves (C-EFF-4 / NFR-001)

`_REMEDIATION_STATE_FLOOR` (5) and `_EXEMPTION_FLOOR` (2) are pinned independently. Nothing asserts
`len(discovered) + len(_EXEMPT_STATES) == 7` (the total non-passing-state count this contract's
census establishes). That total is exactly what C-EFF-4's two counts exist jointly to protect
("Both counts are load-bearing... The exemption pin prevents passing by reclassifying a failing
check as exempt") — but only the exemption's *own* size is pinned, not its relationship to the
remediation floor it trades against.

**Empirically confirmed exploit** (reverted, `git status` clean throughout): in `computer.py`,
changed `_compute_synced_bundle`'s real `missing` branch (line 368, remediation
`"spec-kitty charter generate --no-from-interview"`) to `remediation=None` — a genuine, real
remediation-emitting state silently turned into a no-remediation state, *without* declaring it in
`_EXEMPT_STATES` and *without* bumping `_EXEMPTION_FLOOR`. In the test file, dropped
`_REMEDIATION_STATE_FLOOR` 5→4 and removed the now-unneeded `_CASES` entry for that state. Ran
`pytest tests/architectural/test_remediation_effectiveness.py`:

```
12 passed in 88.04s
```

All 12 tests GREEN. Nothing in the mechanism — not `test_remediation_state_floor_is_pinned`, not
`test_exemption_set_size_is_pinned`, not `test_case_table_matches_ast_derived_states` — detects that
a real, non-exempt state quietly stopped emitting a remediation and lost its effectiveness coverage.
This is worse than the "adjust the floor to dodge a red run" case C-EFF-4 already guards against: it
is coverage loss with *no* accompanying red at all, and it does not even require touching the
`_EXEMPT_STATES` declaration.

**Required fix**: add an explicit invariant test, e.g.:

```python
def test_remediation_and_exempt_floors_sum_to_known_total() -> None:
    assert _REMEDIATION_STATE_FLOOR + _EXEMPTION_FLOOR == 7, (
        "a state moved out of remediation-emitting coverage must land in "
        "_EXEMPT_STATES (and bump _EXEMPTION_FLOOR) in the same change — "
        "the two floors must never drift apart"
    )
```

This makes moving a state between the two buckets legal (as WP03's own 7→5/0→2 change legitimately
was) while making *losing* a state from both floors simultaneously impossible without the test
suite itself flagging the total.

---

## Required change 2 — key `_EXEMPT_STATES` semantically, not by line number (raised by the mission
coordinator mid-review; independently confirmed)

`_EXEMPT_STATES` is keyed on `(layer, lineno)` — `("charter_source", 331)`, `("synced_bundle", 377)`.
`test_case_table_matches_ast_derived_states` computes `expected = discovered - exempt_linenos`: any
AST-derived remediation-emitting lineno that happens to coincide with a value in `_EXEMPT_STATES` is
silently excluded from the required-coverage set, regardless of whether that lineno's state still
carries a real, non-`None` remediation.

**Empirically confirmed** (reverted, `git status` clean throughout): inserted 5 blank lines above
`_compute_charter_source` in `computer.py` (no semantic change) to shift every downstream line
number. Re-ran the mechanism **unmodified**:

```
1 failed, 12 passed in 87.84s
FAILED test_case_table_matches_ast_derived_states — missing={327,373,477,508,521} extra={322,368,472,503,516}
```

The mechanism does fail loudly here — but only because WP01's `_CASES` table is *also* line-number
keyed, so the shift breaks the case-coverage bookkeeping for all five non-exempt states at the same
time, incidentally catching the drift. That coincidental protection is fragile: it depends on the
non-exempt states' `_CASES` linenos moving by the same delta as the exempt states' linenos, which
holds for a uniform insertion but is not guaranteed for a reorder (e.g. moving one producer function
above another shifts different sites by different, non-uniform amounts). In that case a real,
still-remediation-emitting state's line could land exactly on a value already in `_EXEMPT_STATES`,
silently inheriting the exemption's exclusion from `expected` — the mechanism would report green
while a real state escaped C-EFF-1 coverage. This is precisely the "reclassify a check to dodge the
test" loophole C-EFF-2 is written to close, reachable here by accident rather than by intent.

**Required fix**: derive exemption identity the same way `_discover_remediation_emitting_states`
already derives remediation identity — from the AST, keyed on `(producer_function_name, state_value)`
(both are sibling keyword arguments on the same `FreshnessSubState(...)` call, confirmed by
inspection of `computer.py`), e.g. `("_compute_charter_source", "invalid")` /
`("_compute_synced_bundle", "stale")`. This survives arbitrary line movement and cannot be
coincidentally collided with by an unrelated site, closing both failure modes the coordinator raised:
spurious drift-triggered red (still possible, but for the right semantic reason) and silent
inheritance by an unrelated state (closed outright — producer+state identity cannot alias).

Note for scope: this pattern (line-number keying) originates in WP01's `_CASES` table and
`_discover_remediation_emitting_states`, not in WP03. The concrete defect being rejected here is
WP03's own `_EXEMPT_STATES` construct and its use in `test_case_table_matches_ast_derived_states`'s
subtraction — fixing those two is in WP03's scope and does not require touching WP01's `_CASES`
table shape (though the same AST discovery function can be extended to return `(lineno, producer,
state)` tuples so both structures can migrate to the stable key without duplicating the AST walk).

---

## Everything else: verified, no further changes required

- **Backfill closure (T013)**: both sites fixed — the per-check line composition
  (`runner.py:_blocked_reason_line`) and the "no non-passing check found" fallback (formerly also
  `... run \`spec-kitty charter status\``, now a plain internal-inconsistency message with no
  command). Confirmed by reintroducing the backfill in `_blocked_reason_line` (`return f"{check.name}
  {check.state}; run \`spec-kitty charter status\`"`) and rerunning
  `test_exempt_check_output_names_check_with_no_command` and `test_backfill_cannot_return`: both
  correctly went red. Reverted; `git status` clean.
- **Shape pin**: `result.py`'s `blocked_reason: str | None` is unchanged — still a single `str`,
  newline-joined for multiple lines.
- **Coverage replacement (T015)**: the two removed parametrized `_CASES` entries are adequately
  replaced. A state silently regaining a fabricated/real remediation after being declared exempt is
  still caught — by `test_remediation_state_floor_is_pinned` (discovered count would rise from 5,
  failing the pin), independent of the `_CASES` restructuring.
- **Out-of-map edits (CHECK 5)**: `computer.py` (docstrings + `remediation=None` swap on the two
  exempt branches only), `test_computer.py` (one assertion + comment updated in
  `test_charter_source_invalid_when_unparseable`, nothing else touched), `test_runner.py` (one test
  updated, one test added) — all confined to what T014/T015 required. No restructuring of WP01/WP02
  assertions found.
- **`test_invalid_charter_yaml_blocks` latent false-positive**: confirmed empirically. Checked out
  the WP02-era files over HEAD and ran the old assertion (`assert "sync" in result.blocked_reason`)
  with debug output: `blocked_reason` was `'charter_source invalid; run \`spec-kitty charter
  generate\`\nsynced_bundle stale; run \`spec-kitty charter generate\`'` — no `"sync"` substring
  appears in any remediation command, yet the assertion passed, purely because the check name
  `synced_bundle` itself contains `"sync"`. WP03's replacement assertions
  (`"charter_source invalid" in result.blocked_reason`, plus direct field assertions) are correctly
  bound to real content. Reverted; `git status` clean.
- **Operator message wording (CHECK 4)**: the two exempt messages are informative, not silent, and
  correctly explain *why* `charter generate` cannot help rather than presenting it as a next step —
  this is the opposite of the BC-2 pattern (naming a command as the fix that cannot work), not a
  repeat of it. No change requested here.
- **Regression**: `tests/architectural/test_remediation_effectiveness.py` — 13 passed. `tests/specify_cli/charter_preflight/`
  + `tests/specify_cli/charter_freshness/` — 53 passed. `ruff check` on all changed files — clean.
  `mypy --strict` on the three touched `src/` files — 3 pre-existing errors at `computer.py:187/203/210`
  (confirmed present on the WP02 merge-base commit `1e67a4180`, unrelated to WP03's lines 299–385
  edits) — zero new errors from WP03's own diff.

---

## What to do next

Add the sum-invariant assertion (required change 1) and re-key `_EXEMPT_STATES` to
`(producer_function_name, state_value)` (required change 2), both confined to
`tests/architectural/test_remediation_effectiveness.py`. No change to `computer.py`, `runner.py`, or
`result.py` behavior is required — the defect is entirely in the test mechanism's own bookkeeping.
Re-request review; I expect a fast pass given the underlying implementation is already sound.
