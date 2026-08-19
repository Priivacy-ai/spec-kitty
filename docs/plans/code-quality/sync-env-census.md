# `SPEC_KITTY_*` env census — sync surface (mission `sync-cli-degod-wave4-01M0B0MX`, WP12 / FR-007)

**Purpose.** Inventory every `SPEC_KITTY_*` reference on the `spec-kitty sync` surface and
record a `live` / `retire-candidate` verdict for each. This is the **anti-deletion proof**
(FR-007): the Wave-4 sync de-god relocated decision logic off the `cli/commands/sync.py`
god-module into the `specify_cli.sync.sync_*` seam modules, and this census establishes that
the relocation **deleted no environment reference** — a relocation moves a reference from the
husk to a seam module, but the *set* of referenced names is invariant.

**Retirement is out of scope (WS6 / INV-6).** Verdicts are an inventory only. No variable is
deleted, renamed, or rewired by this mission. Every `retire-candidate` is handed to the WS6
follow-on issue (FR-008); it is *documented*, never *actioned*, here.

**Surface scanned.** `src/specify_cli/cli/commands/sync.py` (the husk) plus every `*.py` under
`src/specify_cli/sync/` (recursively). The frozen expected set and the executable guard live in
[`tests/architectural/test_sync_env_census.py`](../../../tests/architectural/test_sync_env_census.py);
a removed reference shrinks the scanned set and turns that guard red.

**Scanner note.** The guard matches `SPEC_KITTY_[A-Z0-9_]+` and discards any token ending in
`_`. A real environment/module name never ends in an underscore; the only trailing-underscore
token on the surface is the wildcard `SPEC_KITTY_SYNC_*` written in a `restart.py` comment
(`# ... the #2573b disable-env skip (SPEC_KITTY_SYNC_*)`), which is a family reference, not a
distinct name.

## Census (8 references, 7 `live` / 1 `retire-candidate`)

| # | Reference | Kind | Verdict | Where / role |
|---|-----------|------|---------|--------------|
| 1 | `SPEC_KITTY_HOME` | env var | **live** | Runtime state root override (`clock.py`, `config.py`, `daemon.py`, `body_upload.py`, …). The canonical home seam; honoured lazily so test `HOME` monkeypatching works. |
| 2 | `SPEC_KITTY_SAAS_URL` | env var | **live** | SaaS target URL override folded into `SyncConfig.resolve_runtime_target` precedence (`config.py`, `owner.py`, `preflight.py`, `target_authority.py`). |
| 3 | `SPEC_KITTY_ENABLE_SAAS_SYNC` | env var | **live** | The SaaS-sync arming flag (`consent.py`, `runtime.py`, `sync_render.py`, `__init__.py`). Arming, never per-project consent — the canonical gate for auth/network flows. |
| 4 | `SPEC_KITTY_SYNC_MINIMAL_IMPORT` | env var | **live** | Import-skip toggle set by the daemon child (`daemon.py`) and read by the package `__init__.py` to avoid eager heavy imports during daemon spawn. |
| 5 | `SPEC_KITTY_SYNC_READONLY_IDENTITY` | env var | **live** | Read-only-identity flag (`events.py`, `READ_ONLY_IDENTITY_ENV`) gating identity mutation on event emission. |
| 6 | `SPEC_KITTY_NO_AUTO_CUTOVER` | env var | **live** | Refuses legacy-root auto-cutover (`layout_generation.py`, `NO_AUTO_CUTOVER_ENV`). Active operator escape hatch. |
| 7 | `SPEC_KITTY_CLI_VERSION` | env var | **live** | Pins the CLI version across daemon respawn (`daemon.py`): read on start, re-exported onto the respawned child's env. |
| 8 | `SPEC_KITTY_DIR` | module-attribute shim | **retire-candidate** | *Not* an `os.environ` variable — a legacy lazily-resolved module attribute on `daemon.py` (`_LAZY_PATH_RESOLVERS`, served via `__getattr__`), the import-time path constant **superseded by `SPEC_KITTY_HOME` + `get_runtime_root()`**. Kept only for external importers/tests that still reference the name. Candidate for removal once those callers migrate — deferred to WS6. |

### Verdict rationale

- **`live` (7)** — every entry except #8 is a genuine, actively-consumed environment variable
  whose deletion would change `sync` behaviour. None is a de-god artefact; all pre-date the
  mission and survive the relocation unchanged.
- **`retire-candidate` (1)** — `SPEC_KITTY_DIR` is a backward-compatibility module shim, not an
  env var. Its runtime authority already moved to `SPEC_KITTY_HOME` / `get_runtime_root()`. It
  is retained (not deleted) because external importers still bind the name; retiring it requires
  migrating those callers, which is WS6 follow-on work, not this mission (WS6 / INV-6).

## Anti-deletion invariant (FR-007)

The frozen set below is the contract. `tests/architectural/test_sync_env_census.py` recomputes
it from the live tree on every run; any shrinkage (a deleted reference) fails the guard.

```
SPEC_KITTY_CLI_VERSION
SPEC_KITTY_DIR
SPEC_KITTY_ENABLE_SAAS_SYNC
SPEC_KITTY_HOME
SPEC_KITTY_NO_AUTO_CUTOVER
SPEC_KITTY_SAAS_URL
SPEC_KITTY_SYNC_MINIMAL_IMPORT
SPEC_KITTY_SYNC_READONLY_IDENTITY
```
