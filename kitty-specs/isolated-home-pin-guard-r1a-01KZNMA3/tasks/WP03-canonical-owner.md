---
work_package_id: WP03
title: The canonical owner, its behavioural probes, and the exemption set they define
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-010
- FR-011
- NFR-003
- NFR-004
- NFR-005
- NFR-006
- C-001
- C-005
- C-006
- C-013
- C-014
planning_base_branch: feat/isolated-home-pin-guard
merge_target_branch: feat/isolated-home-pin-guard
branch_strategy: Planning artifacts for this mission were generated on feat/isolated-home-pin-guard. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/isolated-home-pin-guard unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
history: []
agent_profile: python-pedro
authoritative_surface: tests/
create_intent:
- tests/architectural/_home_pin_exempt.py
- tests/architectural/test_home_owner_behaviour.py
- tests/architectural/test_home_owner_never_wins.py
execution_mode: code_change
owned_files:
- tests/conftest.py
- tests/architectural/_home_pin_exempt.py
- tests/architectural/test_home_owner_behaviour.py
- tests/architectural/test_home_owner_never_wins.py
role: implementer
tags: []
task_type: code-implementation
tracker_refs: []
---

# Work Package Prompt: WP03 (alias WP-a) – The canonical owner, its behavioural probes, and the exemption set they define

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

> ## ⛔ PRECONDITION — CHECK IT, DO NOT ASSUME IT
>
> Before the first subtask: **`tests/architectural/test_home_pin_gate_verdict.py` is present and GREEN in
> this lane's worktree.** The lane allocator merges lane-a's tip in, but **degrades to a printed warning**
> if the dependency branch is unresolvable (`worktree_allocator.py:462-472`). Verify it; a missing gate is
> not permission to proceed.

## Objective

Add the **one** canonical `SPEC_KITTY_HOME` owner fixture to `tests/conftest.py` — the **only** edit to an
existing file in this Mission — fix its contract in writing **before** writing it, prove it actually works
(not merely that it has the right shape), and declare `E`, the two-entry exemption set, where its content is
determined.

## Context

- **Plan concerns**: IC-03 (the canonical owner), IC-08 (CI landing).
- **Files were disjoint; CONTRACTS were not.** The first pass assigned both owner probes to WP-b while WP-a
  added the fixture they request. That absent contract is why the `return None` / `tuple[str, str]` conflict
  survived planning. **Both probes now live here, and `contracts/canonical-home-owner.md` is this WP's FIRST
  deliverable.**
- **`SC-011` is pure shape and `SC-012` carries the entire behavioural load alone.** C-014 limbs (i) and (ii)
  are properties of pytest's fixture machinery, not of the owner's body: **an owner whose body is
  `return None` with no `setenv` and no `mkdir` satisfies both.** In a Mission whose thesis is that shape is
  not effect, that matters — write T012 limb (i) accordingly.
- **`E` fails the reviewer test, and that is the point** (`data-model.md`). An entry in `E` entitles its
  definition to exist forever with no `owed_to`, no `frozen_at_sha` and no tombstone — strictly more than a
  census row. What closes `E` is **mechanism, not prose**: fixed arity by type **plus** a hash of its sorted
  entry set held outside the declaring module.
- **C-001/C-006**: `tests/conftest.py` is the **only** existing file edited; **no existing test module is
  touched**; no file under `src/` changes.

---

### Subtask T010: `contracts/canonical-home-owner.md` — this WP's FIRST deliverable, and an ordering fact that survives a squash

**Purpose**: Fix the names and stances the next four subtasks assert over. A vague contract makes them
unwritable.

**Steps**:

1. Author `contracts/canonical-home-owner.md` (mission-directory artefact assigned to this WP). It fixes,
   **normatively**:
   - the fixture's **NAME** — **because FR-010's resolver limb treats a parameter naming this owner as
     `tmp_path` for both the silhouette and value resolution, the name is a SCANNER INPUT, not a local
     detail**;
   - `autouse=False`;
   - **function scope by ABSENCE of `scope=`**;
   - that it **yields `None`, and WHY**: returning its own path invites
     `assert os.environ[...] == owner`, which compares the environment against the fixture's **own report**
     and passes for an owner that sets nothing;
   - that it establishes the home **ONLY via `monkeypatch.setenv`** — no `Path.home` patch, no process-global
     patch;
   - that it **creates the directory before the test body runs**;
   - that it **never overrides a definition keeping its own pin**;
   - that it is inserted **STRICTLY after `tests/conftest.py:298`**;
   - and that **`tuple[str, str]` is the type of the owner's ENTRY IN `E`, never of the fixture**.
2. **THE DoD IS AN ORDERING FACT, NOT A FILE.** Run
   `git merge-base --is-ancestor <contract commit> <owner commit>` and **RECORD ITS OUTPUT** — both SHAs and
   the command output — into `record.md` **AT AUTHORING TIME**, because the ancestry itself does not survive
   the squash or rebase a lane consolidation may perform. **That recording is the durable artefact.**

**Files**: `contracts/canonical-home-owner.md` (new, ~90 lines); `record.md` (append the ordering evidence).

**Validation**: T011..T014's assertions are stated over the names this document fixes; **T012 parses this
file for the declared fixture name**, so the document is mechanically bound to the code rather than merely
adjacent to it.

**What this cannot see**: whether the owner works. Nothing about a contract can.

---

### Subtask T011: Add the owner fixture to `tests/conftest.py`, strictly after line 298

**Purpose**: FR-005's canonical owner. Every assertion in this subtask is **SHAPE** — that is deliberate, and
it is why T012 exists.

**Steps**:

1. Add **exactly one** new fixture to `tests/conftest.py`, with the name, stance and body the contract fixes.
2. **`git diff -U0` shows NO hunk touching any line at or below 298.**
3. **SC-010 IS MECHANISED AS A LIST, NOT A SCALAR**: assert the module's **ORDERED LIST of definition names,
   with the newly-added owner removed**, is **equal to the same list computed at the merge-base**. Take the
   whole module, not only the names preceding `_isolated_worker_home` — the narrower form cannot see a
   reorder *below* the anchor, and conftest fixture resolution depends on the ordering throughout. (Note for
   the reviewer: `spec.md` SC-010 says the module's ordered list is *"unchanged"*, which is literally
   unsatisfiable once a fixture is added; "unchanged with the new owner removed" is the satisfiable reading
   and is strictly stronger than the preceding-only one.)
   A scalar definition **INDEX** — the previous form — is **invariant under
   insert-one-above-plus-delete-one-above**, and in a Mission governed by C-002 it was the last surviving
   scalar comparand.
4. AST assertions on the new fixture:
   - `autouse` **absent or False**;
   - **no `scope=` kwarg**;
   - **no `monkeypatch.setattr(Path, "home", ...)`** and **no process-global patch**;
   - the body contains a `monkeypatch.setenv("SPEC_KITTY_HOME", ...)` **AND** a `mkdir`;
   - it **yields/returns `None`**.

   **That third and fourth bullet are `FR-006`'s STATIC half** — establishment by `monkeypatch.setenv` only,
   never `monkeypatch.setattr(Path, "home", ...)`, never any process-global patch. It is only half:
   **`FR-006` requires the rule DEMONSTRATED BEHAVIOURALLY, not merely asserted from source**, so T012
   carries the establishment half and T013 the never-wins half.
5. **NFR-005** — no interference with the existing home owner — is **demonstrated by the ordered-list check
   above**, not assumed.
6. **C-005 binds unchanged**: `tests/conftest.py:272-286`'s **env-var-only precedence decision is not
   altered**, and it is the decision this fixture must not violate.

**Files**: `tests/conftest.py` (edited, +~25 lines, strictly after line 298).

**Validation**: **Inserting above 253 shifts the ordering while the old line range shows no modification.**
The ordered-name-list assertion is the only limb that sees it.

**What this cannot see**: that the owner does anything.

---

### Subtask T012: `test_home_owner_behaviour.py` — the owner's statics and the one assertion that proves it works

**Purpose**: Limb (i) carries the entire behavioural load alone. Write it so it cannot be satisfied by an
owner that sets nothing.

**Steps**:

1. **(i) SC-012 limb 1** — a probe requesting the owner asserts
   `os.environ["SPEC_KITTY_HOME"] == str(tmp_path / "home")` **with the expected value COMPUTED IN THE TEST
   from its own `tmp_path`, never read from the fixture's return**, and asserts
   `Path(os.environ["SPEC_KITTY_HOME"]).is_dir()` **AT TEST-BODY ENTRY**.
2. **(ii) C-014 limb (i)** — `ScopeMismatch` at setup. **THE ROUTE MATTERS AND `pytester` IS NOT AVAILABLE**:
   measured, **zero uses under `tests/`**, it is not auto-loaded, and there is **NO root `conftest.py`**, so
   enabling it needs a rootdir conftest or an `addopts` change — **both outside C-006's blast radius**.
   The **in-scope route** is a **module-scoped fixture calling `request.getfixturevalue("<owner>")` inside
   `pytest.raises(pytest.fail.Exception)`**.
   **STATE EXPLICITLY IN THE MODULE that `pytest.raises(Exception)` does NOT catch it** — pytest converts
   `ScopeMismatch` to `Failed`, a `BaseException` subclass, which escapes as a setup **ERROR** and costs an
   implementer an hour.
3. **(iii) C-014 limb (ii)** — a module **not naming** the owner **never instantiates it**, asserted by
   observing the **ABSENCE of the effect**, **never by reading source**.
4. Plus **SC-005's owner limbs** and **SC-010**, AST-asserted over `tests/conftest.py`.
5. Plus **THE CONTRACT BINDING**: this module **parses `contracts/canonical-home-owner.md`** for the declared
   fixture name, autouse stance and scope, and asserts the conftest fixture carries **THAT** name and
   **THOSE** properties, so the document cannot drift from the code.
6. **AND THE ASSERTION THAT CLOSES FR-010's CIRCULARITY**: assert the **same parsed fixture name is a member
   of `_home_pin_scan.OWNER_PARAM_NAMES`**. WP01 ships that set — `{tmp_path, canonical_home, runtime_home}`
   — with `canonical_home` taken from **FR-010's prose**, at a moment when the contract that names the owner
   **did not yet exist**. Measured in review: removing or renaming `canonical_home` reds only two tests and
   **both are WP01's own fixture tree** — the author's string on both sides of the equality; and `runtime_home`
   can be removed entirely with 69/69 still green. **If this WP names the owner anything else, FR-010's limb
   goes PERMANENTLY INERT with every WP01 assertion still green**, and the shrink-only ratchet then greens on
   every disappearance — which is the failure FR-010 exists to prevent (*"the guard goes blind in proportion
   to R1b's adoption"*). This is the **fourth-operand pattern** the `INERT_LIMBS` quadruple established, an
   operand outside the author's control, applied to the **resolver** instead of the registry. WP01 could not
   build it: the document did not exist. **You can, and it is two assertions.**
6. Plus **NFR-006**: the resolved `pytest.__version__` and the **verbatim invocation** are recorded in
   `record.md`. **This WP is where the pytest-version sensitivity actually lives** (`ScopeMismatch`
   conversion, non-instantiation). **Never a bare `uv run`.**

**Files**: `tests/architectural/test_home_owner_behaviour.py` (new, ~220 lines); `record.md` (append pytest
version + invocation).

**Validation**: Limbs (ii) and (iii) are properties of pytest's fixture machinery and **pass against an owner
whose body is `return None`**. **Limb (i) carries the entire behavioural load alone**, and SC-011 green is
**not** evidence the owner works.

**What this cannot see**: C-014 limb (iii), which needs **adopters**; R1a has **zero**, and that residual is
**recorded** (WP06/T030) rather than discovered later.

---

### Subtask T013: `test_home_owner_never_wins.py` — the exempt member, and the negative control that makes the claim bite

**Purpose**: FR-011's probe modules — **TWO of them, because SC-012 limb 2 as specified CANNOT FAIL.**

**Steps**:

1. **(a) THE E-SLOT MEMBER** — a **module-local FIXTURE** (never a body-level `setenv`, which overrides the
   owner unconditionally and proves nothing about the fixture-versus-fixture precedence decision at
   `tests/conftest.py:272-286`) pinning `SPEC_KITTY_HOME` to `str(tmp_path / "home")`, **declared AFTER the
   owner in the requesting order stated in the module**, whose body observes that value.
2. **(b) THE DISCRIMINATING NEGATIVE CONTROL** — a **second** module-local fixture pinning
   `str(tmp_path / "probe-home")`, **requesting the owner**, whose body asserts it observes **`probe-home`**.
3. **Why both.** Probe (a) is a **class member** and spends **one of `E`'s two irrevocable slots**; probe (b)
   is **NOT a member**, costs **no slot**, and is **the ONLY assertion in the pair that can fail** — because
   the owner and any class member both resolve to `str(tmp_path / "home")`, **the SAME STRING within one
   test**, so (a) is green **whether the owner won or lost**.
4. Record this as a **spec finding**, not a silent repair.

**Files**: `tests/architectural/test_home_owner_never_wins.py` (new, ~140 lines).

**Validation**: Remove (b) and the module greens for an owner that **overwrites every module's pin** — the
failure `tests/conftest.py:272-286` records having cost ~16 `tests/sync` cases.

**What this cannot see**: behaviour under real adoption, which R1a has none of.

---

### Subtask T014: `_home_pin_exempt.py` — `E` declared where its content is determined, and content-addressed

**Purpose**: `E` lives here because **both keys are determined by this WP's own two artefacts and nothing
else**. WP04 tests the **MECHANISM** over materialised exempt tuples; WP05 asserts the **REAL** hash and runs
mypy over **this** file. No package edits another's.

**Steps**:

1. Declare `E: tuple[Exempt, Exempt]` — **fixed arity BY TYPE**, using the `Exempt` **exported by
   `_home_pin_scan.py` (WP01/T001)** and **never a local stand-in** — containing exactly:
   - the **canonical owner** (T011), and
   - the **retained-pin probe fixture** (T013a).
2. **THE FORM IS CONSTRAINED BY AN EXISTING RATCHET nobody had named**:
   `tests/architectural/test_ratchet_positional_anchor_ban.py::test_no_int_line_sink_in_architectural_python_seeds`
   walks every `tests/architectural/**/*.py` and flags an **int literal reaching
   `composite_key_from_file(path, N)`'s second positional argument**, including (per its **#2564** clause) a
   **module-level seed constant of `(rel, int, ...)` rows** — which is **exactly the naive shape of `E`**.
3. **Compliant form**: `E`'s keys are **content-addressed 3-tuples**, and any `lineno` used in recomputation
   comes from `discover()` **AT RUNTIME**, never from a literal.
4. A test asserts **each declared key equals `(relpath_posix, *composite_key_from_file(path, lineno))`
   recomputed live with that runtime lineno**, and asserts
   `{e.key for e in E} ⊆ {m.key for m in discover(Path("tests"))}`.

**Files**: `tests/architectural/_home_pin_exempt.py` (new, ~60 lines); assertions live in this WP's test
modules.

**Validation**: An `E` entry naming a **phantom definition** would inflate `census ∪ E` and be caught only in
WP05; **the subset assertion catches it in the package that wrote it.**

**What this cannot see**: whether `E` should have **those two** entries — that is a decision of record, and
`E` **fails the reviewer test by construction**, which §0.4 states plainly.

---

## Definition of Done

Per-subtask completion is a `spec-kitty agent tasks mark-status <Txxx> --status done` event.

1. **PRECONDITION, before the first subtask**: `tests/architectural/test_home_pin_gate_verdict.py` is present
   and **GREEN** in this lane's worktree. The lane allocator merges lane-a's tip in, but **degrades to a
   printed warning** if the dependency branch is unresolvable (`worktree_allocator.py:462-472`), **so this is
   checked, not assumed**.
2. The contract is committed **BEFORE** the owner and the `git merge-base --is-ancestor` output is recorded in
   `record.md` **at authoring time**.
3. **SC-012 limb 1** passes with the expected value **computed by the probe**; **limb 2 ships with the
   differing-value negative control** that makes it falsifiable.
4. `E`'s keys are **content-addressed with runtime linenos**, keeping
   `test_no_int_line_sink_in_architectural_python_seeds` green, and are a **subset of
   `discover(Path('tests'))`**.
5. **ZERO `ast.parse` calls and ZERO `ast.NodeVisitor` subclasses** in every module of this WP; AST work goes
   through `_home_pin_scan`'s seam, and materialised sources through `parse_module`.
6. **IC-08 landing, mechanically**: both new test modules **top-level** and `architectural`-marked, covered by
   `test_gate_coverage.py::test_no_new_orphan_surfaces`. **`tests/_arch_shard_map.py` is NOT edited.**
7. Identical results under `-n0` and `-n auto --dist loadfile` — **this WP touches the root `conftest.py`**,
   so the per-worker HOME isolation path is exercised in both.
8. **C-001** holds: `tests/conftest.py` is the **only** existing file edited and **no existing test module is
   touched**. **NFR-004**: `ruff check` and `mypy --strict` clean, **never `ruff format`**. **NFR-003**:
   identical results in both parallel modes. **C-013**: nothing merged, no `gh issue create`, explicit-path
   `git add`, long commands bounded with `timeout`.

## Not Done If

- The owner returns anything other than `None`, or a probe compares the environment against **the fixture's
  own report**.
- The retained-pin probe's pin lives **in the test body** rather than in a **module-local fixture**.
- `test_home_owner_never_wins.py` ships **without the differing-value negative control**.
- **SC-010 is asserted as a scalar definition index** rather than as the **ordered list of preceding
  definition names**.
- `E` **embeds a literal line number**, or declares a **local `Exempt`** instead of importing
  `_home_pin_scan`'s.
- **Any hunk of the `tests/conftest.py` diff touches a line at or below 298.**

## Risks

| Risk | Mitigation |
|---|---|
| **The golden-count ratchet has ZERO headroom.** `tests/architectural` sits at **25/25** convert-classified sites against a frozen ceiling of **25**, so **any** new `len(x) == N` assertion in this WP trips `test_golden_count_ban::test_convert_sites_do_not_exceed_frozen_baseline`. | Every assertion is a **SET comparison, never a count**. **The baseline may NOT be re-frozen** — the fix is always to convert the assertion, never to raise the bound. C-002 already forbids a counted definition of done; this is that rule at the point it bites. |
| An owner whose body does nothing satisfies SC-011 in full. | T012 limb (i) computes the expected value in the test and asserts the directory exists at body entry. It is the only limb that can fail on an inert owner. |
| `pytest.raises(Exception)` silently fails to catch `ScopeMismatch`. | pytest converts it to `Failed`, a `BaseException` subclass. Use `pytest.raises(pytest.fail.Exception)` and **say so in the module**. |
| `pytester` looks like the natural route for the scope test. | Measured: zero uses under `tests/`, not auto-loaded, no root `conftest.py`. Enabling it is **outside C-006's blast radius**. Use `request.getfixturevalue`. |
| SC-012 limb 2 is vacuous as specified. | The negative control (T013b) is what makes it bite. Recorded as a **spec finding** in WP06/T030, not silently repaired. |
| `E` written as a module-level `(rel, int, ...)` seed. | Reds `test_no_int_line_sink_in_architectural_python_seeds` (#2564 clause). Content-address the keys; take linenos from `discover()` at runtime. |
| Pre-existing reds (C-009 vs DIR-013). | Classify per CLAUDE.md's baseline-red gotcha; record evidence in `record.md`; route to the **OPERATOR** as a TG-item. **C-013 forbids `gh issue create` here.** |

## Reviewer Guidance

- **SC-011 green is not evidence the owner works.** Read T012 limb (i) and confirm the expected value is
  computed from the probe's own `tmp_path`.
- Confirm the negative control in T013b exists and pins a **different** value. Without it the module greens
  for an owner that overwrites every module's pin.
- Confirm SC-010 is an **ordered list**, not an index.
- Confirm the contract-parsing binding in T012(5) actually reads
  `contracts/canonical-home-owner.md` — an unbound contract drifts on the first rename.
- Confirm `git diff -U0` on `tests/conftest.py` shows no hunk at or below line 298.

## Implementation

```bash
spec-kitty agent action implement WP03 --agent <name>
```
