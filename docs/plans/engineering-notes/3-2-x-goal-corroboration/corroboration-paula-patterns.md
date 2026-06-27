---
title: Paula Patterns — 3.2.x Goal Corroboration from the Emerging-Patterns POV
description: "Paula Patterns' corroboration of the 3.2.x goals from the emerging-patterns lens: which recurring boundary leaks and whack-a-field fixes the goals address."
doc_status: draft
updated: '2026-06-16'
---
# Paula Patterns — 3.2.x Goal Corroboration from the Emerging-Patterns POV

> **I am Paula Patterns.** I review recurring boundary leaks, ownership confusion, and
> whack-a-field fixes by naming the *shape* of the recurring pattern and whether the
> codebase's pattern *vocabulary* is actually moving toward the stated goals — not by
> celebrating intent. I separate the patterns that genuinely *spread* in the
> `v3.1.10..v3.2.0` delta from the ones that are pre-existing scaffolding, and I flag where
> the delta shows the **opposite** of the goal (new shadow paths, duplication added).
>
> **Directives applied:** D-001 (Architectural Integrity — find the *owning boundary* a
> pattern serves before crediting it to a goal), D-003 (Decision Documentation — record the
> corroboration verdict so it is not relitigated), D-030 (Quality Gate — treat ratchets as
> the *test surface* proving a failure-class is closed, and count them as evidence), D-032
> (Conceptual Alignment — a recurring name/idiom is the signal that concept drift is or
> is not being strangled). **Tactics applied:** `anti-corruption-layer` (legacy shape
> kept as a *warned* compatibility branch, not a co-equal path), `review-intent-and-risk-
> first` (does the spreading pattern close the observed class, what is the blast radius),
> `domain-event-capture` (canonical event log as the durable SSOT). Builds on my prior
> `naming-identity-ssot-strangler/paula-patterns-duplication-shapes.md`.

**Scope:** `v3.1.10..v3.2.0`, 2317 commits. Method: targeted `git log --grep`/`-S`/`-G`
pickaxe + `git ls-tree`/`git grep` token-counts at each tag boundary (NOT a full-diff read).
All counts are `src/**/*.py` unless noted.

---

## TL;DR — the central finding (read this first)

**The pattern vocabulary of the codebase shifts hard toward the goals across this range —
but the headline evidence is the *enforcement layer*, not the *adoption layer*.** The
biggest, most unambiguous move is **architectural ratchets: 3 → 60 test files** (20×).
The *contract* patterns (frozen value-objects, fail-closed authorities, compose+parse
seams, pure resolvers) all spread 2–3×. But the **adoption** of those SSOTs lags the
construction of them, and in two specific idioms the duplication-class *grew in absolute
terms* — exactly the "seam built, consumers still re-derive inline" gap the 3.2.x research
already named. So the emerging patterns **corroborate the goal *direction* strongly**, and
**corroborate goal *completion* weakly** — which is precisely what a "stabilization-and-
depth cycle" that "stays open until they hold" should look like one release in.

The dominant emerging pattern is the **architectural ratchet (literal-ban / parity /
boundary AST-scan)** — it is the connective tissue that makes every other pattern *stay*
strangled, and its 20× growth is the single clearest signal that "strangle/route, don't
duplicate" has moved from aspiration to enforced practice.

---

## Pattern catalog

| Pattern | new / spreading | first-appearance commit | maps-to-goal | spread metric (v3.1.10 → v3.2.0) |
|---|---|---|---|---|
| **Architectural ratchet** (literal-ban, parity, boundary AST-scan) | **spreading, explosively** | pre-existing 3 files; mass landing `fa80fa0f9` "ratchet burn-down", `b7bf5f9e3` run-twice ratchet, `8dad4de75` canonical-producer lint | **G3** (primary), enforces G2 | `tests/architectural/`: **3 → 60 files** (57 net-new incl. `test_no_op_stable_writes`, `test_no_raw_mission_spec_paths`, `test_no_primary_anchored_gates`, `test_topology_resolution_boundary`, `test_status_module_boundary`, `test_no_dead_symbols`) |
| **Fail-closed authority** (`*_required`, `…Unresolved`/`NotFound`/`Invalid` exceptions) | **spreading** | many; `0ca389814` "fail closed on coord topology gaps", `76bb71557`, `348ef90db` "fail-closed unknown relations" | **G2** (SSOT refuses to guess), **G1** (doctrine refuses malformed pack) | fail-closed exception classes **12 → 27** (2.25×); `*_required` funcs **15 → 23** |
| **Frozen-dataclass immutability** (value-object compute-once) | **spreading** | `b02d35c1b` "PackContext three-state frozen dataclass" | **G2** (immutable SSOT carriers), **G1** (frozen PackContext/template) | `@dataclass(frozen=True)`: **104 → 306** (61 → 159 files, ~3×); `__post_init__` **14 → 36** |
| **Compute-once-thread context FRAGMENT** (`IdentityFragment`/`BranchRefFragment`/`WorkspaceFragment`/`StatusSurfaceFragment`) | **NEW value-objects on a pre-existing surface** | `c5a10ce56` (#1793) — Fragment classes net-new; `mission_runtime/` dir + `runtime_bridge.py` pre-exist | **G2** (the naming/identity/read-path SSOT carriers) | `resolve_action_context` calls **3 → 27** (2 → 9 files); `ExecutionContext` refs **57 → 82** (11 → 19 files) |
| **Compose+parse SSOT seam** (`lanes/branch_naming.py`: `mission_dir_name`/`worktree_path`/`coord_*`/`mission_branch_name_required`/`lane_branch_name`) | **pre-existing, hardened+routed** | module + primitives + `test_no_worktree_name_guess.py` ratchet all in v3.1.10; hardened `fcf9be595` (#2001) | **G2** (identity/naming SSOT) | seam primitives already named at v3.1.10; `mid8` refs **67 → 605** (16 → 54 files) — the *grammar* spread across the tree |
| **Pure resolver / `resolve_*` seam** (testable extraction) | **spreading** | `43fee0bda` canonical kind resolver, `fe2c5695d` pure `plan_activation` seam, `0f634d8a8` `is_planning_lane` seam | **G2** + **G3** (mocks ↓) | distinct `def resolve_*`: **35 → 79** (2.25×) |
| **OHS facade / shared-kernel re-export** (canonical authority behind a thin facade) | **spreading** | `c5a10ce56` status-facade strangle, `fa0a02be6` `template_catalog` facade (allowlist→0), `b7bf5f9e3` shared kernel comparison util | **G2** (route consumers to one authority) | `facade` refs **6 → 49** (3 → 29 files, ~8×) |
| **Declared-identity-keying** ("name proposes, authority disposes": `resolve_mid8`, meta.json governs) | **spreading** | seam `resolve_mid8` pre-exists; selector-disambiguation hardened `fcf9be595` | **G2** (identity SSOT) | covered by `mid8` 67 → 605 and the #1888 existence-check (`8b64bb2f1` ownership seam) |
| **Strangler-fig parallel→route→delete** (collapse a duplicate onto an authority) | **spreading, with real collapses** | `e14db3227` byte-identical do/ask/advise aliases (#1810/#1804), `910ea1a1c` collapse `from_frontmatter` dual branches, `a8fad6ae9` registry-back VALID_AGENTS, `ba18e1d4d` route remaining lane checks through one seam | **G2** (primary) | 7 commits with `strangl*` in title; multiple explicit `collapse`/`byte-identical`/`route … through … seam` commits (see Discipline §) |
| **Doctrine→runtime step binding** (`_resolve_step_agent_profile`/`_resolve_step_binding` thread profile+contract_ref into the `next` step) | **NEW** | `c5a10ce56`-era runtime_bridge hardening | **G1** (the only direct doctrine-governs-execution seam in-range) | step-binding refs **0 → 9**; `runtime/next` doctrine refs **0 → 14** (0 → 5 files) |

---

## Patterns → goals map (does the vocabulary shift toward the goals?)

**Yes — measurably, and in the goal-ordered way the release doc predicts.**

- **G1 (doctrine governs runtime):** the *thinnest* but **net-new** evidence. `runtime_bridge`
  gained `_resolve_step_agent_profile`/`_resolve_step_binding` (0 → 9 refs) so a step's
  resolved `agent_profile`/`contract_ref` from the **frozen mission-type template** now
  decides step execution; `runtime/next` doctrine references went **0 → 14**. The frozen
  PackContext/template + fail-closed-on-malformed-pack patterns (`bc04abae7`,
  `348ef90db`) are the *upstream* half — doctrine that refuses to resolve when malformed.
  This is doctrine starting to *gate*, not just resolve — but it is a *seam*, not yet
  *pervasive*. **Vocabulary present, spread shallow.**
- **G2 (strangle core domains onto SSOTs):** the **dominant** beneficiary. Every spreading
  pattern in the catalog except the G1 binding serves G2: frozen value-objects (×3),
  fail-closed authorities (×2.25), pure resolvers (×2.25), OHS facades (×8), the NEW
  `mission_runtime` Fragment carriers, and the `mid8` grammar spreading 67 → 605. The
  **new `mission_runtime/context.py` Fragments** are the literal "take identity/naming/
  read-path onto its canonical SSOT" instruction in code. **Vocabulary shift is decisive.**
- **G3 (DevEx & enablers):** the **clearest single number** in the whole delta — ratchets
  **3 → 60**. Pure-seam extractions (`resolve_*` 35 → 79; `8b64bb2f1`/`fe2c5695d` explicitly
  "extract … seam for stub-based testing") lower test cost; the ratchet wall makes the
  strangled classes *stay* strangled. The `docs/release-goals/` + `tests/architectural/
  README.md` governance surface also landed in-range. **Vocabulary shift is decisive.**

**Verdict on the claim "emerging patterns point toward the goals":** the codebase's pattern
vocabulary **does shift toward all three goals across the range**, ordered G3≈G2 (loud) >
G1 (quiet-but-real) — consistent with a cycle that front-loads enablers/SSOTs and defers
deep doctrine-into-runtime to later 3.2.x slices.

---

## The discipline signal — "strangle/route, don't duplicate; no shadow paths"

**Emerging practice, not aspirational — but unevenly enforced.** Evidence the discipline is
*being practiced and ratcheted*, not just stated:

**Strangle-then-collapse instances (the right shape):**
- `e14db3227` — `do`/`ask`/`advise` collapsed to **byte-identical aliases** over one
  canonical dispatch (#1810/#1804). Textbook route-then-collapse.
- `910ea1a1c` — "collapse `from_frontmatter` dual branches into one path."
- `a8fad6ae9`/`e7de69d76` — `SKILL_ONLY_AGENTS`/`VALID_AGENTS` **registry-backed** (delete
  the hardcoded twin).
- `0f634d8a8`/`ba18e1d4d` — "single planning-lane classifier seam" + "route remaining lane
  checks through `is_planning_lane`" — extract one classifier, route consumers, delete
  re-derivations (emit-don't-guess for predicates).
- `c5a10ce56` — status-**facade** strangle + canonical `mission_runtime` surface.
- `fa0a02be6` — `template_catalog` facade with **boundary allowlist driven to 0**.
- `8b64bb2f1` — extract `build_wp_manifests` seam *for stub-based testing* (DevEx-driven
  strangle).

**Enforcement that the discipline is now *ratcheted* (D-030):** `test_no_worktree_name_guess`
(literal-ban with shrinking allow-list), `test_no_raw_mission_spec_paths`,
`test_no_primary_anchored_gates`, `test_no_dead_symbols`/`test_no_dead_modules`,
`test_no_op_stable_writes` (run-twice no-op ratchet, `b7bf5f9e3`),
`test_topology_resolution_boundary`, `test_status_module_boundary`, `test_compat_shims` +
`test_shim_registry_schema` (every legacy shim must be *registered*, i.e. a warned
compatibility branch, not a silent parallel path). **The `fa80fa0f9` "ratchet burn-down" is
the discipline made executable.** This is the anti-corruption-layer tactic operationalized:
legacy is kept as a *declared, tested* compat branch, never a co-equal resolver.

**Conclusion:** the discipline is an **emerging, enforced practice** — the 20× ratchet
growth and the explicit collapse commits are corroborating evidence, not vibes.

---

## Anti-corroboration — where the delta shows the OPPOSITE (challenging the claim)

Honesty per `review-intent-and-risk-first`. Three real counter-signals:

1. **The adoption-gap duplication GREW in absolute terms.** The very class the 3.2.x
   research flags as "seam built, ~5% adopted" is visibly *worse* by raw count:
   - bare **`mission_id[:8]` / `_id[:8]` inline: 6 → 27** (4 → 13 files). The seam
     (`resolve_mid8`/`mid8()`) exists and spread 67 → 605, yet **more** consumers hand-roll
     the slice. This is the literal "consumers re-derive `mid8` while holding a context that
     carries it" anti-pattern — and it *increased*. The ratchet for bare `…_id[:8]` repo-wide
     does **not** yet exist (it is a 3.2.1 deliverable), so the recurrence is *unguarded*.
   - **`parents[2]` project-root re-derivation: 4 → 10** (4 → 9 files). The `paths`
     authority exists; the depth-coupled re-derivation idiom **doubled**. No ratchet bans it
     yet (Shape D in my prior note — still the *headline missing guard*).
   - *Mitigant:* the naming f-string composes (`f"…kitty/mission…"`) actually **shrank 7 →
     5**, so the *static-write* end of the same shape is moving the right way. The growth is
     concentrated in the *inline-read* idioms that lack a ratchet — confirming the pattern,
     not refuting it: **what is ratcheted shrinks; what is not, grows.**

2. **"Mirrors X" docstrings exploded 32 → 157** (18 → 93 files, ~5×). On its face this is the
   classic un-extracted-seam tell ("Mirrors the `_…_feature_dir` pattern"). Inspection
   *largely* exonerates it: the bulk are **deliberate contract/schema mirrors and facade
   re-exports** (`charter/*` "Mirrors the vocabulary pinned in…", "mirror `spec_kitty_events`
   schemas", "Mirrors the field-merge semantics") — i.e. documented OHS boundaries, not raw
   logic dup. **But** a residual minority *are* the bad shape (the `implement.py`
   `_lanes_feature_dir` "Mirrors `_status_feature_dir`" family from my prior note). So the
   5× growth is **~80% benign facade-documentation, ~20% genuine un-extracted-mirror debt** —
   the SSOT vocabulary is partly being used to *paper over* mirrors rather than collapse
   them. Watch this number: if facade-mirrors keep growing faster than collapses, the
   "no shadow paths" rule is being satisfied in *docstring* but not in *structure*.

3. **G1 is corroborated only as a seam, not a trajectory.** `runtime/next` doctrine refs
   0 → 14 and step-binding 0 → 9 is *real* but *small* against 2317 commits. The release
   doc's own G1 success criterion ("a test proving the directive/contract changes behaviour")
   is **not yet met in-range** — the binding *reads* the profile/contract; I found no
   in-range ratchet proving a doctrine change *flips* a runtime decision. G1 is the
   weakest-corroborated goal: the *vocabulary* appeared, the *governs-execution proof* did
   not.

---

## Verdict per goal

| Goal | Corroboration | Basis |
|---|---|---|
| **G1 — doctrine governs runtime** | **PARTIALLY supports** | NEW step→profile/contract binding in `runtime_bridge` (0 → 9) + `runtime/next` doctrine 0 → 14 + fail-closed-on-malformed-pack establish the *seam*; but spread is shallow and the "doctrine *changes behaviour*" proof/ratchet is absent in-range. Direction yes, trajectory unproven. |
| **G2 — strangle core domains onto SSOTs** | **SUPPORTS** | Decisive vocabulary shift: NEW `mission_runtime` Fragments, frozen value-objects ×3, fail-closed authorities ×2.25, pure resolvers ×2.25, facades ×8, `mid8` grammar 67 → 605, multiple explicit collapse/byte-identical commits. *Caveat:* construction outran adoption — inline `_id[:8]` 6 → 27 and `parents[2]` 4 → 10 show the strangle is mid-flight, not done. |
| **G3 — DevEx & enablers** | **SUPPORTS (strongest)** | Ratchets **3 → 60** is the loudest single signal in the delta; `resolve_*` seam extractions 35 → 79 explicitly "for stub-based testing"; run-twice/no-op + boundary + dead-symbol ratchets + `docs/release-goals/` governance surface all landed in-range. The enablers that make G1/G2 *stick* are visibly in place. |

**Overall:** the operator's claim — *the 3.2.0 patterns already point toward the 3.2.x
goals* — is **CORROBORATED for direction, with the honest caveat that G2 adoption and G1
depth are early.** The codebase didn't just *declare* the goals; it grew a 20× ratchet wall
and a frozen-SSOT vocabulary to enforce them. The one trajectory to *watch* (not yet a
refutation) is the **un-ratcheted inline-read duplication growing while the seam that should
absorb it sits at ~5% adoption** — which is exactly the 3.2.1 work, and exactly why the
cycle is correctly left *open*.
