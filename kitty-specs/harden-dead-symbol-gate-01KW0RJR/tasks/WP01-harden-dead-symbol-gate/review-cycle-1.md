---
affected_files: []
cycle_number: 1
mission_slug: harden-dead-symbol-gate-01KW0RJR
reproduction_command:
reviewed_at: '2026-06-26T07:13:47Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
review_artifact_override_at: "2026-06-26T08:18:27Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP01"
review_artifact_override_reason: "Cycle-2 review PASSED. Issue-matrix verdicts filled (#2158 fixed; #2049/#2159/#2048/#2152 deferred-with-followup per spec Out of Scope). Overrides stale cycle-1 rejection (bulk-allowlist of 67, now REMEDIATED -> 61 demoted + 6 deferred-public-API allowlisted, auth.transport FR-006) and stale subtask checkboxes (T001-T007 all verified complete). Evidence: ratchet FLAT 12/286 (frozensets shrank 10/275); 61 demotes SAFE (no import-*, all 29 modules import clean, no __all__ assertion broken, sync+readiness+migration 1918 passed); detectors LOAD-BEARING (spot-check re-flagged 11 symbols); gate 7/7; full architectural 500 passed (1 pre-existing marker-convention flake excluded); BANNED_FLAGS test passes; ruff+mypy clean."
---

# WP01 rejected — the 67-entry allowlist violates the mission's core promise (NFR-003)

**Good:** the parser fix, the 4 detectors (alias-map/module-attr, getattr-string, facade), the no-false-negative tests, the ~17 demotes, and the BANNED_FLAGS wiring are all correct — KEEP them.

**The problem:** you added `_CATEGORY_B_T001_UNBLINDED` with **67 symbols**. That GROWS the ratchet +67 — the exact strategy-B outcome this mission (strategy A) exists to avoid. NFR-003 allows growth of only the single deferred auth-trio entry. Per plan D-04, the residue the detectors don't rescue must be **DEMOTED** (dropped from `__all__`), not allowlisted.

## Required rework — split the 67

For EACH of the 67, default to **DEMOTE** (remove from its module's `__all__`, keep the def). Allowlist ONLY when the symbol is a GENUINE externally-consumed public-API contract, with a concrete external-consumer justification. Use `docs/engineering_notes/2158-dead-symbol-classification.md` (the squad's per-symbol evidence) — but note the squad leaned "allowlist"; the HiC decision overrides that toward DEMOTE-by-default.

**Why DEMOTE is safe here:** `__all__` only governs `from module import *`. Explicit `from module import X` (incl. all the test imports) keeps working after a demote. So a symbol used only intra-module or only from `tests/` does NOT need to be in `__all__` — drop it. Verify per-symbol that no `import *` reaches it (C-004).

### KEEP-IN-`__all__` + allowlist (genuine public API — the SHORT list):
- `auth.transport::{AuthenticatedClient, AsyncAuthenticatedClient, AuthRefreshFailed, get_client, get_async_client, reset_clients}` — public client/exception surface + the deferred SaaS-migration trio (FR-006). One justified allowlist entry/block referencing #2158/SaaS wave.
- Any OTHER symbol you can show has a real EXTERNAL consumer (a plugin, an org-pack, a cross-package import, a documented public contract) — allowlist with that evidence. Examples that MIGHT qualify if you find an external consumer: `workspace.context::WorkspaceResolutionError`, the `review._issue_matrix` vocab types (NFR-007), `migration.mission_state::RepairReport`. If you find NO external consumer → DEMOTE them too.

### DEMOTE (drop from `__all__`) — everything else, e.g.:
- `compat.messages::MESSAGES`, `compat.safety::SAFETY_REGISTRY`, `core.upgrade_notifier::{OPT_OUT_ENV_VAR,TTL_SUCCESS_SECONDS,TTL_UNKNOWN_SECONDS}`, `intake.provenance::MAX_PROVENANCE_BYTES`, `missions._substantive::Kind`, `orchestrator_api.envelope::BANNED_FLAGS` (used only inside `parse_and_validate_policy` — demote it; the wiring stays), `status.preflight::filter_dossier_snapshots`, `dashboard.scanner::{gather_feature_paths,read_file_resilient}`, `sync.owner::{MISMATCH_FIELDS,canonical_executable_scope}` (intra-module), `legacy_detector::get_legacy_lane_counts`, the `migration.mission_state` internal types, the `runtime.next._internal_runtime.significance` schema symbols (if intra-module/test-only), `charter._doctrine_paths::_PROJECT_ROOT_CANDIDATES`, the `readiness.upgrade_ux` test-only constants/types, etc.

## Target outcome
- The new allowlist category drops from **67 → ~6-12** (only genuine public API + the deferred auth trio).
- `category_a`/`category_b` net counts ≤ base + that small genuine-public set (NOT +67).
- Gate green; no-false-negative test still passes; full architectural + contract suites green.

If a symbol is genuinely ambiguous (could be public, could be internal) and you can't find an external consumer, DEMOTE it — it can always be re-promoted to `__all__` when a real cross-module need appears.
