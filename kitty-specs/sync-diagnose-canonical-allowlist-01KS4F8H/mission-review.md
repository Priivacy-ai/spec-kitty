# Mission Review — Sync Diagnose Canonical Event-Type Registry

**Mission**: `sync-diagnose-canonical-allowlist-01KS4F8H`
**Anchor**: `Priivacy-ai/spec-kitty#1222`
**Date**: 2026-05-21
**Reviewer**: orchestrator (post-implementation cross-check); Renata
already approved the design pre-implementation (see
`renata-review.md`).

## Intent-vs-outcome — FR/NFR/C coverage

| Requirement | Status | Evidence |
|---|---|---|
| FR-001 — recognise every registry type | DONE | `TestCanonicalRegistryRecognition.test_recognises_every_registry_type` iterates 85 canonical types, all pass. |
| FR-002 — recognise CLI-internal types | DONE | `TestCanonicalRegistryRecognition.test_recognises_cli_internal_types` covers the 7 types (`BuildHeartbeat`, `BuildRegistered`, `DependencyResolved`, `ErrorLogged`, `HistoryAdded`, `MissionOriginBound`, `WPAssigned`). |
| FR-003 — reject genuinely-unknown | DONE | `TestCanonicalRegistryRecognition.test_rejects_genuinely_unknown_type` + existing `test_unknown_event_type`. |
| FR-004 — drift detector | DONE | `TestCanonicalRegistryRecognition.test_drift_detector_picks_up_new_registry_entries` uses `monkeypatch.setitem` against `_EVENT_TYPE_TO_MODEL` and `importlib.reload` on the diagnose module. PASSES. |
| FR-005 — no hardcoded list left | DONE | `grep -n "VALID_EVENT_TYPES" src/specify_cli/sync/diagnose.py` returns only references inside the doc-comment explaining the distinction; no allowlist literal remains. |
| FR-006 — existing tests pass | DONE | `pytest tests/sync/test_diagnose.py -v` → 35 passed, 0 failed. |
| FR-007 — outbound surface unchanged | DONE | `pytest tests/sync/test_forward_compatibility.py -v` → 56 passed (incl. all 3 `TestValidEventTypesOnlyGatesOutgoing` tests). `emitter.py` is git-clean. |
| NFR-001 — comment explains import | DONE | `src/specify_cli/sync/diagnose.py:28-46` is a 19-line comment block documenting the precedent, the doctrine reference (`#1198`), and the SaaS contract surface. |
| NFR-002 — no new pip deps | DONE | `git diff main...HEAD pyproject.toml uv.lock` is empty. |
| NFR-003 — diff scope confined | DONE | See "Diff scope" below — only `diagnose.py`, `test_diagnose.py`, mission dir. |
| NFR-004 — canonical pydantic models in fixtures | DONE | Test envelopes use the existing `_make_valid_event` helper which mirrors a canonical `Event` envelope. No new hand-rolled producers. |
| C-001..C-007 | DONE | No SaaS DB mutation; no new pip deps; no out-of-scope edits; Renata invoked; PR is the next step. |

## Diff scope verification

```
$ git diff origin/main...HEAD --stat
```

```
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/analyze.md         |  57 ++++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/checklists/...     |  36 ++++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/meta.json          |  12 ++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/plan.md            | 191 +++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/renata-review.md   | 111 +++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/spec.md            | 125 +++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/status.events.jsonl|   6 ++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/status.json        |  28 ++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/tasks.md           |  64 ++++
 kitty-specs/sync-diagnose-canonical-allowlist-01KS4F8H/tasks/...          | 174 +++
 src/specify_cli/sync/diagnose.py                                          |  37 +-
 tests/sync/test_diagnose.py                                               | 135 +++
```

All paths are either inside `kitty-specs/<mission-slug>/` (mission
artifacts) or are the two files explicitly named in NFR-003. No
emitter changes. No template changes. No migration changes. No
documentation edits beyond the mission dir.

## Behavioural verification

### Production fix

```python
# src/specify_cli/sync/diagnose.py — new constant
KNOWN_EVENT_TYPES: frozenset[str] = frozenset(
    set(_CANONICAL_EVENT_TYPE_MODELS.keys()) | set(_PAYLOAD_RULES.keys())
)
```

- 85 canonical-registry keys + 26 local payload-rules = 92 unique
  recognised event types (19 overlap, e.g. `WPStatusChanged`,
  `MissionCreated`).
- Old allowlist (`VALID_EVENT_TYPES`, 26 entries) was a *subset* of
  the new recognition set. The widening is monotonic — no event type
  that was previously recognised has been removed.

### Sanity sweep (sync/ test family)

| Test module | Result | Notes |
|---|---|---|
| `tests/sync/test_diagnose.py` | 35 passed, 0 failed | Mission's target module. |
| `tests/sync/test_forward_compatibility.py` | 56 passed, 0 failed | FR-007 — outbound gate tests still green. |
| `tests/sync/` (full) | 1677 passed, 6 failed | All 6 failures are pre-existing on `origin/main` (`test_daemon_intent_gate`, `test_orphan_sweep::*`) — confirmed via `git stash` + `pytest` on the unchanged tree. None implicate this mission. |
| `tests/contract/test_handoff_fixtures.py` | 52 passed, 1 failed | The single failure (`test_fixture_payload_passes_emitter_rules[WPCreated:01JMBYA1B2C3]`) is pre-existing on `origin/main` — confirmed via `git stash` + restore of `test_handoff_fixtures.py` from `origin/main`. Unrelated to this mission. |

### Allowlist genuinely deleted (vs. relocated)?

**Genuinely deleted.** Verification:

```
$ grep -nE "VALID_EVENT_TYPES" src/specify_cli/sync/diagnose.py
33:# (``emitter.VALID_EVENT_TYPES``).  The two contracts are deliberately
34:# distinct: ``VALID_EVENT_TYPES`` gates *outbound* emission and is locked
```

The only mentions of `VALID_EVENT_TYPES` in `diagnose.py` are inside a
doc-comment explaining the distinction between the recognition set
(`KNOWN_EVENT_TYPES`) and the emitter's outbound gate
(`VALID_EVENT_TYPES`). The import is gone; the membership check uses
`KNOWN_EVENT_TYPES`, which is computed at module-load from the canonical
registry.

### Drift detector actually drift-detects?

**Yes.** The test:

1. Adds a synthetic entry `_DriftDetectorSentinelEvent → Event` to
   `spec_kitty_events.conformance.validators._EVENT_TYPE_TO_MODEL` via
   `monkeypatch.setitem`.
2. Reloads `specify_cli.sync.diagnose` via `importlib.reload`, which
   recomputes `KNOWN_EVENT_TYPES` from the now-patched registry.
3. Asserts that the synthetic type passes recognition without any
   change in `diagnose.py`.

If `spec_kitty_events` ships a new event type, the recognition surface
auto-widens at the next CLI release. No follow-up in this repo
required.

## Findings — other hardcoded allowlists spotted (for `spec-kitty#1198`)

Scope-respecting scan via:

```
grep -rn "VALID_EVENT_TYPES|KNOWN_EVENT|ALLOWED_EVENT|RECOGNISED_EVENT|RECOGNIZED_EVENT|EVENT_TYPE_ALLOWLIST" src/specify_cli/
```

| Location | Verdict | Follow-up? |
|---|---|---|
| `src/specify_cli/sync/emitter.py:541` (`VALID_EVENT_TYPES = frozenset(_PAYLOAD_RULES.keys())`) | **Intentional** — this is the outbound-emission gate, locked by `tests/sync/test_forward_compatibility.py::TestValidEventTypesOnlyGatesOutgoing` and `tests/contract/test_handoff_fixtures.py`. It SHOULD remain narrow. Not a drift artifact; it is a deliberate egress contract. | **No follow-up.** |
| `src/specify_cli/audit/shape_registry.py:181` (`LIFECYCLE_AGGREGATE_TYPES = frozenset({"Mission", "Project", "WorkPackage", "MissionDossier"})`) | Hardcoded `aggregate_type` set, not `event_type`. Used for lifecycle-row classification. **Worth a closer look** under `#1198` — `aggregate_type` could potentially derive from the events package's `AggregateType` enum if one exists. | **Yes, flag for `#1198` follow-up.** Filed as informational sighting; no action in this mission per scope discipline. |
| `src/specify_cli/sync/emitter.py:542` (`VALID_AGGREGATE_TYPES = frozenset({"Build", "WorkPackage", "Mission", "MissionDossier"})`) | Outbound-aggregate gate, mirrors `VALID_EVENT_TYPES` in shape. Same reasoning — narrow on purpose. The presence of `"Build"` (CLI-only) vs. `audit/shape_registry`'s `"Project"` suggests two callers have slightly different views of the universe. **Worth a closer look** under `#1198`. | **Yes, flag for `#1198` follow-up.** Same disposition as above. |
| `src/specify_cli/.contextive/system-events.yml:28` | Documentation manifest (Contextive). Not enforced at runtime. | No follow-up. |

### Follow-ups for `spec-kitty#1198` (will be filed as issue comments / linked PRs after this mission lands)

1. **`shape_registry.LIFECYCLE_AGGREGATE_TYPES` vs. `emitter.VALID_AGGREGATE_TYPES`** — two hardcoded `aggregate_type` sets that disagree (one has `"Project"`, the other has `"Build"`). At minimum they should be documented as intentional divergences; ideally one canonical source. Out of scope here.

2. **`spec_kitty_events` public-alias for `_EVENT_TYPE_TO_MODEL`** — this mission's private-import precedent matches `lifecycle_events.py:210` and the SaaS, but a public alias (e.g. `spec_kitty_events.EVENT_TYPE_TO_MODEL` or `spec_kitty_events.conformance.EVENT_TYPE_REGISTRY`) would let downstreams drop the `_`-prefix. Suggested as a `spec-kitty-events` follow-up under `#1198`.

## Operating-rule compliance

- [x] Producers use canonical pydantic models (no new producer added; existing `_make_valid_event` helper unchanged).
- [x] No new pip dependencies.
- [x] `unset GITHUB_TOKEN` will be used at PR creation (next step).
- [x] No direct-to-`main` push. PR-based.
- [x] Reviewer is `reviewer-renata`.
- [x] `frontend-freddy` not invoked — backend only.
- [x] No SaaS DB / queue / readiness mutation.
- [x] No ingress-limit changes.
- [x] Historical events not skipped / replayed / deleted.
- [x] No final `3.2.0` cut.

## Verdict

**APPROVE for PR.**

All FR/NFR/C satisfied. Diff scope confined. Allowlist genuinely
deleted. Drift detector demonstrably drift-detects. Two `#1198`
follow-ups documented but not actioned (scope discipline).
