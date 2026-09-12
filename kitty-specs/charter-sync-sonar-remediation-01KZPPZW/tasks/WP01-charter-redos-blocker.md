---
work_package_id: WP01
title: Charter ReDoS BLOCKER + token_budget complexity
dependencies: []
requirement_refs:
- C-001
- FR-001
- FR-002
- NFR-001
- NFR-003
planning_base_branch: fix/charter-sync-sonar-remediation
merge_target_branch: fix/charter-sync-sonar-remediation
branch_strategy: Planning artifacts for this mission were generated on fix/charter-sync-sonar-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/charter-sync-sonar-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-sync-sonar-remediation-01KZPPZW
base_commit: 1205f0f748a569725927eb7d07558ef64c237a77
created_at: '2026-08-10T21:10:27.048540+00:00'
subtasks:
- T001
history:
- event: created
  at: '2026-08-10T20:30:00Z'
  actor: architect-alphonso
agent_profile: python-pedro
authoritative_surface: src/charter/context_renderers/
create_intent:
- tests/charter/context_renderers/test_token_budget_sonar.py
execution_mode: code_change
owned_files:
- src/charter/context_renderers/token_budget.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile
```
/ad-hoc-profile-load python-pedro
```
---

## Objective (P1 — the BLOCKER)

`src/charter/context_renderers/token_budget.py` has two Sonar findings:
- **`S8786` (BLOCKER) at `:308`** — a regex with **super-linear backtracking** (ReDoS-class). Simplify it to
  linear time WITHOUT changing what it matches.
- **`S3776` at `:365`** (cognitive complexity 28) — reduce to ≤15 via tested helper extraction.

Refetch exact lines: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=Priivacy-ai_spec-kitty&rules=python:S8786,python:S3776&issueStatuses=OPEN,CONFIRMED&ps=500" | python3 -c "import sys,json;[print(i['component'].split(':',1)[1]+':'+str(i.get('line')),i['rule'],'|',i.get('message','')) for i in json.load(sys.stdin)['issues'] if 'token_budget' in i['component']]"`

## ⚠️ AUTHORITATIVE: [post-tasks-squad-findings.md](../post-tasks-squad-findings.md) — read the WP01 section first.

## Guidance (CORRECTED per squad — the regex is NOT catastrophic)

- **The regex (FR-001, NFR-003):** the flagged pattern is `re.compile(r"^###\s+(.+?)\s*$")` — the Sonar
  trigger is the static `.`/`\s` **overlap** (ambiguous partition), NOT exponential backtracking. Empirically
  the OLD pattern is already fast (worst case quadratic; the real input is a single short heading line). So
  **do NOT try to prove "adversarial input slow on old, fast on new" — it doesn't exist.** Reframe NFR-003
  as: remove the `.`/`\s` overlap. **Recommended rewrite:** `^###\s+(\S.*?)\s*$` (capture must start
  non-space → linear).
- **Proof = match-equivalence** (not timing), in `test_token_budget_sonar.py`: assert the new and old
  patterns produce identical results across representative + random inputs (keep the OLD pattern inline as
  the oracle). **Cover the one intentional divergence:** on `"###    "` (marker + only whitespace) the old
  captures `' '`, the rewrite returns `None` — document it as an intentionally-dropped dead input.
- **The complexity (FR-002):** extract deterministic helpers (per the standard playbook in tasks.md) to
  bring `:365` to ≤15; add focused tests for the helpers. Read+run the existing token_budget tests first;
  behavior identical.

## Gates
- `ruff check --select C901 src/charter/context_renderers/token_budget.py` → zero.
- `ruff check` + `mypy` on the file → clean, no added suppressions (NFR-002).
- `PYTHONPATH=$PWD/src PWHEADLESS=1 python -m pytest tests/charter/ -k "token_budget" -p no:cacheprovider -q` → green.

## Review Guidance
- The regex removes the `.`/`\s` overlap and is provably match-equivalent (the `"###    "` divergence is
  documented as an intentionally-dropped dead input). Do NOT expect/require a timing improvement.
- `:365` ≤15 via real helper extraction with tests; behavior unchanged.

## Activity Log
- 2026-08-10T20:30:00Z – system – lane=planned – Prompt created.
