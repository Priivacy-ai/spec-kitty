---
title: Create a doctrine artifact
description: A concrete, followable walkthrough for authoring a new doctrine artifact end to end — file location, schema, and activation.
doc_status: active
updated: '2026-07-20'
type: how-to
related:
- docs/doctrine/doctrine-kinds.md
- docs/doctrine/index.md
- docs/guides/synthesize-doctrine.md
- docs/guides/setup-governance.md
- docs/guides/troubleshoot-charter.md
---
# Create a doctrine artifact

This guide walks through authoring one new doctrine artifact — from picking a kind through
verifying it is live in governed mission context. It uses a **tactic** as the worked example
because tactics have the simplest schema and the most built-in precedent to copy from, but the
same six steps apply to any of the [eight doctrine artifact kinds](doctrine-kinds.md).

This guide covers **project-tier** artifacts — the fast, self-serve path for one project's own
doctrine. If you are building a shareable **org pack** (doctrine distributed across multiple
projects), the file layout differs; see
[Understanding the Org Doctrine Layer](../architecture/org-doctrine-layer.md) after finishing
this guide.

## Prerequisites

- A Spec Kitty project with governance set up (`.kittify/charter/charter.md` exists — see
  [How to Set Up Project Governance](../guides/setup-governance.md) if it does not yet).
- The `spec-kitty` CLI on your `PATH`.

## Step 1: Pick a kind and its project directory

Every kind has its own directory under `.kittify/doctrine/`, its own file suffix, and its own
schema. Project-tier directories use singular names for four kinds and plural names for the
rest — this is a real, code-verified asymmetry (`_PROJECT_KIND_DIRS` in
`src/charter/kind_vocabulary.py`), not a typo:

| Kind | Project directory | File suffix | Schema | ID field |
|---|---|---|---|---|
| `directive` | `.kittify/doctrine/directive/` | `.directive.yaml` | `directive.schema.yaml` | `id` |
| `tactic` | `.kittify/doctrine/tactic/` | `.tactic.yaml` | `tactic.schema.yaml` | `id` |
| `styleguide` | `.kittify/doctrine/styleguide/` | `.styleguide.yaml` | `styleguide.schema.yaml` | `id` |
| `procedure` | `.kittify/doctrine/procedure/` | `.procedure.yaml` | `procedure.schema.yaml` | `id` |
| `toolguide` | `.kittify/doctrine/toolguides/` | `.toolguide.yaml` | `toolguide.schema.yaml` | `id` |
| `paradigm` | `.kittify/doctrine/paradigms/` | `.paradigm.yaml` | `paradigm.schema.yaml` | `id` |
| `agent_profile` | `.kittify/doctrine/agent_profiles/` | `.agent.yaml` | `agent-profile.schema.yaml` | `profile-id` |
| `mission_step_contract` | `.kittify/doctrine/mission_step_contracts/` | `.step-contract.yaml` | (Pydantic model, no standalone JSON Schema file) | `id` |

Schemas live under `src/doctrine/schemas/`. If you are working from a project that installed
`spec-kitty` as a package rather than from this source checkout, the fastest way to see a kind's
required fields is to copy a real built-in file of that kind and edit it — every built-in
artifact under `src/doctrine/<kind-plural>/built-in/` is already schema-valid.

This walkthrough creates a **tactic**, so the target directory is `.kittify/doctrine/tactic/`.

## Step 2: Choose an ID

Doctrine artifact IDs are the config-stem — the filename with its kind suffix stripped — and for
most kinds must match `^[a-z][a-z0-9-]*$` (kebab-case, starting with a letter; see the `id`
pattern in `tactic.schema.yaml`). This ID is what you pass to `spec-kitty charter activate`, so
pick something you'll type again: `example-driven-api-design`, not `Tactic For API Design`.

## Step 3: Write the artifact file

Create `.kittify/doctrine/tactic/example-driven-api-design.tactic.yaml`. A tactic's schema
(`src/doctrine/schemas/tactic.schema.yaml`) requires `id`, `schema_version`, `name`, and at
least one step (each step requires at least a `title`):

```yaml
schema_version: "1.0"
id: example-driven-api-design
name: Example-Driven API Design
purpose: >
  Design a new API surface by writing the concrete request/response examples first,
  then deriving the interface from what makes the examples read cleanly. Prevents
  designing an interface that is technically coherent but awkward for real callers.
steps:
  - title: Write three realistic call examples
    description: >
      Before writing any interface signature, write out three concrete example calls a
      real caller would make, including the exact request and response shape you want
      them to see.
    examples:
      - "Good: a runnable curl example with real field values, not placeholders."
  - title: Derive the interface from the examples
    description: >
      Only after the examples read naturally, write the interface (types, endpoint
      names, parameters) that would make those exact examples true.
  - title: Check for awkward callers
    description: >
      Re-read each example as if you were a caller who has never seen the design.
      If an example needs a comment to explain why a field is shaped the way it is,
      the interface needs another pass.
failure_modes:
  - "Skipping straight to the interface and retrofitting examples afterward — the examples end up justifying the design instead of shaping it."
```

Every field here maps directly onto the schema: `schema_version` must be the literal string
`"1.0"`; `steps` is a non-empty list of objects with at least a `title`; `purpose` and
`failure_modes` are optional but recommended (see the real built-in
`problem-decomposition.tactic.yaml` cited on the [doctrine kinds](doctrine-kinds.md#tactic) page
for a fuller example with `references` to other tactics).

For a different kind, swap the required fields per the table in Step 1 — for example an
`agent_profile` additionally requires `purpose`, `specialization`, and either `role` or `roles`
(see `src/doctrine/schemas/agent-profile.schema.yaml`), and its ID field is `profile-id`, not
`id`.

## Step 4: Confirm the artifact is discovered

Project-tier doctrine is read directly off disk — no separate "import" step. Confirm your new
file is found and parses:

```bash
spec-kitty charter list --show-available
```

Your new tactic should appear as an available-but-not-yet-activated ID under the `tactic` row.
If it does not appear, re-check the filename suffix (`.tactic.yaml`, not `.yaml`) and the
directory (`.kittify/doctrine/tactic/`, singular).

## Step 5: Activate it

An artifact existing on disk is not the same as it being **active** — activation is what makes
an artifact eligible for context injection into governed mission actions. Activate by kind and
ID:

```bash
spec-kitty charter activate tactic example-driven-api-design
```

This is a fast, config-only write to `.kittify/config.yaml`'s `activated_tactics` list (see
`plan_activation`/`commit_plan` in `src/charter/activation_engine.py`) — it does not by itself
regenerate the derived bundle. If your new tactic references other artifacts (via a `references`
field) that are not yet activated, the command warns you and suggests `--cascade`:

```bash
# Activate the tactic and everything it references, in one pass
spec-kitty charter activate tactic example-driven-api-design --cascade all

# Also eagerly refresh the derived bundle/DRG immediately (otherwise this
# happens lazily on the next synthesize)
spec-kitty charter activate tactic example-driven-api-design --resynthesize
```

> **Kinds that skip explicit activation.** `agent_profile` and `mission_step_contract` do not
> use the `activated_<kind>` list at all — all built-ins for those two kinds are available
> without an activation step (`spec-kitty charter list --all` reports them as
> "All built-ins — no explicit activation"). If you are authoring one of those two kinds, Steps
> 4–5 collapse into "confirm the file is present and well-formed"; there is no `charter activate`
> call to make.

## Step 6: Verify it took effect

```bash
# Confirm the ID now shows under "Activated" for its kind
spec-kitty charter list

# Confirm overall charter health
spec-kitty charter status

# Confirm the artifact actually surfaces in a real mission action's context —
# pick an action your tactic is relevant to
spec-kitty charter context --action specify --json
```

If `charter status` reports the bundle as stale, run `spec-kitty charter synthesize` (dry-run
first) to promote it — see
[How to Synthesize and Maintain Doctrine](../guides/synthesize-doctrine.md) for the full
synthesis workflow. If something looks wrong at any step, `spec-kitty doctor doctrine` and
[Troubleshooting Charter Failures](../guides/troubleshoot-charter.md) are the first places to
check.

## Undoing this

```bash
spec-kitty charter deactivate tactic example-driven-api-design
```

Deactivating removes the ID from `activated_tactics`; it does not delete the file. Delete
`.kittify/doctrine/tactic/example-driven-api-design.tactic.yaml` directly if you want the
artifact gone entirely.

## See also

- [Doctrine artifact kinds](doctrine-kinds.md) — what each of the eight kinds is for, with a
  real example of each.
- [Understanding the Org Doctrine Layer](../architecture/org-doctrine-layer.md) — how to package
  and share doctrine artifacts across multiple projects instead of authoring them project-local.
- [How to Synthesize and Maintain Doctrine](../guides/synthesize-doctrine.md) — the broader
  synthesis/resynthesis maintenance workflow this guide's Step 6 hands off to.
