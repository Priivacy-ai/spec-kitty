---
work_package_id: WP04
title: Route the 4 degrade sites and change their 4 handlers — fallback pin, then routing, then handlers (three commits, one WP)
dependencies:
- WP01
- WP03
requirement_refs:
- FR-002
- FR-012
- FR-014
- NFR-003
- C-001
- C-002
- C-008
planning_base_branch: feat/meta-fail-closed-3162
merge_target_branch: feat/meta-fail-closed-3162
branch_strategy: Planning artifacts for this mission were generated on feat/meta-fail-closed-3162. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/meta-fail-closed-3162 unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
- T026
history: []
agent_profile: python-pedro
authoritative_surface: src/
create_intent: []
execution_mode: code_change
owned_files:
- src/mission_runtime/resolution.py
- src/specify_cli/upgrade/feature_meta.py
- src/specify_cli/core/paths.py
- tests/specify_cli/test_meta_fail_closed_full_census_contract.py
- tests/mission_runtime/**
- tests/upgrade/**
role: implementer
tags: []
tracker_refs: []
---

# WP04 — Route the 4 degrade sites and change their 4 handlers

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Route census rows **1, 2, 3, 13** onto `load_meta_fail_closed` and change the four `except ValueError`
handlers that guard them, **in that order, as three commits inside this one work package** — a commit 0 that
pins the four malformed-input fallbacks (green at baseline), commit 1 routing (those four go **red**), commit 2
handlers (green again) — while the observable fallback at each of the four sites stays **byte-identical** across
malformed, absent and valid input. Amend `load_meta_fail_closed`'s docstring in the routing commit (`FR-012` / operator ruling R-2) so
the canonical authority stops documenting a client contract its own client set now contradicts.

## Where this WP runs, how to start it, and where its evidence lands

**This WP runs from the repository root.** Every path below is repo-relative from the tree you are in. Start
with `spec-kitty implement WP04` — `spec-kitty agent action implement WP04 --agent <name>` does **not** resolve
a workspace, its `--help` reads *"Display work package prompt with implementation instructions."*, and
`CLAUDE.md` § Execution Workspace Strategy is explicit that *"`spec-kitty implement WP##` is the only supported
way to prepare a workspace."*

**`PYTHONPATH=<workspace>/src` on every `python -c` and every `pytest` that could run outside the repository
root — this WP touches three trees and is the most exposed in the mission** (T020 creates a `96494e5ec`
worktree; T021 captures `pre.txt` there; T024 captures a green there). The hazard is a *silently wrong* answer,
not an error: `.venv/lib/python3.11/site-packages/_editable_impl_spec_kitty_cli.pth` pins `specify_cli` /
`runtime` imports to the **main** tree's `src/`, while `SRC_ROOT` in the gate
(`tests/architectural/test_inline_meta_read_gate.py:61`) and `_SRC_ROOT` in the ledger test
(`tests/specify_cli/test_meta_fail_closed_full_census_contract.py:54`) derive from **the test file's own
location**. Without `PYTHONPATH` the AST census reads the *edited* `src/` while behavioural assertions import
the *unedited* one — the call-count assertion goes green while its traceback twin stays red, with no diagnosable
cause; and a `pre.txt` captured that way is a **branch** capture wearing the baseline's name, so T025's empty
`diff` is empty for the wrong reason. Nothing provisions `.venv` into a git worktree (`.gitignore:31-32`), so
invoke `.venv/bin/python` by absolute path from a worktree, with `PYTHONPATH` set, and say which tree each
number came from.

**Committed evidence destination.** `mark-status` exposes only `--status`, `--mission`, `--auto-commit`,
`--json`; its payload is `WPInnerStateDelta.subtasks: Mapping[str, Status]`
(`src/specify_cli/status/models.py:481`) — a bare `{T0xx: Status}`, **no evidence field**. This WP's committed
destination is `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP04-evidence.md`, a declared **out-of-map**
planning write with a one-line rationale (`kitty-specs/` paths cannot appear in `owned_files` by construction —
`mission_parsing.py:153-157`, `:207-215`). The 12 probe lines per side, both `wc -l` values, the red traceback
with its SHA, the docstring pre/post pair, the `git log` ordering, the `C901` table and the `gh issue view`
output go **into that file**; `pre.txt`/`post.txt` are scratch files quoted into it. Nothing load-bearing is
left in `/tmp`.

## Context

This is the mission's **sharpest risk**, and `plan.md` says so in as many words (`### IC-04`, "the sharpest
in the mission"). The reason is a type mismatch:

`MissionMetaReadError` is a **`RuntimeError`**, not a `ValueError`
(`src/specify_cli/core/paths.py:506`, `class MissionMetaReadError(RuntimeError)`). All four sites currently
catch a raw `ValueError` from `mission_metadata.load_meta` and fall back to a sentinel. Routing a site
**without** changing its handler therefore does not preserve the degrade — it converts a **silent fallback
into a crash**, and three of the four are on live mission-resolution paths reached from
`merge/executor.py:116`'s import of `resolve_placement_only`.

### The four sites and their four handlers

| Row | Read expression | Function (symbol) | Handler | Fallback | Derived or constant? |
|---|---|---|---|---|---|
| 1 | `src/mission_runtime/resolution.py:509-513` | `_mid8_from_primary_meta` | `:514` | `return ""` | **constant** |
| 2 | `src/mission_runtime/resolution.py:852` | `_resolve_coordination_branch` | `:853` | `return None` | **constant** |
| 3 | `src/mission_runtime/resolution.py:1107` | `_resolve_mission_id` | `:1108` | `f"legacy-{mission_slug}"` (`:1114`) | **constant w.r.t. the file** — derived from the caller's `mission_slug` **argument**, never from `meta.json` |
| 13 | `src/specify_cli/upgrade/feature_meta.py:42` | `load_feature_meta` | `:43` | `return None` | **constant** |

Cite every site by **`file:line` and symbol** (`C-003`); five commits move lines in this lane.

### The one deliberate non-atomicity in the whole mission — three commits, and the red is real

Unlike WP03, this work package lands as **three commits**, in this order:

0. **Commit 0 — the four malformed-input fallback tests, and nothing else.** One per degrade site: malformed
   `meta.json` → that site's own sentinel (`""`, `None`, `legacy-<slug>`, `None`), through the site's own entry
   point with a real corrupt file on disk. **Green at baseline** (the degrade already works — `NFR-003`), so this
   is a behaviour pin, **not** a red-first commit.
1. **Commit 1 — routing only** — the four call sites, the `core/paths.py` docstring amendment, the four
   ledger-row deletions, and the four call-count assertions. **The four commit-0 tests go RED here**, and their
   traceback showing `MissionMetaReadError` escaping `except ValueError` is `FR-002`'s red. Quote it with the SHA.
2. **Commit 2 — handlers only** — the four `except` clauses gain `MissionMetaReadError`; the four commit-0 tests
   are **green again** on the same selection.

**Why commit 0 exists — the previous two-commit shape had an unachievable red.** The only tests that can
produce the escaping `MissionMetaReadError` are those four malformed-input fallback tests, and in the earlier
shape they were written in T024, *after* commit 2. So at commit 1 the cone ran **green**: measured, no
pre-existing test in `tests/mission_runtime` or `tests/upgrade` drives these four sites with corrupt JSON, and
the absent/valid paths are unchanged (`allow_missing=True` hard-coded, `src/specify_cli/core/paths.py:676`). The
only way to tick the box was a hand-rolled scratch traceback — i.e. `FR-002`'s red **never entering the
repository**, and that red is the entire basis on which the charter ATDD exception was granted.

Commit 0 buys a **real green→red→green sandwich, checkable by re-checkout**: the four node ids run green at
commit 0, red at commit 1 (`MissionMetaReadError` escaping `except ValueError`), green at commit 2. **Do not
quote a red from a cone that runs green at commit 1** — if your commit-1 red is not those four tests failing,
you have not produced `FR-002`'s red.

**This is also the single case in the mission where `C-002`'s "same edit" must be read as "same work package"
rather than "same commit".** Say so in your evidence, out loud. As written, `C-002` ("all SIX handlers change in
the same edit as their routing") and `FR-002` ("land the routing first and quote the resulting escape as the
red") **contradict each other**, and an implementer without this paragraph picks one silently — most likely
`C-002`, destroying the only red the requirement has. `plan.md`'s **atomicity coupling 5** is the ruling:
**commit granularity for rows 9 and 12 (WP03), work-package granularity for rows 1, 2, 3 and 13 (here).
Nowhere else.**

### What the red is *not*

`NFR-003` requires the degrade behaviour be **identical** pre and post, so **no test can be red on this WP's
`planning_base_branch` for `FR-002`** — a base-red would pin a behaviour change `D4=(a)` forbids. That is
exactly why commit 0's four tests are **green at baseline**: they pin the behaviour `NFR-003` protects. The red
is on an **intermediate commit** (commit 1). That is a **documented charter exception** (`plan.md` Charter Check
ATDD-first row: "IC-04's red is on an **intermediate commit** … a base-red is **impossible by construction**";
Complexity Tracking row 1, five reviewer-verification steps). With commit 0 in place it is **checkable** rather
than asserted, and must not be reported as an omission.

### The budget is closed by assertion, not by narration — one call-count assertion per routed site

**Commit 1 must carry a per-site structural call-count assertion for each of the four sites**, in the shape
WP02 T011 uses for `read_primary_meta`: `ast`-parse the module and assert the routed function's **own body**
holds **exactly one** `load_meta_fail_closed(` call and **zero** `load_meta(` calls — exact callee name, not a
substring (`load_meta_fail_closed(` contains `load_meta(`). Name the module in each message: `_resolve_mission_id`
is defined in four modules here, two of them this mission's own sites with **opposite arms** (row 3 degrade
here, row 9 refuse-typed in WP03).

This WP is **0-net** on the routed count — WP05 is the mission's single allocator (`129 → 130`) — so **print
the routed count pre and post your own edits; both must read `129`**, band **`[127, 130]`**, **126 is RED**, the
constraint **two-sided**. But the printed pair is only a check; the four assertions are what **close** it. A
fold reads **128**, and `128 >= 126`, `128 > 126`, `128 - 126 = 2 <= 4` — **all three clauses of
`test_routed_load_meta_floor` (`tests/architectural/test_inline_meta_read_gate.py:1084`) are green**; after WP06
sets the floor to 127 the merged tree's folded **129** is green too. A fold survives both gates, caught only by a
printed number a human has to compare, and lanes B and C are concurrent and file-disjoint so no file-overlap
check can see the coupling.

### `resolution.py:509` is different from the other three — do not narrow it

The `try` at `resolution.py:504` wraps **more than the read**: `_canonicalize_primary_read_handle` (`:507`)
and `_compose_primary_feature_dir` (`:505-508`) are **inside** it. Two consequences:

- `_compose_primary_feature_dir` really does raise the traversal `ValueError`
  (`missions/_read_path_resolver.py:1307` → `assert_safe_path_segment`, `core/paths.py:40`). `SC-007`
  requires traversal behaviour **unchanged**, so narrowing this handler to `MissionMetaReadError` alone is
  **forbidden**. Write the tuple: `except (ValueError, MissionMetaReadError):`. Note the trap — `SC-007`'s
  assertion is that tripping the guard **still returns `""`**, captured pre and post. A test that merely
  asserts `pytest.raises(ValueError)` is red at baseline and green after a narrowing, so it reports success
  **while deleting the very behaviour it exists to protect**.
- `MissionSelectorAmbiguous` is deliberately **not** a `ValueError`
  (`missions/_read_path_resolver.py:44`, `class MissionSelectorAmbiguous(Exception)`) and is raised by
  `_canonicalize_primary_read_handle` **inside** this same `try`. It must keep propagating. The in-code note at
  `resolution.py:496-498` states this (`:493-495` is the *separate* traversal-`ValueError` note — cite them
  separately); **require an assertion for it**, not a comment saying "the note still holds".

At `:853`, `:1108` and `feature_meta.py:43` the `try` holds **only** the read (`:851`/`:852`, `:1106`/`:1107`,
`:41`/`:42`), so `except MissionMetaReadError` alone is exact — verified: `_compose_primary_feature_dir` sits
**outside** the `try` at `:845-848` and `:1100-1103`. `upgrade/feature_meta.py:33-45` is a pure absorb-adapter
whose docstring says its purpose is converting `ValueError` to `None`; its `load_meta(feature_dir)` already takes
the canonical defaults (`allow_missing=True, on_malformed="raise"`, `mission_metadata.py:280-285`), so
`load_meta_fail_closed(feature_dir)` is an exact 1:1 swap including the absent-file arm.
**Never `except Exception`** at any of the six handlers (`C-002`, `SC-007` third assertion).

### `FR-012` — the docstring amendment, operator ruling R-2

`load_meta_fail_closed`'s docstring at `core/paths.py:648-651` currently reads:

> *"Callers that must stay deliberately silent about corruption (placement probes, best-effort displays)
> keep using `load_meta_or_empty` or the canonical reader's `on_malformed="none"` arm instead -- they are
> not routed here."*

All four degrade sites **are that class by outcome**. The operator chose to route them anyway **and amend the
docstring in the same commit as the routing** (`SC-014`), so the canonical authority stops documenting a client
contract its own client set contradicts. **The edit is docstring-only** — see T025 step 4a; concurrent WP05
depends on the signature, the exception class and the return contract.

Note also: the same docstring calls itself *"the ONE public reader (FR-007)"* (`core/paths.py:639`) and repeats
`FR-007 / #3140` at `:643`. That `FR-007` is a **foreign** requirement ID that **collides with this spec's own
`FR-007`**. **Qualify the foreign ID while editing** (`DIR-032`, e.g. `#3140#FR-007`).

### `SC-002` — the probe, and the cheat it closed

`NFR-003` requires **all three input shapes** — malformed, **absent**, and valid — at each of the 4 sites:
**4 × 3 = 12 captured lines** per run, **with the input count printed**. A malformed-only probe satisfies the
criterion's *shape* while the absent-file arm regresses untouched — precisely the defect `NFR-003` was rewritten
to catch. The probe runs **twice** (baseline worktree at `96494e5ec`, then branch head) and needs a **positive
control** quoted **first**: break one handler, show the `diff` **non-empty**. A same-run double-print, or an
empty diff over two empty captures, is not evidence.

---

### Subtask T020 — Baseline: routed count PRE, and the `96494e5ec` worktree

**Purpose**: establish the two measurements every later subtask compares against, and stand up the baseline tree the `SC-002` `pre` capture runs in (previously unowned per `plan.md`).

**Steps**

1. Read WP01's `contracts/headroom-allocation.md` and `contracts/routing-manifest.md`. Use **WP01's recorded
   measurement command verbatim** — do not invent a second way to count, or you author a second predicate
   answering the same question (`NFR-002`).
2. Print the live routed count **PRE** with its **input file count**. Expect **129**.
3. Print the band derivation from the three assertions of `test_routed_load_meta_floor`
   (`tests/architectural/test_inline_meta_read_gate.py:1084-1105`) — `>= FLOOR`, `> FLOOR`, `- FLOOR <=
   MARGIN`, with `ROUTED_LOAD_META_FLOOR = 126` and `ROUTED_LOAD_META_FLOOR_MARGIN = 4` (`:220-221`).
   Restate: admissible `[127, 130]`, **126 is RED**.
4. Create the baseline worktree: `git worktree add <scratch>/base-96494e5ec 96494e5ec`. Confirm it is the
   measurement baseline `plan.md:21-23` names (`git diff --name-only 96494e5ec HEAD | grep -v '^kitty-'`
   → **0** files).
5. Record `ruff check --select C901` **PRE**, per touched file:
   `src/mission_runtime/resolution.py`, `src/specify_cli/upgrade/feature_meta.py`,
   `src/specify_cli/core/paths.py`. The ceiling is **15** and handler edits must **not** grow these
   functions (`plan.md` Complexity ceiling register names `_mid8_from_primary_meta` explicitly).

**Files**: read-only this subtask; scratch worktree outside the repo tree.

**Validation**: routed PRE printed as **129** with its input count; band printed; worktree resolves at
`96494e5ec`; three `C901` PRE outputs quoted.

---

### Subtask T021 — COMMIT 0: the four malformed-input fallback tests (green at baseline), then build the `SC-002` probe and capture `pre.txt`

**Purpose**: two things, in this order. First **land commit 0** — the four tests that make `FR-002`'s red a
real, re-checkoutable red instead of a hand-rolled traceback. Then prove `NFR-003` with a probe harness that
**cannot** be satisfied by malformed input alone.

**Steps — part A: COMMIT 0, the four fallback tests**

A1. Write **one test per degrade site**, four in total, under `tests/mission_runtime/**` (rows 1, 2, 3) and
    `tests/upgrade/**` (row 13). Each drives a **real corrupt `meta.json` on disk** through the site's own entry
    point — no patching of `load_meta` or `load_meta_fail_closed` — and asserts the site returns **its own
    sentinel**: row 1 `_mid8_from_primary_meta` → `== ""`; row 2 `_resolve_coordination_branch` → `is None`;
    row 3 `_resolve_mission_id` → `== f"legacy-{mission_slug}"`; row 13 `load_feature_meta` → `is None`.
A2. **These four are GREEN at baseline** — the degrade already works, which is what `NFR-003` asserts. Run them
    on `planning_base_branch` **and** in the `96494e5ec` worktree (with `PYTHONPATH=<scratch>/base-96494e5ec/src`)
    and quote both greens. Commit 0 is **not** a red-first commit; it is a behaviour pin, and `NFR-003` forbids a
    base-red here.
A3. Put the sandwich in each test's docstring so a future editor cannot "simplify" it away: *green at baseline;
    **RED on commit 1** (`MissionMetaReadError` — a `RuntimeError`, `core/paths.py:506` — escapes the site's
    `except ValueError`); green on commit 2.* State that this is what makes the charter ATDD exception
    **checkable by re-checkout**, since `NFR-003` makes a base-red impossible.
A4. Commit the four tests **alone** — no `src/` change, no ledger change — and **quote the SHA** plus
    `git show --stat <sha>` showing only `tests/mission_runtime/` and `tests/upgrade/` files. This is commit 0.
A5. Record the four node ids. T022 quotes their red, T023 their green, T026 re-runs all three states from those
    exact ids.

**Steps — part B: the `SC-002` probe**

1. Write the probe as a standalone script under your scratch directory (not under `src/`, not under
   `tests/architectural/` — a read committed under `src/` raises the inline census and reds a floor it has
   nothing to do with).
2. Enumerate **12 cases**: the 4 sites × 3 input shapes.
   - shapes: **malformed** (`{` — invalid JSON), **absent** (no `meta.json` at all), **valid** (a
     well-formed object with `mission_id` / `coordination_branch` present).
   - sites: `_mid8_from_primary_meta`, `_resolve_coordination_branch`, `_resolve_mission_id`,
     `load_feature_meta`.
3. Print **one line per case** — `site|shape|repr(result)` — plus a final line printing the **input count**
   (`12`). A capture of fewer than 12 lines **fails `SC-002` regardless of what its `diff` says**.
4. Record per site whether the fallback is **derived** or **constant** (see the Context table). All four are
   **constant**; row 3's `legacy-<slug>` is derived from the caller's `mission_slug` argument at
   `resolution.py:1114`, **not** from the file — so no site can emit a plausible-but-wrong value read out
   of a corrupt file. State this finding; `wps.yaml`'s T021 text asserts the opposite (see Reviewer
   Guidance).
5. **Positive control, run FIRST and quoted first**: deliberately break one handler (e.g. narrow
   `:1108` to `except TypeError`), run the probe, `diff` against the baseline capture, show it
   **non-empty**, quote it, then revert. This is what distinguishes a working probe from a probe that
   prints nothing.
6. Capture `pre.txt` by running the probe with `PYTHONPATH=<scratch>/base-96494e5ec/src`. Quote the
   `PYTHONPATH` you used alongside the capture — without it the editable `.pth` imports the **branch** tree's
   `src/` and `pre.txt` is a branch capture wearing the baseline's name, which makes T025's empty `diff` empty
   for the wrong reason. Quote `wc -l pre.txt` — must be non-zero and account for 12 case lines.

**Files**: four new tests under `tests/mission_runtime/**` and `tests/upgrade/**` (commit 0); scratch probe
script; `pre.txt` in scratch. **No `src/` change and no ledger change in this subtask.**

**Validation**: commit 0's SHA quoted with `git show --stat` showing tests only; the four tests quoted **green
at baseline** (both on `planning_base_branch` and in the `96494e5ec` worktree with `PYTHONPATH`); the four node
ids recorded; the green→red→green sandwich written into each test's docstring; positive control `diff` non-empty
and quoted; `pre.txt` at 12 case lines with the input count printed and the `PYTHONPATH` quoted;
`wc -l pre.txt` quoted non-zero.

---

### Subtask T022 — COMMIT 1: routing only + docstring + 4 ledger rows. Quote the RED from commit 0's four tests.

**Purpose**: land the routing and **quote the escaping `MissionMetaReadError` as the red** — as a failure of
the four tests committed in T021 part A, at four recorded node ids. This is `FR-002`'s red-first device and the
only red the requirement has.

**Steps**

1. Route the four reads to `load_meta_fail_closed`, importing from `specify_cli.core.paths`:
   - `resolution.py:509-513` (`_mid8_from_primary_meta`) → `load_meta_fail_closed(primary_dir)`
   - `resolution.py:852` (`_resolve_coordination_branch`) → `load_meta_fail_closed(primary_dir)`
   - `resolution.py:1107` (`_resolve_mission_id`) → `load_meta_fail_closed(primary_dir)`
   - `upgrade/feature_meta.py:42` (`load_feature_meta`) → `load_meta_fail_closed(feature_dir)`
   **Do not touch any `except` clause in this commit.** Update the stale in-code comments that describe the
   old `ValueError` contract (`resolution.py:490-498`, `:849-850`, `:1104-1105`) to describe the seam. Two
   distinct notes live inside that block and they are **not** the same fact — verified by opening the file:
   - **`:493-495`** is the **traversal-`ValueError`** note (*"That `except` is BROADER than the reader contract
     alone: it also swallows the path-traversal-guard `ValueError` (`assert_safe_path_segment`) raised inside
     `_compose_primary_feature_dir` below, degrading an unsafe segment to `""` the same way a malformed
     meta.json does"*). This stays true and is why T023 writes a **tuple**, not a narrowing.
   - **`:496-498`** is the **`MissionSelectorAmbiguous`** note (*"`MissionSelectorAmbiguous` (raised by
     `_canonicalize_primary_read_handle`) is NOT a `ValueError` and correctly still propagates uncaught"*).
     This also stays true and is what T024 assertion (b) pins.
   Keep both. Cite them **separately** — an earlier draft cited `:493-498` for the `MissionSelectorAmbiguous`
   note alone, which silently folded two different facts into one range.
2. **Add the four call-count assertions** (§ The budget is closed by assertion), in **this** commit:
   `ast`-parse each module and assert the routed function's **own body** holds **exactly one**
   `load_meta_fail_closed(` call and **zero** `load_meta(` calls, matched on the exact callee name — for
   `_mid8_from_primary_meta`, `_resolve_coordination_branch` and `_resolve_mission_id` in
   `src/mission_runtime/resolution.py`, and `load_feature_meta` in `src/specify_cli/upgrade/feature_meta.py`.
   Name the module in each message: `_resolve_mission_id` is defined in four modules on this tree.
3. **Same commit** — amend `core/paths.py:648-651` per `FR-012`/R-2: the amended text **names the routed
   degrade callers as clients and states which arm they keep** (malformed → each site's own sentinel, via
   the caller's `except`). While there, qualify the foreign `FR-007` at `:639` and `:643` (`DIR-032`).
   **The edit is docstring-only.** Do not change `load_meta_fail_closed`'s signature, its return contract, or
   `MissionMetaReadError`'s class or bases — concurrent WP05 depends on that contract and this WP owns
   `core/paths.py` whole-file for four lines of prose. T025 proves it.
4. **Same commit** — delete the four `_ACCOUNTED_SITES` rows in
   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`. **Match by content, never by line
   number** — five commits mutate this file in sequence. The four keys, **written out in full** — copy these
   verbatim; an ellipsis in a grep pattern matches nothing, exits `1`, prints nothing, and reads exactly like
   *"already deleted"*:
   ```
   ("src/mission_runtime/resolution.py", "_mid8_from_primary_meta")
   ("src/mission_runtime/resolution.py", "_resolve_coordination_branch")
   ("src/mission_runtime/resolution.py", "_resolve_mission_id")
   ("src/specify_cli/upgrade/feature_meta.py", "load_feature_meta")
   ```
   **Always include the module path.** `grep -n '"_resolve_mission_id"'` over that file matches **two** rows:
   `("src/mission_runtime/resolution.py", "_resolve_mission_id")` (this WP's row 3, **degrade**) and
   `("src/specify_cli/decisions/service.py", "_resolve_mission_id")` (WP03's row 9, **refuse-typed** — the
   opposite arm). The second is already gone today only because `dependencies: [WP01, WP03]` puts WP03 ahead of
   you; a symbol-only grep is one dependency-order change away from deleting the wrong row. WP02 and WP03 write
   their keys with the path; do the same. (Currently `:198`, `:199`, `:200`, `:249` — an at-this-moment
   observation, not a match key.) Coupling 2: the gate is an **exact equality in both directions**, so the
   deletion rides in the routing commit or the tree is red one way or the other.
5. **Capture the RED on the commit, from commit 0's four node ids.** Run the four node ids recorded in T021
   part A step A5, plus the cone (`tests/mission_runtime`, `tests/upgrade`), redirected. **All four must fail**,
   and the quoted traceback must show `MissionMetaReadError` escaping `except ValueError` at the site. Then
   commit and **quote the SHA** alongside that red.
   **If any of the four is green here, stop.** A green cone at commit 1 means the routing did not reach that
   site, or the test does not drive it with a real corrupt file — it does **not** mean the red is unavailable.
   Do not substitute a hand-rolled scratch traceback: `FR-002`'s red must exist in the repository at a named
   SHA and named node ids, or the charter ATDD exception is undocumented.
6. Run the ledger test itself green: `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`.

**Files**: `src/mission_runtime/resolution.py`, `src/specify_cli/upgrade/feature_meta.py`,
`src/specify_cli/core/paths.py`, `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`, plus the
call-count assertions under `tests/mission_runtime/**` and `tests/upgrade/**`.

**Validation**: commit SHA quoted **with** the escaping-`MissionMetaReadError` traceback as its red, **and the
four failing node ids named** (`4 failed` quoted from a redirected run, not a summary);
`git show --stat <sha>` contains **both** `core/paths.py` and the routed site files; the four ledger rows
gone, each matched by its **full `(path, symbol)` key**; ledger test green; **no `except` clause changed in this
commit** (`git show <sha> | grep '^[-+].*except'` → nothing but the deleted-row noise, quoted); the four
call-count assertions present, each asserting **1** and **0**.

---

### Subtask T023 — COMMIT 2: handlers only, green on the same selection

**Purpose**: restore the degrade at each site by widening its handler — and get `resolution.py:514` right, the one that is **extended, not narrowed**.

**Steps**

1. `src/mission_runtime/resolution.py:514` (`_mid8_from_primary_meta`) →
   `except (ValueError, MissionMetaReadError):`. **The tuple is mandatory.** Its `try` (`:504`) also wraps
   `_compose_primary_feature_dir` and `_canonicalize_primary_read_handle`, and the traversal guard
   (`_read_path_resolver.py:1307` → `core/paths.py:40` `assert_safe_path_segment`) raises a **real**
   `ValueError` that `SC-007` requires to keep degrading to `""`.
2. `resolution.py:853` (`_resolve_coordination_branch`) → `except MissionMetaReadError:`.
   `resolution.py:1108` (`_resolve_mission_id`) → `except MissionMetaReadError:`.
   `upgrade/feature_meta.py:43` (`load_feature_meta`) → `except MissionMetaReadError:`.
   At all three the `try` holds **only** the read, so the narrow catch is exact — verified:
   `_compose_primary_feature_dir` is outside the `try` at `:845-848` and `:1100-1103`.
3. **Never `except Exception`.** At `:514` a broadened catch would silently swallow
   `MissionSelectorAmbiguous` (`_read_path_resolver.py:44`, plain `Exception`, raised inside that `try`).
4. Update `upgrade/feature_meta.py`'s docstring (`:33-40`), which currently explains the adapter as
   "converts `ValueError` to `None`" — that sentence becomes false in this commit.
5. Run **the same four node ids** T022 quoted red, plus the same cone selection. All four must now be
   **green**. Quote **`N passed`** and the selected count from a redirected run. Commit; **quote the SHA**.
   That green→red→green triple across commit 0 / commit 1 / commit 2 — same node ids, same selection — is
   `FR-002`'s ATDD evidence, and it is re-checkoutable: a reviewer can reproduce all three states from the
   three SHAs.
6. `ruff check --select C901` **POST** on the three touched source files; compare with T020's PRE. Ceiling
   **15**; `_mid8_from_primary_meta` must not grow past it. `ruff check` only — **never `ruff format`**.

**Files**: `src/mission_runtime/resolution.py`, `src/specify_cli/upgrade/feature_meta.py`.

**Validation**: `except (ValueError, MissionMetaReadError)` present at `:514` and quoted; three narrow
catches quoted; `grep -n 'except Exception' ` over both files → 0, quoted with input count; commit SHA
green on T022's selection with `N passed` quoted **and the four node ids named**; the three states of the four
tests (commit 0 green / commit 1 red / commit 2 green) tabulated with their SHAs; `C901` PRE/POST both quoted
per file.

---

### Subtask T024 — `SC-007`'s three assertions

**Purpose**: pin the two behaviours inside `resolution.py:504`'s `try` that are **not** the `meta.json` read, plus the never-`except Exception` rule across all six handlers.

**Steps**

1. **(a) Traversal guard, asserting the OUTCOME.** New test under `tests/mission_runtime/`: call
   `_mid8_from_primary_meta` with a `mission_slug` that trips `assert_safe_path_segment`
   (`core/paths.py:40`) via `_compose_primary_feature_dir` → `_read_path_resolver.py:1307`, and assert
   **`result == ""`**. Capture it green **pre** (on the `96494e5ec` worktree) **and** post.
   **Do not write `pytest.raises(ValueError)`** — that form is red at baseline and green after a narrowing,
   so it reports `SC-007` met while the degrade-to-`""` behaviour is silently deleted. Put that reasoning
   in the test's docstring so a future editor cannot "simplify" it back.
2. **(b) Ambiguous handle still propagates.** New test asserting an ambiguous mission handle raises
   `MissionSelectorAmbiguous` **out of** `_mid8_from_primary_meta` — not swallowed, not converted.
   `MissionSelectorAmbiguous` is a plain `Exception` (`_read_path_resolver.py:44`) raised by
   `_canonicalize_primary_read_handle` inside the same `try`. This is an **assertion**, and the reviewer
   will reject a comment claiming `resolution.py:496-498`'s note "still holds".
3. **(c) No `except Exception` at any of the six `C-002` handlers.** Assert over **all six**, by symbol and
   file: `resolution.py:514`, `:853`, `:1108`; `decisions/service.py:141`;
   `missions/_resolve_planning_branch.py:122`; `upgrade/feature_meta.py:43`. Read-only over the two files
   this WP does not own — an AST or source assertion, no edits there.
4. The four fallback tests `plan.md`'s red-first register names for `FR-002` (one per site, malformed input →
   the site's own sentinel) are **already committed — they are commit 0, landed in T021 part A**. Do **not**
   write them here: at commit 1 the cone would then run green and `FR-002`'s red would never enter the
   repository. Instead, **re-run their four node ids at all three SHAs** and tabulate the result
   (commit 0 green / commit 1 red / commit 2 green), with `PYTHONPATH` named for any run outside the
   repository root. That table is the checkable form of the charter ATDD exception.
5. **Cone**: `tests/mission_runtime`, `tests/upgrade`, plus the ledger test. **Never** `tests/sync` or
   `tests/cli` — sibling missions may hold those windows (`C-007`). Redirect suite output to a file, quote
   `N passed` and the **selected count**.

**Files**: new/edited tests under `tests/mission_runtime/**` and `tests/upgrade/**`.

**Validation**: assertion (a) asserts `== ""` and is quoted green on baseline and head; (b) exists as an
assertion and cites `resolution.py:496-498` (the `MissionSelectorAmbiguous` note) — **not** `:493-498`, which
also covers the separate traversal-`ValueError` note at `:493-495`; (c) enumerates six handlers with the input
count printed; the commit-0 / commit-1 / commit-2 table for the four fallback node ids is present with all
three SHAs; cone `N passed` + selected count quoted; no `tests/sync` or `tests/cli` in any selection.

---

### Subtask T025 — Capture `post.txt`, empty `diff`, and `SC-014`

**Purpose**: close `NFR-003`/`SC-002` with the pre/post pair, and `FR-012`/`SC-014` with the docstring quote plus commit-shape proof.

**Steps**

1. Run the **same** probe at branch head → `post.txt`.
2. `diff pre.txt post.txt` → **empty**. Quote the diff invocation and its (empty) output, `wc -l` of
   **both** files (non-zero, 12 case lines each), and the printed input count on each side. An empty diff
   over two empty captures is **not** evidence — the `wc -l` pair is what rules that out.
3. `SC-014`: quote `core/paths.py:648-651` **pre** (from the baseline worktree) and **post**. The post text
   must no longer say the deliberately-silent class is "not routed here", and must name the routed degrade
   callers as clients with the arm they keep.
4. `SC-014` second half: `git show --stat <routing sha>` proving the routing commit contains **both**
   `src/specify_cli/core/paths.py` **and** the routed degrade site files. This is what makes the docstring
   amendment and the routing "one commit" (R-2) checkable rather than asserted.
4a. **Prove the `core/paths.py` change is docstring-only.** This WP holds `core/paths.py` **whole-file** for
    four lines of prose while **concurrent WP05 depends on its contract** (`load_meta_fail_closed` is the seam
    WP05 routes `ref_advance.py:247` onto; `MissionMetaReadError` is the type WP05 catches by name). Quote, from
    `git diff <base> -- src/specify_cli/core/paths.py`: (i) **every** changed line is inside a docstring or
    comment — no statement, `def` or `class` line; (ii) `load_meta_fail_closed`'s `def` line byte-identical pre
    and post; (iii) `class MissionMetaReadError(RuntimeError)` (`core/paths.py:506`) unchanged — no new
    exception class, no changed base; (iv) the return contract unchanged —
    `allow_missing=True, on_malformed="raise"` still hard-coded at `core/paths.py:676`, still `None` on absence,
    still `MissionMetaReadError` with `__cause__` on corruption. A signature, exception-class or return-contract
    change is out of scope and breaks WP05 across a lane boundary no file-overlap check inspects — this is the
    only file that couples them.
5. Re-quote the positive control from T021 **before** the empty diff, so the empty diff is read as a
   measurement and not as a broken harness.

**Files**: scratch `post.txt`; no repository file changes.

**Validation**: `diff` empty; both `wc -l` non-zero at 12 case lines; docstring pre/post quoted; routing
`git show --stat` shows `core/paths.py` **and** the site files; positive control quoted first.

---

### Subtask T026 — Closing evidence: ordering, 0-net budget, `SC-009` row

**Purpose**: supply the five reviewer-verification steps that **replace** the impossible base-red (`plan.md` Complexity Tracking row 1), close the budget, and file the residue honestly.

**Steps**

1. `git log --oneline` proving the order **commit 0 (fallback pin) → commit 1 (routing) → commit 2
   (handlers)** inside this work package, and that **all three survive in the lane's final history,
   unsquashed**. Squashing them destroys the only red `FR-002` has. Alongside it, tabulate the four fallback
   node ids at all three SHAs — **green / red / green** — which is the re-checkoutable form of the charter ATDD
   exception. Commit 0 must **not** be squashed into commit 1: without it, commit 1's cone runs green and there
   is no red in the repository at all.
2. Restate in the evidence, explicitly: `C-002`'s "same edit" reads as "same **work package**" here and
   **only** here (`plan.md` coupling 5); `FR-014`'s per-site atomicity is satisfied at
   work-package granularity for rows 1, 2, 3, 13 and at **commit** granularity nowhere in this WP.
3. Routed count **POST** — same command as T020, **delta 0**, both **129**, band `[127, 130]`, floor still
   126, **126 is RED**. WP05 owns the one net call; this WP spending it would break the merged tree in a
   way no single lane's own gate run can see.
4. `ruff check` and `mypy --strict` over the changed files → zero issues, quoted (`SC-017`). `ruff check`
   only; **never `ruff format`**.
5. `ruff check --select C901` PRE/POST table for the three touched source files, ceiling 15.
6. File the `SC-009` register row for `NFR-001`'s recorded residue: the 4 degrade sites remain **knowingly
   indistinguishable** under `D4=(a)` — `""`, `None`, `legacy-<slug>`, `None` are all values a **valid**
   file also yields. Name `Q4` (should a degrade site log when it degrades?) as the candidate remedy and
   state **explicitly that `Q4` is an operator question and is NOT decided here** (`plan.md:783-785`).
   Verify the filing with `gh issue view <n>` and quote it.
7. Append to the mission tracer files (tooling-friction, approach, design-decisions) per charter SO 3.

**Files**: evidence in the WP's status/report surface; no source changes.

**Validation**: `git log --oneline` quoted with **all three** SHAs in order; the four fallback node ids
tabulated green/red/green against those SHAs; routed PRE/POST both 129; `ruff`/`mypy` clean and quoted; `C901`
table complete; `gh issue view` quoted; `Q4` recorded as undecided.

---

## Definition of Done

- [ ] All four sites route through `load_meta_fail_closed`; **zero** `mission_metadata.load_meta` calls
      remain at rows 1, 2, 3, 13 (grep quoted with input count).
- [ ] **Three commits, in order** (fallback pin → routing → handlers), all unsquashed. Commit 0's four tests
      quoted **green at baseline**; routing SHA quoted **with those same four node ids failing** and the
      escaping-`MissionMetaReadError` traceback; handler SHA quoted **green on the same four ids and selection**.
      A commit-1 red that is not those four tests failing does not satisfy `FR-002`; a hand-rolled traceback
      satisfies nothing.
- [ ] **Four call-count assertions** in the routing commit: exactly **1** `load_meta_fail_closed(` and **0**
      `load_meta(` in each of `_mid8_from_primary_meta`, `_resolve_coordination_branch`, `_resolve_mission_id`
      (`src/mission_runtime/resolution.py`) and `load_feature_meta`, exact callee name, module named.
- [ ] The `core/paths.py` change is **docstring-only**, proved (every changed line prose; signature
      byte-identical; `MissionMetaReadError`'s class/bases unchanged, `:506`; `allow_missing=True` still at
      `:676`). Concurrent WP05 depends on all four.
- [ ] Every `python -c` / `pytest` outside the repository root carries `PYTHONPATH=<workspace>/src`, named per
      capture — in particular `pre.txt` (T021) and the baseline-tree green (T024).
- [ ] `resolution.py:514` is `except (ValueError, MissionMetaReadError)` — a **tuple**, not a narrowing.
- [ ] `:853`, `:1108`, `feature_meta.py:43` catch `MissionMetaReadError` by name.
- [ ] `except Exception` appears at **none** of the six `C-002` handlers (asserted, input count printed).
- [ ] `SC-002`: 12 captured lines per run, input count printed, `diff pre.txt post.txt` empty, both
      `wc -l` non-zero, **positive control quoted first and non-empty**.
- [ ] `SC-007`: guard test asserts `== ""` (not `pytest.raises`); `MissionSelectorAmbiguous` propagation is
      an **assertion**; six-handler check present.
- [ ] `SC-014`: docstring amended, quoted pre and post; `git show --stat <routing sha>` contains
      `core/paths.py` **and** the site files. Foreign `FR-007` qualified (`DIR-032`).
- [ ] Four ledger rows deleted **in the routing commit**, matched by their **full `(path, symbol)` keys** with
      the module path written out — never by a bare `"_resolve_mission_id"`, which matches two rows with
      opposite arms, and never by an elided `(…, "…")` pattern, which matches nothing and prints nothing;
      ledger test green.
- [ ] Routed count printed pre and post, **both 129**, delta **0**; band `[127, 130]` restated with
      **126 is RED**.
- [ ] `ruff check --select C901` pre/post per touched file, ceiling 15 respected; `ruff check` + `mypy
      --strict` clean (`SC-017`).
- [ ] Cone was `tests/mission_runtime`, `tests/upgrade`, ledger test only — **no `tests/sync`, no
      `tests/cli`**; `N passed` and selected counts quoted.
- [ ] `SC-009` residue row filed, `Q4` recorded as **not decided here**, `gh issue view` quoted.
- [ ] Every citation carries **`file:line` and symbol** (`C-003`).

**Subtask marking** — run per subtask as it completes. This records **status only**: `mark-status` exposes
`--status`, `--mission`, `--auto-commit`, `--json` and nothing else, and its payload is a bare
`{T0xx: Status}` (`src/specify_cli/status/models.py:481`). It is **not** an evidence channel. Everything above
lives in the committed `kitty-specs/meta-fail-closed-3162-01KZ7FSQ/evidence/WP04-evidence.md`.

```bash
spec-kitty agent tasks mark-status <Txxx> --status done --mission meta-fail-closed-3162-01KZ7FSQ
```

## Risks

1. **Routing without the handler ships a crash.** `MissionMetaReadError` is a `RuntimeError`
   (`core/paths.py:506`). Commit 1 **is** that state, deliberately and briefly — it is `FR-002`'s red. Commit 2
   must follow it inside this work package, and commit 1 must never be the lane's tip at review time.
2. **Narrowing `:514`.** The most likely wrong move in the mission: it looks tidier, passes a
   `pytest.raises(ValueError)` test, and **deletes** `SC-007`'s protected behaviour. Write the tuple.
3. **Swallowing `MissionSelectorAmbiguous`.** `except Exception` at `:514` hides an ambiguous-handle
   refusal. Banned at all six handlers.
4. **A malformed-only probe.** Satisfies `SC-002`'s shape while the absent-file arm regresses — the exact
   defect `NFR-003` was rewritten to catch. 12 lines, input count printed, or the criterion is unmet.
5. **Ledger rows matched by line number, or by an elided key.** `:198`–`:200` and the `:249` region are
   correct *as of now*; five commits mutate that file in sequence. Match by the **full `(path, symbol)` key**.
   Two specific traps: a pattern containing `…` matches nothing — `grep` exits `1` and prints nothing, which
   reads exactly like *"already deleted"*; and a bare `"_resolve_mission_id"` matches **two** rows,
   `("src/mission_runtime/resolution.py", …)` (this WP's row 3, degrade) and
   `("src/specify_cli/decisions/service.py", …)` (WP03's row 9, refuse-typed — the opposite arm).
6. **Folding calls and reding the floor from below.** The routed bound is two-sided; a swap that collapses
   two calls into one lands **126** and reds `test_routed_load_meta_floor`'s strict `>` assertion.
7. **Squashing the lane, or folding commit 0 into commit 1.** Either destroys `FR-002`'s only red and the ATDD
   evidence that replaces the impossible base-red. With commit 0 folded in, commit 1 has no failing test at
   all — measured: no pre-existing test in `tests/mission_runtime` or `tests/upgrade` drives these four sites
   with corrupt JSON, and the absent/valid paths are unchanged (`allow_missing=True` hard-coded,
   `core/paths.py:676`).
9. **Changing more than the docstring in `core/paths.py`.** Concurrent WP05 depends on
   `load_meta_fail_closed`'s signature, `MissionMetaReadError`'s class, and the return contract. This WP holds
   the file whole for four lines of prose; a signature or exception change breaks WP05 across a lane boundary
   that no file-overlap check inspects. T025 step 4a is the proof obligation.
8. **`#2804` marker coupling.** This WP's routing commit is on the marker's live code path
   (`merge/executor.py:116` → `resolve_placement_only` → `_assemble_core_fragments` →
   `_resolve_mission_id`/`_resolve_coordination_branch`). WP07's evidence does **not** survive this landing;
   re-capture belongs to WP08. Do not re-capture it here, and do not touch
   `tests/specify_cli/cli/commands/test_row_aware_merge_driver.py` (`SC-008`: byte-identical).
   **Use exactly that path** — `find tests -name test_row_aware_merge_driver.py` returns it and only it.
   An earlier draft of this prompt said `tests/merge/...`, which does not exist, and
   `git diff --stat` against a nonexistent path prints **nothing** — indistinguishable from the
   byte-identical proof succeeding. Note the real path is under `tests/specify_cli/`, which is **not**
   the barred top-level `tests/cli`.

## Reviewer Guidance

Check these in order; the first four are where this WP fails if it fails.

1. **Three commits, correct order, unsquashed.** `git log --oneline`: fallback pin → routing → handlers.
   Commit 0 carries the four fallback tests and **nothing else** (`git show --stat`); the routing SHA carries the
   red **as those four tests failing at their recorded node ids**; the handler SHA carries the green on the same
   ids. Squashed, commit 0 folded into commit 1, or the handler change riding in commit 1 all leave `FR-002` with
   **no red**. **Re-check it yourself**: check out each SHA and run the four ids — green, red, green. A green
   commit-1 run means the quoted red was manufactured: reject.
1a. **The `core/paths.py` change is docstring-only** — every `+`/`-` line prose, `load_meta_fail_closed`'s
    `def` line byte-identical, `class MissionMetaReadError(RuntimeError)` (`:506`) untouched, `allow_missing=True`
    still at `:676`. Concurrent WP05 depends on all three.
1b. **Four call-count assertions in the routing commit**, one per site: exactly **1** `load_meta_fail_closed(`
    and **0** `load_meta(` in the routed function's own body, exact callee name, module named. A substring check
    or a printed pre/post pair is a rejection — a fold reads **128** (green at `126/4`) and **129** (green once
    WP06 sets 127).
2. **`resolution.py:514` is a tuple.** Anything narrower is a `SC-007` violation regardless of what the
   tests say. Then read the guard test: it must assert the call **returns `""`**. A
   `pytest.raises(ValueError)` form is the documented cheat and must be rejected.
3. **`MissionSelectorAmbiguous` is asserted, not narrated.** Find the assertion. A comment referencing
   `resolution.py:496-498` is not one.
4. **The probe captured 12 lines with its input count, and the positive control came first and was
   non-empty.** Then `diff` empty with both `wc -l` non-zero. An empty diff without those two guards is
   indistinguishable from a broken harness.
5. **The docstring and the routing are one commit.** `git show --stat <routing sha>` must list
   `src/specify_cli/core/paths.py` alongside the site files (`SC-014`). Confirm the foreign `FR-007` at
   `core/paths.py:639`/`:643` was qualified.
6. **Budget.** Routed pre and post both **129**, delta 0. Not `130` (that is WP05's), not `126` (RED).
7. **Charter exception is stated, not hidden.** The WP's evidence must say out loud that (a) `C-002`'s
   "same edit" reads as "same work package" here and only here, and (b) `NFR-003` makes a base-red
   impossible by construction so the red is on an intermediate commit — both recorded in `plan.md`
   (coupling 5; Charter Check ATDD-first row; Complexity Tracking row 1). Silence on either point is a
   rejection, not a style note.

### Three things in the upstream planning artifacts to be aware of

- **`wps.yaml` T021's claim that row 3's `legacy-<slug>` fallback is "derived from the malformed file" is
  wrong** (`plan.md`'s IC-04 risk bullet is the ambiguous source). Verified at
  `src/mission_runtime/resolution.py:1114`: the sentinel is `f"legacy-{mission_slug}"`, from the **caller's
  argument**, never from file content — `meta` is `None` on that path. All four fallbacks are constant w.r.t.
  the file. Record the correction; still execute the underlying instruction (state derived-vs-constant per site).
- **`plan.md` and `analysis-report.md` disagree on IC numbering.** `analysis-report.md` predates the
  renumbering and attributes some IC-05 surfaces to `IC-04`. `plan.md`'s numbering is authoritative: this is
  `IC-04`. `Q4` and `Q11` stay **operator** questions (`plan.md:783-785,824`); this WP owns **filing** `Q4`
  (T026), not answering it.
- **The two-commit shape you may have read elsewhere is superseded.** `plan.md`'s IC-04 and the earlier draft
  of this prompt describe **two** commits. This WP lands **three**: the four malformed-input fallback tests
  move to a commit 0 so `FR-002`'s red is a real failure of committed tests at commit 1 rather than a
  hand-rolled traceback. `wps.yaml`'s T021/T022/T024 text still reflects the old placement — the shape in this
  prompt is authoritative.
