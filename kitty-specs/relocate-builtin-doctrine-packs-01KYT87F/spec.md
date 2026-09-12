# Mission Specification: Relocate Built-In Doctrine to packs/built-in

**Mission Branch**: `feat/relocate-builtin-doctrine-packs`
**Created**: 2026-07-30
**Status**: Draft (post-spec squad hardened)
**Input**: Relocate the built-in doctrine artefact *contents* (data files) out of `src/doctrine` into a top-level `packs/built-in/` directory, and give all three tiers (built-in → org → project) a single shared **resolution seam**. Content (data) only — no doctrine `.py` code moves. Loader/schema *convergence* is explicitly a deferred Phase 2.

## Context & Motivation

Today the shipped built-in doctrine content lives *inside* `src/doctrine/` and is located by
package-relative `importlib.resources.files("doctrine…")` anchors. This mission relocates that
content to a top-level `packs/built-in/` and introduces **one shared path resolver** so built-in,
org, and project tiers resolve through a single seam — making built-in the uniform base tier at the
**resolution-path layer**, and drawing the consumer seam for the open-core delivery window, without
extracting the doctrine *code*.

### Scope boundary (set by the post-spec adversarial squad, 2026-07-30)

The squad proved that routing built-in through the *same loader* org packs use
(`load_org_pack`) is not a relocation but a **schema + merge redesign**: org packs are a single
`drg/fragment.yaml` with `_OrgDRGNode` (id, plural kind, downstream-minted URN); built-in is **14**
`*.graph.yaml` fragments with `DRGNode` (pre-minted URN, singular kind) returned as a `DRGGraph`
that is the *invariant-bearing base* of `merge_three_layers`. Converging them re-architects
`merge_three_layers` and risks the 324/892 parity — the option-(b) work C-002 defers.

**This mission is Phase 1: relocate + repoint + one shared *path* resolver.** True loader/schema
convergence is **Phase 2** (a separate follow-on mission). See C-002.

## Domain Language *(canonical terms)*

- **Built-in / org / project tiers** — the three doctrine layers, merged base→overlay (`built-in → org → project`).
- **`packs/built-in/`** — the new top-level home for the built-in pack content.
- **Resolution seam** — the code that locates a tier's content on disk. After this mission a single
  `resolve_pack_root(tier)` path helper is that seam for all tiers.
- **Content inventory** — the enumerated set of every `files("doctrine*")` (and literal
  `src/doctrine/...`) reader, each with a **move / stay** disposition (FR-002).
- **Graph identity** — the *set* of node URNs and the *set* of `(source, relation, target)` edge
  triples of `load_built_in_graph()` (not cardinality). Parity anchor: 324 nodes / 892 edges.
- Avoid: "unify the loader / same load path as org packs" for Phase 1 — that is the deferred Phase 2
  schema convergence, not this relocation. Phase 1 unifies the **path resolver**, not the loader.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Doctrine runtime resolves built-in from packs/built-in with graph identity preserved (Priority: P1)

After relocation, the doctrine runtime loads all built-in content from `packs/built-in/` and the
composed built-in DRG is **identical** — same node-URN set and same edge-triple set — proving the
move changed *where* content lives, not *what* it is.

**Why this priority**: A silent graph change is the highest-severity failure. Identity (not
cardinality) is the proof.

**Independent Test**: Capture a pre-move golden fixture of `load_built_in_graph()` node-URN set +
edge-triple set; assert set-equality after the move. Fully testable without any consumer.

**Acceptance Scenarios**:

1. **Given** the built-in content has moved, **When** `load_built_in_graph()` runs, **Then** its node-URN set and edge-triple `(source, relation, target)` set equal the captured pre-move golden fixture exactly (cardinality 324/892 is a consequence, used only as a smoke check).
2. **Given** the move, **When** `spec-kitty doctor doctrine --json` runs, **Then** `AgentProfileRepository.skipped_profiles == []`, 18/18 built-in profiles valid, glossary term/pack count unchanged.
3. **Given** the FR-009 guard, **When** it runs, **Then** every resolved built-in path is rooted at `packs/built-in/` and no built-in artefact resolves from inside `src/doctrine/` (paired assertion — scenario 2 alone does not prove relocation, since the old path also reports 18/18).

---

### User Story 2 - All tiers resolve through one shared path seam (Priority: P2)

Built-in, org, and project tiers each resolve their on-disk root through a single
`resolve_pack_root(tier)` helper, so there is one resolution seam instead of a built-in-specific
`files("doctrine.<kind>")` anchor scattered across repositories.

**Why this priority**: This is the durable value (uniform pack authoring) realized at the
resolution-path layer — feasible in one mission, unlike loader convergence (Phase 2).

**Independent Test**: A structural test asserts **no** repository or reader resolves built-in
content via `files("doctrine.<kind>")`; all route through `resolve_pack_root`.

**Acceptance Scenarios**:

1. **Given** the shared resolver, **When** any tier's content is located, **Then** it is located via `resolve_pack_root(tier)` (one entry point), not a per-kind package anchor.

*(Removed: any claim that built-in's on-disk shape matches the org/project pack contract — that is Phase 2.)*

---

### User Story 3 - Packaged and editable installs both resolve packs/built-in (Priority: P1)

`packs/built-in/` resolves correctly in **both** an editable/repo checkout (repo-root `packs/`) and
an installed distribution (wheel + sdist), with zero missing-file errors.

**Why this priority**: `packs/built-in/` sits *outside* the `doctrine` Python package, so the old
`files("doctrine")` anchor finds it in *neither* layout. Getting dual-layout resolution + packaging
right is the crux of the move, not an edge case.

**Independent Test**: A two-layout matrix — (a) editable checkout; (b) built wheel installed in a
clean venv — each runs `spec-kitty doctor doctrine` and `load_built_in_graph()` and resolves built-in
with 0 missing-file errors.

**Acceptance Scenarios**:

1. **Given** the built **wheel** and the built **sdist**, **When** each is inspected, **Then** the set of relative paths under `packs/built-in/` equals the pre-move file manifest exactly (set-equality, not `≥`; duplication in `src/doctrine` would fail FR-009).
2. **Given** a clean-venv install of the wheel, **When** `spec-kitty doctor doctrine` runs from a cwd with no repo `src/`, **Then** built-in resolves with 0 `FileNotFoundError`.
3. **Given** an editable checkout, **When** `load_built_in_graph()` runs, **Then** it resolves `packs/built-in/` from the repo root.

### Edge Cases

- A built-in tree left behind in `src/doctrine/` (partial move) → FR-009 filesystem-manifest assertion fails.
- A moved asset duplicated (left in `src/` *and* copied to `packs/`) → FR-009 + NFR-002 exact-set-equality fails (a `≥` check would hide it).
- An overlay overriding a moved built-in URN → tier precedence + `_tag_source` provenance unchanged (FR-008).
- A relocated asset under a git-ignored path silently dropped from wheel/sdist → NFR-002 manifest parity + `.gitignore` audit (FR-011) catch it.
- A schema referenced via `files("doctrine.schemas")` → schemas **stay** (C-002); validation unaffected.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Relocate built-in tiered content to packs/built-in | As a doctrine maintainer, I want the 9 `<kind>/built-in/` content dirs (**flattened**: `built-in/` level dropped → `packs/built-in/<kind>/`) and the **14** root `*.graph.yaml` fragments (authoritative glob) relocated from `src/doctrine/**` to `packs/built-in/**` via `git mv` (history preserved), data files only. `missions/` and `schemas/` are **not** in the move-set (deferred — C-002/C-003). | High | Open |
| FR-002 | Content-inventory disposition artifact | As a maintainer, I want an enumerated inventory of **every** `files("doctrine*")` reader and every literal `src/doctrine/...` path (in doctrine, `specify_cli`, and `charter`) — including `skills/`, `model_task_routing/`, top-level `templates/`, the `missions/` tree, and `schemas/` — each marked **move** or **stay** with rationale, so nothing is silently omitted or half-moved. | High | Open |
| FR-003 | Repoint the DRG graph seam | As the runtime, I want `built_in_graph_source()` to resolve the 14 fragments from `packs/built-in/`, so the built-in graph loads from the new home. | High | Open |
| FR-004 | Repoint every moved-tree reader | As the runtime, I want each content repository's `built_in_dir` default and every reader of a **move**-dispositioned tree repointed to `packs/built-in/…`, so no moved content is still read from inside the package (incl. the hardcoded `src/doctrine/agent_profiles/built-in` string in `specify_cli`). | High | Open |
| FR-005 | Single shared resolve_pack_root(tier) seam | As a maintainer, I want one shared path helper through which built-in/org/project roots resolve, replacing scattered `files("doctrine.<kind>")` content anchors — a uniform *resolution* seam (no schema convergence). | High | Open |
| FR-006 | Editable + installed dual resolution | As a user in either layout, I want `resolve_pack_root("built-in")` to locate `packs/built-in/` in an editable checkout (repo-root `packs/`) **and** an installed distribution, verified by a two-layout test matrix. | High | Open |
| FR-007 | Ship packs/built-in in wheel AND sdist | As an installed-CLI user, I want `packs/built-in/` shipped in **both** the monolith wheel and the sdist (the sdist `include` is `src/**`, which excludes a top-level `packs/`), replacing the moved content's `src/doctrine` package-data globs. | High | Open |
| FR-008 | Preserve overlay precedence & provenance (behavioral) | As the runtime, I want tier precedence and provenance pinned by behavior: on a synthetic org+project overlay, (a) a higher tier overriding a built-in URN wins (`built-in < org < project`), (b) `_tag_source` tags a moved built-in URN as `built-in` (not the new path/tier), (c) no built-in edge is dropped when an overlay adds edges. | High | Open |
| FR-009 | Regression guard: nothing resolves from src/doctrine (three-part) | As a maintainer, I want a guard asserting (1) *filesystem* — the moved trees are **absent** under `src/doctrine/**` (exact set vs the pre-move manifest), (2) *resolved-path* — every built-in resolution is `is_relative_to(packs/built-in)`, (3) *anchor* — no `files("doctrine.<kind>")` content anchor remains (AST/grep). | High | Open |
| FR-010 | Update the tests the move breaks | As a maintainer, I want every test the move breaks updated in-scope, not left red: `test_builtin_graph_seam.py` (`name=="doctrine"`→`"built-in"`), `test_wheel_packaging.py` (hardcoded paths → **flattened** `packs/built-in/<kind>/` + invert legacy-absent), `tests/architectural/test_no_dead_doctrine_paths.py` (pins the exact `doctrine-daphne.agent.yaml` path; interacts with #3036 — note, do not fix), and the regen-parity gates `test_graph_sharding_equality`, `test_sharding_silent_degrade`, `migration/test_extractor(_projection)`, `test_path_ref_resolver`. | High | Open |
| FR-011 | Live-reference sweep + docs regen + gitignore audit | As a maintainer, I want live (non-ADR) references to moved `src/doctrine` paths swept/updated, the docs retrieval-index/completion-manifest regenerated, and a `.gitignore` audit that no `packs/`/`built-in/` pattern swallows the new tree — leaving historical ADR snapshots immutable. | Medium | Open |
| FR-012 | Migration note + CHANGELOG | As a downstream pack author, I want a migration note (mirroring the shared-package-boundary cutover doc) and a CHANGELOG entry for the path change (DIR-009). | Medium | Open |
| FR-013 | Repoint the graph-regeneration surface | As a maintainer, I want `_doctrine_root()` (detection + write-target) and `extractor.py`'s `_PATH_KIND_PATTERNS` + content walks repointed to the flattened `packs/built-in/<kind>/` home, so `spec-kitty doctrine regenerate-graph` still works after the move (fragments are generated, not hand-maintained). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Graph identity (full projection) | Post-move `load_built_in_graph()` **equals** a captured pre-move golden fixture as *full-model projections*: nodes by `(urn, label, sorted(tags))` and edges by `(source, relation, target, when, reason)` — **not** bare URN/triple sets, since `when`-gated delivery is a live feature a regen could silently drop. Cardinality 324/892 is a smoke consequence only. | Correctness | High | Open |
| NFR-002 | Packaging completeness (exact) | The built **wheel and sdist** each carry a set of `packs/built-in/` relative paths **equal** to the pre-move file manifest (set-equality, not `≥`); a clean-venv install resolves built-in with **0** missing-file errors. | Reliability | High | Open |
| NFR-003 | No behavioral drift | Full `tests/doctrine/`, `tests/charter/`, `tests/architectural/` + `tests/architectural/test_no_legacy_terminology.py` pass with **0** new failures attributable to the move. | Reliability | High | Open |
| NFR-004 | Type & lint clean | `mypy --strict` and `ruff` pass with **0** new issues/warnings; no new suppressions (DIR-006). | Maintainability | High | Open |
| NFR-005 | Resolution uniformity | **0** built-in content reads via `files("doctrine.<kind>")` remain; all tier roots resolve via the single `resolve_pack_root` seam (precise, testable). | Maintainability | Medium | Open |
| NFR-006 | Doctor full health | `spec-kitty doctor doctrine --json` reports **full** health — `skipped_profiles == []`, 18/18 profiles valid, **no `org_drg` errors, no skipped glossary packs**, unchanged glossary counts (glossary_packs/built-in + assets/built-in are moved dirs; a profiles-only gate would miss their degradation). A *separate* gate from NFR-001 (doctor emits no node/edge counts). | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Content-only move | No doctrine `.py` code moves out of `src/doctrine`; only artefact/data files relocate. | Technical | High | Open |
| C-002 | Deferred to Phase 1b / Phase 2 | Out of scope: the **`missions/` tree** (Phase 1b — its readers span the kernel layer + `__file__`-relative idioms that cannot route through the doctrine-layer resolver without a C-004 violation); converging built-in onto the org-pack loader/schema + re-architecting `merge_three_layers` (Phase 2); a standalone `spec-kitty-doctrine` code wheel; `kernel` extraction. | Technical | High | Open |
| C-003 | Schemas stay | The 11 schemas **remain** in `src/doctrine/schemas/` — they resolve via `files("doctrine.schemas")` in the **kernel** layer (C-002-deferred), are not tiered content, and moving them breaks all validation. Moving a schema is an explicit, justified exception requiring a test that all 11 `load_schema` + `_load_agent_profile_schema` resolve. | Technical | High | Open |
| C-004 | Layer direction (C-004 invariant) | The shared resolver stays in the doctrine layer; doctrine must not import `charter`/`specify_cli`, and must not import the `kernel` schema resolver upward beyond today's coupling (preserve `test_layer_rules`). | Technical | High | Open |
| C-005 | Follow prior art | Follow `shared-package-boundary-cutover-01KQ22DS` + ADR `docs/adr/3.x/2026-04-25-1` (architectural guard test, packaging-lock/contract test, clean-install verification, migration note). | Technical | High | Open |
| C-006 | No runtime shim | A migration note is required; a runtime deprecation shim is not (no external consumer of the old path exists yet). | Technical | Medium | Open |
| C-007 | Branch & PR discipline | Consolidate on `feat/relocate-builtin-doctrine-packs` (based on `upstream/main`); PR **upstream** to `Priivacy-ai/spec-kitty`; never push directly to `origin/main`. | Process | High | Open |

### Key Entities

- **Built-in pack** — the relocated `packs/built-in/` content tree; the base tier.
- **Content inventory** — the per-reader move/stay disposition artifact (FR-002); the plan's occurrence-map input.
- **Shared path resolver** — `resolve_pack_root(tier)`, the single resolution seam (FR-005).
- **Graph identity fixture** — captured pre-move node-URN set + edge-triple set (NFR-001).
- **Composed DRG** — the built-in graph (324/892 anchor) whose identity must be preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Post-move `load_built_in_graph()` has **identical** node-URN and edge-triple sets to the pre-move golden fixture (not merely 324/892), and `skipped_profiles == []`.
- **SC-002**: **0** built-in artefacts resolve from inside `src/doctrine/` (FR-009 three-part guard); **0** `files("doctrine.<kind>")` content anchors remain (NFR-005).
- **SC-003**: Both wheel and sdist carry the built-in content at **exact** path-set parity with the pre-move manifest; a clean-venv install and an editable checkout each resolve built-in with **0** missing-file errors.
- **SC-004**: Every `files("doctrine*")` reader in the content inventory (FR-002) is accounted for as move or stay — **0** unclassified readers; the two breaking tests (FR-010) are updated and green.

## Assumptions

- **Target on-disk layout** under `packs/built-in/` (per-kind mirror) is a `/plan` design detail; Phase 1 assumes a **structure-preserving mirror** (org-fragment *shape* convergence is Phase 2).
- The move-set and every reader disposition are enumerated authoritatively during `/plan` (the FR-002 content inventory / occurrence map), not assumed here; the baseline metrics (324 nodes / 892 edges; 18/18 profiles; 108 glossary terms; 14 fragments) were measured live on this branch and are the parity anchors.
- Schemas **stay** by default (C-003); any move is an explicit plan-time exception with its own validation test.
