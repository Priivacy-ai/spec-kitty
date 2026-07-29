# Research: Read-Side Seam: Placement-Authority Closure

All open questions were resolved before planning, by two adversarial squads and a
placement-authority audit run against the live tree at base `e97fc6ab9`. There are **no
outstanding NEEDS CLARIFICATION items**. This document records each decision, why it was
taken, and what was rejected — so a later reader does not re-derive it.

Every empirical claim below was established by AST census (aliases resolved) or by
real-git-repo fixtures, not by grep or by reading alone.

---

## R-01 — Is the seam answer-equivalent to the blind composition?

**Decision**: Yes — equivalent in every topology tested, and *strictly better* in one.

**Evidence**: eight real-repo fixtures comparing
`primary_feature_dir_for_mission(root, _canonicalize_primary_read_handle(root, h))`
against `placement_seam(root, h).read_dir(<PRIMARY kind>)` across three handle forms:

| Fixture | Result |
|---|---|
| flat / `SINGLE_BRANCH`, no coord | equal |
| coord + materialized coord worktree | equal (while `STATUS_STATE` correctly resolves to coord) |
| coord + **husk** worktree (present, no `meta.json`) | equal — the *kind-blind* resolver returns the husk |
| coord branch **deleted** from git | equal, no raise for a PRIMARY kind (`STATUS_STATE` raises, correctly) |
| coord worktree **empty** (create window) | equal, no raise |
| mission absent entirely | equal |
| `repo_root` = a lane worktree | equal (both CWD-invariant) |
| **backfilled** (bare `<slug>` primary, composed `<slug>-<mid8>` coord) | **differs — the blind composition returns a path that does not exist; the seam recovers the real one** |

**Why it is structural, not coincidental**: for a PRIMARY-partition kind the decision layer
short-circuits before any coordination probe, and the resolver's own PRIMARY leg *is* the
composition under audit. The only added behaviour is the seam's bare-slug backfill
recovery.

**Rationale**: this is what makes the migration safe and makes it worth doing — it is a
single-authority move that also fixes a latent silent-wrong-answer shape.

**Alternatives rejected**: "leave the sites alone because the seam might behave
differently" — refuted by the fixtures; "migrate to gain fail-loud behaviour" — refuted by
R-02.

---

## R-02 — Is the value of migrating "fail-loud"?

**Decision**: No. The fail-loud surface for this primitive is **zero**. The value is
**single-authority placement** plus the backfill recovery.

**Evidence**: all 34 in-scope sites read a PRIMARY-partition artifact (`meta.json`,
mission type, target branch, `tasks/`, `spec.md`) off a deliberately PRIMARY anchor. Zero
read a COORD-partition artifact off it. `read_dir()` raises only for a COORD kind on a
coord-routing topology whose branch is deleted, so routing a PRIMARY kind cannot introduce
a raise.

**Rationale**: naming the benefit honestly prevents a vacuous success criterion. The spec
therefore measures *identity of resolved directory* and *absence of the caller-side
decision*, not raising.

**Alternatives rejected**: keeping the original "migrate ~30 sites to fail loud" framing —
it would have produced criteria satisfiable with zero work.

---

## R-03 — Are the 34 sites compliant, semi-compliant, or non-compliant?

**Decision**: **33 semi-compliant, 1 non-compliant, 0 compliant.**

**Evidence**: reproduced with the anchoring gate's own scanner. Every site names the
primary-only primitive, so the partition choice is already made at the call site;
33 pass a provably canonical handle, and one passes a handle from a canonicalizer the
gate's fold set does not recognise — so it is neither routed nor allow-listed and passes
only because nothing looks for it. A second site's guarantee rests on a `.name` escape
hatch whose value is the composed form on a backfilled mission — the divergence shape from
R-01, latent today behind a short-circuit.

**Rationale**: "semi-compliance" is the precise defect: canonical handle, caller-chosen
surface. A gate that checks handle hygiene is not a placement-authority gate.

**Alternatives rejected**: treating the anchoring floors as proof of compliance.

---

## R-04 — What does the pre-existing anchoring gate actually guarantee?

**Decision**: It guarantees **handle hygiene**, not placement authority — and its floors
are use-count floors over the primitive.

**Evidence**: its site model records "was this handle folded through the canonical fold
seam", and its violation text is about passing a *non-canonical handle*. Its two floors
count how many times the primitive is called (and how many of those are folded).

**Consequence**: after Step 2 the floors' subject population is only resolver-internal and
named-sanctioned sites, where a raw handle is correct by contract — at which point the
floors guard nothing and instead oblige the primitive to keep being used, inverting their
purpose.

**Decision on end state**: **retire both floors and transfer the guarantee** to the
read-side bypass census (a censused callee with an explicit sanctioned set). Re-pinning to
post-migration numbers is the mechanical fallback if retirement proves larger than
expected.

**Alternatives rejected**: leaving the floors as-is (they would red on a deliberate,
desirable shrink); relaxing them without recording before/after (forbidden by their own
doctrine).

---

## R-05 — Is the floor collision a safety problem or bookkeeping?

**Decision**: **Bookkeeping**, with in-tree precedent for this exact move.

**Evidence**: the floor comment block records five prior shrinks, one of which is
*literally* routing a `primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))`
anchor onto the seam and lowering the floor by one, annotated as "a genuine routing shrink,
not a re-pin". The governing instruction is to record the honest before/after rather than
re-pin the integer. **No test asserts the primitive must keep being used**; two tests carry
bookkeeping that must be updated in the same change, and one of those tests states its own
remedy ("drop them … to keep the allowlist precise") — a tightening.

**Rationale**: this converts the apparent blocker into a scheduled, documented step
(IC-06).

---

## R-06 — Do the "lands on the husk" comments argue against the seam?

**Decision**: No. They argue against a **different resolver** and do not survive as an
objection.

**Evidence**: each of the six comments names the *coord-aware* / *topology-aware*
resolver — the kind-blind one. The husk and empty-worktree fixtures show the kind-blind
resolver returning the husk while the kind-aware seam returns the primary anchor and does
not raise.

**Rationale**: this is the same defect class as the comment that opened this mission —
arguing against resolver A to justify not using resolver B. The comments must be corrected
(IC-08) while preserving their true warning.

---

## R-07 — Which primitive is genuinely unpoliced?

**Decision**: `resolve_feature_dir_for_mission` — **8 live sites / 7 files**, no census
gate, no ledger row. A latent fifth name exists with zero live sites and would reopen the
gap on first import.

**Evidence**: independent enumeration of the resolver module's handle→directory functions.
The censused class is **kind-blind** (not "topology-blind"); this primitive is kind-blind
*and* topology-routed, which is exactly why it can hand a caller the husk.

**Rationale**: the follow-up issue named the wrong primitive; this is the real gap and
becomes the mission's policing target (IC-03).

**Alternatives rejected**: broadening the census to the module's whole import surface —
attractive (closed under new names) but a larger change than this mission should carry;
recorded as a candidate for a successor.

---

## R-08 — What is the ledger's real parse contract?

**Decision**: The prescribed "per-primitive sub-tables" restructuring is **unsafe as
stated** and must be constrained before rows are added.

**Evidence**: executing that shape showed the parser reads only the **first** table under a
parsed heading — the second primitive's counts vanish while the reconciliation stays
**green and meaningless**. The parsers are positional and heading-exact: a duplicated
verdict key silently overwrites, a mid-inserted column silently skips rows, and the
stay-lenient index's hard uniqueness assertion cannot represent a module with several
censused sites in one function (a known four-site case exists).

**Decision**: exactly one table per parsed heading, verbatim headings, leading columns at
fixed positions, any primitive discriminator **appended** as a trailing column, plus two
new gate tests (parsed row count equals summed census; a per-primitive mutation reds).

**Rationale**: without this, extending the ledger would reintroduce the vacuity a previous
landing pass had to repair. Hence the hard sequencing gate C-009.

---

## R-09 — Delegate-then-remove: is Step 1 expressible, and what does it reveal?

**Decision**: Yes, expressible; it reveals exactly one delta.

**Rationale**: because *all* PRIMARY kinds resolve to the same anchor, the primitive can
delegate using a single PRIMARY kind and remain answer-equivalent for every caller — so
Step 1 is a one-file change with the whole existing suite as its harness, and the two
census floors do not move because no call site changes. The only behavioural delta it can
surface is the bare-slug backfill recovery.

**Why this sequence rather than a one-shot migration**: the equivalence question is
answered in one edit instead of 33; the floor obstacle arrives only at Step 2, when it is
intentional; and a helper that cannot honestly pick a single value for the aware parameter
would itself prove the decision belongs to the caller.

**Alternatives rejected**: rewriting 33 sites first and discovering divergence
site-by-site.

---

## R-10 — What is the end state of the primitive?

**Decision**: **Private, not deleted.**

**Evidence**: it is the terminal `KITTY_SPECS_DIR` path constructor that the resolver's own
PRIMARY leg and several seam internals are built on, and it is the sanctioned owner of that
path assembly under a separate architectural gate.

**Rationale**: a module-private primitive with in-module and named-sanctioned callers is
self-policing; a public one with 34 external callers needs two integer floors and a YAML
allow-list to stay honest. Privatising makes the operator's principle **structural** rather
than test-enforced.

**Alternatives rejected**: deletion (breaks the resolver); leaving it public (keeps the
bookkeeping burden and the reintroduction risk).

---

## R-11 — Which sites must NOT be routed?

**Decision**: four **foundation sites** stay unrouted and are recorded by name with their
rationale.

**Evidence**: they sit *beneath* the seam — one is consumed by the write-side composition
root, the others are peer branch/surface resolvers. No cycle exists for the read path
today, but these are the layer the seam is built on.

**Rationale**: authority tidiness is not worth a resolution cycle (NFR-009). Naming them is
the honest treatment, matching how the seam-internal sites are already handled.

---

## R-12 — Where should the design be documented, and what is the real layering?

**Decision**: a **new** page (`docs/architecture/artifact-placement-seam.md`), paired with
**narrowing the existing competing page** in the same slice; glossary work lands in the
prose glossary plus the Terminology Canon, never in the byte-frozen doctrine stores.

**Evidence and corrections**:

- `docs/architecture/branch-target-routing.md` already asserts per-artifact-kind placement
  rules — the new page's core claim — under a *branch*-sense title, in vocabulary the
  glossary explicitly retires, and with no read path. Publishing without narrowing it
  creates two authorities.
- The layering asserted in an earlier draft was **wrong in two load-bearing ways**: the
  decision layer is **two** functions whose divergence is deliberate (one is
  materialization-blind precisely so it can disagree with a resolved stamp, which is what
  makes an existing guard possible), and the translation step **selects** an
  already-discovered location and refuses when absent — it does not assemble a path.
  Assembly lives in the path-resolver module. A reader who believed otherwise would
  strangle through the translation step and re-add discovery at the call site — the exact
  misappropriation the page exists to prevent.
- The doctrine glossary pack and its seed are byte-frozen by a checksum, a term-count pin
  and a parity gate. The `primary`/`merge` disambiguation precedent is implemented purely
  as prose-glossary entries plus a Terminology Canon block.
- "Routing" has **at least ten** senses in the tree, not five. Governed senses:
  placement, branch-target, commit, dispatch/profile, sync fan-out, model/task, scope.
  Infrastructural senses (event, HTTP request, significance bands) are named as out of
  scope — naming an exclusion is disambiguation; silence is not.

**Rationale**: the decisions already exist in two ADRs; the missing artifact is a findable
*explanation*. The page is explanatory and links to those ADRs for normative rules, with a
`module:symbol` citation on every code-shape claim so drift is detectable.

**Alternatives rejected**: extending `branch-target-routing.md` (would conflate two senses
under one title); a third `*-routing.md` filename (multiplies the overloaded word);
touching the doctrine glossary pack (breaks a frozen parity contract).
