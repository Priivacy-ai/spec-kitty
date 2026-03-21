---
name: spec-kitty-glossary-context
description: >-
  Curate and apply canonical terminology across Spec Kitty missions.
  Triggers: "update the glossary", "use canonical terms", "check terminology",
  "add a term", "fix term drift", "glossary conflicts", "resolve ambiguity",
  "review terminology consistency".
  Does NOT handle: runtime loop advancement, setup or repair requests,
  agent configuration, or direct code implementation tasks.
---

# spec-kitty-glossary-context

Maintain semantic integrity by curating the project glossary, detecting term
drift, and ensuring that all mission artifacts use canonical terminology.

Use this skill when the user wants to inspect, update, or enforce glossary
terms. Do not use it for purely operational tasks like advancing the runtime
loop or repairing an installation.

---

## Step 1: Locate Glossary Context

Identify the glossary state for the current project.

**What to check:**

- Seed files under `.kittify/glossaries/` (one YAML per scope)
- Event logs under `.kittify/events/glossary/` (JSONL, event-sourced)
- The store replays seed files then events at query time

**Commands:**

```bash
spec-kitty glossary list
spec-kitty glossary list --scope spec_kitty_core
spec-kitty glossary list --status active --json
```

**Scopes** (highest to lowest precedence): `mission_local`, `team_domain`,
`audience_domain`, `spec_kitty_core`. When the same surface appears in
multiple scopes, the narrower scope wins. See `references/glossary-field-guide.md`
for full scope details.

**Expected outcome:** You know which scopes are populated and whether event
logs contain runtime mutations.

---

## Step 2: Understand How the Glossary Affects Runtime

The glossary gates mission execution through the strictness system.

**Strictness modes:** `off` (never block), `medium` (block HIGH severity only),
`max` (block any conflict). Resolved via four-tier precedence: global config,
mission override, step override, runtime override.

**Conflict types:** `unknown` (not in any scope), `ambiguous` (2+ active senses),
`inconsistent` (output contradicts definition), `unresolved_critical` (critical
step, low confidence). See `references/glossary-field-guide.md` for severity
scoring and the full conflict resolution flow.

**Commands:**

```bash
spec-kitty glossary conflicts
spec-kitty glossary conflicts --unresolved
spec-kitty glossary conflicts --strictness max --mission 012-documentation-mission
```

**Expected outcome:** You understand why a conflict blocked the runtime, or you
can confirm no blocking conflicts exist.

---

## Step 3: Update Terms and Resolve Conflicts

**Adding or editing terms:** Edit the seed file for the appropriate scope.
See `references/glossary-field-guide.md` for the seed file schema.

Choose the scope by term ownership:

- Project-internal jargon: `mission_local.yaml`
- Shared domain vocabulary: `team_domain.yaml`
- User-facing terms: `audience_domain.yaml`
- Spec Kitty concepts: `spec_kitty_core.yaml` (rarely edited)

Rules: `surface` must be lowercase/trimmed; `status` is `active`, `deprecated`,
or `draft`; `confidence` is 0.0--1.0.

**Resolving conflicts interactively:**

```bash
spec-kitty glossary resolve <conflict_id>
spec-kitty glossary resolve <conflict_id> --mission 012-docs
```

The resolver presents candidate senses. You can select one, enter a custom
definition, or defer. Custom definitions emit both a
`GlossaryClarificationResolved` and a `GlossarySenseUpdated` event.

**Deprecating a term:** Set `status: deprecated` in the seed file. Deprecated
senses are excluded from resolution but remain in event history.

**Expected outcome:** The glossary reflects intended terminology and runtime-
blocking conflicts are resolved.

---

## Step 4: Detect and Prevent Semantic Drift

Semantic drift occurs when artifacts gradually diverge from glossary definitions.
See `references/semantic-drift-examples.md` for six concrete drift patterns.

**Detection:**

1. Run `spec-kitty glossary list --json` and compare definitions against spec,
   plan, and task files
2. Run `spec-kitty glossary conflicts --unresolved` for terms the runtime flagged
3. Search WP frontmatter for informal synonyms (e.g., "task" instead of the
   canonical "work package")

**Correction:**

- Artifact is wrong: replace with the canonical term
- Glossary is outdated: update the seed file definition
- Genuinely ambiguous: add a second sense and let the strictness system force
  disambiguation

**Prevention:**

- Set strictness to `medium` or `max` so the runtime catches conflicts early
- Add domain terms to the glossary before writing specs that use them
- Review the conflict log after each completed mission

**Consistency checklist:**

1. Every WP title and description uses canonical surface forms
2. Plan documents reference terms as defined in the glossary
3. No informal synonyms appear without a corresponding glossary entry
4. Deprecated terms are not reintroduced in new artifacts

**Expected outcome:** Terminology is consistent across all mission artifacts
and the glossary remains a living, enforced contract.

---

## References

- `references/glossary-field-guide.md` -- Seed file schema, scope precedence, status lifecycle, event-sourcing mechanics, and CLI quick reference
- `references/semantic-drift-examples.md` -- Concrete drift patterns with detection and correction strategies
