# Data Model: Rehome & Complete Writing-Comms Doctrine

The "entities" of this doctrine mission are the artifacts, their target paths, the profile
contract fields, the routing signals, and the DRG nodes/edges. Source content lives on ref
`pr-2918` at the OLD `src/doctrine/<type>/built-in/` paths.

## 1. Artifact inventory & path map (30 files)

| # | Old path (`pr-2918`) | New path (`packs/built-in/`) | Reconciliation |
|---|---|---|---|
| 1 | agent_profiles/built-in/analyst-annie.agent.yaml | agent_profiles/analyst-annie.agent.yaml | +canonical-verbs, +doctrine-layers |
| 2 | agent_profiles/built-in/comms-cleo.agent.yaml | agent_profiles/comms-cleo.agent.yaml | role→communicator; +canonical-verbs, +doctrine-layers |
| 3 | agent_profiles/built-in/diagram-daisy.agent.yaml | agent_profiles/diagram-daisy.agent.yaml | role→diagram-author; +canonical-verbs,+output-artifacts,+doctrine-layers; strip 031 ban; trim tool matrix |
| 4 | agent_profiles/built-in/lexical-larry.agent.yaml | agent_profiles/lexical-larry.agent.yaml | +canonical-verbs,+doctrine-layers; glossary-authority boundary vs curator-carla |
| 5 | agent_profiles/built-in/minutes-maker-mahad.agent.yaml | agent_profiles/minutes-maker-mahad.agent.yaml | +canonical-verbs,+doctrine-layers; scope enforcement claims |
| 6 | agent_profiles/built-in/scribe-sally.agent.yaml | agent_profiles/scribe-sally.agent.yaml | +canonical-verbs,+output-artifacts,+mode-defaults,+doctrine-layers |
| 7 | agent_profiles/built-in/synthesizer-sam.agent.yaml | agent_profiles/synthesizer-sam.agent.yaml | role→synthesizer; +canonical-verbs |
| 8 | directives/built-in/047-audience-oriented-writing.directive.yaml | directives/047-audience-oriented-writing.directive.yaml | repoint `references` to writing-audience-catalog |
| 9 | directives/built-in/048-version-governance.directive.yaml | directives/048-version-governance.directive.yaml | +cross-ref boundary to DIRECTIVE_018 |
| 10 | directives/built-in/049-agent-declaration-and-self-introduction.directive.yaml | directives/049-…​.directive.yaml | narrow "must"→"should" (advisory) |
| 11 | directives/built-in/050-credential-handling-discipline.directive.yaml | directives/050-…​.directive.yaml | re-anchor on injection/pre-redaction/least-privilege |
| 12 | styleguides/built-in/professional-communications.styleguide.yaml | styleguides/professional-communications.styleguide.yaml | relocate |
| 13 | styleguides/built-in/meeting-minutes-format.styleguide.yaml | styleguides/meeting-minutes-format.styleguide.yaml | relocate |
| 14 | procedures/built-in/glossary-maintenance-workflow.procedure.yaml | procedures/glossary-maintenance-workflow.procedure.yaml | relocate (well-behaved composer — keep) |
| 15 | procedures/built-in/meeting-minutes-pipeline.procedure.yaml | procedures/meeting-minutes-pipeline.procedure.yaml | state trust boundaries; scope enforcement |
| 16 | tactics/built-in/communication/writing-audience-catalog.tactic.yaml | tactics/communication/writing-audience-catalog.tactic.yaml | keep `type: asset` |
| 17-26 | assets/audiences/built-in/{5 personas}.md (+ .asset.yaml) | assets/audiences/{persona}.md (+ .asset.yaml) | invert nesting |
| 27 | assets/audiences/built-in/README.md | assets/audiences/README.md | invert nesting |
| 28 | agent_profiles/built-in/README.md | agent_profiles/README.md (merge into existing) | list 25 ids |
| 29 | agent_profiles/README.md (package) | (package README) | list 25 ids |
| 30 | tests/doctrine/test_shipped_profiles.py | tests/doctrine/test_shipped_profiles.py | +7 ids (see gates) |

(16 schema-checkable YAML artifacts + 5 assets×2 sidecar pairs + 3 READMEs + 1 test = the 30-file surface.)

## 2. Agent-profile contract fields (shipped-profiles gate)

Each non-sentinel profile MUST declare non-empty: `roles` (≥1), `purpose`, `name`,
`specialization.primary_focus`, `collaboration.canonical-verbs`,
`collaboration.output-artifacts`, `mode-defaults` (+ each mode's `use-case`),
`context-sources.doctrine-layers`, `directive-references`; schema-valid; no scalar `role:`.

| Profile | canonical-verbs | output-artifacts | mode-defaults | doctrine-layers | roles[0] change |
|---|---|---|---|---|---|
| analyst-annie | **ADD** | ok | ok | **ADD** | — (analyst, non-canonical) |
| comms-cleo | **ADD** | ok | ok | **ADD** | curator→**communicator** |
| diagram-daisy | **ADD** | **ADD** | ok | **ADD** | designer→**diagram-author** |
| lexical-larry | **ADD** | ok | ok | **ADD** | — (semantic-analyst) |
| minutes-maker-mahad | **ADD** | ok | ok | **ADD** | — (documentarian) |
| scribe-sally | **ADD** | **ADD** | **ADD** | **ADD** | — (documentarian) |
| synthesizer-sam | **ADD** | ok | ok | ok | curator→**synthesizer** |

16 field additions total. `canonical-verbs` must be domain-specific (not generic
design/curate/classify verbs) so they don't re-open a routing collision.

## 3. Routing signals & collisions

Router precedence: `profile_hint` → canonical-verb→`roles[0]` candidate set → domain-keyword
filter → **priority tiebreaker (higher wins)**. Only `roles[0]` participates.

| Bucket (bare verb, no context) | Candidates before fix | Winner before | Winner after fix |
|---|---|---|---|
| DESIGNER (design/mockup/prototype/wireframe) | designer-dagmar@50, diagram-daisy@60 | diagram-daisy ❌ | designer-dagmar ✅ (daisy leaves bucket) |
| CURATOR (curate/classify/organize/tag/validate/verify) | curator-carla@40, doctrine-daphne@48, comms-cleo@55, synthesizer-sam@50 | comms-cleo ❌ | doctrine-daphne/curator-carla ✅ |

Non-collisions (no change): analyst-annie@60 (analyst non-canonical), lexical-larry,
minutes-maker-mahad, scribe-sally. The "researcher" bucket does not collide (researcher is a
secondary role on cleo/sam).

## 4. DRG node/edge model

- **Node** (uniform): `{urn: <kind>:<id>, kind: <kind>, label: <Name>}`. Directives use
  `directive:DIRECTIVE_047` (id form `DIRECTIVE_NNN`), others use the slug id.
- **Edge**: `{source, target, relation[, when, reason]}`. Reachability-conferring relations:
  `requires`, `suggests`, `specializes_from`, `scope`. (`delegates_to`, `in_tension_with`,
  `reconciles_tension`, `rejects`, `applies`, `refines` do NOT confer context reachability.)
- **Edge sources (frontmatter → generated)**:
  - profile → directive/tactic: `context-sources.directives` (→requires), `tactic-references` (→requires)
  - directive/procedure/tactic → X: top-level `references: [{type,id,when?}]`
  - styleguide → X: `references: [<path str>]` (→suggests)
- **Orphan** = a node with no inbound reachability edge. Every new artifact needs ≥1 inbound
  `requires`/`suggests` edge (assets are reached via the tactic's `type: asset` reference;
  profiles are seeded as profile-channel roots and additionally wire out via
  `context-sources.directives`).

## 5. Pinned-count entities (gates)

| Gate literal | File | From | To |
|---|---|---|---|
| `EXPECTED_PROFILE_COUNT` | test_pack_relocation_doctor_gate.py | 18 | 25 |
| `(node_count, edge_count)` tuple | test_pack_relocation_doctor_gate.py | (324, 892) | recompute post-regenerate |
| `EXPECTED_PROFILE_IDS` | test_shipped_profiles.py | 18 ids | +7 ids |
| `EXPECTED_GLOSSARY_TERM_COUNT` | test_pack_relocation_doctor_gate.py | 108 | 108 (unchanged) |
| reachability frozensets | drg/test_reachability.py | — | recompute empirically; unchanged unless charter-activated |
