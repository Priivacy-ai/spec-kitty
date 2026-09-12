---
work_package_id: WP05
title: Sync complexity
dependencies: []
requirement_refs:
- FR-006
- FR-008
- FR-009
- NFR-001
- NFR-002
planning_base_branch: fix/charter-sync-sonar-remediation
merge_target_branch: fix/charter-sync-sonar-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-sync-sonar-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-sync-sonar-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-sync-sonar-remediation-01KZPPZW
base_commit: 1205f0f748a569725927eb7d07558ef64c237a77
created_at: '2026-08-10T21:14:30.382381+00:00'
subtasks:
- T005
history:
- event: created
  at: '2026-08-10T20:30:00Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_sonar_complexity_helpers.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/dossier_pipeline.py
- src/specify_cli/sync/runtime_event_emitter.py
- src/specify_cli/sync/body_upload.py
- src/specify_cli/sync/owner.py
- src/specify_cli/sync/orphan_sweep.py
- src/specify_cli/sync/background.py
- src/specify_cli/sync/classification.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load python-pedro
```
---

## Objective

Fix ALL Sonar findings in these 7 sync files (behavior-preserving; no new suppressions). Follow the
**standard playbook in [tasks.md](../tasks.md)**. Findings (refetch to confirm):

| File | Findings |
|------|----------|
| `src/specify_cli/sync/dossier_pipeline.py` | `S3776`:38 (33 — heaviest) + `S8572`×2 |
| `src/specify_cli/sync/runtime_event_emitter.py` | `S3776`:186 (21) |
| `src/specify_cli/sync/body_upload.py` | `S3776`:212 (19) |
| `src/specify_cli/sync/owner.py` | `S3776`:925 (17) |
| `src/specify_cli/sync/orphan_sweep.py` | `S3776`:705 (17) |
| `src/specify_cli/sync/background.py` | `S3776`:776 (17) + `S7632` + `S1172` (unused param) |
| `src/specify_cli/sync/classification.py` | `S3776`:359 (16) |

Refetch: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&issueStatuses=OPEN,CONFIRMED&ps=500" | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),i['rule'],'|',i.get('message','')[:80]) for i in json.load(sys.stdin)['issues'] if any(x in i['component'] for x in ['dossier_pipeline','runtime_event_emitter','body_upload','sync/owner','orphan_sweep','sync/background','sync/classification'])]"`

## Discipline
- `S3776` → tested helper extraction to ≤15 (helpers tested in `test_sonar_complexity_helpers.py` or the
  module's test file); read+run each function's existing tests before/after; behavior identical.
- `S8572` (dossier_pipeline.py:83,:194) — **⚠️ [tracer](../post-tasks-squad-findings.md) WP05:** it's
  `logger.error(msg, e)` → `logger.exception(msg)` (drop the `e` arg; adds a traceback — check no sync
  log-assertion test pins exact log text). `S7632` → fix/remove. `S1172` → remove unused param, but check
  Protocol/ABC/callback contracts first (grep sibling impls); `_`-prefix if a contract slot.
- **dossier_pipeline.py:38 (33):** decompose by its 4 sequential `try/except`-wrapped steps — each extracted
  helper MUST retain its own try/except (per-step failure isolation) and thread back the `events_emitted`
  counter / `errors` list. See the tracer.
- **orphan_sweep.py / background.py (daemon/port-sensitive):** extract ONLY the decision/partition branches;
  leave the port/timing I/O (sweep, safe-to-sweep, shutdown→terminate→kill escalation, drain, sleeps/timeouts)
  BYTE-IDENTICAL so `tests/sync/test_orphan_sweep.py` (real-port, `-n0`) stays timing-stable.
- **Characterize first** where a target function's existing coverage is thin; read+run its tests before/after.
- ⚠️ Some sync tests use real ports/daemons (`tests/sync/test_orphan_sweep.py`) — run those serially `-n0`
  if needed; keep behavior identical (these are timing/daemon-sensitive).

## Gates
- `ruff check --select C901` on the 7 files → zero. `ruff check` + `mypy` → clean, no added suppressions.
- `PYTHONPATH=$PWD/src PWHEADLESS=1 python -m pytest tests/sync/ -k "dossier or emitter or body_upload or owner or orphan or background or classification" -p no:cacheprovider -q` → green (targeted; the orphan-sweep real-port test may need `-n0`).

## Review Guidance
- Every `S3776` ≤15 via real helpers with tests; behavior-preserving (esp. the daemon/port-sensitive paths).

## Activity Log
- 2026-08-10T20:30:00Z – system – lane=planned – Prompt created.
