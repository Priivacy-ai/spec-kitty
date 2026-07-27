# Research: Charter Phase 7 Release Closure

## Codebase Findings

### `validate_synthesis_state()` is already implemented

**Decision**: Call `validate_synthesis_state()` directly — no re-implementation needed.

`src/charter/bundle.py` already contains `validate_synthesis_state(repo_root: Path) -> BundleValidationResult`. It checks:
- Every artifact under `.kittify/doctrine/**` has a corresponding provenance sidecar under `.kittify/charter/provenance/`
- Every provenance sidecar references an artifact file that exists on disk
- If `.kittify/charter/synthesis-manifest.yaml` exists, verifies `content_hash` values match on-disk bytes
- Stale `.kittify/charter/.staging/<runid>.failed/` directories produce warnings (non-blocking)

Return type `BundleValidationResult` is a typed dataclass:
```
synthesis_state_present: bool
errors: list[str]
warnings: list[str]
passed: property -> bool  (True when len(errors) == 0)
```

When no synthesis state is present (no doctrine artifacts, no sidecars, no manifest), the function returns `synthesis_state_present=False` and an empty `errors` list — the legacy-bundle path is already handled gracefully.

**Rationale**: The helper already covers FR-001 through FR-004. No duplication needed.

**Alternatives considered**:

| Option | Rejected because |
|--------|-----------------|
| Re-implement checks inline in `charter_bundle.py` | Duplicates tested logic; divergence risk over time |
| New CLI subcommand for synthesis validation | Breaks the user model — `charter bundle validate` should be the single public gate |

---

### Public `charter bundle validate` command does not call the helper

`src/specify_cli/cli/commands/charter_bundle.py` has a `@app.command("validate")` with:
- `json_output: bool = typer.Option(False, "--json", ...)` parameter
- Human-readable output via Rich console
- JSON output via `sys.stdout.write(_json.dumps(report, indent=2) + "\n")`
- Does **not** currently call `validate_synthesis_state()`

**Gap (FR-001 to FR-004)**: The helper is never invoked. Synthesis-state failures silently pass.

**Gap (FR-005 to FR-006)**: The Rich console default is stdout. Any Rich output written before the `--json` branch executes leaks plain/formatted text to stdout. WP01 must audit and fix this.

---

### Existing test coverage

| File | Exists | What it covers |
|------|--------|----------------|
| `tests/charter/test_bundle_validate_cli.py` | Yes | CLI integration: JSON shape, missing tracked files, out-of-scope warnings |
| `tests/charter/synthesizer/test_bundle_validate_extension.py` | Yes | Direct unit tests of `validate_synthesis_state()` — does **not** go through the CLI |
| `tests/specify_cli/cli/commands/test_charter_status_provenance.py` | Yes | Bundle compatibility checks; provenance field validation through CLI |

**Decision**: New CLI regression tests (FR-008) extend `tests/charter/test_bundle_validate_cli.py`. The existing `test_bundle_validate_extension.py` exercises the helper in isolation; new tests must duplicate the same scenarios but invoke the public CLI surface.

**Rationale**: FR-008 explicitly requires the public CLI surface. Direct helper tests are not a substitute.

---

### JSON report extension strategy

**Decision**: Add a nested `synthesis_state` key; mirror blocking errors into the flat top-level `errors` list with a `"synthesis_state: "` prefix. See `contracts/validate-json-output.md` for the full shape.

**Rationale**: Confirmed by owner (DM-01KQFAPRVNBB7V1QWN1E4C2VJ7). This gives:
- Existing consumers: can keep using `passed` and `errors` without schema change
- New consumers: structured detail at `synthesis_state.present / passed / errors / warnings`
- CI gates: fail on `passed: false` without knowing the new schema
- Debuggers: can distinguish canonical bundle errors from synthesis/provenance-chain errors

**Alternatives considered**:

| Option | Rejected because |
|--------|-----------------|
| Flat merge into top-level `errors` only | No way to distinguish synthesis errors from manifest errors; worse for debuggers |
| Nested `synthesis_state` only | Breaks existing consumers relying solely on top-level `errors` |

---

### No new dependencies

All required logic (`validate_synthesis_state`, `BundleValidationResult`) is in `src/charter/bundle.py`. The integration requires only an import and a call. No new packages.
