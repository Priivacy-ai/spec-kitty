# Contract: `.kitty.env` pre-import loader

`src/specify_cli/bootstrap/env_file.py` — invoked before any spec-kitty import.

## Behavioral guarantees (tests)
- **C-LDR-1 (precedence)**: var set in real env, per-repo `.kittify/.kitty.env`, and home-tier `${SPEC_KITTY_HOME}/.kitty.env` → resolved value is the real-env one; with real-env unset, the per-repo one; with both unset, the home one. (Tiers merged `{**home, **repo}`, then one `os.environ.setdefault`.)
- **C-LDR-2 (pre-import)**: `SPEC_KITTY_SYNC_MINIMAL_IMPORT` set only in `.kitty.env` → the import-time-gated behavior (`sync/__init__.py:455`) observes it; proves seed precedes `import specify_cli` (`__init__.py:36`).
- **C-LDR-3 (fail policy)**: absent file → warn+continue (exit 0); present-but-unreadable `env_file` → non-zero exit naming the file; malformed line → skipped + debug log, bootstrap survives.
- **C-LDR-4 (locator recursion)**: a `SPEC_KITTY_HOME=` line inside `.kitty.env` → ignored with a warning.
- **C-LDR-5 (single pointer)**: `config.yaml` `env_file` resolved once at bootstrap; a raw config reader never receives an unexpanded `${…}` token; the key is outside `extra="forbid"` blocks.
- **C-LDR-6 (budget)**: loader is stdlib-only; the completion benchmark shows no regression beyond its noise floor.
- **C-LDR-7 (cross-platform, state-root home)**: home-tier resolves to the STATE root — `%LOCALAPPDATA%\spec-kitty` on Windows, `~/.spec-kitty` on POSIX (NOT `~/.kittify`). The shim reuses ONE stdlib-safe kernel-floor state-root primitive (no 4th resolver); a test asserts the shim's unset-`SPEC_KITTY_HOME` default equals `get_runtime_root().base` on both platforms.
