# Phase 0 Research — Charter Ownership Consolidation and Neutrality Hardening

**Mission**: `01KPD880` · **Phase**: 0 (Outline & Research)

Every research item below was pre-empted by a baseline inventory of the two charter packages, a pre-mortem risk scan across six silent-breakage categories, and a short deliberation on banned-term and deprecation-warning mechanics. No `NEEDS CLARIFICATION` markers survive into Phase 1.

Each entry follows the standard Decision / Rationale / Alternatives structure, with the evidence that grounds the decision.

---

## R-001 — Baseline inventory of charter package surfaces

**Decision**: Treat `src/charter/` as the already-canonical implementation owner (18 modules). Treat the 4 files under `src/specify_cli/charter/` as pure deprecation shims to be kept and annotated, **not** reimplemented or rearchitected.

**Rationale**: The inventory confirmed both hard-success-criterion functions already have exactly one definition each:

- `build_charter_context()` — defined at `src/charter/context.py:67`; all other occurrences are re-exports or callers.
- `ensure_charter_bundle_fresh()` — defined at `src/charter/sync.py:66`; same pattern.

All 4 files under `src/specify_cli/charter/` are pure shims: `__init__.py` (108 lines of re-exports), and `compiler.py` / `interview.py` / `resolver.py` (9 lines each, using the `sys.modules` aliasing trick to redirect fully-qualified imports of the legacy submodule path to the canonical module). No real implementation survives in the legacy surface.

**Alternatives considered**:

- *Total deletion of `src/specify_cli/charter/`.* Rejected because the user explicitly chose option (C) hybrid-with-sunset in specify discovery — some plausible external importer may rely on the legacy path, and a DeprecationWarning cycle is the respectful migration.
- *Rewrite `charter/` from scratch.* Rejected on sight — baseline is healthy.

**Evidence**: Inventory report dated 2026-04-17; see the user-facing Agent summary in the plan conversation and the module list captured in plan.md under Project Structure.

---

## R-002 — Pre-mortem sweep of silent-breakage categories

**Decision**: The six high-risk categories identified during planning are all either empty or accounted for. Only two real migrations remain.

**Rationale**: Grep + content scan across the repo yielded the following hit distribution for patterns that could survive a naive import-path rewrite:

| Category | Hits | Risk level | Action |
|---|---|---|---|
| Dynamic imports (`importlib.import_module("specify_cli.charter…")`) | 0 | None | None |
| Entry points / package metadata in `pyproject.toml` / `setup.cfg` | 0 | None | None |
| `[[tool.mypy.overrides]]` "Transitional quarantine" entries | 1 (`specify_cli.charter.context` at `pyproject.toml:218`) | Medium (typing-scope, not runtime) | See below — a typing-scope change, not cosmetic cleanup. |
| String-based module paths in YAML/JSON doctrine | 0 | None | None |
| Test-time mocks (`mock.patch("specify_cli.charter…")`) | 2 intentional C-005 fixtures (see R-007) | Zero if preserved, **high** if naively rewritten | Treat as occurrence-map exceptions; see R-007. |
| Agent profile / skill pack Python-path references | 0 | None | None |
| Documentation teaching `from specify_cli.charter …` | 0 | None | None |
| **Actual callers to migrate** (`from specify_cli.charter …`) | 28 | Tractable (minus C-005 exceptions) | Rename in place during implementation, excluding three intentional legacy-import test files. See R-007 and `occurrence_map.yaml`. |

**On the `pyproject.toml` entry**: the hit at `pyproject.toml:218` is inside a `[[tool.mypy.overrides]]` block explicitly labelled "Transitional quarantine" that relaxes mypy strictness for legacy modules. It is NOT a package-inclusion or entry-point reference — those have no such entry. The `specify_cli.charter.context` submodule path it names **never existed as a real submodule shim** (there is no `src/specify_cli/charter/context.py`), so the quarantine entry is effectively stale today. Removing it is a **typing-scope change**: dropping the override may surface previously-suppressed `mypy --strict` errors against the canonical `charter.context` module. Planning therefore treats this as an explicit task (run `mypy --strict src/charter/context.py`, fix any newly-visible errors, then delete the override line or migrate it to `charter.context` if errors cannot be fixed in this mission's scope).

**Alternatives considered**:

- *Skip the pyproject.toml edit.* Rejected — the stale quarantine entry teaches future contributors that `specify_cli.charter.context` is a thing they can import, which it is not, and lets mypy regressions hide under a legacy override that does nothing useful.
- *Delete the quarantine line blindly without running mypy.* Rejected — if newly-visible strict errors exist, landing a mission that fails `mypy --strict` is a regression against the mission's own gates (see plan.md Charter Check).
- *Build string-scanning regression tests for each pre-mortem category.* Rejected for this mission as scope creep; the empty result sets make lint-level tripwires unnecessary. Reintroduction can be spec'd later if a regression is ever observed.

**Evidence**: Same inventory pass as R-001.

---

## R-003 — Banned-term list design

**Decision**: Ship an initial banned-terms YAML with both literal and regex entries, keyed by a human-readable id and category. Contributors can extend by editing a single file.

**Initial term set** (subject to Phase 1 schema; the final authoritative list ships in `src/charter/neutrality/banned_terms.yaml`). The initial list is deliberately **narrow** — only the four highest-signal Python-bias tokens that do not collide with legitimate multi-ecosystem vocabulary:

| ID | Kind | Pattern | Rationale |
|---|---|---|---|
| PY-001 | literal | `pytest` | Primary offender in pre-3.1.5 prompts. Unambiguously Python-specific. |
| PY-002 | literal | `junit` | Python-ecosystem reporter name (pytest-junit, junit.xml). Unambiguously Python-test-ecosystem. |
| PY-003 | regex | `\bpip install\b` | Concrete Python install command. |
| PY-004 | regex | `\bpython -m\b` | Python module execution command. |

**Terms dropped after a grep pass against generic templates**: earlier draft candidates `pytest.ini`, `pyproject.toml`, `\b\w+\.py\b`, and `conftest.py` were removed because a content audit of generic-scoped templates (e.g., `src/specify_cli/missions/*/command-templates/*.md`) showed `pyproject.toml` appearing in multi-ecosystem file enumerations alongside `package.json`, `go.mod`, `Cargo.toml`, and `.py` as a suffix appearing in discussions of "language files" next to `.ts`, `.go`, `.rs`. Banning those tokens would fire false positives on content that is *already* ecosystem-neutral. The neutrality lint can be extended later with a deliberate rationale if a specific regression surfaces.

**Rationale**: The pattern set is scoped to bias classes actually observed in pre-3.1.5 artifacts, while excluding tokens that already appear in ecosystem-neutral enumerations. Keeping it editable in a single file honours FR-014 and NFR-006.

**Alternatives considered**:

- *Phrase-level or AST-based analysis.* Rejected — out of scope (C-003, no schema redesign) and unnecessary given the narrow shape of historical regressions.
- *Schema-level `scope:` field on artifacts.* Same rationale as R-003 alternative above; deferred to a future mission if/when schema redesign is in scope.
- *Separate files per term class (Python/Node/Ruby).* Rejected for v1 — YAML with a `categories` or `languages` field already supports multi-language ingress. The initial term list is all Python-scoped; adding terms for future languages does not require a new file.

---

## R-004 — Shim sunset release policy

**Decision**: Single-minor deprecation window. Shims ship deprecated in the release that lands this mission (tentatively 3.2.0 based on current versioning cadence); removal is targeted for the following minor (tentatively 3.3.0).

**Rationale**: Matches user direction (Q1 answer (i)) and is concrete enough to drive changelog and migration-guide wording. Shim overhead is trivial (135 total lines, zero runtime cost once imports resolve), so the window can be short without operational pain.

**Alternatives considered**: (ii) two-minor window, (iii) policy-based-no-target, (iv) immediate deletion — all rejected per user decision in planning Q1.

**Artifact impact**: `CHANGELOG.md` entry for landing release names the removal target release. Removal ships as a separate small PR against 3.3.0 and is not in scope of this mission.

---

## R-005 — DeprecationWarning emission from `sys.modules`-aliasing shims

**Decision**: Emit `DeprecationWarning` at shim load time (module body execution) via `warnings.warn(..., DeprecationWarning, stacklevel=2)`. The warning names the canonical replacement import and the target removal release. Existing tests that import through the legacy path get updated to assert the warning via `pytest.warns(DeprecationWarning)`.

**Rationale**:

- `stacklevel=2` points the warning at the *caller* of the legacy import (e.g., `some_test.py`), which is the signal contributors need to update their imports.
- Warning fires once per import chain (Python's warning filters dedup by (category, module, lineno)) — no per-call noise.
- The three `sys.modules` aliasing files currently execute `sys.modules[__name__] = sys.modules["charter.X"]` at module top-level; the warning emits immediately before the alias. For `__init__.py`, which does straight re-exports, the warning emits at module top-level before any re-export.
- FR-005 is satisfied: every surviving shim emits a catchable `DeprecationWarning` that names the canonical path and removal release.

**Alternatives considered**:

- *Module-level `__getattr__` (PEP 562) for lazy warnings.* Rejected because the `sys.modules` aliasing trick replaces the module object, so `__getattr__` on the original module is never consulted.
- *Emit at first attribute access rather than import.* Rejected — the import itself is the event a contributor should be notified about; attribute access is too late for the import-discovery UX.
- *Use `FutureWarning` or `PendingDeprecationWarning`.* Rejected — `DeprecationWarning` is the idiomatic choice for scheduled removal; FutureWarning is for user-facing behavior changes (this is developer-facing import API) and PendingDeprecationWarning is silenced by default.

---

## R-006 — CI integration of neutrality lint

**Decision**: Implement as a regular pytest module under `tests/charter/test_neutrality_lint.py`. It runs as part of the standard pytest invocation that CI already executes; no separate CI job needed.

**Rationale**:

- NFR-001 bounds the lint at ≤ 5 seconds on typical dev hardware; amortized into the existing pytest run, the impact is imperceptible.
- Keeping it as a pytest module gives contributors a familiar "run the tests" mental model and produces a diagnostic error message via pytest's standard output formatting.
- No pre-commit hook requirement was stated; adding one is orthogonal and can be introduced later without re-speccing.

**Alternatives considered**:

- *Standalone CLI lint.* Rejected as redundant; would duplicate pytest's collection and reporting infrastructure.
- *Pre-commit hook.* Rejected for this mission; it restricts contributors without a clear win over CI-side enforcement. Optional follow-on.
- *Separate GitHub Actions workflow.* Rejected — adds CI minutes and a new surface to maintain for a test that takes under 5 seconds.

---

## R-007 — Preservation of C-005 compatibility tests

**Decision**: Exempt three test files from the global `tests_fixtures: rename` action. They import the legacy `specify_cli.charter.*` surface **by design** to prove the deprecation window actually works. Rewriting them would destroy the coverage that makes C-005 verifiable.

**Files exempted** (`occurrence_map.yaml` exceptions):

- `tests/specify_cli/charter/test_defaults_unit.py` — imports from `specify_cli.charter.compiler`, `specify_cli.charter.interview`, `specify_cli.charter.resolver`; uses `monkeypatch.setattr("specify_cli.charter.interview...")`. The legacy import surface is the subject under test.
- `tests/charter/test_sync_paths.py` — `test_sync_shim_re_exports_canonical_sync` literally asserts that `from specify_cli.charter import sync` still resolves. The comment on the import line reads `# C-005: shim must re-export sync callable`.
- `tests/charter/test_chokepoint_coverage.py` — exercises the legacy import chokepoint to verify shim re-exports remain intact.

**Rationale**: A naive category-level rewrite of `tests_fixtures: rename` would convert every `from specify_cli.charter import X` into `from charter import X`, at which point these tests would no longer test what their names claim. The correct classification is `do_not_change` for these three specific paths, while `tests_fixtures: rename` remains the correct default for other test files that incidentally import through the legacy path.

**Alternatives considered**:

- *Recategorize all of `tests_fixtures` as `manual_review`.* Rejected as over-broad — most test-file migrations are truly mechanical. Per-path exceptions are more precise and leave the happy path automatic.
- *Delete the three compatibility tests and rely on the shim-deprecation contract alone.* Rejected — the shim-deprecation contract (C-2) proves `DeprecationWarning` emission but does not prove every re-exported symbol still resolves through the legacy path. The compatibility tests catch re-export regressions (a shim silently dropping a symbol) that a warning-only test would miss.

**Evidence**: File content inspection 2026-04-17 (`tests/specify_cli/charter/test_defaults_unit.py:9-15, 37, 55, 69, 84, 88`; `tests/charter/test_sync_paths.py:17, 34-38`).

---

## R-008 — mypy quarantine removal and `mypy --strict` implications

**Decision**: Treat removal of the `specify_cli.charter.context` entry from the `[[tool.mypy.overrides]]` "Transitional quarantine" block (`pyproject.toml:218`) as a typing-scope change. Run `mypy --strict src/charter/context.py` before deleting the override; fix any newly-visible strict errors as part of this mission or (if out of scope) migrate the override to target the real module (`charter.context`) with a `# TODO: remove in mission NNN` comment.

**Rationale**: The quarantine block's stated purpose is to relax strictness for legacy modules. The specific entry `specify_cli.charter.context` does not correspond to any real file — there is no `src/specify_cli/charter/context.py`. Meanwhile, the canonical `src/charter/context.py` is in scope for `mypy --strict` per the Charter Check. Removing the stale entry exposes nothing (no module has been matching it). What it *does* expose is the question "is `charter.context` actually strict-clean today?" — which must be answered with a real run before the line disappears, because the stale entry's mere presence has been camouflaging that question for some time.

**Alternatives considered**:

- *Delete the line without running mypy.* Rejected — the gate is `mypy --strict passes`. Landing without running the check would be a regression against the mission's own Charter Check.
- *Leave the stale entry in place.* Rejected — leaving it teaches future contributors the legacy path is a live submodule (it is not), and makes the quarantine block noisier than it needs to be.
- *Rename the entry to `charter.context`.* Defensible as a fallback if strict errors exist and cannot be fixed in this mission. Preferred outcome is still deletion; the rename is only a compromise.

**Evidence**: Inspection of `pyproject.toml:218-240` (the `[[tool.mypy.overrides]]` block) and `src/specify_cli/charter/` directory (no `context.py` file exists there).

---

## Premortem — "how could this mission still silently break things?"

Applying the `premortem-risk-identification` planning tactic from the charter context, the residual failure modes worth guarding against are:

1. **A contributor adds a NEW module under `src/specify_cli/charter/` that is NOT a shim.** Mitigation: add a test at `tests/specify_cli/charter/test_no_new_legacy_modules.py` that fails if any file under `src/specify_cli/charter/` is > N lines (say 50) OR contains a `class …` or non-re-export `def …`. Captured as a task in Phase 2.
2. **A contributor re-introduces `build_charter_context()` or `ensure_charter_bundle_fresh()` as a shadow definition anywhere in the repo.** Mitigation: `tests/charter/test_charter_ownership_invariant.py` uses `ast` to scan for `FunctionDef` nodes with those names anywhere under `src/` and fails if count > 1 per name.
3. **A contributor adds a new generic-scoped doctrine file whose filename or content accidentally matches a banned term.** Mitigation: the neutrality lint + allowlist registration flow forces an explicit contributor decision on ingress.
4. **A surviving shim emits its DeprecationWarning only in non-common import paths.** Mitigation: the shim-deprecation test imports the legacy path from a fresh Python process and asserts the warning emitted.

All four residual risks have concrete task mitigations folded into the Phase 2 plan (the `/spec-kitty.tasks` command will materialize these).

---

## Open questions surviving Phase 0

**None.** All `NEEDS CLARIFICATION` markers are resolved. Phase 1 proceeds.
