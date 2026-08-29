---
work_package_id: WP04
title: Charter mechanical smells
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- NFR-002
planning_base_branch: fix/charter-sync-sonar-remediation
merge_target_branch: fix/charter-sync-sonar-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-sync-sonar-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-sync-sonar-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-sync-sonar-remediation-01KZPPZW
base_commit: 1205f0f748a569725927eb7d07558ef64c237a77
created_at: '2026-08-10T21:13:35.399795+00:00'
subtasks:
- T004
history:
- event: created
  at: '2026-08-10T20:30:00Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
owned_files:
- src/charter/activation/pack_context.py
- src/specify_cli/charter_runtime/freshness/computer.py
- src/specify_cli/charter_runtime/preflight/runner.py
- src/charter/activation/context_renderers/reference_pointers.py
- src/charter/activation/context_json.py
- src/charter/activation/context_renderers/activation_block.py
- src/charter/activation/context_renderers/artifact_bodies.py
- src/charter/activation/context_renderers/selection_block.py
- src/charter/activation/doctrine_service_builder.py
- src/charter/activation/action_grain.py
- src/charter/activation/default_pack.py
- src/charter/activation/synthesizer/manifest.py
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

Fix ALL Sonar findings in these 12 charter files — mechanical, behavior-preserving, no new suppressions.
Follow the **standard playbook in [tasks.md](../tasks.md)**. Findings (refetch to confirm):

- `S7632` (malformed suppression comment → fix syntax + keep with rationale, or REMOVE if unnecessary; no
  `# noqa:` literal left inside a prose comment): `pack_context.py`×2, `preflight/runner.py`,
  `reference_pointers.py`, `context_json.py`, `doctrine_service_builder.py`, `action_grain.py`, `default_pack.py`.
- `S1192` (dup literal → named constant): `freshness/computer.py`×2, `context_renderers/artifact_bodies.py`,
  `context_renderers/selection_block.py`.
- `S1172` (unused param → remove or `_`-prefix; read callers first): `preflight/runner.py`, `activation_block.py`.
- **`S5890` (`synthesizer/manifest.py:89`) is a Pydantic `PrivateAttr` FALSE-POSITIVE** (⚠️
  [tracer](../post-tasks-squad-findings.md) WP04): `_raw_field_names: frozenset[str] | None =
  PrivateAttr(default=None)` is idiomatic Pydantic v2; Sonar mis-infers the RHS type. No behavior-preserving
  code fix keeps both typing and Pydantic semantics. Disposition: UI won't-fix with rationale + PR-body
  callout (SC-001 "documented residual"). Do NOT mandate a code edit here.
- **`S1172`** (`preflight/runner.py`, `activation_block.py`): before removing an unused param, check for
  Protocol/ABC/override/callback contracts (grep sibling implementations); `_`-prefix if it's a contract slot.

Refetch: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&issueStatuses=OPEN,CONFIRMED&ps=500" | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),i['rule'],'|',i.get('message','')[:80]) for i in json.load(sys.stdin)['issues'] if any(x in i['component'] for x in ['pack_context','freshness/computer','preflight/runner','reference_pointers','context_json','activation_block','artifact_bodies','selection_block','doctrine_service_builder','action_grain','default_pack','synthesizer/manifest'])]"`

## Gates
- `ruff check` + `mypy` on all 12 files → clean, no added suppressions (NFR-002).
- `PYTHONPATH=$PWD/src PWHEADLESS=1 python -m pytest tests/charter/ tests/specify_cli/charter_freshness tests/specify_cli/charter_preflight -p no:cacheprovider -q` → green (targeted to touched modules; adjust to reality — do not run the whole tree if heavy).

## Review Guidance
- Every finding fixed by a real change (no new suppressions); behavior unchanged; constants replace real repeats.

## Activity Log
- 2026-08-10T20:30:00Z – system – lane=planned – Prompt created.
