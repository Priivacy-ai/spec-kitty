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

## Implementation phase

_(append as decisions are made/revised)_
