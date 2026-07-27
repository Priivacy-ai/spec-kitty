# Phase 0 Research — Opt-in SPDD/REASONS Doctrine Pack

## R1. Reuse existing artifact kinds vs introduce a new "doctrine pack" kind

**Decision**: Reuse existing artifact kinds (paradigm + tactics + styleguide + directive + template fragment + skill).

**Rationale**:
- Spec spec.md C-003 mandates this preference.
- All required behavior maps cleanly onto existing kinds:
  - The umbrella philosophy → paradigm.
  - The "fill canvas" and "review canvas" workflows → two tactics.
  - The voice/section rules → styleguide (scope `docs`).
  - The change-boundary enforcement rule → directive `DIRECTIVE_038`.
  - The agent-facing trigger and instructions → skill `spec-kitty-spdd-reasons`.
  - The seven-section canvas skeleton → template fragment.
- Adding a new artifact kind would require schema, repository, loader, and DRG changes that violate C-007 (no schema changes unless absolutely required) and increase blast radius.

**Alternatives considered**:
- New "doctrine_pack" kind that bundles related artifacts atomically. Rejected — existing kinds compose naturally; a pack-level metadata file is unnecessary because charter selection already binds them together.
- Single super-directive with embedded canvas template. Rejected — directives don't carry templates and conflate enforcement with content.

## R2. DIRECTIVE_038 enforcement level

**Decision**: `enforcement: lenient-adherence` with explicit allowances enumerated.

**Rationale**:
- The directive must allow documented deviations (spec FR-016, FR-017).
- `required` would block any deviation; `advisory` would not block scope drift.
- `lenient-adherence` per `directive.schema.yaml` (lines 7–12) requires `explicit_allowances` array, which we will populate with the four legitimate deviation outcomes:
  1. Documented approved deviation (recorded in canvas as a deviation note).
  2. Glossary update follow-up.
  3. Charter follow-up.
  4. Follow-up mission.

**Alternatives considered**:
- `required` enforcement: rejected because it makes drift handling impossible without bypass mechanisms.
- `advisory`: rejected because it cannot block unrecorded scope drift, defeating the WP5 goal.

## R3. Conditional prompt rendering mechanism

**Decision**: The prompt template carries a clearly marked "REASONS Guidance (when active)" subsection. The runtime renderer (the same path that today materializes `command-templates/*.md` to per-agent prompt files) checks the active doctrine context and either includes or omits the subsection. When omitted, the surrounding template renders byte-identically to today's output.

**Rationale**:
- The repo does not have a Jinja-style template engine for prompts; templates are passed largely as-is, with `$ARGUMENTS` and similar substitution.
- The cleanest seam is to add a single, well-marked block per prompt and have the renderer drop it when the pack is inactive. This avoids "always-on" template edits (per C-004).
- Activation status is read from the same `_load_action_doctrine_bundle` machinery used by `charter context`. The bundle exposes selected paradigms/tactics/directives; we check membership of `structured-prompt-driven-development`, `reasons-canvas-fill`, `reasons-canvas-review`, or `DIRECTIVE_038`.

**Implementation notes**:
- The "active doctrine context" check is implemented as a small helper, e.g. `is_spdd_reasons_active(repo_root) -> bool`, in a new module `src/doctrine/spdd_reasons/activation.py` (or similar; placement to be confirmed during WP2).
- The conditional block uses HTML comment markers `<!-- spdd:reasons-block:start -->` / `<!-- spdd:reasons-block:end -->` so the renderer can identify and excise it deterministically. The `<!-- ... -->` markers themselves are ALSO stripped on render so the inactive output is byte-identical to today.

**Alternatives considered**:
- Introduce a Jinja template engine: rejected as over-engineering for one feature.
- Maintain two parallel template files (active vs inactive): rejected — duplication and drift.
- Always render REASONS sections: rejected by C-004.

## R4. Active-doctrine detection contract

`is_spdd_reasons_active(repo_root)` returns true iff any of the following appear in the active charter selection (read from `.kittify/charter/governance.yaml` and/or `directives.yaml` via existing loaders):

- paradigm `structured-prompt-driven-development`, OR
- tactic `reasons-canvas-fill`, OR
- tactic `reasons-canvas-review`, OR
- directive `DIRECTIVE_038`.

ANY of the four is sufficient because users may select tactics-only or directive-only without selecting the umbrella paradigm.

## R5. Action scoping (rendering scope per action)

| Action      | Canvas sections rendered into prompt              |
|-------------|---------------------------------------------------|
| `specify`   | Requirements, Entities                            |
| `plan`      | Approach, Structure                               |
| `tasks`     | Operations, WP boundaries (Operations subset)     |
| `implement` | Full WP-scoped canvas (R, E, A, S, O, N, S)       |
| `review`    | Comparison surface (R, O, N, S)                   |

Rationale comes directly from spec FR-009 and FR-014/015. Each action receives the smallest useful slice; full canvas only at implement time to keep prompts compact.

## R6. Skill placement and conventions

`src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md` follows the same shape as `spec-kitty-charter-doctrine` (existing peer): YAML frontmatter (`name`, `description`, trigger phrases), Markdown body (capabilities, instructions, escalation rules, what it does NOT handle).

## R7. Tests strategy

- **Schema/compliance**: rely on existing `tests/doctrine/test_artifact_compliance.py`, `test_directive_consistency.py`, `test_tactic_compliance.py`, `test_artifact_kinds.py`, `test_nested_artifact_discovery.py`. New artifacts must pass without modification to those tests.
- **Charter context activation**: new file `tests/charter/test_charter_context_spdd_reasons.py` covering active and inactive snapshots, performance bound, action scoping.
- **Prompt rendering**: new file `tests/prompts/test_prompt_fragment_rendering.py` asserting byte-or-semantic identity for inactive projects across all five command templates.
- **Review gate**: new file `tests/reviews/test_review_gate_activation.py` asserting drift handling on active projects and unchanged behavior on inactive.
- **Skill discoverability**: existing skill discovery tests cover the new file, if such tests exist; otherwise add one assertion in the doctrine compliance test.

## R8. Risk register

| Risk | Mitigation |
|---|---|
| Inactive-project regression (e.g., a spurious newline) | Byte-or-semantic snapshot test in WP4 covering all five command templates; CI must compare current `main` baseline to PR output for an inactive fixture. |
| `_load_action_doctrine_bundle` doesn't surface paradigms | Validate during WP2; if needed, extend bundle to include paradigm membership without changing the public output schema. |
| Charter `bundle.py` doesn't write paradigms | Validate during WP2; add minimal paradigm `SynthesisTarget` plumbing if missing (kind ordering already supports paradigm by extension). |
| Schema regression from a malformed YAML | Existing schema tests catch this; CI will block. |
| Skill triggers conflict with existing skills | Reviewed against listed peer skills; "use SPDD" / "use REASONS" / "generate a REASONS canvas" / "apply structured prompt driven development" / "make this mission SPDD" do not collide. |

## R9. Performance

`charter context --action` performance is dominated by DRG resolution. Adding 3 new artifacts (paradigm + 2 tactics + 1 directive) increases DRG node count by ≤4. NFR-002 (≤2s) holds with comfortable margin.
