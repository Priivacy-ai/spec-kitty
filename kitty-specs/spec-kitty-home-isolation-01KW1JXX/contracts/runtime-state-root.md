# Contract: Runtime State Root Resolution

**Surface**: `specify_cli.paths.get_runtime_root()` → `RuntimeRoot`
**Consumers**: all global sync/auth/tracker/daemon/state modules

## Environment variable contract

| Condition | `RuntimeRoot.base` (all platforms) |
|-----------|------------------------------------|
| `SPEC_KITTY_HOME` set, non-empty | `Path(os.environ["SPEC_KITTY_HOME"])` |
| `SPEC_KITTY_HOME` unset or empty, POSIX | `Path.home() / ".spec-kitty"` |
| `SPEC_KITTY_HOME` unset or empty, Windows | `platformdirs.user_data_dir("spec-kitty", appauthor=False, roaming=False)` |

## Behavioral guarantees

- **G1**: For any two distinct values of `SPEC_KITTY_HOME`, the resolved `base` paths are
  distinct (isolation).
- **G2**: Resolution is pure — no directory is created, no file is read (NFR-002).
- **G3**: With `SPEC_KITTY_HOME` unset, `base` equals the pre-fix value on each platform
  (POSIX byte-identical — NFR-001; Windows = platformdirs base — NFR-003/D4).
- **G4**: Every global-state location is `get_runtime_root().base` joined with a fixed,
  per-surface relative suffix (see `state-surface-map.md`); no consumer recomputes the home
  independently (FR-010).

## Test obligations

| ID | Assertion |
|----|-----------|
| T-RR-1 | `SPEC_KITTY_HOME=/tmp/x` ⇒ `get_runtime_root().base == Path("/tmp/x")` on linux, darwin, win32 (monkeypatched platform). |
| T-RR-2 | `SPEC_KITTY_HOME=""` ⇒ falls through to platform default on each platform. |
| T-RR-3 | Unset ⇒ POSIX `~/.spec-kitty`; Windows platformdirs base. |
| T-RR-4 | Calling `get_runtime_root()` creates no directories (assert base/`auth`/etc. absent on a temp HOME). |
| T-RR-5 | Architectural guard: no module in `sync/auth/tracker/state` contains `Path.home() / ".spec-kitty"` (allowlist keystone + asset-home + migration/fallback). |
