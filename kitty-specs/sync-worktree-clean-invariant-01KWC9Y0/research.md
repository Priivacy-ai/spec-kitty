# Phase 0 Research: Worktree-Clean Sync Invariant

All findings grounded in code-trace of `spec-kitty` + `spec-kitty-saas` at HEAD `4f457d6`.

## Decision 1 — Identity stability on non-writing read paths (NFR-001)

**Decision:** **Option C — deterministic `build_id`.** Keep `project_uuid` generation unchanged. When `build_id` is the missing field, derive it deterministically as `uuid5(NAMESPACE, f"{project_uuid}:{node_id}")` so `resolve_identity()` returns a stable identity with no `config.yaml` write. Migrate the 8 read-path `ensure_identity` call sites to `resolve_identity`; keep `ensure_identity` only at write-authorized boundaries (`init`, explicit bind/apply). Recorded as decision `DM-01KWCAQMZM…`.

**The problem this resolves.** The spec carried one open assumption: that identity completion is deterministic. It is **not**. `ProjectIdentity.with_defaults` (`identity/project.py:73-79`) fills missing fields as:

| Field | Generator (`project.py`) | Deterministic? |
|-------|--------------------------|----------------|
| `project_slug` | `derive_project_slug(repo_root)` — git remote / dir name | ✅ |
| `node_id` | `sha256(hostname:username)[:12]` (`:200-203`) | ✅ |
| `project_uuid` | `uuid4()` (`:118-124`) | ❌ random |
| `build_id` | `str(uuid4())` (`:127-133`) | ❌ random |

`ensure_identity` (`:299`) persists precisely to lock those random values. The read-only twin `resolve_identity` (`:336-359`) returns `with_defaults(...)` **in memory** — so for an incomplete identity it would mint a *fresh* random `project_uuid`/`build_id` on every call → drift. The realistic incomplete case is a **legacy `config.yaml` missing only `build_id`** (newest required field per FR-009 / events 4.0.0); `project_uuid`/`slug`/`node_id` are already persisted and stable. So drift is concentrated in `build_id`.

**Rationale (why C).** C eliminates the only drifting field for the realistic case with zero `project_uuid` semantic change, zero new user surface, and trivial reversibility. The SaaS research (Decision 2) confirms a deterministic `build_id` is constraint-safe and that `build_id` drift, while not catastrophic, produces real observability garbage — so stabilizing it has positive value beyond NFR-001.

**Alternatives considered:**
- **A — fully deterministic minting** (seed `project_uuid` from repo). Rejected: it changes what "a project" is — two clones of one repo would share a `project_uuid` and **merge into one SaaS project**. The SaaS side *endorses* this (it's the repo-sharing model), so A is not unsafe — but it is a deliberate *product* identity decision that must not ride in on a P1 bug fix. Larger blast radius, harder to reverse.
- **B — persist at write boundary only** (keep random; add a `doctor identity --backfill`). Rejected: it does not actually guarantee NFR-001 — a legacy checkout that emits *before* the user runs the backfill still drifts `build_id`. Adds a new command + user action while leaving a correctness window open.

## Decision 2 — SaaS-side safety of a deterministic `build_id` and of `build_id` drift

**Decision:** Confirmed server-safe; no SaaS changes required. (Research agent traced `spec-kitty-saas/apps/sync/`.)

**Findings (quoted evidence):**
- **Project keyed on `(team, project_uuid)`** — `models.py:82` `UniqueConstraint(["team","project_uuid"])`; lookup `materialize.py:354` `Project.objects.filter(team=team, project_uuid=project_uuid).first()`. Shared `project_uuid` across checkouts is **intended** (purpose-built `ProjectIdentityAlias`, `models.py:97`; repo-sharing reuses `project_uuid`, `sharing.py:117`).
- **Build keyed on `(team, project, build_id)`** — `models.py:1148`; no global uniqueness on `build_id`. Find-or-create is idempotent and race-guarded (`materialize.py:1797, 1870-1872`). A deterministic `build_id` therefore **cannot raise IntegrityError** and yields stable Build-row reuse.
- **Aggregate hierarchy:** `Project ← Mission(FK project, models.py:528) ← WorkPackage(FK mission, :694)`; **`Build` is a sibling side-branch** (`FK project, :1114`) carrying clone telemetry only. **Mission/WP never join on a Build** → `build_id` drift **cannot strand missions/WPs**.
- **Event dedup on `event_id` (PK)** — `ingestion.py:180,274` → `{"status":"duplicate"}`. Re-emitting the same `build_id` is absorbed.
- **Drift cost:** each distinct `build_id` mints a new Build row (garbage), inflates active-clone counts, and can trigger `_trigger_synthesized_baseline_if_needed` (`materialize.py:1743`). Not catastrophic, but stabilizing `build_id` keeps observability clean.

**Bottom line:** Option C is the cleanly server-safe pick. Option A is also server-safe but couples a project-identity/product change into the bug fix. Option B leaves a real drift window.

## Decision 3 — Reuse the existing read-only identity API

**Decision:** Use the already-shipped `resolve_identity()` (`identity/project.py:336`, landed under #1916) for read/emit paths; do not invent a new API.

**Rationale:** Its docstring states it is the side-effect-free counterpart "for … the sync emitter init" — exactly this use case. The bug is that the emitter never adopted it. Reusing it keeps the change minimal and honors DIRECTIVE_024 (locality).

**Call-site inventory** (`grep ensure_identity(`): **keep** `init.py:99,863` (write-authorized); **migrate** `emitter.py:100,115`, `sync/routing.py:47`, `sync/events.py:180`, `sync/__init__.py:253`, `sync/dossier_pipeline.py:233`, `tracker/origin.py:452`; confirm `cli/commands/tracker.py:680` remains a write-authorized `tracker bind` boundary. Each read-context site must be confirmed during implementation.

## Decision 4 — Tracker dirt source and fix shape

**Decision:** Convert `_maybe_upgrade_binding_ref` to report-only on read paths; persist only on explicit bind/apply.

**Rationale / evidence:** `_maybe_upgrade_binding_ref` (`tracker/saas_service.py:141`) calls `save_tracker_config` which writes **`.kittify/config.yaml`** (`tracker/config.py:156` — *"Persist tracker config into .kittify/config.yaml, preserving other sections"*) — the same file the identity write touches. It is reached from `status`/`sync_pull`/`sync_push`/`sync_run`/`map_list`. It is conditional (only when the server returns a changed `binding_ref`).

## Decision 5 — Enforcement mechanism and test prior art

**Decision:** One parametrized "no-dirty-tree" contract test over the command surface, modeled on existing clean-tree tests.

**Rationale:** `record-analysis`'s allowlist is intentionally tiny (`meta.json`, `.kittify/encoding-provenance/...`), so `config.yaml` is real dirt. C-001 forbids widening the allowlist; the correct enforcement is a test that fails on any porcelain change. Prior art to model on: `tests/specify_cli/cli/commands/test_accept_clean_tree.py`, `tests/mission_runtime/test_self_bookkeeping_allowlist.py`, `tests/specify_cli/cli/commands/test_accept_readiness_no_write.py`. Repo git helpers live in `core/vcs/git.py` / `core/git_preflight.py`.
