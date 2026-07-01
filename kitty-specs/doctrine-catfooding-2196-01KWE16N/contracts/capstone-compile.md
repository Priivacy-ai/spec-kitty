# Contract — Capstone charter compile (IC-05 / FR-014 / C-007)

The capstone WP MUST follow this ordered sequence. Order is load-bearing.

## Preconditions
- All conversion WPs approved; the wiring WP has run the single `graph.yaml` regeneration and `tests/doctrine/drg/*` are green.
- The existing `.kittify/charter/charter.md` (v1.1.5) is read first — this is a **reconcile**, not a greenfield compile.

## Sequence (activate → generate; NEVER the reverse)
1. **Confirm graph + health**: `pytest tests/doctrine/drg/ -q` green; `spec-kitty doctor doctrine --json` healthy.
2. **Activate**: `spec-kitty charter activate <kind> <id> --cascade …` for the catfooding artifacts. Writes `.kittify/config.yaml` `activated_<kind>` lists. (Activation ≠ generation — this step does not render the charter.)
3. **Mirror answers** (named manual sub-step — no auto-bridge): edit `.kittify/charter/interview/answers.yaml` so `selected_directives`/`selected_tactics`/… include the activated catfooding IDs. Without this, `charter generate` renders a charter that references none of them.
4. **Generate**: `spec-kitty charter generate`. Renders `charter.md` + `references.yaml` from answers + the **activation-filtered** DRG closure (this is why step 2 precedes step 4).
5. **Reconcile**: ensure the regenerated `charter.md` supersedes v1.1.5 coherently (version bump, existing content preserved/merged — not clobbered).

## Acceptance (C-007 / NFR-003 / SC-003)
- `charter.md` + `references.yaml` regenerated from the activated set; version past 1.1.5.
- Reference closure **non-shallow**: every activated catfooding artifact's `requires`/`suggests` edges resolve in `references.yaml` (not just direct interview selections).
- `spec-kitty doctor doctrine --json` healthy after compile.
- `spec-kitty charter list` shows all 8 sections represented (SC-001).

## Failure modes to guard
- generate-before-activate → shallow closure (WRONG order).
- skipping the answers mirror → charter references no catfooding directives.
- greenfield generate → clobbers v1.1.5.
