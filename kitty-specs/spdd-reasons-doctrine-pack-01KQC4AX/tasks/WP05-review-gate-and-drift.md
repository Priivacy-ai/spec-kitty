---
work_package_id: WP05
title: Opt-in REASONS Review Gate and Drift Handling
dependencies:
- WP04
requirement_refs:
- FR-015
- FR-016
- FR-017
- FR-018
- NFR-001
planning_base_branch: doctrine/spdd-reasons-pack
merge_target_branch: doctrine/spdd-reasons-pack
branch_strategy: Planning artifacts for this feature were generated on doctrine/spdd-reasons-pack. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/spdd-reasons-pack unless the human explicitly redirects the landing branch.
created_at: '2026-04-29T08:15:46Z'
subtasks:
- T020
- T021
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "48570"
history:
- date: '2026-04-29'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/missions/software-dev/command-templates/review.md
execution_mode: code_change
model: claude-opus-4-7
owned_files:
- src/specify_cli/missions/software-dev/command-templates/review.md
- tests/reviews/__init__.py
- tests/reviews/test_review_gate_activation.py
role: implementer
tags:
- review
- drift-handling
---

## ⚡ Do This First: Load Agent Profile

- Run `/ad-hoc-profile-load` with profile `python-pedro` and role `implementer`.
- Profile file: `src/doctrine/agent_profiles/shipped/python-pedro.agent.yaml`.
- After load, restate identity, governance scope, and boundaries before continuing.

# WP05 — Opt-in REASONS Review Gate and Drift Handling

## Branch Strategy

- **Planning base branch**: `doctrine/spdd-reasons-pack`
- **Merge target**: `doctrine/spdd-reasons-pack`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP05 --agent claude --mission spdd-reasons-doctrine-pack-01KQC4AX`. Do not guess the worktree path.

## Objective

Add the conditional REASONS Canvas Comparison subsection to `review.md`, using the same `spdd:reasons-block` marker convention introduced in WP04. The review gate activates ONLY for projects that opted in to the doctrine pack via charter (FR-018). Inactive projects must observe zero change in reviewer prompt content (NFR-001).

## Context

### Spec & contracts
- FR-015, FR-016, FR-017, FR-018, NFR-001.
- [contracts/review-gate.md](../contracts/review-gate.md) — full reviewer expectations, drift taxonomy, and seven test cases.
- [contracts/prompt-fragment.md](../contracts/prompt-fragment.md) — marker convention (reused).

### Drift classification taxonomy (from contracts/review-gate.md)
| Outcome | Action |
|---|---|
| approved | APPROVE |
| approved_with_deviation | APPROVE + canvas update |
| canvas_update_needed | APPROVE conditionally; open canvas update task |
| glossary_update_needed | APPROVE conditionally; open glossary update task |
| charter_follow_up | APPROVE conditionally; open charter follow-up |
| follow_up_mission | APPROVE current scope; open follow-up mission |
| scope_drift_block | REJECT |
| safeguard_violation_block | REJECT |

Charter directives take precedence over canvas content (FR-016).

### Renderer
The renderer hook from WP04 (`process_spdd_blocks`) handles `review.md` automatically once a marker block is present. Do NOT change the renderer.

## Subtasks

### T020 — Add SPDD reasons-block to `review.md`

**Path**: `src/specify_cli/missions/software-dev/command-templates/review.md`

Insert a marker block at a natural seam. The plan recommends "after `### 2a. Load Agent Profile`" — confirm this seam is still present in the current `review.md` and place the block after it. If a more appropriate seam exists, document the choice in the WP completion notes.

Block content (≤60 markdown lines):

```
<!-- spdd:reasons-block:start -->

### REASONS Canvas Comparison (active for this project)

This project's charter selected the SPDD/REASONS doctrine pack. Use the
mission's REASONS canvas as a comparison surface for this work package.

**1. Load the canvas.** Read `kitty-specs/<mission>/reasons-canvas.md`. If it
is missing, invoke the `spec-kitty-spdd-reasons` skill to author it before
completing review. Do not auto-approve in the absence of a canvas.

**2. Trace the diff.**

- For each Requirement and Operation in the canvas, find concrete evidence in
  the diff or note its absence.
- Detect entities, files, or surfaces touched by the diff that do not appear
  in canvas Structure or Approach.
- Verify Norms (testing, observability, style) and Safeguards (hard
  constraints, security, performance limits, things not to break).

**3. Classify the divergence.** Choose ONE outcome:

| Outcome | When | Action |
|---|---|---|
| approved | No divergence OR all divergences match Deviations entries. | APPROVE |
| approved_with_deviation | Divergence is acceptable; reviewer adds a Deviations entry. | APPROVE + canvas update |
| canvas_update_needed | Code reality reveals the canvas was wrong. | APPROVE conditionally; open canvas update task |
| glossary_update_needed | Term drift surfaced. | APPROVE conditionally; open glossary update task |
| charter_follow_up | Charter selection should change. | APPROVE conditionally; open charter follow-up |
| follow_up_mission | Out-of-scope work surfaced. | APPROVE current scope; open follow-up mission |
| scope_drift_block | Out-of-bounds undocumented work. | REJECT |
| safeguard_violation_block | Safeguard rule violated. | REJECT |

**4. Charter precedence.** If a charter directive conflicts with the canvas,
follow the directive and add a deviation note to the canvas.

**5. Record the outcome.** Reviewer should explicitly name the chosen outcome
in the review summary so downstream automation can route the WP correctly.

<!-- spdd:reasons-block:end -->
```

### T021 — Add `tests/reviews/test_review_gate_activation.py`

**Path**: `tests/reviews/test_review_gate_activation.py`

Test cases (mirror `contracts/review-gate.md` table):

```python
class TestReviewGateActivation:
    def test_inactive_review_template_byte_equivalent_to_baseline(self): ...
    def test_active_review_template_contains_canvas_comparison_headline(self): ...
    def test_active_review_lists_eight_drift_outcomes(self): ...
    def test_active_review_mentions_charter_precedence(self): ...
    def test_active_review_instructs_load_canvas(self): ...
    def test_active_review_instructs_classify_divergence(self): ...
    def test_active_review_instructs_record_outcome(self): ...
```

For the inactive baseline: capture `review.md` rendered output before this WP lands, store as `tests/reviews/fixtures/baseline/review.expected.md`, and compare bytes after this WP's changes. (If WP04 already provides a baseline for `review.md`, reuse it.)

## Definition of Done

- `review.md` contains the marker block at a sensible seam.
- Inactive rendering of `review.md` is byte-identical to baseline.
- Active rendering contains the REASONS Canvas Comparison headline and the eight drift outcomes.
- All seven contract tests pass.
- Full test suite passes: `uv run pytest tests -q`.
- `uv run mypy --strict src/specify_cli` clean (if it currently is).

## Reviewer guidance

- Confirm the block appears at a natural seam in `review.md` (just after the agent-profile load section is recommended).
- Confirm charter-directives-take-precedence is explicit in the block content.
- Confirm all eight drift outcomes are listed.
- Confirm reviewer is instructed to escalate (canvas authoring) when the canvas is missing — NOT to auto-approve.

## Risks

- **Seam drift**: if `review.md` no longer contains a `### 2a. Load Agent Profile` heading, choose the closest equivalent seam and document the choice.
- **Block size**: keep the block compact. The reviewer prompt is human-read by an agent; bloating it degrades review quality.
- **Charter precedence**: tests must verify the explicit precedence statement appears.

## Out of scope

- Renderer hook (delivered in WP04; reused here).
- Charter wiring (WP02).
- User-facing docs (WP06).

## Activity Log

- 2026-04-29T09:14:02Z – claude:opus:python-pedro:implementer – shell_pid=47292 – Started implementation via action command
- 2026-04-29T09:17:57Z – claude:opus:python-pedro:implementer – shell_pid=47292 – Ready for review: review.md SPDD block + 7 contract tests
- 2026-04-29T09:18:15Z – claude:opus:reviewer-renata:reviewer – shell_pid=48570 – Started review via action command
- 2026-04-29T09:20:28Z – claude:opus:reviewer-renata:reviewer – shell_pid=48570 – Review passed: review.md gains REASONS gate at sensible seam; 8 drift outcomes verbatim; charter precedence explicit; markers match WP04 convention; 7 contract tests green; no regressions or out-of-scope edits.
