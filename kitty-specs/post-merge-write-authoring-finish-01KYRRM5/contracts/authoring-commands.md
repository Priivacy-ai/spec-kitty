# Contract — Authoring finish-work (Lane D) + terminology foundation

## Acceptance authoring — extend `agent mission acceptance-verdict` (#2318, C-008)

No new command; the `NegativeInvariant` dataclass already carries all fields (no schema migration).

- **Register (FR-007)**: `spec-kitty agent mission acceptance-verdict --negative-invariant <id> --description <…> --verification-command <…> [--expect-absent …]` (exact flags per the dataclass) → persists a well-shaped `NegativeInvariant`; zero hand-edited JSON. Routes via `write_target(ACCEPTANCE_MATRIX)`.
- **Execute (FR-008)**: runs the invariant's verification via the existing `enforce_negative_invariants` engine; records `result` (pass/fail).
- **Diagnose hardening (FR-009)**: `spec-kitty accept --diagnose` wraps per-invariant load so a malformed `NegativeInvariant.from_dict` is reported (id + reason) and the command exits non-zero — no unhandled `TypeError` at load.
- **Fresh verdict (FR-010)**: canonical acceptance persists the recomputed `overall_verdict` on the all-pass/no-invariant branch (samuelgoff: `pass`, not stale `pending`).
- **Prompt (FR-011)**: `src/doctrine/missions/mission-steps/**/<accept step>/prompt.md` (SOURCE only) drives `acceptance-verdict` — asserted to DRIVE the CLI, not merely mention it. Never edit the 12 generated agent copies (propagation via `spec-kitty upgrade`).

**Tests**: SC-006 (full accept pass incl. a negative invariant, 0 hand-edited JSON; malformed reported, 0 exceptions); SC-007 (all-pass persists `pass`).

## Issue-reference discovery (#1738, C-011)

- **FR-012**: widen the SINGLE `_GH_ISSUE_PATTERN` (`tasks/issue_matrix.py:61`) with a same-repo GitHub-issue-URL alternation (repo from the canonical constant/remote). Cross-repo URLs NOT matched. No second matcher.
- **FR-013**: `IssueReference` gains `source_file`; `to_dict`/`from_dict` carry it; multi-file dedup preserves first-occurrence provenance.

**Tests**: SC-008 — a same-repo URL in `spec.md`'s `**Input**` field (samuelgoff #320) is discovered + produces a matrix row + records source_file; an unrelated cross-repo URL in prose does NOT newly block the completeness gate; every discovered ref has a non-empty source_file.

## Terminology foundation (#3080, IC-01)

- **ADR (FR-014)**: `docs/adr/3.x/2026-07-30-1-consolidated-write-surface-and-consolidate-terminology.md` — design (CONSOLIDATED wiring) + canonical-term decision; extends 2026-07-23-2, reaffirms C-006.
- **Glossary (FR-015)**: `docs/context/orchestration.md` — `consolidate` canonical for the lane-consolidation sense; that sense of "merge" → legacy alias + "do NOT use when" guards.
- **Drift guard (FR-016)**: `tests/architectural/test_no_legacy_terminology.py` — curated forbidden lane-consolidation-sense phrasings + baseline allow-set (shrink-only). Bite fixture proves a NEW forbidden phrasing fails (SC-011); green on git-merge/publish uses + grandfathered occurrences.

**Boyscouting (C-012)**: any lane-consolidation-sense "merge" in code/docs this mission touches → canonical in new symbols/touched prose/comments. Existing public merge-named symbols (`spec-kitty merge`, `MergeState`, `baseline_merge_commit`) and git-merge/publish senses stay (→ #3080).
