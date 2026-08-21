# Tracer — Approach (M3)

## Strategy
Predicate-over-set across five surfaces, one policy-reversal ADR. Consume already-landed
primitives (M0 backfill, M5 `canonical_mission_type_key`); do not rebuild readers or guard tables.

## Sequencing intent (to be firmed at plan)
1. **Re-ground first** (done): 3-pass code-truth → finalized spec + locked forks.
2. **ADR + red-first WP01**: the policy-reversal ADR (FR-016) names every red-by-design test; land the reversals as red-first.
3. **Surface slices** (candidate WP cut lines): (A) action gate #3596 + `_KNOWN_ACTIONS` fold; (B) governance-slot probe #3598; (C) artifact-name seam #3599/#3597 (largest — sub-slice); (D) CLI-guard family #3407.
4. Preserve NFR-003 byte-compat for the 4 built-ins except the 2 intentional reversals.

## Point-cuts
POST-SPEC squad (running) → plan → POST-PLAN squad → tasks → POST-TASKS squad → implement/review (impl→sonnet, review→opus) → closeout draft PR.

## (append during implement)
