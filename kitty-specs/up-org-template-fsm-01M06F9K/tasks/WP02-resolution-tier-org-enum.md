---
work_package_id: WP02
title: ResolutionTier.ORG enum member and _tier_to_origin label
dependencies: []
requirement_refs:
- FR-002
- FR-012
planning_base_branch: up-org-template-fsm
merge_target_branch: up-org-template-fsm
branch_strategy: Planning artifacts for this mission were generated on up-org-template-fsm. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into up-org-template-fsm unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
phase: Phase 1 - Foundation
history:
- at: '2026-08-17T00:02:22Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: ''
authoritative_surface: src/doctrine/resolver.py
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/resolver.py
- src/charter/activation/template_resolver.py
- tests/doctrine/test_resolver.py
- tests/charter/test_template_resolver.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP02 – `ResolutionTier.ORG` Enum Member + `_tier_to_origin` Label

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any
user-defined profile), and behave according to its guidance before parsing the rest of this
prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for
`task_type: implement` and `authoritative_surface: src/doctrine/resolver.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review.
Address every feedback item and update the Activity Log as you go.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

---

## Objectives & Success Criteria

This WP is **IC-02** from `plan.md`'s Implementation Concern Map. It establishes the new tier's
identity **once**, in the single place both resolver modules and the charter facade share it from,
so WP03, WP04, and WP05 can all reference `ResolutionTier.ORG` without redefining it.

**Success criteria**:
- `ResolutionTier` gains a 6th member, `ORG`, positioned between `LEGACY` and `GLOBAL_MISSION`.
- `charter.resolution.ResolutionTier is doctrine.resolver.ResolutionTier` continues to hold by
  **identity** (re-export, not a parallel declaration) — no edit needed in `src/charter/resolution.py`.
- `CharterTemplateResolver._tier_to_origin` gains an `ORG` entry so an org-tier resolution reached
  through that class renders `"org/..."` instead of falling back to `"unknown/..."`.

## Context & Constraints

Read before starting:
- `kitty-specs/up-org-template-fsm-01M06F9K/spec.md` — FR-002, FR-012, DEC-008, Key Entities
  (`ResolutionTier.ORG`).
- `kitty-specs/up-org-template-fsm-01M06F9K/plan.md` — IC-02's Purpose/Risks; Plan-Time
  Verification's citations for `src/doctrine/resolver.py:47-52` (the enum),
  `src/charter/resolution.py:29` (re-export by identity), and
  `src/charter/activation/template_resolver.py:165-174` (`_tier_to_origin`'s `tier_prefix` dict).

**This mission is dogfooded inside spec-kitty's own repository — a PUBLIC repo based on `main`.**
No host paths, no usernames, no absolute local paths in any committed file — sweep your diff before
finishing.

`src/charter/resolution.py` re-exports `ResolutionTier` **by identity** — you do not need to (and
must not) add a second, parallel `ORG` declaration there. Verify this yourself by reading
`src/charter/resolution.py`'s import line before assuming it needs an edit.

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: {{planning_base_branch}}
- **Merge target branch**: {{merge_target_branch}}

Implementation command (no dependencies):
```bash
spec-kitty agent action implement WP02 --agent <name>
```

## Subtasks & Detailed Guidance

### Subtask T006 – Add the `ORG` enum member

**Purpose**: Give the org tier a real identity in the one enum both resolver modules and the
charter facade share.

**Steps**:
1. Open `src/doctrine/resolver.py` and locate `class ResolutionTier(Enum):` (currently around
   lines 47-52 — re-verify the live line numbers).
2. Insert `ORG = "org"` **between** `LEGACY` and `GLOBAL_MISSION`:
   ```python
   class ResolutionTier(Enum):
       OVERRIDE = "override"
       LEGACY = "legacy"
       ORG = "org"
       GLOBAL_MISSION = "global_mission"
       GLOBAL = "global"
       PACKAGE_DEFAULT = "package_default"
   ```
3. Do not change any other member's name or value.

**Files**: `src/doctrine/resolver.py`.

**Parallel?**: Yes, alongside T008 (different files) — but T008's test can only meaningfully
reference `ResolutionTier.ORG` once this subtask lands, so do this one first in practice.

**Notes**: Position matters — `plan.md`/spec.md are explicit that ORG sits "between LEGACY and
GLOBAL_MISSION" in precedence. WP03 and WP04 both insert their org-tier logic at this exact
relative position; getting the enum's declared order right here does not by itself enforce runtime
precedence (that is WP03/WP04's job), but it keeps the vocabulary consistent.

### Subtask T007 – Identity test

**Purpose**: Prove the re-export contract holds, not just that `ORG` exists somewhere.

**Steps**:
1. In `tests/doctrine/test_resolver.py`, add a test asserting:
   - `ResolutionTier.ORG` exists (`hasattr` or direct reference).
   - `from charter.resolution import ResolutionTier as CharterResolutionTier;
     assert CharterResolutionTier is ResolutionTier` — identity (`is`), not merely
     `CharterResolutionTier.ORG == ResolutionTier.ORG` (value equality would pass even for two
     separate enum classes with the same member values, which is not what the re-export guarantees).

**Files**: `tests/doctrine/test_resolver.py`.

**Parallel?**: No — depends on T006.

### Subtask T008 – Red-first `_tier_to_origin` test

**Purpose**: Capture DEC-008's "before" state — prove the silent-`"unknown/..."`-degradation
exists today, before fixing it.

**Steps**:
1. In `tests/charter/test_template_resolver.py`, add a test calling
   `CharterTemplateResolver._tier_to_origin(ResolutionTier.ORG, "software-dev", "templates",
   "spec-template.md")` and asserting the result starts with `"unknown/"` (pre-fix).
2. Note: `tests/charter/test_template_resolver.py:113` already has
   `test_tier_to_origin_falls_back_to_unknown_prefix`, which uses a generic `object()` sentinel to
   test the fallback path in general — do not confuse that test with this one. This new test is
   specifically about the real `ResolutionTier.ORG` member, which (pre-T009) is a real enum member
   not yet present in the `tier_prefix` dict, distinct from an arbitrary non-tier sentinel.
3. Run the test and capture the failure/pass output for the WP report (it will *pass* pre-fix,
   since `"unknown/..."` is the expected, defective behavior at this point — the "red" state here
   is a red *feature* test asserting the post-fix `"org/..."` value, which should fail before T009
   lands. Write the assertion for the **post-fix** value (`"org/..."`) and run it now to confirm it
   fails for the right reason.)

**Files**: `tests/charter/test_template_resolver.py`.

**Parallel?**: Depends on T006 (needs `ResolutionTier.ORG` to exist to reference it).

### Subtask T009 – Add the `ORG` label

**Purpose**: Close DEC-008's gap.

**Steps**:
1. Open `src/charter/activation/template_resolver.py` and locate `_tier_to_origin`'s `tier_prefix` dict
   (currently around lines 165-174 — re-verify).
2. Add `ResolutionTier.ORG: "org",` to the dict, in the same style as the existing entries
   (`ResolutionTier.OVERRIDE: "override"`, etc.).
3. Confirm T008's test now passes (renders `"org/..."`).

**Files**: `src/charter/activation/template_resolver.py`.

**Parallel?**: No — depends on T008 (red-first).

### Subtask T010 – Exhaustive-match grep sweep

**Purpose**: `plan.md`'s IC-02 risk note flags that code iterating `ResolutionTier` by an
exhaustive `match`/`if-elif` chain over all members might need a new `ORG` arm — this was not
identified during planning's grounding pass, but was also not exhaustively ruled out.

**Steps**:
1. Grep the codebase for `ResolutionTier.PACKAGE_DEFAULT` and `ResolutionTier.GLOBAL_MISSION`
   (the two members most likely to appear in an exhaustive chain, being the two most-recently-added
   before this mission) to find candidate call sites:
   ```bash
   grep -rn "ResolutionTier\." src/ | grep -v "^src/doctrine/resolver.py\|^src/charter/activation/template_resolver.py"
   ```
2. For each hit, check whether it is an exhaustive match (every member has an explicit arm, no
   default/fallback) or has a safe default (like `_tier_to_origin`'s `.get(tier, "unknown")`,
   which degrades silently rather than raising — already fixed for this one call site by T009, but
   there may be others).
3. Report findings in the WP report: either "none found" (if the sweep turns up nothing) or a list
   of additional call sites that need a new `ORG` arm, with a recommendation for whether they are
   in scope for this WP or should be flagged for a follow-up.

**Files**: None (investigation-only; may surface follow-up edits — if a genuine silent-degradation
site is found outside `owned_files`, report it rather than editing outside this WP's ownership
without a one-line rationale).

**Parallel?**: No — do this last, after T006-T009 land, so the enum's final shape is what you're
sweeping against.

## Test Strategy

```bash
pytest tests/doctrine/test_resolver.py tests/charter/test_template_resolver.py -q
```
FR-002 and FR-012 fall under the **diff-coverage critical-path** list (`src/doctrine/*` is in
`.github/workflows/ci-quality.yml:3349`'s `--fail-under=90` scope) — `src/charter/activation/template_resolver.py`
is not `src/doctrine/*`, but treat both with the same rigor.

## Risks & Mitigations

- **Low risk overall** (per `plan.md`'s IC-02 risk assessment) — FR-012 has zero production callers
  today (DEC-008), so there is no live-path regression surface for the label fix.
- Enum member insertion position should not break iteration order elsewhere, but T010 exists
  specifically because this was not exhaustively verified during planning.

## Review Guidance

A reviewer should confirm:
1. `ResolutionTier.ORG = "org"` sits between `LEGACY` and `GLOBAL_MISSION` in the enum declaration.
2. T007's identity test uses `is`, not `==`.
3. T008's test references the real `ResolutionTier.ORG` member, distinct from the existing generic
   `object()`-sentinel fallback test.
4. `src/charter/resolution.py` was **not** edited (re-export by identity needs no change) — if it
   was edited, ask why.
5. T010's sweep findings are reported, even if the answer is "none found".

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-08-17T00:02:22Z – system – Prompt created.
