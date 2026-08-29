---
work_package_id: WP02
title: Charter complexity group A
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
- NFR-001
- NFR-002
planning_base_branch: fix/charter-sync-sonar-remediation
merge_target_branch: fix/charter-sync-sonar-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-sync-sonar-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-sync-sonar-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-sync-sonar-remediation-01KZPPZW
base_commit: 1205f0f748a569725927eb7d07558ef64c237a77
created_at: '2026-08-10T21:11:27.226395+00:00'
subtasks:
- T002
history:
- event: created
  at: '2026-08-10T20:30:00Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_sonar_complexity_a_helpers.py
execution_mode: code_change
owned_files:
- src/charter/activation/evidence/code_reader.py
- src/specify_cli/charter_runtime/lint/checks/org_layer.py
- src/charter/activation/context.py
- src/charter/activation/context_renderers/catalog_diagnosis.py
- src/charter/activation/compiler.py
- src/charter/activation/consistency_check.py
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

Fix ALL Sonar findings in these 6 charter files (behavior-preserving; no new suppressions). Follow the
**standard playbook in [tasks.md](../tasks.md)**. Per-file findings (refetch to confirm current lines):

| File | Findings |
|------|----------|
| `src/charter/activation/evidence/code_reader.py` | `S3776`:182 (complexity 33 — the heaviest; extract tested helpers to ≤15) |
| `src/specify_cli/charter_runtime/lint/checks/org_layer.py` | `S3776`:64 (29) + `S1192` (dup literal → constant) |
| `src/charter/activation/context.py` | `S3776`:127 (19) + `S3776`:363 (19) — two functions |
| `src/charter/activation/context_renderers/catalog_diagnosis.py` | `S3776`:61 (20) |
| `src/charter/activation/compiler.py` | `S3776`:1216 (20) |
| `src/charter/activation/consistency_check.py` | `S3776`:485 (22) + `S7632`×4 (malformed suppression comments → fix/remove) |

Refetch: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&issueStatuses=OPEN,CONFIRMED&ps=500" | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),i['rule'],'|',i.get('message','')[:80]) for i in json.load(sys.stdin)['issues'] if any(x in i['component'] for x in ['code_reader','org_layer','charter/context.py','catalog_diagnosis','charter/compiler','consistency_check'])]"`

## Discipline
- `S3776` → tested helper extraction to ≤15; read+run each function's existing tests before/after (add a
  characterization test first where coverage is thin); each helper gets a focused test in
  `tests/charter/test_sonar_complexity_a_helpers.py` (or the module's existing test file). Behavior identical.
- `S1192` → named constant. `S7632` → fix syntax (keep + rationale) or remove; no `# noqa:` literal in prose.

## Gates
- `ruff check --select C901` on the 6 files → zero. `ruff check` + `mypy` → clean, no added suppressions.
- `PYTHONPATH=$PWD/src PWHEADLESS=1 python -m pytest tests/charter/ -k "code_reader or org_layer or context or catalog or compiler or consistency" -p no:cacheprovider -q` → green (targeted).

## Review Guidance
- Every `S3776` function ≤15 via real helpers with tests; existing charter tests green (behavior-preserving).
- No new suppressions; constants replace real repeats.

## Activity Log
- 2026-08-10T20:30:00Z – system – lane=planned – Prompt created.
