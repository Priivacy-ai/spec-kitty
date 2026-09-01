# Canonical Operator Surface Map — M2 `charter-code-topology` (FROZEN, pre-edit)

**Status**: Awaiting operator approval. **No source edit may land until this is approved** (FR-001 / US1; the mission's one bounded design question). Frozen against merged `main` `22882d72b0` (M1 + landing pass).

**Set-equality basis (census on the frozen base):** `src/doctrine` = 265 tracked files (96 `.py`); `src/charter` = 113 `.py`; **456** files import the top-level `doctrine` package (53 in `src/charter`, 158 edges); **`specify_cli.doctrine*` / `doctrine_synthesizer` / `org_charter` = 84 imports EXCLUDED** (separate package). The closing audit re-derives this set on the same base; every row below must be set-equal to it.

## MAP-000 — module partition (whole-package relocate + activation split)

- **`src/doctrine/**` → `src/charter/offering/**`** (whole-package `git mv`; all 96 `.py` + 169 data files). The offer catalogue.
- **`src/charter/` activation code → `src/charter/activation/`**: `activation_engine.py`, `_activation_render.py`, `activations.py`, `cascade.py`, `kind_vocabulary.py`, `pack_manager.py`, `pack_context.py`, `compiler.py`, `context*.py`, `synthesizer/**`, `interview.py`, `sync.py`, `default_pack.py`, `drg.py`, `scope*.py`, `org_*.py`, the `resolver.py` wrapper, `exceptions.py` (`CharterActivationError`), `schemas.py` (charter-extraction `Directive`).
- **Boundary (C-004, hard exit)**: `charter.offering` MUST NOT import `charter.activation`; `activation` MAY import `offering`. Enforced by MAP-GATE below.
- **MAP-NOTE-1**: `doctrine/spdd_reasons/activation.py` → `offering/spdd_reasons/activation.py` (offer-side read-only predicate; the name is a trap — do NOT file into `activation/`).

## MAP-COLLISION — per-name disposition (existing `src/charter` vs relocated `offering`)

| MAP | Name | Disposition | Target |
|-----|------|-------------|--------|
| MAP-C01 | `pack_paths.py` | **collapse-facade** | real → `offering/pack_paths.py`; `charter/pack_paths.py` → top-level `charter.*` CR-06 shim |
| MAP-C02 | `provenance.py` | collapse-facade | real → `offering/provenance.py`; facade → CR-06 shim (NB `charter/synthesizer/provenance.py` is unrelated activation code — keep) |
| MAP-C03 | `template_catalog.py` | collapse-facade | real → `offering/template_catalog.py`; facade → CR-06 shim |
| MAP-C04 | `versioning.py` | collapse-facade | real → `offering/versioning.py`; facade → CR-06 shim |
| MAP-C05 | `primitives.py` | collapse-facade | `doctrine/missions/primitives.py` → `offering/missions/primitives.py`; `charter/primitives.py` → CR-06 shim |
| MAP-C06 | `resolver.py` / `DoctrineService` | **relocate-both-distinct — NEVER merge** | offer 6-tier → `offering/resolver.py`; activation wrapper → `activation/resolver.py` |
| MAP-C07 | `exceptions.py` | relocate-both-distinct | `offering/shared/exceptions.py` + `activation/exceptions.py` |
| MAP-C08 | `errors.py` | relocate-both-distinct | `offering/shared/errors.py` + `activation/synthesizer/errors.py` (already distinct subpkgs) |
| MAP-C09 | symbol `Directive` | relocate-both-distinct | offer artifact `offering/directives/models.py` + charter-extraction `activation/schemas.py` |
| MAP-C10 | `canonical_yaml` | **de-dup fold** | SSOT → `offering/yaml_utils.py`; fold `synthesizer/synthesize_pipeline.py:157` duplicate to delegate |
| MAP-C11 | `__init__.py` (×17) | role-split relocate | doctrine inits → `offering/**`; `charter/__init__.py` stays as parent of both sub-modules |
| MAP-C12 | facade placement rule | **all 5 collapsed facades live at top-level `charter.*`, NOT inside `offering/` or `activation/`** — else a manufactured `offering→activation` edge |

## MAP-GATE — architectural gates

- **NEW** `test_charter_offering_does_not_import_activation` (hard M2 exit, not CR-budgeted): copy `tests/architectural/test_charter_no_specify_cli_import.py`; **add level-aware `ast.ImportFrom` resolution** (catch relative `from ..activation import X`) + a `tmp_path` non-vacuity case for the relative form.
- **RE-HOME** `conftest.py:89` landscape (drop `doctrine` node), `test_layer_rules.py` `_DEFINED_LAYERS`, `test_kernel_no_doctrine_import.py` `_FORBIDDEN_IMPORT_ROOTS` (doctrine→charter) — **retarget** the 2 `kernel/schema_utils.py:88,96` exemptions, never delete.

## MAP-CR — serialized-surface compat shims (each replicates CR-01 `src/charter/sync.py:278-311`)

| CR | Surface | Target word | Key sites | Guard |
|----|---------|-------------|-----------|-------|
| CR-02 | `spec-kitty doctrine` CLI group | `charter` | `cli/commands/__init__.py:258,293`, `doctrine.py:60,67,74,81,87` | `deprecated=True` + callback stderr warn. **Do NOT fold `doctrine mission-type` (activation-blind) into `charter mission-type` (activation-filtered)** — add `--include-inactive` or a distinct home |
| CR-03 | tracker mode/block | **`ownership`** (≠charter!) | `tracker/config.py:125-126,176-178,192,200-209`, `tracker.py:422,624-626,720-721,899`, `saas_service.py` | dual-key reader; `--doctrine-mode` hidden alias; machine-status payload = downstream contract |
| CR-04 | `.kittify/config.yaml` `doctrine.org.packs` | `charter_packs` | `org_pack_config.py:~573,462-485` | 3rd shape: charter_packs → doctrine.org → legacy organisation_packs |
| CR-05 | URN `doctrine:<kind>:<id>` | `charter:` | producer `doctrine_synthesizer/apply.py:409,663` ONLY | NOT `drg/merge.py:596`/`models.py:378`; event validators accept both; external `spec_kitty_events` fixture = paired change |
| CR-06 | `import doctrine` module surface | `charter.offering` | 36 module-form sites (budget 8 = module names) | `runtime/next/__init__.py:15-28` `__getattr__` + `retrospective/deprecation.py` warn-once + `test_charter_facades_reexport_doctrine.py` identity guard; register `compat/shim-registry.yaml` |
| CR-07 | `.kittify/doctrine/` path literals | `charter-packs` | 42 src files + **split-literals** `apply.py:187` `_DOCTRINE_BASE`, `write_pipeline.py:62`/`reconcile.py:67` `_DOCTRINE_DIRNAME` | dual-root reader; **normalize split-literals FIRST** (census-invisible) |

## MAP-BUILD — packaging / wheel / CI

- `pyproject.toml`: `:149` packages (drop `src/doctrine`), `:152-163` exclude, **`:178-186` artifacts — WIDEN `src/charter/**` globs to `.md/.json/.csv/.template`** (R2 wheel silent-drop — currently `*.yaml` only), `:201-210` sdist, `:488` fixture copy.
- `release.yml:210-245` payload counts → `src/charter`; skill counts (`:226,229`) → relocated skills tree.
- **Dormant `spec-kitty-doctrine` wheel → DELETE** (`src/doctrine/pyproject.toml` + `hatch_build.py` + `tests/doctrine/test_hatch_build.py` + `test_doctrine_wheel_closure.py`) — never built/published (#3101 is a separate deferred decision).
- 13 `files("doctrine")` resource sites + `kernel/schema_utils.py:22` + `kernel/sibling_paths.py:45` retargeted **before** the CR-06 shim lands.
- Skills tree `src/doctrine/skills/` (55 dirs/83 files, OC-41) = pure `git mv` + `registry.py:44,59-61,67` retargets; IDs stay (→ M4).

## MAP-EXCLUDE (do NOT touch)

`specify_cli.doctrine`, `specify_cli.doctrine_synthesizer`, `specify_cli.doctrine_service_factory`, `specify_cli.org_charter` — a separate package (84 imports). `drg/merge.py`/`models.py` 2-part node URN space (CR-05 is the 3-part synthesizer URN only). `packs/built-in/**` data move (that's `relocate-builtin-doctrine-packs`). Data under `.kittify/doctrine/` (M3 moves it; M2 only introduces the CR-07 reader).

---

**Approval requested:** the module partition (MAP-000), the 12 collision dispositions (MAP-C01…C12), the 6 CR shim targets (note tracker→`ownership`, not `charter`), and the delete-not-rename call on the dormant wheel. On approval, S1 (skeleton + gate + layer re-home) begins; the first `git mv` is S2.
