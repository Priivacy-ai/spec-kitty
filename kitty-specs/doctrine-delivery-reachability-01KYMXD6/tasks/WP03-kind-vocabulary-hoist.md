---
work_package_id: WP03
title: Kind vocabulary hoist, totality, and scaffold parity
dependencies: []
requirement_refs:
- C-001
- C-006
- C-010
- FR-006
- FR-007
- NFR-002
- NFR-005
planning_base_branch: feat/doctrine-delivery-reachability
merge_target_branch: feat/doctrine-delivery-reachability
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-delivery-reachability. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-delivery-reachability unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-doctrine-delivery-reachability-01KYMXD6
base_commit: af1d7af8e738374f9e6c87361ca9ef68a90d2212
created_at: '2026-07-28T21:55:02.009749+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
phase: Phase 1 - Foundation
history:
- at: '2026-07-28T19:48:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/artifact_kinds.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/artifact_kinds.py
- src/charter/kind_vocabulary.py
- src/charter/pack_manager.py
- src/specify_cli/cli/commands/doctrine.py
- tests/doctrine/drg/test_kind_mapping_totality.py
- tests/doctrine/test_artifact_kinds.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# WP03 — Kind vocabulary hoist, totality, and scaffold parity

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the profile named in the frontmatter, and behave
according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

Resolve it with **`spec-kitty agent profile show python-pedro`** — the *resolved* definition, with
lineage and `enhances`/`overrides` applied. **Do not read the raw `*.agent.yaml`**: it is the
unresolved base and drops exactly the doctrine this mission delivers. Use `spec-kitty agent profile
list` only to discover a profile when none is named.

---

## Objective

One project-tier kind mapping, hosted at the lowest layer and imported downward, with the totality
guard able to **see every copy** — and `doctrine new --kind asset` writing to the directory the
resolver actually reads.

This is a **class-closure** work package (C-010). The repository already ships the mechanism —
`tests/doctrine/drg/test_kind_mapping_totality.py` — and the instruction is to *extend* it, not to
hand-patch four dicts. A patch that adds `asset` to every copy and never hoists **satisfies the
letter and misses the point**; see the DoD.

## Context you need before starting

### The mapping is restated four times, in three conventions

`src/doctrine/artifact_kinds.py`'s module docstring already declares that no second kind enumeration
may exist. There are four:

| Site | Key type | Keyed by | Visible to the guard? |
|---|---|---|---|
| `src/doctrine/service.py:19` | `dict[str, str]` | **plural** strings | **No — invisible** |
| `src/specify_cli/cli/commands/doctrine.py:442` | `dict[str, str]` | singular strings | **No — invisible** |
| `src/charter/kind_vocabulary.py:79` | `dict[ArtifactKind, str]` | enum | Yes, but **exempted** |
| `src/charter/pack_manager.py:136` | `dict[ArtifactKind, str]` | enum | Yes, but **exempted** |

The guard's AST scan matches only `EnumName.MEMBER` attribute keys, so the two string-keyed copies are
**not discovered at all** — a different and worse failure than exemption. All four are `.get(x, …)`
defaulted, with three different fallbacks.

**`src/doctrine/service.py` is NOT yours** — it belongs to WP04, which converts it as part of wiring
the asset repository. Coordinate: your hoist must land the canonical mapping WP04 then consumes.

### The guard cannot detect disagreement

It checks each dict independently against the enum. Two copies can both be total and still disagree.
**The class-closing mechanism for "scaffold and resolver disagree" is the hoist**; the guard is the
ratchet that keeps it total afterwards. Write the DoD accordingly.

### Scaffold parity targets two surfaces the plan first missed

`doctrine new --kind asset` fails **two dicts upstream** of `:442`:

1. `:606` rejects against `_CANONICAL_KIND_SINGULAR_TO_PLURAL` (`:431`) — 8 of 12 kinds, no `asset`.
   This dict also **duplicates `ArtifactKind._PLURALS`**, eleven lines above the one the plan named.
2. `:464` `_stub_template` is an **eight-arm `if`-chain** over kind strings ending in `raise
   ValueError`. It is a kind projection **no dict-scanning guard can ever see**.

`:442` is consulted only at `:626`, after both gates. Meanwhile `_SUFFIX_TO_KIND` (`:673`) already has
`.asset.yaml` — which is exactly the validate/scaffold asymmetry this WP closes.

---

## Subtasks

### T012 — Hoist the canonical project-tier kind mapping

**Steps**:
1. Add the canonical project-tier directory mapping to `src/doctrine/artifact_kinds.py`, keyed by
   `ArtifactKind`, covering **all** kinds including `asset`.
2. Declare the canonical form explicitly in the module docstring — singular vs plural, and what the
   fallback is (or that there is none; prefer fail-closed).
3. `doctrine` is the lowest layer, so charter and specify_cli import **down**. This is C-001-legal in
   all three directions.

**Validation**: `pytest tests/doctrine/test_artifact_kinds.py -q`.

### T013 — Convert the CLI copy to `ArtifactKind` keys

**Steps**:
1. Convert `src/specify_cli/cli/commands/doctrine.py:442` from `dict[str, str]` to consuming the
   hoisted authority.
2. Update its call site at `:626`; each of the three sites has a different `.get` fallback — replace,
   do not preserve.

### T014 — Retire the two charter copies and drop their exemptions

**Steps**:
1. Point `charter/kind_vocabulary.py:79` and `charter/pack_manager.py:136` at the hoisted authority.
2. **Remove their entries from `_EXEMPT_GET_PARTIALS`** in `tests/doctrine/drg/test_kind_mapping_totality.py:63-79`.
   Leaving the exemptions while removing the partiality is the "green but pointless" outcome.
3. That file has tests proving the exemption mechanism does real work
   (`test_naive_total_only_guard_would_false_fail_on_current_tree`,
   `test_exempt_partials_are_discovered_and_genuinely_partial`). Keep them meaningful — if the exempt
   set becomes empty, those tests need a synthetic fixture rather than deletion.

### T015 — Fold `_CANONICAL_KIND_SINGULAR_TO_PLURAL` into the authority

**Steps**:
1. `doctrine.py:431` duplicates `ArtifactKind._PLURALS`. Retire it onto the enum.
2. Verify `:606`'s rejection path now admits `asset`.

### T016 — Replace the `_stub_template` if-chain with a kind-keyed mapping

**Purpose**: an `if`-chain is a kind projection the totality guard structurally cannot see. Converting
it to a mapping brings it **into** the guard's reach — this is the class-closure move.

**Steps**:
1. Convert `:464`'s eight-arm chain to a `dict[ArtifactKind, str]` (or a mapping of template
   builders).
2. Add the `asset` entry, with a stub matching the shipped `AssetManifest` shape (`id`, `mime`,
   `path`, `title`).
3. Ensure the guard now discovers it. If it cannot (e.g. because it is not module-level), say so and
   add an explicit exemption **with a reason**, rather than leaving it invisible.

### T017 — Extend the totality guard to the newly-discoverable copies

**Steps**:
1. Red-first: add a deliberately partial copy in a fixture; the guard must fail naming it.
2. Confirm the two formerly string-keyed copies are now discovered.
3. Confirm the guard fails if a new `ArtifactKind` member is added without a mapping entry.

### T018 — End-to-end: scaffold writes where the resolver reads

**Steps**:
1. `spec-kitty doctrine new --kind asset <name>` succeeds (exit 0) and writes a valid manifest.
2. The directory it wrote to is the directory the resolver reads for the project tier.
3. **This assertion is the whole point of the WP.** Today it exits 2.

**Note**: `DoctrineService` resolution is WP04's. Assert the *path*, not the service round-trip, and
leave a comment pointing at WP04's test for the round-trip.

---

## Branch Strategy

- **Planning base**: `feat/doctrine-delivery-reachability`
- **Final merge target**: `feat/doctrine-delivery-reachability`
- Execution worktrees are allocated per computed lane from `lanes.json`; `spec-kitty implement WP03`
  resolves the workspace.

**File-ownership note**: `src/specify_cli/cli/commands/doctrine.py` is also touched by WP05 (asset
subapp registration). You own the file; WP05 owns the new `_doctrine_asset.py` module. Register its
subapp here as a one-line import so WP05 does not need to edit your file.

## Test strategy

```bash
PWHEADLESS=1 pytest \
  tests/doctrine/drg/test_kind_mapping_totality.py \
  tests/doctrine/test_artifact_kinds.py \
  tests/doctrine/test_service.py \
  tests/architectural/test_layer_rules.py -q
```

Baseline: `test_kind_mapping_totality.py` 5 passed.

## Definition of Done

- [ ] **One** canonical project-tier mapping exists in `artifact_kinds.py`; the other copies import it
- [ ] The hoist is real — a reviewer can delete any consumer copy and nothing re-declares the mapping
- [ ] The two string-keyed copies are enum-keyed and **discovered** by the guard
- [ ] Both exemptions are removed, and the exemption-mechanism tests still prove something
- [ ] `_stub_template` is a mapping, not an if-chain, and is guard-visible or explicitly exempted with a reason
- [ ] `doctrine new --kind asset` exits 0 and writes where the project-tier resolver reads
- [ ] A red commit precedes each green commit (C-006)
- [ ] `ruff` + `mypy --strict` clean, zero new suppressions

## Risks

| Risk | Mitigation |
|---|---|
| Adding `asset` to four copies and calling it done | DoD requires the copies to **import**, not to match |
| Removing exemptions leaves the exemption tests hollow | Replace with a synthetic partial fixture, don't delete |
| The if-chain stays invisible after conversion | T016 requires guard-visibility or a reasoned exemption |
| Touching `service.py` | **Not yours** — WP04 owns it; coordinate the canonical form |

## Reviewer guidance

1. `grep -rn "_PROJECT_KIND_DIRS\|_CANONICAL_KIND_SINGULAR_TO_PLURAL"` — every hit should be an import
   or the single definition.
2. Add a thirteenth `ArtifactKind` member in a scratch copy; the guard must fail.
3. Run `doctrine new --kind asset` and then resolve that path — the two must agree.
4. Confirm the exemption list shrank **and** the exemption tests still assert something real.
