# Implementation Plan: Verification Trust — make our own verification honest

**Branch**: `feat/verification-trust-3115` | **Date**: 2026-07-31 | **Spec**: [`spec.md`](spec.md)
**Mission**: `verification-trust-3115-01KYVYWM` | **Topology**: `lanes` | **Mission type**: `software-dev`
**Issues**: `Priivacy-ai/spec-kitty#3115`, `#3113`; `#3030` carried as a third matrix row
**Base commit**: `bb2020fea9` — level with `Priivacy-ai/main`. Every baseline, "before" measurement
and red-first demonstration in this plan is taken at this commit (NFR-009).
**Reading order**: [`spec.md`](spec.md) → [`standing-rules.md`](standing-rules.md) →
[`notes/post-plan-squad-findings.md`](notes/post-plan-squad-findings.md) →
[`notes/post-spec-squad-findings.md`](notes/post-spec-squad-findings.md) →
`kitty-specs/journal-project-consent-3030-01KYKWQS/tracer-tooling-friction.md`.
**Revised**: 2026-07-31, after the post-plan adversarial squad (three lenses; `paula-patterns`
BLOCK, `reviewer-renata` REQUEST-CHANGES, `python-pedro` NEEDS-CHANGE). See the scope-cut note
immediately below, and `notes/post-plan-squad-findings.md` for every finding and its disposition.

---

> ### ⚠ SCOPE CUT — WP08 / FR-008 (`_isolated_home` convergence) is removed from this plan
>
> **Cut by operator decision, 2026-07-31, after the post-plan adversarial squad. This is a decision,
> not an omission.** `spec.md` carries the matching FR-008 tombstone; the work-package table below
> jumps WP07 → WP09 and **WP08's number is retired, not reassigned**.
>
> **Why.** Three lenses independently measured the 22 `_isolated_home` definitions and converged:
> they are a **name collision, not a duplicated seam**. Seven incompatible shapes; three victim
> files that pin **no home at all** — and those three are the `#3115` victims, so a root owner
> pinning `SPEC_KITTY_HOME` would change behaviour in exactly the files WP02/WP03 fix; contradictory
> `SPEC_KITTY_ENABLE_SAAS_SYNC` policies documented as load-bearing **in opposite words** at their
> own sites; three fixture return contracts and one class-method fixture a root conftest cannot
> replace; five callers of `reset_coalesce_strategy()`, a constraint this plan never named. And the
> DoD's instrument was wrong: collected counts do not move when a fixture *body* changes, so the
> acceptance was satisfiable by a deletion making isolation strictly worse.
>
> **Where it went.** A follow-up issue against `Priivacy-ai/spec-kitty` carries it. The **measured
> equivalence-class evidence** lives in
> [`notes/post-plan-squad-findings.md`](notes/post-plan-squad-findings.md) ("The convergent finding
> — FR-008 cut from scope"), and `spec.md`'s follow-up-candidates section states how the successor
> must be scoped. The successor number lands on `#3115`'s matrix row at mission close.
>
> **What was re-derived because of the cut** — nothing is left dangling:
> - **WP07 now owns the five `578a659162` files** and applies its own verdict. WP08 was to apply it;
>   with WP08 gone, the measure-then-apply split has no second half, and WP07 is the only agent that
>   would be live in those files anyway.
> - **The three "provably dead `COLUMNS` sets" removal is dropped outright, not reassigned.** Finding
>   F2 measured them **live** outside `TERM=dumb`. See "The `COLUMNS` sets" below.
> - **Lane assignments, `blocked_by` edges, `parallel_group` depths and the critical path are all
>   recomputed** from the post-cut ownership map. See "Lane allocation" and "Critical path".
> - **WP13's `blocked_by` becomes WP03, WP05, WP07, WP12** (WP08 replaced by WP07).
> - **The `#3115` matrix row's `evidence_ref` drops FR-008.**
>
> ### The `COLUMNS` sets — dropped, and why they are not reassigned
>
> WP02's old "note passed forward to WP08" said the seam makes three `monkeypatch.setenv("COLUMNS", …)`
> sites provably dead, and WP08 was to remove or annotate them. **That is withdrawn.** Finding F2
> measured that under `CliRunner` in the default environment `rich`'s `is_terminal` is False, the
> `is_dumb_terminal` early return does **not** fire, and `COLUMNS` **is** consulted —
> `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111` passes
> `env={"COLUMNS": "240"}` and is **live today**. The sets are inert on the *failing* path only.
>
> **Disposition: all three are left exactly as they are** —
> `tests/cli/commands/test_sync_status_per_project_3030.py:83`,
> `tests/cli/commands/test_sync_doctor_per_project_3030.py:72`,
> `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`. **No work package removes
> or annotates them.** WP07 owns the first two *files* (for the FR-009 docstring) and is explicitly
> forbidden from touching their `COLUMNS` lines; nothing owns the third. The one constraint the
> finding does impose lands on **WP02**, which authors the pin: **the pinned width must be ≥ 240**,
> or the seam narrows `test_activation_layout`'s render surface below what it asks for.

## Summary

Three defects and one configuration gap, all of the same shape: the mechanism that is supposed to
tell us whether the code is correct returns an answer that is not about the code.

1. **`#3115` CLI half** — a *measured* console render-width defect. `rich.console.Console.size`
   returns `ConsoleDimensions(80, 25)` from the `if self.is_dumb_terminal:` branch, which sits
   **above** the `COLUMNS` read; the `Project` column is `overflow="fold"`
   (`src/specify_cli/cli/commands/sync.py:1440`, deliberate, documented at `:1430-1436`); a 36-char
   uuid folds and stops being a contiguous substring. Fix layer: **one conftest seam** that pins the
   render surface structurally, plus a guard and a proof that the obvious wrong fix is wrong.
2. **`#3115` sync half** — a narrower, separately-verified defect: `@patch(".../saas_client.time.sleep")`
   resolves the **stdlib** `time` module object (`src/specify_cli/tracker/saas_client.py:19` is a bare
   `import time`), so the call recorder counts sleeps made by any live thread in the worker. Fix
   layer: an inventory, an autouse leak guard scoped to that inventory, and a bounded investigation
   with a written exit.
3. **`#3113`** — the egress guard's all-positional transport-call evasion. Fix layer: the guard's own
   docstring limit list, its bite-test parametrisation, and (measurement permitting) a **structural**
   AST tightening in `_classify`'s bare-`Name` branch.
4. **The `pytest.ini` timeout gap** — a hang is not a measurement. Fix layer: a counter pin in the
   loop-driving tests **first**, then a harness-level timeout backstop over a tree where the counter
   already holds.

The deliverable is not "make CI green once". It is: a cheap committed reproducer; the render surface
pinned at one owner with a guard against silent regression; the sync half diagnosed on its own
evidence and `578a659162`'s self-declared-unproven token-manager hardening resolved either way; the
egress guard's negative control measured in *shapes*; and a non-terminating loop that reds by name
and by count. (The isolation-seam convergence that once sat in this list was **cut** — see the
scope-cut note above.)

## Technical Context

**Language/runtime**: Python 3.11/3.12, pytest + pytest-xdist + pytest-timeout, Typer CLI,
`rich` 15.0.0. **`pytest-randomly` is NOT installed** — corrected post-plan (F3): not importable
(`importlib.util.find_spec("pytest_randomly")` → `None`), absent from `pyproject.toml:101-113`'s
`test` extra, absent from every workflow. Nothing randomises test order on this tree. That is why
C-005 is struck and why WP01's determinism criterion is rewritten below. No production source change
is required by any FR except FR-015's optional matcher tightening (which lives in a test module) —
this is a **test-and-harness mission**.

### The CLI half: where the fix goes, and why that layer

**The seam is a conftest fixture, not a per-test patch and not `COLUMNS`.**

- **Why not `COLUMNS`** (C-012, hard): `Console.size`'s `COLUMNS` read sits *below* the
  `if self.is_dumb_terminal:` early return. On the failing path it is never consulted. The victim
  files already set it — `tests/cli/commands/test_sync_status_per_project_3030.py:83` and
  `tests/cli/commands/test_sync_doctor_per_project_3030.py:72` both
  `monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)`, and
  `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111` passes `env={"COLUMNS": "240"}`.
  **These three sets are inert on the failing path.** They are the strongest available evidence that
  `COLUMNS` is not a fix: it was already there and it never fired. **But they are not dead**
  (corrected post-plan, F2): on the **non-dumb** path — `CliRunner` in the default environment, where
  `is_terminal` is False — the early return does not fire and `COLUMNS` *is* read.
  `test_activation_layout.py:111` is live today. So the sets stay, and the pin must be **≥ 240**.
- **Why both dimensions** (measured, spec FR-002 / SC-003): rich's explicit-size early return
  requires `self._width is not None and self._height is not None`. Measured under
  `TERM=dumb FORCE_COLOR=1 COLUMNS=220`: no width → `(80, 25)`; `width=220` **alone** → `(80, 25)`;
  `width=220, height=50` → `(220, 50)`; `TTY_COMPATIBLE=0` → `(220, 25)`. A width-only pin is the
  single most likely way this fix ships broken and green.
- **Why the root conftest**: the house precedent is two doors down. `tests/conftest.py:307-329`
  (`_plain_cli_console_seam`, autouse, set → `yield` → restore in `finally`) already owns exactly
  this concern for *colour*; `tests/conftest.py:253-299` (`_isolated_worker_home`, autouse,
  per-worker) is the root-scoped precedent for a process-surface pin. And
  `tests/specify_cli/cli/commands/_help_snapshot.py` already pins `10_000 × 100` for exactly this
  reason and documents the trap in its module docstring — *"Rich early-returns the explicit size only
  when width AND height are set"*. **Decision: extend `_plain_cli_console_seam` in
  `tests/conftest.py` to pin the render surface as well as the colour**, rather than adding a second
  autouse fixture. One owner; one `finally`; the docstring that already explains the colour half
  gains the width half. (The earlier draft justified this by analogy to FR-008's `_isolated_home`
  convergence; **FR-008 is cut**, and the argument stands on its own without it — colour and width
  are one concern at one object, which is what `_plain_cli_console_seam` already says.)
- **Why `CliConsole` and not `rich.Console`**: every CLI module renders through the
  `console` / `err_console` singletons constructed at import in
  `src/specify_cli/cli/console.py:126-127`, and `CliConsole._instances` (`console.py:49`) is a
  `WeakSet` of **every** live instance — the singletons *and* the deliberately-distinct specials.
  `set_all_plain` already walks it.
- **How far the width pin may walk that set — corrected post-plan (F1).** Colour and width are *not*
  symmetric here. `set_all_plain` can walk everything because plain-ness is uniform; a width pin
  cannot, because three instances are **deliberately sized**:
  `src/specify_cli/cli/commands/charter/list_cmd.py:26` (`width=200`),
  `src/specify_cli/cli/commands/glossary.py:46` (`width=120`), and
  `src/specify_cli/cli/commands/docs.py:43` (`width=120`, whose 120 is stated load-bearing in the
  comment at `docs.py:40-42`). A blanket `size = (W, H)` walk overwrites all three.
  **Decision: the seam pins only the two singletons** (`console.py:126-127`), or equivalently exempts
  any instance constructed with an explicit `width=`.
- **The two consoles the seam structurally cannot reach — a stated gap, not a hidden one.**
  `src/specify_cli/cli/helpers.py:234` (`CliConsole(stderr=True, color_system=_color)`) and
  `src/specify_cli/cli/logging_bootstrap.py:92` (`CliConsole(stderr=True, highlight=False)`) are
  constructed **inside functions**, i.e. after the seam's setup-time walk has already run. They are
  **not pinned**. FR-003's "non-zero inspected count" would pass while both are unpinned, which is
  exactly the vacuous-gate shape this mission exists to stop — so the guard asserts it saw the
  **named** singletons by identity and reports these two as a named gap (see WP03).
- **What must not move**: `overflow="fold"` on the Project column stays (C-009 —
  `sync.py:1430-1436` states why: an ellipsized identity is a prefix the operator cannot pass to
  `sync purge`). No whitespace flattening (C-009); FR-004 proves it rather than asserting it, because
  the fold interleaves the rest of the table row *between* the two uuid fragments.

**Blast-radius surfaces to check before/after** (FR-002): the golden `--help` snapshot tests (which
pin their own console independently via `_help_snapshot.force_wide_help_console`, so they should be
unaffected — but *should* is not a measurement);
`tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`; and — **added post-plan (F2)** —
`tests/specify_cli/cli/commands/charter/test_activation_layout.py`, whose `env={"COLUMNS": "240"}` at
`:111` is on the **live** path and which the pin will now override. That file is the reason the pin
must be ≥ 240; it is a blast-radius *subject*, not a write target.

### The sync half: where the fix goes, and why that layer

The patch-target mechanism is **settled** and must not be re-derived (FR-005): `saas_client.py:19` is
a bare `import time`; `saas_client.py` has exactly two module-level names (`_SESSION_EXPIRED_MESSAGE`
`:36`, `_UNAUTHENTICATED_CATEGORY` `:39`); the backoff is local variables at `:466-468`. A
module-global backoff leak is **structurally impossible** and is not funded. The victim file's own
`_advancing_clock` docstring (`tests/sync/tracker/test_saas_client.py:32-50`) already documents this
exact class for `time.monotonic`.

What remains open is **which live thread is sleeping inside the patch window**. The candidate source
named in the spec is `src/specify_cli/sync/daemon.py` (threads `:587`, `:767`, `:828`; sleep loops
`:584`, `:1382`). The fix layer for the *guard* is `tests/sync/conftest.py` — an autouse snapshot of
the globals and the live-thread set that FR-006's inventory marks reachable, failing the **polluter**
rather than the victim. It is scoped to the inventory, **not** to FR-005's answer, so it ships
whether or not the attribution converges.

**Hard constraint on that file**: `tests/sync/conftest.py` is 259 lines and its final fixture
(`:242-259`) is the filename-token consent-grant guard (`protected = ("consent", "capture_gate")`).
That guard is **explicitly out of scope** (spec "Out of scope", and the friction record's *"A shared
fixture whose guard is filename-matched can silence the pins it guards"*): it is **armed** — replacing
the token guard with a marker reds three `test_runtime.py` tests whose natural remedy would undo
`#3030`'s T028. The WP that adds the leak guard **may not touch `tests/sync/conftest.py:242-259` at
all**, and its brief must say so in those words.

### `#3113`: where the fix goes

All three FRs land in **one file** — `tests/architectural/test_egress_consent_boundary.py`
(1,080 lines):

- **FR-013** — the module docstring's "Completeness limits" list currently runs **1-7** (verified:
  `getattr`-by-string; empty callback registries; dynamic import/`exec`; variable-command
  `subprocess`; at-rest pooling; bare `.put(x)`; multi-sink-per-file). The all-positional /
  no-`headers=` transport call becomes **limit 8**, in the same voice, plus a meta-test so a future
  docstring trim reds.
- **FR-014** — `test_scanner_detects_each_sink_shape` (`:933`) is parametrised over eight shapes; the
  transport-call shapes are `injected-transport-parameter`
  (`poster(url, data=body, headers=hdrs, timeout=5.0)`) and `aliased-transport-method`. Two
  **positional** cases are added. Case (A) `def go(poster, url, body, hdrs): return poster(url, body, hdrs)`
  passes trivially under a name-keyed rule because `_attr_tail` (`:266-272`) returns `node.id`
  verbatim for a bare `Name` and `url` is in `_URL_ARG_NAMES` (`:197`). **Case (B)
  `def relay(post, u, payload, meta): return post(u, payload, meta)` is the adoption gate.**
- **FR-015** — `_transmits_a_body` (`:295-306`) requires `headers` **and** a body keyword, so an
  all-positional call is invisible. The candidate tightening is **structural**: the callee is a bare
  `ast.Name` whose `id` resolves to a **parameter of the enclosing `FunctionDef`**. `_classify`
  already has the bare-`Name` branch to hang it on (`:312-316`, `return SinkKind.TRANSPORT_CALL if
  _transmits_a_body(node) else None`). Decidable with **no author-chosen word**. C-006 binds: keying
  on `_URL_ARG_NAMES` is the `RETIRED_DRAIN_NAMES` failure with a different subject and is rejected
  *regardless of its false-positive count*.

  **Two corrections taken post-plan (F4), which re-order WP10 and change its expected outcome:**

  1. **It is a scanner restructure, not a branch edit.** The predicate needs enclosing-scope
     information that `_classify(node: ast.Call)` (`:309`) does not carry — `_classify` is reached
     from a flat `ast.walk(tree)` at `:347`, which discards the enclosing `FunctionDef`. Adopting it
     means threading the enclosing function's parameter set through the walk. The bare-`Name` branch
     is where the *decision* would live, but the *information* is not there to decide with.
  2. **The measurement has already been run, and it forbids adoption on present evidence.** Over
     `src/`, the minimal rule that catches the adoption-gate case (B) yields **5 false positives**,
     arising in four named enclosing functions — `resolve_workspace_for_wp`, `locate_work_package`,
     `behind_commits_touch_only_planning_artifacts`, `get_wp_lane` — against **211 candidate sites
     across 13 files** in total. By WP10's own DoD, non-zero false positives means **the matcher is
     left alone** and FR-014 lands as two `xfail(..., strict=True)`. **Both outcomes close `#3113`.**

  Consequently WP10 takes the `src/`-wide count **first** and funds the restructure **only** if it
  returns zero. The numbers above are stated here so the WP does not re-derive the *scoping*
  decision from scratch; the WP still **re-runs and quotes its own count**, because a planning
  paragraph is not a measurement.

**Ratchet coupling**: `tests/architectural/_baselines.yaml:368` pins `egress_allowlist_files: 28` and
`:375` pins `known_ungated_files: 0`; growth **fails** `test_ratchet_baselines.py` — a different test
in a different file. A tightening that adds sites in `src/` may move a count. This is a *file*
contention, not just a sequencing one; see the ownership map.

### The timeout gap: where the fix goes, and the one ordering that cannot be lost

**The counter pin must precede the timeout default. This is the plan's single hardest sequencing
constraint.** Once a global timeout exists, a non-terminating dispatch loop reds on the *timeout*,
and FR-018's red-first becomes unobservable — the backstop masks the missing pin, and
`Failed: Timeout (>Ns) from pytest-timeout` is explicitly **not** an acceptable red (FR-018, SC-014).
Prove the counter first, on a tree with no global timeout; then add the timeout over a tree where the
counter already holds.

- **FR-018** lands in `tests/delivery/test_dispatch_window_consent_3030.py`
  (`test_no_non_consented_event_ever_enters_the_live_dispatch_window` `:157`,
  `test_the_window_is_filled_with_consented_events_not_wasted_on_denied_ones` `:218`, driving
  `_RecordingIngress` `:68`). The shape to mirror is `DISPATCH_CALL_CAP = 25` in
  `tests/delivery/test_nfr002_loop_permanence_3030.py:69`, asserted at `:154-157` — `#3030` already
  adopted this shape for exactly this reason.
- **FR-016/FR-017** choose between (a) `addopts` in `pytest.ini` and (b) scoping the flag to the fast
  job command lines in `.github/workflows/ci-quality.yml`. `pytest.ini` sets `testpaths = tests`, so
  an `addopts` default caps **every** invocation of this ini, including the `slow`/`stress`/`e2e`
  opt-ins that FR-017's regression clause structurally cannot observe (46 `slow` tests, defined in
  `pytest.ini` as ">30 seconds", against ~15 `@pytest.mark.timeout` sites). **The plan does not
  pre-decide (a) vs (b)** — FR-016 requires the derivation to decide it and the WP to state which.
  What the plan *does* fix: derivation (a) is only permissible if `--durations` is actually collected
  over every selection that inherits the ini; if the WP cannot afford that, it takes (b) and its
  blast radius is the enumerated job list. Both fast shard commands carry `--cov`
  (`ci-quality.yml:1132`, `:1543`), which installs a per-thread trace function, changes thread
  scheduling and **inflates** `--durations`; the coverage state must be stated with the value.

### CI facts this mission's evidence depends on — verified, quote these

| Fact | Verified at | Consequence |
|---|---|---|
| `fast-tests-cli` selection | `ci-quality.yml:1540-1546`: `pytest tests/cli/ tests/specify_cli/cli/ -m "fast and not windows_ci" -q --tb=short -n auto --dist loadfile --durations=50 --cov=src/specify_cli/cli … \|\| test $? -eq 5` | FR-011 quotes this selection verbatim; `\|\| test $? -eq 5` means an empty collection is a **green job** — any claim must quote the collected count (NFR-008) |
| `fast-tests-sync` selection | `ci-quality.yml:1124-1133`: `pytest tests/sync/ -m "fast and not windows_ci" … --ignore=tests/sync/test_orphan_sweep.py --ignore=…daemon_orphan_classification.py --ignore=…daemon_cleanup_boundary.py --ignore=…issue_1071_singleton_reconfirmation.py -n auto --dist loadfile --durations=50 --cov=src/specify_cli/sync` | FR-011's `--ignore` enumeration comes from here, not from memory |
| `fast-tests-sync` gate | `ci-quality.yml:1101`: `needs.changes.outputs.sync == 'true' \|\| github.event_name == 'push'` | The `push` escape only fires on `main`/`develop`/`2.x` (`ci-quality.yml:39-42`), **never** on this feature branch. So the shard runs only via the path filter |
| The path filter | `changes` job: `sync:` includes `tests/sync/**` | **Mitigation, verified**: this mission edits `tests/sync/conftest.py` and `tests/sync/test_sync_consent_default_deny.py`, so `needs.changes.outputs.sync` will be `true` and the shard *will* run. This is worth stating in the PR because the spec's risk was that it would not |
| Workflow triggers | `ci-quality.yml:3-13` — `pull_request` targeting `main`/`develop`/`2.x` only | The only CI observation available to this mission is the cross-fork PR. There is no branch-push CI |

## Charter Check

*GATE: must pass before implementation. Re-check before `accept`.*

| Gate | Status | Note |
|---|---|---|
| No production behaviour change | **Pass by design** | C-001 (no routing change), C-009 (no `overflow="fold"` removal). Only FR-015 touches matcher logic, and that logic lives in a test module |
| Fail-closed defaults preserved | Pass | FR-012 *strengthens* the fail-closed pin by adding a filesystem-independent one; it never relaxes it |
| Reuse over reinvention | **Pass, and it is the point** | FR-002 extends `_plain_cli_console_seam` rather than adding a second autouse fixture; FR-018 mirrors `DISPATCH_CALL_CAP`. (FR-008's convergence was the third example and is **cut**; the row still passes on the other two) |
| Guards detect, never repair | Pass by constraint | H8 / FR-003 / FR-007. A guard that widens the console it watches silences what it guards |
| Fixtures restore, never clear | Pass by constraint | C-002, `finally`-restore, precedent `tests/conftest.py:307-329` |
| No `kitty-specs/` writes from lanes | **Pass with named relocations** | `src/specify_cli/policy/commit_guard.py:84-89` refuses staged `kitty-specs/` paths from implementation branches. Every lane-written artefact is outside it (see Project Structure). Narrative evidence is folded into `notes/` **by the orchestrator on the mission branch**, never by a lane |
| No writes into a closed mission's dossier | Pass by constraint | C-010: `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md` is cited one-directionally and **not edited** |
| **ATDD-First Discipline** (binding per C-011) | **Pass with five stated exceptions** | Eight of thirteen WPs comply in full. Five cannot, for a reason the charter's own wording supplies. See the reconciliation below — it is stated here because a reviewer applying the clause literally would otherwise have grounds to reject compliant work |
| `ruff format` not run | Pass by constraint | C-008; `ruff check` only |

### ATDD-First reconciliation — the five exceptions, and the anchor

The charter binds: *"The WP cannot start coding until at least one failing-first ATDD test exists that
pins the **user-observable behaviour the WP delivers**… The reviewer verifies red→green: the test was
RED on the WP's `planning_base_branch` AND GREEN on the WP's final commit."*

**Eight WPs comply fully** — WP01, WP02, WP03, WP05, WP09, WP10, WP11 and WP12. Every one commits its
failing test first, and this mission's red-first regime is *stricter* than
the charter baseline: the red must be a **consequence** with named assertion text, never a boolean
flip, and a `TypeError`, fixture error, collection error or empty output file explicitly does not
satisfy it.

**Five WPs deliver no user-observable behaviour, so there is nothing for an ATDD test to pin:**

| WP | Delivers | Why no ATDD test |
|---|---|---|
| WP04 | An inventory document | A markdown map of process-global state. A test asserting a document exists is decoration |
| WP06 | An attribution, which may legitimately be a negative result | Its own T020 requires no failing-first test, and its `(F-b)` branch explicitly permits closing with **no red at all** — *"an explicit written statement that it could not be reproduced locally"*. A WP that may close having never produced a red is not ATDD-compliant, and correctly so: it is an investigation |
| WP07 | A measurement verdict + a docstring correction | Its output is four quoted count lines and a per-site split. The verdict may legitimately be "not load-bearing" |
| WP13 | A shard-proof script and its recorded run | It measures the other WPs' tests; it introduces no behaviour of its own |
| WP14 outcome B | A deferral | Produces no code **by construction** — the declared file is deliberately left untouched |

Writing an ATDD test for any of these would produce a test that passes for the wrong reason, which is
the defect class this entire mission exists to close. **Each instead carries an evidence obligation
stronger than a passing test would be**: named exclusion measurements per mechanism (WP04, WP06), a
per-site split with a non-zero suppressed count and a void-null-verdict rule (WP07), enumerated
node-ids with per-case outcomes and the job conclusion (WP13), and a successor handle in the matrix
`evidence_ref` (WP14-B). These are recorded as the ATDD substitute, not as an exemption from evidence.

**On the anchor, and it has an expiry.** This dossier anchors red-first at `bb2020fea9`; the charter
requires RED on the WP's own `planning_base_branch`, which is `feat/verification-trust-3115` for all
thirteen. Those are currently the **same tree for source and test purposes** — verified: `bb2020fea9`
is an ancestor of HEAD and **no non-`kitty-specs/` file has changed since**, so every baseline taken
at the mission base is also a baseline at each WP's declared base. **That equivalence expires the
moment the first WP merges.** Once WP01 lands, WP02's `planning_base_branch` tip is no longer
`bb2020fea9`, and per NFR-009 every lane merges the mission branch before its first measurement and
**states the commit it measured at**. Reviewers verify red at the WP's own base from that point on —
the `bb2020fea9` anchor is a convenience that holds only until the first merge, and it is named here
so nobody carries it past that point without noticing.

## Project Structure

### Documentation (this mission)

```
kitty-specs/verification-trust-3115-01KYVYWM/
├── spec.md                              # FR-001…018, NFR-001…010, C-001…012, SC-001…018
├── plan.md                              # this file
├── standing-rules.md                    # carried verbatim into every subagent brief
├── notes/post-spec-squad-findings.md    # four-lens squad, the re-scope, the base correction
├── lanes.json                           # written at tasks time — EVERY WP below has an entry
├── issue-matrix.json                    # canonical; three rows (3115, 3113, 3030)
└── tasks/                               # WP prompts
```

### Files this mission writes (repository root) — the complete set

```
tests/
├── conftest.py                                  # FR-002 seam (extend _plain_cli_console_seam :307-329)
├── _arch_shard_map.py                           # FR-003's new arch test must be assigned a shard
├── architectural/
│   ├── test_cli_console_render_width.py         # NEW — FR-003 width guard
│   ├── test_egress_consent_boundary.py          # FR-013 + FR-014 + FR-015
│   └── _baselines.yaml                          # FR-015 ratchet reconciliation (:368, :375)
├── cli/commands/
│   ├── test_render_fold_not_repairable_3115.py  # NEW — FR-004
│   ├── fixtures/render_width_3115/              # NEW — the 80-col and pinned-width captures
│   └── (5 files of 578a659162)                  # FR-009 docstring ONLY. COLUMNS lines untouched
├── sync/
│   ├── conftest.py                              # FR-007 leak guard — :242-259 IS OFF LIMITS
│   ├── test_leak_guard_probe_3115.py            # NEW — FR-007's probe (see WP05: last resort)
│   ├── test_sync_consent_default_deny.py        # FR-012
│   └── tracker/test_saas_client.py              # FR-005 attribution recorded at the site
└── delivery/test_dispatch_window_consent_3030.py# FR-018 counter pin
scripts/
├── repro_3115_render_width.sh                   # NEW — FR-001, committed, one line to run
└── mutants/                                     # NEW — every C-003 plugin, one file per mutant
docs/development/
├── testing-parallel.md                          # FR-001 reproducer section (existing page)
├── process-global-inventory-3115.md             # NEW — FR-006 (outside kitty-specs/, per C-010)
├── toc.yml                                      # nav entry for the new page
└── 3-2-page-inventory.yaml                      # GENERATED lockfile — regenerate, never hand-edit
pytest.ini  and/or  .github/workflows/ci-quality.yml   # FR-016 (the WP chooses and states which)
```

**Removed from this set by the scope cut**: the 17 further `_isolated_home` files, and
`tests/conftest.py`'s second role as the hoisted `_isolated_home` owner. `tests/conftest.py` is now
touched by **exactly one** work package (WP02), for the render seam only.

**Structure decision — `scripts/mutants/`, and why not `tests/`.** C-003 requires every mutation and
every blinding to be a pytest plugin, never a source edit. Those plugins must live somewhere
committed (a mutant nobody can re-run is a recollection, not a measurement). They do **not** go under
`tests/`: the root conftest's `_fail_on_wall_clock_assertions` (`tests/conftest.py:245`, invoked from
the collection hook at `:218`) runs `find_test_python_paths(Path(__file__).parent)` over the whole
`tests/` tree at collection and raises `pytest.UsageError` on wall-clock assertion violations — a
sleep-shaped mutant under `tests/` risks failing *collection of the entire suite*, which is precisely
the "harness error dressed as a domain verdict" this mission exists to stop. `scripts/mutants/` is
outside `testpaths`, outside pytest collection, and outside every docs lint. One file per mutant,
named for its WP, so no two agents share one.

### The mutant-plugin contract — CORRECTED, and binding on WP02, WP06, WP07, WP11 and WP12

> **This replaces every "loaded via `PYTHONPATH`" statement in the earlier draft.** The post-plan
> squad probed the old contract against a known-answer baseline and found it produced a **silently
> inert** mutant in two independent ways — i.e. the plan was committing the exact rot mode it exists
> to guard against (M1, CRITICAL). Any WP brief that quotes the old wording is wrong.

1. **Placement.** `scripts/mutants/<verb>_<subject>_3115.py`, one file per mutant, named for its
   authoring WP. Committed.
2. **Loading — `PYTHONPATH` alone does *not* load a plugin.** Making the module importable is
   necessary and not sufficient. The invocation is:
   `PYTHONPATH=scripts/mutants pytest -p <module_name> …` (or `PYTEST_PLUGINS=<module_name>`).
   A `PYTHONPATH`-only mutant is imported by nothing, binds nothing, and its run reads as a passing
   gate. **Every mutant run in this mission's evidence quotes the `-p <module>` it was loaded with.**
3. **Neutralisation site — hook level, never a same-named fixture.** Neutralise in
   `pytest_configure` (import-time and session-level seams) or `pytest_fixture_setup` (to intercept a
   named fixture's setup). **A same-named autouse fixture defined in a plugin loses to a conftest
   fixture** for items under that conftest's directory — pytest resolves conftest fixtures at higher
   precedence — so the "define `_plain_cli_console_seam` in the plugin" shape the earlier draft
   implied is a guaranteed no-op. Probed: the hook-level form produced a named red
   (`AssertionError: seam was off`); the fixture form did not bind at all.
4. **Self-proof — three parts, all mandatory.**
   - **Assert its own binding.** The plugin fails loudly at `pytest_configure` if the symbol or
     fixture it intends to patch is absent, renamed or relocated.
   - **Report the per-site split** across *every* name the symbol is reachable by. An aggregate count
     cannot distinguish "both sites mutated" from "one mutated, one inert" (fifth rot mode).
   - **Fail loudly if the symbol it patched was never called** during the session. A zero suppressed
     count is a finding about the **mutant**, not about the code, and **no verdict may be drawn from
     such a run** — this is what makes a null result ("not load-bearing", "the counter did not bind")
     falsifiable rather than automatic.
5. **Reporting.** Every run under a mutant quotes the mutant's own binding/suppression report **beside**
   its count line and collected count. "Ran under the mutant, still green" without a non-zero
   suppressed count is not a measurement.

## Complexity Tracking

| Choice | Why needed | Simpler alternative rejected because |
|---|---|---|
| Extending the **existing** `_plain_cli_console_seam` rather than adding a width fixture | One owner, one `finally`, one docstring that already explains half the problem. Colour and width are the same concern (*"determinism is a property of the object, not the environment"*, `tests/conftest.py:308-320`) | A second autouse fixture is a second thing to disable and a second restore path |
| ~~A **root**-scoped `_isolated_home` owner~~ | **WITHDRAWN — cut with FR-008/WP08.** Retained as a tombstone row because the *reasoning* is what the follow-up issue must not inherit uncritically: the 22 definitions span five packages, so a root owner looked like the only reach — but the post-plan measurement showed they are seven incompatible shapes, so **reach was never the binding constraint; equivalence was**. Whatever the successor does, it does not start from "one owner because no package conftest reaches all five" | — |
| **WP07 both measuring and applying** the FR-009 verdict, in the same package | A consequence of the cut: WP08 was the applying half. With it gone, splitting measure/apply would put two agents in the five `578a659162` files for no benefit, and C-007 permits one | A second WP to apply a docstring is a lane, a worktree and a handoff for a five-line change |
| One WP owning all three `#3113` FRs | All three edit `tests/architectural/test_egress_consent_boundary.py`. C-007 permits one live agent per file | Three WPs on one file is the shared-index failure that lost 13 files on `#3030` |
| The timeout WP being repo-wide and last | `testpaths = tests` means an `addopts` default caps **every** invocation of this ini | Landing it early makes every subsequent lane's baseline incomparable to the ones taken before it, and masks FR-018's red-first |
| A **pre-allocated placeholder WP** (WP14) for an outcome that may not exist | The friction record: *"WPs created after planning have no lane, so two gates silently no-op"* — the lane-staleness gate fires inapplicably and the pre-review gate prints `no_coverage — skipping the gate cheaply` on work that received no gate at all | Adding the WP after the investigation lands reproduces that friction knowingly |

## Implementation Concern Map

> **Note**: Implementation concerns are architectural groupings, not executable units. The work-package
> decomposition below is the planner's **binding** translation of them, because this mission's file
> contention (C-007) constrains the slicing more tightly than concern boundaries do.

### IC-01 — The render surface, pinned structurally

- **Purpose**: Stop the tests asking the ambient environment how wide the terminal is, at one owner.
- **Requirements**: FR-001, FR-002, FR-003, FR-004; NFR-005; C-002, C-003, C-009, C-012;
  SC-001…005. (C-005 is struck; SC-006 is struck with FR-008.)
- **Surfaces**: `tests/conftest.py:307-329`; `src/specify_cli/cli/console.py:49,126-127` (read only);
  `tests/specify_cli/cli/commands/_help_snapshot.py` (precedent, read only);
  `scripts/repro_3115_render_width.sh`; `docs/development/testing-parallel.md`.
- **Depends on**: none. FR-001 is two environment variables and one file, so nothing downstream is
  hostage to it.
- **Risks**: the width-alone trap (ships broken and green); the golden `--help` fixtures; and the
  fact that `SILENT`/`OPTED_OUT` pass at width 80 *incidentally* via an un-tabled warning paragraph —
  **only the `CONSENTED` iteration demonstrates anything**.

### IC-02 — The sync cone: inventory, guard, attribution, exit

- **Purpose**: Diagnose the sync half on its own evidence and ship the isolation seam whether or not
  the attribution converges.
- **Requirements**: FR-005, FR-006, FR-007, FR-010; NFR-004, NFR-006, NFR-008; C-002, C-003.
- **Surfaces**: `docs/development/process-global-inventory-3115.md`; `tests/sync/conftest.py`
  (excluding `:242-259`); `tests/sync/tracker/test_saas_client.py`;
  `src/specify_cli/sync/daemon.py` and `src/specify_cli/tracker/saas_client.py` (read only).
- **Depends on**: none for the inventory; FR-005 and FR-007 both consume it.
- **Risks**: the leak guard **becoming** the polluter by snapshotting state in a way that
  instantiates it — its positive control must include a run where nothing leaks and nothing is
  flagged. NFR-004 binds the probe runs: sequential, or explicitly partitioned by `SPEC_KITTY_HOME`
  and port range.

### IC-03 — The token-manager verdict

> **Re-scoped by the post-plan cut.** This concern was "seam convergence *and* the token-manager
> verdict". The convergence half (FR-008) is **cut**; what remains is the verdict, which is smaller,
> independently valuable, and the thing that closes `#3030`'s matrix row.

- **Purpose**: Resolve `578a659162` / `4f8e4ca781`'s self-declared-unproven `reset_token_manager()`
  hardening either way, and record the verdict **at the site**.
- **Requirements**: FR-009; NFR-007, NFR-009; C-002, C-003. (SC-006 is struck with FR-008.)
- **Surfaces**: the five files of `578a659162` —
  `tests/cli/commands/test_sync_doctor_per_project_3030.py`,
  `…/test_sync_status_per_project_3030.py`, `…/test_sync_migrate_backfills_h4.py`,
  `…/test_sync_purge_3030.py`, `…/test_sync_doctor_consent_health_3030.py` — plus
  `scripts/mutants/neutralise_reset_token_manager_3115.py`.
- **Depends on**: IC-01 (FR-009 case (b) needs the pinned width to discriminate).
- **Risks**: the five files carry **two** live concerns rather than the three the earlier draft
  feared — the FR-009 docstring, and their `COLUMNS` sets, which are now **left alone** (F2). One
  live agent (WP07) covers both, and the brief forbids touching the `COLUMNS` lines outright. The
  residual risk is the mutant: a null verdict is only admissible from a run whose plugin reports a
  **non-zero** suppressed count at the five function-local call sites, and names the two
  package-name-bound sites in `tests/auth/` as deliberately unpatched rather than as zero.

### IC-04 — The egress guard's negative control

- **Purpose**: Make the guard's coverage measurable in **shapes**, and tighten it on structure only.
- **Requirements**: FR-013, FR-014, FR-015; C-006, C-011; SC-011, SC-012.
- **Surfaces**: `tests/architectural/test_egress_consent_boundary.py`;
  `tests/architectural/_baselines.yaml:347-375`.
- **Depends on**: none.
- **Risks**: a zero delta must be **written down** as *"the only demonstrated bite is the synthetic
  case"* rather than passing as a success (H9). Every `xfail` carries `strict=True` (C-011) —
  `pytest.ini` sets no `xfail_strict` and `pyproject.toml:183-192` forbids a
  `[tool.pytest.ini_options]` block, so the default is non-strict and a "pinned hole" that starts
  passing would report `XPASS` and stay green.

### IC-05 — Termination: the counter, then the backstop

- **Purpose**: Make a non-terminating loop red by name and by count, and give the harness a backstop
  that produces a **named red**, not a killed job.
- **Requirements**: FR-016, FR-017, FR-018; NFR-003, NFR-007; SC-013…015.
- **Surfaces**: `tests/delivery/test_dispatch_window_consent_3030.py`; `pytest.ini` and/or
  `.github/workflows/ci-quality.yml`; `scripts/mutants/`.
- **Depends on**: FR-018 **strictly before** FR-016/017.
- **Risks**: pytest-timeout's thread method killed a `#3030` session mid-run and produced no summary
  and therefore no verdict; the signal method reds with a traceback. `ci-windows.yml` has no
  `SIGALRM` — state what method it gets and what its failure mode is, do not assume parity.

### IC-06 — The `/tmp` root-walk artifact

- **Purpose**: Turn a machine-specific failure into a message that names the offending directory,
  without letting a hostile machine delete coverage of a consent invariant.
- **Requirements**: FR-012; C-001; SC-016.
- **Surfaces**: `tests/sync/test_sync_consent_default_deny.py:127-152`.
- **Depends on**: none.
- **Risks**: C-001 is absolute — no change to `locate_project_root` /
  `resolve_checkout_sync_routing_readonly`, and none to `SPECIFY_REPO_ROOT`'s precedence. The
  existing test never asserts `SPECIFY_REPO_ROOT` is unset (it only `delenv`s `SPEC_KITTY_HOME`),
  and that env var is tier-1 authoritative in `core/paths.py`.

## Work packages

> Ownership below is **binding on `/spec-kitty.tasks`**. `owned_files` is enumerated explicitly per
> C-007, **every new literal path carries a `create_intent` entry** (see the ownership map), and
> every WP has a lane entry pre-allocated. A WP's Definition of Done is stated as *measurable
> evidence*: what must red first, and which count line must be quoted.
>
> **Thirteen work packages. WP08 is retired** (see the scope-cut note); the sequence runs
> WP01…WP07, WP09…WP14 and the gap is deliberate.

| ID | Goal (one line) | FRs | Lane | Blocked by |
|---|---|---|---|---|
| **WP01** | Commit a one-command, two-env-var reproducer for the `#3115` CLI red | FR-001 | lane-a | — |
| **WP02** | Pin the render surface (**≥ 240**, singletons only) at the conftest seam that already owns the console | FR-002 | lane-b | WP01 |
| **WP03** | Guard the width by **named** singleton, and prove flattening cannot repair the fold | FR-003, FR-004 | lane-c | WP01, WP02 |
| **WP04** | Inventory the `tests/sync/` cone's process-globals and thread seams | FR-006 | lane-d | — |
| **WP05** | Autouse leak guard that fails the polluter, scoped to WP04's inventory | FR-007 | lane-e | WP04 |
| **WP06** | Attribute the `sleep`-count failure on its own evidence, within budget, above a recorded floor | FR-005 | lane-f | WP04 |
| **WP07** | Resolve the `reset_token_manager()` hardening, both directions measured, **and apply the verdict** | FR-009 | lane-g | WP01, WP02 |
| ~~**WP08**~~ | ~~Converge 22 `_isolated_home` definitions to one owner~~ — **RETIRED, cut by operator decision after the post-plan squad. Number not reused.** | ~~FR-008~~ | — | — |
| **WP09** | `/tmp` root-walk: name the offender, and pin the invariant filesystem-independently | FR-012 | lane-h | — |
| **WP10** | Egress guard: **count first**, state limit 8, add two positional shapes, tighten only at zero FPs | FR-013, FR-014, FR-015 | lane-i | — |
| **WP11** | Counter pin on the dispatch loop, red-first under a non-terminating **hook-level** mutant | FR-018 | lane-j | — |
| **WP12** | A default per-test timeout with a stated method, derivation and enumerated blast radius | FR-016, FR-017 | lane-k | **WP11** (hard) |
| **WP13** | Prove the **13 enumerated node-ids** under a shard matching CI, quoting the job | FR-011 | lane-l | WP03, WP05, **WP07**, WP12 |
| **WP14** | **PLACEHOLDER** — the sync half's terminal state: remedy, or `deferred-with-followup` | FR-010 | lane-f | WP06 |

**What changed in this table post-plan**: WP08 retired; WP07 gains the apply half and moves off
lane-d; WP13's `blocked_by` swaps WP08 → WP07; and **the lane column is now the ownership-derived
lane, not a hand-authored intent** — see "Lane allocation" for why that distinction is load-bearing.

### WP01 — The reproducer

- **owned_files**: `scripts/repro_3115_render_width.sh` (**new**), `docs/development/testing-parallel.md`.
- **create_intent**: `scripts/repro_3115_render_width.sh`.
- **Goal**: `TERM=dumb FORCE_COLOR=1`, one file, one process, no xdist.
- **Collected counts, measured at planning time and binding on the count lines below.** The earlier
  draft attributed `1 failed, 3 passed` / `4 passed` to the **doctor** file. Re-measured with
  `pytest --collect-only -q` on a tree level with `bb2020fea9`:
  `tests/cli/commands/test_sync_status_per_project_3030.py` collects **4**;
  `tests/cli/commands/test_sync_doctor_per_project_3030.py` collects **12** (unchanged under
  `-m "fast and not windows_ci"`). **The four-test count line belongs to the status file.** Every
  count line in this WP's evidence is quoted **beside its file's collected count** (NFR-008); a count
  line that does not reconcile against the collected count is not evidence and is re-measured, not
  argued about.
- **DoD (evidence)**:
  - Red first, on `bb2020fea9`: `pytest tests/cli/commands/test_sync_status_per_project_3030.py`
    under the two env vars, output to a **file**, tail read (NFR-003). Count line
    `1 failed, 3 passed` quoted beside the collected count **4**. Assertion text quoted and it must
    be the per-file assertion text quoted verbatim from source — ``<uuid> is in the journal but `status` did not name it`` (backticks, `test_sync_status_per_project_3030.py:154`) or `<uuid> is in the journal but doctor did not name it` (no delimiters, `test_sync_doctor_per_project_3030.py:174`); they differ, and neither is normalised. A `TypeError`, fixture error,
    collection error or **empty output file** satisfies nothing. `Queue 0 event(s)` is **excluded** —
    it renders from `OfflineQueue().size()` (`sync.py:5182-5185`) on the green path too.
  - Independently repeated for `test_sync_doctor_per_project_3030.py`, whose count line is
    `1 failed, 11 passed` beside the collected count **12** — **not** `1 failed, 3 passed`.
  - **Determinism — rewritten so it can fail** (post-plan squad, F3). The old criterion ("three
    consecutive runs, same node-id") was **trivially satisfied**: `pytest-randomly` is not installed
    on this tree (`importlib.util.find_spec("pytest_randomly")` → `None`; absent from
    `pyproject.toml:101-113` and from every workflow), so nothing randomises order and repetition
    cannot go the other way. Green for the wrong reason, in the mission built to eliminate that. The
    WP reports **both** of:
    - (a) *the stability observation, no longer load-bearing*: three consecutive runs, same node-id,
      **same assertion text byte-for-byte**, same collected count, all three quoted; and the run's
      own `plugins:` header line quoted, so the ordering-plugin state is a measurement rather than an
      assumption.
    - (b) **the falsifiable clause**: the red reproduces with the failing case selected **alone by
      node-id** — `TERM=dumb FORCE_COLOR=1 pytest '<file>::<node-id>'` — same assertion text,
      **collected count 1**. A red that needs its file-siblings to run first is order-dependent,
      falsifies "two environment variables and one file", and fails C-004. **This is the clause that
      must be able to red, and it is what the determinism claim rests on.**
  - **Control**: the same command `+ TTY_COMPATIBLE=0` on the base commit quotes `4 passed` for the
    status file (and `12 passed` for the doctor file) — this is what separates "the width is the
    cause" from "this file is broken".
  - NFR-005: wall clock under 2 minutes, and the documented command is **one line**.
- **Forbidden**: editing any test file; `COLUMNS`; xdist. (`-p no:randomly` is pointless rather than
  forbidden — **C-005 is struck**; if any run uses it, say so and state why, but it changes nothing
  on this tree.)

### WP02 — The render seam

- **owned_files**: `tests/conftest.py`, `scripts/mutants/disable_render_seam_3115.py` (**new**).
- **create_intent**: `scripts/mutants/disable_render_seam_3115.py`.
- **Goal**: extend `_plain_cli_console_seam` (`tests/conftest.py:307-329`) to pin the render surface
  as well as the colour — **both** `width` and `height` (or `TTY_COMPATIBLE=0`, or
  `force_terminal=False`), set → `yield` → restore in `finally` (C-002). **Never `COLUMNS`** (C-012).
- **Two hard constraints on the pin, both from post-plan measurements:**
  - **The width must be ≥ 240** (F2). `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`
    passes `env={"COLUMNS": "240"}` and is **live**: under `CliRunner` in the default environment
    `is_terminal` is False, the `is_dumb_terminal` early return does not fire, and `COLUMNS` *is*
    consulted. An explicit size below 240 narrows that test's surface below what it asks for. The
    four measured trap values below were taken at 220; the **shipped** value is ≥ 240 and the
    docstring states both.
  - **Pin the singletons only; exempt the explicitly-sized specials** (F1). `CliConsole._instances`
    (`src/specify_cli/cli/console.py:49`) also holds three deliberately-sized consoles —
    `src/specify_cli/cli/commands/charter/list_cmd.py:26` (`width=200`),
    `src/specify_cli/cli/commands/glossary.py:46` (`width=120`),
    `src/specify_cli/cli/commands/docs.py:43` (`width=120`, stated load-bearing at `docs.py:40-42`).
    A blanket `size = (W, H)` walk overwrites all three. The seam pins `console` and `err_console`
    (`console.py:126-127`), **or** walks `_instances` while skipping any instance constructed with an
    explicit `width=`. Whichever it chooses, it states which and why.
- **DoD (evidence)**:
  - Both directions on **one commit**: WP01's falsifier greens (count line quoted **beside its
    collected count** — `4 passed` / 4 for the status file, `12 passed` / 12 for the doctor file);
    the same command with the seam disabled **by the plugin** reds with WP01's exact assertion text
    (`1 failed, 3 passed` / 4, `1 failed, 11 passed` / 12).
  - **The plugin obeys the corrected mutant contract** (see "The mutant-plugin contract" above, and
    C-003): loaded with `-p disable_render_seam_3115` under `PYTHONPATH=scripts/mutants` — **the
    `-p` flag is quoted in the evidence**, because `PYTHONPATH` alone loads nothing; neutralising at
    **hook level** (`pytest_fixture_setup` intercepting `_plain_cli_console_seam`, or
    `pytest_configure` unsetting the pin), **never** by defining a same-named fixture, which loses to
    the conftest one; asserting its own binding; reporting the **per-site split**; and **failing
    loudly if the seam it neutralised was never invoked**. A green run under a plugin that suppressed
    zero sites proves nothing about the seam.
  - The seam's docstring records the four measured values verbatim (no width → `(80, 25)`;
    `width=220` alone → `(80, 25)`; `width=220, height=50` → `(220, 50)`; `TTY_COMPATIBLE=0` →
    `(220, 25)`), states the **shipped** value and why it is ≥ 240, cites
    `tests/specify_cli/cli/commands/_help_snapshot.py`, **names the `#3115` victim files it covers**,
    and **names the two consoles it does not reach** — `src/specify_cli/cli/helpers.py:234` and
    `src/specify_cli/cli/logging_bootstrap.py:92`, both constructed *inside functions* and therefore
    born after the seam's setup-time walk. That gap is **stated**, not left for a non-zero inspected
    count to conceal.
  - **Blast radius**: the golden `--help` snapshot suite,
    `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` **and
    `tests/specify_cli/cli/commands/charter/test_activation_layout.py`** run before and after with
    their **collected counts** quoted; any changed outcome is reconciled, never absorbed.
- **The `COLUMNS` note is withdrawn — nothing is passed forward.** The earlier draft had WP02 record
  that the seam makes three `COLUMNS` sets "provably dead" and hand the removal to WP08. **That is
  wrong and WP08 no longer exists.** F2 measured those sets **live** on the non-dumb path. WP02
  records the *correct* finding — *inert on the failing path, consulted on the passing one* — in the
  seam's docstring, and **no work package removes or annotates them.** WP02 still does not touch
  those files.

### WP03 — Width guard + the forbidden remedy proved forbidden

- **owned_files**: `tests/architectural/test_cli_console_render_width.py` (**new**),
  `tests/cli/commands/test_render_fold_not_repairable_3115.py` (**new**),
  `tests/cli/commands/fixtures/render_width_3115/**` (**new — declared as a glob**, because
  `tests/cli/commands/fixtures/render_width_3115/` is a *directory*: a literal directory path with no
  repo match is a hard `exit 1` at `/spec-kitty.tasks`
  (`src/specify_cli/ownership/validation.py:384-449`, raised at
  `src/specify_cli/cli/commands/agent/mission_finalize.py:998-1006`), whereas a glob degrades to a
  soft warning), `tests/_arch_shard_map.py`.
- **create_intent** (M3): `tests/architectural/test_cli_console_render_width.py`,
  `tests/cli/commands/test_render_fold_not_repairable_3115.py`,
  `tests/cli/commands/fixtures/render_width_3115/capture_width80.txt`,
  `tests/cli/commands/fixtures/render_width_3115/capture_width80.provenance.json`,
  `tests/cli/commands/fixtures/render_width_3115/capture_pinned.txt`,
  `tests/cli/commands/fixtures/render_width_3115/capture_pinned.provenance.json`. The four fixture
  files are named concretely so the intent is a commitment rather than a directory-shaped promise;
  the glob in `owned_files` is what keeps the write scope honest if the capture set grows.
- **Why `tests/_arch_shard_map.py` is owned here**: `tests/architectural/test_arch_shard_marker_completeness.py`
  proves the arch shard partition is **total**. A new file under `tests/architectural/` with no
  assignment row reds that guard. WP03 is the only WP adding an arch test file, so it owns the map
  outright.
- **DoD (evidence)**:
  - FR-003 red first: with WP02's seam disabled by the plugin (loaded with `-p`, neutralising at hook
    level, reporting a **non-zero** suppressed count — C-003's corrected contract), the guard reds
    naming **the console, its measured `size.width`, and the identifier length** it compared against.
  - FR-003 positive control — **named singletons, not a count** (post-plan squad, F1). With the seam
    in place the guard passes **and asserts, by object identity, that it saw
    `specify_cli.cli.console.console` and `specify_cli.cli.console.err_console`**
    (`console.py:126-127`). A non-zero inspected count is **not** sufficient: `_instances` is a
    `WeakSet` that also holds three deliberately-sized specials, so a count of 3 is satisfiable with
    both singletons absent. Alongside the identity assertion it prints: the inspected count; the
    longest asserted identifier length; the **exempted** specials by `module:line` with their widths
    (`list_cmd.py:26` 200, `glossary.py:46` 120, `docs.py:43` 120); and, as a **named gap**, the two
    consoles constructed inside functions that no setup-time walk can reach —
    `src/specify_cli/cli/helpers.py:234` and `src/specify_cli/cli/logging_bootstrap.py:92`. The gap
    is printed on the **passing** path, so it is visible in a green run rather than only in a red
    one.
  - FR-003 **detects and fails; it does not repair** (H8). Rot control: if `_instances` or the seam
    is renamed, moved or deleted, the guard fails loudly rather than silently inspecting nothing.
  - **FR-004 capture provenance** (post-plan squad). Each committed capture carries a sidecar
    (`*.provenance.json`) recording: the **exact command** that produced it; the **commit** it was
    taken at (`bb2020fea9`); the `TERM` / `FORCE_COLOR` / `TTY_COMPATIBLE` / `COLUMNS` values in
    force; and the **observed `Console.size` tuple** at capture time. A capture with no provenance is
    a recollection, and a fixture nobody can re-derive is the same shape as a gate that prints like a
    pass. A meta-assertion reds if a capture file exists without its sidecar.
  - FR-004: after **full** whitespace collapse (`re.sub(r"\s+", " ", out)`) of the committed
    80-column capture, the uuid is *still* not a substring, and the test **reports the number of
    characters the fold interleaved** between the two fragments.
  - **FR-004 in-file positive anchor** (post-plan squad). "The uuid is not a substring" is satisfied
    just as well by a capture that lost the uuid **entirely**, which would make the test trivially
    true and silently wrong. So the same test additionally asserts, against the 80-column capture:
    (i) **both** uuid fragments **are** present; (ii) their **concatenation equals the uuid**; and
    (iii) the **interleaved character count is > 0**. Each of the three is a separate assertion with
    its own message, so the failure names which one broke. The identical substring assertion against
    the pinned-width control capture **finds** the uuid — so the test discriminates across two
    captures *and* is anchored inside the one it is really about.
  - Both new test files must be selected by a live CI gate (see risk R6) — state which gate and its
    marker, **with the collected count of that gate's selection** before and after the files land
    (NFR-008); "the marker is right" without a collected count is the `exit 5` shape.

### WP04 — The `tests/sync/` process-global inventory

- **owned_files**: `docs/development/process-global-inventory-3115.md` (**new**),
  `docs/development/toc.yml`, `docs/development/3-2-page-inventory.yaml`.
- **create_intent** (M3): `docs/development/process-global-inventory-3115.md`.
- **Why the docs plumbing is owned here**: `docs/development/3-2-page-inventory.yaml` is a
  **generated lockfile** (`scripts/docs/inventory_lockfile.py`, ADR 2026-06-27-1 D1) guarded by
  `tests/docs/test_inventory_path_stable.py`, and `docs/development/toc.yml` is the nav. A new page
  needs frontmatter (`title`/`description`/`doc_status`/`updated`/`type`/`related`, per
  `docs/development/testing-parallel.md:1-13`), a `toc.yml` entry and a lockfile **regeneration**.
  WP04 is the only WP adding a page, so it owns all three; WP01 only appends a section to an existing
  page and touches neither.
- **DoD (evidence)**: scope is the `tests/sync/` cone **only** (the CLI cone is excluded — its
  failure has a measured non-global cause). Each entry carries the **four mandatory values**:
  (1) module and symbol; (2) `reset seam: <name>` / `no reset seam` / `not reachable`; (3) who calls
  that seam, or `nobody`; (4) whether `test_429_respects_retry_after`'s outcome **depends** on it —
  `depends` / `does not depend` / `undetermined`, with the evidence. The **count of modules scanned**
  is stated and a **per-bucket count** is given for each of the four values. A grep-shaped deliverable
  with no dependence column does not close this WP.
- **Survives a failed hunt.** This is the map; FR-010's deferral inherits it.

### WP05 — The sync leak guard

- **owned_files**: `tests/sync/conftest.py` (**strictly excluding `:242-259`**),
  `tests/sync/test_leak_guard_probe_3115.py` (**new**).
- **create_intent** (M3): `tests/sync/test_leak_guard_probe_3115.py`.
- **Note on that new file**: it is declared so ownership and the lane entry exist, but see the probe
  clause below — the **preferred** outcome is that this file is a thin harness pointing at a **real**
  inventoried leak, not a synthetic leaker. An owned file with no diff is legal.
- **Explicit prohibition, stated in the brief in these words**: *do not read, edit, refactor or
  "improve" the filename-token consent-grant fixture at `tests/sync/conftest.py:242-259`
  (`protected = ("consent", "capture_gate")`). It is out of scope, it is **armed** — replacing the
  token guard with a marker reds three `test_runtime.py` tests whose natural remedy would undo
  `#3030`'s T028 — and it needs its own mission.*
- **DoD (evidence)**:
  - Autouse guard snapshots the globals **and the live-thread set** that WP04's inventory marks
    reachable, and **fails the test that leaves them dirty**, naming the symbol (or the thread's
    `name` and target) and the node-id.
  - **Red first — the contradiction resolved** (post-plan squad). FR-007 forbids *"a purpose-written
    file that satisfies the criterion by construction"*, and the earlier draft of this WP named
    exactly that file as the red-first mechanism. The order of preference is now **binding**:
    1. **Bite a real inventoried leak from WP04.** An existing test in the `tests/sync/` cone that
       WP04's inventory marks as leaving an inventoried entry dirty is **named by node-id** and
       **failed by the guard on that test**. The probe file is then a harness (selection + assertion
       on the guard's own report), not a leaker.
    2. **Only if WP04's inventory surfaces no such test** may a synthetic probe be used — and then
       the limitation is written down **in WP10's exact voice**: *"the only demonstrated bite is the
       synthetic case"*, verbatim, in the probe file's docstring **and** in the WP's transition note.
       Recording it is a pass; passing it off as a demonstrated bite is not.
    Either way the probe mutates **exactly one inventoried entry and nothing else**, and the **probe**
    carries the failure, not a later victim.
  - **The designated control-your-diagnostic case runs FIRST**, before the guard's verdict on
    anything else is trusted: point the guard at
    `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s `wiring` fixture — the
    known `reset_adapters()` leak, whose answer is already known — and **quote the outcome**. A guard
    that does not flag the known leak is an invalid probe, and every later verdict from it is void.
    (Standing rules, *"Control your diagnostic, not just your test"*.)
  - Positive control: a clean selection is **not** flagged, and the guard reports how many tests it
    inspected **and which inventory entries it did not watch, with the reason** (H8, NFR-008).
  - Scoped to WP04's inventory, **not** to WP06's answer — it ships whether or not WP06 converges.
  - Rot control: a renamed/moved/deleted watched symbol fails loudly.
  - NFR-006: added wall clock over the `fast-tests-sync` selection measured before/after at the same
    worker count and the same coverage state. Over 5% → change the guard's **implementation**, never
    its reach.
  - NFR-004: probe runs are sequential, or explicitly partitioned by `SPEC_KITTY_HOME` and port range.

### WP06 — The `sleep`-count attribution

- **owned_files**: `tests/sync/tracker/test_saas_client.py`,
  `scripts/mutants/attribute_sleep_count_3115.py` (**new** — named concretely rather than as
  "`scripts/mutants/` (its own files only)", which is not a declarable path).
- **create_intent** (M3): `scripts/mutants/attribute_sleep_count_3115.py`.
- **A FLOOR, recorded before the budget starts** (post-plan squad — this WP was previously closable
  with **zero test runs**, its non-converging branch requiring only self-reported hours and a
  self-reported mechanism list). Before any of the 6 hours are counted, WP06 records **one** of:
  - **(F-a)** the symptom **observed red locally**, with its failure text quoted verbatim
    (`AssertionError: Expected 'sleep' to be called once. Called <n> times.`), the exact selection
    that produced it, and that selection's **collected count**; or
  - **(F-b)** an explicit written statement that **it could not be reproduced locally**, enumerating
    every selection tried with each one's **collected count** and outcome — file-level, cone-level,
    with and without `-n auto --dist loadfile`, with and without the daemon-spawning siblings.

  Neither branch may be closed without one of these two on the record. "I could not reproduce it" is
  admissible; "I could not reproduce it" *without the list of what was tried and what each collected*
  is not.
- **DoD (evidence)**: a written attribution naming **(i)** a leaked live thread and its start site,
  **or (ii)** a specific other mechanism, supported by a reproduction that **shows the call count
  moving** — the count before and the count after, both quoted with their assertion texts (NFR-007).
  **Each excluded mechanism carries a named exclusion measurement** — the command run, the collected
  count, and the observed `sleep` call count — not an argument from structure. (The two legs already
  closed in advance by FR-005 are *arguments from structure*, and they are the only two permitted to
  be.) Budget: **at most 6 agent-hours and at most 3 candidate mechanisms** measured after WP04's
  inventory is complete and after the floor is recorded; hours spent and mechanisms tried are
  reported (FR-010).
  - **Explicitly permitted**: "the two symptoms have two different causes."
  - **Explicitly forbidden**: adopting the issue's *"common shape"* sentence as the finding; funding
    the module-global-backoff leg (structurally impossible) or `_poll_operation` threading (nothing
    in the tree threads it).
  - **Narrative goes to the PR body and to `notes/` via the orchestrator on the mission branch** —
    a lane may not write `kitty-specs/` (C-010). The finding is recorded *at the site* in the victim
    file's docstring, in the voice `_advancing_clock`'s docstring already uses (`:32-50`).

### WP07 — The token-manager verdict

> **Re-scoped by the cut.** WP07 previously owned **no test file** — it measured, and WP08 applied.
> WP08 is retired, so **WP07 now measures *and* applies**, and it becomes the sole owner of the five
> `578a659162` files. That is still one live agent in those files (C-007); it is simply the same one
> twice rather than two in sequence.

- **owned_files**: `scripts/mutants/neutralise_reset_token_manager_3115.py` (**new**), and the five
  files of `578a659162`: `tests/cli/commands/test_sync_doctor_per_project_3030.py`,
  `tests/cli/commands/test_sync_status_per_project_3030.py`,
  `tests/cli/commands/test_sync_migrate_backfills_h4.py`,
  `tests/cli/commands/test_sync_purge_3030.py`,
  `tests/cli/commands/test_sync_doctor_consent_health_3030.py`.
- **create_intent** (M3): `scripts/mutants/neutralise_reset_token_manager_3115.py`. (The five test
  files exist; they need no intent.)
- **HARD PROHIBITIONS on those five files, stated in the brief in these words**:
  - *Edit the `reset_token_manager()` call sites' surrounding docstring/comment and nothing else.
    Do not remove, weaken, move or annotate the `monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)` lines
    at `test_sync_status_per_project_3030.py:83` and `test_sync_doctor_per_project_3030.py:72`.*
    The earlier plan called them "provably dead" and handed their removal to WP08; that finding was
    **wrong** (post-plan F2: `COLUMNS` is consulted on the non-dumb path, and
    `test_activation_layout.py:111` is live), WP08 is gone, and **the removal is not reassigned to
    WP07 or to anyone**. Touching them would drag the ≥ 240 render-width constraint into this WP; it
    belongs to WP02, where the pin is authored.
  - *Do not touch these files' `_isolated_home` fixtures.* FR-008 is cut; the count stays at 22.
- **DoD (evidence)**:
  - With `reset_token_manager()` neutralised **by the plugin** — obeying the corrected mutant
    contract in full: loaded with `-p neutralise_reset_token_manager_3115` under
    `PYTHONPATH=scripts/mutants` (**the `-p` flag is quoted in the evidence**), neutralising at
    **hook level** in `pytest_configure`, never as a same-named fixture, asserting its own binding —
    run **(a)** WP01's falsifier and **(b)** the same file at the pinned width. **All four count
    lines, each beside its file's collected count, and all four assertion texts are quoted.**
  - **The per-site split is mandatory and its shape is already measured.** All five `578a659162`
    files import `reset_token_manager` **function-locally, inside the fixture body, from the defining
    module** `specify_cli.auth.manager` — `test_sync_doctor_per_project_3030.py:62`,
    `test_sync_status_per_project_3030.py:73`, `test_sync_migrate_backfills_h4.py:57`,
    `test_sync_purge_3030.py:83`, `test_sync_doctor_consent_health_3030.py:70` — so a plugin patching
    `specify_cli.auth.manager.reset_token_manager` **does** bind at all five, and the fifth rot mode
    (`from X import f` rebinding by value) does not bite there. **Two other sites do bind eagerly by
    value via the package name** at module import — `tests/auth/integration/conftest.py:22` and
    `tests/auth/test_websocket_provisioning.py:28`, both
    `from specify_cli.auth import reset_token_manager`. They are **deliberately unpatched** (they are
    outside this WP's cone) and the plugin's report must **name them as deliberately-unpatched, not
    report them as zero**. An aggregate suppressed count is rejected.
  - **The null verdict needs a non-zero suppressed count.** The reset is load-bearing **only if**
    case (b) turns red with a named assertion; a red that is a `TypeError` or a fixture error
    satisfies nothing (NFR-007). An unchanged colour in both cases **is the finding** — recorded as
    "not load-bearing", not explained away — **but only from a run whose plugin reports a non-zero
    suppressed count across the five patched sites.** A null verdict drawn from a run that suppressed
    zero calls is a finding about the mutant, and it is void.
- **Output, and WP07 lands it itself**: the corrected docstring for the retained reset
  (defence-in-depth, not the fix) is written **at each of the five sites**, in the voice
  `tests/sync/tracker/test_saas_client.py`'s `_advancing_clock` docstring already uses (`:32-50`),
  quoting the measurement that produced the verdict. Deletion is acceptable **only** if shown inert
  **and** WP04's inventory shows nothing reads the singleton on that path.
- **Collected counts before and after** for each of the five files, quoted; the change is a docstring
  edit, so any moved count is a defect in the edit and is reconciled, not absorbed.
- **This WP closes `#3030`'s matrix row.**

### ~~WP08~~ — RETIRED (was: `_isolated_home` convergence)

> **CUT FROM SCOPE by operator decision, 2026-07-31, after the post-plan adversarial squad. The
> number WP08 is retired and is not reused.** `spec.md` carries the matching FR-008 tombstone. This
> section is retained, rather than deleted, so that the gap between WP07 and WP09 reads as a decision
> and so that everything the package used to carry is visibly re-homed rather than dropped.

**What it was**: hoist 22 `_isolated_home` definitions across 22 files to one root-scoped owner,
carry `reset_journal_cache()` and `reset_token_manager()` in the hoisted owner, apply WP07's verdict,
and remove the three "provably dead" `COLUMNS` sets. Acceptance was counted: `grep -c` 22 before, M
after.

**Why it was cut** — three lenses, independently, on `bb2020fea9`:

- **Seven incompatible shapes.** Three of the 22 files pin **no home at all**, and those three are
  the `#3115` victims (`test_sync_status_per_project_3030.py`, `test_sync_doctor_per_project_3030.py`,
  `test_sync_migrate_backfills_h4.py`). A root owner pinning `SPEC_KITTY_HOME` would change behaviour
  in exactly the files WP02/WP03 fix.
- **Contradictory env policies, documented as load-bearing in opposite words at their own sites.**
  Two files *set* `SPEC_KITTY_ENABLE_SAAS_SYNC="1"`, thirteen *delete* it —
  `tests/sync/test_body_drain_consent_3030.py:51-54` (*"leaving it set here keeps these tests honest
  about what they prove"*) versus `tests/specify_cli/sync/test_local_commit_consent_3030.py:78-82`
  (*"deleted rather than set … leaving the developer's own export in place would prove nothing either
  way"*). A single owner must silently overrule one of them.
- **Five call `reset_coalesce_strategy()`** — a constraint that appears **zero times** anywhere in
  this mission's dossier. A constraint the plan never names is one the WP would not carry.
- **Three fixture contracts** (14 × `-> None`, 7 × `-> Iterator[None]`, 1 × `-> Path`), and
  `tests/specify_cli/identity/test_identity_value_faults_3030.py:294-297` is a **class-method**
  fixture a root conftest cannot replace without changing fixture resolution.
- **The red-first criterion was internally contradictory**: a test asserting the fixture is "defined
  at most once" cannot pass at any M > 1, which this plan explicitly allowed.
- **The DoD's detector was the wrong instrument.** Collected counts do not move when a fixture *body*
  changes, so a dropped `reset_coalesce_strategy()` or a flipped arming policy is invisible — the
  counted acceptance was satisfiable by a deletion that makes isolation strictly worse.

**Where the work went**: a follow-up issue against `Priivacy-ai/spec-kitty`, carrying the **measured
equivalence-class evidence** in
[`notes/post-plan-squad-findings.md`](notes/post-plan-squad-findings.md). `spec.md`'s follow-up
candidates state how the successor must be scoped — equivalence classes first, and a **behavioural**
acceptance rather than a `grep -c`. The successor number is recorded on `#3115`'s matrix row at
mission close. One inherited sequencing note travels with it: **WP03's width guard must precede any
such convergence**, because it is the only guard that would catch a hoist changing the victim files'
render surface.

**Where each of WP08's obligations went — nothing is dangling:**

| WP08 obligation | Disposition |
|---|---|
| Hoist the 22 `_isolated_home` definitions | **Cut.** Count stays at 22 (verified: `grep -r "def _isolated_home" tests/` = 22). No WP adds, moves or removes one |
| Apply WP07's corrected `reset_token_manager()` docstring at the five `578a659162` sites | **Moved into WP07**, which now measures *and* applies. Same file set, still one live agent |
| Remove/annotate the three "provably dead" `COLUMNS` sets | **Dropped outright, and deliberately NOT reassigned.** F2 measured them **live** outside `TERM=dumb`. See the scope-cut note. WP02 gains the constraint that follows from it instead: the pinned width must be **≥ 240** |
| Own `tests/conftest.py` after WP02 | **Gone.** `tests/conftest.py` now has exactly one owner, WP02, and the sequential-handoff risk on that file disappears with it |
| Sit last in lane-a so no other agent is live in the victim files | **Gone.** WP07 is the only agent in those five files, in its own lane |
| Be WP13's last upstream dependency | **Replaced by WP07** in WP13's `blocked_by` |

### WP09 — The `/tmp` root-walk artifact

- **owned_files**: `tests/sync/test_sync_consent_default_deny.py`.
- **DoD (evidence)**: (a) a **filesystem-independent** pin — force the resolution seam to yield
  "unresolvable" and assert `is_sync_enabled_for_checkout()` is `False` — so a hostile machine cannot
  silently remove coverage of the invariant; (b) the existing walk-up test
  (`:127-152`) keeps its cwd-based form and gains an **asserted precondition** reporting the first
  ancestor carrying a `.git`/`.kittify` marker **and the value of `SPECIFY_REPO_ROOT`** (today it
  `delenv`s only `SPEC_KITTY_HOME` and never asserts `SPECIFY_REPO_ROOT`, which is tier-1
  authoritative in `core/paths.py`).
  Red first: with a marker planted above the tmp root, the current test fails on the **bare consent
  assertion**; after the change it fails **naming the offending ancestor**; the new pin passes in
  both environments. **C-001 binds: no production routing change.**

### WP10 — The egress guard

- **owned_files**: `tests/architectural/test_egress_consent_boundary.py`,
  `tests/architectural/_baselines.yaml`.
- **Why one WP**: all three FRs edit the same file (C-007). Why it also owns `_baselines.yaml`: the
  FR-015 measurement is the only thing in this mission that can move `egress_allowlist_files: 28`
  (`:368`) or `known_ungated_files: 0` (`:375`), and that reconciliation must happen in the same
  change as the matcher edit. **No other WP may edit `_baselines.yaml`.**
- **ORDER IS BINDING — re-ordered post-plan (F4).** The earlier draft let the WP restructure the
  scanner and then measure. Reversed:
  1. **FR-013** (limit 7 → 8, plus the meta-test) and **FR-014**'s two positional cases red-first.
     Neither depends on the measurement.
  2. **The `src/`-wide false-positive count is taken FIRST**, against the *candidate* predicate,
     **before any matcher edit**.
  3. **The scanner restructure is funded only if that count returns zero.** If it does not, the
     matcher is left alone and FR-014 lands as two `xfail(..., strict=True)` — **which is a pass**.
- **The measurement has already been run once, and its numbers are stated here so the WP does not
  re-derive the scoping decision** (it still re-runs and quotes its **own** count; a planning
  paragraph is not a measurement): over `src/`, the minimal rule catching adoption-gate case (B)
  yields **5 false positives**, arising in four named enclosing functions —
  `resolve_workspace_for_wp`, `locate_work_package`,
  `behind_commits_touch_only_planning_artifacts`, `get_wp_lane` — against **211 candidate sites
  across 13 files** in total. **So the expected outcome is: no tightening, two strict xfails, row
  `#3113` closed.** The WP starts from that expectation rather than from an intent to adopt.
- **Why this is a scanner restructure, not a branch edit** — stated so the cost is visible before it
  is committed to: the predicate needs enclosing-scope information that `_classify(node: ast.Call)`
  (`:309`) does not carry. `_classify` is reached from a flat `ast.walk(tree)` at `:347`, which
  discards the enclosing `FunctionDef`. The bare-`Name` branch (`:312-316`) is where the *decision*
  would live, but the *information* to decide with is not there. Threading the enclosing function's
  parameter set through the walk is the actual change. **That cost is paid only against a zero
  count.**
- **DoD (evidence)**:
  - FR-013: the limit list grows from **7** to exactly **8**; both counts stated; a meta-test asserts
    the entry exists so a future docstring trim reds. The cross-reference to
    `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md` is **one-directional** —
    that file belongs to a closed mission and is **not edited** (C-010).
  - FR-014 red first: on `bb2020fea9`, **both** new cases fail with `scanner went blind to
    transport-call` (`:938`), and each failure text is quoted. **Case (B)
    `def relay(post, u, payload, meta): return post(u, payload, meta)` is the adoption gate** — a
    matcher that passes (A) and fails (B) is blind in exactly the way `#3113` is about.
  - FR-015: sites / files / **false positives** over the whole of `src/` reported **before**
    adoption, the way the callee-agnostic rule was adopted (25 sites / 13 files / 0 FPs). **The
    command that produced the count and the count itself are both quoted** — a false-positive number
    with no reproducible command is a recollection. The sites the tightening **newly adds** are
    reported **separately** from the pre-existing ones. A zero delta is written down verbatim as
    *"the only demonstrated bite is the synthetic case"*. If the WP's own count differs from the
    **5 FPs / 211 sites / 13 files** recorded above, the discrepancy is **named and reconciled**, not
    silently preferred in either direction.
  - If false positives are non-zero: the matcher is left alone, the number is recorded in the
    docstring next to limit 8, and FR-014 lands as two `xfail(..., strict=True)` cases. **Either
    outcome is a pass; an unmeasured tightening is not.**
  - C-006: a tightening that cannot be expressed without an author-chosen identifier — including
    `_URL_ARG_NAMES` — is **rejected regardless of its false-positive count**.
  - C-011: `strict=True` explicit on every `xfail`.

### WP11 — The counter pin

- **owned_files**: `tests/delivery/test_dispatch_window_consent_3030.py`,
  `scripts/mutants/nonterminating_dispatch_3115.py` (**new**).
- **create_intent** (M3): `scripts/mutants/nonterminating_dispatch_3115.py`.
- **DoD (evidence)**:
  - Both loop-driving tests (`:157`, `:218`) gain a hard cap on the recorded batch count that reds
    **naming the count**, mirroring `DISPATCH_CALL_CAP = 25`
    (`tests/delivery/test_nfr002_loop_permanence_3030.py:69`, asserted `:154-157`).
  - **Red first is a consequence, not a threshold flip**: the non-terminating-loop **plugin** mutant
    — obeying the corrected contract (see "The mutant-plugin contract"): importable via
    `PYTHONPATH=scripts/mutants` **and loaded with `-p nonterminating_dispatch_3115`, with the `-p`
    flag quoted in the evidence** (`PYTHONPATH` alone loads no plugin); neutralising at **hook
    level** in `pytest_configure`, **never** as a same-named fixture; asserting its own binding;
    reporting the **per-site split**; and **failing loudly if the patched symbol was never called** —
    makes `_run_dispatch_batches` fail to make progress, and each test reds **on
    the counter, naming the count** — and specifically **not** on
    `Failed: Timeout (>Ns) from pytest-timeout`. A red whose text is the timeout means the counter
    did not bind.
  - Both measurements are reported: the threshold-flip one (proves the assertion fires) **and** the
    mutant one (proves it fires *on the defect*). **The mutant one is the acceptance.**
  - The rule is recorded in the file: *any assertion about termination needs a counter; the timeout
    is a backstop for the harness, not a substitute for the pin.*
- **Measured on a tree with NO global timeout.** This is the reason for the ordering constraint.

### WP12 — The timeout default

- **owned_files**: `pytest.ini`, `.github/workflows/ci-quality.yml` (the WP chooses derivation (a) or
  (b) and **states which**; it owns both files either way so the choice can be made from the
  measurement rather than from availability), `scripts/mutants/hang_a_fast_test_3115.py` (**new** —
  the deliberately non-terminating `fast` test used for the red-first below; it is a plugin, not a
  committed test file, so it cannot be collected by anything else).
- **create_intent** (M3): `scripts/mutants/hang_a_fast_test_3115.py`.
- **Blocked by WP11 — hard, non-negotiable.** With a global timeout in place, WP11's mutant reds on
  the timeout and the missing pin becomes unobservable.
- **This is the mission's only repo-wide package. It is the last code-changing WP merged.** Every
  lane cut before it re-merges the mission branch before its next measurement (NFR-009).
- **DoD (evidence)**:
  - The **method** is stated explicitly, not left to pytest-timeout's platform default. Red first: a
    deliberately non-terminating `fast` test **hangs** the selection on `bb2020fea9`. The hanging
    test is injected by `scripts/mutants/hang_a_fast_test_3115.py` under the corrected mutant
    contract — loaded with `-p hang_a_fast_test_3115` (the flag quoted), collecting/injecting at hook
    level, asserting its own binding, and **failing loudly if the injected test was never collected**
    (a "the selection ended fine" result from a run that never collected the hanging test is not a
    measurement). Green after: the same selection **ends and prints a summary line naming that
    test**. A run that ends with empty output does **not** satisfy this — it is the same "empty
    output is not a failure" trap one layer down.
  - **`pytest-timeout`'s `signal` method is verified to work under `xdist` on Linux** (post-plan
    squad, carried forward): probed at `--timeout=3 --timeout-method=signal -n 2` →
    `Failed: Timeout (>3.0s) from pytest-timeout`, a named red with a real summary and a correct
    elapsed time. **Caveat that binds the evidence**: the same run also emitted an
    `execnet gateway_base._thread_receiver` traceback, so the evidence must quote the **summary
    line**, never "the output was clean".
  - `ci-windows.yml` has no `SIGALRM`: state what method it gets and what its failure mode is.
  - The **chosen value, chosen method, chosen derivation (a)/(b), coverage state, and the measured
    maximum unmarked-test duration** are all stated, with a floor of **4×** that maximum.
    `--cov` is on for both fast shards (`ci-quality.yml:1132`, `:1543`) and inflates `--durations` —
    if the value is derived with coverage on, say so and justify against the coverage-on numbers.
  - Blast radius stated because `testpaths = tests`: 46 `slow` tests (ini definition: ">30 seconds")
    against ~15 `@pytest.mark.timeout` sites, and the opt-in selections that run them are ones the
    regression clause structurally **cannot** observe. Existing explicit marks override the ini
    default.
  - **Regression clause, enumerated not aggregate**: the first full CI run after the change lists
    **every job that inherited the new default** with its conclusion and **collected count**, and
    separately **every selection that did not run at all** with the reason. Zero tests newly red
    attributable to the timeout; any that are, are listed with their durations and either marked or
    the value raised. *"Nothing newly red" over a set that did not run is not a result.*
  - **No new pytest marker.** `timeout` is already registered in `pytest.ini`. WP12 is the sole owner
    of that file, and no other WP may add a marker there.

### WP13 — The shard proof

- **owned_files**: none (measurement WP; evidence goes to the PR body and, via the orchestrator on
  the mission branch, to `issue-matrix.json`).
- **Blocked by**: WP03, WP05, **WP07** (was WP08), WP12.
- **Expected gate no-op, stated in advance** (post-plan squad). WP13 owns **zero files**, so
  `_mt_resolve_pre_review_workspace` returns `None`
  (`src/specify_cli/cli/commands/agent/tasks_move_task.py:937-962`) and the pre-review regression
  gate will print `no_coverage — skipping the gate cheaply`. **That line is expected and is not
  evidence of anything.** WP13's `for_review` transition note must say so in those words and **name
  the manual evidence standing in for the gate**: the two shard runs below, with their job names,
  conclusions and collected counts. A transition note that lets the `no_coverage` line stand
  unremarked is the "mechanism reporting success for having done nothing" shape, one layer up.
- **DoD (evidence)** — every element of NFR-001, or it is not a measurement:
  - Worker count **quoted from the run's own xdist `gw0..gwN` header**, never inferred from the
    runner label; `--dist loadfile`; marker selection `-m "fast and not windows_ci"`; the exact file
    and `--ignore` selection copied from `ci-quality.yml:1124-1133` / `:1540-1546`; whether `--cov`
    was on; the **collected test count**.
  - **The 13 cases are enumerated here, by node-id, and each outcome is quoted from the run's own
    report** (post-plan squad — this WP previously checked only the shard's properties, so a case
    deselected by the marker or swallowed by one of the four `--ignore`s was invisible, with
    `|| test $? -eq 5` underneath). Taken from `#3115`'s own "Affected tests" list and resolved
    against `pytest --collect-only -q` at `bb2020fea9`:

    | # | Node-id (or group) | Reconciliation this WP owes |
    |---|---|---|
    | 1 | `tests/cli/commands/test_sync_status_per_project_3030.py::test_status_names_every_project_with_count_age_and_consent` | Exact; the WP01 falsifier's own case. File collects 4 |
    | 2 | `tests/cli/commands/test_sync_doctor_per_project_3030.py::test_doctor_names_every_project_with_count_age_and_consent` | Exact. File collects 12 |
    | 3-6 | `tests/cli/commands/test_sync_doctor_consent_health_3030.py` — the issue says **4 param cases**. At `bb2020fea9` the file's only parametrised test is `test_doctor_names_the_action_for_each_project_local_fault_kind`, which collects **3**: `[unparseable-…-REPAIR THE FILE'S SYNTAX]`, `[wrong_shape-…-MAKE THE DOCUMENT A MAPPING]`, `[unusable-…-CORRECT THE FIELD VALUE]`. File total: 15 collected | **A real discrepancy, to be reconciled and not absorbed.** The issue's fourth case is either a since-removed parametrisation or a fourth non-param case in that file. WP13 quotes the collected set, names which, and either identifies the fourth node-id or records its absence as a **named exclusion with the reason**. Reporting "3 of 4 passed" without saying which is missing does not close this |
    | 7 | `tests/cli/commands/test_sync_migrate_backfills_h4.py::test_the_consent_backfill_reports_records_it_could_not_resolve` | Exact |
    | 8-9 | `tests/cli/commands/test_sync_purge_3030.py::TestPurgeAll` — the issue says **2**; the class collects **7** at `bb2020fea9` | WP13 names **which two** the issue meant, or runs all seven and says so, quoting each outcome. "`TestPurgeAll` passed" without naming the cases does not satisfy this |
    | 10-12 | `tests/sync/test_consent_write_refusal_3030.py` — the issue says **3 param cases**. The only 3-wide parametrisation in that file at `bb2020fea9` is `test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli[opt-in]` / `[opt-out]` / `[server]`. File total: 69 collected, including two 8-wide parametrisations | WP13 confirms this identification against the collected set, or names the three it ran and why |
    | 13 | `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` | The sync half's own case. Its outcome is reported **whether or not** WP06 converged; a red here is FR-010's business, not a reason to withhold the shard result |

  - **Any enumerated node-id absent from the collected set is named and explained** — marker-deselected,
    swallowed by one of the four `--ignore`s, or renamed since the issue was written — and an absence
    is closable **only** by naming it as a deliberate exclusion with its reason. A shard-level
    `N passed` with no per-node-id reconciliation does **not** satisfy this WP, because
    `|| test $? -eq 5` makes an empty collection a green job.
  - All 13 pass, **run twice** (SC-009), with each run's collected count quoted.
  - Any CI claim names the **job** (`fast-tests-cli`, `fast-tests-sync`), its **conclusion**
    (`success` / `skipped` / `failure`) and its **collected count**. A claim that `fast-tests-sync`
    passed is rejected if that job's conclusion was `skipped`. A workflow conclusion is not evidence.
  - `tests/sync` and `tests/cli` sessions are **not** run in parallel on one machine (NFR-004).
  - Re-measured at the merge commit if **WP12, WP06 or WP14** lands after WP13's first pass. WP06 and
    WP14 own `tests/sync/tracker/test_saas_client.py`, which carries node-id 13. WP13 is deliberately
    **not** blocked on them — FR-010's budget must not hold the shard proof hostage — but a pass
    taken before they land states the commit it was taken at, and node-id 13's outcome is re-quoted
    afterwards.

### WP14 — PLACEHOLDER: the sync half's terminal state

- **owned_files** (M4 — **fixed at planning time, not at dispatch**):
  `tests/sync/tracker/test_saas_client.py`. **Corrected post-plan**: the earlier draft left ownership
  "to be fixed at dispatch time", which does not produce the lane it claimed. Lane membership is
  computed **solely** from `owned_files` overlap (`src/specify_cli/lanes/compute.py:1-11`), so a
  placeholder with **empty** ownership lands in its own singleton lane — and outcome A would then
  write a file another lane's worktree owns. Declaring the file now puts WP14 in the **same lane as
  WP06**, which is the only thing that makes outcome A a within-lane transfer.
  - *Outcome A — cause identified*: the remedy lands in `tests/sync/tracker/test_saas_client.py`.
    If the attribution names a **thread-owning fixture in another file**, that file is **not** taken
    over: the remedy is expressed at the declared file and the other file's change is raised as a
    successor, because ownership may not be invented after planning (this is the whole point of the
    pre-allocation).
  - *Outcome B — budget exhausted*: the declared file is **left untouched** — an owned file with no
    diff is legal, and it is what keeps the lane entry valid. The deliverable is the successor issue
    (filed against `Priivacy-ai/spec-kitty`), inheriting WP04's inventory **and the harness's
    negative result** — which mechanisms were excluded and by what measurement — plus the
    `deferred-with-followup` verdict and the successor number on `#3115`'s matrix row.
- **Expected gate no-op on outcome B, stated in advance** (post-plan squad). Pre-allocating ownership
  closes only **one** of the two paths to `no_coverage — skipping the gate cheaply`: it fixes the
  workspace-resolution path (`tasks_move_task.py:937-962`), but outcome B produces **no diff**, so
  the changed-file path (`tasks_move_task.py:965-980`) returns an empty tuple and the gate folds to
  `no_coverage` anyway. **On outcome B the transition note must state that the printed line is
  expected** and name the manual evidence standing in for it: the successor issue number, WP06's
  recorded floor, and the enumerated exclusion measurements. On outcome A the gate should run
  normally, and if it prints `no_coverage` **that is a defect to investigate, not to absorb**.
- **DoD (evidence)**: the **only** permitted terminal states for this leg are (a) cause identified
  with a **both-directions** reproduction, or (b) explicit `deferred-with-followup` with the
  successor issue number recorded. **"Recorded as unproven" plus a green shard is not a permitted
  closure** — that is the exact path that produced `578a659162`.
- **Why it exists now**: the friction record's *"WPs created after planning have no lane, so two
  gates silently no-op"*. A WP added later defaults to `lane-a`, makes the lane-staleness gate fire
  inapplicably (advising a rebase of somebody else's approved lane), and makes the pre-review
  regression gate print `no_coverage — skipping the gate cheaply` on work that received no gate at
  all. Pre-allocating the lane entry is the whole fix.

## File-ownership map — one live agent per file (C-007)

> **Recomputed after the WP08 cut.** Every new literal path carries a `create_intent` entry, per M3:
> `validation.py:384-449` treats a literal `owned_files` path with zero repo matches as a **hard
> error** (raised at `mission_finalize.py:998-1006`, `typer.Exit(1)`), and a `grep -rn create_intent`
> over the earlier dossier returned nothing while nine new literal paths were declared —
> `/spec-kitty.tasks` would have hard-failed exit 1 before any code was measured. Globs degrade to a
> soft warning; literal paths do not.

| File | Sole owner | `create_intent`? | Note |
|---|---|---|---|
| `scripts/repro_3115_render_width.sh` | WP01 | **yes** | New |
| `docs/development/testing-parallel.md` | WP01 | no | Existing page; no `toc.yml` / lockfile change |
| `tests/conftest.py` | **WP02, alone** | no | **Changed by the cut**: WP08 was the second owner. The render seam is now the only thing this mission puts here, so the sequential-handoff risk on the root conftest disappears entirely |
| `scripts/mutants/disable_render_seam_3115.py` | WP02 | **yes** | New |
| `tests/architectural/test_cli_console_render_width.py` | WP03 | **yes** | New |
| `tests/cli/commands/test_render_fold_not_repairable_3115.py` | WP03 | **yes** | New |
| `tests/cli/commands/fixtures/render_width_3115/**` | WP03 | **yes**, four concrete capture + provenance files | **Declared as a glob**, because the path in the earlier draft was a *directory* — a literal directory path matching zero files is the hard error above |
| `tests/_arch_shard_map.py` | WP03 | no | Only WP adding a `tests/architectural/` file |
| `docs/development/process-global-inventory-3115.md` | WP04 | **yes** | New page |
| `docs/development/toc.yml`, `docs/development/3-2-page-inventory.yaml` | WP04 | no | Nav + **generated** lockfile; regenerated by `scripts/docs/inventory_lockfile.py`, never hand-edited |
| `tests/sync/conftest.py` | WP05 | no | **`:242-259` off limits** (armed, out of scope) |
| `tests/sync/test_leak_guard_probe_3115.py` | WP05 | **yes** | New; preferred shape is a harness over a real inventoried leak, not a synthetic leaker |
| `tests/sync/tracker/test_saas_client.py` | WP06, then WP14 | no | Same lane by construction (M4: WP14 declares it at planning time, which is what puts the two in one lane) |
| `scripts/mutants/attribute_sleep_count_3115.py` | WP06 | **yes** | New; named concretely — "`scripts/mutants/` (its own files only)" is not a declarable path |
| The five files of `578a659162` — `tests/cli/commands/test_sync_doctor_per_project_3030.py`, `…/test_sync_status_per_project_3030.py`, `…/test_sync_migrate_backfills_h4.py`, `…/test_sync_purge_3030.py`, `…/test_sync_doctor_consent_health_3030.py` | **WP07** | no | **Moved here by the cut** — WP08 was to apply the verdict WP07 measured. WP07 now does both; still one live agent. **Docstring edits only**; the `COLUMNS` lines at `…status…:83` and `…doctor…:72` are off limits, and so are these files' `_isolated_home` fixtures |
| `scripts/mutants/neutralise_reset_token_manager_3115.py` | WP07 | **yes** | New |
| `tests/sync/test_sync_consent_default_deny.py` | WP09 | no | Clean sole ownership |
| `tests/architectural/test_egress_consent_boundary.py` | WP10 | no | All three `#3113` FRs, one WP |
| `tests/architectural/_baselines.yaml` | WP10 | no | Sequenced **inside** the guard package. No other WP may edit it |
| `tests/delivery/test_dispatch_window_consent_3030.py` | WP11 | no | Clean sole ownership |
| `scripts/mutants/nonterminating_dispatch_3115.py` | WP11 | **yes** | New |
| `pytest.ini`, `.github/workflows/ci-quality.yml` | WP12 | no | Sole owner. **No other WP may register a marker or edit CI** |
| `scripts/mutants/hang_a_fast_test_3115.py` | WP12 | **yes** | New |

**Ten `create_intent` entries across seven WPs** — WP01 ×1, WP02 ×1, WP03 ×2 + 4 capture files,
WP04 ×1, WP05 ×1, WP06 ×1, WP07 ×1, WP11 ×1, WP12 ×1.

**Files nobody owns, and nobody may edit**: `tests/architectural/_gate_coverage_baseline.json` (see
R6), `kitty-specs/journal-project-consent-3030-01KYKWQS/**` (C-010), `src/**` (no production change
is required by any FR), `src/specify_cli/cli/commands/sync.py` (C-009 protects `overflow="fold"`),
**the 22 `_isolated_home` definition sites** (FR-008 is cut; the count stays at 22), and
**`tests/specify_cli/cli/commands/charter/test_activation_layout.py`** (its `COLUMNS=240` at `:111`
is live — F2 — and is WP02's blast-radius *subject*, not its write scope).

## Lane allocation

> ### How `lanes.json` is actually produced — corrected post-plan (M2, CRITICAL)
>
> The earlier draft said *"`lanes.json` is written by `/spec-kitty.tasks` from this table"*. **It is
> not.** `compute_lanes` derives lanes **solely from `owned_files` glob overlap**
> (`src/specify_cli/lanes/compute.py:1-11`: *"Two WPs are placed in the same lane when: 1. They have
> overlapping `owned_files` globs … Dependency edges do not collapse lanes by themselves. They are
> preserved as lane-level dependencies"*). A hand-authored lane table is an **intent statement**, not
> an input. **Lane intent must therefore be expressed through ownership**, and cross-lane ordering
> through `blocked_by`, which becomes `depends_on_lanes`.
>
> **And a cycle would not be caught.** `compute.py:618-630`'s docstring says cycle detection is
> "best-effort" and that *"callers that need cycle-accurate depths should validate the lane graph
> before invoking"*; the comment at `:639` says the cycle "is logged via" the caller's validation.
> **No such validation exists anywhere in `src/specify_cli/lanes/`** (verified: `rg -n "cycle|validate_lane"`
> over that package returns only docstrings and comments). A cyclic lane graph deadlocks at dispatch
> and allocates from the wrong merge base, silently.
>
> **The cycle the earlier draft contained**: WP02+WP08 shared `tests/conftest.py` → one lane; WP07
> owned only a mutant script → a different lane; WP08 blocked by WP07, WP07 blocked by WP02 → a
> **mutual `depends_on_lanes` edge**. WP08 is now cut, so the cycle is gone by removal — but the
> assignment is fixed **explicitly** below rather than by accident, and the table is re-derived from
> ownership so that what `compute_lanes` produces and what this plan claims are the same thing.

**The lanes below are the equivalence classes `compute_lanes` will derive from the ownership map
above.** No two WPs share an `owned_files` entry except WP06/WP14 (deliberately, per M4), so every
other WP is its own lane. Twelve lanes, thirteen WPs. Ordering is carried by `blocked_by`, not by
co-location.

| Lane | WPs (in order) | Write scope | depends_on_lanes | parallel_group |
|---|---|---|---|---|
| `lane-a` | WP01 | `scripts/repro_3115_render_width.sh`, `docs/development/testing-parallel.md` | — | 0 |
| `lane-b` | WP02 | `tests/conftest.py`, `scripts/mutants/disable_render_seam_3115.py` | `lane-a` | 1 |
| `lane-c` | WP03 | `tests/architectural/test_cli_console_render_width.py`, `tests/cli/commands/test_render_fold_not_repairable_3115.py`, `tests/cli/commands/fixtures/render_width_3115/**`, `tests/_arch_shard_map.py` | `lane-a`, `lane-b` | 2 |
| `lane-d` | WP04 | `docs/development/process-global-inventory-3115.md`, `docs/development/toc.yml`, `docs/development/3-2-page-inventory.yaml` | — | 0 |
| `lane-e` | WP05 | `tests/sync/conftest.py`, `tests/sync/test_leak_guard_probe_3115.py` | `lane-d` | 1 |
| `lane-f` | WP06 → WP14 | `tests/sync/tracker/test_saas_client.py`, `scripts/mutants/attribute_sleep_count_3115.py` | `lane-d` | 1 |
| `lane-g` | WP07 | the five `578a659162` files, `scripts/mutants/neutralise_reset_token_manager_3115.py` | `lane-a`, `lane-b` | 2 |
| `lane-h` | WP09 | `tests/sync/test_sync_consent_default_deny.py` | — | 0 |
| `lane-i` | WP10 | `tests/architectural/test_egress_consent_boundary.py`, `tests/architectural/_baselines.yaml` | — | 0 |
| `lane-j` | WP11 | `tests/delivery/test_dispatch_window_consent_3030.py`, `scripts/mutants/nonterminating_dispatch_3115.py` | — | 0 |
| `lane-k` | WP12 | `pytest.ini`, `.github/workflows/ci-quality.yml`, `scripts/mutants/hang_a_fast_test_3115.py` | `lane-j` | 1 |
| `lane-l` | WP13 | *(none — measurement only)* | `lane-c`, `lane-e`, `lane-g`, `lane-k` | 3 |

**Acyclicity, checked by hand because the tooling will not check it for you**: the lane-dependency
edges are `b←a`, `c←a,b`, `e←d`, `f←d`, `g←a,b`, `k←j`, `l←c,e,g,k`, plus one **intra**-lane edge
(WP14 ← WP06, inside `lane-f`, which `compute_lanes` sees as a self-loop and treats as a depth-0
anchor — harmless, and it is what makes WP14's ownership a within-lane transfer). No edge points
backwards. **There is no cycle.**

**Ordering rules that bind the orchestrator, not just the lanes:**

1. **WP11 before WP12.** They no longer share a lane (their `owned_files` are disjoint, so
   `compute_lanes` will not merge them). The ordering is carried by `blocked_by: WP11`, which becomes
   `lane-k depends_on_lanes lane-a…` — specifically `lane-j`. **This is a case where the earlier
   plan's "structural, not conventional" claim was resting on a lane co-location that the tooling
   would never have produced.** It is now carried by the dependency edge, which the tooling does
   honour.
2. **WP12 is the last code-changing WP merged.** Any lane cut before it merges the mission branch
   into its worktree **before its next measurement** and states the commit it measured at (NFR-009).
3. **Lane `for_review` transitions are taken ONE AT A TIME** (NFR-010). See R3.
4. Every lane **merges the mission branch into its worktree before its first measurement** and states
   its merge-base (NFR-009). This is the friction record's first entry, and this mission's own
   orchestrator already reproduced it once by creating the mission at `9189cf2b36`.
5. **If `/spec-kitty.tasks` produces a lane grouping different from the table above, the table is
   wrong and the computed grouping wins** — but the divergence is *reported*, because it means an
   `owned_files` entry overlaps in a way this plan did not intend.

## Critical path

```
WP01 ──► WP02 ──┬─► WP03 ─────────────────► WP13          ◄── CRITICAL PATH (either branch)
                │
                └─► WP07 ─────────────────► WP13          ◄── CRITICAL PATH (either branch)

WP04 ──► WP05 ─────────────────────────────► WP13
WP04 ──► WP06 ──► WP14
WP11 ──► WP12 ─────────────────────────────► WP13
WP09  (independent)
WP10  (independent)
```

**The critical path is WP01 → WP02 → (WP03 ∥ WP07) → WP13 — four sequential packages.** It was five
(WP01 → WP02 → WP07 → WP08 → WP13); **WP08's removal shortened it by one**, and WP03 and WP07 are now
co-equal branches of the same length rather than WP03 being a side-spur off a longer chain.

**Which of the two branches is heavier**: WP07. It gained WP08's applying half, it carries the
mutant with the strictest self-proof requirement in the mission (a null verdict is inadmissible from
a run with a zero suppressed count), and it is the package that closes `#3030`'s matrix row. WP03 is
two new test files, a shard-map row and two committed captures. Schedule accordingly, but neither can
start before WP02.

**WP11 → WP12 → WP13** is the second-longest chain and the one with the hard ordering constraint.
`lane-j` runs in `parallel_group` 0 alongside `lane-a`, `lane-d`, `lane-h` and `lane-i`, so it is not
on the critical path *unless* WP12 slips — at which point it becomes the critical path, because WP13
cannot take its final measurement over a tree that is about to gain a repo-wide timeout.

**Three lanes hold `parallel_group` 0 with no upstream at all** — `lane-h` (WP09), `lane-i` (WP10)
and `lane-j` (WP11) — plus `lane-a` (WP01) and `lane-d` (WP04). Five lanes can start immediately.

### Which WPs still land if the sync-half investigation stalls

FR-010 gives the sync-half investigation a budget (**6 agent-hours, 3 candidate mechanisms**) and a
blocking exit clause. Operationalised: **only WP06 and WP14 are affected. Everything else lands.**

| Unaffected — lands regardless | Why |
|---|---|
| WP01, WP02, WP03 | The CLI half's cause is **measured**. It has nothing to do with globals |
| WP04 | It is the **map**, not the answer. It needs no culprit and survives a failed hunt; WP14 outcome B inherits it |
| WP05 | Scoped to WP04's inventory, **not** to WP06's answer (H4). It ships either way |
| WP07 | Driven by the width falsifier, not by the sleep-count mechanism. **Now also the package that lands the FR-009 docstring**, so `#3030`'s row resolves regardless of the sync half |
| WP09 | Independent |
| WP10 | Independent (`#3113`) |
| WP11, WP12 | Independent (the timeout gap) |
| WP13 | Measures the 13 enumerated node-ids under a CI-matching shard; a stalled attribution does not change that selection. Node-id 13 (`test_429_respects_retry_after`) is **reported**, red or green — its colour is FR-010's business, not a reason to withhold the shard result |

**WP06 lands either way** — its negative result (which mechanisms were excluded and by what
measurement, above the recorded floor) is a deliverable, not a failure. **WP14 changes shape**:
outcome A (remedy) or outcome B (`deferred-with-followup` + successor issue). What is **never**
permitted is closing the sync half on a green shard while the cause is unidentified.
## Risk register — pre-decided workarounds

| # | Risk | Pre-decided workaround |
|---|---|---|
| **R1** | **Lanes cut from a stale base.** The friction record's first entry: a lane cut from a commit predating the mission's acceptance pins reported a clean 0-failure baseline while the tests defining success were absent. This mission's own orchestrator already did it once (created at `9189cf2b36`, 7 commits behind) | **Every lane merges the mission branch into its worktree before its first measurement and states the commit it measured at and its merge-base** (NFR-009). A baseline whose commit is unstated is **void** and is re-taken, not argued about. `spec-kitty` allocates the worktree; the merge is the lane's first action, before any pytest invocation |
| **R2** | **The pre-review regression gate's 300s cap is below the runtime of the suites this mission touches** (friction record: *"the suite this mission touches takes ~2 minutes on its own, so the gate could not complete"*). Gate `timed_out` refuses the transition | **Pre-authorised**: `--force` on the `for_review` transition **with the reasoning recorded in the transition note**, exactly as `#3030` did, **and** the equivalent evidence measured manually and quoted (count lines, not exit codes). The reasoning must state that the check was *inapplicable or unable to complete*, never merely inconvenient |
| **R3** | **The gate's serialisation lock degrades to no-lock after 5s** (`src/specify_cli/review/pre_review_gate.py:256`, `_LOCK_ACQUIRE_TIMEOUT_DEFAULT = 5.0`; "fallback-to-run" rationale at `:275-279`). Gate runs here take ~2 minutes, so a second lane transitioning concurrently **runs its suite anyway**, recreating the 16 recorded false reds from parallel `tests/sync` + `tests/cli` sessions | **Lane `for_review` transitions are taken ONE AT A TIME by the orchestrator** (NFR-010). Any gate red is **re-measured serially before it is believed**. This is a process rule the orchestrator enforces; no lane can enforce it for itself |
| **R4** | **`fast-tests-sync` is path-filtered and may not run at all.** It is gated on `needs.changes.outputs.sync` (`ci-quality.yml:1101`) and was **skipped** on run `30622853036`. The `\|\| github.event_name == 'push'` escape only fires on `main`/`develop`/`2.x` (`:39-42`), never on this branch | **Verified mitigation**: the `changes` filter's `sync` predicate includes `tests/sync/**`, and this mission edits `tests/sync/conftest.py` (WP05) and `tests/sync/test_sync_consent_default_deny.py` (WP09) — so the shard **will** run. **This must still be verified, not assumed**: SC-010 requires the PR to quote the job's own conclusion and collected count. If the job is `skipped`, no claim about it is admissible |
| **R5** | **`fast-tests-cli` tolerates `exit 5`** (`\|\| test $? -eq 5`, `ci-quality.yml:1545`) — a selection that collects nothing is a **green job** | Every claim about that shard quotes the **collected count** (NFR-008). A green `fast-tests-cli` with no collected count is not evidence |
| **R6** | **New test files can be born ungated.** `tests/architectural/test_gate_coverage.py`'s orphan ratchet reds on any new file that no CI gate selects (baseline: `tests/architectural/_gate_coverage_baseline.json`). WP03 adds two test files and WP05 adds one | The correct response is **to make the new tests gate-selected** (correct markers, correct directory), **never to widen the baseline**. `_gate_coverage_baseline.json` is on the nobody-may-edit list. Each WP adding a test file states which gate selects it and under which marker. WP03 additionally registers its arch file in `tests/_arch_shard_map.py` (`test_arch_shard_marker_completeness.py` proves the arch partition is total) |
| **R7** | **The docs lockfile / nav is a hidden shared file.** A new `docs/development/*.md` page needs frontmatter, a `toc.yml` entry, and a regeneration of the **generated** `3-2-page-inventory.yaml` (`scripts/docs/inventory_lockfile.py`), guarded by `tests/docs/` | Only **one** WP adds a page (WP04) and it owns all three files. WP01 appends to an existing page and touches neither. The lockfile is **regenerated by the script**, never hand-edited |
| **R8** | **The seam ships broken and green** by pinning `width` alone — measured: `width=220` alone still returns `(80, 25)` on a dumb terminal | WP02's DoD requires the plugin-disabled falsifier to red **and** the enabled one to green on one commit, with all four measured `Console.size` values quoted in the docstring (SC-003). A green that was never shown to be able to red is not a pass |
| **R9** | **The width guard passes vacuously** by inspecting zero consoles (`_instances` is a `WeakSet`) — **and, post-plan, by inspecting the *wrong* consoles**: a non-zero count is satisfiable by the three deliberately-sized specials alone, with both singletons absent from the weak set | FR-003 / NFR-008: the guard **asserts by identity that it saw `console` and `err_console`** (`console.py:126-127`), *then* prints the inspected count, the longest asserted identifier length, the exempted specials by `module:line`, and the two function-constructed consoles (`helpers.py:234`, `logging_bootstrap.py:92`) as a **named gap**. Rot control fails loudly if `_instances` or the seam is renamed, moved or deleted |
| **R9b** | **The width pin overwrites the deliberately-sized consoles** — `list_cmd.py:26` (200), `glossary.py:46` (120), `docs.py:43` (120, load-bearing per `docs.py:40-42`) — so the seam breaks three surfaces to fix one (F1) | WP02 pins **only the singletons**, or exempts any instance constructed with an explicit `width=`, and states which. Blast radius adds `test_activation_layout.py` to the before/after list |
| **R9c** | **The pinned width is set below 240** and narrows `test_activation_layout.py:111`'s live `COLUMNS=240` surface (F2) | WP02's DoD constrains the shipped value to **≥ 240** and requires the docstring to state it alongside the 220-based trap measurements |
| **R10** | **The sync leak guard becomes the polluter** by snapshotting state in a way that instantiates it | Its positive control **must include a run where nothing leaks and nothing is flagged**, and it reports which inventory entries it did **not** watch, with reasons |
| **R11** | **A mutation silently lies** — five recorded ways (standing rules): redundant second gate; `TypeError`s from a changed signature; a hard-coded value the tests vary; a branch unreachable on the local interpreter; `from X import f` rebinding by value | **Every** mutant in `scripts/mutants/` asserts its own binding and reports the **per-site split** when a symbol is reachable by more than one name. An aggregate count cannot distinguish "both sites mutated" from "one mutated, the other inert" |
| **R11b** | **A mutant is silently inert — the sixth way, and the one this plan itself committed** (M1, CRITICAL). Two independent mechanisms, both probed: (i) **`PYTHONPATH` alone does not load a pytest plugin** — the earlier draft said "loaded via `PYTHONPATH`" in five places and never mentioned `-p` or `PYTEST_PLUGINS`; (ii) **a same-named autouse fixture in a plugin loses to a conftest fixture** for items under that conftest's directory, so the obvious way to "disable the seam" binds nothing. Either way the run is green, and the green reads as a passing gate | **The corrected contract** (see "The mutant-plugin contract", and C-003): load with `-p <module>` under `PYTHONPATH=scripts/mutants` and **quote the `-p` flag in the evidence**; neutralise at **hook level** (`pytest_configure` / `pytest_fixture_setup`), never as a same-named fixture; assert the binding; report the per-site split; and **fail loudly if the patched symbol was never called**. **No verdict — least of all a null one — may be drawn from a run whose mutant reports a zero suppressed count.** Binds WP02, WP06, WP07, WP11, WP12 |
| **R16** | **The lane graph is cyclic, or diverges from this plan, and nothing catches it.** `compute_lanes` derives lanes from `owned_files` overlap only (`compute.py:1-11`); a hand-authored table is not an input. `compute.py:618-630` calls cycle detection "best-effort" and defers to caller validation that **does not exist** anywhere in `src/specify_cli/lanes/` — so a cyclic graph deadlocks at dispatch and allocates from the wrong merge base, silently | The lane table is **derived from the ownership map, not authored beside it**, and its acyclicity is checked by hand in "Lane allocation". If `/spec-kitty.tasks` produces a different grouping, **the computed grouping wins and the divergence is reported**, because it means an `owned_files` entry overlaps in a way this plan did not intend. Ordering that matters (WP11→WP12, WP02→WP07) is carried by `blocked_by`, which becomes `depends_on_lanes`, **never** by assuming two WPs will share a lane |
| **R17** | **`/spec-kitty.tasks` hard-fails exit 1 on a literal `owned_files` path that matches zero files** (`ownership/validation.py:384-449`; `mission_finalize.py:998-1006`). The earlier draft declared **nine** new literal paths and **zero** `create_intent` entries, none of them globs, so none would have degraded to the soft-warning branch | Every WP declaring a new file carries a `create_intent` entry — enumerated in the file-ownership map. The one **directory** path (`tests/cli/commands/fixtures/render_width_3115/`) is declared as a **glob** in `owned_files` plus concrete `create_intent` entries, since a literal directory path is the same hard error |
| **R12** | **A verification run measured in the tree being edited.** Four instances on `#3030` | Baselines run in a throwaway `git worktree` with `PYTHONPATH=$WT/src` or a dedicated venv **inside** the worktree (NFR-002) — `.venv/.../_editable_impl_spec_kitty_cli.pth` holds the **absolute path of the main checkout**, so a worktree using the main `.venv` imports the live tree and makes isolation *look* performed. Conclusions of **sameness** taken without this are **void** |
| **R13** | **The `done` gate cannot be satisfied per-WP** — `--to done` requires every issue row to hold a terminal verdict, so WPs park at `approved` even when finished and merged (friction record) | **Expected, not a defect to fight.** WPs park at `approved`; the matrix resolves at mission close. Budget for it rather than rediscovering it |
| **R14** | **Bulk-edit heuristics false-positive.** `#3030`'s spec scored 4/4 because it discussed a migration; the spec still uses "converge" and "hoist" **in the FR-008 tombstone and the scope-cut note**, which are now the only places those words appear as description rather than as instruction | Expect `--acknowledge-not-bulk-edit` on lane allocation. **The many-file edit the heuristic would have been reacting to (WP08, 22 files) no longer exists.** The largest remaining multi-file change is WP07's five-file docstring edit. If the gate fires, the answer is that this mission's own out-of-scope section forbids the migration the words describe, and the count it would police (`grep -r "def _isolated_home" tests/` = 22) is **unchanged before and after** |
| **R15** | **Known pre-existing failures get chased.** Six families are listed in `standing-rules.md` | If one appears in a run, **name it as pre-existing and move on**. Do not chase, do not fix in-PR, do not retry to green |

## Issue-matrix plan

`issue-matrix.json` is the **single canonical artifact** (`src/specify_cli/tasks/issue_matrix.py:9-11`);
**no `.md` render is emitted**. Verdict vocabulary is closed
(`src/specify_cli/cli/commands/review/_issue_matrix.py:65-68`): `fixed`, `verified-already-fixed`,
`deferred-with-followup`, `in-mission` — and `in-mission` is non-terminal: it is accepted at per-WP
`approved` but **rejected at mission `done`**.

**Three rows. No synthetic row. No `#0000`.**

| Row | Verdict at `done` | Evidence that closes it (`evidence_ref`) |
|---|---|---|
| **`3115`** | `fixed` **if** the sync half converges (WP06 names a mechanism with a moving call count); otherwise **`deferred-with-followup`** with WP14's successor issue number recorded | CLI half: FR-001 (reproducer, red-first + control + determinism), FR-002 (both directions on one commit), FR-003 (guard reds with the seam disabled, prints its inspected count), FR-004 (whitespace collapse still fails, interleave count stated, both fragments anchored), FR-009 (four count lines with a non-zero suppressed count), FR-011 (shard, job conclusion, collected count, **13 node-ids reconciled**). **FR-008 is removed from this `evidence_ref`** — it is cut; the successor issue number is recorded on this row instead. **The timeout work rides this row**: `evidence_ref` additionally names **FR-016, FR-017, FR-018** |
| **`3113`** | `fixed` | FR-013 (limits 7 → 8, meta-test), FR-014 (**both** positional cases red on `bb2020fea9` with `scanner went blind to transport-call`; after the change both pass **or** both are `xfail(strict=True)`), FR-015 (sites/files/FPs over `src/` before adoption, new sites reported separately, zero delta written down verbatim). **Both FR-015 outcomes close the row** — the row does not depend on the tightening being adopted |
| **`3030`** | `verified-already-fixed` | **This row is the contentious one and FR-009 is what resolves it.** `#3030`'s consent fix merged; what was *unproven* was `578a659162` / `4f8e4ca781`'s token-manager hardening, whose own commit message says *"this is defensive hardening of a credible process-global … not a confirmed-necessary fix."* **WP07 measures it in both directions and records the verdict at the site itself** (WP08 was to do the recording; it is cut) — kept with a corrected docstring (defence-in-depth, not the fix) if inert, or kept as load-bearing with the measurement quoted. **A null verdict is admissible only from a run whose mutant reported a non-zero suppressed count** at the five function-local sites, and whose report named `tests/auth/integration/conftest.py:22` and `tests/auth/test_websocket_provisioning.py:28` as deliberately-unpatched rather than as zero. Either way the claim stops being unproven, which is what the terminal verdict asserts. **Only if WP07 cannot obtain a discriminating measurement** does this row fall back to `deferred-with-followup` with a successor number — it may **not** sit at `in-mission` |

**Why this row set is now safe.** The post-spec squad's C4 finding was that
`detect_issue_references` (`issue_matrix.py:88-95`) requires `^`, whitespace, `(` or `[` before the
`#`, and every `#3115`/`#3113` in the previous spec was inside backticks — so the mission's own
issues would get no row while `#3030` got one that had to be terminal. **Verified on the current
spec**: `spec.md:13` reads ``**Issues in scope**: #3115 (shard-parallel …`` — bare, whitespace-preceded,
detectable; `#3113` likewise. The three rows are nonetheless **hand-authored** rather than left to the
scaffold, because the scaffold cannot know which verdicts or `evidence_ref`s belong to them.

**Orchestrator action**: `issue-matrix.json` lives under `kitty-specs/` and is therefore written **on
the mission branch by the orchestrator**, never from a lane (`commit_guard.py:84-89`). Lanes deliver
evidence; the orchestrator records verdicts.

## Test strategy

Every rule below is a standing rule with a measurement behind it. They are not style preferences.

**Measuring**

- **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports `tail`'s
  status. Write full output to a **file** and read the tail of the file, or check `${PIPESTATUS[0]}`.
  **An empty output file is no measurement** (NFR-003).
- **Quote the `N passed` / `N failed` line**, never "exit 0". Quote it with its **assertion text**
  (NFR-007) — a tally moving is not evidence, and a `TypeError` from a changed signature is not
  evidence of the defect under test.
- **A killed run is neither a pass nor a fail.** Re-run it **narrowed**; do not explain it; check
  elapsed time against the `timeout` value before attributing it.
- **Print the input count beside any "all checks passed"** (NFR-008): consoles inspected, tests
  inspected, modules scanned, candidate mechanisms measured. This is a live hazard on this very
  branch — `fast-tests-cli` treats `exit 5` as success.
- **Worktree isolation, with the import path stated** (NFR-002): `PYTHONPATH=$WT/src`, or a dedicated
  venv created **inside** the worktree. Without it a worktree using the main `.venv` imports the live
  tree and manufactures sameness conclusions.
- **State the commit** every baseline was taken at, and the lane's merge-base (NFR-009).

**Sweeping**

- **Never run `tests/sync` and `tests/cli` sessions concurrently on one machine.** They spawn real
  daemons and `pgrep`/port-scan, so sibling sessions reap each other's — **16 recorded false reds**
  (NFR-004). **Fan out the coding, serialise the sweeps.** This binds WP05's probe runs (sequential,
  or explicitly partitioned by `SPEC_KITTY_HOME` and port range) and WP13's shard proof.
- Lane `for_review` transitions **one at a time** (NFR-010, R3).

**Proving**

- **Red first, and make the red a consequence, not a boolean.** A fix that cannot be shown to fail
  before it is applied is not a fix. Merely flipping a threshold below a legitimate value proves the
  assertion fires, not that it fires **on the defect** (FR-018 requires both measurements and the
  mutant one is the acceptance).
- **Include a positive control that must pass**, or "nothing broke" is indistinguishable from "the
  harness never ran the code" (FR-003, FR-005, FR-007 all carry one).
- **Control your diagnostic**: run any probe against a case whose answer you already know before
  trusting it. The mission's designated control case is
  `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s `wiring` fixture — the known
  `reset_adapters()` leak, fixed by *restoring* the default handlers rather than clearing (C-002).
- **Mutations are pytest plugins, never source edits, and never while a verification run is in
  flight** (C-003). **The loading contract is `-p <module>` with `PYTHONPATH=scripts/mutants`, and
  the `-p` flag is quoted in the evidence** — `PYTHONPATH` alone loads nothing. **Neutralise at hook
  level, never as a same-named fixture** — a plugin fixture loses to a conftest fixture. Every mutant
  **asserts its own binding**, reports the **per-site split**, and **fails loudly if the patched
  symbol was never called**. **No verdict may be drawn from a run whose mutant suppressed zero
  calls.** See "The mutant-plugin contract".
- **C-005 is struck.** `pytest-randomly` is not installed on this tree, so `-p no:randomly` is a
  no-op and forbidding it forbids nothing. The live rules that replace it: any run that disables or
  fixes ordering states the plugin, the seed and the reason; **and any determinism claim names a way
  it could have gone the other way** (WP01's node-id-alone re-run is this mission's instance).
- **The reproducer may not depend on the scheduler** (C-004). `--dist loadfile` assignment is dynamic
  and work-stealing.

**Hygiene**

- `git add <paths>`, **never** `git add -A` / `git add .` / `git commit -a`; `git status --short`
  before every commit; never `reset` / `checkout --` / `stash` / `rebase` on a shared branch —
  **report instead**. 13 files were lost to a shared index on `#3030` (C-007).
- **`ruff format` is not run** (C-008; `line-length = 164`, the repo is not clean under it). Only
  `ruff check` is meaningful.
- Every lane worktree is its own checkout. Disjoint file sets do **not** make a shared index safe,
  because `git add -A` is index-wide, not path-aware.

## Open decisions — carried, not resolved here

1. **What the `sleep`-count failure's mechanism is.** The patch target's process-wide reach is
   settled; two legs are closed in advance. What remains is *which live thread, started where, is
   sleeping inside the patch window*. WP06 answers it or WP14 exits. **Two symptoms, two causes is
   explicitly permitted.**
2. **Whether `_transmits_a_body` can be tightened on the structural property at zero false-positive
   cost.** The answer is a measurement over `src/` (WP10). Both outcomes are acceptable deliverables;
   deciding it here without the count would be the unmeasured adoption the guard's own history warns
   against.
3. **Timeout derivation (a) `addopts` vs (b) fast-job command lines.** Deliberately left to WP12's
   measurement. The plan fixes only the *constraint*: (a) is permissible only if `--durations` is
   actually collected over every selection that inherits the ini; otherwise (b), with the blast
   radius stated as the enumerated job list.

**Deliberately not open**, because the material decides them: what causes the `#3115` CLI reds
(measured — render width); global timeout vs per-test marks (**both**, with a division of labour —
the timeout is the harness backstop, the counter is the pin); harden vs document the `/tmp` artifact
(**harden, with the invariant separately pinned**).

## Out of scope — record, do not absorb

Everything in `spec.md`'s "Out of scope" section binds this plan unchanged. Restated for the lanes,
because these are the items an implementer is most likely to fix helpfully and wrongly:

- **The `_isolated_home` convergence (ex-FR-008 / ex-WP08).** **Cut by operator decision after the
  post-plan squad.** No lane adds, moves or removes an `_isolated_home` definition; the count stays
  at **22** and a diff that changes it is a scope violation. This is first on the list because it is
  the single most likely thing a well-meaning implementer would do on WP07's file set — four of the
  five `578a659162` files carry one. **They are read-only for the purpose of this mission.**
- **Removing or annotating the three `COLUMNS` sets** —
  `tests/cli/commands/test_sync_status_per_project_3030.py:83`,
  `tests/cli/commands/test_sync_doctor_per_project_3030.py:72`,
  `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`. The earlier plan called
  them "provably dead" and assigned their removal to WP08. **The finding was wrong** (F2: `COLUMNS`
  *is* consulted on the non-dumb path, and `test_activation_layout.py:111` is live today) and the
  removal is **dropped, not reassigned**. WP02 carries the one constraint that survives: the pinned
  width is **≥ 240**.
- **Chasing what makes rich's `is_terminal` true on the CI runner.** The mission's principal known
  unknown. Offered to the operator and **not selected**. It must be carried into the PR's limits
  section (SC-018), together with the fact that **nothing here was tested under xdist**.
- **The enumerated pairwise polluter search across both shard cones.** Offered and **declined** in
  favour of the measured cause.
- **`tests/sync/conftest.py:242-259`** — the filename-token consent-grant guard. **Armed.** Needs its
  own mission with the trap written into its spec.
- **Production routing changes for the `/tmp` root-walk artifact** (C-001), and any change to
  `SPECIFY_REPO_ROOT`'s precedence.
- **Removing or weakening `overflow="fold"`** on the Project column (C-009), or any rendering change
  made to satisfy a test.
- **The known pre-existing failures** in `standing-rules.md` — name them and move on.
- **Re-architecting the CI shard topology** — the `|| test $? -eq 5` tolerance, the `needs.changes`
  path filter, port-range or `SPEC_KITTY_HOME` partitioning per shard.
- **Everything else in the `#3030` follow-up backlog.**

## Follow-up candidates — surfaced by planning, not absorbed

- **The 22 `_isolated_home` fixtures (ex-FR-008 / ex-WP08) — the successor issue.** Cut from this
  mission; see the scope-cut note and `spec.md`'s follow-up candidates for how the successor must be
  scoped (equivalence classes first, and a **behavioural** acceptance rather than a `grep -c`, since
  collected counts cannot see a fixture *body* change). Full measured evidence:
  `notes/post-plan-squad-findings.md`. Two things travel with it: **WP03's width guard must land
  first**, because it is the only guard that would catch a hoist changing the victim files' render
  surface; and the successor's own plan must state the `SPEC_KITTY_ENABLE_SAAS_SYNC` policy conflict
  as a **decision it has to make**, not as an inconsistency it can normalise away.
- **`compute_lanes` has no cycle validation, and its docstring says otherwise.**
  `src/specify_cli/lanes/compute.py:618-630` calls cycle detection "best-effort" and defers to
  caller-side validation *"before invoking"*; `:639`'s comment says the cycle "is logged via
  `compute_lanes`'s validation". **No such validation exists in `src/specify_cli/lanes/`.** A cyclic
  lane graph deadlocks at dispatch and allocates from the wrong merge base, silently. Real,
  pre-existing, and out of this mission's scope — but this plan contained exactly such a cycle before
  the post-plan squad found it by reading, not by running anything. The durable fix is a real
  topological check at `lanes.json` write time that fails loudly.
- **A hand-authored lane table in a plan is not an input to `lanes.json`.** Lanes come from
  `owned_files` overlap only (`compute.py:1-11`). Every plan in this repo that writes "`lanes.json`
  is written from this table" is stating something false, and the divergence is invisible until
  dispatch. A `spec-kitty` check that diffs the plan's stated lane grouping against the computed one
  would close it.
- **`egress_allowlist_files: 28` (`tests/architectural/_baselines.yaml:368`) is count-anchored**, so
  a *substitution* — one entry removed and another added — passes the ratchet silently. Real,
  **pre-existing**, out of scope. The durable shape is a content hash or a set comparison.
- **`tests/architectural/_gate_coverage_baseline.json`'s orphan ratchet is a worklist, not a floor.**
  A new test file can be born ungated and the correct fix (gate it) and the wrong fix (baseline it)
  are equally easy. A collected-count floor per gate would close it.
- **Post-planning WPs have no lane** — `lanes.json` is written once at planning time and the tooling
  defaults an unmapped WP to `lane-a`, making the lane-staleness gate fire inapplicably and the
  pre-review regression gate print `no_coverage — skipping the gate cheaply`. This plan works around
  it by pre-allocating WP14; the fix belongs upstream (register post-planning WPs, or fall back to
  diffing `owned_files` against the merge base, or fail loudly — anything but a skip that prints like
  a pass).
- **The pre-review regression gate's 300s cap and its 5-second serialisation fallback**
  (`src/specify_cli/review/pre_review_gate.py:256`). NFR-010 and R2/R3 work around it here; the fix
  belongs upstream.
- **`fast-tests-cli` tolerates `exit 5`** and **`fast-tests-sync` is path-filtered** — a test-only
  branch can merge with the sync shard never having run. A required check or an always-run smoke
  selection would close it.
- **`getattr(obj, "name", None)` is invisible to `tests/architectural/test_no_dead_symbols.py`** —
  the same AST blind spot `#3113` is an instance of, in a second guard.
- **`docs/development/3-2-page-inventory.yaml` is a generated lockfile with 686 entries** that any
  new docs page must regenerate. Worth a pre-commit regeneration hook so it is never a merge conflict
  between two doc-adding lanes.
