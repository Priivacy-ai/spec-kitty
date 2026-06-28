---
title: How to Create an Org Doctrine Pack
description: Author, validate, assemble, publish, and consume a spec-kitty org doctrine pack.
doc_status: active
updated: '2026-06-03'
related:
- docs/guides/setup-governance.md
- docs/guides/synthesize-doctrine.md
- docs/migration/doctrine-local-overlay-to-org-layer.md
---
# How to Create an Org Doctrine Pack

This guide walks a governance system maintainer through producing an org doctrine pack,
validating it, optionally assembling several packs into a single distributable, publishing
it, and configuring consumer projects to install it.

For background on what the org layer is and how it composes with built-in and project
doctrine, see [Understanding the Org Doctrine Layer](../architecture/org-doctrine-layer.md).

---

## Before you start

You need:

- Spec Kitty installed and on `PATH` (verify with `uv run spec-kitty --version`).
- A directory you control where you can lay out pack files.
- For publishing: a git remote, an HTTPS bundle location, or a custom HTTP API endpoint —
  whichever your organisation prefers.

You do **not** need a spec-kitty project to author a pack. Authoring is independent of any
consumer project.

---

## Step 1: Lay out the pack directory

The canonical layout uses one directory per artifact type. All directories are optional;
a valid pack may contain any non-empty subset.

```
my-pack/
├── directives/                 # *.directive.yaml — project rules
├── tactics/                    # *.tactic.yaml — domain tactics
├── styleguides/                # *.styleguide.yaml — style standards (subdirs allowed)
├── toolguides/                 # *.toolguide.yaml — tool usage rules
├── paradigms/                  # *.paradigm.yaml — paradigm definitions
├── procedures/                 # *.procedure.yaml — operational procedures
├── agent_profiles/             # *.agent.yaml — agent personas
├── mission_step_contracts/     # *.contract.yaml — mission step contracts
├── drg/                        # *.graph.yaml — DRG graph extension fragments
└── org-charter.yaml            # optional: org governance policy
```

**Important: do not create `pack-manifest.yaml` yourself.** It is written by
`doctrine fetch` (for non-git sources) and `doctrine pack assemble`. Authors should leave
it alone; manual edits surface as an advisory in `pack validate`.

---

## Step 2: Author your artifacts

Each artifact file conforms to the same YAML schema used elsewhere in spec-kitty. The
recipe is the same for every artifact type — give it a unique `id`, fill in the required
fields for its schema, and save it in the matching directory.

### Example: a directive

```yaml
# directives/acme-001-secret-handling.directive.yaml
id: acme-001-secret-handling
title: Never commit credentials to the repository
severity: high
description: |
  Secrets must be supplied via environment or secret manager. Pre-commit hooks
  must scan staged content for known credential shapes.
action_scope:
  - implement
  - review
```

### Example: an agent profile

```yaml
# agent_profiles/acme-implementer.agent.yaml
id: acme-implementer
role: implementer
identity: |
  An ACME engineer adopts this profile during implement actions. They prioritise
  security review, follow the change-intent canvas, and refuse to commit secrets.
governance_scope:
  - acme-001-secret-handling
```

### Namespace your IDs

IDs in an org pack collide globally with built-in and project IDs. To keep collisions
visible (and to make `doctor doctrine` output readable), prefix your IDs with an
organisation-specific code:

| Artifact type | File pattern | Recommended ID prefix |
|---|---|---|
| Directives | `*.directive.yaml` | `<org>-<seq>-<slug>` (e.g. `acme-001-secret-handling`) |
| Tactics | `*.tactic.yaml` | `<org>-tac-<seq>` |
| Styleguides | `*.styleguide.yaml` | `<org>-sty-<seq>` |
| Toolguides | `*.toolguide.yaml` | `<org>-tg-<seq>` |
| Paradigms | `*.paradigm.yaml` | `<org>-par-<seq>` |
| Procedures | `*.procedure.yaml` | `<org>-proc-<seq>` |
| Agent profiles | `*.agent.yaml` | `<org>-<role>` |
| Mission step contracts | `*.contract.yaml` | `<org>-msc-<seq>` |

Collisions with built-in IDs are **permitted** but produce a full-replace advisory at
resolution time — keep them intentional and rare.

### DRG extensions

If your pack contributes typed graph relations (for example, a new directive that scopes
to a specific mission action), add a fragment under `drg/`:

```yaml
# drg/010-security.graph.yaml
nodes: []   # nodes are inferred from the artifact files
edges:
  - source: urn:directive:acme-001-secret-handling
    target: urn:action:implement
    relation: scope
```

DRG fragments are **additive only**. They may add new edges and nodes but must not
remove or modify built-in graph state. Multiple fragment files in `drg/` merge in
alphabetical filename order, so name them with numeric prefixes when ordering matters
(`010-`, `020-`, ...).

---

## Step 3: Optional — author `org-charter.yaml`

If your pack should pre-fill the project charter interview, require specific directives
across all consumers, or surface advisory governance policies, add an `org-charter.yaml`
at the pack root:

```yaml
# org-charter.yaml
schema_version: "1"
org_name: ACME Corporation
interview_defaults:
  language: python
  test_framework: pytest
required_directives:
  - acme-001-secret-handling
  - acme-002-code-review
governance_policies:
  - field: min_test_coverage
    value: "80"
    enforcement: advisory
```

The `org-charter.yaml` file is **optional**. Packs that ship only doctrine artifacts (no
policy) simply omit it.

For more on how `org-charter.yaml` composes when multiple packs are configured, see
[the org charter composition section of the explanation doc](../architecture/org-doctrine-layer.md#org-charter-composition).

---

## Step 4: Wrap an existing governance system

If your organisation already documents its rules — typically as Markdown policy pages,
internal wikis, or a YAML config in a different format — you can migrate that content
into a pack without rewriting it from scratch.

The recipe:

1. **Identify the artifact type.** A Markdown policy doc usually maps to one or more
   directives. An "engineering principles" page often maps to paradigms. A "best practices"
   page often maps to tactics. A "how do we do X" runbook maps to a procedure.
2. **Extract one rule per file.** Resist the urge to dump a whole policy page into a
   single directive — split it so each rule has its own `id` and can be cited
   individually in lint advisories and review feedback.
3. **Validate.** Run `pack validate` after each batch (see Step 5 below) so you catch
   schema mistakes early.

**Before** (`security-policy.md`, existing Markdown wiki page):

```markdown
## Secret handling

Credentials, API tokens, and TLS private keys must never be committed to the repository.
Use the secret manager. Pre-commit hooks must scan staged content.
```

**After** (`directives/acme-001-secret-handling.directive.yaml`):

```yaml
id: acme-001-secret-handling
title: Never commit credentials to the repository
severity: high
description: |
  Credentials, API tokens, and TLS private keys must never be committed to the
  repository. Use the secret manager. Pre-commit hooks must scan staged content.
action_scope:
  - implement
  - review
```

The wiki page can keep existing — link to it from the directive's description if you
want to preserve narrative context. The directive is the structured rule the runtime
will see.

---

## Step 5: Validate the pack

Before publishing, validate against schema and DRG constraints:

```bash
uv run spec-kitty doctrine pack validate ./my-pack
```

Exit codes:

- `0` — pack passes. Advisories are printed but do not affect exit.
- `1` — pack has at least one error. Fix and re-validate.

For machine-readable output (CI integration, scripts):

```bash
uv run spec-kitty doctrine pack validate ./my-pack --json
```

### Reading the output

The validator distinguishes errors from advisories:

| Condition | Class |
|---|---|
| Artifact YAML fails schema validation | Error |
| Duplicate `id` within the pack | Error |
| Dangling DRG edge (target URN not in merged artifact set) | Error |
| DRG extension tries to modify or remove a built-in node | Error |
| `org-charter.yaml` schema violation | Error |
| Artifact ID collides with a built-in ID | Advisory |
| `pack-manifest.yaml` exists and was author-edited | Advisory |
| `enforcement` value other than `"advisory"` | Advisory |

If validation reports `Dangling DRG edge`, the named URN does not resolve in your pack's
artifact set. Either add the missing artifact, fix the URN, or remove the edge.

---

## Step 6 (optional): Assemble multiple packs into a distributable

If your organisation prefers a single distributable artifact over multiple independent
pack repositories, you can merge several packs into one with `doctrine pack assemble`:

```bash
uv run spec-kitty doctrine pack assemble \
  ./distributable-out \
  ./security-pack ./architecture-pack ./compliance-pack
```

The first positional argument is the output directory. All remaining positional arguments
are input pack directories. The command produces a single merged pack at the output
path and validates the result before exiting.

If two input packs ship the same artifact ID or define conflicting DRG edges, the
default behaviour is to **fail** with a conflict report. You have two options:

```bash
# Write the conflict report to a file for inspection
uv run spec-kitty doctrine pack assemble \
  ./out ./security ./architecture \
  --conflicts-out conflicts.json

# Resolve conflicts by last-pack-wins (and drop duplicate edges silently)
uv run spec-kitty doctrine pack assemble \
  ./out ./security ./architecture --force
```

Exit codes: `0` on success; `1` if conflicts block the merge or the assembled output
fails validation.

Adding `--json` switches the assemble summary to machine-readable output.

---

## Step 7: Publish the pack

The org layer supports three transport mechanisms. Pick one based on your distribution
model.

### Option A: Git repository (recommended)

Push the pack to a git remote your developers can reach. Tag releases.

```bash
cd my-pack
git init
git add .
git commit -m "Initial pack"
git tag v1.0.0
git remote add origin git@example.com:acme/security-doctrine.git
git push origin main v1.0.0
```

Consumers point at the git remote and pin to a tag.

### Option B: HTTPS bundle

Upload a tarball or zip to an HTTPS-served location (object storage, releases page).
Consumers download and extract.

```bash
tar czf security-doctrine-v1.0.0.tar.gz -C my-pack .
# upload to https://releases.example.com/doctrine/security-doctrine-v1.0.0.tar.gz
```

### Option C: Custom HTTP API

For organisations with an existing governance API server, expose pack contents under a
base URL. The contract for that API is in
[contracts/org-doctrine-source-api-contract.md](https://github.com/Priivacy-ai/spec-kitty/blob/main/kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/org-doctrine-source-api-contract.md)
(in the mission's planning artifacts).

### Versioning strategy

Whichever transport you choose, **pin versions** in consumer config. For git, use a tag
name or commit SHA. Branch names are accepted but discouraged for reproducibility — a
moving target on `main` will silently change behaviour for every consumer on every
fetch.

---

## Step 8: Configure consumers

A consumer project enables the org layer by adding a `doctrine.org` block to its
`.kittify/config.yaml`:

```yaml
# .kittify/config.yaml
doctrine:
  org:
    packs:
      - name: security
        local_path: "~/.kittify/org/security/"
        source_type: git
        url: "git@example.com:acme/security-doctrine.git"
        ref: "v1.0.0"
      - name: architecture
        local_path: "~/.kittify/org/architecture/"
        source_type: git
        url: "git@example.com:acme/architecture-doctrine.git"
        ref: "v0.3.0"
```

Field reference:

| Field | Required | Purpose |
|---|---|---|
| `name` | yes | Unique pack name (used by `--pack` flag, displayed in `doctor doctrine`) |
| `local_path` | yes | Filesystem path where the snapshot lives (tilde expanded) |
| `source_type` | no | One of `git`, `https`, `api`; omit if pre-provisioned |
| `url` | required if `source_type` set | Remote URL |
| `ref` | no | Version pin (git tag/SHA; HTTPS advisory; API query param) |

Then the consumer runs:

```bash
# Fetch all configured packs
uv run spec-kitty doctrine fetch

# Or fetch a single pack
uv run spec-kitty doctrine fetch --pack security

# Preview without contacting any remote
uv run spec-kitty doctrine fetch --dry-run
```

Verify the install:

```bash
uv run spec-kitty doctor doctrine
```

The output enumerates each configured pack, its on-disk version, per-artifact counts,
and `org-charter.yaml` status. Add `--json` for scripting.

Confirm the org layer is participating in actual context resolution:

```bash
uv run spec-kitty charter context --action implement --json
```

Resolved artifacts will have a `source` field of `builtin`, `org`, or `project`.

---

## Troubleshooting

### Advisory: "org layer overrides built-in artifact"

You wrote an artifact whose `id` collides with a built-in id. The override applies as
intended (full-replace), but `charter lint` and `pack validate` warn because the
collision is usually unintentional. Either rename the artifact (recommended — namespace
your IDs as in Step 2) or accept the override if you genuinely meant to replace the
built-in version.

### Error: "No artifact directories found in fetched snapshot"

The fetched pack contains no recognised artifact directories. Check that the pack root
is correct (the pack directory itself, not a parent folder) and that at least one of
the canonical subdirectories exists with valid YAML files.

### Error: "Dangling DRG edge"

A DRG fragment references a URN that does not resolve in the merged artifact set.
Either:

- Add the missing artifact to your pack.
- Fix the URN in the fragment.
- Remove the offending edge.

The validator prints the URN and the fragment file, so locate the offender by grepping
for the URN.

### Error: "DRG extension attempts to modify a built-in node"

A DRG fragment tries to remove or modify a node that originates in the built-in layer.
This is forbidden — extensions are additive only. Refactor the fragment to add new
edges or nodes instead.

---

## See also

- [Understanding the Org Doctrine Layer](../architecture/org-doctrine-layer.md)
- [Migrating shared doctrine to the org layer](../migration/doctrine-local-overlay-to-org-layer.md)
- [How to set up project governance](setup-governance.md)
- [How to synthesize and maintain doctrine](synthesize-doctrine.md)
