# Mission Specification: Test-Quality Doctrine Series

**Created**: 2026-07-26
**Status**: ⏸ **NOT YET SPECCED — deliberately.** Scope sketch only.
**Programme**: Mission **C** of five — see the programme record [`doctrine-canonical-structure-remediation-01KYEYSD`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md).
**Order**: Fourth. Blocked by **B2**.
**Tracker**: the original [#2935](https://github.com/Priivacy-ai/spec-kitty/issues/2935) deliverable.

## Why this is a sketch and not a specification

**Operator guidance, 2026-07-26:** do not over-specify or plan any mission after phase A. Missions run
**one at a time**, each specced and planned only after the previous phase is finalized.

This mission is last for a substantive reason: C-001 and C-002 require the series to be authored
**edge-native from birth** — zero inline `references:` blocks, every relationship a DRG edge — and
that is only coherent against a tree where B2's authored-edge tier already exists. Authoring it
earlier would mean writing the legacy surface and then migrating it. Speccing it now would describe
an authoring surface that does not yet exist.

**Nothing is lost by waiting.** The user stories, the traps and the requirement set live in the
programme record's [`spec.md`](../doctrine-canonical-structure-remediation-01KYEYSD/spec.md) (US3,
US4, US5) and [`plan.md`](../doctrine-canonical-structure-remediation-01KYEYSD/plan.md) (IC-14).

## Scope sketch

Turn the #2934 over-mocking failure into a citable rule. A reviewer seeing a test that mocks an
internal of the system under test to pin a call contract can today only argue from taste; after this
they can cite a rule, an anti-pattern node, and a remediation procedure.

- Author the series: paradigm + `DIRECTIVE_047` + procedure + 2 anti-patterns + 4 assets, plus the augments.
- Split `DIRECTIVE_041`'s intent to the new paradigm, linked by a `refines` edge.
- Excise duplicated checklists to assets so one copy of each exists.
- Update `doctrine-daphne` with the layout convention, the edges-only rule, and the regeneration command.
- Give the PowerShell toolguide a real inbound edge — or restate its requirement honestly.
- Close the CLI/CI validator parity gap. **Characterize before fixing.**

Estimated 3–5 agent-days, ~30–45 files.

## Carried constraints — do not lose these when speccing

- **The `041 → paradigm` link is the first `refines` edge any built-in fragment has ever carried** (histogram: 0). #2079 fixed a silent `refines`→`applies` downgrade that nothing shipped has exercised, so the round-trip assertion is a real risk item, not a formality. The path is the **built-in fragment load** (`load_graph_or_dir`), not the org→DRG bridge.
- **Editing `DIRECTIVE_041` is its own reviewed change (C-005).** It is live at `enforcement: required`; audit inbound edges first, and do its migration **with** the intent split rather than as an anonymous line in a bulk pass.
- **Every new resolved-only node needs a proven inbound edge.** A loadable, id-resolvable, unreachable artefact is exactly the PowerShell toolguide's failure — "resolves" was operationalized as id-lookup, not reachability.
- **Anti-pattern nodes hold only `urn`/`kind`/`label`/`tags`** — structurally incapable of carrying a rationale. Design for that rather than discovering it mid-authoring.
- **⚠️ `anti_pattern` and `asset` are among the five kinds `extractor._KIND_MAP` silently drops** (measured 2026-07-26: it maps 11 of 16 `NodeKind` members; the missing five are `anti_pattern`, `asset`, `glossary`, `glossary_pack`, `glossary_scope`). This mission authors **2 anti-patterns and 4 assets**. Without mission A's site-3 fix they would vanish at extraction with no error — the series would validate, load, and then partly not exist. **This makes A a hard prerequisite for C on its own merits**, independent of the B2 ordering.
- **De-duplication must be measured**, not assumed: the excised content appears exactly once under `src/doctrine/`.
- **Part of the reported validator gap is likely the frozen inline surface behaving correctly.** Where that is so, document it as intended rather than "fixing" it.
- **Zero inline `references:` blocks** in anything this mission authors.
