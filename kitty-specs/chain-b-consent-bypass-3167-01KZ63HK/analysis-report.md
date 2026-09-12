# Post-specify adversarial squad — findings and adjudication

**Date:** 2026-08-04 · **Baseline:** `upstream/main` `abca7ec96`
**Lenses (4, profile-loaded, independent):** `architect-alphonso` (seams/topology) ·
`debugger-debbie` (live evidence/coverage) · `reviewer-renata` (fakeability) ·
`planner-priti` (scope/sequencing/tracker)

**Outcome: the spec is REJECTED on its central premise.** Two lenses independently found it, a third
demonstrated the thing that looked like a refutation, and the orchestrator adjudicated from source.

---

## 1. The premise is false — `sync/batch.py`'s drain has no production caller

`research.md` §3a asserted that `_is_checkout_sync_enabled_for_batch` "gates the **event drain** — the
path that POSTs queued events to SaaS." **It does not.** It gates the *retired* queue-backed drain.

Adjudicated from source, not from the lenses' reports:

```
$ git grep -n 'batch_sync\|sync_all_queued_events' -- src/ | grep -v '^src/specify_cli/sync/batch.py:'
src/specify_cli/sync/__init__.py:61:    # NOTE (#3030 FR-012): ``batch_sync`` and ``sync_all_queued_events`` are
src/specify_cli/sync/background.py:494:        invokes the event ``batch_sync`` / ``queue.process_batch_results`` path.
src/specify_cli/sync/background.py:580:                # This called ``sync_all_queued_events`` over the machine-global
```

All three are **comments**. Zero production callers. And the repository records the position in three
independent places:

- `sync/__init__.py:61-66` — "They are the retired queue-backed event drain, which carries no
  per-project consent; the journal dispatcher (`delivery/dispatcher.py`) is the **sole event drain**.
  Re-exporting them reinstates the cross-project leak."
- `tests/architectural/test_egress_consent_boundary.py:577-586` — `sync/batch.py` allowlisted
  `AllowanceKind.UNREACHABLE`, inventory **E15**: "The retired queue-backed drain. **Ungated, but
  unreachable**… If it is ever re-wired this allowance is void."
- `tests/sync/test_no_queue_drain_constructed_3030.py` — a standing AST guard that reds if any
  production module imports or calls either name. Its docstring nominates the successor work:
  "**Retiring the implementations outright belongs to the work package that already opens
  `batch.py`.**"

And the revival rule is already written, at `sync/emitter.py:2441-2443`:

> **WHAT WOULD FLIP IT:** if a queue-backed sender is ever restored, this write becomes egress and
> must be gated on consent *first*. That is a precondition on restoring the drain, not a follow-up
> ticket.

**Why the apparent refutation was not one.** `debugger-debbie` did demonstrate a non-consenting
project's payload reaching a POST body, twice, in both the fresh-clone and the cwd variant. But her
harness **called `batch_sync` directly** — which is exactly the construction the standing guard exists
to prevent in production, and exactly what the other two lenses predicted the only possible red would
be. Her result proves **the gate is broken**; it does not prove **the path is live**. She conceded the
gap herself. The three lenses agree once read precisely.

**The failure in my own research:** I read what the function does and traced its precedents, and never
asked whether anything calls it. That is the same class of error this programme exists to close —
checking what the code says rather than whether it runs.

## 2. The "documented-but-false claim" was not false — I mis-read a bound term

`research.md` §4 and `spec.md` FR-008 claimed `sync/runtime.py:203-205` falsely asserts the drain
reaches the consent seam. **"The drain" is bound in this repo to `delivery/selection.py`**, which *is*
on Chain A. Two sites spell it out verbatim:

```
src/specify_cli/sync/__init__.py:343-344:  "the same funnel the drain
                                            (``delivery/selection.py``) and the emitter use"
src/specify_cli/tracker/egress_consent.py:26-27: "the same funnel the drain
                                            (``delivery/selection.py``), the emitter, the daemon…"
```

So the docstring is **true as written**, and FR-008 would have rewritten a correct docstring — then
the natural rewrite would have asserted coverage for a module with no live caller, *manufacturing* the
defect class User Story 4 exists to remove. `architect-alphonso` called this; `debugger-debbie`'s
"false as shipped" reading was the term collision. **FR-008 is withdrawn.** The residual is a
terminology fix: "the drain" has at least three referents (`delivery/selection.py` dispatch selection,
`sync/background.py:280` body upload, `sync/batch.py` the retired event drain) and no glossary entry —
the same overload class `docs/context/orchestration.md#routing` already governs for "routing".

## 3. Findings that stand regardless of disposition

These are independent of the premise and each is worth acting on.

| Sev | Finding | Evidence |
|---|---|---|
| **HIGH** | **The `tests/sync` suite structurally cannot observe the batch gate.** `tests/sync/conftest.py:221` is an autouse fixture that patches `specify_cli.sync.batch.is_sync_enabled_for_checkout` to `True` for every file whose name lacks `"consent"`/`"capture_gate"` — confirmed live via `--setup-show`. A covering test written in its natural home (`test_batch_sync.py`) is *granted consent by the fixture* and passes regardless of implementation. This is why F-09's coverage is zero and nobody noticed. | `tests/sync/conftest.py:221,:279-283`; `--setup-show` output |
| **HIGH** | **The fixture patches with `raising=False`**, so once production stops consulting that name the patch becomes **inert with no `AttributeError`** — green for the wrong reason, silently. Its own docstring at `:258-263` names the trap. Blast radius: **20** files under `tests/sync/` plus 4 outside. | `tests/sync/conftest.py:283` |
| **HIGH** | **`consented_project_uuids` writes machine-global config on read.** `consent.py:512` → `_reconcile_index` → `set_project_consent` whenever the project-local level answers. Measured: machine index for a project goes `None` → `True` after one read, and the grant then **survives removal of the project-local grant**. So any migration trades a documented side-effect-free gate for one that mutates machine state per tick, and refusal/positive-control tests cross-contaminate through a shared `SPEC_KITTY_HOME`. | `sync/consent.py:483,:512`; measured transcript |
| **HIGH** | **`research.md:107` mints a mandatory issue-matrix row this mission cannot resolve** — a bare `#3030` inside a quoted docstring. The merge gate calls the multi-file `discover_issue_references(feature_dir)`, not the `spec.md`-only detector I ran. `spec.md` is genuinely clean (0 of 192 lines, control returns 1); the mission is not. | `research.md:107`; `policy/merge_gates.py:139,:307-329` |
| **HIGH** | **Decision D8 is wrong for a mission's own issue.** `owner/repo#NNNN` evades `_GH_ISSUE_PATTERN` (`issue_matrix.py:87-95` requires a non-word char before `#`), so this mission mints **no** row for `#3167` and the gate returns a vacuous "nothing to enforce" — a green that means nothing, in a programme whose thesis is that such greens are the defect. **D8 needs a carve-out: the mission's own issue is declared bare or by canonical URL; foreign issues keep `owner/repo#`.** | detector transcript; `merge_gates.py:311-315` |
| **MEDIUM** | **A silent-outage shape with no scenario (matrix cell 3).** A *consenting* project's events are withheld today when cwd is inside no project — the daemon's usual case, since `daemon.py:1319` passes no `cwd=` to `Popen` and sets `start_new_session=True`, freezing the spawning cwd forever. Demonstrated: `requests made: 0`, `"skipped: SaaS sync disabled for current checkout"`. `emitter.py:1910-1914` records this over-refusal having already happened once. | measured transcript; `sync/daemon.py:1319` |
| **MEDIUM** | **Three envelope→`project_uuid` resolvers exist and disagree** — `sync/project_identity.py:70-125` (envelope *then* payload, nil-normalised), `delivery/consent_gate.py:183-206` (envelope-only, no normalisation), `sync/queue.py:110-127` (third walker with a per-event-type legacy overlay). The same row can resolve differently by caller. | the three sites |
| **MEDIUM** | **`drain_blocked_reason` is a closed vocabulary owned by the emit layer**, and its other consumer treats an unrecognised value as **permanently terminal** (`delivery/selection.py:114-124`). Reusing it drain-side without amending `TRANSIENT_DRAIN_BLOCKED_REASONS` would have stranded withheld rows forever — the exact opposite of what R-1 chose. Had the mission proceeded, this was a latent CRITICAL. | `emitter.py:1885`; `delivery/selection.py:56,62,114` |
| **LOW** | **The leak guard's failure text still points readers at `tests/sync/conftest.py`** for a registry that moved to `_leak_guard.py` in `#3144`. Same false-pointer class as User Story 4, in a file this mission opens. Belongs to the sync-cone mission (registry owner) — **file, do not fold**. | `tests/sync/_leak_guard.py:572,:585,:822` |

### My research's counts were wrong

`research.md` §1 says "**12 importer sites**" and then lists 11, of which 3 are docstring mentions.
Measured: `git grep -c 'consented_project_uuids(' -- src/` excluding `consent.py` → **8 real call
sites** (`delivery/consent_gate.py:156`, `delivery/selection.py:100`, `sync/__init__.py:369`,
`sync/background.py:296`, `sync/body_upload.py:111`, `sync/emitter.py:2008`,
`sync/local_commit.py:203`, `sync/runtime.py:242`). A "before/after" comparison against a wrong
"before" measures nothing, so `NFR-004`/`SC-005` rested on a bad baseline.

## 4. The baseline, committed as `SC-006` requires

`git diff --stat abca7ec96 HEAD -- src/ tests/` is **empty**, so this measures the baseline directly.

```
$ .venv/bin/python -m pytest tests/sync -n0 -q -p no:cacheprovider --timeout=300 -rf   [redirected]
2376 passed, 19 skipped, 1 warning, 5 errors in 215.15s
EXIT=1
```

> **⚠️ CORRECTED 2026-08-04 after WP02's review — this baseline was a scalar and should never have been
> one.** A second measurer ran the base arm **five** times and got errors `{5, 5, 6, 6, 6}`; the after arm
> three times and got `{6, 6, 7}`. **5 is not the mode — it is the tail.** The run quoted above was `n=1`,
> and every WP prompt that told an implementer to "attribute against 5 errors" was asking them to attribute
> against noise.
>
> **The cone's error count is a distribution, not a number: 5–6 at `b0482a832^`, measured n=5.** A 6-error
> run is not a regression and a 5-error run is not "the baseline". Any pre/post comparison must be a
> **per-node-id set difference over ≥5 runs per arm**, never a scalar.
>
> **And the counting command was wrong in the other direction too.** `grep -c '^ERROR '` **over**-counts:
> a captured-log record at level ERROR (`ERROR specify_cli.sync.background:background.py:369 Refusing to
> start background sync…`) begins with `ERROR ` and made one 6-error run read as 7. **Count
> `^ERROR tests/`.** So this file previously carried a rule that was itself unsafe — first `-rf` suppressed
> the lines, then the fixed grep counted too many.
>
> The volatile band is exactly one shape — `live thread name='Thread-N' target=None` — produced by
> `_ChainedTimer` (`sync/daemon.py:687,:715,:745`) and `threading.Timer` (`sync/background.py:528`), and
> attributed by `_leak_guard.py:737`'s `after − before` set difference to whichever test spans the thread's
> lifetime. **The observer moves; the leak does not.** None of those producers is a file this mission owns.
>
> Nodes proven to fire in the volatile band at **both** commits — do not re-investigate without new
> evidence: `test_background.py::TestSingletonAccessor::{test_get_sync_service_returns_same_instance,
> test_reset_clears_singleton}`, `test_daemon_self_retirement.py::TestStartSelfCheckTick::test_returned_timer_thread_is_daemon`,
> `test_legacy_queue_guard_3030.py::TestARefusedStartLeavesNoDeadSingleton::test_get_sync_service_does_not_cache_a_service_that_failed_to_start`.
> The **stable floor at both commits** is 5 nodes: `test_daemon_self_retirement::TestRunSyncDaemonWiring` ×2,
> `test_dual_write_integration` ×2, and the `:420` pin's partial match.
>
> Two environment footguns, paid for: `/tmp` is a 7.8 G tmpfs and one sweep costs ~1.5–2 G of `pytest-of-*`,
> so three retained generations truncate a run mid-write with a bogus `EXIT=1` — wipe basetemp between runs
> and keep it on `/tmp` (`/home` reds 3 consent/routing nodes via the `.kittify` root-walk; `/var/tmp` reds
> ~1530). And `pkill -f` needs the bracket class **in argument position too**, not only inside scripts:
> `pkill -f 'pytest tests/sync'` matched the caller's own shell and killed it.
>
> Filed as `Priivacy-ai/spec-kitty#3193`. Neither measurer asserts this diff had zero influence; both assert
> the failure **class** pre-exists, reproduces at base, and implicates no file this mission owns.

Input count 2376 + 19 = **2395**, identical to the collect-only count — not a vacuous run. Zero
`FAILED`. All 5 are leak-guard **teardown** errors, no assertion failures, none attributable to this
mission (DIR-013):

1. `test_daemon_self_retirement.py::TestRunSyncDaemonWiring::test_serve_forever_exits_cleanly_when_server_shutdown`
2. `test_daemon_self_retirement.py::TestRunSyncDaemonWiring::test_sigterm_exits_without_deadlocking_server_shutdown`
3. `test_dual_write_integration.py::TestDualWriteEventAndFrontmatterConsistent::test_dual_write_event_and_frontmatter_consistent`
4. `test_dual_write_integration.py::TestDualWriteMultipleTransitions::test_dual_write_multiple_transitions`
5. `test_lifecycle_readiness.py::test_init_emits_project_init_event_offline` — **a pin at
   `_leak_guard.py:420`**, erroring as a *partial* match

**Pin ledger:** 10 `ACCEPTED (#3130)` + 1 `UNOBSERVABLE this run` + 1 partial-match error = **12**.
The three pins in files this mission would own: `:420` fires as an error **only in the full serial
sweep** (isolated: `8 passed`, EXIT=0) and its `[E26]` observability is supplied by baseline error #3,
a file this mission does not own; `:389` and `:395` are `ACCEPTED`, not errors. **Nothing was re-pinned
or removed, and no change to any pin is proposed here.**

Handoff for the sync-cone mission: ordering alone gives WP01 a *fresh* enumeration but not
**attribution** — it cannot distinguish "leak fixed" from "leak made unobservable by a conftest
change". A per-node-id pre/post delta note is required, not optional.

## 4b. Pin line numbers moved — every citation in this dossier was rewritten

WP03 added C-006's in-code residual (a `#3167 CONE HAZARD` block plus a per-entry note) to
`tests/sync/_leak_guard.py`, which **shifted the three pinned node-ids this mission's cone touches**:

| Node id | Was | Now |
|---|---|---|
| `test_lifecycle_readiness.py::test_init_emits_project_init_event_offline` | `:371` | **`:420`** |
| `test_runtime.py::TestSyncRuntime::test_starts_background_service` | `:389` | **`:442`** |
| `test_runtime.py::TestUnauthenticatedBehavior::test_no_websocket_when_unauthenticated` | `:395` | **`:452`** |

Verified against the file, not inferred from the diff: `grep -n '_PinnedLeak('` still returns **12**
openers, and the three node-id strings sit at `:420`, `:442`, `:452`.

Every citation across `spec.md`, `research.md`, this file, `WP03`'s prompt, `issue-matrix.json` and
`research/evidence-log.csv` was rewritten to the new numbers. A dossier that cites line numbers which no
longer resolve is a documented-but-false pointer — the exact class this mission's User Story 4 exists to
remove, and it would have been self-inflicted one commit after fixing someone else's.

## 5. Squad process notes

- The `tests/sync` window was held exclusively; `tests/cli` was never run. Final state verified
  daemon-free (`pgrep` exit 1, no listeners on 9400-9449).
- One leaked daemon **was** produced by the sweep (pid holding 127.0.0.1:9400) and reaped — the
  in-process leak guard cannot see it.
- The `pkill`/`pgrep` footgun fired in `pgrep` form: a reap script's own subshell matched
  `pgrep -f 'run_sync_daemon'` and killed itself. **The bracket class is required in the reaper too**,
  not only in interactive greps.
- `grep -c '^ERROR '` returned 0 on a run with 5 errors because `-rf` suppresses the error
  short-summary. Use `-ra` so the count the standing rules ask for is actually emitted.
- One lens retracted a finding after re-measurement (an apparent `C-002` violation that was an
  ordering artefact of the write-on-read above). Recorded so it is not re-litigated: **"offered
  checkout roots can widen a consent answer" is FALSE.**
