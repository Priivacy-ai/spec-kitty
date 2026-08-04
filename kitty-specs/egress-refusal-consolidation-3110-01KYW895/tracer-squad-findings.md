# Adversarial squad findings — Bundle B, mission `egress-refusal-consolidation-3110-01KYW895`

Point-cuts: post-specify (this file, §1), post-plan (§2), post-tasks (§3).
Each finding records: severity, the claim, my adjudication, and the resolution.

---

# §1 — POST-SPECIFY PASS

Four profile-loaded lenses, all opus, all read-only:
`architect-alphonso` (structure/seams) · `debugger-debbie` (live evidence/coverage) ·
`reviewer-renata` (anti-laziness/fakeable) · `paula-patterns` (recurrence/boundaries).

## Lens: paula-patterns (recurrence, ownership, whack-a-field) — VERDICT ACCEPT-WITH-CHANGES

### P-1 [HIGH] FR-003 creates a FOURTH divergence route, and no requirement covers it — **CONFIRMED, release-blocking**

FR-006 enumerates three root-shaped divergence routes (cwd, `SPECIFY_REPO_ROOT`, the
`or Path.cwd()` fallback). FR-003 makes an **operator-supplied `--mission-slug`**
load-bearing on the live path — a **fourth, slug-shaped route**.

That string feeds `resolve_feature_dir_for_mission(repo_root, mission_slug)`
(`src/specify_cli/missions/_read_path_resolver.py:1608-1631`), which delegates to
`mission_runtime.resolve_action_context(feature=mission_slug)` — a topology-aware
selector resolver — and returns `Path(context.feature_dir)` with **no assertion that the
result lies under `repo_root`**.

Whichever ledger that resolves to answers the ownership question, while consent is still
answered about `repo_root`. **That is the bug class exactly** — a consent answer reached
through something other than the data's own owner — reintroduced by this mission's own fix.

The lens was explicit that it did **not** prove a traversal is reachable; it reports an
*unconstrained seam*, not a measured leak. That distinction is honest and I am keeping it.

**Adjudication: CONFIRMED.** This is precisely the failure I dispatched this lens to look
for. The cost of closing it is one `Path.is_relative_to` check.

**Resolution:** extend FR-006 to four routes; add a requirement that the resolved mission
directory be verified under the acting root **before its index is consulted**.

**MY OWN VERIFICATION — the finding is stronger than the lens stated.** Read directly at
`missions/_read_path_resolver.py:1608-1630`:

```python
def resolve_feature_dir_for_mission(
    repo_root: Path, mission_slug: str, *, cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    from mission_runtime import resolve_action_context
    context = resolve_action_context(
        repo_root=repo_root, action="tasks", feature=mission_slug, cwd=cwd, env=env,
    )
    return Path(context.feature_dir)          # <-- no containment assertion
```

The lens named one ambient input (the slug). There are **three**: the slug, `cwd`, and
`env` — and `env` is the channel `SPECIFY_REPO_ROOT` already travels on (F-B4). So the
function proposed to *establish* ownership accepts ambient context through three
parameters and returns a path with no assertion it lies under `repo_root`.

This makes P-2 (name and place the derivation) and P-1 the same remediation: the
ownership function must take its inputs explicitly and assert containment, or it is
simply a fourth spelling of the defect.

### P-2 [HIGH] FR-001 has no placement/naming constraint, while the string formatter has five — **CONFIRMED**

FR-008 (a presentation concern) is constrained by C-001, C-002, C-004, C-005 and a
five-row trade-off table (Q1). FR-001 — the P1 confidentiality requirement and the only
new *concept* in the mission — carries no placement constraint, no naming constraint, and
no requirement that it be a single reusable function rather than a block inlined into
`cmd_widen` (`cli/commands/decision.py:523-572`).

An inlined derivation would be the **fifth private answer** to "which project owns this
record", unreachable by the next transport author.

**Adjudication: CONFIRMED.** The rigour is genuinely inverted. Cheap to fix.

**Resolution:** FR-001 gains a constraint of the same weight as C-003 — one named
function, one stated home, consumed by `decision widen` and available to future
construction sites.

### P-3 [HIGH] Acceptance Scenario 1 asserts an outcome C-009 says is unobtainable — **CONFIRMED**

AS1 (`spec.md:63-65`) requires the error to name "both the decision's owner and the
checkout that was used". The edge case (`spec.md:179-181`) requires distinguishing "not
found" from "found, owned elsewhere".

With no `decision_id`→project mapping (F-B1; `IndexEntry` at `decisions/models.py:68-96`
is `extra="forbid"` and carries no project identity), a membership test against the
acting root's ledger yields only *yes / not in this mission / no such mission here*.
**"Owned elsewhere" is not a state this design can enter.**

**Adjudication: CONFIRMED.** Shipping an acceptance scenario a correct implementation
cannot satisfy is a defect in the spec, not a stretch goal.

**Resolution:** weaken AS1 and the edge case to what the design can deliver (name the
acting root, the mission slug consulted, and that ownership was not established), or
promote Q4's checkout search to a requirement. Prefer weakening — the search has its own
disclosure implications.

### P-4 [HIGH] The boundary has zero presence in either charter authority path — **CONFIRMED, and it is the recurrence mechanism**

Measured by the lens, with a controlled diagnostic (known-present term returns 12,
known-absent nonsense returns 0):

```
grep -rn "resolve_egress_consent|ConsentedBatch|project_egress_refusal" docs/adr/3.x/ docs/context/
  -> 0 hits
```

A P0 mission built `ConsentedBatch`, a boundary guard and a renamed registry seam, and
recorded its rationale only in a **mission-local tracer file** that no maintainer editing
a transport will read — while the charter instructs every agent to read `docs/adr/3.x/`
"when you change a structural boundary".

**Adjudication: CONFIRMED.** This is the only item in the bundle that acts on
*recurrence* rather than on an instance, and it is the cheapest.

**Resolution:** fold a one-page ADR into this mission naming the boundary, the provenance
invariant, and the fact that the attribution guard is syntactic.

### P-5 [MEDIUM] The guard is hardened on the count axis only; the correctness axis stays unenforceable and the spec never says so — **CONFIRMED**

FR-014–FR-017 and NFR-003 make the guard harder to render *vacuous*. **None of them moves
it from "a root was passed" to "the owning root was passed."** The guard's own docstring
concedes this verbatim at `tests/specify_cli/saas_client/test_client_consent_gate_3030.py:312-315`:
*"It cannot prove the root is the right one."*

A reviewer reading FR-014–017 plus SC-005/SC-007 would reasonably conclude ownership is
now guarded. It is not.

**Compounding, and this one is sharp:** the per-site enumeration in
`saas_client/egress_consent.py:52-76` still says the `decision widen` entry is bounded
because the id is "a ULID, not a slug" — **which F-B2 already falsified** (there is no
validation). So the prose carrying the correctness argument is now stale *and* the guard
cannot catch it.

**Resolution:** state in FR-014's falsifier block that the guard is syntactic by
construction; require the per-site enumeration be **updated** for the post-FR-001
`decision widen` site.

### P-6 [MEDIUM] NFR-001's "no new egress surface" metric is non-conservative — **CONFIRMED**

Two documented holes make an unchanged count compatible with a new sink: the parent's own
**Limit 7** (`egress-inventory.md:300-309` — a file may hold more than one sink and an
allowance covers them all) and `#3113`'s positional-call blind spot (already acknowledged
in C-006).

**Resolution:** state NFR-001's bound explicitly, the way C-006 does for the others.

### P-7 [MEDIUM] Disputes my F-B7 inference — **I CONCEDE; the lens's formulation is better**

F-B7's *measurements* are correct and undisputed. My framing question — whether the
path-typed seam is *the structural defect* — is answered **no**, with evidence:

- Uuid-typing the seam does not make the substitutions inexpressible, only one call
  longer: `resolve(project_uuid_of(locate_project_root()))` is the same bug respelled.
- The parent's *correct* fixes are not uniformly uuid-keyed. E2's `bind_mission_origin`
  is sound **with a path**, because `_resolve_repo_root(feature_dir)` derives it from the
  data (`egress-inventory.md:216-230`).

**The invariant is about the argument's PROVENANCE, not its TYPE: consent must be keyed
on something derived from the record being sent, never from ambient context.** A type
cannot express provenance; a constructor that refuses to build the sender's input without
a data-derived answer can — which is exactly what `ConsentedBatch` does
(`delivery/consent_gate.py:1-20`).

**Adjudication: I accept this over my own F-B7 framing.** It is a strictly better
statement of the bug class and it explains why some path-keyed sites are sound. Declining
to widen the seam remains a defensible scope call; declining to *name the provenance
invariant durably* does not — which is P-4.

### P-8 [MEDIUM] Split-brain is real and should be named — **CONFIRMED (mild)**

After this mission there are three live notions of "which project owns this data":
(1) envelope-carried uuid (`delivery/consent_gate.py:181-207` + the `ConsentedBatch`
mint); (2) positional/locality (three interview sites, three tracker sites, invocation Op
records); (3) FR-001's new ledger-membership derivation, at one call site.

(3) is the **first mechanical reader of positional ownership** in the codebase — a good
thing. It becomes split-brain only if inlined and unnamed, which is P-2.

**Resolution:** record as a Key Entity — "Owning project of a record", with its three
current spellings and which is authoritative where.

### P-9 [LOW] C-007's exclusion is correct but its stated reason is imprecise — **CONFIRMED**

C-007 says the interview sites are excluded because "root and owner already agree by
derivation". The load-bearing fact is stronger: those sites read the data **through** the
root (`_get_mission_id(repo_root, slug)`, `WidenPendingStore(repo_root, slug)`), so a
root-scoped read **cannot reach another project's record by construction**. Stated that
way, C-007 also supplies the *test* for admitting any future site to the exclusion.

### P-10 [LOW] Q7's ULID check risks being this mission's own whack-a-field — **CONFIRMED**

Three ULID regexes already exist (`decisions/verify.py:40`, `invocation/record.py:30`,
`context/mission_resolver.py:55`) and none guards this argument. Adding a fourth at the
CLI and a fifth in the client makes five spellings of one shape check. Prefer one, at the
boundary where provenance changes from keyboard to store.

### On D-1 (the `#3109` seam)

**Lens confirms D-1 and would not reopen it.** Option (b) genuinely dominated. One
strengthening observation: D-1's ground 2 makes the seam a *documentation carrier pinned
by a test* — the weakest form of the artefact. Filing the ADR (P-4) gives the refusal a
durable home; ground 2 then weakens honestly while ground 1 (scope) still holds, and a
future mission gains a clean falsifier for deleting the seam. **Strictly better end state.**
This converges with my own correction C-3.

### Deliberately NOT folded (paula's own recommendation)

**Extend the `ConsentedBatch` pattern to the `saas_client` and `tracker` transports** —
`_get`/`_post`/`_request` stop accepting a bare path attribution and accept a value that
cannot be constructed without a data-derived consent answer. Touches seven construction
sites across four dorny CI groups. **Follow-up issue, not this mission.**
*Falsifier for the issue itself:* if a `decision_id`→project mapping ever lands, the
positional derivation stops being the only option and the design is revisited.


---

## Lens: reviewer-renata (anti-laziness / fakeable assertions) — VERDICT ACCEPT-WITH-CHANGES

Reverse-specced the delivered system from the requirements alone. **13 of 29 requirement
items pass with a literal no-op** — some are legitimate regression ratchets, but the spec
does not label them, so an implementer cannot tell "already true, keep it true" from
"must be built".

### R-1 [BLOCKER] SC-002 and FR-002/FR-003 cannot both hold, and the spec does not say which yields — **CONFIRMED**

SC-002 asserts *"No existing successful invocation becomes a refusal."* FR-002 + FR-003 +
the omitted-slug edge case + C-009 (no mapping) force ownership to be established from a
slug. **If Q4 resolves to "slug required on the live path", then every current invocation
without `--mission-slug` — including from the owning checkout — becomes a refusal, and
SC-002 is false by construction.**

Predicted lazy resolution: require the slug, then evidence SC-002 using only slug-bearing
invocations, and report both green.

**Adjudication: CONFIRMED BLOCKER.** Two requirements in direct contradiction across the
unresolved Q4 answer space is not a deferred design question — it is a spec defect.

**Resolution:** decide precedence in the spec. See R-2, which dissolves the dilemma.

### R-2 [HIGH] Q4 is a false dichotomy; the cheapest correct option is missing — **CONFIRMED, and it dissolves R-1**

Q4 offers only "slug required" or "optional with cross-checkout search" (and correctly
notes the latter has disclosure implications). It omits the obvious third:

> **Search the missions of the acting checkout only** — glob
> `<repo_root>/kitty-specs/*/decisions/index.json` and membership-test with the existing
> `load_index` (`decisions/store.py:46,58-64`), reusing the membership shape already at
> `store.py:112-120`.

This answers *"does this checkout own this decision?"* with **no slug, no cross-checkout
enumeration, no network call** (satisfies NFR-002) and **preserves SC-002 exactly**. It
cannot name *which other* project owns it — which is precisely why P-3/R-3 must weaken
the owner-naming acceptance criteria.

**Adjudication: CONFIRMED, and this is the single most valuable finding of the pass.** It
resolves the R-1 blocker, answers Q4, and supersedes my correction C-2 (which framed the
omission path as a stall). The design does not need a mapping *or* a mandatory slug.

### R-3 [HIGH] Two acceptance criteria require information C-009 says does not exist — **CONFIRMED, converges with P-3**

Independent of paula-patterns, same conclusion: AS1 and the first edge case require
identifying project B, possible only by enumerating other checkouts. Predicted cheat: drop
the owner-naming half silently (it is in no FR and no SC) and mark AS1 done.

**Two lenses converged here independently. Treated as settled.**

### R-4 [HIGH] FR-004 is unobservable under the design the spec prefers — **CONFIRMED**

If FR-002 refuses on every divergence, the only paths reaching the consent gate have
owning root == acting root, so a test asserting "the resolver received the owner's root"
**cannot distinguish the fixed code from `bb2020fea`**. FR-007's falsifier further advises
*against* the re-resolve implementation, which is the only one making FR-004 observable.
FR-004 therefore has zero marginal cost and zero evidence.

**Resolution:** fold FR-004 into FR-002 as an explicit restatement, or state the one
assertion that makes it non-vacuous and accept that it forces the re-resolve design.

### R-5 [HIGH] FR-005 never states it is defence-in-depth — **CONFIRMED, with an honest concession**

Concretely fakeable: SC-001 requires zero requests "from a checkout that does not own the
named decision". **If the divergence test uses a slug-shaped or malformed `decision_id`,
the ULID regex alone makes it green** — SC-001 satisfied with no ownership logic at all.

The lens conceded fairly: an implementer cannot satisfy the *whole* spec with a regex —
AS1 would still red. But they can satisfy **SC-001, which is the criterion that will be
cited as evidence.**

**Resolution:** add to FR-005 "This is defence-in-depth. It does not satisfy FR-001 or
FR-004." Add to SC-001 "…using a **well-formed ULID that is present in project B's
ledger**."

### R-6 [HIGH] FR-009's bar is aesthetic and its test is self-referential — **CONFIRMED**

"Names every identifier kind the transport can transmit" — but the spec never enumerates
the identifier-kind set per transport. The implementer picks the wording *and* writes the
assertion checking it: **a test that cannot fail.**

**Resolution:** enumerate both sets in Key Entities, derived from source. Then FR-009
becomes mechanical: "the merged string names every member of the union, and each
transport's test asserts its own set is fully named."

### R-7 [HIGH] SC-004's byte-identity clause is tautological once FR-008 lands — **CONFIRMED**

If both transports import one shared constant, "byte-identical" is guaranteed by Python;
a test comparing them **compares an object to itself**. It proves nothing and will be
cited as evidence for the consolidation.

**Resolution:** assert identity **end-to-end** — drive each transport through its real
refusal path to an operator-visible string (as `test_saas_client_consent_gate_3030.py:352`
and `test_client_consent_gate_3030.py:376` already do) and compare the two *rendered*
outputs.

### R-8 [HIGH] NFR-004's verification is strictly weaker than NFR-004's requirement — **CONFIRMED**

Requirement: "names a concrete next action…; no branch returns a bare 'denied'".
Verification: "non-empty and distinguishable". **Five strings `"denied 1".."denied 5"`
pass.** Defect-masking assertion under DIR-041.

**Resolution:** per-branch content pin — `DENIED` must contain `sync opt-in`; the
import-failure branch must contain the exception text; `NO_RESOLVER` must name the
resolver. All five already satisfy this at `bb2020fea`; pin them.

### R-9 [HIGH] US3/FR-017's preservation premise is FACTUALLY WRONG at baseline — **CONFIRMED, and it corrects my F-A3 Mechanism 4**

Measured at `bb2020fea`:
- `src/specify_cli/tracker/**` → `agent_surface` (`ci-quality.yml:401`)
- tracker guard lives in `tests/sync/tracker/`, `pytestmark = pytest.mark.fast` (`:39`)
- the only two jobs running `tests/sync/` gate on `needs.changes.outputs.sync == 'true'`
  (`ci-quality.yml:1100-1101`, `:2320-2322`)
- the catch-all `core-misc` shard explicitly `--ignore=tests/sync` (`:1638`)

**Therefore a PR confined to `src/specify_cli/tracker/**` already does not run the tracker
attribution guard today.** The saas guard is fine — it sits in the `specify-cli-rest`
shard whose gate (`:1580`) fires on both `agent_surface` and `platform`.

**Adjudication: CONFIRMED, and it corrects me.** My F-A3 Mechanism 4 framed this as a gap
a *merged* guard would introduce. **The gap exists today, with no merge.** FR-017 is
therefore not preservation — it is a **new fix to a pre-existing CI routing defect**, and
per F-ENV-6 it may cost the 5-edit atomic group registration.

**Resolution:** correct US3's framing; record FR-017 as a fix with SC-006 as a **red-first**
criterion (it reds at baseline — which is good); and **decide explicitly whether it belongs
in this mission or a follow-up issue.** This is a scope decision, flagged in R-16.

### R-10 [MEDIUM] FR-010/SC-010 pin the branch that is NOT at risk — **CONFIRMED, converges with my correction C-1**

All four assertions target `project_egress_refusal(None)` — the `UNDETERMINED` branch,
already byte-identical. **The string that actually changes is the `DENIED` branch**
(`saas:127` "decision" vs `tracker:190` "engagement"), unpinned by anything. SC-010 would
stay green even if the `DENIED` branch were deleted entirely. Also `could not be
determined` appears in `UNANSWERABLE` too (my C-1), so "preserved exactly" is ambiguous
about which occurrence.

**Resolution:** relabel FR-010/SC-010 "already true; must stay true". **Add** a
requirement that the merged `DENIED` wording be pinned by a content assertion in **both**
packages' test trees. Per `delete-the-assertion-not-the-test`: do not touch the existing
four — add.

### R-11 [MEDIUM] 12 of 25 requirements have no success criterion — **CONFIRMED**

Including FR-015, which the spec itself calls the *silent* direction.
**Resolution:** add an FR→SC coverage table; explicitly mark no-op ratchets
(FR-011/012/013) "already true; no SC needed" so a gap is distinguishable from a
deliberate omission.

### R-12 [MEDIUM] The `#3113` dependency row is misattributed — **CONFIRMED; this corrects my F-ENV-5 extrapolation**

`#3113`'s blind spot is in `_transmits_a_body` (`test_egress_consent_boundary.py:295-306`)
— a property of the **egress-consent boundary** guard. The **attribution** guards match by
class name and count every match regardless of call form:
`SaasClient.from_env(root)` positional is counted *and* treated attributed via
`bool(node.args)`; `SaaSTrackerClient(root)` positional is counted *and* flagged
unattributed, loudly. **They have no positional blind spot.**

**Adjudication: CONFIRMED — I over-applied F-ENV-5.** The mechanism I recorded is correct;
the spec's dependency table extended it to guards it does not touch. Leaving it would hand
a successor a ready-made excuse ("my coverage claim is bounded by #3113") for a claim that
is **not** in fact bounded.

**Resolution:** narrow the `#3113` row to the boundary guard only.

### R-13 [MEDIUM] FR-003's "load-bearing" is not an observable — **CONFIRMED**

Satisfied by printing the slug. **Resolution — restate as an unfakeable differential:**
*holding `decision_id`, cwd and `--invited` fixed, changing `--mission-slug` from the
owning mission to a non-owning one must flip the outcome from one request to zero.*

### R-14 [MEDIUM] FR-008 contradicts Q1 option (e) — **CONFIRMED**

FR-008 requires the mapping "exist once"; option (e) keeps two copies and is called "a
legitimate answer to the same requirement". Both cannot be true. FR-008 also has no SC.
**Resolution:** restate FR-008 outcome-first — "exactly one editable presentation,
enforced mechanically" — which (e) can satisfy via its gate; add an SC naming the
enforcement mechanism whichever way Q1 goes.

### R-15 [MEDIUM] NFR-006 has no verification mechanism, on a known-hostile interpreter — **CONFIRMED**

Asks the implementer to "identify in the plan" version-divergent branches — a judgement
made on the wrong interpreter (F-ENV-2: 3.14 only). **Resolution:** require an actual
`uv venv --python 3.11` run of this mission's touched test files with the `N passed` line
quoted, **or delete NFR-006** rather than carry an unverifiable requirement.

### R-16 [MEDIUM] Scope discipline — the bundle is growing — **CONFIRMED**

Delivered surface now includes: local ownership resolution, a possible cross-checkout
search (Q4), CLI identifier validation, a possible uuid seam re-typing (Q3), dry-run
semantics (Q5), a CI filter-group registration (FR-017, possibly 5-edit atomic), and
package classification (C-005). **Any of Q3, Q4-with-search, or FR-017's registration is
comparable in size to the entire #3110 half.**

**Resolution:** name a hard bound in the spec — if Q4 resolves to cross-checkout search or
Q3 to a uuid-typed seam, that work defers to a follow-up issue and this mission ships the
within-checkout resolution (R-2).

### R-17 [MEDIUM] "Engagement" is load-bearing and absent from the terminology authority (DIR-032) — **CONFIRMED**

`grep -ril engagement docs/context/` → **0 of 22 entries**. Probe non-vacuous: the same
grep for `mission_slug` returns 1. The spec builds its central confidentiality argument on
"a `mission_slug` is a client engagement name", and FR-009 would bake the word into an
operator-facing string.

**Resolution:** define "engagement" in `docs/context/` as part of this mission, or resolve
Q2 toward vocabulary the glossary already knows. Do not ship an operator-facing term the
glossary does not know.

### R-18 [MEDIUM] SC-005 already passes at `bb2020fea` — **CONFIRMED**

Both guards `assert scanned` on a per-guard counter, which reds at zero, so deleting all
sites of either class reds today. SC-005 is not change-forcing; **NFR-003's per-class
integer floor is.**

**Resolution:** restate SC-005 as "removing **any one** construction site of either class
reds that class's guard, with the floor as a named integer (tracker 3, SaaS client 4)".

### R-19 [MEDIUM] SC-005/006/008 do not say whether "Demonstrated" is a standing gate or one-off PR evidence — **CONFIRMED**

A mutation demonstration performed once and not preserved rots immediately — the precise
failure FR-019 exists to prevent for the seam.

### R-20 [LOW] FR-011/012/013 are satisfied by doing nothing and are not labelled as such — **CONFIRMED**
### R-21 [LOW] FR-018 has no SC and AS4.2 is not executable — **CONFIRMED**
Resolution: mechanical pin — the docstring must contain `request_text` and must **not**
contain "Called once at sync package startup" (the stale claim at `adapters.py:133`).
### R-22 [LOW] NFR-005/SC-009 are vacuous over an empty set — **CONFIRMED**
Resolution: evidence must state the **count and file list** alongside the result.

### Renata resolved my open caveat C-4

**F-A3's counts independently reproduced** using the guards' own AST predicates:
4 `SaasClient` sites (`charter/interview.py:216`, `decision.py:558`,
`plan_interview.py:150`, `specify_interview.py:150`) and 3 `SaaSTrackerClient` sites
(`tracker/origin.py:165`, `:265`, `saas_service.py:109`). **My correction C-4's "inherited,
not re-measured" caveat is now discharged — tracker 3, SaaS client 4 are correct.**

### Conceded as genuinely strong (recorded so it is not re-litigated)

- The two framing corrections ("consent laundering, not unconsented egress") are correct
  and the mechanism was independently verified.
- The Falsifiers section is "genuinely unusual and genuinely good"; the FR-001/FR-004
  anti-vacuity clause is exactly DIR-041 discipline.
- C-004's seam-symbol trap confirmed.
- C-009 / F-B1 confirmed and load-bearing.
- D-1 confirmed; F-A7's read-side/write-side inversion verified at
  `invocation/adapters.py:188-215` and `propagator.py:137`. FR-019 is clean and unfakeable.
- FR-006 is fine — the three routes converge in `locate_project_root`, so the property
  holds by construction.

---

## Lens: debugger-debbie (live evidence / would this catch the regression?) — VERDICT ACCEPT-WITH-CHANGES

Established its own baseline first (control-your-diagnostic): copied both guards' AST
predicates **verbatim** into a probe → `SasClient scanned: 4`, `SaaSTrackerClient
scanned: 3`, reproducing the gates. Then ran the guards themselves **unpiped**, exit
status captured directly: `PYTEST_EXIT=0`, `2 passed in 55.60s`.

### D-1 [CRITICAL] SC-001 — the mission's load-bearing acceptance criterion is vacuous-passable at `bb2020fea` with ZERO production change — **CONFIRMED**

SC-001 reads *"from a checkout that does not own the named decision produces zero
outbound HTTP requests."* **It never says *consenting*.**

A non-consenting checkout already produces zero requests today:
`_refuse_unless_project_consents` is called at `saas_client/client.py:181` (and `:157`)
**before** `url = f"{self._base_url}{path}"` at `:182`. So an acceptance test that builds
project A without a consent record **passes SC-001 unchanged against the pre-fix code** —
the exact "tests refusal-when-denied, proves nothing" shape.

The consenting-neighbour precondition exists only in US1 prose and AS1 — **neither is a
Success Criterion**, and the SC table is what tasks are generated from and checked off
against.

**Adjudication: CONFIRMED, and this is the most serious finding of the entire pass.**

**Resolution:** SC-001 must read "from a **consenting** checkout that does not own the
named decision", and SC-002's positive control must be bound to SC-001's **same fixture
and module**, not merely co-listed.

### D-2 [CRITICAL] SC-003 attaches the byte-level assertion to the SECONDARY defect — **CONFIRMED**

SC-003 asserts the constructed request line, but **only for an id that fails the shape
check** (FR-005). The consent-laundering defect — a well-formed ULID owned by B,
transmitted to A's team under A's token — is covered by request **count alone**.

The standing rule is to assert the engagement-relevant identifier reaching the transport,
**not a flag or a tally**; and a count of zero is also what an unrelated upstream
short-circuit produces (`tracer-tooling-friction.md:632-645`).

**Resolution:** add an SC asserting B's `decision_id` appears in **no** constructed
request line, and that no request line addressed to A's `team_slug` carries it. **The
idiom already exists in-repo:** `transmitted_text(sink)` at
`tests/specify_cli/saas_client/test_client_consent_gate_3030.py:293`.

### D-3 [BLOCKER] The spec permits at FR level an implementation its own acceptance forbids — **CONFIRMED**

FR-007's falsifier explicitly admits two shapes: refuse on divergence, **or** re-resolve
token and team from the owning root. **Under re-resolve, exactly one request IS sent** (to
B's team, under B's token) — and both SC-001 ("zero outbound HTTP requests") and AS1 ("no
HTTP request is constructed") **red**.

A plan taking the admitted second shape is forced either to abandon it or to rewrite
SC-001 downward — and rewriting an acceptance criterion to fit an implementation is how a
red-first proof is lost.

**Resolution:** restate SC-001 as the invariant that holds under **both** shapes — *"no
request line carrying B's identifier is addressed to A's team or authorised by A's
token"* — or decide the shape in the spec and delete the second option from FR-007's
falsifier.

### D-4 [HIGH] SC-008's counterfactual is measurably FALSE — **CONFIRMED; the spec over-generalised my F-A7**

SC-008/US4-AS1 say that at `bb2020fea` deleting `register_saas_client_factory` "leaves the
suite green", citing F-A7. **Measured false:**

- `tests/invocation/test_adapters.py:29` imports the symbol **at module scope**, calls at
  `:141`, `:194`, `:195`, `:233`
- `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py:53` imports it, calls
  at `:108`, `:316`
- `tests/architectural/baselines/fast-tests-core-misc-nodeids.txt:1841` pins
  `test_register_saas_client_factory_idempotent_by_qualname` **by node id**

Deleting the `def` is a **collection-time ImportError in two files** — loudly red.

**My F-A7 is correct and the lens confirms it**: `test_sync_registers_no_saas_client_factory`
genuinely never names the symbol. **The spec generalised "that one test stays green" into
"the suite stays green" without re-measuring.** Only the **export** half is truly unpinned
— nothing imports the symbol from the `specify_cli.invocation` *package*, so removing
`invocation/__init__.py:21` and `:111` does leave the suite green.

**Resolution:** narrow FR-019/SC-008 to the **export half** and say why. Otherwise an
implementer working red-first finds the red already present and lands a pin with no
demonstrated discriminating power.

### D-5 [HIGH] The per-class floor catches ONE of the four halving mechanisms — measured — **CONFIRMED; my proposed remediation was insufficient**

In **both** guards `scanned += 1` executes **before** the attribution test
(`test_client_consent_gate_3030.py:340` vs `:342-346`;
`test_saas_client_consent_gate_3030.py:387` vs `:388`).

- **Mechanism 2 (vocabulary widening) leaves the per-class counts EXACTLY unchanged** —
  NFR-003 and SC-007 report green with the coverage gone.
- **Mechanism 3 measured:** all three tracker construction sites are bare `ast.Name`
  callees (AST dump of `tracker/origin.py:165`, `:265`, `saas_service.py:109`). So
  unifying on the saas guard's stricter `Name`-only predicate leaves
  `scanned["SaaSTrackerClient"] == 3` — **exactly at the proposed floor** — while
  permanently blinding the guard to `mod.SaaSTrackerClient(...)`.
- Mechanism 4 is outside any counter by construction.

Compounding: **FR-015 and FR-016 have no Success Criterion at all.**

**Adjudication: CONFIRMED, and it corrects my F-A3 remediation.** A per-class floor is
necessary but nowhere near sufficient.

**Resolution:** retitle NFR-003 from "Guard coverage does not decrease" to **"scanned-site
count does not decrease"** (the metric cannot support the stronger claim). Add SCs for
FR-015/FR-016 asserting, per class, (a) a **rejection** of the other class's accepted
attribution form and (b) a **match** on a callee shape no `src/` site uses today —
neither is exercised by the current corpus, so neither is protected by any count.

### D-6 [HIGH] Rot-mode 5 is live on the exact symbol being consolidated — **CONFIRMED**

Both deciding modules bind **by value**:

```
saas_client/client.py:23      from specify_cli.saas_client.egress_consent import project_egress_refusal
tracker/saas_client.py:34     from specify_cli.tracker.egress_consent  import project_egress_refusal
```

with decisions at `client.py:157` and `tracker/saas_client.py:329`. After consolidation
the symbol is reachable by **three** names; patching or mutating the shared module leaves
**both deciding modules inert**.

SC-004's conclusion is a **sameness** — the friction doc's explicitly flagged suspect kind
(`tracer-tooling-friction.md:468-478`). Concrete collapse route: a partial consolidation
leaving `tracker/egress_consent.py` as a re-export lets a shared-module test report
byte-identity **while the tracker transport still returns "engagement identifiers"**.

**And C-004 does not prevent this** — the seam-allowance gate only requires the literal
`project_egress_refusal` in `tracker/saas_client.py`, which the **import line at `:34`
already satisfies**.

**Resolution:** promote US2-AS1's "produced via the tracker transport **and** via the SaaS
client transport" into SC-004's own text; add as a requirement the recorded rule —
*patch every name the symbol is reachable by and report the per-site split*
(`tracer-tooling-friction.md:581-584`).

### D-7 [HIGH] Q6's "no precedent" premise is measurably FALSE, and it is already steering Q1 — **CONFIRMED**

Q6 claims reading CI filter definitions from a test "is the only mechanism… and there is
no precedent for it in this repository", then concludes "the second option is probably
right… it partly answers Q1."

**Measured:** `tests/architectural/_gate_coverage.py` **already** parses
`dorny/paths-filter` steps (`:357`, `:531-533`), builds `filter_groups` (group → globs,
`:476`) and `job_gating_groups` (job → filter outputs in each job's `if:`, `:474`, `:612`),
enumerates always-on ungated jobs (`:1539`), and maps `src/specify_cli/<dir>` to its
covering dorny glob (`:1587`). `tests/architectural/test_gate_coverage.py` is its live
guard suite. **This is precisely SC-006's mechanism.**

Sharper still: the friction doc's "Control your diagnostic" entry
(`tracer-tooling-friction.md:531-547`) **is about this very module** — so the spec's own
evidence base contradicts the claim.

**Resolution:** name `_gate_coverage`'s `filter_groups`/`job_gating_groups` as SC-006's
mechanism, and **re-open Q1 without Q6's false premise.**

### D-8 [MEDIUM] The C-005 hole falls in a band where NEITHER gate fires — **CONFIRMED**

`_gate_coverage.py:1205` sets `T_LOC = 500`. The unclaimed-src-dir worklist rule
(`:1230-1233`, enforced `:1483`) requires `>= t_loc` LOC. The two modules being
consolidated are **150 and 219 lines**, so any shared module lands at ~150–250 LOC —
**under half the threshold**.

Q1 option (d) therefore sits in the one size band where **neither** the integration-boundary
gate **nor** the LOC-gated coverage detector fires. `run_all` "loud by design" covers job
*selection*, not *classification*.

**Resolution:** if (d) is taken, make the C-005 classification edit an explicitly listed
task with its own assertion, and record in the plan that **no existing gate will notice
its omission.**

### D-9 [MEDIUM] FR-003 in isolation WIDENS the disclosure surface — **CONFIRMED**

Making `--mission-slug` load-bearing *without* FR-001/FR-004 means an operator standing in
A can now name B's slug and have it affect the real invocation. Today the flag is inert on
the live path (`decision.py:550`, dry-run only). Each FR carries an independent
`Status: Open` row and US1's "Independent Test" is asserted at story level, **so nothing
forbids FR-003 landing alone.**

**Resolution:** state that FR-003 must not land without FR-001 and FR-004, or fold it in.

### D-10 [MEDIUM] NFR-001's scans match a literal class name — **CONFIRMED, converges with R-12**

The scans match `ast.Name(id="SaasClient")` / `from_env` on a `Name("SaasClient")`
receiver (`test_client_consent_gate_3030.py:330-337`) and `name != "SaaSTrackerClient"`
(`test_saas_client_consent_gate_3030.py:381-384`). **An aliased import, a factory, or a
transport injected as a parameter is invisible** — so "count unchanged or lower" is
satisfiable while a new egress surface is added.

Independently confirms R-12: the Bundle A table credits this bound to `#3113`, but
`#3113`'s mechanism is `_transmits_a_body` reading `node.keywords` only — **a different
scan with a different hole.**

**Resolution:** name the alias/indirection blind spot separately; restate NFR-001 as a
count over **name-matched sites**, not a proof about egress surface.

### D-11 [MEDIUM] Rot-mode 4 is not adequately addressed, and the mission's OWN edge case sits on it — **CONFIRMED**

NFR-006 asks only that version-divergent branches "be identified in the plan", at Medium
priority, and **no SC covers it**.

The connection the lens drew is excellent: the mission's own edge case — *"the decision
ledger under the named mission is missing or malformed. Unreadable ownership is not
consent"* (`spec.md:188-189`) — sits **directly** on the recorded divergence.
`Path.exists()` swallows `EACCES` on 3.14 and propagates on 3.11/3.12
(`tracer-tooling-friction.md:484-493`). So a permission-denied ledger takes the "not
found" branch locally and **raises on CI**.

**Resolution:** make NFR-006 executable — require the `#3111` acceptance file and both
attribution guards to run once under `uv venv --python 3.11` with the `N passed` line
quoted — and give it an SC.

### D-12 [MEDIUM] Both candidate test directories FABRICATE the consent precondition US1 depends on — **CONFIRMED**

`tests/specify_cli/saas_client/conftest.py:51,74` and `tests/sync/tracker/conftest.py:55,166`
— each autouse fixture injects a **consenting** `project_root` whenever the kwarg is
omitted. The widen path itself is safe as written (`from_env` always passes `project_root`
explicitly, `client.py:136-142`), **but any `#3111` test that constructs a client inline in
those directories inherits fabricated consent.**

That is the recorded trap twice over: the filename-matched guard
(`tracer-tooling-friction.md:104-122`) and the three tests green only because a directory
fixture arranged their premise (`:666-686`). **The spec never mentions these fixtures.**

**Resolution:** require the `#3111` acceptance test to write **both** checkouts'
`.kittify/config.yaml` on disk and pass roots explicitly, with an **in-file positive
control** proving A's consent actually grants.

### D-13 [LOW] FR-011's self-enforcement claim survives Q1 option (d) — **CONFIRMED, no change needed**

`test_no_dead_symbols.py:13-24` walks **every** `*.py` under `src/`, so a new package's
`__all__` is scanned. Recorded so the plan does not re-derive it.

### Debbie's honest scope concessions (recorded, not treated as gaps)

- Did **not** reproduce the `#3111` leak. The gate-precedes-URL claim is read from source
  — **"reasoning, not measurement", labelled as such** so it can be upgraded.
- Did not verify the `ci-quality.yml` line numbers in F-A3/F-ENV-6; verified the
  gate-coverage machinery modelling those filters exists and is live.
- Ran nothing on 3.11/3.12; the NFR-006 finding rests on the friction doc's recorded
  measurement plus the absence of any SC.
- Did not assess Q4 or Q5 (design-choice questions, not verification-strength).

---

## Lens: architect-alphonso (structure / seams / topology) — VERDICT ACCEPT-WITH-CHANGES

Measurement hygiene declared: AST-only probes, `PYTHONPATH` pinned to this clone, **input
count printed (937 files)**, each probe run against a known-answer case first, no piped
pytest, no `ruff format`. Noted HEAD = `7300b8fe` (one commit past `bb2020fea`,
`meta.json` only) — **I verified this independently: `git diff --stat bb2020fea HEAD` = 1
file, 14 insertions, no `src/`, no `tests/`, no workflows.**

### A-0 — The constraint set is NOT over-determined. No BLOCKER on placement.

The question I dispatched this lens to answer. **Answer: every one of Q1's five
candidates is legal.** C-004 is a *substring* test and `tracker/saas_client.py` contains
the literal at **two** independent places — `:34` (import) and `:329` (call). C-001
excludes only the four CORE dirs. C-005 is a one-line `INTEGRATION_PREFIXES` addition and
— verified — needs **no** second edit, because `test_layer_rules.py:_DEFINED_LAYERS`
enumerates **top-level** `src/` packages only (`_SRC.iterdir()`, `:203-208`).

### A-1 [BLOCKER] FR-017's property is already false for the tracker guard — **CONFIRMED, converges independently with R-9**

Full measured chain at HEAD:
- tracker guard is `pytest.mark.fast` (`test_saas_client_consent_gate_3030.py:39`)
- only `fast-tests-sync` (`ci-quality.yml:1125`) and `integration-tests-sync` (`:2333`)
  collect `tests/sync/`; both gate on `needs.changes.outputs.sync == 'true'` (`:1100-1101`)
- the `sync` dorny filter has exactly three members (`:203-205`) — **`tracker/**` is not
  one of them**
- the fail-closed catch-all cannot save it: `tracker/**` *is* in `agent_surface`
  (`:400-405`), which is in the `unmatched` union loop (`:469`) → `unmatched=false`,
  `sync` stays false (`:162`)
- `fast-tests-core-misc` (the job `agent_surface` gates) explicitly `--ignore=tests/sync`
  (`:1640`); its `specify-cli-rest` shards are scoped to `tests/specify_cli` (`:1604`)
- `unit-contract-residual` selects `-m "(unit or contract) and not (fast or …)"` (`:2827`)
  — excludes a `fast`-marked module

**Two lenses reached this independently, by different routes. Treated as settled fact.**

### A-2 [BLOCKER] FR-017 is keyed on the wrong unit — ZERO of the four SaaS-client sites live in the SaaS-client package — **CONFIRMED, and this is the sharpest finding of the pass**

Re-ran both guards' AST predicates over 937 files, reproducing the baseline exactly
(4 SaaS-client, 3 tracker — third independent confirmation). But their **locations**
falsify the requirement's shape:

```
SaasClient sites (4):   cli/commands/charter/interview.py:216
                        cli/commands/decision.py:558
                        missions/plan/plan_interview.py:150
                        missions/plan/specify_interview.py:150
SaaSTrackerClient (3):  tracker/origin.py:165, :265
                        tracker/saas_service.py:109
```

**Not one of the four SaaS-client construction sites is under `src/specify_cli/saas_client/**`.**
They sit in the `cli` group (`:258-261`) and `missions` (`:213-215`). A PR confined to
`cli/**` sets `cli=true` and nothing else; `fast-tests-core-misc`'s gate (`:1580`) lists
ten groups and **`cli` is absent**. `fast-tests-cli` runs `tests/cli/ tests/specify_cli/cli/`
(`:1540`) and never `tests/specify_cli/saas_client/`.

⇒ **Adding a fifth unattributed `SaasClient.from_env(...)` to `cli/commands/decision.py`
produces a PR on which the SaaS attribution guard does not run.** That file is *exactly
what this mission edits for `#3111`*. The guard's whole purpose is to catch that edit.

**Resolution:** re-key FR-017/SC-006 on **construction-site locations**, not transport
package names: *"for every source directory containing a scanned construction site, a diff
confined to that directory selects a job that collects the guard covering that class."*
Derive the directory set from the guards' own scan. **Materially larger than the spec's
version — the plan must be told so.**

### A-3 [HIGH] Q1 option (a) — placing the wrapper in `sync/` structurally DEFEATS FR-013 — **CONFIRMED**

FR-013's contract depends on the import being **lazy and inside the function**
(`saas_client/egress_consent.py:107-113`). If the wrapper becomes `specify_cli.sync.<mod>`,
any caller doing a module-scope `from specify_cli.sync.<mod> import project_egress_refusal`
forces `specify_cli/sync/__init__.py` to execute **first**. An unimportable sync package
then raises `ImportError` at *transport module import time* — **the transport cannot be
imported in order to be asked**, so US2 AS#4 is unreachable and NFR-004 is answered by a
traceback.

Measured so as not to overstate cost: `sync/__init__.py` defers heavy deps via
`__getattr__` (`:11-12`), module-level closure is 3 modules — a **semantics** objection,
not a load-time one. Also measured: no import cycle (`sync` reaches neither `tracker` nor
`saas_client` at module level).

**Resolution:** add the "Against" row to Q1(a). **This is a structural argument for
option (d) the spec currently lacks** — a classified `src/specify_cli/egress/` is the only
candidate preserving FR-013 under module-level caller imports.

### A-4 [HIGH] C-005's framing is wrong — the laundering hole exists TODAY, nine times over — **CONFIRMED; corrects the spec, not me**

The mechanism is verified against the scanner. But the lens ran the module-level
transitive closure (937 modules indexed, 93 CORE scanned, full AST including lazy
imports): **nine CORE modules already reach `specify_cli.sync` transitively through
unclassified packages**, all green under the gate. Hand-verified chain:

```
status/aggregate.py:620                → coordination.status_transition
coordination/status_transition.py:288  → git.commit_helpers
git/commit_helpers.py:1148             → sync.local_commit
```
Negative control run: `status/aggregate.py` has no direct integration-prefix import, so it
passes the scan. Others: `readiness/{auth,coordinator,render}.py → cli/commands/_auth_recovery
→ sync.routing`; `core/version_checker → specify_cli → sync.restart`.

**Resolution:** keep C-005 (one line, cheap) but restate honestly as **"do not add a
tenth"**, and drop the spec's implication (`:379-384`) that classification *closes* the
route. Name the transitive-reach scan in "Out of scope" as a separate mission.

### A-5 [HIGH] C-004 inherits an over-claim from my F-A5 — **CONFIRMED; MY ERROR**

F-A5 states *"Renaming the function, or removing its call from that file, reds this gate."*
The gate is a plain substring test over the whole file. `tracker/saas_client.py` contains
the literal at `:34` (import) **and** `:329` (call). **Delete the call at `:329` and the
import at `:34` still satisfies the gate.** Put the name in a docstring and it satisfies
with no code at all.

The mission's own consolidation is precisely the change most likely to produce that state.
C-004 as written will be read by the plan phase as "the seam is protected". **It is not —
the *text* is protected.**

**Resolution:** keep C-004 as a hard textual constraint (it is real and it will red on a
rename), but add a companion requirement: the consolidation must leave
`project_egress_refusal` a **live call on the transmit path**, asserted **behaviourally**
(drive the transport into a non-consenting project, observe the refusal), not by
substring. Squarely DIR-041.

### A-6 [MEDIUM] Q6's "no precedent" is false — **CONFIRMED, converges with D-7**

`tests/architectural/_gate_coverage.py` has `parse_workflow`, `load_gates`, `Gate`,
`WorkflowModel`, `positive_marker_tokens`, `parse_pytest_invocation` (`:199-517`), plus
five live guard suites and the census `ci_topology_census.json`.

Additional insight beyond D-7: `test_ci_collection_completeness.py:1-16` asserts every
collected node is selected by ≥1 job **that runs on a push to `main`** — and on the push
path `github.event_name == 'push'` makes every gate true. **That is exactly why A-1
survives that gate.** The existing invariant is push-path; FR-017 is a **PR-path**
question.

**Resolution:** name `_gate_coverage` as the mechanism. **Strike Q6's fallback** ("keep
one guard per package in its existing tree… holds by construction") — that is the
arrangement which is currently broken. *(This retracts the reading I gave earlier: I had
called Q6's fallback "likely the right answer". It is not.)*

### A-7 [MEDIUM] D-1's domination argument for (b) rests on a property already true of (a) — **CONFIRMED; MY REASONING ERROR, conclusion survives**

I rejected (b) because it "leaves a getter that can never return non-`None` and a consumer
branch dead by construction". But `propagator.py:64-72` says of **today's** state, in
source: *"In production this returns `None` every time, and has always done so (#3030
FR-032)… Everything below this lookup in `_propagate_one` is therefore inert."*

**That is (a).** The getter already can never return non-`None`.

**The sound version, which reaches the same verdict:** (b) removes the only mechanism by
which the getter could **ever become** meaningful, while keeping the getter and its
consumer — converting a *usable* empty seam into a *permanently* dead branch.

Consequently my phrase "the read side is live" is ambiguous in the way that matters:
**"live" means executed on every propagation, NOT returns a client.**

**Resolution:** restate as "executed on every propagation, returns `None` by construction
until a factory is registered". **Keep D-1.**

### A-8 [MEDIUM] D-1's option set is incomplete — a fourth option exists — **CONFIRMED; MY OMISSION**

My (c) bundled "delete `register`, `get`, **and** the propagator's egress branch". Those
are **separable**. The consent-gate ordering D-1 leans on (`propagator.py:96-100`, gate at
`:127-134`) exists independently of the seam functions. So:

> **(d) Delete `register_saas_client_factory` and `get_saas_client`; keep the propagator's
> consent gate and the recorded `request_text` refusal.**

This preserves D-1's ground 2 in a *more* discoverable location while removing the empty
seam entirely. It does not preserve ground 1 (it still edits `propagator.py`), so I expect
(a) still wins — **but an analysis that collapses two separable deletions into one option
has not shown (a) beats every alternative.** DIR-003.

**Resolution:** record (d) and dismiss it explicitly. Done in the handoff.

### A-9 [MEDIUM] FR-018 creates a second copy of a rationale that already has a canonical home — **CONFIRMED**

The `request_text` hazard is recorded **in full, at the point of use**, at
`propagator.py:70-83`. FR-018 asks `adapters.py:130-137` to state the same two facts —
**two independently-editable presentations of one policy, structurally the identical defect
FR-008 exists to remove.**

**Resolution:** narrow FR-018 to (i) delete the false sentence at `adapters.py:135` and
(ii) **point to** `propagator._get_saas_client` as the canonical record.

**Trap flagged for the plan:** the **identical** sentence appears on the sibling registrar
`register_egress_consent_resolver` (`adapters.py:113`), where it is **TRUE** — sync does
register that resolver. **A grep-and-replace across `adapters.py` would break a correct
docstring.**

### A-10 [LOW] Q1 silently drops `delivery/`, a candidate my own F-A4 named — **CONFIRMED**

Measured: `src/specify_cli/delivery/**` is in the `core_misc` filter group
(`ci-quality.yml:273`), routing to `fast-tests-core-misc` / `integration-tests-core-misc`
— **the same jobs that already run the SaaS guard, a stronger routing position than (d)'s
`run_all`-by-accident.** Also `delivery` already imports `specify_cli.sync`, so it carries
the same C-005 gap as (d) without C-005 binding it.

**Resolution:** add the row with trade-offs, or state why it was dropped.

### A-11 [LOW] C-002 mis-describes today's structure — **CONFIRMED**

Both guards scan the **entire** `src/specify_cli` tree (`rglob("*.py")` at
`test_client_consent_gate_3030.py:319-324`, `test_saas_client_consent_gate_3030.py:373-378`).
They are independent **per transport class**, not per package. FR-014 gets this right;
C-002 does not.

**The useful consequence, which removes a worry the plan would otherwise carry:**
wherever the shared wrapper lands, **neither guard's scan scope changes. Placement cannot
shrink coverage** — only merging the counters (Mechanism 1) or the predicates
(Mechanisms 2–3) can.

### Alphonso's verdict on MY recorded findings

Held up under independent measurement: F-A1, F-A2, **F-A3 (all four mechanisms)**, F-A4,
F-A7, F-B1–B7, F-ENV-1/4/5/6, and NFR-001's 3/4 baseline.

- **F-A5 OVER-claims** → A-5. My error.
- **F-A3 Mechanism 4 UNDER-claims** → A-1/A-2. I recorded it as a hazard the consolidation
  *could create*; it is a hole that **exists now**, and the construction-site locations make
  it worse than the two-way split I described.
- **D-1's conclusion right; its stated ground for dismissing (b) is not, and its option set
  is incomplete** → A-7, A-8.

### Alphonso's scope concessions

Ran **no test suite** — all claims from source, workflow YAML and AST probes. Explicitly
recommends the tracker-guard routing finding (A-1) be **confirmed by an actual CI
observation on a tracker-only diff** before the plan commits to a fix shape: the dorny/
`needs` evaluation model is a reading of the YAML, not a run. Did not evaluate Q2, Q4, Q5,
Q7 or NFR-006 (outside a topology lens).

---

# §1.5 — ORCHESTRATOR ADJUDICATION AND DECISIONS

All four lenses returned **ACCEPT-WITH-CHANGES**. Tally: **2 CRITICAL, 3 BLOCKER,
17 HIGH, ~20 MEDIUM/LOW.** No irreconcilable divergence — two pairs converged
independently (R-9/A-1 on tracker routing; D-7/A-6 on Q6's false premise), and no lens
contradicted another on a consequential point. **No second-opinion delegate needed.**

## Divergence check (required by the squad recipe)

| Potential conflict | Adjudication |
|---|---|
| R-2 (within-checkout search) vs P-3/R-3 (weaken AS1) | **Compatible.** The search answers "does *this* checkout own it"; it structurally cannot name project B — which is exactly *why* AS1 must weaken. They are the same finding from two directions. |
| A-3 (favours a neutral package) vs A-10 (`delivery/` has better routing) vs D-8 (a neutral package falls under `T_LOC`) | **Complementary, not conflicting.** Three independent inputs to Q1. The plan phase weighs them; the spec must record all three. |
| P-7 (provenance, not type) vs my F-B7 | **I conceded to P-7.** No other lens contested it. |
| D-4 (SC-008 counterfactual false) vs my F-A7 | **No conflict.** F-A7 is correct; the *spec* over-generalised it. |

## Decisions I am taking now, so the remediation does not have to guess

### D-2 — Q4 resolves to the **within-checkout search** (R-2)

Glob `<repo_root>/kitty-specs/*/decisions/index.json`, membership-test with the existing
`load_index` (`decisions/store.py:46,58-64`) reusing the shape at `store.py:112-120`.

**Why:** it dissolves the R-1 BLOCKER (SC-002 stays true — no currently-succeeding
invocation becomes a refusal), needs **no** `decision_id`→project mapping (C-009 stands),
needs **no** mandatory `--mission-slug` (no compatibility break on a hidden
automation-facing command), makes **no** network call (NFR-002 holds), and performs **no**
cross-checkout enumeration (no new disclosure surface). It is strictly better than both
options Q4 originally offered.

**Precondition that would falsify D-2:** if a `decision_id`→owning-project mapping ever
lands, the search stops being the only option and the design should be revisited.

### D-3 — FR-007 resolves to **refuse-on-divergence**; the re-resolve option is deleted

The D-3 BLOCKER is that FR-007's falsifier admits two shapes and the acceptance criteria
only permit one. **Under D-2 the dilemma disappears, because re-resolve is not
implementable:** re-resolving token and team "from the owning root" requires *knowing the
owning root*, and per C-009/F-B1 that is exactly what cannot be determined. The
within-checkout search returns *owns it* / *ownership not established* — never an
identified project B.

So refuse-on-divergence is **forced by C-009**, not merely preferred. It also matches the
parent mission's discipline: *inability to determine consent is not consent.*

**Resolution:** delete the re-resolve option from FR-007's falsifier and state that it is
unimplementable under C-009, so a successor does not re-propose it.

### D-4 — FR-017 splits: a narrow in-mission requirement plus a filed follow-up issue

A-1/A-2 establish that the CI routing gap is **pre-existing**, that it affects **both**
guards, and that keying the fix on construction-site *locations* is materially larger than
the spec's version. The operator's standing instruction is to **file follow-up issues for
anything found out of scope rather than absorbing it.**

- **In mission (narrow, provable):** the guard covering each transport class whose
  construction sites this mission *touches* must run on this mission's own diff. This
  mission edits `cli/commands/decision.py:558` — a SaaS-client site — so the SaaS
  attribution guard must be routed onto a `cli`-only diff. Non-negotiable, because
  otherwise this mission's own change is unguarded (A-2).
- **Follow-up issue (out of scope):** re-key guard routing on construction-site locations
  generally, covering the tracker guard's `tests/sync/` placement (A-1) and any future
  site migration. Mechanism exists: `_gate_coverage`'s `filter_groups` /
  `job_gating_groups` (D-7/A-6).

### D-5 — Q1 loses option (a); the rest stay open for the plan

Option (a) `sync/` is **eliminated** on A-3's ground: it converts FR-013's
operator-actionable refusal into an `ImportError` at transport-import time under
module-level caller imports. That is a structural defect, not a trade-off.

(b), (c), (d), (e) and the restored `delivery/` candidate (A-10) remain open. **The plan
phase owns the choice** and must weigh A-3 (neutral package preserves FR-013), A-10
(`delivery/` routes better), and D-8 (a ~150–250 LOC package falls under `T_LOC = 500`, so
**no existing gate notices a missing classification**).

### D-6 — I retract a reading I gave earlier

I previously judged Q6's fallback — *"keep one guard per package in its existing tree,
which makes the routing property hold by construction"* — as "likely the right answer".
**Two lenses measured that premise false** (D-7, A-6) and A-1/A-2 showed the existing
arrangement is the broken one. **Retracted.** The fallback must be struck from Q6.

## Findings deliberately NOT actioned in this mission (carried as residuals)

Each is MEDIUM-or-below or explicitly out of scope, and each is written where a successor
will find it — this file plus the handoff prompt.

| Finding | Why carried, not fixed |
|---|---|
| P-4 ADR for the egress-consent boundary | **Actioned, not carried** — folded in as a requirement. Cheapest item in the bundle and the only one acting on recurrence. |
| A-4 nine pre-existing CORE→sync transitive reaches | Out of scope: needs a transitive-reach scan, a separate mission. C-005 restated as "do not add a tenth". Follow-up issue. |
| R-17 "engagement" absent from `docs/context/` | Folded as a small requirement (define the term) — it is one glossary entry and FR-009 would otherwise ship an operator-facing term the glossary does not know. |
| paula's `ConsentedBatch` extension to both transports | Out of scope, explicitly. Seven sites, four CI groups. Follow-up issue with its own falsifier. |
| A-1 tracker-guard routing (general fix) | Out of scope per D-4; follow-up issue. |
| Alphonso's request to confirm A-1 by real CI observation | **Cannot be done pre-implementation** — needs a pushed tracker-only diff. Recorded as an explicit unverified premise in the handoff. |

---

# REVIEW-LOOP GOVERNANCE (corrected by the operator, mid-mission)

**Correction received:** the review loop and the 3-round escalation rule apply to the
**spec, plan and tasks artifacts**, not only to implementation work packages. My earlier
reading — one squad pass per point-cut, remediate, move on — was wrong.

## The rule, as it actually binds

Every artifact (spec, plan, tasks) goes: **author → independent review → REJECT means fix
the findings, then send it back for re-review → repeat.**

- **After 3 review rounds on the same artifact**, if any finding above **MEDIUM** severity
  still stands (HIGH / BLOCKER / CRITICAL) → **halt and escalate to the operator with a
  multiple-choice question.** No fourth round. **Never lower a severity to clear the gate.**
- **MEDIUM and below** may be carried as recorded residuals, provided they are written
  where a successor will find them — this file and the handoff prompt.
- Reviewers are always a different agent than the author, and **reviewers do not edit** —
  they issue a verdict.

## Round ledger

| Artifact | Round | Reviewers | Outcome |
|---|---|---|---|
| **spec** | 1 | `paula-patterns`, `reviewer-renata`, `debugger-debbie`, `architect-alphonso` (4 lenses, opus, read-only) | **REJECT** — 2 CRITICAL, 3 BLOCKER, 17 HIGH confirmed. Remediated 526→1001 lines; committed `df64f07`. |
| **spec** | 2 | `reviewer-renata` + `debugger-debbie` (the two lenses that raised the gating items), re-reviewing their own findings *and* the ~475 lines of new surface | *in flight* |
| **spec** | 3 | — | only if round 2 rejects; **escalation gate after this** |
| **plan** | 1 | post-plan squad | not started — gated on the spec loop closing |
| **tasks** | 1 | post-tasks squad | not started |

## Sequencing correction

`spec-kitty plan` was run before the spec's review loop had closed. The plan author was
allowed to continue rather than discard the work, because it is grounded in decisions
D-2..D-6, which round 2 is **not** re-opening (round 2 checks whether the *fixes* are real
and attacks the *new* requirements). **The plan is provisional until the spec is accepted**,
and any spec change arising from round 2 is folded into the plan **before** the plan's own
review round 1 begins.

---

# §2 — PLAN AUTHORING: measurements that CORRECTED earlier findings

Recorded here (not only in `plan.md`) because two of these overturn things a squad lens
asserted, and the operator asked specifically for "anything a squad raised that you judged
wrong, and why — so it is not re-raised as new".

## PL-1 — ROT-MODE 4 IS LIVE, EXECUTED ON BOTH INTERPRETERS, AND IT LANDS ON THIS MISSION'S OWN EDGE CASE

The highest-value measurement in the mission so far, and it was **executed**, not reasoned:

```
Path.exists() on an EACCES path:
  Python 3.14.4  -> returns False
  Python 3.11.15 -> raises PermissionError
```

`decisions/store.py:63` is `if not path.exists()` — **inside `load_index`, the exact
function Decision D-2 mandates FR-001 reuse.**

⇒ An unreadable decision ledger **refuses correctly on 3.14 and produces an uncaught
traceback on CI (3.11/3.12).** The mission's own edge case ("unreadable ownership is not
consent") sits directly on the divergence.

**Consequence for the design:** FR-002's unreadable-ledger branch **cannot rely on
`load_index`**; the new ownership module needs an explicit `except OSError`, and it must be
executed under 3.11 to prove it.

This is exactly what debugger-debbie's D-11 predicted from the friction record — and the
plan phase **measured** it rather than accepting the prediction. A plan-phase judgement
made on 3.14 alone would have shipped it.

## PL-2 — A-3's headline claim is TOO STRONG (squad finding partially overturned)

**A-3 (architect) claimed:** a neutral package "is the only candidate that preserves
FR-013 with module-level caller imports".

**Measured** (module-level import closure of every surviving candidate; controls:
`saas_client`/`tracker` must be NO because FR-013 works today, and a known column-0 sync
importer must be YES): **only `sync/` reaches `specify_cli.sync` at module level.**

⇒ **FR-013 eliminates option (a) and discriminates nothing else.** Option (d)'s headline
advantage is **withdrawn**; the plan re-justified (d) on other grounds.

**Adjudication: A-3's elimination of (a) STANDS** (my Decision D-5 is unaffected). **A-3's
"only candidate" clause is overturned by measurement.** Do not re-raise it as an argument
for (d).

## PL-3 — A-10 was right, but drift entered the spec's Q1 table (two senses of "classified")

`delivery/**` **is** in the `core_misc` dorny group (`ci-quality.yml:273`), but
`specify_cli.delivery` is **NOT** in `INTEGRATION_PREFIXES`. Those are two different senses
of "classified".

**In C-005's sense, `delivery/` is unclassified** — so option (f) carries D-8's gap while
the spec's Q1 "For" column records that it does not. **A-10 stated this correctly; the
conflation was introduced when it was transcribed into the Q1 table.** Filed as **FU-7**.

## PL-4 — A worked near-miss on "control your diagnostic", recorded as a pattern

The plan author's **first** closure probe reported `delivery/ → sync`, one step from
concluding that (f) fails A-3 exactly like (a). **The edge was `delivery/targets.py:56`,
inside an `if TYPE_CHECKING:` block** — not a runtime import at all.

The v1 control **passed** but did not *discriminate that error mode*. This is the friction
doc's rule biting in a new costume: a control that passes is not the same as a control that
can detect the specific way you are about to be wrong.

Recorded in `plan.md` as a worked example.

## Q1 RESOLVED by the plan: option (d), `src/specify_cli/egress/`

With **two mandatory one-line accompaniments** (neither is F-ENV-6's 5-edit atomic new-group
registration):
1. `"specify_cli.egress"` added to `INTEGRATION_PREFIXES`
2. `'src/specify_cli/egress/**'` added to the **existing** `core_misc` glob

**Trade-off accepted, stated plainly:** a new package for one function and one constant,
plus two edits that **no gate will notice if forgotten** (~150–250 LOC vs `T_LOC = 500`).
Both are explicitly listed tasks with their own assertions.

**Falsifiers:**
- **F1** — if `specify_cli.delivery` ever enters `INTEGRATION_PREFIXES`, option (f) becomes
  genuinely classified at zero marginal cost and Q1 should revisit toward it.
- **F2** — if the merged wrapper cannot be written without importing from a transport
  (decided by **Q2**), the neutral premise is false and **(e) becomes the honest answer**.
  ⇒ **Resolve Q2 before creating the package.**

## Re-measurement discharging my caveat C-4

**SaasClient 4 / SaaSTrackerClient 3, over 937 input files**, predicates copied verbatim,
known-answer control run first. **Fourth independent reproduction.** C-4's "inherited, not
re-measured" caveat is discharged.

## Also resolved as recorded plan decisions

- **Q5** — dry-run **warns but does not refuse** (it transmits nothing, so it is not egress,
  but a dry-run that renders the endpoint without flagging a mismatch is a trap).
- **Q7** — **one** check, at the CLI boundary, reusing an existing ULID regex (avoids the
  fourth and fifth spelling of one shape check, per R-10/P-10).
- **Q8** — standing gate vs one-off PR evidence, chosen **per criterion**.

## Q2 REMAINS OPEN — and it is the operator's call

Which wording survives in the merged refusal. The identifier sets are **asymmetric**
(measured from source): the **tracker carries no `decision_id`**; the **SaaS client carries
no `project_slug` and no issue titles**. A single merged string naming the union is
therefore noticeably longer than either current string.

**Q2 gates IC-03, and via falsifier F2 it gates the Q1 package decision itself.**

---

## Q2 RESOLVED by the operator, 2026-07-31 — per-caller fragment in a shared template

**The decision:** the shared wrapper owns the sentence template, the four verdict branches,
`UNDETERMINED_PROJECT_REFUSAL`, the `None` guard and the import-failure degradation.
**Each transport passes its own identifier-set fragment as an argument.**

Rendered outcome — **both current strings survive verbatim**:
- `saas_client` → "…so its **mission and decision identifiers** must not be transmitted; …"
- `tracker`    → "…so its **mission and engagement identifiers** must not be transmitted; …"

### Why the alternatives were rejected (recorded so they are not re-proposed)

- **Union in one fixed string** — would tell a tracker operator that *decision* identifiers
  were at stake when the tracker cannot transmit one, and the reverse for the SaaS client.
  Measured asymmetry: the tracker carries **no `decision_id`**; the SaaS client carries **no
  `project_slug`** and no issue titles. **Overstating exposure in a confidentiality message
  is the wrong direction to be wrong**, and it violates FR-009's own second clause
  ("implies none it cannot").
- **Superordinate "identifiers"** — never untrue, but drops the specificity that is the
  point of the message. In a product where `mission_slug` values are client engagement
  names, *what* would have crossed is the operator's actual question.
- **Don't merge (Q1 option (e))** — would have fired F2 by choice and removed the placement
  work entirely. Not taken.

### Consequences, which resolve two open items

1. **Falsifier F2 does NOT fire.** The fragment is passed *as an argument*, so the shared
   module never imports from a transport and the neutral premise holds. **Q1's option (d)
   — `src/specify_cli/egress/` — stands**, and the package may now be created.
2. **FR-009 becomes mechanical rather than aesthetic** (closing reviewer finding R-6): each
   transport's test asserts **its own** identifier set is fully named and that no other
   transport's kinds appear. There is a fixed per-caller set to check against, so the
   implementer can no longer both pick the wording and write the assertion that blesses it.
3. **Risk reduction not previously available:** because both DENIED strings survive
   **verbatim**, the consolidation changes **no** operator-visible text on this branch. The
   `decision`/`engagement` divergence — the only runtime string that differed, and the one
   nothing pins — is preserved rather than resolved. F-A1's "which word survives" question
   is answered by *both do*.

### Precondition that would falsify Q2

If a future endpoint makes the two transports' identifier sets **identical**, the per-caller
fragment becomes ceremony and the union string becomes correct and simpler. Revisit then.

### Still required despite the verbatim preservation

Reviewer finding **R-10** stands: the merged `DENIED` wording must be **pinned by a content
assertion in both packages' test trees**. It is unpinned today, and "we did not change it"
is not a guarantee that the next author will not. Per `delete-the-assertion-not-the-test`:
**add** pins, do not touch the existing four.

---

# §1-R2 — SPEC REVIEW ROUND 2

## Lens: reviewer-renata — VERDICT ACCEPT-WITH-CHANGES (no BLOCKER survives)

**Own-findings audit: 15 RESOLVED, 6 PARTIAL, 0 NOT RESOLVED.** No finding was reworded
rather than fixed. R-1 (the round-1 BLOCKER) is **downgraded to HIGH** and narrowed to one
mechanically-proven case.

**No-op count, measured the same way both rounds:**
- Round 1: **13 of 29 (45%)** undeclared no-ops.
- Round 2: **10 of 57 (18%)** undeclared, **plus 8 now explicitly declared**
  (`[ratchet]` / `folded`).
- The lens's own judgement: *"the `[build]`/`[ratchet]`/`folded` labelling is the single
  highest-value structural change in the remediation."*

### N-1 [HIGH] A THIRD SC-002 break survives, and it is not flag-driven — **CONFIRMED**

Measured with three synthetic corruption cases: `load_index` returns an empty index for a
**missing** file but **raises** for a malformed one — `JSONDecodeError` on bad JSON,
`ValidationError` on schema-invalid content (`decisions/store.py:58-64`).

D-2's design reads **every** mission's ledger under the acting root (measured: 49 ledgers
across 333 mission dirs in this repo). So: decision owned by healthy mission Y, unrelated
mission X has a corrupt `index.json` → **today the invocation succeeds** (nothing reads X);
after FR-001 the spec's edge case says "Refuse; do not fall through". **A currently-
succeeding invocation becomes a refusal with no flag involved**, and SC-002's compatibility
clause is scoped entirely to `--mission-slug`, so it does not cover this.

**Resolution:** state the scoping rule — *an unreadable ledger in a mission that is **not**
the answer must not veto a positive membership hit elsewhere; it may be reported as a
warning. Refusal is correct only when the search terminates with **no positive hit** AND at
least one ledger was unreadable.* Also **split the edge case**: "missing" and "malformed"
are measurably different behaviours and the spec lumps them.

### N-2 [HIGH] SC-004 became an empty solution set — **CONFIRMED, and Q2 ALREADY RESOLVES IT**

The lens owns this as an over-correction of its own R-6: SC-004 requires the text be
(i) **byte-identical** across both transports **and** (ii) each transport "name every
identifier kind in that transport's enumerated set", while US2-AS2 requires it to "imply no
kind that transport cannot transmit". **The sets are asymmetric by 15 kinds** — so a single
byte-identical string naming the union necessarily names `decision_id` to a tracker
operator. All three of Q2's candidates were inadmissible under that conjunction.

**Adjudication: the operator's Q2 decision resolves this exactly.** The lens's own
recommended fix is verbatim the option chosen — *one shared **template** plus one per-caller
identifier-kind fragment* — with SC-004 restated as **"the non-fragment portion is
byte-identical, and each transport's fragment names exactly its own enumerated set."**
Drop byte-identity of the *whole string* as the goal; keep it as the **mechanism** goal.

### N-3 [HIGH] SC-013 contradicts FR-016 — mechanically proven — **CONFIRMED**

Six synthetic callee shapes probed (input count stated: 6):

```
mod.SaasClient(x)          -> SaaS guard    False   (excluded BY DESIGN per FR-016)
mod.SaaSTrackerClient(x)   -> tracker guard True    (already true = ratchet)
mod.SaasClient.from_env(x) -> BOTH          False   (genuinely unguarded, unnamed by any requirement)
```

FR-016 requires each class keep today's strictness (SaaS: literal `Name("SaasClient")`
receiver). **SC-013 requires the guard to match `mod.SaasClient(...)` — the exact shape that
predicate is defined to exclude.** Unsatisfiable for the SaaS class without violating FR-016;
for the tracker class it is already true.

**Resolution:** **split SC-013.** Tracker half → `[ratchet]`. SaaS half → delete, **or**
state that FR-016 is *deliberately relaxed for the SaaS class* and give the new predicate.
**Do not ship a criterion that contradicts a requirement.** Also: `mod.SaasClient.from_env(x)`
is unguarded on both and named by nothing — record it.

### MEDIUM findings (each with a stated fix)

- **N-4** FR-021's two admissible discharges are not both compatible with SC-018: under
  discharge (ii) ("don't call the resolver at all") the outside-root case **cannot be
  constructed**, so SC-018 is unsatisfiable or synthetic. Make SC-018 conditional on the
  discharge; for (ii) the substitute is *every path fed to `load_index` is a member of the
  glob's own result set*.
- **N-5** Containment covers the slug path, not the **glob** path. `Path.glob` follows a
  symlinked mission dir and `is_relative_to` on the **unresolved** path returns `True`.
  Measured: **0 symlinks today**, so a shape assumption, not a live leak. Fix: `.resolve()`
  before the containment test; pin the one-level depth assumption (measured: one-level glob
  and repo-wide `rglob` both return 49, **0 missed**).
- **N-6** FR-025/SC-017 are **vacuously satisfiable conditionals** ("*any test that* patches
  or mutates…"). Write no such test and both pass while the rot-mode-5 hazard is untouched —
  the hazard is a property of the *consolidation*, not of any test. Fix: make it
  unconditional inside SC-004's end-to-end comparison, which must **report the per-site
  split** across the shared module and both by-value bindings.
- **N-7** FR-020's forbidden cheat has a permitted near neighbour: a module-private
  `def _owns_decision(...)` at the bottom of `cli/commands/decision.py` satisfies both
  FR-020 and SC-018 **and is still the fifth private answer**. Fix: state the positive
  property — the function must live **outside `cli/commands/**`** and be importable by a
  non-CLI caller. *That is the difference between a helper and a seam.*
- **N-8** FR-027 is labelled `[build]` but is **already true**:
  `tests/sync/tracker/test_saas_client_consent_gate_3030.py:258-289` and `:311-324` already
  drive the tracker transport into a non-consenting project. Relabel `[ratchet]`, cite both.
- **N-9** The coverage table's C-005 row is **a blank cell wearing a sentence** — it claims
  "an explicitly listed task with its own assertion" and **no such assertion exists**, while
  C-005 itself records that no gate notices a forgotten classification. Fix: add **SC-025** —
  if a new `src/specify_cli/<name>/` package lands, a test asserts its name appears in the
  integration-boundary gate's INTEGRATION prefixes. **This closes the only requirement in
  the spec with no enforcement at all.**
- **N-10** SC-019 verifies the ADR by re-running the grep that measured zero and requiring
  non-zero — **a file containing only the three search terms passes.** Either assert the
  three *contents*, or accept it as an existence check and say so.
- **N-11 [LOW, not a defect]** `transmitted_text` is *defined* at
  `test_client_consent_gate_3030.py:73`; `:293` is a use site. Recorded so it is not re-filed.

### R-2's cost worry WITHDRAWN by measurement

The lens retracts its own concern about the within-checkout search's cost: **333 mission
dirs, 49 `index.json`, glob 0.0017 s, parse 0.0032 s.** Also measured: `rglob` returns the
same **49** (0 missed by the one-level glob) and **0** symlinked dirs under `kitty-specs/`.

### OVER-CORRECTION VERDICT — the spec grew four kinds of duplication

Which is this mission's own defect one level up. Ranked cut list:

1. **FR-007** — fold into FR-002 explicitly, as FR-004 was. Its coverage row is
   **byte-identical to FR-002's**. *"Two folds is honest; one fold and one unlabelled twin
   is not."*
2. **FR-025 / SC-017** — delete as standalone rows; move per-site-split reporting into SC-004.
3. **SC-013's SaaS half** — delete (contradicts FR-016); keep the tracker half as `[ratchet]`.
4. **NFR-001 or NFR-003** — keep one. They are *the same integer with opposite inequalities*
   and both map to SC-007.
5. **SC-021** — delete; cite the two existing tests as FR-027's ratchet evidence.
6. **Q8 must be closed in the spec, not carried** — three criteria's meaning depends on it.

**Explicitly keep, despite looking like ceremony:** FR-022 (the ADR is the only
recurrence-acting item), FR-023 (one glossary entry), FR-026 (deleting a **false**
correctness argument from source prose — cheap, and dangerous if left), C-010/SC-024 (the
autouse-fixture trap is real and would have produced a green fake).

## Lens: debugger-debbie — round 2 — VERDICT ACCEPT-WITH-CHANGES (no BLOCKER survives)

Control-your-diagnostic honoured: re-ran both guard predicates against **2 control shapes
whose answers were already known** before probing the 5 new shapes. Own-findings audit:
**10 of 13 structurally closed, 3 PARTIAL for measured reasons, 0 merely reworded.**

**Honest correction from the lens itself:** the "13 of 29" no-op figure was an *aggregate
across four lenses*, not this lens's own. Its defensible measure: over the 24 Success
Criteria, **6 satisfiable by literal no-op, of which 4 are declared** → **2 undeclared**
(SC-017, SC-021), plus **1 unsatisfiable even by a correct implementation** (SC-013).
Previous draft carried ~12 undeclared. **~12 → 2.**

### CONVERGENT with renata (both lenses, independently — treated as settled)

- **SC-013 is inverted** (renata N-3 / debbie P-1). Measured:
  `mod.SaasClient(project_root=r)` → SaaS guard **NOT-MATCHED**, by design per FR-016.
  SC-013 requires it to match. *"An implementer writing this test gets a red whose only
  repair is widening the SaaS predicate — the silent direction FR-015/FR-016 exist to
  forbid."* **The criterion instructs the very defect it was added to prevent.**
  Debbie supplies the correct shape: the unused-but-matching one is the **tracker's**
  `mod.SaaSTrackerClient(project_root=…)` → **matched/attributed**, which is exactly what
  unifying on the SaaS predicate would blind.
- **SC-017 is vacuous over an empty set** (renata N-6 / debbie P-2). *"The spec caught and
  fixed this exact shape for NFR-005/SC-009 and did not carry the fix across."*
- **FR-027 mislabelled `[build]`/High; already true** (renata N-8 / debbie). Existing
  coverage at `tests/sync/tracker/test_saas_client_consent_gate_3030.py:267,279,283`.
- **FR-021 discharge (ii) makes SC-018 unsatisfiable** (renata N-4 / debbie).
- **SC-019/SC-020 are grep-gates whose content half is unenforceable** (renata N-10 / debbie).

### DB-1 [HIGH] SC-002's compatibility clause is incomplete in a way whose REPAIR reinstates the leak — **CONFIRMED; broader than renata's N-1 and subsumes it**

The design silently substitutes *"this checkout's committed `kitty-specs/*/decisions/index.json`
lists the decision"* for *"the server knows this decision"*. **Those are not the same set.**

At `bb2020fea` `cmd_widen` reads **no** ledger (`cli/commands/decision.py:523-572`), so
**every ULID the server accepts succeeds today.** After FR-001/FR-002 these
currently-succeeding invocations become refusals with zero requests:

- (a) a decision recorded on another machine/branch, pushed but **not yet pulled** here
- (b) a **lane worktree** cut before the ledger entry landed
- (c) any checkout where `kitty-specs/` is filtered or cleaned

**The danger is not the break — it is the repair.** An implementer meeting this mid-flight
has an SC-002 red whose obvious fix is *"fall through to the acting root when the ledger
doesn't list it"* — **which reinstates exactly the leak this mission closes.**

**Resolution:** name the **ledger-completeness assumption** explicitly in SC-002; state
whether a stale/absent entry refuses (with the operator action: `git pull`); and decide now
whether a malformed index in one mission fails the whole search or is skipped (renata N-1's
scoping rule). **Do not leave this to be discovered as an SC-002 failure.**

### DB-2 [MEDIUM] SC-001's rationale names two short-circuits; there is a THIRD — **CONFIRMED**

`SaasClient.from_env` → `load_auth_context` raises `SaasAuthError` when no token resolves
(`saas_client/auth.py:66-69`); `SaasAuthError` subclasses `SaasClientError`
(`errors.py:12,24`), which `cmd_widen` catches (`decision.py:570`).

⇒ **An unauthenticated fixture also produces zero outbound requests at `bb2020fea`** —
SC-001 green with no production change. What discriminates it is **SC-002's shared-fixture
positive control**, not any clause of SC-001.

**Resolution:** add the auth short-circuit to SC-001's "why every clause is load-bearing"
list, and state that SC-002 is what closes it — so the red-first order (SC-001 first) is not
mistaken for evidence.

### DB-3 [MEDIUM] FR-007's stated ground is wrong, and FU-4 contradicts it in the same document — **CONFIRMED; corrects MY Decision D-3's reasoning**

FR-007 says re-resolve "is unimplementable under C-009". **C-009 is about the missing
`decision_id`→project *mapping*. What actually blocks re-resolve is the absence of a
*checkout enumeration*** — a different, **buildable** thing. Measured: `checkout_roots` has
exactly two callers, both building a **one-element** list from `locate_project_root(cwd)`
(`delivery/selection.py:103-111`, `sync/background.py:255-278`), and grep for any
machine-level checkout/project enumeration in `src/specify_cli/` returns **zero**.

And the spec's own **FU-4** row concedes it: a cross-checkout search "would enable naming the
actual owning project (making … FR-007's re-resolve shape **expressible**)."

**Adjudication: my D-3 conclusion stands** (re-resolve is correctly deleted — it would need a
whole new subsystem) **but my stated ground was imprecise.** Restate as: *"not expressible
under Decision D-2's within-checkout design; the cross-checkout search that would express it
is deferred to FU-4 under C-011."* A decision recorded on a false ground invites
re-litigation the moment a successor notices.

### DB-4 [MEDIUM] SC-012's SaaS half has no witness; a concrete one exists — **CONFIRMED**

Tracker accepts exactly `{project_root=}`, which the SaaS guard already accepts for direct
construction — so "not widened to admit tracker-only spellings" is **vacuously true**.
Measured, the real witness is on `from_env`: **`SaasClient.from_env(project_root=r)` →
matched / FLAGGED-unattributed today** (`from_env` accepts only positional or `repo_root=`).
That is the assertion that bites if the SaaS vocabulary is widened.

### DB-5 [MEDIUM] SC-014 does not exercise the divergence that justifies NFR-006 — **CONFIRMED**

SC-014 runs the touched files under 3.11 and quotes `N passed`, but **nothing requires a test
that constructs a permission-denied ledger** — so the `Path.exists()`/EACCES branch (PL-1,
measured live) is exercised by no required test on either interpreter. *"A green 3.11 run over
tests that never touch the branch is a true statement about nothing."*

**Resolution:** require one test that makes a searched mission's `decisions/index.json`
unreadable (mode `0o000`) and asserts the refusal, and **name it as a file SC-014's 3.11 run
must include.**

### D-4's replacement independently verified

The export half is genuinely unpinned: `invocation/adapters.py` has **zero** `__all__`
declarations; `grep "from specify_cli.invocation import" src/` → **zero** hits;
`test_all_declarations_required.py:1-20` gates only `src/charter/` and `src/kernel/`.
**The before-state is real.**

### Debbie's over-correction cuts

1. **SC-001's "100% of the four divergence routes"** — FR-006 itself concedes three
   "converge in `locate_project_root` and hold by construction". *Three parameterisations of
   one code path is not three pieces of evidence.* Keep the `--mission-slug` route (genuinely
   new) + one root route; state the rest as held-by-construction with the convergence named.
2. **FR-023/SC-020** conditional on Q2 — **NOW MOOT**: Q2 resolved keeping "engagement" in the
   tracker fragment, so FR-023 stands.
3. **FR-027 at `[build]`/High** — a ratchet wearing build clothing.

**Explicitly earns its length:** the falsifier blocks, the `[build]`/`[ratchet]` labels, the
FR→SC coverage table, and **SC-023's negative control** (the sibling docstring on
`register_egress_consent_resolver` must stay **unchanged**) — *"the only new criterion that
ships its own positive-and-negative pair."*

---

# §1-R2b — REMEDIATION ROUND 2 OUTCOME, AND CORRECTIONS TO THIS FILE

Spec **1001 → 1444 lines (+443)**. All round-2 HIGH/MEDIUM findings actioned; four rows cut
(FR-007 folded, FR-025/SC-017 retired, SC-013's SaaS half deleted, NFR-001 folded into
NFR-003). A "Retired identifiers" table was added so the ID gaps read as deliberate.

## CORRECTION — `decisions/store.py` line numbers were wrong in BOTH lenses' notes AND in my PL-1

**Verified by me directly at HEAD:**

```
61: def load_index(mission_dir: Path) -> DecisionIndex:
64:     if not path.exists():
66:     raw = json.loads(path.read_text(encoding="utf-8"))
67:     return DecisionIndex.model_validate(raw)
```

- My **PL-1** recorded `decisions/store.py:63` for `path.exists()`. **It is `:64`.**
- Both lenses cited `:58-64` for `load_index`; **`:58` is a comment banner**, the function
  begins at `:61`.
- The membership shape is `:115-120`, not `:112-120`.

**No conclusion changes.** The behavioural claim both lenses rested on is confirmed by the
function's own docstring and body: **missing → empty index; malformed → raises**
(`json.loads` → `JSONDecodeError`, `model_validate` → `ValidationError`). The rot-mode-4
finding (PL-1) stands unchanged in substance — only the anchor moves.

Recorded because round 3 will see corrected anchors that differ from the reviewers' own
notes, and an unexplained mismatch would look like drift.

## MY RULING on the one item the remediation flagged for an operator decision

**The claim:** FR-016's coverage is now one-sided — SC-013 covers the tracker class, while
the SaaS class's preserved property (a **non-match** on `mod.SaasClient(...)`) was routed to
"verified by inspection at plan review". The agent judged that asserting an absence is "the
vacuity shape this spec forbids elsewhere" and said it may need an operator ruling.

**Ruling: it does not need one, and inspection-at-plan-review is the wrong disposition.
Assert it.**

The spec's own standing rule is *"any assertion of absence must establish why the thing
would otherwise have happened."* That test is **met here, and unusually cleanly**:

- The witness exists — the AST shape `mod.SaasClient(project_root=…)` is constructible and
  is constructed in the test.
- The counterfactual is established and **already measured**: widening the SaaS predicate to
  `getattr(func, "attr")` — the known silent direction FR-015/FR-016 exist to forbid — makes
  it match. That is not hypothetical; it is Mechanism 3.

So a test asserting `_classify(mod.SaasClient(...)) is not matched` **reds precisely when
someone takes the silent-widening direction.** That is a discriminating pin, not a vacuous
one. The vacuity concern would apply only if no shape could ever have matched.

**Action for round 3:** SC-013 must carry the SaaS-side **non-match assertion** as a test,
not as a plan-review inspection item. This also removes the blank-cell shape a reviewer would
otherwise fairly flag.

## Remediation pushbacks I ACCEPT without further action

- **N-2's "asymmetric by 15 kinds" does not reproduce** — the spec's own table gives 4 SaaS
  kinds vs 12 tracker kinds with one overlap = 14. The figure stays attributed to the lens,
  and the spec now carries the **checkable** form instead: **`mission_id` is the only shared
  member.** Better than the count either way.
- **Two Q1-table cells were measured false in §2 and had not been folded into the spec** —
  PL-2 (option (d) is *not* "the only candidate that preserves FR-013") and PL-3 (option (f)
  is *not* "already classified" — that conflates the dorny group with `INTEGRATION_PREFIXES`).
  **Both were arguments FOR the option that won**, so leaving them made the Q1 decision look
  better supported than it is. Corrected in place; **FU-7** filed. Good catch — this is the
  failure mode where a decision survives on retracted evidence.
- **Q8 closed** with a defensible rule: *any property that could regress later is a standing
  gate; any mutation demonstration is one-off PR evidence.* Rationale accepted — preserving a
  mutation demo as a standing synthetic-corpus harness buys a second copy of the guard that
  can drift (green harness, blind guard).
- **NFR-001 folded into NFR-003**, keeping the *lower* bound as the survivor because that is
  the change-forcing half; NFR-001 disclaimed itself ("not a proof about egress surface"), so
  keeping the self-disclaiming row would have left the load-bearing property carried by a row
  that denies it. Correct call.

## Open tension carried into round 3 (flagged by the remediation itself)

- **Rot-mode-5 protection is weaker under Q2 than before.** Because the two DENIED strings
  are now *supposed* to differ, SC-004's string comparison no longer corroborates the
  per-site-split clause — the split does the work alone. The belt-and-braces alternative is
  exactly the standalone row the cut list ordered deleted. **Round 3 should rule.**
- **Growth is +44% in a round themed on over-correction.** If round 3 flags length, the
  remediation names the cheapest cuts: the Q8 per-criterion table (redundant with the
  per-criterion tags) and the edge-case block's restatement of the `store.py` measurement
  (duplicated in SC-014).

---

# §1-R3 — SPEC REVIEW ROUND 3 (FINAL ROUND)

## Lens: reviewer-renata — VERDICT ACCEPT-WITH-CHANGES — **Findings above MEDIUM: 0**

**Own-findings audit: 20 RESOLVED, 1 PARTIAL (MEDIUM), 0 NOT RESOLVED, 1 N/A.**

### The convergence measurement

Undeclared no-ops, measured the same way each round:

| Round | Undeclared no-ops | Total items |
|---|---|---|
| 1 | **13** | 29 (45%) |
| 2 | **10** | 57 (18%) |
| 3 | **3** | 53 (**6%**) |

The lens's judgement: *"the clearest evidence the remediation is converging rather than
churning."*

### MY RULING WAS RIGHT IN OUTCOME AND WRONG IN GROUND — corrected

I ruled that the SaaS-class non-match must be asserted as a test, on the ground that
widening the predicate is "the silent direction FR-015/FR-016 exist to forbid".

**Measured, control run first (937 files):** applying the tracker's looser
`getattr(func, "attr", None)` predicate to the SaaS class gives **`scanned=4, flagged=0` —
identical to today's strict predicate.**

> **Widening a *match* predicate is monotone in coverage: it can only scan more sites, never
> hide one.**

⇒ **The SaaS non-match property is NOT safety-bearing.** My stated ground was wrong.

The genuinely silent-and-harmful directions are (a) widening the **attribution vocabulary**
(FR-015 — now asserted by SC-012 with the `from_env(project_root=r)` witness), and (b)
applying the **stricter** predicate to the **tracker** (SC-013's tracker half). **Both are
already covered.**

**Corrected ground, which must be carried:** assert the non-match to **pin a deliberate
asymmetry so a future unification is a visible decision** — *not* to guard a silent coverage
loss. The lens is explicit about why this matters: *"carrying the wrong ground into the plan
would invite a successor to 'fix' FR-016 by widening the predicate — the same shape of error
that made round-1's SC-013 instruct the defect it forbade."*

**Adjudication: I accept the correction in full.** The one-line assertion still goes in (it
closes the sentence-in-a-cell for the cost of one `assert not matched`), but the *reason*
changes. **MEDIUM, and the lens explicitly declined to inflate it** — correct discipline.

### RM-1 [MEDIUM] SC-004 clause 3 has a provenance gap that text cannot close — **CONFIRMED, and it answers my Part-3 question**

My framing was right: under Q2 the two DENIED strings are *supposed* to differ, so clause 1
no longer corroborates clause 3. **But clause 3 is weaker than it appears.** It requires the
per-site **rendered string** at three binding sites — and *a surviving
`tracker/egress_consent.py` re-export renders the **identical correct string** as the fresh
path.* So three separate correct observations is **exactly what both a correct consolidation
and a stale re-export produce.** Clause 3 detects nothing in that case. SC-015 does not close
it either — a re-export is not "a second definition".

**Ruling: do NOT restore the retired standalone row** — it was a vacuously-satisfiable
conditional and the cut was right. **Assert provenance, not text:**
`saas_client.client.project_egress_refusal.__module__` and
`tracker.saas_client.project_egress_refusal.__module__` **both equal the shared module's
name.** One line, mechanical, and the only signal Q2 leaves available. It also makes FR-008's
"exactly one editable presentation" behaviourally checkable rather than a source scan.

**MEDIUM, not HIGH:** the failure is latent — no operator-visible defect ships, and under Q2
there is no in-mission string edit for a stale binding to miss. The risk is post-mission
drift, which is the baseline risk today.

### RM-2 [MEDIUM] The corrected `store.py` anchors were not propagated — the four-copies problem caught in the act

`spec.md:403` (FR-001) and `:521` (Decision D-2) still cite `store.py:46,58-64` and
`:112-120`, while the edge case at `:316-318` explicitly corrects exactly those. **The spec
now contradicts itself, and the stale copy is in the requirement row an implementer reads to
build the thing — pointing at a comment banner.** (`:46` for `index_path` is correct; the
membership shape is `:115-118`.)

### RM-3 [LOW] The lane-worktree break is over-enumerated

`locate_project_root` returns the **main** repo root even when invoked from a worktree
(`core/paths.py:184-186`, and its docstring says so). So FR-001's glob reads the main
checkout's `kitty-specs/`, and "a lane worktree cut before the ledger entry landed" collapses
into "pushed but not yet pulled here". Harmless — errs toward naming more breaks than exist,
which is the safe direction.

### IMPLEMENTABILITY — the judgement I asked for

> *"It is implementable, but only by accident of structure, and the spec should say so."*

- **Operative content is ~470 lines** in three contiguous, genuinely self-contained blocks:
  Edge Cases (`:298-383`), Success Criteria (`:1075-1381`), coverage table (`:1383-1444`).
  Every criterion carries its own anti-vacuity clause, measurement, and `[standing]`/`[one-off]`
  tag. **An implementer working from those 470 lines would build the right thing.**
- **The other ~970 lines are justification** — Requirements tables with 8–11-line prose cells
  crammed into markdown cells, plus Falsifiers. That material earns its place at *review*, not
  at *implementation*.
- **Nothing tells the reader which is which.** Honest prediction: *"an implementer opens 1444
  lines, skims, and works from the Requirements table — the worst of the three surfaces to
  work from."*

**Cheapest fix in the document: one sentence near the top.**

### DUPLICATION AUDIT — four contents, each appearing 3–4 times

| Duplicated content | Copies | Keep |
|---|---|---|
| `store.py` missing-vs-malformed measurement | **4** (`:312-340`, `:1128-1134`, `:440`, `:1265-1277`) | Edge cases |
| `mod.SaasClient(...)` non-match reasoning | **4** (`:418`, `:1254-1261`, `:32`, `:1408`) | SC-013 |
| rot-mode-5 by-value binding hazard | **4** (`:373-382`, `:427`, `:1166-1174`, `:29-30`) | SC-004 |
| C-005's "no gate notices a forgotten classification" | **3** (`:450`, `:362-368`, `:1369-1378`) | SC-025 |

Plus the two the remediation named (Q8's per-criterion table; the edge-case restatement).
**~120–150 lines recoverable with zero information loss** — and, more valuably, removing the
risk that a future edit updates one copy and not the other three. **That risk already
materialised once in this document** (RM-2).

### Conceded as genuine quality, not ceremony

The `[build]`/`[ratchet]`/`folded` labels, the FR→SC coverage table **with its own defect
rule**, the Retired-identifiers table, and **SC-023's positive-and-negative pair**.
*"The most rigorously self-auditing specification I have reviewed in this mission — its
remaining problem is length and four-fold duplication, not correctness."*

## Lens: debugger-debbie — round 3 — VERDICT ACCEPT-WITH-CHANGES — **Findings above MEDIUM: 2 (both HIGH)**

6 known-answer controls run first, all as expected. Undeclared no-ops **2 → 1**;
unsatisfiable criteria **1 → 0**. But two criteria "manufacture false greens by measurement,
not by argument, and both are in the *would this catch the regression?* core."

### DIVERGENCE BETWEEN LENSES — adjudicated, not averaged

`reviewer-renata` reported **0 above MEDIUM**; `debugger-debbie` reports **2 HIGH**. Per the
squad recipe I adjudicated from source rather than splitting the difference.

- **SC-014**: renata marked R-15 RESOLVED on the *presence* of the requirement. debbie went a
  level deeper and tested whether the mandated **test shape** can reach the branch. Not a
  disagreement — debbie measured something renata did not examine. **HIGH stands.**
- **SC-004**: renata flagged the same area (RM-1) at **MEDIUM** ("the failure is latent").
  debbie rates **HIGH** because clauses 1 *and* 2 are **also** no-ops, so the whole criterion
  has nothing that reds. debbie's measurement is the stronger evidence. **HIGH stands.**
- Both lenses converge on the **fix**: assert provenance/binding identity, not text.

### HIGH-1 — SC-014's mandated test cannot reach the EACCES branch — **CONFIRMED BY MY OWN MEASUREMENT**

`stat(2)` needs **search permission on the parent**, not read permission on the file — POSIX,
not interpreter-dependent. I re-ran it myself (uid 1000, Python 3.14.4):

```
CASE A  file=0o000  (the shape SC-014 mandates)
          Path.exists() -> True      ; PermissionError(13) arrives later, from read_text()
CASE B  dir=0o000   (the shape the lens prescribes)
          Path.exists() -> False     ; <-- the swallow-EACCES branch
```

⇒ The mandated shape yields the **same result on 3.11 and 3.14**, while SC-014 instructs:
*"Expect this test to behave differently on the two interpreters… which is the point."*
When it behaves identically the honest reading is *"no divergence, NFR-006 discharged"* —
**a false negative in the mission's only portability gate, produced by a claim the spec
presents as measured.**

**Fix:** chmod the containing `decisions/` **directory** to `0o000` (keep the file readable);
restate the expectation as `Path.exists()` returns `False` on 3.12+ and raises
`PermissionError` on 3.11, at `decisions/store.py:64`. Optionally keep the `0o000`-file case,
labelled as exercising `read_text` → `PermissionError` at `:66` and **not** the
version-divergent path.

### HIGH-2 — SC-004 has no clause that reds — **CONFIRMED**

Measured: the two `DENIED` strings are four-part concatenations differing in **exactly one
word** (`saas_client/egress_consent.py:125-130` vs `tracker/egress_consent.py:187-192`);
everything else byte-identical.

- **Clause 1** ("non-fragment portion is byte-identical") — **already true today.**
- **Clause 2** ("both current DENIED strings survive verbatim") — **true of the
  unconsolidated state by construction**; the strings that must survive are the ones that exist.
- **Clause 3** — asks the split be "named separately in the evidence": a **reporting
  instruction**, not an assertion. Nothing reds.

SC-004 is presented as asserting three things and asserts **none that discriminate** — and it
is the criterion that *absorbed retired SC-017 to cure a vacuity finding*. It is vacuous by a
different route. Knock-on: FR-009's only criterion is a no-op while FR-009 is still labelled
`[build]` and is absent from the `[ratchet]` audit.

**Fix:** convert clause 3 into a standing **binding-identity assertion** —
`saas_client.client.project_egress_refusal is egress.project_egress_refusal`, same for
`tracker.saas_client` — and relabel FR-009 `[ratchet]`.

### MY RULING ON THE SaaS NON-MATCH — OVERTURNED ON DIRECTION, and this is the deeper correction

renata corrected my *ground*; debbie corrects the **shape**, with measurement:

- `mod.SaasClient(project_root=r)`: today `False`, under a widened predicate `True`. True —
  **but that direction is not Mechanism 3's defect.** Mechanism 3 is unifying in the direction
  that **loses** sight of shapes. **The SaaS predicate is already the stricter of the two**, so
  unifying can only *loosen* it → the guard sees **more** constructions → a coverage **gain**.
- Pinning it as must-not-match would (a) **red on a change that improves coverage**, and
  (b) **directly collide with FU-8**, which the spec files in the same paragraph precisely
  because `mod.SaasClient.from_env(x)` is unguarded on both and *"closing it means widening a
  predicate"*. **A non-match pin cements the hole FU-8 exists to close.**
- **The correct analogue exists and nobody proposed it:** `SaasClient(project_root=r)` — bare
  direct construction — is **matched/attributed today**, and the corpus is `direct=0,
  from_env=4`. So it is an **unused-but-matching** shape for the SaaS class, exactly parallel
  to the tracker's attribute-receiver shape, and a unification collapsing onto the `from_env`
  form drops it **silently with no count moving**.

**Adjudication: I accept the overturn in full.** My instinct that a blank cell was
unacceptable was right; **the shape I ordered was wrong and would have been actively
harmful.** SC-013 should carry **two per-class match assertions** — tracker
`mod.SaaSTrackerClient(project_root=…)`, SaaS `SaasClient(project_root=…)` — and the
non-match proposal is dropped entirely.

### Rot-mode 5, ruled by splitting the hazard (both arms, corrected framing)

- **Production arm** (a partial consolidation leaves a second live definition): **already
  doubly covered, and not by SC-004** — SC-015 reds if a second definition appears; SC-016
  pins the merged `DENIED` wording by content in **both** trees. **Sufficient. Restoring the
  deleted row would buy a third copy of a property already pinned twice.**
- **Verification arm** (what rot-mode 5 actually *is*): a future mutation patching
  `egress.project_egress_refusal` leaves **both** `client.py:157` and
  `tracker/saas_client.py:329` calling the original object. **Nothing in the spec reds on
  this.** Clause 3 asks the author to report a split — *"which only helps an author who
  already knows to look."* **Insufficient.**

**Ruling: the second mechanism returns as binding identity, not as the deleted row and not as
a string comparison.** Three `is` comparisons, standing, zero cost — and decisively, once
identity is pinned, *any* future patch of the shared module **provably** reaches both decision
points, which is the property the friction rule was written to obtain. **Strictly stronger
than the string comparison Q2 removed.**

### Also raised

- **[MEDIUM] SC-002 clause (c) is a two-sided rule with a one-sided criterion.** SC-014 covers
  the *refuse* half; **nothing asserts the must-not-veto half**, so an implementation that
  refuses on *any* unreadable index passes every criterion while breaking widen invocations
  that succeed today because of one corrupt `index.json` in an unrelated mission. It is also
  the one fall-through variant **SC-001 does not catch**.
- **[LOW]** Growth **not** flagged as a defect this round: *"the added mass is SC-025, the
  SC-002 clause structure and the corrected D-3 grounds — all load-bearing."* (renata takes the
  opposite view on length; both agree the named cuts are worth taking.)
- **DB-1's prohibition verified BINDING, not narrated**: the broad fall-through makes SC-001
  red (a request *is* constructed from consenting A for B's ULID), so an implementer taking it
  cannot reach green. Only the **narrow** variant escapes — which is the MEDIUM above.

---

# ESCALATION GATE TRIPPED

**Three review rounds completed on the spec. 2 HIGH findings still stand.** Per the operator's
rule: *halt and escalate with a multiple-choice question; do not attempt a fourth round, and do
not lower a severity to clear the gate.*

Both HIGHs are confirmed (HIGH-1 by my own independent measurement), both have an agreed fix
from both lenses, and neither requires a design decision. **Escalated to the operator.**

## ESCALATION OUTCOME — operator decision, 2026-07-31

**Operator chose: apply both fixes, accept the spec, continue to the plan phase — with no
fourth review round.**

**Risk the operator explicitly accepted, and which must be carried into the handoff:**
**the closing fixes themselves are unreviewed.** Everything up to round 3 was
adversarially reviewed; the edits that closed round 3's two HIGH findings were not. A
successor should treat SC-014's corrected chmod shape and SC-004's binding-identity clause
as the least-scrutinised text in the document.

### Fixes authorised and applied

| # | Finding | Fix |
|---|---|---|
| HIGH-1 | SC-014 cannot reach the EACCES branch | chmod the containing `decisions/` **directory** to `0o000` (not the file); expectation restated as `exists()` → `False` on 3.12+, raises on 3.11, at `store.py:64` |
| HIGH-2 | SC-004 has no clause that reds | clause 3 becomes a standing **binding-identity** assertion across the three names; clauses 1–2 relabelled `[ratchet]`; FR-009 relabelled `[ratchet]` |
| 3 | SC-013's SaaS half | **two per-class MATCH assertions**; the orchestrator's non-match ruling **withdrawn entirely** |
| 4 | SC-002 clause (c) one-sided | add the **must-not-veto** case: unreadable ledger in X + positive hit in Y → normal single request |
| 5 | Stale `store.py` anchors | propagate corrected anchors to FR-001 and Decision D-2 |
| 6 | Lane-worktree case over-enumerated | merge; note `locate_project_root` returns the **main** root even from a worktree |
| — | Four-fold duplication | cut to one canonical home each + delete the Q8 per-criterion table |
| — | Implementability | add a "How to use this document" note: implementers work from **Edge Cases + Success Criteria + coverage table** (~470 self-contained lines); Requirements/Falsifiers are the review-time justification record |

### FINAL ROUND LEDGER — spec artifact

| Round | Reviewers | Verdict | Above MEDIUM |
|---|---|---|---|
| 1 | 4 lenses (paula, renata, debbie, alphonso) | REJECT | 2 CRITICAL, 3 BLOCKER, 17 HIGH |
| 2 | renata + debbie | ACCEPT-WITH-CHANGES | 0 BLOCKER; several HIGH |
| 3 | renata + debbie | ACCEPT-WITH-CHANGES | renata **0**; debbie **2 HIGH** → **gate tripped** |
| — | *operator decision* | **ACCEPTED** | both HIGH closed by authorised unreviewed edits |

**Convergence measured across rounds (undeclared no-ops):** 45% → 18% → 6%.
**Unsatisfiable criteria:** 1 → 0.

### THREE ORCHESTRATOR RULINGS OVERTURNED BY MEASUREMENT — carried so they are not re-proposed

1. **The SaaS non-match pin.** I ordered it; measurement showed the SaaS predicate is already
   the **stricter** of the two, so widening it is a coverage **gain**, not Mechanism 3's loss
   direction. My pin would have **red-flagged an improvement** and **cemented the hole FU-8
   exists to close.** Withdrawn; replaced by a per-class **match** assertion on
   `SaasClient(project_root=…)` (`direct=0` in a corpus of 4 — genuinely unused-but-matching).
2. **Q6's fallback** ("one guard per package in its existing tree makes routing hold by
   construction") — I called it likely right in round 1. **Two lenses measured the premise
   false**; the existing arrangement is the broken one. Struck.
3. **Decision D-3's stated ground** ("re-resolve is unimplementable under C-009"). The
   conclusion stands; the ground was wrong — C-009 is about the missing *mapping*, whereas
   what blocks re-resolve is the absence of a *checkout enumeration*, a different and
   **buildable** thing. Restated in all four places it appears.

## CLOSING-FIX OUTCOME + orchestrator rulings on the applier's seven pushbacks

Spec **1444 → 1571 (+127)**. All eight authorised items applied.

### PB-4 [the important one] — the 3.11 expectation was extrapolated. NOW MEASURED ON BOTH INTERPRETERS.

The applier flagged that "raises `PermissionError` on 3.11" for the **directory** shape was
inferred from PL-1's earlier **file**-shape measurement — *"the exact failure mode HIGH-1 was
raised about."* **Correct, and I measured it rather than let it stand.**

`uv venv --python 3.11` (CPython 3.11.15) and system 3.14.4, uid 1000, **control run first**:

```
                        3.11.15                     3.14.4
CONTROL readable    ->  True                        True          (diagnostic valid)
CASE A file=0o000   ->  True                        True          <- NO divergence
CASE B dir=0o000    ->  PermissionError(13)         False         <- THE BRANCH
```

**Both halves of SC-014's expectation are now measured, on both interpreters.** CASE A's
identical result on both independently re-confirms HIGH-1: the previously-mandated file shape
could not have detected anything. Update SC-014's provenance note from *extrapolated* to
*measured*.

### PB-3 [real finding] — FR-009's ratchet claim. **RULING: scope the bar to the project's own identifiers.**

The applier is right that "every identifier kind the transport can transmit is named" is not
obviously already-true: `saas_client`'s string says "mission and decision identifiers" while
its Key-Entities set also lists `team_slug` and `invited_user_ids`.

**Ruling:** FR-009's bar covers **the identifiers of the project whose consent was refused** —
the confidential content this mission exists to protect. It does **not** cover every field in
the request. `team_slug` is the **destination** (the team the request would be addressed to,
not the refusing project's identity); `invited_user_ids` are **recipient** ids and are ints.
Neither is an identifier *of the project being refused*.

Under that scoping FR-009 is genuinely a `[ratchet]` and the applier's relabel is correct.
**The scoping must be written into FR-009** so a successor does not re-open it — and so
nobody "fixes" the refusal string by appending the destination team's name to it, which would
*add* an identifier to an operator-facing message rather than remove one.

### PB-5 — two vs three `is` comparisons. **RULING: conditional on the plan's shim decision.**

The rot-mode-5 ruling said "three"; the authorised fix listed two, and two were implemented.
The third would be `egress.project_egress_refusal is tracker.egress_consent.project_egress_refusal`
— pinning the **re-export shim itself**.

**Whether it is required depends on a plan-phase decision not yet taken: do the two
`*/egress_consent.py` modules survive as re-export shims, or are they deleted?**
- **Deleted** → two assertions are complete.
- **Surviving as shims** → the third is **required**, because a stale shim is precisely the
  collapse route round 3 identified (a re-export renders the identical correct string).

**Carried as a binding plan-phase item.**

### PB-1, PB-2, PB-6 — accepted as recorded residuals

- **PB-1 — the document got longer, not shorter.** Cuts recovered ~55 lines; the two HIGH
  fixes plus SC-002(c) added ~180. **The length goal was not met**; the navigation note is
  doing that work alone. Recorded honestly rather than claimed as achieved.
- **PB-2 — `[ratchet]` has a doctrinal edge.** Three rows are now `[ratchet]` *and* carry a
  criterion that must still be authored, which strains the legend's "nothing has to be
  written". Reconciled by extending the legend and citing the NFR-004/FR-027 precedent.
  Acceptable; noted.
- **PB-6 — a fourth copy of C-005's content** survives in the C-005 falsifier block; the audit
  named only three sites. Left in place per "do not restructure anything not listed". MEDIUM-
  or-below residual.

### PB-7 — no defect, and it re-confirms a load-bearing baseline

The applier independently replicated the guard's AST predicate: **`scanned=4, direct=0`, all
four `from_env`.** A grep suggested a fifth site at `saas_client/__init__.py:28` — **it is
inside a module docstring**, so the floor of 4 stands and A-2's "zero of the four live under
`saas_client/**`" stands. **Fifth independent reproduction of the 4/3 baseline.**

---

# §3 — PLAN RECONCILIATION AND ORCHESTRATOR RULINGS

Plan **517 → 672 lines**, reconciled against the ACCEPTED spec. Measurements re-run in-clone
with a control and printed input counts. Two contradictions surfaced; neither was papered over.

## PB-5 DECIDED by the plan — both `*/egress_consent.py` modules are **DELETED**, not shimmed

**Ground, and it is a good one:** the accepted spec carries **exactly two** `is` comparisons.
Choosing "shims survive" would oblige a **third** assertion the spec does not carry — and an
implementer working from the three operative blocks *as the spec instructs* would never write
it, leaving the shim hazard **known and unguarded**. **Deletion is the choice that leaves the
accepted spec sufficient.**

C-004 does not force survival: the rebound import at `tracker/saas_client.py:34` satisfies the
substring gate on its own (this is finding A-5 paying off — the gate protects the *text*, not
the call).

**Falsifier F3 (measured, re-runnable):** deletion is falsified if any importer exists outside
the four measured sites, or if either module path appears in an architectural allowlist.
Measured: importers are exactly `saas_client/client.py:23`, `tracker/saas_client.py:34`, and
two in-test imports (`test_client_consent_gate_3030.py:371`,
`test_saas_client_consent_gate_3030.py:413`) — **all already touched by this mission**; `grep`
over `tests/architectural/` for either path returns **zero** (`_baselines.yaml` keys the
*boundary guard*, not these source files). **If F3 fires → keep both as pure re-exports and add
the third comparison.**

## ORCHESTRATOR RULING D-7 — the ownership derivation lives in `decisions/ownership.py`, NOT `egress/`

**The contradiction:** the spec's FR-020 cell said *"Under the resolved Q1 its home is
`src/specify_cli/egress/`"*; the plan places it at `src/specify_cli/decisions/ownership.py`.

**Ruling: the plan is right and the spec's sentence was the error.** Corrected in place as a
recorded post-acceptance correction. Three grounds, descending:

1. **It would break the premise `egress/` rests on.** The ownership derivation reads the
   decision ledger, so placing it in `egress/` gives the deliberately-transport-neutral package
   a real dependency on `specify_cli.decisions.store`. **That neutrality is the basis on which
   Q2's falsifier F2 does not fire and the Q1 placement stands.** Keeping the old text would
   have falsified the very decision it was written to support.
2. **The operative criterion never said otherwise.** **SC-018 names no package** — single named
   function, stated module, outside `cli/commands/**`, importable by a non-CLI caller.
   `decisions/ownership.py` satisfies every clause. Per the spec's own *How to use this
   document*, SC-018 is the implementation surface and the Requirements table is the
   justification record; **where they disagreed, the table was the stale side.**
3. **Cohesion** — the ledger lives in `specify_cli/decisions/`; the derivation that reads it
   belongs beside it.

**This is reviewer finding P-2's conflation reappearing inside the fix for P-2**: Q1 answered
*"where does the refusal **wrapper** live"* and the sentence silently applied that answer to
*"where does the **ownership derivation** live"*. Worth recording as a pattern — a resolved
question's answer migrating onto a different question.

## Collateral of PB-5, recorded so it is not misread as a defect

**SC-022's anchor moves.** It cites the per-site enumeration at
`saas_client/egress_consent.py:52-76`; under PB-5 that file is deleted, so the enumeration
relocates to the shared module. **Substance preserved, anchor moves.** A reviewer must not read
SC-022 as unsatisfiable, and **the PR body must say so**. This is the one cost of deletion the
spec did not anticipate.

## Plan-phase corrections to its own earlier work

- **MUT-2 was WRONG under Q2 and was restated.** It mutated the wrapper to restore "engagement
  identifiers" — but under Q2 that **is** the correct tracker state, so the mutant could red
  nothing. Restated as a **stale-binding** mutation that reds SC-004 clause 3 while **every
  string observation stays green** — which is precisely rot-mode 5's signature. **New MUT-6**
  added for SC-013's SaaS half.
- **SC-006 gains a required real CI observation** (Q8's `[standing]`/`[one-off]` split), which
  also discharges Decision D-4's long-standing unverified premise.
- **SC-025 downgraded honestly:** it gates the `INTEGRATION_PREFIXES` half; the `core_misc`
  glob half stays **ungated**.

## THE MISSION'S ONLY UNENFORCED OBLIGATION — carried, named, and flagged

**Nothing gates the `core_misc` glob edit.** SC-025 closed the `INTEGRATION_PREFIXES` half.
If the glob line is forgotten, `egress/` matches no named group → `unmatched → run_all` → **every
future PR touching `egress/` runs the entire suite, forever**, and no gate says why.

It is procedural by necessity (the LOC-gated detector needs `T_LOC = 500`; the module is
~150–250 lines — finding D-8). **Named here, in the plan, and required in the handoff.**

## Standing exposure from the operator-accepted risk

The plan states it plainly: **SC-014's chmod shape and SC-004's identity clause are the
least-reviewed text in the spec.** The plan **independently re-executed SC-014's measurement**,
halving that exposure. **SC-004 clause 3 remains unreviewed — and it is the only clause in that
criterion that reds.** Plan review round 1 was briefed to attack it specifically.

---

# §3-R1 — PLAN REVIEW ROUND 1

## Lens: debugger-debbie — VERDICT CHANGES REQUESTED — **Findings above MEDIUM: 2 (both HIGH)**

Both are **new findings on the plan**, not carry-overs. **Both spec HIGHs survived contact
with the plan intact**: SC-014's corrected shape is executed correctly everywhere, and SC-004
clause 3 is implemented in the right *shape* (module attributes, two independently imported
names) — **it is the name count that is wrong.**

### PR-1 [HIGH] The plan's own `egress/` layout creates a FOURTH name — measured, 8 cases

The plan says "after consolidation the symbol is reachable by **three names**" (`:240`) and
"the shims are deleted, so **two assertions are complete**" (`:261`). **True of the spec's
abstract three-name model; false of the layout this plan mandates.**

`egress/refusal.py` **defines** `project_egress_refusal` (`:469`) while `egress/__init__.py`
must re-export it, because the deciding modules rebind as
`from specify_cli.egress import project_egress_refusal` (`:415`, `:428-429`). **That is a
by-value re-export.** Four names:

1. `specify_cli.egress.refusal.project_egress_refusal` — **definition site**
2. `specify_cli.egress.project_egress_refusal` — package re-export
3. `specify_cli.saas_client.client.project_egress_refusal`
4. `specify_cli.tracker.saas_client.project_egress_refusal`

Measured, control first, exact plan layout reproduced:

```
== CONTROL ==            both decision points -> DENIED-real        OK
                         SC-004 cl.3 #1/#2    -> True/True          OK
== mutation patches the DEFINITION site (egress.refusal) only ==
   saas decision point sees mutant?    -> False   <- INERT
   tracker decision point sees mutant? -> False   <- INERT
   SC-004 cl.3 #1 / #2 still GREEN     -> True    <- GATE SILENT
INPUT CASE COUNT: 8 (expect 8)
```

**A mutation patching the definition site — the natural target for MUT-1 ("delete the `DENIED`
branch from the consolidated wrapper", `:320`) — is inert at both decision points *and*
SC-004 clause 3 does not red.** The mutant reports "survived", which reads as "SC-016's
content pins do not detect deletion of the `DENIED` branch": **a false finding about the gate,
produced by rot-mode 5 reappearing inside the fix for rot-mode 5.**

**AND IT CORRECTS A CLAIM I RECORDED AS SETTLED.** The plan states at `:259` (inherited from
the round-3 recommendation I wrote into this file): *"once identity is pinned, **any** future
patch of the shared module **provably** reaches both decision points."* **Measured false** —
after `egress.project_egress_refusal = mutant`, the decision point still returned
`'DENIED-real'`. **Identity DETECTS a stale binding; it never makes a patch EFFECTIVE.** The
correct operative rule is the plan's own "patch every name it is reachable by" (`:265`) — but
that rule says *three* names, so following it exactly still leaves name (1) unpatched.

**Direct answer to the question I posed:** PB-5's deletion decision correctly closes the
**shim** route, but **it does not make two comparisons sufficient** — for a reason PB-5 never
considered.

**Recommendation (a), the cheaper fix, preserving PB-5):** collapse to three names —
`egress/__init__.py` re-exports **nothing**; both deciding modules import
`from specify_cli.egress.refusal import project_egress_refusal`. The plan's "three names / two
assertions complete" then becomes **true as written**, and C-004's substring gate is still
satisfied by the rebound line at `tracker/saas_client.py:34`.
*(b) keep the re-export, state **four** names, add a third `is`, and strike the false
"provably reaches" clause.*

### PR-2 [HIGH] The guards' predicates are inline in test-function bodies, so half the mutation suite has nothing it can provably kill

Measured: both attribution predicates are **local code inside a single test function**, not
importable symbols — SaaS at `test_client_consent_gate_3030.py:~332-340`, tracker at
`test_saas_client_consent_gate_3030.py:~385`.

Two plan rules collide with this and it resolves neither:
1. `:341`/`:568` require SC-012/SC-013 to be **"asserted against a synthetic sample, not the
   live corpus"** — but an inline predicate cannot be called on a synthetic sample.
2. `:214` (rule 11) mandates **"mutations are pytest plugins via `PYTHONPATH`, never source
   edits"** — but a plugin cannot patch logic inside a function body. MUT-4/5/6 all mutate
   exactly that logic.

**The path of least resistance is to re-write the predicate in the new test — a second copy.**
Then MUT-4/5/6 mutate one copy while SC-012/SC-013 assert against the other: **the mutants
become unkillable, or are applied to the copy and reported as kills that prove nothing about
the live guard.**

The plan **names this exact failure** for SC-005 — *"a harness that can drift from the real
guard is a gate that goes green while the guard goes blind"* (`:338`) — **but never
generalises it to SC-012/SC-013, which are the criteria that structurally require it.**

**Blast radius: IC-01, the "must land first" package.** MUT-5/MUT-6 are the *only* evidence in
the mission that the per-class floor does not detect predicate narrowing; MUT-4 the only
evidence for vocabulary widening. **Losing all three silently is rot-mode 2/3 territory.**

**Recommendation:** add an IC-01 deliverable — **extract each guard's predicate to a
module-level function in its own guard file**; the live `rglob` scan **and** the synthetic
assertions call the **same object**; MUT-4/5/6 patch that symbol (importable — verified
`tests/__init__.py`, `tests/specify_cli/__init__.py`,
`tests/specify_cli/saas_client/__init__.py` all exist). Binding sentence: *a synthetic
assertion that does not call the same predicate object the live scan calls does not satisfy
SC-012/SC-013.*

### PR-3 [MEDIUM] SC-014's assertion target is stated at `Path.exists()` level — a pathlib characterization test

`:215`/`:637` state the expectation as *"at `store.py:64`: `Path.exists()` returns `False` on
3.12+ and raises on 3.11"*. **That passes identically whether or not `decisions/ownership.py`
carries the `except OSError`** — so it cannot catch the regression the rot-mode-4 section
exists to catch. The plan carries the correct requirement at `:134` and `:612`, so **the plan
contradicts itself and the binding verification section is on the wrong side.**

**Compounding:** spec `:1205-1206` assigns SC-002 clause (c)'s **refuse half** to *"SC-014's
unreadable-ledger test"*. The plan mandates the must-not-veto half in four places but **never
restates where the refuse half is asserted.** Round 3's two-sided rule ends up one-sided again
— with the *other* side missing this time.

**Fix:** state the assertion target as **`resolve_decision_ownership`'s outcome** under
`decisions/` at `0o000` — *not established*, unreadable flag set, **no exception escaping, on
both interpreters** — and name that same test as the home of SC-002 clause (c)'s refuse half.

### PR-4 [MEDIUM] MUT-2 is stated as a source-tree state, not the `PYTHONPATH` plugin rule 11 mandates

Its cell describes leaving `tracker/egress_consent.py` in place — **a source state, producible
only by a source edit, which rule 11 forbids twice.** Since MUT-2 demonstrates the mission's
headline property, leaving its mechanism underspecified **invites the exact violation**.
Expressible as a plugin: `pytest_configure` rebinding the deciding module's attribute to a
delegating wrapper returning the identical string. (The clause-3 snippet is already correctly
shaped to detect it — it reads module **attributes** at assert time.)

### PR-5 [MEDIUM] Acceptance step 2 is not executable under step 5, and the fact that actually closes the fabricated-consent trap is unstated

Step 2 says *"pass both roots explicitly, never omit the kwarg"*; step 5 mandates the **real
invocation**, under which **the test never constructs a client** — `cmd_widen` does
(`decision.py:558`). There is no kwarg to pass. An implementer reconciling them may construct
inline, **abandoning C-008's real entry point and the FR-003 slug route with it.**

**The trap IS closed on this path — by a mechanism the plan never names:** `from_env` always
passes `project_root=` as a keyword **even when `None`** (`client.py:137-142`), so the autouse
guard `if "project_root" not in kwargs` (`conftest.py:74`, mirror at `:166`) is **unreachable
from `cmd_widen`**. *"Right now that safety is held by luck rather than by measurement — and
the plan's own rules demand the latter."*

**Fix:** convey A's root through `SPECIFY_REPO_ROOT` (`core/paths.py:224`, highest priority);
record the measured reason the fixtures cannot fire; **name the acceptance module's directory**
(unspecified at `:506`, yet `transmitted_text` must be imported from
`test_client_consent_gate_3030.py:73`, not re-implemented).

### PR-6 [LOW] The per-site-split instruction is over-generalised; MUT-1's row omits it where the reader looks

Meaningful only for mutations touching the consolidated symbol (MUT-1, MUT-2); demanding it of
MUT-3/4/5/6 produces filler that dilutes the one place it discriminates. **And given PR-1,
MUT-1 is precisely the mutant that will be applied to the wrong single name.**

### Conceded as strong (recorded so it is not re-litigated)

- **SC-014's corrected shape survives everywhere — no file-shape corner.** Every binding site
  (`:16, :122-127, :143, :215, :226, :544, :637`) says **directory**; the only `file=0o000`
  mentions are the labelled companion and the negative evidence. **The plan re-executed the
  two-interpreter measurement itself rather than transcribing it.**
- **The red-first proof asserts the bytes** — `:283-287` puts
  `assert DECISION_ID_OWNED_BY_B not in transmitted_text(sink)` **first** and demotes
  `sink == []` to corroboration; `:276-278` requires **observing** the pre-fix request.
- **All three SC-001 short-circuits named with the right discriminator**, third one verified in
  source (`errors.py:12,24` → `decision.py:570`).
- **SC-002's must-not-veto half is carried in four places** — load-bearing, not co-listed.
- **Every guard anchor re-verified exact**, so MUT-4's counter-intuitive control (counts
  *exactly unchanged*) and MUT-5/6's floor controls are **measured-true, not asserted**.
- **MUT-2's restatement is right** — the old form could red nothing under Q2.

## Lens: architect-alphonso — plan round 1 — VERDICT CHANGES REQUESTED — **Above MEDIUM: 2 (both HIGH)**

### PA-1 [HIGH] The `core_misc` glob accompaniment makes routing WORSE — measured

After adding the module to `core_misc`, a diff confined to it sets **one** group true and
`unmatched=false` — so `fast-tests-sync` (gated on the `sync` group alone,
`ci-quality.yml:201-204`, job `:1096-1101`) does **NOT** run. Unrun on exactly the diff shape
**FR-008 is designed to produce**: SC-021/FR-027's two tracker behavioural ratchets, FR-024/
SC-016's **tracker-side** `DENIED` content pin, and the tracker attribution guard.

**Without the glob edit, unmatched → run_all → all of it runs.** The accompaniment **trades
fail-safe-but-loud for half-blind**, on the one file the consolidation makes common to both
transports.

**Sharpened during remediation:** `fast-tests-core-misc`'s `core-misc` shard carries an
explicit **`--ignore=tests/sync`** (`:1640`), so `tests/sync/tracker/` runs **nowhere but
`fast-tests-sync`.** That makes the `core_misc`-only form a **genuine silent coverage loss**,
not merely a risk.

**MY RULING: add the module to BOTH `sync` and `core_misc`.** Direct precedent verified —
`core/loopback_http.py` is in `sync` (`:203`) *and* in `core_misc` via `core/**`. Nothing
enforces src-glob exclusivity. **This inverts my earlier statement to the operator that the
glob edit was needed to avoid run_all-forever: the single-group form is worse than run_all.**

### PA-2 [HIGH] SC-006's `[one-off]` CI observation is structurally unobtainable

Any PR carrying the FR-017 fix **changes `ci-quality.yml`, which is itself a `core_misc` glob
member** (`:263`) — so `core_misc` goes true regardless of the new `cli` gate and the run
proves nothing. This is the mission's **only** empirical discharge of Decision D-4's
explicitly unverified premise, so an unnoticed confound means the premise is **carried as
discharged when it is not** — friction's "green for an unrelated reason".

**Fix applied:** stacked throwaway PR **based on the mission branch** (dorny diffs against the
PR base, so a comment-only change under `cli/**` is genuinely `cli`-only while the base
already carries the fix), quoting job list + run URL, closed unmerged — or a declared
post-merge observation. **"Re-reading the YAML is not admissible."**

### PA-4 [MEDIUM] — MY FR-020 RULING'S LEAD GROUND WAS FALSIFIABLE, AND THEY FALSIFIED IT

My ground 1 claimed placing the derivation in `egress` "would break the premise `egress` rests
on… the basis on which F2 does not fire." **Wrong on two counts:**
1. **F2's antecedent is that the shared module imports from `saas_client/` or `tracker/`** — an
   edge to `specify_cli.decisions.store` does not satisfy it. **F2 is about *transport*
   neutrality, not import-freedom.**
2. **Measured** (controls first — known sync-importer **YES**; `saas_client` 6 modules **NO**,
   `tracker` 11 **NO**, `delivery` 4 **NO**, reproducing PL-2 exactly with an independently
   written probe excluding `TYPE_CHECKING` and function-scope imports):
   **`specify_cli.decisions.store` closure = 2 modules, reaches `specify_cli.sync` = NO.**

**The ruling stands** on ground 2 (SC-018 is the operative surface and names no package —
decisive alone) and ground 3 (cohesion), **plus a fourth ground stronger than the one I led
with: bounded-context ownership (DIR-031).** *"Which project owns this record" is a
decisions-context question; `egress` is a presentation wrapper for a refusal string. Putting a
ledger reader inside it makes it a two-concern module and re-creates precisely the
three-spellings conflation FR-020 exists to prevent.*

**Rewritten in the ACCEPTED spec** — bounded-context promoted to ground 1, old ground 1 demoted
to the weaker true claim, falsification recorded. *A falsifiable lead ground sitting in an
accepted spec is an invitation for a successor to overturn the ruling by measuring what the
lens just measured.*

### PA-5 [MEDIUM] → drove the module ruling; PA-3, PA-6, PA-7, PA-8 [MEDIUM/LOW] all applied

- **PA-6**: R2 split into **R2a** (safety — forgetting `INTEGRATION_PREFIXES`, gated by SC-025)
  and **R2b** (cost — forgetting a glob line, **fail-safe in the coverage direction**). *"The
  glob's risk is CI minutes, not coverage. The dangerous direction is not forgetting the glob —
  it is MAKING the `core_misc` entry without the `sync` entry."*
- **PA-7**: PB-5 carry-through 2 → **4 items**, incl. a **src-side** dangling pointer at
  `saas_client/__init__.py:17`.
- **PA-8**: the "declared disagreement" block is stale → retitled **CONCORDANCE**.

### Conceded strong

PB-5 right and for the right reason; Q1's rejection of (b)/(c)/(f) sound (the measured absence
of any `tracker`↔`saas_client` edge is the correct discriminator); **retraction discipline
"exemplary"** (PL-2 overturns the author's own prior headline, PL-4 records a near-miss);
**every plan anchor checked reproduced** (937 files exact, both `pytestmark` lines,
`INTEGRATION_PREFIXES` exactly five prefixes, `_SRC.iterdir()` top-level-only).

## ORCHESTRATOR ADJUDICATION — the two lenses proposed INCOMPATIBLE fixes

debbie PR-1 fix (a): `__init__` re-exports nothing.
alphonso: **SC-004 clause 3 asserts `specify_cli.egress.project_egress_refusal`**, so that name
must exist. **Incompatible.**

**RULING D-8: take the plain-module form — `src/specify_cli/egress.py`, NOT a package.**

1. **Eliminates the fourth name by construction.** One definition site — exactly the name
   SC-004 clause 3 already asserts. **Three names; the spec's existing TWO `is` comparisons
   become correct as written; no third assertion; SC-004 untouched.**
2. **Lower structural cost.** A module obtains every property the plan enumerates. Verified
   in-clone: `test_no_dead_symbols` walks every `*.py`; `test_layer_rules.py:202-208` filters
   `p.is_dir()` **and** scans top-level only (two independent reasons it is untouched);
   `test_integration_boundary.py:151-152` is `mod == prefix or mod.startswith(prefix + ".")` —
   the module is caught by the **first arm**.
3. **Bonus measurement, not briefed:** `_gate_coverage._src_dir_of_glob('src/specify_cli/egress.py')
   → None` (control: the `/**` form → `'egress'`), and the worklist iterates direct child
   **directories** — so a module is **structurally outside** the unclaimed-src-dir detector, and
   **the `T_LOC = 500` argument (finding D-8) is no longer load-bearing.**

**Authorised consequence:** SC-025's and C-005's antecedents were **package-shaped**, which
would make SC-025 vacuous under a module. Amended to *"a new `<name>.py` **module** or
`<name>/` **package**"*. **Not a workaround — the hazard is about what the thing *imports*, so
the package-shaped wording was a latent gap regardless.**

---

# §3-R2 — PLAN REVIEW ROUND 2

## Lens: architect-alphonso — **APPROVE WITH MINOR CHANGES — Above MEDIUM: 0**

Both HIGHs closed in substance, **verified through `_gate_coverage`'s own parser, not by
reading YAML.** Controls first; input counts stated.

```
== CONTROLS ==  cli-only -> fast-tests-cli True / fast-tests-sync False; sync-only -> True
   INPUT: 5 workflow models, 30 named groups, 57 jobs
== egress-confined diff, one glob vs two ==
   fast-tests-sync       core_misc-only=False   core_misc+sync=True
   fast-tests-core-misc  core_misc-only=True    core_misc+sync=True
```

PA-1's two-glob fix **routes correctly**. The silent-coverage-loss sharpening reproduced
independently. **One unnamed cost:** the `sync` glob also pulls `integration-tests-sync-real-port`
and the serial daemon family on every future refusal-string edit — still far cheaper than
`run_all`, but worth one sentence.

### A trap NEITHER lens had checked — and the module ruling survives it

`src/specify_cli/__init__.py:218` defines `__getattr__` that **raises `AttributeError` for
every name except `"app"`**. On a synthetic replica (4 cases, controls first): `from pkg import
egress`, `import pkg.egress`, and `from pkg.egress import f` **all resolve to the same object**
(`e1 is e2 → True`, `f is e2.f → True`). **SC-004 clause 3's two `is` comparisons are safe
under the module form**, in the spelling the plan uses.

Module-form claims all verified: `_src_dir_of_glob('…/egress.py') → None` (control: `/**` →
`'egress'`); `mapped_src_dirs` excludes `egress`; worklist keys are all directories (36 today);
the integration gate catches the module in **all three** import shapes including
**function-scope**, via `mod == prefix` (`test_integration_boundary.py:151-152`); no name
collision among 19 sibling top-level modules.

### PR-A [MEDIUM] SC-006 substitute (1) — the stacked throwaway PR — is INOPERATIVE in this repo

`ci-quality.yml:3-14`: `on.pull_request.branches` is `[main, develop, 2.x]`, and **that filter
applies to the PR's *base* ref.** A PR based on `bundle-b-egress-refusal-3110` therefore
**never triggers CI Quality at all** — no job selection to observe, no run URL to quote: the
plan's own *"an empty output file is no measurement"* state.

The workaround-of-the-workaround fails too: adding the mission branch to
`on.pull_request.branches` **edits `ci-quality.yml`**, the `core_misc` member at `:263` —
**reinstating the exact confound.** Rebasing onto `main` puts the whole mission in the diff.

**MEDIUM not HIGH because substitute (2) is sound and unaffected**, so the obligation stays
dischargeable and **cannot yield a false green (there is nothing to quote).** But (1) is listed
first and in most detail, so it is the one an implementer would take.
**Fix: strike (1); state that SC-006's `[one-off]` half is *necessarily* post-merge in this repo.**

### PR-B [MEDIUM] SC-021's guarantee rests on routing that does not exist for `tracker/**`

Measured: `agent_surface` (which owns `src/specify_cli/tracker/**`, `:401`) selects
`fast-tests-core-misc` but **not** `fast-tests-sync`. So a future PR confined to
`src/specify_cli/tracker/saas_client.py` — **the file whose call at `:329` FR-027/SC-021 exists
to protect** — runs **neither ratchet**, while C-004's substring gate stays green on the import
line alone. **That is finding A-5's hazard with a routing hole in front of it.**

**Pre-existing, not introduced by the remediation**, and this mission's own PR is covered
(it carries `egress.py`, so `sync` fires). **But the plan now presents the coverage story as
closed.** Fix: add `'src/specify_cli/tracker/**'` to the `sync` group as a **third glob** (same
one-line pattern, same precedent) — *"it is what makes SC-021 durable rather than incidental"* —
**or** record under FU-1, in one sentence, that **SC-021's ratchets are not routed to the file
they protect, so the mission does not hand over a guarantee that expires when `egress.py`
leaves the diff.**

### PR-C [LOW] Anchor regression introduced by the remediation

`INTEGRATION_PREFIXES` is `test_integration_boundary.py:75-81` (verified: `:74` blank, `:75`
opener, `:81` closing bracket). The remediation wrote `:74-80` at `:484` and `:741` while `:191`
still says `:75-81`. **One anchor, two forms, same document — the RM-2 four-copies problem this
mission caught in the act, recurring.**

### PR-D [LOW] The worklist point is booked as an advantage; it is the loss of a latent detector

A **package** that grew past `T_LOC = 500` while unmapped would appear in
`live_derived_worklist`; a **module never can, at any size**. The spec's SC-025 text states this
correctly — as a reason SC-025 is *needed*. The plan's ground 2 states it as a **gain**. Minor
(R2b establishes glob-omission is fail-safe) and it does not disturb ruling D-8 — but align the
wording so **the record does not carry a weakening described as a strength** (DIR-003).

### Conceded

*"The package→module adjudication is correct, verified on every claim it makes plus one trap it
did not check, and it is the rare case where resolving two lenses' incompatible fixes dissolved
the problem instead of splitting it."* The four-state R2b table is called **"the best artefact
in this revision — it converts a procedural obligation into a review question a reviewer can
actually ask."** Both spec corrections are improvements independent of the module decision.

## Lens: debugger-debbie — plan round 2 — **ACCEPT-WITH-CHANGES — Above MEDIUM: 0**

Both round-1 HIGHs closed, **re-measured rather than accepted from the remediation's account.**

```
== CONTROL (known answers first) ==
   both decision points -> DENIED-real; clause 3 #1/#2 -> True/True
   name count reachable (module form) -> 1   (expect 1)
== CASE A: MUT-1 shape, patch the shared module ONLY ==
   both decision points see mutant? -> False ;  clause 3 REDS -> yes   <- DETECTED
== CASE B: patch ALL THREE names ==  both decision points see mutant? -> True
== CASE C: MUT-2 shape, stale binding on tracker only ==
   every string observation stays green -> DENIED-real
   clause 3 #2 REDS on the stale binding ; #1 stays green
INPUT CASE COUNT: 13 (expect 13)
```

**PR-1 closed.** The id-set over the three names has size **1**. Exhaustive enumeration of
`project_egress_refusal` across `src` + `tests` — **9 sites** (4 importers, 4 test-prose
pointers, 1 src-prose pointer at `saas_client/__init__.py:17`) — confirms the only module-scope
by-value binds are `saas_client/client.py:23` and `tracker/saas_client.py:34`; the two in-test
imports are **in-function**, so they re-read the attribute at call time and are **not persistent
names**. C-004's allowance is keyed on `seam_module="specify_cli/tracker/saas_client.py"`
(`test_egress_consent_boundary.py:519`), **not** on either `*/egress_consent.py` path — F3's
allowlist half holds.

### FRAMING CORRECTION — record it THIS way or the error re-arms

I asked whether a mutation patching the shared module "now reaches both decision points".

> **No. It does not, and no layout can make it.** CASE A: after patching name 1 alone, **both
> decision points still returned `'DENIED-real'`.** That is a property of `from X import f`, not
> of package-vs-module.

**What the module form actually buys, and it is the right closure:** under the **package** form,
patching the *definition site* was inert **and clause 3 stayed green** — *undetectable*. Under
the **module** form the definition site **is** name 1, so any patch of it **makes clause 3 red**.

> **The module form converts a silent no-op into a DETECTED one; it does not make one-name
> patching effective.**

The plan states this correctly (`:269`, `:290-293` *"Identity is a **detector**, never an
**actuator**"*, `:299`). **Recording the closure as "the patch now reaches both decision points"
would re-arm the exact error PR-1 was about.**

### PR-E [MEDIUM] IC-01's acceptance test is a metric the plan has itself proven blind

The hoist's stated proof is *"must not change a single count — `SaasClient scanned=4
unattributed=0` / `SaaSTrackerClient scanned=3 unattributed=0`"*. **But the plan's own mutation
table already measured that those numbers cannot see the predicate changes it cares about:**
MUT-4 counts *exactly unchanged* (`scanned += 1` precedes the attribution test), MUT-5
`scanned == 3` exactly at the floor, MUT-6 `scanned == 4` unchanged because `direct=0`.
`unattributed=0` is equally blind — every live site is already attributed.

**So an extraction that accidentally widened or narrowed the predicate would emit byte-identical
evidence and pass the stated proof** — and would then make MUT-4/5/6 mutate an already-mutated
predicate, so SC-012/SC-013 read as red-at-baseline or "survived". *"Using a metric you have
proven non-discriminating as the gate on the refactor everything else depends on is the same
shape as the vacuous-count failure the plan opens with."*

**Fix:** keep the counts, **add the four synthetic witness shapes** to the before/after evidence
— `SaaSTrackerClient(repo_root=…)`, `SaasClient.from_env(project_root=r)`,
`mod.SaaSTrackerClient(project_root=…)`, `SaasClient(project_root=…)` — recording the
`(matched, attributed)` tuple for each, expected values derived from reading the pre-hoist
source. **Those four are exactly the shapes the live corpus does not contain, which is why they
discriminate and the counts do not.**

### PR-F [MEDIUM] PR-5's reopening condition is one-sided, and a reopening would be INVISIBLE to every test this mission adds

The mechanism verified exactly: `client.py:137-142` **always** passes `project_root=`, including
on the `None` branch; both autouse guards are `if "project_root" not in kwargs`
(`conftest.py:74`, `:166`). **The trap is not re-armed.**

But the safety property is a **conjunction over two files** and the plan's falsifier watches only
the **producer**. Changing the conftest guard to `if kwargs.get("project_root") is None` is a
natural "improvement" — *and the conftest's own comment shows its author already reasoned about
the `project_root=None` case.* Under that edit the injection fires on the real path.

**Why it is a finding, not a note: the fabrication would be invisible to every test this mission
adds.** The ownership gate keys on the acting root from `SPECIFY_REPO_ROOT`, **not** on
`project_root` — so SC-001's refusal still occurs and the in-file positive control still passes.
**Green either way — the trap's signature.**

**Fix:** convert the two-file prose invariant into a **runtime assertion** in the acceptance
module — assert the client the command actually built carries A's on-disk root (e.g.
`client._project_root == A_ROOT`, captured via the same sink/spy the byte assertion uses).
**That reds the moment either side changes.** Extend the reopening condition to name the conftest
guard as the second falsifier.

### PR-G [LOW] PR-6's scoping went one bullet too far

Scoping the whole block to MUT-1/MUT-2 also carried away *"the plugin must **fail loudly when its
target is absent**, so a no-op cannot masquerade as a clean gate."* **That rule is needed MOST by
MUT-4/5/6** — now the only plugins that must reach a symbol in a *test* module by dotted path,
**whose target does not exist yet** (IC-01 creates it). A rename during the hoist, a wrong dotted
path, or rootdir not on `sys.path` at `pytest_configure` all give a silently absent target →
"mutant survived" → a false finding. Move that bullet to the standing rules; drop the stale
"reports the per-site split" from R7's detection cell.

### PR-H [LOW] `egress.py` joins the `sync` CI **group** while F2/FR-013 forbid a `specify_cli.sync` **import edge** — two senses, unlabelled

**This mission's own recorded recurrence pattern** (PL-3: *drift entered the spec's Q1 table
through two senses of "classified"*), now with a fresh instance. A future author could read the
group membership as licence for an import edge, **or "tidy" the glob away** to restore apparent
consistency — silently re-creating the half-blind routing.

**Fix:** one sentence at the glob task — *this is CI **routing**, not an import-edge claim;
`egress.py` must still import nothing from `specify_cli.sync` (F2/FR-013), and removing this glob
switches off the tracker guard and both SC-021 ratchets on an `egress.py`-confined diff.*

### PR-C [LOW, CONVERGENT with alphonso] the `INTEGRATION_PREFIXES` anchor regressed to `:74-80`

Both lenses independently. Correct span is **`:75-81`** (`:74` blank, `:75` opener, `:81` closing
bracket). `plan.md:191` still correct; `:484` and `:741` wrong. **Same class the plan itself
fixed for `store.py`.**

### Conceded

**PR-3 closed more thoroughly than asked** — *both* contradicting sides fixed, and SC-002 clause
(c)'s refuse half addressed in three places. **PR-4 closed exactly right**, CASE C confirms the
prescribed rebind reds clause 3 while every string observation stays green. Both spec corrections
*"justified as **latent gaps independent of Q1's answer** rather than as accommodations of the
module choice"* — with the gate's own matcher cited as ground. `_src_dir_of_glob` verified true
from source (`_gate_coverage.py:1406` returns `None` when the segment ends `.py`).

---

# PLAN ARTIFACT — ACCEPTED after round 2

| Round | Lenses | Verdict | Above MEDIUM |
|---|---|---|---|
| 1 | alphonso + debbie | CHANGES REQUESTED | **4 HIGH** (2 each, all distinct) |
| 2 | alphonso + debbie | APPROVE / ACCEPT-WITH-CHANGES | **0 / 0** |

**No escalation.** Round-2 MEDIUM/LOW items applied as a closing polish (they are cheap and
concrete); anything left is a recorded residual.
