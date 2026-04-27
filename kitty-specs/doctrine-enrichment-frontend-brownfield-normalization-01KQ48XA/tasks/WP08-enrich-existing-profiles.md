---
work_package_id: WP08
title: Enrich Existing Profiles
dependencies:
- WP03
- WP04
- WP05
requirement_refs:
- FR-006
- FR-007
- FR-011
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
agent: "claude:sonnet:curator-carla:implementer"
shell_pid: "104942"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: src/doctrine/agent_profiles/shipped/
execution_mode: code_change
owned_files:
- src/doctrine/agent_profiles/shipped/implementer-ivan.agent.yaml
- src/doctrine/agent_profiles/shipped/reviewer-renata.agent.yaml
- src/doctrine/agent_profiles/shipped/architect-alphonso.agent.yaml
- src/doctrine/agent_profiles/shipped/java-jenny.agent.yaml
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Enrich four existing profiles with new tactic and paradigm references introduced in this mission. All changes are additive — append to existing arrays, do not replace existing content.

**Dependencies**: WP03 (`development-bdd` tactic), WP04 (`bug-fixing-checklist`, `test-readability-clarity-check`), WP05 (`behaviour-driven-development` paradigm, `bdd-scenario-lifecycle` procedure) must all be merged before this WP.

**Read each profile file before editing** — the exact YAML structure varies between profiles.

---

## Subtask T027 — Add `bug-fixing-checklist` to `implementer-ivan.agent.yaml`

**File**: `src/doctrine/agent_profiles/shipped/implementer-ivan.agent.yaml`

**Change**: Add one entry to the `tactic-references` array (create the array if absent):

```yaml
tactic-references:
  # ... (existing entries preserved)
  - id: bug-fixing-checklist
    rationale: >
      Enforce test-first defect resolution — write a failing reproduction test before
      modifying production code. All specialist profiles (java-jenny, python-pedro,
      frontend-freddy, node-norris) inherit this discipline.
```

**Also add** to `operating-procedures` (in `collaboration` section, if not already present):
```yaml
    - bug-fixing-checklist
```

**Validation**: Read the file after saving; confirm the new entry is syntactically valid YAML and the `id` matches exactly `bug-fixing-checklist`.

---

## Subtask T028 — Add BDD refs to `reviewer-renata.agent.yaml`

**File**: `src/doctrine/agent_profiles/shipped/reviewer-renata.agent.yaml`

**Changes** (additive only):

1. Add to `tactic-references`:
```yaml
  - id: test-readability-clarity-check
    rationale: >
      Apply the dual-perspective reconstruction check during review: read only the
      test suite and attempt to reconstruct system behavior, then compare against
      the specification. Tests that fail reconstruction are documentation gaps.
  - id: bdd-scenario-lifecycle
    rationale: >
      Verify that every behavior covered in scope has a passing executable scenario
      before approving the WP. Scenarios not yet wired to step definitions block approval.
```

2. Add to `context-sources.doctrine-layers` (if `paradigms` not already listed):
```yaml
    - paradigms
```

3. Add to `context-sources.additional`:
```yaml
    - behaviour-driven-development-paradigm
```

**Rationale**: Renata's review now explicitly includes: (a) test readability reconstruction, and (b) BDD scenario completeness check. This encodes the review workflow described in Scenario C and Scenario E of the spec.

---

## Subtask T029 — Add BDD context to `architect-alphonso.agent.yaml`

**File**: `src/doctrine/agent_profiles/shipped/architect-alphonso.agent.yaml`

**Changes** (additive only):

1. Ensure `paradigms` is in `context-sources.doctrine-layers` (it likely already is — verify):
```yaml
  doctrine-layers:
    - paradigms
    # ... existing layers
```

2. Add to `context-sources.additional`:
```yaml
    - behaviour-driven-development-paradigm
    - example-mapping-workshop-procedure
    - bdd-scenario-lifecycle-procedure
```

3. Add to `tactic-references` (or create if absent):
```yaml
tactic-references:
  - id: development-bdd
    rationale: >
      Use BDD behavioral contract definition during architecture design to express
      observable system boundaries in stakeholder-readable terms. Behavioral contracts
      precede implementation and shape system component boundaries.
```

**Rationale**: Alphonso uses behavioral contracts as a design artifact — `development-bdd` is architecture-level (shapes boundaries), while `behavior-driven-development` is technique-level (testing implementation).

---

## Subtask T030 — Add BDD enrichment to `java-jenny.agent.yaml`

**File**: `src/doctrine/agent_profiles/shipped/java-jenny.agent.yaml`

**Changes** (additive only):

1. Add to `context-sources.doctrine-layers` (if not present):
```yaml
    - paradigms
```

2. Add to `tactic-references`:
```yaml
  - id: behavior-driven-development
    rationale: >
      BDD scenarios define acceptance criteria for Java features. Wire Gherkin
      scenarios via Cucumber-JVM as acceptance tests before implementing production code.
  - id: bdd-scenario-lifecycle
    rationale: >
      Apply the Formulation → Automation lifecycle: write Gherkin first, run red,
      implement minimal production code, run green, publish Serenity BDD report.
```

3. Extend `self-review-protocol.steps` with a new step (append after existing steps):
```yaml
    - name: bdd-scenarios
      command: "mvn verify -Pcucumber"
      gate: all Cucumber/Serenity BDD scenarios in scope pass; no scenario in @wip state
```

**Rationale**: Java Jenny's Java/JVM context makes Cucumber-JVM + Serenity BDD the natural toolchain for BDD acceptance testing. The self-review gate ensures scenarios are green before handoff.

---

## Subtask T031 — Verify all 4 updated profiles pass schema validation

```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from doctrine.agent_profiles.repository import AgentProfileRepository
r = AgentProfileRepository()
profiles = r.load_all()
for pid in ['implementer-ivan', 'reviewer-renata', 'architect-alphonso', 'java-jenny']:
    assert pid in profiles, f'{pid} not found'
    print(f'OK: {pid}')
print('All 4 profiles load successfully')
"
pytest -m doctrine -q
```

**Per-profile validation checklist**:

*implementer-ivan*:
- [ ] `tactic-references` contains `bug-fixing-checklist`
- [ ] `operating-procedures` contains `bug-fixing-checklist`

*reviewer-renata*:
- [ ] `tactic-references` contains `test-readability-clarity-check`
- [ ] `tactic-references` contains `bdd-scenario-lifecycle`
- [ ] `context-sources.doctrine-layers` contains `paradigms`

*architect-alphonso*:
- [ ] `tactic-references` contains `development-bdd`
- [ ] `context-sources.additional` contains BDD-related procedure refs

*java-jenny*:
- [ ] `tactic-references` contains `behavior-driven-development`
- [ ] `tactic-references` contains `bdd-scenario-lifecycle`
- [ ] `self-review-protocol.steps` contains `bdd-scenarios` step

*All profiles*:
- [ ] `pytest -m doctrine -q` green

---

## Branch Strategy

Depends on WP03, WP04, WP05. Merges into `feature/doctrine-enrichment-bdd-profiles`.

```bash
spec-kitty agent action implement WP08 --agent claude
```

---

## Definition of Done

- All 4 profile files modified with additive changes
- No existing content removed or replaced
- All 4 profiles pass schema validation
- Doctrine test suite green

## Reviewer Guidance

- Read each file's diff — all changes must be additive (no existing arrays replaced)
- Verify `implementer-ivan` gains `bug-fixing-checklist` (which cascade-covers all specialists)
- Verify `reviewer-renata` gains both `test-readability-clarity-check` and `bdd-scenario-lifecycle`
- Verify `java-jenny` self-review-protocol has the new Cucumber/Serenity step
- Check that none of the original directives or tactic-references were accidentally removed

## Activity Log

- 2026-04-26T12:49:32Z – claude:sonnet:curator-carla:implementer – shell_pid=104942 – Started implementation via action command
- 2026-04-26T12:57:43Z – claude:sonnet:curator-carla:implementer – shell_pid=104942 – 4 profiles enriched with BDD/bug-fixing refs; doctrine tests green (1163)
- 2026-04-26T12:58:41Z – claude:sonnet:curator-carla:implementer – shell_pid=104942 – Review passed: all 4 profiles load correctly. implementer-ivan gains bug-fixing-checklist (inherited by all specialists). reviewer-renata gains test-readability + bdd-scenario-lifecycle refs. architect-alphonso gains development-bdd tactic ref. java-jenny gains BDD tactic refs + Cucumber self-review step. 1163 tests green.
- 2026-04-26T13:10:37Z – claude:sonnet:curator-carla:implementer – shell_pid=104942 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
