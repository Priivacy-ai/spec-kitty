---
work_package_id: WP05
title: The frozen census, its baseline, and the one assertion that proves the class is frozen
dependencies:
- WP03
- WP04
requirement_refs:
- FR-003
- FR-004
- NFR-003
- NFR-004
- C-002
- C-006
- C-007
- C-011
- C-012
- C-013
planning_base_branch: feat/isolated-home-pin-guard
merge_target_branch: feat/isolated-home-pin-guard
branch_strategy: Planning artifacts for this mission were generated on feat/isolated-home-pin-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/isolated-home-pin-guard unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
- T024
- T025
- T026
history: []
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/architectural/census/spec_kitty_home_pin_R1a.yaml
- tests/architectural/spec_kitty_home_pin_baseline.yaml
- tests/architectural/test_spec_kitty_home_pin_census.py
execution_mode: code_change
owned_files:
- tests/architectural/census/spec_kitty_home_pin_R1a.yaml
- tests/architectural/spec_kitty_home_pin_baseline.yaml
- tests/architectural/test_spec_kitty_home_pin_census.py
- tests/_arch_shard_map.py
role: implementer
tags: []
task_type: code-implementation
tracker_refs: []
---

# Work Package Prompt: WP05 (alias WP-c) – The frozen census, its baseline, and the one assertion that proves the class is frozen

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

> ## 📌 IF A REVIEWER DEEP-REVIEWS EXACTLY ONE PACKAGE, IT IS THIS ONE (plan §10)
>
> The parallelism in plan §4 is bought by moving the real-tree `discovered == census ∪ E` assertion out of
> WP04 and into **this** package. It is the right trade, but it has a cost invisible from the dependency
> graph: **WP05 now looks like a generated data file, and generated data files get skimmed.**
> **The single assertion that actually proves the class is frozen lives in the package least likely to get a
> hard look.** Write it accordingly.

## Objective

Generate the frozen census and its baseline through the **single documented command**, assert the classifier
against the external C-011 anchor with `E` subtracted and disjointness **proved**, ship the real-tree ratchet
with both hashes recomputed from content, make the `:1165` red diagnosable, and cross-check `home_partition`
against M4 **by recomputation on a named join key**.

## Context

- **Plan concerns**: IC-06 (the frozen census, its baseline, the real-tree equality), IC-08 (CI landing).
- **The anchor was measured at `5d49d31ed`, BEFORE the owner and the probe existed.** At this point
  `discover(Path("tests"))` returns **42** keys, not 40, and an assertion of `discovered == anchor` is
  **FALSE**. Three assertions replace it — see T023.
- **The hash is over the sorted key set, not the file bytes** (plan §5). Hashing bytes passes every test on
  day one and turns an `owed_to` re-point or a header edit into a **fake adjudication** on day thirty.
- **C-002**: no counted definition of done anywhere in this WP. **The literal `40` is content, never a
  threshold, and appears in NO assertion.**
- **C-011**: the evidence artefact at `research/spec_kitty_home_pin_evidence/` is checked in **verbatim** and
  must **never** be imported by, merged into, or "tidied" against `_home_pin_scan.py`. `discover()` is compared
  **against** it; it is never derived **from** the module under test.

---

### Subtask T022: Generate the census and the baseline through the single documented command

**Purpose**: FR-003's frozen census and its baseline, produced by — and **only** by — one command.

**Steps**:

1. Run, verbatim:
   ```
   python -m tests.architectural._home_pin_scan --regenerate --root tests --sha <freeze sha> \
       --owed-to '#3121' --exempt-module tests.architectural._home_pin_exempt
   ```
   **`--exempt-module` is part of the documented command literal**, because **without it nothing subtracts the
   owner and the retained-pin probe, which ARE in `discover(root=tests)` at this point.**
2. Both artefacts carry a header **naming that exact command**; **neither is hand-edited**; a **re-run is
   byte-identical**.
3. Structural assertions, **all as SETS**:
   - the census **HEADER key set** and the census **ROW column name set** are each asserted **by set
     equality** (`{key, lineno, kind, home_partition}` for rows), so **`reason`, `frozen_at_sha` and `owed_to`
     are absent from rows BY CONSTRUCTION** and **a `reason` cannot hide in the header either**;
   - `owed_to` matches `^#[0-9]+$`;
   - rows are **sorted**;
   - **the canonical owner's key is not among them**;
   - the baseline's key set **includes `tombstones`**, which is its **named home**.

**Files**: `tests/architectural/census/spec_kitty_home_pin_R1a.yaml` (new, generated);
`tests/architectural/spec_kitty_home_pin_baseline.yaml` (new, generated);
`tests/architectural/test_spec_kitty_home_pin_census.py` (new, ~120 lines at this stage).

**Validation**: A hand-written census fails the **byte-identical re-run**; a `frozen_at_sha` promoted to a row
fails the **column-name set equality**; a census generated **without `--exempt-module`** contains the owner and
**fails T023**.

**What this cannot see**: whether `#3121` is the right **SCOPE** for 40 distinct adjudications — SC-003 can only
check that `owed_to` is **well-formed and not prose**.

---

### Subtask T023: SC-001 and SC-003 — set equality against the external anchor, with `E` subtracted and disjointness PROVED

**Purpose**: The Mission's only comparison against an instrument it did not write.

**Steps** — **three** assertions, not two:

1. `discover(Path("tests")) - {e.key for e in E} == anchor`
2. `census == anchor`
3. `anchor ∩ {e.key for e in E} == set()` — **stated EXPLICITLY as its own assertion**, because (1) and (2)
   together only **imply** it and **a reviewer must see disjointness proved rather than relied upon**.

**Building the anchor**:

4. The anchor is **C-011's checked-in evidence artefact**, derived from
   `research/spec_kitty_home_pin_evidence/members.json` by applying
   `(relpath_posix, *composite_key_from_file(path, lineno))` **to each entry of each member's `sites`**.
   **The key ENCODING comes from the repo primitive; the identification of WHICH sites are members comes from
   the external artefact**; the key is C-012's **path-qualified 3-tuple**, so **the anchor never passes through
   the instrument under test**.
   **MIND THE `tests/` PREFIX, and prefix at comparison time.** `Member.relpath` is relative to the **walk
   root**, so `discover(Path("tests"))` yields `cli/commands/foo.py`, while `members.json` stores
   **repo-root-relative** paths (`tests/cli/commands/foo.py`). `data-model.md` records this normatively; it is
   named again *here*, at the point of comparison, because that is where it bites. **The cheapest wrong repair
   is to edit the C-011 anchor** — and `members.json` is the one artefact in this Mission that must never be
   touched to make a test pass: its entire evidential value is that the party it checks did not write it.
5. **`verify.py` exits 0.**
6. **The literal `40` appears in NO assertion.**

**Files**: `tests/architectural/test_spec_kitty_home_pin_census.py` (+~130 lines).

**Validation**: The previous revision asserted `discovered == anchor` **and** `census == anchor - E`, which is
**a false assertion beside a no-op subtraction that reads as load-bearing**; the implementer facing that red
**would relax to containment — in the WP whose own `not_done_if` names containment as a failure.**
Under the **bare 2-tuple** the anchor has **19** elements and a classifier finding **one member per collision
class** produces the **same 19-element set, green**; the 3-tuple restores this criterion's power, and **the key
must be path-qualified and formed at the WRITE SITE.**

**What this cannot see**: whether any member **deserves** to be a member. Entirely R1b's.

---

### Subtask T024: The real-tree ratchet, the recomputed hashes, and mypy over the REAL `E`

**Purpose**: **This is the single assertion that proves the class is frozen.**

**Steps**:

1. `discover(Path("tests")) == census ∪ E` over `MemberKey` **3-tuples** — **SET EQUALITY, not containment.**
2. The guard **RECOMPUTES `census_key_set_sha256` from the census** and compares it against
   `tests/architectural/spec_kitty_home_pin_baseline.yaml` — **a DIFFERENT file from the census**, so the pin
   is **never editable in the same hunk as its subject** — and **recomputes `exempt_set_sha256` from the real
   `E`**.
3. **Every census delta must be accounted for by a tombstone.** A delta **plus a re-pinned hash still reds**
   unless a tombstone explains it, **while a legitimate adjudication passes.**
4. **AND SC-005'S ARITY LIMB IS DISCHARGED HERE ON THE REAL FILE**:
   `[sys.executable, "-m", "mypy", "--strict", "tests/architectural/_home_pin_exempt.py"]` **exits zero**,
   which is what SC-005 actually asks for. **WP04/T018 proves the MECHANISM over a materialised module; only
   this limb type-checks the artefact that ships**, and **CI will not do it** — mypy there covers `src/` only
   and runs with `continue-on-error`.

**Files**: `tests/architectural/test_spec_kitty_home_pin_census.py` (+~140 lines).

**Validation**: **A subset-only ratchet passes every WP04 tree except T017's and fails here.**

**What this cannot see**: whether a tombstone corresponds to a **real adjudication**. A tombstone written to
green a red is the entitlement C-007 forbids **wearing the mechanism meant to prevent it**; **only a reviewer
catches that.**

---

### Subtask T025: Make the `:1165` red diagnosable, and pin the fragility register as a SET

**Purpose**: When the known-fragile row goes stale, the cheapest green for a confused contributor is a
tombstone — recording an adjudication that never happened. Two distinct messages close that path.

**Steps**:

1. For **any stale row** the guard **re-runs the EFFECT LIMB ALONE** — *does a site in that file still write
   `SPEC_KITTY_HOME` to `tmp_path/"home"`?* — and emits **one of two distinct messages**:
   - `site still present, silhouette no longer satisfied — this is NOT an adjudication`
   - `site absent — deleted`
2. **BOTH branches are exercised over materialised trees** (importing **WP04's `_home_pin_synthetic`, never
   editing it**), **each asserting the exact message**, so **neither branch is dead code**.
3. **AND THE FRAGILITY REGISTER IS A SET EQUALITY**, not the phrase *"the sole such case of the 40"*: the set
   of members **held in the class by a silhouette parameter that their keyed def declares and never
   references** is asserted **EQUAL to `{the :1165 key}`**.
4. **Measured true today — exactly one — and asserted by nothing until now**, while being **the only thing
   that makes T026's "single known-fragile row" true.** One extra walk over trees the pass has already parsed.

**Files**: `tests/architectural/test_spec_kitty_home_pin_census.py` (+~100 lines).

**Validation**: **A count in the row whose red this subtask exists to diagnose is the shape this Mission keeps
catching.**

**What this cannot see**: the deletion itself. The polarity is a **spurious red on a behaviour-preserving
edit**, which is correct and needs no change.

---

### Subtask T026: The census header's load-bearing prose, and the M4 cross-check recomputed on a named join key

**Purpose**: Put the rationale where FR-003 says rationale goes — the header — and turn the M4 agreement from a
quoted figure into a recomputation.

**Steps**:

1. The census **HEADER** (never a `reason` column) **names `:1165` as the known-fragile row**, states that its
   membership **rests on an unused parameter**, and instructs: **if this row goes stale with the site still
   present, the repair is neither a tombstone nor a predicate change — it is an R1b adjudication.**
2. It follows `tests/architectural/census/verdict_seam_IC01.yaml`, whose header carries this kind of
   load-bearing prose while the rows stay data, and it **survives the reviewer test**: **it entitles the
   definition to NOTHING and changes no check's outcome.**
3. **The `home_partition` cross-check is RECOMPUTED at test time.** M4's per-member labels are parsed from
   `research/m4_ablation_evidence/TABLES.md`, whose **28 rows are keyed `(file, fixture_qualname)` with no
   lineno**, so **THE JOIN KEY IS `(rel_path, KEYED-DEF qualname)`** — measured **injective over the 40**,
   giving **exactly 28 matches and zero unmatched**.
4. **`MemberKey[1]` is NOT that field**: it is the **INNERMOST** qualname and **differs from the keyed-def
   `qual` at `:1165`**.
5. **Do not reject the 2-tuple projection by false analogy with the 19-key collapse**, which was about
   `(qualname, token_line)` and is a **different hazard**.
6. The set of **DISAGREEING keys is asserted EMPTY** with the **intersection size published**, and a
   **positive control** feeds the comparator a **deliberately mislabelled materialised row**.
7. **OPERATOR RULING, RECORDED**: `home_partition` appears in **no key, no hash and no equality**, so it is
   **REGENERABLE in a follow-up under FR-004(2)** and **MAY NOT HOLD THE RATCHET HOSTAGE** — **if this column
   blocks the freeze, the column yields, not the ratchet.**

**Files**: `tests/architectural/census/spec_kitty_home_pin_R1a.yaml` (header prose, via the generator);
`tests/architectural/test_spec_kitty_home_pin_census.py` (+~120 lines).

**Validation**: Copying `A=27 / B1=11 / B2=2` and `28 agreements` out of the plan into a comment satisfies any
prose-shaped criterion; **recomputation on a named join key with an empty-disagreement set and a positive
control is the only form that reds when the classifier drifts.**

**What this cannot see**: whether M4's labels are right — it is a **second external anchor, not an oracle**.

---

## Definition of Done

Per-subtask completion is a `spec-kitty agent tasks mark-status <Txxx> --status done` event.

1. **`discover(Path('tests')) - E == anchor`, `census == anchor`, and `anchor ∩ E == set()` as three separate
   assertions**; and **`discover(Path('tests')) == census ∪ E` as set equality** with **both hashes recomputed
   from content**.
2. **The literal `40` appears in no assertion anywhere in this WP**; every comparison is against a key **SET**.
3. **`mypy --strict` runs over the REAL `_home_pin_exempt.py`** via `[sys.executable, '-m', 'mypy']` and
   **exits zero** — SC-005's arity limb discharged **on the artefact that ships**, since **CI will not do it**.
4. **The M4 cross-check is recomputed on the `(rel_path, keyed-def qualname)` join key** with an
   **empty-disagreement set and a positive control**, **not quoted**.
5. **The fragility register is a set equality against the `:1165` key**, not the phrase "the sole such case".
6. `test_no_int_line_sink_in_architectural_python_seeds` stays green: **no int literal reaches
   `composite_key_from_file`'s second positional argument from any module-level seed** in this WP's modules.
7. **IC-08 landing, mechanically**: `test_spec_kitty_home_pin_census.py` is **top-level** and
   `architectural`-marked, covered by `test_gate_coverage.py::test_no_new_orphan_surfaces`.
   **`tests/_arch_shard_map.py` is OWNED BY THIS WP AS A RESERVATION** — exactly one package may optionally pin
   shard balance, and this is that package — **but IT NEEDS NO EDIT**: `default_fallback=True` (`:419`) with
   hash-bucketing (`_shard_registry.py:181`) auto-covers every new file, and the module's own docstring says an
   explicit row is **authoritative balance control, not a keep-green obligation**. **The default is not to edit
   it.**
8. **NFR-003**: identical verdicts under `-n0` and `-n auto --dist loadfile`. **NFR-004 / SC-008**:
   `ruff check` and `mypy --strict` clean, **no suppression added, never `ruff format`**. **C-002**: no counted
   definition of done anywhere in this WP — **the literal `40` is content, never a threshold**. **C-006**: no
   file under `src/` changes. **C-013**: nothing merged, no `gh issue create`, explicit-path `git add`.

## Not Done If

- **T023 asserts `discovered == anchor` without subtracting `E`**, or **omits the explicit
  `anchor ∩ E == set()` assertion**.
- The census holds rows keyed on the **bare 2-tuple**, or keyed at the **definition line** rather than the
  **write site**.
- **The comparison is containment rather than set equality.**
- **A tombstone was written to green a red.**
- **`E` and the census share a key**, or **the baseline lives in the same file as the census**.
- **The regeneration command is run without `--exempt-module`.**

## Risks

| Risk | Mitigation |
|---|---|
| **The golden-count ratchet has ZERO headroom.** `tests/architectural` sits at **25/25** convert-classified sites against a frozen ceiling of **25**, so **any** new `len(x) == N` assertion in this WP trips `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline`. | Every assertion is a **SET comparison, never a count**. **The baseline may NOT be re-frozen** — the fix is always to convert the assertion, never to raise the bound. C-002 already forbids a counted definition of done; this is that rule at the point it bites. |
| This package looks like a generated data file and gets skimmed (plan §10). | The banner at the top of this prompt and the Reviewer Guidance below. **Do not let the reviewer's attention follow the code.** |
| `sha256(file.read_bytes())` — the natural implementation of "a checked-in hash". | It is **wrong** (plan §5). FR-004 pins a hash of the **sorted key set**. WP01/T005's invariance triple is the mechanism; this WP recomputes from content. |
| The T023 red gets relaxed to containment. | The three-assertion form removes the false assertion that produced the pressure. Containment is named in **Not Done If**. |
| A tombstone written to green a red. | No mechanism catches it. **Only a reviewer does.** Every tombstone must name a real adjudication. |
| The `home_partition` column blocks the freeze. | **Operator ruling, recorded**: the column yields, not the ratchet. It is regenerable under FR-004(2). |
| Editing `tests/_arch_shard_map.py` "to be safe". | `default_fallback=True` auto-covers. **The default is not to edit it.** The reservation exists so no two packages race on it. |
| Pre-existing reds (C-009 vs DIR-013). | Classify per CLAUDE.md's baseline-red gotcha; record evidence in `record.md`; route to the **OPERATOR** as a TG-item. **C-013 forbids `gh issue create` here.** |

## Reviewer Guidance

Plan §10 names four things nothing else will catch. Check them here:

1. **The baseline hash is over the sorted key set, not the file bytes.** Hashing bytes passes every test on day
   one and turns an `owed_to` re-point or a header edit into a fake adjudication on day thirty.
2. **The census row count is content, not a threshold** (C-002/C-011). **If the diff contains a literal `40` in
   an assertion, that is the tune-until-40 path C-011 names.**
3. **`discovered == census ∪ E` is set equality, not containment.** A subset-only ratchet passes WP04's
   synthetic trees for every transition except SC-004's — confirm SC-004 is present and **reds**.
4. **Every tombstone corresponds to a real adjudication.** A tombstone written to green a red is the
   entitlement C-007 forbids, wearing the mechanism that was supposed to prevent it.

And review the two `E` entries: if the key type changes, `E`'s hash input changes with it.

## Implementation

```bash
spec-kitty agent action implement WP05 --agent <name>
```
