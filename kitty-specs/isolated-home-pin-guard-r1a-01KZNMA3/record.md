# R1a — The Reduced Record

**Mission**: `isolated-home-pin-guard-r1a-01KZNMA3` — the guard half.
**Work package**: WP06 (alias WP-d), subtasks T027–T030.
**Branch**: `feat/isolated-home-pin-guard`.
**Written**: 2026-08-12.

This file is where R1a states **what it did not prove**. Every item below is a claim R1a would
otherwise be read as having proved. A missing residual is a false claim by omission.

**Measurement discipline for this file.** Every figure carries **both its population and the SHA it
was measured at**. Figures below marked *(constructed here)* were re-derived for this record under
the pinned interpreter `/home/jeroennouws/dev/sk-missions/3157/.venv/bin/python`, not copied from a
prior pass. Figures taken from a review artefact are attributed to it.

---

## 0. The two SHA frames, and the numeral that means two different things

Two frames appear throughout this Mission. **They are not interchangeable, and one numeral is a
trap.**

| Population | at baseline `5d49d31ed` | at freeze SHA `fe5d492ed` |
|---|---|---|
| `.py` files under `tests/` | **2737** | **2752** |
| files hitting `b"SPEC_KITTY_HOME"` | **100** | **111** |
| `SPEC_KITTY_HOME` write sites | **191** in 85 files | **194** in 87 files |
| **effect-class members (the CLASS)** | **40 in 36 files** | **42 in 38 files** |
| **census rows (the CENSUS)** | — (no census exists there) | **40 rows in 36 files** |

*(All twelve figures constructed here, under the pinned interpreter, from `git archive` extractions
of both SHAs. The `5d49d31ed` column reproduces spec §0.8 exactly; `plan.md:52` carries the same
`2737 / 100 / 191 / 40-in-36` figures and `plan.md:53` states they are "settled and not re-measured
by this plan", sourced to §0.8 — so the plan is **not** an independent frame, it is the spec's frame
quoted.)*

**THE TRAP: "40 in 36" is true at both SHAs and names a DIFFERENT POPULATION at each.** At
`5d49d31ed` it is the **class**. At `fe5d492ed` it is the **census** — where the class is **42 in
38**. The difference is exactly `E`'s two entries (residual **B** below, which names them). Writing "the class is 40 at
the freeze SHA" restates in prose **this record's own headline finding**, the `census` /
`census ∪ E` conflation. Say *census* when you mean census.

**Freeze SHA in full**: `fe5d492ed9210907797876066504f419e136b2ff` — read from the census header, not
assumed. It is a **lane-e merge commit and is NOT an ancestor of `feat/isolated-home-pin-guard`**:
WP01–WP05 are approved but unmerged, so none of the `_home_pin_*` modules, the census, or the verdict
artefact exist on the mission branch at the time this record is written. Anything in this file
measured against those artefacts was measured against a `git archive` extraction of a lane commit,
never by entering a lane worktree.

---

## T027 — The halt-path ADR: imported, not authored

**File**: `docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md`

**Provenance.**

| | |
|---|---|
| Source | `git show spike/isolated-home-3121:docs/adr/3.x/2026-08-07-1-a-mission-halting-instrument-is-worth-its-cost.md` |
| Source `sha256` | `88f5b668678ca46551a7f3c5dac2295a813963de0e7d586d7ba610142a31298b` (209 lines) |
| Landed `sha256` | `73838631d7d737d11e1039b5ab3dde5091068f84989053a1a5776e072b14ac21` (210 lines) |
| **Body-only `sha256`, both sides** | **`727658bee495b760aadbfc61a7200540f6f04bacc2130f031285adcc39fec5ee`** — identical |
| Precondition verified | file **ABSENT** on `feat/isolated-home-pin-guard`, **PRESENT** on `spike/isolated-home-3121` |
| Branch integration | **none**. `git show` only. No merge, no rebase, no cherry-pick. The spike branch is untouched. |

**T027's literal byte-identity DoD was RELAXED BY OPERATOR RULING.** The two hashes above differ.
This is recorded, not hidden.

- **What changed**: exactly one added line — a `description:` frontmatter key. `diff` against the
  spike blob reports `2a3` and nothing else. The **body is byte-identical**, proved by the shared
  body-only hash above.
- **Why the ruling was needed**: the ADR carries **no `description` frontmatter and no leading prose
  paragraph**, so `resolve_abstract` returns `""`. The `docs/adr/` carve-out in
  `description_length_check.py` **was retired** — `tests/docs/test_docs_index.py:299-303` says so in
  as many words, and the script's own historical note at `description_length_check.py:87-113` records
  that the census gate "explicitly permits additional frontmatter keys, so nothing forbids an ADR
  from carrying a `description`", and that the `docs-seo-metadata-enforcement` mission backfilled one
  onto all 151 of them. `docs-freshness.yml:80` runs the gate `--strict`, exit 1.
- **Why the relaxation does not defeat what byte-identity protected**: byte-identity exists so R1a
  cannot land a **second, divergent record of one halt**. A `description` key cannot make the record
  diverge — it adds no account of the halt and changes no sentence of the one imported. The account
  is byte-identical; one metadata line satisfies the gate.
- **Measured convention**: **100 of the 101 ADRs under `docs/adr/3.x/` already carry a
  `description`** *(constructed here)*. The imported file was the sole holdout. The added key makes
  it conform to the repository's convention rather than deviate from it.

**Positive control — the gate can see this file.** Landed byte-identical first and ran the gate:
`checked 677 page(s); 1 violation(s) — MISSING …(length=None)`, **exit 1**. Then added the key:
`checked 677 page(s); 0 violation(s)`, exit 0. The population-0 result is a real green, not an
unreachable assertion.

### The defect this import introduced, found by hunting for it — and the canonical tool that owns it

**Landing an ADR requires THREE index updates, not one.** The first pass of this WP made two of them
and was green on all four gates it ran. It was still wrong.

| Artefact | Status after the first pass |
|---|---|
| `docs/development/3-2-page-inventory.yaml` | regenerated ✔ |
| `docs/development/3-2-docs-retrieval-index.yaml` | **initially MISSED** — caught by running `check_docs_freshness.py`, which went **newly red** with `DOCS-INDEX-DRIFT`. Regenerated ✔ |
| **`docs/adr/3.x/README.md` index row** | **MISSED, and NO gate I had run caught it** ✔ (fixed) |

**The README row is the real defect.** `docs/adr/3.x/README.md` itself states the rule — *"After
adding an ADR file, run `python scripts/docs/freshen_adr_inventory.py docs/adr/3.x/<your-adr>.md` to
update the page-inventory lockfile **and add the row to the index table below**"* — and
`freshen_adr_inventory.py`'s own docstring says why it exists: *"Agents repeatedly trip the gate
(`LEAK-MISSING-INVENTORY`, `INVENTORY-INCOMPLETE`, `INVENTORY-LOCKFILE-DRIFT`) by forgetting one of
these."* **This WP is another instance of the exact failure that tool was written to prevent.**

Detected by positive control, not by absence:
`freshen_adr_inventory.py --check <adr>` → `ADR-README-ROW-MISSING`, **exit 1**,
`missing_rows=1 inventory_stale=False` — pinpointing that the inventory work was correct and the
README row alone was missing. Repaired with the canonical tool (`README-ROW-ADDED`,
`rows_added=1 inventory=unchanged`), never by hand. `--check --all` is now clean across all 101 ADRs.

**The transferable part, and it is the charter's own rule.** Four gates ran green over a repository
that had a canonical one-command tool for precisely this task, and **not using the canonical tool is
what produced the defect** — "Use Canonical Sources, Never Improvise" is not style advice here, it is
the thing that would have prevented this. **A green gate set is not evidence that the task was done
the supported way.** It is the same shape as residual **A** below and as the "124 passed" finding:
*green over a population that does not include the thing you changed.*

### DO NOT TOUCH — the two forbidden-term occurrences inside the ADR body

The imported body contains the forbidden term at **lines 102 and 112** of the landed file (101 and
111 of the spike blob; +1 from the added `description` line). **They are legal and MUST NOT be
"fixed".**

- `tests/architectural/test_no_legacy_terminology.py:42-51` exempts `docs/adr/` as immutable
  historical snapshots, and the narrowness of that exemption is pinned by
  `test_docs_adr_exemption_is_narrow`.
- **Editing them would mint the divergent second record T027 exists to prevent.** A one-character
  "tidy" makes it a second record of one halt.

---

## T030 — What R1a proved, what it did not, and what it hands to R1b

*A note on the mandate's numbering: `WP06-reduced-record.md` numbers its list 1–15 but assigns **12
twice** — once to the framework defects and once to the registry-test obligation. All sixteen items
are carried below; the duplicate is split as 12a and 12b rather than silently dropped. Recording it
because a list that loses an item to a numbering slip is exactly the failure mode this file exists
to catch.*

### 1. C-014 limb (iii) remains VACUOUS — R1a's recorded residual

C-014's three precedence-safety limbs: **(i)** `ScopeMismatch` makes scope inversion loud at setup —
exercisable; **(ii)** a non-autouse owner is never instantiated in a module that does not request it
— exercisable; **(iii)** every **retained and adopting** definition stays function-scoped.

**Limb (iii) is genuinely vacuous in R1a, and it is vacuous over adopters R1a does not have.** R1a is
the guard half; adoption is R1b's. There are **zero adopting definitions** in this Mission, so limb
(iii) quantifies over an empty set and cannot fail. It is not "green"; it is unexercised. R1b
inherits it as the first thing adoption must make bite.

### 2. SC-011 is PURE SHAPE; SC-012 carries the entire behavioural load alone

SC-011 exercises C-014 limbs (i) and (ii). Both are **properties of pytest's fixture machinery, not
of the owner's body**: an owner whose body is `return None` with no `setenv` and no `mkdir` satisfies
both. Spec §SC-011 states this against itself — *"In a Mission whose thesis is that shape is not
effect, SC-011 is pure shape and SC-012 carries the entire behavioural load alone."*

**A reviewer seeing SC-011 green must not read it as evidence the owner works.**

### 3. SC-012 limb 2 is vacuous as specified; the negative control in WP03/T013b is what makes it bite

As first written, limb 2 — a probe that keeps its own `setenv` **and** requests the owner observes
**its own** value, "failing if the owner's is seen" — **cannot fail, by construction**: FR-005 forces
the owner to pin `str(tmp_path/"home")`, any class member pins `str(tmp_path/"home")`, and `tmp_path`
is function-scoped and shared, so within one test the two strings are **identical**.

**Reproduced live by the WP03 reviewer, not argued** (`WP03/review-cycle-1.md:24-70`): deleting
probe (a)'s `monkeypatch.setenv` left `test_the_retained_pin_probe_observes_its_own_value`
**PASSING**.

What makes the pair falsifiable is the **second, NON-MEMBER probe pinning `tmp_path/"probe-home"`** —
a value the owner can never produce — declared in a **module-local fixture**, not the test body,
because fixture setup completes before the body and a body-level `setenv` would override the owner
unconditionally and prove nothing about the fixture-versus-fixture precedence decision at
`tests/conftest.py:272-286`.

**Recorded because it is not what the criterion says**: the same mutation reds four *other* tests —
`test_both_probes_request_the_owner_before_pinning`,
`test_only_probe_a_is_a_class_member_so_probe_b_costs_no_slot`,
`test_the_exempt_set_is_a_subset_of_the_discovered_class`,
`test_the_owner_and_the_probe_are_the_only_members_of_their_two_files`. **Probe (a)'s pin is
load-bearing, just not for the assertion that names it.**

### 4. THE GATE'S POWER TO HALT THIS MISSION WAS SPENT WHEN `r` LEAKED

Stated in those terms, because it is the single most embarrassing fact in this Mission and the record
is the place for it.

**The leaked values**: while verifying the VOID finding, an **independent lens** measured
**`r = 100%` at `|R| = 9, 33, 34`** — at candidate windows roughly **300, 600 and 2000 first-parent
commits back**. On that published evidence the verdict was **already known to be `proceed` before
WP-0b ran**. WP-0b therefore **confirms a known answer rather than discovering one**.

**R1a must stop describing the gate as its own stopping mechanism.**

**What survives** is a published measurement under a **pre-committed rule whose stopping criterion
never reads `r`**. Verified by the WP02 reviewer against the code
(`WP02/review-cycle-1.md:219-227`): `window_accepted` (`_home_pin_gate.py:599-609`) touches
`measurement.error`, `len(measurement.arrivals)` and `stability(...).stable`, and **never** reads
`measurement.label`, `result.base_band` or `result.base_consequence`. It branches only on the boolean
class-invariance, never on which class — **a stable *halt* window would have been accepted and the
walk would have stopped there.** A leaked value cannot steer a rule that does not read it.

**What is LOST and is not recoverable**: the analyst's blindness, which was a real part of the
instrument's value. Both facts are stated because only one of them is comfortable.

**Attribution correction, constructed here.** The leak's `|R| = 9, 33, 34` came from the
**independent lens**, **not** from the walk table. Parsed directly from
`research/home_pin_gate/verdict.yaml`: the 314 attempted windows contain **only two `|R|` values —
3 and 33** — and **every one of the 313 VOID attempts is exactly `(|R|, |R_f|) = (3, 3)`**. Nothing
in the published walk reports `|R| = 9` or `34`. Do not attribute those values to the walk.

### 5. THE VERDICT RESIDUAL, in its narrowed honest form

A collected test proves **internal consistency**, **the band**, **AND** that every **surviving
end-SHA key recomputes to real content in this tree**.

**Only the START-SHA operands remain unprovable without git.** The start-SHA site set is an operand a
reviewer can recompute only by re-extracting `ba0db69ad…` — the collected test cannot reach it. That
is the residual, and it is narrower than "the verdict is unproven": three of the four things the
verdict asserts are mechanised.

### 6. The named escapes, with measured populations — and the enumeration is NOT claimed complete

| Escape | Measured population | Note |
|---|---|---|
| `getfixturevalue` (static **and** dynamic) | **0** | the dynamic form is statically unresolvable by any predicate |
| Env-key indirection | **0** | 73 of 1245 `setenv`/`delenv` calls use a non-literal key; none is a member |
| **Delegation** — a silhouette-satisfying def calling a sibling helper that does the `setenv` | **0** | 3 ready targets exist. **Not closed by inlining** — one level of inlining invites two |
| **Subprocess environment dicts** — `env["SPEC_KITTY_HOME"] = …` into a `dict` passed to a child | **1 site**, `tests/sync/_daemon_harness.py:263` | correctly **excluded** from the 191: mutates a local dict, not the test process's environment. Recorded because it is a **live instance of a shape the three-form write does not claim to cover** |
| **Unmodelled value forms** — `os.path.join`, `%`-format, `.format()`, `+` concat | **3 UNRESOLVED sites, 0 members-in-waiting** | closed by FR-001's widening, which admits **0** new members |

**THE ENUMERATION IS NOT CLAIMED COMPLETE.** It was once, and a **fifth escape was found by the
post-plan gate**. Spec §0.5 item 5 records that the earlier form — *"the four named escapes, each
with population 0"* — was a **false completeness claim** carrying an unearned guarantee about a set
whose membership had not been established. The correction is kept here rather than quietly dropped,
because the shape of that error is the Mission's most-repeated one.

### 7. C-008 — `|P| = 5` is not used, not inherited, not cited; R1b MUST RE-RUN WP01

`|P| = 5` was measured over **28** members, at a merge-base **predating #3108**, with **two current
members never ablated**, and under the **superseded decorator-limbed predicate**.

**The class is now 40 under a different predicate** (42 including `E`, at the freeze SHA — item 0).

`|P| = 5` is **not an input to R1a**, is **not inherited by R1b**, and is **not cited as evidence
anywhere in this Mission**. **R1b MUST RE-RUN WP01 over the current class.** Reusing the figure would
be the same class-substitution error the whole Mission exists to name.

### 8. C-010 — PR #3285 is R1b's coordination dependency, not an R1a blocker

**#3285** (`test: assertively sanitize low-signal suite cruft`, verified **OPEN**): 35 files, all
under `kitty-specs/`; **intersection with the member files is empty**. It is a coordination
dependency for R1b and **not an R1a blocker**.

### 9. D-1 and D-2 deferred to R1b, with the reason

| | Defect | Where it lives |
|---|---|---|
| **D-1** | `evidence/ablation/VERDICT.md` §8 reads `GREEN 147/147` for the identity member; that fixture is `self`-bound and governs exactly **6** tests (live collection: module **147** nodes, class **6**). Should read `GREEN 6/6 governed (147/147 module nodes green)`. **A presentation defect, not an evidence gap.** | `spike/isolated-home-3121` **only** |
| **D-2** | `scripts/mutants/ablate_home_pin_3121.py:482–499` — `home_ok`'s `within_tmp` tests the **current test's** `tmp_path` and misses `tmp_path_factory` siblings, producing **15 false-positive** home violations, all `tests/cli/commands/test_sync_routes.py`. **Repair before reuse.** *(The defect was confirmed by reading the code; the count of 15 was **not** re-measured.)* | `spike/isolated-home-3121` **only** |

**The reason for deferral, stated once and applying to both**: both target files exist **only on
`spike/isolated-home-3121`**, and **C-013 bars merging**, so **there is no in-scope path in R1a to
either** — including any escape hatch, because the artefact to mark is also absent. They are struck
from C-006's blast radius and carried to R1b, which will have the branch in scope.

*(M4's ablation evidence was imported verbatim to `research/m4_ablation_evidence/` under BLOCKER-2.
That import **does not change D-1's deferral** — importing evidence is not discharging the
correction.)*

### 10. TG-1 through TG-4 — for the OPERATOR to route. NO ISSUE CREATED.

| ID | Gap | Evidence | Worked around how |
|---|---|---|---|
| **TG-1** | **No CLI surface updates a Mission's `purpose_tldr` / `purpose_context` after creation.** `spec-kitty agent mission` offers ten subcommands, none of which edits the stakeholder blurb, so it goes stale the moment the spec is revised. | `spec-kitty agent mission --help` (v3.2.5) | `meta.json`'s `purpose_context` hand-edited and re-validated as JSON — an edit to a tool-managed artefact, which the canonical-sources rule discourages |
| **TG-2** | **`CLAUDE.md:256` is stale on where repo-wide gates run.** It says *"Some repo-wide gates run only in CI's `integration-tests-core-misc` job, NOT in the `fast-tests-*` suites"*. Superseded by the `ci-topology-shrink` extraction; `tests/architectural/` now runs in the always-on `arch-adversarial` pole on 100% of PRs. The practical advice in that line remains sound. | `.github/workflows/ci-quality.yml:2007-2026`, `:1872-1875` | OD-004 resolved against the workflow file rather than the doc |
| **TG-3** | **No executable pre-filter coverage proof exists in this repository to follow.** Two byte pre-filters ship today — `_sole_door_scan.py:461-476` and `test_commit_target_kind_guard.py:186-188` — and both argue soundness in a comment only. | Read directly; no `test_*prefilter*` exists | R1a **sets** the precedent (NFR-002, SC-002b) rather than inheriting one |
| **TG-4** | **The repo's own shrink-only baseline is co-located with the artefact it bounds, has no generator, and has no co-edit guard.** `load_baseline(ALLOWLIST_PATH)` reads `charter_path_literal_baseline: 49` from the same file as the allowlist; the `token` field is documented as *"a FROZEN tool-derived string — never typed by hand"* but **no generator exists in the tree**. | `test_charter_path_literal_authority.py:116, 934-935`; `charter_path_literal_allowlist.yaml:25` | Not worked around — exact accounting makes the gate survivable. R1a states its own placement rule (FR-004) rather than copying |
| **TG-5** | **The DIR-013 / C-013 governance conflict** — see item 14. | — | Routed to the operator; unresolved by design |

**No `gh issue create` was run.** C-013 forbids it. TG items are routed to the **operator**, who opens
anything that needs opening.

### 11. WP01's OWN FINDINGS — carried here because they live only in docstrings inside `_home_pin_scan.py`

`record.md` is WP06's owned file, so WP01 could not write them and **nothing else owns carrying
them**. *A finding that lives only in a docstring is a finding the record does not have.*

**11a. The `key_member` / `Attribution` contract deviation.** The seam contract
(`contracts/home-pin-scan-seam.md`) specifies `key_member(site, chain) -> Member | None`. **That is
unsatisfiable**: `Member` carries `relpath`, which is unavailable from `site`/`chain`, and `key`,
while the same contract's key section says the key is formed *"Never inside `find_write_sites` or
`key_member`."* Both cannot hold. The implementer kept the positional signature and **narrowed the
return to `Attribution`**, with `member_key` composing at the boundary in `discover`. Adjudicated
**SOUND and the substitution FAITHFUL** (`WP01/review-cycle-1.md:86-92`). **The contract still needs
amending** — `-> Attribution | None`, and `Attribution` added to the public surface. Cycle 4 notes
two further undocumented public names, `Fragility` and `fragility_register`. **This amendment has not
landed and is R1b's to make.**

**11b. C-012(5)'s member-level substitution — the literal form RAISES ON 11 OF 40.** C-012(5) as
first written prescribed `_ratchet_keys.py`'s `assert_descriptor_unique_within_qualname` applied per
member. **Applied to the real tree it raises on 11 of the 40 members** — verified **independently in
review** (`WP01/review-cycle-1.md:94-105`), which enumerated all eleven. Cause: `code_tokens_by_line`
strips string literals, so `_isolated_home`'s three consecutive `monkeypatch.setenv` calls
(`SPEC_KITTY_HOME`, `HOME`, `LOCALAPPDATA`) collapse to **one** normalized token line of which
**only one is a member**. **Source-scoped descriptor uniqueness is not the property the clause wants:
it fires on sites the guard does not own.** The substitution — member-level key uniqueness over
`discover()`'s own output, raising `DuplicateMemberKeyError` at import, with `ContentDescriptor`
retained as the **diagnostic vehicle** — is the property the contract actually argues for. **The
contract needs amending to restate the mechanism at member level.**

**11c. The `NEEDLE_BYTES` derivation and the reason for it.** The needle ships as
`NEEDLE_BYTES = b'SPEC_KITTY_HOME'` with the **text derived from the bytes**, not written twice.
Reason: **the guard's own artefact is inside the guard's own population.** Mutating the module back
to a literal `NEEDLE = "SPEC_KITTY_HOME"` reds
`test_every_inert_sub_form_has_population_zero_over_the_real_tree[SC-002b]` at
`('architectural/_home_pin_scan.py', 105)`. The empty-set assertion is therefore **a live constraint
on this module, not a promise** (`WP01/review-cycle-1.md:107-114`). *(Constructed here:
`NEEDLE_BYTES == b'SPEC_KITTY_HOME'` at the freeze SHA.)*

**11d. `OWNER_PARAM_NAMES`'s PROVISIONAL status — and the binding DID land.** At WP01 cycle 1,
`canonical_home` was a **provisional** name that **no operand outside the module constrained**;
WP03/T012 was named as the closing obligation. **It landed, and it was constructed rather than
read**: the WP03 reviewer renamed the fixture in `tests/conftest.py` **and** the contract row to
`spec_home_owner` (a name absent from `OWNER_PARAM_NAMES`) and confirmed **both limbs bite
separately** — `test_the_declared_owner_name_is_a_member_of_owner_param_names` and
`test_the_owner_alias_limb_actually_fires_on_the_owner_name` both FAILED, while the contract-parse
limb stayed green (`WP03/review-cycle-1.md:72-97`). **FR-010's circularity is closed;
`canonical_home` was forced, not chosen.** *(Constructed here: `OWNER_KEY` in `_home_pin_exempt.py`
is `('conftest.py', 'canonical_home', …)`.)*

**11e. The `_corpus` `lru_cache` staleness caveat.** `_corpus` is `lru_cache`d on `(root, prefilter)`
and holds parsed trees for the session, so **re-writing the same root mid-session yields stale
results** — the shape that hits it is "the natural way to write a mutate-and-re-scan test". No test
hits it and no live consumer path reaches it (WP02's two `git archive` extractions use distinct temp
roots). Note **`discover()` does NOT share the cache while `inert_hits()` does.** Documented at
`_home_pin_scan.py:1030-1040`; carried here because a docstring is not the record.

### 12a. The four framework defects met in planning — CITED, NEVER RE-FILED

All four verified **OPEN** at the time of writing. **No issue was created; none was re-filed.**

| # | Defect |
|---|---|
| **#2991** | `finalize-tasks` silently drops `SC-###` from `requirement_refs` — success criteria are outside the requirement graph by construction |
| **#3170** | the `finalize-tasks` requirement-ID scraper reads prose and cannot distinguish a mission's own IDs from citations of another mission's |
| **#3226** | `tasks-outline` mandates `finalize-tasks --validate-only`, but that gate reads WP prompt files the next step creates |
| **#2642** | staged `tasks-outline` cannot advance because runtime still requires `tasks.md` (the exit guard masking a real failure) |

### 12b. THE STANDING OBLIGATION: WP01/T004's registry test parses FR-007's table out of THIS mission's `spec.md`

WP01/T004's registry test reads FR-007's table **out of
`kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/spec.md`**.

**Consequence, stated plainly: flattening or archiving the mission directory re-points a collected,
always-on test.** The test is not scoped to the Mission's lifetime — it runs on every push and PR via
`arch-adversarial`. Any future mission-directory hygiene sweep that moves, renames or archives this
path breaks a green gate for reasons that will look unrelated to whoever runs the sweep. **This is a
live coupling from the repository's test suite into a mission artefact, and it outlives R1a.**

### 13. THE RESIDUAL IN THE HALT ENFORCEMENT — it is PROCEDURAL

The lane machine blocks downstream WPs **only if an implementer performs two transitions correctly**:
leave **WP-0b at `for_review`**, and move **WP03..WP06 to `blocked`**. They must do this **at the
moment they have just learned the Mission is halting** — the single worst moment to expect two
correct discretionary state transitions.

**Marking WP-0b `approved` out of habit opens the gate.** Nothing prevents it. The enforcement is a
convention, not a mechanism.

**The collected verdict test is defence-in-depth BEHIND that, not the enforcement itself.** It reds
until the published artefact reads `proceed` or `proceed-degraded`, which gates all four packages at
once and cannot be skipped by whichever one starts first — but it is a second lock, and the first
lock is a human remembering two steps under bad conditions.

### 14. EVERY PRE-EXISTING RED met during implementation — ROUTED TO THE OPERATOR (C-009)

Pre-existing reds are **not this Mission's to fix** (C-009). **DIR-013's GitHub issue is the
operator's to open, and C-013 forbids the implementer opening it.** This is a **live governance
conflict between DIR-013 and C-013 that R1a does not resolve** — it is filed above as **TG-5** and is
**the operator's to adjudicate**.

**Red A — `tests/architectural/` wall-clock fragility.**
Command: `pytest tests/architectural/ -n auto --dist loadfile`.
Merge-base: **1 failed / 1850 passed** (975 s) — `test_wp_prompt_build_latency::…implement…` at
6.08 s against a 6.0 s budget.
Lane: **3 failed / 1917 passed** (922 s) — that red, plus `…review…` at 7.21 s, plus
`test_ci_quality_path_filters::test_core_misc_shards_plus_e2e_owner_cover_legacy_selection`.
Merge-base evidence: the named test **passes alone** on the lane branch (221 s at `-n0`); its
failure mode is a `_collect_nodes` subprocess wall-clock timeout **documented in that module's own
comment as a concurrency artefact**. **Not a semantic regression.**

**Red B — deselect control at the same parallelism** (`WP02/review-cycle-1.md:327-346`). Running
`tests/architectural/` at `-n8 --dist loadfile` with WP01's and WP02's three new modules **deselected
entirely** reproduces **the same three reds** — `3 failed, 1848 passed, 5 skipped, 2 xfailed in
954.96 s`. Same machine, same parallelism, everything else fixed. **This is the strongest form of
merge-base evidence in the Mission**: it holds the tree constant and removes only the diff.

**Red C — the terminology gate, since FIXED.**
`test_no_legacy_terminology.py::test_forbidden_term_does_not_appear[ceremony]` failed on
`test_home_pin_verdict_seam.py:769`, attributed by `git log -S` to **`ee4728edf` (WP04)**. **Fixed in
WP04 cycle 4**, which also swept a latent case-insensitive occurrence at `:202`. Recorded because of
what it revealed — see the blindness finding below.

**Red D — a baseline claim that DID NOT REPRODUCE, corrected here.** A prior pass reported
`check_docs_freshness.py` as **already red** on `feat/isolated-home-pin-guard` with
`REF-EXTRA doctor review-cycle-reconcile`, exit 1, one finding. **Constructed here, that does not
reproduce.** At HEAD `5d8111da8`, under the pinned interpreter, with this WP's files set aside:
`check_docs_freshness: exit=0 findings=6 errors=0 warnings=6` — **exit 0**, all six findings
`LINK-HEALTH-FAILED` warnings (offline network probes), **zero errors, no `REF-EXTRA`**. The
pre-existing-red list for this gate is **empty**, and the prior claim is withdrawn.

The prior pass's framing of *why* a pytest-shaped baseline capture misses this class of red remains
correct and is worth keeping: **a pytest-shaped baseline capture cannot see a gate-shaped red.** The
repo's docs gates are scripts run by a workflow, not collected tests; `chore: Capture baseline tests
for WP06` captured pytest. That is a real gap in the baseline method — it is simply not the case that
this particular gate was red.

### 15. OD-003's measured runner figure, with the contention headroom STATED rather than assumed

**The figure**: NFR-001's `3×` CI-runner factor is **a measured 1.86× two-machine spread, doubled**
for a runner nobody had measured. The discharge is to read the real figure out of the
`timing-nfr-serial` job — `blacksmith-4vcpu-ubuntu-2404`, `-m timing -n0`, `if: always()`, no filter
gate, no `needs:` edge, wired into `quality-gate.needs` so a red timing gate blocks merge.

**The contention headroom, stated not assumed**: `timing-nfr-serial` measures the guard
**UNCONTENDED**, while `arch-adversarial` runs it under `-n auto` on 4 vCPUs alongside three other
workers. **The serial figure is a FLOOR, not the worst case.** That is the correct trade — a
contended wall-clock assertion is a flake, not a gate — but **the budget must be raised against the
serial figure with the contention headroom stated explicitly, never silently assumed to cover both.**

**And the invariant that does not move**: **the budget may be raised with runner evidence; the walk
may NEVER be narrowed.** No directory filter, no filename filter, no `except SyntaxError: continue`.

---

## Carried forward (the three the DoD names)

**CF-1 — The ordering evidence from WP03/T010.** `MERGE_BASE_DEFINITION_NAMES` was verified by
**deriving the list from git rather than reading it** (`WP03/review-cycle-1.md:99-138`):
merge-base `9117219081c1f88cf0b90937b9cb46723ceebcd2` (matching the docstring),
`git show <merge-base>:tests/conftest.py` → AST definition names, **merge-base count 68, declared
count 68, EQUAL: True**.
**The self-reported defect is real**: the operand now derives from the author, not from git, so a
future implementer facing a red can regenerate it from the recipe in the constant's own docstring
and **green the ratchet with a reorder intact**. The neighbour-anchor test
(`test_the_owner_sits_between_its_named_ordering_anchors`) covers only `names[i-1]` / `names[i+1]`
and **sees nothing below the anchor**. Judged acceptable — NFR-005 constrains the diff under review
only, and a frozen baseline is this repo's idiom — but recorded as a real weakening.

**CF-2 — The pytest version from WP03/T012.** **pytest `9.0.3`, CPython `3.11.15`**, resolved via
the external pinned interpreter `/home/jeroennouws/dev/sk-missions/3157/.venv/bin/python`.
Invocation recorded verbatim: `… -m pytest <paths> -p no:cacheprovider -q -n0`. Explicitly: **no
`uv run`, no `uv sync`, no venv created inside this tree** (NFR-006). The measured `Failed` MRO is
recorded with it.

**CF-3 — The SC-002b figures from WP04/T020, and their DRIFT.** The criterion asserts the
**assignment-bound** `"SPEC_KITTY_HOME"` constant population is **0**, published against its
denominator — *the 229 is what makes the 0 meaningful.*
**The drift, stated as drift**: the spec published **229 occurrences in 98 files** over `src/ ∪
tests/`. WP04/T020 first documented **226/95** — which was **entirely a scope difference, not
staleness**: `tests/` = 0 bound / 226 / 95 and `src/` = 0 / 3 / 3, and `226 + 3 = 229`, `95 + 3 =
98`. **By WP03's landing the integrated tree measured 229 occurrences in 97 files**, the two new
hit-lines being WP03's owner (`conftest.py:338`) and probes
(`architectural/test_home_owner_never_wins.py:88,122`). So the figure moved **226/95 → 229/97**, and
the file count does **not** match the spec's 98 by the same arithmetic. WP04 cycle 2 fixed the
reporting to print **the scope in the line** — *"over src/ ∪ tests/ — src: 0/3/3; tests: 0/226/95"*.
**A denominator that moves when a package lands is a denominator that must be printed with its
scope**, which is what the repair does.

---

## Additional residuals this Mission would otherwise be read as having proved

These are not on the mandated list. They are recorded because each is a claim a reader would
otherwise infer.

**A. `test_no_legacy_terminology.py` is STRUCTURALLY BLIND to WP06 — a population-0 assertion with
no positive control.** `_EXCLUDED_PATH_FRAGMENTS` excludes **both `kitty-specs/` and `docs/adr/`** —
**which is exactly and only where WP06's two owned files live**. **Running that guard green proves
nothing whatever about either deliverable.**
**Constructed, not read**: the imported ADR sits in the tree carrying the forbidden term **twice**
(lines 102, 112) and `pytest tests/architectural/test_no_legacy_terminology.py` reports **10
passed**. The guard cannot see the file. This is the same shape as Red C, one level up: there, "124
repo-gate tests green" coexisted with a red terminology gate because **the six-file selection did not
include the module**; here the module runs and is blind by path. **Selection scope and exclusion
scope are two different ways for a green to mean nothing.**

**B. The `E` slot cost — and the correct names.** `E` is typed `tuple[Exempt, Exempt]`: a third entry
is a `mypy --strict` error, not a one-line literal. **Its two slots are the OWNER FIXTURE and the
MEMBER PROBE** — not two probes.
- Slot 1: **`conftest.py::canonical_home`**, the canonical owner, itself a member of the class it
  owns.
- Slot 2: **`architectural/test_home_owner_never_wins.py::retained_pin_home`** — the slot-costing
  member. Its own `why` (`_home_pin_exempt.py:67-85`) reads: *"Its non-member sibling
  `probe_home_pin` carries the falsifiability and costs no slot."*

**These are the real names.** "Probe (a)" and "probe (b)" are **not** names in the codebase; T030's
whole requirement is a labelled item findable **without reading the spec**, and invented labels
defeat it. The honest accounting: `retained_pin_home` **cannot bite** (item 3), the implementer had
**no discretion** (FR-011 mandates exactly one real-tree member probe; FR-004 types `E` at exactly
two), and `spec.md:546` already says *"an assertion that need not bite is not worth that price"*.
**Raised for adjudication, correctly not repaired in-package.**

**C. `frozen_at_sha` must name the MEASURED tree — and the guard caught it live.** The hazard is
procedural: `--frozen-at-sha $(git rev-parse HEAD)` names **HEAD**, which is not necessarily the tree
that was measured. **It was caught in real time, during review, when HEAD advanced to a status
commit** — a wrong `frozen_at_sha` reds T022's byte-identity check, which is how it surfaced.
**Record the incident with the residual: a guard that caught a real error in real time, during its
own review, is a non-vacuity datum worth more than the warning.** R1b inherits it because **R1b is
where regeneration becomes routine**, which is the only place the hazard bites.

**D. The partition's only external anchor is M4, at 28 of 40.** M4's `TABLES.md` is the **only
external label source** for `home_partition`, and it covers **28 of the 40** census rows. The
cross-check joins on `(rel_path, keyed-def qualname)` — **measured injective over the 40** — giving
**28 matches, zero unmatched**, with the disagreeing set asserted empty and a positive control
feeding a deliberately mislabelled row. **For the 12 members M4 does not label there is no external
anchor**, and manufacturing one would be the invent-an-oracle failure C-011 exists to prevent.
**Declining to invent it is the correct call, and it is a residual, not a gap that was closed.**

**E. WP04's two open findings, neither closed.** **[MED]** the self-exemption is **module-scoped**
while every stated reason is **construct-scoped** — a second copy of the digest, the exact thing
signal 2 exists to ban, can be added to either exempt module with **no `EXEMPT` row and no pin
regeneration**, so the external pin never sees it. It should **name the SIGNALS, not the
constructs**. **[LOW]** the pin's honest ceiling — **it buys diff-visibility, not tamper-resistance**
— is **absent from the module's own "what this guard CANNOT see" list**. Both carried to R1b.

**F. The `|R| ± 1` stability axis is provably DECISION-IRRELEVANT — a spec-level inert limb.** Two of
eight injected mutants survived, and they are the same limb: dropping the `|R|+1` axis, and dropping
the whole `|R|` axis, are **caught by NOBODY**. Proved rather than observed: over
`|R| ∈ [10, 4000]`, `|R_f| ∈ [0, |R|]`, the `|R| ± 1` axis **never changes a consequence class** —
zero differing states across 3991 window sizes. It is **measured and published** (both perturbations
`(32,33)` and `(33,34)` appear in the artefact) but **can never affect admissibility, at any window
size, ever.** §0.9 presents it as catching what *"a false pair moves `|R|`, not `|R_f|`"* — **true of
what is MEASURED, false of what is DECIDED.** WP02 implemented the spec faithfully; the inert limb is
the spec's.

**G. The floor is met by TWO AUTHORING EVENTS, not 33 independent ones.** The published walk shows
`|R| = 3` for **313 consecutive windows**, then 33 at the 314th. So **30 of the 33 arrivals landed in
a single first-parent commit** (`2bad3228…`, the #3030 governance-dossier landing: 101 files, 22124
insertions), and the other 3 are #3108. §0.9 says plainly the floor is *"a VISIBILITY floor, not
statistical adequacy"*, so this violates nothing — **but §0.3's own doctrine, "two points from one
landing do not define a rate", applies with equal force to a SAMPLE**, and the record is where that
gets said.

**H. The driver half of the gate has no test coverage.** `detect_renames`, `window_accepted`,
`measure_window`, `widening_walk`, `effect_class_sites`, `verdict_document`, `crosscheck_start_sha`
and `extracted_tests` are **referenced nowhere in `tests/` outside their own definitions**. The WP02
reviewer constructed the correctness proof by hand over eight cases, and recorded the residual in the
right words: **"nothing in the tree would notice if it stopped being right."**

**I. Aliased `ast` imports evade the seam ban.** `_ast_aliases` collects the **bound** name while
`_is_ast_member` compares the **original**, so `from ast import parse as _p, NodeVisitor as _NV`
evades T007's ban entirely. **Not a live violation — but one alias away from silent.**

**J. The framework regression gate was SILENT on WP01, not green.** `move-task` reported
`no_coverage — excluded scope — unverified`: both WP01 files land only in a catch-all group, so **the
gate ran nothing against that change**. The cycles' mutation evidence stands in for it. **A later
reader must not read that gate result as a pass.**

**K. The transferable finding, and the shape vocabulary.** Exactly **one** finding in this Mission is
explicitly self-identified as transferable (`WP01/review-cycle-4.md:20-37`), and it is stated so it
outlives the WP: **"every optional argument that changes an artefact needs a control that runs with
it PRESENT and asserts the artefact MOVED."** `--exempt-module` fed only `render_baseline`'s
`exempt=` hash and never the census, so census output was byte-identical with and without the flag
while `evaluate(...).ok` returned `True`. **It survived four approvals because WP01's only `main()`
test ran with the flag ABSENT** — a flag whose entire purpose is to change an output was never
exercised in the state where it changes it. The generalisation the reviewer drew is the one worth
keeping: **"the risk register is not the same thing as the surface area."**
A second, related contribution extends an existing four-shape self-audit vocabulary
(second-lock-same-door, untested branches, counted proxy, unapplied standard) with a **fifth**: a
**scope mismatch between a mechanism and its own stated justification**, visible only by reading the
`why` prose against the signal set it actually forgives.
*Recorded precisely because "four transferable findings" has been said of this Mission and is not
what the artefacts contain: one is labelled transferable, and the four-shape list is a pre-existing
taxonomy this Mission extended, not four findings it produced.*

**L. The reviewer's own instrument failed a "prove it can see" check.** The WP01 reviewer's mutation
helper had been silently overwritten by an unrelated harness that **exits 0 without editing the
file**, producing a false "2 passed" on both mutations. **Had that output been trusted, a genuinely
non-vacuous test would have been reported as vacuous.** The helper was rebuilt with a write-back
self-check before any conclusion was drawn. **Positive control before conclusion, including for the
reviewer's own tools.**

---

## THE HEADLINE FINDING — `census ∪ E` degenerates when `E ⊆ census`

Stated on its own because it is the finding the Mission spent itself closing, and because item 0's
trap is a restatement of it.

`test_t024_the_real_tree_is_set_equal_to_the_census_union_e` asserts
`discovered == census ∪ E`. **With `E ⊆ census`, that union is a NO-OP and the assertion degenerates
to `discovered == census`** — **the Mission's central accounting reporting success while checking
nothing.**

Verified by construction by the WP05 reviewer: regenerating the census **without**
`--exempt-module` (42 rows, `E ⊆ census`) and replaying all 25 tests against the defective artefacts
gave `total 25  RED 10  GREEN 15` with
`*** test_t024_the_real_tree_is_set_equal_to_the_census_union_e: GREEN` —
`unexpected=[] stale=[] census_hash_ok=True exempt_hash_ok=False`. **Both limbs of the famous
assertion were TRUE on the defective artefact.** What actually caught it was
`test_t022_neither_exempt_entry_is_a_census_row` and
`test_t023_the_census_equals_the_c011_anchor`.

**Constructed independently for this record**, against the shipped artefacts at the freeze SHA:

```
census rows: 40  in 36 files
frozen class: 42 in 38 files
frozen MINUS census: 2
    ('architectural/test_home_owner_never_wins.py', 'retained_pin_home', ...)
    ('conftest.py', 'canonical_home', ...)
frozen - census == E  ->  True
census u E == frozen  ->  True
census MINUS frozen   ->  set()
```

The accounting is correct **as shipped**, because `E` is kept **out of** the census. The residual is
that **the assertion which names the property is not the assertion that enforces it.**

---

## T028 / T029 — The #3121 update: the comment, and where it lives

**COMMENT URL**: <https://github.com/Priivacy-ai/spec-kitty/issues/3121#issuecomment-5261252413>

Recorded here so the publication is recoverable **from the Mission record** rather than only from
GitHub.

**Posted with `gh issue comment 3121`.** `gh issue create` was **NOT** run — C-013 bars it, and it
would mint the very `owed_to` ambiguity OD-001 decided against. **#3121 was OPEN before the comment
and is OPEN after it** (verified). Nothing was merged; no PR was un-drafted; no `gh pr merge`.

**Why #3121 and not a new issue (OD-001).** #3121 is live, assigned, and its subject **is** the
adjudication R1b will perform, so it is a creditor rather than a placeholder. The decision was made
**reversible at zero cost**: re-pointing `owed_to` is a *regeneration*, not a hand-edit, and because
the baseline hash is over the **sorted `composite_key` set** and not over the file, a mass re-point
changes no hash and needs no tombstone.
**What this cannot see**: whether #3121 is the right *scope* for 40 distinct adjudications. SC-003
can only check that `owed_to` is a well-formed reference and not prose.

### The seven items, and where each is discharged in the posted body

| # | DoD item | Section of the comment |
|---|---|---|
| 1 | the **three separately labelled** reach figures — never one merged ratio | §1 (plus the two-frame warning) |
| 2 | explicit **RETRACTION** of the struck 26.06% | §2 |
| 3 | **census-is-not-a-manifest** + its reviewer test, stated over *anything that makes a definition acceptable to the guard* | §3 |
| 4 | **§0.3's provenance correction**, incl. authored-versus-committed and the refusal to state a growth rate | §4 |
| 5 | **R1a adjudicates NOTHING** | §5 |
| 6 | **UNCONDITIONALLY** `r`, `|R|`, `|R_f|`, both window SHAs, **EVERY** attempted window **including the VOID at `709a59534` (`|R| = 3`)**, and the machine-readable band verdict | §6 |
| 7 | the window **MOVED**, and `28 -> 30` is **SUPERSEDED** — in those words | §7 |

*Item 6 is the historically-dropped one: the first revision enumerated four items that did not
include `r`, which made the publication obligation invisible outside the degraded band. FR-008 is
unconditional.*

---

## The comment body as posted (verbatim)

<!-- Reproduced so the record does not depend on GitHub remaining reachable. -->

```markdown
## R1a — the guard half: the reduced record

Mission `isolated-home-pin-guard-r1a-01KZNMA3`. WP01–WP05 approved; WP06 (the record) is this update.

**Every figure below carries its population AND the SHA it was measured at.** Two frames appear in
this Mission and they are not interchangeable — see item 1's warning.

---

### 1. The three reach figures — separately labelled, never one merged ratio

Measured at **baseline `5d49d31ed`** (spec §0.1/§0.8's frame), under the FR-001 predicate
(silhouette over the enclosing scope chain, **no decorator limb**):

| Figure | Value | What it means |
|---|---|---|
| members / effect-class **SITES** | **40 / 40 = 100%** | every `tmp_path/"home"` write site is inside a member |
| members / effect-class **FILES** | **36 / 36 = 100%** | every file carrying one is covered |
| members / **ALL** `SPEC_KITTY_HOME` pin sites | **40 / 191 = 20.9%** | the class is a fifth of all home pinning; the rest is other buckets, out of scope **by definition, not by blindness** |

These are three figures. **They are not combinable into one ratio**, and publishing a single merged
percentage is how an inherited figure becomes a gate.

**The second frame, and a numeral that means two different things.** At the census **freeze SHA
`fe5d492ed`** the same populations measure: **2752** `.py` under `tests/`, **111** byte-hit files,
**194** write sites, and **42 members in 38 files** — while the **census is 40 rows in 36 files**.

> ⚠️ **"40 in 36" is true at both SHAs and names a DIFFERENT POPULATION at each.** At `5d49d31ed` it
> is the **class**. At `fe5d492ed` it is the **census**, where the **class is 42 in 38**. The
> difference is exactly the two entries of the exemption set `E` — the canonical owner
> (`conftest.py::canonical_home`) and the retained-pin probe
> (`test_home_owner_never_wins.py::retained_pin_home`). Saying "the class is 40 at the freeze SHA"
> restates the Mission's own headline defect, the `census` / `census ∪ E` conflation. **Say *census*
> when you mean census.**

---

### 2. RETRACTION — the struck 26.06%

**"49 of 188 — 26%" is RETRACTED.** It was wrong in **both** numerator and denominator, and it was
stated as operator decision 1's entire justification.

- Of the 49 pin-bearing fixtures, **19 are not members** (7 pin bare `tmp_path`, 6 pin
  `tmp_path/"consent-home"`, and one each `"kittify"`, `"global_kittify"`, `"_home"`,
  `"trigger-home"`, `"runtime-home"`, `"spec-kitty-home"`).
- 188 counts `setenv` only, **excluding the 3 `os.environ[...]` assignments**.

**26.06% was a ratio between two populations, neither of which is the guard's domain.** It is
withdrawn and replaced by the three labelled figures in item 1.

Two further claims from the first revision are **struck as FALSE**: that the ten non-fixture effect
sites were *"structurally invisible to any form of this guard"* (all 10 carry the full
`(tmp_path, monkeypatch)` silhouette at their keyed def — they were **filtered out by the decorator
limb, not invisible**), and that *"three undecorated helpers [are] one decorator away from
membership"* (they resolve to `hangfix-home`, `<case>-home/.spec-kitty` and `env-root` — adding
`@pytest.fixture` makes them **fixtures, not members**).

---

### 3. The census is not a manifest — and the reviewer test

| | Manifest row (R1b) | **Census row (R1a)** |
|---|---|---|
| **Means** | may exist **forever**, because *\<measured cause\>* | **existed at SHA X**, **owed an adjudication** |
| **Is** | a decision — terminal | **debt** — transient |
| **Columns** | `reason`, mirrored at the definition site | `MemberKey`, `lineno` (non-authoritative), `kind`, `home_partition` — **no `reason`** |
| **Direction** | may grow when a cause is measured | **monotonically non-increasing**, mechanised |

The census can reach **zero**, and `census == ∅` is **R1b's definition of done** — one line,
checkable by anyone.

> **THE REVIEWER TEST, binding on every review of R1a and R1b — and stated over *anything that makes
> a definition acceptable to the guard*, NOT merely over a census row:**
>
> ### *What does this entitle its definition to?* — the answer must be **nothing**.
>
> Stated over census rows alone the test does not reach the owner singleton, the tombstone list, or
> any future allowance — **which is exactly how an exemption relocates out of the audited artefact
> and into the guard's own source.**

**`E` FAILS that test, and saying so is the point.** An entry in `E` entitles its definition to exist
forever, with no `owed_to`, no `frozen_at_sha` and no tombstone — strictly **more** than a census row.
No honest answer of "nothing" is available, because the owner must exist forever. The remedy is not
prose but mechanism: **`E` cannot grow** — fixed arity by type (`tuple[Exempt, Exempt]`, a third
entry is a `mypy --strict` error), hash-pinned outside the module that declares it, two entries, both
named above.

**The cost, stated honestly.** The predicate is strong; the **semantic content is empty**. The guard
proves *the class has not changed since SHA X*. It does **not** prove *any member deserves to be
there*.

---

### 4. Provenance correction (§0.3) — there is no observed arrival rate

A previous framing described the class as being re-created **at a rate**. **That framing is false and
must not be repeated.**

| Member | Arrival commit | **Authored** | **Committed** | PR |
|---|---|---|---|---|
| `test_sync_doctor_tracker_egress_3108.py::doctor_environment` | `970852644` | 2026-08-04 | 2026-08-10 | **#3108** |
| `test_tracker_egress_refusal_3108.py::_isolated_home_and_arming` | `161a0c179` | 2026-08-04 | 2026-08-10 | **#3108** |

**The authored-versus-committed distinction is the whole correction.** Both were members at the
commits that added them. `971fa0e3e` (authored 2026-08-07) and `b88d47728` (authored 2026-08-10) are
**last-touch, not arrival**. All four share committer date **2026-08-10 because the branch was
rebased before landing** — so **reading committer dates as arrival dates manufactures a four-day
spread out of ONE EVENT FROM ONE PR.**

> **There is no observed arrival rate. Two points from one landing do not define one, and this
> Mission REFUSES to compute one.**

What is true and sufficient: the class grew **28 → 30 in a single landing the halted baseline could
not see**, both arrivals are partition-B1 trap cases (verified against M4's labels), and the `HOME`
orphaned-binding trap rose **9 → 11** *(itself a correction: this read "7 → 9" for five passes, low
by two at both endpoints, against a definition that lived only on `spike/isolated-home-3121` —
importing the artefact is what falsified it)*.

---

### 5. R1a ADJUDICATES NOTHING

R1a is the **guard half**. It freezes a measured behaviour class and publishes the census. It does
**not** decide that any member should converge, should be deleted, or deserves to exist. **Every
adjudication is R1b's.**

Concretely: `|P| = 5` from the halted Mission is **not used, not inherited and not cited** here — it
was measured over **28** members at a merge-base predating #3108, under the superseded
decorator-limbed predicate, with two current members never ablated. **R1b must re-run that
measurement over the current class.**

---

### 6. The gate's outputs — published UNCONDITIONALLY, not only in the degraded band

**`verdict: proceed`** (machine-readable, from `research/home_pin_gate/verdict.yaml`).

- **|R| = 33**
- **|R_f| = 33**
- **r = 100%**
- **window START SHA** — `ba0db69ade41f0fd788adea360e03456caf0c3e4`
- **window END SHA** — `5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac`
- **band verdict — `proceed`** (machine-readable `verdict:` field)
- stability: **stable**. Perturbations `(R_f=32, R=33)` → `proceed-degraded` → `go`, and
  `(R_f=33, R=34)` → `proceed-degraded` → `go` — same consequence class as base.
- renames excluded: **0**; refused-ambiguous: **0**
- unpaired arrivals: **33**; unpaired departures: **0**
- start-SHA crosscheck against the independent C-011 instrument: **symmetric difference EMPTY**

**EVERY attempted window — 314 of them, including every discarded one:**

- **`{VOID: 313, proceed: 1}`**
- **THE VOID RESULT AT `709a59534a1b8aac7e55a1cf6f5d2106a32c31ea`: `|R| = 3` against a floor of 10.**
  This is the **stated** window, and it is VOID. It is published because it was attempted.
- **All 313 VOID attempts are `(|R|, |R_f|) = (3, 3)`.** The accepted attempt is at **index 313** —
  `ba0db69ad…`, `(33, 33)` — exactly **313 first-parent commits back** from the stated start SHA.
- **Lowering the floor to fit the window was REFUSED, explicitly, by the operator.**

**THE MEASUREMENT LEAKED, and this update says so rather than leaving a reader to infer it.** While
verifying the VOID finding, an **independent lens** measured **`r = 100%` at `|R| = 9, 33, 34`**
(≈300 / ≈600 / ≈2000 first-parent commits back). On that evidence the verdict was **already known to
be `proceed` before the gate ran**. **The gate's power to halt this Mission was spent when `r`
leaked**; it confirms a known answer rather than discovering one.

*Note those leaked `|R|` values came from the independent lens, **not** from the walk table — the
published walk contains only `|R| ∈ {3, 33}`.*

**What survives** is a published measurement under a **pre-committed rule whose stopping criterion
never reads `r`**: `window_accepted()` reads `|R|` and ±1 consequence-class stability **only**, never
the label or the band — verified against the code in review. A stable *halt* window would have been
accepted and the walk would have stopped there. **What is lost is the analyst's blindness, and that
is not recoverable.**

---

### 7. The window MOVED — and §0.3's `28 → 30` is **SUPERSEDED**

**The window moved.** The stated window `709a59534 → 5d49d31ed` is **VOID** (`|R| = 3`). The walk
widened, one first-parent commit at a time with **no attempt cap**, to
`ba0db69ade41f0fd788adea360e03456caf0c3e4 → 5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac`.

**§0.3's `28 → 30` figure is SUPERSEDED.** In that word — not "addressed", and not "re-derived".

The `28 → 30` growth was measured under the **superseded decorator-limbed predicate** across the
**stated** window. **Neither endpoint is recoverable under the current predicate, so it cannot be
re-derived at the moved SHA.** Under the current predicate the effect class grows **7 → 40** across
the **selected** window, and **37 → 40** across the stated one. `28 → 30` is retained by §0.3 as the
historical fact that motivated freezing, labelled as such, and **is no longer a statement about this
Mission's window.**

---

### What this update does not claim

The full residual record — the two vacuous success criteria, the `E` slot cost, the procedural halt
enforcement, the named escapes with their measured populations and the **explicit statement that
their enumeration is NOT claimed complete**, and every pre-existing red routed to the operator —
lives in `kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/record.md`.

Framework defects met in planning are **cited, not re-filed**: #2991, #3170, #3226, #2642. PR #3285
is **R1b's coordination dependency, not an R1a blocker**. **No issue was created for any of this**
(C-013); tooling gaps TG-1…TG-5 are routed to the operator in the record.

```
