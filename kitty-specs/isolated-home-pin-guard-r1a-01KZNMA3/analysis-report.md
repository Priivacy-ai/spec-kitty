---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
mission_id: 01KZNMA3ME8T2NTAHWZH2S3VX0
generated_at: '2026-08-11T15:17:57.145794+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/sk-missions/3121/kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/spec.md
    sha256: 065de067bd878e39e7facac30932c5208f9028bb051890c6e9fd27b7d05cd79e
  plan.md:
    path: /home/jeroennouws/dev/sk-missions/3121/kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/plan.md
    sha256: 9410e3a4ff088b3fbe99bb1eac794ad0d388ab08aea8c99cb6a130477b513807
  tasks.md:
    path: /home/jeroennouws/dev/sk-missions/3121/kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/tasks.md
    sha256: 3e5209ab3225b8b0c4ab603ffbc682262c445cba7964f8dc9fa8546264a9333e
  charter:
    path: /home/jeroennouws/dev/sk-missions/3121/.kittify/charter/charter.md
    sha256: 1bd09b6a66be218d6f0b4ef843c3fa4bf4aee04ec79af07cb7ce852c784444ea
verdict: unknown
issue_counts:
  info:
  critical:
  high:
  low:
  medium:
findings: []
---

# Cross-artefact analysis — `isolated-home-pin-guard-r1a-01KZNMA3`

**Mission** `isolated-home-pin-guard-r1a-01KZNMA3` · **Branch** `feat/isolated-home-pin-guard`
**Reviewed at** `dc809376e` · **Reviewer** reviewer-renata (profile-loaded, read-only)
**Recorded at** `a5a2402f4`, after the remediation this report prescribes.
**Delta review at** `cdc8801f4` (2026-08-11) — see §8. **Verdict unchanged: READY.**

## Verdict

**READY** for `spec-kitty implement WP01`.

All six work packages are `planned`; WP01 has no dependencies and is claimable. Every artefact WP01
needs exists, every anchor it cites resolves, and its four measured preconditions hold. Nothing in
this review blocks the first `implement`.

Two findings blocked **later** lanes (WP02, WP05) and one sat inside WP01/T004. **All were
remediated before this report was recorded** — see *Disposition* below.

**Re-affirmed over the delta of 2026-08-11 (`204c6307f` → `cdc8801f4`), for WP02.** WP01 was
implemented, reviewed across two cycles and approved; six commits amended the mission directory.
Nothing in that delta invalidates a WP02 Definition of Done, and **one amendment removed a latent
WP02 blocker**. The four findings the delta left standing are all LOW/MEDIUM and all land on WP03,
WP04, WP05 or WP06 — **none on WP02, which is the halt gate and next in sequence.** Full derivation
in §8.

## Directives and tactics applied

Profile directives (doctrine namespace): **DIR-001** architectural integrity, **DIR-024** locality
of change, **DIR-030** test/typecheck gate, **DIR-032** conceptual alignment, **DIR-041** tests as
scaffold. Project charter directives: **DIR-010/DIR-011** identifier safety, **DIR-013**
pre-existing failure reporting. Tactics: `code-review-incremental`, `language-driven-design`,
`reverse-speccing`, `test-readability-clarity-check`, `delete-the-assertion-not-the-test`.

Note a namespace collision worth recording: the **profile** returns doctrine IDs `DIR-001/024/030/032/041`
while the **charter** returns project IDs `DIR-001…DIR-013` with entirely different titles. Both sets
were applied, disambiguated by source.

## 1. Population claims — all twenty reproduced

Figures were not read; they were rebuilt by an independently written classifier (stdlib only,
authored from the spec's predicate text), run after confirming `tests/` is byte-identical to the
baseline (`git diff --stat 5d49d31ed HEAD -- tests/` is empty).

| # | Claim | Published | Measured |
|---|---|---|---|
| 1 | `.py` under `tests/` / parse failures | 2737 / 0 | **2737 / 0** |
| 2 | byte-hit files `b"SPEC_KITTY_HOME"` | 100 | **100** |
| 3 | all write sites | 191 = 188 `setenv` (83 files) + 3 `environ` + 0 `setdefault` | **identical** |
| 4 | the 3 `environ`-assign sites | `test_no_legacy_path_literals.py:94,112`; `test_ensure_runtime_concurrent.py:43` | **identical** |
| 5 | value buckets | global 42/3f · home 40/36f · kittify 17/4f · bare 10/10f · home/.kittify 8/2f · consent-home 7/7f | **identical, all six** |
| 6 | members (FR-001 predicate) | 40 in 36 files | **40 in 36 files** |
| 7 | `kind` at keyed def | 30 / 10 / 0 | **30 / 10 / 0** |
| 8 | `kind` at innermost (withdrawn split) | 30 / 9 / 1 | **30 / 9 / 1** |
| 9 | members under innermost attribution | 39 | **39** |
| 10 | `HOME` sites unfiltered | 85 in 50 files | **85 in 50 files** |
| 11 | `HOME` sites pre-filtered | 52 in 29 files | **52 in 29 files** |
| 12 | `home_partition` over the 40 | A=27 / B1=11 / B2=2 / other=0 | **identical** |
| 13 | members re-pinning `HOME` | 13 of 40 | **13** |
| 14 | literal `"SPEC_KITTY_HOME"` constants, `src/` ∪ `tests/` | 229 in 98 files | **229 in 98 files** |
| 15 | assignment-bound such constants | 0 | **0** |
| 16 | distinct bare 2-tuples over the 40 | 19 | **19** |
| 17 | distinct 3-tuples over the 40 | 40 | **40** |
| 18 | 3-tuple injectivity over all 191 sites | 190 distinct, 1 class of 2 | **190 distinct** |
| 19 | `setdefault` / bare-name `setenv` population | 0 / 0 | **0 / 0** |
| 20 | pin-bearing fixtures / with explicit `scope=` | 49 / 0 | **49 / 0** |

**One apparent discrepancy reconciles rather than contradicts.** The independent instrument reported
**4** UNRESOLVED sites where FR-001 publishes **3**. The fourth is
`tests/audit/test_no_legacy_path_literals.py:94`, which FR-010 separately names as the live
population-1 `runtime_home` shape — unresolvable only to a resolver that has *not* implemented
FR-010's owner-parameter limb, which the independent instrument had not. That is independent
confirmation that FR-010's limb is load-bearing rather than decorative.

**Repository anchors, verified by construction:** `anchoring.py:220` `composite_key` ✓ · `:242`
`composite_key_from_file` returns `tuple[str, str]` ✓ · `:192-195` the `except SyntaxError` swallow ✓ ·
`tests/conftest.py` `_isolated_worker_home` decorator 253 / def 254 / end 298 ✓ ·
`_enable_saas_sync_feature_flag` 301-304 ✓ · `:272,:286` precedence docstring bounds ✓ ·
`pyproject.toml:246` per-file-ignores ✓ · `tests/_arch_shard_map.py:419` `default_fallback=True` ✓ ·
`_shard_registry.py:181` hash-bucket ✓ · `pytest.ini` has `testpaths` and **no** `python_files` ✓ ·
`_gate_coverage_baseline.json` `orphan_files: []` ✓ · `time.time()` in `_BANNED_CALLS` ✓ ·
`worktree_allocator.py:462-472` printed-warning degradation ✓ · `dependency_graph` admits only
`approved`/`done` ✓.

**WP01 preconditions:** `Exempt`, `MemberKey`, `Member`, `INERT_LIMBS` are defined **nowhere** under
`tests/` or `src/`; none of the eleven owned files exists; the halt-path ADR is absent on HEAD and
present on `spike/isolated-home-3121`.

**Identifier safety:** U+2011 survives in `spec.md` only (parent-ID citations), zero occurrences in
any other artefact, and zero ASCII-hyphen phantom IDs anywhere. No scrape hazard reintroduced.

## 2. Definition-of-Done fidelity

`wps.yaml`'s `definition_of_done` / `not_done_if` / per-subtask `dod` are binding planning content;
the prompt bodies restate them **in substance, not verbatim**, and nothing mechanically binds the two.

A prose matcher cannot separate paraphrase from divergence. The comparison was therefore made over
**normative tokens** — backticked identifiers, multi-digit numbers, ALL-CAPS emphasis — on the
reasoning that paraphrase preserves identifiers and numbers while a dropped clause loses them.
Across 30 subtask DoDs plus 46 WP-level clauses: **1201 tokens, 76 apparent absences (6.3%), all 76
resolved by hand.**

- ~60 are extractor artefacts — markdown line-wrapping splits a backtick span across two lines.
- ~14 are ALL-CAPS emphasis re-rendered as bold lowercase.
- 2 are deliberate **relocations that strengthen**: WP05/T023's "`discover()` returns 42 keys, not 40"
  moved into WP05's Context block where it is read before any subtask; WP02/T009's abstract
  `move-task <WPID> --to blocked` expanded into four concrete commands in the halt banner.

**Conclusion: no prompt has weakened, dropped, or subtly restated a `wps.yaml` DoD clause.** The six
highest-weight subtasks were read side by side and are faithful: WP01/T003 (identity vs attribution,
all 54 tokens), WP01/T004 (the completeness quadruple), WP02/T008 (verdict limbs (a)–(g)), WP03/T013
(the two probes and the `E` slot), WP04/T016 (the eight SC-006 transitions), WP05/T023 (the three
census assertions). The single place a prompt diverges from `wps.yaml`, it **corrects** it.

## 3. Requirement coverage

| | |
|---|---|
| FR/NFR/C defined in `spec.md` | **31** (FR-001…011, NFR-001…006, C-001…014) |
| SC defined | **15** (SC-000, 001, 002, 002b, 003…013) |
| Defined but not claimed by any WP | **0** |
| Claimed but not defined | **0** |
| SC traceable through `wps.yaml` | **15 / 15** |

All 46 IDs are claimed by ≥1 WP and discharged by ≥1 subtask DoD.

**Caveat recorded during remediation:** the coverage audit that first returned this result used
substring matching and was falsely green. Over this mission's vocabulary there are **21 ordered
substring-contained pairs** — 14 `C-0NN` ⊂ `SC-0NN`, 6 `FR-00N` ⊂ `NFR-00N`, 1 `SC-002` ⊂ `SC-002b`
— so 21 of 46 IDs were falsely greenable. Re-run with word boundaries (trailing guard
`(?![0-9]|[a-z](?![a-z]))`, since a plain `\b` truncates `SC-002b`), three IDs were uncited: WP01
`C-013`, WP03 `FR-006`, WP04 `C-002`. All three are now cited at the point of discharge, and the
corrected matcher ships with ten of its own positive and negative controls.

## 4. Findings and disposition

Every finding below was **remediated before this report was recorded**. Commits: `f0387bbc7`
(the four unswept artefacts), `095e1719f` (tasks layer), `a5a2402f4` (SC-010 satisfiability).

### HIGH

**H1 — `data-model.md` `Verdict` table omitted `start_sha_crosscheck`** while WP02/T006 binds the
emitted document's key set to **equal** that table, and T008(e)/T009/`not_done_if` all require the
key present. *Resolved:* the row was added with sub-fields `instrument`, `start_sha`,
`symmetric_difference`, `explanation`. T006's set equality was **not** relaxed to containment.

**H2 — `quickstart.md` published the regeneration command without `--exempt-module`**, the form
WP05's `not_done_if` names as a failure; FR-004(2) requires both artefacts to carry a header naming
*one* literal, and two were documented as the one. A WP05 implementer following quickstart would
generate a census containing the owner and fail T023. *Resolved:* corrected to T022's literal with
the freeze-SHA placeholder and the reason stated inline.

### MEDIUM

| | Finding | Disposition |
|---|---|---|
| M1 | `contracts:45` `find_write_sites` carried the `withitem`/`:1165` rationale §0.8 struck as FALSE, in a contract WP01's prompt calls normative | struck; replaced with the measured statement (receiver-agnosticism on the call is the discriminator; `withitem`-bound-receiver *resolution* has population 0 and is registered inert) |
| M2 | `contracts:44` `resolve_value` listed 4 value forms where FR-001 now has 8 | extended to eight, each noted as carrying a positive control |
| M3 | `contracts:18` granted WP-b a right to extend `_home_pin_scan.py` that ownership, lane scope and two `not_done_if` clauses forbid | changed to "WP-b / WP-c — Import and invoke. Never edit" |
| M4 | `plan.md:213` (IC-04) carried struck FR-004 limb (a) | replaced with FR-004's successor sentence |
| M5 | `plan.md:198-199`, `:859` repeated the owner `None`/`tuple[str,str]` conflation FR-005 struck | `tuple[str,str]` attributed to `E`'s entry; `return None` left as the fixture's contract |
| M6 | `plan.md:206`, `:859` described SC-010 as a scalar definition **index**, which WP03's `not_done_if` names as a failure | both updated to the ordered-list form |
| M7 | `plan.md:855` said `SC-006 ×7`; there are **eight** transitions | corrected |
| M8 | IC-08 listed five limbs, omitting OD-004's positional-anchor ratchet — the constraint on `E`'s literal form | inserted as limb 3, renumbered to six, §11(8) corrected |
| M9 | T004's `spec_table` operand was not externally derivable: FR-007's table had **8 rows and no id column**, one cell packing four sub-forms and one row anaphoric, against a 15-element control set | FR-007's table gained a canonical `id` column with **fourteen one-sub-form rows**; verified by executing the parser — `spec_table_ids ∪ {SC-002b}` = 15, `inline_expected − spec_table_ids = {SC-002b}` |
| M10 | WP02's DoD misstated the lane mechanism (`lane-c` depends on `lane-b`, not `lane-a`; the allocator takes no transitive closure) | restated from the measured graph; the conclusion now rests on the true mechanism — two hops, each with a soft failure — which strengthens the case for WP03/WP04's explicit precondition |

### LOW

`MemberKey` triples (not "pairs") in `plan.md` and `quickstart.md`; R6's consolidated resolver table
extended to eight forms; R4's second finding marked `[WITHDRAWN]` in place; `anchoring.py:173,211`
citation corrected; `data-model.md`'s "non-tunable" qualified against §0.9's widening schedule;
`FR-006` and `C-002` cited by ID where discharged.

### Found by the prescribed sweep, beyond the review

`spec.md` was **not** clean either: SC-010 itself, NFR-005, and US2 acceptance scenario 2 all still
prescribed the scalar definition index that the tasks layer's `not_done_if` bans — the definitions
the plan's copies derive from carried the same defect. All corrected to the ordered list.

That correction then produced a defect of its own: *"the ordered list is unchanged"* is **literally
unsatisfiable**, because FR-005 requires WP03 to add the owner to `tests/conftest.py`. A criterion
that could not fail became one that could not pass — same axis, opposite end — and the cheapest
repair for an implementer hitting it leads straight back to the scalar form. Corrected on all four
surfaces to *"the ordered list of definition names, **with the newly-added owner removed**, is
unchanged"* — one known addition, then exact equality; not "ignore differences", but exactly one
named definition removed with everything else matching **including ordering on both sides of the
anchor**.

## 5. Implementability of the first lane

**WP01 is one session's work, with T004 as the long pole.**

| Subtask | Assessment |
|---|---|
| T001 walk, pre-filter, `parse_module`, shared types | Mechanical. The self-AST `except SyntaxError` check plus its positive control is the only subtlety. |
| T002 resolver + write-site finder | The bulk of the algorithm — 8 value forms, 3 write forms receiver-agnostic, 2 env keys. Real work, not deep. M1's contract correction removes the trap. |
| T003 keyer, `discover()`, identity vs attribution | The most reversible decision in the mission. The `{fixture:30, test-body:10, helper:0}` vs `{30,9,1}` assertion gives a **local** red, so getting it backwards surfaces in WP01 rather than in WP05. |
| T004 registry + quadruple | **The long pole.** Fifteen ids × (empty-set assertion + positive control) = 30 checks over materialised modules, plus the spec-table parser. |
| T005 generators | Contained. The invariant/invariant/changes triple is three tests. |

Nothing in WP01 depends on an artefact that does not exist. WP01's `mission_dir_artifacts` is empty,
so it writes only its two owned files, both inside lane-a's write scope.

## 6. Known and accepted (not defects of this mission)

- **`SC-###` refs are erased from every WP prompt's frontmatter.** `_flush_frontmatter_writes`
  replaces the list with the `\b(?:FR|NFR|C)-\d+\b` subset rather than skipping it — a delete, not a
  drop. `wps.yaml` retains all 15 and is the surviving record; the ids still appear in prompt bodies.
  Upstream **#2991** (measured evidence posted).
- **`agent` is stripped from every prompt frontmatter** by the same rewrite, though Step 4a of the
  canonical template instructs writing it. Same cause; reported on **#2991**.
- **`finalize-tasks --validate-only` writes `tasks.md`.** Upstream **#3221**.
- **`analysis-report.md` is required by the implement gate but produced by no step.** Upstream **#2582**.
- **`.kittify/overrides/missions/software-dev/command-templates/tasks-packages.md` is stale** and wins
  over the built-in per `resolver.py:154`, lacking Step 4a, the `plan_concern_refs` guard and the
  profile-load section. The built-in was followed deliberately. Operator decision pending.
- **The gate's verdict is already known to be `proceed`** (`r = 100%` at candidate windows; recorded
  in §0.9). WP02 confirms a known answer rather than discovering one.
- **Halt enforcement is procedural, not structural** — recorded in WP02's banner, WP02 Risks and
  WP06/T030. The framework offers no way to make a lane transition conditional on a test.
- **Parent-mission IDs use U+2011 deliberately** to defeat the scraper (upstream **#3170**, whose
  silent mode attributed the parent's `C-009`/`C-010` to R1a's own same-numbered constraints). Never
  normalise them to ASCII.

## 7. What is clean

Stated plainly, because after two adversarial gates a clean result is the expected outcome and
inventing findings would be worse than none: twenty of twenty population claims reproduce exactly on
an independently constructed classifier; requirement coverage is complete with zero orphans and zero
phantoms; no prompt weakens a `wps.yaml` DoD across 1201 normative tokens; the lane graph is sound
and matches `wps.yaml` exactly; identifier safety is intact.

The findings clustered in one place, and it was a coherent place: **`plan.md`'s concern map,
`contracts/home-pin-scan-seam.md`, `quickstart.md` and `data-model.md` were written before the last
four remediation rounds and were not swept afterwards. `spec.md`, `wps.yaml` and the six prompts
were.** That is `spec.md`'s own named recurring defect — *a rule changed in one section, its
consequences left standing in others* — applied to the sweep discipline itself, and `spec.md`
already prescribes the fix: after changing any derivation rule, grep the derived figures.

## 8. Delta since `204c6307f` — 2026-08-11, at `cdc8801f4`

**Scope.** This is a delta review, not a re-run. The twenty population claims of §1 were not
re-derived: nothing in the delta touches the classifier's inputs (`git diff --stat` over
`204c6307f..cdc8801f4` shows no file under `tests/` or `src/`). Six commits touch the mission
directory — `dd0a1ceef` (contract + C-012(5) amendments), `507279f91` (four tasks-layer
follow-ups), `7d3539910` (FR-010's anchor), `2d7563cdf` / `cdc8801f4` (WP01's two review cycles),
`842882364` (the VCS lock). `spec.md` changed in exactly three hunks: FR-001's UNRESOLVED-site
sentence, FR-010's row, and C-012(5).

### 8.1 Verdict on the delta

**READY holds, and specifically for WP02.** Checked constructively rather than by reading: WP02's
prompt and its `wps.yaml` entry were read against the **current** contract, spec and shipped WP01
module (lane-a `75d790885`), and each DoD clause traced to the artefact that satisfies it.

### 8.2 The C-012(5) amendment REMOVED a WP02 blocker

The struck mechanism — `assert_descriptor_unique_within_qualname` applied per member — **raises on
11 of the 40 members on the real tree** (verified independently by the requesting operator and in
WP01's review cycles; not re-derived here). WP02/T006 calls `discover()` on a `git archive`
extraction **once per window across an unbounded first-parent walk**. Under the pre-delta
prescription every one of those calls would have raised, and WP02 could not have run at all. The
member-level restatement has population **0** on the current tree and is what WP01 shipped
(`_assert_exactly_one`, keyed on `MemberKey`, `ContentDescriptor` retained as the diagnostic
vehicle only). **The amendment is load-bearing for the package it precedes, not cosmetic.**

### 8.3 `key_member → Attribution` does not reach WP02

`key_member` appears **nowhere** in WP02's prompt or its `wps.yaml` entry; WP02 consumes
`discover()` and `MemberKey`. Constructive check against the shipped module:

- `discover(root: Path, *, prefilter: bool = True) -> set[Member]` matches the contract verbatim.
- `Member` carries exactly the four fields T006's rename detector keys on — `resolved_value`,
  `params`, `kind`, `relpath` — plus `key` and `lineno` for T008(g).
- `MemberKey`'s composition, `(relpath_posix, *composite_key_from_file(path, lineno))`, is
  **untouched** by the delta, so T008(g)'s recomputation formula stands unchanged.
- `_home_pin_scan.py` imports neither `subprocess` nor any git surface, and has **no module-level
  `discover()` call** — both limbs of T007 are satisfiable against the module as shipped.

### 8.4 §0.9 and WP02 agree on the amended widening schedule

§0.9 was **not touched** by the delta. It reads: walk `upstream/main`'s first-parent history one
commit at a time, **no attempt cap**, stopping at the first SHA where **both** `|R| >= 10` and ±1
consequence-class stability hold, with the defined exit at the **root of first-parent history**, at
which the operator decides. WP02/T006(6) restates all four elements; T006(7) and the `not_done_if`
both pin the stopping rule to `|R|` and stability, **never `r`**. That independence is intact and is
the only thing still protecting a verdict already known to be `proceed`. The 806-state oracle
reconciles: `Σ(|R|+1)` for `|R| ∈ [10,40]` = **806** = 380 go + 364 halt + 62 inadmissible.

### 8.5 Requirement coverage, re-measured against the changed `wps.yaml`

| | |
|---|---|
| Defined in `spec.md` | **46** — 11 FR + 6 NFR + 14 C + 15 SC |
| Claimed via `requirement_refs` | **46 / 46** |
| Discharged in `definition_of_done` / `not_done_if` / `subtask_details` | **46 / 46** |
| Defined but not claimed | **0** |
| Claimed but not defined | **0** |
| SC traceable through `wps.yaml` | **15 / 15** |

Matcher: `\b(?:NFR|FR|SC|C)-\d{3}[a-z]?(?![0-9]|[a-z](?![a-z]))`, shipped with **15 controls, all
passing**, covering all three contained-pair families — `C-0NN ⊂ SC-0NN`, `FR-00N ⊂ NFR-00N`, and
`SC-002 ⊂ SC-002b` (a plain `\b` truncates the last). **§3's result survives the `wps.yaml`
change.**

### 8.6 The delta's new golden-count claim is TRUE, and it binds WP02

Verified with the guard's own primitives on `HEAD` (`convert_counts_by_dir(scan_repo())` against
`_golden_count_baseline.json`): `tests/architectural` = **25 un-escaped convert-classified sites
against a frozen ceiling of 25 — headroom exactly 0**. WP01's two lane-a files add **zero** (one
site, escaped), so lane-b's base inherits zero headroom. **WP02 trips
`test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline` on its first
`len(x) == N`.** The clause `507279f91` added is accurate and the "may not be re-frozen" instruction
beside it is the right one.

### 8.7 Findings the delta left standing

Same shape every time, and it is the mission's own named signature: **a rule changed in one place,
its consequences left standing in others.** None blocks WP02.

**M-D1 (MEDIUM — WP03, WP05; §2 qualified).** Four clauses `507279f91` added to `wps.yaml` were
mirrored into the prompts **at a lower binding level than they hold in `wps.yaml`**:

- the golden-count clause is a **`definition_of_done`** entry for WP02–WP05 in `wps.yaml`, but
  appears in each prompt only as a **Risks** row;
- WP03's new `not_done_if` (*the owner contract's fixture name must be asserted against
  `_home_pin_scan.OWNER_PARAM_NAMES`*) is **absent from WP03's "Not Done If"**; the substance is in
  T012's item 6 prose only;
- WP05's new `not_done_if` (*the `tests/` prefix mismatch must not be repaired by editing
  `members.json`*) is **absent from WP05's "Not Done If"**; the substance is in T023's item 4 prose
  only.

§2 certified that *no prompt weakens, drops or subtly restates a `wps.yaml` DoD clause*. As of
`cdc8801f4` the **content** is present everywhere, but the **binding level** diverges in four
places. For WP02 the clause is the first Risks row with its mitigation stated, so nothing is lost;
for WP03 and WP05 a reviewer working the prompt's gate sections will not see the new gates.

**L-D2 (LOW — WP03, WP06).** The same commit introduced duplicate list numbering: WP03/T012 now has
**two items numbered `6.`** (the FR-010 circularity assertion and the pre-existing NFR-006 item),
and WP06/T030 has **two numbered `12.`**. Compounding it, WP03's Reviewer Guidance still directs the
reviewer to *"the contract-parsing binding in T012(5)"* and was **not extended to the new item** —
so the assertion `wps.yaml` now names as a `not_done_if` gate is absent from WP03's Not Done If
**and** from its Reviewer Guidance.

**L-D3 (LOW — WP04, SC-006).** *"The **live population-1** `runtime_home` shape"* survives in four
places after `7d3539910` restated that same shape as **population 0 at member level**:
`spec.md:452` (**inside FR-010's own row**), `spec.md:530` (SC-006 transition 6), `wps.yaml:722`
(WP04), `tasks/WP04-guard-prefilter-budget.md:147`. It is not false — exactly one def in `tests/`
declares `runtime_home`, so the *shape* is population 1 — but "population 1" is the **middle,
superseded stage** of the row's own three-stage narration (*manufactures → widens an existing escape
at population 1 → population 0 at member level*), and it is being used as the live descriptor by the
very edit that superseded it. One clause fixes all four: *population-1 as a **shape**, population 0
as a **member***. Does not reach WP02; should be closed before WP04 is claimed.

**L-D4 (LOW — wording, not code).** The amended C-012(5) is stated *"at import"* in `spec.md`,
`data-model.md` and the contract, but WP01 implements `_assert_exactly_one` **inside `discover()`**.
Per-call is the **correct** placement — an import-time real-tree scan would contradict FR-009's root
parameterisation and load NFR-001's budget onto every importer, including WP02's
`_home_pin_gate.py`. The wording is the stale part, not the code.

**L-D5 (LOW — code; carry to WP06/T030).** The shipped `discover()` docstring still attributes the
uniqueness check to *"the repository's D-1 rule (`assert_descriptor_unique_within_qualname` /
`ContentDescriptor.occurrence`)"*, while `_assert_exactly_one`'s docstring twenty lines below
records that primitive's predicate as **measurably false and explicitly not used**. Two adjacent
docstrings on one mechanism, opposite claims — in the module WP02–WP05 all import. WP06/T030 already
carries *"C-012(5)'s member-level substitution"* as a finding to record; this contradiction is a
separate live one.

**L-D6 (LOW — residual, WP02).** `discover()` now raises `DuplicateMemberKeyError` at member level,
and T006 calls it on `git archive` extractions at **arbitrary historical SHAs** across an unbounded
walk. The population-0 measurement is on `HEAD` only; nothing bounds it at a historical window, and
neither §0.9 nor WP02 says what the walk does if a window raises. **Not a blocker** — the failure is
loud, not silent, so it cannot green the gate for the wrong reason (DIR-041). T006 should treat a
raise exactly as it treats a timeout: **a datum**, recorded as an attempted window, never retried
into a different answer.

**INFO.** `Attribution` is now a type on the contract's public surface but is defined in no planning
artefact. This is consistent with existing practice — `data-model.md` types the persisted and
compared records (`Member`, `Exempt`, `CensusRow`, `Baseline`, `Verdict`) and does not type
`WriteSite` either — so it is recorded, not raised.

### 8.8 What the delta corrected in this report

§1's reconciliation of the fourth UNRESOLVED site is **strengthened**, not falsified. FR-001's
amended row now names `tests/audit/test_no_legacy_path_literals.py:112` explicitly as the second of
`_capture_nudge`'s two writes, and FR-010 states that `:94` resolves to the bare parameter and
`:112` is unresolvable — which is exactly the 3-versus-4 split the independent instrument produced.
One qualification carries over from **L-D3**: §1 calls `:94` *"the live population-1 `runtime_home`
shape"*; read that as **population 1 as a shape, 0 as a member**. No other claim in §§1–7 is
falsified by the delta.
