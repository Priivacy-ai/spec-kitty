---
affected_files: []
cycle_number: 2
mission_slug: relocate-builtin-doctrine-packs-01KYT87F
reproduction_command:
reviewed_at: '2026-07-31T03:12:37Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP08
---

# WP08 review — cycle 1: REJECT

One blocking issue: a WP08-owned test is **red at HEAD**. Everything else in the
committed scope is correct (see "What passed" below), so this is a single,
localized fix.

## Blocking issue — owned Gate D guard fails on its own migration note

The new Gate D guard added by T024 —
`tests/architectural/test_no_dead_doctrine_paths.py::test_no_live_doc_names_a_pre_move_builtin_path`
— fails at HEAD:

```
FAILED tests/architectural/test_no_dead_doctrine_paths.py::test_no_live_doc_names_a_pre_move_builtin_path
Live documentation still names a pre-move built-in path...
  docs/migrations/relocate-builtin-doctrine-packs.md:30:| Built-in agent profiles | `src/doctrine/agent_profiles/built-in/*.agent.yaml` | ... |
  docs/migrations/relocate-builtin-doctrine-packs.md:31:| Built-in glossary packs | `src/doctrine/glossary_packs/built-in/*.glossary-pack.yaml` | ... |
  docs/migrations/relocate-builtin-doctrine-packs.md:142:  still carry `guide_path: src/doctrine/toolguides/built-in/<FILE>.md` in their
```

Root cause: the guard's `_MOVED_BUILTIN_DOC_RE` scans **all of `docs/`** except
the three subtrees in `_GUARD_DOC_EXCLUSIONS` (`docs/adr`, `docs/plans`,
`docs/development/3-2-docs-retrieval-index.yaml`). But the migration note
**created by this same WP** legitimately names the retired paths in its old→new
mapping table (lines 30–31) and in a follow-on note (line 142). A migration note
*must* name the old paths — that is its purpose — yet the guard forbids them.
The guard and its own reference doc contradict each other, so the owned test is
red.

Both files are owned by WP08 (`test_no_dead_doctrine_paths.py` and
`docs/migrations/relocate-builtin-doctrine-packs.md`), so this is a
self-inflicted red, not an environmental/baseline one (regen check is clean,
graph is 324/892, ruff is clean — see below).

### Suggested fix
Exclude the migration note from the guard, exactly as `docs/adr` is excluded and
for the same reason — its `src/doctrine/...` references are *documentation of the
move*, not live pointers to where doctrine now lives. Add to
`_GUARD_DOC_EXCLUSIONS`:

```python
#:  * docs/migrations/relocate-builtin-doctrine-packs.md -- the migration note
#:    itself documents the old->new path mapping; its src/doctrine/ references
#:    describe what moved, they are not live pointers.
":(exclude)docs/migrations/relocate-builtin-doctrine-packs.md",
```

Then re-run the guard and confirm it is green:
```
PWHEADLESS=1 python -m pytest tests/architectural/test_no_dead_doctrine_paths.py -q
```

(Do **not** weaken the regex or strip the old paths out of the mapping table —
the table is the correct content for a migration note. Scope the exclusion to the
note, keeping the guard live for every other doc.)

## What passed (do not re-do)

1. **Breaking tests** — `test_builtin_graph_seam` (`name` "doctrine"→"built-in"),
   `test_wheel_packaging` (flattened `packs/built-in/<kind>/…`, inner `built-in`
   correctly dropped, legacy-absent inverted to `doctrine/agent_profiles/built-in/`),
   `test_no_dead_doctrine_paths` discriminator repoints — all path-literal only,
   assertion structure unchanged.
2. **Extra test-literal reds** — `test_sharded_layout`, `test_unknown_kind_fails_loudly`,
   `test_model_strictness_roundtrip`, `test_instantiates_edges`,
   `test_no_authored_applies_edge`, `test_errors`, `test_inline_ref_rejection` —
   all green (158 passed in the scoped run), path-literal only, no vacuity-floor
   weakened.
3. **No assertion weakened** — diff is path-literal + comment only across every
   changed test.
4. **`errors.py` migration_hint** — legit production fix (`src/doctrine/<kind>.graph.yaml`
   → `packs/built-in/<kind>.graph.yaml`), matching test updates green.
5. **Over-reach reverted** — the `excise-doctrine…schema.json` is NOT in the commit.
6. **Graph integrity** — `load_built_in_graph()` → 324 nodes / 892 edges;
   `spec-kitty doctrine regenerate-graph --check` exit 0 (fresh, no drift). Prose
   edits to `packs/built-in/toolguides/*.md` + `src/doctrine/templates/**` did not
   desync fragments.
7. **Migration note + CHANGELOG** — both present; migration note mirrors
   shared-package-boundary-cutover and records the two follow-ons.
8. **ruff** — clean on changed files.

## Anti-pattern checklist
- Dead code: N/A (no new production module) · Synthetic-fixture: PASS ·
  Silent empty return: PASS · FR coverage: PASS · Frozen surface: PASS (ADR
  snapshots untouched) · Locked decision: PASS · Shared-file ownership: PASS ·
  Production fragility: PASS.

Only item 8 (the committed guard) blocks: the guard exists and asserts the right
thing, but is currently **red** against the committed tree. Fix the exclusion and
resubmit.
