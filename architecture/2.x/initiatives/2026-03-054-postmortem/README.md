# Post-Implementation Review: Feature 054 — Charter Interview Compiler and Bootstrap

| Field | Value |
|---|---|
| Date | 2026-03-10 |
| Feature | 054-charter-interview-compiler-and-bootstrap |
| Branch | `feature/agent-profile-implementation` |
| Work Packages | WP01–WP12 (all done) |
| Scope | Phase 1 of Doctrine-to-Execution Integration |

---

## 1. Implementation Quality Assessment

### What shipped well

1. **Transitive reference resolution** (`reference_resolver.py`): The DFS walker
   from directives through tactic_refs to styleguides/toolguides/procedures is
   clean and cycle-safe. The two-stage intersection (action index intersection
   project selections) prevents cross-action governance bleed — this is a key
   architectural invariant and it holds.

2. **Action index design**: `actions/<action>/index.yaml` is the right
   abstraction. It decouples "what governance applies to this phase" from "what
   the project selected" and keeps the intersection logic in one place
   (`context.py`).

3. **Charter-as-configuration**: The decision to not materialise a
   `library/` directory and instead fetch live from `DoctrineService` on every
   `context` call is correct. It avoids stale-cache bugs and keeps the doctrine
   package as the single source of truth for shipped content.

4. **Depth semantics**: The 1/2/3 depth model with first-load bootstrap
   (depth 2) and subsequent compact (depth 1) is pragmatic. It prevents prompt
   bloat while still giving agents a full governance boot on first encounter.

5. **ArtifactKind consolidation** (WP09–WP10): Moving from scattered string
   constants to a canonical enum reduces an entire class of typo bugs and makes
   the artifact taxonomy explicit in code.

6. **MissionRepository extraction** (WP11): Redirecting package resolution away
   from `specify_cli/missions/` to `src/doctrine/missions/` correctly positions
   missions as doctrine artifacts rather than CLI concerns.

7. **Stale content removal** (WP12): Cleaning `specify_cli/missions/` content
   removes the ambiguity about which directory is authoritative for mission
   templates.

### What could be stronger

1. **Guidelines prose is still narrative**: The `guidelines.md` files in
   `actions/<action>/` are free-form markdown rather than structured artifacts
   with schema validation. They are the only doctrine content not governed by
   JSON Schema. This makes them opaque to tooling — you cannot programmatically
   query "which guidelines mention worktrees" without text search.

2. **Context output is a string blob**: `CharterContextResult.text` is
   rendered markdown. Consumers (agents, connectors) cannot selectively parse
   out directive content vs. tactic steps vs. guidelines without regex. A
   structured alternative (list of typed sections) would enable smarter
   downstream processing.

3. **Depth semantics are implicit**: The depth 1/2/3 behaviour is documented
   but not visible to consumers. An agent receiving depth-1 compact output has
   no structured way to request "give me tactic X at full depth" without
   re-requesting the entire context at depth 3.

4. **Test coverage disparity**: The charter compiler and context modules
   have good coverage, but the integration between `context.py` and the actual
   command templates (the bootstrap injection point) is tested through snapshot
   fixtures rather than behavioural assertions. This makes the test suite
   fragile to formatting changes.

5. **Local support file declarations are additive-only**: The design is correct
   (local supplements shipped, never overrides), but there is no mechanism for
   a project to *suppress* a shipped directive it disagrees with. The only option
   is to not select it — which is fine if you control the charter, but
   becomes a friction point if a team inherits a pre-built charter.

---

## 2. Architecture Documents Requiring Update

### Must update

| Document | What changed | Action |
|---|---|---|
| `initiatives/2026-03-doctrine-execution-integration/README.md` | Phase 1 status is "In Progress" but feature 054 is complete | Update Phase 1 to "Complete" with completion date. Note remaining deployment item (m_2_0_2 migration for slimmed templates). |
| `04_implementation_mapping/README.md` | Table row for Agent Tool Connectors still says `src/specify_cli/missions/*/command-templates/` | Update to reflect `src/doctrine/missions/*/command-templates/` as new source (WP11/WP12). |
| `04_implementation_mapping/README.md` | "What is emerging or aspirational" table lists "Charter compiler consumes Doctrine" as emerging | Move to "What exists and works today" — this is now fully implemented. |
| `04_implementation_mapping/README.md` | Charter components table is incomplete | Add Action Context Resolver `charter/context.py` as distinct component with depth semantics and action index intersection. |
| `03_components/README.md` | Component diagram does not show ActionIndex or ContextBootstrap | Add ActionIndex as a component within Doctrine, and ContextBootstrap as a component within Charter. |

### Should update (alignment)

| Document | Gap | Action |
|---|---|---|
| `02_containers/README.md` | Loop C (Governance) does not describe action-scoped context | Extend Loop C to show the `charter context --action <X>` path as a sub-loop of execution, not just a setup step. |
| `00_landscape/README.md` | Doctrine container description says "knowledge store" without mentioning mission-scoped action indexes | Add a note that Doctrine now includes action-scoped governance indexes per mission type. |
| `02_containers/runtime-execution-domain.md` | No mention of governance injection at execution boundary | Add a note that every WP execution begins with a charter context bootstrap call. |

### No update needed

| Document | Reason |
|---|---|
| ADRs 2026-02-23-1 (Doctrine Governance) | Feature 054 is a faithful implementation of this ADR — no divergence. |
| ADR 2026-02-09-1 (Status Model) | Orthogonal to 054. |
| ADR 2026-02-17-1 (Next Command) | 054 does not change the next-action loop contract. |

---

## 3. Proximity to "Indoctrinating" the Spec Kitty Process

**Assessment: Close, but not yet self-hosting.**

The gap between "doctrine artifacts exist" and "doctrine artifacts govern every
spec-kitty action" has narrowed significantly with 054. Here is the maturity
scorecard:

| Capability | Maturity | Evidence |
|---|---|---|
| **Directive content available at runtime** | Production | `DoctrineService` + transitive resolution operational |
| **Action-scoped governance injection** | Production | Action indexes + context bootstrap working for all 4 software-dev actions |
| **Charter as typed configuration** | Production | Interview → compile → context pipeline end-to-end |
| **Agent profile shaping governance** | Partial | Models + repository exist (048). Profile-aware resolution in resolver.py. Not yet auto-selected during `implement`. |
| **Governance prose extracted from templates** | Partial | `guidelines.md` per action exists. Templates still contain narrative prose that *should* be doctrine but isn't yet schema-governed. |
| **All missions doctrine-governed** | Partial | `software-dev` fully wired. `documentation`, `plan`, `research` missions have action directories but thinner indexes. |
| **Doctrine governs its own curation** | Not started | The curation pipeline (`_proposed/` → `shipped/`) is manual. No doctrine artifact governs *how curation decisions are made*. |
| **Template slimming deployed** | Not started | Migration `m_2_0_2` pending. Current templates still carry inline governance prose alongside the bootstrap section. |

**What "fully indoctrinated" looks like:**

1. Every command template contains *only* structural workflow instructions
   (create worktree, run tests, commit). All governance content is retrieved
   at runtime via `charter context`.
2. The charter interview is itself governed by doctrine (a "meta-interview
   directive" that defines what questions must be asked).
3. Agent profile selection is automatic based on the action being performed
   (implement → implementer profile, review → reviewer profile).
4. Non-software-dev missions (documentation, research) have equally rich
   action indexes.
5. The curation pipeline has its own doctrine — curate is a mission type with
   its own action indexes and governance.

**Estimated remaining work:**
- Template slimming migration (m_2_0_2): 1 feature
- Auto profile selection: 1 feature
- Documentation/research mission parity: 1 feature each
- Curation-as-mission: 1 feature (this is the self-hosting milestone)

---

## 4. Next Curation Steps

### Immediate (before merging this branch to main)

1. **Update the doctrine-execution-integration initiative**: Mark Phase 1
   complete. Document what Phase 1 actually delivered vs. what was planned.
   Note the deferred items (m_2_0_2 migration, MissionTemplateRepository).

2. **Run artifact curation**: The 054 spec noted curation is "ongoing" but
   not a hard blocker. Now that the pipeline is operational, curate the
   `_proposed/` directives top-to-bottom. This is the quality gate before
   the next consumers can trust the content.

3. **Validate action index completeness**: For each of the 4 software-dev
   actions, verify that every directive referenced in the index actually
   exists in `shipped/` and passes schema validation. Run:
   ```bash
   pytest tests/doctrine/ -k "action_index or directive_consistency"
   ```

### Short-term (next 1-2 features)

4. **Deploy slimmed templates** (m_2_0_2): Strip inline governance prose from
   all 48 agent template copies. Templates should contain only:
   - Charter context bootstrap call
   - Structural workflow steps (create worktree, run tests, commit)
   - Feature-specific interpolation variables

5. **Enrich non-software-dev action indexes**: The `documentation`, `plan`,
   and `research` mission action indexes are thin. Add directive and tactic
   references appropriate to each mission type.

### Medium-term (next 2-4 features)

6. **Auto profile selection**: Wire agent profile resolution into the
   `implement` / `review` / `specify` entry points so the correct profile
   is selected automatically, not manually during interview.

7. **Structured context output**: Replace `CharterContextResult.text`
   (string blob) with a structured payload that consumers can selectively
   query. This unblocks smarter connectors (Phase 2).

---

## 5. Streamlining Mission Steps via Doctrine Artifacts

### Problem: Repeated governance across mission actions

Currently, each command template (`specify.md`, `plan.md`, `implement.md`,
`review.md`) contains:
1. A charter context bootstrap section (standardised)
2. Structural workflow instructions (action-specific)
3. Residual governance prose (should be doctrine, isn't yet)

Items 1 and 3 are repetitive across actions. The bootstrap call is identical
except for the `--action` parameter. The residual prose often restates
directive intent that is already captured in the shipped directive YAML.

### Solution: MissionStepContracts + runtime enrichment

**Implemented**: `MissionStepContract` is a new doctrine artifact type
(`src/doctrine/mission_step_contracts/`). Each contract defines the structural
steps of a mission action, with optional delegation to doctrine artifacts
for concretization and a freeform `guidance` field for step-specific prose.

Shipped contracts exist for all 4 software-dev actions:
- `implement.step-contract.yaml` (6 steps, paradigm delegation for workspace)
- `specify.step-contract.yaml` (6 steps)
- `plan.step-contract.yaml` (6 steps)
- `review.step-contract.yaml` (6 steps)

**Key design:**
- `delegates_to.kind` links a step to a doctrine artifact type (paradigm,
  tactic, directive) for concretization at runtime
- `delegates_to.candidates` lists which artifacts *could* concretize the step;
  the charter's selections determine which one applies
- `guidance` is a freeform field for additional step-specific instructions
- `command` is an optional CLI command for purely structural steps

**Access via DoctrineService:**
```python
service = DoctrineService()
contract = service.mission_step_contracts.get_by_action("software-dev", "implement")
```

**Next step**: Template slimming migration (m_2_0_2) can now render step
contracts instead of inline governance prose.

**Doctrine artifacts that replace repeated template prose:**

| Currently repeated | Doctrine artifact that replaces it |
|---|---|
| "Run tests before committing" in every template | Directive 030 (test-and-typecheck-quality-gate) |
| "Use smallest viable diff" in every template | Tactic `change-apply-smallest-viable-diff` |
| "Sign commits with co-author" in every template | Directive 029 (agent-commit-signing-policy) |
| Worktree discipline prose | Toolguide `worktree-management` (to be created) |
| Pre-read verification instructions | Directive 028 (search-tool-discipline) |

This eliminates governance duplication across 48 template copies (12 agents
x 4 actions) and makes doctrine the single source of truth for behavioural
rules.

---

## 6. Charter-Driven Git Branching Strategy

### Problem

Spec Kitty currently hardcodes a worktree-per-work-package branching model.
This is baked into:
- `implement.md` templates (all 48 copies)
- `src/specify_cli/orchestrator/` (worktree creation logic)
- `src/specify_cli/merge/` (worktree-based merge assumptions)
- Charter context guidelines (worktree discipline prose)

Users wanting git-flow branches, CI to a shared branch, or trunk-based
development cannot configure this without forking templates.

### Solution: Branching strategy as a doctrine paradigm

**Layer 1: Paradigm artifact defines the mental model**

```yaml
# doctrine/paradigms/shipped/workspace-per-wp.paradigm.yaml
id: workspace-per-wp
schema_version: "1.0"
title: Workspace per Work Package
description: >
  Each WP gets an isolated git worktree with a dedicated branch.
  Enables parallel development across WPs. Merges happen sequentially
  via the merge command.
tactic_refs:
  - worktree-isolation
  - sequential-merge
opposed_by:
  - id: shared-branch-ci
    contradiction: >
      Shared-branch CI trades isolation for simpler merge flow.
      Conflicts detected earlier but parallelism is limited.
```

```yaml
# doctrine/paradigms/shipped/shared-branch-ci.paradigm.yaml
id: shared-branch-ci
title: Shared Integration Branch
description: >
  All WPs commit to a shared feature branch. CI validates integration
  continuously. No worktrees needed. Simpler for solo developers or
  small teams.
tactic_refs:
  - feature-branch-workflow
  - ci-integration-testing
opposed_by:
  - id: workspace-per-wp
    contradiction: >
      Worktree isolation prevents merge conflicts during development
      but adds complexity for solo developers.
```

```yaml
# doctrine/paradigms/shipped/git-flow.paradigm.yaml
id: git-flow
title: Git Flow
description: >
  Classic git-flow with develop, release, hotfix branches.
  WPs branch from develop, merge back via pull requests.
tactic_refs:
  - git-flow-branching
  - pull-request-merge
```

```yaml
# doctrine/paradigms/shipped/trunk-based.paradigm.yaml
id: trunk-based
title: Trunk-Based Development
description: >
  All work committed directly to main behind feature flags.
  WPs are short-lived branches (< 1 day) merged frequently.
tactic_refs:
  - short-lived-branches
  - feature-flag-gating
```

**Layer 2: Tactics implement the branching behaviour**

Each paradigm references tactics that describe the concrete steps. The
`worktree-isolation` tactic has steps for `git worktree add`, the
`feature-branch-workflow` tactic has steps for `git checkout -b`, etc.

**Layer 3: Charter interview captures the choice**

The charter interview already captures `selected_paradigms`. Adding
branching paradigms to the selection:

```yaml
# In interview/answers.yaml
selected_paradigms:
  - test-first
  - workspace-per-wp    # <-- branching strategy selection
```

**Layer 4: Action index routes to correct tactics**

The `implement` action index becomes branching-strategy-aware:

```yaml
# missions/software-dev/actions/implement/index.yaml
action: implement
directives: [...]
tactics:
  # Always included:
  - acceptance-test-first
  - tdd-red-green-refactor
  # Branching-strategy-conditional:
  - $paradigm:workspace-per-wp:worktree-isolation
  - $paradigm:shared-branch-ci:feature-branch-workflow
  - $paradigm:git-flow:git-flow-branching
  - $paradigm:trunk-based:short-lived-branches
```

The `$paradigm:` prefix is a conditional inclusion syntax: include this tactic
only if the named paradigm is in the project's `selected_paradigms`.

**Layer 5: Orchestration reads charter, not hardcoded strategy**

```python
# Pseudocode for implement entry point
def implement_wp(wp_id, repo_root):
    charter = load_charter(repo_root)

    if "workspace-per-wp" in charter.selected_paradigms:
        create_worktree(wp_id)
    elif "shared-branch-ci" in charter.selected_paradigms:
        checkout_feature_branch(wp_id)
    elif "git-flow" in charter.selected_paradigms:
        checkout_from_develop(wp_id)
    elif "trunk-based" in charter.selected_paradigms:
        checkout_short_lived_branch(wp_id)
```

**Layer 6: Merge command respects strategy**

The merge command similarly reads the paradigm selection to determine merge
mechanics (worktree-based sequential merge, PR-based merge, direct-to-trunk,
etc.).

### Implementation roadmap

| Step | Scope | Effort |
|---|---|---|
| 1. Create branching paradigm artifacts | Doctrine only — no code changes | Small |
| 2. Create branching tactic artifacts | Doctrine only — step definitions | Small |
| 3. Add conditional inclusion to action index loader | `action_index.py` change | Medium |
| 4. Charter interview: add branching paradigm question | `interview.py` change | Small |
| 5. Refactor orchestrator to read paradigm | `orchestrator/` refactor | Large |
| 6. Refactor merge to read paradigm | `merge/` refactor | Large |
| 7. Update templates to remove hardcoded worktree instructions | Migration | Medium |

Steps 1-4 are low-risk doctrine additions. Steps 5-6 are the heavy lift —
they require the orchestration and merge subsystems to become
strategy-polymorphic rather than worktree-hardcoded.

### Key insight: The charter is already the right indirection point

The charter already sits between "what the project wants" (interview
answers) and "what the agent does" (context bootstrap). Making branching
strategy a paradigm selection flows naturally through the existing pipeline:

```
Interview → selected_paradigms includes branching strategy
  → Compiler resolves paradigm → tactic_refs
  → Action index intersects with paradigm-conditional tactics
  → Context bootstrap injects correct branching procedures
  → Agent follows the procedures it received
  → Orchestrator reads same paradigm to create correct workspace type
```

No new architectural primitives needed. The doctrine stack already supports
this — it just needs the branching-specific content authored and the
orchestrator decoupled from the worktree assumption.

---

## Related Documents

- Feature 054 spec: `kitty-specs/054-charter-interview-compiler-and-bootstrap/spec.md`
- Doctrine execution integration: `architecture/2.x/initiatives/2026-03-doctrine-execution-integration/`
- Implementation mapping: `architecture/2.x/04_implementation_mapping/README.md`
- System landscape: `architecture/2.x/00_landscape/README.md`
- ADR Doctrine Governance: `architecture/2.x/adr/2026-02-23-1-doctrine-artifact-governance-model.md`
