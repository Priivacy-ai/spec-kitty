---
work_package_id: WP04
title: Refactor-stable doctrine styleguide + DRG
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: tidy/gate-substrate
merge_target_branch: tidy/gate-substrate
branch_strategy: Planning artifacts for this mission were generated on tidy/gate-substrate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/gate-substrate unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
phase: Phase 1 - Parallel substrate work
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1709664"
history:
- at: '2026-07-03T06:37:42Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/styleguides/built-in/testing-principles.styleguide.yaml
- src/doctrine/graph.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Refactor-stable doctrine styleguide + DRG

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

CT8 (#2310, spec FR-006): the operator's refactor-stable testing rulings become
first-class governance in `testing-principles.styleguide.yaml`, with `graph.yaml`
regenerated in the same change (two byte-freshness gates enforce it). Success = both
freshness gates green + the acceptance-time content script confirms ≥6 named
principles, each with non-empty good/bad examples, ≥1 citing PR #2308.

## Context & Constraints

Read FIRST:
- `research.md` D6 (mechanics: file, schema, activation, `generate_graph` at
  src/doctrine/drg/migration/extractor.py:767, the two freshness gates) and D7 (the
  six-principle content outline — your authoring skeleton).
- The existing styleguide file — match its voice, structure, and example style
  exactly (it already carries e.g. the realistic-test-data rule; the new content
  joins, never rewrites, the existing principles).
- The source rulings (quote-grounding): the operator's 2026-07-03 statements —
  "if our architecture / acceptance tests need to change on every cleanup/refactor:
  they are not good tests" and "no frivolous LOC tests; we have Sonar for those" —
  and the PR #2308 precedents (LOC-gate retirement commit 052d465e9;
  literal-scan deletion commit 50abe2fdc; the quarantine adjudication).

Constraints: C-001 applies to the styleguide's OWN examples — bad-examples are quoted
illustrative content, never live scans; NO standing content-coupled suite test is
added (the content check is the T018 acceptance-time script); graph.yaml only via
`generate_graph` (C-004); terminology canon in all prose.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/gate-substrate
- **Merge target branch**: tidy/gate-substrate

## Subtasks & Detailed Guidance

### Subtask T016 – Author the principles + patterns/anti_patterns

- **Steps**: Add to `testing-principles.styleguide.yaml` (schema: `principles` string
  list; `patterns`/`anti_patterns` as {name, description, good_example, bad_example}):
  1. Six principles per research D7: invariants-over-shape;
     negative-and-behavioral-forms-first; size-metrics-belong-to-sonar;
     convert-or-delete-never-re-pin (with surviving-coverage proof);
     shrink-only-count-ratchets-are-sanctioned;
     transitional-shape-guards-need-a-retirement-path.
  2. At least two pattern entries (e.g. "content-pinned gate keys (Design-P)" with the
     frozen-composite good example vs the raw-line bad example; "negative AST
     invariant" with the forbidden-pattern scan good example vs the positive
     literal-presence bad example).
  3. At least one anti-pattern entry citing the PR #2308 precedents concretely (the
     retired LOC ceiling; the twice-broken literal scan that was deleted with
     surviving-coverage proof).
  4. Keep it additive — existing principles/patterns untouched.
- **Files**: the styleguide YAML.

### Subtask T017 – generate_graph regeneration + freshness gates

- **Steps**:
  1. Regenerate: `python -c "import sys; sys.path.insert(0,'src'); from pathlib import
     Path; from doctrine.drg.migration.extractor import generate_graph;
     generate_graph(Path('src/doctrine'), Path('src/doctrine/graph.yaml'))"`.
  2. Run BOTH freshness gates: `PWHEADLESS=1 pytest
     tests/doctrine/drg/migration/test_extractor.py
     tests/doctrine/drg/migration/test_path_ref_resolver.py -q` — byte-green.
  3. If the regenerated graph is byte-identical (no new edge-bearing metadata),
     commit only the styleguide; record that outcome.
- **Files**: `src/doctrine/graph.yaml` (possibly unchanged).

### Subtask T018 – Acceptance-time content-check script

- **Steps** (contract corrected to the REAL schema — `principles` is a flat STRING
  list; only patterns/anti_patterns carry examples): Write
  `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/doctrine_content_check.py`
  (mission artifact, NOT a suite test) asserting ALL of:
  (a) ≥6 NEW principle strings matching the D7 topics, each substantive — minimum
  length ~80 chars, no "TODO"/placeholder markers;
  (b) ≥2 new `patterns` AND ≥1 new `anti_patterns` entries, each with BOTH
  `good_example` and `bad_example` non-empty;
  (c) ≥1 entry literally citing `#2308` or one of its commits;
  (d) additive-only: every pre-existing principle/pattern string still present
  verbatim (snapshot the pre-edit list inside the script).
  Run it, paste the output into the Activity Log; WP06 wires it into the
  acceptance-matrix FR-006 evidence.
- **Files**: the mission-dir script (commits with planning artifacts — note the
  lane-hygiene guard may require committing it on the PLANNING branch from the primary
  checkout; the WP02-degod precedent applies).

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"; PYTHONPATH="$PWD/src"
PWHEADLESS=1 pytest tests/doctrine/drg/migration/test_extractor.py tests/doctrine/drg/migration/test_path_ref_resolver.py -q
PWHEADLESS=1 pytest tests/doctrine/ -q -p no:cacheprovider   # neighbor sweep
python kitty-specs/refactor-stable-gate-substrate-01KWK3FY/doctrine_content_check.py
```

## Risks & Mitigations

- **Byte-freshness drift**: never hand-edit graph.yaml; regenerate only.
- **Terminology guard**: the styleguide is user-facing prose — run
  `pytest tests/architectural/test_no_legacy_terminology.py` before handoff.
- **Voice mismatch**: mirror the existing entries' tone/length; this file is read by
  agents at doctrine-load time — brevity is a feature.

## Review Guidance

- Both freshness gates green; content script output in the log.
- The six principles are faithful to the operator rulings (quote-check against the
  research grounding).
- The bad-examples are quoted content (C-001) — not live scans.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T06:37:42Z – system – Prompt created.
- 2026-07-03T07:12:11Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – Assigned agent via action command
- 2026-07-03T07:27:28Z – claude:opus:python-pedro:implementer – shell_pid=1660876 – Ready for review: 6 refactor-stable principles + 2 patterns + 1 anti-pattern added to testing-principles.styleguide.yaml (testing-principles styleguide). graph.yaml byte-identical after regen. Freshness gates: 76/76 green. Doctrine sweep: 2393/2393 green. Terminology guard: 3/3 green. Content script ALL ASSERTIONS PASSED (19 total principles, 5 patterns, 5 anti_patterns). PR #2308 cited in The Literal-Scan Trap anti-pattern. Lane commit edbc78007.
- 2026-07-03T07:28:12Z – claude:opus:reviewer-renata:reviewer – shell_pid=1709664 – Started review via action command
- 2026-07-03T07:33:23Z – user – shell_pid=1709664 – Review passed: additive-only (98/0, zero deletions); 6 refactor-stable principles faithfully encode operator rulings (invariants-over-shape; Sonar-owns-size no-LOC-tests; convert-or-delete-with-surviving-coverage never re-pin; shrink-only ratchets sanctioned; transitional guards need retirement path; negative-and-behavioral-forms-first) + 2 patterns + 1 anti-pattern citing PR #2308 (052d465e9/50abe2fdc); C-001 self-conformance (bad_examples quoted YAML literals, no standing content-coupled suite test); graph.yaml byte-identical (regen clean + freshness 76/76 green); terminology 3/3; content-check exit 0 against LANE edited YAML (6 new principles/2 patterns/1 anti-pattern); no changes outside owned_files.
