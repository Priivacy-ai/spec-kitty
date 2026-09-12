---
affected_files:
  - tests/sync/conftest.py
cycle_number: 1
mission_slug: verification-trust-3115-01KYVYWM
reproduction_command: '.venv/bin/python -m pytest tests/sync -m "fast and not windows_ci" -n 8 --dist loadfile'
reviewed_at: '2026-08-01T15:44:35Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP05
---

# WP05 — APPROVED

Final commit `15542e449f`. Three independent review rounds, one operator escalation, one
orchestrator error corrected. Nothing above MEDIUM stands.

## The deviation, adjudicated first

The operator's instruction was *"pin the 12 as strict xfails"*. **That was not implementable as
worded**, and the reviewer proved it rather than accepting the implementer's account:

```
FxFx                                                       [100%]
FAILED test_x.py::test_leaky_still_leaks - [XPASS(strict)] pinned leak
FAILED test_x.py::test_leaky_that_stopped_leaking_clean - [XPASS(strict)] pin...
2 failed, 2 xfailed in 0.01s          EXIT=1
```

Two failures, both worse than the implementer had claimed:

1. The **still-leaking** case — the one meant to be silently accepted — is `FAILED`, exit 1. `xfail`
   never delivers the "does not red the suite" half.
2. Still-leaking and stopped-leaking are **byte-identical** in output. `xfail(strict=True)` cannot
   discriminate them, so it never delivers the "fail loudly if one stops reproducing" half either.

`xfail` governs the **call** phase; this guard raises from **teardown**. The hand-rolled allowlist is
therefore not a shortcut around the instruction — it is the only mechanism that implements it. C-007
holds independently: no work package owns any of the twelve files, so a marker on the test functions
would have been an ownership violation.

## The HIGH, and how it was resolved

`#3130`'s twelfth leak is observable **only from a clean-baseline worker**. Pinned naively, it fired
a *false* strict failure in any serial run — because `test_target_authority.py` sorts first
alphabetically and leaves the value already dirty, so the wiring node's own diff is empty:

> *"but this run left NOTHING dirty. The pinned leak no longer reproduces. … remove this node's
> entry from `_PINNED_LEAKS` to prove the fix"*

The message was false and its instruction would have deleted a live pin for a live defect. Measured
deterministic in serial (`2 passed, 1 error`, exit 1) and reproducible under `-n 1 --dist loadfile`.

That tripped the mission's 3-round escalation rule and went to the operator, who chose to drop the
node from the pin set.

**The orchestrator's framing of that choice was wrong, and it is recorded here because the error was
the orchestrator's.** Dropping the pin did not remove the red — it *moved* it. An unpinned node that
leaks reds as an unpinned leak, which is exactly what a clean baseline produces. Verified directly on
the drop commit:

```
ERROR tests/sync/test_target_authority_wiring.py::test_readiness_host_config_keys_off_resolved_target
1 passed, 1 error in 58.81s          EXIT=1
```

The option had been presented as "measured unreachable as a red in the gating shard", which was true
of the *strict-check* red and was never carried through to the *unpinned-leak* red the drop would
create. The four green CI-selection observations were four samples of a worker-placement lottery, not
proof of absence.

**Resolution: `requires_clean_baseline`.** `_PinnedLeak` gained the flag plus a `baseline_watch`
slot. The discriminator reads that pin's named entry directly out of the exact `before` snapshot
`pytest_runtest_teardown` already holds — not an approximation of it. When the entry was already
non-default on entry, the strict failure is suppressed and recorded as a **third, distinct outcome**
(`UNOBSERVABLE this run`), deliberately kept out of `ACCEPTED` so the two cases stay
distinguishable. Twelve pins again; both count sites derive from `len(_PINNED_LEAKS)` so they cannot
drift.

## Proofs

| # | Case | Result |
|---|---|---|
| 1 | isolated, clean baseline | `1 passed`, exit 0, `ACCEPTED (#3130)` |
| 2 | serial two-node, inherited-dirty | `2 passed`, exit 0, `UNOBSERVABLE this run` |
| 3 | **flag flipped to `False`** | `2 passed, 1 error`, exit 1 — false failure reproduced exactly; flipped back → exit 0 |
| 4 | suppression is narrow — unflagged pin that stopped leaking | `1 passed, 1 error`, exit 1 |
| 5 | CI selection `-n 8` / `-n 4` | `2110 passed, 12 skipped`; **zero `[FR-007 leak guard]` errors** |
| 6 | all twelve, serial default order | `12 passed`, exit 0 — 11 `ACCEPTED`, 12th `UNOBSERVABLE` |

Proof 3 is the load-bearing one: without it, a green suite shows only that nothing fired, not that
the flag is what stopped it firing.

Independently re-verified at approval: the previously-red isolated run is `1 passed`, exit 0, node
`ACCEPTED`. Twelve `_PinnedLeak(` entries; the flag set on exactly one; the discriminator guarded by
a defensive raise if called without the flag.

## Also fixed this round

- **`[E26]` was missing** from `test_lifecycle_readiness`'s markers. `#3130`'s row 11 records **four**
  leaks; the pin modelled three. The cross-check that passed earlier had verified the *node-id*
  column and not the *leaked-symbol* column. All twelve marker tuples re-derived against the symbol
  column; only this one needed a change.
- **A false locator.** The caveat claimed the `ACCEPTED (#3130)` lines "are in its own captured
  output". `grep -c` returns **0** under xdist — `pytest_terminal_summary` never runs in workers, so
  they are emitted in no process. Corrected to the truthful remedy. The load-bearing summary line
  does print, so the un-forgettable requirement was always met; only the pointer lied.
- **A misquoted source.** The exclusion of `test_get_sync_service_returns_same_instance` cited
  `#3130` as recording it passing. `#3130` says the opposite. The decision is right — three
  independent `--dist loadfile` runs show it green — so the measurement is now the stated reason.
- **A stale count** introduced by the drop (`11 node(s) are pinned` beside `none of the 12 …`).
- Two unreachable `return result` statements after `pytest.fail(...)`.

## Residuals

- **Markers are bare substrings.** `"target=None"` matches any anonymous leaked thread, so a
  genuinely new anonymous-thread leak on those four nodes would be absorbed by an existing pin.
  Documented in `_PinnedLeak`'s docstring; not redesigned.
- **The flag is scoped to one node.** Artificially reversing collection order so the wiring node runs
  *before* its sibling makes the unflagged sibling show the same false-failure shape. This cannot
  occur in the real default alphabetical order, which is what CI and every measurement here use.
  Reported by the implementer unprompted.
- **`tests/sync` at large is short by six.** Outside `-m "fast and not windows_ci"`, six further
  guard errors appear on four unpinned, unfiled files. Not this package's scope; commented onto
  `#3130`, along with a sub-observation that the guard may be attributing a **victim** as the
  polluter in one case.

## One measurement artefact, reported rather than buried

The implementer's first round-3 `-n 8`/`-n 4` runs contradicted the reviewer's numbers. Root cause
was its own leaked `run_sync_daemon` subprocesses on ports 9400-9402, never reaped across
back-to-back runs — the standing rules' documented sibling-daemon hazard, self-inflicted. After
clearing them the numbers matched exactly. It reported this rather than presenting a disagreement,
which is why the final figures are trustworthy.
