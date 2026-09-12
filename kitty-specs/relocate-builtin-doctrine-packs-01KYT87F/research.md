# Research: Relocate Built-In Doctrine to packs/built-in (Phase 0)

## D-1: `resolve_pack_root(tier)` resolution strategy (the crux)

**Decision**: A filesystem resolver in `src/doctrine/pack_paths.py` with a deterministic search order:
1. **Env override** — `SPEC_KITTY_PACKS_ROOT` (test/ops escape hatch) → `<env>/<tier>`.
2. **Editable/repo checkout** — walk up from `Path(__file__)` to the first ancestor containing
   `packs/<tier>/`; return it. (Finds repo-root `packs/built-in/` in a dev checkout.)
3. **Installed distribution** — `Path(str(files("doctrine"))).parent / "packs" / <tier>` — i.e.
   `packs/` shipped as a **sibling of the installed `doctrine` package** in site-packages.
4. Else raise `PackRootNotFound(tier)` (fail-closed, never fall open to a wrong tree).

**Rationale**: `packs/built-in/` is **not** a Python package (and `built-in` has a hyphen, so
`files("packs.built-in")` is impossible) — so package-relative resolution cannot address it. A
filesystem resolver anchored on the already-resolvable `doctrine` package covers both layouts with no
new package. It stays in the doctrine layer (C-004 — no upward import). Org/project tiers reuse the
same helper (org root from `.kittify/config.yaml`, project from the project dir) → one seam (FR-005).

**Alternatives rejected**:
- *Ship `packs/built-in` as package data under `src/doctrine/`* → defeats "outside the code"; identical to today.
- *Make `packs` a Python package* → the `built-in` hyphen blocks module import; `assets`/`glossary_packs` names collide with kind dirs.
- *Rely on `importlib.metadata` distribution files* → brittle across editable vs wheel; the sibling-of-doctrine path is simpler and layout-symmetric.

## D-2: Packaging — ship `packs/built-in/` in wheel AND sdist

**Decision**: Root `pyproject.toml`:
- Wheel: `[tool.hatch.build.targets.wheel] force-include = { "packs" = "packs" }` (lands `packs/` as a
  site-packages sibling of `doctrine`, matching D-1 step 3). Remove the moved content's
  `src/doctrine/**` package-data globs.
- Sdist: extend `[tool.hatch.build.targets.sdist].include` (currently `src/**`) with `packs/**` —
  otherwise the sdist ships **zero** built-in content (squad finding).

**Rationale**: The pre-spec squad proved a build can go green while shipping an empty/partial artifact;
NFR-002 therefore gates on **exact path-set equality** of the built wheel *and* sdist against the
pre-move manifest, plus a clean-venv import — not on "build succeeds."

**Alternatives rejected**: data-files/`[project.scripts]`-style install (non-deterministic location);
separate `spec-kitty-doctrine-packs` distribution (that's option-(b)/Phase 2).

## D-3: Schemas STAY (C-003)

**Decision**: The 11 schemas remain in `src/doctrine/schemas/`. **Rationale**: they resolve via
`files("doctrine.schemas")` through `src/kernel/schema_utils.py` (the **kernel** layer, C-002-deferred)
and `agent_profiles/validation.py`; every artefact/profile validator depends on them; they are not
tiered/overlaid content, so moving them yields zero unification value and breaks all validation
(doctor red). Moving a schema is an explicit exception requiring a test that all 11 `load_schema` +
`_load_agent_profile_schema` still resolve — not in Phase 1.

## D-4: Parity proof = graph identity, not cardinality

**Decision**: Capture a **pre-move golden fixture** = `sorted(node.urn for node in graph.nodes)` +
`sorted((e.source, e.relation, e.target) for e in graph.edges)`; assert set-equality post-move.
Cardinality (324/892) is a smoke check only. **Rationale**: a dropped edge masked by an added one, or
a mis-URN'd node, passes a count check but fails identity (squad + doctrine-daphne golden-count-ledger
boundary). "Byte-identical" is also false (fragments carry `generated_at: STATIC`; merge order is
alphabetical over the source dir, so a path change can reorder) — assert the sets, not bytes.

## D-5: `missions/` disposition — RESOLVED: DEFER to Phase 1b

**Decision (post-plan squad, unanimous)**: **do not move `missions/` in Phase 1.** Its readers span
four layers — including `kernel/paths.py:111` (`files("doctrine")/"missions"`); routing a *kernel*
reader through the doctrine-layer `resolve_pack_root` is a **C-004 upward-import violation**, and
pushing the resolver into kernel is the C-002 kernel extraction we defer. Several readers are also
`Path(__file__)`-relative (invisible to a `files()`/string sweep), and live upgrade migrations read
missions content. **Graph identity is safe either way** — the mission-derived nodes
(`mission_step_contract`, `mission_type`, `template`, `action`) are authored *in* the moving 14
fragments, not scanned from the `missions/` tree at load (daphne, live-verified). Follow-on **Phase
1b** whose first task is the cross-layer missions-reader inventory.

## D-6: Layout — FLATTEN + repoint the regeneration surface

**Decision**: move `src/doctrine/<kind>/built-in/` → `packs/built-in/<kind>/` (drop the inner
`built-in/` level) for a clean pack layout, **and bring the graph-regeneration surface into scope**:
`_doctrine_root()` (detection + write-target) and `extractor.py`'s `_PATH_KIND_PATTERNS` (hardcoded
`src/doctrine/<kind>/built-in/…$`) + content walks must be repointed to the flattened home, else
`spec-kitty doctrine regenerate-graph` silently breaks (daphne blocker). **Alternative rejected**:
preserving the nesting (`packs/built-in/<kind>/built-in/`) minimizes extractor churn but yields a
redundant, ugly layout that defeats the clean-pack goal; the extractor repoint is bounded.

## D-7: Parity fixture = full-model projection (not bare triples)

**Decision**: the golden fixture pins nodes by `(urn, label, sorted(tags))` and edges by
`(source, relation, target, when, reason)`. **Rationale**: `DRGEdge.when` gates delivery (this repo's
live `suggests`/`when`-gated feature); a regeneration that drops or mutates `when` leaves the
URN/triple sets identical while changing traversal — the doctrine-daphne "silent relation change looks
untouched" trap. `git mv` preserves these, but the fixture must catch a regen/dedup mistake.
