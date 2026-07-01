---
title: Quality & Tech-Debt Standing Orders
description: "Eight-section standing orders for spec-driven missions: adversarial squads, campsite cleaning, test discipline, architectural gates, sources, git workflow, and mission hygiene."
---

# Quality & Tech-Debt Standing Orders

A working set of standing practices for keeping quality high and paying tech debt
back incrementally, applied across spec-driven missions (spec → plan → tasks →
implement → review → merge).

**The throughline:** never trust a green check, a clean diff, or a confident
summary. Verify against live code, witness the bug in a real run, and let
independent adversarial perspectives try to break the work *before* it lands —
at the cheapest possible point in the lifecycle.

---

## 1. The Adversarial Squad Cadence (the spine)

At **every planning point-cut**, run a bounded, multi-profile adversarial squad
*before* proceeding to the next phase. This is the single highest-leverage
practice: it reliably catches undersizing (repeatedly observed at 4–5×) and
fakeable acceptance criteria while they are still cheap prose, not code.

**Where the squads run:**

| Point-cut | Squad focus |
|-----------|-------------|
| **Pre-planning** (before a spec) | Related-issues + live code-state check; campsite-fold check (§2) |
| **Post-spec** | Scope/sizing sanity, completeness |
| **Post-plan** (before `/tasks`) | Brownfield checks: foldable-issue search, split-brain/dual-authority scan, LOC/sizing, deprecation check — plus a **residual hunt** when a "fixed" claim rests on static reading |
| **Post-tasks** (before implement) | Anti-laziness pass on the work-package decomposition: verify every cited claim against live code, hunt fakeable Definitions of Done, remediate before a line of code is written |

**Squad playbook (how to run one well):**
- **Bounded** — a small, deliberate number of agents, one **lens per agent**
  (architecture, code-truth/debugging, fakeability-review, patterns).
- **Profile-loaded** — each agent *reads and adopts* its governing doctrine
  profile (not merely a persona name), so the review carries real directives.
- **Model discipline** — strongest model for the hard lenses (sizing,
  fakeability, code-truth); cheaper model for mechanical passes.
- **One squad per context** — don't reuse a squad across unrelated questions.
- **Synthesize, then remediate** — fold the findings back into the
  spec/plan/tasks artifacts *before* moving on; the squad's value is realized
  only when its findings change the work.

> Real example: the post-tasks squad on a recent mission found a P0 defect was
> *already half-fixed by a prior merged PR* (the spec had over-scoped from stale
> code-state) and that the gate's anti-mass-allowlist defense was enforced
> nowhere — both fixed before implementation started.

---

## 2. Campsite Cleaning & Incremental Debt Paydown

Leave the campsite cleaner than you found it — **without inflating scope**.

- **Domain-matched folds only.** At each planning point, check whether any part
  of the standing tech-debt backlog can be folded into *this* mission — but only
  when the debt's domain matches the mission's intended scope. A test-hygiene
  ratchet adjacent to files the mission already opens: fold it. An unrelated
  sweep: leave it.
- **Consolidate logical duplication.** When a bug cluster is really *one
  operation duplicated across N sites*, fix it by collapsing to **one canonical
  seam** (compose-and-parse, canonical-first, emit-don't-guess, plus a
  literal-ban ratchet) rather than N parallel patches. Run a patterns lens early
  — spec and plan almost always undersize this.
- **Frozen-baseline ratchets.** When you can't remediate an existing litter
  class in-mission, freeze the current offenders as a baseline and block *new*
  ones — debt stops growing while you chip at it.
- **Tracker hygiene.** Meta/convenience rollups reference work via checklist;
  they are never the canonical parent of a functional ticket. Park work under
  functional epics.

---

## 3. Mission Tracer Files

Seed three small **tracer files** at planning, append to them during
implementation, and assess them at mission close:

- **Tooling-friction** — every place the tooling fought you (feeds the
  tooling-gap backlog).
- **Approach** — what you tried, what worked, what you'd do differently.
- **Design decisions** — the rationale that would otherwise evaporate.

Why: the friction and rationale captured here feed the *next* mission's planning
and make recurring tool/process gaps visible instead of re-discovered.

---

## 4. Test Remediation & Bug-Fix Discipline

- **Judge the test, not git-blame.** A failing test is one of three things:
  *stale* → re-pin the assertion; *a stub/scaffold* → delete it; *valid and
  current* → the **product** is wrong, fix the product. Never retry-to-green;
  never soften a good test to make a build pass.
- **Red-first reproduction.** Write the RED test **first**, through the
  **pre-existing** entry point (not the fix's brand-new API), and prove it red
  against pre-fix code. A test that's green before *and* after the fix captures
  nothing.
- **Live evidence over static-fixed.** A bug witnessed in a real run is *not*
  fixed because the code now "looks fixed." Carry it OPEN until a live
  reproduction confirms the fix.
- **Tests are friction, not scaffold.** A degraded suite silently reverts good
  changes and wastes effort. When a correct structural change turns a test red,
  suspect the test before reverting the change.
- **Realistic test data.** Production-shaped (real-format IDs, realistic
  lengths). Handcrafted placeholders mask real behavior.

---

## 5. Architectural Gate Discipline

- **Close defect classes by construction.** When a defect class is "a convention
  every caller must remember," don't add more discipline — add an architectural
  **call-site gate** (e.g. AST-based) that makes the omission a CI failure.
- **Make the gate non-vacuous.** Every gate needs a **concrete floor** (a real
  integer, never self-referential) and a **self-mutation test** (inject a
  violation → gate fails → revert → passes) so it cannot silently become a
  no-op. Allowlists are **shrink-only** against a frozen pre-sweep baseline, and
  each allowlisted exception carries a recorded rationale.
- **A "route-or-allowlist" gate needs a routed-count floor.** Otherwise it is
  vacuously satisfiable by allowlisting everything.
- **A gate-unmask cannot self-validate.** Un-masking a gate only takes effect
  *after* the merge, so it cannot catch offenders within its own merge. Pair
  every un-mask with a **pre-merge full-gate dry-run**; never ship a
  mission-diff-scoped assertion to the main branch.
- **Post-merge arch-gate adjudication.** Run the **full** architectural-gate
  sweep on the merged branch before opening the PR. Verify any "pre-existing"
  failure via a **cross-base diff** (the lane base is not the mission base). Run
  the CI-only shards (integration/git) locally too — some gates only run in CI.
- **Keep the new code clean.** Lint/type checks pass on new and boy-scout-touched
  code; fix failing tests rather than rationalizing them.

---

## 6. Canonical Sources & Unification

- **Use canonical sources, never improvise.** Always use the canonical doctrine
  templates, skills, and CLI commands — never copy structure from an older
  mission or hand-roll an equivalent. Drift propagates.
- **Unification, not parity.** Chase one canonical surface/authority; don't
  preserve a lacklustre existing quirk for "parity." The old quirk is mess to
  remove — with the caveat that you don't drop a load-bearing invariant you
  haven't proven is dead.
- **A missing CLI command is a gap, not a workaround.** If a documented command
  is absent or broken, trace the source and file an upstream gap rather than
  silently routing around it.
- **Guard the terminology canon.** Run the terminology guard before pushing
  doctrine or user-facing prose; forbidden terms get reworded, not exempted.

---

## 7. Git & Workflow Discipline

- **PRs only; the operator merges.** All changes to the protected main branch go
  through pull requests. The operator merges manually — agents prepare
  merge-ready (green CI, un-drafted, issues linked) and hand off; they never
  merge to the remote main themselves.
- **Read intent before high-risk ops.** Read the mission spec/intent *before*
  any merge, rebase, or deletion. Never delete a test to make a build pass.
  Escalate when unsure — correctness over speed.
- **Isolate PR-touching agents.** Any agent that reviews or rebases a PR runs in
  an **isolated worktree** — otherwise it stages the PR's diff into the active
  mission checkout and cross-contaminates.
- **Compress history after landing.** Once a mission lands, compress its branch
  history (administrative commits bunched, code grouped by slice).
- **No version prescription in scope.** Don't assign patch/version numbers during
  planning — versions are superimposed at release time.

---

## 8. Mission Hygiene

- **Issue-matrix discipline.** For ticket-based missions, every addressed issue
  gets an issue-matrix row, a claim, and a tracker comment naming the mission.
- **Ownership-map leeway.** Give implementers rationale-backed leeway to edit
  outside their declared owned-files; the *no-overlap* rule between work packages
  is the real guard against parallel collisions, not a strict prohibition (strict
  prohibition just causes workarounds).
- **Role separation.** Distinct profiles for distinct roles — a dedicated
  reviewer profile for work-package reviews, kept separate from the implementer
  profile.
- **Tiered rigour.** Apply DDD-tiered coding standards — more rigour for core
  domain logic, less for glue/IO — encoded in doctrine, CI, and the effort a
  delegated agent spends.

---

## In one sentence

Wrap every planning and execution boundary in a bounded, profile-loaded
adversarial pass; fold in only domain-matched debt; prove fixes red-first and
with live evidence; and close defect classes with non-vacuous, self-testing
gates rather than with discipline alone.
