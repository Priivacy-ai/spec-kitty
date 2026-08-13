---
work_package_id: WP01
title: Guide correction — step-contract suffix (FR-001, documentation-only)
dependencies: []
requirement_refs:
- FR-001
- C-001
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
history: []
authoritative_surface: docs/guides/how-to/governance/create-an-org-doctrine-pack.md
create_intent: []
execution_mode: code_change
owned_files:
- docs/guides/how-to/governance/create-an-org-doctrine-pack.md
tags: []
---

## PR Shape (mission-level note)

This mission ships as **one PR for the whole mission** — spec-kitty's default topology, not
tk's per-WP-PR rule (`.kittify/charter/charter.md`, Collaboration Strategy: "Draft PR
first... one PR" is the spec-kitty convention this repo follows; `meta.json`'s
`"topology": "lanes"` governs in-mission worktree parallelism, not PR count). This WP is
placed in **Lane A**, independent of Lane B (WP02 → WP03 → WP04), and its own diff is placed
here at the top of the mission's first WP file because WP01 is the one WP with no upstream
dependency, making it a reasonable durable home for this note pending `tasks.md`'s
auto-generation (which will fold a short PR-shape summary in from the mission's final report).

**Assessment**: the resulting one-PR diff is a documentation edit (this WP) plus three narrow,
independently-reasoned validator diagnostics — each a small new helper function plus one call
site, plus two one-line call-site edits in two other files for FR-004's carve-outs, plus
focused tests per FR, plus one changelog entry (per plan.md's file-by-file "Source Code"
breakdown). Total touched-file count is eight non-test files across four WPs, none large,
none touching more than ~2 functions per file. This is reviewable by a human in one sitting:
each FR is self-contained (its own helper, its own tests, its own acceptance criteria), the
chokepoint file (`pack_validator.py`) accumulates changes in a strictly sequential,
low-risk-to-high-risk order that a reviewer can read top-to-bottom as three additive diffs
rather than one tangled one, and the total new production code across all three code-bearing
WPs is on the order of three new helper functions (each under 30 lines) plus two
one-line-each call-site edits — not a rewrite of any existing function. **Recommendation:
one PR, as planned.** If mission-level review finds the aggregate diff harder to hold in one
sitting than this estimate assumes (e.g., if FR-004's positive-fire fixture construction turns
out to need substantial new test scaffolding), the fallback is to split at the natural lane
boundary (WP01 alone vs. WP02+WP03+WP04 as one PR) — but nothing in the plan's Implementation
Concern Map suggests that will be necessary.

---

## Objective

Correct the org-pack authoring guide's documented step-contract file suffix from
`*.contract.yaml` to `*.step-contract.yaml` — the suffix the loader
(`src/doctrine/missions/step_contracts.py:174`) and `pack_validator.py`'s own artifact
registry (`src/specify_cli/doctrine/pack_validator.py:181`) have always required — and point
the reader at ADR `2026-08-13-1` so they learn the whole step-contract surface is slated for
retirement and do not treat the corrected suffix as a durable target.

## Context

**Why this WP exists**: every org-pack author who followed the previously published guide
named their step-contract files `*.contract.yaml`, a suffix neither the loader nor the
validator has ever matched — the file silently never loads, and `pack validate` silently
reports nothing (an empty glob match produces no error in either surface). The guide text
itself was the trap.

**Binding scope — read this before touching anything**: this WP's acceptance bar is the
binding operator ruling at
`kitty-specs/org-pack-authoring-diagnostics-01KZY463/reviews/spec.ruling.md`, not the
mission's original FR-001 draft. The ruling narrowed FR-001 to **documentation-only**. Two
whole categories of change that an earlier draft of this mission considered are **explicitly
out of scope and must not be introduced here**:

1. A shared step-contract suffix constant consumed by `step_contracts.py` and
   `pack_validator.py`'s `_artifact_schema_registry()` — dropped; the two definitions already
   agree today, and de-duplicating them hardens a surface an Accepted ADR retires wholesale.
2. A new `pack_validator.py` near-miss mismatch diagnostic for a `*.contract.yaml` file with
   no matching `*.step-contract.yaml` — dropped; it is new code on the retiring surface.
3. Removal of `snapshot.py`'s dead `_ARTIFACT_BUCKETS` table — dropped from this mission
   entirely (it is genuinely dead code, confirmed by `spec.md`'s Verified Code Surfaces table,
   but belongs to ADR `2026-08-13-1`'s retirement work, a different domain than org-pack
   authoring diagnostics — not this mission's campsite scope).

**This WP touches no code and no test file.** Per C-004's own annotation and the plan's "The
Baseline" step 4, FR-001 contributes no entry to the mission's targeted test surface and is
outside the C-011 ATDD-First Discipline's applicability (there is no runtime-observable
behaviour to pin with a failing-first test — a Markdown correction has no red state to
capture). Do not add a test for this WP.

**Why plain prose, not a Markdown link, for the ADR citation**: the ADR file
(`docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`)
does not exist on this branch — it ships only inside unmerged PR #3378. The `docs-freshness`
CI workflow's relative body-link gate
(`scripts/docs/relative_link_fixer.py --check`) checks that every relative Markdown link
(`[text](path)`) in a changed doc resolves to a real file. A Markdown link to a file that
does not yet exist on this branch would fail that gate. Cite the ADR by ID and title in
**plain prose** instead — e.g. "see ADR `2026-08-13-1`, *Built-in mission subtree stays
nested; retire legacy step contracts* (Accepted)" — so the gate has nothing to resolve and
cannot fail on a target that legitimately lands later via a different PR.

**No overlap with Lane B**: this WP's only owned file
(`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`) is not touched by any other
WP in this mission. It runs fully independently of WP02 → WP03 → WP04's chokepoint on
`pack_validator.py`.

### Subtask T001: Correct the documented suffix and cite the retirement ADR

**Purpose**: Stop the guide from instructing authors to create files the loader can never
read, and tell the reader why the corrected suffix is not a durable authoring target.

**Steps**:
1. Open `docs/guides/how-to/governance/create-an-org-doctrine-pack.md`.
2. At line **`:65`** (the layout-tree code block under "Step 1: Lay out the pack directory"),
   change:
   ```
   ├── mission_step_contracts/     # *.contract.yaml — mission step contracts
   ```
   to:
   ```
   ├── mission_step_contracts/     # *.step-contract.yaml — mission step contracts
   ```
3. At line **`:140`** (the namespace table under "Namespace your IDs"), change the row:
   ```
   | Mission step contracts | `*.contract.yaml` | `<org>-msc-<seq>` |
   ```
   to:
   ```
   | Mission step contracts | `*.step-contract.yaml` | `<org>-msc-<seq>` |
   ```
4. Immediately after the namespace table (or in a short paragraph directly below the
   corrected `:65` layout-tree entry — pick whichever placement reads more naturally in
   context; both satisfy AC-2, which only requires the citation to be "in the same guide
   section"), add a plain-prose note along these lines:

   > **Note**: the `mission_step_contracts/` surface documented above (`step_contracts.py`,
   > the `MissionStepContract` model, and this file suffix) is slated for retirement in its
   > entirety in favor of a unified `MissionStep` model — see ADR `2026-08-13-1`, *Built-in
   > mission subtree stays nested; retire legacy step contracts* (Accepted). Treat the
   > corrected suffix above as a bridge, not a durable authoring target.

   Do **not** render the ADR reference as a Markdown link (`[text](path)`) — write it as
   plain text naming the ADR ID and title, per the Context section above.
5. Search the whole file for any other occurrence of `*.contract.yaml` as the
   mission-step-contract suffix (`grep -n "\.contract\.yaml" docs/guides/how-to/governance/create-an-org-doctrine-pack.md`)
   and correct any you find — AC-1 requires **no remaining reference** to the stale suffix
   anywhere in the guide, not just at `:65` and `:140`.

**Files**: `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` (edit in place, ~3-6
line delta).

**Validation**:
- `grep -n "\.contract\.yaml" docs/guides/how-to/governance/create-an-org-doctrine-pack.md`
  returns zero matches for the mission-step-contract suffix (a legitimate substring match
  inside `*.step-contract.yaml` itself is fine — check that no *standalone*
  `*.contract.yaml` reference to this artifact type remains).
- `grep -n "step-contract.yaml" docs/guides/how-to/governance/create-an-org-doctrine-pack.md`
  shows the corrected suffix at both the layout tree and the namespace table.
- `grep -n "2026-08-13-1" docs/guides/how-to/governance/create-an-org-doctrine-pack.md` shows
  the plain-prose ADR citation.
- Manually confirm the ADR citation is NOT wrapped in `[...](...)` Markdown link syntax.

### Subtask T002: Bump the freshness date and verify the doc-gate set

**Purpose**: Keep the guide's `updated:` frontmatter honest (the charter's
`docs-freshness-sla` styleguide treats a page without a current freshness date as stale) and
confirm the specific CI sub-checks this edit is known to trip are actually satisfied before
handing this WP to review.

**Steps**:
1. In the file's YAML frontmatter, change:
   ```
   updated: '2026-07-21'
   ```
   to:
   ```
   updated: '2026-08-14'
   ```
   (today's date — the plan cites `2026-08-13` as the mission's planning date; use the actual
   date you make this edit, matching the freshness-SLA's intent that `updated` reflects when
   the content last changed).
2. Run the terminology guard (fast, ~0.1s) since this is a `docs/` prose change:
   ```bash
   pytest tests/architectural/test_no_legacy_terminology.py -q
   ```
3. If `markdownlint-cli2` is available locally, run it against the changed file; otherwise
   rely on CI's `markdownlint` step — no new Markdown syntax is introduced here beyond a
   plain-prose paragraph, so this is expected to be a no-op.
4. Confirm you did **not** touch `docs/changelog/CHANGELOG.md`, its root symlink, or any file
   outside this WP's single `owned_files` entry — this WP's diff is exactly one file.

**Files**: `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` (frontmatter line
only, in addition to T001's body edits — commit together as one change, this WP has no
red/green pair to preserve).

**Validation**:
- `git diff --stat` (once this WP's change is staged) shows exactly one file changed:
  `docs/guides/how-to/governance/create-an-org-doctrine-pack.md`.
- `pytest tests/architectural/test_no_legacy_terminology.py -q` passes.
- Frontmatter `updated:` reflects the date of this edit, not the stale `2026-07-21`.

## Definition of Done

- [ ] `:65`'s layout tree documents `*.step-contract.yaml`, not `*.contract.yaml`.
- [ ] `:140`'s namespace table documents `*.step-contract.yaml`, not `*.contract.yaml`.
- [ ] No remaining reference to `*.contract.yaml` as the mission-step-contract suffix exists
      anywhere in the guide (whole-file grep, not just the two cited lines).
- [ ] The guide cites ADR `2026-08-13-1` by ID and title, in plain prose (no Markdown
      relative link), stating the step-contract surface is slated for retirement in its
      entirety.
- [ ] The `updated:` frontmatter field is bumped to the date of this edit.
- [ ] No code file, test file, or any file other than the one guide is touched.
- [ ] `pytest tests/architectural/test_no_legacy_terminology.py -q` passes.

## Risks

- **Low risk overall** — single-file, prose-only edit with a well-defined acceptance bar (the
  binding ruling). The one real risk is scope creep: an implementer familiar with the
  mission's original (pre-ruling) FR-001 draft might reflexively add the suffix constant, the
  near-miss diagnostic, or the `_ARTIFACT_BUCKETS` removal. All three are explicitly dropped —
  see the Context section's numbered list. If in doubt, this WP's `owned_files` is exactly one
  Markdown file; touching any `.py` file is out of scope by construction.
- **Relative-link-checker false-fail**: if the ADR citation is accidentally written as a
  Markdown link (`[ADR 2026-08-13-1](../../../adr/3.x/...)`) instead of plain prose, the
  `docs-freshness` workflow's relative body-link gate will fail because the target file does
  not exist on this branch. Double-check the citation renders as plain text before finishing.

## Reviewer Guidance

- Verify this WP's diff against `kitty-specs/org-pack-authoring-diagnostics-01KZY463/reviews/spec.ruling.md`
  directly, not against the mission's original FR-001 prose — the ruling **replaces** the
  acceptance bar. A reviewer who checks this WP against the original spec text will
  incorrectly flag the docs-only scope as "under-specified."
- Confirm the diff touches exactly one file (`docs/guides/how-to/governance/create-an-org-doctrine-pack.md`)
  and zero lines of Python.
- There is no red/green test pair to verify for this WP — C-011's ATDD-First Discipline does
  not apply here (see Context section). Do not ask for a test; do not treat the absence of
  one as a defect.
- Confirm the ADR citation is plain prose, not a Markdown relative link (see Risks).
- This WP has no dependency on, and no dependents among, WP02/WP03/WP04 — it can be reviewed
  and merged independently of Lane B's progress.

---

`spec-kitty agent action implement WP01 --agent <name>`
