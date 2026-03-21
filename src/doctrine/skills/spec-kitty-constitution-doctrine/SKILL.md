---
name: spec-kitty-constitution-doctrine
description: >-
  Run constitution interview, generation, context, and sync workflows for
  project governance in Spec Kitty 2.x.
  Triggers: "interview for constitution", "generate constitution",
  "sync constitution", "use doctrine", "set up governance",
  "constitution status", "extract governance config".
  Does NOT handle: generic spec writing not tied to governance,
  direct runtime loop advancement, setup/repair diagnostics,
  or editorial glossary maintenance.
---

# spec-kitty-constitution-doctrine

Manage the constitution lifecycle: interview, generate, context-load, sync,
and status. The constitution is the single authoritative governance document
for a Spec Kitty project. All structured config (governance.yaml,
directives.yaml, references.yaml) is derived from it.

---

## Step 1: Understand the Governance Model

Three layers:

1. **Constitution** -- human-readable markdown capturing project policy
   (testing, quality, branching, directives, tools). Lives at
   `.kittify/constitution/constitution.md`.

2. **Extracted config** -- structured YAML derived deterministically by sync.
   Machine-readable, consumed by the runtime at each workflow action.

3. **Doctrine references** -- library documents providing detailed guidance
   for selected paradigms, directives, and tools. Stored under
   `.kittify/constitution/library/`.

The constitution constrains runtime behavior. When the runtime loads context
for a workflow action (specify, plan, implement, review), it reads governance
config and injects policy into the agent prompt. Doctrine is not advisory --
it shapes what the agent sees and does.

See `references/doctrine-artifact-structure.md` for the file layout.

---

## Step 2: Run the Constitution Interview

**Fast path (deterministic defaults):**

```bash
spec-kitty constitution interview --mission software-dev --profile minimal --defaults --json
```

**Full interactive interview:**

```bash
spec-kitty constitution interview --mission software-dev --profile comprehensive
```

Key flags: `--profile minimal|comprehensive`, `--defaults`, `--json`,
`--selected-paradigms`, `--selected-directives`, `--available-tools`.
See `references/constitution-command-map.md` for all flags.

**Output:** `.kittify/constitution/interview/answers.yaml`

---

## Step 3: Generate the Constitution

```bash
spec-kitty constitution generate --from-interview --json
```

Key flags: `--mission`, `--force`, `--from-interview`, `--json`.

Generation triggers an automatic sync, so governance.yaml and directives.yaml
are written immediately.

**Output:** `.kittify/constitution/constitution.md` plus extracted YAML files.

---

## Step 4: Load Context for Workflow Actions

Load governance context before each workflow action:

```bash
spec-kitty constitution context --action specify --json
spec-kitty constitution context --action plan --json
spec-kitty constitution context --action implement --json
spec-kitty constitution context --action review --json
```

| Mode | When | Content |
|------|------|---------|
| `bootstrap` | First load for an action | Full policy summary + reference doc list |
| `compact` | Subsequent loads | Resolved paradigms, directives, tools |
| `missing` | No constitution exists | Instructions to create one |

The runtime calls context automatically. Manual invocation is useful for
debugging what governance policy an action will receive.

---

## Step 5: Sync After Manual Edits

```bash
spec-kitty constitution sync --json
spec-kitty constitution sync --force --json   # re-extract even if unchanged
```

Sync produces `governance.yaml`, `directives.yaml`, and `metadata.yaml`.
It is idempotent -- skips extraction when the constitution hash is unchanged
unless `--force` is passed.

---

## Step 6: Check Status

```bash
spec-kitty constitution status --json
```

Reports `synced` or `stale`, current and stored hashes, library doc count,
and per-file sizes.

---

## When Doctrine Constrains Runtime

Doctrine constrains the runtime when:

- **Testing policy** applies -- `min_coverage: 90` blocks review acceptance.
- **Quality gates** apply -- `pre_commit_hooks: true` prevents hook bypass.
- **Branch strategy** applies -- `main_branch: main` sets the merge target.
- **Directives fire** -- rules with `severity: error` block progression.

Doctrine does NOT constrain when:

- The user works outside a mission.
- No constitution has been generated.
- The action is not a bootstrap action (specify, plan, implement, review).

---

## Governance Anti-Patterns

1. **Editing derived files** -- `governance.yaml`, `directives.yaml`, and
   `library/*.md` are overwritten by sync/generate. Edit `constitution.md`.
2. **Skipping the interview** -- produces generic defaults; the constitution
   is most valuable with project-specific decisions.
3. **Stale constitution** -- an outdated constitution silently injects wrong
   policy. Run `status` to check, `sync` to fix.
4. **Legacy path assumptions** -- canonical path is
   `.kittify/constitution/constitution.md`, not `.kittify/memory/`.

See `references/doctrine-artifact-structure.md` for the full anti-pattern table.

---

## References

- `references/constitution-command-map.md` -- Full CLI command reference with all flags and output fields
- `references/doctrine-artifact-structure.md` -- File layout, authority classes, and data flow
