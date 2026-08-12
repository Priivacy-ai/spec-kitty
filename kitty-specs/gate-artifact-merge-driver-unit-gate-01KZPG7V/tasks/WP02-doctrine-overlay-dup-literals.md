---
work_package_id: WP02
title: Clear S1192 dup-literals in doctrine hand_authored_overlay
dependencies: []
requirement_refs:
- C-004
- FR-006
- NFR-004
- NFR-005
planning_base_branch: fix/gate-artifact-merge-driver-unit-gate
merge_target_branch: fix/gate-artifact-merge-driver-unit-gate
branch_strategy: Planning artifacts for this mission were generated on fix/gate-artifact-merge-driver-unit-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/gate-artifact-merge-driver-unit-gate unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-gate-artifact-merge-driver-unit-gate-01KZPG7V
base_commit: ec37ad919f2cd336fd1532990e1f876425f5170c
created_at: '2026-08-10T19:33:52.743168+00:00'
subtasks:
- T006
- T007
history:
- event: created
  at: '2026-08-10T19:04:04Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/drg/migration/hand_authored_overlay.py
role: implementer
tags: []
tracker_refs:
- '#3232'
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objectives & Success Criteria

Clear the 36 `python:S1192` (repeated-literal) Sonar HIGH findings in
`src/doctrine/drg/migration/hand_authored_overlay.py` by hoisting each repeated non-trivial literal to a
single named module constant referenced at every site. **Behavior-preserving** — no logic change.

**Done when** (FR-006, SC-005): a fresh Sonar analysis reports 0 open `S1192` in this file; `ruff`/`mypy`
clean; the doctrine tests that exercise this module stay green.

## Context & Constraints

- **NFR-005**: no `# noqa`/`# type: ignore`/Sonar-suppression to clear a finding — hoist the literal, don't silence it.
- **NFR-004 / C-004**: no behavior change; scoped to this one file.
- **Ownership boundary (squad fix 4)**: this WP is behavior-preserving and adds NO new tests. WP03 owns
  `tests/doctrine/**`; do NOT create a test file under `tests/doctrine/` (it would collide with WP03).
  Verify via the existing suite only.
- The exact S1192 sites (each names the duplicated literal + the lines it repeats on) are in SonarCloud.
  Fetch them precisely:
  ```bash
  curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&rules=python:S1192&issueStatuses=OPEN,CONFIRMED&ps=500" \
    | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),'|',i.get('message','')) for i in json.load(sys.stdin)['issues'] if 'hand_authored_overlay' in i['component']]"
  ```

## Subtasks & Detailed Guidance

### Subtask T006 — Hoist repeated literals to named constants (FR-006)

- For each S1192 finding, identify the duplicated literal (string/path/message), define ONE
  `UPPER_SNAKE_CASE` module-level constant with a descriptive name near the top of the module, and replace
  every occurrence with the constant. Group related constants logically.
- Prefer names that document intent (e.g. `_OVERLAY_KIND_KEY = "kind"`), not `_LITERAL_1`.
- Do not merge literals that are only coincidentally equal (a `"kind"` key and a `"kind"` in a message
  that happen to match but mean different things) — Sonar flags per-literal; keep semantically-distinct
  duplicates as separate constants if they read more clearly that way. Judgement over mechanical dedupe.

### Subtask T007 — Verify behavior-preserving (NFR-004, NFR-005)

- `ruff check` + `ruff format --check` + `mypy` on the file — zero issues, no suppressions added.
- Run the module's tests (targeted, not the whole suite):
  `PWHEADLESS=1 python -m pytest tests/doctrine/drg/migration/ -p no:cacheprovider -q` (adjust to the
  actual test path that imports this module) — green.

## Review Guidance

- Every constant replaces ≥2–3 real occurrences (not a single-use "constant").
- No behavior change; no suppressions; names are descriptive.
- Confirm via the Sonar query that S1192 count for this file dropped to 0.

## Activity Log

- 2026-08-10T19:04:04Z – system – lane=planned – Prompt created.
