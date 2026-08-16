---
affected_files: []
cycle_number: 2
mission_slug: per-project-sync-consent-ledgers-01KZKMQZ
reproduction_command:
reviewed_at: '2026-08-10T03:28:10Z'
reviewer_agent: codex
wp_id: WP04
---

# WP04 Review Cycle 2 — Changes Requested

Cycle 2 closes the four exact cycle-1 specimens, but two material project-store
boundary gaps remain.

## 1. The required live incident spy/counter no longer executes

The mandatory history/incident/purge command is red:

```text
tests/sync/test_project_consent_incident_baseline.py::
test_spies_and_counter_observe_current_production_write_paths
TypeError: EventJournal.__init__() missing 1 required positional argument: 'authority'
22 passed, 1 failed
```

The failure is at
`tests/sync/test_project_consent_incident_baseline.py:415`, where the incident
control still calls the retired `EventJournal(journal_path)` constructor. The
same function later calls the retired path constructor
`SqliteDeliveryLedger(str(tmp_path / "result-ledger.db"))` at line 447, so
repairing only the first failing line will not restore the control. Its old
single-ledger A/B counter model is also incompatible with the new physical
project-store isolation and result rows now require an owning journal event.

This is a WP04 regression, not the declared pre-existing JUnit baseline: the
test exercised the production journal/ledger write paths before WP04 removed
those constructors, and WP04 reviewer guidance explicitly requires the
incident controls to run. Formally assign sequential ownership of
`tests/sync/test_project_consent_incident_baseline.py` from WP01 to WP04 in the
planning/lanes evidence, then re-pin the entire spy/counter test to real
`ProjectSyncStore` unit(s) of work and layout authority. Preserve its positive
controls and prove the A write opens/counts only A while B's store remains
byte/count unchanged. Do not restore `EventJournal(path)`, a default ledger, or
any shared compatibility path.

## 2. Status still cross-pairs a context with another physical store

`build_project_store_status()` now checks that journal, ledger, and body queue
share a UUID and connection identity
(`src/specify_cli/delivery/status_report.py:544-555`), but it never binds those
repositories to `context.store_identity`. UUID equality is not physical-store
identity.

An exact real-store probe derived a granted context for UUID P under
`SPEC_KITTY_HOME/home-a`, then passed a journal, ledger, and body queue for the
same UUID P under `SPEC_KITTY_HOME/home-b`, all on one home-b UoW. The function
accepted the cross-pair and returned:

```text
same_path=False
reported_consent={'state': 'granted', 'generation': 1}  # home-a
reported_body_count=1                                  # home-b
```

This directly violates the WP04 reviewer rule to reject independently supplied
store/UUID pairs even when ordinary callers pair them correctly. Bind status to
one non-forgeable, store-derived identity: either construct the complete status
repository bundle from one verified UoW/context or expose an opaque verified
store identity from that UoW and require exact equality with
`context.store_identity` before any read. A comparison of caller-visible path
strings alone is not sufficient. Add the same-UUID/home-a-vs-home-b negative
test, with a same-store positive control and a read counter proving rejection
occurs before journal, ledger, or body reads.

## Verified cycle-2 evidence

- The six exact cycle-1 controls pass: fabricated `SimpleNamespace` capability
  rejection; persisted genuine history selection; changed cohort and opt-out
  invalidation; physical body-row/reference deletion with exact A/B
  differential; foreign queue purge rejection before read; and A-context/B-queue
  status rejection before read.
- Exact owned/authorized matrix: `254 passed, 2 xfailed`.
- Required extended history/incident/purge gate: `22 passed, 1 failed` on the
  incident constructor above (expected target was 23 passed).
- Normal collection/backoff gate: `65 passed`; the deterministic clock test is
  semantic and the former wall-clock assertion is gone.
- Architecture gate: `48 passed, 2 xfailed`; the resolver and layout-permit
  mutations remain load-bearing. A four-test writer-census superset also passed.
- Strict mypy: no issues in the 24 non-architecture touched files. Ruff check
  passed and all 26 cycle-2 fix files are formatted. Compileall,
  `git diff --check f2437c8cd^..2debe8d9e`, and the new `--feature` grep pass.
- The architectural files retain exactly 12 `TODO(#3280)` markers; the separate
  thirteenth repository marker remains the pre-existing incident disclosure.
- Cycle-1 review artifact SHA-256 remains byte-exact at
  `33f755bfc5e1ade42a989a52d09d898c40aea720edbdb4a5be53b0024b93984e`.
- Cycle-2 RED `f2437c8cd` precedes fix `2debe8d9e`. Neither cycle-2 commit
  touches WP07/WP10 reserved sources/tests or
  `tests/delivery/test_purge_all_body_uploads_3030.py`; the per-project body
  differential is correctly WP04-owned and the legacy total purge remains WP10.
- No component-level `connect()`/`commit()` or new live default/global resolver
  was introduced in the owned repositories. All current repository writes,
  including body deletion, remain under the active UoW and immediate layout
  permit.
- `preserve_delivery_history` call sites are correctly separated: GC explicitly
  passes `True` and retains result history, while explicit project purge uses
  the default `False` and removes aggregate children. The exact purge tests pass.
- All issue-matrix rows have an allowed verdict; no unknown/empty row was found.

## Anti-pattern checklist

1. **Dead code — PASS**: the new history revalidation seam is called by ledger
   selection; the purge and status checks are live.
2. **Synthetic fixtures — PASS**: the cycle-1 closure tests and both review
   probes use real project stores, UoWs, and SQLite rows.
3. **Silent empty return — PASS**: no new silent-empty failure was found.
4. **Functional-requirement coverage — FAIL**: the incident write-path control
   aborts before observing any current journal/ledger write.
5. **Frozen surface — PASS**: cycle-2 commits leave WP07/WP10 reserved files and
   the cycle-1 artifact untouched. The incident-test ownership transfer must be
   recorded before its reroll.
6. **Locked decisions — FAIL**: one context can still report authority and
   payload counts from different physical stores.
7. **Shared-file ownership — PASS for the submitted diff**: the WP03 history
   revalidation integration is the direct remediation required by cycle-1
   feedback; no uncoordinated WP07/WP10 file was changed. The next reroll needs
   the explicit WP01-to-WP04 incident-test assignment above.
8. **Production fragility — FAIL**: status can silently produce a coherent-looking
   but physically cross-paired report; the incident regression also removes a
   required safety control from the executable gate.

WP06 and WP10 depend on WP04 and must consume the corrected cycle-3 reroll.
