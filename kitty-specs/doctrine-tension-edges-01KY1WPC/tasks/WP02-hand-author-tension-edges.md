---
work_package_id: WP02
title: Hand-author tension/reconciliation/rejection edges
dependencies:
- WP01
requirement_refs:
- FR-006
- FR-007
- FR-011
- FR-014
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
phase: Phase 1 - Foundation
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "91207"
shell_pid_created_at: "1784643626.615457"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/directive.graph.yaml
create_intent:
- src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/directive.graph.yaml
- src/doctrine/tactic.graph.yaml
- src/doctrine/paradigm.graph.yaml
- src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – Hand-author tension/reconciliation/rejection edges

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/doctrine/directive.graph.yaml` (doctrine content authoring).

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## Objectives & Success Criteria

Author the new-relation content directly into the per-kind DRG graph fragments. **Critical context**: `opposed_by` (the field this mission retires) is authored in each artifact's own frontmatter YAML and mechanically converted into a graph edge by `src/doctrine/drg/migration/extractor.py`. The three new relations have **no such frontmatter mechanism** — per spec.md, "the extractor can no longer generate them," so they are hand-authored directly in the committed `*.graph.yaml` fragment files. This is a different authoring surface than WP03's removal target, and that is deliberate — do not look for an `in_tension_with:` frontmatter key on `024-locality-of-change.directive.yaml`; it does not exist and should not be added.

Done means:
- `directive:024-locality-of-change` and `directive:025-boy-scout-rule` have one canonical `in_tension_with` edge between them (lex-smaller URN as source — `024` < `025` lexicographically, so `024` is the source).
- `tactic:change-apply-smallest-viable-diff` and `directive:025-boy-scout-rule` have the equivalent edge (INV-005 — the "recovered tactic tension").
- 6 marked `anti_pattern` nodes exist: `anemic-domain-model`, `big-ball-of-mud`, `big-upfront-design`, `code-is-the-documentation`, `database-driven-design`, `single-diagram-architecture`.
- 8 `rejects` edges exist from the relevant paradigms to those 6 nodes.
- A new built-in directive `reconcile-change-scope-tensions` exists with `reconciles_tension` edges to all three of: `directive:024-locality-of-change`, `directive:025-boy-scout-rule`, `tactic:change-apply-smallest-viable-diff`.
- All of the above loads without validation errors.

## Context & Constraints

- Read `plan.md`'s IC-02 section and `data-model.md`'s "Built-in reconciliation directive" section before starting.
- **Do not remove any `opposed_by` content in this WP.** WP03 (sequenced after this one) does that removal — C-006 requires the new edges to exist *before* the old field is dropped, so the pack never loses tension information mid-migration. If you notice `opposed_by` while editing these files, leave it exactly as-is.
- This WP depends on WP01 — `Relation.IN_TENSION_WITH`/`RECONCILES_TENSION`/`REJECTS` and `NodeKind.ANTI_PATTERN` must exist first (Pydantic validation will reject an edge/node referencing an enum member that doesn't exist yet).
- Current file state to ground yourself: `024-locality-of-change.directive.yaml` currently has an `opposed_by:` block naming `DIRECTIVE_025`; `directive.graph.yaml` is a committed, `generated_by: drg-migration-v1` graph fragment containing nodes and edges for all built-in directives.

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP02 --agent <name>` (depends on WP01 — do not branch from a base that predates WP01's merge).

## Subtasks & Detailed Guidance

### Subtask T007 – Author the 024↔025 `in_tension_with` edge

- **Purpose**: This is the flagship example spec.md uses throughout (US1's worked example) — the two directives compete (Locality of Change vs. Boy Scout Rule) and must be queryable as such.
- **Steps**:
  1. Open `src/doctrine/directive.graph.yaml`. Find the `edges:` list (or add one if the file is currently nodes-only for this section — check the file's actual top-level shape before assuming).
  2. Add one `DRGEdge`-shaped entry: `source: "directive:DIRECTIVE_024"`, `target: "directive:DIRECTIVE_025"`, `relation: in_tension_with` (confirm the exact URN casing/format used elsewhere in this file — the node list you read earlier uses `directive:DIRECTIVE_024`, not the slug — match that convention exactly, not the slug-style `directive:024-locality-of-change` used in prose elsewhere in this repo).
  3. Optionally add a `reason:` field explaining the tension (mirror the `opposed_by` reason text currently in `024-locality-of-change.directive.yaml` as a starting point, without deleting the original).
- **Files**: `src/doctrine/directive.graph.yaml`
- **Parallel?**: Yes, relative to T009/T010 (different file).
- **Notes**: C-002 requires exactly ONE canonical edge (lex-smaller URN as source) — do not also add the reverse `025→024` edge.

### Subtask T008 – Author the tactic↔025 `in_tension_with` edge (INV-005)

- **Purpose**: Spec.md explicitly calls this out as a *recovered* tension that must be authored AND surface in the checker — it's easy to do the flagship pair and forget this one.
- **Steps**:
  1. Determine which graph fragment file holds the edge — since one endpoint is a tactic and the other a directive, check whether cross-kind edges live in one fragment or need mirroring in both (`tactic.graph.yaml` and `directive.graph.yaml`) — read how existing cross-kind edges (e.g. `requires`/`suggests` between a tactic and a directive, if any exist) are currently stored before deciding.
  2. Add the edge: `source`/`target` between `tactic:CHANGE-APPLY-SMALLEST-VIABLE-DIFF` (confirm exact URN casing from the tactic's existing node entry) and `directive:DIRECTIVE_025`, `relation: in_tension_with`, lex-smaller URN as source.
- **Files**: `src/doctrine/tactic.graph.yaml` and/or `src/doctrine/directive.graph.yaml` (per the cross-kind storage convention you find)
- **Parallel?**: Yes, relative to T007 within reason (both touch `directive.graph.yaml` if cross-kind edges live there — sequence carefully to avoid clobbering).
- **Notes**: This is the one most likely to be silently skipped — INV-005 exists specifically because the mission's authors flagged this as easy to miss.

### Subtask T009 – Create the 6 marked anti-pattern nodes

- **Purpose**: `rejects` edges (T010) need first-class, validatable targets (D2 — not phantom nodes the extractor invents, not `kind: paradigm` nodes wearing a tag).
- **Steps**:
  1. In `src/doctrine/paradigm.graph.yaml` (or a new dedicated fragment if the existing file's structure doesn't cleanly accommodate a different `kind`, in which case check whether the graph-loading code merges multiple fragment files by convention before creating a new one), add 6 new nodes:
     `anti_pattern:anemic-domain-model`, `anti_pattern:big-ball-of-mud`, `anti_pattern:big-upfront-design`, `anti_pattern:code-is-the-documentation`, `anti_pattern:database-driven-design`, `anti_pattern:single-diagram-architecture` — each `kind: anti_pattern`, with a `label:` and `tags: [anti-pattern]` (or `[smell]` per D2, if a specific one is more apt for a given node — read each paradigm's existing `opposed_by` reason text for a hint at which framing fits).
- **Files**: `src/doctrine/paradigm.graph.yaml`
- **Parallel?**: Yes, relative to T007/T008.
- **Notes**: These are NEW nodes, not re-kinded existing paradigm nodes — the paradigms (`brownfield-onboarding`, `c4-incremental-detail-modeling`, `domain-driven-design`) that currently `opposed_by` these anti-patterns stay `kind: paradigm`; only the *targets* of the rejection become `anti_pattern`.

### Subtask T010 – Author the 8 `rejects` edges

- **Purpose**: Migrates the paradigm `opposed_by` anti-pattern usages to the new directional relation (FR-007).
- **Steps**:
  1. Read the `opposed_by` blocks in `brownfield-onboarding.paradigm.yaml`, `c4-incremental-detail-modeling.paradigm.yaml`, and `domain-driven-design.paradigm.yaml` to identify exactly which paradigm rejects which anti-pattern and why (do not guess the pairing — read all 8 entries across the 3 files first).
  2. Add 8 `rejects` edges in `src/doctrine/paradigm.graph.yaml`: `source` = the paradigm's URN, `target` = the matching `anti_pattern:<id>` node from T009, `relation: rejects`, carrying the original `opposed_by` reason text.
- **Files**: `src/doctrine/paradigm.graph.yaml`
- **Parallel?**: Sequential after T009 (needs the target nodes to exist).
- **Notes**: Exactly 8 edges to exactly 6 nodes (not 8 nodes) — some anti-patterns are rejected by more than one paradigm. Do not create a 1:1 node-per-edge assumption.

### Subtask T011 – Create the `reconcile-change-scope-tensions` directive

- **Purpose**: FR-011 — the built-in default pack must ship coherent out of the box (SC-002) despite the always-on tension check (D3).
- **Steps**:
  1. Create `src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml` — follow the exact frontmatter shape of an existing built-in directive (e.g. `024-locality-of-change.directive.yaml`) for required fields (`id`, `title`, body/description, `schema_version`, etc. — copy the shape, not the content).
  2. Write the body content explaining how to weigh the 024/025/smallest-viable-diff tensions (this is real guidance an operator reads when the tension fires — not boilerplate).
  3. Add the directive's node + its 3 `reconciles_tension` edges (to `directive:DIRECTIVE_024`, `directive:DIRECTIVE_025`, `tactic:CHANGE-APPLY-SMALLEST-VIABLE-DIFF`) to `directive.graph.yaml` (and `tactic.graph.yaml` if cross-kind edges are stored per-target-kind, per your T008 finding).
  4. If this directive has ordinary `requires`/`scope` relations too, author those normally in its own frontmatter — the extractor still handles those; only the `reconciles_tension` edges need hand-authoring.
- **Files**: `src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml` (new), `src/doctrine/directive.graph.yaml`, possibly `src/doctrine/tactic.graph.yaml`
- **Parallel?**: No — depends on T007/T008's edges existing conceptually (same pairs), though it can be drafted alongside them.
- **Notes**: Exactly 3 edges, no more, no fewer — SC-002's live assertion (removing this directive makes the findings reappear, restoring it clears them) depends on this being precise.

### Subtask T012 – Verify load + flag the freshness-canary handoff

- **Purpose**: Prove this WP's content is structurally valid before WP03 builds on it, and hand WP03 a clear heads-up rather than a surprise.
- **Steps**:
  1. Run the existing graph-load tests (e.g. `tests/doctrine/drg/test_shipped_graph_valid.py` or equivalent) against your changes — confirm no validation errors.
  2. Do NOT attempt to fix the shipped-graph freshness canary (`test_shipped_graph_yaml_is_fresh`, `test_shipped_graph_is_fresh_and_byte_identical`) in this WP — those tests currently expect the committed graph to be byte-identical to a fresh extractor regeneration, and your hand-authored edges will make that comparison fail until WP03 reconciles it. That reconciliation is explicitly WP03's job (see its T018).
  3. Leave a clear note in this WP's Activity Log describing exactly what you added (edge list, node list) so WP03's implementer doesn't have to re-derive it from a diff.
- **Files**: none (verification only)
- **Parallel?**: No — last step.
- **Notes**: It is expected and fine for the freshness canary to be red after this WP and before WP03 completes — that is the intended intermediate state C-006 describes, not a bug in your work.

## Test Strategy

- Run whatever existing test(s) load and validate the shipped graph fragments (do not run the byte-identical freshness canary as a pass/fail gate for this WP — see T012).
- No new test files are required from this WP; WP03/WP04/WP05/WP06 add the tests that exercise this content's behavior.

## Risks & Mitigations

- **Risk**: Guessing URN casing/format wrong (e.g. `directive:024-locality-of-change` vs `directive:DIRECTIVE_024`) breaks graph loading silently until a downstream WP's test fails far from the actual mistake. **Mitigation**: read the existing node list in each `*.graph.yaml` file and match its exact convention before adding edges.
- **Risk**: INV-005's tactic↔directive edge gets skipped because it's less visually obvious than the flagship 024↔025 pair. **Mitigation**: T008 is called out individually for this reason — do not treat it as optional.

## Review Guidance

- Confirm exactly 2 `in_tension_with` edges, 6 new `anti_pattern` nodes, 8 `rejects` edges, and 1 new directive with exactly 3 `reconciles_tension` edges — not approximately these counts.
- Confirm no `opposed_by` content was touched or removed.
- Confirm the Activity Log clearly documents what was added, for WP03's benefit.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP02 --to <status>` to change WP status.
- 2026-07-21T13:40:40Z – claude:sonnet:python-pedro:implementer – shell_pid=80430 – Assigned agent via action command
- 2026-07-21T14:19:19Z – claude:sonnet:python-pedro:implementer – shell_pid=80430 – Ready for review. Hand-authored content added (owned_files: src/doctrine/directive.graph.yaml, src/doctrine/paradigm.graph.yaml, src/doctrine/anti_pattern.graph.yaml [new], src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml [new]).

URN casing convention confirmed from existing files: directives use directive:DIRECTIVE_NNN (not slug style); tactics/paradigms use kind:kebab-slug. Cross-kind edges live in the SOURCE node's own fragment file (confirmed precedent: tactic->directive edges live only in tactic.graph.yaml, never mirrored in directive.graph.yaml) -- I followed the same rule.

T007/T008 (directive.graph.yaml edges, both in_tension_with):
- directive:DIRECTIVE_024 -> directive:DIRECTIVE_025 (024 is lex-smaller)
- directive:DIRECTIVE_025 -> tactic:change-apply-smallest-viable-diff (directive: is lex-smaller than tactic: by first-char compare 'd'<'t')

T009 (new anti_pattern nodes): created NEW dedicated fragment src/doctrine/anti_pattern.graph.yaml (NOT inside paradigm.graph.yaml) because tests/doctrine/drg/test_sharded_layout.py::test_fragment_per_populated_node_kind and test_graph_sharding_equality.py::test_every_populated_kind_has_a_fragment enforce one <kind>.graph.yaml fragment per populated NodeKind (DD-8 totality). 6 nodes: anti_pattern:anemic-domain-model, anti_pattern:big-ball-of-mud, anti_pattern:big-upfront-design (all tags:[anti-pattern]); anti_pattern:code-is-the-documentation, anti_pattern:single-diagram-architecture (tags:[smell] -- these read as practice smells rather than named literature anti-patterns); anti_pattern:database-driven-design (tags:[anti-pattern]).

T010 (8 rejects edges, in paradigm.graph.yaml, source=paradigm per cross-kind convention):
- paradigm:brownfield-onboarding -> anti_pattern:big-ball-of-mud
- paradigm:brownfield-onboarding -> anti_pattern:big-upfront-design
- paradigm:c4-incremental-detail-modeling -> anti_pattern:big-upfront-design
- paradigm:c4-incremental-detail-modeling -> anti_pattern:code-is-the-documentation
- paradigm:c4-incremental-detail-modeling -> anti_pattern:single-diagram-architecture
- paradigm:domain-driven-design -> anti_pattern:anemic-domain-model
- paradigm:domain-driven-design -> anti_pattern:big-ball-of-mud
- paradigm:domain-driven-design -> anti_pattern:database-driven-design
(reason text carried verbatim from each paradigm's opposed_by block -- opposed_by itself untouched, still present in all 3 paradigm frontmatter files and still generating the pre-existing 'replaces' edges in paradigm.graph.yaml; WP03 removes those.)

T011 (new directive): src/doctrine/directives/built-in/reconcile-change-scope-tensions.directive.yaml, id: RECONCILE_CHANGE_SCOPE_TENSIONS (uppercase-snake id, no numeric prefix -- precedent for non-numbered built-in directive ids exists in test fixtures, e.g. DEFENSIVE_REVIEW_LENIENT), enforcement: advisory (avoids the lenient-adherence->explicit_allowances requirement; real procedural/integrity_rules/validation_criteria body content included, not boilerplate). Node + exactly 3 reconciles_tension edges added to directive.graph.yaml:
- directive:RECONCILE_CHANGE_SCOPE_TENSIONS -> directive:DIRECTIVE_024
- directive:RECONCILE_CHANGE_SCOPE_TENSIONS -> directive:DIRECTIVE_025
- directive:RECONCILE_CHANGE_SCOPE_TENSIONS -> tactic:change-apply-smallest-viable-diff

T012 (verification): tests/doctrine/drg/test_shipped_graph_valid.py + test_validator_profile_edges.py pass (14/14). Full tests/doctrine/ sweep: 2737 passed, 16 failed -- ALL 16 accounted for:
(a) 14 are the extractor-vs-shipped freshness/zero-delta canary family (extractor cannot regenerate opposed_by-independent hand-authored relations by design -- FR-006/007 note this explicitly): test_extractor.py::test_shipped_graph_yaml_is_fresh, test_extractor_projection.py::test_regenerated_graph_matches_baseline_counts + test_shipped_graph_is_fresh_and_byte_identical, test_path_ref_resolver.py::test_shipped_graph_is_fresh, test_graph_sharding_equality.py (7 of its tests: node/edge sets+counts, canonical-sorted node/edge, sharded-reload-equals-monolith), test_sharding_silent_degrade.py::test_pack_validator_builtin_urn_set_is_full. These are explicitly out of scope per T012's guidance and are WP03's job (plan.md IC-02 risk note: 'freshness canary must accept these hand-authored edges post-extractor-retirement'). NOTE: this list is BROADER than the 2 tests named in the WP02 prompt -- I found 6 more tests in the same family (same root cause: extractor regeneration diverges from shipped fragments because the 3 new relations + anti_pattern nodes have no frontmatter->extractor path). WP03 will need to reconcile/update ALL of these, not just the 2 originally named.
(b) 2 are pre-existing WP01 baseline reds, confirmed by reproducing on the WP01-only commit (024bd0cb6) before applying my diff: test_artifact_kinds.py::test_all_expected_members_present and test_exclusion_set_is_exactly_template_and_asset (WP01 added ArtifactKind.ANTI_PATTERN and put it in the exclusion set, but didn't update these 2 tests' hardcoded expectations). Not mine to fix.
I additionally fixed 2 tests myself (structural, unrelated to the freshness-canary family) by creating the dedicated anti_pattern.graph.yaml fragment: test_sharded_layout.py::test_fragment_per_populated_node_kind and test_graph_sharding_equality.py::test_every_populated_kind_has_a_fragment now pass.

opposed_by untouched everywhere (grep confirms all 3 opposed_by blocks in 024/025 directive files and the 3 paradigm files, plus the tactic's opposed_by block, are unchanged). No Python files touched (ruff N/A).
- 2026-07-21T14:20:29Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=91207 – Started review via action command
- 2026-07-21T14:27:57Z – user – shell_pid=91207 – Review passed. Verified via git diff 024bd0cb6..a576d713e: exactly 2 in_tension_with edges (directive:DIRECTIVE_024->DIRECTIVE_025; directive:DIRECTIVE_025->tactic:change-apply-smallest-viable-diff, the INV-005 recovered tension - present and correctly lex-ordered), 6 anti_pattern nodes with tags in new src/doctrine/anti_pattern.graph.yaml, 8 rejects edges in paradigm.graph.yaml, and 1 new reconcile-change-scope-tensions directive with exactly 3 reconciles_tension edges to all three tension participants. Cross-checked all 8 rejects edges against the original opposed_by entries in brownfield-onboarding/c4-incremental-detail-modeling/domain-driven-design paradigm.yaml (3+2+3=8 entries) - pairing and reason text match exactly, no content lost or mis-paired. grep for opposed_by across the full diff returns zero hits - nothing touched/removed (WP03's job intact). New anti_pattern.graph.yaml fragment justified: confirmed tests/doctrine/drg/test_sharded_layout.py::test_fragment_per_populated_node_kind and test_graph_sharding_equality.py::test_every_populated_kind_has_a_fragment require fragment_kinds == populated_kinds exactly, so a new populated NodeKind (anti_pattern) requires its own fragment file - not scope creep. Ran PYTHONPATH=src .venv/bin/python -m pytest tests/doctrine/drg/ -q: 14 failed, 212 passed, matching the expected freshness-canary family exactly (verified each failure name individually): test_extractor.py::test_shipped_graph_yaml_is_fresh; test_extractor_projection.py::test_regenerated_graph_matches_baseline_counts + test_shipped_graph_is_fresh_and_byte_identical; test_path_ref_resolver.py::test_shipped_graph_is_fresh; test_graph_sharding_equality.py's 9 tests (test_node_sets_equal, test_node_counts_equal, test_edge_sets_equal, test_edge_counts_equal, test_canonical_sorted_nodes_equal, test_canonical_sorted_edges_equal, test_sharded_reload_equals_monolith_reload_raw, test_per_kind_node_counts_equal, test_no_node_urn_lost); test_sharding_silent_degrade.py::test_pack_validator_builtin_urn_set_is_full. All 14 are extractor/freshness/sharding-equality comparisons against a regenerated graph that cannot reproduce hand-authored edges/nodes by design - none are unrelated/unexpected failures. Also ran test_shipped_graph_valid.py + test_validator_profile_edges.py directly: 14/14 passed, confirming structural validity. Reproduced the diff-compliance check programmatically (check_diff_compliance against occurrence_map.yaml): passed=True, all 4 changed files (anti_pattern.graph.yaml, directive.graph.yaml, paradigm.graph.yaml, reconcile-change-scope-tensions.directive.yaml) classify as serialized_keys/manual_review per path heuristic, none flagged do_not_change - legitimate per the map's own rationale (hand-authored replacement edges need judgment, not blanket rename). yaml.safe_load succeeds on all 4 new/changed files plus tactic.graph.yaml. No Python files touched.
