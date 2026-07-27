# Quickstart — Slice F: Multi-Context Extensibility

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Companions: [plan.md](plan.md) | [data-model.md](data-model.md) | [contracts/](contracts/)

Slice F opens spec-kitty along three previously-implicit axes. This quickstart shows the three operator personas the new surfaces serve, with a 3-step recipe for each.

---

## Recipe 1 — "I'm an org operator. How do I configure an org pack?"

**Persona:** an enterprise spec-kitty operator at an organisation that maintains proprietary governance artefacts (custom directives, compliance frameworks, internal artifact kinds).

### Step 1 — Scaffold the org pack

```bash
# Create the org pack skeleton at a path you control
spec-kitty doctrine org init ../acme-org-doctrine

# What you get:
#   ../acme-org-doctrine/
#   ├── org-charter.yaml         # required_<kind> selections (Mission B parity)
#   ├── drg/
#   │   └── fragment.yaml        # NEW: org-tier DRG fragment (Slice F)
#   └── README.md                # stub onboarding doc for your team
```

### Step 2 — Configure the org pack in your project

In your project's `.kittify/config.yaml`:

```yaml
organisation_packs:
  - name: acme-compliance
    source: local_path
    path: ../acme-org-doctrine
```

(`source: url` and `source: package` are reserved for follow-up missions. This mission ships `local_path` only — see [plan.md §6 Plan-Time Decisions / NEW-1](plan.md#6-plan-time-decisions).)

### Step 3 — Validate and inspect

```bash
# Validate the org pack's structure (catches schema errors early)
spec-kitty doctrine org validate ../acme-org-doctrine

# Inspect the merged three-layer doctrine state
spec-kitty doctor doctrine
#   ...
#   Organisation Layer:
#     ✓ acme-compliance (path: ../acme-org-doctrine, 12 nodes, 4 edges)
#   Selections (resolved across all layers):
#     directives: sox-controls (source: org:acme-compliance), ...

# Lint all three layers (shipped + org + project) in one call
spec-kitty charter lint
#   [built-in]              OK -- 87 nodes, 142 edges
#   [org:acme-compliance]   OK -- 12 nodes, 4 edges
#   [project]               warn: directive 'caveman-comments' selected but no body found
```

**What changed under the hood:** `build_charter_context` now resolves through all three layers; every rendered artifact stanza carries `source: built-in | org:<pack> | project` provenance so prompt inspection is unambiguous.

**Exception handling:** if the configured `local_path` doesn't exist, the runtime hard-fails with a named-pack-and-path error per FR-004. Fix it by either fetching the pack to the expected location OR removing the entry from `.kittify/config.yaml`.

---

## Recipe 2 — "I'm a monorepo team lead. How do I configure per-package charter scoping?"

**Persona:** a team operating a monorepo with multiple packages, each with its own charter (`packages/auth/.kittify/charter/...`, `packages/web/.kittify/charter/...`).

### Step 1 — Place a charter in each package

```bash
# Inside packages/auth/
cd packages/auth
spec-kitty charter scaffold

# Inside packages/web/
cd ../web
spec-kitty charter scaffold
```

### Step 2 — Declare the scopes in the repo-root config

In the repo-root `.kittify/config.yaml`:

```yaml
charter_scopes:
  - root: packages/auth
    name: auth
  - root: packages/web
    name: web
```

### Step 3 — Run spec-kitty from any subdirectory

```bash
# From deep inside the auth package
cd packages/auth/src/some/deep/dir

# spec-kitty resolves the nearest enclosing charter (auth's)
spec-kitty charter status
#   Scope: auth (root: /repo/packages/auth)
#   Charter version: 1.1.5
#   ...

# Implement work on a feature; the prompt carries the auth-scope governance
spec-kitty implement WP01
```

**Backward compatibility:** single-project repositories (no `charter_scopes:` configuration) behave exactly as before. The 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged (NFR-001). No migration required.

**Exception handling:** if your monorepo configuration is malformed (e.g. two `.kittify/charter/` directories at incompatible nesting depths), the runtime reports the conflict explicitly with both paths so you can disambiguate.

---

## Recipe 3 — "I'm a team author. How do I author and select a custom workflow?"

**Persona:** a team whose actual integration flow requires an additional `design-review` step between `plan` and `tasks`.

### Step 1 — Author the workflow YAML

Create `src/doctrine/workflows/our-team-design-first.workflow.yaml`:

```yaml
workflow_id: our-team-design-first
description: "Team workflow with mandatory design-review between plan and tasks."
version: 1
initial: specify
actions:
  - action_name: specify
    next: [plan]
    description: "Author the mission specification."
  - action_name: plan
    next: [design-review]
    description: "Author the implementation plan."
  - action_name: design-review
    next: [tasks]
    description: "Design lead reviews the plan."
  - action_name: tasks
    next: [implement]
    description: "Decompose into work packages."
  - action_name: implement
    next: [review]
    description: "Execute work package."
  - action_name: review
    next: [merge]
    description: "Review."
  - action_name: merge
    next: []
    description: "Merge."
    terminal: true
```

### Step 2 — Select it for a new mission

When creating the mission, set `workflow_id` in `meta.json`:

```json
{
  "mission_id": "...",
  "mission_slug": "...",
  "workflow_id": "our-team-design-first"
}
```

### Step 3 — Run `spec-kitty next`

```bash
spec-kitty next --agent claude --mission <mission-slug>
#   Next action: specify
#     -> next: plan
#
# After /spec-kitty.specify:
spec-kitty next --agent claude --mission <mission-slug>
#   Next action: plan
#     -> next: design-review        # the extra step!
#
# After /spec-kitty.plan:
spec-kitty next --agent claude --mission <mission-slug>
#   Next action: design-review
#     -> next: tasks
```

**Backward compatibility:** missions **without** `workflow_id` (every Mission A / B / C mission predating this work) default to `software-dev-default`, which produces a byte-identical sequence to today's hardcoded behaviour (C-008). The `workflow_id` field is **opt-in, not migration-required** (NEW-2 binding).

**Exception handling:** if `meta.json` references a `workflow_id` that doesn't exist (typo, deleted YAML), `spec-kitty next` hard-fails with a message naming the unknown id and listing the available workflows. **No silent fallback** to default (FR-015).

---

## Cross-cutting: catalog-miss visibility improvement

A bonus operator-facing improvement absorbed in Slice F: when your charter selects an artifact ID that doesn't resolve (typo, missing pack, etc.), you now see a visible warning on stderr instead of a silently-degraded prompt:

```bash
spec-kitty implement WP01
# (... prompt builds ...)
# WARNING  Catalog miss: styleguide=caveman-comemnts (cause=typo). Did you mean: caveman-comments? [mission=01KRX5C8MQ..., scope=None]
```

This works under all CLI invocations — including subprocess use from CI scripts. No configuration required (the FR-130 / FR-131 bootstrap installs the handler at CLI startup).

---

## Further reading

- **Spec:** [spec.md](spec.md) — the source of truth
- **Plan:** [plan.md](plan.md) — architectural design + WP decomposition
- **Data model:** [data-model.md](data-model.md) — schemas for `OrgDRGFragment`, `CharterScope`, `WorkflowSequence`, …
- **Contracts:** [contracts/](contracts/) — 6 input/output/failure-mode contracts
- **ATDD coverage:** [atdd-coverage.md](atdd-coverage.md) — canonical executable contract for the mission
- **Predecessor mission (Mission B):** [../charter-mediated-doctrine-selection-01KRTZCA/](../charter-mediated-doctrine-selection-01KRTZCA/) — the selection-layer baseline Slice F builds on
