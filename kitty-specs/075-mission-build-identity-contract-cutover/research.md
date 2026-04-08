# Research: Mission & Build Identity Contract Cutover

**Mission**: 075-mission-build-identity-contract-cutover
**Date**: 2026-04-08
**Status**: Complete — all decisions resolved; no open unknowns

## Decision Log

### D1 — build.id storage location

**Decision**: `{git-dir}/spec-kitty-build-id`, resolved via `git rev-parse --git-dir`

**Rationale**: Immune to `git clean -fdx` (which CI pipelines run routinely and which silently wipes `.kittify/build_id.local`). Per-worktree by construction without `.gitignore` coordination. Git itself uses this directory for ephemeral state refs (`ORIG_HEAD`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`), establishing precedent. `spec-kitty` already shells out to git throughout the codebase.

**Failure mode addressed**: Option A (`.kittify/build_id.local`) silently regenerates `build_id` after `git clean`. A new `build_id` does not raise an error — it produces orphaned `started` events with no matching `complete` in the SaaS, breaking Phase 4 profile invocation correlation silently.

**CI environments**: `git rev-parse --git-dir` raises `CalledProcessError` when no `.git` exists (Docker with shallow clone, some CI setups). This is caught and re-raised as `BuildIdentityError: No git repository found. spec-kitty requires a git checkout.` No fallback.

**Alternatives rejected**: `.kittify/build_id.local` (wiped by git clean); `$TMPDIR/spec-kitty-<path-hash>` (lost on reboot).

---

### D2 — FR-015 provenance status

**Decision**: Already implemented. No content change to `upstream_contract.json` needed.

**Finding**: `upstream_contract.json` at `src/specify_cli/core/upstream_contract.json` already contains:
```json
{
  "_schema_version": "3.0.0",
  "_source_events_commit": "5b8e6dc",
  "_source_saas_commit": "3a0e4af",
  "_comment": "..."
}
```
The file is loaded via `importlib.resources` in `_load_contract()` in `contract_gate.py`. The remaining work is Scenario 4 test only: `_load_contract()["_schema_version"] == "3.0.0"`.

---

### D3 — FR-013 file enumeration (verified)

**Decision**: Exactly five files. Enumeration is complete and confirmed by grep.

**Verification**: `grep -r "feature_slug" src/specify_cli/ --include="*.py" -l` excluding `migration/`, `upgrade/`, `rebuild_state`, `history_parser`, `legacy_bridge` returns exactly:
1. `core/identity_aliases.py`
2. `core/worktree.py`
3. `status/models.py`
4. `status/validate.py`
5. `status/wp_metadata.py`

`upgrade/feature_meta.py` and `migration/rebuild_state.py` are the correct locations for legacy field reads and are explicitly out of scope.

---

### D4 — Legacy event fixture (Scenario 1 prerequisite)

**Decision**: New fixture file required. Write `tests/cross_branch/fixtures/legacy_feature_slug_event.jsonl`.

**Finding**: No existing `.jsonl` test fixture contains a `feature_slug`-only event (no `mission_slug`). Scenario 1 acceptance test requires at least one such fixture event. Writing it is the first task in WP01 (test-first).

**Fixture shape**:
```json
{"actor":"claude","at":"2025-01-01T00:00:00+00:00","event_id":"01HXXXXXXXXXXXXXXXXXXXXXXX","evidence":null,"execution_mode":"worktree","feature_slug":"034-legacy-feature","force":false,"from_lane":"planned","reason":null,"review_ref":null,"to_lane":"claimed","wp_id":"WP01"}
```
Note: `mission_slug` deliberately absent. `feature_slug` present. Post-WP01, this must raise `KeyError("mission_slug")` when passed to `StatusEvent.from_dict`.

---

### D5 — Tracker bind integration point

**Decision**: Extend `SaaSTrackerClient.bind_mission_origin()` to accept and send `build_id`. Load via `ProjectIdentity` at the already-resolved `repo_root`.

**Finding**: `bind_mission_origin` in `tracker/origin.py` calls `actual_client.bind_mission_origin(provider, project_slug, mission_slug=..., ...)` without `build_id`. The repo root is already resolved via `_resolve_repo_root(feature_dir)`. `ProjectIdentity` can be loaded from there.

**Dependency**: WP02 must be merged before WP03, because WP03's `build_id` must come from the per-worktree `.git/`-based source (not the legacy committed config).
