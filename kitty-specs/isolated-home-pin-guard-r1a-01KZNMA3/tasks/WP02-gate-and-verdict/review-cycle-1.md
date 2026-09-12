---
affected_files:
- path: tests/architectural/_home_pin_gate.py
- path: tests/architectural/test_home_pin_seam_no_second_copy.py
- path: tests/architectural/test_home_pin_gate_verdict.py
cycle_number: 1
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-11T19:44:44+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP02
---

# WP02 (WP-0b) — the halt gate — review cycle 1

**VERDICT: APPROVED.** The gate's `verdict: proceed` stands. WP03..WP06 are not blocked.

Directives applied (resolved via `spec-kitty agent profile show reviewer-renata` and
`spec-kitty charter context --action review --json`): **DIR-001** (architectural integrity /
component boundaries — C-003 containment, the no-second-copy seam), **DIR-024** (locality of
change — the diff adds six files and edits none), **DIR-030** (test and typecheck quality gate —
ruff, `mypy --strict`, the architectural suite at two parallelisms), **DIR-032** (conceptual
alignment — mission vocabulary against `spec.md` §0.9 / `data-model.md`; Terminology Canon check
for `feature`), **DIR-041** (tests as scaffold, not friction — mutation testing, positive-control
verification, the tunable-ratchet question). Project **DIR-005..DIR-009** (code review checklist)
and **DIR-013** (pre-existing failure reporting) also applied; DIR-013 is in live conflict with
C-013 and is recorded below rather than resolved. Tactics applied: `code-review-incremental`,
`reverse-speccing`, `test-readability-clarity-check`, `delete-the-assertion-not-the-test`,
`language-driven-design`.

Method note: every load-bearing claim below was **constructed, not read** — the oracle was
re-derived from `spec.md` §0.9 independently, the 314-step walk was re-run from a different
repository root, the seam guard's evasion was materialised, the rename detector was exercised
directly, and the baseline reds were reproduced under a deselect control.

---

## 1. The four raised deviations — adjudicated

### (1) `R` drawn over the EFFECT CLASS, not over `discover()`'s member difference — **CORRECT**

This is the WP's most consequential judgement and it is right.

`spec.md` §0.9 defines `R` as *"the sites **resolving to `tmp_path/"home"`** present at the end SHA
and absent at the start SHA"*, and `R_f` separately as *"the members of `R` the FR-001 predicate
catches"*. Two populations, explicitly. `discover()` returns members only, so differencing it
gives `R = R_f` and `r ≡ 1` **by construction** — the instrument would measure nothing. The
implementer's reading is the only one the text admits.

**It is not a second implementation.** `_home_pin_gate.effect_class_sites` (`:345-371`) is
`_home_pin_scan._scan_records`'s pipeline with exactly one stage removed:

| stage | `discover()` (`_home_pin_scan.py:840-852, 855-871`) | `effect_class_sites` |
|---|---|---|
| file walk | `enumerate_py_files` → `byte_prefilter` | same primitives |
| parse | `parse_module` | same |
| bindings | `module_level_bindings` → `bindings_for_site` | same |
| sites | `find_write_sites(key=NEEDLE)` | same |
| **silhouette** | `def_chain` → `key_member` (None ⇒ drop) | **omitted — this is the R/R_f difference** |
| value | `resolve_value` vs `TMP_PATH_HOME` | same primitives, same constant |
| key | `member_key` | same |

Membership is then a **set lookup against `discover()`'s own output**
(`_home_pin_gate.py:353, 366`), never a re-evaluated predicate. No predicate is owned here, so
C-006 and the seam's no-second-copy rule hold — and T007's own guard covers
`_home_pin_gate.py` as a named member of the discovered consumer set.

The two populations do coincide today (7/7 at the selected start, 40/40 at the end — asserted by
`test_e_effect_class_fallback_is_asserted_inert_at_both_ends`), so a wrong reading would indeed
have produced the same number. The correct reading shipped anyway.

### (2) The verdict artefact's path — **ACCEPTABLE, with a note for merge**

I verified the refusal the implementer cites is real: `move-task --to for_review` blocks committed
`kitty-specs/` paths on a lane branch at
`/home/jeroennouws/dev/spec-kitty/src/specify_cli/cli/commands/agent/tasks_parsing_validation.py:782`.
`--force` was not used. The mission-relative reading was genuinely unavailable.

WP05 and WP06 **will** find it: no downstream WP names the path at all (grep over
`tasks/WP0[3-6]*.md` returns nothing for `home_pin_gate`), the sole authority is the module
constant `gate.VERDICT_RELPATH`, and WP06's obligations (`r`, `|R|`, `|R_f|`, both SHAs, every
attempted window including the VOID one, the machine-readable band) are content obligations that
the artefact satisfies.

Note for the operator at merge: the file lands inside a **pre-existing, unrelated repo-root
`research/`** directory (agent research docs, `01-claude-code.md` …), while the sibling
`research/` reference in the same module — `EVIDENCE_RELDIR` — resolves *mission*-relative. Two
`research/` prefixes with different meanings, resolved differently, in one module. The module
documents this at `:159-171`. Raised, not repaired.

### (3) The rename signature's fallback for non-members — **the limb bites**

`_shape_of` (`:332-342`) takes the fallback iff `member is None`, which is exactly iff
`Site.is_member` is `False`. `test_e_effect_class_fallback_is_asserted_inert_at_both_ends`
asserts `{row["is_member"] for row in sites_at_start ∪ sites_at_end} == {True}` — the precise
negation of "the fallback was exercised" — and it is **non-vacuous**: an empty site list yields
`set()`, which is `!= {True}`, so it reds rather than passing. The artefact confirms 7/7 and
40/40. Correct and falsifiable.

*Sub-finding, LOW:* `_signature` (`:396-399`) also guards `site.resolved_value is None`, but
`effect_class_sites` skips every site whose value `!= TMP_PATH_HOME`, so that branch is
**structurally unreachable**. FR-007's own rule — a limb matching nothing must be *known* to match
nothing — applies, and this one is unregistered while its twin (the `kind is None` fallback) is.

### (4) `NodeTransformer` matched alongside `NodeVisitor` — **CORRECT**

`ast.NodeTransformer` *is* a subclass of `ast.NodeVisitor`, so a class deriving from it *is* a
`NodeVisitor` subclass. T007's words ("ZERO `ast.NodeVisitor` subclasses") already cover it; this
is a faithful reading, not a widening, and it carries no false-positive surface. Approved.

*Nit:* the hit is labelled `"ast.NodeVisitor"` even when the base was `NodeTransformer`
(`test_home_pin_seam_no_second_copy.py:164-168`) — a diagnostic that names the wrong base.

---

## 2. The self-reported defect: `KEYS_CHECKED_FLOOR = 30`

**Acceptable as shipped. Not blocking. Must be derived before the census lands.**

Confirmed on both halves of the implementer's account:

* It **is** invisible to `test_golden_count_ban` — that scanner matches only
  `len(<expr>) == <int>` in either operand order, and this is `>=` against a named constant.
* T008(g) **literally mandates** *"a **PUBLISHED NON-ZERO FLOOR** on the number of keys checked"*,
  so the constant discharges the written DoD rather than evading it.

**But one of the two cited constraints does not actually bite.** The implementer says a
set-membership claim is blocked because the artefact's key set is pinned to fifteen fields with
"nowhere to publish a survivor set". It needs no new field. The claim can be stated entirely
inside the test, over data already published:

```python
vanished = {row["relpath"] for row in document["sites_at_end"]
            if not (TESTS_ROOT / str(row["relpath"])).is_file()}
assert vanished == set(), f"published end-SHA sites whose file no longer exists: {sorted(vanished)}"
```

That is a set equality with **no tunable number**, it publishes nothing new, it degrades to a red
that *names* the vanished relpaths instead of degrading to silence, and a legitimate file move
then gets explained rather than absorbed — the same discipline this Mission applies everywhere
else. The prompt's "published non-zero floor" is satisfied a fortiori by a claim that admits zero
losses.

Why it is not blocking: limb (g)'s primary assertion (`mismatches == {}`) is content-anchored and
does bite; the floor is only the anti-vacuity backstop. Measured 40, floor 30 — a 25% tolerance
whose failure mode (files legitimately moving) is loud in review. Carry to WP06's residual list
and convert; it is a one-line change.

**Secondary — the §0.3/leak header and limb (h): acceptable, LOW.** The observation is right: a
gutted paragraph retaining the word "SUPERSEDED" passes `test_h_...`. Two things bound it. The
header is **generated** from `VERDICT_HEADER` and `.format()`ed from the measurement
(`_home_pin_gate.py:839-895`), and the artefact declares itself never hand-edited — so the
realistic failure requires editing a reviewed module constant, not the artefact. And the semantic
claim is not mechanisable; a presence check is the honest ceiling. Weaker point: the control
`test_h_control_a_silent_record_reds` asserts the *helper* returns empty, where (b), (d) and (g)
all assert the *assertion* reds via `pytest.raises`. Tighten it when the module is next touched.

---

## 3. Can these tests fail? Mutation results

Eight mutants injected into the pure functions; six killed, two survive — and the two are the
same limb.

| mutant | caught by |
|---|---|
| `band`: `r >= 50%` → `r > 50%` | `test_f_oracle_full_mapping_over_consequences` |
| `band`: VOID returns `"halt"` instead of raising | `test_f_void_is_a_precondition_and_not_a_band` |
| `band`: `r == 100%` → `r > 100%` | `test_d_band_recomputed_equals_published_label` |
| perturbations: floor clamp on `|R|−1` dropped | `test_f_oracle_full_mapping_over_consequences` |
| **perturbations: `|R|+1` axis dropped** | **NOBODY** |
| **perturbations: whole `|R|` axis dropped** | **NOBODY** |
| `stability`: `all()` → `any()` | `test_f_oracle_full_mapping_over_consequences` |
| `stability`: always reports stable | `test_f_oracle_full_mapping_over_consequences` |

### MEDIUM — the `|R| ± 1` stability axis is provably decision-irrelevant

I proved why the two mutants survive. Over `|R| ∈ [10, 4000]`, `|R_f| ∈ [0, |R|]`, the `|R| ± 1`
axis **never changes a consequence class** — it is entirely subsumed by the `|R_f| ± 1` axis:

* `|R|+1` crosses the 50% threshold only where `2|R_f| = |R|`, and there `|R_f|−1` already crosses;
* `|R|−1` crosses only where `2|R_f| = |R|−1`, and there `|R_f|+1` already crosses;
* from `r = 100%`, `|R|+1` lands in *proceed-degraded*, the same consequence class.

Zero differing states across 31 window sizes, and zero across 3 991. So the second axis is
**measured and published** — both artefact perturbations `(32,33)` and `(33,34)` are there, one per
axis — but it can never affect admissibility, at any window size, ever.

`spec.md` §0.9 presents it as *"what an earlier revision could not see: a false pair moves `|R|`,
not `|R_f|`"*. That is true of what is **measured** and false of what is **decided**. WP02
implemented the spec faithfully — this is a spec-level inert limb, and FR-007's own rule ("a limb
matching nothing must be known to match nothing, or it will be read as enforcement") applies to
it. Recorded for WP06, not a rejection ground.

It does not touch the verdict: admissibility at `(33,33)` rests on `(32,33)` → `32/33` →
*proceed-degraded* → `go`, same class as the base. Stable. Correct.

### MEDIUM — the driver half of T006 has zero test coverage

`detect_renames`, `window_accepted`, `measure_window`, `widening_walk`, `effect_class_sites`,
`verdict_document`, `crosscheck_start_sha` and `extracted_tests` are referenced **nowhere** in
`tests/` outside their own definitions. T006 step 5 requires the rename detector be *"proven on
materialised departure/arrival sets"* — that obligation is undischarged.

I constructed the proof myself. Eight cases against §0.9: unique mutual best match pairs;
2-vs-2 tie **refused** with all four sites retained; 1-vs-2 refused; cross-file never pairs;
`kind` mismatch never pairs; `kind is None` never pairs; `resolved_value is None` never pairs;
`params` mismatch never pairs. All eight behave exactly as specified. **The code is right — but
nothing in the tree would notice if it stopped being right**, and the rename detector is the only
thing that can move `|R|`, which is half the stopping rule. Highest-value single follow-up.

### The oracle itself — independently re-derived

I transcribed §0.9's banding, clamp and ±1 rule from the specification from scratch and enumerated
`|R| ∈ [10,40]`, `|R_f| ∈ [0,|R|]`: **806 states, `380 go / 364 halt / 62 inadmissible`** over
consequences, and `318 proceed-degraded / 364 halt / 124 inadmissible` with `proceed` in exactly 0
states over labels. Both match the module, the shipped inline transcription, and the
specification's independently published figures.

---

## 4. The stopping rule reads `|R|` and stability only

Confirmed by reading `window_accepted` (`_home_pin_gate.py:599-609`). It touches
`measurement.error`, `len(measurement.arrivals)`, and `stability(len(measurement.caught),
size).stable`. It never reads `measurement.label`, `result.base_band` or
`result.base_consequence`. Passing `|R_f|` into `stability` is required by §0.9's own definition
of stability; the rule then branches **only on the boolean class-invariance, never on which
class** — a stable *halt* window would be accepted and the walk would stop there. That is the
proof it is band-blind, and it is the property that survives the leak.

---

## 5. C-003 containment, T007's teeth, and the golden-count conversion

**C-003 — confirmed.** `subprocess` and git appear only in `_home_pin_gate.py` (`_git`,
`first_parent_history`, `extracted_tests`, and the two `subprocess.*Error` classes in
`_WINDOW_ERRORS`). `_home_pin_scan.py` has zero, mechanised by
`test_seam_module_holds_no_subprocess_and_no_git_surface` with a control that bites. The
occurrence in the seam test is inside a materialised source *string*. The only git invocations are
`rev-list --first-parent` (topology) and `archive` (content) — no `log -S`, no `diff | grep`.

*Nit:* `# noqa: S603` at `_home_pin_gate.py:488` is dead — `S603` is globally ignored **and**
`tests/**` carries a blanket `S` per-file-ignore. Harmless, but it reads as an active suppression.

**T007's positive controls — three of four bite; one hole.** The second-copy control finds both
constructs; the unrelated-`parse` control correctly does *not* fire on
`from urllib.parse import urlparse as parse`; the git-surface control fires; the consumer set is
discovered and asserted non-empty with two named members.

### MEDIUM — aliased `ast` imports evade T007's ban entirely

Constructed and verified. A materialised module containing:

```python
from ast import parse as _p, NodeVisitor as _NV
from tests.architectural._home_pin_scan import discover

class Copy(_NV): ...
def again(text): return _p(text), discover
```

is **discovered as a consumer** and yields `_offenders(...) == {}`. `_ast_aliases` collects the
*bound* name (`alias.asname or alias.name`) but `_is_ast_member` then compares
`node.id == member` against the *original* name, so any rename defeats it
(`test_home_pin_seam_no_second_copy.py:145-147, 172-178`). The module's own docstring claims this
class is covered — the `import ast as a` attribute form **is** handled; the aliased from-import
form is not.

Not a live violation (no consumer uses aliased `ast` imports today), but T007 exists to stop
*future* drift and it is one alias away from silent. One-line fix: have `_ast_aliases` return
`bound_name -> original_name` and resolve through it.

**Golden-count — baseline untouched, conversion genuinely equivalent.** The diff adds six files
and edits none; `_golden_count_baseline.json`, `_gate_coverage_baseline.json` and
`tests/_arch_shard_map.py` are all unmodified against the mission branch.
`test_golden_count_ban` + `test_gate_coverage` + `test_ci_architectural_gate_coverage`: **51
passed**. The conversion `len(left)==1 and len(right)==1` → `not left[1:] and not right[1:]` is
equivalent because both lists are non-empty by construction — the group comes from
`set(departure_groups) & set(arrival_groups)` and every group list is built by
`setdefault(...).append(...)` — so `not left[1:]` ⟺ `len(left) == 1`. And it does express the
truer statement: **no rival on either side**, which is what unique-mutual-best-match means.

---

## 6. Reproducibility — independently confirmed, from a different root

I re-ran the full 314-step walk once, from a **different repository root**
(`/home/jeroennouws/dev/sk-missions/3121`, not the lane worktree). Result: same accepted start SHA
`ba0db69ade41f0fd788adea360e03456caf0c3e4`, same 314 attempts, same `|R| = 33 / |R_f| = 33`, same
stability block, same empty crosscheck. The emitted document differs in **exactly one field —
`invocation`** — and the single header line that interpolates it. Every other byte matches.

That is stronger than a same-directory re-run: it also independently confirms FR-009's root
parameterisation, since the keys proved root-relative rather than checkout-dependent.

*Informational:* `invocation` necessarily embeds absolute machine-local paths (NFR-006 mandates
the resolved interpreter path and verbatim invocation), so any regeneration from another checkout
will always show that one line as a diff. Expected, not a defect.

---

## 7. MEDIUM — the sample's concentration is not surfaced in the record

The published `attempted_windows` shows `R_size = 3` for **313 consecutive windows**, then `33` at
the 314th — monotone, zero errors, zero `UNMEASURABLE`. So **30 of the 33 arrivals landed in a
single first-parent commit** (`2bad3228…`, the `#3030` governance-dossier landing: 101 files,
22 124 insertions), and the other 3 are `#3108`. The `|R| ≥ 10` floor is met by **two authoring
events, not 33 independent ones**.

This violates nothing — §0.9 says plainly the floor is *"a VISIBILITY floor, not statistical
adequacy"*, and the concentration is recomputable by a reviewer from the published attempts
without re-running, which is SC-000(i)'s standard. But §0.3's own doctrine — *"Two points from one
landing do not define [a rate]"* — applies with equal force to a *sample*, and the record does not
name it. Should be stated in WP06's record. Not repaired here.

---

## 8. Crosscheck positive control is not shipped — LOW/MEDIUM

`start_sha_crosscheck.symmetric_difference` is `[]` — a population-0 assertion. The implementer's
`for_review` transition note records that a control was run (clf@selected vs discover@end,
difference 33, "proving the instrument can see"). That control lives **only in the note**: nothing
in the tree re-runs it, and `test_e_start_sha_crosscheck_is_published_and_explained` checks only
presence plus the explanation-if-non-empty rule. T008(e)'s letter is met. Carry the control into
WP06's record at minimum; better, ship it.

---

## 9. Baseline reds — confirmed by a deselect control at the same parallelism

I ran `tests/architectural/` at `-n8 --dist loadfile` on this same tree with WP01's and WP02's
three new modules **deselected entirely**, so the Mission's new test code contributes nothing to
contention:

```
3 failed, 1848 passed, 5 skipped, 2 xfailed in 954.96s
FAILED test_ci_quality_path_filters::test_core_misc_shards_plus_e2e_owner_cover_legacy_selection
       (subprocess `--collect-only` TimeoutExpired after 240 s)
FAILED test_build_wp_prompt_implement_stays_under_latency_budget  (6.30 s vs 6.0 s)
FAILED test_build_wp_prompt_review_stays_under_latency_budget     (6.37 s vs 6.0 s)
```

The **same three** reds reproduce with WP02 removed, on the same machine, at the same parallelism,
holding everything else fixed — which attributes them more tightly than a merge-base comparison
would. `1848 + 23 (WP02) + 70 (WP01) = 1941`, matching the implementer's report.
`test_wp_prompt_build_latency` additionally **passes serially** on the lane (82 s, 2 passed),
confirming a contention/budget gate rather than a correctness red. Not fixed; no issue opened
(C-013).

### Live governance conflict — RECORDED, not resolved

**DIR-013** requires a GitHub issue before pre-existing failures are treated as accepted baseline.
**C-013** forbids `gh issue create` in this Mission. They cannot both be satisfied.

The implementer routed this to the operator in the `for_review` transition note, which is
operator-visible on the status surface. Confirmed present in
`status.events.jsonl`. What the note states is the **outcome** ("classified, not fixed, no issue
opened per C-013"), not the **conflict** as a decision item, and `record.md` — where WP02's Risks
table says to record it — is WP06's artefact and does not exist yet. Adequate for now. **It must
be carried into WP06/T030 as a named TG-item**, and it is restated here so the operator meets it
in the review record as well.

---

## 10. Standing gates

| Gate | Result |
|---|---|
| `ruff check` (three files) | clean — `ruff format` never run |
| `mypy --strict` (three files, `MYPYPATH=src`) | clean |
| WP02's 23 tests, `-n0` | 23 passed (52 s) |
| WP02's 23 tests, `-n auto --dist loadfile` | 23 passed (148 s) — **identical results** (DoD 6) |
| `test_golden_count_ban` + `test_gate_coverage` + `test_ci_architectural_gate_coverage` | 51 passed |
| `_gate_coverage_baseline.json`, `_golden_count_baseline.json`, `tests/_arch_shard_map.py` | untouched |
| Both new modules top-level and `architectural`-marked | yes (IC-08) |
| Terminology Canon — `feature` in new files | zero occurrences |
| Verdict artefact committed and tracked | yes |
| C-006 — files touched | six new files; nothing under `src/`; `_home_pin_scan.py` unedited |
| Artefact top-level key set | 15 keys, equal to `data-model.md`'s `Verdict` field list |

---

## 11. Findings

- `[MEDIUM] tests/architectural/test_home_pin_seam_no_second_copy.py:145-147,172-178` — aliased
  `ast` imports (`from ast import parse as _p, NodeVisitor as _NV`) evade the ban entirely;
  verified against a materialised second copy, which the guard discovers as a consumer and reports
  clean. `_ast_aliases` collects the bound name, `_is_ast_member` compares the original.
  **Recommendation:** return `bound_name -> original_name` from `_ast_aliases` and resolve through
  it; add the aliased form to the existing positive control.
- `[MEDIUM] tests/architectural/_home_pin_gate.py:441-478, 599-609, 621-651, 345-371, 773-831` —
  the entire driver half of T006 (`detect_renames`, `window_accepted`, `measure_window`,
  `widening_walk`, `effect_class_sites`, `verdict_document`, `crosscheck_start_sha`) has no test
  anywhere in `tests/`. T006 step 5 requires the rename detector be "proven on materialised
  departure/arrival sets". I verified the behaviour is correct across all eight specified cases.
  **Recommendation:** ship the eight-case rename-detector table and a `window_accepted` test that
  asserts a stable *halt* window is accepted — that last one is the executable form of the
  band-blindness property.
- `[MEDIUM] tests/architectural/_home_pin_gate.py:234-253` — the `|R| ± 1` stability axis is
  provably subsumed by the `|R_f| ± 1` axis: zero differing consequence classes over
  `|R| ∈ [10, 4000]`. Both mutants that delete it survive the whole suite. Faithful to §0.9, but it
  is an inert limb presented as enforcement, which FR-007's own rule forbids.
  **Recommendation:** register it as asserted-inert in WP06's record and state the subsumption;
  do not remove it (the spec mandates it).
- `[MEDIUM] tests/architectural/test_home_pin_gate_verdict.py:69,436-440` —
  `KEYS_CHECKED_FLOOR = 30` is a hand-written integer a future editor can lower, invisible to
  `test_golden_count_ban`. The cited blocker (nowhere to publish a survivor set) does not bite: the
  vanished-relpath set can be asserted empty inside the test from data already published, with no
  sixteenth artefact key and no tunable number. **Recommendation:** convert before the census
  lands; carry to WP06's residual list.
- `[MEDIUM] research/home_pin_gate/verdict.yaml` (`attempted_windows`) — 30 of the 33 arrivals
  landed in one first-parent commit (`2bad3228…`, `#3030`); the floor is met by two authoring
  events. Permitted (§0.9's floor is visibility, not adequacy) and recomputable from the published
  attempts, but unstated. **Recommendation:** name the concentration in WP06's record.
- `[LOW] research/home_pin_gate/verdict.yaml` (`start_sha_crosscheck`) — the empty symmetric
  difference has no shipped positive control; the control exists only in the lane-transition note.
  **Recommendation:** carry it into WP06's record, or ship it as an eighth limb.
- `[LOW] tests/architectural/_home_pin_gate.py:396-399` — the `resolved_value is None` guard in
  `_signature` is structurally unreachable (`effect_class_sites` filters non-`TMP_PATH_HOME`
  values). **Recommendation:** register as asserted-inert alongside the `kind is None` fallback.
- `[LOW] tests/architectural/test_home_pin_gate_verdict.py:304-308` —
  `test_h_control_a_silent_record_reds` asserts the *helper* returns empty, not that the
  *assertion* reds; weaker than (b)/(d)/(g)'s `pytest.raises` controls.
  **Recommendation:** wrap the assertion.
- `[LOW] tests/architectural/test_home_pin_seam_no_second_copy.py:164-168` — a `NodeTransformer`
  base is reported as `"ast.NodeVisitor"`. **Recommendation:** report the matched name.
- `[INFO] tests/architectural/_home_pin_gate.py:488` — `# noqa: S603` is dead (`S603` globally
  ignored; `tests/**` has a blanket `S` per-file-ignore). **Recommendation:** demote to a plain
  comment.

None of the above changes the verdict, its operands, or the stopping rule's independence.

---

## 12. What I checked, and what I could not

**Checked, by construction:** the §0.9 reading of `R`/`R_f`; the composition-not-copy property
against `discover()`'s pipeline; the 806-state oracle re-derived independently from the
specification (`380/364/62` and `0 proceed` over labels, both matched); `band()`'s clamp and
`stability()`'s ±1 under eight mutants; the rename detector's eight specified cases exercised
directly; limb (a)'s absent-artefact red and limbs (b)/(d)/(g)'s controls; the seam guard's four
controls plus a constructed evasion; C-003 containment; the golden-count conversion's equivalence
and the untouched baselines; the full 314-step walk re-run from a different repository root; the
baseline reds reproduced under a deselect control at the same parallelism; ruff, `mypy --strict`,
and both parallelisms.

**Could NOT check — stated plainly:**

1. **The start-SHA operands.** `sites_at_start` (7 rows at `ba0db69a`) names content that is not in
   this tree; limb (g) recomputes only the end half. My re-run *reproduces* those rows but does not
   *externally verify* them — it runs the same instrument. The start half is anchored solely by the
   C-011 crosscheck, whose empty symmetric difference has no shipped positive control (finding
   above). If `discover()` and `clf.py` share a blind spot at that SHA, nothing in this WP would
   show it. The module states this in its own "what this cannot see"; I am not treating it as newly
   discovered, but an approver should be explicit about it.
2. **That `attempted_windows` is a contiguous first-parent chain.** Unprovable inside the collected
   module by T008's own no-git constraint. A record omitting intermediate windows would pass. My
   independent re-run reproduces the same 314 attempts, which is the available mitigation.
3. **Whether ±1 stability is satisfiable at any window** — not evidenced, per the WP's own risk
   table. It happened to hold at the first window meeting the floor.
4. **The three baseline reds' root causes.** Attributed, not diagnosed; per C-013 no issue was
   opened and per the instruction nothing was fixed.

---

## Verdict

**APPROVED.**

The judgement that could have invalidated the whole instrument — drawing `R` over the effect class
rather than over `discover()`'s difference — is textually correct against §0.9 and implemented as
a genuine composition of the seam rather than a second copy. The band is **recomputed** rather than
trusted, `halt` reds, an absent artefact reds, the oracle reproduces §0.9's independently published
`380/364/62` (which I re-derived from scratch and matched), the stopping rule is demonstrably
band-blind, and the measurement reproduced field-for-field from a different checkout. The
pre-existing reds are confirmed pre-existing by a same-tree deselect control.

Every finding above is *narrowing* work — a one-line guard hole, an untested-but-verified-correct
rename detector, a tunable anti-vacuity floor, an inert stability axis, and two record gaps. None
of them changes `verdict: proceed`, its operands, or the independence of the rule that selected the
window. WP03..WP06 are not blocked.
