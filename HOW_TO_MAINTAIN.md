# HOW TO MAINTAIN — Spec Kitty Issue Tracker

> Maintainer entry-point for tracker hygiene. Authored 2026-06-16 (planner-priti, governance op).
> Grounded in **live repo data** (`Priivacy-ai/spec-kitty`) and the operator conventions in
> [`work/TRACKER_DOCTRINE_NOTES.md`](work/TRACKER_DOCTRINE_NOTES.md). Items marked **(inferred)**
> are derived from observed usage, not an explicit written rule; everything else is **confirmed**
> from the label taxonomy, native GitHub Types, or an existing convention doc.
>
> Decision rationale for the milestone / release-goal recommendations lives in
> [§5 Recommended additions](#5-recommended-additions) (per Directive 003 — Decision Documentation).

---

## 1. Issue tracker structure

Three structural roles. Keep them distinct — conflating them is the most common drift.

| Role | What it is | Parenting rule |
|------|-----------|----------------|
| **Functional epic** | A *domain that produces code/behaviour* — a subsystem, capability, or bug-class. Labelled `epic`, native Type `Feature`. | **Owns** work. Functional tickets are parented here via native sub-issues. |
| **Functional ticket** | A single Bug / Task / enhancement that changes the product. | Lives under exactly one functional epic (single-parent constraint). |
| **Meta-tracker** | A release / go-no-go / stabilization rollup (e.g. *3.2.0 release tracker*). **Not** a domain of work. | **NEVER the canonical parent** of functional tickets. Prefix `META-TRACKER:`. References work via a body checklist only. |

**The cardinal rule (confirmed — CLAUDE.md "Meta vs functional epics" + TRACKER_DOCTRINE_NOTES §1):**
> Functional epics own work; meta-trackers only *reference* it. Never make a meta-tracker the parent
> of a functional ticket — use a checklist in the meta-tracker body, and parent the ticket under its
> functional epic.

Live example of the pattern done right: **#1929** (`Tracking: post-#1908 adversarial-panel findings`)
is a checklist-only meta view; each of its four findings (#1915–#1918) is canonically parented under
its *functional* epic (#1795/#1868/#1666/#1914), and #1929 explicitly states it is **not** their parent.

### Native sub-issues are the source of truth

- Parent/child is the **native GitHub sub-issue graph**, *not* body checklists (checklists are invisible
  to tooling). **Confirmed:** 29 of 35 open epics already use native sub-issues; e.g. **#1619** carries 10
  native children. Backfill native links wherever a body checklist implies a parent.
- REST: `POST/DELETE /repos/{owner}/{repo}/issues/{n}/sub_issues`; `sub_issue_id` is the integer
  **database id** (use `gh api -F`, not `-f`). Single-parent → `DELETE` from the old parent before `POST`.
- `.parent` is reliable only via **GraphQL** (`issue.parent`), not REST.

### Hygiene invariants (every open ticket)

1. Resolves to a **functional epic** — not an orphan, not meta-rooted, not under a closed/superseded epic.
2. Has an **issue Type** (`Task` / `Bug` / `Feature`; epics = `Feature`). See [§3](#3-issue-types).
3. Has a **priority** label (`priority:P0..P3`). See [§2](#2-priority-levels).

Sweep closed epics for *open* children and rehome them — open tickets under a closed parent look
tracked but are invisible.

### How a mission maps to issues

A mission's **issue-matrix** (in the mission spec) lists every tracker issue the mission addresses.
At spec time:

- Every addressed issue → a row in the issue-matrix **and** a tracker comment naming the mission.
- The issue is **claimed** (assigned to the operator) per the claim discipline below.

**Claim discipline (operator rule, 2026-06-16):**

- **Claim before WORKING** a ticket — assign it to yourself/operator *before* starting implementation,
  so concurrent agents/contributors don't collide.
- **Closing / cleanup is exempt.** You may close a provably-done ticket **without claiming it first** —
  attach an evidence comment (the PR/commit/test proving it's done). No claim needed to close.

---

## 2. Priority levels

Priority is a **tracker-state label** (`priority:P0..P3`), distinct from the MoSCoW planning lens
(MoSCoW = a scoping discipline at mission-negotiation time; `priority:Px` = backlog state). Both
coexist; do not collapse one into the other.

Operational meaning is **confirmed** from the label descriptions and **(inferred)** from observed
application across the current 3.2.x stabilization lane:

| Label | Label description (confirmed) | Operational meaning (inferred from usage) | Open count | Example |
|-------|-------------------------------|-------------------------------------------|-----------:|---------|
| `priority:P0` | *Release blocker / must decide before final 3.2.0* | **Release/merge blocker.** Must be resolved or explicitly decided before the targeted release ships. | 7 | #1844 (rc verify blocked), #1619 (exec-context epic) |
| `priority:P1` | *High-value stabilization / bug or release confidence* | **Important** — high-value stabilization or release-confidence work; not a hard ship-gate but strongly targeted for the cycle. | 63 | #1978 (naming split-brain), #1945 (ToolSurfaceContract epic) |
| `priority:P2` | *Planned enhancement / post-blocker work* | **Normal** — planned enhancements / cleanup scheduled after blockers clear. | 83 | #1979, #1928 (lint/strict debt epic) |
| `priority:P3` | *Backlog / future / needs reconfirmation* | **Low** — backlog; future or needs reconfirmation before it's actionable. | 55 | #1973 (experiment), #1911 |

Triage rule: assign a **provisional priority and flag it** rather than silently guessing. The
`p1-decision:*` and `triage:*` labels (see §3) record in-flight triage decisions on top of the base level.

---

## 3. Issue Types

**Confirmed:** the repo uses GitHub's **native org-level issue Types** (not type-via-label). Three
types are enabled: `Task`, `Bug`, `Feature` (GitHub's built-in default set — note this `Feature` is
GitHub's generic Type and is *unrelated to* the prohibited domain term "feature/Mission"; do not
rename it).

| Type | Use for |
|------|---------|
| `Bug` | An unexpected problem or incorrect behaviour to fix. |
| `Task` | A specific, scoped piece of work (refactor, chore, doc, tech-debt item). |
| `Feature` | A request / new capability **and all epics** (epic = `Feature` + `epic` label). |

Set Type via GraphQL `updateIssue(input:{id, issueTypeId})` (type ids are per-repo). Derive Type
objectively — from the conventional-commit prefix + labels — not by guesswork.

**Adoption gap (inferred — action item):** Type coverage is incomplete. In an 80-issue recent-open
sample, ~24% (19/80) had **no** Type set (e.g. #1929, #1978 at time of audit). Backfilling Type on
untyped open issues is a standing hygiene task.

### Type-flavour labels (label-based, complement the native Type)

These labels add a *flavour* the three native Types don't capture:

- `tech-debt` — accumulated lint / type-check / static-analysis / code-quality debt.
- `reliability` — runtime reliability, resiliency, observability, incident-prevention.
- `usability` — operator/user experience and ergonomics.
- `documentation` — docs additions/improvements.
- `research-mission` — research-mission related.
- `deferred` / `future` — paused pending an activation trigger / out-of-cycle vision work.

### `triage:*` and `p1-decision:*` workflow labels

These record **in-flight triage state**, not the final classification:

- `triage:maybe-duplicate` — suspected dup pending confirmation (vs confirmed `duplicate`).
- `triage:needs-revision` — scope/spec needs rework before action.
- `triage:stale` — reproduce and close if no longer valid.
- `p1-decision:keep | split | close-if-stale | defer` — the disposition reached for a P1 during a
  triage sweep (keep as-is / split into children / reproduce-and-close / defer out of the lane).
- `p1:verified`, `ddd-audit:reviewed` — audit provenance stamps.

Clear `triage:*` labels once the decision is executed.

---

## 4. Labels (area / component taxonomy)

Beyond priority and type-flavour labels, the area/component taxonomy (confirmed from `gh label list`):

- **Subsystem / area:** `dashboard`, `doctrine`, `agent-profiles`, `schema-versioning`, `git`,
  `workflow`, `windows`, `oauth-ddd-refactor`.
- **Release / coordination:** `release` (tracking & coordination), `launch-blocker`
  (must resolve before broad launch), `mvp` (current Private Teamspace MVP), `design-spike`.
- **Version tag labels (current release-scoping mechanism):** `3.2.0` (43 issues), `3.3.0` (17),
  and historically `0.15.0`. **(inferred)** These version labels are how releases are scoped today —
  see §5, because GitHub *milestones* are not currently used for this.
- **Stock GitHub labels:** `bug`, `enhancement`, `documentation`, `duplicate`, `invalid`, `question`,
  `wontfix`, `help wanted`, `good first issue`.

Keep area labels few and orthogonal; prefer native sub-issue parenting over inventing a new area label.

---

## 5. Recommended additions

> Two governance recommendations for the maintainer. Both are **proposals to execute, not yet done**
> — no milestones were created and the tracker was not mutated by this op (Directive 003: rationale
> recorded inline).

### 5a. Adopt GitHub Milestones for release scoping

**As-found (confirmed):** Milestones are effectively **abandoned**. Only two historical milestones
exist (`2.1 release`, `0.15.0 - 1.x Quality Bugfixes`), both with no due-date and no open issues, and
**zero** open issues carry any milestone. Release scoping currently rides on **version labels**
(`3.2.0`, `3.3.0`).

**Recommendation:** Adopt **one milestone per release** (`v3.2.1`, `v3.3.0`, …) as the *single*
release-scoping surface, and retire the parallel version-label mechanism over time.

- **What it buys:** a real "what's left for 3.2.1" burndown (open/closed counts, % done) for free in
  the GitHub UI; a due-date for the release; a description field that can hold the release goal (§5b).
  Version labels give a flat list with none of this.
- **Cost:** every in-flight issue must be (re)assigned to a milestone; dual-running with version
  labels during transition risks drift — pick milestones as canonical and treat labels as legacy.
- **How (maintainer to execute — do NOT auto-create):**

  ```bash
  unset GITHUB_TOKEN
  # create the milestone (UI: Issues → Milestones → New milestone, or:)
  gh api repos/Priivacy-ai/spec-kitty/milestones -f title="v3.2.1" \
    -f description="<release goal — see 5b>" -f due_on="2026-07-01T00:00:00Z"
  # assign in-flight issues:
  gh issue edit <num> --repo Priivacy-ai/spec-kitty --milestone "v3.2.1"
  ```

### 5b. Formalize Release Goals (analogous to sprint goals)

**Recommendation:** State a single-sentence **release theme/intent** per release. Use the **milestone
description field** (from §5a) as the *primary* home for the goal — it keeps intent next to the
burndown and needs no extra file to drift. Mirror the same sentence into the matching mission's
issue-matrix preamble so mission scope and release intent stay one click apart.

- Why milestone-description over a `RELEASE_GOALS.md` file or a pinned issue: it is zero-maintenance
  (no separate file to keep in sync), visible exactly where the scoped issues live, and editable
  without a commit. A `docs/release-goals/` file is the fallback only if milestones are *not* adopted.
- **Connection to mission practice:** a release goal should map to **one driving mission** (or a small
  named set). The mission's issue-matrix is the detailed breakdown; the release goal is its one-line
  intent.

**Filled-in example — v3.2.1:**

> **v3.2.1 — "Strangle the split-brain naming surface."**
> Land the naming/identity SSOT strangler so mission slug, branch, worktree, and dashboard identity
> derive from one canonical source. Driver: mission `01KV6510` (mid8 naming seam) + merge-blocker
> **#1978**. Done when the duplicated identity-derivation sites collapse to one seam and #1978 is closed.

---

### Quick maintainer checklist

- [ ] Every open issue: functional-epic parented (native sub-issue), Typed, prioritized.
- [ ] No functional ticket parented under a `META-TRACKER:` issue.
- [ ] Backfill native sub-issue links where a body checklist implies a parent.
- [ ] Backfill issue **Type** on the ~24% currently untyped.
- [ ] Claim before working; close-with-evidence is claim-exempt.
- [ ] (Proposal) Stand up a `v3.2.1` milestone + one-line release goal in its description.
