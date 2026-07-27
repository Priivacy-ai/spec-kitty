## Investigation outcome — 7-day window

Investigation per `mission-exception.md` `## Follow-up` operator commitment, mission `investigate-canary-followups-1142-1141-01KS02TV`. Hypothesis 1 ruled out; hypothesis 2 confirmed.

### Hypothesis tested

- **Hypothesis 1** (stale canary venv): RULED OUT.
- **Hypothesis 2** (WP01 predicate doesn't cover all lifecycle emitters): CONFIRMED.

### Commands run

```bash
# Hypothesis 1 — clean canary venv against the merged-mission CLI (rc14)
cd /tmp && rm -rf sk-canary-1142 && mkdir sk-canary-1142 && cd sk-canary-1142
git clone https://github.com/Priivacy-ai/spec-kitty-end-to-end-testing.git canary-repo
cd canary-repo
git checkout origin/kitty/pr/sync-identity-boundary-deployed-dev-canary-01KRXVW4-to-main  # PR #42 branch — scenarios live here, NOT on canary main
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                                                       # canary harness
pip install /path/to/spec-kitty                                        # spec-kitty 3.2.0rc14 (post-#1143 merge)
spec-kitty --version                                                   # spec-kitty-cli version 3.2.0rc14
SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_E2E_TRUSTED_RUNNER=1 \
  pytest tests/identity_boundary/test_scenario_1_*.py tests/identity_boundary/test_scenario_2_*.py \
    -v --capture=no -m sync_identity_boundary_deployed_dev --timeout=60
```

### Evidence

Both scenarios FAIL on a brand-new clean canary venv with `spec-kitty-cli 3.2.0rc14`:

```
FAILED tests/identity_boundary/test_scenario_1_fresh_authenticated_mission.py::test_scenario_1_fresh_authenticated_mission_reaches_saas
FAILED tests/identity_boundary/test_scenario_2_legacy_queue_migration.py::test_scenario_2_legacy_queue_row_migration
======================== 2 failed in 161.89s (0:02:41) =========================
```

Inner CLI failure (verbatim from the test output):

```
spec_kitty_e2e.shell.CommandError: Command failed (1): spec-kitty sync now --report ...
stdout:
╭──────────────── TeamSpace Migration Required ─────────────────╮
│ TeamSpace mission-state migration is required before connecting.      │
│ Found 2 TeamSpace blocker(s) across 2 mission(s).                     │
│ Finding codes: FORBIDDEN_KEY                                          │
│                                                                       │
│ Recommended sequence:                                                 │
│   spec-kitty doctor mission-state --audit --fail-on teamspace-blocker │
│   spec-kitty doctor mission-state --fix                               │
│   spec-kitty doctor mission-state --teamspace-dry-run                 │
╰───────────────────────────────────────────────────────────────────────╯
Blocked: `spec-kitty sync now` will not connect until this migration is complete.
```

**This rules out hypothesis 1.** The venv is brand-new (`/tmp/sk-canary-1142/canary-repo/.venv`), `spec-kitty --version` confirms `3.2.0rc14` (the merged-mission CLI carrying the WP01 fix from #1143), and the failure still reproduces. Stale-install hypothesis is not the root cause.

**Hypothesis 2 confirmed by static analysis of the lifecycle emitter surface and a minimal local repro.**

The WP01 predicate ([`src/specify_cli/audit/shape_registry.py:169–198`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/specify_cli/audit/shape_registry.py#L169-L198)) restricts lifecycle classification to rows with `aggregate_type == "Mission"`:

```python
def is_mission_lifecycle_row(row: Mapping[str, Any]) -> bool:
    if not isinstance(row, Mapping):
        return False
    if row.get("aggregate_type") != "Mission":
        return False
    event_type = row.get("event_type")
    return isinstance(event_type, str) and bool(event_type)
```

Static walk across the named emitter surfaces shows **3 distinct non-`Mission` aggregate_types in active lifecycle envelopes** — each fails the predicate:

| File | Line | `aggregate_type` literal | Passes predicate? |
|---|---|---|---|
| `src/specify_cli/status/lifecycle_events.py` | 410 | `"Project"` | **NO** |
| `src/specify_cli/status/lifecycle_events.py` | 459 | `"Mission"` | YES |
| `src/specify_cli/status/lifecycle_events.py` | 521 | `"Mission"` | YES |
| `src/specify_cli/status/lifecycle_events.py` | 562 | `"WorkPackage"` | **NO** |
| `src/specify_cli/dossier/events.py` | 414 | `"MissionDossier"` | **NO** |
| `src/specify_cli/dossier/events.py` | 490 | `"MissionDossier"` | **NO** |
| `src/specify_cli/dossier/events.py` | 555 | `"MissionDossier"` | **NO** |
| `src/specify_cli/dossier/events.py` | 628 | `"MissionDossier"` | **NO** |

All envelopes structurally carry `event_type` as a top-level key (built by `_build_envelope`, `lifecycle_events.py:156–169`). `FORBIDDEN_KEYS = {"event_type", "event_name"}` (`audit/detectors.py:64–69`). `detect_forbidden_keys` (`detectors.py:113–148`) only skips envelopes for which `is_mission_lifecycle_row()` returns True — so every non-`Mission` envelope's structural `event_type` key is flagged as `FORBIDDEN_KEY`.

**Concrete row captured by a minimal local repro** (`spec-kitty init test-project --ai claude` on a fresh tmpdir wrote this to `.kittify/canonical-events.jsonl`):

```json
{
  "aggregate_id": "23860ff5-ad42-484d-bde7-8c327edf9cba",
  "aggregate_type": "Project",
  "event_id": "01KS05J4W9RCFD9J9D03K4DG71",
  "event_type": "ProjectInitialized",
  "payload": { "actor": "spec-kitty init", "project_slug": "test-project", "runtime_version": "3.2.0rc14", ... },
  "project_slug": "test-project",
  "project_uuid": "23860ff5-ad42-484d-bde7-8c327edf9cba",
  "schema_version": "5.0.0",
  "timestamp": "..."
}
```

When the audit (`spec-kitty doctor mission-state --audit`) scans this row, `is_mission_lifecycle_row()` returns False (because `aggregate_type == "Project"`), so `detect_forbidden_keys` flags the top-level `event_type` field and emits a `FORBIDDEN_KEY` finding. The same construction holds for every `WorkPackage` and `MissionDossier` envelope.

### Conclusion

CONFIRMED — Hypothesis 2 explains the failure. The WP01 predicate's `aggregate_type == "Mission"` filter is structurally too narrow; lifecycle envelopes with `aggregate_type` of `Project`, `WorkPackage`, or `MissionDossier` are mis-classified as non-lifecycle rows and trip the `FORBIDDEN_KEYS` rule on their structural `event_type` key.

### Recommendation

**A — open a 1-WP follow-up mission** to broaden the lifecycle-row classifier. The fix surface is well-bounded: extend `is_mission_lifecycle_row` (or rename to `is_lifecycle_row`) to accept the full set `{"Project", "Mission", "WorkPackage", "MissionDossier"}`, possibly via a `LIFECYCLE_AGGREGATE_TYPES` constant co-located with `FORBIDDEN_KEYS` in `audit/detectors.py`. Add unit tests covering one row per aggregate type. Re-run the canary scenarios 1+2 from a trusted runner to verify.

### Notes on state drift discovered during investigation

For future operators picking up similar follow-ups:

1. The scenarios cited in the original issue body live on PR branch `kitty/pr/sync-identity-boundary-deployed-dev-canary-01KRXVW4-to-main` in `Priivacy-ai/spec-kitty-end-to-end-testing` (PR e2e#42, still open). They are **not** on the canary's `main`.
2. The canary scenarios are deployed-dev tests, not local — they need `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, `SPEC_KITTY_E2E_TRUSTED_RUNNER=1`, working `flyctl auth whoami`, and SaaS reachable. The "10 minute clean-venv repro" framing in the original recommendation slightly understated the runtime requirements. The repro is still well within an hour from an authenticated trusted-runner workstation.

---

*Investigated by claude:opus-4-7:researcher-robbie:implementer (orchestrated by HiC) within the 7-day window of mission `investigate-canary-followups-1142-1141-01KS02TV`. Outcome record: `kitty-specs/investigate-canary-followups-1142-1141-01KS02TV/research/outcome-1142.md`. Emitter walk: `.../research/h2-emitter-walk-1142.md`.*
