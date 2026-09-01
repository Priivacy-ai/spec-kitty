# Phase 1 Data Model — schema, model & DRG-shape changes

This mission changes no runtime storage. The "entities" are doctrine schema /
model shapes and DRG projection rules. Each change below is a boundary made
single-sourced or fail-loud.

## E1 — `_DRG_NODE_KINDS` (derived set) [IC-1, #3608]

- **Before**: hand-maintained `frozenset[str]` literal in
  `topic_resolver.py:37` (drifted 6 kinds vs `NodeKind`).
- **After**: `_DRG_NODE_KINDS: frozenset[str] = frozenset(k.value for k in NodeKind)`.
- **Invariant** (pinned by drift-guard test): `_DRG_NODE_KINDS == {k.value for k in NodeKind}`
  — exact equality (fails on missing *and* extra).
- **Consumer**: membership gate at `topic_resolver.py:236`
  (`if lhs not in _DRG_NODE_KINDS: return None`). Post-change, every canonical
  kind (incl. `glossary_pack`, `mission_step_contract`, `anti_pattern`, `asset`,
  `glossary`, `template`) is recognized.

## E2 — `ContextSources` / `AgentContextSources` / profile schema [IC-2, #3629 p1]

- **Before** (both pydantic models + `agent-profile.schema.yaml`): field
  `context-sources` with subfields `directives, tactics, toolguides, styleguides,
  doctrine-layers, additional` (all `list[str]`).
- **After**: `context-sources` block **removed** entirely from
  `profile.py::ContextSources` (and its attribute on `AgentProfile`),
  `schema_models.py::AgentContextSources`, and the JSON schema. Because both models
  use `extra="forbid"`, a profile still authoring `context-sources` is **rejected
  at load** (fail-loud) — the desired boundary.
- **Canonical surface (retained/authoritative)**: top-level `*-references`
  — `directive-references`, `tactic-references`, `toolguide-references`,
  `styleguide-references` (structured `{id, rationale}` / DirectiveRef).
- **Migration mapping** (upgrade migration + the 25 shipped profiles):
  | from `context-sources.*` | to |
  |---|---|
  | `directives` | `directive-references` (id, keep any rationale) |
  | `tactics` | `tactic-references` |
  | `toolguides` | `toolguide-references` |
  | `styleguides` | `styleguide-references` |
  | `additional` | **dropped** (freeform, no artefact/edge target) |
  | `doctrine-layers` | **dropped** (layer names, no NodeKind) |
- **Invariant**: no authored *artefact reference* is lost (directives/tactics/
  toolguides/styleguides preserved); delivered content to a dispatched agent is
  unchanged (C-006).

## E3 — agent_profile DRG projection (extractor) [IC-2, #3629 p1]

- **Before**: extractor projects `context-sources.directives`→`requires`→directive
  (`extractor.py:920-929`) and top-level `tactic-references`→`requires`→tactic
  (`:930-942`).
- **After**: projects from the `*-references` surface uniformly — `directive-references`
  → `requires` → directive (replacing the context-sources.directives loop);
  `tactic-references` unchanged; add `toolguide-references`/`styleguide-references`
  → `suggests` (or `requires`) → toolguide/styleguide when authored.
- **Invariant**: the set of DRG edges minted for a given profile is unchanged for
  content that was already delivered; net-new edges only for previously-inert
  authored refs now carried on `*-references`.

## E4 — governance-profile scope edges (fail-loud) [IC-3, #3629 p2]

- **State**: `assert_governance_scope_edges_resolve` (`extractor.py:1406`) already
  raises on any `selected_*` target that is not a minted node (built-in path,
  tested). **Verify** the org-tier governance-profile path is equally guarded.
- **Invariant** (target end-state): a nonexistent `selected_*` id fails loud on
  **both** built-in and org tiers; valid selections mint scope edges unchanged.

## E5 — `load_validated_graph` org seams [IC-4, #3530]

- **Before**: two seams. `org_fragments=` folds `drg/fragment.yaml` via
  `merge_three_layers`. `org_roots=` (`_drg_helpers.py:138-182`) reads only root
  `*.graph.yaml`, **ignores `drg/fragment.yaml`**, and **suppresses the "no graph"
  warning** when a fragment exists (`:174`). Callers `executor.py:362` and
  `action_doctrine_bundle.py:192` pass only `org_roots` → silent drop.
- **After**: the `org_roots=` seam also loads `drg/fragment.yaml` per root (or the
  two callers thread `org_fragments`), and the warning is honest (no false
  suppression). No double-fold when both `org_roots` and `org_fragments` are given.
- **Invariant**: an org pack's declared nodes/edges reach every consumer seam;
  a genuinely missing DRG produces a real warning.

## E6 — `packs/internal/` (fixture) [IC-4/IC-5, #3530]

- **Structure**: already conformant — no shape change. README refreshed to list
  the on-disk `directives/` dir + `OPERATOR_SIGNAL_CONTRACT` node.
- **Role**: #3530 chain-delivery fixture (built-in layer 0 + internal org layer 1).
- **Declared kinds to verify delivered**: `glossary_packs` (spk-internal-glossary),
  `procedures` (landing-contributor-prs), `directives` (OPERATOR_SIGNAL_CONTRACT),
  and `refines` edges to built-in `procedure:red-main-release-discipline` /
  `tactic:pr-agent-worktree-isolation`.

## E7 — extractor doc-nit [IC-6, #3629 p3]

- Docstring at `extractor.py:557` ("no golden-count update was required") clarified
  to match the M2 WP04 re-ledger reality. No behaviour change.
