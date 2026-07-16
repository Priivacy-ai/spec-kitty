# Implementation Plan: Primary & Merge Vocabulary Disambiguation (Track 1)

**Branch**: `feat/terminology-primary-merge-disambiguation` | **Date**: 2026-07-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/primary-merge-vocabulary-01KXP11C/spec.md`

## Summary

Give the overloaded terms **"primary"** (4 senses: PRIMARY partition / Primary Branch / repository root
checkout / target ref) and **"merge"** (3 operations: lane consolidation / branch integration / publish to
origin) **one canonical term each** across the glossary (`docs/context/`), prose/`--help`/docstrings, and a
small set of **SAFE code changes** — with every shipped identifier, serialized key, and CLI/command name
left **byte-identical**. This is **Track 1** of the #2653 epic; the high-risk Sense-C `repository_root_checkout_*`
code rename is **Track 2 (#2730)** and the `src/glossary/` package removal is **#2727**.

Technical approach: a **classified bulk edit**. A plan-phase `occurrence_map.yaml` (this file's sibling)
partitions every in-scope occurrence into CLARIFY-PROSE / RENAME (internal only) / EXEMPT / DEFER-Track-2 /
DO-NOT-TOUCH-unrelated. The load-bearing acceptance property is **invariance**: exempt tokens byte-identical
and the full suite + `ruff` + `mypy --strict` green. Enforcement is honestly scoped — Track 1 ships **no
automated primary/merge sense-guard** (the terminology guard is a hardcoded 2-literal grep); sense-correctness
is review-enforced against the occurrence map, and a durable alias-ban guard is deferred to Track 2 (FR-011).

## Technical Context

**Language/Version**: Python 3.11+ (docs/prose + light code; no runtime behavior change)
**Primary Dependencies**: `docs/context/` glossary prose; `src/specify_cli/` (resolver + merge/partition helpers); `glossary/` legacy prose. No new deps.
**Storage**: N/A — Markdown/YAML text + Python symbol renames; no data migration.
**Testing**: existing `test_git_ops`, `test_tasks_compat_surface`, `test_precondition_ref_unification`, `test_partition_authority_characterization`, merge-helper importers (~13); gate suites: docs anti-sprawl ratchet (`--strict`), description-length, relative-link, `test_no_legacy_terminology.py`; arch pins (`test_mission_runtime_surface`, `test_shared_package_boundary`) must stay green (exempt-surface guard). ATDD red-first for the resolver consolidation + any new alias-ban assertions.
**Target Platform**: Linux/CI (repo tooling)
**Project Type**: single (docs + light code)
**Performance Goals**: N/A (no hot path renamed — Sense-C deferred)
**Constraints**: INVARIANCE — exempt tokens byte-identical (spec C-001/C-002/C-004); `ruff` + `mypy --strict` clean with **zero new suppressions**; sequence around in-flight `mission-step-authority-01KXNZMT` (C-006).
**Scale/Scope**: Bounded. Mostly prose (glossary entries + `--help`/docstring/ADR/CLAUDE.md sweep) + 3-4 internal symbol renames + one resolver consolidation. The occurrence map sizes the exact edit set; expectation is a concentrated, low-LOC change.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** — PASS. `occurrence_map.yaml` is the single authority for what changes; the spec + research are the single authority for the canonical terms. No improvised rename lists.
- **Terminology adherence** — PASS (and is the point). Establishes canonical terms per sense; `docs/context/` is the canonical prose-glossary home. Enforcement scoped honestly (FR-011) — no false claim of gate coverage.
- **ATDD-first** — PASS. Red-first for the `resolve_primary_branch` consolidation (compat-guard + behavior) and any opt-in alias-ban assertions precede edits.
- **Architectural gate discipline** — PASS. No gate relaxed; exempt-surface pins (`test_mission_runtime_surface`, `test_shared_package_boundary`, `test_tasks_compat_surface`) stay green; changes to them are contract updates, not weakenings.
- **Campsite / bulk-edit discipline (DIRECTIVE_035)** — PASS. `change_mode: bulk_edit`; occurrence map actions all 8 categories; ambiguous → human decision.
- **No version prescription** — PASS. No patch number assigned (PO superimposes at release).

No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/primary-merge-vocabulary-01KXP11C/
├── plan.md                 # This file
├── spec.md                 # Mission spec (squad-hardened)
├── occurrence_map.yaml     # REQUIRED bulk-edit classification (sibling of this file)
├── research.md             # Phase 0 (grounded in scratchpad research report)
├── quickstart.md           # Phase 1 verification walkthrough
├── contracts/              # Phase 1 (exempt-surface + canonical-term contracts)
└── tasks.md                # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root) — surfaces this mission touches

```
docs/context/
├── orchestration.md        # FR-001/002 — add primary A/B/D + merge 1/2/3 sense entries (append-only; C-006)
└── execution.md            # FR-001 — Sense-C "repository root checkout" prose entry (prose only; C-002)
glossary/
├── README.md               # FR-005 — repoint stale glossary/contexts/ links → docs/context/
├── historical-terms.md     # FR-006 — fold into docs/context/ (moves[])
└── naming-decision-tool-vs-agent.md  # FR-006 — fold into docs/context/ (moves[])
src/specify_cli/
├── core/git_ops.py                       # FR-007 — canonical resolve_primary_branch (keep)
├── cli/commands/agent/tasks_shared.py    # FR-007 — delegating shim (compat re-export decision)
├── cli/commands/agent/mission_branch_context.py  # FR-007 — _resolve_primary_branch_for_recommendation (fold/scope-out)
├── lanes/merge.py                        # FR-008 — merge_lane_to_mission / merge_mission_to_target (internal rename)
├── cli/commands/implement_cores.py       # FR-008 — _primary_ref_for (internal rename)
├── coordination/commit_router.py         # FR-008 (optional) — _resolve_primary_target_branch
├── cli/commands/merge.py                 # FR-003 — --help / docstring clarify
└── cli/commands/agent/mission_accept_merge.py  # FR-003 — accept→merge --help clarify
CLAUDE.md                   # FR-003/011 — condense 3 warnings → 1 glossary pointer that still names the footgun
docs/adr/3.x/2026-06-24-2-*.md  # FR-003 — clarify the conflating "primary" paragraph
```

**Structure Decision**: Single project. Edits are concentrated in `docs/context/` (glossary), a handful of
`src/specify_cli/` modules (safe renames + resolver consolidation), and top-level prose (`glossary/`,
`CLAUDE.md`, one ADR). No new directories except relocated prose under `docs/context/`.

## Complexity Tracking

*No Charter Check violations → intentionally empty.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Glossary sense entries (`docs/context/`)

- **Purpose**: Author one canonical glossary entry per sense (4 primary + 3 merge) in `orchestration.md`/`execution.md` using the existing per-term table format, with `Do NOT use when` + cross-links.
- **Relevant requirements**: FR-001, FR-002, FR-004 (Primary Branch already exists — extend, don't duplicate).
- **Affected surfaces**: `docs/context/orchestration.md` (append-only blocks — C-006), `docs/context/execution.md`.
- **Sequencing/depends-on**: none (but coordinate with C-06 sequencing vs `mission-step-authority`).
- **Risks**: hot-file collision on `orchestration.md` with in-flight `mission-step-authority-01KXNZMT` (C-006) → keep additions append-only; description-length gate (≤180) on any new page.

### IC-02 — Prose / `--help` / docstring disambiguation sweep

- **Purpose**: Reword the conflating surfaces to name the specific sense; condense CLAUDE.md's 3 warnings into one glossary pointer that still names the partition-vs-branch footgun.
- **Relevant requirements**: FR-003, FR-011.
- **Affected surfaces**: `cli/commands/merge.py`, `cli/commands/agent/mission_accept_merge.py`, `lanes/merge.py`, merge-step doctrine prompts, ADR `2026-06-24-2`, `CLAUDE.md`.
- **Sequencing/depends-on**: IC-01 (entries must exist to cross-reference).
- **Risks**: a `--help`/prose string asserted byte-exact in a test → update assertion in lockstep or treat as exempt (edge case).

### IC-03 — Glossary-infrastructure cleanup

- **Purpose**: One prose-glossary home — repoint `glossary/README.md` and fold legacy `glossary/` prose into `docs/context/`.
- **Relevant requirements**: FR-005, FR-006.
- **Affected surfaces**: `glossary/README.md`, `glossary/historical-terms.md`, `glossary/naming-decision-tool-vs-agent.md`, inbound references (note downstream #1341/#648).
- **Sequencing/depends-on**: none.
- **Risks**: moving docs breaks `../` relative links (`relative_link_fixer --check`) and `.github` symlinks (`git add -f`).

### IC-04 — `resolve_primary_branch` consolidation

- **Purpose**: One canonical resolver behavior; resolve the delegating-shim compat re-export and the recommendation re-implementation (fold-with-bias or scope-out) — DIRECTIVE_044 unification.
- **Relevant requirements**: FR-007.
- **Affected surfaces**: `core/git_ops.py`, `cli/commands/agent/tasks_shared.py`, `cli/commands/agent/tasks.py` (`__all__`), `cli/commands/agent/mission_branch_context.py`; guard `test_tasks_compat_surface`.
- **Sequencing/depends-on**: none.
- **Risks**: `tasks.py.__all__` + `test_tasks_compat_surface` are a pinned compat contract — must move in lockstep; the recommendation re-impl has a deliberate no-feature-bias behavior that must be preserved.

### IC-05 — Internal helper renames (merge + Sense-D)

- **Purpose**: Align genuinely internal helper names to canonical operations; `is_primary_artifact_kind` EXCLUDED (public).
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `lanes/merge.py` (+ `orchestrator_api/commands.py` callers, ~13 test importers, `write_candidate_classification.yaml` arch fixture), `implement_cores.py` (+ `implement.py`, 2 pinning tests), optional `commit_router.py`.
- **Sequencing/depends-on**: IC-04 (same review area, sequence to avoid churn).
- **Risks**: helpers are broadly imported (not "internal-only") — every caller + arch fixture must move together or the surface-audit gate reds.

### IC-06 — Occurrence-map authoring + enforcement disclosure

- **Purpose**: The `occurrence_map.yaml` (all 8 categories) is the single change authority; state the enforcement model honestly (FR-011).
- **Relevant requirements**: FR-009, FR-011, NFR-004, C-005.
- **Affected surfaces**: `occurrence_map.yaml`; spec FR-011 disclosure; optional opt-in alias-ban assertion for non-Sense-C aliases.
- **Sequencing/depends-on**: authored at plan time (this phase); enforced at implement.
- **Risks**: single-term schema vs two-term mission — modeled with `primary` headline + both-term category policy + exceptions (see occurrence_map notes).
