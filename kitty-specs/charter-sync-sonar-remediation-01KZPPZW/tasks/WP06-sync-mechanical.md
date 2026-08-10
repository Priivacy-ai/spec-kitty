---
work_package_id: WP06
title: Sync mechanical smells
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- NFR-002
planning_base_branch: fix/charter-sync-sonar-remediation
merge_target_branch: fix/charter-sync-sonar-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-sync-sonar-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-sync-sonar-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-sync-sonar-remediation-01KZPPZW
base_commit: 1205f0f748a569725927eb7d07558ef64c237a77
created_at: '2026-08-10T21:14:52.674994+00:00'
subtasks:
- T006
history:
- event: created
  at: '2026-08-10T20:30:00Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent:
- tests/sync/test_sonar_mechanical_helpers.py
execution_mode: code_change
owned_files:
- src/specify_cli/sync/__init__.py
- src/specify_cli/sync/emitter.py
- src/specify_cli/sync/migrate_journal.py
- src/specify_cli/sync/events.py
- src/specify_cli/sync/queue.py
- src/specify_cli/sync/body_queue.py
- src/specify_cli/sync/local_commit.py
- src/specify_cli/sync/runtime.py
- src/specify_cli/sync/consent.py
- src/specify_cli/sync/client.py
- src/specify_cli/sync/restart.py
- src/specify_cli/sync/sharing_client.py
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

Fix ALL Sonar findings in these 12 sync files — mostly mechanical, behavior-preserving, no new suppressions.
Follow the **standard playbook in [tasks.md](../tasks.md)**. Findings (refetch to confirm):

- `S1192` (dup literal → constant): `__init__.py`×4, `queue.py`×2, `body_queue.py`×2, `sharing_client.py`.
- `S7632` (fix/remove malformed suppression comment): `emitter.py`, `migrate_journal.py`×2, `local_commit.py`,
  `runtime.py`, `consent.py`.
- `S107` (too many params — **⚠️ see [post-tasks-squad-findings.md](../post-tasks-squad-findings.md) WP06**):
  group into a small dataclass/params **object** (NOT keyword-only — that does not reduce Sonar's param
  count). `emit_token_usage_recorded` (emitter.py + events.py wrapper) is a **two-layer** signature — thread
  the params-object through BOTH layers. `emit_wp_status_changed` (events.py, 15 params) has **~103 test
  call-sites** — NOT mechanical: bundle ONLY the optional metadata tail (`policy_metadata, force, reason,
  review_ref, execution_mode, evidence, occurred_at, causation_id`) into one optional params object with a
  default, keeping the core positional args so core-only call-sites stay untouched. Give it its own tested slice.
- `S5713` (raise-without-from / redundant except — read the message): `emitter.py`, `queue.py`.
- `S5779` (`events.py:78`, `_ensure_dashboard_sync_daemon`): the `raise AssertionError(...)` inside
  `try/…except Exception` is an unreachable defensive guard swallowed into warning-and-continue.
  **Characterize first** (confirm no control-flow relies on the catch), then replace the `raise
  AssertionError(...)` with a direct `logger.warning(...)` in that branch (same observable outcome —
  behavior-preserving). See the tracer.
- **S1172 (`restart.py`)**: before removing an unused param, check for Protocol/ABC/override/callback contracts
  (grep sibling implementations, not just direct callers); `_`-prefix if it's a contract slot.
- **Suppression-comment gotcha (#3232):** an explanatory/rationale comment must NOT contain a `# noqa:`
  literal — ruff re-flags it.
- `S6353` (regex `\w` with explicit `re.ASCII` if ASCII-only — see #3232 WP04; prove match-equivalent):
  `migrate_journal.py`.
- `S7503` (`client.py`) and `S1172` unused param (`restart.py`) — fix per the concrete finding.

Refetch: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&issueStatuses=OPEN,CONFIRMED&ps=500" | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),i['rule'],'|',i.get('message','')[:80]) for i in json.load(sys.stdin)['issues'] if any(x in i['component'] for x in ['sync/__init__','sync/emitter','migrate_journal','sync/events','sync/queue','body_queue','local_commit','sync/runtime.py','sync/consent','sync/client','sync/restart','sharing_client'])]"`

## Gates
- `ruff check` + `mypy` on all 12 files → clean, no added suppressions (NFR-002).
- `PYTHONPATH=$PWD/src PWHEADLESS=1 python -m pytest tests/sync/ -k "emitter or events or queue or body_queue or migrate or consent or client or restart or sharing or local_commit or sync_init or runtime" -p no:cacheprovider -q` → green (targeted; adjust to reality).

## Review Guidance
- Every finding fixed by a real change; `S107` grouping is behavior-preserving + tested; `S5779` no longer
  swallows the assertion; `S6353` regex proven match-equivalent; no new suppressions.

## Activity Log
- 2026-08-10T20:30:00Z – system – lane=planned – Prompt created.
