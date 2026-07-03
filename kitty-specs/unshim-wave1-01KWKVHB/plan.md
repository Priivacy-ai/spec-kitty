# Implementation Plan: Unshim Wave 1 — category_4 shim deletion + category_7 orphan triage

**Branch**: `tidy/unshim-wave1` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md) (rev 2, squad-hardened)
**Input**: Feature specification from `/kitty-specs/unshim-wave1-01KWKVHB/spec.md`

## Summary

Pure zero-caller deletion + census-coherence mission: delete the 8 category_4 backcompat re-export shims (#2289, 135 LOC) with ~45–50 test re-anchors to squad-verified canonical homes, and execute the category_7 adjudication (#2292): delete 4 orphans (833 LOC + 3 single-purpose test files), keep `policy.audit` (adopt-as-follow-up issue), keep `auth.transport` untouched (ADR 2026-05-18-2 deferral to Robert). Every deletion drains its gate/baseline rows atomically in the same WP (C-006 — the stale-allowlist guard reds any intermediate tip otherwise). The #2258 dead-function prune already rides this branch as a completed pre-mission op (commit `c194f8d`). No behavior changes to live code; the mission's value is gate-trap atomicity, census integrity, and tracker coherence — deliberately thin by squad-proven construction (the green bidirectional dead-module gate guarantees no hidden foldable surface exists).

## Technical Context

**Language/Version**: Python 3.11 (repo standard; `.python-version` 3.11.15)
**Primary Dependencies**: pytest (+ pytest-xdist), ruff, mypy, PyYAML (only as already present — no new dependencies; deletion-only diff)
**Storage**: N/A (no data surfaces; `_baselines.yaml` and allowlist frozensets are the only "state" edited)
**Testing**: `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider` full suite; targeted `tests/architectural/test_no_dead_modules.py` + `test_no_dead_symbols.py` per WP; per-site `patch()` interception proofs per AC 1.2 (assert_called* or red-first bogus-target flip)
**Target Platform**: Linux dev/CI (repo-standard)
**Project Type**: single (existing `src/specify_cli` + `tests/` layout; no structural changes — only deletions within it)
**Performance Goals**: N/A (no runtime paths change; NFR-001 requires the parallel suite green, no new budget gates)
**Constraints**: C-001 auth.transport no-touch (ADR-bound); C-002 deletion/triage only; C-003 `next/`+glossary out of scope (#2291); C-006 atomic delete+drain per WP; refactor-stable doctrine self-conformance (shrink-only ratchets, no re-pins)
**Scale/Scope**: 12 module deletions (≈968 src LOC) + 3 test-file deletions (≈539 LOC) + ~45–50 re-anchor edits across ~19 test files + gate/config drains in 4 files + ~13 LOC doc hygiene + tracker closeout

## Charter Check

*GATE: evaluated against `.kittify/charter/charter.md` (compact context loaded).*

- **Single canonical authority / unification**: ✅ the mission's whole point — one import path per module, shim aliases removed; census corrected where issue bodies drifted (C-005).
- **Quality & Tech-Debt Standing Orders**: ✅ campsite cleaning (doc-path re-points ride the deletions); adversarial squad cadence honored (pre-spec 4-lens + post-spec 3-lens, findings folded as spec rev 2); test-remediation discipline (deleted tests adjudicated per the judge-the-test framework — single-purpose shields delete with their dead subjects, live-contract tests re-anchor); canonical sources (doctrine templates used; verified canonical homes are the re-anchor authority).
- **ATDD-first / red-first**: adapted for deletion work — the stale-allowlist guard IS the executable contract (a deletion without its drain reds; a drain without its deletion reds). The `patch()` interception proofs are the red-first surface for re-anchors (AC 1.2 option b is literally a red-flip proof).
- **Architectural gate discipline**: ✅ full `tests/architectural/` sweep per WP and on the merged branch; all baseline changes shrink-only (NFR-004).
- **Terminology canon**: ✅ prose audited; no `feature*`/banned terms introduced.
- **Git/workflow discipline**: ✅ planning on `tidy/unshim-wave1`; lands on upstream main via PR only; operator merges.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/unshim-wave1-01KWKVHB/
├── spec.md              # rev 2 (squad-hardened census = binding facts)
├── issue-matrix.md      # tracker verdicts incl. executed #2258 op
├── plan.md              # this file
├── research.md          # Phase 0: squad-synthesis decisions D1–D8
├── quickstart.md        # Phase 1: per-WP and merge-time validation commands
└── tasks.md + tasks/    # Phase 2 (/spec-kitty.tasks)
```

`data-model.md` and `contracts/`: **N/A by design** — no data entities, no API surfaces; the "contract" of this mission is the stale-allowlist guard + the spec's verified-canonical-homes table, both already binding. Recorded here so downstream gates don't read absence as omission.

### Source Code (repository root)

```
DELETE (src, 12 modules):
src/specify_cli/{acceptance_matrix,doc_generators,doc_state,gap_analysis,state_contract,tasks_support,workspace_context,task_profile}.py
src/specify_cli/core/identity_aliases.py
src/specify_cli/sync/{replay,tracker_client_glue}.py
src/specify_cli/retrospective/lifecycle.py

DELETE (tests, 3 single-purpose shields):
tests/.../test_replay_tenant_collision.py
tests/.../test_task_profile_suggestion.py
tests/.../test_tracker_bidirectional_retry.py

EDIT (re-anchors, ~19 test files — authority: spec rev 2 canonical-homes table;
      dominant: ~14 files for tasks_support incl. 10 patch() strings → task_utils)

EDIT (gate/config drains, atomic per C-006):
tests/architectural/test_no_dead_modules.py    (_CATEGORY_4 8→0, _CATEGORY_7 6→2)
tests/architectural/test_no_dead_symbols.py    (identity_aliases row :176 + replay×8 + glue×4 = −13 category_b)
tests/architectural/_baselines.yaml            (category_4 0, category_7 2, category_b 224)
pyproject.toml                                 (3 mypy-override entries removed)

EDIT (doc hygiene):
src/specify_cli/sync/queue.py                  (:1352 docstring xref scrub)
docs/architecture/documentation-mission.md     (:899-901 → doc_analysis.* paths)
docs/plans/degod-unshim-inventory.md           (strike executed rows at closeout)
```

**Structure Decision**: single-project layout unchanged; deletion-only diff inside existing directories. No package becomes empty (verified: every deleted file has surviving siblings or is top-level).

## Implementation Concern Map

> Concerns are not WPs; `/spec-kitty.tasks` translates them. Squad-adjudicated shape: **single sequential lane** (paula × alphonso convergence — 2-lane parallelism is illusory: co-tenant gate files force carve-out overhead for zero wall-clock gain on deletion work).

### IC-01 — Category_4 core sweep (7 shims minus tasks_support)

- **Purpose**: Delete the 7 non-tasks_support shims and re-anchor their ~14 test sites to verified canonical homes; drain their gate rows atomically.
- **Relevant requirements**: FR-001, FR-002 (partial), FR-003 (partial)
- **Affected surfaces**: the 7 shim files; their re-anchor test files; `test_no_dead_modules.py` `_CATEGORY_4` rows; `test_no_dead_symbols.py:176` (identity_aliases — NOTE: also the −1 of category_b's −13); `_baselines.yaml category_4` 8→1; pyproject overrides for `doc_state`+`gap_analysis`; `doc_state` dynamic `import … as mod` sites need module-object re-anchoring.
- **Sequencing/depends-on**: none (first).
- **Risks**: missing a re-anchor leaves the canonical home "dead-module"-flagged mid-WP — run the architectural sweep after the batch, not just at the end; 3 shims (`identity_aliases`, `state_contract`, `workspace_context`) are zero-importer pure deletes.

### IC-02 — tasks_support risk-isolated re-anchor

- **Purpose**: Delete `tasks_support` and re-anchor its ~35 sites / ~14 files — the entire silent-no-op risk class — with per-site interception proofs.
- **Relevant requirements**: FR-001, FR-002 (dominant), FR-003 (remainder: last `_CATEGORY_4` row, `category_4` 1→0, tasks_support pyproject override)
- **Affected surfaces**: `tasks_support.py`; ~14 test files incl. the 10 `patch("specify_cli.tasks_support...")` strings (rewrite target = consumer's lookup namespace, per AC 1.2 note); `test_no_dead_modules.py`; `_baselines.yaml`; `pyproject.toml`.
- **Sequencing/depends-on**: IC-01 (keeps every tip green with a monotone category_4 count).
- **Risks**: the AC 1.2 proof obligation is the WP's core deliverable, not an afterthought — most of the 10 patch sites have NO call assertion today; reviewer's whole surface is "did every re-pointed mock provably still intercept".

### IC-03 — Category_7 orphan execution

- **Purpose**: Delete the 4 adjudicated orphans + their 3 test shields; scrub the queue.py docstring xref; re-point the documentation-mission.md paths; drain category_7/category_b rows atomically.
- **Relevant requirements**: FR-004, FR-005
- **Affected surfaces**: the 4 orphan modules; 3 test files; `sync/queue.py:1352`; `docs/architecture/documentation-mission.md:899-901`; `test_no_dead_modules.py` `_CATEGORY_7` 6→2; `test_no_dead_symbols.py` replay×8+glue×4 rows; `_baselines.yaml` category_7 2 / category_b 224.
- **Sequencing/depends-on**: IC-01, IC-02 (single lane; also the category_b arithmetic depends on IC-01's identity_aliases −1 having landed).
- **Risks**: C-001 hard boundary — `auth/transport.py` and its singleton tests MUST NOT appear in any diff; `policy/audit.py` + its test stay intact.

### IC-04 — Adjudication records + tracker/doc closeout

- **Purpose**: Make the non-executed verdicts durable and the tracker coherent: policy.audit follow-up issue, auth.transport ADR-deferred verdict + #2292 attribution correction, epic #1797 progress comment, degod-unshim-inventory strike-through, the two new debt-class issue filings (operator may veto), issue-matrix terminal verdicts.
- **Relevant requirements**: FR-006, FR-007, FR-008
- **Affected surfaces**: tracker (gh) + `docs/plans/degod-unshim-inventory.md` + `kitty-specs/unshim-wave1-01KWKVHB/issue-matrix.md`. No src.
- **Sequencing/depends-on**: IC-03 (records final counts/evidence).
- **Risks**: premature issue closure (#2289/#2292/#2258 close via the PR's `Closes` lines, never by hand); NFR-002's pinned grep runs at merge time here.

## Complexity Tracking

*(empty — no charter violations)*
