# Mission Specification: Tooling Stability & Guard Coherence

**Mission ID**: 01KTRC044W67V3KC9H7TBFSY7B
**Slug**: tooling-stability-guard-coherence-01KTRC04
**Type**: software-dev
**Target + planning branch**: fixups/code-engine-stabilization (continue — PR held until tooling stability is proven)
**Parent**: #1619 (unify mission execution context) · slice; advances #1796
**Drains (intake)**: #1819, #1820, #1821, #1796, #1334, #1777, #1784, #1631, #1623, #1624, #1330, #1355
**Design anchor**: ADR 2026-06-03-2 Decision 2 — this mission completes the deferred **"Strangler Step 7"** (`safe_commit` consumes `CommitTarget`). See `research/architect-review-spec-vs-design.md`.

## Purpose

Mission 01KTPKST's closeout + dogfood surfaced **tooling-stability papercuts** in spec-kitty's own command surfaces (the operator hits them on every mission): the `record-analysis` verdict miscounts severities, `safe-commit`/protected-branch guards fight legitimate commits, and the status surface is not fully threaded onto the resolved context. This follow-up — a slice of #1619 — **hardens those surfaces into coherent, stable mechanisms** and clears two deferred code-health debts (`doctor.py` god-module, `merge.py` typing). The bar this mission sets is the operator's PR-gate: *the tooling must be significantly more stable before the accumulated execution-context work is PR'd.*

## User Scenarios & Testing

**Primary actor:** an operator/agent running spec-kitty commands during a mission lifecycle.

- **Scenario A — commit guard is coherent:** an operator runs `safe-commit` with a directory argument, on a protected branch, for a legitimate `spec.md`/planning artifact, with an explicit `--to-branch`. *Success:* the commit succeeds (or is blocked with an actionable, correct reason) via **one** guard — no contradictory protected-branch / message-prefix / destination-ref behaviors, and the no-direct-push-to-origin/main protection still holds.
- **Scenario B — analysis verdict is honest:** `record-analysis` on a report with no blocking findings returns `ready`; on a report with a real CRITICAL finding returns `blocked` — **derived from the structured findings table**, not prose wording. *Success:* verdict matches the table regardless of prose.
- **Scenario C — status resolves once:** `MissionStatus.load` and `status_transition` resolve their surface from the carried `StatusSurfaceFragment` (single path). *Success:* a static check shows no second coord-path re-derivation.
- **Scenario D — debt cleared:** `doctor.py` is no longer a god-module (health-render extracted to focused modules); `merge.py`'s `_tag_source` sidecar is typed. *Success:* `mypy` clean; module sizes/responsibilities focused.

## Functional Requirements

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-001 | **Complete ADR 2026-06-03-2 "Strangler Step 7":** the consolidated safe-commit / protected-branch / destination-ref guard **consumes the resolved `CommitTarget`** (from the `MissionExecutionContext` / `ArtifactPlacementFragment`) as its single atomic decision input — `safe_commit(CommitTarget, …)` becomes the ONE guard entry point. Enforce **at the facade, not at the rim**: all ~15 caller files route through it. *(Plan decision: the guard's bounded-context home — recommended Shared Kernel.)* | #1796 / ADR 2026-06-03-2 | Draft |
| FR-002 | `safe-commit` **accepts directory and bulk arguments** (matching contained files against `worktree_root`) and **honors explicit `--to-branch`**; the `SPEC_KITTY_INFER_DESTINATION_REF` path no longer misfires with "No requested changes". Folds the #1330 path-handling guidance. | #1820, #1330 | Draft |
| FR-003 | **Legitimacy is defined by resolved placement, not guard relaxation:** a commit is legitimate iff the resolved `CommitTarget`/`ArtifactPlacementFragment` names that ref as the intended destination. **Root-cause finding (split review F-2):** the planning paths (`setup-plan`/`finalize-tasks`) bypass `resolve_action_context` entirely (no `wp_id` pre-tasks) and `_resolve_planning_branch` reads meta.json as a SECOND destination authority — the actual #1784 root. Fix: expose a **`resolve_placement_only(repo_root, mission_slug)` projection** in `mission_runtime.resolution` (a legitimate op-composite sharing the resolver's internal helpers — NOT a parallel resolver), thread it through specify / plan / finalize-tasks, and **retire the meta.json second authority**. Guard refusal messages state the resolved destination (no "switch to lane branch" advice pre-lanes); direct-push-to-origin/main protection preserved (C-003). | #1777, #1784, #1631, split review F-2 | Draft |
| FR-004 | `record-analysis` **verdict + issue-counts derive from a structured findings carrier** (frontmatter, per D3) — never from substring-counting report prose. **Reuse, don't mint (binding):** the carrier's severity vocabulary REUSES the existing canonical severity model (the codebase already has 8+ `Severity`/`Finding` models; `charter_runtime/lint/findings.py::SEVERITY_ORDER` already encodes the blocking ladder) — minting a 9th vocabulary is prohibited. Malformed/missing carrier fails loudly on the **write path**; vocab drift fails schema validation. | #1819, split review (randy, binding) | Draft |
| FR-005 | `MissionStatus.load` + `coordination/status_transition` **consume the carried `StatusSurfaceFragment`** from the resolved `MissionExecutionContext` (single resolution path; no second coord-path composition). | #1821 | Draft |
| FR-006 | **Extract the doctrine health-render helpers from `doctor.py`** into focused module(s) beside `_doctrine_health.py` (DIRECTIVE_013 / adversarial finding I-10) — **pure extraction, behavior-preserving**. The full god-module split of `doctor.py` (3,271 LOC) is explicitly OUT of this FR's scope. | #1623 | Draft |
| FR-007 | **Type the `_tag_source` provenance sidecar in `src/doctrine/drg/merge.py`** (Governance domain; DIRECTIVE_013). This is a **public-shape change**: the fix (typed `Provenanced[T]` wrapper OR a declared optional field on the models — *decide in plan*) ripples through every `getattr(node, "provenance", None)` consumer across 3 layers; the consumer migration is part of the acceptance criteria. `mypy` clean on the touched path. | #1624 | Draft |
| FR-008 | **One privilege channel: the asserted capability.** The live code carries **FIVE** privilege channels — (1) the `_is_protected_branch_exception` message-prefix list, (2) `allow_protected_branch_in_test_mode` (passed `=True` at production sites), (3) `allow_completed_op_on_protected_branch`, (4) the op-record *file-content* exception, (5) env hatches. ALL five fold into the single **`GuardCapability` asserted-at-the-surface parameter** (split-review adjudication: assert-at-surface, NOT derived — `CommitTarget.kind` is topology, not operation intent; capability value is auditability for the LLM-agent threat model, defaults `standard`, and can never expand past the resolved placement). The guard MUST NOT derive privilege from commit-message content, file content, or ambient env. The #1334 live repro + a per-channel refusal test become **permanent negative regression tests**. | #1334, split review F-1 | Draft |
| FR-009 | **ADR addendum:** amend ADR 2026-06-03-2 to record (a) `resolve_action_context`'s actual post-boundary home (`src/mission_runtime/resolution.py`, not the retired `specify_cli/core/execution_context.py` path), (b) the delivered `CommitTarget` shape `(ref, kind)` vs the ADR's sketched `(worktree_root, destination_ref)` — the shape drift is deliberate and now canonical, and (c) Step 7 as delivered by this mission. | architect review G-8, split review F-3 | Draft |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | Backward compatibility. | No regression to existing commit/guard/analysis/status flows; existing suites green. | Draft |
| NFR-002 | Code quality. | `ruff` + `mypy` zero issues on changed paths; `tests/architectural/` (terminology, shared-package-boundary, dead-symbols, parity) pass. | Draft |
| NFR-003 | No parallel mechanisms. | ONE commit-guard, ONE status resolution path; static/review check confirms (C-005 carryover). | Draft |
| NFR-004 | Stability evidence. | Each drained ticket carries a regression test; the safe-commit cluster repros (#1334/#1777/#1784/#1631/#1820/#1330) pass; the `test_safe_commit_import_boundary` ratchet is **tightened** once callers are converted (#1355). | Draft |
| NFR-005 | ATDD ordering. | The C-003 protection-preserved negative suite (direct-push-to-origin/main blocked; non-placement commits to protected refs refused; #1334 repro) is authored FIRST and stays green throughout the strangle. | Draft |

## Constraints

| ID | Constraint | Status |
|----|-----------|--------|
| C-001 | Branch = `fixups/code-engine-stabilization` (continue; accumulate with 01KTPKST; PR held until stability proven). | Active |
| C-002 | No parallel mechanisms — consolidate the guard/status surfaces, do not fork new ones. | Active |
| C-003 | **Coherence ≠ removing protection** — the consolidated guard MUST still prevent direct pushes to origin/main and honor protected-branch intent (CLAUDE.md git workflow). | Active |
| C-004 | Honor the Terminology Canon (Mission not feature; no "ceremony"). | Active |

## Success Criteria
- **SC-1:** ONE commit-guard entry point consuming `CommitTarget` — all ~15 callers route through it; `rg`/review finds no parallel/contradictory guard and **no message-content privilege channel**; the 6 safe-commit-cluster repros (#1820/#1334/#1777/#1784/#1631/#1330) pass; the #1355 import-boundary ratchet is tightened; direct-push-to-origin/main still blocked.
- **SC-2:** `record-analysis` verdict reflects the **structured findings carrier** — a "no blocking findings" report → `ready`; a seeded CRITICAL row → `blocked`; prose wording does not change the verdict; a malformed/drifted carrier fails loudly.
- **SC-3:** `MissionStatus.load`/`status_transition` read the carried `StatusSurfaceFragment` — static check shows a single resolution path.
- **SC-4:** Doctrine health-render extracted from `doctor.py` (behavior-preserving) + `drg/merge.py` `_tag_source` typed incl. consumer migration; `mypy` clean.
- **SC-5:** Full suite + `ruff` + `mypy` + `tests/architectural/` green; no regression (NFR-001).
- **SC-6:** A fresh mission on a protected-target repo completes `specify → plan → tasks → finalize-tasks` with planning artifacts committed to their resolved destination — no catch-22, no manual branch gymnastics (#1777/#1784 e2e).

## Key Entities
- **`CommitTarget`** — the ADR 2026-06-03-2 value object (built by 01KTPKST) that becomes `safe_commit`'s single atomic decision input (Step 7); the guard's legitimacy source.
- **Commit-guard entry point** — the single consolidated safe-commit / protected-branch / destination-ref decision path (recommended home: Shared Kernel; enforce at the facade, not the rim).
- **Structured findings carrier** — the declared schema (frontmatter or validated table contract + canonical severity vocabulary) from which verdict + counts derive.
- **`StatusSurfaceFragment`** — the carried status-surface (from 01KTPKST's `MissionExecutionContext`) that `MissionStatus.load`/`status_transition` must consume.
- **Doctrine health-render module(s)** — pure extraction from `doctor.py`, beside `_doctrine_health.py`.
- **`Provenanced[T]` / declared provenance field** — the typed replacement for the `_tag_source` `object.__setattr__` sidecar in `doctrine/drg/merge.py` (shape decided in plan).

## Assumptions
- The 01KTPKST `MissionExecutionContext` + `StatusSurfaceFragment` are merged on `fixups/code-engine-stabilization` (this mission builds on them).
- The safe-commit cluster (#1334/#1777/#1784/#1631) shares the protected-branch/commit-path surface with #1796/#1820 (verified by intake scan) and is folded for coherence.
- Execution-context seams already drained by 01KTPKST are NOT in scope; #1738 (issue-matrix gate) is a separate surface, out of scope.

## Out of Scope
- Execution-context seams already fixed by 01KTPKST (#1737/#1735/#1814/#1816/#1764 etc.).
- #1738 issue-matrix completeness gate (different surface).
- Opening a PR — held until the operator judges tooling stability sufficient.
