# Contract: Kernel env-expansion seam

`src/kernel/env_expand.py` — one primitive, two policies. Consumed by charter (below specify_cli) and specify_cli.

## API
```python
def expand_env_template(raw: str, *, inject_defaults: bool, environ: Mapping[str,str] | None = None) -> str
class UnresolvedEnvTokenError(ValueError): ...
# kernel/paths.py
def get_packs_root_default() -> Path   # == get_built_in_pack_root().parent
```

## Behavioral guarantees (tests)
- **C-EXP-1**: `expand_env_template("${SPEC_KITTY_PACKS_ROOT}/built-in/x", inject_defaults=True)` with the var UNSET → resolves to `str(get_packs_root_default()) + "/built-in/x"` (no literal token, no raise).
- **C-EXP-2**: same call with `inject_defaults=False` and var unset → raises `UnresolvedEnvTokenError` naming the token.
- **C-EXP-3**: `get_packs_root_default()` == `get_built_in_pack_root().parent` (token names `…/packs`; resolver returns `…/packs/built-in`; no double-join).
- **C-EXP-4**: `org_pack_config._expand_path_template` delegates with `inject_defaults=False`; an org-pack `local_path` with an unset `${VAR}` still raises the existing fail-loud error (behavior byte-preserved).
- **C-EXP-5**: kernel module imports nothing from `specify_cli`/`doctrine` (arch-gated by `test_kernel_no_doctrine_import`/`test_layer_rules`).
