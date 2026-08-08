# WP05 notes — the mechanism-keyed gate, its seam arm, and the frozen baseline

Declared out-of-map planning write for WP05 (`wps.yaml` WP05 block). Reproducing commands are
stated rather than frozen figures: any count in this file that is *about a file in this tree* is
accompanied by the command that re-derives it, because a self-measuring block is true only at the
instant it is written.

## Environment verification (run before any other command)

Tree measured: the **composed tree** — lane-e (this WP) with `lane-b` (WP02) and `lane-c` (WP03)
merged in. Neither dependency was on `feat/sync-sleep-count-3136` at the time WP05 started, so the
composition was done in-lane; see the two merge commits at the head of this branch.

```bash
V=/home/jeroennouws/dev/sk-missions/3136/.venv
"$V/bin/python" -V                       # Python 3.12.13
"$V/bin/python" -m pytest --version      # pytest 9.0.3
"$V/bin/ruff" --version                  # ruff 0.15.12
"$V/bin/mypy" --version                  # mypy 1.20.2 (compiled: yes)
command -v pytest                        # /home/jeroennouws/.local/bin/pytest  <- NOT this tree
command -v python                        # /usr/bin/python                      <- NOT this tree
```

`command -v` resolves to an unrelated checkout on the system interpreter, which is why every command
in this WP spells out `"$V/bin/…"` rather than a bare tool name.

**Never a bare `uv run` or `uv sync` in this checkout** — it re-solves against the tracked
`.python-version` (`3.11.15`), destroys `.venv`, and recreates it without pytest/ruff/mypy. Four
occurrences in this mission. The only sanctioned forms are `"$V/bin/python" -m …` and, if a solve is
genuinely required, `uv run --python 3.12 --extra test --extra lint python -m …` — the flags are not
optional.

## Cross-tree trap — which tree an import resolves to

The venv carries an editable `.pth` pointing at the **root** checkout's `src`, not at this lane:

```bash
"$V/bin/python" -c "import specify_cli; print(specify_cli.__file__)"
#   -> /home/jeroennouws/dev/sk-missions/3136/src/specify_cli/__init__.py        (ROOT — wrong tree)
PYTHONPATH="$PWD/src" "$V/bin/python" -c "import specify_cli; print(specify_cli.__file__)"
#   -> …/.worktrees/sync-sleep-count-3136-01KZ9B5A-lane-e/src/specify_cli/…      (this lane)
```

Every measurement in this WP therefore sets `PYTHONPATH` explicitly and prints
`specify_cli.__file__` alongside its result, rather than inheriting an ambient path.

---

## What shipped

Three surfaces, and the third is why this WP owns three files rather than two:

1. `tests/architectural/test_shared_module_object_patches.py` — the gate (20 arms).
2. `tests/architectural/_baselines.yaml` — the 13th top-level key, 22 frozen rows.
3. `tests/architectural/test_ratchet_baselines.py` — the four edits **without which the key is read
   by nothing**, plus a zero-tolerance pin for the other pre-existing inert key.

### The predicate, and why both halves are enforced in code

Reproducing command (prints the four counts and the `httpx.Client` verdict):

```bash
PYTHONPATH="$PWD/src" "$V/bin/python" -m pytest \
  tests/architectural/test_shared_module_object_patches.py -q -ra -p no:cacheprovider -s
```

Measured on the composed tree (lane-e + lane-b + lane-c):

| quantity | value |
|---|---|
| total dotted `patch()` sites under `tests/sync/` | 669 |
| the **literal** FR-005 predicate would flag | 654 |
| **narrowed** — mechanism half alone | 270 |
| **the shipped gate flags** — mechanism AND read-side | **22** |

The read-side half is code, not a docstring, and `[UNVERIFIED]` item 12 closes here: of the
**131** `specify_cli.tracker.saas_client.httpx.Client` sites, the mechanism half flags **131** and
the shipped gate flags **0**. Zero of their bound mocks (`mock_cls` ×115, `mock_http_cls` ×13,
`mock_httpx_client_cls` ×3) carry a count-or-equality read. Three carry a `side_effect=`
**assignment**, which drives a mock but asserts nothing, so it is deliberately not a read — folding
drives into the read half would re-open the whole 131-row bucket and make the gate unshippable.

### Which reader arm 4c uses, and how the exemption is sized

**The AST reader** — `patch_seam_census.run_census`, which counts `ast.Call` patch nodes and skips
docstrings and comments by construction (NFR-007). Named explicitly because RL-014 records that this
count is reader-dependent: an AST pass finds **1** surviving live pre-fix `time.sleep` `patch()`
target, a regex pass finds **3**, the extra two being prose an AST pass correctly skips.

Arm 4c has two parts, sized differently and deliberately separate:

- Over the **two retarget files** (`test_saas_client.py`, `test_saas_client_origin.py`): 0 pre-fix
  targets and 14 / 9 / 1 post-fix, with **no exemption of any kind** — the guard is not in that scope.
- **Repo-wide over `tests/sync/`**: exactly **1** surviving pre-fix target, exempted by the
  *mechanism* that makes it legitimate — its node also patches the corresponding alias, i.e. it is a
  **two-sided recorder**. Never by filename. A second guard built the same way would be exempt for
  the same structural reason; a file that merely shared a name would not.

### The 16-vs-14 scoping decision (RL-022), and how it is declared

**14, guard-excluded** — the invariant `spec.md:560-568` expresses. Declared as
`_two_sided_recorder_nodes()`: a node that patches both a pre-fix seam target and its alias. Both
figures are printed by the arm, so the exclusion is visible rather than folded into a total:

```
[WP05 gate] sleep_seam_patch_sites (unscoped)      = 16
[WP05 gate] declared exclusion: two-sided recorder nodes = [('tests/sync/tracker/test_sleep_attribution_guard_3136.py', '_dual_recorder_window')]
[WP05 gate] sleep_seam_patch_sites (scoped)        = 14
[WP05 gate]   13 in tests/sync/tracker/test_saas_client.py
[WP05 gate]   1 in tests/sync/tracker/test_saas_client_origin.py
```

16 unscoped was rejected because it grades the mission's own output and rises again with any later
guard. A hardcoded filename was rejected because a gate that silently knows one file's name is not
mechanism-keyed — the exact vacuity the instrument exists to prevent.

### `test_no_dead_symbols` — the disposition, recorded explicitly

**The scoped-arm fallback** (`plan.md` `[UNVERIFIED]` item 10's stated escape), not a silent pick and
not a deletion. `test_no_unregistered_baseline_keys_are_added` fires for any key added from this
mission forward; the one pre-existing offender sits in a **closed** `_GRANDFATHERED_UNREGISTERED_KEYS`
frozenset pinned by its own equality assertion, so widening it costs a visible diff in
`test_ratchet_baselines.py` rather than a silent one in the YAML. Choosing between its two honest
dispositions needs the owner of the gate it governs, which is outside this mission. Filed as
**RL-030**.

The *other* half of the inert pair needed a different answer and got one, folded in scope:
`test_all_declarations_required` is in `_REQUIRED_TOP_LEVEL_KEYS` yet read by no comparison, and it
structurally cannot join `single_baselines` — the module publishes no module-scope frozenset for
`_import_module_attr` to take the `len()` of. Its sub-keys are zero-tolerance pins, so
`test_declaration_pins_are_zero_tolerance` reads them directly.

### Red-first evidence

Every arm was shown failing before it was believed. Reproducing commands:

```bash
# BLOCKER-3 reproduced: the 13th key present, registration absent
git stash  # or check out the commit before the ratchet edits
"$V/bin/python" -m pytest tests/architectural/test_ratchet_baselines.py -q -ra -p no:cacheprovider
#   -> 3 passed. The key is in the YAML and NOTHING reads it.

# Registration bites (T030): flagged_sites 22 -> 21, then restore
sed -i 's/^  flagged_sites: 22$/  flagged_sites: 21/' tests/architectural/_baselines.yaml
"$V/bin/python" -m pytest tests/architectural/test_ratchet_baselines.py::test_growing_an_allowlist_above_baseline_fails -q -ra
git checkout -- tests/architectural/_baselines.yaml

# Reverse containment bites (T031): add a throwaway 14th key, then revert
printf '\ntest_throwaway_unregistered_key_3136:\n  entries: 1\n' >> tests/architectural/_baselines.yaml
"$V/bin/python" -m pytest tests/architectural/test_ratchet_baselines.py::test_no_unregistered_baseline_keys_are_added -q -ra
git checkout -- tests/architectural/_baselines.yaml
```

Verbatim failure text observed:

```
E   - test_shared_module_object_patches.BASELINE_SITES: baseline=21 current=22. Remove the new
    entry OR edit _baselines.yaml from 21 to 22 with a justification comment in the PR.

E   AssertionError: `_baselines.yaml::test_shared_module_object_patches.flagged_sites` records 21
    but the module publishes 22 rows.

E   AssertionError: `_baselines.yaml` carries top-level key(s) no comparison reads:
    ['test_throwaway_unregistered_key_3136'].
E   assert {'test_no_dea...red_key_3136'} <= frozenset({'t...ead_symbols'})
E     Extra items in the left set:
E     'test_throwaway_unregistered_key_3136'

# arm 4a against a wrapper-form seam
    wrapper form keeps live stdlib calls at [(4, 'time.sleep'), (6, 'time.monotonic'), (8, 'secrets.randbelow')]
# arm 4b against the same
    alias name(s) ['_monotonic', '_randbelow', '_sleep'] are defs, not assignments
# arm 4c on a synthetic pre-fix copy (also shipped as an in-suite arm)
    {'…time.sleep': 14, '…time.monotonic': 9, '…secrets.randbelow': 1, '…_sleep': 0, '…_monotonic': 0, '…_randbelow': 0}
# baseline set equality, BOTH directions
    flagged-not-frozen=['tests/sync/test_batch_sync.py:150 | specify_cli.sync.batch.requests.post | assert_not_called']
    frozen-not-flagged=['tests/sync/ghost.py:1 | pkg.mod.time.sleep | call_count']
```

The anti-weasel twin for the owner-completion arm is not decorative: every row is `unassigned` today,
and `unassigned` is never complete, so the arm would pass without exercising anything. The twin
injects a **real** completed owner read out of the event log (`WP01` on this run) and requires the arm
to catch it. It skips loudly, with a reason, if no work package has completed yet.

### Arm D of WP03's control was NOT moved

`tests/architectural/test_patch_seam_census_control.py` → `9 passed`, `EXIT=0`, tables untouched.
Arm D scans `tests/sync/` and selects `pre`/`post` by an AST discriminator; this WP adds files only
under `tests/architectural/`, so no third tree state was created. Independently re-derived: the
composed tree measures `own_module 384 / reach_through 264 / foreign 6 / not_a_module 15 /
unresolvable 0`, which is Arm D's `post` table exactly.

### `tests/sync` and `tests/cli` were NEVER run by this WP

This gate is a static AST reader over that source; it parses those files, it never collects them. The
only pytest invocations in this WP's transcript name `tests/architectural/`.

### Gate results (quoted verbatim, with the command that reproduces each)

```bash
"$V/bin/ruff" check tests/architectural/                               # EXIT=0  All checks passed!
"$V/bin/mypy" --strict tests/architectural/test_shared_module_object_patches.py \
                       tests/architectural/test_ratchet_baselines.py   # EXIT=0

"$V/bin/python" -m pytest tests/architectural/test_shared_module_object_patches.py -q -ra -p no:cacheprovider
#   20 passed in 64.94s (0:01:04)
"$V/bin/python" -m pytest tests/architectural/test_ratchet_baselines.py -q -ra -p no:cacheprovider
#   5 passed in 47.01s          (3 passed before the registration edits)
"$V/bin/python" -m pytest tests/architectural/test_patch_seam_census_control.py -q -ra -p no:cacheprovider
#   9 passed in 77.06s          (Arm D's tables unmoved)
"$V/bin/python" -m pytest tests/architectural/test_golden_count_ban.py \
                          tests/architectural/test_pytest_marker_convention.py -q -ra -p no:cacheprovider
#   11 passed in 62.81s
"$V/bin/python" -m pytest tests/architectural/ -q -ra -p no:cacheprovider -n auto --dist loadfile
#   1720 passed, 2 skipped, 2 xfailed, 1 warning in 788.20s (0:13:08)
```

`ruff format` was never run. The 2 skips (`test_compat_shims.py:96`, `:104` — empty parameter sets)
and the 2 xfails (`test_egress_consent_boundary.py` #3113 cases A and B, both carrying their own
recorded non-adoption decision) are **pre-existing and unrelated** to this WP; they are present on the
same suite before these files existed.

**One timeout, reported rather than retried silently.** The first full-suite attempt was bounded at
600s and was killed by that bound at ~96% with zero failures — `EXIT=124`. That is a datum about the
bound, not a result about the suite. It was re-run at a 1800s bound, which completed in 788s. The
figure quoted above is the completed run.

### Definition-of-Done item 11, with the RL-003 correction applied

The prompt's block at `WP05-mechanism-gate-and-baseline.md:609-617` reuses the twin-token loop RL-003
documents as unsatisfiable — it greps a token from a sibling file against a file with no reason to
carry it. Here `command -v` *does* belong in this file (the environment transcript is section 1), so
the literal check happens to pass; but the corrected shape is used as well, with a token this
specific file must carry:

```bash
NOTES=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/mechanism-gate-3136.md
test -s "$NOTES" && echo "NON-EMPTY: $(wc -l < "$NOTES") lines"   # must print a line count
grep -c 'command -v'     "$NOTES"    # prompt's token — load-bearing here only by coincidence
grep -c 'BASELINE_SITES' "$NOTES"    # CORRECTED twin: a token THIS file must carry
grep -n 'uv run'         "$NOTES"    # -n, not -c: the count is not the evidence
```

**No output of those commands is transcribed here, deliberately.** A count about the file it is
written in is invalidated by the act of writing it down — that is recurring failure pattern #1, and
an earlier revision of this very block re-incurred it: it recorded four numbers that were true one
commit earlier and false the moment the block was committed. The header at the top of this file
promises every count travels with its re-derivation command; the command *is* the evidence, and a
frozen number beside it is strictly worse than no number at all, because it looks checkable.

The property being evidenced is **not** a count. It is: *no occurrence of `uv run` in this file is a
bare command form.* Re-derive it by reading each hit `grep -n` prints and classifying it — every one
must be either (a) prose **about** the bare form, including the warning against it and the text of
these grep arguments, or (b) an actual command carrying `--python 3.12 --extra test --extra lint` in
full. A `grep -c` cannot tell those apart (RL-003b), which is why the count was never the evidence
and why `-n` replaces `-c` above.
