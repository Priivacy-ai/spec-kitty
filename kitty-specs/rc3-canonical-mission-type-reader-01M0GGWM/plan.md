# Implementation Plan: M5 — Canonical mission-type reader

**Branch**: `rc3-canonical-mission-type-reader-01M0GGWM` | **Date**: 2026-08-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/rc3-canonical-mission-type-reader-01M0GGWM/spec.md`; re-grounded census in [research.md](research.md)

## Summary

Converge the ~10–12 hand-rolled `meta.json` mission-type readers onto **one**
shared, runtime-neutral `read_mission_type(meta: dict) -> str | None` helper
(canonical `mission_type` → `canonical_mission_type_key` → `None`; **no legacy
`mission` fallback, no silent `software-dev` default**). Retire legacy
`{"mission":…}` resolution and the silent defaults from every in-scope runtime
reader, each in an explicit, test-pinned step. Fold the #2901 WP-frontmatter
tolerant reader (mostly landed) and the #2477–#2480 inline-migration reads
(mostly exemptions). Ship the deliberate legacy-retirement behavior change under
an ADR, gated by the already-landed M0 backfill.

**Re-grounding shrank the mission** (see research.md): the charter read path and
the retrospective reader/writer are already canonical-only; #2901's tolerant
reader and three consumers already landed; FR-007's backfill is built and
correct. Load-bearing new work: the shared seam + M3 delegation, ~8 read
converters, the FR-010 structural gate, one #2901 route, the exemption
allow-list, ADR + changelog.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib (`json`), existing `charter.mission_type_key`, `charter.mission_type_profiles`
**Storage**: `meta.json` files (dict-in helper — file I/O stays per-reader)
**Testing**: pytest; one **structural table-driven** invariant test (FR-010) is the gate, not per-reader hand-copies
**Project Type**: single (CLI + library)
**Constraints**: layer-legal (`charter` may not import `specify_cli`; `test_layer_rules.py`); ruff + mypy clean, no new suppressions; deliberate behavior change under ADR
**Scale/Scope**: ~8 read converters + 1 shared seam + 1 M3 delegation + 1 structural gate + 1 #2901 route + FR-009 allow-list + ADR/changelog

## Charter Check

*GATE: passes.*

- **Single canonical authority** — the mission's whole point: one `read_mission_type` seam. ✅
- **Terminology adherence** — Mission canon; no `feature*` reintroduction; run `tests/architectural/test_no_legacy_terminology.py`. ✅
- **ATDD / red-first** — FR-010 structural test authored red first; per-reader regression pins precede each converter. ✅
- **Canonical sources** — reuse `canonical_mission_type_key`; do not re-derive normalization. ✅
- **Deliberate behavior change** — legacy-retirement carries an ADR + per-surface changelog; M0 backfill is the safety net that runs first. ✅ (Complexity Tracking below.)

## Project Structure

### Documentation (this mission)

```
kitty-specs/rc3-canonical-mission-type-reader-01M0GGWM/
├── spec.md            # LIGHT spec (operator-decided 2026-08-20)
├── research.md        # Phase 0 — re-grounded census (this mission)
├── plan.md            # This file
└── tasks/             # Phase 2 — WP files (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/charter/
├── mission_type_key.py            # ADD read_mission_type(meta) beside canonical_mission_type_key (FR-001/FR-004)
└── mission_type_profiles.py       # delegate _read_meta_mission_type/_resolve_type_key to shared seam (M3↔M5)

src/specify_cli/
├── mission.py                     # _canonical_meta_mission_type → thin delegate; drop legacy read
├── dashboard/handlers/features.py # FR-005 visible change: canonical field via helper
├── dashboard/diagnostics.py       # drop legacy read
├── mission_metadata.py            # read path (:255) converge; build path (:216) is a write-boundary
├── retrospective/generator.py     # :1319 drop default (coord w/ M8)
├── context/resolver.py            # :94 drop legacy read
├── verify_enhanced.py             # drop legacy read
├── retrospective/reader.py|writer.py  # parity route (already canonical-only)
├── status/wp_metadata.py          # #2901 tolerant reader (landed) — route residual sites
├── audit/classifiers/wp_files.py  # route through tolerant reader (coord w/ M6)
└── (allow-list) inline_meta_read_allowlist.yaml  # FR-009 encoded exemptions

tests/
├── (new) structural invariant test (FR-010)
└── per-reader regression pins + dashboard visible-change pin (AC-1)

docs/adr/3.x/ …  legacy-retirement ADR
CHANGELOG.md      [Unreleased] — per user-visible surface
```

**Structure Decision**: Single project. The shared seam lands in the `charter`
layer (below `specify_cli`, importable by both) — dissolving #2480's import
blocker. File I/O stays per-reader (dict-in helper).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Deliberate behavior change (legacy `{"mission":…}` stops resolving) | Operator ruling 2026-08-20 closes the #3598 split *downward* to canonical-only; a legacy-honoring convergence would preserve the very inconsistency M5 kills | Keeping legacy resolution leaves the CLI/charter split (#3598) and the silent-default masking in place |
| FR-009 exemptions over conversions | Frozen migrations read legacy/`mission_name` fields *by design* on historical state; converting breaks byte-exact replay | A blanket conversion sweep is prohibited (FR-006) and would corrupt migration replay |

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Shared canonical reader seam
- **Purpose**: Add `read_mission_type(meta: dict) -> str | None` beside `canonical_mission_type_key` in `charter/mission_type_key.py`; the sole resolution authority.
- **Relevant requirements**: FR-001, FR-004.
- **Affected surfaces**: `src/charter/mission_type_key.py`; `test_layer_rules.py` (no new edge).
- **Sequencing/depends-on**: none (foundation).
- **Risks**: Must stay pure/dict-in; keep `__all__` correct (dead-symbol gate).

### IC-02 — M3↔M5 reader reconciliation
- **Purpose**: Make the charter path (`_read_meta_mission_type`/`_resolve_type_key`) and the CLI `_canonical_meta_mission_type` both delegate field-extract+canon to the shared seam, so the two readers cannot re-diverge.
- **Relevant requirements**: FR-001, FR-002; cross-mission M3↔M5 (spec §Cross-mission).
- **Affected surfaces**: `charter/mission_type_profiles.py`, `specify_cli/mission.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Charter path is already canonical-only — this is a parity/authority refactor, not a behavior change; pin byte-parity.

### IC-03 — Runtime READ converters (legacy + default drop)
- **Purpose**: Route every in-scope runtime **read** through the seam, dropping legacy `mission` and silent `software-dev` — one reader per step, each test-pinned.
- **Relevant requirements**: FR-002, FR-003, FR-005, FR-006.
- **Affected surfaces**: `dashboard/handlers/features.py` (FR-005, visible), `mission_metadata.py:255`, `retrospective/generator.py:1319`, `context/resolver.py:94`, `verify_enhanced.py`, `dashboard/diagnostics.py`, `retrospective/reader.py|writer.py` (parity).
- **Sequencing/depends-on**: IC-01, IC-02.
- **Risks**: Caller boundaries that expected a concrete default must tolerate typeless (`get_mission_type` precedent); dashboard is a user-visible change → changelog line + regression pin.

### IC-04 — Write / echo / inference & audit boundary classification
- **Purpose**: Classify the non-read sites — converge the *field set* where they still echo legacy (`mission_create.py:374`), exempt-with-rationale where they are create-time writers (`mission_metadata.py:216`), inference writers (`upgrade/feature_meta.py`), interview-payload reads (`interview.py:225`), or the field-aware audit tool (`_mission_type_audit.py`).
- **Relevant requirements**: FR-006, FR-002.
- **Affected surfaces**: the five WRITE-BOUNDARY/EXEMPT sites in research.md.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Over-converging a write/inference path could remove a legitimately-needed create-time default; keep the audit tool field-aware (it classifies legacy-only as a bucket).

### IC-05 — Structural invariant gate (the real gate)
- **Purpose**: One table-driven test asserting (a) every in-scope reader == `read_mission_type(meta)` for the same dict, and (b) no in-scope module carries a `software-dev` fallback or a legacy `mission` read — with an encoded, rationale-carrying allow-list.
- **Relevant requirements**: FR-010, FR-006; AC-1, AC-3, AC-7.
- **Affected surfaces**: new `tests/…` structural test; allow-list.
- **Sequencing/depends-on**: authored red first (before IC-03); tightened as converters land.
- **Risks**: Source-scan must be robust (AST or precise regex) and avoid golden-count-ban patterns; needs `pytestmark`.

### IC-06 — FR-007 backfill: verify-and-sequence
- **Purpose**: Verify M0's `backfill-mission-type` maps legacy→`mission_type` (AC-5), document the `backfill-identity` gap, and encode the sequencing (backfill runs before legacy-drop reaches projects) in the ADR.
- **Relevant requirements**: FR-007; AC-5.
- **Affected surfaces**: verification test (or reuse M0's); ADR sequencing line. **No new backfill.**
- **Sequencing/depends-on**: none (verification).
- **Risks**: Rebuilding what M0 shipped — explicitly avoid.

### IC-07 — Fold #2901 (WP-frontmatter tolerant reader) — residual only
- **Purpose**: Route the residual divergent site(s) through the landed `status/wp_metadata.py` tolerant reader; pin the already-routed consumers with a parity assertion.
- **Relevant requirements**: FR-008; AC-6.
- **Affected surfaces**: `audit/classifiers/wp_files.py` (route; coord w/ M6), `mission_v1/guards.py` (evaluate). `review/prompt_metadata.py` is out of scope (review prompts, not WP).
- **Sequencing/depends-on**: none (independent).
- **Risks**: Scope creep into review-prompt frontmatter; verify-first — three consumers already landed.

### IC-08 — Fold #2477–#2480 (inline migration + charter reads)
- **Purpose**: Route the inline `meta.json` reads onto the shared helper with a replay-equivalence check, OR carry an encoded `inline_meta_read_allowlist.yaml` exemption citing the issue — never a silent path-exclude.
- **Relevant requirements**: FR-009; AC-6.
- **Affected surfaces**: `m_0_13_0_research_csv_schema_check.py` (exempt — historical legacy read), `m_0_13_5` (exempt — `mission_name`), `migration/mission_state.py:1617` (evaluate/exempt), the allow-list file.
- **Sequencing/depends-on**: IC-05 (allow-list is consumed by the structural test).
- **Risks**: Frozen-migration replay drift; default to exemption-with-rationale where equivalence can't be guaranteed.

### IC-09 — ADR + per-surface changelog
- **Purpose**: Author the legacy-retirement ADR (blast radius, M3 compounding, M0-backfill-first sequencing) and a `[Unreleased]` changelog entry per user-visible surface (dashboard / retrospective / interview).
- **Relevant requirements**: spec §Risks (user-visible surfaces), Decisions Resolved (b).
- **Affected surfaces**: `docs/adr/3.x/…`, `CHANGELOG.md`.
- **Sequencing/depends-on**: last (documents the landed change).
- **Risks**: Must name the M3↔M5 compounding so neither mission ships the compound break unguarded.
