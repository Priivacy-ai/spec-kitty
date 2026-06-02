# Contract: Wave 3 — Charter Activation

## C3.1 Validate-before-write, non-mutating failure (FR-011, FR-012, NFR-003)

- **Given** `charter activate directive nonexistent-id`
  **When** run
  **Then** it exits non-zero, names the kind + missing ID + recovery path (`charter list --show-available` / `doctor doctrine`), and the bytes of `.kittify/config.yaml` are unchanged (compared before/after).
- **Given** the implementation
  **Then** `plan_activation(...)` is pure and raises on unknown ID **before** any mutation; `commit_plan(...)` performs the single `_save_config` write. No default-pack materialization is persisted on a failing plan.

## C3.2 No-cascade warning (FR-013)

- **Given** activating an artifact that references others, without `--cascade`
  **When** run
  **Then** the direct activation completes and a warning names the target, the skipped reference kinds, and the recovery command/consistency check.

## C3.3 Cascade scope preserved (FR-014)

- **Given** `charter activate mission-type research --cascade agent-profile,tactic`
  **When** run
  **Then** only referenced agent-profiles and tactics are activated; the scope string is **not** collapsed to a bool; `charter list` reflects exactly that scope. `--cascade all` is the explicit all-kind shorthand; absence of `--cascade` never means all.

## C3.4 Shared-reference-safe deactivation (FR-015, FR-016, C-005)

- **Given** `charter deactivate <kind> <id> --cascade <scope>` where a referenced artifact is also referenced by another active artifact
  **When** run
  **Then** exclusively-referenced artifacts are deactivated; the shared artifact is **skipped** and the still-referencing active artifact is named in the report. No shared artifact is silently removed.
- **Given** the implementation
  **Then** exclusivity is computed via `edges_to` reverse reachability over the merged DRG (a target is exclusive iff unreachable from all other still-activated sources after removal) — no per-kind special cases (FR-016).
