# Tracer: Design Decisions — verdict-seam-boundary-hardening-01KZG179

> Rationale that would otherwise evaporate. Append during implementation.

## Scope & fold adjudications (operator-confirmed)

- **Fold #3217 + #3216 in; #3243 out.** #3217 (census helper-construction blind spot) is a sibling of #3236 in the *same* file — closing #3236 without it leaves the census half-hardened, so they land together. #3216 (hand-rolled review-cycle reader dedup) is on the façade-consolidation theme and touches `review/artifacts.py`, which #3244 already opens. #3243 (numbering off-by-one) is a distinct behavior fix — left separate.
- **#3256: include the full stress lane here, not split.** Operator chose to own the CI-topology work in this mission rather than spin a separate CI-infra mission.
- **#3254 collateral: migrate all 4, no exemption ledger.** The widened guard also catches `emit`/`store`×2/`lane_reader` submodule-object imports; operator chose to fully close the boundary by migrating them rather than ledgering exemptions.

## Corrected scope (research squad vs. issue bodies)

- **verdict_vocab public surface is 10, not 8** — must also promote the `EventVerdict` type alias + `APPROVED`/`REJECTED`/`CHANGES_REQUESTED` constants, else `proof/events.py` (type), `tasks_move_task.py`/`verdict_provenance_backfill.py` (constants) cannot migrate.
- **8 submodule-object consumers, not 6** (added `tasks_move_task.py:150`, `verdict_provenance_backfill.py:76`). Two of the original six use only `is_changes_requested` (already on the façade) → migratable independently.

## Ordering & mechanism decisions

- **Export-before-dedup (C-002, hard).** `review_result_from_state` must be on `status.__all__` *before* `_event_sourced_gate_verdict`'s local decode is retired — the duplicate exists *only* because the symbol was unexported (its own docstring says so). Reversing the order reds the merge-blocking gate. The dedup adapts return type: `str(lookup.result.verdict) if lookup.result else None`.
- **Guard widening targets submodule *names*, not a bare `startswith` (C-003).** `from specify_cli.status import <name>` where `node.module == "specify_cli.status"` — a naive widening flags 100+ legitimate façade-symbol imports. Distinguish submodule names via filesystem `.py` check / explicit set. Non-vacuity teeth test required (NFR-002).
- **Arbiter fix adds `latest_cycle_number` (filename-only); does NOT touch `.latest`/`from_file` (C-004).** The arbiter caller needs only the cycle number, but a second caller (`workflow_executor.py:1134`) needs the full parsed body — so the parse contract stays intact and we add a narrow filename-only resolver instead. More correct too: `artifact_path` is built *from* the number, so a filename-derived number is authoritative.
- **Census function-level exclusion is a new mechanism.** None exists today; add one (e.g. `_EXCLUDED_FUNCTIONS`) rather than keep the coarse module-level exclusion that masks genuine readers.
- **`accept --json` advisory stays in the CLI layer (C-005).** Inject a uniform `advisories: list[str]` at the 4 emit sites; do not couple into the acceptance domain model.

## Re-baseline note (arch gates)

- Widening `test_status_module_boundary.py` and narrowing `test_verdict_seam_census.py` changes **no** golden-count/shard-map file (both already carry the `architectural` marker and are in `_arch_shard_map.py`; the `len==1` check is a synthetic-fixture teeth test, not a repo count) — NFR-005.

## Post-tasks squad (point-cut) — revisions

- **#3216 descoped and closed as already-resolved.** The post-tasks anti-laziness lens (verifying against code, not the issue body) found that #3216's target — the hand-rolled `_get_latest_review_cycle_verdict` reader in `tasks_parsing_validation.py` — was **already retired by the prior mission's WP05** (#3245, FR-003); comments at `tasks_parsing_validation.py:294-299` and `:1029-1030` document the deletion, and `latest_review_artifact_verdict` exists only as a retired-concept docstring. There is no live duplicate to dedup. Dropped WP04/T019 + spec FR-014; #3216 closed as already-resolved. **Lesson:** the pre-planning foldable-issue sweep grounded #3216 against the issue *body*; always verify a fold's premise against current code before committing scope. See [[feedback_live_evidence_over_static_fixed]].
- **WP prompt hardening from the squad:** WP02/T007 gained an objective cc-before/after gate + a focused test for the `_build_claim_review_override` extract (a skipped extract lands at ~cc14, under the 15 ceiling, so it would pass silently — the gate catches it). WP03/T013 gained a dedicated two-way non-vacuity teeth for the helper-construction predicate. WP06/T024 tightened to an in-ownership marker flip (the durability test is the sole test in its module; no re-home to `tests/stress/` which is out of ownership). WP05 gained an explicit "do not touch the ~8 error `json.dumps` sites" guard.
- **Ownership lens: clean.** The 12-site migration (8 verdict_vocab + 4 collateral) is exhaustive; the 39 rebased-in upstream commits introduced no new submodule-object site; no owned_files overlap; WP01→WP02 and WP02↔WP03 hazards proven safe.

## Implementation phase

- **Pre-merge squad earned its keep — 3 aggregate-only census-fixture staleness defects** that NO per-lane run could see (the full `tests/architectural/` suite isn't run per-lane; each lane's isolated fixture was internally consistent). All in the `[writer]` category of `verdict_seam_census.yaml`, all because lane-b mutated census-scope source while lane-c froze the expected-set against the base:
  1. **Growth:** WP02 extracted `_build_claim_review_override` (carries the `ReviewOverride` ctor) → new direct writer, no fixture row → add row.
  2. **Shrinkage:** WP02's FR-004 dedup made `_event_sourced_gate_verdict` delegate to `review_result_from_state` (no ctor) → no longer a writer → retire row.
  3. **Cascade shrinkage (squads missed this one; only the post-merge census run caught it):** `_mt_persist_wp_file` was a writer only via the ONE-HOP closure through `_mt_emit_runtime_state`. The extract demoted `_mt_emit_runtime_state` to a closure-writer, pushing `_mt_persist_wp_file` to TWO hops from the ctor, past the one-hop horizon → retire row. **Lesson for future extracts in census-scope code:** moving a record ctor into a new helper doesn't just add a row and keep the direct caller's row — it silently demotes every caller that was writer-*via-closure*-through the now-demoted function. Check the closure chain, not just the direct caller.
- Two independent pre-merge lenses (architecture-scout + aggregate-adjudicator) both caught #1 and #2; only running the actual census on the consolidated tree caught #3 — a reminder that a live gate run beats static reasoning for closure-sensitive invariants.
- **The `status/__init__.py` "double edit" (WP01 ∩ WP02) was a non-issue:** lane-b descends from lane-a (WP02 depends on WP01), so it's a clean stack (b ⊇ a), not a 3-way conflict. The merge subsumed lane-a.

## Implementation phase (append as decisions are made/revised)

