---
title: 'CaaCS — Architect Alphonso: Forensic→Architecture Synthesis (3.2.1)'
description: Architect Alphonso's CaaCS forensic-to-architecture synthesis (3.2.1) for the naming/identity SSOT strangler, connecting behavioral evidence to the design.
doc_status: draft
updated: '2026-06-16'
---
# CaaCS — Architect Alphonso: Forensic→Architecture Synthesis (3.2.1)

**Author:** Architect Alphonso (CaaCS squad — forensic/behavioral lens)
**Branch:** `research/naming-identity-ssot-strangler` @ spec-kitty 3.2.0 (read-only; no commit/switch)
**Date:** 2026-06-16
**Companion (static squad):** `00-OVERVIEW.md`, `architect-alphonso-intended-design.md`,
`randy-reducer-split-brain-map.md`, `paula-patterns-duplication-shapes.md`,
`python-pedro-implementation-feasibility.md`, `planner-priti-*.md`.
**CaaCS siblings:** robbie (dataset), randy (split-brain coupling), paula (recurring defects) —
not present in this directory at synthesis time; I mined my own `git log` evidence (recipes below)
to ground the verdicts. Findings should reconcile with theirs when they land.

> **Governance (architect-alphonso).** Directives applied: **DIR-001** (Architectural Integrity —
> the forensic boundary is *where the data says the seam is*, not where the file tree draws it),
> **DIR-003** (Decision Documentation — every verdict below carries the recipe + numbers it rests on),
> **DIR-031** (Context-Aware Design — the coord/primary translation layer is preserved, never collapsed;
> the data tells us *which side* leaks), **DIR-032** (Conceptual Alignment — terms keyed to the 5-SSOT
> model and CLAUDE.md canon). **Tactic applied:** `forensic-repository-audit` (CaaCS — churn × bus-factor
> × bug-hotspot × velocity × firefighting, intersected with the 5-SSOT bounded-context model and the
> connascence/temporal-coupling overlay).

---

## 0. Method note — squash distortion and the window I trusted

3.2.0 shipped as squash `fcf9be595` (= `v3.2.0`); HEAD is `v3.2.0-3` (docs only). Per the tactic's
**squash-merge distortion** failure mode, the squash collapses the entire identity-seam mission into
one commit, so a `--since="3.2.0"` window is blind. I therefore mined the **full pre-3.2.0 history**
(richest, ~6,220 commits) plus a **4-month velocity-adjusted window** (velocity is *accelerating* —
Jun 2026 already at 1,152 commits mid-month — so the tactic's heuristic selects a 3–6mo recent window).
The backup lane tags (`backup/20260615-2110/...-lane-{a..i}`) share a merged base and do **not** isolate
per-concern diffs, so I do not lean on them for concern→lane mapping. Exclusions applied: lockfiles,
`dist/`, `node_modules`, snapshots, `.po/.pot`. **Commit-message hygiene is strong** (conventional
commits, issue refs) so the bug-grep is high-signal here — a notable contrast to the tactic's
weak-message caveat.

---

## 1. The forensic evidence (the numbers the verdicts rest on)

### 1a. Churn — the resolvers are cold; their consumers are infernos

| File | Concern | Full-hist churn | 4-mo churn | Read as |
|---|---|---|---|---|
| `cli/commands/implement.py` | **consumer of A/C/D** | **93** | **59** | top-5 hotspot, entire corpus |
| `dashboard/scanner.py` | consumer of A/D + Shape-D | 35 | 28 | hotspot |
| `core/worktree.py` | A (compose) | 28 | 17 | hot |
| `core/mission_creation.py` | A (compose) | 19 | 19 | **100% recent** — actively churning |
| `core/paths.py` | **B (SSOT)** | 19 | 15 | warm |
| `lanes/branch_naming.py` | **A (SSOT)** | 11 | 11 | **100% recent** (born in 3.2.0) |
| `core/project_resolver.py` | B (shim) | 10 | 7 | warm |
| `ownership/validation.py` | **E (SSOT)** | 10 | 10 | warm |
| `coordination/surface_resolver.py` | **D (SSOT)** | 8 | 8 | **100% recent** |
| `missions/_read_path_resolver.py` | **D (SSOT)** | 8 | 8 | **100% recent** |
| `lanes/worktree_allocator.py` | atomicity (#1915) | 8 | 8 | 100% recent |
| `missions/feature_dir_resolver.py` | D (shim) | 4 | 4 | cold |

**The single most important forensic fact:** the **SSOT resolver modules are low-churn** (4–19),
but the **consumer that juggles them inline (`implement.py`) is a top-5 hotspot of the whole repo (93)**.
Churn did not concentrate *in* the authorities — it concentrated *at the call sites that re-derive what
the authority should hand them*. That is the behavioral fingerprint of a **missing seam**: the cost is
paid by the consumer, every time, because the boundary leaks.

### 1b. Defect density — this whole subsystem is a crime scene

`bug-touch / total-touch` per file (grep `fix|bug|broken|regress`, dedup by SHA):

| File | bug/total | density |
|---|---|---|
| `coordination/surface_resolver.py` | 8/8 | **100%** |
| `lanes/branch_naming.py` | 11/11 | **100%** |
| `core/mission_creation.py` | 17/19 | **89%** |
| `dashboard/scanner.py` | 31/35 | **89%** |
| `missions/_read_path_resolver.py` | 7/8 | **88%** |
| `lanes/worktree_allocator.py` | 7/8 | **88%** |
| `cli/commands/implement.py` | 79/96 | **82%** |
| `core/worktree.py` | 24/30 | **80%** |
| `core/paths.py` | 16/20 | **80%** |
| `core/project_resolver.py` | 8/10 | **80%** |
| `ownership/validation.py` | 7/10 | **70%** |

**Every file in the 5-SSOT surface has 70–100% defect density.** Across spec-kitty as a whole this is
abnormally high — these files exist almost exclusively to be *fixed*. The two pure resolvers
(`surface_resolver`, `_read_path_resolver`) are **low-volume but ~100% defect**: every single time
someone touches them, it is to fix a bug. That is the signature of **load-bearing, fragile, under-seamed
topology code** — exactly the marquee split-brain (Concern D).

### 1c. Temporal coupling — one fan-out hub, not a mesh

Co-change partners (full history) of each SSOT file collapse onto **the same consumer cluster**:

```
  implement.py  ⇄  agent/tasks.py (45) · agent/workflow.py (39) · merge.py (33) · orchestrator_api (20)
  surface_resolver.py  ⇄  agent/workflow.py (6) · agent/mission.py (6) · merge.py (5) · _read_path_resolver (4) · implement.py (4)
  _read_path_resolver.py  ⇄  agent/tasks.py (6) · implement.py (5) · agent/workflow.py (5) · agent/mission.py (5) · scanner.py (4)
  worktree.py  ⇄  agent/workflow.py (18) · agent/tasks.py (16) · merge.py (15) · implement.py (14)
  mission_creation.py  ⇄  agent/mission.py (13) · merge.py (10) · sync/emitter (9)
  branch_naming.py  ⇄  implement.py (7) · merge.py (6) · agent/workflow.py (6) · agent/tasks.py (6)
```

The resolvers **barely co-change with each other** (`surface_resolver ⇄ _read_path_resolver` = 4 only).
They each co-change with **the same 5 command files** that consume them. This is the decisive
boundary signal: **the coupling is consumer↔resolver (a leaked boundary), not resolver↔resolver
(cohesion).** The verdict in §2 follows directly.

### 1d. Class spread — the un-routed classes are BIGGER than the static squad measured

| Un-routed class | Static squad count | Forensic count | Note |
|---|---|---|---|
| inline read/lanes-surface consumers | "high-traffic commands" (~3) | **38 files** | every file calling `resolve_mission_read_path`/`candidate_feature_dir`/`resolve_status_surface`/`require_lanes_json`/`_lanes_feature_dir` |
| bare `mission_id[:8]` mid8 (2c) | ~10 | **20** | randy missed the `migrations/`, `doctrine_synthesizer/apply.py` (×2), `status/aggregate.py` sites |
| `Path(__file__)…parents[N]` (Shape D) | ~6 | **16** total → **7 in `migrations/` (package-root), 9 non-migration (project-root)** | the intent split Paula flagged is **real and majority package-root** |

### 1e. Velocity & firefighting — healthy pipeline, so the defect density is *design*, not chaos

- **Velocity: accelerating** (Jun 2026 mid-month already 1,152 commits).
- **Firefighting: 24/6,220 = 0.4%** reverts/hotfixes — well under the 5% trust threshold. The team
  trusts its pipeline. So the 70–100% defect density on the SSOT surface is **not** pipeline panic; it
  is a *structural* defect concentration — a genuine architectural hotspot, not noise.

---

## 2. Boundary verdicts (forensic → architecture, per high-coupling pair)

For each high co-change pair, I rule **LEGITIMATE cohesion (keep)** or **PATHOLOGICAL leaked-boundary
(consolidate)**, tied to the 5-SSOTs and the DIR-031 guardrails (identity≠path; meta/primary ≠
status/coord ≠ lanes/coord).

| Pair (co-change) | Verdict | Where the EVIDENCE locates the boundary |
|---|---|---|
| **`implement.py` ⇄ `surface_resolver`/`_read_path_resolver`/`branch_naming`** | **PATHOLOGICAL — missing seam** | The resolvers are cold (8–11 churn, ~100% defect); `implement.py` is a 93-churn inferno. The evidence locates the real boundary **at the consumer's inline derivation**, not inside the resolver. The static design assumed the read *authority* is consolidated (true) — but the data shows the **projection/entry is the leak**: 38 files re-derive surface inline. **Consolidate to a single resolved `MissionSurfaces` context the command consumes.** *(Confirms randy's "entry/projection scatter" reading over the design note's "read side consolidated" framing — both true, but the churn says the entry side is where the cost lands.)* |
| **`surface_resolver` ⇄ `_read_path_resolver`** (4) | **LEGITIMATE cohesion — keep separate** | They barely co-change *with each other*; both co-change with consumers. Two distinct artifact-family surfaces (status vs feature-dir) that correctly stay distinct (C-LANES-1 / DIR-031). The ~100% defect density is from *consumers misusing them*, not from the two leaking into each other. **Do NOT merge.** |
| **`mission_creation.py` ⇄ `worktree.py` ⇄ `branch_naming`** (A composes) | **PATHOLOGICAL — un-routed composer (mild)** | `mission_creation`/`worktree` are 80–89% defect and `mission_creation` is 100%-recent-churn — actively re-bugging the compose. The 3 allow-listed inline composes are the leak. **Route through `mission_dir_name`/`worktree_path` (the canonical/stripping twin).** Low blast radius, mechanical. |
| **`mission_dir_name` (strip) vs `coord_*` (verbatim) twins** | **LEGITIMATE fork — keep two functions** | These do **not** co-change as a pair in a way that suggests accidental divergence; they are a genuine compose-new vs reconstruct-existing semantic fork (Shape B). The forensic risk is *wrong-twin selection at a callsite*, not duplication. **Guard the choice (directional lint); do not merge behind a `strip:` flag** — that re-creates the #1589 orphaned-coord class. |
| **`paths.py` ⇄ `project_resolver.py`** (B) | **PATHOLOGICAL but already largely strangled** | `paths` 80% defect / `project_resolver` 80% defect, both warm. Behavior is consolidated (#1971 delegation). The residual leak is the **double-hop import surface** + the **9 non-migration `parents[N]` sites**. Low churn → low future-bug yield → **lower priority** (see §3). |
| **`worktree_allocator.py` ⇄ (dep-merge)** (#1915) | **NOT a naming boundary — atomicity** | 100% recent churn, 88% defect, but co-change pattern is git-transaction, not naming. **Out of this mission's SSOT envelope** — carry the ≥2-dep regression test, close. Confirms randy/paula/priti. |
| **`ownership/validation.py`** (E) | **LANDED — verify only** | 70% defect (lowest of the surface), behavior shipped (#1886). No live coupling pathology. **Verify #1888 is a dup; carry the typo test; close.** |

**Net boundary finding:** the empirical boundary is **not** between the resolvers (the static design's
implicit fault line). It is between **the resolver authorities and the ~38 consumers that re-derive
surface inline**. The disease is *projection scatter on the read/entry side*, and its most expensive
host is `implement.py`. This **sharpens** the static design rather than contradicting it: the design
named the right SSOTs; the forensics name the right **failure surface** (consumer entry, not authority).

---

## 3. Forensically-prioritized WP order (risk = churn × pathological-coupling × defect-density)

The static squad's order (00-OVERVIEW §6) is: **WP01** verify-and-close → **WP02** #1993 lanes-dir →
**WP03** #1971 project-root + parents[N] → **WP04** #2000 + #1899-tail + 2c + ratchet (last).

**Forensic risk score** (relative, churn-weighted defect-prevention per unit effort):

| Proposed WP | Churn host | Defect density | Coupling pathology | Effort | **Bugs-prevented/effort** |
|---|---|---|---|---|---|
| **WP04** #2000 + 2c + ratchet | `mission_creation`(19,100%-recent) + `worktree`(28) + 20 `[:8]` sites | 80–89% | composer leak, **actively re-bugging** | low (mechanical) | **HIGHEST** |
| **WP02** #1993 lanes-dir extract | inside `implement.py`(93) | 82% | **the marquee fan-out**, kills 12-mock test | low (pure) | **HIGH** |
| **WP01** verify-and-close (#1888/#1915) | `validation`(10,70%) + `allocator`(8) | 70–88% | none (landed) | trivial | MEDIUM (hygiene, de-risks scope) |
| **WP03** #1971 + parents[N] | `paths`(19) + `project_resolver`(10) + 9 sites | 80% | strangled; intent-split caveat | low–med | **LOWEST** (cold, behavior already correct) |

**Forensic re-order (my binding recommendation):**

```
WP-α  (was WP04)  #2000 + #1899-tail + 2c routing + ratchet-shrink/extend   [route the HOTTEST composer first]
WP-β  (was WP02)  #1993 extract resolve_lanes_dir() from implement.py        [first cut into the #1 hotspot]
WP-γ  (was WP01)  verify-and-close #1888 + #1915 (+ carry tests)             [hygiene; can run parallel, deps: none]
WP-δ  (was WP03)  #1971 import-collapse + parents[N] (intent-split first)    [cold, lowest yield — sequence last]
```

**Why this differs from the static order:**

1. **The static order leads with hygiene (WP01) and trails with the routing capstone (WP04).** The
   forensics invert the *value*: WP04 touches the **hottest, still-actively-re-bugging** composer
   surface (`mission_creation` is 100%-recent-churn at 89% defect). Routing it + tightening the ratchet
   **prevents the most future bugs per unit effort** — it should lead, not trail. The "enforcement reads
   cleanest last" argument is a *readability* preference, not a risk argument; the ratchet can shrink
   incrementally as each site routes.
2. **#1993 (WP-β) is the first surgical cut into the #1 repo hotspot** (`implement.py`, churn 93). Even
   though it is "just" a pure extraction, it is the highest-leverage *structural* move because it begins
   draining the fan-out hub the §2 verdict identified. It should sit right behind the composer routing.
3. **#1971 + parents[N] (WP-δ) is genuinely lowest-yield** and belongs last: `paths`/`project_resolver`
   are warm-not-hot, behavior is already correct (#1971 landed), and the forensics confirm Paula's
   intent-split — **7 of 16 `parents[N]` sites are `migrations/` = package-root, not project-root.**
   Blindly routing them to `locate_project_root` would mis-resolve installed-package assets. This WP
   needs an **intent-classification step before any routing** and yields the fewest prevented bugs;
   sequence it last so it never blocks the high-value routing.

**Concrete data refinement the spec must absorb:** the **2c class is 20 sites, not ~10** (randy's grep
missed `migrations/`, `doctrine_synthesizer/apply.py` ×2, `status/aggregate.py`), and the **parents[N]
class is 16, split 7-package-root / 9-project-root.** WP-α's ratchet-extend and WP-δ's routing must size
for the *real* counts, or they ship an incomplete oracle that lets the class regrow — the exact failure
this mission exists to kill.

---

## 4. The #1878-defer decision — challenged with evidence, then **CONFIRMED (with one carve-in)**

The static squad defers the #1878 coord/primary **write/entry** strangler to a separate later mission.
I challenged this against the forensic #1-crime-scene test (highest churn + coupling + defect).

**The evidence says the coord/primary surface IS the empirical #1 crime scene:**
- `implement.py` (its inline host) is a **top-5 churn hotspot (93)** with **82% defect density**.
- `surface_resolver` + `_read_path_resolver` are **~100% defect** (every touch is a fix).
- It is the **temporal-coupling fan-out hub** (§1c) — all six SSOT files route through its consumers.
- It is **still actively bleeding**: of `implement.py`'s 79 fix-commits, **7 are coord/topology-class,
  and 5 of those 7 are dated 2026-06** (#1991 lanes-from-coord, coordination-topology blockers, #1793
  hardening, #1615 coord-aware gate, idempotent-vs-coord planning commit). The class is **hot this
  month**, not historical.

**So why confirm the defer?** Because the forensic case bifurcates the surface, and the two halves have
opposite risk profiles:

- **The READ/entry projection** (route the 3 surfaces into one `MissionSurfaces` the command consumes)
  is *partly addressable now and cheaply* — and **#1993 (WP-β) is exactly its first, bounded, pure
  step.** The forensics say: **pull THIS slice forward** (it is WP-β, already in the slice).
- **The WRITE side** (`is_committed` primary-HEAD predicate, setup-plan auto-commit fallback, lifecycle
  emission to protected main, single ref-advance helper, `_ensure_branch_checked_out` retirement)
  touches **commit/protected-branch durability semantics** — a *different bounded context*
  (merge/coordination durability) that DIR-031 forbids collapsing into the naming layer. The 0.4%
  firefighting rate says the pipeline is *trusted*; a write-side strangler that regresses safe-commit
  would *create* the firefighting this repo has so far avoided. High churn × high blast-radius ×
  semantics-sensitive = **the one place where "fix the hottest thing now" is wrong.** It warrants its
  own characterization-test scaffold (coord/flat/primary/husk topologies) and its own mission.

**Verdict: CONFIRM the #1878 write-side defer — but make the carve-in explicit and forensically
justified.** #1993 (lanes-dir extraction) is not a "nice extra"; it is **the first ROI-positive cut into
the #1 crime scene** and must be sequenced high (WP-β), not treated as optional. The deeper write-side
work stays deferred *because it is semantics-sensitive in a trusted pipeline*, not because it is cold —
it is the hottest surface, and that is precisely why it needs the larger, characterization-first mission
the static squad scoped. The defer is **right; the framing must change** from "the read side is
consolidated so D is mostly done" to "**D is the live #1 crime scene; we take its one safe slice now
(#1993) and quarantine the semantics-sensitive remainder into a guarded follow-on.**"

---

## 5. Out-of-slice crime scene the 3.2.1 mission does NOT touch

The forensics surface a hotspot the proposed slice ignores: **`dashboard/scanner.py` — churn 35,
defect density 89% (31/35 fixes), recent-churn 28.**

- It **co-changes with `_read_path_resolver` (4) and `worktree.py` (8)** — i.e. it is a *fourth*
  consumer that **re-derives mission/worktree surface independently** of the read primitive (the static
  design note even lists "`dashboard/scanner`" as one of the "four surfaces answering where is the
  mission dir?"). It carries **both** un-routed classes: a bare `mission_id[:8]` (line 438, in the 2c
  list) **and** is in the Shape-D `parents[N]` project-root cohort.
- At 89% defect it is **as defective as `mission_creation.py`** but is **not named in any WP** of the
  proposed slice except incidentally (its `[:8]` site folds into WP-α's 2c routing if the ratchet is
  scoped repo-wide).

**Recommendation:** do **not** widen the mission to a full scanner refactor (it pulls in the dashboard
bounded context). **But** (a) ensure WP-α's 2c ratchet + routing is **repo-wide** so it catches
`scanner.py:438` (and the `doctrine_synthesizer`/`status/aggregate` sites) — otherwise the "completeness
oracle" has a hole the size of a 89%-defect file; and (b) **file a follow-up** to route `scanner.py`'s
surface derivation onto the read primitive as part of the eventual #1878 read-projection work. The
forensics say scanner is a real #1878-family crime scene hiding outside the slice — the slice's *ratchet*
must reach it even if its *refactor* does not.

---

## 6. The decision-documented forensic case (for the mission spec's risk/justification section)

> **Ship THIS slice, in THIS order, because the data shows X.**
>
> **X = the cost of this subsystem is paid at the consumer call sites, not in the authorities.** Across
> the 5-SSOT surface, every file carries **70–100% defect density** and the team's pipeline is **trusted
> (0.4% firefighting)** — so this is *structural* debt, not chaos. The authorities (`branch_naming`,
> `surface_resolver`, `_read_path_resolver`) are **cold (8–11 churn) yet ~100% defect**: load-bearing
> and fragile. The cost concentrates in **`implement.py` (churn 93, a top-5 repo hotspot, 82% defect)**,
> which is the **temporal-coupling fan-out hub** every resolver routes through. The disease is therefore
> **projection scatter on the read/entry side** — **38 files re-derive mission surface inline** — not a
> defect in the authorities.
>
> **Therefore:** (1) Route the **hottest, still-actively-re-bugging composer** first — `mission_creation`
> is 100%-recent-churn at 89% defect; routing #2000/#1899-tail + the **20-site** (not 10) bare-`[:8]`
> class through the seam and **shrinking + extending the ratchet repo-wide** prevents the most future
> bugs per unit effort. (2) Take the **first safe cut into the #1 crime scene** — extract `resolve_lanes_dir`
> (#1993) out of `implement.py`, killing the 12-mock test and beginning to drain the fan-out hub.
> (3) Run **verify-and-close** (#1888/#1915) as parallel hygiene to lock scope-truth. (4) Sequence the
> **coldest, already-correct** work last — #1971 import-collapse + the **16-site** `parents[N]` cohort,
> which must first be **split 7-package-root / 9-project-root** before any routing.
>
> **What we deliberately do NOT do, and why the data backs the restraint:** the **#1878 write-side
> strangler** is the *hottest* surface (coord-topology fixes are dated **this month**), but it touches
> **commit/protected-branch durability** — a different bounded context. In a pipeline this trusted, a
> regression there would *manufacture* the firefighting we have so far avoided. We take its **one safe
> slice now (#1993)** and quarantine the semantics-sensitive remainder into a **characterization-first
> follow-on mission**. And we ensure the slice's **ratchet reaches `dashboard/scanner.py`** (89% defect,
> outside the slice) so the completeness oracle has no hole.

**Bottom line for the operator:** the static squad named the right SSOTs and the right disposition
(verify-don't-reimplement). The forensics **do not overturn the slice — they re-order it and resize two
of its classes.** Lead with the hot composer + ratchet (was WP04 → now first), follow with the #1993
cut into the hotspot, run hygiene in parallel, and trail with the cold project-root work. Confirm the
#1878 write-side defer, but reframe it: D is the **live #1 crime scene**, we take its safe slice now and
guard the rest. The slice's *membership* is right; its *sequence and sizing* change.
