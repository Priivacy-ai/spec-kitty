---
title: SPEC_KITTY_* env census — sync surface
description: 'Env census of the sync surface: a live or retired verdict for every SPEC_KITTY_* reference, proving the Wave-4 de-god deleted no environment name.'
doc_status: active
updated: '2026-08-29'
related:
- docs/plans/code-quality/index.md
- docs/plans/code-quality/targeted-cleanup-scoping.md
- docs/plans/refactor/degod-unshim-roadmap.md
---
# `SPEC_KITTY_*` env census — sync surface (mission `sync-cli-degod-wave4-01M0B0MX`, WP12 / FR-007)

**Purpose.** Inventory every `SPEC_KITTY_*` reference on the `spec-kitty sync` surface and
record a `live` / `retire-candidate` verdict for each. This is the **anti-deletion proof**
(FR-007): the Wave-4 sync de-god relocated decision logic off the `cli/commands/sync.py`
god-module into the `specify_cli.sync.sync_*` seam modules, and this census establishes that
the relocation **deleted no environment reference** — a relocation moves a reference from the
husk to a seam module, but the *set* of referenced names is invariant.

**Retirement was out of scope for the Wave-4 mission itself (WS6 / INV-6).** Verdicts were an
inventory only there; no variable was deleted, renamed, or rewired by that mission. Every
`retire-candidate` was handed to the WS6 follow-on issue (FR-008) for deliberate, later action.

**Update (#3569, 2026-08-20).** The sole `retire-candidate`, `SPEC_KITTY_DIR`, has been retired:
its remaining test importers were migrated off the name (they patched it defensively alongside
the real `DAEMON_*_FILE` lazy attributes but nothing in production ever read it — the patches
were removed outright) and the shim was deleted from `daemon.py`. The census below reflects the
post-retirement state (7 references, all `live`).

**Update (#3626, 2026-08-21).** The negotiated-admission fix (restoring hosted event-sync
delivery, #3564/#3620) added one new `live` reference — `SPEC_KITTY_SYNC_STRICT_ADMISSION`, the
operator opt-in that flips the admission gate from its non-strict default to strict enforcement
(read by `sync/admission_negotiation.py`). This is a **growth**, not a relocation or deletion:
the frozen set and the census table below now carry 8 `live` references.

**Update (#2801 / #3799, 2026-08-29).** The `sync-deactivate-by-default` mission made the
legacy local-sync surface **inactive by default** (opt in via `SPEC_KITTY_ENABLE_SAAS_SYNC=1`)
and, as part of that, cleanly **cut the pre-review regression gate off the shared sync
toggles onto its own dedicated env**, `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` (FR-009). That gate
lives in the move-task command (`cli/commands/agent/tasks_move_task.py`) — deliberately NOT on
the sync husk/package surface, because a machine that disabled sync must still enforce the
review gate. To keep the anti-deletion invariant aware of the decoupled flag, the guard folds
that one file into the scanned surface but admits **only** its `SPEC_KITTY_PRE_REVIEW_*`
family (never its incidental docstring mentions of the now-no-op sync-disable toggles). This is
a **growth**, not a relocation or deletion: the frozen set and the census table below now carry
9 `live` references.

**Surface scanned.** `src/specify_cli/cli/commands/sync.py` (the husk) plus every `*.py` under
`src/specify_cli/sync/` (recursively), plus the decoupled pre-review gate file
`src/specify_cli/cli/commands/agent/tasks_move_task.py` — folded in for its
`SPEC_KITTY_PRE_REVIEW_*` family only (#2801 / FR-009). The frozen expected set and the executable guard live in
[`tests/architectural/test_sync_env_census.py`](../../../tests/architectural/test_sync_env_census.py);
a removed reference shrinks the scanned set and turns that guard red.

**Scanner note.** The guard matches `SPEC_KITTY_[A-Z0-9_]+` and discards any token ending in
`_`. A real environment/module name never ends in an underscore; the only trailing-underscore
token on the surface is the wildcard `SPEC_KITTY_SYNC_*` written in a `restart.py` comment
(`# ... the #2573b disable-env skip (SPEC_KITTY_SYNC_*)`), which is a family reference, not a
distinct name.

## Census (9 references, all `live`; 1 historical `retired`)

| # | Reference | Kind | Verdict | Where / role |
|---|-----------|------|---------|--------------|
| 1 | `SPEC_KITTY_HOME` | env var | **live** | Runtime state root override (`clock.py`, `config.py`, `daemon.py`, `body_upload.py`, …). The canonical home seam; honoured lazily so test `HOME` monkeypatching works. |
| 2 | `SPEC_KITTY_SAAS_URL` | env var | **live** | SaaS target URL override folded into `SyncConfig.resolve_runtime_target` precedence (`config.py`, `owner.py`, `preflight.py`, `target_authority.py`). |
| 3 | `SPEC_KITTY_ENABLE_SAAS_SYNC` | env var | **live** | The SaaS-sync arming flag (`consent.py`, `runtime.py`, `sync_render.py`, `__init__.py`). Arming, never per-project consent — the canonical gate for auth/network flows. |
| 4 | `SPEC_KITTY_SYNC_MINIMAL_IMPORT` | env var | **live** | Import-skip toggle set by the daemon child (`daemon.py`) and read by the package `__init__.py` to avoid eager heavy imports during daemon spawn. |
| 5 | `SPEC_KITTY_SYNC_READONLY_IDENTITY` | env var | **live** | Read-only-identity flag (`events.py`, `READ_ONLY_IDENTITY_ENV`) gating identity mutation on event emission. |
| 6 | `SPEC_KITTY_NO_AUTO_CUTOVER` | env var | **live** | Refuses legacy-root auto-cutover (`layout_generation.py`, `NO_AUTO_CUTOVER_ENV`). Active operator escape hatch. |
| 7 | `SPEC_KITTY_CLI_VERSION` | env var | **live** | Pins the CLI version across daemon respawn (`daemon.py`): read on start, re-exported onto the respawned child's env. |
| 8 | `SPEC_KITTY_SYNC_STRICT_ADMISSION` | env var | **live** | Strict-admission opt-in (`admission_negotiation.py`, `STRICT_ADMISSION_ENV_VAR`). Flips the negotiated admission gate from its non-strict default (mint a local self-admission so a consented, authenticated project delivers) to strict enforcement (require a server-issued admission). Added #3626 for the hosted event-sync delivery restore (#3564/#3620); dormant until the SaaS admission endpoint (spec-kitty-saas#795) deploys. |
| 9 | `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` | env var | **live** | The pre-review regression gate's own disable flag (`cli/commands/agent/tasks_move_task.py`, `_PRE_REVIEW_GATE_DISABLE_ENV`). A **gate** flag, not a sync flag: #2801 / FR-009 cut the pre-review gate off the shared sync toggles onto this dedicated env so a machine with sync disabled still enforces the gate. Added by the `sync-deactivate-by-default` mission (#3799). Folded into the scanned surface (its family only) so a silent deletion still reds the guard. |
| ~~10~~ | `SPEC_KITTY_DIR` | module-attribute shim | **retired (#3569)** | *Was not* an `os.environ` variable — a legacy lazily-resolved module attribute on `daemon.py` (`_LAZY_PATH_RESOLVERS`, served via `__getattr__`), superseded at runtime by `SPEC_KITTY_HOME` + `get_runtime_root()`. Had no production readers; the only remaining bindings were defensive `monkeypatch`/`patch` calls in daemon tests (alongside the still-live `DAEMON_*_FILE` lazy attributes) that had no effect on behaviour. Those bindings were deleted and the shim removed from `daemon.py` and `_LAZY_PATH_RESOLVERS`. |

### Verdict rationale

- **`live` (9)** — every entry except the retired historical `SPEC_KITTY_DIR` is a genuine,
  actively-consumed environment variable whose deletion would change behaviour. Entries #1–#7
  pre-date the Wave-4 mission and survive its relocation unchanged; #8
  (`SPEC_KITTY_SYNC_STRICT_ADMISSION`) was added by #3626 as a new live opt-in; #9
  (`SPEC_KITTY_PRE_REVIEW_GATE_DISABLE`) was added by #2801 / #3799 as the decoupled pre-review
  gate's own flag (a gate flag folded into the scanned surface, not a de-god artefact).
- **`retired` (1, was `retire-candidate`)** — `SPEC_KITTY_DIR` was a backward-compatibility module
  shim, not an env var. Its runtime authority had already moved to `SPEC_KITTY_HOME` /
  `get_runtime_root()`; the only remaining callers were test monkeypatches that did nothing (they
  set an attribute production code never read). #3569 (the WS6 follow-on, FR-008) confirmed that
  and deleted the shim.

## Anti-deletion invariant (FR-007)

The frozen set below is the contract. `tests/architectural/test_sync_env_census.py` recomputes
it from the live tree on every run; any shrinkage (a deleted reference) fails the guard.

```
SPEC_KITTY_CLI_VERSION
SPEC_KITTY_ENABLE_SAAS_SYNC
SPEC_KITTY_HOME
SPEC_KITTY_NO_AUTO_CUTOVER
SPEC_KITTY_PRE_REVIEW_GATE_DISABLE
SPEC_KITTY_SAAS_URL
SPEC_KITTY_SYNC_MINIMAL_IMPORT
SPEC_KITTY_SYNC_READONLY_IDENTITY
SPEC_KITTY_SYNC_STRICT_ADMISSION
```

(`SPEC_KITTY_DIR` was removed from this frozen set by #3569's deliberate retirement — see the
census row above. `SPEC_KITTY_SYNC_STRICT_ADMISSION` was added by #3626's deliberate growth,
and `SPEC_KITTY_PRE_REVIEW_GATE_DISABLE` by #2801 / #3799's deliberate decoupling — both new
live references, likewise recorded in the census rows above.)
