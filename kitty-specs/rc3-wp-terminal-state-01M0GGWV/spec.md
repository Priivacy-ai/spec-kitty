# Mission Specification: WP terminal-state model — an honest lifecycle for a completed-but-diffless WP

**Mission Branch**: `[NNN-wp-terminal-state-model]`
**Created**: 2026-08-20
**Status**: Draft (LIGHT spec — specify-phase only; NOT finalized)
**Input**: Mission M6, deep slice of epic #3550. Author: analyst-annie.
**Scope note**: One of eight specs feeding a single-branch PR before rc2. This is the DEEP structural fix the #3590 interim (Mission M4) explicitly defers. Scope EXPANDED by operator decision (2026-08-20) to cover BOTH #3590 directions plus the #3433 reconciliation.
**Hard dependency**: **Mission M7 (ExecutionMode consolidation, #3416) MUST land before this mission.** D1's new completion-mode value lands on M7's cleaned/renamed enum — do not mint it on the pre-consolidation type.

---

## Problem & Impact (BLUF)

Spec Kitty's WP lifecycle has **no honest way to complete a work package that legitimately produces no diff**, and its two terminal-completion consumers (`accept` and `merge`) disagree about what "complete" means. Three structural properties compose into a trap (#3590):

1. **Lane progression and review gates are diff-defined.** `for_review` requires an implementation commit on the lane worktree beyond base (`lanes/for_review_gate.py`); a WP whose deliverable is an *action, observation, artifact, or verdict* has nothing to commit, so the only advance is `--force` or checking subtasks describing post-integration observations (a false claim pre-merge).
2. **`accept` refuses a canonically-terminal WP.** `_ACCEPTED_READY_LANES = frozenset({"approved","done"})` (duplicated at `acceptance/__init__.py:102` and `acceptance/gates_core.py:52`) excludes `canceled`, so a deliberately-canceled WP with recorded provenance blocks acceptance (#2945, P1). A **third** drifting constant `_TERMINAL_LANES = {"done","approved"}` at `audit/classifiers/wp_files.py:16` is misnamed — it too excludes the real terminal lane `canceled`.
3. **`merge` does not gate on the acceptance record.** Its dry-run plans all lanes with the mission unaccepted — the de-facto escape hatch out of the unreconcilable state, and the only reason such missions ship (#3590 root cause).

Downstream, lane computation never consults terminal-lane state, so a canceled WP still demands an ownership manifest it cannot satisfy — every one of five retire routes is refused (#3432, P0) — and the sole workaround (delete the prompt file) manufactures event-log ↔ `tasks/` drift that every diagnostic reports healthy (#3433, P2).

**Impact:** Missions reach a permanently non-terminal state (open worktrees tripping pre-upgrade gates, #3590), operators are forced to *falsely approve* removed work (#2945), a P0 blocks any supported retirement route (#3432), and orphaned WPs pass `status doctor` silently (#3433). The blast radius is the FSM ↔ accept ↔ merge spine — the highest-leverage correctness surface in the tool.

---

## In Scope (this mission — the deep fix)

**D1 — Non-diff completion contract.** A WP may declare that its completion is evidenced by something other than a diff — an **observation**, an **artifact**, or a **recorded verdict** — carried as a new completion-mode value on the (M7-consolidated) `ExecutionMode` enum. The `for_review`/review gate evaluates the declared evidence instead of demanding a commit beyond base. This removes the trap at source for action-shaped WPs (#3590 Direction 1).

**D2 — Honest accept-tolerated terminal state.** Centralize terminal-lane semantics into one authority imported by status, acceptance, and audit; retire the three drifting constants (`acceptance/__init__.py:102`, `acceptance/gates_core.py:52`, `audit/classifiers/wp_files.py:16`) onto canonical `status_lanes.TERMINAL_LANES`. `accept` counts a `canceled` WP as terminal **only when its status event carries a non-empty cancellation `reason`**, surfaces it separately (e.g. `canceled_wps`), and never requires a false approval or replacement (#2945). Lane computation excludes terminal-lane WPs so a canceled WP no longer demands an ownership manifest (#3432, P0).

**#3433 — Event-log ↔ `tasks/` reconciliation.** `status doctor` gains a reconciliation check comparing WPs in the reduced event-log snapshot against prompt files present in `tasks/`, reporting an orphan in either direction as a fault (today the counts silently disagree and doctor reports healthy).

**Supported retirement ordering.** Document and enforce the safe ordering: emit the terminal transition **before** any file removal, so the event log and filesystem never disagree.

## Out of Scope (stays in epic #3550 or sibling missions / tickets)

- **Closing the `merge`-doesn't-gate-accept asymmetry.** Documented here as **deliberate-for-now** ("accept validates, merge integrates"); the closure is filed as a **separate follow-on ticket** — do NOT remove the safety valve in this mission (operator decision).
- **`tasks`-time authoring warning** when acceptance criteria are only observable post-integration (#3590 interim — Mission M4; do not duplicate).
- **ExecutionMode enum consolidation itself** (#3416, Mission M7) — a hard *upstream* dependency, not this mission's work. D1 consumes M7's cleaned enum; it does not perform the consolidation.
- **Post-collapse acyclicity check** (#3431) — sibling #3550 slice.
- **Direct-on-target terminus** (`merge --skip-lanes`, `mission close` coord-branch orphan — #2745) — distinct terminus story; cross-reference only.

---

## Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Completion-mode declaration (D1) | As a mission author, I want a WP to declare its completion is an observation / artifact / verdict rather than a diff, via a completion-mode value on the consolidated `ExecutionMode`, so an action WP has a legitimate route to completion. | High | Open |
| FR-002 | Review gate evaluates declared evidence (D1) | As a reviewer, I want the `for_review`/review gate to evaluate the WP's declared completion evidence instead of requiring a commit beyond base when a non-diff completion-mode is set, so a diffless WP can advance honestly (no `--force`). | High | Open |
| FR-003 | Non-diff WP reaches `done` without false subtask checks (D1) | As an operator, I want a completed non-diff WP to reach a terminal lane without checking subtasks that describe post-integration observations, so completion is never a false claim. | High | Open |
| FR-004 | Single terminal-lane authority (D2) | As a maintainer, I want one canonical `TERMINAL_LANES` imported by status, acceptance, and audit so the consumers cannot disagree about what "terminal" means. | High | Open |
| FR-005 | Accept tolerates provenance-backed cancel (D2) | As an operator, I want `accept` to treat a `canceled` WP carrying a cancellation reason as terminal (not a blocker), so a documented replan does not force a false approval (#2945). | High | Open |
| FR-006 | Cancel without provenance is a structured blocker (D2) | As an operator, I want a `canceled` WP with no recorded reason reported as a structured acceptance blocker, so accidental cancels cannot slip through. | High | Open |
| FR-007 | Canceled WPs surfaced separately (D2) | As an operator, I want accept output (`--json`) to list terminal cancellations distinctly (e.g. `canceled_wps`), so the audit trail stays explicit. | Medium | Open |
| FR-008 | Lane computation skips terminal WPs (D2) | As a mission author, I want lane computation to exclude terminal-lane WPs so a canceled WP no longer demands an ownership manifest, closing the P0 retire-route refusal (#3432). | High | Open |
| FR-009 | Non-terminal lanes still block (D2) | As an operator, I want `planned`/`claimed`/`in_progress`/`for_review`/`in_review`/`blocked` to remain acceptance blockers with actionable diagnostics, so this change never green-washes live work. | High | Open |
| FR-010 | Event-log ↔ `tasks/` reconciliation (#3433) | As an operator, I want `status doctor` to report a WP present in the event log but absent from `tasks/` (and the inverse) as a fault, so orphans stop passing as healthy. | High | Open |
| FR-011 | Safe-ordering for retirement | As a mission author, I want a documented, supported ordering (emit terminal transition, THEN remove any file) so the event log and filesystem never disagree (pre-empts #3433 orphans). | Medium | Open |
| FR-012 | Deliberate merge/accept asymmetry documented | As a maintainer, I want the "accept validates, merge integrates" asymmetry documented as deliberate-for-now, with a linked follow-on ticket for its closure, so the de-facto escape hatch is a known, tracked decision rather than a silent gap. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No drifting duplicate | Zero module-local terminal-lane constants remain; a repo grep for a hardcoded `{"approved","done"}` / `{"done","approved"}` frozenset outside the canonical home returns nothing (arch guard). | Reliability | High | Open |
| NFR-002 | Behaviour preserved for diff WPs | Existing diff-based `for_review`/approved/done behaviour is preserved unchanged; non-diff evaluation is gated behind an explicit completion-mode declaration. | Reliability | High | Open |
| NFR-003 | Completion-mode lands on M7's enum | D1's new value is defined on the M7-consolidated `ExecutionMode`; no pre-consolidation or parallel enum is introduced (fails closed if M7 has not landed). | Maintainability | High | Open |
| NFR-004 | Typed & clean | `mypy` and `ruff` clean; each migrated/added site carries a focused regression. | Maintainability | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical source only | Terminal-lane semantics resolve through `status_lanes.TERMINAL_LANES`; completion-mode resolves through the consolidated `ExecutionMode`. No parallel types. | Technical | High | Open |
| C-002 | M7 is a hard upstream dependency | This mission MUST NOT start D1 implementation until M7 (#3416) has landed the consolidated/renamed `ExecutionMode`. | Technical | High | Open |
| C-003 | Do not close the merge gate here | `merge` must NOT be changed to gate on the acceptance record in this mission; the asymmetry is documented and its closure ticketed separately. | Technical | High | Open |
| C-004 | Provenance-gated cancel only | `canceled` counts terminal only with a non-empty `reason`; the field already exists on the status event (`status/models.py:345`). | Technical | High | Open |

### Key Entities

- **Completion mode** — a value on the consolidated `ExecutionMode` describing how a WP evidences completion: `diff` (default, today's behaviour), plus non-diff variants (observation / artifact / verdict). Determines which review-gate evaluation path runs.
- **Terminal lane** — the canonical `TERMINAL_LANES` set (`done`, `canceled`), the single authority all consumers import.
- **Cancellation provenance** — the non-empty `reason` on a `canceled` status event that makes the cancellation acceptance-terminal.

## Success Criteria

- **SC-001**: A WP declaring a non-diff completion mode with satisfied declared evidence advances through `for_review` → terminal without a commit beyond base and without `--force` (closes #3590 Direction 1).
- **SC-002**: A mission with `by_lane = {approved: N, canceled: M}`, every canceled WP carrying a reason, passes `accept` once all non-canceled WPs are approved/done (closes #2945).
- **SC-003**: `finalize-tasks` / lane computation succeeds on a mission containing a `canceled` WP without demanding an ownership manifest for it (closes #3432, P0).
- **SC-004**: A `canceled` WP with no reason produces a structured, actionable acceptance blocker naming the missing provenance.
- **SC-005**: `status doctor` reports a WP present in the event log but absent from `tasks/` (and the inverse) as a fault instead of healthy (closes #3433).
- **SC-006**: Exactly one terminal-lane constant exists in the tree; arch guard enforces it (retires the three drifting copies).

---

## Acceptance Criteria (Given/When/Then)

**D1 — non-diff completion contract**
1. **Given** a WP declaring completion-mode `observation` with its declared evidence recorded, **When** it is moved to `for_review`, **Then** the review gate passes on the evidence and no commit-beyond-base is required.
2. **Given** a WP declaring a non-diff completion-mode with evidence **absent**, **When** it is moved to `for_review`, **Then** the gate refuses with a structured reason naming the missing evidence (not the generic "commit the work" message).
3. **Given** a completed non-diff WP, **When** it reaches its terminal lane, **Then** no post-integration subtask needed to be checked to get there.
4. **Given** M7's consolidated `ExecutionMode` is **not** present, **When** the mission's D1 code loads, **Then** it fails closed (NFR-003) rather than defining a parallel enum.

**D2 — terminal state + accept**
5. **Given** a mission with all non-canceled WPs approved/done and every canceled WP carrying a `reason`, **When** `accept --json` runs, **Then** it passes and lists the cancellations under `canceled_wps`.
6. **Given** a `canceled` WP with an empty `reason`, **When** `accept` runs, **Then** it returns a structured blocker naming the missing provenance.
7. **Given** a WP in a non-terminal lane (`in_review`/`blocked`/…), **When** `accept` runs, **Then** it remains a blocker with an actionable diagnostic (no green-wash).
8. **Given** a mission containing a `canceled` WP, **When** `finalize-tasks` computes lanes, **Then** it succeeds without demanding an ownership manifest for the canceled WP.
9. **Given** the codebase after this mission, **When** an arch guard greps for a hardcoded terminal-lane frozenset outside the canonical home, **Then** it finds none.

**#3433 — reconciliation**
10. **Given** a WP present in the reduced event-log snapshot but with no prompt file in `tasks/`, **When** `status doctor` runs, **Then** it reports the orphan as a fault.
11. **Given** the inverse (a `tasks/` prompt file with no event-log presence), **When** `status doctor` runs, **Then** it likewise reports a fault.

---

## Key Design Decisions

- **Both directions, in this mission (operator decision).** D2 (terminal state) closes the P0 (#3432) and P1 (#2945); D1 (non-diff completion contract) removes the trap at source for action WPs (#3590). #3433 reconciliation is folded because #3432's only historical workaround manufactures exactly that orphan — they share the ordering root.
- **D1 rides M7's enum — hard sequence.** The completion-mode value is defined on the `ExecutionMode` that Mission M7 (#3416) consolidates/renames. M7 lands first (C-002, NFR-003); attempting D1 before M7 fails closed rather than minting a fifth drifting enum. This is the load-bearing coupling and the reason the two missions are ordered, not parallel.
- **Centralization is the D2 spine.** #2945's own suggested resolution ("centralize terminal-lane semantics in the lifecycle service used by both status and acceptance") drives FR-004…FR-009. Three drifting constants is the "one op across N sites → ONE authority" campsite; the misnamed `audit/classifiers/wp_files.py:16` copy is the clearest evidence of the drift.
- **Provenance is the cancel gate.** `canceled` is acceptance-terminal only with a non-empty `reason` (field already on the status event), preserving #2945's requirement that accidental cancels never silently satisfy readiness.
- **The merge/accept asymmetry is preserved, documented, and ticketed — not closed here.** Making `merge` gate the acceptance record in the same mission that loosens `accept` (to tolerate canceled + non-diff completions) would remove the only safety valve before the new terminal paths are proven. FR-012 documents it deliberate-for-now; C-003 forbids closing it here; a separate follow-on ticket owns the closure.

## Risks

- **Largest blast radius of the program: the FSM ↔ accept ↔ merge spine.** A wrong terminal-lane or completion-mode semantic green-washes live (non-terminal) work at the accept gate — the exact failure this program exists to prevent. Mitigation: FR-009 + regressions for every non-terminal lane; NFR-002 preserves diff-WP behaviour behind an explicit completion-mode gate; AC 2/6/7 pin the refusal paths.
- **D1 broadens the review contract.** Evidence-based review is a genuinely new gate path; a permissive evaluator could accept unbacked claims. Mitigation: AC 1–2 pin present/absent evidence; NFR-002 keeps the default diff path unchanged.
- **M7 slippage blocks D1.** If M7 does not land, D1 cannot proceed. Mitigation: NFR-003 fail-closed + C-002; D2 and #3433 remain deliverable independently of M7, so the mission degrades gracefully to the D2+#3433 subset if M7 slips (plan-time sequencing decision).
- **Lane-compute exclusion (FR-008) interacts with dependency gating.** A terminal WP that others depend on could deadlock/orphan a chain — specify terminal-dependency readiness behaviour at plan time.
- **Merge asymmetry left open (by decision)** keeps the escape hatch alive until the separate closure ticket lands. Mitigation: FR-012 makes it a tracked, documented decision, not a silent gap.
- **Silent-drift regression:** a future contributor re-hardcodes `{"approved","done"}`. Mitigation: NFR-001 arch guard.

## Issues

- **Epic:** #3550 (WP retirement lifecycle).
- **Closed/advanced here:** #3590 (no honest terminal state — BOTH directions), #2945 (accept rejects canceled, P1), #3432 (canceled WP can't satisfy lane computation, P0), #3433 (event-log ↔ `tasks/` orphan passes doctor, P2).
- **Hard upstream dependency:** #3416 / Mission M7 (ExecutionMode consolidation) — lands before this mission.
- **New follow-on to file:** closure of the `merge`-doesn't-gate-accept asymmetry (the de-facto escape hatch) — separate ticket, not this mission.
- **Cross-reference (distinct terminus story):** #2745 (direct-on-target terminus gaps, P1); sibling #3431 (cyclic lanes.json).

---

## Resolved specify-phase decisions (were OPEN QUESTIONS)

- **(a) Direction — RESOLVED: BOTH D1 and D2 in-mission**, plus #3433 reconciliation. (operator)
- **(b) merge/accept asymmetry — RESOLVED: DOCUMENT as deliberate-for-now** (FR-012, C-003); file closure as a SEPARATE ticket; do not remove the safety valve here. (operator)
- **(c) scope boundary — RESOLVED: expanded to the deep fix** — #3590 (both), #2945, #3432, #3433 in; #3431 and #2745 stay out. (operator)
- **(d) M7 dependency — RESOLVED: HARD dependency, M7 lands FIRST**; D1's completion-mode value lands on M7's cleaned/renamed `ExecutionMode` (C-002, NFR-003). (operator)

## Cross-mission coordination (rc3 integration check)

- **M7 → M6 (hard dependency).** M6's D1 non-diff completion-mode value lands on M7's cleaned/renamed `ExecutionMode` — M7 lands first; M7's guard test must permit M6's additive member.
- **Same-file coordination with M5.** M6 and M5 (#2901 fold) both edit `audit/classifiers/wp_files.py` — M6 the terminal-lane constant, M5 the failure-classification reader. Assign per-symbol ownership at plan time.
