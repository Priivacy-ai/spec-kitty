---
affected_files: []
cycle_number: 1
mission_slug: mission-identity-seam-and-1908-panel-01KV6510
reproduction_command:
reviewed_at: '2026-06-15T19:26:21Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP08
review_artifact_override_at: "2026-06-15T19:39:46Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP08"
review_artifact_override_reason: "Cycle-2 re-review PASS (reviewer-renata) over full 2-cycle diff. Cycle-1 rejection (3rd readiness writer + stopgap-coupled test) remediated in cycle 2: sync/routing.is_sync_enabled_for_checkout now routes through resolve_checkout_sync_routing_readonly. All 3 readiness write-paths closed under DEFAULT SaaS-enabled config: get_emitter read-only resolve_identity + seeds _identity/_git_resolver; resolve_identity genuinely read-only (no atomic_write_config); routing read-only twin. Headline test runs under autouse SPEC_KITTY_ENABLE_SAAS_SYNC=1 (no opt-out) asserting config.yaml byte+mtime unchanged. NO global persist=False flag. Write-authorized intact: ensure_identity untouched; enable/disable_checkout_sync still writing resolver; positive persist test green. Stopgap fully retired (git grep zero src refs); ACCEPT_OWNED_PATHS preserved. Idempotency test faithfully rewritten to post-stopgap contract. 10/10 owned tests pass; -k accept 203 passed. 6 test_acceptance_regressions.py failures confirmed PRE-EXISTING on base coord branch (file untouched). ruff clean; mypy errors identical to base. Anti-pattern checklist all PASS."
---

# WP08 review feedback — cycle 1 (scope completion, not a quality rejection)

Your cycle-0 work is SOUND and stays: read-only `resolve_identity` in `identity/project.py`,
emitter cache-seeding in `sync/events.py`, and the full stopgap retirement
(`_filter_accept_owned_project_config` + caller + `_expand_untracked_kittify` +
`_PROJECT_CONFIG_RELPATH` + comment) are all correct. Keep them.

The DoD ("accept readiness writes nothing to `.kittify/config.yaml`") is NOT yet met in the
**default (SaaS-sync-enabled)** configuration because the readiness write also fires through a THIRD
path you correctly stopped at the ownership boundary. WP08's owned_files has now been EXPANDED to
authorize the two files needed to finish:

## Remaining work (now in scope — owned_files updated)

1. **`src/specify_cli/sync/routing.py` — route the readiness check through the read-only twin.**
   `is_sync_enabled_for_checkout` (:94) calls the WRITING `resolve_checkout_sync_routing` (:96) →
   `ensure_identity` (:47) which persists `.kittify/config.yaml`. Change `is_sync_enabled_for_checkout`
   to call the EXISTING `resolve_checkout_sync_routing_readonly` (:51) instead — it only needs to know
   IF sync is enabled, not to mint identity.
   - **Do NOT touch** the genuinely write-authorized callers at :118/:125/:136/:157 (those are real
     sync operations, not the readiness path) — unless you verify a specific one is reached from accept
     readiness/diagnose; if so, document it. Keep the change surgical to the readiness path.

2. **`tests/specify_cli/acceptance/test_accept_idempotency.py` — remove/rewrite the stale test.**
   `test_accept_still_trips_on_non_owned_kittify_file` is coupled to the removed stopgap
   (`_expand_untracked_kittify` + the config.yaml exclusion). Either delete it or rewrite it to assert
   the NEW contract (a genuinely non-owned `.kittify/` file still trips the dirty gate, WITHOUT relying
   on the retired exclusion helper). Preserve the legitimate intent (non-owned dirt must still block).

## Acceptance for cycle 1
- With SaaS sync ENABLED (the default / autouse fixture), an `accept --no-commit` readiness run on an
  incomplete-identity project leaves `.kittify/config.yaml` byte-unchanged (extend/confirm your RED
  test to run under the default fixture, not only with SaaS disabled).
- The `-k accept` suite is green except the genuinely pre-existing baseline failures you already
  identified (the 6 in `test_acceptance_regressions.py` — name them in your handoff so the reviewer
  can confirm they predate this WP via `git stash`).
- ruff/mypy clean on changed lines (pre-existing baseline mypy noise is acceptable if you name it).
- Record in your commit message that `sync/routing.py` + the idempotency test are authorized
  out-of-original-map edits (rationale: the full #1916 readiness write surface).
