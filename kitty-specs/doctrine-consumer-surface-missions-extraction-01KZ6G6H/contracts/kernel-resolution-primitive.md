# Contract: Kernel-Owned Sibling-Path-Resolution Primitive (FR-004)

Not an HTTP/API contract — this mission has no network surface. This is the behavioral contract the new kernel primitive and its two call sites (`kernel.paths.get_package_asset_root()`, `doctrine.pack_paths._resolve_built_in()`) must satisfy.

## Inputs

| Input | Source | Constraint |
|---|---|---|
| `anchor_file` | The calling module's own `__file__` | Must be the caller's own file — never a string naming another package. |
| `env_override` | Caller-read environment variable (e.g. `SPEC_KITTY_TEMPLATE_ROOT`, `SPEC_KITTY_PACKS_ROOT`) | The primitive receives the resolved override value, if any; it does not know environment-variable *names* (those stay caller-specific, since `kernel.paths` and `doctrine.pack_paths` use different variable names today). |
| `sibling_relative_path` | Caller-supplied relative path under the resolved root | e.g. `"missions"` (for kernel's asset root) or `"built-in"` (for doctrine's pack root). |

## Resolution order (must match `pack_paths._resolve_built_in`'s existing 4-step order exactly)

1. **Env override wins**, if the resolved override path (joined with `sibling_relative_path`) is a directory.
2. **Editable checkout**: walk `anchor_file.resolve().parents`, looking for `packs/built-in` (or the equivalent sibling shape) at each ancestor; `.resolve()` happens before the walk so symlinked editable installs still reach the real repo root.
3. **Installed wheel**: `anchor_file`'s own containing package directory's parent, joined with the sibling path — this works today because `packs/` is force-included as a site-packages sibling of *every* top-level package in the current monolith wheel, not specifically `doctrine` (verified against the root `pyproject.toml`).
4. **Fail closed**: raise a named exception (analogous to `PackRootNotFound`) naming what was sought and where it was not found. Never return a nonexistent path; never fall back to an arbitrary tree.

## Postconditions

- For every existing passing test in `tests/kernel/`, `tests/doctrine/`, and any test exercising `get_package_asset_root()`/`resolve_pack_root("built-in")`/`MissionTemplateRepository.default_missions_root()`, behavior is unchanged (NFR-001).
- No code path inside `src/kernel/` — including any transient/interim state during implementation — holds the literal string `"doctrine"`, `"specify_cli"`, or any mission-type name (`"software-dev"`, `"documentation"`, `"research"`, `"plan"`).
- **Three** call sites converge onto this primitive, not two: `kernel.paths.get_package_asset_root()`, `doctrine.pack_paths._resolve_built_in()`, and `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` (the authority a prior mission's WP06 already promoted, per `tests/charter/test_missions_root_authority.py`, and explicitly deferred converging to this issue).
- `doctrine.pack_paths.doctrine_package_dir()` is untouched — a separate, identity-pinned public symbol (`tests/doctrine/test_built_in_location_authority.py`) also consumed directly by `drg/migration/extractor.py`. This contract replaces `_resolve_built_in()`'s internal call to it, never the symbol itself.
- Since kernel cannot import `doctrine.pack_paths.PackRootNotFound` (layer direction), the primitive raises its own exception type. `pack_paths._resolve_built_in()`'s call site must catch-and-re-raise as `PackRootNotFound` — at least one consumer (`specify_cli/doctrine/pack_validator.py:793`, `except (PackRootNotFound, BuiltInContentDirNotAvailable)`) depends on that specific type surviving at the `pack_paths` boundary.

## Verification (NFR-002)

A new kernel-scoped architectural test, in the same AST-walk idiom as `tests/architectural/test_charter_no_specify_cli_import.py` (that gate's own docstring explains why pytestarch's import-edge analysis is insufficient here — it does not see a string-literal `importlib.resources.files(...)` call), must:

1. Walk every module under `src/kernel/**` and fail if any AST node contains the literal strings named above (import, call-argument, or f-string component).
2. Demonstrate non-vacuity via self-mutation: temporarily reintroducing the pattern must turn the new gate red, naming the exact site (mirrors the charter gate's own NFR-004-style proof).
