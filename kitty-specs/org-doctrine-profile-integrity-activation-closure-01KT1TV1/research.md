# Research: Org Doctrine Profile Integrity Activation Closure

This document captures the issue-derived research and architectural decisions for the mission. It intentionally pulls the relevant context from #1111, #1557, #1583, and #1584 so planning can proceed without reopening the issue threads.

---

## Source Issue Context

### #1111 - Release epic context

The parent epic tracks 3.2.0 charter/doctrine launch work. Most original launch-blocker slices are now closed, including lifecycle freshness, shipped DRG freshness, git policy, dashboard glossary resilience, organisation-layer DRG, monorepo charter visibility, composable workflow sequencing, and external governance references.

The remaining release-relevant work is concentrated in the charter activation and org-pack correctness path:

- #1557: complete deferred charter activation behavior from PR #1535.
- #1583: add a proper DRG relation for profile inheritance.
- #1584: make invalid org-pack profiles visible to repositories and diagnostics.

### #1557 - Charter activation follow-on

PR #1535 shipped the activation surface across nine doctrine artifact kinds, default pack support, consistency checks, and lifecycle gates. It deliberately deferred:

- cascade activation and deactivation,
- artifact ID validation on `charter activate`,
- production wiring for OperationalContext,
- cleanup items from adversarial review.

The issue records the concrete gap: `--cascade` is parsed but does not perform scoped graph traversal; no-cascade warning behavior is inverted or incomplete; invalid activation IDs can be written to config; OperationalContext exists but returns empty values and has no production call sites.

### #1583 - DRG profile lineage relation

Org doctrine packs need to express that an agent profile specializes another profile. The example motivating this mission is a domain-specific data-model analyst profile that inherits from a built-in analyst profile.

The current DRG relation vocabulary does not include a structural lineage relation. `delegates_to` is semantically wrong because it means runtime work handoff, not inheritance. `enhances` is less wrong but still imprecise. This forces org packs into lossy mappings and risks corrupting graph traversal semantics.

Decision needed: add `specializes_from` or a more general `extends` relation. The mission defaults to `specializes_from` because it matches the existing agent profile field and is precise for the immediate use case.

### #1584 - Profile load diagnostics

During rc30 to rc32 upgrade, org-pack agent profiles using now-disallowed `context-sources` keys failed validation. The loaded profile list was shorter, while the caller had no retained diagnostic path after construction. This made `doctor doctrine` appear healthy when only DRG counts were considered.

The observed failure mode is not simply "no warning ever exists"; repository construction may emit transient warnings. The durable problem is that consumers of `list_all()` cannot discover what was skipped unless they independently glob the pack directory and diff against returned IDs.

Decision needed: retain structured load diagnostics in the repository and expose them to doctor output.

---

## R-001 - Relation Name for Profile Lineage

**Decision**: Add `specializes_from` as the first-class DRG relation for agent profile lineage.

**Rationale**:

- The agent profile schema already uses `specializes_from`, so the graph relation matches the domain language users see in profile YAML.
- It avoids overloading `delegates_to`, which remains runtime work handoff.
- It is more precise than `enhances`, which does not imply inheritance or lineage.

**Alternative considered**: `extends`.

`extends` is more general and could apply to tactics or paradigms later. It is not chosen for this mission because no current issue requires cross-kind extension semantics, and broadening the term now would invite unplanned graph behavior. Future work may add `extends` separately or alias it after a research mission.

**Consequences**:

- DRG fixtures and validation tests must include at least one profile-to-profile `specializes_from` edge.
- Delegation traversal tests must prove lineage edges are not interpreted as runtime handoff.

---

## R-002 - Invalid Profile Handling Model

**Decision**: Keep `list_all()` valid-only, and add a durable diagnostic surface for skipped profiles.

**Rationale**:

- Returning invalid profiles as degraded objects would require a new runtime contract: can they be listed, assigned, activated, or rendered? That is too broad for a release-closure mission.
- Valid-only `list_all()` preserves existing callers.
- A diagnostic API makes invisible loss observable without letting invalid profiles enter runtime selection.

**Expected diagnostic fields**:

- `layer`: one of built-in, org, project.
- `path`: repository-relative or absolute path suitable for operator action.
- `profile_id`: parsed ID when present before validation fails; otherwise null.
- `error`: concise validation or parse error summary.

**Consequences**:

- Doctor can present a pack as degraded even when valid profiles and graph counts exist.
- Activation validation can distinguish "unknown ID" from "known file failed to load" when feasible.

---

## R-003 - Doctor Doctrine Health Semantics

**Decision**: `doctor doctrine` should surface invalid profile diagnostics in both human and JSON output, but it should remain a diagnostic command rather than a hard gate.

**Rationale**:

- The existing command is documented as a diagnostic with exit code 0. Changing exit behavior would be a bigger operator contract change.
- Human output must still make the degraded state visible.
- JSON output gives automation a stable way to fail CI if a project chooses to gate on invalid profiles.

**Consequences**:

- Tests should assert JSON fields, not only formatted text.
- Human output can evolve, but it must contain pack/layer/path/error enough for action.

---

## R-004 - Activation Validation Before Mutation

**Decision**: All activation commands that take an artifact ID validate the ID before writing activation state.

**Rationale**:

- #1557 shows current behavior can write arbitrary strings into config.
- Once invalid profiles are observable, the user should get a clearer result: unknown ID, invalid profile, or inactive dependency.
- Non-mutating failure is required to keep activation state trustworthy.

**Consequences**:

- Tests must compare config bytes before and after a failing activation.
- Error messages should point to `charter list --show-available` or `doctor doctrine` depending on failure type.

---

## R-005 - Cascade Semantics

**Decision**: Preserve explicit cascade scope from CLI to service and use graph/catalog references to determine cascade targets.

**Rationale**:

- #1557 records that collapsing `--cascade agent-profile,tactic` to boolean loses the user's requested scope.
- Cascade must be deterministic and auditable. Operators should know exactly what was activated, skipped by scope, deactivated, or skipped because it is shared.

**Consequences**:

- `--cascade all` is explicit; absence of `--cascade` never means all.
- Deactivation requires shared-reference analysis before mutation.

---

## R-006 - OperationalContext Scope

**Decision**: Wire OperationalContext only where this mission already needs it: work package claim/review lifecycle and `next` runtime decision boundaries.

**Rationale**:

- #1557 explicitly says OperationalContext is specced but not wired.
- A full retrofit across every context-aware resolver is larger than this release-closure slice.
- Populating it at the entry points removes the dead extension point and gives later context-aware activation work a stable carrier.

**Consequences**:

- Guard methods must be tested with real production-like context, not all-None stubs.
- Dead-symbol allowlist entries should be removed once call sites exist.

---

## R-007 - Agent Profile Context Selector Reachability

**Decision**: Make `charter context --include agent-profile:<id>` work by normalizing hyphenated selector kinds to their canonical doctrine kind before dispatch, and advertise the kind in help.

**Observed gap**:

- `build_charter_context_include()` (`src/charter/context.py`) lowercases the kind but does not convert hyphens to underscores. `_render_doctrine_artifact_include()` keys its renderer table on `agent_profile` (underscore), while every user-facing surface (e.g. `charter activate`) documents and accepts the hyphenated `agent-profile`.
- The result is that `--include agent-profile:<id>` raises `Unsupported --include selector kind 'agent-profile'`, even though the renderer for `agent_profile` exists. Operators currently reach profiles only via the Python API (`DoctrineService.agent_profiles`) or by reading the profile YAML directly.
- The `--include` help text lists `directive|styleguide|section` but never mentions agent profiles, so the capability is undiscoverable even in its working underscore form.

**Rationale**: The fix is a normalization + discoverability gap, not a new renderer. A single hyphen->underscore normalization of the selector kind aligns `--include` with the activation verbs and unblocks the documented `agent-profile` form (and `mission-step-contract`) without changing activation semantics.

**Consequences**:

- Add CLI coverage asserting human and `--json` rendering for `--include agent-profile:<id>`.
- Confirm normalization does not regress existing underscore/lowercase selectors.

---

## R-008 - Charter Catalog Completeness (`charter list --all`)

**Decision**: Add `charter list --all` that lists every available artifact per kind across built-in, org-pack, and project layers, and extend `CharterPackManager.list_available()` to include non-built-in artifacts.

**Observed gap**:

- `charter list` exposes only `--show-available`. Its availability source, `CharterPackManager.list_available()` (`src/charter/pack_manager.py`), scans only the built-in doctrine filesystem; the `ctx` parameter is explicitly ignored ("reserved for future org-pack support").
- Packaged artifacts (org-pack, project) are therefore invisible in the catalog, so an operator cannot see the full set of artifacts they could activate.

**Rationale**: This mission already makes org-pack profile state trustworthy (FR-005..FR-010) and validates activation IDs against the active catalog (FR-011). A catalog listing that silently omits the same packaged artifacts is inconsistent with that catalog-integrity goal. `--all` gives operators the complete activatable surface, annotated by source layer.

**Consequences**:

- `list_available()` must resolve org/project roots (reusing the same resolution used by activation validation) and annotate source layer.
- `--all` implies and supersedes `--show-available`; tests cover a fixture pack so non-built-in artifacts appear with their layer.

---

## R-009 - Refactoring & Cleanup Opportunities (do these first)

A critical read of the code paths behind FR-022..FR-026 shows the new findings are **symptoms of kind-vocabulary fragmentation**, not isolated bugs. Doing the small consolidation below first turns each FR into a one-line dispatch change instead of another special-case patch, and prevents the same gaps reappearing for sibling kinds (e.g. `mission-step-contract`).

### Observed state: one concept, five tables, three spellings

The set of doctrine artifact kinds is declared independently in at least five places, in three incompatible spellings:

| Location | Spelling | Shape | Used by |
|----------|----------|-------|---------|
| `doctrine/artifact_kinds.py` `ArtifactKind` (`_PLURALS`, `_PATTERNS`) | underscore singular (`agent_profile`) | **canonical** enum + plural + glob | doctrine layer (zero-dependency) |
| `charter/activations.py` `_SINGULAR_TO_PLURAL_KIND` / `normalize_artifact_kind()` | underscore singular -> plural | singular->plural map | activation registry resolution |
| `charter/pack_manager.py` `YAML_KEY_MAP` | **hyphen** (`agent-profile`, `mission-type`) | CLI token -> config YAML key | `charter activate` / `deactivate` |
| `charter/pack_manager.py` `_KIND_TO_DOCTRINE_DIR` | **hyphen** | CLI token -> (built-in dir, suffix) | `list_available()` |
| `cli/commands/charter/list_cmd.py` `_KIND_ORDER` | **hyphen** | display order | `charter list` |
| `charter/context.py` renderers dict + `_render_generic_artifact_include` candidate tuple | underscore singular | kind -> (service attr, label, renderer) | `charter context --include` |

`_PLURALS` (artifact_kinds) and `_SINGULAR_TO_PLURAL_KIND` (activations) are byte-for-byte the same data. `_PATTERNS` (artifact_kinds) equals the suffix column of `_KIND_TO_DOCTRINE_DIR`. None of the charter tables reference `ArtifactKind`.

### Root cause of FR-022 / FR-023

`charter context --include` (`build_charter_context_include`) lowercases the kind but applies **no hyphen->underscore normalization**, and its renderer table is keyed on the underscore form. Operators type the hyphenated `agent-profile` (the form `charter activate` documents and accepts), so it falls through to `Unsupported --include selector kind`. Note the existing `normalize_artifact_kind()` would **not** fix this either: it only maps singular->plural, not hyphen->underscore. So the canonical normalizer is itself incomplete for the operator token.

### Recommended cleanups (sequence before the FR work)

- **CL-1 — One operator-token normalizer.** Extend the canonical kind layer (preferably `doctrine.artifact_kinds`, with a thin `from_operator_token()` / hyphen-aware accessor) so a single function maps the operator hyphen token (`agent-profile`, `mission-step-contract`) to the canonical `ArtifactKind`, and route `charter context --include`, `activate`, `deactivate`, and `list` through it. Resolves FR-023; makes FR-022 a dispatch fix. Keep `mission-type` handled explicitly (see CL-4).
- **CL-2 — Collapse the context `--include` kind table onto the registry.** Replace the hand-maintained renderers dict + duplicated candidate-kind tuple in `context.py` so the supported kinds derive from the canonical set. This guarantees `agent-profile` (FR-022) *and* its siblings are reachable through the same path, instead of patching one kind.
- **CL-3 — Decouple layer from kind in `_KIND_TO_DOCTRINE_DIR`.** Today the constant bakes the `built-in` path segment into each entry and re-declares the file suffix that `ArtifactKind.glob_pattern` already owns. Split kind -> (base dir, glob from `ArtifactKind`) from the layer segment so `list_available()` can iterate {built-in, org, project} roots in a loop. This makes FR-025/FR-026 a clean traversal rather than a second hardcoded table.
- **CL-4 — Account for `mission-type` living outside `ArtifactKind`.** The charter surfaces cover **9** kinds; `ArtifactKind` enumerates 8 doctrine artifact kinds (plus `template`, minus `mission_type`). Mission types are a separate subsystem. Any consolidation must treat the charter kind set as `ArtifactKind` artifact kinds **plus** the explicit `mission-type` token, so planning does not assume one enum covers all nine. Flagging this prevents a refactor that silently drops or mis-routes mission-type.
- **CL-5 — `list_available()` signature carries layer roots as data, not `ctx`.** The `ctx` parameter is explicitly unused ("reserved for future org-pack support") — FR-026 is that future. Per C-008, resolve org/project roots in `specify_cli` (as `charter context` already does for `org_root`) and pass them in as data; do not reach into `specify_cli` from `charter`.

### Scope discipline

These are **enabling** refactors scoped to the kind-vocabulary surfaces this mission already edits. They are not a license to rewrite the activation engine, the DRG, or the broader doctrine loader. If CL-1..CL-3 prove larger than a contained change during planning, the fallback is the minimal patch (hyphen-normalize in `--include` only, add a parallel org/project scan) with a follow-on cleanup ticket — but the consolidated approach is preferred because it removes the drift that produced both findings.

---

## R-010 - MissionStepContract rejects `enhances` (augmentation vocabulary gap)

**Finding**: An org-pack `*.step-contract.yaml` that declares `enhances: <built-in-id>` (or `overrides:`) fails validation. The `MissionStep` / step-contract Pydantic models in `src/doctrine/missions/models.py` use `ConfigDict(extra="forbid")` and never gained the `enhances`/`overrides` fields, so the keys are rejected as unknown. The org-pack DRG auto-emitter (`_AUGMENTATION_PLURAL_TO_KIND` in `src/doctrine/drg/org_pack_loader.py`) likewise scans only 5 kinds, so even if the field were tolerated, no `enhances` edge would be auto-emitted for a step contract.

**Why this happens**: The augmentation pair `enhances`/`overrides` was introduced in mission `charter-ux-and-org-pack-vocabulary-01KSAF14` (issue #1291), and its FR-010 deliberately scoped the fields to exactly **five** kinds: `Tactic`, `Styleguide`, `Paradigm`, `Procedure`, `AgentProfile`. Directives, toolguides, **mission step contracts**, and mission types were left out. The relation enum (`doctrine.drg.models.Relation`) *does* define `ENHANCES`/`OVERRIDES` globally — the gap is purely in the per-kind schema fields and the auto-emit table, not in the DRG vocabulary.

**Is the exclusion principled?** Partly. There is a real design wrinkle: mission step contracts describe **workflow topology** (action sequence, step inputs/outputs), so "enhance = field-merge" needs explicitly defined merge semantics (which fields merge vs. replace, how a partial step overlay composes) in a way that content artifacts like tactics do not. ADR `2026-05-16-1-doctrine-layer-merge-semantics.md` ratifies layer field-merge generally but does **not** single out step contracts or document a reason to exclude them. So the current state reads as an **incomplete rollout scoped to the five content kinds**, not a deliberate, documented boundary. Treating "mission steps cannot be enhanced" as intended behavior would be a misread.

**Relation to this mission**: This is adjacent to FR-001/FR-002 (adding `specializes_from` and keeping the relation vocabulary coherent) and to the kind-vocabulary consolidation in R-009 — all three touch how per-kind augmentation/lineage vocabulary is declared and validated. But extending `enhances`/`overrides` to step contracts is its own design unit: it needs step-contract field-merge semantics, a schema field addition (with the same `extra="forbid"` non-regression bar as NFR-004 of #1291), an entry in `_AUGMENTATION_PLURAL_TO_KIND`, and validator/advisory parity. **Scope decision pending** (see open question below) on whether to land it here or defer to a follow-on.

**OQ-1 — RESOLVED (operator decision)**: Close the augmentation vocabulary **fully** in this mission — add `enhances`/`overrides` to all four currently-missing kinds: directives, toolguides, mission step contracts, and mission types. See FR-028..FR-032 and Scenario 10.

### Surfaces that must change (all-4 decision)

| Surface | File | Change |
|---------|------|--------|
| Per-kind schema fields | `doctrine/directives/models.py`, `doctrine/toolguides/models.py`, `doctrine/missions/models.py` (step contract + mission type) | Add optional `overrides: str \| None` / `enhances: str \| None`; keep `extra="forbid"` otherwise |
| DRG auto-emit table | `doctrine/drg/org_pack_loader.py` `_AUGMENTATION_PLURAL_TO_KIND` | Add the newly-eligible kinds |
| Validator augmentation set | `specify_cli/doctrine/pack_validator.py` `_AUGMENTATION_PLURAL_KINDS` | Add the same kinds (today a hand-synced copy — see CL note) |
| JSON Schema mirrors (if present) | wherever the #1291 JSON Schemas live | Mirror the new optional fields |

### Asymmetry to resolve in planning (binding design note)

- Directives, toolguides, and mission step contracts (`mission_steps`) are **already** in the 8-kind org-pack DRG universe (`_ORG_DRG_CANONICAL_KINDS`), so they only need the schema fields + auto-emit/validator entries. This is the same shape as the WP05 work for the original five.
- **Mission types are NOT in the org-pack DRG canonical universe** and are not org-pack DRG node kinds. Augmenting a mission type therefore cannot reuse the existing `enhances`-edge auto-emit path as-is. Planning must choose one of: (a) expand the canonical kind universe to include mission types — a **C-009-binding** change with contract-test sweep implications and drift checks against `charter.activations._ALLOWED_KINDS`; or (b) define a separate mission-type augmentation path (mission types are activated via the `mission-type` charter kind and may field-merge through a different mechanism). The topology-merge semantics from R-010 apply doubly to mission types, which own the action sequence itself.

### Consolidation tie-in (R-009)

`_AUGMENTATION_PLURAL_TO_KIND` (loader) and `_AUGMENTATION_PLURAL_KINDS` (validator) are two copies of the same set, kept aligned only by a "Kept in sync with…" comment. Completing augmentation coverage is the moment to make them derive from one canonical source (R-009 / CL-1..CL-3) instead of widening two hand-synced tables.

---

## R-011 - Pre-Implementation Code Review (subagent fan-out)

A read-only fan-out reviewed the code behind each FR cluster for enabling refactors and long-method splits to do *before* the feature work. Findings are anchored to `file:line` as observed on this branch; planning should re-verify line numbers.

### A. DRG relations & profile lineage (FR-001..FR-004)

- **Add `SPECIALIZES_FROM = "specializes_from"` to the `Relation` enum (`src/doctrine/drg/models.py:47`) FIRST.** No default-include traversal exists — every traversal (`walk_edges` in `drg/query.py:57`, `resolve_context`, `edges_from` in `models.py:132`) is opt-in by relation set, and cycle detection in `validate_graph` only follows `REQUIRES`. So a distinct enum value makes **FR-002 hold by construction** (a `DELEGATES_TO`/work-handoff filter can never match it). Note: `DELEGATES_TO` currently has **zero DRG-traversal consumers**, so FR-002 is vacuous today — add a guard test so a future `edges_from(urn, Relation.DELEGATES_TO)` can't regress it.
- **Enabling refactor — fix the silent `None`-drop in `_bridge_org_edge_to_drg_edge` (`src/charter/drg.py:~432-439`).** An org-fragment relation string not in the enum/aliases silently drops the entire edge. If a pack authors `relation: specializes_from` before the enum member exists, the lineage edge vanishes with no error → **quiet FR-003 failure**. Add the enum member first, then decide whether unknown relations should surface rather than drop.
- **Normalize the org-vs-project asymmetry.** Org-fragment edges are silently dropped on unknown relation (`charter/drg.py:~432`), but project-fragment edges go straight through `model_copy()` (`drg.py:~537-538`) and are rejected loudly by Pydantic. FR-003's three sources (shipped/org/project) should behave identically.
- **Make the DRG lineage edge DERIVED from the profile field, not independently authored.** `specializes_from` already exists as an agent-profile frontmatter field consumed by `agent_profiles/repository.py:~468-595` (hierarchy/ancestors/cycle-validation) — a parallel lineage graph. Auto-emit the DRG edge from that field (single source of truth) to prevent drift. Today the auto-emitter (`org_pack_loader.py:~333-379`, table at `:89`) only emits `enhances`/`overrides` via a hardcoded `("enhances","overrides")` tuple; extract a module-level `_AUGMENTATION_FIELDS` list so adding `("specializes_from","specializes_from")` is one line. `_collect_augmentation_edges` (~46 lines, deep nesting) should split its per-file extraction into a helper before this.
- **Most valuable:** enum member + silent-drop fix (the only quiet FR-003 path).

### B. Agent profile loading & diagnostics (FR-005..FR-007)

- **Headline: `AgentProfileRepository` is the ONLY doctrine repo not on `BaseDoctrineRepository` (`src/doctrine/base.py:82`).** It hand-rolls a fully-duplicated three-layer loader; org and project blocks are near-identical copies. This duplication is the root difficulty for FR-005..FR-007.
- **Invalid profiles dropped at 5 `warnings.warn` sites** (`repository.py:250,279,311,342,371`) plus silent `continue`/`pass` branches (`:241,271,336` and the language filters; `delete()` swallow at `:744`). Everything but a formatted string is discarded; `self._profiles`/`self._provenance` are valid-only. **No structure exists to carry diagnostics — one must be introduced.**
- **Enabling refactors (do first):** (1) introduce a `SkippedProfile` record (layer, path, profile_id|None, error_summary) + `self._skipped` field + `skipped_profiles()` accessor returning a deterministically-sorted copy; (2) route every drop site through one `_record_skip(...)` helper; (3) collapse the three duplicated layer loops into one shared per-layer method before instrumenting. `validate_agent_profile_yaml()` (`validation.py:49`) already returns structured field errors but is never called by the repo — wire it in for richer summaries.
- **FR-007 mostly free once the field exists:** `DoctrineService.agent_profiles` (`service.py:130-138`) caches the repo in `self._cache`, so `self._skipped` survives. **NFR-002 risk:** built-in uses `rglob`, org/project use unsorted `glob` (`repository.py:238,268,333`) — sort at the read boundary for determinism. `_load()` (~85 lines) and `_load_org_profiles_from_dir()` (~59 lines) are the split targets.
- **Optional (bigger):** migrate the repo onto `BaseDoctrineRepository` (its union-merge/`excluding`/kebab-alias semantics differ from the base's `{**a,**b}`, so larger scope).

### C. `doctor doctrine` surface (FR-008..FR-010)

- **All in `src/specify_cli/cli/commands/doctor.py` (a 2762-line module; doctrine slice ~1743-2396).** Human and JSON outputs are built **independently** (JSON hand-assembled inline at `~1971-1978`; human via separate renderers), with the org-DRG load+merge logic **duplicated** between `_collect_org_layer_data` (`~2156`) and `_render_org_layer_section` (`~2092`). Any new invalid-profile field must be added twice → drift. **Enabling refactor:** one `DoctrineHealthReport` dataclass (mirror existing `DoctorFinding` at `:2404`) with `to_dict()`, consumed by both surfaces.
- **FR-010 false-healthy exact decision point:** `_render_doctrine_pack` (`:1843`) greens a pack on `snapshot_present` alone, and `_count_pack_artifacts` (`:1803`) counts profiles by raw `glob("*.yaml")`. Fix: derive per-pack health from `valid_count == discovered_count`, which requires the loader diagnostics from cluster B.
- **The command never instantiates `AgentProfileRepository`** — it globs files, and `_collect_doctrine_collisions` (`:2017`) scrapes `warnings` text with a regex (`~2054-2059`), lossy (no path/id). **Coordination point:** define the FR-009 stable JSON fields on the loader's `SkippedProfile` dataclass (cluster B) so doctor JSON is a passthrough. **NFR-001:** build the report once (single `DoctrineService`/DRG load) instead of the current redundant double-loads. Long methods: `doctrine_check` (~140 lines, `:1875`), `_build_selection_block` (~87, `:2288`), `_collect_doctrine_collisions` (~68).

### D. Charter activate / deactivate / cascade (FR-011..FR-016, NFR-003)

- **Biggest blocker: dual ID system.** `config.yaml` stores file-stem IDs (`001-architectural-integrity-standard`) while DRG URNs use the `id:` field (`directive:DIRECTIVE_001`). `CharterPackManager.list_available` (`pack_manager.py:371-416`) **discards the `id:` field and returns filename stems** (`~413-414`), even though `catalog._extract_artifact_id` (`catalog.py:215-235`) already reads it. This forces `consistency_check._check_drg_cross_kind_refs` to work at KIND level only (`consistency_check.py:186-270`, documented `:194-204`). **Build a catalog-backed ID resolver** — this single seam unblocks FR-014/015/016 so cascade can resolve a config ID to a DRG node and reuse `walk_edges`/`resolve_transitive_refs`.
- **NFR-003 seam:** `activate()` (`pack_manager.py:176-258`) is *mostly* validate-then-commit (FR-011 ID check at `:217` precedes the single `_save_config` at `:257`), but validation, default-pack materialization (`:224-231`), and append are interleaved. Extract pure `plan_activation(...) -> ActivationPlan` (raises on FR-011/012) + `commit_plan(...)` (single write) so "no write on failure" is structural and testable. `merge_defaults()` writes a backup *before* `_load_config` (`:452` vs `:455`) — a latent NFR-003 ordering trap if ever wired into activate.
- **`--cascade` scope collapsed to bool at `activate.py:47` / `deactivate.py:47`** (`bool(cascade)`), discarding the scope string. CLI option is already `str | None` — thread the scope through `activate()`/`deactivate()` signatures (`pack_manager.py:176-183,260-267`). `ActivationResult.cascade_activated/cascade_deactivated/skipped_shared` are **already `dict[str,list[str]]`** and the CLI already renders them — only input scope + population logic are missing. Add a small `CascadeScope` value object so `all` is an explicit shorthand (FR-014).
- **FR-015 shared-reference analysis must be built** (none exists; only deferral comments at `pack_manager.py:279,327,330`). The DRG lacks an incoming-edge index — add `edges_to(urn)`/reverse adjacency, then a target is *exclusive* iff unreachable from all other still-activated sources after removal. Pure graph logic, no per-kind branches (FR-016).
- **Per-kind smells to generalize:** the `kind == "mission-type"` block inlined in `activate.py:49-73` (move behind the plan seam); `deactivate` raises `sys.exit(1)` from the manager (`pack_manager.py:309-315`) — replace with a typed exception (layering). Long: `activate_cmd` (~64, CLI), `activate`/`deactivate` (~82/~76).

### E. Runtime OperationalContext (FR-017..FR-020, C-006)

- **IMPORTANT precondition: the dead-symbol gate `tests/architectural/test_no_dead_symbols.py` is ALREADY RED at this branch point** — confirmed by running it: 5 offenders + 7 stale allowlist entries. **Investigated (git blame): all 5 are inherited from `main`, none introduced by this mission's own commits** (this branch added only docs/meta). All 5 are *very recent* (2026-05-31 / 06-01), so `main` itself is currently red on this gate — a regression that landed without the gate blocking it. Classification of the 5 offenders:
  - **In-scope for this mission (2):** `specify_cli.cli.commands.charter.activate::charter_activate_app` and `...deactivate::charter_deactivate_app` — both from commit `5b594562e` ("charter CLI activate/deactivate/list/pack commands + FR-014 reader gap fix"), the exact surface this mission extends. These are the dead sub-apps cluster E flagged; **FR-020 already covers their removal**, so the mission naturally clears them.
  - **Out of scope (3):** `charter.pack_context::CharterPackConfigError` (commit `bc04abae`, "fail closed on malformed pack activations"), `specify_cli.git.sparse_checkout::SparseCheckoutKind` (`aa330af9`, lane sparse-checkout), `specify_cli.lanes.lifecycle_sync::LANE_AUTO_REBASE_FAILED` (`8ad6bb40`, lane state sync). Unrelated recent infra additions whose symbols aren't yet wired/imported.
  - The 7 stale allowlist entries (`next._internal_runtime.events::*`, `lanes.auto_rebase::AutoRebaseReport`) are symbols that *gained* callers — pure allowlist hygiene, also inherited.
  - **Resolved handling (operator):** the 2 charter sub-apps stay in via FR-020; the **7 stale allowlist entries are pulled in (FR-036)**; **`CharterPackConfigError` is pulled in (FR-035)** — it is charter-relevant (raised internally by `_config_error()` at `pack_context.py:214`, "fail closed on malformed pack activations", but caught by no external caller; wiring = the activation/context CLI catches it, tying to FR-011/FR-012). The 2 git/lanes offenders (`SparseCheckoutKind`, `LANE_AUTO_REBASE_FAILED`) are **out of scope** — they are heavily used within their own modules and unrelated to charter/doctrine; if the gate cannot pass with them present they are allowlisted with a tracker reference (NFR-006), not silently fixed. See [[ci-retro-pending]].

### #1333 template discovery/resolution (now in scope)

Templates exist on disk (`src/doctrine/templates/`, per-mission `missions/<m>/templates/` + `command-templates/`) and `resolver.py::resolve_template` resolves them **by exact name** through the 5-tier chain (override → legacy → global-mission → global → package). Gaps that #1333 closes: (1) **no discovery/listing** — callers must already know the name; (2) `ArtifactKind.TEMPLATE` has an **empty glob** (`artifact_kinds.py:32`) so templates aren't file-discoverable like other kinds; (3) `template` is absent from `charter list`, `charter context --include`, and `_KIND_TO_DOCTRINE_DIR`. Because templates live in **mission-scoped tier directories with no extension** (unlike the flat `doctrine/<plural>/built-in/*.<suffix>` layout), the R-009 kind consolidation must special-case template discovery (tier+mission walk, name-based) rather than assuming the uniform glob shape. Integrates with FR-022/FR-025 (context/list) and C-009 (DRG-addressable templates).
- **FR-017 strictly precedes FR-019.** OC symbols sit in allowlist category C (`test_no_dead_symbols.py:407-410`); removing them before wiring makes them offenders. The gate's stale-detector (`:771-802`) auto-fails if they stay allowlisted after wiring — so wiring forces the removal.
- **Three production call sites** (inputs already available): WP claim via `workflow.py:1234` and `implement.py:740` (`start_implementation_status`), and `next` decision via `runtime_bridge.py:1980` `decide_next_via_runtime`. Inputs: `active_model`=`--agent`; `active_profile` via existing `_resolve_step_agent_profile` (`runtime_bridge.py:991`); `current_activity`=`step_id`/`mission_state`; `active_role`=claim actor; `tech_stack` from charter/meta.
- **C-006 SAFE by construction** (layer order kernel←doctrine←charter←specify_cli): keep `build_operational_context()` in `charter/invocation_context.py:186` as a **pure explicit-parameter assembler**; call it from `specify_cli`. Do NOT build OC inside `doctrine.*`, nor inside the side-effect-free `next/discovery.py`. `decide_next_via_runtime` is already `# noqa: C901` — extract a `_build_operational_context_for_decision(...)` helper rather than inlining.
- **FR-020 items located:** (1) `charter_activate_app`/`charter_deactivate_app` sub-apps are dead — `_app.py:17/48` register the bare `activate_cmd`/`deactivate_cmd` callbacks instead; pick one pattern and drop the other (`activate.py:13`, `deactivate.py:13`, `_app.py`). (2) FR-008 comment misattribution at `_app.py:47` (the `activate` verb is FR-004; FR-008 is only the in-flight warning). (3) Orphaned empty category `_CATEGORY_C_WP_IN_FLIGHT_WORKFLOW_REGISTRY` (`test_no_dead_symbols.py:420-425`, still unioned at `:538`) — safe to delete. (4) Obsolete activation-override writer already gone (`charter_activate.py:11`); leave the legitimate `.kittify/overrides/` template tier in `doctrine/resolver.py` untouched.

### Cross-cutting synthesis

Three independent clusters converge on the **same root cause flagged in R-009**: a kind/ID vocabulary that is re-declared per surface with no single source of truth — the dual config-stem-vs-DRG-`id` system (D), the hand-synced augmentation tables (R-010), and the per-command kind tables (R-009). A small canonical kind+ID resolver layer is the highest-leverage enabling refactor across FR-014/015/016, FR-022..FR-027, and FR-028..FR-032. Two clusters (B and C) converge on a second: **structured load diagnostics** introduced once on the profile loader feed both FR-005..FR-007 and FR-008..FR-010. Recommended ordering: (1) canonical kind/ID resolver + DRG enum member; (2) profile-loader `SkippedProfile` diagnostics; (3) `DoctrineHealthReport`; (4) `plan/commit` activation seam + `edges_to` reverse index; (5) OC wiring then allowlist prune.

---

## R-012 - DRG is the source of truth for relationships (operator directive)

**Directive (operator)**: The DRG is to be the **canonical source of truth for doctrine relationships**, to enable extensibility. Adding a new relationship type should be a DRG-vocabulary change, not an N-times per-artifact-schema change.

**This reverses R-011 cluster-A recommendation #3.** That finding suggested keeping the agent-profile *field* canonical and deriving the DRG edge from it. Per this directive, the polarity flips: the **DRG edge is canonical**; relationship resolution flows *from* the DRG, and any per-artifact relationship field is a convenience input that **projects into** the DRG, not an independent authority.

**Why this is the right grain (extensibility)**: It is the same root friction as R-009 and R-010. Today a relationship like `enhances`/`overrides`/`specializes_from` must be added as a typed field to each artifact's Pydantic model (and JSON Schema), and each consumer reads the field directly — so FR-028..FR-032 means touching 4 more models, and any *future* relation repeats that churn. If relationships are first-class DRG edges, a new relation type is added once to `Relation` (`doctrine/drg/models.py:47`) and the auto-emit/validation vocabulary, with no per-kind schema change.

### Resolved model (recommended interpretation)

1. **Canonical representation**: a relationship exists iff there is a DRG edge for it. The merged DRG is the resolved truth.
2. **Authoring**: retain the existing frontmatter fields (`enhances`/`overrides`/`specializes_from`) as **authoring projections** — they emit DRG edges via the auto-emitter. This keeps parity with the five kinds #1291 already shipped and avoids a disruptive authoring migration. (Strict alternative: move authoring entirely into DRG fragments and drop the fields — larger, migration-heavy; see OQ-2.)
3. **Consumption**: consumers resolve relationships by DRG traversal (`walk_edges`, `edges_from`, and a future `edges_to`), **not** by re-reading per-kind fields. The agent-profile hierarchy resolver (`agent_profiles/repository.py:476-580`, 8+ direct `specializes_from` reads) is the first consumer to migrate onto DRG traversal — this also collapses the "two parallel lineage graphs" drift noted in R-011 cluster A.

### Layering constraint (binding — resolve in planning)

The doctrine-layer DRG loader exists (`doctrine/drg/loader.py`), but the **three-layer merge** (`merge_three_layers`) lives in `charter/drg.py`, and **doctrine must not import charter** (`tests/architectural/test_layer_rules.py:151`, ADR 2026-03-27-1, mission C-006). So a doctrine-layer consumer (the profile repository) can read the *built-in* DRG but cannot read the *org/project-merged* DRG without violating layering. Options for planning:
- **(a)** Push the relationship-merge primitive down into `doctrine.drg` (doctrine-layer merge of built-in + provided org/project fragments as data), leaving charter as a thin caller. Doctrine consumers then resolve against the doctrine-layer merged graph. Cleanest for "DRG source of truth at every layer," larger refactor.
- **(b)** Keep the merge in charter; doctrine-layer consumers resolve only the built-in graph; cross-layer (org/project) relationship resolution is a charter/specify_cli responsibility that passes merged data down. Smaller, but means "source of truth" is layer-qualified.

**OQ-2 — RESOLVED (operator)**:
- **(i) Authoring = DRG-fragment-only.** Relationships are authored as DRG edges; the per-artifact relationship fields (`enhances`/`overrides`/`specializes_from`) are removed as authoring inputs. This is the migration-heavy option and it goes **beyond** simply adding fields to the four uncovered kinds: the five kinds that gained these fields in #1291 (`tactic`, `styleguide`, `paradigm`, `procedure`, `agent_profile`) migrate *away* from field-authoring too, and the agent-profile `specializes_from` lineage moves into DRG fragments. Implication: this supersedes the field-addition framing of FR-028 — see the FR reframe below and the migration NFR. Scope/magnitude is significant; planning must size a migration of built-in + shipped-pack artifacts and the org-pack authoring docs.
- **(ii) Layering = doctrine owns models + the canonical merge; charter aggregates from the merged DRG.** Push the relationship-merge primitive down into `doctrine.drg` so the **merged/combined DRG is a doctrine-layer artifact** (built-in + org/project fragments supplied as data). `charter` no longer owns `merge_three_layers`; it becomes a consumer that *aggregates* activation-aware views from the doctrine-merged graph. Doctrine-layer consumers (the profile hierarchy resolver) resolve directly against the merged DRG — no layering violation, "canonical at every layer" holds. `charter/drg.py`'s merge logic relocates to `doctrine.drg`; charter retains only activation filtering/aggregation.

**Consequences of OQ-2 for requirements**:
- **FR-028 reframed** (see spec): no new per-kind *fields*; instead relationship authoring for ALL kinds (the 4 uncovered + the 5 existing) is via DRG fragments, and the field inputs are retired behind a migration.
- **New migration requirement**: existing field-authored relationships (built-in doctrine + shipped packs) must be migrated to DRG-fragment edges with zero relationship loss (additive, reversible audit). This is a notable scope addition.
- **Merge relocation**: `merge_three_layers` (and helpers) move from `charter/drg.py` into `doctrine.drg`; `test_layer_rules` expectations and charter call sites update accordingly.
- **Profile resolver**: `agent_profiles/repository.py` lineage reads (`:476-580`) migrate onto doctrine-layer merged-DRG traversal.

### Impact on existing requirements

- **FR-001/FR-002**: `specializes_from` becomes a first-class DRG relation (already planned); the profile hierarchy resolver should consume it via DRG traversal rather than the field (subject to OQ-2 layering).
- **FR-028..FR-032**: reframe from "add fields to 4 models" toward "augmentation/lineage are DRG edges; fields are projections." The auto-emit table consolidation (R-010, FR-030) becomes the central mechanism rather than a side cleanup.
- **R-011 cluster A**: keep the *silent-drop fix* and the *enum-member-first* recommendations; replace "derive DRG from field (field canonical)" with "project field into DRG (DRG canonical)."

---

## Deferred Research

- #1333 should become a follow-on mission for doctrine template discovery and DRG-backed template resolution.
- #1040 remains a design-spike / research-mission candidate for full ADR primitives. This mission only benefits from the existing idea of schema-registered policy artifacts; it does not implement ADR tooling.
