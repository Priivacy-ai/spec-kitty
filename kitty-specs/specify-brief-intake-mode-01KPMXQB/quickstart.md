# Quickstart: Specify Brief Intake Mode

## The problem this solves

You have a plan document — from Claude Code plan mode, Cursor, Codex, a Linear ticket, or just a Markdown file you wrote. Without this feature, `/spec-kitty.specify` ignores it and asks discovery questions the plan already answers. With this feature, you hand the plan to Spec Kitty and get a spec in minutes.

---

## Workflow: plan document → spec

```bash
# 1. You have a plan document
cat PLAN.md

# 2. Ingest it
spec-kitty intake PLAN.md

# Output:
#   ✓ Brief written to .kittify/mission-brief.md
#   ✓ Provenance written to .kittify/brief-source.yaml

# 3. Run specify — brief is detected automatically
/spec-kitty.specify

# Agent output:
#   BRIEF DETECTED: .kittify/mission-brief.md (source: PLAN.md)
#   Reading brief...
#   [one-paragraph summary]
#   [0–2 gap-filling questions, or none]
#   [extracted FR/NFR/C set for confirmation]
#   → spec.md written and committed
#   → brief files deleted
```

## Stdin / piped input

```bash
# Pipe from any source
cat PLAN.md | spec-kitty intake -
echo "Build a login page with email + password" | spec-kitty intake -
pbpaste | spec-kitty intake -      # macOS clipboard
```

## Inspect the current brief

```bash
spec-kitty intake --show
# Prints: brief content + source_file, ingested_at, brief_hash
```

## Overwrite an existing brief

```bash
spec-kitty intake REVISED_PLAN.md --force
```

## Tracker ticket flow (no change needed)

If you created the mission with `mission create --from-ticket`, the ticket context file is already in place. Just run `/spec-kitty.specify` — it detects `ticket-context.md` automatically (priority 2 behind `mission-brief.md`).

---

## What the brief files look like

**`.kittify/mission-brief.md`**:
```markdown
<!-- spec-kitty intake: ingested from PLAN.md at 2026-04-20T07:47:00+00:00 -->
<!-- brief_hash: a3f8c2d1... -->

# My Plan

[your plan content verbatim]
```

**`.kittify/brief-source.yaml`**:
```yaml
source_file: PLAN.md
ingested_at: "2026-04-20T07:47:00+00:00"
brief_hash: "a3f8c2d1..."
```

Both files are gitignored. They exist only until `/spec-kitty.specify` commits `spec.md`, then they are deleted.

---

## Brief quality and discovery questions

| Your plan contains | Questions asked |
|-------------------|----------------|
| Objective + constraints + approach + acceptance criteria | 0–1 |
| Objective + constraints, no acceptance criteria | 2–3 |
| Goal statement only | 4–5 |
| Nothing (no brief file) | Full discovery interview (current behaviour) |

---

## The `spec-kitty plan` command is unchanged

`spec-kitty intake` is a separate root-level command. `spec-kitty plan` (which scaffolds `plan.md`) is untouched.
