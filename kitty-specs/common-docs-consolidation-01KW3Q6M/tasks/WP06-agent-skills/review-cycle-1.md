# WP06 Review Feedback — Cycle 1

**Reviewer:** reviewer-renata  
**Date:** 2026-06-27  
**Verdict:** FAIL — return to planned

---

## Issue 1 (BLOCKING): ADR alignment contradiction — DoD item 1 not satisfied

**DoD item 1 requires:** "The install-vs-out-of-scope decision from the ADR is implemented."

The ADR (`architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md`) records the
following in its **Neutral consequences** section (lines 225-227):

> "The three Common Docs Agent Skills (`scaffold`/`write`/`find`) install as peer skills, but
> `find`'s static lookup table is **not** adopted — its topic→path role is backed by the richer,
> gated DRG + page-inventory."

WP06 implemented the **opposite** decision: declared all three skills **out of scope** and
installed none of them.

The research note (`02-common-docs-standard.md`, lines 120-122) then states:

> "No common-docs skills are installed. The decision is recorded in
> `architecture/3.x/adr/2026-06-27-1-common-docs-reconciliation.md` (Neutral consequences)."

This citation is a **misrepresentation**: the ADR's Neutral consequences say "install as peer
skills," not "out of scope." Citing the ADR's Neutral consequences as authority for the
out-of-scope decision contradicts the ADR.

**How to fix (choose one):**

A. **Install the skills as the ADR records** — author
   `.agents/skills/spec-kitty.common-docs-{scaffold,write,find}/SKILL.md` and register them
   in `.kittify/command-skills-manifest.json` via the canonical installer
   (`src/specify_cli/skills/`). Note: `find`'s static lookup table is explicitly NOT adopted per
   the ADR; the SKILL.md for `find` should back topic→path via the DRG + page-inventory instead.
   Remove the "out of scope" prose added to the research notes (revert the §Skills section of
   `02-common-docs-standard.md` to an accurate description of what was decided).

B. **Amend the ADR** — coordinate with the WP01 owner (architect-alphonso) to update the
   Neutral consequences to explicitly record the out-of-scope decision:
   "The three Common Docs Agent Skills (`scaffold`/`write`/`find`) are **out of scope** for
   this project — they automate nothing load-bearing; `find`'s topic→path role is already
   served by the gated DRG + page-inventory." Once the ADR is amended and merged, update the
   citation in `02-common-docs-standard.md` to match.

**Note on grep:** The remaining mentions of the skill names in the descriptive table at
`02-common-docs-standard.md` lines 76-78 are acceptable — they describe what the external
Common Docs standard offers, not claims of installation. If option A is chosen, those table
rows become correct documentation of the installed skills. If option B is chosen, the table
may be retained with the explicit "out of scope" qualifier.

---

## Non-blocking observation: status.events.jsonl merge artifact

The diff against the mission base shows a line REMOVED from
`kitty-specs/common-docs-consolidation-01KW3Q6M/status.events.jsonl`:

```
-{"actor":"claude:opus:reviewer-renata:reviewer","at":"2026-06-27T07:08:27...","to_lane":"in_review","wp_id":"WP02"}
```

This is the WP02 review-start event (emitted at 07:08:27) which post-dates WP06's implementation
commit (07:07:16). The lane-f merge at `a60cbb0d1` did not pick up this event. This is expected
parallel-lane behavior, but the event must not be lost when WP06's lane merges into the
integration branch. Flag to the operator / merge coordinator: the WP02 in_review event must be
preserved or re-emitted at merge time.

---

## Passing checks

- **ruff:** `All checks passed!` — no linting issues.
- **Owned files:** Only `docs/engineering_notes/651-docs-consolidation/index.md` and
  `02-common-docs-standard.md` were edited (both are WP06-owned). No other doc-tree
  mutations introduced.
- **Grep in WP06 worktree** (definitive, against the implemented state):
  Only the descriptive table rows 76-78 in `02-common-docs-standard.md` remain — these
  describe the external standard, not installed skills. `.agents/` is clean (no skills
  installed). `src/` is clean. `docs/engineering_notes/651-docs-consolidation/index.md`
  "Open questions" section was correctly updated to remove the installation-intent reference.
