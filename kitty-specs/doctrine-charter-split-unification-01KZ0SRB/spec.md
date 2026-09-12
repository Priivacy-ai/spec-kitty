# Mission Specification: Doctrine-Charter Split — Single-Path Authority Foundation

**Mission**: `doctrine-charter-split-unification-01KZ0SRB`
**Type**: software-dev (architecture / unification)
**Status**: Draft
**Purpose (TL;DR)**: Make the doctrine-pack & charter split (#3101) clean and usable by resting it on
**one** charter read/path authority — the compiled `.kittify/charter/charter.yaml` is the deterministic,
schema-guarded resolution authority and **takes precedence**; `charter.md` is a **secondary** rationale /
free-form read point that never overrides it — with correct wiring across the layer order
`kernel <- doctrine <- charter <- glossary/runtime <- specify_cli`, and the wheel-packaging **groundwork**
in place so the #3101 cutover becomes a mechanical follow-on.

> **Research basis:** a 3-lens pre-spec adversarial squad (planner-priti — related-issues & sequencing;
> paula-patterns — code-state / brownfield read-authority & meta.json fail-closed audit;
> architect-alphonso — layer-order & wheel-split sizing) scoped this mission on the post-#3146 tree
> (upstream/main `8466727eb`). All three converged on **foundation-first**: #3101's wheel cutover is
> blocked on a not-yet-existent `kernel` wheel and the shared-package-boundary ADR
> (`docs/adr/3.x/2026-04-25-1-shared-package-boundary.md`, C-007) **forbids partial cutovers** — so this
> mission lands the single read/path authority + layer wiring + packaging **groundwork**, and the actual
> kernel→doctrine→charter wheel cutover is a **deferred, explicit follow-on**.
>
> **Predecessor:** #3146 (`charter-pack-usage-journey-01KYWWTF`, LANDED on main) fixed the dispatch-net
> predicate, retargeted the **context / status / dispatch** presence gates to `charter.yaml`, retired the
> resolver catalog-fallback, and shipped a `context_schema_version` **tracking** stamp. This mission
> extends that unification to the **residual** `charter.md` presence/config readers #3146 left behind.
>
> **Post-spec squad (2026-08-02) folded** — reviewer-renata (fakeable acceptance), architect-alphonso
> (packaging/structure), debugger-debbie (live code-truth), all anchors verified: FR-005 is a
> schema+compiler+resolver change (`GovernanceConfig` has **no** `retrospective` field today); FR-007
> reuses the existing `core/paths` typed authority (no second home) + an enumerated caller census; FR-008
> ships an AST-walk guard (pytestarch is green **with** the edge present); FR-010's `packs/` mechanism is
> out-of-tree and must be `hatch build`-spiked; FR-013 repoints **both** parity fixtures; added **FR-016**
> anti-regression durability gate; NFR-001 fixtures must delete `charter.md` (not seed both).
>
> **Scope closes / folds:** #3150 (dashboard presence probe, P1), #3140 (meta.json fail-closed authority,
> P1), #3149 (CI path-filter gap), #3107 (inert CLI-reference parity gate + remainder), #3102-closeout,
> plus the `charter/context.py` OR-gate, the `analysis_report.py` hash-input, and the retrospective-policy
> frontmatter resolver — all the same "un-unified charter read authority" root cause. **Deferred as an
> explicit follow-on:** #3101 wheel cutover, #3091/#3022/#3036/#3039/#2986, #2787-freeze (coordinate epic
> #2519), the epics.

## User Scenarios & Testing *(mandatory)*

The users are an **operator** running a project whose charter is compiled to `charter.yaml`, and the
**maintainer** who needs the doctrine/charter layer to be independently packageable. The failure today:
`charter.yaml` is nominally the authority, but several surfaces still key their **presence / config**
decision on the display-only `charter.md`, so deleting `charter.md` (or never seeding it) makes those
surfaces disagree with the authority — an un-unified read model — and the layer that #3101 wants to ship
as a wheel is still bundled with packaging-closure gaps.

### User Story 1 — Charter presence resolves from one authority (Priority: P1, #3150)

An operator's project has a compiled `charter.yaml` but no `charter.md` (SC-002 of #3146: the display
companion is deleted, or was never seeded on a compiled-only project). Today `charter context --json`
reports `present: true` (fixed by #3146) while the **dashboard** still shows "no charter", the
**analysis report** hashes the wrong file, and the `charter/context.py` "missing" gate only passes because
of an `OR charter.md` test-compat bridge. Every surface that answers *"does a charter exist / where is
it?"* must resolve from `charter.yaml` (authority), consistently.

**Why this priority**: it is a P1 correctness divergence — the same "is there a charter?" question gets
two different answers depending on which surface asks, which is exactly the un-unified read authority the
mission exists to close, and #3150 is filed P1.

**Independent Test**: seed a project with `charter.yaml` and **no** `charter.md`; assert dashboard,
analysis-report staleness, and the `charter/context.py` presence gate all report the charter as present /
resolvable.

**Acceptance Scenarios**:
1. **Given** a project with `charter.yaml` and no `charter.md`, **When** the dashboard **presence probe**
   (`resolve_project_charter_path`) resolves the project charter, **Then** it reports present (keys on
   `charter.yaml`) — asserted at the probe-function level (dashboard UI behaviour stays covered by the
   existing UI e2e guard, not claimed from the unit probe); the prose **body** it serves still reads
   `charter.md` when that exists.
2. **Given** the same project, **When** the analysis report computes its charter staleness input, **Then**
   it hashes `charter.yaml` (the resolving authority), and the legacy `charter/charter.md` location
   fallback is gone.
3. **Given** a `charter.md`-only project (no `charter.yaml`), **When** `charter context` renders, **Then** it
   still renders the `charter.md` prose (charter.md as readable secondary); **and given** both files exist,
   the compiled `charter.yaml` governance takes precedence — the `context.py:249` prose-presence gate is
   pinned, not retired (see FR-002).
4. **Given** a project with **both** files, **When** any *authority*-presence surface (dashboard, analysis,
   status) runs, **Then** it keys on `charter.yaml`; `charter.md` remains readable for prose/rationale.

### User Story 2 — Retrospective policy resolves from the authority, with rationale in prose (Priority: P1)

The retrospective policy (`retrospective/{policy,mode,gate}.py`) is resolved today from `charter.md` YAML
frontmatter — a **resolving** read of the display-only companion, which contradicts the "charter.md never
resolves / charter.yaml takes precedence" model. The policy must resolve from `charter.yaml` governance
(deterministic, schema-guarded, authoritative); `charter.md` frontmatter stays readable as an **overridden
secondary** so existing projects keep working and prose/rationale still lives in the markdown.

**Why this priority**: it is the strongest surviving invariant violation (a decision input resolved from
the non-authority), and it directly instantiates the operator's charter.yaml-precedence model.

**Independent Test**: a project whose `charter.yaml` governance sets a retrospective policy AND whose
`charter.md` frontmatter sets a **different** one — assert `charter.yaml` wins; a `charter.md`-only legacy
project still resolves its policy from the markdown.

**Acceptance Scenarios**:
1. **Given** `charter.yaml` governance carrying a retrospective policy, **When** the retrospective mode /
   gate / policy resolves, **Then** it uses the `charter.yaml` value.
2. **Given** both `charter.yaml` and a divergent `charter.md` frontmatter policy, **When** it resolves,
   **Then** `charter.yaml` **takes precedence** (yaml wins).
3. **Given** a legacy `charter.md`-only project (no policy in `charter.yaml`), **When** it resolves,
   **Then** it still reads the `charter.md` frontmatter (backward compatible, secondary source).
4. **Given** the change, **When** the three `_CHARTER_REL` constants are examined, **Then** they are a
   single shared definition, not three redeclarations.

### User Story 3 — A corrupt meta.json always fails closed (Priority: P1, #3140)

A malformed or non-conforming `meta.json` today lets a raw `ValueError` propagate out of ~25 unwrapped
`load_meta` callers (e.g. `mission_runtime/lifecycle_phase.py:120`, reached by the mission-status
aggregate). There is a canonical **parser** but the **fail-closed contract** is fragmented across one
typed authority, ~6 divergent per-module wrappers, and the unwrapped callers. A corrupt `meta.json` must
fail closed everywhere — a typed domain exception or `None`, never a raw `ValueError`.

**Why this priority**: it is a P1 with red tests on `main` (the mission-status aggregate fail-closed
tests), and it is the same "one authority" thesis applied to the meta.json read path.

**Independent Test**: write a corrupt and a non-dict `meta.json`; assert each enumerated product reader
returns `None` or raises the typed `MissionMetaReadError` — never a bare `ValueError`.

**Acceptance Scenarios**:
1. **Given** a corrupt `meta.json`, **When** the mission-status aggregate loads it, **Then** it raises the
   typed `MissionMetadataUnavailable`/`MissionMetaReadError` (the two red `test_mission_status_aggregate`
   fail-closed tests go green), **not** a raw `ValueError`.
2. **Given** a non-dict (`list`) `meta.json`, **When** any enumerated fail-closed reader loads it, **Then**
   it fails closed (typed exception or `None` per that site's contract), never a raw `ValueError`.
3. **Given** the change, **When** the meta.json fail-closed readers are examined, **Then** they route
   through **one** shared `load_meta_fail_closed` authority (the divergent wrappers are collapsed onto it);
   genuinely-silent callers keep an explicit `load_meta_or_empty`.

### User Story 4 — The layer is wired and packaging-ready for the split (Priority: P2, #3101 groundwork)

A maintainer wants to eventually ship `src/doctrine/` (then `src/charter/`) as an installable wheel on the
`kernel <- doctrine <- charter` chain. The layer **order** is already correct and CI-enforced, but one
real upward edge remains, and the existing `spec-kitty-doctrine` wheel scaffold is inert with
packaging-closure gaps (no `kernel` wheel to depend on; the doctrine wheel omits its `kernel` dependency
and the relocated `packs/built-in` content). This mission removes the edge and lands the packaging
**groundwork** so the follow-on cutover is mechanical — **without** performing the (forbidden-as-partial)
cutover itself.

**Why this priority**: it is enabling groundwork, not the operator-facing correctness win; it de-risks the
follow-on and closes the single genuine layer violation, but ships value even if the cutover never runs.

**Independent Test**: a non-vacuous wheel-closure test that fails if the doctrine pyproject drops its
`kernel` dependency or its `packs/` inclusion; `test_layer_rules` green after the edge deletion.

**Acceptance Scenarios**:
1. **Given** the layer graph, **When** the mission completes, **Then** the `charter -> specify_cli` edge in
   `synthesize_pipeline.py:68` is gone (`__version__` via `importlib.metadata` only) **and** a non-vacuous
   AST-walk gate FAILS if any `src/charter/**` module re-imports `specify_cli` at any scope (the pytestarch
   layer rule alone is green with the edge present, so it is not the guard).
2. **Given** the wheel manifests, **When** the closure test runs, **Then** `src/kernel/pyproject.toml`
   exists (`spec-kitty-kernel`, zero first-party deps), `src/doctrine/pyproject.toml` declares its `kernel`
   dependency **and** carries `packs/` via the spike-verified out-of-tree mechanism (packs is a repo-root
   `doctrine`-sibling, not in-tree), and the test **fails** if either is removed.
3. **Given** the mission, **When** the root `pyproject.toml` is inspected, **Then** `src/kernel`,
   `src/doctrine`, `src/charter` are **still** in the monorepo wheel `packages` (no cutover performed —
   groundwork only; a partial cutover is forbidden).
4. **Given** the charter wheel question, **When** the ADR/assessment is read, **Then** it records that
   `src/charter` is cleanly extractable in principle, sequences the cutover kernel→doctrine→charter as an
   explicit no-partial follow-on, and extends (not reinvents) the `2026-04-25-1` boundary pattern.

### User Story 5 — Charter/doctrine tooling CI is honest and focused (Priority: P2, folds #3149, #3107, #3102)

The dedicated `doctrine-charter-tests.yml` workflow (shipped by #3146) is path-filtered but **misses**
`src/specify_cli/cli/commands/charter/**` — where the charter CLI presence gates and the JSON producer
live — so a regression there is false-green under a workflow named for it. Separately, the CLI-reference
parity gate is **inert** (its `REFERENCE_PATH` points at a non-existent `docs/reference/cli-commands.md`
while the live doc is `docs/api/cli-commands.md`), and #3102 is fixed-but-still-open.

**Why this priority**: contributor-feedback + advertised-surface honesty in the same neighbourhood the
read-authority work already opens; cheap to fold, wasteful to leave loose.

**Independent Test**: the workflow triggers/selects the charter CLI command dir + its tests; the parity
gate is no longer SKIPPED and runs against `docs/api/cli-commands.md`.

**Acceptance Scenarios**:
1. **Given** a PR changing only `src/specify_cli/cli/commands/charter/**`, **When** `doctrine-charter-tests`
   runs, **Then** it triggers and runs those tests (no longer false-green over the CLI layer).
2. **Given** the parity gate, **When** the architectural suite runs, **Then** `test_docs_cli_reference_parity`
   executes (not SKIPPED) against `docs/api/cli-commands.md`, and the generated reference is current for the
   `charter pack list/path/apply` surface.
3. **Given** #3102, **When** the PR is prepared, **Then** it confirms the workflow shipped and closes #3102.

### Edge Cases

- **"Present" means `charter.yaml` exists.** A compiled-only project (no `charter.md`) is *present*; a
  `charter.md`-only pre-consolidation project is a **migration-compat** shape — the `_status_collectors`
  legacy fallback that serves it is **scoped explicitly**, not silently retired, unless we decide that
  shape is unsupported.
- **Retrospective precedence:** `charter.yaml` governance value wins over `charter.md` frontmatter when
  both exist; the markdown remains a legacy/secondary source (backward compatible), never an override.
- **No partial wheel cutover.** The doctrine/charter/kernel packages stay in the root wheel this mission;
  minting/fixing the sub-wheel pyprojects without a `clean-install` cutover is deliberate groundwork, and
  the closure test must not assert a state that requires the cutover to be green.
- **Prose readers stay on `charter.md`.** The `--include section:<id>` / policy-summary / compact-governance
  body renderers legitimately read `charter.md` (the #3146 C-003 prose class) — they are **not** collapsed
  into the presence gate and **not** retargeted to `charter.yaml`.
- **meta.json silent callers.** Sites with a deliberately-silent contract (`load_meta_or_empty`,
  `on_malformed="none"`) keep it; only the raise-default/`ValueError`-leaking callers are routed through
  the fail-closed authority.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Establish **one** charter read/path authority seated in the charter layer: `charter/bundle.py` (`CHARTER_YAML`/`CHARTER_MD`, which **already exist**) + `charter/charter_yaml_io` is the single door every **presence / path** decision resolves through, keyed on `charter.yaml` (authority). This FR owns **only the shared constant home**; each per-file repoint of an inline `".kittify"/"charter"/"charter.md"` literal-builder **folds into the surface WP** that already rewrites that file (FR-002/003/004/005) — it is **not** a separate lane (avoids coord write-scope collision). The tasks phase **enumerates** the exact target set (~23 `"charter.md"` literal occurrences across ~15 files) and **excludes** `upgrade/migrations/**` (historical-path determinism) and the C-003 prose readers. `charter/context.py` already imports the `bundle` constants (pre-deduped by #3146). `charter.md` stays a **secondary** prose/rationale read point (never a resolving override). | Draft |
| FR-002 | **Scope + pin (do NOT retire) the `charter/context.py:249` prose-presence gate** as a legitimate C-003 surface. Post-#3146 it is already correct: `charter.yaml` (authority) takes precedence and renders when present; `charter.md` (readable secondary — the operator model) still renders when it is the only surface; prose graceful-degrades when `charter.md` is absent (`:300`); "missing" only when **both** are absent. Retiring the `charter.md` disjunct would demote `charter.md` from readable-secondary to invisible and regress 26 `charter.md`-only fixtures (post-tasks squad correction of an earlier misreading). WP01 **pins** the four cells (yaml-only renders; md-only renders; both-absent missing; **yaml governance takes precedence when both present**) and clarifies the inline rationale. The genuine residual *authority*-presence readers are retargeted by FR-003/004/006 — not this prose gate. | Draft |
| FR-003 | **#3150** — Split `dashboard/charter_path.py::resolve_project_charter_path` so the **presence** probe (drives the dashboard "no charter" UI / `api.py`) keys on `charter.yaml` and survives `charter.md` deletion, while the prose **body** served (`api.py` `read_text`) still reads `charter.md` when present. | Draft |
| FR-004 | `analysis_report.py:190-196` — key the analyzer staleness input on `charter.yaml` (the resolving authority): the resulting hash-input set contains `charter.yaml` and **removes both** `charter.md` entries — the `:191` canonical companion **and** the `:192` legacy `charter/charter.md` fallback that every other resolver refuses. Acceptance: staleness computes without error when `charter.md` is absent (SC-001). | Draft |
| FR-005 | Migrate retrospective **policy resolution** to the `charter.yaml` authority. **This is a schema + compiler + resolver change, NOT a read swap** — `GovernanceConfig` (`src/charter/schemas.py`) has **no** `retrospective` field today and the compiled bundle carries no such block. (a) Add a `retrospective` model to `GovernanceConfig`; (b) wire the compiler/emitter so `charter generate` populates it (omit-when-empty for back-compat, `_OPTIONAL_EMPTY_OMIT_KEYS`-style); (c) change `retrospective/{policy,mode,gate}.py` to resolve **yaml-first** (authoritative, takes precedence) with `charter.md` frontmatter as an **overridden secondary** for legacy `charter.md`-only projects. Collapse the three duplicate `_CHARTER_REL` constants (`policy.py:39`/`mode.py:67`/`gate.py:116`) to one shared definition. Ship focused regression tests: yaml-wins, both-present-precedence, legacy-md-only. | Draft |
| FR-006 | Scope the `_status_collectors.py:85-87` "legacy charter.md gate" **explicitly** (a documented pre-consolidation migration-compat branch, `charter.md` present / `charter.yaml` absent). **Add a backward-compat regression test** for the `charter.md`-only status-collector shape — or, if that shape is declared unsupported, remove the branch (do **not** leave it comment-scoped and untested). The staleness **display** header/listing (`:74-84,103`) is unchanged (legitimate display). | Draft |
| FR-007 | **#3140** — Establish **one** public fail-closed `meta.json` reader with a typed contract, **reusing the existing authority**: `core/paths.py` already defines `MissionMetaReadError` (`:506`) and a private `_load_meta_fail_closed` wrapper (`:660-663`). Decide a **single home** (promote/re-home that wrapper as the public reader, or have `mission_metadata` delegate to it — **no** competing second authority). The tasks phase emits an **enumerated caller census** (all ~108 `load_meta(` call sites, each classified: raise-default-unwrapped / divergent-wrapper / deliberately-silent) as a reviewable artifact; route the unwrapped callers and the ≥6 divergent wrappers through the one reader; keep `load_meta_or_empty` for silent sites. The two red `test_mission_status_aggregate::TestLoadCoordUnavailableFailsClosed` tests go green via `mission_runtime/lifecycle_phase.py`. (Note: `_widen` is already green — fixed by #3146.) | Draft |
| FR-008 | Delete the single real upward layer edge: `charter/synthesizer/synthesize_pipeline.py:68` lazy in-function `import specify_cli` (used only for a `__version__` fallback) → resolve via `importlib.metadata` only. **Ship a non-vacuous guard**: `test_layer_rules`/pytestarch does **not** catch this in-function import (it is green **with the edge present**), so add an AST-walk gate (mirroring `_collect_specify_cli_imports` in the `mission_runtime` boundary ledger) that FAILS if any `src/charter/**` module imports `specify_cli` at **any** scope — proven by a self-mutation check. | Draft |
| FR-009 | Mint `src/kernel/pyproject.toml` (`spec-kitty-kernel`, zero first-party dependencies — the true root of the wheel chain), following the `2026-04-25-1` precedent shape. **Groundwork only** — not wired into the release/build path yet. | Draft |
| FR-010 | Fix `src/doctrine/pyproject.toml` so the standalone doctrine wheel is closed: add its `kernel` dependency (the `spec-kitty-kernel` wheel). **Correct the `packs/` mechanism** — `packs/built-in` is a **repo-root** tree resolved as a *site-packages sibling* of the `doctrine` package (`pack_paths.py::_resolve_built_in`, `doctrine_dir.parent/"packs"/"built-in"`), **not** in-tree under `src/doctrine/`; a naive `force-include ../../packs` is outside the project root and hatchling refuses it. The tasks phase **decides + spike-verifies with a real `hatch build`** the concrete mechanism (build-context-relative `force-include` or a build hook) that lands `packs/` as a `doctrine` sibling in the standalone wheel. Add a **non-vacuous** closure test that FAILS if the `kernel` dep or the chosen `packs/` mechanism is removed (self-mutation proof). **Groundwork only** — the nested wheel is not built by any CI job this mission. | Draft |
| FR-011 | Record a charter-wheel **assessment + ADR draft**: `src/charter` is cleanly extractable in principle (zero real upward entanglement after FR-008) but transitively needs the kernel+doctrine wheels first; sequence the cutover **kernel→doctrine→charter** as an explicit **no-partial** follow-on that extends `2026-04-25-1` (boundary test + pyproject-shape test + `clean-install-verification` job). Enumerate the deferred follow-on issues (#3101, #3091, #3022, #3036, #3039, #2986). | Draft |
| FR-012 | **#3149** — Add `src/specify_cli/cli/commands/charter/**` (+ `tests/specify_cli/cli/commands/charter/**` and `test_analyze_surface_agreement.py`) to the `doctrine-charter-tests.yml` trigger paths **and** pytest selection, so the charter CLI command layer is no longer false-green under that workflow. | Draft |
| FR-013 | **#3107** — Un-inert the CLI-reference parity gate (`tests/architectural/test_docs_cli_reference_parity.py`). It has **two** inert fixtures via `_read_or_skip` — `REFERENCE_PATH` (→ `docs/reference/cli-commands.md`) **and** `AGENT_REFERENCE_PATH` (→ `docs/reference/agent-subcommands.md`); the load-bearing `test_visible_paths_match_reference` skips if **either** is missing. Repoint **both** to the live `docs/api/` docs and regenerate `docs/api/cli-commands.md` + `docs/api/agent-subcommands.md` for the current `charter pack list/path/apply` surface. Acceptance asserts the test **ran green** (not merely that its first fixture stopped skipping). | Draft |
| FR-014 | **#3102 closeout** — Confirm the `doctrine-charter-tests.yml` workflow is delivered (post-FR-012) and record in the PR body the closing keyword for #3102 (fixed-but-still-open hygiene). | Draft |
| FR-015 | Investigate #2831 (implement gate false-fails `charter_source missing` despite sync passing, P0) and #2992 (`charter sync --force` "already in sync" while `status` MISSING, P1). **Timebox** the investigation (a bounded read, not an open chase) and **default to defer-with-reason**; only **fold** the fix if the root cause is *provably* the same charter presence/read split-brain this mission unifies — never let FR-015 silently expand the WP set (DIR-013 issue hygiene). | Draft |
| FR-016 | **Anti-regression durability gate.** Add an architectural test that FAILS if (a) a new inline `".kittify"/"charter"/"charter.{yaml,md}"` path literal is introduced outside `charter/bundle.py` (allowlisting `upgrade/migrations/**` + the C-003 prose readers), or (b) a new `charter.md`-keyed `.exists()` **presence** gate is added — so the single read authority stays durable, not a point-in-time cleanup that rots on the next PR. Non-vacuous: frozen-allowlist + self-mutation proof. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | Charter presence is proven single-authority. | Every retargeted presence surface (dashboard, analysis-report, `charter/context.py` gate, retrospective) works with `charter.md` **deleted** and `charter.yaml` present — executable regression tests, one per surface, and **each presence fixture DELETES/omits `charter.md`** (seeds `charter.yaml` only). A both-files seed is a separate no-regression case, **never** the presence proof (guards against the fixture-seeds-both fake-green). | Draft |
| NFR-002 | No new lint/type regressions. | `ruff` + `mypy` zero new issues on all changed modules (no new `# noqa`/`# type: ignore`/per-file ignore). | Draft |
| NFR-003 | meta.json fails closed with a typed contract everywhere. | A corrupt and a non-dict `meta.json` surface **zero** raw `ValueError` across the readers; a load-counting/contract test pins the typed-exception / `None` outcome **for the full enumerated caller set (the FR-007 census)**, not a sample. | Draft |
| NFR-004 | The mission's structural gates are non-vacuous. | Self-mutation proofs: the doctrine-wheel-closure test FAILS when the `kernel` dep **or** the chosen `packs/` mechanism is removed (FR-010); the FR-008 charter-import gate FAILS when the `specify_cli` import is re-added; the FR-016 literal gate FAILS on a re-introduced inline charter path literal. | Draft |
| NFR-005 | Behaviour-change decisions are explicit, not slipped. | The spec/PR record: (a) the retrospective **precedence flip** (charter.yaml > charter.md frontmatter) and its backward-compat contract; (b) the `charter/context.py` OR-gate retirement; (c) that **no** wheel cutover was performed (groundwork only). CHANGELOG updated per DIR-009. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **charter.yaml precedence, charter.md secondary.** `charter.yaml` is the deterministic, schema-guarded resolution authority and takes precedence for every presence/config decision; `charter.md` stays a readable secondary rationale/prose source and is **never** an override. Do **not** collapse the prose/body readers (the #3146 C-003 class: `--include section:<id>`, policy-summary, compact-governance) into the presence gate or retarget them to `charter.yaml`. | Active |
| C-002 | **No wheel cutover in this mission.** Packaging is **groundwork only** — mint/fix the sub-wheel pyprojects + a closure test. Do **not** remove `src/kernel`/`src/doctrine`/`src/charter` from the root `pyproject.toml` `packages`, do not publish wheels, do not add a release gate. (Already satisfied by the tree: root `packages` lists all three and `packs` is root-force-included — the mission simply must not remove them.) **Residual:** confirm **no** CI job builds/installs the nested `spec-kitty-doctrine`/`spec-kitty-kernel` wheel standalone this mission (the added `kernel` dep is unresolvable until the follow-on publishes the kernel wheel) — else "groundwork only" breaks CI. A partial cutover is forbidden (ADR `2026-04-25-1` C-007); the cutover is the sequenced follow-on. | Active |
| C-003 | **Retrospective migration is backward compatible.** Legacy `charter.md`-only projects keep resolving their policy from frontmatter (secondary); `charter.yaml` governance wins when present. Provide the migration path; do not break existing projects. | Active |
| C-004 | **Classify reds vs the base; never green-wash.** The two `test_mission_status_aggregate` fail-closed reds ARE this mission's to fix (FR-007). Pre-existing unrelated reds (sync/coord P0s, and any not caused by this diff) are classified against the merge-base and left honest per red-main discipline; file/annotate per DIR-013. | Active |
| C-005 | **Coord topology hygiene.** Issue-matrix verdicts land in the coordination worktree; reviewer ≠ implementer; every folded issue gets an issue-matrix row + tracker comment naming the mission. | Active |

### Key Entities

- **`charter.yaml`** — `.kittify/charter/charter.yaml`; the deterministic, schema-guarded governance
  resolution authority; **takes precedence**.
- **`charter.md`** — `.kittify/charter/charter.md`; secondary rationale / free-form prose companion;
  readable, never a resolving override.
- **Charter path authority** — `charter/bundle.py` constants + `charter/charter_yaml_io`; the single
  charter-layer door every presence/path read routes through.
- **`load_meta_fail_closed`** — the **one** public fail-closed `meta.json` reader (typed `MissionMetaReadError`
  / `None`), reusing the existing `core/paths.py` authority (`MissionMetaReadError:506`, `_load_meta_fail_closed:660`)
  — a single home, not a competing second authority.
- **`spec-kitty-kernel` / `spec-kitty-doctrine` wheels** — packaging-closure groundwork manifests; not
  cut over from the root wheel this mission.
- **`doctrine-charter-tests.yml`** — the path-filtered CI workflow for the doctrine/charter layer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every charter **authority-presence / config** decision resolves from `charter.yaml`; a project
  with `charter.yaml` and `charter.md` **deleted** reports the charter present / resolvable across context,
  status, dispatch (already #3146), **dashboard (#3150)**, analysis-report, and retrospective policy. The
  `context.py:249` **prose**-presence gate is separately *pinned* (C-003): it renders on `charter.yaml`
  (precedence) **or** `charter.md` (readable secondary) — it is not an authority gate and is not retired.
- **SC-002**: `charter.yaml` **takes precedence** over `charter.md` for retrospective policy (yaml wins when
  both present); a legacy `charter.md`-only project still resolves (backward compatible).
- **SC-003**: A corrupt / non-dict `meta.json` fails closed (typed `MissionMetaReadError` or `None`) at
  every enumerated product reader; the two red `test_mission_status_aggregate` fail-closed tests go green;
  **no** raw `ValueError` leaks; the readers route through one `load_meta_fail_closed` authority.
- **SC-004**: The layer order stays clean — **zero** real upward edges (the `synthesize_pipeline`
  `import specify_cli` deleted); `test_layer_rules` green.
- **SC-005**: Packaging groundwork proven — `src/kernel/pyproject.toml` exists (`spec-kitty-kernel`, zero
  first-party deps); `src/doctrine/pyproject.toml` declares its `kernel` dep **and** ships `packs/`; a
  **non-vacuous** closure test fails if either is removed; and **no** root-wheel cutover was performed
  (kernel/doctrine/charter still in the root `packages`).
- **SC-006**: `doctrine-charter-tests.yml` covers `cli/commands/charter/**` (+ its tests); the CLI-reference
  parity gate **runs green** (both `REFERENCE_PATH` and `AGENT_REFERENCE_PATH` repointed to `docs/api/`, both
  docs regenerated — not merely un-skipped); #3102 confirmed shipped/closed.
- **SC-007**: A charter-wheel assessment + ADR draft is recorded, sequencing the #3101 kernel→doctrine→charter
  cutover as an explicit no-partial follow-on with the deferred issue set enumerated.

## Assumptions

- `charter/bundle.py` (`CHARTER_YAML`/`CHARTER_MD`) + `charter/charter_yaml_io.load_charter_yaml` are the
  canonical charter-layer path/read authority; `specify_cli`/`doctrine` should consume them, not re-derive
  the path.
- #3146 already retargeted the context/status/dispatch presence gates and shipped the
  `context_schema_version` tracking stamp; this mission extends the unification to the **residual** readers
  only — it does not re-open #3146's surfaces.
- The layer order `kernel <- doctrine <- charter <- glossary/runtime <- specify_cli` is already correct and
  CI-enforced by `tests/architectural/test_layer_rules.py`; only the one `synthesize_pipeline` edge violates
  it.
- The `#3140` product problem on this base is the mission-status aggregate fail-closed path (2 red tests)
  plus the ~25 unwrapped callers; the `_widen` site is already green (fixed by #3146).
- `#3101`'s wheel cutover is deferred; this mission does not build a publisher, remove packages from the
  root wheel, or add a release gate.
