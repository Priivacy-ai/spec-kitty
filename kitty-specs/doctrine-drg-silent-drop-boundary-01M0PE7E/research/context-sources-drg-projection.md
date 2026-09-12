# Research: profile context-sources vs the canonical `*-references` surface

**Date:** 2026-08-23
**Method:** 3-agent read-only research squad (per user steer on #3629 part 1).
**Decision resolved:** DM-01M0PEAQ5G1VDR3CSJSV51SD8Y → *Full consolidate on top-level `*-references`.*

## The question (user steer)

> "Are these fields in the different artefacts themselves? If so they should be
> replaced by DRG edges/relationships. For ContextSources check how it is used
> and what is in it now. Either clean up or replace with DRG-provisioned
> elements."

## Findings

### 1. There are TWO parallel profile-reference surfaces

| Kind | `context-sources.*` (bare string list) | top-level `*-references` (structured `{id, rationale}`) | Which is LIVE |
|---|---|---|---|
| directives | `context-sources.directives` | `directive-references` | **context-sources** (→ DRG `requires` edge, `extractor.py:920-929`); `directive-references` *also* rendered by `_render_profile_directives` (`profile_sections.py:560-582`) |
| tactics | `context-sources.tactics` | `tactic-references` | **top-level** (`extractor.py:930-942` → `requires` + rationale); `context-sources.tactics` inert |
| toolguides | `context-sources.toolguides` | `toolguide-references` | top-level rendered (`profile_sections.py:350-370`); both effectively dead in projection |
| styleguides | `context-sources.styleguides` | `styleguide-references` | top-level rendered (`profile_sections.py:327-347`); both dead in projection |
| doctrine-layers | `context-sources.doctrine-layers` | — | inert (layer names, no NodeKind) |
| additional | `context-sources.additional` | — | inert (freeform, no edge shape) |

The **renderer that delivers text to a dispatched agent**
(`src/charter/context_renderers/profile_sections.py`, `_render_profile_sections`
at 639-659) reads the **top-level `*-references` fields** + the DRG profile
channel — *not* `context-sources.*`. The lone exception is
`context-sources.directives`, delivered via DRG `requires`-edge projection.

### 2. `context-sources.*` is a redundant / inert second surface (25 shipped profiles)

- `context-sources.tactics` — 6 profiles, ~20 ids, **inert** (live channel is `tactic-references`).
- `context-sources.toolguides` / `styleguides` (list form) — **zero** profiles author them.
- `context-sources.additional` — 16 profiles, ~50 free-text names, **mostly not artefact ids** (no edge target).
- `context-sources.doctrine-layers` — 24 profiles, but **layer names** (paradigms/tactics/…), not artefact ids; **no `LAYER` NodeKind**.
- `context-sources.directives` — the one live field; but `directive-references` is authored by all 25 profiles too.

### 3. DRG vocabulary is sufficient; no new relation needed

`Relation` already spans mandatory/advisory (`REQUIRES`/`SUGGESTS`); `NodeKind`
has `directive/tactic/toolguide/styleguide/paradigm`. The profile DRG channel
(`reachability.py:110-136`) already walks `{requires, specializes_from,
suggests}`, and `render_profile_suggested_doctrine`
(`profile_sections.py:441-498`) already delivers all six kinds. So the delivery
side needs **no change**; the gap is purely which authored surface the extractor
projects.

### 4. Answer to the steer

The target kinds *are* first-class DRG artefacts — but the DRG-provisioned home
**already exists** (top-level `*-references` + the profile DRG channel).
`context-sources.*` duplicates it as an inferior bare-string surface. Therefore
the correct move by the user's own principle is **clean up**: remove
`context-sources.*` and consolidate on the canonical `*-references` surface.
`additional` / `doctrine-layers` have no edge shape and are removed outright.

## Resolved direction (DM-01M0PEAQ5G1VDR3CSJSV51SD8Y)

**Full consolidate on `*-references`:**
1. Remove all `context-sources.*` fields from `ContextSources` (`profile.py`),
   `AgentContextSources` (`schema_models.py`), and `agent-profile.schema.yaml`.
2. Migrate the one live use (`context-sources.directives`) onto
   `directive-references`; ensure the extractor projects `agent_profile` edges
   from the `*-references` surface (directives + tactics already; add
   toolguides/styleguides if authored).
3. Migration + update the 25 shipped `packs/built-in/agent_profiles/*.agent.yaml`.
4. Net: one canonical, rationale-bearing, DRG-provisioned delivery surface; zero
   dead fields; no silent-drop boundary remains for profile references.

## Scope note discovered during research

**#3629 part 2 is already fixed on `main`** — `assert_governance_scope_edges_resolve`
(`extractor.py:1406`, commit `d8beee2761`, wired at `extractor.py:1574`, tested at
`tests/doctrine/drg/migration/test_extractor.py:1608-1653`). It fails loud on any
governance-profile `scope` edge whose target is not a minted node. The mission
treats part 2 as **verify-and-close**, not implement.

---

# Addendum: org-pack conventions + the `packs/internal` silent-drop (research round 2)

**Question (operator):** use `packs/internal` (spec-kitty-internal) as the #3530
integration fixture, "first updated to match the latest structural conventions."

**Finding:** the pack is **already conformant**. The actionable work is a code fix
(a silent-drop boundary) + a README refresh — not a pack restructure.

## Latest org-tier pack conventions (authority-backed)

- **Required file:** `<root>/drg/fragment.yaml` (single fragment) — `OrgDRGFragment`
  schema, `extra="forbid"` (`org_pack_loader.py:429-449,496-501`). Root per-kind
  `*.graph.yaml` is the **built-in** shape, NOT the org convention; the validator
  only flags a pack that has *neither* a root `*.graph.yaml` *nor* a
  `drg/fragment.yaml` (`pack_validator.py:357-365`).
- **Node kinds are PLURAL** (`glossary_packs`/`procedures`/`directives`) — canonical,
  not deprecated (`org_pack_loader.py:87-124,361-377`). Edge URNs are singular
  `<kind>:<id>` (`merge.py:445,533`). The internal pack matches both.
- **`org-charter.yaml`** is optional, `OrgCharterPolicy` schema
  (`org_charter.py:119-169`); internal's parses clean.
- **`pack.yaml`/`pack.md`/`pack-manifest.yaml` NOT required** for org packs —
  deferred per ADR `2026-08-16-1` §"Deferred" (lines 153-167); only built-in emits
  the unified manifest. (Ties to #3511 seam 1.)
- **Validator green:** `validate_pack(packs/internal)` → OK, 0 errors, 0 advisories;
  `merge_three_layers` resolves both `refines` edges against the real built-in DRG.

## The real defect (5g) — branch-aligned silent-drop

`load_validated_graph` (`src/charter/_drg_helpers.py:60`) has two org seams:
- **`org_fragments=`** → folded via `merge_three_layers` (`_drg_helpers.py:217-221`).
  The ONLY seam that reads `drg/fragment.yaml`. Callers: `gate_bindings.py:308`,
  `activate.py:303,401`, `deactivate.py:159`, `charter/lint.py:97`,
  `_status_collectors.py:514`, `_doctrine_collect.py:691`,
  `context_renderers/selection_block.py:655`.
- **`org_roots=`** → loop at `_drg_helpers.py:138-182` reads only root
  `*.graph.yaml`; does NOT read `drg/fragment.yaml`; and **suppresses the
  "no graph" warning when `drg/fragment.yaml` exists** (`:174`). Callers that pass
  only `org_roots` → **silently drop the fragment**:
  `mission_step_contracts/executor.py:362`, `charter/action_doctrine_bundle.py:192`.

Existing evidence: `tests/specify_cli/mission_step_contracts/test_executor.py:878-916`
models `packs/internal`'s exact shape and asserts it "degrades with warning instead
of crashing" — i.e. the executor/step-contract path does NOT fold internal's doctrine.

**Fix (recommended, matches branch intent):** make the `org_roots` seam also load
`drg/fragment.yaml` per root (or thread `org_fragments=load_org_drg(...)` into the
executor + `action_doctrine_bundle`), and stop suppressing the warning. Keep the
org-fragment shape as the canonical convention.

## Concrete `packs/internal` delta

| Item | Required? |
|------|-----------|
| plural kinds / `drg/fragment.yaml` / singular edge URNs | already correct — no change |
| `pack.yaml`/`pack-manifest.yaml` | NOT required (deferred) — optional forward-compat only |
| README refresh | yes — README omits the `directives/` dir + `OPERATOR_SIGNAL_CONTRACT` node now on disk |
| org_roots-seam silent-drop fix | **yes — code fix, the mission centerpiece for this item** |

## Chain note

built-in (layer 0) + internal (org layer_index 1) is the ≥2-layer chain. No
fixture currently exercises a multi-*org*-pack `extends:` chain
(`grep extends: tests/doctrine/fixtures` → none); if the strict multi-org-pack
merge path must be exercised, a second minimal org fixture is net-new (plan-time).
Reusable chain tests: `tests/integration/test_three_layer_drg_end_to_end.py`,
`test_org_pack_artifact_lifecycle.py`, `tests/doctrine/test_overlay_precedence.py`.
