---
work_package_id: WP03
title: Doctrine / glossary anchor + tactic repair
dependencies: []
requirement_refs:
- FR-005
tracker_refs: []
planning_base_branch: feat/pre-doctrine-stabilization-remediation
merge_target_branch: feat/pre-doctrine-stabilization-remediation
branch_strategy: Planning artifacts for this mission were generated on feat/pre-doctrine-stabilization-remediation. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/pre-doctrine-stabilization-remediation unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-pre-doctrine-test-stabilization-01KSMG8Y
base_commit: fcec446d1be3c2c67d5ce9f0bc36a40133fe6684
created_at: '2026-05-27T12:19:12.586234+00:00'
subtasks:
- T009
- T010
- T011
- T012

shell_pid: "37654"
agent: "claude:claude-sonnet-4-6:curator-carla:implementer"
history:
- date: '2026-05-27'
  event: created
agent_profile: curator-carla
authoritative_surface: src/doctrine/
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- src/doctrine/glossary/**
- src/doctrine/tactics/built-in/five-paradigm-parallel-debugging.tactic.yaml
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

---

## Objective

Add two missing glossary anchors (`doctrine-pack` and `platform-darwin--platform-linux`) and fix the `five-paradigm-parallel-debugging.tactic.yaml` schema violations. All four failing doctrine tests in `test_glossary_link_integrity` and `test_tactic_compliance` must pass after this WP.

**Closes**: GitHub issue #1304

---

## Context

The doctrine glossary is a YAML-based knowledge structure where entries can reference each other via anchors. Two expected anchors are missing, causing link-integrity tests to fail. The five-paradigm tactic file has schema violations and references unresolved terms.

The root causes were identified by the 01KSF9HJ triage but the fixes were never merged. This WP completes the fix using test-driven investigation.

**Important**: Anchor additions are content additions to existing YAML files — no schema version bump is needed (Assumption 2 in spec.md).

---

## Subtask T009 — Run failing tests to identify exact locations

**Purpose**: Before editing any files, run the failing tests with `--tb=long` output to get the exact file paths, missing anchors, and schema violations. Editing blindly wastes time and risks introducing new errors.

**Steps**:

1. Run the glossary link integrity tests:
   ```bash
   pytest tests/doctrine/test_glossary_link_integrity.py -v --tb=long 2>&1 | head -80
   ```

2. Run the tactic compliance tests:
   ```bash
   pytest tests/doctrine/test_tactic_compliance.py -v --tb=long 2>&1 | head -80
   ```

3. From the output, record:
   - Which context YAML files are missing the `doctrine-pack` anchor
   - Which context YAML files are missing the `platform-darwin--platform-linux` anchor
   - Which field in `five-paradigm-parallel-debugging.tactic.yaml` fails schema validation
   - Which terms are unresolved in the tactic file

4. List the doctrine glossary structure to understand file layout:
   ```bash
   find src/doctrine/glossary/ -name "*.yaml" | sort
   ```

**Validation**:
- [ ] You know which specific YAML files need the two anchor additions
- [ ] You know which fields in the tactic YAML are invalid
- [ ] You know which glossary terms are unresolved in the tactic

---

## Subtask T010 — Add `doctrine-pack` anchor

**Purpose**: Add the `doctrine-pack` anchor entry in the correct glossary context YAML file identified in T009.

**Steps**:

1. Open the target context YAML file (identified in T009)

2. Add an anchor entry for `doctrine-pack`. The entry should follow the existing YAML structure in the file. A typical glossary anchor entry looks like:

   ```yaml
   - id: doctrine-pack
     label: Doctrine Pack
     definition: >
       A versioned, distributable bundle of doctrine artefacts (glossary terms,
       tactics, agent profiles, and skill packages) that can be installed into
       a project to govern its development practices.
     aliases: []
     see_also: []
   ```

   Adjust the definition to match the actual content in the 01KSF9HJ triage notes or the context inferred from the test output.

3. Run the link-integrity test again to confirm the anchor is now resolved:
   ```bash
   pytest tests/doctrine/test_glossary_link_integrity.py -v --tb=short -k "doctrine_pack"
   ```

**Files**: The specific context YAML identified in T009 (under `src/doctrine/glossary/`)

**Validation**:
- [ ] `doctrine-pack` anchor resolves without errors
- [ ] YAML remains valid (parseable without errors)
- [ ] Existing anchors in the file are unchanged

---

## Subtask T011 — Add `platform-darwin--platform-linux` anchor

**Purpose**: Add the `platform-darwin--platform-linux` anchor entry in the correct glossary context YAML file.

**Steps**:

1. Open the target context YAML file (identified in T009)

2. Add an anchor entry for `platform-darwin--platform-linux`. The double-dash convention in doctrine anchor IDs typically represents a compound concept (here: `platform-darwin` combined with `platform-linux`). The entry should capture both platform variants:

   ```yaml
   - id: platform-darwin--platform-linux
     label: Platform (Darwin / Linux)
     definition: >
       The macOS (Darwin kernel) and Linux operating system targets supported
       by spec-kitty. Commands and scripts must behave identically on both
       platforms unless explicitly documented otherwise.
     aliases:
       - platform-darwin
       - platform-linux
     see_also: []
   ```

   Adjust based on the test output from T009.

3. Run the link-integrity test to confirm the anchor resolves:
   ```bash
   pytest tests/doctrine/test_glossary_link_integrity.py -v --tb=short
   ```

**Files**: The specific context YAML identified in T009 (may be the same file as T010 or a different one)

**Validation**:
- [ ] `platform-darwin--platform-linux` anchor resolves without errors
- [ ] YAML remains valid
- [ ] The entry is placed in the correct context file (where the tests expect it)

---

## Subtask T012 — Fix five-paradigm-parallel-debugging.tactic.yaml

**Purpose**: Fix the schema violations and unresolved references in the tactic file so `test_tactic_compliance` passes.

**Steps**:

1. Read the tactic file:
   ```bash
   cat src/doctrine/tactics/built-in/five-paradigm-parallel-debugging.tactic.yaml
   ```

2. Read the tactic schema (if a schema definition exists):
   ```bash
   find src/doctrine/ -name "*.schema.yaml" -o -name "tactic.schema.json" | head -5
   ```

3. Cross-reference with test output from T009 to identify which fields are schema-invalid and which terms are unresolved.

4. Fix in-place:
   - For schema violations: correct the field names or values to match the schema
   - For unresolved refs: either add the missing glossary entries (if they belong to this tactic's domain) or remove the references if they are erroneous
   - Do NOT change the content meaning of the tactic — only fix structural compliance

5. Run both test files to confirm:
   ```bash
   pytest tests/doctrine/test_glossary_link_integrity.py tests/doctrine/test_tactic_compliance.py -v --tb=short
   ```

**Files**: `src/doctrine/tactics/built-in/five-paradigm-parallel-debugging.tactic.yaml`

**Validation**:
- [ ] All four failing tests in `test_glossary_link_integrity` pass
- [ ] All failing tests in `test_tactic_compliance` pass
- [ ] YAML is valid (no parse errors)
- [ ] The tactic's semantic content is preserved (only structural fixes)

---

## Branch Strategy

- **Planning/base branch**: `feat/pre-doctrine-stabilization-remediation`
- **Final merge target**: `feat/pre-doctrine-stabilization-remediation`

To start implementation:
```bash
spec-kitty agent action implement WP03 --agent claude
```

---

## Definition of Done

- [ ] All four failing tests in `test_glossary_link_integrity` pass
- [ ] All failing tests in `test_tactic_compliance` pass
- [ ] No new test failures introduced in `tests/doctrine/`
- [ ] YAML files remain syntactically valid
- [ ] No schema version bumps added

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| Anchor must go in a specific context file that is non-obvious | Medium | Let test output guide the target file; don't guess |
| Tactic unresolved refs point to terms that don't exist anywhere | Medium | Check if term should be added to glossary or if ref is simply wrong |
| YAML formatting breaks existing parsing | Low | Run pytest after each file edit |

---

## Reviewer Guidance

1. Confirm both anchors exist in the correct context YAML files (as identified by test output, not by assumption)
2. Confirm the tactic YAML parses without errors
3. Confirm all four originally-failing tests pass and no new failures were introduced
</content>

## Activity Log

- 2026-05-27T12:19:13Z – claude:claude-sonnet-4-6:curator-carla:implementer – shell_pid=37654 – Assigned agent via action command
- 2026-05-27T12:25:49Z – claude:claude-sonnet-4-6:curator-carla:implementer – shell_pid=37654 – T009-T012 complete: glossary anchors added, platform link fixed, tactic YAML schema violation removed. All 4 doctrine tests pass (1688 total passing).
