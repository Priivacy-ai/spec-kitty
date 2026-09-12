---
work_package_id: WP03
title: Charter complexity group B
dependencies: []
requirement_refs:
- FR-002
- FR-003
- FR-004
- FR-005
- NFR-001
- NFR-002
planning_base_branch: fix/charter-sync-sonar-remediation
merge_target_branch: fix/charter-sync-sonar-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-sync-sonar-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-sync-sonar-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-sync-sonar-remediation-01KZPPZW
base_commit: 1205f0f748a569725927eb7d07558ef64c237a77
created_at: '2026-08-10T21:12:40.332465+00:00'
subtasks:
- T003
history:
- event: created
  at: '2026-08-10T20:30:00Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent:
- tests/charter/test_sonar_complexity_b_helpers.py
execution_mode: code_change
owned_files:
- src/charter/synthesizer/write_pipeline.py
- src/specify_cli/charter_activate.py
- src/charter/synthesizer/interview_mapping.py
- src/charter/context_renderers/section_bodies.py
- src/charter/context_renderers/profile_sections.py
- src/specify_cli/charter_runtime/lint/checks/contradiction.py
- src/specify_cli/charter_runtime/lint/checks/reference_integrity.py
- src/charter/kind_vocabulary.py
- src/charter/interview.py
- src/charter/context_renderers/bootstrap_text.py
- src/charter/pack_manager.py
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

Fix ALL Sonar findings in these 11 charter files (behavior-preserving; no new suppressions). Follow the
**standard playbook in [tasks.md](../tasks.md)**. Findings (refetch to confirm current lines):

| File | Findings |
|------|----------|
| `src/charter/synthesizer/write_pipeline.py` | `S3776`:451 (23) |
| `src/specify_cli/charter_activate.py` | `S3776`:106 (24) |
| `src/charter/synthesizer/interview_mapping.py` | `S3776`:208 (18) |
| `src/charter/context_renderers/section_bodies.py` | `S3776`:148 (18) |
| `src/charter/context_renderers/profile_sections.py` | `S3776`:150 (18) + `S3776`:416 (17) + `S1192` |
| `src/specify_cli/charter_runtime/lint/checks/contradiction.py` | `S3776`:53 (18) |
| `src/specify_cli/charter_runtime/lint/checks/reference_integrity.py` | `S3776`:88 (17) |
| `src/charter/kind_vocabulary.py` | `S3776`:142 (16) |
| `src/charter/interview.py` | `S3776`:354 (16) |
| `src/charter/context_renderers/bootstrap_text.py` | `S3776`:165 (19) + `S7632` |
| `src/charter/pack_manager.py` | `S3776`:662 (16) + `S3516` (method-always-returns-same-value) + `S1172` (unused param) |

## ⚠️ AUTHORITATIVE: [post-tasks-squad-findings.md](../post-tasks-squad-findings.md) — read the WP03 section.

## Discipline
- `S3776` (12 functions — the biggest complexity lane) → tested helper extraction to ≤15; **read+run each
  function's existing tests before/after; add a characterization test FIRST where coverage is thin**; helpers
  tested in `test_sonar_complexity_b_helpers.py` or the module's test file; behavior identical.
- `S1192` → constant. `S7632` → fix/remove (an explanatory comment must NOT contain a `# noqa:` literal — ruff
  re-flags it, #3232).
- **`S3516` (pack_manager.py:559 `deactivate`) is likely STALE/FALSE-POSITIVE** — it already has a single
  `return result` (input-varying `ActivationResult`) + a prior "(S3516 → single return)" comment. There is no
  clean behavior-preserving code fix. Re-run Sonar; if it persists, mark won't-fix in the SonarCloud UI with
  rationale + call it out in the PR body (per CLAUDE.md). Do NOT contort correct code. Before dropping ANY
  return for S3516, grep callers for return-value consumption (assignment/boolean-test/chaining) — keep it if consumed.
- **`S1172`** → before removing an unused param, check for Protocol/ABC/override/callback contracts (grep
  sibling implementations, not just direct callers); `_`-prefix if it's a contract slot, do NOT remove.

## Gates
- `ruff check --select C901` on the 11 files → zero. `ruff check` + `mypy` → clean, no added suppressions.
- `PYTHONPATH=$PWD/src PWHEADLESS=1 python -m pytest tests/charter/ tests/specify_cli/charter_lint tests/specify_cli/charter_preflight -k "write_pipeline or charter_activate or interview or section_bodies or profile_sections or contradiction or reference_integrity or kind_vocabulary or bootstrap or pack_manager" -p no:cacheprovider -q` → green (targeted; adjust paths to reality).

## Review Guidance
- Every `S3776` ≤15 via real helpers with tests; `S3516`/`S1172` fixed not suppressed; existing tests green.

## Activity Log
- 2026-08-10T20:30:00Z – system – lane=planned – Prompt created.
