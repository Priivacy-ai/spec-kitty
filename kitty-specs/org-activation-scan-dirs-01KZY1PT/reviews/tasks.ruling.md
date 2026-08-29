# Operator ruling — tasks phase, `finalize-tasks` false-positive block

**Date**: 2026-08-13
**Mission**: `org-activation-scan-dirs-01KZY1PT` (issue #3385)
**Phase**: tasks (authoring)

## What blocked

`spec-kitty agent mission finalize-tasks --mission org-activation-scan-dirs-01KZY1PT --json`
refused to commit `wps.yaml`/`tasks/WP01-*.md` into `tasks.md`, reporting
`unmapped_functional_requirements: ["FR-021"]` even though WP01 correctly claimed all three of
spec.md's own Requirements-table rows (`FR-001`, `FR-002`, `FR-003`). Root cause: spec.md:124
cited, in explanatory prose, an unrelated already-shipped mechanism's requirement id
(`CharterPackManager.activate`'s FR-021 default-pack materialization) as background evidence for
why the bug this mission fixes is easy to miss. `parse_requirement_ids_from_spec_md`
(`src/specify_cli/requirement_mapping.py:104-117`) regex-scans spec.md's entire raw text for
`FR-\d+`-shaped substrings rather than scoping to the Requirements table, so that citation was
misread as an unmapped requirement of *this* spec. No CLI bypass exists. Full trace: this
mission's `tracer-tooling-friction.md`, "Tasks phase" section.

## Ruling

Filed upstream as **[issue #3394](https://github.com/Priivacy-ai/spec-kitty/issues/3394)**
(workspace-local ledger id `SK-14` in `SPEC-KITTY-LEDGER.md`). Operator selected **option (a)**:
a scoped, mechanical edit to spec.md:124 to remove the bare `FR-021` token, rather than (b)
waiting on the upstream parser fix or (c) an unscoped bypass.

## What was edited

`spec.md:124` — removed only the `FR-021 ` token from the phrase `` `CharterPackManager.activate`'s
FR-021 default-pack materialization `` → `` `CharterPackManager.activate`'s default-pack
materialization ``. Every `file:line` citation in the surrounding sentence
(`src/charter/activation/pack_manager.py:601-616`, `src/charter/activation/activation_engine.py:257-268`,
`src/charter/activation/pack_manager.py:511-518`) is unchanged. The sentence's meaning, its scope claim
("not an org-specific gap... the same exclusion would equally apply to an unlisted built-in or
project artifact"), and its "not a defect this mission changes" framing are unchanged — this is a
**semantically inert** edit made for tooling reasons only, not a content revision of the
already-reviewed, PASSED spec.

**Verification performed**:
- Re-read spec.md:113-135 in full post-edit; paragraph reads correctly, no dangling reference.
- `grep -oE '\bFR-[0-9]+\b' spec.md | sort -u` → exactly `FR-001 FR-002 FR-003` (this spec's own
  three Requirements-table rows).
- `grep -oE '\bNFR-[0-9]+\b' spec.md | sort -u` → empty.
- `grep -oE '\bC-[0-9]+\b' spec.md | sort -u` → `C-001 C-002 C-003 C-004 C-005 C-011`. `C-011`
  (cited once, referencing the charter's ATDD-First Discipline directive in User Story 2's prose)
  was checked and found harmless: `parse_requirement_ids_from_spec_md`'s functional-mapping
  validation (`_validate_requirement_mapping` in `mission_finalize.py`) only computes
  `unmapped_functional_requirements` from `FR-`-prefixed ids; it never applies the same check to
  `C-`-prefixed ids appearing in spec.md's `all_ids` set. Left as-is — not the same defect class,
  no action needed.

## Authorization

Explicitly authorized by the operator in the message that resolved this mission's BLOCKED report,
citing issue #3394 as the upstream reference. This ruling record exists so a later reader of
spec.md's git history sees why an already-reviewed, PASSED artifact was touched after review
closed: a mechanical, meaning-preserving edit forced by a downstream tooling defect, not a
re-opening of the spec's content.
