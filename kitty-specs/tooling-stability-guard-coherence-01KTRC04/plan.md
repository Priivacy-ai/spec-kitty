# Implementation Plan: Tooling Stability & Guard Coherence

**Branch**: `fixups/code-engine-stabilization` (continue — accumulates with merged 01KTPKST; **PR held** until stability proven)
**Date**: 2026-06-10 | **Spec**: `kitty-specs/tooling-stability-guard-coherence-01KTRC04/spec.md`
**Input**: amended spec (FR-001..FR-009) + binding architect review (`research/architect-review-spec-vs-design.md`)

## Summary

Complete **ADR 2026-06-03-2 "Strangler Step 7"**: `safe_commit` consumes the resolved `CommitTarget` as its
single atomic decision input, with the protection **policy extracted to an owned Shared-Kernel module**
(operator decision D1) and the entry point staying in `git/commit_helpers.py` (mechanism — zero caller import
churn). Privilege is **structural** (resolved placement + caller capability), never commit-message content
(FR-008/#1334). Planning-phase commit paths (specify/plan/finalize-tasks) thread `ArtifactPlacementFragment`
so protected-target repos stop hitting the catch-22 (FR-003). Independent lanes: structured findings
frontmatter for `record-analysis` (D3), `StatusSurfaceFragment` threading (FR-005), doctor health-render
extraction (FR-006), DRG `Provenanced[T]` wrapper (D2). ATDD-first: the C-003 protection-preserved negative
suite is authored before any conversion (NFR-005).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic (DRG models); internal: `mission_runtime` (`MissionExecutionContext`, `CommitTarget`, `ArtifactPlacementFragment`, `StatusSurfaceFragment` — all built by 01KTPKST), `specify_cli.git.commit_helpers` (1,126 LOC; entry point), `specify_cli.status` (facade), `specify_cli.analysis_report`, `specify_cli.cli.commands.doctor` (3,271 LOC), `src/doctrine/drg/merge.py` (494 LOC)
**Storage**: git refs/branches (commit destinations); YAML frontmatter on `analysis-report.md` (new `analysis-findings/v1` carrier); `status.events.jsonl` unchanged
**Testing**: `pytest`; NEW protection-preserved negative suite (ATDD-first, NFR-005); per-ticket regression repros (#1334/#1777/#1784/#1631/#1820/#1330); `test_safe_commit_import_boundary` ratchet tightened (#1355); `ruff` + `mypy` zero-issue gate; `tests/architectural/` stays green
**Target Platform**: Linux/macOS developer CLI
**Project Type**: single (Python package `src/`)
**Performance Goals**: N/A — correctness/stability mission
**Constraints**: C-003 coherence ≠ removing protection (direct-push-to-origin/main stays blocked); strangler discipline — one live guard at all times, never "GuardV2 beside old"; no parallel mechanisms (NFR-003); enforce at the facade not the rim
**Scale/Scope**: ~15 guard caller files; 9 FR; 12 in-mission tickets; 3 resolved design decisions (D1 SK policy module / D2 Provenanced[T] / D3 frontmatter carrier)

## Charter Check

- **ATDD-First (C-011, binding):** PASS by design — IC-01 authors the protection-preserved negative suite + ticket repros RED/green-locked before any guard conversion (NFR-005).
- **Burn-down (C-004, binding):** PASS — the message-prefix privilege channel is deleted only AFTER all callers are on the CommitTarget path and the negative suite is green; never delete-then-rewire.
- **No parallel mechanisms:** PASS — one guard entry point, one policy module; #1355's import-boundary ratchet enforces it structurally.
- **`__all__` (C-007):** new SK policy module declares `__all__`.
- **Git workflow:** all work on `fixups/code-engine-stabilization`; **no PR** until operator gives the word; no direct push to origin/main — and C-003 makes preserving that protection an explicit success criterion, not a casualty.
- **Terminology Canon:** PASS — no `feature*` aliases introduced.

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this mission)
```
kitty-specs/tooling-stability-guard-coherence-01KTRC04/
├── plan.md / spec.md / issue-matrix.md / checklists/requirements.md
├── research.md                  # D1-D3 decisions + caller census plan + architect review pointer
├── research/architect-review-spec-vs-design.md   # binding intake review
├── data-model.md                # guard verdict model, findings/v1 schema, Provenanced[T]
├── contracts/                   # commit-guard contract + findings-carrier contract
├── quickstart.md                # validation scenarios (SC-1..SC-6)
└── tasks.md                     # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)
```
src/
├── specify_cli/
│   ├── core/commit_guard.py         # NEW — SK policy module (D1): evaluate(CommitTarget, protection, capability)
│   ├── git/commit_helpers.py        # entry point stays; consumes CommitTarget; message-prefix channel DELETED
│   ├── cli/commands/safe_commit_cmd.py  # dir/bulk args + --to-branch (FR-002)
│   ├── cli/commands/ planning commit paths (specify/plan/finalize)  # placement threading (FR-003)
│   ├── analysis_report.py           # findings/v1 frontmatter carrier + verdict-from-structure (FR-004)
│   ├── status/aggregate.py + coordination/status_transition.py  # StatusSurfaceFragment threading (FR-005)
│   └── cli/commands/doctor.py → _profile_health_render.py extraction (FR-006)
├── doctrine/drg/merge.py + models   # Provenanced[T] wrapper + consumer migration (FR-007)
└── mission_runtime/                 # consumed, not changed (CommitTarget already exists)

architecture/3.x/adr/2026-06-03-2-*.md   # addendum (FR-009)
tests/  # protection-preserved suite, ticket repros, import-boundary ratchet
```

**Structure Decision**: single package; ONE new module (`core/commit_guard.py`); everything else is conversion/extraction in place.

## Resolved Plan Decisions (Decision Moment Protocol — all resolved, none deferred)

| ID | Decision | Resolution |
|----|----------|------------|
| D1 (01KTRFSF2S…) | Guard policy home | **Shared Kernel policy module** (`core/commit_guard.py`); `safe_commit` in `git/commit_helpers.py` stays the single entry point (mechanism); policy independently owned + tested |
| D2 (01KTRFSFWZ…) | FR-007 shape | **`Provenanced[T]` wrapper** — typed generic carrier; accept the 3-layer consumer ripple; consumer inventory first; migration in AC |
| D3 (01KTRFSGQ3…) | FR-004 carrier | **Frontmatter block** — schema `analysis-findings/v1` on analysis-report.md; verdict from frontmatter only; loud failure on malformed/missing |

## Implementation Concern Map

> Concerns are NOT work packages; `/spec-kitty.tasks` translates them. Sequencing: IC-01 first (ATDD);
> IC-02 is the spine; IC-03/IC-04 ride the spine; IC-05..IC-08 are independent lanes; IC-09 closes the spine.

### IC-01 — Protection-preserved negative suite (ATDD-first)
- **Purpose**: author the C-003 ratchet BEFORE any conversion: direct-push-to-origin/main blocked; non-placement commits to protected refs refused; the #1334 message-prefix live repro (FAILS against today's bypass, PASSES post-fix as "bypass refused"); these stay green through every subsequent IC.
- **Relevant requirements**: NFR-005, C-003, FR-008 (test half)
- **Affected surfaces**: new test modules under `tests/`
- **Sequencing/depends-on**: none (first)
- **Risks**: the suite must exercise the real guard path (no mocks), per 01KTPKST's mutation-tested precedent.

### IC-02 — Guard spine: caller census + safe_commit(CommitTarget) + SK policy module
- **Purpose**: (1) census ALL caller files of `safe_commit`/`assert_not_protected_branch` (17 call sites confirmed by split review — the rim inventory, first task); (2) create `core/commit_guard.py` (D1) — `evaluate(CommitTarget, protection_state, capability) → verdict`; (3) convert `safe_commit` to consume `CommitTarget` (ADR Step 7) and route every caller through the one entry point; (4) **fold ALL FIVE privilege channels** (split review F-1) into the asserted-at-surface `GuardCapability`: message-prefix list, `allow_protected_branch_in_test_mode` (incl. its `=True` production call sites in agent/workflow.py + agent/mission.py and its propagation through ~8 modules), `allow_completed_op_on_protected_branch`, the op-record file-content exception, env hatches; (5) DELETE all five channels + their helpers (`_is_protected_branch_exception`, `_is_completed_op_record_exception`, `_test_mode_allows_protected_branch`, prefix constants) — strangler-ordered, only after conversion + green suite; capability grants wire ATOMICALLY with the `safe_commit` change (no mid-strangle wedge).
- **Relevant requirements**: FR-001, FR-008
- **Affected surfaces**: `core/commit_guard.py` (new), `git/commit_helpers.py`, the 17 call sites (4 awkward: `upgrade.py` no-context → FLATTENED+capability, `decision_log.py` runtime_bridge boundary, `mission_creation.py` pre-spec, `agent/mission.py` planning paths → IC-04)
- **Sequencing/depends-on**: IC-01
- **Risks**: highest blast radius (every commit in the toolchain) + **self-hosting hazard** (this repo's own WP commits use this guard — document the escape hatch in the WP; never land a broken guard in a WIP commit). Convert callers incrementally; IC-01 suite + existing flows gate each step. Likely 2 WPs at tasks time (mechanical 13 + awkward 4 & channel deletion).

### IC-03 — safe-commit ergonomics (dir/bulk args, --to-branch)
- **Purpose**: directory & bulk arguments match contained files against `worktree_root`; explicit `--to-branch` honored; the `SPEC_KITTY_INFER_DESTINATION_REF` misfire fixed (or that env-var path retired in favor of explicit/context-resolved destination). Folds the #1330 path-handling guidance.
- **Relevant requirements**: FR-002 (#1820, #1330)
- **Affected surfaces**: `cli/commands/safe_commit_cmd.py`, commit helpers
- **Sequencing/depends-on**: IC-02 (CommitTarget in place)
- **Risks**: dir expansion must not silently include unintended files — emit an explicit expansion report.

### IC-04 — Planning-phase placement threading (the catch-22 killer)
- **Purpose**: **Root cause (split review F-2):** `setup-plan`/`finalize-tasks` bypass `resolve_action_context` (no `wp_id` pre-tasks) and `_resolve_planning_branch` reads meta.json as a SECOND destination authority — the #1784 root. Fix: add **`resolve_placement_only(repo_root, mission_slug)`** in `mission_runtime.resolution` — a shared **projection** reusing the resolver's internal helpers (adjudicated: a legitimate op-composite, NOT a C-CTX-1 violation); thread it through specify/plan/finalize-tasks commit paths; **retire the `_resolve_planning_branch` meta.json authority**. Finalize reads the SAME resolution; guard refusals state the resolved destination. E2E: SC-6 fresh-mission-on-protected-target (fixture MUST contain `.kittify/` or the guard is skipped entirely).
- **Relevant requirements**: FR-003 (#1777, #1784, #1631)
- **Affected surfaces**: `mission_runtime/resolution.py` (projection), planning command commit paths, `_resolve_planning_branch` retirement, runbook/prompt text for guard messages
- **Sequencing/depends-on**: IC-02 — and SHARES the destination-authority API with IC-02 (single-destination-authority contract: `evaluate` echoes `CommitTarget.ref`, never re-derives; `--to-branch` resolves into the same CommitTarget)
- **Risks**: must hold for protected-main, flattened, and coord topologies; verify against #1784's step-by-step repro; IC-02↔IC-04 destination split-brain is the named duplication risk — one authority.

### IC-05 — Structured findings carrier (frontmatter) + verdict derivation
- **Purpose**: define the `analysis-findings/v1` frontmatter schema **REUSING the existing canonical severity vocabulary** (binding adjudication: `charter_runtime/lint/findings.py::SEVERITY_ORDER` already encodes the blocking ladder; the codebase has 8+ Severity models — minting a 9th is prohibited); `record-analysis` computes verdict + counts from the validated frontmatter ONLY; missing/malformed carrier → loud structured error **on the write path only** (the freshness/read path tolerates legacy reports with `verdict: unknown`); prose never affects the verdict. Replace `infer_verdict`/`infer_issue_counts` substring logic (delete after cutover). Update the analyze prompt/template so agents emit the frontmatter.
- **Relevant requirements**: FR-004 (#1819), D3
- **Affected surfaces**: `analysis_report.py`, record-analysis path in `cli/commands/agent/mission.py`, analyze command template (SOURCE under `src/doctrine/`)
- **Sequencing/depends-on**: none (independent lane)
- **Risks**: migration window — pre-existing reports lack the carrier; define the fallback policy (legacy reports → `verdict: unknown` + guidance, never a fabricated verdict).

### IC-06 — StatusSurfaceFragment threading
- **Purpose**: `MissionStatus.load` + `coordination/status_transition` consume the carried fragment from the resolved context; delete their local coord-path compositions. Extend the 01KTPKST parity ratchet with an assertion that the fragment is the source (closes the latent SC-4 drift).
- **Relevant requirements**: FR-005 (#1821)
- **Affected surfaces**: `status/aggregate.py`, `coordination/status_transition.py`, parity test (extend)
- **Sequencing/depends-on**: none (independent lane)
- **Risks**: low — both already hit the same authority; threading, not behavior change.

### IC-07 — doctor.py health-render extraction
- **Purpose**: pure extraction of the doctrine health-render helpers into `_profile_health_render.py` beside `_doctrine_health.py`; repoint imports; ZERO behavior change. The full god-module split is explicitly out of scope.
- **Relevant requirements**: FR-006 (#1623)
- **Affected surfaces**: `cli/commands/doctor.py`, new `cli/commands/_profile_health_render.py`
- **Sequencing/depends-on**: none (independent lane)
- **Risks**: low (adversarial finding I-10 scoped it as pure extraction); diff-review for accidental logic edits.

### IC-08 — DRG Provenanced[T] wrapper + consumer migration
- **Purpose**: (1) inventory every `getattr(node, "provenance", None)` / provenance consumer across the 3 layers FIRST; (2) introduce the typed `Provenanced[T]` carrier (D2) replacing the `object.__setattr__` sidecar in `doctrine/drg/merge.py::_tag_source`; (3) migrate all consumers; `mypy` clean.
- **Relevant requirements**: FR-007 (#1624), D2
- **Affected surfaces**: `doctrine/drg/merge.py`, DRG node/edge consumers (3 layers)
- **Sequencing/depends-on**: none (independent lane)
- **Risks**: public-shape change — the consumer inventory gates the design; if the ripple proves larger than inventoried, STOP and escalate rather than half-migrate.

### IC-09 — Spine closure: import-boundary ratchet + ADR addendum
- **Purpose**: tighten `test_safe_commit_import_boundary` once all callers are converted (#1355 — the structural one-guard enforcement); amend ADR 2026-06-03-2 (resolver home path drift + Step 7 delivered by this mission).
- **Relevant requirements**: NFR-004 (#1355), FR-009
- **Affected surfaces**: the boundary test, `architecture/3.x/adr/2026-06-03-2-*.md`
- **Sequencing/depends-on**: IC-02 (+ IC-03/IC-04 callers converted)
- **Risks**: none — ratchet + docs.

### IC-10 — Deep review / sign-off (R-07 pattern)
- **Purpose**: architect-alphonso deep-review of the guard spine (IC-02: capability model, policy module, no message-privilege residue) and the DRG shape change (IC-08); reviewer-renata standard review on all WPs.
- **Relevant requirements**: NFR-003 (one mechanism), C-003
- **Affected surfaces**: cross-cutting (review only)
- **Sequencing/depends-on**: IC-02, IC-08
- **Risks**: this is the gate against the architect review's failure-modes 1–3 (rim-hardening recurrence, relaxation-as-coherence, GuardV2).
