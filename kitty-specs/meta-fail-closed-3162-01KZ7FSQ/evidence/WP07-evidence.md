# WP07 evidence — Re-pin both of #2804's red assertions and close the tracker honestly

**Out-of-map planning write, declared.** `spec-kitty agent tasks mark-status` carries only
`{T0xx: Status}` (`src/specify_cli/status/models.py:481`) and has no evidence field; `kitty-specs/`
paths cannot appear in `owned_files` by construction (`mission_parsing.py:153-157`, `:207-215`). This
file is WP07's committed evidence destination, per the WP prompt's "Committed evidence destination"
section.

- **Mission**: `meta-fail-closed-3162-01KZ7FSQ` — **WP07** — profile `python-pedro`, role `implementer`
- **Tree**: repository root `/home/jeroennouws/dev/sk-missions/3162` (`.worktrees/` absent), branch
  `feat/meta-fail-closed-3162`
- **WP07 commits** (four, unsquashed, in order):
  | # | SHA | Subject |
  |---|---|---|
  | 1 | `a199e4865` | `test(WP07): widen #2804 assertion 1 to the design's admissible verdicts` — **INTERMEDIATE RED** |
  | 2 | `cea544596` | `test(WP07): re-pin #2804 assertion 2 to evidence survival, not marker absence` |
  | 3 | `06258eb46` | `test(WP07): SC-010 companion — the re-pinned pair fails on the defect's own fixture` |
  | 4 | (this commit) | `docs(WP07): backfill the tracker numbers (#3231, #3232) + WP07 evidence` |

## `C-008` exception, declared out loud

**This requirement's red is an INVERTED RED — pre-existing on `main` and *wrong*.** The assertions
were wrong, not the product. So, uniquely for this WP, the work makes the marker **green**, and all
four steps of the inverted-red protocol are discharged below: (1) the failing selection quoted
**before** the change on a pristine base; (2) **every** failing assertion named — there were two, not
one; (3) the **separately-filed product defect** cited (#3231), plus #3138 for the red itself; (4) the
companion falsifiability test failing on **the defect's own fixture**, not on an unrelated disallowed
value.

---

# T041 — Both reds quoted, pristine-base reproduction, reconciler measured control-first

## 1. Both assertions and the shared banner, quoted verbatim pre-change

File: `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py`
Enclosing symbol: `test_merge_resets_filled_gate_artifacts_to_placeholder` (`C-003`)

**Banner — one banner, two assertions** (first line `:476`):

```python
    # --- CONTRACT (RED on base): the permanent record left on the          # :476
    # integration branch must still be the FILLED content, not the reset
    # scaffold placeholder. On buggy main, the ``-X theirs`` squash-merge
    # conflict resolution takes the mission branch's stale placeholder over
    # target's already-accepted fill. ---
```

**Assertion 1** (`:482`):

```python
    assert post_matrix.get("overall_verdict") == "pass", (
        "#2804: spec-kitty merge reset acceptance-matrix.json's overall_verdict "
        f"to {post_matrix.get('overall_verdict')!r} -- the filled, accepted "
        "evidence was clobbered by the mission->target squash merge's "
        "'-X theirs' conflict resolution (mission branch's stale placeholder "
        "won over target's already-accepted fill)."
    )
```

**Assertion 2** (`:489`):

```python
    assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix), (
        "#2804: spec-kitty merge reset acceptance-matrix.json's criteria back "
        f"to the scaffold placeholder ({SCAFFOLD_TODO_MARKER!r}), discarding "
        f"the real accepted evidence. Post-merge content: {post_matrix!r}"
    )
```

**Line numbers confirmed by opening the file**, not by grep. `:442` is a **different**
`SCAFFOLD_TODO_MARKER not in json.dumps(...)` assertion — the **pre-merge precondition on
`pre_matrix`** — and is **not** one of the two:

```python
    assert SCAFFOLD_TODO_MARKER not in json.dumps(pre_matrix), (          # :442
        "precondition: fixture must start FILLED, not the scaffold placeholder"
    )
```

Grepping for the marker and taking the first hit picks that wrong assertion. `:442` is untouched by
this WP.

## 2. Pristine-base reproduction on `upstream/main` `98198e980`

```bash
git worktree add <scratch>/repro-3162-main 98198e980
cd <scratch>/repro-3162-main
PYTHONPATH=<scratch>/repro-3162-main/src \
  /home/jeroennouws/dev/sk-missions/3162/.venv/bin/python -m pytest -ra \
  tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder \
  > <scratch>/pre.txt 2>&1; echo "exit=$?"
```

- `git rev-parse upstream/main` → `98198e980045752a1f5ce0ba75796d3e5dddadf1` (i.e. `98198e980` **is**
  `upstream/main`)
- **`PYTHONPATH` used**:
  `/tmp/claude-1000/.../scratchpad/wp07/repro-3162-main/src` — the pristine worktree's **own** `src/`.
  Without it, `.venv`'s editable `.pth`
  (`_editable_impl_spec_kitty_cli.pth`) would import **this branch's** `src/` and the "pristine" red
  would not be pristine.
- **Tree this result came from**: the pristine `98198e980` worktree, confirmed by `rootdir:`.

```
rootdir: /tmp/claude-1000/-home-jeroennouws-dev-sk-missions/ca298d9c-391a-43ff-ab54-419c109c6f77/scratchpad/wp07/repro-3162-main
```

```
E   AssertionError: #2804: spec-kitty merge reset acceptance-matrix.json's overall_verdict to 'pending' -- the filled, accepted evidence was clobbered by the mission->target squash merge's '-X theirs' conflict resolution (mission branch's stale placeholder won over target's already-accepted fill).
E   assert 'pending' == 'pass'
E     
E     - pass
E     + pending
```

```
======================== 1 failed in 161.89s (0:02:41) =========================
```

`exit=1`. `grep -c '^ERROR tests/' <scratch>/pre.txt` → **0**. (Counted `^ERROR tests/`, not
`^ERROR `. `-ra`, never `-rf`. Redirected, never piped. The run completed; it was not killed.)

## 3. "Known class tracked elsewhere" is **not** a pre-existing classification

Only the **same-selection reproduction on a pristine base** above is one. #3138 ("Regression: #2804's
red marker is failing again on main") names the class, but naming a class does not establish that
*this* selection is red on *this* base. The `98198e980` worktree run, with its own `PYTHONPATH`, does.
That reproduction also discharges the charter's **Pre-existing Failure Reporting Rule** for this red,
which is tracked as #3138.

**Routed count PRE** — WP01's recorded measurement command (`contracts/routing-manifest.md` §4.1),
verbatim, on the repository root tree:

```bash
.venv/bin/python -m pytest tests/architectural/test_inline_meta_read_gate.py -ra > <scratch>/wp07_routed_pre.txt 2>&1
```

```
======================== 40 passed in 165.24s (0:02:45) ========================
```

`grep -c '^ERROR tests/'` → **0**. Then the gate's own AST scanners invoked directly, printing the
count **and the input file count walked**:

```
== §4 LIVE COUNTS (gate's own AST scanners) ==
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 129
  INLINE live (AST walk): 7
  DERIVED routed band: [127, 130] (two-sided; 126 is RED)
  routed 129 in [127, 130]: OK
```

**Routed PRE = 129** over an input population of **1 199** `*.py` files under `src/`. Band `[127, 130]`,
two-sided; **126 is RED** (clause 2 of `test_routed_load_meta_floor` is strict:
`len(routed) > ROUTED_LOAD_META_FLOOR`, and `126 > 126` is false). See T045 for POST and for why the
branch-level number is not WP07-attributable.

## 4. Reconciler measurement pair — **control first**

Probe: `reconcile_acceptance_matrix_documents` (`src/specify_cli/cli/commands/merge_driver.py:601`)
fed the marker module's **own** fixtures — `FILLED_ACCEPTANCE_MATRIX` as *ours*,
`PLACEHOLDER_ACCEPTANCE_MATRIX` as *theirs*, empty base (the add/add divergence).

```
CONTROL filled fixture contains marker?  False
merged criterion_ids: ['AC-001', 'FR-001', 'FR-003']
overall_verdict: pending
POST contains SCAFFOLD_TODO_MARKER?      True
```

and, for the assertion-2 re-pin target:

```
accepted evidence survives in merged doc: True
take-theirs control (placeholder alone):  False
two-way self-control: handle in FILLED: True
```

## 5. Conclusion, in one line

**Widening only the verdict assertion cannot make `SC-008` pass**, because the row-union admits the
scaffold row whose `description`/`notes` *are* the marker — the control proves the marker is not
already in the FILLED input, so it arrives **with the union**, by design.

---

# T042 — COMMIT 1 `a199e4865`: assertion 1 widened

**SHA: `a199e4865`** — `test(WP07): widen #2804 assertion 1 to the design's admissible verdicts`

**Pre** (`:482`): `assert post_matrix.get("overall_verdict") == "pass", ...`

**Post**:

```python
    assert post_matrix.get("overall_verdict") in ADMISSIBLE_MERGED_VERDICTS, (
        "#2804: spec-kitty merge left acceptance-matrix.json's overall_verdict "
        f"at {post_matrix.get('overall_verdict')!r}, outside the design's "
        f"admissible verdicts {sorted(ADMISSIBLE_MERGED_VERDICTS)!r} -- the "
        "filled, accepted evidence was clobbered by the mission->target squash "
        "merge's '-X theirs' conflict resolution (mission branch's stale "
        "placeholder won over target's already-accepted fill)."
    )
```

with

```python
ADMISSIBLE_MERGED_VERDICTS: frozenset[str] = frozenset(
    {"pass", "pending", VERDICT_PASS_PENDING_CONSOLIDATION}
)
```

**`pending` is demonstrably ADMITTED** — it is a member of the frozenset, and the T042 run below shows
assertion 1 passing on a document whose `overall_verdict` is `'pending'`. That is required, not
incidental: the cross-file sibling
`tests/specify_cli/cli/commands/test_row_aware_merge_driver.py::test_merge_driver_acceptance_matrix_writes_result_to_ours`
pins `merged["overall_verdict"] == "pending"` for exactly this union shape, and contradicting it would
weaken the row-union design rather than fix the marker.

The assertion's own comment records both facts a future reader would otherwise re-derive wrongly:
`"fail"` **is** a concrete disallowed verdict reachable from a one-criterion fixture
(`src/specify_cli/acceptance/matrix.py:259`, `if any(v == "fail" for v in criterion_results)`), **and
`"fail"` alone is insufficient evidence** because `pending` is the defect's own signature and must be
admitted — so `verdict in {"pass", "pending"}` passes with the regression fully present. Assertion 2
carries the falsifiability.

**Not touched in this commit**: assertion 2, and the already-widened, already-green issue-matrix
assertions.

## The intermediate state — quoted as RED, never as green

Re-captured on a **clean detached worktree at `a199e4865`** (so no later edit could contaminate the
report), `PYTHONPATH=<worktree>/src`:

```
rootdir: /tmp/claude-1000/.../scratchpad/wp07/wt-a199e4865
```

```
E   AssertionError: #2804: spec-kitty merge reset acceptance-matrix.json's criteria back to the scaffold placeholder ('TODO: replace with a real acceptance criterion'), discarding the real accepted evidence. ...
E   assert 'TODO: repla...ce criterion' not in '{"mission_s...riants": []}'
```

```
FAILED tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder
======================== 1 failed in 108.54s (0:01:48) =========================
```

`grep -c '^ERROR tests/'` → **0**.

**Still-failing assertion, named**: assertion 2,
`assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix)`. Assertion 1 now passes (the real
post-merge `overall_verdict` is `'pending'`, which the widened predicate admits). **COMMIT 1 is an
intermediate red. It is not green and is not presented as green.**

A second capture of the same intermediate state was taken from the repository root
(`1 failed in 145.84s`), with the same failing assertion; the clean-worktree capture above is the
authoritative one.

**Load-bearing detail visible in that same failure output**: the post-merge document produced by the
**real** squash merge already contains `'WP01 (commit d5b8324f9): src/charter/generator.py deleted; ...'`
— i.e. the accepted evidence handle survives the real merge, not merely the reconciler in isolation.
That is what makes the T043 re-pin satisfiable against reality.

`ruff check tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` → `All checks passed!`
(**`ruff format` never run** — this repo is not `ruff format`-clean.)

---

# T043 — COMMIT 2 `cea544596`: assertion 2 re-pinned to evidence survival

**SHA: `cea544596`** — `test(WP07): re-pin #2804 assertion 2 to evidence survival, not marker absence`

**Assertion 2 pre** (`:489`): `assert SCAFFOLD_TODO_MARKER not in json.dumps(post_matrix), ...`

**Assertion 2 post** (inside the shared helper):

```python
    assert ACCEPTED_EVIDENCE_HANDLE in json.dumps(post_matrix), (
        "#2804 (assertion 2, evidence survival): spec-kitty merge discarded the "
        f"target's real, accepted evidence ({ACCEPTED_EVIDENCE_HANDLE!r}) "
        "without leaving any trace of it -- not even inside a structured "
        f"conflict marker. Post-merge content: {post_matrix!r}"
    )
```

**Re-pinned, NOT deleted.** `Q10` is settled: keep the marker. The message has the same shape as the
in-file issue-matrix sibling's `"verified-already-fixed" in json.dumps(merged_row)` (the `assert` is
on **`:512`** in the pre-change file — confirmed by opening it; an earlier draft said `:513`).

**Module constant**, derived from the fixture rather than hand-typed twice:

```python
ACCEPTED_EVIDENCE_HANDLE = "d5b8324f9"
```

It is the commit handle already carried by `FILLED_ACCEPTANCE_MATRIX`'s `FR-001` evidence — at
**`:117-124`** in the pre-change file (the WP prompt says `:114-121`; **opened and
corrected** — the `"evidence": (` key opens on `:117` and the closing paren is on `:124`, with
`d5b8324f9` on `:118`).

**Two-way fixture self-control**, asserted on every call of the helper:

```python
    assert ACCEPTED_EVIDENCE_HANDLE in json.dumps(FILLED_ACCEPTANCE_MATRIX), (...)
    assert ACCEPTED_EVIDENCE_HANDLE not in json.dumps(PLACEHOLDER_ACCEPTANCE_MATRIX), (...)
```

A handle absent from the filled side makes the pin unsatisfiable by construction (a permanent false
red); a handle present on the placeholder side makes it vacuous (it would survive even a total
take-theirs clobber). Neither is catchable by the merged-document assertion alone.

**Shared helper exists and the marker calls it:**

```python
def _assert_2804_acceptance_contract(post_matrix: Mapping[str, Any]) -> None:
```

called from `test_merge_resets_filled_gate_artifacts_to_placeholder` as
`_assert_2804_acceptance_contract(post_matrix)`, replacing the two inline assertions.

**Measured** (T041 §4): `accepted evidence survives in merged doc: True`;
`take-theirs control (placeholder alone):  False`.

**Docstring diff** — the false framing removed and replaced:

```diff
-RED-FIRST P0 reproduction, intentionally FAILING until the product defect is
-fixed. Tracking issue: https://github.com/Priivacy-ai/spec-kitty/issues/2804.
-Do NOT xfail/skip/quarantine to green; fix the product.
+**WP07 ... re-pin.** This module was previously framed as "intentionally FAILING
+until the product defect is fixed". That framing is now FALSE and has been
+removed: the red was an **inverted red** ... Both assertions ... have been
+re-pinned ... ``Q10`` is **settled: keep the marker.**
+ 1. **Admissible verdict.** ... It deliberately **admits** ``pending``.
+ 2. **Evidence survival.** ... negatively controlled against the take-theirs shape.
+**Why the shape changed.** ... the **row-union authority model** shipped as
+``#3076``'s FR-008 ... The marker moved, not the design.
+**The product defect is FILED, NOT FIXED here** (``C-006``; filed per ``C-009``)
+... ``matrix.py:263`` ... ``gates_core.py:525`` ... ``:528`` ...
+Product defect: .../issues/3231. Superseding issue for #2804: .../issues/3232.
+... #2804 (**superseded, not reopened**). Returning-red bisect: #3138.
+... ``b04da00e1`` (-249 lines); ... deliberately NOT restored here.
```

(The issue numbers were placeholders in `cea544596` and are backfilled in COMMIT 4, per T043 step 5 /
T046 step 5.) The per-test docstring's "Intentionally FAILS until the product bug is fixed" was
replaced on the same commit.

**Both re-pinned assertions now pass** — see T044's combined run (`2 passed`), which is the run that
exercises assertion 2 against the document a **real** squash merge left behind.

`ruff check` → `All checks passed!`

---

# T044 — COMMIT 3 `06258eb46`: the companion, fed the defect's own fixture

**SHA: `06258eb46`** — `test(WP07): SC-010 companion — the re-pinned pair fails on the defect's own fixture`

**The failing case is the defect's OWN fixture**, quoted:

```python
def _take_theirs_acceptance_document() -> dict[str, Any]:
    """The #2804 defect's **own** fixture: the take-theirs / scaffold-clobber
    document. ... criteria reset to ``PLACEHOLDER_ACCEPTANCE_MATRIX`` alone.
    Built through the real :class:`AcceptanceMatrix` so ``overall_verdict`` is
    COMPUTED (``pending``), not hand-asserted, and the accepted evidence handle
    is **absent**."""
    return AcceptanceMatrix.from_dict(PLACEHOLDER_ACCEPTANCE_MATRIX).to_dict()
```

with both preconditions asserted in the test itself — `overall_verdict == "pending"` (the defect's own
signature) and `ACCEPTED_EVIDENCE_HANDLE not in json.dumps(take_theirs)` (that absence **is** the
defect).

**It calls the same helper the marker calls** — not a copy:

```python
    with pytest.raises(AssertionError) as excinfo:
        _assert_2804_acceptance_contract(take_theirs)
```

**The raised message is asserted and attributed to the evidence-survival clause:**

```python
    assert "assertion 2, evidence survival" in message, (...)
    assert ACCEPTED_EVIDENCE_HANDLE in message, (...)
    assert "assertion 1" not in message, (
        "SC-010: 'pending' is the defect's own signature and MUST be ADMITTED "
        "by assertion 1 (the cross-file row-aware sibling pins it). ...")
```

The raised `AssertionError` text is the helper's assertion-2 message:

```
#2804 (assertion 2, evidence survival): spec-kitty merge discarded the target's real, accepted
evidence ('d5b8324f9') without leaving any trace of it -- not even inside a structured conflict
marker. Post-merge content: {...}
```

A future edit that moved the failure to some other clause (or to the fixture self-control) would break
those assertions, so it is visible.

**Positive twin present and passing**: `_assert_2804_acceptance_contract(merged)` on
`_row_union_merged_acceptance_document()` — what the shipped reconciler actually produces for this
fixture pair. A negative with no positive twin is the vacuous gate
`architectural-gate-non-vacuity` forbids (charter Standing Order 5).

**`"fail"` witness present and labelled insufficient**: `_one_criterion_fail_document()` yields
`overall_verdict == "fail"` (`src/specify_cli/acceptance/matrix.py:259`) and
`pytest.raises(AssertionError, match="assertion 1")`. The docstring states in one paragraph that
`pending` is the defect's own signature and is *admitted* by the widened predicate, so
`verdict in {"pass", "pending"}` plus a `fail` fixture is **not** falsifiability — and that this
witness *alone* is **not `SC-010` evidence**.

**Runtime** — fast by construction; it never runs the squash-merge harness:

```
============================= slowest 6 durations ==============================
0.02s setup    tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_widened_2804_assertion_rejects_wrong_verdict

(2 durations < 0.005s hidden.  Use -vv to show these durations.)
======================== 1 passed in 111.55s (0:01:51) =========================
```

The companion's **own** cost is `0.02s` setup and a call under `0.005s`; the ~111 s wall clock is this
repo's session-level pytest startup (collection/plugins/conftest), identical for any single-node run
here — not the test.

**Marker + companion together, by node id, redirected, `-ra`:**

```bash
.venv/bin/python -m pytest -ra \
  "tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder" \
  "tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_widened_2804_assertion_rejects_wrong_verdict" \
  > <scratch>/t044_both.txt 2>&1
```

```
collected 2 items

tests/regression/test_issue_2804_merge_resets_gate_artifacts.py ..       [100%]

========================= 2 passed in 90.61s (0:01:30) =========================
```

`grep -c '^ERROR tests/'` → **0**. **Selected count: 2 of 2 green.**

`ruff check` → `All checks passed!`

---

# T045 — `SC-008`'s byte-identity proofs, routed delta, perishability

## 1. The cross-file sibling is byte-identical **and** green

```bash
$ ls tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
tests/specify_cli/cli/commands/test_row_aware_merge_driver.py      # exit 0 — the file exists

$ git diff --stat upstream/main -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
                                                                   # (no output; 0 lines)
```

The output is **empty**, and `ls` succeeds — so the emptiness means "unchanged", not "no such path".
(The `tests/merge/test_row_aware_merge_driver.py` variant does **not** exist and would have printed
nothing for the wrong reason; `ls tests/merge/test_gate_artifact_merge_drivers_2804.py` →
`No such file or directory`, which is the separate, deliberate T046 citation.)

**Unchanged is not green**, so it was also run. It lives inside `tests/specify_cli` and is **not** the
barred top-level `tests/cli`:

```bash
.venv/bin/python -m pytest -ra tests/specify_cli/cli/commands/test_row_aware_merge_driver.py > <scratch>/t045_sibling.txt 2>&1
```

```
collected 39 items

tests/specify_cli/cli/commands/test_row_aware_merge_driver.py .......... [ 25%]
.............................                                            [100%]

======================== 39 passed in 85.38s (0:01:25) =========================
```

`grep -c '^ERROR tests/'` → **0**. **Selected count: 39, all green** — including
`test_merge_driver_acceptance_matrix_writes_result_to_ours`, which pins
`merged["overall_verdict"] == "pending"` for this union shape. That sibling is the **correct** side of
the old contradiction; the marker moved, not it.

## 2. `SC-008` restated, and the one item this WP could **not** satisfy as worded

`SC-008`'s original phrasing — "both assertions pass on current `main`" — is **unrunnable**: the
widened marker lives on the branch, not on `main`. The runnable restatement (`spec.md:403-405`) is
**"passes on branch head with `src/` unchanged from the measurement baseline `96494e5ec`"**, proved by
`git diff --stat 96494e5ec -- src/` printing nothing.

**That command no longer prints nothing, and cannot be made to — through no act of WP07.** WP07 ran
in the shared repository root (`.worktrees/` absent) **concurrently with the WP02 and WP05 agents**,
which committed their own routing work to the same branch, interleaved with WP07's commits:

```
$ git diff --stat 96494e5ec -- src/
 src/runtime/next/_internal_runtime/planner.py   | 12 ++--
 src/runtime/next/runtime_bridge_io.py           | 12 ++--
 src/specify_cli/bulk_edit/gate.py               |  6 +-
 src/specify_cli/git/ref_advance.py              | 96 +++++++++++++++++++++----
 src/specify_cli/missions/_read_path_resolver.py | 12 ++--
 5 files changed, 108 insertions(+), 30 deletions(-)
```

Every one of those files belongs to WP02/WP05's owned surfaces (`resolution`/`planner`/`bridge_io`/
`gate`/`ref_advance`/`_read_path_resolver`), and none of them is WP07's. **The WP07-attributable form
of the same invariant is per-commit, and it is empty for all three code commits:**

```
$ git diff --stat a199e4865^ a199e4865 -- src/     # (no output; 0 lines)
$ git diff --stat cea544596^ cea544596 -- src/     # (no output; 0 lines)
$ git diff --stat 06258eb46^ 06258eb46 -- src/     # (no output; 0 lines)
```

**WP07 moved no `src/` file.** This is recorded as a prompt/reality mismatch, not as a satisfied DoD
item — see "Anything wrong, ambiguous or unachievable" at the end.

## 3. Routed count, and why the branch-level number is not WP07's

Measured with the gate's own AST scanner on **commit-pinned, isolated worktrees** (the repository root
carries other agents' uncommitted edits and is therefore not a measurable surface):

| Tree | Meaning | `INPUT .py` | **ROUTED** | `INLINE` |
|---|---|---|---|---|
| `4147417c1` | parent of WP07 commit 1 — **PRE** | 1199 | **129** | 7 |
| `e06dfdc6f` | parent of WP07 commit 3 (WP05's routing commit) | 1199 | **130** | 7 |
| `06258eb46` | WP07 commit 3 — **POST** | 1199 | **130** | 7 |

Live root measurement at T041 time: **129** (quoted in full above).

**WP07's own routed delta is 0-net**, proved directly by the three empty `src/` diffs in §2 — a commit
that changes no `src/` byte cannot change an AST census over `src/`. The branch-level `129 → 130` is
**entirely** `e06dfdc6f` (`fix(WP05): route ref_advance site A onto load_meta_fail_closed`), which is
exactly the single net routed call the routing manifest allocates to WP05
(`contracts/routing-manifest.md` §6 ledger: `WP05` → **130**, **+1**; `WP07` → 130, **0-net**, "test +
tracker only").

Both 129 and 130 sit inside the derived band **`[127, 130]`** (two-sided; **126 is RED**, because
clause 2 of `test_routed_load_meta_floor` is strict — `len(routed) > ROUTED_LOAD_META_FLOOR` and
`126 > 126` is false). Constants read off the gate:
`ROUTED_LOAD_META_FLOOR = 126` (`tests/architectural/test_inline_meta_read_gate.py:221`),
`ROUTED_LOAD_META_FLOOR_MARGIN = 4` (`:220`).

**The WP prompt's "expect 129, unchanged at T045" and the routing manifest ledger's "WP07 → 130" are
both right, from different assumptions** — the ledger assumes WP05 has already landed, the prompt
assumes it has not. Both were true at different points during this lane. WP07's contribution is 0
either way.

## 4. Perishability statement — **this capture is lane-local**

Every green above is **lane-local and expires**. Two independent couplings make it so:

**(i) The marker's live path crosses WP04's degrade sites.** The marker imports
`_run_lane_based_merge` (`specify_cli.cli.commands.merge`); `src/specify_cli/merge/executor.py:116`
carries `from mission_runtime import MissionArtifactKind, placement_seam, resolve_placement_only`
(**verified by opening the line**); `resolve_placement_only`
(`src/mission_runtime/resolution.py:1333`) reaches `_assemble_core_fragments` (`:1213`) →
`_resolve_mission_id` (`:1058`, degrade at **`:1107`** — `meta = load_meta(primary_dir,
allow_missing=True, on_malformed="raise")` inside a `try` whose `except ValueError` degrades to the
`legacy-` sentinel; census row 3) and `_resolve_coordination_branch` (`:800`, degrade at **`:852`** —
the `except ValueError:` that returns `None`; census row 2). **Two of WP04's four degrade sites.**
(Path note: the module is `src/mission_runtime/resolution.py`, **not**
`src/specify_cli/mission_runtime/resolution.py` as some artifacts write it.)

**(ii) The marker shells out to a merge driver WP05 may edit.**
`src/specify_cli/lanes/merge.py:84` registers `command="spec-kitty merge-driver-meta %O %A %B"` for
`pattern="kitty-specs/**/meta.json"` (**verified by opening the lines**). That runs
`cli/commands/merge_driver.py` **as a subprocess**, so any edit to it is **invisible until
`pip install -e .`** — the documented stale-install false-red class. *(Correction, post-review: an
earlier parenthetical here blamed the ~90–160 s single-node cost on the marker's own fixture building
a venv. That is wrong. The venv is a **session-level** cache created by `tests/conftest.py`
(`_VENV_CACHE_PATH = Path(".pytest_cache/spec-kitty-test-venv")`, `conftest.py:141`); `--collect-only -q`
on the companion node alone already takes ~66 s, so the cost is session startup, not this fixture.
The §T044 account is the correct one.)*

**Therefore a green capture here is NOT evidence that the marker still passes after WP04 and WP05
land.** A capture taken before the reinstall is a stale-install false red or false green — both
worthless. **WP08 re-captures `SC-008` and `SC-010` on the integrated tree, after
`pip install -e .`.** WP07 does **not** claim `SC-008`/`SC-010` are settled for the mission, and does
not re-capture WP08's integration evidence here.

---

# T046 — COMMIT 4: the two tracker filings (`SC-009` rows 1 and 2)

**File, do not absorb (`C-009`).** Both filings are WP07's; neither is optional. Both assigned to the
**HiC** (`MOES-Media` / Jeroen Nouws) per the charter's Tracker Ticket Assignment Rule. `GITHUB_TOKEN`
was unset before every `gh` call.

## `SC-009` row 2 — the product defect: **#3231** (`FR-011`, `C-006`)

```bash
gh issue view 3231 --repo Priivacy-ai/spec-kitty --json number,title,body
```

```
number: 3231
title: Acceptance gate: one admitted scaffold row makes `overall_verdict` `pending` and blocks acceptance (pending-poisons-the-aggregate)
body[0:600]:
**Filed by mission `meta-fail-closed-3162-01KZ7FSQ`, WP07 (`SC-009` register row 2; `FR-011`, `C-006`, `C-009`). Filed, NOT fixed — see "Why this is filed and not fixed" below.**

## Symptom

After a mission→target squash merge, the row-aware `acceptance-matrix.json` reconciler admits **both** sides' criterion rows. When the mission branch still carries the `finalize-tasks` scaffold placeholder, the merged document therefore legitimately contains the scaffold row `AC-001` with `pass_fail: "pending"` — and that single admitted row makes the whole aggregate verdict `pending`, which blocks accept
...
body length: 4813
state: OPEN   assignees: [MOES-Media]
```

It cites **`src/specify_cli/acceptance/gates_core.py:525`** (`verdict = acc_matrix.overall_verdict`)
as the evidence line, with `:528-529` as the blocking arm, and
`src/specify_cli/acceptance/matrix.py:263` (`any(v == "pending")` dominates) as the aggregation
mechanism — **all three opened and confirmed to say what the citation claims**. It names the
**scaffold-row suppression rule** as the candidate fix and states that it is **rejected for this
mission**: the reconciler has zero scaffold awareness today, so the rule would amend the row-union
authority model shipped as `#3076`'s FR-008. It says explicitly that this filing is the reason the
marker's pin could be widened at all.

**`C-006` restated: the product defect is NOT fixed here.** No `src/` file was touched by WP07 (§T045.2).

## `SC-009` row 1 — the superseding issue for #2804: **#3232** (`FR-010`, `Q9`)

```bash
gh issue view 3232 --repo Priivacy-ai/spec-kitty --json number,title,body
```

```
number: 3232
title: Supersedes #2804: the re-pinned regression marker (row-union authority model) and the unit gate deleted in `b04da00e1`
body[0:600]:
**Supersedes #2804.** Filed by mission `meta-fail-closed-3162-01KZ7FSQ`, WP07 (`SC-009` register row 1; `FR-010`, `Q9`, `C-009`). #2804 is **superseded, not reopened**.

## What happened

#2804's regression marker — `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py::test_merge_resets_filled_gate_artifacts_to_placeholder` — was **honestly red on `main`** (that red is tracked as #3138). But it was an **inverted red**: the *assertions* were wrong, not the product. The marker carried **two** red assertions under one `# --- CONTRACT (RED on base) ---` banner (banner first line `:476`
...
body length: 6274
state: OPEN   assignees: [MOES-Media]
```

It records what is pinned **now** (assertion 1: admissible verdicts, matched to the in-file
issue-matrix sibling's already-widened form; assertion 2: evidence survival, take-theirs negatively
controlled), **why the shape changed** (the row-union authority model), and the `b04da00e1` deletion.

## The deleted unit gate, cited and **not** restored

```bash
$ git show --stat b04da00e1
commit b04da00e13da00bd4f5917db6f9597bae6507b02
    Write-side placement seam: deterministic matrix/tracer writers + row-aware merge driver (#3076)
 .../merge/test_gate_artifact_merge_drivers_2804.py | 249 --------
 130 files changed, 11878 insertions(+), 679 deletions(-)
```

`tests/merge/test_gate_artifact_merge_drivers_2804.py` was deleted (**−249 lines**) inside a 130-file
commit. It was the **unit gate that held this invariant** at driver level, and **no requirement
currently owns its absence**. Cited in #3232; **deliberately NOT restored** — it was written against
the pre-`#3076` whole-file heuristic and would have to be rewritten against the row-union model, which
is its own scope call. Confirmed absent today: `ls tests/merge/test_gate_artifact_merge_drivers_2804.py`
→ `No such file or directory`.

## Supersede, do not reopen (`Q9`)

#2804 is **OPEN** (P0) and was **not** reopened, **not** closed, and **not** edited. A comment was
posted pointing it at #3232 and #3231, and both new issues link back to #2804:

```
https://github.com/Priivacy-ai/spec-kitty/issues/2804#issuecomment-5199337103
```

## Charter obligations discharged

- **Tracker Ticket Assignment Rule** — both #3231 and #3232 assigned to the HiC (`MOES-Media`),
  verified above.
- **Standing Order 8** — #2804 (the addressed issue) has its issue-matrix row, claim and mission-naming
  tracker comment:
  ```
  spec-kitty agent issue-verdict --mission meta-fail-closed-3162-01KZ7FSQ --issue "#2804" \
    --verdict deferred-with-followup --actor "python-pedro/WP07" --wp WP07 --evidence-ref "..."
  OK #2804 -> deferred-with-followup (committed, surface=feat/meta-fail-closed-3162)
  ```
  (verdict `deferred-with-followup` because the **product** defect is filed forward as #3231, not fixed
  — `fixed` would be a false claim, and `verified-already-fixed` is worse.)
- **Pre-existing Failure Reporting Rule** — discharged for this red by T041's pristine-base
  reproduction on `98198e980`; the red is tracked as #3138.
- **Standing Order 3, mission tracer files** — the three tracer files **did not exist** for this
  mission (`kitty-specs/.../traces/` was absent) and were created by
  `spec-kitty agent tracer-append`, one finding each:
  `design-decisions` (`b40935115`, the inverted-red finding — *a marker can be honestly red and
  wrong*), `approach` (`63bf39f17`, the `SC-010` non-vacuity trap), `tooling-friction` (`a2e155a2f`,
  the shared-root concurrency that broke the `96494e5ec -- src/` invariant).

## `SC-009` register backfilled with the real numbers

`spec.md:418-419`:

```
  | 1 | Superseding issue for #2804: ... `b04da00e1` deleted ... (−249 lines) | `FR-010`, `Q9` | #3232 |
  | 2 | The pending-poisons-the-aggregate product defect, `acceptance/gates_core.py:525` as evidence, the scaffold-row suppression rule as candidate fix | `FR-011`, `C-006` | #3231 |
```

No `[to record]` remains in rows 1 and 2. **Rows 3–8 are deliberately untouched** — they belong to the
work packages that own their surfaces.

---

# Final verification at COMMIT 4

Re-run after the docstring backfill, by node id, redirected, `-ra`:

```
tests/regression/test_issue_2804_merge_resets_gate_artifacts.py ..       [100%]

======================== 2 passed in 152.72s (0:02:32) =========================
```

`grep -c '^ERROR tests/'` → **0**. Selected count **2**, both green.
`ruff check tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` → `All checks passed!`

(Subject to §T045.4: this green is **lane-local**.)

---

# Cone and hygiene

- Cone honoured: `tests/regression` (owned) + `tests/merge` read-only for context (only `ls`) + the
  row-aware sibling under `tests/specify_cli`. **No `tests/sync`, no `tests/cli`** appears in any
  quoted selection.
- Every run **redirected** (never piped), **by node id** where a node was named, **`-ra` never
  `-rf`**, `N passed` / `N failed` quoted with the selected count, `^ERROR tests/` counted (never bare
  `^ERROR `).
- `ruff check` run on the owned file after every edit → `All checks passed!`. **`ruff format` never
  run.**
- Only `tests/regression/test_issue_2804_merge_resets_gate_artifacts.py` changed by the three code
  commits — `git show --stat` per commit lists exactly that one file, and nothing else:
  `a199e4865` `1 file changed, 43 insertions(+), 7 deletions(-)`;
  `cea544596` `1 file changed, 156 insertions(+), 28 deletions(-)`;
  `06258eb46` `1 file changed, 132 insertions(+)`.
  No `src/`, no routing ledger, no sibling merge-driver test.
- Every `file:line` citation in this document was **opened and read** before being quoted. Corrections
  made as a result are listed below.

---

# Anything wrong, ambiguous or unachievable in the prompt

1. **`git diff --stat 96494e5ec -- src/` cannot print nothing** (DoD item, T045 step 2). Sibling work
   packages WP02 and WP05 committed `src/` routing changes to the shared branch **concurrently with
   this lane**, in the shared repository root (`.worktrees/` absent). Five `src/` files differ from
   `96494e5ec`, none of them WP07's. The runnable, WP07-attributable substitute is recorded in
   §T045.2: `git diff --stat <c>^ <c> -- src/` empty for all three WP07 commits. **Reported, not
   worked around.**
2. **`plan.md`'s "`git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'` → 0 files" is likewise no
   longer 0** — same cause. Measured 6 files at lane start, more since.
3. **Routed PRE/POST are not both 129.** The prompt says 129 pre and post; the routing manifest ledger
   says WP07 sits at 130 (post-WP05). Both are self-consistent under different assumptions about
   whether WP05 has landed. Measured: **129 at `4147417c1`, 130 at `06258eb46`**, with the +1 fully
   attributed to WP05's `e06dfdc6f`. **WP07's own delta is 0**, proved by three empty `src/` diffs.
   Both values are in band `[127, 130]`.
4. **`FILLED_ACCEPTANCE_MATRIX`'s `FR-001` evidence is at `:117-124`, not `:114-121`** as the WP
   prompt states. Opened and corrected; the handle `d5b8324f9` is on `:118`.
   *(Correction, post-review: this record originally attributed `:114-121` to `plan.md` as well.
   `plan.md` contains no reference to `FILLED_ACCEPTANCE_MATRIX`, `d5b8324f9` or `114-121` — zero
   grep hits. The prompt-only claim is correct and sufficient; the `plan.md` half was asserted
   without being checked, in a document that claims every citation was opened.)*
5. **The in-file issue-matrix sibling's comment block starts at `:497`, not `:496`** — `:496` is
   `merged_row = post_issue_matrix["rows"]["#2373"]`. The two `assert`s are at `:507` and `:512`; the
   WP's correction of `:512` (against an earlier draft's `:513`) is right.
6. **`gates_core.py:528` is the `elif verdict == "pending":` line; the `activity_issues.append(...)`
   that actually blocks is `:529`.** The WP says ":528 turns it into a blocking activity issue" —
   substantively correct, cited as `:528-529` in #3231.
7. **`resolution.py` lives at `src/mission_runtime/resolution.py`.** The line numbers `:1107` and
   `:852` are correct. *(Correction, post-review: this was filed as a **prompt defect**, which it is
   not — the WP prompt writes the path correctly at `:194` and `:405`. The
   `src/specify_cli/mission_runtime/` form appears only in older unrelated notes and other missions'
   artifacts, never in this prompt. Not a defect in this WP's inputs.)*
8. **The three mission tracer files did not exist**, so "append to the three mission tracer files" was
   a create-then-append. Done via the canonical `spec-kitty agent tracer-append`, not by hand.
9. **`spec-kitty implement WP07` was not the entry point.** The task directed `move-task WP07 --to
   doing` in the existing repository root, and `.worktrees/` is absent; the WP prompt's start command
   would have created a lane workspace. Followed the task's instruction; recorded here because the WP
   prompt says otherwise.
10. **A `pre-merge` adversarial-gate nudge fired** during T046 (a `PostToolUse` hook on the tracer
    commit). Not actioned: WP07 ends at `for_review`, and the pre-merge point-cut belongs to the
    operator/WP08, not to this lane.

**`[UNVERIFIED]` values: none.** Every number, SHA, line number and command output in this document
was measured or opened in this session. The only quantity this document declines to assert is the
one it explicitly disclaims: that these greens still hold after WP04 and WP05 land — that is WP08's
re-capture, and it is stated as such rather than assumed.
