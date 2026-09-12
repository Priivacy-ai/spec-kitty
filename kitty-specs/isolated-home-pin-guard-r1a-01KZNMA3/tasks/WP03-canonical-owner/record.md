# WP03 (WP-a) — record

The canonical owner, its behavioural probes, and the exemption set they define.
Subtasks T010–T014. Lane `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-c`.

---

## PRECONDITION (checked, not assumed)

The WP prompt requires `tests/architectural/test_home_pin_gate_verdict.py` to be present and
**GREEN** in this lane's worktree, because the lane allocator degrades to a printed warning when
the dependency branch is unresolvable (`worktree_allocator.py:462-472`).

```
/home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest \
  tests/architectural/test_home_pin_gate_verdict.py -p no:cacheprovider -q -n0
-> 17 passed in 76.98s
```

WP02's halt gate is present and green. Proceeding was permitted.

---

## NFR-006 — the pinned runtime

**Resolved version, read from the interpreter that ran every measurement below:**

```
pytest.__version__ = 9.0.3
sys.version        = 3.11.15
sys.executable     = /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python
```

**Verbatim invocation** (the form every run in this record used; only the selection and the
`-n` flag vary):

```
/home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest <paths> -p no:cacheprovider -q -n0
```

No `uv run`, no `uv sync`, no venv created inside this tree. `mypy` and `ruff` were invoked through
the same interpreter as `-m mypy` / `-m ruff`.

**This WP is where the pytest-version sensitivity actually lives**, and it was measured rather than
assumed. On pytest 9.0.3 the `ScopeMismatch` raised by `request.getfixturevalue` for a
function-scoped fixture requested from a module-scoped request is converted to `Failed`, whose MRO
is:

```
(<class 'Failed'>, <class '_pytest.outcomes.OutcomeException'>, <class 'BaseException'>, <class 'object'>)
```

`Exception` is **not** in that MRO, so `pytest.raises(Exception)` does not catch it and it escapes
as a setup ERROR. `test_home_owner_behaviour.py` asserts the subclass relation mechanically
(`test_the_scope_mismatch_route_is_not_reachable_through_the_exception_hierarchy`) so a future
pytest that changes it reds here instead of quietly catching nothing.

---

## T010 — the ordering fact, recorded AT AUTHORING TIME

`contracts/canonical-home-owner.md` was committed **before** the owner, and the ancestry is
recorded here because it does not survive the squash or rebase a lane consolidation may perform.

| | SHA |
|---|---|
| contract commit | `8d55a97687afb877c55a62995aaac4e414e03899` |
| owner commit | `d8088b08d49857f3b91f21e8c91e2d44de575d93` |

```
$ git merge-base --is-ancestor 8d55a97687afb877c55a62995aaac4e414e03899 d8088b08d49857f3b91f21e8c91e2d44de575d93
$ echo $?
0
```

Exit status **0** — the contract commit is an ancestor of the owner commit. **This recording is the
durable artefact**, not the ancestry itself.

---

## The fixture name, and why it was not a choice

**`canonical_home`.**

`tests/architectural/_home_pin_scan.py`'s `OWNER_PARAM_NAMES` ships
`frozenset({"tmp_path", "canonical_home", "runtime_home"})`, and its own docstring records
`canonical_home` as **provisional and unbound** — the name came from FR-010's prose at a moment
when no contract named the owner — naming WP03/T012 as the closing obligation. `_home_pin_scan.py`
is lane-a's write scope and this WP may not edit it, so any other name would have left FR-010's
resolver limb **permanently inert with every WP01 assertion still green**.

**T012's binding is in place:**
`test_home_owner_behaviour.py::test_the_declared_owner_name_is_a_member_of_owner_param_names`
parses the declared name out of `contracts/canonical-home-owner.md` and asserts
`OWNER_NAME in scan.OWNER_PARAM_NAMES`. A sibling test
(`test_the_owner_alias_limb_actually_fires_on_the_owner_name`) constructs the *effect* — membership
in the frozenset is not the same claim as `normalise_params` honouring it — and carries its own
negative control.

---

## Red-first evidence (DIR-034)

### T012 — before the fixture existed

```
$ ... -m pytest tests/architectural/test_home_owner_behaviour.py -p no:cacheprovider -q -n0
8 failed, 4 passed, 2 errors in 50.79s
```

Failure text, verbatim:

```
AssertionError: expected exactly one definition named 'canonical_home' in conftest.py, found []
AssertionError: assert [] == ['canonical_home']
ValueError: tuple.index(x): x not in tuple
```

The 2 errors were the two fixture-requesting tests (SC-012 limb 1 and the `ScopeMismatch` probe)
erroring at setup because the fixture did not exist. The 4 that passed pre-fixture are the two
`OWNER_PARAM_NAMES` limbs, the `pytest.fail.Exception` MRO limb, and — vacuously, its positive
control being one of the two errors — the C-014 limb (ii) non-instantiation test.

### T013/T014 — before `_home_pin_exempt.py` existed

```
$ ... -m pytest tests/architectural/test_home_owner_never_wins.py -p no:cacheprovider -q -n0
ImportError: cannot import name '_home_pin_exempt' from 'tests.architectural'
1 error in 52.27s
```

### After

```
$ ... -m pytest tests/architectural/test_home_owner_never_wins.py \
      tests/architectural/test_home_owner_behaviour.py -p no:cacheprovider -q -n0
23 passed in 65.57s
```

### NFR-003 — identical results in both parallel modes

This WP touches the root `conftest.py`, so the per-worker HOME isolation path is exercised in both.

```
$ ... -m pytest tests/architectural/test_home_owner_behaviour.py \
      tests/architectural/test_home_owner_never_wins.py -p no:cacheprovider -q -n auto --dist loadfile
23 passed in 217.33s

$ ... -m pytest <same selection> -p no:cacheprovider -q -n0
23 passed in 94.45s
```

Identical verdicts, 23/23 both ways. (`--dist loadfile`, never bare `--dist load`.)

---

## Falsification checks — every load-bearing limb was made to bite

Green is not evidence a test can fail. Each mutation below was applied to a working tree copy, run,
and reverted; `git status` confirmed restoration after each.

| # | Mutation | Expected | Observed |
|---|---|---|---|
| **M1** | owner made `autouse=True` | C-014 limb (ii) reds, SC-012 limb 1 stays green | **1 failed, 1 passed** — `test_a_test_not_naming_the_owner_never_sees_the_owners_effect` red; limb 1 green |
| **M2** | probe (b) loses its own `setenv` | the negative control reds, observing the OWNER's value | **1 failed** — `assert '.../probe-home' == '.../home'` |
| **M3** | probe (a) loses its own `setenv` | SC-012 limb 2 **as specified** stays GREEN | **1 passed** — see the finding below |
| **M4a** | owner's `mkdir` removed | SC-012 limb 1's `is_dir()` reds | **1 failed** — `assert False where False = is_dir()` |

**M1 verbatim:**

```
AssertionError: assert '/tmp/pytest-of-jeroennouws/pytest-36/test_a_test_not_naming_the_own0/home'
             != '/tmp/pytest-of-jeroennouws/pytest-36/test_a_test_not_naming_the_own0/home'
```

**M4a verbatim:**

```
tests/architectural/test_home_owner_behaviour.py:517: in test_owner_pins_the_env_and_creates_the_directory_before_the_body_runs
    assert Path(os.environ[scan.NEEDLE]).is_dir()
E   AssertionError: assert False
```

M4a is the one that matters most: **SC-011 green is not evidence the owner works.** Every AST limb
in `test_home_owner_behaviour.py` and both C-014 limbs pass against an owner whose body is
`return None`. M4a shows SC-012 limb 1 is the only limb that reds on an inert owner.

---

## FINDING 1 (raised, not repaired) — SC-012 limb 2 as specified cannot fail, CONSTRUCTED

**M3 is the proof, not an argument.** Probe (a)'s own `monkeypatch.setenv` was deleted — so the
value observed in the body could only have come from the owner — and
`test_the_retained_pin_probe_observes_its_own_value` **passed**:

```
$ ... -m pytest tests/architectural/test_home_owner_never_wins.py -q -n0 -k "retained_pin_probe_observes"
1 passed, 8 deselected in 104.17s
```

FR-005 forces the owner to pin `str(tmp_path / "home")`; any class member pins
`str(tmp_path / "home")`; `tmp_path` is function-scoped and shared within a test. The two strings
are identical, so *"fails if the owner's value is seen"* has nothing to distinguish.

**Shipped repair**: the second, **non-member** probe pinning `str(tmp_path / "probe-home")`
(probe (b), T013b), which M2 shows is the only assertion of the pair that can be falsified. The
vacuity is recorded here as a **spec finding** for WP06/T030 rather than silently patched.

Probe (a) still ships, because FR-011 mandates the member probe and it is what pays for one of
`E`'s two slots.

---

## FINDING 2 (raised, not repaired) — WP03's mandated owner falsifies two WP01 real-tree assertions

**This is the significant one, and it is a cross-WP consequence, not a defect in this WP.**

The spec states plainly (§"Canonical owner"): the owner is *"itself a class member under FR-001,
which is why `discovered == census ∪ E` is the only correct form"*. FR-011 adds exactly one further
member, the retained-pin probe. So WP03 necessarily takes `discover(Path("tests"))` from **40 to
42** members.

Measured after this WP:

```
total members: 42
kind_distribution(keyed) = {'fixture': 32, 'test-body': 10, 'helper': 0}
home_partition           = {'A': 29, 'B1': 11, 'B2': 2, 'other': 0}
```

The two new members are exactly the two `E` entries, both `kind=fixture`, both `home_partition=A`:

```
('conftest.py', 'canonical_home', 'monkeypatch . setenv ( , str ( home ) )')                              lineno 338
('architectural/test_home_owner_never_wins.py', 'retained_pin_home', 'monkeypatch . setenv ( , str ( home ) )')  lineno 88
```

Probe (b) is correctly **not** classified (it resolves to `<tmp_path>/probe-home`), so it costs no
slot — asserted by `test_only_probe_a_is_a_class_member_so_probe_b_costs_no_slot`.

WP01's `tests/architectural/test_home_pin_scan_limbs.py` froze both distributions at the
**pre-WP03** population:

```
FAILED test_home_pin_scan_limbs.py::test_kind_distribution_over_the_real_tree_mechanises_c004
  assert {'fixture': 32} != {'fixture': 30}
FAILED test_home_pin_scan_limbs.py::test_home_partition_over_the_real_tree_matches_the_published_distribution
  assert {'A': 29} != {'A': 27}
(2 failed, 113 passed in 724.24s — the rest of that file, test_gate_coverage.py and
 test_real_home_isolation_guard.py are green)
```

**Not repaired here, deliberately.** `test_home_pin_scan_limbs.py` is WP01's `owned_files` and is
outside this WP's owned set; C-001 forbids editing an existing test module; and the docstrings
carry WP01's published measurements, so a silent number bump would erase a recorded finding. The
repair belongs to WP01's owner or to WP05 (which regenerates the census and already owns the
`discovered == census ∪ E` accounting where the 40/42 split is expressed).

Note the shape: this is the Mission's own signature defect — *the guard's own artefact landing
inside the guard's own population* (FR-009's wording) — operating this time on WP01's real-tree
distribution assertions. It was foreseeable from FR-005 and was not foreseen.

---

## FINDING 3 (noted) — DIR-013 vs C-013 on pre-existing reds

The project charter's DIR-013 requires opening a GitHub issue for pre-existing failures before
proceeding. C-013 and this WP's instructions forbid `gh issue create` in this Mission. C-013 is
Mission-normative and more specific, so it governs: the baseline reds are **reported to the
operator here** as a TG-item and no issue was created. Flagged because the two rules genuinely
conflict.

---

## Baseline-red classification (C-013 — reported, no issue opened)

Lane baseline supplied with the WP, at `-n auto --dist loadfile`: **3 failed**.

| Test | Classification |
|---|---|
| `test_wp_prompt_build_latency` (×2) | **Contention, not semantics.** ~6.3–6.7 s against a 6.0 s budget; the merge-base measures 6.08 s, i.e. already within noise of the budget before this lane existed. Not touched by this WP — no file in WP03's owned set is on that path. |
| `test_ci_quality_path_filters` | **Contention, not semantics.** Subprocess collection timeout under 8 workers; passes 17/17 serially. Not touched by this WP. |

Neither is attributable to WP03: this WP adds one fixture to `tests/conftest.py`, three new files
under `tests/architectural/`, and one mission-directory document. The two WP01 reds in FINDING 2
**are** attributable to this WP's mandated change and are reported as such rather than folded into
the baseline.

---

## Static gates (NFR-004)

```
$ ... -m ruff check tests/conftest.py tests/architectural/_home_pin_exempt.py \
      tests/architectural/test_home_owner_behaviour.py tests/architectural/test_home_owner_never_wins.py
All checks passed!
```

`ruff format` was **not** run.

```
$ ... -m mypy --strict tests/architectural/_home_pin_exempt.py \
      tests/architectural/test_home_owner_behaviour.py \
      tests/architectural/test_home_owner_never_wins.py tests/conftest.py
Found 7 errors in 4 files (checked 4 source files)
```

**Zero of the seven are in this WP's three new modules, and zero are new.** Four are in
`tests/utils.py`, `tests/test_isolation_helpers.py` and `tests/status/conftest.py` — files this WP
does not touch, pulled in as imports. Three are in `tests/conftest.py` at lines 517 / 534 / 555,
which are the pre-existing untyped `clean_spec_kitty_queue`, `_neutralize_worktree_detection` and
`_always_main_repo`, shifted +40 lines by this WP's insertion. Verified against the merge base:

```
$ git show 9117219081c1f88cf0b90937b9cb46723ceebcd2:tests/conftest.py | sed -n '477p;494p;515p'
def clean_spec_kitty_queue():
def _neutralize_worktree_detection(request, monkeypatch: pytest.MonkeyPatch) -> None:
    def _always_main_repo(cwd=None):
```

Identical. No `# noqa`, no `# type: ignore`, no per-file ignore was added.

---

## Repo gates

```
$ ... -m pytest tests/architectural/test_ratchet_positional_anchor_ban.py \
      tests/architectural/test_golden_count_ban.py \
      tests/architectural/test_home_pin_seam_no_second_copy.py -p no:cacheprovider -q -n0
52 passed in 70.50s
```

* **Golden-count ratchet (zero headroom, 25/25).** Every assertion added by this WP is a **set** or
  ordered-sequence comparison. There is no `len(x) == N` anywhere in the three new modules and the
  baseline was **not** re-frozen.
* **`test_no_int_line_sink_in_architectural_python_seeds` (#2564 clause).** `_home_pin_exempt.py`
  contains **no int literal at all**: `MemberKey` is a content-addressed 3-tuple of strings, and
  the only `lineno` in the recomputation comes from `discover()` at runtime
  (`composite_key_from_file(path, member.lineno)`).
* **WP02's seam guard.** Both new test modules import `_home_pin_scan`, hold zero `ast.parse` calls
  and zero `NodeVisitor` subclasses, and route every parse through `_home_pin_scan.parse_module` —
  including the parse of `tests/conftest.py` and each module's parse of its own source. Complied
  with as written; the guard's known evadability via aliased imports was not relied on.
* **`test_gate_coverage.py::test_no_new_orphan_surfaces`** green: both new modules are top-level in
  `tests/architectural/` and carry `pytestmark = pytest.mark.architectural`.
  **`tests/_arch_shard_map.py` was not edited.**
* **`time.time()`** appears nowhere in this WP's files.

---

## C-001 / C-006 blast radius

```
$ git diff -U0 tests/conftest.py | grep '^@@'
@@ -300,0 +301,40 @@ def _isolated_worker_home(
```

A single hunk, `-300,0` — a **pure insertion with zero lines removed**. No hunk touches a line at
or below **298**. `tests/conftest.py` is the only existing file edited; no existing test module was
touched; nothing under `src/` changed.

---

## `E` — the two entries, and what they cost

```python
E: tuple[Exempt, Exempt] = (...)   # fixed arity BY TYPE — a third entry is a mypy --strict error
```

| Entry | Definition | Why |
|---|---|---|
| `("conftest.py", "canonical_home", "monkeypatch . setenv ( , str ( home ) )")` | the canonical owner (FR-005) | itself a class member; excluding it by predicate would need a narrowed silhouette, which C-004 forbids |
| `("architectural/test_home_owner_never_wins.py", "retained_pin_home", "monkeypatch . setenv ( , str ( home ) )")` | the retained-pin probe (FR-011) | keeping its own pin is what demonstrates the owner never wins, and is what makes it a member |

Both keys carry **no string literal** in their token-line component — `code_tokens_by_line` strips
them — so declaring `E` does not create the first assignment-bound `"SPEC_KITTY_HOME"` constant and
does not falsify SC-002b.

**Probe (a) spends one of `E`'s two irrevocable, hash-pinned slots. The second is not spent.**
That cost is this Mission's most irreversible decision and it is recorded here.
