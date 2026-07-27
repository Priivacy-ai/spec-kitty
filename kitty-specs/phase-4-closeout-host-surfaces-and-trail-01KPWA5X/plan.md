# Implementation Plan: Phase 4 Closeout — Host-Surface Breadth and Trail Follow-On

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Mission ID**: `01KPWA5X6617T5TVX4C7S6TMYB`
**Branch**: `main` (current) | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/Users/robert/spec-kitty-dev/charter-apr-23/spec-kitty/kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/spec.md`
**Baseline commit**: `eb32cf0a8118856de9a59eec2635ddda0b956edf` on `origin/main` (Phase 4 core + 3.2.0a5 closeout slice landed)

## Branch Contract

- **Current branch at plan start**: `main`
- **Planning / base branch**: `main`
- **Final merge target**: `main`
- **`branch_matches_target`**: `true`
- Completed changes merge back into `main`. No branch changes during planning.

## Summary

Close out the remaining Phase 4 follow-on work as one combined mission with two strictly-ordered tranches:

- **Tranche A — #496 host-surface breadth tail.** Bring the remaining 13 slash-command + 2 Agent Skills host surfaces to parity with the landed advise/ask/do governance-injection contract, fix shipped misalignments (dashboard user-visible `Feature` → `Mission Run` wording, CLI / README / doc wording sweep), and promote a durable host-surface parity matrix to `docs/host-surface-parity.md`.
- **Tranche B — #701 trail follow-on.** Add four narrow, additive capabilities on top of the shipped trail contract: append-only correlation links (`commit_link`, `artifact_link`) on the invocation JSONL, runtime derivation of `mode_of_work` from the CLI entry command, mode-aware enforcement at the Tier 2 promotion boundary, and a typed SaaS read-model policy module. Tier 2 evidence stays **local-only** in 3.2.x — documented decisively in `docs/trail-model.md`. `#534` / `spec-kitty explain` remains deferred.

Execution is **A → B strict**. The smallest next chunk is Tranche A's dashboard wording fix (scoped to `src/specify_cli/dashboard/templates/index.html`, `.../dashboard/static/dashboard/dashboard.js`, and `.../dashboard/diagnostics.py`), preceded by the host-surface inventory matrix that drives the rest of Tranche A.

## Technical Context

**Language/Version**: Python 3.11+ (existing spec-kitty requirement).
**Primary Dependencies**: Existing toolchain only — `typer` (CLI), `rich` (console), `ruamel.yaml` (YAML frontmatter), `python-ulid` (invocation IDs), `pytest` (tests), `mypy --strict` (types). No new third-party dependency is added.
**Storage**: Filesystem-only. Append-only JSONL at `.kittify/events/profile-invocations/<invocation_id>.jsonl`; existing evidence at `.kittify/evidence/<invocation_id>/`; existing invocation index at `.kittify/events/invocation-index.jsonl`; new documentation at `docs/trail-model.md` (updated in place) and `docs/host-surface-parity.md` (new).
**Testing**: `pytest` with ≥ 90 % line coverage on new code (NFR-004). Mutation-aware coverage is encouraged for new invocation modules but not required as a gate. Headless run via `PWHEADLESS=1 pytest tests/`.
**Target Platform**: Linux + macOS developer environments (unchanged).
**Project Type**: Single-project Python CLI (unchanged — no frontend/backend split).
**Performance Goals**: NFR-001 — P95 `started`-event write ≤ 5 ms, no new blocking I/O before started write. NFR-002 — `spec-kitty invocations list --json` P95 ≤ 200 ms at 10,000 JSONL files.
**Constraints**: Local-first invocation trail (C-002); additive propagation only (C-003); append-only JSONL (C-004); host-LLM ownership unchanged (C-001); no new top-level CLI command (C-008); no broad `Feature` rename (C-007); `#534` stays deferred (C-005); no new third-party dependency (C-009).
**Scale/Scope**: ~15 host surfaces × 3 parity dimensions for Tranche A; 4 new/extended invocation modules + 1 policy module + 1 CLI flag extension + ~6 documentation updates for Tranche B. Estimated ~12 work packages total (5 Tranche A + 7 Tranche B), formalised by `/spec-kitty.tasks`.

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present at `.kittify/charter/charter.md`. Action doctrine loaded for `plan` (bootstrap mode, first-load).

| Gate | Source | Evaluation | Status |
|------|--------|------------|--------|
| Host-LLM ownership immutable | C-001 + architecture policy | Plan introduces no LLM invocation inside Spec Kitty; all reading/generation stays host-side. | PASS |
| Local-first trail invariant | C-002 + `_propagate_one` sync-gate | Plan keeps Tier 1 writes unconditional; SaaS policy is read-side only, never blocks Tier 1. | PASS |
| Additive propagation | C-003 + emitter contract | New events (`artifact_link`, `commit_link`) are additive new lines; new fields (`mode_of_work`) are additive on existing event shape. | PASS |
| Append-only JSONL | C-004 + `InvocationWriter` | `write_started` stays exclusive-create; new `append_correlation_link` uses append mode; no existing line mutated. | PASS |
| `#534` stays deferred | C-005 | Plan contains no `spec-kitty explain` design or scaffolding. | PASS |
| No Phase 5 glossary rework | C-006 + mission 094 landed | Plan does not touch chokepoint, DRG, or glossary term registry. | PASS |
| No broad `Feature` rename | C-007 | Scope is the 3 dashboard files only; backend identifiers preserved per FR-004. | PASS |
| No new top-level CLI command | C-008 | Correlation ships as flags on existing `profile-invocation complete`; no new verb. | PASS |
| Tooling conformance | C-009 | Plan uses typer/rich/ruamel.yaml/pytest/mypy only. | PASS |
| DIRECTIVE_003 decision capture | Charter `plan` doctrine | Four ADRs defined (correlation, mode derivation, SaaS policy shape, Tier 2 resolution) — see `decisions/` plan in Phase 1. | PASS |
| DIRECTIVE_010 spec fidelity | Charter `plan` doctrine | Plan traces each FR/NFR/C back to a concrete implementation target; deviations explicitly called out below (none). | PASS |

**Tactic application notes:**
- **Problem decomposition**: tranche split + WP sketch (Section "Project Structure" below) decomposes the mission into 12 independently tractable WPs.
- **Premortem risk identification**: applied in `research.md` (Failure Modes section).
- **ADR drafting workflow**: applied for the four material decisions.
- **Requirements validation workflow**: every FR is traced to an evidence/acceptance surface in `research.md` and `contracts/`.

**Charter Check: PASS — no violations, no Complexity Tracking entries needed.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/
├── plan.md                              # This file
├── spec.md                              # Mission specification
├── research.md                          # Phase 0 output — decisions D1..D10 with rationale
├── data-model.md                        # Phase 1 output — InvocationRecord, correlation events, ModeOfWork, ProjectionRule, inventory schema
├── quickstart.md                        # Phase 1 output — operator walkthrough of new capabilities
├── contracts/
│   ├── profile-invocation-complete.md   # CLI contract for extended `complete` with --commit / --artifact
│   ├── projection-policy.md             # Python module contract for projection_policy.py
│   └── host-surface-inventory.md        # Inventory matrix schema + example row
├── decisions/
│   ├── ADR-001-correlation-contract.md  # D1 decision record
│   ├── ADR-002-mode-derivation.md       # D2 decision record
│   ├── ADR-003-projection-policy.md     # D4 decision record
│   └── ADR-004-tier2-saas-deferral.md   # D5 decision record
├── artifacts/
│   └── host-surface-inventory.md        # Tranche A living matrix (promoted to docs/ at closeout)
├── checklists/
│   └── requirements.md                  # Spec quality checklist (already complete)
├── tasks/                               # Populated by /spec-kitty.tasks (not this command)
└── status.events.jsonl                  # Status event log (runtime-managed)
```

### Source Code (repository root)

Work touches only files already committed to `main`; there is no new package directory.

```
src/specify_cli/
├── invocation/
│   ├── executor.py                 # MODIFIED (Tranche B): mode derivation on started event; read mode on complete_invocation for enforcement
│   ├── writer.py                   # MODIFIED (Tranche B): append_correlation_link() — new append method for artifact_link/commit_link events
│   ├── record.py                   # MODIFIED (Tranche B): InvocationRecord gains optional `mode_of_work` field (null-tolerant)
│   ├── errors.py                   # MODIFIED (Tranche B): add InvalidModeForEvidenceError
│   ├── propagator.py               # MODIFIED (Tranche B): consult PROJECTION_POLICY before envelope build
│   ├── projection_policy.py        # NEW (Tranche B): typed module — ModeOfWork + ProjectionRule + POLICY_TABLE + resolve_projection()
│   └── modes.py                    # NEW (Tranche B): ModeOfWork enum + derive_mode(entry_command) helper
├── dashboard/
│   ├── templates/index.html        # MODIFIED (Tranche A): user-visible Feature → Mission Run wording (5 strings)
│   ├── static/dashboard/dashboard.js  # MODIFIED (Tranche A): user-visible wording + "Unknown feature" fallback (~6 strings)
│   ├── static/dashboard/dashboard.css # UNCHANGED — class names .feature-selector etc. stay per FR-004
│   └── diagnostics.py              # MODIFIED (Tranche A): "no feature context" → "no mission context"
└── cli/
    └── commands/
        └── profile_invocation.py   # MODIFIED (Tranche B): add --commit and --artifact flags to `complete` subcommand

docs/
├── trail-model.md                  # MODIFIED: new subsections — "Mode of Work (runtime-enforced)", "Correlation Links", "SaaS Read-Model Policy", "Tier 2 SaaS Projection — deferred"
└── host-surface-parity.md          # NEW (Tranche A closeout): promoted matrix

src/doctrine/skills/
├── spec-kitty-runtime-next/SKILL.md       # VERIFY PARITY (Tranche A) — already has Standalone Invocations section
└── (13 slash-command agent skill-pack mirrors per CLAUDE.md AGENT_DIRS)
                                            # TOUCHED per agent config — VERIFY PARITY (Tranche A)

.agents/skills/
└── spec-kitty.advise/SKILL.md      # VERIFY PARITY (Tranche A) — already has Governance context injection section

tests/specify_cli/invocation/
├── test_invocation_e2e.py          # EXTENDED (Tranche B): add correlation-link write/read; mode enforcement; projection policy
├── test_projection_policy.py       # NEW (Tranche B): parameterised table test
├── test_modes.py                   # NEW (Tranche B): derive_mode() mapping test
└── test_correlation.py             # NEW (Tranche B): append_correlation_link + path-normalisation
tests/specify_cli/dashboard/
└── test_dashboard_wording.py       # NEW (Tranche A): asserts user-visible mission wording in template/js/diagnostics
```

**Structure Decision**: Single-project Python CLI (existing layout). All new runtime code lands in `src/specify_cli/invocation/` next to existing modules; dashboard wording changes are scoped to three files; docs gain one new operator-facing file plus additions to `trail-model.md`. No restructuring.

### Work Package Sketch (finalised by `/spec-kitty.tasks`)

Tranche A (strict predecessor of Tranche B):
1. **WP01** — Host-surface inventory matrix (builds the parity matrix at `artifacts/host-surface-inventory.md`; determines A3–A5 scope).
2. **WP02** — Dashboard user-visible wording fix (`index.html`, `dashboard.js`, `diagnostics.py`) — the smallest-next chunk once WP01 confirms scope.
3. **WP03** — Rendering-contract consistency sweep (CLI help strings for advise/ask/do/complete/list, README governance section, cross-doc wording).
4. **WP04** — Skill-pack parity rollout to the host surfaces WP01 flags as non-parity. Each surface either receives in-surface parity content or an explicit pointer, per FR-002 / FR-006.
5. **WP05** — Promote `artifacts/host-surface-inventory.md` to `docs/host-surface-parity.md`; close `#496`.

Tranche B (starts only after WP05 is approved):

6. **WP06** — Mode derivation: add `src/specify_cli/invocation/modes.py`; record `mode_of_work` on `started` event; backfill null-tolerance on read paths.
7. **WP07** — Correlation contract: `InvocationWriter.append_correlation_link()`; extend `profile-invocation complete` with repeatable `--artifact` and singular `--commit`; artifact-ref normalisation to repo-relative when under checkout, absolute fallback otherwise.
8. **WP08** — Mode enforcement at promotion: `InvalidModeForEvidenceError`; `complete_invocation` reads started-event mode and rejects `--evidence` on `advisory`/`query`.
9. **WP09** — SaaS read-model policy: `src/specify_cli/invocation/projection_policy.py` as a typed module; wire `_propagate_one` through `resolve_projection()`; `docs/trail-model.md` policy table.
10. **WP10** — Tier 2 SaaS projection — keep local-only: update `docs/trail-model.md` with the "Tier 2 SaaS Projection — deferred" subsection and reasoning; no code change (D5 decision).
11. **WP11** — Migration note + CHANGELOG entry (FR-013).
12. **WP12** — Tracker hygiene execution: close `#496` at WP05 merge; close `#701`, update `#466`, cross-link `#534` to `#499`/`#759` at mission merge (FR-014). CLI-level executor for this WP is a scripted checklist run by the release owner — no code change.

Task dependencies are straightforward (A→B strict; within each tranche roughly linear except WP03 can run in parallel with WP04 once WP01 is complete). `/spec-kitty.tasks` will finalise lanes.

## Complexity Tracking

*Fill ONLY if Charter Check has violations that must be justified*

No Charter Check violations. No complexity entries required.

---

## Phase 0 — Outline & Research

**Goal**: Resolve every design unknown identified during the planning interrogation, grounded in the live `main` baseline and the spec.

Research methodology:
- Inspect landed code at `eb32cf0a` for `invocation/`, `dashboard/`, propagator sync-gate behaviour, and `complete_invocation` promotion path.
- Cross-reference GitHub issues `#496`, `#701`, `#534`, `#461`, `#466` for acceptance language.
- Cross-reference CLAUDE.md `AGENT_DIRS` and the per-agent directory conventions for Tranche A host-surface inventory.
- Apply the premortem tactic (from `plan` action doctrine) to surface failure modes for each of the 10 design decisions.

**Output**: `research.md` — full D1–D10 resolution with rationale, alternatives considered, rejected options, failure modes, and acceptance-surface mapping per FR.

Every `[NEEDS CLARIFICATION]` slot is resolved in `research.md`. None remains open.

---

## Phase 1 — Design & Contracts

**Prerequisite**: `research.md` complete.

Design artifacts to generate:

1. **`data-model.md`** — Typed data-model for the new/extended entities:
   - `InvocationRecord` (extended): new optional `mode_of_work: ModeOfWork | None` field on `started` events; unchanged `completed` schema; null-tolerant on read for pre-mission records.
   - `ModeOfWork` enum: `advisory`, `task_execution`, `mission_step`, `query`. Exhaustive derivation mapping from CLI entry command.
   - Correlation events: `{event: "artifact_link", invocation_id, kind, ref, at}` and `{event: "commit_link", invocation_id, sha, at}`. Ref-normalisation rule: repo-relative when the resolved absolute path is under the repo root, absolute fallback otherwise.
   - `ProjectionRule` dataclass: `{project: bool, include_request_text: bool, include_evidence_ref: bool}`.
   - `POLICY_TABLE: dict[tuple[ModeOfWork, EventKind], ProjectionRule]` — the backing table for the lookup helper.
   - `HostSurfaceInventoryRow`: `{surface_key, directory, has_advise_guidance, has_governance_injection, has_completion_guidance, guidance_style: "inline" | "pointer", notes}`.

2. **`contracts/`**:
   - `profile-invocation-complete.md` — CLI contract for the extended `complete` subcommand: flag semantics, exit codes, error shapes, examples. Specifies that `--artifact` is repeatable and `--commit` is singular. Specifies ref-normalisation: canonicalise to repo-relative when the resolved path is under `repo_root`; otherwise record the absolute path as-provided.
   - `projection-policy.md` — Python module contract for `src/specify_cli/invocation/projection_policy.py`: `ModeOfWork` + `EventKind` + `ProjectionRule` + `POLICY_TABLE` + `resolve_projection(mode, event) -> ProjectionRule`. Import surface, typed signatures, invariants.
   - `host-surface-inventory.md` — Inventory-matrix schema + one worked example row so Tranche A WP01 can be executed mechanically.

3. **`quickstart.md`** — Operator walkthrough that exercises, end-to-end: (a) invoking `spec-kitty do "…"` → reading `mode_of_work` in the JSONL → closing with `--artifact` and `--commit` → listing the same invocation with its correlation links; (b) attempting Tier 2 promotion on an `advisory` invocation and seeing the rejection; (c) reading the SaaS projection policy table from `docs/trail-model.md`; (d) confirming `propagation-errors.jsonl` stays empty with sync disabled.

4. **`decisions/`** — Four ADRs, each ~40–80 lines, using the `adr-drafting-workflow` tactic format (context, decision, rationale, alternatives considered, consequences, revisit trigger):
   - `ADR-001-correlation-contract.md` (D1)
   - `ADR-002-mode-derivation.md` (D2)
   - `ADR-003-projection-policy.md` (D4)
   - `ADR-004-tier2-saas-deferral.md` (D5)

**Charter re-check after Phase 1:** re-evaluated below (same 11 gates), still PASS after artifacts are authored. Re-check is recorded in the footer of this plan at report time.

---

## Post-Phase-1 Charter Re-check

| Gate | Status after design |
|------|---------------------|
| Host-LLM ownership immutable | PASS — no LLM calls added in any design artifact. |
| Local-first trail invariant | PASS — `resolve_projection()` is read-side; propagator still short-circuits on `routing.effective_sync_enabled` before policy lookup. |
| Additive propagation | PASS — `mode_of_work` is additive-null; correlation events are additive new lines; `POLICY_TABLE` does not remove or reshape existing fields. |
| Append-only JSONL | PASS — `append_correlation_link` uses append; `write_started` / `write_completed` unchanged. |
| `#534` stays deferred | PASS — no explain surface in any artifact. |
| No Phase 5 glossary rework | PASS — glossary modules untouched. |
| No broad `Feature` rename | PASS — design limits wording change to the three identified dashboard files. |
| No new top-level CLI command | PASS — correlation ships as flags, not a new verb. |
| Tooling conformance | PASS — typer/rich/ruamel.yaml/pytest/mypy only. |
| DIRECTIVE_003 decision capture | PASS — four ADRs drafted in `decisions/`. |
| DIRECTIVE_010 spec fidelity | PASS — every FR/NFR/C maps to a concrete artifact surface in `data-model.md` or `contracts/`. |

---

## Risks and Mitigations (from Premortem Tactic)

Applied to each design decision; full narrative in `research.md` Section "Failure Modes and Premortem".

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dashboard wording bleed beyond the three files | Low | Medium | WP01 inventory must list every user-visible `Feature` string; WP02 tests assert on specific template/JS/diagnostics strings; plan commits wording grep in the test. |
| Mode enforcement false-positive (legitimate `task_execution` misclassified as `advisory`) | Low | Medium | D2 derivation is from CLI entry command, not routed action — deterministic and documented. Parameterised test (WP06) covers every entry command. |
| Correlation event confuses old readers | Low | Low | Readers already skip unknown `event` values (see `glossary_checked` precedent in `writer.py`); contract documents that `artifact_link`/`commit_link` are additive. |
| `resolve_projection()` bug silently drops Tier 1 propagation | Low | High | NFR-007 test asserts zero errors with sync disabled; contract test asserts default behaviour for `(task_execution, started)` projects exactly as today. |
| Ref-normalisation breaks for symlinked repos or worktrees | Medium | Low | Use `Path.resolve().is_relative_to(repo_root.resolve())` pattern (already used in `complete_invocation` for evidence ref); WP07 tests include worktree + symlink cases. |
| Tracker hygiene forgotten at merge | Medium | Low | WP12 is a dedicated WP and is part of Definition of Done (FR-014); checklist in `quickstart.md` operator section. |

---

## Artifact Index

- Plan: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/plan.md`
- Spec: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/spec.md`
- Research: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/research.md`
- Data model: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/data-model.md`
- Quickstart: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/quickstart.md`
- Contracts: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/contracts/`
- Decision records: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/decisions/`
- Checklists: `kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/checklists/requirements.md`

Branch contract (restated): current `main`, planning base `main`, merge target `main`, `branch_matches_target=true`.
