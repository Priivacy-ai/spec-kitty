---
affected_files:
- path: tests/conftest.py
- path: tests/architectural/_home_pin_exempt.py
- path: tests/architectural/test_home_owner_behaviour.py
- path: tests/architectural/test_home_owner_never_wins.py
cycle_number: 1
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-11T22:23:11+02:00'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP03
---

# WP03 (WP-a) — review cycle 1

**Verdict: APPROVED.**

Every load-bearing claim below was **constructed**, not read: each mutation was applied to the lane
worktree, run against the pinned interpreter, and reverted with `git checkout -- <path>`;
`git status --porcelain` was confirmed empty after each and at the end of the review.

## Adjudications requested

### 1. M3 — SC-012 limb 2 cannot fail. Reproduced. The pair is now falsifiable.

**M3 reproduced.** Probe (a)'s `monkeypatch.setenv` deleted from `retained_pin_home`:
`test_the_retained_pin_probe_observes_its_own_value` **passed**. The implementer's finding stands
by construction, not by argument.

**But the module is not blind to M3.** The same mutation reds four other tests:

```
FAILED test_both_probes_request_the_owner_before_pinning
FAILED test_only_probe_a_is_a_class_member_so_probe_b_costs_no_slot
FAILED test_the_exempt_set_is_a_subset_of_the_discovered_class
FAILED test_the_owner_and_the_probe_are_the_only_members_of_their_two_files
```

The `E`-accounting limbs catch the deletion the SC-012 limb cannot. That was not claimed in
`record.md` and is worth recording: probe (a)'s pin is load-bearing, just not for the assertion
that names it.

**The pair is falsifiable — constructed.** I built a genuine owner-wins owner (a process-global
patch that survives a later `monkeypatch.setenv`, the analogue of the `setattr(Path, "home", …)`
shape `tests/conftest.py:272-286` records) and ran both probes:

```
test_the_retained_pin_probe_observes_its_own_value                  PASSED
test_the_negative_control_probe_observes_its_own_differing_value    FAILED
  assert '.../probe-home' == '.../home'
```

Probe (b) reds, probe (a) does not. The pair discriminates exactly as designed, and probe (b)
carries the whole discrimination — as the module docstring says.

**Does probe (a) still earn one of `E`'s two irrevocable slots?** Yes, but **not on falsifiability
grounds**, and the honest accounting is:

* It cannot bite (M3). Its *existence* is load-bearing only for the four `E`-accounting assertions
  above, which exist *because* it holds a slot — the justification is partly self-referential.
* The implementer had **no discretion**. `FR-011` mandates *"exactly one real-tree probe is a
  member ... declared in `E` beside the owner"*, and `FR-004` types `E` as `tuple[Exempt, Exempt]`
  at exactly two entries. Dropping probe (a) would require re-adjudicating FR-011 and changing the
  declared arity — neither is WP03's to do.
* `spec.md:546` already states the residual in its own words: *"an assertion that need not bite is
  not worth that price"*, and §0.5 records it as this Mission's most irreversible decision.
  `record.md` FINDING 1 raises it for WP06/T030 rather than silently repairing it.

Correctly raised, correctly not repaired here. The slot is spent per spec; the cost is recorded
where it can be adjudicated.

### 2. The fixture name — the FR-010 binding bites. Constructed on both limbs.

Renamed the fixture in `tests/conftest.py` **and** the `| **Fixture name** |` row in
`contracts/canonical-home-owner.md` to `spec_home_owner` (a name absent from
`OWNER_PARAM_NAMES`), consistently, so the contract-parse limb stays green and only the FR-010
limb can speak:

```
PASSED  test_the_conftest_fixture_carries_the_name_the_contract_declares
FAILED  test_the_declared_owner_name_is_a_member_of_owner_param_names
        AssertionError: the contract declares the owner 'spec_home_owner', which is NOT in
        OWNER_PARAM_NAMES=['canonical_home', 'runtime_home', 'tmp_path']
FAILED  test_the_owner_alias_limb_actually_fires_on_the_owner_name
        assert frozenset({'m..._home_owner'}) >= frozenset({'m..., 'tmp_path'})
```

Both limbs bite, and they are **two different claims**, as required: membership in the frozenset
(`test_the_declared_owner_name_is_a_member_of_owner_param_names`) and the resolver honouring it
(`test_the_owner_alias_limb_actually_fires_on_the_owner_name`, which calls `normalise_params` and
checks the silhouette). The second carries its own discriminating control —
`normalise_params({"unrelated_home", "monkeypatch"})` must **not** satisfy the silhouette — so it
cannot pass for a `normalise_params` that maps everything. Verified non-vacuous by inspection of
both branches; an identity `normalise_params` fails the first assertion and passes the second.

The operand (`_home_pin_scan.OWNER_PARAM_NAMES`) is lane-a's write scope and outside this author's
control. FR-010's circularity is closed. `canonical_home` was indeed forced, not chosen.

### 3. `MERGE_BASE_DEFINITION_NAMES` — the self-reported defect. **Acceptable as shipped.**

**The claim is true today, verified independently.** I derived the list from git rather than
reading it:

```
merge-base: 9117219081c1f88cf0b90937b9cb46723ceebcd2   (matches the docstring)
git show <merge-base>:tests/conftest.py -> AST definition names
merge-base count: 68   declared count: 68   EQUAL: True
```

**The defect is real and correctly self-reported.** The operand now derives from the author, not
from git; a future implementer facing a red can regenerate it — from the recipe printed in the
constant's own docstring — and green the ratchet with a reorder intact. The neighbour-anchor test
(`test_the_owner_sits_between_its_named_ordering_anchors`) covers only `names[i-1]` / `names[i+1]`,
so it sees nothing below the anchor. And the shape is the one `FR-004(b)` names as circular in this
very spec — *"asserting `E` is 'exactly as declared' while both the declaration and the assertion
live in the guard module"* — here with the declaration and the assertion both in
`test_home_owner_behaviour.py`.

**Judgement: acceptable, and deriving from git at test time would be worse.** Three reasons:

1. **NFR-005 constrains this WP's own diff, not all future time.** *"The owner must not alter,
   shadow, or reorder relative to `_isolated_worker_home`"* is a property of the change under
   review. At the moment SC-010 exists to fire — this landing — the operand is provably the merge
   base, verified above. Its perpetual-ratchet value is a bonus, not the requirement.
2. **A git-derived operand is not durable, and its failure modes are both worse.**
   `git merge-base HEAD feat/isolated-home-pin-guard` requires that ref to exist. After the mission
   lands and the branch is deleted the derivation is unresolvable, leaving exactly two options: a
   permanent false red (DIR-041 friction) or a skip-when-unavailable (a green that cannot see —
   the defect-masking shape DIR-041 forbids outright). T010's DoD anticipated precisely this
   (*"the ancestry does not survive the squash or rebase a lane consolidation may perform"*), which
   is why T010's durable artefact is a **recording**, not the ancestry.
3. **A frozen baseline is this repository's idiom** (`_golden_count_baseline.json`,
   `test_allowlist_shrink_only`, `charter_path_literal_baseline`; doctrine tactic
   `frozen-baseline-shrink-only-ratchet`), and the constant carries its provenance — the merge-base
   SHA, the byte-identity check, and *"regenerate only alongside a reviewed, intentional conftest
   change"* — in the docstring.

Recorded as [MINOR] below with a non-blocking hardening suggestion.

## Findings

**[MINOR]** `tests/architectural/test_home_owner_never_wins.py:63-64` — the comment reads *"The
owner's name, taken from the same contract T012 parses — **never re-typed as a literal here**"* and
the line it annotates is `OWNER_NAME = "canonical_home"`, which is exactly a re-typed literal. In
the one module whose whole subject is anti-circularity, this is a false statement about its own
binding. **Not a coverage hole** — constructed: renaming the owner errors this module at fixture
resolution (`retained_pin_home` / `probe_home_pin` request `canonical_home` by parameter name), so
a drift reds loudly. *Recommendation:* import `OWNER_NAME` from `test_home_owner_behaviour` (or
re-parse the contract), or correct the comment to say what is true — that the binding is carried by
T012 and that a rename reds here at collection.

**[MINOR]** `tests/architectural/test_home_owner_behaviour.py:98` —
`MERGE_BASE_DEFINITION_NAMES` is author-derived and its regeneration recipe sits inline (`:89-97`).
Adjudicated acceptable above. *Non-blocking hardening, if the operator wants defence in depth:*
move the operand to a sidecar data file beside `_golden_count_baseline.json`, matching FR-004(b)'s
*"held outside the declaring module"* idiom, so a regeneration lands in a reviewer-watched data
diff rather than in the same file as the assertion. Not required by SC-010, and not a condition of
this approval.

**[NIT]** `record.md` FINDING 1 reports M3 as *"1 passed"*. True for the named test, but the same
mutation reds four `E`-accounting tests in the same module. Worth adding — it is the strongest
available statement that probe (a) is not inert.

No MAJOR or BLOCKER findings.

## The rest — what was checked

**FR-005 conformance.** Exactly one new fixture. `git diff -U0 tests/conftest.py` shows a single
hunk `@@ -300,0 +301,40 @@` — a pure insertion, zero lines removed, **no hunk at or below 298**.
Non-autouse (no `autouse=` kwarg), function-scoped **by absence** of `scope=`, body contains no
`return <value>` and no `yield` (AST-asserted, and the runtime test asserts
`canonical_home is None`). `return None` was **not** "improved" — the probe computes
`str(tmp_path / "home")` from its own `tmp_path` and never reads the fixture's value.

**FR-006 — constructed, four mutations run by me.**

| Mutation | Result |
|---|---|
| `monkeypatch.setattr(Path, "home", …)` added to the owner | `test_owner_establishes_by_setenv_only_and_creates_the_directory` **RED** (`assert 'setattr' not in {'mkdir','setattr','setenv'}`) |
| `mkdir` removed | **both** halves red — SC-012 limb 1 on `is_dir()`, and the static half on `assert 'mkdir' in called` |
| owner made `autouse=True` | `test_a_test_not_naming_the_owner_never_sees_the_owners_effect` **RED**; its positive-control sibling `test_owner_pins_the_env_and_creates_the_directory_before_the_body_runs` **stays green**. That is the pair, and it is why limb (ii) is not written as "grep for autouse" |
| owner wins over a later `setenv` | probe (b) **RED**, probe (a) green (see §1) |

Establishment is `monkeypatch.setenv` only; `find_write_sites` over the owner's line range returns
`{"setenv"}` exactly.

**SC-011 non-evidence.** The module says so in three places and does not leave it to prose alone:
the module docstring (`:6-13`), the limb-(i) test's own docstring (*"An owner whose body is
`return None` passes this. It is here because SC-011 binds it normatively, not because it is
evidence."*), and contract §6. A reviewer seeing SC-011 green cannot read it as evidence the owner
works. `test_owner_pins_the_env_and_creates_the_directory_before_the_body_runs` is confirmed as the
only limb that reds on an inert owner (the `mkdir` mutation above).

**`pytest.raises(pytest.fail.Exception)`.** Used at `:546`, and the MRO fact is asserted
mechanically at `:534-535` (`issubclass(pytest.fail.Exception, BaseException)` and
`not issubclass(..., Exception)`) rather than left in a comment. Green on pytest 9.0.3.

**T014 / `E`.** Fixed arity **by type** — constructed: appending a third `Exempt` yields
`error: Incompatible types in assignment (expression has type "tuple[Exempt, Exempt, Exempt]",
variable has type "tuple[Exempt, Exempt]") [assignment]` under `mypy --strict`. `Exempt` and
`MemberKey` are imported from `_home_pin_scan` (`:46`); **no local stand-in anywhere** in the WP's
files. Keys are content-addressed 3-tuples; `_home_pin_exempt.py` contains **no int literal at
all**, and the only `lineno` reaching `composite_key_from_file`'s second positional argument comes
from `member.lineno` off `discover()` at runtime. `test_ratchet_positional_anchor_ban.py` +
`test_golden_count_ban.py`: **46 passed**.

**Golden-count 25/25, zero headroom.** No `len(x) [=!<>]= N` in any of the four files (grepped).
`_golden_count_baseline.json` is **not** in the WP03 diff — last touched by `de47df6b7`, an earlier
landing commit. Every new assertion is a set or ordered-sequence comparison, including
`test_the_owner_and_the_probe_are_the_only_members_of_their_two_files`, which is a set equality
where a count would have been cheaper.

**NFR-006.** `record.md` §"NFR-006" records the resolved `pytest.__version__ = 9.0.3`,
`sys.version = 3.11.15`, `sys.executable`, the verbatim invocation
(`… -m pytest <paths> -p no:cacheprovider -q -n0`), the explicit "no `uv run`, no `uv sync`, no
venv created inside this tree", and the measured `Failed` MRO. All confirmed against my own runs.

**Gates (DIR-030).**

```
test_home_owner_behaviour.py + test_home_owner_never_wins.py     23 passed
test_golden_count_ban.py + test_ratchet_positional_anchor_ban.py 46 passed
test_home_pin_seam_no_second_copy.py                              6 passed
test_gate_coverage.py::test_no_new_orphan_surfaces                1 passed
ruff check (4 files)                                             All checks passed
mypy --strict (4 files)                                          7 errors, ZERO in the new modules
```

The 7 mypy errors are pre-existing: 4 in `tests/utils.py` / `tests/test_isolation_helpers.py` /
`tests/status/conftest.py` (pulled in as imports, untouched), and 3 in `tests/conftest.py` at
`:517/:534/:555` — the untyped `clean_spec_kitty_queue`, `_neutralize_worktree_detection` and
`_always_main_repo`, shifted +40 by this insertion. Verified against the merge base at `:477/:494/
:515`. No `# noqa`, no `# type: ignore`, no per-file ignore added. `ruff format` was not run.

**DIR-024 locality.** The WP03 commits touch exactly six paths, all inside `owned_files` +
the WP's two assigned mission-directory artefacts. No file under `src/`; no existing test module;
`tests/_arch_shard_map.py` untouched; `_home_pin_scan.py` and `_home_pin_gate.py` untouched.

**DIR-032 conceptual alignment.** Zero occurrences of `feature` / `--feature` in the added lines
or the new files. Terminology matches the contract and `data-model.md`'s `Exempt` / `MemberKey`
vocabulary throughout.

**DIR-041.** No `xfail`, no skip, no retry, no weakened assertion anywhere in the diff. Every
population-0 or absence assertion I checked ships a control that proves the instrument can see:
limb (ii) has its requesting sibling; the key recomputation has both `assert recomputed` and the
forged-qualname control; the resolver limb has its non-member control; probe (a) has probe (b).

## Not checked / out of scope

* WP01's two real-tree distribution reds (`test_kind_distribution_over_the_real_tree_mechanises_c004`,
  `test_home_partition_over_the_real_tree_…`) — operator-accepted as WP01's to repair, not WP03's.
* The `move-task --force` framework conflict on `kitty-specs/` from a lane branch — operator-accepted.
* DIR-013 vs C-013 on pre-existing reds — C-013 governs; no issue filed.
* The three baseline reds (`test_wp_prompt_build_latency` ×2, `test_ci_quality_path_filters`) —
  contention under `-n auto`, not re-measured.
* WP05's real `E` hash and the `discovered == census ∪ E` accounting — WP05's scope.
* The full `tests/` suite was not run; scoping was narrow by instruction.

## Verdict

**APPROVED.** Two MINOR findings, neither blocking, both documentation/hardening rather than
correctness. Every limb this WP was sent to build was constructed to bite, and the two that cannot
bite (SC-012 limb 2, SC-011) are named as such in the code, in the contract and in `record.md`
rather than presented as evidence.
