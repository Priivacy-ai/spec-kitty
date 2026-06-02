# Adversarial Review Debrief — `org-doctrine-profile-integrity-activation-closure-01KT1TV1`

**Date:** 2026-06-02
**Method:** 4 parallel read-only adversarial reviewers, each loading a doctrine agent profile via `/ad-hoc-profile-load` and proving every claim by execution (pytest, ruff, mypy, grep, live CLI).
**Reviewers / focus:**
- `reviewer-renata` — mission-objective adherence, claimed-changes verification, documentation consistency
- `architect-alphonso` — architecture, modularity, layering (charter↔doctrine boundary, R-009/C-009 cutover)
- `debugger-debbie` — functional correctness & runtime behavior (live CLI exercise, edge/failure paths)
- `python-pedro` — code & test quality (ATDD rigor, ruff/mypy, complexity, dead code)

## Overall assessment

Strong, well-wired work. **36/36 FRs functionally implemented and wired to live paths** (verified). Test quality is **exemplary** (real ATDD: byte-compare purity proofs, parametrized negative matrices, no tautologies, no over-mocking). Architecture is **structurally sound** (doctrine/charter layer purity intact; DRG field→fragment cutover complete on the read side; clean plan/commit + cascade value objects).

**Not cleanly approvable as-is:** one core-objective functional hole (I-1) and one mission-introduced CI-gate regression (I-2) block merge; the remainder is quality/debt/documentation cleanup. Three findings (I-1, I-6, I-9) share the mission's own anti-pattern — *"a thing reported done/healthy when it isn't"* — and should be treated as one trust-surface hardening pass.

---

## Findings (consolidated, deduplicated, severity-ranked)

### HIGH — fix before merge

**I-1 · `doctor doctrine` reports a pack HEALTHY when a profile carries a forbidden inline-ref field** (debbie F1; regresses the #1584 objective)
- Evidence: `InlineReferenceRejectedError` is a deliberately *propagating* contract (`src/doctrine/agent_profiles/repository.py:423-424`), but `_collect_profile_health`'s broad `except Exception` in `src/specify_cli/cli/commands/doctor.py` swallows it → empty report → `report.healthy = all([]) = True`, hiding **all** profiles (org + built-in). Reproduced live with an org profile carrying `tactic_refs`. This is the exact false-healthy class #1584 exists to close, reintroduced for the crash class.
- Test gap (structural root): every `tests/specify_cli/test_doctor_doctrine.py` case hand-builds `PackHealth`/`SkippedProfile`; none drive `_collect_profile_health` against a repository load that raises.
- Action: Decide skip-vs-propagate for inline-ref rejection. Either catch `InlineReferenceRejectedError` in `repository._load_layer` → `_record_skip` (consistent with `diagnostics.py` which lists it as a skip reason), or have `_collect_profile_health` translate it to `PackHealth(healthy=False)`. Add an integration test driving `doctor doctrine` against a `tactic_refs` org profile.

**I-2 · 5 new mission test files lack `pytestmark` → invisible to CI marker profiles** (renata H-1 + alphonso A-3; converged, independently confirmed)
- Evidence: `tests/charter/test_kind_vocabulary.py`, `tests/charter/test_operational_context.py`, `tests/doctrine/test_drg_merge.py`, `tests/doctrine/test_relationship_migration.py`, `tests/specify_cli/test_operational_context_wiring.py` — all new-in-mission, `grep -c pytestmark` = 0. `tests/architectural/test_pytest_marker_convention.py` fails naming them; under `-m fast`/`-m contract`/`-m architectural` the mission's flagship contract tests do not run.
- Action: Add `pytestmark = [pytest.mark.<category>]` to each (unit/contract for charter+doctrine; integration for the wiring test).

**I-3 · 4 strict-mypy errors in `src/doctrine/drg/merge.py`** (pedro H1 + alphonso A-4; converged)
- Evidence: `_tag_source(obj: BaseModel) -> BaseModel` (line 184) loses the concrete type; results feed `dict[str,DRGNode]`/`list[DRGEdge]` → `[misc]/[assignment]/[arg-type]` at lines 444-469. Mission-authored file (WP03 relocation; pattern inherited from main). CI mypy is advisory so technically non-gating, but `strict=true` is the declared bar.
- Action: Make generic — `def _tag_source[T: BaseModel](obj: T, source: str) -> T`. Zero runtime change; clears all 4.

### MEDIUM

**I-4 · Runtime→charter→doctrine boundary allowlist (0→2) is half-justified; charter facades already exist** (alphonso A-1/A-2 + pedro M1; converged)
- Evidence: `src/specify_cli/cli/commands/charter/activate.py:45` imports `ArtifactKind`/`MissionTypeNotAnArtifactKind` direct from doctrine though `charter.kind_vocabulary` re-exports both (the allowlist comment claiming "already routed via charter.kind_vocabulary" is factually false). `list_cmd.py:13-14` imports `CHARTER_KIND_TOKENS` + `ResolutionTier` direct, both facaded (`charter.kind_vocabulary`, `charter.resolution`). Only `template_catalog` (line 15) genuinely lacks a facade.
- Action: Route the 3 facaded imports through `charter.*`; add a one-line `charter.template_catalog` re-export facade. Both files then leave `_BASELINE_ALLOWLIST` → baseline back to 0 (supersedes the #1588 follow-up). Update `tests/architectural/_baselines.yaml`.

**I-5 · Stale "cascade not yet implemented" warnings printed while cascade actually runs** (debbie F2; FR-016/FR-020)
- Evidence: `charter activate … --cascade all` prints `Warning: …cascade… not yet implemented (deferred)…` immediately followed by `Cascade-activated: directive/010-…`. CLI owns cascade (`charter.cascade`) but still calls `manager.activate(cascade=scope is not None)`, triggering the obsolete deferral warning in `src/charter/pack_manager.py:419-428` (and worse for deactivate `:492-498`).
- Action: Pass `cascade=False` to `manager.activate/deactivate` (CLI owns cascade) or delete the stale warning blocks. Add a test asserting the "not yet implemented" string is absent from output.

**I-6 · FR-036 only partially done; 2 allowlisted `events::*` entries mask redundant re-exports** (renata M-1)
- Evidence: comment claims "six payload entries removed," but `SignificanceEvaluatedPayload`/`TimeoutExpiredPayload` remain allowlisted in `tests/architectural/test_no_dead_symbols.py`; they have live callers of the canonical defs in `specify_cli/next/_internal_runtime/significance.py`, while the allowlist points at the redundant `events.py` re-exports (no direct importer). `JsonlEventLog` is legitimately allowlistable.
- Action: Drop the two redundant re-exports from `events.py.__all__` (keep canonical in `significance.py`) and remove their allowlist entries; or scope the FR-036 claim precisely.

**I-7 · `acceptance-matrix.json` shipped as 36 untouched scaffold stubs** (renata M-2)
- Evidence: every FR-001..036 has `notes: "TODO: replace…"`, `pass_fail: "pending"`, `evidence/verified_by: null`, `overall_verdict: pending`. No committed FR→evidence traceability though the FRs are implemented + tested.
- Action: Populate with real per-FR criteria + the proving test IDs; set `overall_verdict` once filled.

**I-8 · `CLAUDE.md` not synced with the new subsystems** (renata M-3; DIRECTIVE_037)
- Evidence: `git diff merge-base..HEAD -- CLAUDE.md` empty; no mention of charter activation/cascade, `kind_vocabulary`, `OperationalContext`, `specializes_from`, template discovery. (Mitigant: `docs/explanation/doctrine-relationships.md` was added.)
- Action: Add a CLAUDE.md section for the activation/cascade model, canonical kind vocabulary, and `specializes_from` lineage (mirroring existing "Status Model"/"Mission Identity" sections).

### LOW

**I-9 · Doc drift, same root as I-1** (debbie F3): `src/doctrine/agent_profiles/diagnostics.py:6` calls inline-ref rejection a *skip reason*; `repository.py:423` says it *must propagate*. Resolve in lockstep with I-1.

**I-10 · `doctor.py` god-module growth** (alphonso A-5): +454 lines this mission; health-render helpers (lines ~1919-2062) could move beside `_doctrine_health.py`. Defer.

**I-11 · `provenance` monkey-patch** (pedro L1): `object.__setattr__(obj, "provenance", …)` sidecar on frozen Pydantic models (`merge.py:202`) is the upstream cause of I-3; a typed `Provenanced[T]` wrapper or declared optional field would be cleaner. Optional.

**I-12 · Pre-existing failures not tracked per DIRECTIVE_013** (renata L-1): the `ceremony` legacy term (`src/doctrine/missions/mission-steps/software-dev/tasks/guidelines.md:26`, present on main) + two `git_repo` marker gaps (`test_no_legacy_terminology.py`, `test_local_commit_wiring.py`) are pre-existing — file a tracker issue (like #1588) rather than silently inherit.

---

## Anti-findings (verified clean — do NOT "fix")
- Layer purity: `doctrine` never imports `charter`/`specify_cli`; `charter` never imports `specify_cli` (mission-introduced). C-006/C-008 honored.
- DRG cutover read-side: zero lingering `.specializes_from`/`.enhances`/`.overrides` field readers in `src/`.
- Retired-field rejection: explicit allowlist + actionable error naming the DRG-fragment migration path (exceeds spec).
- `deactivate.py` / `_doctrine_health.py` boundary routing: done correctly through `charter.*` facades.
- Test rigor: ATDD-satisfying; `test_activation_engine.py` proves purity by byte-compare; `test_relationship_fields_rejected.py` is a full negative matrix.

## Recommended action sequence
1. **I-1** (objective hole, needs new integration test) + **I-2** (CI visibility) — the two merge blockers.
2. **I-3, I-4, I-5** — small, mechanical, high-value (type gate, boundary hygiene, operator trust). I-4 retires the #1588 follow-up.
3. **I-6, I-7, I-8** — completion-proof / documentation accuracy.
4. **I-9–I-12** — cleanup/tracking; bundle I-9 with I-1.

## Reviewer evidence note
All findings above were reproduced by the reviewers with command + output and file:line citations; I-1 and I-2 were additionally re-confirmed by the orchestrator. No code was changed during the review.
