# Research: FSM Write-Path Integrity

**Mission**: `fsm-write-path-integrity-01M1TZV6` · **Date**: 2026-09-06 · **HEAD verified**: PR #3904 branch tip `27a40ee90` (dossier anchors re-checked; all still hold except where noted in §3)
**Inputs**: `spec.md`, `research/28-missionA-research-dossier.md` (binding ground truth), the ten planning decision records in `decisions/`, and a fresh AST census of the tree (§1.1).

This file consolidates the plan-phase decisions in the required *Decision / Rationale / Alternatives* shape, records the evidence the planning debate produced, flags dossier drift, and carries the risk register forward.

---

## 1. Q4 — the named orchestrator (RESOLVED, decision `01M1V80R6F6RTMR7Y3C2WBKR32`)

### 1.1 Evidence: who writes status today (AST scan of `src/`, production only)

| Door | Production call sites | Module |
|---|---|---|
| `MissionStatus.transition` (aggregate) | **1** — `cli/commands/agent/status.py:411` | `status/aggregate.py` |
| `emit_status_transition_transactional` | **8 direct** (`merge/done_bookkeeping.py:268,:421`, `orchestrator_api/commands.py:1742`, `lanes/recovery.py:803`, `status/bootstrap.py:166`, `status/work_package_lifecycle.py:230,:295`, `cli/commands/implement.py:1459`) + 2 from the aggregate | `coordination/status_transition.py:1318` |
| `emit_status_transition_batch_transactional` | 2 (`work_package_lifecycle.py:159,:198`) | coordination `:1574` |
| plain `emit_status_transition` | **0** outside the coordination fallback arms (`status_transition.py:392,:404`); 41 test importers | `status/emit.py:508` |
| plain `emit_status_transition_batch` | 0 outside fallback arms (`:450,:458`) | `emit.py:808` |
| `emit_inner_state_changed` / `_transactional` | 6 + 2 | mixed |

Reading: the ADR-named "authoritative write entry point" (`MissionStatus`) is paper authority; the de-facto orchestrator is the transactional door in `coordination`. The plain door is effectively the fallback-arm target plus the test surface.

### 1.2 Options evaluated (six, not two)

| # | Option | Verdict | Decisive reason |
|---|---|---|---|
| 1 | `MissionStatus` aggregate named orchestrator, composed over the pipeline | rejected for this mission | Real authority requires migrating 8 callers (not in WP02's 4–5 days) AND blessing the aggregate's lazy `coordination` import (`aggregate.py:623`) — the very precedent-violation C-006 cites. `MissionStatus.load` is slug-keyed + topology-resolving; routing flat callers through it is the C-008 semantics change by another door. |
| 2 | **Status-owned pure pipeline is the named validation/build authority; aggregate is one caller; exactly two shells** | **ACCEPTED (with rider)** | Names what D5 actually builds; lands in `status/` (layering correct, no new reach); pure + I/O-parameterized so WP04's verdict is a parameter; zero caller migration; the future #2173 StatusWriter seam. |
| 3 | Transactional door in `coordination` named orchestrator (status quo made explicit) | rejected | Front door would be the facade's own exempt plumbing; converging the plain door onto it is option 5 by another name. |
| 4 | Build the #2173 StatusWriter port now | rejected (non-goal 1) | Wrapping an interface around three divergent implementations before unifying them. |
| 5 | Shim-over-coordination (plain door delegates to transactional door) | rejected (dossier D5) | Inverts C-006; flat/LANES missions silently gain git subprocesses + commits (C-008). |
| 6 | Shared kernel only, name nothing | rejected | Fixes validation divergence but not the shell-level P1 defects (phantom fan-out, lockless batch); violates the charter's single-canonical-authority principle. |

**Decision**: Option 2. **Rider**: `MissionStatus` remains the *intended* domain facade for callers but is not the write chokepoint until a later caller-migration mission; recorded as an amendment note to the #1667 / C-004 ADR chain in the WP02 design note (directive 003). The two senses of "authoritative" (domain facade vs validation/build authority) are named explicitly to avoid a `primary`/`merge`-style footgun.

**Consequence for the design**: "one orchestrator" = one pure pipeline + two shells with explicit per-shell failure policies (C-007). Lock acquisition, commit ordering, and fan-out timing are shell responsibilities by design; the phantom fan-out fix (FR-008) is a shell fix. WP03's gates must also constrain shell proliferation (see `contracts/write-gates.md` §3).

---

## 2. Remaining planning decisions (all recorded in `decisions/`)

| Q | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| Q10 (`01M1V8HS2Q…`) | WP05 stays in Mission A, A-first; **rider: WP05 declares no dependency on WP01–04 and is sequenced/merged first** to free the four shared runtime files for Mission B early | Both specs already pin A-first; B's touches on those files are ADR-gated and may never execute; WP05's edits are ~6 lines + one call swap + one rekey | Move to B (holds a real P3 defect hostage to an unrelated ADR; breaks A's SC-006); shared single-owner lane (tooling does not model it; overhead > payload) |
| Q8 (`01M1V8HVDQ…`) | Guard is **fail-OPEN on `None`** | Two live probe sites (`lanes/recovery.py:78`, `agent/tasks_transition_core.py:337`) build their own `GuardContext`; fail-closed kills both silently. Sound because post-WP03 no durable write bypasses the shells, which supply the verdict (FR-013). Do NOT copy `subtasks_complete`'s `is not True` polarity (`wp_state.py:370`). | Fail-closed + update both probe sites (adds two more verdict suppliers outside the shells; re-opens the "who resolves readiness" question at non-chokepoint sites) |
| Q1 (`01M1V8HXAV…`) | Batch-door lock lands in **WP02** | Keeps `status/emit.py` single-owner; the batch shell composition is where the lock belongs | WP01 (adds `emit.py` to a shared file; two changes instead of one) |
| Q2 (`01M1V8HZ5D…`) | Finite **default** L1 timeout is a **follow-up on #3893** (R9); FR-003(a)/(b) finite timeouts are in scope | Default-timeout semantics touch every L1 taker in the tree — a blast radius WP01 should not carry | In scope for WP01 |
| Q3 (`01M1V8J0Z1…`) | Harden **both** retrospective writers; `lifecycle_events.py` (live post-merge path) first; `events.py` keeps its "do not add new callers" note | A superseded-but-present raw `open("a")` is still an unlocked writer for the gate's census | Deprecation note only for `events.py` (leaves an unlocked writer the gate must then allowlist) |
| Q5 (`01M1V8J2RR…`) | Batch shell gains single-shell **parity** (owned-mission `ActionContextError` + `effective_root`) | Verified at HEAD: single `:1342-1345`/`:1362-1369`, batch `:1605-1614` has none; no evidence of intent | Adjudicate as intentional (no evidence found) |
| Q7 (`01M1V8J4KE…`) | **Preserve** emit cost; call-count assertion for `_derive_from_lane` (≤1 per emit, one full read) | Snapshot-anchored read is compaction-adjacent (non-goal 3) | Allow snapshot-anchored read in WP02 |
| Q6 (`01M1V8J667…`) | **DEFERRED** to WP02 implementer | Implementation detail; hard constraint carried: frontmatter `lane` mirror stays the only `write_frontmatter` of `lane` (`test_2093_authority_invariant.py`) | — |
| Q9 (`01M1V8J842…`) | **DEFERRED** to WP05 implementer/operator | Precedent for the legacy key is `f"legacy-{mission_slug}"` (`status_transition.py:1360/:1543/:1606`, all three transactional doors); shape (in-place vs one-shot) is an implementation choice | — |

---

## 3. Dossier drift found during planning (flag, do not silently fix)

- **D-1 — C-008's "four plain-door callers" are not callers.** `contracts/anchoring.py:277`, `dossier/rebaseline.py:104`, `runtime/next/runtime_bridge_composition.py:126` mention `emit_status_transition` in docstrings/comments only. `migration/verdict_provenance_backfill.py:419` calls the raw store primitive `append_events_atomic_verified` — which WP01's census already counts as unlocked writer ⑥. Production plain-door callers outside the coordination fallback arms: **zero**. **Disposition**: the no-new-commits pin (SC-007) is retained, because `_fallback_emit_single._primary` (`status_transition.py:392`) really does route flat/`LANES` missions through the plain door with uncommitted semantics. The plan cites the fallback arm as the rationale, not the four files. Spec FR text is left as-is (spec is committed; this is a plan-level correction to be folded at the next spec touch).
- **D-2 — `legacy-<slug>` precedent line.** The spec cites `:1606`; at HEAD the same expression appears in all three transactional doors (`:1360` single, `:1543` inner-state, `:1606` batch). All three are the precedent. No behavioural impact.
- **D-3 — #3460 pin tests enumerated (spec US2-5 obligation)**: `tests/specify_cli/coordination/test_status_transition.py::test_inner_state_annotation_degrades_when_coordination_branch_missing` (the degrade pin), `::test_transactional_emit_fails_closed_when_coordination_branch_missing` (the #1848 fail-closed sibling), and `tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py::test_runtime_state_persistence_error_propagates` (move-task persistence behaviour referenced under #3460). All three must stay green through WP02.

---

## 4. Domain rules, invariants, lifecycle (Phase 0 targets — resolved)

| Unknown | Resolution |
|---|---|
| Atomicity boundary of an emit | One lock acquisition covers: from-lane derivation → pipeline → append → materialize (flat shell) or → txn append → commit (transactional shell). Fan-out is *outside* the lock in both shells and *after commit* in the transactional/coord arms. |
| Lock hierarchy (no inverse edges) | L5 merge-global → L1; L3 verdict-save queue → L1 (bounded, `_in_queue_status_lock_timeout`); L1 re-entrant (3 deep); L1 → L4 workspace `threading.Lock` → git only via `BookkeepingTransaction`. New L1 takers in WP01 sit under no enclosing lock. |
| Lock key | `feature_dir.name` via `resolve_status_lock_root(feature_dir, repo_root)` (`workspace/root_resolver.py:36`); today `locking.py:57-60` keys on `mission_slug`. |
| Guard semantics | `dependency_ready: bool | None` on `GuardContext`; checked only on `planned→claimed` and `claimed→in_progress`; `None` ⇒ pass; `False` ⇒ refuse unless `force` with actor+reason; `True` ⇒ pass. Readiness = `dependency_readiness_for_wp(...).satisfied` (approved OR done OR canceled-with-provenance). |
| Replay purity | `reducer.py` keeps zero `validate_transition`/`GuardContext` references; `validate.py:validate_transition_legality` edge-only. |
| Run-state identity | Index key = `mission_id` (26-char ULID); slug stored as display field; legacy key per Q9. Missing `state.json` with live entry ⇒ `RunStateMissing` structured error (name TBD in WP05). |
| Externally visible events | SaaS/zeitgeist fan-out via the existing `status/adapters.py` registry (unchanged, non-goal 5); only *timing* changes (post-commit in coord arms). |

---

## 5. Integration points

- `BookkeepingTransaction` (`coordination/transaction.py`) — unchanged internals (non-goal 4); the transactional shell composes it as today.
- `status/adapters.py` fan-out registry — unchanged; called later.
- `core/dependency_graph.dependency_readiness_for_wp` — reused verbatim.
- `workspace/root_resolver.resolve_status_lock_root` — becomes the single lock-key derivation.
- `tests/architectural/test_status_module_boundary.py` — must stay green; the new pipeline module must not import `coordination`.
- `tests/architectural/test_layer_rules.py` runtime ledger — WP05 stays within ledgered subpackages; any removed lazy reach ⇒ same-PR ledger edit.
- PR #3888 / Mission B / Mission C / PR #3885 — interference map in `spec.md`; unchanged by planning except the Q10 rider (WP05 merges first).

---

## 6. Risk register (carried from spec R1–R12; plan additions R13–R15)

| # | Risk | Mitigation home |
|---|---|---|
| R1–R12 | as in `spec.md` §Risk Register | unchanged |
| R13 | `os.replace` atomicity on Windows CI (`ci-windows.yml`) for `_write_snapshot`/journal | WP05 copies the `reducer.materialize` tmp+replace shape already exercised on Windows CI; add the crash-window test with a `tmp_path` fixture only |
| R14 | Shell proliferation after WP02 (a third "shell" appears, re-creating divergence) | WP03 allowlist covers `feature_status_lock` + raw append composition sites; gate non-vacuity floor (see `contracts/write-gates.md` §3) |
| R15 | The Q4 rider is misread as "MissionStatus is deprecated" | WP02 design note + ADR amendment name both senses of "authoritative" explicitly |

---

## 7. Supply-chain security check (directive 051 / tactic `supply-chain-install-safety`)

**Dependency decision**: none. This mission adds, upgrades, and removes **no** packages in any ecosystem. `pyproject.toml` and `uv.lock` are untouched. Registry authenticity, package freshness, lifecycle-script discipline, and Node LTS awareness are therefore **not applicable**; this is recorded as "no dependency change", not as silence.

**Adversarial evidence**: no security-impacting dependency decision was made, so no adversarial-squad challenge pass is required for supply-chain. The post-plan adversarial squad (charter standing order: adversarial squad cadence) is **deferred_with_rationale** to the operator's post-plan point-cut: the spec already carries the post-spec squad's findings (commit `27a40ee90`), and the plan introduces no new mechanism beyond the Q4 selection, which was itself argued adversarially in §1.2 with all six options dispositioned (5 rejected, 1 accepted). Contested findings from that debate: none dropped.

---

## 8. Recommendations (for `/spec-kitty.tasks`)

1. Keep the five-WP slicing from `spec.md`; add the Q10 rider (WP05 first, no deps).
2. WP02's design note must contain: the Q4 amendment paragraph, the pipeline module name, the Q6 landing choice, and the enumerated #3460/#1848 pins (§3 D-3).
3. WP03's two gates must each ship with a non-vacuity floor test and a "synthetic writer reds the gate" test in the same PR.
4. WP04 must include the force + chain-order matrix and both probe-site `None` pins.
5. Every WP records `make test-fast` + blast radius commands and counts in its PR body (NFR-005).
