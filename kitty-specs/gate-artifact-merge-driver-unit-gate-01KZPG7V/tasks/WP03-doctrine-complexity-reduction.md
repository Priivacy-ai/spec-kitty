---
work_package_id: WP03
title: Reduce tractable S3776 complexity in doctrine (+ extractor S1192)
dependencies: []
requirement_refs:
- C-004
- FR-006
- FR-007
- NFR-004
- NFR-005
planning_base_branch: fix/gate-artifact-merge-driver-unit-gate
merge_target_branch: fix/gate-artifact-merge-driver-unit-gate
branch_strategy: Planning artifacts for this mission were generated on fix/gate-artifact-merge-driver-unit-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/gate-artifact-merge-driver-unit-gate unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-gate-artifact-merge-driver-unit-gate-01KZPG7V
base_commit: ec37ad919f2cd336fd1532990e1f876425f5170c
created_at: '2026-08-10T19:35:23.178375+00:00'
subtasks:
- T008
- T009
- T010
- T011
history:
- event: created
  at: '2026-08-10T19:04:04Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
owned_files:
- src/doctrine/drg/merge.py
- src/doctrine/drg/validator.py
- src/doctrine/agent_profiles/repository.py
- src/doctrine/drg/org_pack_loader.py
- src/doctrine/base.py
- src/doctrine/versioning.py
- src/doctrine/drg/migration/extractor.py
- tests/doctrine/**
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

Reduce the 7 tractable `python:S3776` (cognitive-complexity > 15) doctrine functions toward ≤15 via clean,
behavior-preserving helper extraction with focused tests, and hoist the single `S1192` dup-literal in
`extractor.py`. **`extractor.py:545` (complexity 183) is OUT OF SCOPE (deferred, C-004).**

**Done when** (FR-007, FR-006, SC-006): each of the 7 functions is at cognitive complexity ≤15 (or carries
a documented, meaningfully-reduced residual with an inline rationale); every extracted helper has focused
tests exercising its branches (Sonar new-code coverage); `extractor.py`'s S1192 is a named constant;
`tests/doctrine/` stays green; `ruff`/`mypy` clean; NO suppressions (NFR-005).

## Context & Constraints

- **The 7 target functions** (verify current line numbers — they shift as you edit):
  | File | ~Line | Complexity → target |
  |------|-------|---------------------|
  | `src/doctrine/drg/merge.py` | 941 | 16 → ≤15 (trivial) |
  | `src/doctrine/drg/org_pack_loader.py` | 746 | 16 → ≤15 (trivial) |
  | `src/doctrine/drg/migration/extractor.py` | 933 | 16 → ≤15 (trivial) |
  | `src/doctrine/drg/validator.py` | 35 | 24 → ≤15 |
  | `src/doctrine/base.py` | 227 | 28 → ≤15 |
  | `src/doctrine/agent_profiles/repository.py` | 365 | 36 → ≤15 |
  | `src/doctrine/versioning.py` | 316 | 65 → ≤15 (hardest) |
- Refetch exact locations: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&rules=python:S3776&issueStatuses=OPEN,CONFIRMED&ps=500" | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),'|',i.get('message','')) for i in json.load(sys.stdin)['issues'] if 'src/doctrine/' in i['component']]"`
- **NFR-004**: behavior-preserving — the existing doctrine tests for each module MUST stay green. Read the
  function's current tests first; a refactor that changes observable behavior is a defect.
- **NFR-005**: no `# noqa: C901`, no `# type: ignore`, no Sonar suppression to pass — extract real helpers.
- **C-004**: scoped to `src/doctrine/` + `tests/doctrine/`. Do NOT touch `extractor.py:545`.

## Subtasks & Detailed Guidance

### Subtask T008 — Extract tested helpers for the 7 S3776 functions (FR-007, NFR-004)

- For each function: identify deterministic sub-phases (a validation block, a lookup/build/emit split, a
  nested-conditional cluster) and extract each into a small, pure, well-named helper with a single
  responsibility. Prefer pure functions with stable inputs/outputs (per the repo's Sonar guidance).
- After each extraction, confirm the parent's cognitive complexity dropped (ruff `C901`/local re-analysis)
  and the module's existing tests stay green.
- **Characterization-test-first (squad fix 1):** before extracting from a function that is NOT already
  covered through a public entry point, add a characterization (behavior-lock) test through the existing
  entry point FIRST, so the refactor is provably a no-op. The two hardest ARE covered
  (`test_versioning.py`, `test_profile_repository.py`); the three trivial 16s may have only incidental
  coverage — lock them before touching.
- **Preserve justified existing suppressions (squad fix 2):** `versioning.py` carries ~6 legitimate
  `# noqa: BLE001` broad-except guards. **Carry them with the relocated code** — NFR-005 forbids ADDING a
  suppression to clear a Sonar finding, NOT preserving an existing justified one. Do not strip them
  (that would red ruff `BLE001`).
- **Extraction sketches (both squad lenses, verified against the real functions):**
  - `versioning.py:316 migrate_v1_to_v2` (65) — breadth, not depth: 3 independent sequential phases.
    Extract `_migrate_provenance_sidecars(...)`, `_migrate_synthesis_manifest(...)`,
    `_stamp_charter_bundle_version(...)` (each returns `(changes, errors)` to merge), factor per-sidecar
    field defaulting into `_apply_v2_sidecar_defaults(...)`, and collapse the 4× repeated
    `io.BytesIO → yaml.dump → write_bytes` block into one `_dump_yaml_safe(path, data, errors)` helper.
    Parent → ~15-line orchestrator merging the returned lists. ≤15 reachable — do NOT defer.
  - `repository.py:365 _load_layer` (36) — a linear per-file gate-chain loop over `sorted(scan)`. Extract
    the loop body into `_parse_profile_from_file(...) -> AgentProfile | None` (records skips internally,
    `continue`→`return None`); optionally split parse vs build (`_parse_profile_yaml` / `_build_profile`).
    Loop drops to ~6. ≤15 easily reachable.
- **Documented residual (safety valve, unlikely needed):** if a genuine ≤15 is unreachable without harming
  clarity/behavior, reduce as far as is clean and leave a one-line inline rationale (an inline rationale is
  NOT a suppression; it does not violate NFR-005). Sonar is advisory (SC-006 accepts a documented residual).

### Subtask T009 — Hoist extractor.py's S1192 dup-literal (FR-006)

- The single `S1192` in `extractor.py` (≈line 267 — refetch to confirm) → one named module constant
  referenced at all sites (same discipline as WP02). Behavior-preserving.
- **37-total reconciliation (squad fix 3):** WP02 clears 36 in `hand_authored_overlay.py`, this WP clears
  the extractor one. If the live S1192 distribution differs from 36/1, WP02+WP03 together must still clear
  ALL doctrine S1192 (SC-005 = 0 from 37); neither WP stops at its stated count — a residual must not fall
  between the two owners.

### Subtask T010 — (reserved) — no work; the 3 minor smells are WP04

### Subtask T011 — Focused helper tests + verify (NFR-004, SC-006)

- Add focused unit tests for each extracted helper (exercise its branches directly) under the matching
  `tests/doctrine/...` path. This is required — Sonar's project gate is dominated by new-code coverage, and
  the repo's Sonar expectations require tests in the same PR as extracted helpers.
- Run the touched modules' tests (TARGETED — never the whole `tests/doctrine/` dir in one shot if it's
  heavy; run per-subdir):
  `PWHEADLESS=1 python -m pytest tests/doctrine/drg/ tests/doctrine/agent_profiles/ tests/doctrine/ -k "<relevant>" -p no:cacheprovider -q` — green.
- `ruff check` (incl. `C901` complexity) + `mypy` on all touched files — zero issues, no suppressions.

## Risks & Mitigations

- **Behavior drift**: read + run each function's existing tests before and after; refactor is a no-op on behavior.
- **Complexity not reaching 15** (`versioning.py`): partial reduction + documented residual is acceptable; never suppress.
- **Un-owned edit**: stay within the owned files; the 3 minors are WP04, `extractor.py:545` is deferred.

## Review Guidance

- Each extracted helper is pure/small, named for intent, and has a focused test.
- Existing doctrine tests unchanged and green (behavior-preserving).
- No suppressions; confirm via Sonar query that S3776 count for the 7 functions dropped (or a documented residual).

## Activity Log

- 2026-08-10T19:04:04Z – system – lane=planned – Prompt created.
