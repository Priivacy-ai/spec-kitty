# Adversarial Review Findings — wp-lane-state-machine-fsm (01KTGZAZ)

> **Status: tracked for remediation (not yet applied).** Recorded so the findings —
> including the "minor" UX items, which are user-impactful — are not lost. Posted on
> PR #1775 as a comment; this file is the canonical in-repo record. Remediation of the
> MAJOR/MINOR items follows as subsequent commits on this branch.

## 🔎 Multi-profile adversarial review — PR #1775 (WP lane state-machine FSM)

Three independent adversarial reviewers were run, each loading a canonical agent profile first, on `mission/wp-lane-state-machine-fsm` rebased onto `upstream/main`:

- **reviewer-renata** — code-review correctness & quality lens
- **architect-alphonso** — design-integrity / single-source-of-truth lens
- **debugger-debbie** — edge-case / failure-mode lens

Findings are consolidated and de-duplicated below, ordered by consensus severity. The **(N/3)** tag is how many reviewers independently flagged the issue — convergence is a confidence signal. Severity reflects the consensus; where reviewers disagreed, the range is noted.

> These are **review findings for triage — not yet applied and not independently re-verified by the orchestrator**. The two reviewers that issued an overall verdict both said **REQUEST-CHANGES**. Nothing here is a merge-blocker assertion until the author triages it.

---

### MAJOR — single-source-of-truth regressions (the mission's core invariant)

**M1 · `validate.py::_edge_is_legal` keeps a parallel genesis edge table `_GENESIS_OUTBOUND` (3/3)**
`src/specify_cli/status/validate.py` (~L33, L47). The function routes the 9 canonical lanes through the FSM but short-circuits genesis against a hardcoded `frozenset({PLANNED, CANCELED})` instead of `wp_state_for(Lane.GENESIS).may_transition_to(...)`. This re-introduces exactly the dual-source drift the mission exists to eliminate (ADR Invariant I1 / FR-021): if `GenesisState.allowed_targets()` ever changes, this table silently diverges. Currently consistent, so not a live bug — but a structural regression.
*Severity range:* CRITICAL (alphonso) / MAJOR (renata) / MINOR (debbie).
*Fix:* delete `_GENESIS_OUTBOUND` + the genesis special-case; let `_edge_is_legal` resolve genesis through the FSM like every other lane.

**M2 · `InProgressState.guard_for` consults `ctx.force` → contract split + dead code (3/3)**
`src/specify_cli/status/wp_state.py` (~L319–322). `guard_for` is documented as force-free (force is handled by `check_transition._check_force`), but `InProgressState` short-circuits on `ctx.force`. Net effect: `can_transition_to(FOR_REVIEW, force=True)` returns `True` while `check_transition(FOR_REVIEW, force=True, no actor/reason)` returns `False` — an inconsistency, and a trap for future guard authors who copy this as the template. The branch is unreachable via the canonical path (dead code).
*Severity range:* MAJOR (alphonso, renata) / MINOR (debbie).
*Fix:* remove the `ctx.force` branch from `InProgressState.guard_for`; add a docstring stating guards must not consult force; pin the contract with a test.

**M3 · `implement.py` unconditionally drops canonical status files for non-coord missions (2/3)**
`src/specify_cli/cli/commands/implement.py` (~L449–456, `_ensure_planning_artifacts_committed_git`). The `_coord_owned_status` exclusion filter is applied to `status_paths` regardless of topology. On a **non-coordination** mission, dirty `status.events.jsonl` / `status.json` are silently excluded from `files_to_commit` — a behavioral regression vs. pre-PR (the sibling `_stage_finalize_artifacts_in_coord_worktree` in `mission.py` is correctly guarded on `coord_worktree.exists()`).
*Severity:* MAJOR (renata, debbie — independently confirmed).
*Fix:* gate the exclusion on `coord_branch_for_filter` being set; add a non-coord regression test asserting status files are committed when present.

**M4 · `aggregate.py` genesis read/write parity gap (alphonso CRITICAL; debbie MINOR on adjacent reader)**
`src/specify_cli/status/aggregate.py` (~L426–430, L492–503) hardcodes `Lane.PLANNED` as the `_resolve_current_lane` fallback, and the test `test_resolve_current_lane_maps_uninitialized_to_planned` still asserts the pre-FSM `planned` result. An unseeded WP routed through `MissionStatus.transition()` can become `planned`, bypassing the genesis rejection gate (FR-008/FR-009). Related reader defaults still return `Lane.PLANNED` for unseeded WPs: `lane_reader.py` (~L63/L83), `lifecycle.py` (~L198/L202), `views.py` (~L109), `progress.py` (~L165).
*Fix:* default these read paths to `Lane.GENESIS` (or skip non-display), and update the stale aggregate test to the new canonical behavior.

**M5 · `implement.py` genesis rejection raises bare `ValueError`, not `WorkPackageStartRejected` (2/3)**
`src/specify_cli/cli/commands/implement.py` (~L800–803) vs. `work_package_lifecycle.py` (~L113). FR-009 specifies `WorkPackageStartRejected` (a `TransitionError` subtype); the `implement` path uses `ValueError`, so programmatic callers catching the typed exception miss this path. No test covers `implement` invoked on an unseeded/genesis WP.
*Severity range:* MAJOR (renata) / MINOR (alphonso).
*Fix:* raise `WorkPackageStartRejected` at the implement site; add the negative test.

**M6 · `lifecycle_events._is_bootstrap_status_event` is stale vs. the new genesis seed (1/3, alphonso)**
`src/specify_cli/status/lifecycle_events.py` (~L707) still matches `force=True AND to_lane=="planned"`. The canonical bootstrap seed is now `genesis → planned` with `force=False`, so the new seed is invisible to the detector — `has_non_bootstrap_status_history()` (used by merge pre-flight) misclassifies seeded logs. Not covered by the `status/` suite; surfaces at merge time.
*Fix:* match `from_lane == "genesis"` as the bootstrap signal; add a targeted test.

**M7 · Duplicate "coord-owned status files" definition (1/3, alphonso)**
`mission.py` (~L95, `_COORD_OWNED_STATUS_FILES`) vs. `implement.py` (~L450, inline `_coord_owned_status` set literal). Two definitions of the same domain invariant will drift if a third status artifact is added — the same single-source principle the mission champions.
*Fix:* extract one shared constant (e.g. in `status/store.py` or `status/constants.py`) and import in both; have the finalize test import it too.

---

### MINOR

- **m1 · genesis WPs silently dropped from kanban / metrics (2/3 — renata, debbie).** `agent_utils/status.py` (~L223): `total = len(work_packages)` counts genesis WPs while lane buckets use `_display_wps` (genesis-excluded), so `total` exceeds summed columns (skews `done_pct`/progress). debbie rates the silent-drop a spec-contract concern (SC-002) but MINOR in normal flow (genesis WPs exist only pre-finalize). *Fix:* `total = len(_display_wps)`.
- **m2 · SaaS payload validator accepts `genesis` as `to_lane` (2/3 — renata, debbie).** `sync/emitter.py` (~L276): `to_lane` validator uses `_CANONICAL_LANE_VALUES` (includes genesis). `validate.py` already rejects `to_lane=genesis`; the SaaS gate should too once events 6.0.0 lands. *Fix:* a display-only lane set (`Lane` minus `GENESIS`) for the `to_lane` validator; keep genesis valid for `from_lane`.
- **m3 · discovery returns `no_planned_wps` instead of an actionable `not_finalized` for genesis-only missions (1/3 — debbie).** `runtime/next/discovery.py` `_claimable_selection_reason`. The `implement` command itself gives the correct "run finalize-tasks" message, so this is preview-only UX. *Fix:* add a `not_finalized`/`finalize_required` reason token when all candidates are genesis.
- **m4 · `validate_transition` can return `(False, None)` (1/3 — debbie).** `transitions.py` (~L85–86) returns `exc.reason`, which is `None` if a `guard_for` override returns `(False, None)` or `InvalidTransitionError` is raised reasonless — callers expecting a message could break. Ties to M2's guard contract. *Fix:* guarantee a non-None reason (fallback message) and/or enforce the guard contract.

---

### NITs (grouped)

- **FR-016 shared seed fixture residue (2/3 — alphonso, renata):** several test files still define local seed helpers / inline genesis-seed JSONL instead of the shared `seed_wp_to_planned` conftest fixture (`tests/agent/.../test_status_cli.py`, `tests/status/test_agent_status_emit_cli.py`, `tests/lanes/test_implementation_recovery.py`, `tests/specify_cli/coordination/test_status_transition.py`). Consolidate toward ≤2 shared fixtures (SC-006).
- **Docstrings/ADR (renata, alphonso):** `wp_state.py` module docstring references only the 2.x ADR — add the new `2026-06-07-1` ADR; `is_run_affecting` docstring omits `genesis`; the new ADR's "Non-goals: guard unification stays where it is" now contradicts the shipped guard migration (DM-01KTH03G) — add a revision note.
- **Stale comments (renata):** `tests/status/test_validate.py` (~L252) says "27-pair" model; it's now 29 (27 + 2 genesis edges).
- **Test seed hygiene (alphonso):** `test_status_transition.py` (~L119) seeds with `force=True`; canonical bootstrap dropped `force=True` — use `force=False`.
- **`emit.py` BLE001 (alphonso, ~L70–78):** the genesis-capability probe uses broad `except Exception  # noqa: BLE001`; narrow to `(ImportError, AttributeError)` and drop the suppression.
- **`@runtime_checkable` on `TransitionInputs` (alphonso, `wp_state.py` ~L27):** no runtime `isinstance` use — drop the decorator unless a caller needs it.
- **ULID length in fixture (renata):** `test_finalize_clobber_e2e.py` uses a 24-char `mission_id` (ULID is 26) — pad to avoid future validation breakage.

---

### Convergence summary

| Finding | renata | alphonso | debbie |
|---|---|---|---|
| M1 `_GENESIS_OUTBOUND` parallel gate | MAJOR | CRITICAL | MINOR |
| M2 `guard_for` force leak | MAJOR | MAJOR | MINOR |
| M3 non-coord status-file drop | MAJOR | — | MAJOR |
| M4 read/write genesis parity | — | CRITICAL/MAJOR | MINOR |
| M5 `ValueError` vs `WorkPackageStartRejected` | MAJOR | MINOR | — |
| m1 genesis kanban/total count | MINOR | (F3 adj.) | MINOR |
| m2 SaaS `to_lane` accepts genesis | MINOR | — | MINOR |

**Headline:** M1 and M2 are the two findings all three reviewers independently surfaced — both are "parallel-authority / contract-split" regressions, the precise anti-pattern this mission exists to remove. They're the highest-ROI fixes even though neither is a live bug today.

*Verdicts: renata REQUEST-CHANGES · alphonso REQUEST-CHANGES · debbie (stopped before final verdict; findings reconstructed from her trace).*

<sub>🤖 Generated with [Claude Code](https://claude.com/claude-code) — 3× Sonnet adversarial reviewers, profile-loaded.</sub>
