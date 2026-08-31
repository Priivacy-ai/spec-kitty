# Research: CLI Bug Sweep & Tool Surface Self-Registration

Source: Debugger Debbie five-paradigm investigation, 2026-06-15.
All findings are evidence-based from source code at HEAD.

---

## IC-01: Stale xfail in test_distribution.py

**Decision**: Remove the decorator entirely. No change to `init.py`.

**Rationale**: The `--ai` guard at `src/specify_cli/cli/commands/init.py:617` (`if ai_assistant:`) is correct and complete. `multi_select_with_arrows` is unreachable when `--ai` is provided. The `--script` and `--mission` flags referenced in the xfail reason do not exist in the CLI. The `strict=False` with an incorrect reason provides zero regression protection.

**Alternatives considered**:
- Replace xfail with a skip: rejected — the test passes correctly; no skip is warranted.
- Update the xfail reason only: rejected — the stated failure mode no longer applies; keeping the decorator preserves the masking behavior.

**Residual risk**: If `ensure_runtime()` inside `init` is flaky in CI (due to absent global runtime state), the test will fail visibly after marker removal. This is a pre-existing latent issue; file a new issue if it manifests rather than restoring the xfail.

---

## IC-02: Branch naming pathological case

**Decision**: Add test; add docstring. No logic changes.

**Rationale**: `_human_slug_for_mid8_branch()` at `branch_naming.py:134–140` uses `endswith(f"-{mid8(mission_id)}")` to strip the embedded mid8 before re-appending. When the slug's embedded mid8 differs from `mission_id`'s mid8, the strip does not fire and the mid8 is appended twice. This is the documented pathological case. Production risk is low (slug mid8 is set from the mission's own ULID at creation and never mutated), but the behavior is untested.

**The five ad-hoc guard sites** (`coordination/workspace.py`, `coordination/transaction.py`, `coordination/status_transition.py`, `lanes/_read_path_resolver.py`) operate on filesystem path composition — a different artifact from branch names. They are correct and independent; do not consolidate them with the branch naming guard.

**Alternatives considered**:
- Reject mismatched mid8 with an error: deferred. The production case is theoretically impossible; an error would be overly defensive and break backwards compatibility for callers that pass `mission_id=None`.

---

## IC-03: Charter bundle validation

**Decision**: Three-part fix — git rm sidecars, fix `doctrine_kind_subdir()`, add `built_in_only` early-exit.

**Root cause**: Three interlocking defects:
1. `doctrine_kind_subdir()` in `src/charter/synthesizer/artifact_naming.py` maps kinds to plural dirs (`directives/`, `tactics/`, `styleguides/`) while `.gitignore` whitelists singular dirs (`directive/`, `tactic/`). Synthesized artifacts can never be committed under current structure.
2. 7 `adapter_id: fixture` sidecar placeholders were committed in commit `0b6e2d7d9` without corresponding generated artifacts.
3. `validate_synthesis_state()` early-exits only when artifact_files, provenance_files, AND manifest are ALL absent. The seeded `synthesis-manifest.yaml` (with `built_in_only: true`, `artifacts: []`) prevents the early-exit even in fresh-seed state.

**Validator call chain**: `CLI → validate_synthesis_state() → _check_provenance_have_artifacts() → _find_artifact()` which does `doctrine_root.rglob("*.directive.yaml")` — finds nothing because no plural-dir artifacts exist.

**Fix order**: (A) `git rm` sidecars first, then (B) fix `doctrine_kind_subdir()`, then (C) add early-exit. Parts B and C can be done in any order.

**Alternatives considered**:
- Change `.gitignore` to whitelist plural dirs: rejected. The existing tracked tree uses singular names; changing gitignore to accommodate the synthesizer's wrong output would commit generated artifacts that should stay gitignored.
- Remove only the sidecars (Fix A alone): insufficient. Any future `charter synthesize --apply` run would recreate the same failure class by writing to plural dirs.
- Fix only the validator early-exit (Fix C alone): masks the symptom without fixing the cause; leaves structurally ungittrackable synthesizer output.

**Callers of `doctrine_kind_subdir()` to audit**: `src/charter/synthesizer/write_pipeline.py` lines ~174, ~206, ~584. Any hardcoded plural-dir string in that file must also be updated.

---

## IC-04: Tool surface self-registration seam

**Decision**: Introduce `SurfaceRegistration` dataclass and `SurfaceProviderRegistry` class store; each provider declares its own registration; `service.py` derives all configuration from the store.

**Root cause**: `service.py` is a registration convergence point with four hand-maintained literal regions (imports, `_KIND_TOKENS`, `build_providers()`, `build_registry()`). All 7 providers touch all 4 regions. Parallel lane merges collide with probability ≈ 1.0.

**Model**: `MigrationRegistry.register` + `auto_discover_migrations` in `src/specify_cli/upgrade/`. Key difference: discovery must use an explicit import tuple (not pkgutil) to satisfy the dead-symbol static analysis gate.

**`SurfaceRegistration` required fields** (from full provider enumeration):

| Field | Type | Required by |
|-------|------|-------------|
| `provider_class` | `type[ReportingSurfaceProvider]` | all providers |
| `definitions` | `tuple[SurfaceDefinition, ...]` | all; `session_presence` has 3, others have 1 |
| `kind_tokens` | `dict[str, SurfaceKind]` | all; includes hyphen+underscore aliases |
| `synthetic_key` | `str \| None` | `plugin_bundle` uses `PLUGIN_BUNDLE_TOOL_KEY`; others use `None` |
| `order` | `int` | all; explicit integer for deterministic ordering (FR-010) |

**Circular import**: `plugin_bundle.py` has a lazy import of `build_plans_for_bundles` from `service.py` inside a method body. Preserve this workaround unchanged. Do not attempt to resolve the cycle as part of this mission.

**`_BUNDLE_SOURCE_TOOL_KEYS`** (`("codex", "claude", "copilot", "vibe")`): This is a projection scope filter, not a provider identity. It remains as a module-level constant in `service.py` — not part of `SurfaceRegistration`.

**Directive-030 conformance test assertions**:
1. Every non-underscore module in `src/specify_cli/tool_surface/providers/` has a corresponding entry in `SurfaceProviderRegistry._registrations`.
2. `service.py` source contains no patterns matching the central provider literal forms (e.g., no `build_providers` inner list literals, no `_KIND_TOKENS = {` dict literal).

**Alternatives considered**:
- Alphabetize lists in `service.py`: rejected. Ordering doesn't prevent parallel authors from editing the same lines.
- `import *` from providers: rejected. Fails ruff F403/F405 and mypy; still requires central literals.
- pkgutil filesystem scan: rejected. Violates dead-symbol gate (C-001).
