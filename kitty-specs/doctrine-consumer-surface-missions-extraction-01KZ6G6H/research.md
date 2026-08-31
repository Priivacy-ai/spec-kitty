# Phase 0 Research: Missions/ Doctrine Tree Relocation & Gate Preconditions

No `[NEEDS CLARIFICATION]` markers exist in `spec.md` — every decision was resolved during specify/post-spec-squad/planning. This document grounds the plan's design in the actual current code (not the earlier research pass's characterization, some of which the squad corrected), and records the one Phase-0-relevant design decision left open by the spec.

## R1 — `test_no_dead_doctrine_paths.py`'s actual four-gate scope (grounds IC-01)

Verified directly against the file (841 lines):

| Gate | Scan function | Scope root | Discriminator-proof test |
|---|---|---|---|
| A | `scan_graph_monolith_paths` (:158) / `scan_graph_monolith_shipped` (:403) | `_SRC_ROOT` (`src/`, all of it) | `test_project_tier_graph_path_would_false_red_without_its_discriminator` (:498), **`test_forbidding_mention_would_false_red_without_its_discriminator` (:517)** |
| B | `scan_shipped_pack_paths` (:269) / `scan_shipped_pack_shipped` (:416) | `_SRC_ROOT` (`src/`, **not** `_DOCTRINE_ROOT` — also CLI-wide) | `test_shipped_prose_would_false_red_without_the_path_shape_discriminator` (:577), `test_frozen_seed_mirror_would_false_red_without_its_discriminator` (:598) |
| C | `scan_doctrine_cross_links` (:343) / `scan_doctrine_cross_links_shipped` (:429) | `_DOCTRINE_ROOT` (`src/doctrine/` — the only gate actually scoped here) | `test_code_example_links_would_false_red_without_their_discriminator` (:702), `test_placeholder_links_would_false_red_without_their_discriminator` (:716) |
| D | `test_no_live_doc_names_a_pre_move_builtin_path` (:822) | `docs/` (a third, distinct scope) | (self-contained; no separate discriminator-proof pair) |

**Decision**: IC-01 groups A+B together (both genuinely `src/`-wide today, confirmed by their own pinned exclusion lists naming `src/charter/...`, `src/specify_cli/...`, `src/runtime/next/...` — files entirely outside `src/doctrine/`), C separately (the only doctrine-content-scoped gate), and D gets its own named landing module. This corrects the original spec draft's "Gate A vs Gates B/C" grouping, which the post-spec squad found factually wrong.

**Rationale**: Grouping by actual scan root, not by shared filename, is the only grouping that doesn't silently narrow a gate's real coverage when the file splits.

**Alternatives considered**: Splitting all four into four separate modules (rejected — A and B share the same `_SRC_ROOT` scope and much of the same "is this a dead/forbidden path reference" scanning logic per their function signatures; a and B module together avoids duplicating that shared scanning machinery for no scope benefit).

## R2 — The NFR-003 proof's exact current shape and #3036's recorded fix (grounds IC-02)

`test_forbidding_mention_would_false_red_without_its_discriminator` (:517-535) — a **Gate A** proof, not Gate C: `forbidding_mentions` is a `GraphMonolithScan` field (:124) populated by `scan_graph_monolith_paths` (:158), and this test calls `scan_graph_monolith_shipped()` (:519). It therefore follows Gate A into the CLI-wide (A+B) module at the FR-001 split. It does:

```python
excluded = sorted((site.path, site.text) for site in scan.forbidding_mentions)
assert excluded == [
    ("packs/built-in/agent_profiles/doctrine-daphne.agent.yaml", "src/doctrine/graph.yaml"),
]
```

**Correction (post-plan review, 2026-08-04):** the original draft of this research quoted the pre-relocation path (`src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml`). That file was moved to `packs/built-in/agent_profiles/doctrine-daphne.agent.yaml` by the already-merged `relocate-builtin-doctrine-packs-01KYT87F` mission (commit `873832aa1`, 2026-08-01) — three days *before* this research was written. The live assertion above and the current `avoidance-boundary` mention (at that file's line 136) both use the corrected path; a `git stash`/edit against the old path fails outright (`pathspec ... did not match any file(s)`). All plan/spec references now use the current path.

Issue #3036's tracker comment (2026-07-28, author stijn-dejongh) explicitly rejects loosening this to tolerate an empty list, citing the file's own sibling test for discriminator A1:

```python
assert scan.project_tier, (
    "A1 excludes nothing, so it cannot be proven. Either the live project-tier "
    "path is gone (delete A1) or the pattern stopped matching it."
)
```

**Decision**: Redrive the proof from a `tmp_path`-planted synthetic fixture — a temp file carrying a forbidding mention — rather than the live `doctrine-daphne.agent.yaml`. This repo already has the exact idiom for this shape in the same file: `test_gate_a_rejects_a_planted_violation` (:538) and `test_gate_b_rejects_a_planted_violation` (:669) both construct a `tmp_path` fixture and assert the gate reds against it. IC-02's WP should follow that established local pattern, not invent a new one.

**Rationale**: Matches the recorded #3036 design decision verbatim; reuses an idiom already proven correct in the same file rather than a novel mechanism.

**Alternatives considered**: Loosening the live assertion to tolerate zero exclusions (explicitly rejected by #3036's own comment — "that remedy would make the problem worse").

## R3 — Kernel primitive's exact current entanglement (grounds IC-04)

`src/kernel/paths.py::get_package_asset_root()` (:63-117, the only public function in `__all__` for this purpose) contains, inside its body:

- `_looks_like_missions_root` (:76-84): hardcodes the mission-type vocabulary `("software-dev", "documentation", "research", "plan")` and the `templates`/`command-templates`/`mission-steps` directory shape.
- `_resolve_env_root` (:86-100): candidate list includes both `root / "src" / "doctrine" / "missions"` and `root / "src" / "specify_cli" / "missions"` literally.
- The canonical-location branch (:110-115): `importlib.resources.files("doctrine") / "missions"`.

`src/doctrine/pack_paths.py::_resolve_built_in()` (:177-203) is algorithmically parallel but *without* the domain-specific vocabulary: env override → `Path(__file__).resolve()` ancestor walk for an editable checkout → `doctrine_package_dir()` (a lazy `files("doctrine")` call, self-referential since this **is** the doctrine package) → fail-closed `PackRootNotFound`.

**Decision**: Extract the *shape* of `_resolve_built_in()` (env override → caller's-own-`__file__` ancestor walk → caller's-own-installed-package-sibling lookup → fail-closed) as the kernel primitive, parameterized by the caller's own anchor (its `__file__`/package name) and the sibling path being sought — not by a string literal naming `"doctrine"`. Both `kernel.paths.get_package_asset_root()` and `doctrine.pack_paths._resolve_built_in()` call the same primitive, each supplying their own anchor. This is safe because `packs/` ships as a site-packages sibling of *every* top-level package in the current monolith wheel (root `pyproject.toml`'s `force-include = {"packs" = "packs"}`), not specifically of `doctrine` — confirmed by reading the root `pyproject.toml`. That invariant holds only as long as C-001 keeps kernel/doctrine/charter in one wheel; a future standalone-kernel-wheel cutover (#3101, explicitly deferred) would need to revisit this, since a truly separate kernel wheel would not ship `packs/` alongside it. Noting this as a known limitation, not a blocker for this mission.

**Rationale**: Removes every doctrine-/specify_cli-identifying string from `src/kernel/`, satisfying the spec's SC-002/US1-AS2 requirement, while reusing (not duplicating) the already-correct 4-step resolution shape `pack_paths.py` already implements.

**Alternatives considered**: Leaving `kernel.paths` and `doctrine.pack_paths` as two parallel implementations (rejected per DM-01KZ6JH5 — the operator chose to converge now).

## R4 — `UnknownMissionTypeError`'s current message (grounds IC-07)

`src/charter/mission_type_profiles.py:506-514` (per direct verification during the post-spec squad pass) already carries an in-repo docstring reproducing the exact defect: activating only `my-custom` with no resolvable profile raises `"Unknown mission type 'my-custom'. Registered types: my-custom."` — the id appears in both the "unknown" clause and the "registered" list. This docstring was authored the same day as (and before) this spec, from a genuine reproduction during the PR #3175 landing pass.

**Decision**: Split the message into two independent facts — activation state and profile-loadability — so no sentence claims both "unknown" and "registered" of the same id. Exact wording is an implementation-time choice (e.g. "Mission type 'my-custom' is activated but has no loadable profile"), not fixed here.

## R5 — TIER-1 override templates' current staleness (grounds IC-08)

Verified: both `.kittify/overrides/missions/software-dev/command-templates/implement.md` (lines 10, 27, 29, 39, 41) and `review.md` (lines 10, 26, 28, 38, 40) still reference `spec-kitty constitution context` and raw `AgentProfileRepository(...)`/`DoctrineService(...)` construction. Both files were last touched 2026-04-17/04-22 — well before the PR #3175 sole-door landing (2026-08-04), confirming that landing did not touch them (it changed production `src/` construction sites, not this repo's own dogfood command-template overrides).

**Decision**: Rebase both files against the current canonical templates (which already demonstrate `charter.doctrine_service_builder.build_activation_aware_doctrine_service`) or delete either file if it no longer diverges usefully from the canonical template it overrides.

## R6 — Cross-layer `missions/` reader inventory: method, not result (grounds IC-03)

The inventory itself is FR-003's deliverable, not pre-computed here (doing so would defeat the point of a checkable, committed artifact). Research-phase guidance for the implementer:

- **Search method: trace symbol usage, not path literals.** A bare `grep -rn "doctrine.missions\|doctrine/missions\|specify_cli.missions\|specify_cli/missions" src/ tests/ --include="*.py"` sweep is a starting point, but the post-plan review found it misses load-bearing sites — `doctrine/missions/repository.py`'s own `files("doctrine") / "missions"` call (line 107, R7 below) was found only via an *unrelated* backward-compat-alias comment nearby, not the grep pattern itself. Trace every symbol imported from `doctrine.missions.*` (and every caller of `MissionTemplateRepository`) to its actual implementation, not just path literals.
- Cross-check against `src/kernel/paths.py` (R3), `src/doctrine/pack_paths.py`, `src/doctrine/missions/repository.py` (R7), `src/doctrine/drg/migration/extractor.py` (R8), any other `charter` reader of mission-type content, and `src/specify_cli/upgrade/migrations/*.py` (upgrade migrations are historically easy to miss — they read old layouts by design).
- Record shape: per reader, `(file:line, current path assumption, decision: move|stay|repoint, rationale)` — matching the structure the ADR (`docs/adr/3.x/2026-08-02-1-charter-wheel-assessment.md`) itself used for its own deferred-issue table.
- The prior `relocate-builtin-doctrine-packs-01KYT87F` mission's own reader-inventory approach (for the sibling `agent_profiles/`/`directives/`/etc. relocation) is confirmed still on `main` and worth reading as a direct precedent for format — its `occurrence_map.yaml` uses the same directory-level `moves:` shape this mission's does.
- **Two sites are already known** (found during this mission's own post-plan review, not left for FR-003 to discover from scratch) — see R7 and R8.

## R7 — `MissionTemplateRepository.default_missions_root()`: the already-promoted authority (grounds IC-03, IC-04)

`src/doctrine/missions/repository.py::MissionTemplateRepository.default_missions_root()` (a `@classmethod`, ~line 97-108) is **not** a fourth independent implementation to discover — it is the authority the `charter-sole-door-bypass-closure-01KZ3WAA` mission's own WP06 already promoted. That WP's regression test, `tests/charter/test_missions_root_authority.py` (docstring, lines 1-22), states verbatim:

> Before this WP, 3 sites independently constructed the shipped `src/doctrine/missions` root: (1) `charter.mission_type_profile_repository.builtin_missions_root()`, (2) `specify_cli.runtime.home.get_package_asset_root()`'s `dev_roots` fallback, (3) `doctrine.missions.repository.MissionTemplateRepository.default_missions_root()` — the `importlib.resources`-based, wheel-safe implementation. WP06 retargets (1) and (2) onto (3) as the ONE promoted authority... **Full convergence onto `doctrine.pack_paths.built_in_dir` remains deferred to GitHub issue #3091** (`pack_paths` has no `missions/` content directory today) — this WP does NOT claim that convergence, and these tests do not exercise it.

Issue #3091 is this mission. `default_missions_root()`'s own body (`importlib.resources.files("doctrine") / "missions"`, with a bare fallback to `Path(__file__).parent`) is algorithmically the same entangled shape FR-004 already targets in `kernel.paths`, just without the mission-type-vocabulary helpers.

**Decision**: `MissionTemplateRepository.default_missions_root()` is a third call site converging onto the FR-004 primitive, alongside `kernel.paths.get_package_asset_root()` and `doctrine.pack_paths._resolve_built_in()`. This closes the exact convergence the sole-door mission's own test explicitly deferred to this issue — not new scope, but the completion of already-declared scope.

## R8 — DRG extractor's `_missions_root()`: reads the pre-relocation location by explicit assumption (grounds IC-03, IC-05)

`src/doctrine/drg/migration/extractor.py::_missions_root(doctrine_root)` (~line 103-120) resolves `missions/` for DRG-fragment generation. Its own docstring states:

> Missions were **not** relocated by the flatten (WP03 left `missions/` and `schemas/` in place), so they still live inside the `doctrine` package... A flattened **pack** root (`packs/built-in`) does not carry `missions/`, so the package's own `missions/` is resolved via `files("doctrine")`.

This mission's FR-005 directly falsifies that assumption once the data content moves. `packs/built-in/mission_type.graph.yaml` and `packs/built-in/mission_step_contract.graph.yaml` are **generated** from this resolver's output (via `extract_artifact_edges`/`generate_graph`), not hand-authored — `tests/doctrine/drg/test_regen_roundtrip.py`'s `test_regenerated_fragments_match_on_disk_full_projection`/`test_regenerated_fragments_are_byte_identical` will fail loudly if the extractor is left unrepointed, but the repoint and the subsequent regeneration-and-diff are themselves a stated task, not something to discover only via that test's red.

**Decision**: `_missions_root()` is repointed as part of FR-005 (co-landed with the data-content move, not a separate step — moving the data without repointing this reader is exactly the kind of broken-intermediate-state IC-05 exists to avoid). The two dependent graph fragments are regenerated and diffed against committed state in the same change.

## R9 — `src/doctrine/missions/` is a Python package with data content mixed in, not a pure data directory (grounds FR-003/FR-005 scope)

Confirmed directly (directory listing, not assumed): the directory holds 11 top-level `.py` modules (`repository.py`, `mission_type_repository.py`, `mission_step_repository.py`, `step_projection.py`, `models.py`, `action_index.py`, `primitives.py`, `step_contracts.py`, `step_offer_seam.py`, `glossary_hook.py`, `__init__.py`) alongside data: `mission_types/` (per-type `.yaml` profiles), `mission-steps/` (per-type step-prompt directories), `built_in_step_contracts/` (step-contract YAML), four per-type content directories (`documentation/`, `plan/`, `research/`, `software-dev/`), and `README.md`. Multiple existing call sites do `from doctrine.missions.repository import ...`-shaped imports — these must keep working. `packs/built-in/` cannot host Python modules: the hyphenated name is not a legal package identifier, and `pack_paths.py`'s own docstring establishes every sibling kind directory ships YAML/MD content only.

**Decision**: only the data subdirectories relocate to `packs/built-in/missions/`; the `.py` modules stay in `src/doctrine/missions/` as an ordinary Python package, repointed (via the FR-004 primitive, through `MissionTemplateRepository.default_missions_root()`) to read data from the new external root. `plan.md`'s Project Structure and this mission's spec.md were both corrected to state this explicitly rather than the ambiguous "`missions/` deleted" framing the earlier draft used.

**WP03's completed cross-layer reader inventory** (FR-003/SC-007 deliverable) lives at [`docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md`](../../docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md) — a set of readers require repoint (that table is the authority; do not hard-code a count here, since it drifts as sites are found), including two the post-move ancestor-walk self-match trap still catches even after WP04's convergence; see that document for the full move/stay/repoint table WP05 must consume.
