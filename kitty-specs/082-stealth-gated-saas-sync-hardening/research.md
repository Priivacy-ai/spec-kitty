# Phase 0 Research — 082 Stealth-Gated SaaS Sync Hardening

**Date**: 2026-04-11
**Status**: Complete — all six deferred decisions resolved.

This document records the discrete decisions needed to remove `[NEEDS CLARIFICATION]` items before Phase 1 design. Every decision is grounded in the **current** code shape (file:line citations) so the plan reflects reality, not assumption.

---

## R-001: Where the new shared package lives

**Decision**: Create a new top-level package `src/specify_cli/saas/` that owns rollout gating, readiness evaluation, and the background-daemon policy enum.

**Rationale**:
- Today, `is_saas_sync_enabled()` and `saas_sync_disabled_message()` are **duplicated** verbatim in `src/specify_cli/tracker/feature_flags.py:11-19` and `src/specify_cli/sync/feature_flags.py:11-19`. Picking either existing module as the canonical home would force the other to become a re-export, leaving the cross-module dependency visually arbitrary.
- A neutral `saas/` package makes it obvious that rollout + readiness are **shared concerns** owned by neither tracker nor sync. This matches the spec's "shared readiness abstraction" wording.
- Co-locating `rollout.py` and `readiness.py` in one package signals to future contributors that they belong to the same boundary.

**Alternatives considered**:
- *Hang it off `tracker/`*: rejected — tracker is a consumer of the gate, not the owner. Locating ownership inside a consumer creates an upward dependency.
- *Hang it off `sync/`*: rejected — same reason; `sync` is also a consumer.
- *Put it in `cli/`*: rejected — the readiness evaluator must be callable from non-CLI code paths (dashboard, daemon).

**Backwards compatibility**: Both existing `feature_flags.py` modules become **thin re-export shims** that import from `specify_cli.saas.rollout`. No call-site renaming is required in this mission. A future cleanup mission can collapse the shims when callers have migrated.

---

## R-002: Readiness state taxonomy

**Decision**: `ReadinessState` is a closed `Enum` with exactly six members:

| Member | Meaning | Triggered by |
|---|---|---|
| `ROLLOUT_DISABLED` | The env var is not set. The hosted surface is invisible to customers. | `is_saas_sync_enabled() == False` |
| `MISSING_AUTH` | No cached SaaS auth token / credentials are present. | Auth lookup returns nothing |
| `MISSING_HOST_CONFIG` | The SaaS host URL is missing or empty in `SyncConfig.server_url` (and any future `SPEC_KITTY_SAAS_URL` override). | Host string is absent |
| `HOST_UNREACHABLE` | The configured host did not answer a bounded probe within the timeout. | Probe failure (only checked when caller opts in) |
| `MISSING_MISSION_BINDING` | The current command requires a bound mission, but no binding exists for this repo. | Binding lookup returns nothing for the active feature slug |
| `READY` | All prerequisites the caller asked about are satisfied. | All checks pass |

**Rationale**:
- Six members map 1:1 to the spec's named edge cases (Edge Cases section of spec.md, lines 79-82) plus the spec's NFR-002 ("100% of readiness failures must name the missing prerequisite").
- A closed enum (vs free-form strings) gives mypy --strict full discrimination and lets each CLI command decide which states it considers fatal vs degraded.
- `ROLLOUT_DISABLED` is **first** in the evaluator's check order so the cheapest, most consequential gate runs before any I/O.

**Alternatives considered**:
- *Boolean ready/not-ready*: rejected — kills NFR-002.
- *Free-form `(bool, str)` tuple*: rejected — defeats mypy and spreads message-formatting logic across callers.
- *Subdividing `MISSING_AUTH` into `NO_TOKEN | EXPIRED_TOKEN`*: rejected for this mission — current auth lookup does not distinguish; this can be added later without an enum break.

---

## R-003: Reachability probe semantics

**Decision**: `evaluate_readiness()` accepts a `probe_reachability: bool = False` argument. When `False`, the evaluator never makes a network call and never returns `HOST_UNREACHABLE`. When `True`, it issues a single bounded HTTP `HEAD` against `SyncConfig.server_url` with a 2-second timeout and a 1-attempt retry budget.

**Rationale**:
- NFR-003 forbids passive network side effects in help and local-only commands. Making reachability **opt-in** preserves that guarantee even when commands accidentally call `evaluate_readiness()` for a non-network reason (e.g., displaying status).
- A 2-second cap honors the charter's "CLI < 2 s for typical projects" budget on the worst case, and the 1-attempt budget keeps `HOST_UNREACHABLE` from masking transient flakes (the user re-runs the command).
- The probe lives behind the same evaluator entry point so callers do not need to chain two functions.

**Alternatives considered**:
- *Always probe*: rejected — violates NFR-003 for any caller that just wants to know "is auth present".
- *Never probe (separate function)*: rejected — adds an API surface for a degenerate case and forces callers to remember two entry points.
- *Background pre-warm reachability cache*: rejected — would itself be a passive network side effect.

---

## R-004: Where `sync.background_daemon` lives

**Decision**: Add `background_daemon: BackgroundDaemonPolicy = AUTO` to the existing `SyncConfig` dataclass at `src/specify_cli/sync/config.py:12-70`, persisted in the existing user-level `~/.spec-kitty/config.toml` under the existing `[sync]` table. **No project-level config is added in this mission.**

**Rationale**:
- The spec wording is "operator-facing config that decides whether hosted commands auto-start the background sync daemon." Daemon startup is a per-machine decision (operator preference about local resource use), so user-level is the correct scope.
- `SyncConfig` already exists, already has a `[sync]` table, and is already loaded everywhere the daemon runs — extending it costs one field and one TOML key.
- Project-level overrides in `.kittify/config.yaml` are explicitly **out of scope** for this mission. If a future need emerges (e.g., per-repo CI policy), the layering can be added by introducing a `resolve_background_daemon_policy(repo_root) -> BackgroundDaemonPolicy` helper that consults project config first and falls back to user config. The new enum and the daemon's intent gate stay unchanged.

**Alternatives considered**:
- *Project-level only*: rejected — operator preference does not belong in source-controlled config.
- *Both, with project taking precedence*: rejected as scope creep for this mission. Documented as the future migration path.
- *Environment variable*: rejected — env vars are already overloaded by `SPEC_KITTY_ENABLE_SAAS_SYNC`; adding a second knob there confuses the rollout story.

---

## R-005: How "intent" is expressed at daemon call sites

**Decision**: Introduce a typed `DaemonIntent` enum with two members (`LOCAL_ONLY`, `REMOTE_REQUIRED`) and require it as a **mandatory keyword-only argument** on `ensure_sync_daemon_running()`. The function refuses to start the daemon when:

```
intent != DaemonIntent.REMOTE_REQUIRED
  OR
SyncConfig.background_daemon == BackgroundDaemonPolicy.MANUAL
```

When `MANUAL` blocks an otherwise-`REMOTE_REQUIRED` call, the function returns a typed `DaemonStartOutcome` indicating the manual block, and CLI callers print "Background sync is in manual mode. Run `spec-kitty sync run` to perform a one-shot remote sync."

**Rationale**:
- A mandatory keyword-only enum forces every existing caller to **make an explicit choice at the call site** during the audit pass. There is no default that can silently regress to the old behavior.
- Two values are sufficient — the spec only distinguishes "needs hosted sync" from "doesn't". Adding more granularity now would be speculative.
- Returning an outcome (rather than raising) lets the dashboard server log "manual mode active" without crashing on every request.

**Audit list** (call sites that must be updated):
| File | Current behavior | New intent |
|---|---|---|
| `src/specify_cli/dashboard/server.py` (daemon ensure on dashboard startup) | Always starts | `LOCAL_ONLY` — dashboard reads local state; remote sync is opt-in via explicit dashboard action |
| `src/specify_cli/dashboard/handlers/api.py` (daemon ensure on API requests) | Starts on every API hit | `LOCAL_ONLY` for read endpoints; `REMOTE_REQUIRED` only on the explicit "sync now" endpoint |
| `src/specify_cli/sync/events.py` (daemon ensure on event emission) | Starts when an event needs uploading | `REMOTE_REQUIRED` — events are the canonical signal that hosted sync is needed |

The audit's correctness is verified by `tests/sync/test_daemon_intent_gate.py` (Phase 1 contract).

**Alternatives considered**:
- *Boolean `intent_remote: bool`*: rejected — booleans at call sites are easy to flip the wrong way and read poorly.
- *Per-command Typer decorator*: rejected — the daemon is started from non-Typer code paths (dashboard server) too.
- *Default `intent=LOCAL_ONLY`*: rejected — silent defaults are how the current bug exists.

---

## R-006: Test fixture strategy for dual-mode coverage

**Decision**:
- The existing autouse fixture `_enable_saas_sync_feature_flag` at `tests/conftest.py:57-60` stays in place so unrelated tracker tests do not regress.
- New dual-mode tests **explicitly opt out** via `monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)` inside the rollout-off case.
- Two new shared fixtures live under `tests/saas/conftest.py`:
  - `rollout_disabled` — `monkeypatch.delenv(...)`
  - `rollout_enabled` — `monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")`
- Auth/config/binding fixtures are factored into `tests/saas/conftest.py` and shared between unit and integration layers. Unit tests pass them via stubs of the readiness evaluator's prerequisite probes; integration tests pass them by writing real fixture files into a `tmp_path` and pointing `SyncConfig` at it.
- Parametrized tests use `pytest.mark.parametrize("mode", [rollout_disabled, rollout_enabled])` so each user story gets one test row per mode without duplication.

**Rationale**:
- Reverses the autouse default only where dual-mode behavior is the subject under test, leaving every other test stable.
- Sharing fixture data between stubs and real evaluation prevents the unit/integration layers from drifting in what "auth present" actually looks like.
- Parametrization (rather than separate test functions) keeps the spec's "both modes" requirement legible in a single place.

**Alternatives considered**:
- *Remove the autouse fixture*: rejected — would touch every existing tracker test in this mission.
- *Use environment files instead of monkeypatch*: rejected — `monkeypatch` is already the project pattern.
- *Skip integration layer*: rejected — directly contradicts the spec's "smaller integration layer for the real evaluator" requirement.

---

## Items Explicitly Out of Scope (Recorded for Future Missions)

The following came up during Phase 0 and are deliberately deferred:

1. **Project-level override of `sync.background_daemon`** — see R-004. Path forward documented; no work in this mission.
2. **Subdividing `MISSING_AUTH`** into `NO_TOKEN | EXPIRED_TOKEN` — see R-002. Requires upstream auth lookup changes.
3. **Reachability cache** to amortize the 2-second probe cost — see R-003. Would itself be a passive side effect; deferred.
4. **Removing the `feature_flags.py` re-export shims** — once all callers import from `specify_cli.saas.rollout`, the shims can be deleted. Out of scope here.
5. **Removing the `SPEC_KITTY_ENABLE_SAAS_SYNC` env var entirely** — explicitly forbidden by the spec's locked planning decisions.
