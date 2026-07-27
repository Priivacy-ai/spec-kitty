# Verification Ledger — Mission-Type Creatability (S-C)

Tracer (seeded at planning; the falsifiable checklist; tick during implement, assess at close).

## Concern A — cutover (behavior-preserving)
- [ ] `MissionType.template_set` field removed; `grep` finds no persisted/authorable field or `template_set` overlay (kept the `action_sequence` overlay).
- [ ] `MissionTypeRepository.default().get("software-dev")` constructs; resolves `{spec, plan}` identically.
- [ ] software-dev resolved **filenames** byte-for-byte identical; `mission_type show --json` key order == `sequence_index` order (CLI-test baseline updated).
- [ ] Pack/YAML-authored `template_set:` → loud `ValidationError` (regression test).
- [ ] NFR-003: N template resolutions for one type → exactly one `mission-steps/` walk (call-count/spy).
- [ ] `TestSoftwareDevProjectionParity` green; injection-half + ~6 field-pin tests retired/migrated.

## Concern B — creatability (the #2689 fix)
- [ ] `mission create` succeeds for `documentation`, `research`, `plan`.
- [ ] `/plan`-setup template resolution succeeds for each (the `"plan"` key).
- [ ] All 16 seeded-blank prompts non-empty, free of `TODO`/`PLACEHOLDER`/`FIXME` (machine floor); substance-reviewed (NFR-004).
- [ ] Emptiness scaffold retired; positive "every sequence step has a non-empty prompt" assertion in place.
- [ ] No two types project the same `template_file` (NFR-006 guard).

## Concern C — graph-back
- [ ] Shipped graph has `action:<type>/<step> --instantiates--> template:<type>/<file>` edges (positive assertion); software-dev's 2 refs graphed.
- [ ] DRG counts `280+N`/`757+N`, orphans = 10; `regenerate-graph --check` + `tests/doctrine/drg/` freshness green; every arch marker re-baselined.
- [ ] resolve-by-URN == resolve-by-name for an authored template; a `.kittify/overrides/templates/` override wins on the URN lane (US3.3).
- [ ] 16 bare `template:<name>` exemplars untouched (still `edges:[]`).

## Gates
- [ ] ruff + mypy --strict clean, zero new suppressions; complexity ≤15.
- [ ] terminology guard green (prose touched).
- [ ] C-002 arch assertion: new URN/resolver code references no scalar `template_set` surface.
