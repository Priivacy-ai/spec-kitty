# Data Model — states & invariants

## #4017 — cold-start assessment/observation model
| Concept | Source | Meaning |
|---------|--------|---------|
| `AssetObservation.role` (NEW) | tagged at `observe()` (`asset_preparation.py:177-195`) | `source_read` (package input) vs `destination_probe` (HOME output) |
| recheck comparison set | `check_assets` (`:482-496`) | compares only `source_read` observations for "asset input changed"; `destination_probe` changes do not raise |
| loser re-assess | `ensure_runtime` cold path (`bootstrap.py`) | after flock, recompute effects vs warm home → `effects==[]` → warm return |
| operator signal | NEW, existing sink | human+machine: "runtime assets already materialized by a concurrent peer; nothing to do" |

### Invariants
- **INV-1 (FR-001)**: after the winner materializes HOME, the loser's re-assess under the lock yields `effects==[]` and it returns without applying (no `mkdir`/`open("x")` over existing bytes).
- **INV-2 (FR-003)**: a genuine `source_read` (package) change between assess and apply STILL raises/re-applies — role-tagging narrows destinations only, never sources.
- **INV-3 (FR-005/NFR-002)**: warm startup performs exactly one assess and takes no lock (the re-assess is cold-path-only).
- **INV-4 (C-002)**: `PreparedAssets.observations` retains all entries (role-tagged) — the fingerprint + cross-family agreement/membership invariants are unchanged.
- **INV-5 (FR-004)**: the fix is observed on the generic `check_assets`/`ensure_runtime` batch path for all owners (runtime + agent_commands + agent_skills + managed_skills), not runtime-only.
- **INV-6 (OPERATOR_SIGNAL)**: the converged-no-op / applied outcome is emitted on an existing operator-visible surface, and the red-first asserts on that signal.

## #4015 — test disposition model
| Disposition | Precondition | Evidence required |
|-------------|--------------|-------------------|
| `split` | mixed timing+functional | functional assert retained verbatim per-PR; timing → @performance nightly, budget preserved |
| `helper`/`rename` | vocab-blocked timing-only | guard-clean via assert_timing_budget or recognized-token rename |
| `delete` | persistently-flaky low-value pure-timing | flake-rate observation + AST zero-functional-assert + OPERATOR SIGN-OFF (HiC) |
### Invariant
- **INV-7 (NFR-003)**: per-PR functional-assertion count/text after ≥ before (diffable coverage-mapping table).
