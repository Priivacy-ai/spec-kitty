# Contract: Opt-in REASONS Review Gate

## Activation
- The gate is included in the reviewer prompt only when `is_spdd_reasons_active(repo_root)` is `True`.
- When inactive, the reviewer prompt is byte-identical to the pre-feature output (covered by `prompt-fragment.md`).

## Reviewer expectations (when active)

1. Locate `kitty-specs/<mission>/reasons-canvas.md`. If missing, instruct the reviewer to call the `spec-kitty-spdd-reasons` skill to author one before completing review (do not auto-approve in absence of canvas).
2. For each Requirement and Operation in the canvas, identify supporting evidence in the diff or note its absence.
3. Detect entities, files, or surfaces touched by the diff that are absent from the canvas Structure or Approach.
4. Verify Norms and Safeguards adherence.
5. Charter directives take precedence; if a charter directive conflicts with the canvas, follow the directive and add a deviation note.

## Drift classification

Reviewer outputs one of:

| Outcome | Definition | Action |
|---|---|---|
| approved | No divergence OR all divergences match Deviations entries. | APPROVE |
| approved_with_deviation | Divergence is acceptable; reviewer adds a Deviations entry. | APPROVE + canvas update |
| canvas_update_needed | Canvas was wrong; canvas should be revised before next WP. | APPROVE conditionally; open canvas update task. |
| glossary_update_needed | Term drift surfaced; glossary should be revised. | APPROVE conditionally; open glossary update task. |
| charter_follow_up | Selection should change. | APPROVE conditionally; open charter follow-up. |
| follow_up_mission | Out-of-scope work surfaced; create a separate mission. | APPROVE current scope; open follow-up. |
| scope_drift_block | Out-of-bounds undocumented work. | REJECT. |
| safeguard_violation_block | Safeguard rule violated. | REJECT. |

## Tests (WP5)

| Case | Project state | Diff | Expected outcome |
|---|---|---|---|
| 1 | inactive | any | Reviewer prompt unchanged from baseline. |
| 2 | active, no canvas | any | Reviewer instructed to author canvas first. |
| 3 | active, in-bounds diff | matches canvas | approved |
| 4 | active, OOB undocumented | new file outside Structure | scope_drift_block |
| 5 | active, safeguard breach | violates a Safeguard | safeguard_violation_block |
| 6 | active, OOB but recorded in Deviations | matches Deviations entry | approved_with_deviation |
