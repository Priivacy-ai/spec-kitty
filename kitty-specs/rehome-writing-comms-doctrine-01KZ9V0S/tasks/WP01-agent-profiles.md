---
work_package_id: WP01
title: Writing-comms agent profiles — relocate, complete, narrow, reconcile, wire
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-005
- FR-006
- FR-007
- FR-010
- FR-011
- NFR-002
planning_base_branch: feat/rehome-writing-comms-doctrine
merge_target_branch: feat/rehome-writing-comms-doctrine
branch_strategy: Planning artifacts for this mission were generated on feat/rehome-writing-comms-doctrine. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/rehome-writing-comms-doctrine unless the human explicitly redirects the landing branch.
created_at: '2026-08-05T21:14:46Z'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
- T008
history:
- at: '2026-08-05T21:14:46Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: packs/built-in/agent_profiles/
create_intent:
- packs/built-in/agent_profiles/analyst-annie.agent.yaml
- packs/built-in/agent_profiles/comms-cleo.agent.yaml
- packs/built-in/agent_profiles/diagram-daisy.agent.yaml
- packs/built-in/agent_profiles/lexical-larry.agent.yaml
- packs/built-in/agent_profiles/minutes-maker-mahad.agent.yaml
- packs/built-in/agent_profiles/scribe-sally.agent.yaml
- packs/built-in/agent_profiles/synthesizer-sam.agent.yaml
- tests/specify_cli/invocation/test_writing_comms_routing.py
execution_mode: code_change
model: ''
owned_files:
- packs/built-in/agent_profiles/analyst-annie.agent.yaml
- packs/built-in/agent_profiles/comms-cleo.agent.yaml
- packs/built-in/agent_profiles/diagram-daisy.agent.yaml
- packs/built-in/agent_profiles/lexical-larry.agent.yaml
- packs/built-in/agent_profiles/minutes-maker-mahad.agent.yaml
- packs/built-in/agent_profiles/scribe-sally.agent.yaml
- packs/built-in/agent_profiles/synthesizer-sam.agent.yaml
- packs/built-in/agent_profiles/README.md
- src/doctrine/agent_profiles/README.md
- tests/specify_cli/invocation/test_writing_comms_routing.py
role: curator
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load doctrine-daphne
```

## Objective

Land the 7 writing-comms agent profiles on the canonical `packs/built-in/agent_profiles/`
surface, complete their shipped-profile contract, **preserve legacy dispatch routing** (the
mission's highest-risk regression), remove the profile-level over-claims / false attributions
the squad reviews flagged, and declare the frontmatter that mints their DRG reachability edges.
Source content is on ref `pr-2918` at the OLD path `src/doctrine/agent_profiles/built-in/`.

Contributor authorship is preserved — every relocation commit carries a
`Co-Authored-By: Zohar Stolar <...>` trailer (use the author identity from
`git show -s --format='%an <%ae>' pr-2918`).

## Context & Constraints

- **Canonical surface only (C-001):** files live at `packs/built-in/agent_profiles/<id>.agent.yaml`.
  The loader scans only `packs/built-in`; a file left at the old path is silently dead.
- **Routing mechanic (research D-03):** `ActionRouter.route()` resolves
  profile_hint → canonical-verb→role candidate set → domain-keyword filter → **priority
  tiebreaker (higher wins)**. `AgentProfile.role` returns `roles[0]` ONLY. With no context, a
  bare canonical verb selects among all profiles sharing that primary role by priority.
- **Real collisions (exactly two buckets):** DESIGNER (`diagram-daisy@60` vs `designer-dagmar@50`)
  and CURATOR (`comms-cleo@55`, `synthesizer-sam@50` vs `doctrine-daphne@48`/`curator-carla@40`).
  The "researcher" claim does NOT reproduce (secondary role); `analyst-annie@60` is harmless
  (non-canonical primary role) — do not touch it.
- **Shipped-profile contract (research D-04):** each non-sentinel profile must declare non-empty
  `collaboration.canonical-verbs`, `collaboration.output-artifacts`, `mode-defaults` (+ each
  mode's `use-case`), `context-sources.doctrine-layers`, `directive-references`, ≥1 role.
- **DRG edges (research D-01):** the extractor mints profile→X edges ONLY from
  `context-sources.directives` (→requires) and `tactic-references` (→requires) — NOT from the
  display-only `directive-references` field. To be DRG-reachable a profile needs the
  `context-sources.directives` / `tactic-references` entries. (Regeneration itself is WP04.)
- **Do not edit incumbents** except an additive boundary line on the Larry↔Carla relationship
  (T007) — and that boundary text lives on Larry, not Carla (Carla is owned nowhere here; keep
  the change to Larry's own file).
- **No greenwashing (C-004):** fix root causes; keep the Terminology Canon.

## Subtask T001 — Relocate the 7 profiles + READMEs

- `git show pr-2918:src/doctrine/agent_profiles/built-in/<id>.agent.yaml` for each of:
  analyst-annie, comms-cleo, diagram-daisy, lexical-larry, minutes-maker-mahad, scribe-sally,
  synthesizer-sam → write to `packs/built-in/agent_profiles/<id>.agent.yaml`.
- Update **both** READMEs this WP owns — `packs/built-in/agent_profiles/README.md` AND the
  package README `src/doctrine/agent_profiles/README.md` (both exist on the branch and
  `test_readme_profile_ids_match_shipped_yaml` asserts each lists exactly the 25 shipped ids —
  see tests/doctrine/test_shipped_profiles.py:171-172). Add the 7 new ids to both tables.
- Commit with the `Co-Authored-By` trailer (FR-011).
- **Validation:** `git ls-files 'src/doctrine/agent_profiles/built-in/*'` → empty; the 7 files
  exist under `packs/built-in/agent_profiles/`.

## Subtask T002 — Author the shipped-profile contract fields (16 gaps)

Add per `data-model.md §2`:
- `collaboration.canonical-verbs`: ALL 7. Make them **domain-specific** (e.g. Daisy: `diagram`,
  `chart`, `visualize`; Cleo: `draft-comms`, `edit-copy`; Sam: `synthesize`, `reconcile`) — do
  NOT use generic `design`/`curate`/`classify` verbs (that would re-open a routing collision, see
  T004 / R-4).
- `collaboration.output-artifacts`: diagram-daisy, scribe-sally.
- `mode-defaults` (+ each mode's `use-case`): scribe-sally.
- `context-sources.doctrine-layers`: all except synthesizer-sam.
- **Validation:** `spec-kitty doctrine validate packs/built-in/agent_profiles/<id>.agent.yaml`
  → 0 errors for each of the 7.

## Subtask T003 — Red-first routing regression (shipped profiles)

Author `tests/specify_cli/invocation/test_writing_comms_routing.py`. **Non-fakeable form
(contracts/routing-behavior.md):** build a `ProfileRegistry` populated from the **real shipped**
`packs/built-in/agent_profiles/` YAML — NOT a `MagicMock`, NOT `FIXTURES_DIR` stubs (a mock
hand-feeds role/priority and would pass regardless of the YAML). Assert the registry actually
loaded `diagram-daisy`/`comms-cleo`/`synthesizer-sam` from `packs/built-in`, and assert each
shipped `profile.role` (`diagram-daisy.role == "diagram-author"`, etc.). Then, with no
discriminating context:
- `route("design the login screen")` selects `designer-dagmar` (NOT diagram-daisy).
- `route("classify these documents")` selects an incumbent curator (`curator-carla` or
  `doctrine-daphne`), NOT `comms-cleo`/`synthesizer-sam`.
- Positive guard: a diagram-as-code request (hint or domain keyword) still selects diagram-daisy.
- Researcher non-collision (SC-004 / R-5): a bare researcher verb selects `researcher-robbie`,
  documenting that cleo/sam do not collide on their secondary researcher role.
- **RED-FIRST:** commit this test BEFORE T004. On the just-relocated profiles (still
  `roles[0]=designer/curator`) the two negative assertions FAIL — **capture that pre-narrowing
  RED run as a committed evidence artifact (command output on the relocated-but-not-narrowed
  tree), referenced by commit SHA in the WP evidence bundle** (a green-from-the-start test does
  not satisfy the red-first contract).

## Subtask T004 — Narrow the colliding primary roles → routing GREEN

- `diagram-daisy` `roles[0]`: `designer` → `diagram-author`
- `comms-cleo` `roles[0]`: `curator` → `communicator` (keep `researcher` secondary if present)
- `synthesizer-sam` `roles[0]`: `curator` → `synthesizer`
- (`roles` has `min_length=1`; replace the first entry, don't just delete.)
- **Validation:** T003 now GREEN; re-run `doctrine validate` on the three (a custom role is
  allowed — the gate needs ≥1 role, not a canonical one).

## Subtask T005 — diagram-daisy: strip false Directive-031 attribution + trim tool matrix

- Remove the `directive-references` block citing code `031` and strike the
  hexagon/ports-and-adapters/three-tier/utility-microservice ban from `purpose` (research D-06 §1:
  Directive 031 has no such policy and the ban contradicts existing hexagonal/C4 doctrine).
- Trim the inline per-diagram tool matrix in `specialization.primary_focus` to *reference* the
  `mermaid-diagramming` / `plantuml-diagramming` toolguides + the `use-c4-model-techniques`
  directive instead of re-stating conventions those artifacts own (research D-06 §5b).
- **Validation (non-fakeable — `doctrine validate` is schema-only, does not check prose):**
  `grep -n "031" packs/built-in/agent_profiles/diagram-daisy.agent.yaml` → no Directive-031
  reference; `grep -iE 'hexagon|ports-and-adapters|three-tier|utility[- ]?microservice'
  packs/built-in/agent_profiles/diagram-daisy.agent.yaml` → empty; a reference to
  `mermaid-diagramming`/`plantuml-diagramming`/`use-c4-model-techniques` is present.

## Subtask T006 — minutes-maker-mahad: scope enforcement claims

- Reword description/specialization/success-definition so the profile *follows* a
  validation/attribution discipline and *renders for* a publish target the human operates —
  remove "enforces … hard pre-publish gate", "publishes via an authenticated API",
  "schema-valid" (research D-06 §2: no schema/validator/publisher ships). Keep this consistent
  with the procedure edits in WP03 (T016).
- **Validation (non-fakeable):** `grep -iE 'hard pre-publish gate|authenticated API|schema-valid|publishes via'
  packs/built-in/agent_profiles/minutes-maker-mahad.agent.yaml` → empty (the verbatim D-06 §2
  over-claim phrases); keep consistent with WP03/T016.

## Subtask T007 — lexical-larry: glossary-authority boundary

- Add an explicit boundary (on Larry's file): `curator-carla` owns the glossary index and final
  entry acceptance; Larry is the diagnostic/analyst feeder (emits conflict/delta reports for
  Carla). Ensure Larry does NOT claim `glossary-curator` ownership in a way that competes with
  Carla (research D-06 §5a).
- **Validation:** Larry's roles/capabilities no longer assert glossary ownership; `doctrine validate` clean.

## Subtask T008 — Wire profile DRG frontmatter

- For each of the 7, ensure the governance it should require is expressed in
  `context-sources.directives` and/or `tactic-references` (these mint the `requires` DRG edges;
  `directive-references` alone does NOT). E.g. comms-cleo → 047; lexical-larry → 048 +
  glossary tactics; minutes-maker-mahad → 049/050 + meeting-minutes procedure; diagram-daisy →
  use-c4-model-techniques + diagram toolguides.
- **CROSS-LANE (priti-H1):** several of these target ids are *minted in the parallel WP02/WP03
  lanes* (047-050, writing-audience-catalog, meeting-minutes-pipeline) and will NOT resolve on
  this lane's branch in isolation. **Declare the intended refs anyway — do NOT prune them.**
  047-050 are not charter-activation kinds, so their ONLY inbound `requires` edges come from
  these profile refs; pruning them orphans 047-050 at the WP04 gate. Cross-artifact resolution
  is confirmed at integration in WP04, not on lane-a.
- Do NOT hand-edit graph fragments (WP04 regenerates them).
- **Validation:** the intended `context-sources.directives`/`tactic-references` are declared at
  the canonical ids of the writing-comms directives/tactic/procedure (spelling/id matches
  WP02/WP03's created ids); resolution is confirmed at WP04 integration.

## Branch Strategy

Planning base and mission merge target are both `feat/rehome-writing-comms-doctrine`.
`/spec-kitty.implement` allocates this WP's worktree from the computed lane in `lanes.json`.
Completed work merges back into `feat/rehome-writing-comms-doctrine`; the PR to `origin/main`
is a mission wrap-up step the operator merges.

## Definition of Done

- [ ] 7 profiles relocated; old path empty; both profile READMEs list the shipped ids (T001).
- [ ] All 16 contract-field gaps closed; each profile `doctrine validate` clean (T002).
- [ ] Red-first routing test committed RED then GREEN; incumbents win DESIGNER + CURATOR; positive guard passes (T003, T004).
- [ ] diagram-daisy: no Directive-031 attribution, no arch-representation ban, tool matrix → toolguide/C4 references (T005).
- [ ] minutes-maker-mahad: no unshipped-enforcement claims (T006).
- [ ] lexical-larry: diagnostic-feeder boundary; no competing glossary ownership (T007).
- [ ] Each profile's `context-sources.directives`/`tactic-references` declared for reachability (T008).
- [ ] Relocation commits carry the `Co-Authored-By` contributor trailer (FR-011).
- [ ] `spec-kitty doctrine validate` clean on all 7; ruff clean on the new test.

## Risks & Mitigations

- **Re-collision via canonical-verbs (R-4):** keep T002 verbs domain-specific; the T003 negative
  assertions guard against re-entry into DESIGNER/CURATOR buckets.
- **Mock vs shipped test:** use the live `ProfileRegistry` fixture so the test pins the YAML, not
  just the router mechanic.
- **Over-narrowing:** the positive guard (T003) ensures narrowed profiles still route for their scope.
- **Incumbent drift:** touch only Larry's file for the boundary; do not edit curator-carla.

## Reviewer Guidance

- Confirm the routing test was RED on the relocated-but-not-narrowed state (demand the red run).
- Verify no `031` reference and no arch-ban survive in diagram-daisy; verify Mahad claims nothing
  unshipped; verify Larry doesn't compete with Carla.
- Confirm reachability frontmatter is in `context-sources.directives`/`tactic-references`, not
  only `directive-references`.
- Confirm authorship trailer present.

## Activity Log

- 2026-08-05T21:14:46Z — system — Prompt generated via /spec-kitty.tasks
