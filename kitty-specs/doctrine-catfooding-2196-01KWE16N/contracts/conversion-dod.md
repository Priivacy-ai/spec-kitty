# Contract — Per-conversion Definition of Done

Every §-conversion WP (IC-02, IC-03) MUST satisfy this contract. It operationalizes C-001 + C-002.

## Pre-conditions (first subtask — the overlap-audit, C-001)
1. Read the enumerated existing artifact(s) for this section (see `data-model.md` inventory).
2. Record an explicit **augment-vs-create** decision per target (DIRECTIVE_003): what already exists, what atom is uncovered, whether to extend/reference/create, and the chosen artifact kind.
3. If the audit shows the rule is fully covered → do NOT author a new artifact; extend/reference only. (A new artifact restating an existing rule fails review — NFR-002.)

## Authoring
4. Author/extend the artifact(s) at the correct kind (per D-2). §1 MUST NOT be `enforcement: required` (C-006).
5. Author the artifact's inline DRG edges (`requires`/`suggests`/`refines`) in the YAML. **Do NOT regenerate `graph.yaml`** — that is the wiring WP's job (PD-2).
6. Stay within `owned_files`; shared surfaces are single-owner (C-003).

## Gates (before move-to-for_review)
7. `spec-kitty doctor doctrine --json` → 0 skipped / 0 invalid (NFR-001). **Note: doctor-green is NOT schema proof for newly-authored artifacts.** `doctor doctrine` reports org/pack/selection/profile health — it does NOT schema-validate a newly-authored built-in directive/tactic/procedure/styleguide/toolguide. A malformed new artifact YAML passes doctor-green; real schema validation is gated in WP12's DRG tests. To catch schema errors at per-WP review (before WP12), run the targeted per-artifact gate below.
8. `PWHEADLESS=1 python -m pytest tests/doctrine/drg/test_shipped_graph_valid.py -q` → green for all newly authored or extended artifacts in this WP. This is the per-artifact schema validation gate. Run it against all new/changed artifact YAMLs immediately after authoring; a malformed YAML caught here saves WP12 from a downstream failure. Keep doctor-green (gate 7) AND this schema gate; they are complementary.
9. `pytest tests/architectural/test_no_legacy_terminology.py` → green; forbidden terms in examples are quoted-and-marked, not used (C-004).
10. `ruff` + `mypy` clean on any Python touched (NFR-004).

## Deferred to the wiring WP (do NOT do here)
- `graph.yaml` regeneration + `tests/doctrine/drg/*` pass.
- Wiring the new directive into agent-profile `directives:` lists (C-002c).

## Review checklist (reviewer)
- Overlap-audit record present + honest (no duplicate authority).
- Correct artifact kind; §1 optionality preserved.
- Inline DRG edges present (regen deferred, not skipped).
- `tests/doctrine/drg/test_shipped_graph_valid.py` green (per-artifact schema validation — confirms YAML is well-formed before WP12; doctor-green alone is not sufficient).
- doctor + terminology + lint green.
