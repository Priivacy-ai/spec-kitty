# WP04 evidence — Route the 4 degrade sites and change their 4 handlers

Agent: `python-pedro` (implementer). Mission `meta-fail-closed-3162-01KZ7FSQ`,
branch `feat/meta-fail-closed-3162`. All work executed **from the repository root**.

**Declared out-of-map writes.** This file is a planning write under `kitty-specs/`, which
cannot appear in `owned_files` by construction (`mission_parsing.py:153-157`, `:207-215`).
Also out-of-map: `tests/mission_runtime/test_wp04_f1_absent_arm_is_intended.py` — mandated by
the operator's assignment of ledger item **F1** to WP04; it lives under `tests/mission_runtime/**`
which *is* owned, so only its subject matter (two modules outside the four census sites) is
out-of-map, and both of those modules are read **read-only**. No file outside `owned_files` was
edited.

---

## 0. Startup guard refusal (exact error)

```
$ spec-kitty agent action implement WP04 --agent claude --mission meta-fail-closed-3162-01KZ7FSQ
Branch: feat/meta-fail-closed-3162 (target for this mission)
Error: dependencies_not_satisfied: WP04 depends on WP03; all dependencies must be approved or done before implementation can start
```

Note the guard fired on **dependency gating**, not on workspace resolution. WP03 is in
`for_review`, not `approved` — so the briefing's "WP01, WP02, WP03, WP05, WP07 are approved" is
stale for WP03. Measured board: `WP01 WP02 WP05 WP07` approved; `WP03 WP06` for_review;
`WP04 WP08` planned. Proceeded from the repository root as directed.

---

## 1. The charter exceptions, stated out loud (Reviewer Guidance 7)

**(a) `C-002`'s "same edit" reads as "same WORK PACKAGE" here, and only here.**
`C-002` ("all six handlers change in the same edit as their routing") and `FR-002` ("land the
routing first and quote the resulting escape as the red") contradict each other as written.
`plan.md`'s atomicity coupling 5 is the ruling: **commit** granularity for rows 9 and 12 (WP03),
**work-package** granularity for rows 1, 2, 3 and 13 (here). `FR-014`'s per-site atomicity is
therefore satisfied at work-package granularity for these four rows and at commit granularity
**nowhere** in this WP.

**(b) A base-red is impossible by construction, so the red is on an intermediate commit.**
`NFR-003` requires the degrade behaviour be identical pre and post, and `D4=(a)` forbids pinning a
behaviour change. So the four fallback tests are **green at baseline** by requirement. The red
lives on commit 1. With commit 0 in place this is **checkable by re-checkout** (§5) rather than
asserted — a documented charter exception (`plan.md` Charter Check ATDD-first row; Complexity
Tracking row 1), not an omission.

---

## 2. Baseline (T020)

### 2.1 Routed count PRE — and two stale figures in the prompt

Measured with the manifest's own recorded command, `scripts/verify_meta_routing_manifest_3162.py`:

```
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 130
  const ROUTED_LOAD_META_FLOOR = 127
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band: [128, 131] (two-sided; 127 is RED)
  routed 130 in [128, 131]: OK
VERDICT: PASS
```

**Routed PRE = 130** over an input population of **1 199** `*.py` files.

> **Prompt defect 1.** The prompt states routed PRE "Expect **129**", band `[127, 130]`, floor
> `126`, "**126 is RED**". All four figures are stale: WP05 spent its allocated +1 (129 → 130) and
> WP06 re-derived the floor 126 → 127. The live band is **`[128, 131]`** and **127 is RED**.
> WP04's allocated delta in `contracts/headroom-allocation.md:41` is **0-net** — that part holds,
> and is what I honoured.

Band re-derived from the three quoted clauses, not copied: clause 2 (`len(routed) > FLOOR`) is
strict and dominates clause 1, so low bound = `FLOOR + 1` = 128; clause 3 gives high bound
= `FLOOR + MARGIN` = 131. A live count of exactly **127 is RED** (`127 > 127` is false).

### 2.2 Baseline worktree at `96494e5ec`

```
$ git worktree add <scratch>/base-96494e5ec 96494e5ec
HEAD is now at 96494e5ec test(landing): pin the #3194 EACCES-safe stat guard with real permission fixtures
$ git merge-base --is-ancestor 96494e5ec HEAD && echo YES
YES
$ git diff --name-only 96494e5ec HEAD | grep -v '^kitty-' | wc -l
36
```

> **Prompt defect 2.** The prompt asserts this check yields **0** files. Measured: **36**. The 36
> are precisely the sibling WPs' landings (WP02/WP03/WP05/WP06/WP07) — including
> `src/specify_cli/missions/_read_path_resolver.py` and
> `src/specify_cli/coordination/surface_resolver.py`, which are **in my four sites' own call
> chain**. The claim was true only before any src/ landed on the lane.
>
> Consequence handled, not ignored: I captured `pre` **twice** — once against `96494e5ec` and once
> against HEAD-before-my-edits — so my delta is attributable separately from siblings'. The 12 case
> lines are **identical** between the two (§6), so `96494e5ec` remains a sound `pre` for this
> measurement despite the drift.

### 2.3 `C901` PRE (ceiling 15)

| File | C901 PRE | C901 POST |
|---|---|---|
| `src/mission_runtime/resolution.py` | `All checks passed!` | `All checks passed!` |
| `src/specify_cli/upgrade/feature_meta.py` | `All checks passed!` | `All checks passed!` |
| `src/specify_cli/core/paths.py` | `All checks passed!` | `All checks passed!` |

No function crossed the ceiling; `_mid8_from_primary_meta` did not grow past it.

---

## 3. The four sites, cited by `file:line` and symbol (`C-003`)

Line numbers below are **pre-edit**, and matched the prompt exactly at start of work.

| Row | Read (pre-edit) | Symbol | Handler (pre-edit) | Fallback | Derived or constant? |
|---|---|---|---|---|---|
| 1 | `src/mission_runtime/resolution.py:509` | `_mid8_from_primary_meta` | `:514` | `return ""` | **constant** |
| 2 | `src/mission_runtime/resolution.py:852` | `_resolve_coordination_branch` | `:853` | `return None` | **constant** |
| 3 | `src/mission_runtime/resolution.py:1107` | `_resolve_mission_id` | `:1108` | `f"legacy-{mission_slug}"` (`:1114`) | **constant w.r.t. the file** |
| 13 | `src/specify_cli/upgrade/feature_meta.py:42` | `load_feature_meta` | `:43` | `return None` | **constant** |

Post-edit handler positions: `resolution.py:523`, `:867`, `:1134`; `feature_meta.py:53`.

> **`wps.yaml` T021's claim corrected.** It asserts row 3's `legacy-<slug>` fallback is "derived
> from the malformed file". It is not. Measured at `resolution.py` — the sentinel interpolates the
> **caller's own `mission_slug` argument** and `meta` is `None` on that path. The probe shows it
> directly: with handle `wp04-sc002-degrade-probe-01KWP04S`, the malformed capture is
> `'legacy-wp04-sc002-degrade-probe-01KWP04S'` — the handle echoed back, never file content.
> **All four fallbacks are constant with respect to the file**, so no site can emit a
> plausible-but-wrong value read out of a corrupt file.

---

## 4. The three commits, in order, unsquashed

| # | SHA | Subject | Contents |
|---|---|---|---|
| 0 | `45b278823` | `test(WP04): commit 0 — pin the four degrade-site malformed-input fallbacks` | tests only |
| 1 | `d5f39510f` | `feat(WP04): commit 1 — route the 4 degrade sites, amend the reader docstring` | routing + docstring + ledger rows + call-count assertions |
| 2 | `eaa75ecd1` | `fix(WP04): commit 2 — widen the 4 degrade handlers, restoring the degrade` | handlers only |

Plus a fourth, `d5fcfa731` — `SC-007`'s three assertions and the F1 pin (tests only).

```
$ git log --oneline 7cf529302..HEAD
d5fcfa731 test(WP04): SC-007's three assertions, and pin ledger item F1 as intended
f5972099e fix(3162): module-level pytestmark — the marker gates never see class-level marks
eaa75ecd1 fix(WP04): commit 2 — widen the 4 degrade handlers, restoring the degrade
15631ffdb chore(spec-kitty): status transition WP06
d5f39510f feat(WP04): commit 1 — route the 4 degrade sites, amend the reader docstring
45b278823 test(WP04): commit 0 — pin the four degrade-site malformed-input fallbacks
2b70e1cf8 chore(spec-kitty): status transition WP06
```

A sibling's commits (`f5972099e`, and two WP06 status transitions) are **interleaved**. My three
are in the required relative order and all three survive unsquashed.

Commit 0 carries tests and nothing else:

```
$ git show --stat 45b278823
 .../test_wp04_degrade_site_fallbacks.py            | 190 +++++++++++++++++
 .../test_wp04_row13_load_feature_meta_fallback.py  |  90 ++++++++++
 2 files changed, 280 insertions(+)
```

Commit 1 carries **both** `core/paths.py` and the routed site files (`SC-014` second half):

```
$ git show --stat d5f39510f
 src/mission_runtime/resolution.py                  |  51 ++++---
 src/specify_cli/core/paths.py                      |  28 +++-
 src/specify_cli/upgrade/feature_meta.py            |   5 +-
 .../test_wp04_routed_call_counts.py                | 154 +++++++++++++++++++++
 .../test_meta_fail_closed_full_census_contract.py  |   4 -
 5 files changed, 211 insertions(+), 31 deletions(-)
```

**No `except` clause changed in commit 1:**

```
$ git show d5f39510f | grep -cE '^[+-][[:space:]]*except .*:'
0
```

(A looser `grep '^[-+].*except'` returns 6 — all six are comment or docstring **prose** lines
mentioning the word, not statements. The anchored pattern above is the load-bearing one.)

---

## 5. `FR-002`'s red — green → red → green, re-checkoutable

The four node ids (recorded in T021 A5):

```
tests/mission_runtime/test_wp04_degrade_site_fallbacks.py::test_row1_mid8_from_primary_meta_degrades_to_empty_string
tests/mission_runtime/test_wp04_degrade_site_fallbacks.py::test_row2_resolve_coordination_branch_degrades_to_none
tests/mission_runtime/test_wp04_degrade_site_fallbacks.py::test_row3_resolve_mission_id_degrades_to_legacy_sentinel
tests/upgrade/test_wp04_row13_load_feature_meta_fallback.py::test_row13_load_feature_meta_degrades_to_none_on_malformed
```

**Verified by re-checkout** in a detached scratch worktree, running those exact ids at each SHA:

| SHA | Commit | Result |
|---|---|---|
| `45b278823` | commit 0 | **4 passed** in 76.68s |
| `d5f39510f` | commit 1 | **4 failed** in 53.11s |
| `eaa75ecd1` | commit 2 | **4 passed** in 55.57s |

Commit 0 was additionally green **against baseline source** — 6 passed, run *from* the
`96494e5ec` worktree (see §11 on why `PYTHONPATH` is the wrong instrument for pytest here).

The commit-1 red, quoted from the redirected run — `4 failed`, and every one of the four fails
with the escaping typed error:

```
E   specify_cli.core.paths.MissionMetaReadError: Cannot read <tmp>/kitty-specs/wp04-degrade-fallback-pin-01KWP04D/meta.json:
    Malformed JSON in <same path>: Expecting value: line 1 column 15 (char 14)
    — fail-closed (meta.json exists but is corrupt or unreadable)
```

with the escape past `except ValueError` visible in the traceback:

```
src/mission_runtime/resolution.py:515: in _mid8_from_primary_meta
    meta = load_meta_fail_closed(primary_dir)
src/specify_cli/core/paths.py:694: in load_meta_fail_closed
E   specify_cli.core.paths.MissionMetaReadError: ...
```

Same shape at `resolution.py:859` (`_resolve_coordination_branch`), `resolution.py:1120`
(`_resolve_mission_id`) and `feature_meta.py` (`load_feature_meta`). This is a real failure of
committed tests at a named SHA — **not** a hand-rolled scratch traceback.

---

## 6. `SC-002` / `NFR-003` — 12 lines per side, positive control first

**Positive control, quoted first.** One handler deliberately broken (`resolution.py:1108`
narrowed `except ValueError:` → `except TypeError:`) in an **isolated copy** of the baseline `src`,
so no lane's working tree was ever dirtied:

```
$ diff <(grep '|' pre_base.txt) <(grep '|' poscontrol.txt)
7c7
< _resolve_mission_id|malformed|'legacy-wp04-sc002-degrade-probe-01KWP04S'
---
> _resolve_mission_id|malformed|!!RAISED ValueError: Malformed JSON in <tmp>/meta.json: Expecting value: line 1 column 15 (char 14)
diff exit=1
```

**Non-empty** — the probe is sensitive to exactly the defect class it exists to catch.

**The captures.** Probe = `4 sites × 3 shapes` (malformed / absent / valid). It is a standalone
script in scratch, never under `src/` or `tests/architectural/`. `PYTHONPATH` **is** honoured for
standalone `python` (verified per capture by the printed resolved module path).

```
pre_base.txt : PYTHONPATH=<scratch>/base-96494e5ec/src   → mission_runtime resolved from <scratch>/base-96494e5ec/src/mission_runtime
pre_head.txt : PYTHONPATH=<repo>/src                     → mission_runtime resolved from <repo>/src/mission_runtime
post.txt     : PYTHONPATH=<repo>/src                     → mission_runtime resolved from <repo>/src/mission_runtime

$ wc -l pre_base.txt pre_head.txt post.txt
  20  20  20   (60 total)          # non-zero on every side
$ grep 'INPUT cases' *.txt         # printed input count, each side
INPUT cases: 12   (pre_base)
INPUT cases: 12   (pre_head)
INPUT cases: 12   (post)
$ for f in pre_base pre_head post; do grep -c '|' $f.txt; done
12  12  12                         # 12 case lines each
```

**Both diffs empty:**

```
$ diff <(grep '|' pre_base.txt) <(grep '|' post.txt) ; echo exit=$?
exit=0
$ diff <(grep '|' pre_head.txt) <(grep '|' post.txt) ; echo exit=$?
exit=0
```

The 12 captured lines (identical on all three sides):

```
_mid8_from_primary_meta|malformed|''
_mid8_from_primary_meta|absent|''
_mid8_from_primary_meta|valid|'01KWP04S'
_resolve_coordination_branch|malformed|None
_resolve_coordination_branch|absent|None
_resolve_coordination_branch|valid|'kitty/coord-sc002-probe'
_resolve_mission_id|malformed|'legacy-wp04-sc002-degrade-probe-01KWP04S'
_resolve_mission_id|absent|'legacy-wp04-sc002-degrade-probe-01KWP04S'
_resolve_mission_id|valid|'01KWP04SC002PROBE7X9QZTBVKMN'  (mission_id echoed)
load_feature_meta|malformed|None
load_feature_meta|absent|None
load_feature_meta|valid|{...parsed mapping...}
```

The **absent** arm is captured explicitly at all four sites — a malformed-only probe would have
satisfied the criterion's shape while that arm regressed untouched.

---

## 7. The budget is closed by assertion (Reviewer Guidance 1b)

Routed count **PRE 130 → POST 130**, delta **0**. Band `[128, 131]`, floor 127, **127 is RED**.
The swap is 0-net by construction: `load_meta` and `load_meta_fail_closed` are both in
`ROUTED_CALLEES`, so exchanging one for the other adds no call site.

Four per-site structural assertions in the routing commit
(`tests/mission_runtime/test_wp04_routed_call_counts.py`): each routed function's **own body**
holds exactly **1** `load_meta_fail_closed(` and **0** `load_meta(`, matched on the **exact callee
name**, module named in every message. Nested function definitions are excluded so "own body"
means what it says.

The file also carries a **discriminator control** —
`test_exact_name_matching_is_what_the_assertion_actually_does` — proving the matcher is exact-name
and not substring. Without it the four assertions could be vacuous, since
`load_meta_fail_closed` *contains* `load_meta`.

---

## 8. `SC-014` — the docstring amendment, and the docstring-only proof

**PRE** (`core/paths.py:648-651`, quoted from the baseline worktree):

> *"Callers that must stay deliberately silent about corruption (placement probes, best-effort
> displays) keep using `load_meta_or_empty` or the canonical reader's `on_malformed="none"` arm
> instead -- they are not routed here."*

**POST** — the "not routed here" claim is gone, and the routed degrade callers are named as
clients with the arm they keep:

> *"Deliberately-silent callers ARE routed here (#3162 / FR-012, operator ruling R-2). Four
> degrade sites — `mission_runtime.resolution._mid8_from_primary_meta`,
> `._resolve_coordination_branch`, `._resolve_mission_id` and
> `specify_cli.upgrade.feature_meta.load_feature_meta` — are silent about corruption by outcome and
> are nonetheless clients of this function. They keep the **malformed arm** by catching
> `MissionMetaReadError` in the caller's own `except` and degrading to that site's own sentinel
> (`""`, `None`, `legacy-<slug>`, `None` respectively); the absent-file and valid arms are
> unchanged. So corruption is absorbed at the call site, never inside this reader — this function's
> contract stays strictly fail-closed, and the choice to stay silent is visible in the caller."*

**`DIR-032` — foreign `FR-007` qualified.** `core/paths.py:639` and `:643` carried a bare `FR-007`
belonging to **#3140**, colliding with this spec's own `FR-007`. Both now read `#3140#FR-007`, with
an inline note stating why.

**Docstring-only proof (T025 4a) — WP05 depends on all four:**

- (i) Every changed line is inside the docstring. `git diff -- src/specify_cli/core/paths.py`
  shows 22 insertions / 6 deletions, **all prose** — no statement, `def` or `class` line.
- (ii) `def load_meta_fail_closed(feature_dir: Path) -> dict[str, Any] | None:` — byte-identical,
  still line **638**, baseline and live.
- (iii) `class MissionMetaReadError(RuntimeError):` — unchanged, still line **506**. No new
  exception class, no changed base.
- (iv) Return contract unchanged: `allow_missing=True, on_malformed="raise"` still hard-coded
  (`:676` pre-edit → `:692` post-edit, shifted only by the 16-line docstring growth); still `None`
  on absence, still `MissionMetaReadError` with `__cause__` on corruption.

---

## 9. The handlers (`SC-007`)

```
$ grep -n "except (ValueError, MissionMetaReadError)\|except MissionMetaReadError" \
    src/mission_runtime/resolution.py src/specify_cli/upgrade/feature_meta.py
src/mission_runtime/resolution.py:523:    except (ValueError, MissionMetaReadError):
src/mission_runtime/resolution.py:867:    except MissionMetaReadError:
src/mission_runtime/resolution.py:1134:    except MissionMetaReadError:
src/specify_cli/upgrade/feature_meta.py:53:    except MissionMetaReadError:
```

`resolution.py:523` is a **tuple**. `:867`, `:1134` and `feature_meta.py:53` are exact narrow
catches — their `try` holds **only** the read (`_compose_primary_feature_dir` sits outside, above).

**`except Exception` at none of the six `C-002` handlers.** `resolution.py` contains 3
`except Exception`, all in unrelated functions and all **pre-existing at `96494e5ec`** (count 3
there too): `:591 _resolve_wp_lane`, `:627 _resolve_wp_bearing_fields`, `:733 _resolve_review_wp_id`.
`feature_meta.py` contains **0**. Asserted structurally over all six handlers by symbol, with the
input count printed (`SC-007(c) INPUT: 6 handlers enumerated by symbol, N except-clauses inspected`).

### `SC-007`'s three assertions — and proof each is load-bearing

**(a) Traversal guard asserts the OUTCOME `== ""`**, never `pytest.raises(ValueError)`.
5 parametrized unsafe segments (`..evil`, `a..b`, `evil/../x`, `.hidden`, `foo/bar`).
**Control:** with the `:523` tuple narrowed to `MissionMetaReadError` alone in a detached control
worktree, these 5 go **RED**:

```
5 failed, 3 passed
E   ValueError: Not a safe path segment: 'foo/bar' — value must not contain path separators.
src/specify_cli/missions/_read_path_resolver.py:1319: in _compose_primary_feature_dir
src/specify_cli/core/paths.py:97: in assert_safe_path_segment
```

This is the documented cheat made concrete: a `pytest.raises(ValueError)` form would have been
**green** on that narrowed tree while the degrade-to-`""` behaviour was deleted. Asserting the
return value is what makes the test sensitive to the narrowing. (b) and (c) correctly stayed green,
confirming they are orthogonal.

**(b) `MissionSelectorAmbiguous` propagates** out of `_mid8_from_primary_meta` — an **assertion**,
built on two missions sharing mid8 `01KWP04A`. It also asserts the message names *both* candidates,
so the refusal stays diagnosable. `MissionSelectorAmbiguous` is a plain `Exception`
(`_read_path_resolver.py:49`) raised inside the same `try`, which is why `except Exception` there
is banned. Cited to the `MissionSelectorAmbiguous` in-code note specifically — **not** the range
that also covers the separate traversal-`ValueError` note above it.

**(c) Six handlers, by symbol**, plus a complement assertion that all six *do* name
`MissionMetaReadError` — "not too broad" and "wide enough" both pinned. The two modules WP04 does
not own (`decisions/service.py::_resolve_mission_id`,
`missions/_resolve_planning_branch.py::load_mission_target_branch`) are read **read-only**.

---

## 10. Ledger rows deleted in the routing commit

Matched by **full `(path, symbol)` key**, verified 1 → 0 each:

```
PRE  matches=1 / POST matches=0   ("src/mission_runtime/resolution.py", "_mid8_from_primary_meta")
PRE  matches=1 / POST matches=0   ("src/mission_runtime/resolution.py", "_resolve_coordination_branch")
PRE  matches=1 / POST matches=0   ("src/mission_runtime/resolution.py", "_resolve_mission_id")
PRE  matches=1 / POST matches=0   ("src/specify_cli/upgrade/feature_meta.py", "load_feature_meta")
```

Deletion was done by exact full-line string match with an `assert count == 1` per key, never by
line number and never by bare symbol.

> **Prompt observation.** The prompt warns that a bare `grep '"_resolve_mission_id"'` matches
> **two** rows. Measured now: it matches **one** (`:200`), because WP03 has since deleted its
> `decisions/service.py` row 9. The trap is currently inert; the discipline was applied regardless,
> since dependency order is the only thing that made it inert.

Ledger test green: `tests/specify_cli/test_meta_fail_closed_full_census_contract.py` +
call-count assertions → **32 passed**.

---

## 11. The `PYTHONPATH` instruction is unsound for pytest — measured

> **Prompt defect 3, and the most consequential one.** The prompt requires
> `PYTHONPATH=<workspace>/src` on *"every `python -c` and every `pytest` that could run outside the
> repository root"*. For **pytest this does not work**, and it fails **silently** — the exact class
> of hazard the prompt was written to prevent.

`pytest.ini:9` sets `pythonpath = src`, which pytest resolves **relative to its own rootdir** and
inserts *ahead* of the `PYTHONPATH` env var. Measured `sys.path` from inside a pytest run invoked
with `PYTHONPATH=<control>/src`:

```
  syspath: /home/jeroennouws/dev/sk-missions/3162
  syspath: /home/jeroennouws/dev/sk-missions/3162/tests/mission_runtime
  syspath: /home/jeroennouws/dev/sk-missions/3162
  syspath: /home/jeroennouws/dev/sk-missions/3162/src        <-- rootdir's src wins
  syspath: /home/jeroennouws/dev/sk-missions/3162
  syspath: <scratch>/narrowctl/src                            <-- PYTHONPATH, too late
MISSION_RUNTIME: /home/jeroennouws/dev/sk-missions/3162/src/mission_runtime
```

**How it was caught:** my first `SC-007(a)` control run reported `8 passed` against a tree whose
handler I had deliberately narrowed. A control that cannot fail is not a control, so I traced it
rather than accepting the green.

**Correct method, used for every cross-tree measurement in this evidence:** run pytest **from
inside** the target tree (`cd <worktree> && pytest ...`), so rootdir — and therefore `src` —
is the tree under test. `PYTHONPATH` remains correct and necessary for standalone
`python` / `python -c`, where it *is* honoured (verified per capture by printing the resolved
module path).

Two claims were re-derived under the corrected method: commit 0's baseline green (**6 passed**, run
from the `96494e5ec` worktree) and the `SC-007(a)` narrowing control (**5 failed, 3 passed**, run
from a detached control worktree).

---

## 12. The chain hazard — calibrated sweep, per routed site

Calibration first; an uncalibrated sweep's silence means nothing.

```
$ .venv/bin/python scripts/sweep_degrade_arms_on_routed_chain_3162.py --self-check
  CONTROL: expected ['_read_path_resolver.py:1257', 'mission_check_prerequisites.py:238',
                     'mission_finalize.py:291', 'mission_record_analysis.py:259',
                     'mission_setup_plan.py:301', 'surface_resolver.py:564']
  CONTROL: hazards found 6, locations [... 12 entries ...]
  CONTROL: PASS - known answer reproduced exactly
== SELF-CHECK PASSED: the 6 HAZARD(S) above are the *control's* known answer at f1681bf1 ==
  live sweep (seed read_primary_meta): HAZARDS: 0 → VERDICT: CLEAN
```

Per routed site, **dotted qualnames**:

| Seed | Transitive callers | Escape frames | Hazards |
|---|---|---|---|
| `mission_runtime.resolution._mid8_from_primary_meta` | 62 | 54 | **0** — CLEAN |
| `mission_runtime.resolution._resolve_coordination_branch` | 234 | 181 | **1** |
| `mission_runtime.resolution._resolve_mission_id` | 220 | 166 | **1** |
| `specify_cli.upgrade.feature_meta.load_feature_meta` | 5 | 5 | **0** — CLEAN |

Both hazards are the **same single arm**:

```
safe_commit_cmd.py:306  (try at :300)
  except (FileNotFoundError, ValueError):
  in      : specify_cli.cli.commands.safe_commit_cmd._resolve_mission_aware_target
  catches : ['FileNotFoundError', 'ValueError']  (no RuntimeError -> strands MissionMetaReadError)
  guards  : mission_runtime.resolution.resolve_placement_only
```

**It is a true positive, and it is pre-existing — measured, not argued.** `resolve_placement_only`
really does leak `MissionMetaReadError` on malformed meta (12-case probe over 4 artifact kinds ×
3 shapes: malformed leaks at all four kinds; absent and valid return `CommitTarget`). Attribution
across three trees, same probe:

| Tree | malformed | absent | valid |
|---|---|---|---|
| baseline `96494e5ec` | **LEAKED** | OK | OK |
| commit 0 `45b278823` (pre-routing) | **LEAKED** | OK | OK |
| HEAD (post commit 2) | **LEAKED** | OK | OK |

Byte-identical at all three ⇒ **my routing did not cause it**, and it already leaked before the
lane's first routing commit. Origin traced:

```
resolution.py:1490 in resolve_placement_only
paths.py:781       in get_feature_target_branch
paths.py:720       in read_target_branch_from_meta
paths.py:694       in load_meta_fail_closed
```

That is **F1's site A reached via a third, previously unrecorded caller**
(`get_feature_target_branch` ← `resolve_placement_only`). Ledgered as F11 (§14).

### The `contextlib.suppress` blind spot — closed with a calibrated probe

The sweep inspects only `ast.Try`; `with contextlib.suppress(ValueError, OSError):` is the same arm
and is invisible to it. Reusing WP03's approach, I wrote a probe importing the sweep's own
`CallGraph`, `STRANDABLE` and `ABSORBING` vocabulary — so both agree on "stranded" — seeded with my
four routed functions, and **calibrated against WP03's recorded known answer before reporting**
(it exits 2 and refuses if the control does not reproduce):

```
  CONTROL total: expected 48, got 48 -> PASS
  modules parsed   : 1199
  functions indexed: 9831
  seeds            : 4
  transitive callers reaching any seed (incl. seeds): 242
  suppress() arms inspected ON-CHAIN: 20
  CONTROL on-chain: expected 0, got 0 -> PASS

VERDICT: CLEAN
```

**20 suppress arms sit on the four routed chains; none of them strands `MissionMetaReadError`.**

> **Correction to my own first draft of this evidence.** An earlier version of this section asserted
> that a plain `grep -rn 'contextlib.suppress' src/` "finds no suppress arm on any of the four
> routed chains". That claim was **never measured** and was wrong in two ways: the bare grep returns
> **154** matches (not zero), and grep cannot answer the on-chain question at all. The calibrated
> probe above is the real evidence. Recorded rather than quietly replaced, since this mission has
> produced repeated wrong citations *and* wrong corrections.

---

## 13. F1 — outcome: **intended, and now pinned** (not fixed)

Re-derived independently by instrumented traceback on a real corrupt-meta fixture. Exactly **one
escaping raise per command** (the other two raises per run are absorbed inside
`lifecycle_phase.py:142 _read_baseline_merge_commit`, which prints
*"lifecycle phase probe: unreadable meta.json … treating baseline_merge_commit as absent"*):

```
check-prerequisites  (3 raises, 1 escapes)
  paths.py:678(load_meta_fail_closed) <- paths.py:704(read_target_branch_from_meta)
    <- mission_branch_context.py:66(_resolve_feature_target_branch)
    <- mission_check_prerequisites.py:257(check_prerequisites)      <-- ABSENT ARM

finalize-tasks       (3 raises, 1 escapes)
  paths.py:678(load_meta_fail_closed) <- gate.py:80(ensure_occurrence_classification_ready)
    <- mission_finalize.py:543(_validate_occurrence_map_ready)
    <- mission_finalize.py:1729(finalize_tasks)                     <-- ABSENT ARM
```

Confirmed **absent**, not stranded: `check-prerequisites`' *first* read is guarded at `:245` by
`except (MissionMetaReadError, ValueError, ActionContextError)` (WP02's widening); the escaping read
at `:257` sits **after** that block, outside any `try`.

**Decision: the fail-closed refusal at both sites is INTENDED. I did not add an absorbing arm.**
Evidence:

1. **The authority mandates the absent arm.** `read_target_branch_from_meta`'s own docstring
   (`core/paths.py`, `Raises:`) reads: *"Callers MUST NOT silently swallow this — the error must
   propagate so corruption is visible (fail-closed doctrine)."*
2. **This mission did not cause it.** `read_target_branch_from_meta`'s body is byte-identical
   `data = load_meta_fail_closed(feature_dir)` at `96494e5ec` **and** at `upstream/main` tip `98198e980` —
   never routed by this mission; fail-closed since #2139. For the gate,
   `ensure_occurrence_classification_ready` was `meta = load_meta(feature_dir)` with **no arm** at
   baseline, raising a bare `ValueError` that was **equally unabsorbed** and landed in the *same*
   top-level `except Exception`. WP02's routing changed only the exception **type**, not whether an
   arm exists — so `C-001` is not violated: there was never an arm here to change.
3. **Absorbing would be strictly worse.** At `_resolve_feature_target_branch` the fallback is
   `get_current_branch(repo_root) or "main"` — an arm there would make `check-prerequisites` report
   a **wrong `target_branch`** on a corrupt file, silently. At the gate, the `meta is None` branch
   returns `GateResult(passed=True)`, so an arm would make the bulk-edit occurrence gate report
   **passed** for a mission whose `change_mode` could not be read — a **fail-open on a guardrail**.
4. **The payload is not a raw crash.** Both commands exit `1` with structured JSON naming the
   corrupt file and saying `— fail-closed`. What it lacks is `error_code` / `mission_flag` /
   `available_missions` — *mission-detection* keys, meaningful for "could not tell which mission you
   meant", not for "found your mission, its meta.json is corrupt". Calling this "degraded" conflates
   two different failures. **I record this as a correction to F1's wording**, while accepting F1's
   underlying observation as accurate.

**The tested decision** — `tests/mission_runtime/test_wp04_f1_absent_arm_is_intended.py`, 4 tests:
each site must **raise** on corruption, plus a positive control per site that the *absent* and
*valid* arms still behave (branch string still resolved; gate still passes). Proved load-bearing:
adding the rejected absorbing arm makes it fail `DID NOT RAISE` while all 3 controls stay green.
So a future editor cannot quietly introduce the silent-wrong-value behaviour.

---

## 14. Cone, gates, and quality

**Cone** — `tests/mission_runtime`, `tests/upgrade`, ledger test. **No `tests/sync`, no
`tests/cli`** (verified: 0 matches in the run log).

```
916 passed in 84.63s        exit 0
grep -c '^ERROR tests/'  →  0
grep -c '^FAILED'        →  0
```

**Gate coverage of the 5 new test files — verified with `_gate_coverage.py` and the gates' own
marker expressions, not by grepping the workflow.** CI selects by **marker**; all five files carry
module-level `pytestmark = [pytest.mark.integration, pytest.mark.git_repo]` (module-level per
sibling commit `f5972099e`). Collected under each gate's real expression:

```
misc shard   -m "not windows_ci and (git_repo or integration or architectural) and not timing and not regression"
  4  tests/mission_runtime/test_wp04_degrade_site_fallbacks.py
  4  tests/mission_runtime/test_wp04_f1_absent_arm_is_intended.py
  5  tests/mission_runtime/test_wp04_routed_call_counts.py
  8  tests/mission_runtime/test_wp04_sc007_guard_and_handler_contract.py
upgrade gate -m "not windows_ci and (git_repo or integration)"
  2  tests/upgrade/test_wp04_row13_load_feature_meta_fallback.py
```

23 tests, all gate-selected. `_gate_coverage_baseline.json` was **not** regenerated (F10 is WP08's).

**`ruff check`** over all 9 changed files → `All checks passed!`. **`ruff format` was never run.**

**`mypy --strict`** — clean on all files I authored. Three `no-any-return` remain in files I
touched, **all confirmed pre-existing at `96494e5ec`** and left unfixed and unsuppressed:

| Live | Baseline | Note |
|---|---|---|
| `core/paths.py:278` | `core/paths.py:278` | identical |
| `core/paths.py:692` | `core/paths.py:676` | same line, shifted by my 16-line docstring growth |
| `feature_meta.py:52` | `feature_meta.py:42` | same line, shifted by my docstring growth |

All three are the same root cause — `follow_imports = "skip"` for `specify_cli.*`
(`pyproject.toml:299`) erasing return types across the package boundary. Not fixed: `core/paths.py`
must stay **docstring-only** for WP05, and fixing one file of a repo-wide typing-config artefact is
the whack-a-field pattern (`DIR-024`). Ledgered as F12. **Note these three are *not* in the
briefing's known-pre-existing list** (`merge_driver.py:645`, 10 under `cli/commands/agent/`, 2 in
`decisions/service.py`) — recorded as an addition to that set.

**`#2804` / `SC-008`** — untouched, as instructed:

```
$ git diff 96494e5ec..HEAD --stat -- tests/specify_cli/cli/commands/test_row_aware_merge_driver.py
(no output — byte-identical)
$ find tests -name test_row_aware_merge_driver.py
tests/specify_cli/cli/commands/test_row_aware_merge_driver.py     # exactly one, the real path
```

Re-capture of WP07's marker evidence belongs to WP08 and was **not** attempted here.

---

## 15. `SC-009` residue row for `NFR-001` — and `Q4`

**Filed in `residual-ledger.md`, not as a tracker issue.** Operator direction for this mission is
explicit: *"Do not run `gh issue create` for anything."* This **consciously overrides charter
`DIR-013`**, which would otherwise require a GitHub issue. So T026 step 6's `gh issue view <n>`
verification is **not applicable** and no issue number exists — recorded rather than faked.

**The residue.** The four degrade sites remain **knowingly indistinguishable** under `D4=(a)`:
`""`, `None`, `legacy-<slug>` and `None` are each values a **valid** `meta.json` also yields. The
probe demonstrates it directly — `_mid8_from_primary_meta` returns `''` for both malformed and
absent input, and a valid file lacking `mid8`/`mission_id` would return `''` too. So a caller cannot
distinguish "corrupt" from "absent" from "validly empty" at any of the four.

`Q4` — *should a degrade site log when it degrades?* — is named as the candidate remedy. **`Q4` is
an operator question and is NOT decided here** (`plan.md:783-785`). Nothing in this WP logs, and
nothing in this WP forecloses either answer.

---

## 16. Anything unverified

- **`[UNVERIFIED]`** Whether the F11 hazard (`safe_commit_cmd.py:306`) causes an operator-visible
  misbehaviour in a real `safe-commit` invocation. I proved the leak reaches that arm and that the
  arm does not absorb it, both by static sweep and by direct call to `resolve_placement_only`; I did
  **not** drive `safe-commit` end-to-end to observe the resulting operator-facing behaviour. It is
  pre-existing either way, so this does not gate WP04.
- **`[UNVERIFIED]`** Whether the three pre-existing `no-any-return` findings would disappear under a
  `follow_imports` setting other than `skip`. Not tested; changing that config is far outside scope.
- The full repository suite was **not** run (`tests/sync` and `tests/cli` are barred and other
  agents are live). Only the declared cone plus the architectural gate scripts were executed.
