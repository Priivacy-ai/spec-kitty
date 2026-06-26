# Phase 0 Research: SPEC_KITTY_HOME State Isolation

All findings are grounded in the current code (verified during planning), not the issue's
prose alone.

---

## D1 — Where the bug actually lives

**Decision**: The keystone is `specify_cli.paths.get_runtime_root()` in
`src/specify_cli/paths/windows_paths.py:58`. It returns a frozen
`RuntimeRoot(platform, base)` with derived properties (`auth_dir`, `sync_dir`,
`daemon_dir`, `tracker_dir`, `cache_dir`), but **never reads `SPEC_KITTY_HOME`**: POSIX
hardcodes `Path.home() / ".spec-kitty"`, Windows uses `platformdirs.user_data_dir(...)`.

**Rationale**: Some Windows call sites already delegate to `get_runtime_root()`
(daemon `_daemon_root`/`_sync_root`, `token_manager._refresh_lock_path`,
`tracker.credentials._tracker_root`). Fixing the root therefore auto-fixes those Windows
paths. The remaining ~12 POSIX sites hand-roll `Path.home() / ".spec-kitty"` directly.

**Alternatives considered**:
- *Introduce a brand-new `get_state_root()`* — rejected; `get_runtime_root()` already
  models exactly this concept and is already partly wired. Adding a parallel function
  would deepen the very drift that caused the bug (DIRECTIVE_001).
- *A new env var (e.g. `SPEC_KITTY_STATE_HOME`)* — rejected per spec C-003 and the
  operator decision in `/spec-kitty.specify`: the public contract is `SPEC_KITTY_HOME`.

---

## D2 — How `SPEC_KITTY_HOME` should be read (semantics)

**Decision**: Mirror the existing asset-home idiom exactly:
`if env_home := os.environ.get("SPEC_KITTY_HOME"): base = Path(env_home)`. A set,
non-empty value becomes `base` **directly** (so `config.toml` lands at
`$SPEC_KITTY_HOME/config.toml`, matching the issue's "Not observed" expectation). An
unset **or empty** value falls through to the platform default.

**Rationale**: `get_kittify_home()` (both `runtime/home.py:33` and `kernel/paths.py:46`)
already uses the walrus-falsy idiom; `tests/kernel/test_paths.py` confirms empty string
falls through. Reusing the idiom satisfies FR-012 with zero surprise and keeps the two
home concepts consistent about how the variable is parsed.

**Alternatives considered**:
- *Treat empty string as "use empty dir"* — rejected; would create state under the CWD
  root and contradicts the asset-home behavior + existing test.

---

## D3 — Preserve per-platform child layout (the critical compatibility constraint)

**Decision**: Reroute each call site to `get_runtime_root().base` **and re-append that
site's current child suffix verbatim**. Do **not** blindly swap to `RuntimeRoot`'s derived
properties on POSIX.

**Rationale**: The POSIX layout is *flat* and diverges from the `RuntimeRoot` derived
properties (which match the *Windows* nested layout):

| Surface | POSIX today | `RuntimeRoot` property | Same? |
|---------|-------------|------------------------|-------|
| auth store | `base/auth` | `auth_dir = base/auth` | ✅ |
| sync daemon `_sync_root` | `base/sync` | `sync_dir = base/sync` | ✅ |
| sync daemon `_daemon_root` | `base` (flat) | `daemon_dir = base/daemon` | ❌ |
| tracker creds | `base` → `base/credentials` | `tracker_dir = base/tracker` | ❌ |
| tracker DB | `base/trackers` | `tracker_dir = base/tracker` | ❌ |
| sync config | `base/config.toml` | (no property) | — |
| clock | `base/clock.json` | (no property) | — |

Using `.daemon_dir`/`.tracker_dir` on POSIX would move `~/.spec-kitty/` → `~/.spec-kitty/daemon/`
and `~/.spec-kitty/credentials` → `~/.spec-kitty/tracker/credentials` — a silent
regression violating **NFR-001**. The safe transform is "swap the base, keep the suffix."

**Alternatives considered**:
- *Unify POSIX onto the nested `RuntimeRoot` properties* — rejected; breaks NFR-001 and
  would orphan existing operator data without the migration we explicitly excluded (C-001).

---

## D4 — Windows backward-compat (decision DM-01KW1KDHVGWZ0QERDMV1CRJ15S)

**Decision**: **Normalize all Windows surfaces onto the single platformdirs base.** Today,
several surfaces (sync `config.py`, `queue.py`, `clock.py`, tracker `store.py`) have **no
platform branch** and leak to `Path.home()/.spec-kitty` even on Windows, while daemon,
auth-lock, and tracker-creds already use the platformdirs base. Routing everything through
`get_runtime_root().base` makes Windows internally consistent. On unset Windows the
leaking surfaces move from `~/.spec-kitty/…` to the platformdirs app-data base.

**Rationale**: The issue's own acceptance criteria say "Windows tests confirm
`SPEC_KITTY_HOME` takes precedence over `platformdirs`" — i.e. platformdirs *is* the
canonical Windows base; the leaking sites are latent bugs. Operator (HiC) confirmed
normalization in plan. Recorded for fidelity (DIRECTIVE_003).

**Consequences / mitigations**:
- CHANGELOG entry documenting the Windows path normalization (IC-07, DIR-009).
- **No auto-migration** of existing Windows `~/.spec-kitty` data (C-001).
- `windows_storage.py` (auth) currently hardcodes `Path.home()/.spec-kitty/auth`; it is
  normalized to `auth_dir`. Verify/adjust `tests/auth/test_secure_storage_file.py` and any
  Windows auth test that pins the old path.

**Alternatives considered**:
- *Strictly preserve current per-surface Windows paths + per-surface legacy fallbacks* —
  rejected by decision; leaves Windows inconsistent and adds fallback complexity.

---

## D5 — Lazy resolution (import-time trap)

**Decision**: Replace the module-level `SPEC_KITTY_DIR = Path.home() / ".spec-kitty"` in
`sync/daemon.py:94` with a lazy function (or a call through `get_runtime_root()` at use
sites). Audit other modules for import-time path evaluation; resolve all global-state paths
**at call time**.

**Rationale**: Module-level constants are evaluated once at import, before tests (or a
shell) can set `SPEC_KITTY_HOME`, and cannot be monkeypatched per-test. Lazy resolution is
required for both correctness (env honored) and testability. `clock.py` already uses
`field(default_factory=…)` (lazy) and just needs its target swapped.

---

## D6 — Regression guard

**Decision**: Extend `tests/audit/test_no_legacy_path_literals.py` to assert that no
global-state module under `src/specify_cli/{sync,auth,tracker,state}` contains a
hand-rolled `Path.home() / ".spec-kitty"`. Allowlist the keystone
(`paths/windows_paths.py`), the asset-home modules (which use `.kittify`), and
migration/fallback code (`paths/windows_migrate.py`, the platformdirs-failure fallback).

**Rationale**: The bug is fundamentally "scattered literals drift from the contract." A
structural guard is the durable fix for FR-010 and prevents recurrence
(DIRECTIVE_001/024). Complements `tests/architectural/test_real_home_isolation_guard.py`.

**Alternatives considered**:
- *Rely on review only* — rejected; the literal already re-scattered once; convention is
  insufficient.

---

## Resolved unknowns

| Question | Resolution |
|----------|-----------|
| Does `get_runtime_root()` exist / what shape? | Yes — `windows_paths.py:58`, frozen `RuntimeRoot(platform, base)` + derived dirs. |
| Is the issue's call-site inventory complete? | Yes — 12 sites confirmed; no additional global-state sites. `windows_migrate.py` + platformdirs-fallback are init/migration, excluded. |
| Empty-string handling? | Falsy → falls through (matches asset-home; has existing test). |
| New dependencies? | None. |
| POSIX vs Windows layout? | Diverges; preserve POSIX suffix, normalize Windows to platformdirs base (D3/D4). |
| Where to add tests? | `tests/kernel/test_paths*.py`, `tests/paths/`, `tests/sync|auth|tracker`, `tests/audit/test_no_legacy_path_literals.py`. |
