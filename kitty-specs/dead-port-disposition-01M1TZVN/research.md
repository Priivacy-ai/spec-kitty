# Research: Dead-Port Disposition

**Mission**: `dead-port-disposition-01M1TZVN` · **Date**: 2026-09-06 · **HEAD verified**: branch `missions/coreloop-proto-missions` after merging `origin/main` (`ba58652f0`, includes PR #3888)
**Inputs**: `spec.md`, `research/29-missionB-research-dossier.md` (binding), nine decision records in `decisions/`, live `gh` checks of PRs #3888/#3898/#3899.

## 1. Gate-state verification (the three external gates)

| Gate | State at plan time | Consequence |
|---|---|---|
| PR #3888 (touches `test_layer_rules.py`) | **Merged** into `main` (`c0054153b`); present in this branch since `ba58652f0` | FR-013 (`constitution` exclusion at `test_layer_rules.py:65-73`, verified present) is unblocked; C-002 satisfied by construction. |
| PR #3898 (RuntimeEventEmitter disposition ADR, `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md`) | **Open**, ADR `status: Proposed` | FR-012 is NOT executable; WP03 ships the **shrunk** variant (decision OD7). Re-check at tasks-finalize. |
| PR #3899 (quick-wins, draft) | **Open**; files: CODEOWNERS, CONTRIBUTING, Makefile, testing-parallel.md, pyproject.toml, pytest.ini, six `scripts/**`, one `tests/ci/**`, uv.lock | Carries none of the `src/mission_runtime` residue → OD8 default (ride this mission) holds. **Shared-file note**: #3899 edits `pyproject.toml` + `uv.lock` (`truststore`); this mission's WP01 edits the same two files (`transitions`). Whichever lands second rebases; keep one dependency change per PR (C-004). |
| Mission A (`fsm-write-path-integrity-01M1TZV6`) | In implementation on this branch (WP01/WP02/WP05 claimed) | C-001: B's WPs are claimed only after A merges into the branch. |

## 2. Decisions (Decision / Rationale / Alternatives)

| OD | Decision (id) | Rationale | Alternatives |
|---|---|---|---|
| OD1 | **FULL** (`01M1VAHEBB…`) | `guards.py`'s "shape precedent" is docstring prose in `review/gate_registry.py:7,132`, citable via git history; keeping ~680 test-only LOC for a citation is the rot shape this mission removes. FULL adds four gate edits (fold-gate `:60`, `_gate_coverage.py:1456`, the two schema-validation test halves) plus the `:3278` pin (drift D-1). | MIN (keeps guards/schema; leaves the pack-DSL validator alive with nothing to validate). |
| OD2 | **DEFERRED** — assume NO/retire (`01M1VAHFNE…`) | Operator-only; operator delegated completion. Spec, dossier, and reports 20/21/24/25/27 all frame retirement; no roadmap item references DSL v1. Override before WP01 claim. | YES → WP01 becomes re-justification; pin stays. |
| OD3 | Delete pack blocks; keep `MISSION_COMPAT_IGNORED_FIELDS` (`01M1VAHGZM…`) | Post-FULL the blocks have no interpreter; shipped templates must not imply one; `mission.py:59-67,260-261` tolerance stays for consumer overrides that still carry them. | Keep-with-comment (leaves inert YAML in every consumer's upgrade payload). |
| OD4 | `events.py` stays; docstring rewritten (`01M1VAHJ9R…`) | Relocation touches `next_invocation_lifecycle.py:332`, `decision.py:200`, the seam test, and the runtime ledger row `mission_v1` (`test_layer_rules.py:194`) — runtime files adjacent to Mission A. | Relocate under `status/` (candidate for Mission D). |
| OD5 | (a) canonicalize self-bootstrap; #1868 tracker note (`01M1VAHKNX…`) | (b) is a design change with no driver; report 27 recommends (a). Mission C unminted → tracker note owns the FR-020 follow-through. | (b) real registration seam. |
| OD6 | **DEFERRED** — assume ACCEPT documented-but-unwired (`01M1VAHN0C…`) | Operator-only; spec non-goal 3 already excludes wiring. No WP depends on it. | Mint the wiring feature issue. |
| OD7 | Shrunk variant; follow-up for execution (`01M1VAHPAR…`) | ADR not merged-and-Accepted (verified). | Wait for the ADR (blocks the whole P3/P4 slice on an external PR). |
| OD8 | Residue rides this mission (`01M1VAHQN3…`) | #3899 edits no gate file and none of the residue; one owner for `test_no_dead_symbols.py` (WP01), WP03 re-pins sequenced behind it. | Extend #3899 (two PRs on the same gate file). |
| OD9 | Mission B WP04 owns `decision.py` after A merges (`01M1VAHS32…`) | A's WP05 is claimed and deliberately small; the `mission_v1` ledger edge survives via `next_invocation_lifecycle.py:332`, so no ledger edit is triggered by the deletion. | Add a rider to A-WP05 mid-flight. |

## 3. Dossier/spec drift found during planning

- **D-1 — a fourth dead-symbol pin.** `tests/architectural/test_no_dead_symbols.py:3278` pins `specify_cli.mission_v1.schema::strip_v1_keys`. Under FULL, `schema.py` is deleted, so this pin must go in the same change as the three at `:720-727`. Folded into `contracts/dsl-retirement.md` §3. Spec C-005/SC-006 text left as-is (spec committed).
- **D-2 — eager block line numbers.** Spec says `:20-28`; at HEAD the eager imports are `:20-29` (compat `:20`, events `:21`, guards `:22`, runner `:23`, schema `:24-29`). Cosmetic.
- **D-3 — `evaluate_guards` consumers.** `tests/next/test_decision_unit.py:28,189-219` imports and tests `derive_mission_state`; the dossier says zero *callers* (true for `src/`); the test section is WP04's to delete.
- **D-4 — glossary_hook.py line drift.** The fiction sentence is at `glossary_hook.py:16-17` as stated; the self-bootstrap is at `:127-137` (verified `:130-135`). No impact.

## 4. Domain rules and invariants (Phase 0 targets — resolved)

| Unknown | Resolution |
|---|---|
| What must survive in `mission_v1` | `events.py` (`emit_event`, `read_events`) + a thin `__init__.py` re-exporting exactly those two; package docstring rewritten. |
| How to prove the hot-path fix | Subprocess-isolated test: `python -c "import sys, specify_cli.mission_v1.events; assert 'transitions' not in sys.modules and 'six' not in sys.modules"`; RED today, permanent after. |
| Dependency mechanics | Delete `pyproject.toml:82`; `uv lock`; verify `six` remains (via `python-dateutil`); CHANGELOG entry under `[Unreleased] - 3.2.7rc1` (no version bump: the rc cycle is already open; `__init__.py` version untouched). |
| Gate ledger (NFR-003) | Every deletion edits its gate in the same WP: dead-symbol pins ×4, `_gate_coverage.py:1456` (row stays if `tests/specify_cli/mission_v1/` keeps the trimmed events test + the new ratchet — it does), fold-gate `:60`, schema-validation halves, `test_pyproject_shape.py`, runtime ledger (no change expected). |
| Glossary contract | Self-bootstrap canonical; degradation only when `glossary.attachment` is unimportable; pinned by a behaviour test in `tests/doctrine/missions/test_glossary_hook.py`. |
| FR-020 honesty | `.. note::` in `glossary_hook.py` module docstring + tracker text for #1868 drafted in WP02's design note (operator posts). |
| Emitter slice | Record only: `research/emitter-adr-inputs.md` (name-collision map, 29-site `sync_emitter` map, flush-target defect at `runtime_bridge.py:2149-2150/:2187` vs `:1560-1565`, `spec_kitty_events` 9.1.6 `VOLATILE_EVENT_TYPES`, parity oracle `test_bridge_parity.py:1131-1152`); docstring correction at `event_emitter.py:1-10` pointing at `status/adapters.py:364-366`. |
| Residue | `constitution` exclusion (`test_layer_rules.py:65-73`); `team_projection/` (only `__init__.py`; bans at `test_no_retired_subsystems.py:39-40,99-100` + `pyproject.toml` TID251 assert absence — stay green; check wheel includes); `ActionContext` (two files); 13 `__all__` demotions (demote, never delete: `content_present_at_primary_tip`, `get_packs_root_default` have in-package callers). |

## 5. Integration points

- `runtime/next/next_invocation_lifecycle.py:332` (`emit_event`) — must keep working unchanged (FR-003); seam test `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py:49`.
- `runtime/next/decision.py:200` (`read_events`) — consumer deleted by WP04; until then unchanged.
- `tests/architectural/test_layer_rules.py:194` runtime ledger row `mission_v1` — stays (live edge preserved).
- `specify_cli/mission.py` `MISSION_COMPAT_IGNORED_FIELDS` — stays; comment updated.
- `charter/offering/missions/glossary_hook.py` ↔ `kernel/glossary_runner.py` ↔ `glossary/attachment.py` — the self-bootstrap triangle; no behaviour change.
- Mission A — none of B's owned files overlap A's; B waits for A's merge (C-001).

## 6. Supply-chain security check (directive 051)

**Dependency decision**: removal of `transitions` only; no additions or upgrades. Registry authenticity, freshness, and lifecycle-script discipline are not exercised by a removal; `uv lock` regeneration must be reviewed for an unchanged set of *other* pins (the only expected lock diff: the `transitions` entry and its `six` edge; `six` itself remains). Node LTS: N/A. **Adversarial evidence**: no security-impacting decision; deferred_with_rationale — the mission's adversarial pass is the operator's post-plan squad; nothing contested here.

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Deleting files without breaking the eager block (or vice versa) | Ratchet test (FR-004) + FULL deletion in one WP. |
| R2 | A gate goes red or vacuous after deletion | NFR-003 checklist in `contracts/dsl-retirement.md` §3; run the full `tests/architectural/` once in WP01 (pyproject touched). |
| R3 | `uv.lock` conflict with PR #3899 | Rebase whichever lands second; one dependency per PR. |
| R4 | Consumer projects' `mission.yaml` overrides still carry DSL blocks | `MISSION_COMPAT_IGNORED_FIELDS` retained (OD3). |
| R5 | Operator answers OD2 "yes" after WP01 lands | Override window stated in `plan.md`; WP01 not claimed until Mission A merges, leaving time. |
| R6 | `team_projection/` deletion breaks wheel build | Check `[tool.hatch.build.targets.wheel].packages` and `test_pyproject_shape.py` in WP03. |
| R7 | FR-020 note reads as a promise to wire | Note text explicitly says "documented-but-unwired; wiring is a separate feature decision" (OD6). |

## 8. Recommendations for `/spec-kitty.tasks`

1. Four WPs: WP01 DSL retirement (∥), WP02 glossary repair (∥), WP03 residue + emitter shrunk (after WP01), WP04 `decision.py` dead readers (∥). Mission-level gate: claim nothing until Mission A merges.
2. WP01 carries the CHANGELOG entry and the clean-install smoke; WP03 carries the FR-011 extraction and the follow-up mint text for the emitter execution.
3. Re-check PR #3898 at tasks-finalize; if merged-and-Accepted, extend WP03 per FR-012 (or mint WP05).
