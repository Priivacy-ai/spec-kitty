---
name: paula-patterns
description: >-
  Architecture-scout review for recurring boundary leaks, ownership confusion,
  whack-a-field fixes, and regressions where point patches keep exposing the
  same missing architecture decision. Dispatches five architecture scouts with
  different philosophies, then synthesizes a matrix that separates the smallest
  release-safe fix from deferred architecture work. Use when asked for "Paula
  Patterns", "architecture scouts", "why does this keep recurring", "boundary
  leakage", "ownership confusion", or "not another point fix". Do not use for
  cheap local defects, purely mechanical refactors, or first-occurrence issues
  without evidence of architectural recurrence.
---

# Paula Patterns

Paula Patterns is a heavyweight architecture-review skill. It dispatches
five independent architecture scouts over the same review surface, then the
parent LLM synthesizes their findings into one pragmatic decision.

Use it when a change feels like whack-a-field fixes, repeated regressions,
ownership confusion, or boundary leakage. The skill should answer:

- Why does this problem keep recurring?
- Which architectural boundary is missing or violated?
- Which short-term release fix is appropriate now?
- Which long-term architecture issue should be filed separately?

This skill is the agent-facing entry point. The reusable doctrine procedure is
the `paula-patterns-architecture-scout-review` tactic. Load that tactic when
you need the durable doctrine artifact; use this skill when operating an agent
session.

---

## When to Use This Skill

Use Paula Patterns when any of these are true:

- A review keeps finding new variants of the same missing field, state, or
  boundary rule.
- Multiple fixes have patched symptoms but not ownership.
- Logic crosses presentation, application, domain, and infrastructure layers.
- External system details leak into core domain decisions.
- Observed state, generated diagnostics, or machine-output contracts are being
  treated inconsistently.
- The team needs to decide what must ship now vs what belongs in a follow-up
  architecture issue.

Do not use Paula Patterns when:

- The defect is a one-line typo or localized stack-trace fix.
- The desired output is a full rewrite plan before a release.
- There is no recurrence, boundary, or ownership question.
- Five subagents would cost more than simply reviewing the change directly.

---

## Step 1: Frame the Review Surface

Load the reusable doctrine tactic
`paula-patterns-architecture-scout-review`, then write one shared review
statement for all five scouts. Include:

- The observed recurrence or review smell.
- The files, PR, issue, or diff range under review.
- Prior reactive fixes and what each changed.
- The boundary or ownership question the team keeps circling.
- Any release deadline or compatibility constraint.

Do not include your own preferred architecture answer in the shared statement.
The scouts must inspect independently.

---

## Step 2: Dispatch Five Architecture Scouts

Read `references/scout-prompts.md` and dispatch all five scouts in parallel
where tool support allows:

- Layered Architecture Scout.
- Bounded Context / DDD Scout.
- Event-Driven Architecture Scout.
- Hexagonal / Ports-and-Adapters Scout.
- Consumer Compatibility / Contract Scout.

Each scout gets the same review statement and its role-specific prompt from
`references/scout-prompts.md`. Do not inline-modify those prompts in the skill
body; keep the copyable prompts in the reference file and the reusable
procedure in the tactic.

---

## Step 3: Synthesize Through the Tactic

Follow `paula-patterns-architecture-scout-review` for the synthesis rules.
The parent LLM owns the architecture decision and must not paste the five
reports back-to-back. Use the matrix template in
`references/synthesis-matrix.md`:

| Finding | Layered | DDD | EDA | Hexagonal | Contract | Evidence | Release action | Long-term action |
|---|---|---|---|---|---|---|---|---|

For each recurring issue, identify:

- Shared root cause across lenses.
- Concrete release blocker, if any.
- Smallest safe release fix.
- Deferred architecture issue.
- Tests required before merge.

The parent decision must separate:

- **Release fix:** smallest change that safely closes the currently observed
  failure without destabilizing the release.
- **Long-term architecture fix:** boundary, ownership, contract, or state model
  work that deserves a separate issue or mission.

Do not let a scout force a large refactor into the release path. Also do not
hide a true release blocker by calling it architecture debt.

---

## Step 4: Produce the Decision

Return these sections:

1. `Verdict`
   - Whether Paula Patterns was warranted.
   - Release blocker yes/no.
   - Recommended release action.
   - Recommended long-term architecture action.

2. `Scout Matrix`
   - The synthesis matrix above.

3. `Release Fix`
   - Files or modules likely touched.
   - Tests required before merge.
   - Compatibility constraints.

4. `Long-Term Issue`
   - Issue title.
   - Problem statement.
   - Architecture boundary to restore.
   - Non-goals.

5. `Scout Notes`
   - Unique findings from each scout.
   - Divergence that the parent accepted or rejected, with reason.

---

## Reference Pattern: #1343 / #1359 uv-tool Remediation

Problem: `spec-kitty review` needed uv-tool remediation for a missing test
runner, but fixes kept missing Git/source installs, version specifier quoting,
spoofed uv paths, custom `UV_TOOL_DIR`, Windows shell syntax, and editable extra
deps.

Scout synthesis:

- Layered: review command was parsing uv receipts and rendering installer
  commands.
- DDD: `InstallMethod.UV_TOOL` was too thin; the real domain was installed CLI
  runtime/provenance.
- EDA: heuristic detection became mutation authority without verified runtime
  state.
- Hexagonal: shell strings were used instead of structured
  `argv/env/platform/provenance` command data.
- Contract: JSON diagnostic exposed one shell string, creating POSIX/Windows
  and machine-output risk.

Release action:

- Patch known uv-tool receipt/provenance cases in #1359.
- Keep JSON diagnostic stable.
- Avoid a full runtime/provenance refactor before release.

Long-term action:

- File #1358 for shared `InstalledCliRuntime` and structured remediation
  planning.

---

## References

- `references/scout-prompts.md` - copyable scout prompts and output contracts.
- `references/synthesis-matrix.md` - parent synthesis template and example.
- Doctrine tactic: `paula-patterns-architecture-scout-review`.
