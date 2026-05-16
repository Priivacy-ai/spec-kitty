---
work_package_id: WP06
title: Wire WP frontmatter agent_profile through prompt builder; add Governance Payload Contract section to templates
dependencies:
- WP03
- WP04
requirement_refs:
- FR-004
- FR-005
- FR-010
- NFR-003
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
agent: claude
agent_profile: python-pedro
authoritative_surface: src/specify_cli/next/prompt_builder.py
execution_mode: code_change
owned_files:
- src/specify_cli/next/prompt_builder.py
- src/specify_cli/missions/software-dev/command-templates/implement.md
- src/specify_cli/missions/software-dev/command-templates/review.md
- tests/architectural/test_template_governance_payload_contract.py
role: implementer
history: []
tags: []
---

## Objective

Close the wiring loop so the resolver work delivered in WP03 and WP04 is actually
visible to the executing agent:

1. In `src/specify_cli/next/prompt_builder.py`, extract `wp_meta.agent_profile` from
   the WP frontmatter at the existing `read_wp_frontmatter` site (`_build_wp_prompt`)
   and forward it to `_governance_context(..., profile=<id>)`. (FR-004 wiring side)
2. In `_governance_context`, forward `profile=` to `build_charter_context`.
3. Add the `## Governance Payload Contract` section to both runtime templates
   (`implement.md` and `review.md`) per the contract in
   `contracts/runtime-template-governance-payload-contract.md`. (FR-005)
4. Add the architectural test that pins template-promise ↔ resolver-reality
   consistency.
5. Run the full ATDD suite and confirm 23/23 pass (FR-010, NFR-003 acceptance gate).

This is the final integration WP for the mission's core pipeline.

---

## Context

WP03 made `build_charter_context(profile=)` load-bearing on the resolver side. WP04
added the two new structural sections. Without the wiring delivered here, no caller
actually passes the profile to the resolver, so the executing agent still sees the
old payload.

WP06 is also the gate for FR-005 (the runtime template either drops the forbid clause
or carries the Governance Payload Contract section). The chosen option is **(b)**: keep
the forbid clause, add the contract section. The contract section is the honest
counterpart to the forbid clause — the template now promises what the prompt will
carry.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`
- **Implement command**: `spec-kitty agent action implement WP06 --agent claude`

---

## Subtask T023 — Extract `wp_meta.agent_profile` in `_build_wp_prompt`

**File**: `src/specify_cli/next/prompt_builder.py`

At the existing line ~125 (`wp_meta, _ = read_wp_frontmatter(wp_files[0])`), capture the
profile:

```python
wp_meta, _ = read_wp_frontmatter(wp_files[0])
agent_profile_id = wp_meta.agent_profile or None
```

Pass `profile=agent_profile_id` to the `_governance_context(...)` call at line ~147.

WP frontmatter `agent_profile` is already a real field (the existing missions write it;
e.g. `kitty-specs/layered-doctrine-org-layer-01KRNPEE/tasks/WP01-multifile-drg-loading.md`
carries `agent_profile: python-pedro`). The `wp_meta` model needs a corresponding
optional attribute if it does not already expose `agent_profile`; check
`specify_cli.next.frontmatter` (or wherever `read_wp_frontmatter` is defined) and add the
field if missing.

---

## Subtask T024 — Forward `profile=` in `_governance_context`

**File**: `src/specify_cli/next/prompt_builder.py`

At `_governance_context(repo_root, action=..., profile=None)` (currently around line
265–280), accept the new keyword argument and forward to
`build_charter_context(repo_root, action=action, profile=profile)`.

When `profile is None`, the resolver behaves byte-identically to today (WP03's NFR-005
contract).

---

## Subtask T025 — Add Governance Payload Contract section to `implement.md`

**File**: `src/specify_cli/missions/software-dev/command-templates/implement.md`

Insert the new top-level section **between** the forbid clause (lines 68–71 today) and
`## Execution Steps`. Use the four-block schema specified in
`contracts/runtime-template-governance-payload-contract.md` §2.

The heading text must be exactly `## Governance Payload Contract` so the architectural
detection regex `r"##\s+Governance\s+Payload\s+Contract\b"` matches.

The four blocks (in order):

1. **Guaranteed bodies** — bulleted list naming the three action-critical sections.
2. **Guaranteed citations** — describe the two profile-cited surfaces (directives + tactics).
3. **Guaranteed authority pointers** — list defaults + note about `authority_paths:` extension.
4. **Fetch commands** — list the three canonical fetch-command forms.

Use the exact text from contract §2 as the starting point; adapt only for project-
specific phrasing (e.g. the additional "consult external governance" sentence may be
adjusted to fit `implement.md`'s voice).

⚠️ Remember: edit the SOURCE template at
`src/specify_cli/missions/software-dev/command-templates/implement.md`, NOT the
generated agent copies under `.claude/`, `.amazonq/`, etc. (Per the project CLAUDE.md.)

---

## Subtask T026 — Add Governance Payload Contract section to `review.md`

**File**: `src/specify_cli/missions/software-dev/command-templates/review.md`

Same four-block schema, adapted for the reviewer:

- **Guaranteed bodies**: same three sections.
- **Guaranteed citations**: every `DIRECTIVE_NNN` / tactic-id from the loaded reviewer
  profile (e.g. `reviewer-renata` declares DIRECTIVE_032 — Conceptual Alignment). MUST
  include the sentence specified by contract §5:

  > When you assess a WP that renames identifiers or terms, the prompt cites
  > DIRECTIVE_032 (Conceptual Alignment) by ID; consult its rule body inline or via
  > the paired fetch command and apply.

- **Guaranteed authority pointers**: identical to `implement.md`.
- **Fetch commands**: identical to `implement.md`.

---

## Subtask T027 — Architectural template-contract test

**File**: `tests/architectural/test_template_governance_payload_contract.py` (new)

Per contract §7 (drift prevention), this test parses the template's
`## Governance Payload Contract` section and the resolver's output for a fixture
mission with a known profile, and asserts every guaranteed surface listed in the
template is present in the resolver output.

Test outline:

```python
def test_implement_template_contract_matches_resolver_output(tmp_path):
    # 1. Load source template src/specify_cli/missions/software-dev/command-templates/implement.md
    # 2. Slice the ## Governance Payload Contract section
    # 3. Extract guaranteed-bodies, guaranteed-citations, guaranteed-authority-pointers blocks
    # 4. Build a fixture project (charter + WP) with profile=python-pedro
    # 5. Call build_charter_context(action="implement", profile="python-pedro")
    # 6. Assert every guaranteed body name appears in the resolver text
    # 7. Assert every authority path appears in the resolver text
    # 8. Assert every fetch-command form is parseable from the resolver text
```

A parallel test for `review.md`.

The reverse direction (resolver may emit surfaces not listed in the template) is
intentionally NOT enforced.

---

## Subtask T028 — Run full ATDD suite; confirm 23/23 pass

Run:

```bash
pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
```

Expected: 23 passed, 0 failed. If any test fails, the cause is one of:

- WP03 / WP04 / WP05 left a section out of the rendered output.
- The WP frontmatter agent_profile is not being read (T023).
- The template contract section is missing or malformed (T025 / T026).
- A regex anchor in the ATDD test does not match the rendered shape.

Each failure is a defect in this mission's upstream WPs; surface it back as a rework
on the offending WP before marking WP06 done.

---

## Definition of Done

- [ ] `_build_wp_prompt` extracts `agent_profile` from WP frontmatter and forwards it to `_governance_context`.
- [ ] `_governance_context` forwards `profile=` to `build_charter_context`.
- [ ] `## Governance Payload Contract` section present in both `implement.md` and `review.md` (source templates, not agent copies).
- [ ] `tests/architectural/test_template_governance_payload_contract.py` passes (2 tests minimum: implement + review).
- [ ] ATDD `test_template_either_drops_forbid_or_guarantees_governance_payload` passes.
- [ ] ATDD `test_implement_prompt_self_sufficiency` passes (FR-010 aggregate gate).
- [ ] Full ATDD suite reports `23 passed, 0 failed` (NFR-003).
- [ ] `tests/architectural/test_layer_rules.py` (8 tests) still passes.
- [ ] `ruff check` and `mypy` are clean on every file this WP touches.

---

## Risks

- **R-1**: Editing the wrong template (an agent copy under `.claude/commands/` instead
  of the source under `src/specify_cli/missions/software-dev/command-templates/`).
  Catastrophic — the source template never gets the section, so consumer projects don't
  get it on upgrade. **Mitigation**: hard call-out at top of T025 and T026; reviewer
  verifies the path before approving the diff.
- **R-2**: The architectural test parses the template too literally and breaks when a
  future mission adds a fourth action-critical section. **Mitigation**: the test asserts
  every guaranteed-body name is present in the resolver output, not the inverse.
  Adding sections to the resolver does not break the test; only removing them or
  renaming the contract heading does.
- **R-3**: `read_wp_frontmatter` returns a `wp_meta` model that lacks `agent_profile`.
  **Mitigation**: T023 includes the field addition (verify it does not already exist).
- **R-4**: A WP frontmatter with no `agent_profile:` field passes `None` and section 5
  / 6 of the resolver text are omitted. The ATDD self-sufficiency test fixture MUST
  specify a profile to exercise the full payload. **Mitigation**: documented in the
  ATDD test fixtures already (e.g. test file lines 130-148).

---

## Reviewer Guidance

Check that:

1. The source templates are edited, NOT the agent copies. Confirm:
   - `src/specify_cli/missions/software-dev/command-templates/implement.md` has the new section.
   - No `.claude/commands/spec-kitty.implement.md` or `.amazonq/prompts/...` was modified.
2. The Governance Payload Contract section in `implement.md` appears AFTER the existing
   forbid clause (lines 68-71) and BEFORE `## Execution Steps`.
3. The heading text is exactly `## Governance Payload Contract` — case-sensitive, no
   trailing words.
4. The review template carries the DIRECTIVE_032 sentence per contract §5.
5. `wp_meta.agent_profile` is read as `None` when the field is absent (no
   `AttributeError`).
6. The architectural template-contract test asserts presence of every promised surface
   in the resolver output, not the reverse.
7. Final pytest run: `pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py`
   reports `23 passed, 0 failed`. Paste the summary line into the activity log.
