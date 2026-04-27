# Research: CLI Upgrade Nag and Lazy Project Migration

**Mission**: `cli-upgrade-nag-lazy-project-migrations-01KQ6YDN`
**Phase**: 0 (Research)
**Inputs**: [`spec.md`](spec.md), [`plan.md`](plan.md)

This document resolves every open technical question that the spec deliberately deferred to planning. Each entry follows the **Decision / Rationale / Alternatives considered** pattern from DIRECTIVE_003.

---

## R-01 — Latest-version source

**Decision**: Use the PyPI JSON metadata endpoint `https://pypi.org/pypi/spec-kitty-cli/json` as the default `LatestVersionProvider` implementation. Parse `info.version`. Timeout 2 s. `follow_redirects=False`. Response body capped at 1 MB before parsing.

**Rationale**:
- Stable, well-documented JSON shape; PyPI explicitly supports the JSON API for read-only metadata.
- Zero subprocess cost (compared to shelling out to `pip index`).
- Single hostname (`pypi.org`) → trivial to allowlist for security review (see security checklist CHK013).
- httpx already a runtime dep, no new dependency surface (C-009).
- Failure modes (network down, DNS error, HTTP 4xx/5xx, malformed JSON, oversized response) all produce a clean `None` from the provider, which the planner treats as "latest unknown" → no nag, no error (NFR-002 fail-open).

**Alternatives considered**:
- *GitHub Releases API*. Higher rate-limit pressure for unauthenticated callers; needs a separate hostname; would require following redirects. Rejected.
- *`pip index versions spec-kitty-cli`*. Subprocess cost (~200–500 ms cold), output format is not strictly stable, fragile under user pip configurations. Rejected.
- *Embedded "last known release" file shipped with the CLI*. Stale by definition; defeats the purpose of a freshness nag. Rejected.

**Implementation notes**:
- Provider returns a `LatestVersionResult` with `version: str | None` and `source: Literal["pypi","none"]`. Never raises.
- Sanitises the parsed version string against `^[A-Za-z0-9.\-+]{1,64}$` before returning, so a hostile payload cannot inject ANSI / shell metacharacters into the upgrade hint (security CHK016, CHK028).

---

## R-02 — Nag cache location

**Decision**: Use `platformdirs.user_cache_dir("spec-kitty")` if `platformdirs` is available transitively; otherwise fall back to manual XDG resolution: `$XDG_CACHE_HOME/spec-kitty/` (default `~/.cache/spec-kitty/` on Linux, `~/Library/Caches/spec-kitty/` on macOS, `%LOCALAPPDATA%\spec-kitty\Cache\` on Windows). File name: `upgrade-nag.json`.

**Rationale**:
- Per-user (not per-project) → lines up with FR-021 (no global project registry) and A-001.
- Standard cache location respects OS conventions; users who clear their cache lose only the throttle.
- Manual fallback path keeps C-009 satisfied (no new mandatory runtime dep).

**Alternatives considered**:
- *`~/.kittify/upgrade-nag.json`*. Couples nag state to per-project runtime dir; conceptually wrong (nag is per-user) and risks corrupting `~/.kittify/` if filled with stale entries. Rejected.
- *In-memory only / no cache*. Defeats throttle; would re-fetch from PyPI on every invocation. Rejected.

**Implementation notes**:
- File written via `os.open(path, O_CREAT | O_WRONLY | O_TRUNC, 0o600)` on POSIX (security CHK006).
- Parent directory created with mode 0o700.
- Reader refuses to follow symlinks: stat the path with `os.lstat`; reject if it's a symlink (CHK009/CHK010).
- Reader refuses to operate when `$XDG_CACHE_HOME` (or the resolved cache dir) is owned by a different uid than the process (CHK023). Best-effort on Windows.

---

## R-03 — Install-method detection

**Decision**: A small detection chain returns one of `pipx | pip-user | pip-system | brew | system-package | source | unknown`. Hint strings are pulled from a static table.

**Rationale**: A wrong hint (e.g. `pipx upgrade` for a `pip --user` install) is worse than no hint. The detection must fail to `unknown` rather than guess.

**Algorithm** (first match wins):

1. **Source / dev install**: `Path(spec_kitty.__file__).parent.is_relative_to(Path.cwd())` AND a `pyproject.toml` exists at the package root → `source`. Hint: "rebuild from source: `pip install -e .` (or your normal dev workflow)".
2. **pipx**: `sys.executable` lives under any of `~/.local/pipx/venvs/`, `/usr/local/pipx/venvs/`, or any path matching `*/pipx/venvs/spec-kitty*`. Hint: `pipx upgrade spec-kitty-cli`.
3. **brew**: `sys.executable` lives under `<brew-prefix>/Cellar/` or `<brew-prefix>/opt/`, where `<brew-prefix>` comes from `subprocess.run(["brew","--prefix"], ...)` with a 1 s timeout, or `/opt/homebrew/` / `/usr/local/` heuristics if `brew` isn't on PATH. Hint: `brew upgrade spec-kitty-cli`.
4. **System package**: `sys.executable` is `/usr/bin/python*` AND the package was installed by a system manager (`importlib.metadata.distribution("spec-kitty-cli").read_text("INSTALLER")` returns something like `apt`, `dnf`, `pacman`). Hint: "use your system package manager (`apt|dnf|pacman` upgrade spec-kitty-cli)".
5. **pip user vs pip system**: `importlib.metadata` `INSTALLER` says `pip` AND distribution location lies under `site.getusersitepackages()` → `pip-user`, hint `pip install --user --upgrade spec-kitty-cli`. Otherwise `pip-system`, hint `pip install --upgrade spec-kitty-cli`.
6. **Fallback**: `unknown`. Hint: a documented multi-line manual block, NOT a copy-pasteable shell command (security CHK031).

**Alternatives considered**:
- *Always print a generic `pip install --upgrade ...`*. Wrong for pipx and brew users → `pip` would create a parallel install. Rejected.
- *Ask the user*. Violates FR-007 (provide guidance, do not interrogate). Rejected.

**Implementation notes**:
- Detection is invoked once per planner call and cached in-process.
- The chain MUST NOT shell out unless step 3 needs `brew --prefix`; that subprocess has a hard 1 s timeout and falls through silently on failure.

---

## R-04 — Project metadata loading hardening

**Decision**: Reuse `migration.schema_version.get_project_schema_version(repo_root)` as the canonical reader. Wrap it with these added guards:

- File-size cap of 256 KB before parsing (CHK020 — yaml-bomb defense).
- `yaml.safe_load` only (`ruamel.yaml.YAML(typ="safe")` per the charter dependency).
- Schema-version field validated against `int` in range `[0, 1000]`; anything else → `"unreadable"` (CHK021).
- `.kittify/metadata.yaml` ownership not enforced; if owned by another user, planner returns `BLOCK_PROJECT_CORRUPT` rather than reading further (CHK023). Documented behavior.

**Rationale**: `get_project_schema_version` already exists and is the right home for these guards. We harden it once and every caller benefits.

**Alternatives considered**:
- *New parser in `compat/`*. Two parsers means two safety bugs to fix. Rejected.

---

## R-05 — Schema version range activation

**Decision**: Replace `REQUIRED_SCHEMA_VERSION: int | None` with two integers:

```python
MIN_SUPPORTED_SCHEMA: int = N      # below this → migrate the project
MAX_SUPPORTED_SCHEMA: int = M      # above this → upgrade the CLI
```

Both are set during the implementation phase; values are derived from the current migration registry's lowest and highest target schema. The existing `REQUIRED_SCHEMA_VERSION` symbol is kept as a deprecated alias (`MIN_SUPPORTED_SCHEMA`) so any third-party importer doesn't break (NFR-006).

The gate's "early return when `REQUIRED_SCHEMA_VERSION is None`" is replaced by the planner. With both `MIN` and `MAX` set, the planner returns:

| Project schema | Decision |
|---|---|
| `< MIN` | `BLOCK_PROJECT_MIGRATION` (or `ALLOW` if invocation is safe per registry) |
| `MIN ≤ x ≤ MAX` | `ALLOW` or `ALLOW_WITH_NAG` |
| `> MAX` | `BLOCK_CLI_UPGRADE` |
| field missing | `BLOCK_PROJECT_MIGRATION` (legacy project — needs init/migrate) |
| metadata corrupt | `BLOCK_PROJECT_CORRUPT` |

**Activation ordering** (RP-01 mitigation):
1. Implementation merges `compat/` with planner returning `ALLOW` for all projects (gate still effectively no-op).
2. The migration that bumps schema to the new minimum is shipped in the same release.
3. After both ship, a separate small change sets `MIN_SUPPORTED_SCHEMA` to a value that includes existing real-world projects. Document in CHANGELOG.

This avoids a release in which a pre-existing project is suddenly blocked before users could run `spec-kitty upgrade`.

**Alternatives considered**:
- *Keep `REQUIRED_SCHEMA_VERSION` as a single integer.* Forces the spec's "project too new" case (FR-010) to be ad-hoc; today the gate has no way to express it. Rejected.

---

## R-06 — Throttle window default and configuration

**Decision**:
- Default throttle window: **86 400 seconds (24 h)** per user.
- Configuration surfaces:
  1. Environment variable `SPEC_KITTY_NAG_THROTTLE_SECONDS` (highest precedence).
  2. User config file `$XDG_CONFIG_HOME/spec-kitty/upgrade.yaml`, key `nag.throttle_seconds`.
  3. Built-in default 86 400.
- Acceptable range: `60 ≤ value ≤ 31_536_000` (1 minute to 1 year). Out-of-range values fall back to the default and emit a debug-level note.

**Rationale**:
- Env var first matches Spec Kitty conventions in `cli/helpers.py` (e.g. `SPEC_KITTY_SIMPLE_HELP`).
- File-based override gives users a stable place to disable nag entirely (set to a year).
- Range bound prevents user error or hostile env from disabling (`0`) or overflowing (`MAX_INT`) the throttle (security CHK025/CHK044).

**Alternatives considered**:
- *Hardcoded 24 h, no override*. Rejected (NFR-009 mandates configurability).
- *Per-project override*. Couples a per-user concern to per-project config. Rejected.

---

## R-07 — CI / non-interactive predicate

**Decision**: A request to `compat.planner.plan(...)` enters CI/non-interactive mode if **any** of the following is true:

- `os.environ.get("CI", "").lower() in {"1","true","yes","on"}`
- `os.environ.get("SPEC_KITTY_NO_NAG", "").lower() in {"1","true","yes","on"}`
- `--no-nag` is in `sys.argv` for this invocation
- `not sys.stdout.isatty()`

When any of these holds, the planner uses `NoNetworkLatestVersionProvider` (which always returns `None` and never opens a socket) and the nag line is suppressed regardless of cache state.

**Rationale**: the union biases toward "less surprising" behavior in any automation context. The combination is conservative; users who explicitly want a network check in CI can use `spec-kitty upgrade --cli` (which always allows network).

**Alternatives considered**:
- *Only `CI=1`*. Misses `pytest` and any tool that pipes stdout to `less`. Rejected.
- *Only no-TTY*. Misses GitHub Actions where stdout is technically a TTY in some matrices. Rejected.

---

## R-08 — Exit codes for blocked unsafe commands

**Decision**:

| Decision | Exit code |
|---|---|
| `ALLOW` | 0 (or whatever the underlying command returns) |
| `ALLOW_WITH_NAG` | 0 (or whatever the underlying command returns) |
| `BLOCK_PROJECT_MIGRATION` | **4** |
| `BLOCK_CLI_UPGRADE` | **5** |
| `BLOCK_PROJECT_CORRUPT` | **6** |
| `BLOCK_INCOMPATIBLE_FLAGS` | **2** (typer convention for usage errors) |

`spec-kitty upgrade --dry-run` always exits **0** (the plan content is in the payload, not the exit code), per FR-012 and SC-004.

**Rationale**: distinct exit codes let scripts switch on cause without parsing stderr. Codes start at 4 to avoid colliding with typer's reserved 1 (general error) and 2 (usage), and shell convention 130 (SIGINT).

**Alternatives considered**:
- *All blocks return 1*. Loses the "what went wrong" signal that wrappers care about. Rejected.

---

## R-09 — JSON contract stability scope

**Decision**: The `--json` schema documented in `contracts/compat-planner.json` is **stable across patch releases of `spec-kitty-cli`**. Minor releases may **add** fields with sensible defaults; they may not remove or repurpose existing fields. Major releases may break the contract; the breakage is called out in CHANGELOG.

**Rationale**: matches checklist CHK056 and the spirit of FR-022. Patch-stability is the minimum viable promise for users wiring scripts; minor-additive matches typical SemVer practice for CLI JSON.

**Alternatives considered**:
- *Stable forever, no breakage permitted*. Couples internal evolution to one early choice. Rejected.

---

## R-10 — Fail-closed unregistered command behavior

**Decision**: Per the user's Q3 refinement: any command path that is not present in the central `SAFETY_REGISTRY` is treated as `UNSAFE` when the project schema is incompatible. The seed registry covers the existing CLI surface (a single short table). Newly added commands must register or accept the unsafe default. A unit test in `tests/specify_cli/compat/test_safety.py` enumerates `typer`'s registered commands and asserts that any command missing from the registry is observably treated as unsafe (i.e. the policy is enforced, not just documented).

**Rationale**: prevents the silent "I added a command and forgot to classify it, so it accidentally runs under an incompatible schema" failure mode.

**Alternatives considered**:
- *Default to safe for unknown commands*. Spec is explicit: under schema mismatch we want to err on the side of refusing to run (FR-008). Rejected.

---

## R-11 — Test fixtures for fixture projects

**Decision**: `tests/conftest.py`-level fixtures provide three on-disk fixture-project shapes via `tmp_path`:

- `fixture_project_compatible`: `.kittify/metadata.yaml` with `spec_kitty.schema_version` = `MAX_SUPPORTED_SCHEMA`.
- `fixture_project_stale`: schema set to `MIN_SUPPORTED_SCHEMA - 1` (only meaningful once the gate is activated; until then test forces the comparison via planner injection).
- `fixture_project_too_new`: schema set to `MAX_SUPPORTED_SCHEMA + 1`.

A fourth fixture, `fixture_project_corrupt`, writes a YAML file that fails parse-bounds checks (oversized, malformed, alias-bombed).

**Rationale**: explicit fixture shapes keep integration tests readable and avoid every test re-rolling its own metadata file. Aligns with checklist CHK032.

---

## R-12 — Documentation update scope

**Decision**: `docs/how-to/install-and-upgrade.md` is rewritten for SC-008 to:
- explain the difference between "upgrade the CLI" and "migrate the current project";
- show a worked example for each FR-23 case;
- document `--cli`, `--project`, `--yes`, `--no-nag`, the env vars `SPEC_KITTY_NO_NAG` and `SPEC_KITTY_NAG_THROTTLE_SECONDS`, and the exit codes from R-08;
- link to the contract JSON schema in `contracts/`.

No new docs files are created; the existing how-to is the canonical entry point.

**Rationale**: minimum sufficient documentation deliverable; satisfies SC-008 without doc sprawl.

---

## Open items deferred to implementation

None. Every spec assumption is now backed by a concrete decision above.

If the implementer hits an unknown during work-package execution, they MUST surface it via `/spec-kitty.review` and update this `research.md` with a new `R-NN` entry (per DIRECTIVE_003), rather than making the choice silently in code.
