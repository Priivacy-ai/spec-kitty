# Deletion manifest

> **The totals in this manifest were measured at `f04ee0a78`** (the commit before the deletion). Re-running
> `scripts/verify_batch_retirement_3167.py` at HEAD reports `dead=2 alive=21`, because the 33 symbols no
> longer exist — the script cannot distinguish *absent* from *present-but-dead*. Pinning the ref was
> missing from the authority block and is added here: an instruction to "re-run and confirm 33" without a
> ref is an instruction that fails for the right reason and looks like the wrong one.
 — `sync/batch.py` queue-backed senders

**Mission:** `chain-b-consent-bypass-3167-01KZ63HK` · **Work package:** WP01 · **Requirements:** FR-002, NFR-001, NFR-002
**Frozen:** 2026-08-04 · **Branch:** `feat/chain-b-consent-bypass-3167`

This is the frozen list WP02 is reviewed **against**. It is not a summary to be re-derived by each
reader; it is the contract. Every number below carries the command that produced it.

## Provenance and the three controls

**Authority:** `scripts/verify_batch_retirement_3167.py`

```
sha256  92bd4d620bf51aed1f395c7e099829e3ed583638921cfb5ffdeff6c9dbfd3464
run     .venv/bin/python scripts/verify_batch_retirement_3167.py     (from the REPOSITORY ROOT CHECKOUT)
```

Run it from the repository root checkout, **not** from a `.worktrees/…` path — a dot-prefixed path
segment makes some of this repo's architectural collectors discover zero files and pass vacuously.

WP01 owns this script and `main()` only prints, so an edited script could reproduce any totals on
demand. A self-reported control is therefore worth nothing, and three independent controls were run.
**Two of the three failed on first execution and exposed real resolver bugs.**

### Control 1 — known production consumers must resolve

The four consumers stated independently in the WP prompt all resolve, module-qualified:

| Symbol | Resolved to | Tier |
|---|---|---|
| `run_final_sync_with_retries` | `src/specify_cli/sync/background.py` | ALIVE |
| `BatchEventResult` | `src/specify_cli/sync/background.py` | ALIVE |
| `BatchSyncResult` | `src/specify_cli/sync/background.py` | ALIVE |
| `categorize_error` | `src/specify_cli/sync/diagnose.py` | ALIVE |

The three symbols the *first* manifest attempt got wrong are now on the correct side, and the
manifest shows why (see §1).

### Control 2 — injection: an injected caller must flip a symbol out of the dead set

Appended to `src/specify_cli/sync/diagnose.py`, then re-run, then restored:

```python
from .batch import batch_sync  # WP01 INJECTION CONTROL
def _wp01_injection_control_probe() -> object:
    return batch_sync
```

**FIRST RESULT: FAILED. The report was byte-identical — an empty `diff`.** The resolver was blind to
an injected caller of exactly the symbol whose callerlessness is this mission's premise.

Diagnosed rather than assumed: the same injection for a *non-seed* first-tier symbol
(`_build_batch_payload`) flipped correctly (`FIRST TIER 24 → 23`, `alive 21 → 22`, with
`prod CODE refs: ['src/specify_cli/sync/diagnose.py']`). So the injection mechanism worked and the
blindness was specific to the seeds.

**Root cause — resolver bug 1.** `main()` opened the fixpoint with `dead = set(SEEDS)`, and the loop
skips anything already in `dead` (`if sym in dead or sym in API_ALIVE: continue`). `batch_sync` and
`sync_all_queued_events` were therefore **dead by fiat**: the two symbols the mission proposes to
delete were the only two whose absence of a production caller the closure could not test. It assumed
its own premise.

**Fix.** Seeds must earn the dead set on the same evidence as every other symbol:

```python
dead = {s for s in SEEDS if s not in API_ALIVE and not prod_code_refs(s)}
unproven_seeds = sorted(SEEDS - dead)
```

Seeding is still *required* — `sync_all_queued_events` has no intra-module referrer, so the
`referrers <= dead` rule can never derive it — but it is now conditional. The run also **REFUSES
(exit 1)** if a seed turns out to have a production caller, and prints the per-seed verdict with its
evidence.

**After the fix the totals were unchanged** (`dead=33 (first=24 second=9) alive=21`; the only diff
was the added header lines). The premise is now *established over 3905 scanned files*, not assumed.

**RE-RUN: PASSES.** With the injection present:

```
seed premise: batch_sync   HAS production CODE refs ['src/specify_cli/sync/diagnose.py']
   batch_sync              prod CODE refs: ['src/specify_cli/sync/diagnose.py']   <- was SECOND TIER
TOTALS  dead=3 (first=2 second=1)  alive=51                                       <- was dead=33 alive=21
closure exit=1
*** REFUSED: the mission premise is false for ['batch_sync'] ***
```

The collapse from 33 dead to 3 is the point: one live sender keeps its whole callee tree alive. That
entire cascade is what `dead = set(SEEDS)` was concealing.

### Control 3 — deletion: dropping a real caller must flip ALIVE → dead

`src/specify_cli/sync/background.py` lines 32–36 removed (the whole
`from .batch import (BatchEventResult, BatchSyncResult, run_final_sync_with_retries)` block), re-run,
restored. Precondition asserted each time: **the mutated file still parses**, because a `SyntaxError`
makes `_classify_external` fall back to all-PROSE and would flip symbols for the wrong reason.

**FIRST RESULT: FAILED.** `run_final_sync_with_retries` correctly lost its reference
(`prod CODE refs: ['…background.py']` → `[]`) but **stayed in the ALIVE tier**. Per the WP prompt,
that makes the ALIVE tier vacuous.

**Root cause — resolver bug 2.** The promotion rule read
`if referrers and referrers <= dead and not prod_code_refs(sym)`. The leading `referrers and` means a
symbol with **no intra-module referrer** — i.e. an entry point — can never be derived dead however
the external evidence falls. Measured: exactly two ALIVE callables have zero intra-module referrers,
`run_final_sync_with_retries` and `write_failure_report`.

**Fix.** An empty referrer set satisfies `referrers <= dead` vacuously; an entry point's liveness
rests entirely on external evidence. The unreferenced-**constant** carve-out (deferred to ruff /
dead-symbol review) is preserved so the correction cannot silently widen the deletion set.

This fix was **provably totals-preserving before it was applied**: of the two zero-referrer callables,
`run_final_sync_with_retries` has a real production reference and `write_failure_report` is API-alive
via the lazy map, so neither changes tier; every other ALIVE symbol has intra-module referrers, and no
ALIVE constant has a zero referrer set. Confirmed empirically — output byte-identical.

**RE-RUN: PASSES.**

```
baseline : run_final_sync_with_retries   prod CODE refs: ['src/specify_cli/sync/background.py']   (ALIVE)
deleted  : run_final_sync_with_retries   tests: ['tests/sync/test_final_sync_diagnostics.py']    (SECOND TIER, dead)
TOTALS   : dead=33 (first=24 second=9) alive=21   ->   dead=46 (first=35 second=11) alive=8
```

The `_final_sync_*` family cascades dead with it, which is the correct consequence: it is reachable
only through that entry point.

### A control failure of my own, disclosed

The first versions of both control scripts used `set -euo pipefail`. Once the closure legitimately
exited 1 (REFUSED), `set -e` aborted the script **at** the closure invocation, before the restore —
so `diagnose.py` was left mutated and the deletion control then ran on a contaminated tree. Both
scripts reported success lines that never printed, and I caught it only because the deletion run
reported `batch_sync HAS production CODE refs`. Both source files were restored from `HEAD` and
**both controls were re-run from a verified-clean tree**; the results quoted above are the re-runs.
Restores now run from a `trap` and the closure's exit status is captured explicitly.

### Verification of non-interference

`scripts/` is inside the closure's own `SEARCH_ROOTS`, so the script scans itself. Its docstring
mentions several target symbols; all such self-references classify as **PROSE**, and PROSE never
affects liveness (`prod_code_refs` requires kind `CODE`). Confirmed in the per-symbol dump in §1.

---

## 1. Tier table with per-symbol referrer sets

```
target: src/specify_cli/sync/batch.py   seeds: ['batch_sync', 'sync_all_queued_events']
declared symbols: 54  (callables/classes 45, constants 9)
files scanned for references: 3905  (roots: ['src', 'tests', 'scripts'])
API-alive via specify_cli.sync lazy map: ['BatchEventResult', 'BatchSyncResult', 'categorize_error',
                                         'format_sync_summary', 'generate_failure_report',
                                         'write_failure_report']
seed premise: batch_sync                no production CODE ref -> deletable
seed premise: sync_all_queued_events    no production CODE ref -> deletable

TOTALS  dead=33 (first=24 second=9)  alive=21
```

Input count stated alongside the verdict: **3905 files scanned**. This reconciles exactly — `git ls-files '*.py'`
counts 3906 tracked files under `src/ tests/ scripts/`, minus `sync/batch.py` itself, which the closure
skips as the target. No `.py` file anywhere outside those three roots names either sender, so
`SEARCH_ROOTS` is not hiding a caller (17 tracked `.py` live outside them; none matches).

### FIRST TIER — delete now (24)

No external reference of any kind in `src/`, `scripts/` or `tests/`.

| Symbol | External referrers |
|---|---|
| `DECOMPRESSED_BYTES_SAFETY_FACTOR` | — |
| `HISTORICAL_MISSION_STATE_FORBIDDEN_KEYS` | — |
| `SYNC_INGRESS_LIMITS_TIMEOUT_SECONDS` | — |
| `_body_mentions_missing_private_team` | PROSE only — see collision note below |
| `_build_batch_payload` | — |
| `_decompressed_byte_limit` | — |
| `_extract_sync_ingress_limits` | — |
| `_fetch_advertised_sync_ingress_limits` | — (**a direct sender**, see §4) |
| `_find_historical_mission_state_keys` | — |
| `_handle_single_oversized_event` | — |
| `_historical_mission_state_rejection` | — |
| `_http_error_category` | — |
| `_http_error_message` | — |
| `_is_oversized_batch_response` | — |
| `_merge_batch_sync_result` | — |
| `_positive_int` | — |
| `_prepare_events_for_ingress` | — |
| `_record_all_events_failed` | — |
| `_retry_limits_from_response` | — |
| `_safe_response_json` | — |
| `_select_events_for_advertised_limits` | — |
| `_should_probe_advertised_limits` | — |
| `_should_stop_sync_loop` | — |
| `_single_oversized_event_result` | — |

### SECOND TIER — dead in `src/`, held only by tests (9)

Deletable once the coupled tests retire; their disposition is a separate decision (WP02/WP03).

| Symbol | Test referrers |
|---|---|
| `DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH` | `tests/sync/test_batch_sync.py` |
| `MAX_DECOMPRESSED_BYTES_PER_BATCH_CEILING` | `tests/sync/test_batch_sync.py` |
| `_current_team_slug` | `tests/sync/test_batch_error_surfacing.py`, `tests/sync/test_batch_sync.py`, `tests/sync/test_offline_replay.py` |
| `_is_checkout_sync_enabled_for_batch` | `tests/sync/test_batch_sync.py` |
| `_parse_error_response` | `tests/sync/test_batch_error_surfacing.py` |
| `_parse_event_results` | `tests/sync/test_batch_error_surfacing.py` |
| `_shrink_events_for_retry` | `tests/architectural/test_batch_split_single_authority.py` |
| `batch_sync` | `tests/sync/test_batch_400_no_details_poison_2736.py`, `tests/sync/test_batch_error_surfacing.py`, `tests/sync/test_batch_retry_hygiene.py`, `tests/sync/test_batch_sync.py`, `tests/sync/test_integration.py`, `tests/sync/test_offline_replay.py` |
| `sync_all_queued_events` | `tests/sync/test_batch_sync.py`, `tests/sync/test_offline_replay.py` |

### ALIVE — must survive (21)

| Symbol | Basis |
|---|---|
| `BatchEventResult` | prod CODE: `src/specify_cli/sync/background.py` |
| `BatchSyncResult` | prod CODE: `src/specify_cli/sync/background.py` |
| `run_final_sync_with_retries` | prod CODE: `src/specify_cli/sync/background.py` |
| `categorize_error` | prod CODE: `src/specify_cli/sync/diagnose.py` |
| `format_sync_summary` | API-alive (lazy map) |
| `generate_failure_report` | API-alive (lazy map) |
| `write_failure_report` | API-alive (lazy map) |
| `CATEGORY_ACTIONS` | derived — referrer `format_sync_summary` is alive |
| `ERROR_CATEGORIES` | derived — referrer `categorize_error` is alive |
| `FINAL_SYNC_MAX_ATTEMPTS` | derived — `_has_final_sync_retry_remaining`, `run_final_sync_with_retries` |
| `FINAL_SYNC_RETRY_BACKOFF_SECONDS` | derived — `_sleep_before_final_sync_retry` |
| `_emit_final_sync_failure_diagnostic` | derived — 3 live referrers |
| `_final_sync_result_error_text` | derived — 2 live referrers |
| `_finalize_exhausted_final_sync` | derived — `run_final_sync_with_retries` |
| `_handle_final_sync_exception` | derived — `run_final_sync_with_retries` |
| `_handle_final_sync_result` | derived — `run_final_sync_with_retries` |
| `_has_final_sync_retry_remaining` | derived — `_sleep_before_final_sync_retry` |
| `_is_failed_final_sync_result` | derived — 2 live referrers |
| `_result_from_final_sync_exception` | derived — 2 live referrers |
| `_should_retry_final_sync_result` | derived — `_handle_final_sync_result` |
| `_sleep_before_final_sync_retry` | derived — `_handle_final_sync_exception`, `_handle_final_sync_result` |

### The name collisions the first attempt got wrong, in both directions

This is the whole reason the manifest resolves references module-qualified. **A bare
`git grep -w <name>` gets these three wrong.**

`_sleep_before_final_sync_retry` — was filed as a **deletion candidate**. It is **ALIVE**: called on
the live `run_final_sync_with_retries` chain that `background.py` drives. Its only external hit is
PROSE in `tests/sync/tracker/test_saas_client.py`. Deleting it breaks a production daemon path.

`_current_team_slug` — was filed **production-alive** on the strength of five `src/` hits. Every one
is **PROSE**, not a call:

```
PROSE       src/specify_cli/cli/commands/sync.py
PROSE       src/specify_cli/delivery/retention.py
PROSE       src/specify_cli/sync/emitter.py          <- EventEmitter._current_team_slug: a DIFFERENT symbol
PROSE       src/specify_cli/tracker/saas_client.py
PROSE       scripts/verify_batch_retirement_3167.py  <- this script's own docstring
STR-TARGET  tests/sync/test_batch_error_surfacing.py
STR-TARGET  tests/sync/test_batch_sync.py
STR-TARGET  tests/sync/test_offline_replay.py
+ 10 further PROSE hits under tests/
```

Zero `CODE` references. Correct tier: **SECOND**.

`_body_mentions_missing_private_team` — also filed production-alive. Its only two hits are
`src/specify_cli/sync/body_transport.py` (**that module's own definition** — a different symbol) and
this script's docstring. Both PROSE. Correct tier: **FIRST**.

---

## 2. Module-level imports orphaned by the deletion

`ruff check` **cannot name these today** — the dead symbols are still present, so every import still
has a user. F401 will name them only after WP02's deletion. They are therefore predicted
structurally: an import is orphaned iff every top-level symbol referencing it is in the dead set and
no surviving module-level statement uses it.

**Control:** the WP prompt names six independently (`gzip`, `requests`, `urlparse`, `OfflineQueue`,
`batch_partition`, `validate_outbound_payload`). **All six are predicted orphaned** — so the
prediction is checked against a known answer before its novel rows are trusted.

**12 orphaned imports** (of 24 module-level imports in `batch.py`):

| Bound name | Import statement | Used only by |
|---|---|---|
| `gzip` | `import gzip` | `batch_sync` |
| `requests` | `import requests` | `_fetch_advertised_sync_ingress_limits`, `batch_sync` |
| `urlparse` | `from urllib.parse import urlparse` | `_should_probe_advertised_limits` |
| `suppress` | `from contextlib import suppress` | `batch_sync` |
| `OfflineQueue` | `from .queue import OfflineQueue` | `_handle_single_oversized_event`, `_select_events_for_advertised_limits`, `batch_sync`, `sync_all_queued_events` |
| `batch_partition` | `from specify_cli.core import batch_partition` | `_shrink_events_for_retry` |
| `validate_outbound_payload` | `from specify_cli.core.contract_gate import validate_outbound_payload` | `batch_sync` |
| `request_with_stdlib_fallback_sync` | `from specify_cli.auth.http import request_with_stdlib_fallback_sync` | `batch_sync` |
| `is_saas_sync_enabled` | `from .feature_flags import is_saas_sync_enabled` | `batch_sync`, `sync_all_queued_events` |
| `saas_sync_disabled_message` | `from .feature_flags import saas_sync_disabled_message` | `batch_sync`, `sync_all_queued_events` |
| `is_sync_enabled_for_checkout` | `from .routing import is_sync_enabled_for_checkout` | `_is_checkout_sync_enabled_for_batch` |
| `resolve_private_team_id_for_ingress` | `from specify_cli.sync._team import resolve_private_team_id_for_ingress` | `_current_team_slug` |

**Excluded deliberately:** `from __future__ import annotations` also has no surviving *named* user,
but it is a compiler directive, never referenced by name, and `ruff` does not flag it. Removing it
would be a behaviour change. The raw structural pass reports 13; the F401-actionable count is **12**.

**11 imports are retained** — each still has a live user: `CATEGORY_MISSING_PRIVATE_TEAM`, `Callable`,
`Counter`, `Path`, `SyncDiagnosticCode`, `classify_sync_error`, `dataclass`, `emit_sync_diagnostic`,
`json`, `now_utc_iso`, `time`.

Note `request_with_stdlib_fallback_sync` and `requests` are both on this list. That is NFR-001 going
to zero at the import level as well as the call level.

---

## 3. Coupled test files

### The 7 code-coupled files (real work when the symbols go)

| Test file | Dead symbols it imports or monkeypatches |
|---|---|
| `tests/architectural/test_batch_split_single_authority.py` | `_shrink_events_for_retry` |
| `tests/sync/test_batch_400_no_details_poison_2736.py` | `batch_sync` |
| `tests/sync/test_batch_error_surfacing.py` | `_current_team_slug`, `_parse_error_response`, `_parse_event_results`, `batch_sync` |
| `tests/sync/test_batch_retry_hygiene.py` | `batch_sync` |
| `tests/sync/test_batch_sync.py` | `DEFAULT_MAX_DECOMPRESSED_BYTES_PER_BATCH`, `MAX_DECOMPRESSED_BYTES_PER_BATCH_CEILING`, `_current_team_slug`, `_is_checkout_sync_enabled_for_batch`, `batch_sync`, `sync_all_queued_events` |
| `tests/sync/test_integration.py` | `batch_sync` |
| `tests/sync/test_offline_replay.py` | `_current_team_slug`, `batch_sync`, `sync_all_queued_events` |

All 7 are inside lane-b's declared write scope.

### The 19 prose-only files (correct the sentence, not the code)

These merely *mention* a dead symbol. **No code work.** Listing them separately is the point — the
distinction a bare grep cannot draw, and the one that produced this mission's earlier false findings.

1. `tests/architectural/test_egress_consent_boundary.py`
2. `tests/cli/commands/test_sync_now_empty_selection_t005.py`
3. `tests/contract/test_event_envelope.py`
4. `tests/delivery/test_dispatch_honours_drain_blocked_3031.py`
5. `tests/delivery/test_dispatch_window_consent_3030.py`
6. `tests/delivery/test_liveness_predicate_before_limit_3030.py`
7. `tests/delivery/test_nfr002_loop_permanence_3030.py`
8. `tests/merge/test_merge_time_number_assignment.py`
9. `tests/specify_cli/sync/test_worktree_clean_invariant.py`
10. `tests/sync/test_events.py`
11. `tests/sync/test_issue_598_hang_fixes.py`
12. `tests/sync/test_no_queue_drain_constructed_3030.py`
13. `tests/sync/test_strict_json_stdout.py`
14. `tests/sync/test_sync_e2e_integration.py`
15. `tests/sync/test_team_ingress_resolver.py`
16. `tests/sync/tracker/conftest.py`
17. `tests/sync/tracker/test_saas_client_consent_gate_3030.py`
18. `tests/sync/tracker/test_saas_client_origin.py`
19. `tests/sync/tracker/test_saas_client_routing.py`

Item 12 is the NFR-004 guard: it must keep passing and must not be deleted, weakened or narrowed.

---

## 4. NFR-001 baseline sender count

**Definition** (as instructed): a *sender* is a top-level symbol in `sync/batch.py` from which a
`requests.*` or `request_with_stdlib_fallback_sync` call is **transitively** reachable.

**Probe controlled first.** The WP prompt names four transmit sites; the probe found exactly those
four and no others:

| Line | Primitive | Enclosing symbol |
|---|---|---|
| `:223` | `requests.get` | `_fetch_advertised_sync_ingress_limits` |
| `:1125` | `requests.post` | `batch_sync` |
| `:1212` | `request_with_stdlib_fallback_sync` | `batch_sync` |
| `:1282` | `request_with_stdlib_fallback_sync` | `batch_sync` |

# NFR-001 BASELINE SENDER COUNT = 3

| Sender | Basis |
|---|---|
| `batch_sync` | direct — `requests.post :1125`, `request_with_stdlib_fallback_sync :1212, :1282` |
| `_fetch_advertised_sync_ingress_limits` | direct — `requests.get :223` |
| `sync_all_queued_events` | indirect — transitively reaches `batch_sync` |

2 direct, 1 indirect, out of 45 top-level callables/classes.

**All 3 are inside the dead set** (`batch_sync` and `sync_all_queued_events` second tier,
`_fetch_advertised_sync_ingress_limits` first tier), so WP02's deletion takes the count **3 → 0**.
NFR-001 is now verifiable in both directions: the baseline is stated, and the target is the same
enumeration re-run.

---

## 5. Reachability beyond static callers (FR-002)

To invoke `batch_sync` or `sync_all_queued_events` in production, a caller must obtain the function
object. There are exactly four routes. **Each is closed, and each closure states why a caller would
otherwise have appeared.**

### Route 1 — static import

`from specify_cli.sync.batch import X`, the relative `from .batch import X`, or
`import specify_cli.sync.batch` plus attribute access.

**Result: zero `CODE` references from `src/` or `scripts/`**, over 3905 scanned files.

**Why one would otherwise have appeared:** this is not an unexercised claim about a detector. The
injection control added exactly one line of this form to `diagnose.py` and the closure flipped
`batch_sync` out of the dead set and exited 1; the deletion control removed the *real* one from
`background.py` and `run_final_sync_with_retries` flipped ALIVE → dead. The detector is demonstrated
live **in both directions** on this exact form. It also already caught one real bug: the first
version missed the relative `from .batch import` form and reported every sibling-module consumer as
unreferenced.

### Route 2 — the package public surface

`specify_cli.sync.batch_sync`. **Closed.** Proven at runtime, not by reading:

```
getattr(specify_cli.sync, 'batch_sync')             -> AttributeError
getattr(specify_cli.sync, 'sync_all_queued_events') -> AttributeError
  in dir(): False      in __all__: False    (both names)

POSITIVE CONTROL — names that ARE in the lazy map resolve through that same __getattr__:
getattr(specify_cli.sync, 'categorize_error')  -> RESOLVED
getattr(specify_cli.sync, 'BatchSyncResult')   -> RESOLVED
```

`sync/__init__.py:93` `__getattr__` resolves `_LAZY_IMPORTS` and otherwise **raises**; there is no
fallback branch. Both senders are deliberately absent from the map, with the reason recorded in the
source at `sync/__init__.py:61-66`. The positive control matters: it shows the `AttributeError` is the
map's exclusion doing its job, not a broken probe.

Confirmed the senders **do** still exist on the submodule
(`specify_cli.sync.batch.batch_sync` resolves), so the absence above is the package surface hiding
them, not a typo in the probe.

### Route 3 — dynamic resolution

`getattr` / `importlib` / `import_module` / `__import__` / `eval` / `exec` on either name, or either
name as a string literal.

**Result: zero occurrences in `src/`.**

**Why one would otherwise have appeared:** dynamic reach must spell the name as a string somewhere.
The identical grep shape finds `"categorize_error"` at `sync/__init__.py:67` — a name that **is**
dynamically resolved — so the pattern is not blind, and its silence on the senders is evidence rather
than a failed search. No `.toml`/`.yaml`/`.json`/`.cfg`/`.ini` file names either sender except this
mission's own planning artifacts.

### Route 4 — a separate process entry point

```
[project.scripts]      = {'spec-kitty': 'specify_cli:main'}     (exactly 1)
[project.gui-scripts]  = {}
[project.entry-points] = {}
```

Neither sender is an entry point, and reaching one from `main` still requires route 1, 2 or 3.

### Disclosed gap

Routes 1–4 exclude **in-repo** callers. `specify_cli` ships on PyPI, so an out-of-tree consumer
importing the private submodule `specify_cli.sync.batch` directly cannot be excluded by any in-repo
evidence. This is mitigated but not eliminated: both senders are absent from `__all__` and from the
lazy map, making `sync.batch` a private submodule with no advertised surface. **I could not establish
absence of out-of-tree importers, and do not claim to.**

---

## 6. NFR-002 exported-name baseline — FROZEN

WP02's T010 diffs against **this** list, not one it re-derives.

```bash
.venv/bin/python -c "import specify_cli.sync as s; ns=sorted(set(dir(s))|set(getattr(s,'__all__',[]))); print(len(ns)); print(chr(10).join(ns))"
```

# 69 names

```
BackgroundSyncService            _LOCAL_COMMIT_MODULE            emit_wp_status_changed
BatchEventResult                 __all__                         ensure_sync_daemon_running
BatchSyncResult                  __annotations__                 flush_pending_local_commits
LamportClock                     __builtins__                    format_sync_summary
OfflineQueue                     __cached__                      generate_failure_report
SAAS_SYNC_ENV_VAR                __doc__                         generate_node_id
SyncConfig                       __file__                        get_emitter
SyncDaemonStatus                 __getattr__                     get_runtime
SyncRuntime                      __loader__                      get_sync_daemon_status
SyncState                        __name__                        get_sync_service
WebSocketClient                  __package__                     is_saas_sync_enabled
_EVENTS_MODULE                   __path__                        is_truthy
_FEATURE_FLAGS_MODULE            __spec__                        load_sync_state
_LAZY_IMPORTS                    _contextlib                     os
_dossier_emit_via_sync           _dossier_sync_handler           record_local_commit_ack
_lifecycle_saas_fanout_handler   _saas_fanout_handler            register_default_handlers
categorize_error                 emit_dependency_resolved        register_dossier_emitter
emit_diagnostic                  emit_diff_summary_recorded      reset_emitter
emit_error_logged                emit_history_added              reset_runtime
emit_local_commit                emit_mission_closed             reset_sync_service
emit_mission_created             emit_proof_event                saas_sync_disabled_message
emit_token_usage_recorded        emit_wp_assigned                save_sync_state
emit_wp_created                  stop_sync_daemon                write_failure_report
```

### ⚠️ This baseline is only valid on a COLD import — load-bearing for WP02

`specify_cli.sync` is a lazy package, and resolving a lazy name binds its **submodule** as a package
attribute, which inflates `dir()`. Measured:

```
before touching a lazy name : 69
after  s.SyncRuntime; s.WebSocketClient : 80
added: _team, body_queue, client, config, consent, feature_flags, git_metadata,
       project_identity, queue, routing, runtime
```

So WP02 **must** run the one-liner above in a fresh interpreter with no prior attribute access, exactly
as written. Comparing 69 against a figure taken after other imports would show an 11-name "difference"
and read as an NFR-002 violation that has not occurred. The count is stable at 69 across repeated cold
runs (verified 3×).

---

## 7. The out-of-scope files carrying ambiguous "the drain" prose (FR-009)

WP04's T019 residual issue needs a list, not a figure. **Definition used**, assembled from the
mission's own words: `spec.md` Key Entities records that "the drain" has **three** referents, so an
occurrence is *ambiguous* when no adjacent qualifier (`body`, `queue-backed`, `journal`, `dispatch`,
`event`, `retired`, `coord`, `write-target`, `artifact`, `legacy`) names which one is meant;
`plan.md:270` and WP04 T018 scope in-place naming to files the mission already opens, so an
out-of-scope file is one with ≥1 ambiguous occurrence that is **not** in any lane's `write_scope`.

**Control:** `emitter.py` returns **11** total occurrences, matching the figure stated independently
at `plan.md:270` and `WP04:86` before the enumeration is trusted.

### ⚠️ I do not reproduce 13, and I am not bending the definition to reach it

The "13" appears only as a bare assertion in `plan.md:270` and `WP04:86`. **No derivation is recorded
anywhere in the mission artifacts** — `research.md` and `analysis-report.md` do not enumerate it —
so it cannot be reverse-engineered with confidence. All readings, measured:

| Reading (universe = `src/` production code) | Count |
|---|---|
| ≥1 occurrence, excluding mission-opened files | **21** |
| ≥1 *ambiguous* occurrence, excluding mission-opened files | **21** |
| ≥2 *ambiguous* occurrences, excluding mission-opened files | **12** |
| ≥2 occurrences, excluding mission-opened files | **12** |
| ≥2 occurrences, **including** mission-opened files | **13** |
| ≥2 *ambiguous* occurrences, **including** mission-opened files | **13** |

**Most probable reconciliation:** the planner counted `src/` files with ≥2 occurrences **without**
subtracting `sync/batch.py`, which is in lane-b's write scope. `12 + batch.py = 13`. On that reading
the genuine residual for WP04's issue is **12 files**, because `batch.py`'s own 2 ambiguous
occurrences are handled inside WP02 (the module is largely deleted there anyway).

**Operator/WP04 must choose the scope.** All three candidate lists are below so the issue can be
written against any of them.

### The 12 out-of-scope files with ≥2 ambiguous occurrences (recommended residual scope)

| File | total | ambiguous |
|---|---|---|
| `src/specify_cli/sync/emitter.py` | 11 | 7 |
| `src/specify_cli/cli/commands/sync.py` | 8 | 7 |
| `src/specify_cli/event_journal/journal.py` | 5 | 5 |
| `src/specify_cli/delivery/dispatcher.py` | 5 | 4 |
| `src/specify_cli/delivery/selection.py` | 4 | 4 |
| `src/specify_cli/sync/background.py` | 4 | 4 |
| `src/specify_cli/sync/consent.py` | 4 | 4 |
| `src/specify_cli/event_journal/models.py` | 3 | 3 |
| `src/specify_cli/sync/queue.py` | 3 | 3 |
| `src/specify_cli/sync/routing.py` | 2 | 2 |
| `src/specify_cli/delivery/status_report.py` | 2 | 2 |
| `src/specify_cli/delivery/consent_gate.py` | 2 | 2 |

Add `src/specify_cli/sync/batch.py` (3 total / 2 ambiguous, **in** lane-b scope) to reach the
planner's 13.

### The further 9 single-occurrence files (reach 21 under the broadest reading)

`src/specify_cli/cli/commands/implement.py`, `src/specify_cli/delivery/receivers.py`,
`src/specify_cli/delivery/retention.py`, `src/specify_cli/invocation/propagator.py`,
`src/specify_cli/review/pre_review_gate.py`, `src/specify_cli/saas_client/egress_consent.py`,
`src/specify_cli/sync/body_queue.py`, `src/specify_cli/sync/local_commit.py`,
`src/specify_cli/tracker/egress_consent.py` — each 1 total / 1 ambiguous.

### Mission-opened files with drain prose (in-place naming, not residual)

`src/specify_cli/sync/batch.py` (3/2), `src/specify_cli/sync/__init__.py` (1/1),
`src/specify_cli/sync/runtime.py` (1/0 — already qualified, no action).

Note `sync/__init__.py` is named as in-scope prose by `plan.md` IC-05 but appears in **no** lane's
`write_scope`. Whichever lane fixes it will be editing a file outside its declared scope — worth
resolving before WP04 rather than discovering at commit time.

The three referents, for the glossary entry WP04 T018 adds:

| Term use | Means |
|---|---|
| the drain (dispatch selection) | `delivery/selection.py` — the live event drain |
| the body drain | `sync/background.py:280` — artifact body upload |
| the retired queue-backed drain | `sync/batch.py` — gone as of this mission |

---

## Pre-existing debt disclosed, not absorbed

`ruff check scripts/verify_batch_retirement_3167.py` reports **2 findings, both pre-existing and both
`C901` complexity**:

- `_classify_external` is too complex (25 > 15) — **pre-existing and untouched**. It is the
  load-bearing classifier; refactoring it would put the entire classification at risk for a lint
  score, so it is left alone and reported. Candidate for a follow-up issue.
- `main` is too complex (21 > 15) — **pre-existing at 28**. My resolver fixes took it to 30; I
  extracted `_test_file_dispositions` and `_print_tiers` to bring it to **21**, i.e. better than
  found, with output verified byte-identical at each step. Still above the ceiling of 15.

One trivial pre-existing `C420` was fixed (`dict.fromkeys`), with the equivalence proven rather than
assumed, since it sits on a `SyntaxError` fallback path the baseline run never exercises.

`mypy scripts/verify_batch_retirement_3167.py` — **Success: no issues found in 1 source file.**

### A pre-existing architectural red, filed not absorbed

Running `tests/architectural/` from the repository root checkout surfaced **2 failures unrelated to
this mission**, both in `test_pytest_marker_correctness` and both naming
`tests/runtime/test_runtime_bridge_identity.py`: it carries `pytest.mark.fast` while shelling out to
real `git`, and lacks the `git_repo` marker — so CI's `-m git_repo` filter **silently skips it**.

Attributed before being reported: that file was last touched by `943058143` (2026-08-03), and this WP
changed exactly two files, neither a test. Filed per charter DIR-013 as
`Priivacy-ai/spec-kitty#3188`. **Not fixed here** — it is outside this WP's scope, and a disclosed red
beats a silent one.

Also recorded, because it cost a full 10-minute timeout: the complete `tests/architectural/` suite
does **not** finish in 10 minutes. That run was killed at ~26% (no failures up to that point) and is
therefore neither a pass nor a fail; the result above is the re-run, narrowed to the five gates that
could plausibly react to a new file under `scripts/`. The narrowed gate is non-vacuous — it inspects
**2366** test files from the repository root, and **0** from a `.worktrees/…` path.

## What this WP did not change

No source and no test file was modified. `git status --short src/ tests/` is empty, and both files
temporarily mutated by controls 2 and 3 were verified byte-identical to `HEAD` afterwards
(`diagnose.py` `b3949ae1…`, `background.py` `ef754768…`).

---

# 8. WP02 — per-node disposition of every retired test (FR-004 / SC-004)

**Frozen:** 2026-08-04 · **Working path:** the **repository root checkout**
`/home/jeroennouws/dev/sk-missions/3167` on `feat/chain-b-consent-bypass-3167`. The lane-b
worktree `.worktrees/chain-b-consent-bypass-3167-01KZ63HK-lane-b` **does not exist**
(`git worktree list` shows only the root checkout), as on WP01. Everything below was run
from the root checkout, which is also what the `tests/architectural/` collectors require —
a dot-prefixed `.worktrees/…` path segment makes `test_pytest_marker_correctness` discover
zero files and pass vacuously.

## How K was computed, not asserted

At WP02's base commit `f04ee0a78` and again after the deletion:

```bash
.venv/bin/python -m pytest tests/sync tests/architectural --collect-only -q -p no:cacheprovider \
  > /tmp/nodes-{pre,post}.txt
comm -23 <(grep '^tests/' /tmp/nodes-pre.txt  | sort -u) \
         <(grep '^tests/' /tmp/nodes-post.txt | sort -u) > /tmp/retired.txt
wc -l < /tmp/retired.txt
```

```
pre  : 3982 node ids   ("3982 tests collected")
post : 3895 node ids   ("3895 tests collected")
added:    4 node ids   (tests/architectural/test_batch_drain_retired_3167.py)

# K = 91
```

Reconciles exactly: `3982 - 91 + 4 = 3895`. The `grep '^tests/'` filter drops 13 non-node
prose lines the leak-guard epilogue prints; they are identical pre and post and would have
cancelled in `comm` regardless.

Retired nodes per file — matching `plan.md` IC-02's table figure for figure, with **no
collateral loss anywhere else in the two cones**:

| File | Retired | Survived |
|---|---|---|
| `tests/sync/test_batch_sync.py` | 37 | 3 |
| `tests/sync/test_batch_error_surfacing.py` | 26 | 28 |
| `tests/sync/test_offline_replay.py` | 11 | 4 |
| `tests/sync/test_integration.py` | 7 | 2 |
| `tests/sync/test_batch_retry_hygiene.py` | 6 | 0 (whole file) |
| `tests/sync/test_batch_400_no_details_poison_2736.py` | 2 | 0 (whole file) |
| `tests/architectural/test_batch_split_single_authority.py` | 2 | 2 (T018) |
| **Total** | **91** | |

## Two coverage gaps found here, filed rather than papered over

Three of the 91 rows below name a survivor that covers the *area* but **not the specific
branch**. Rather than dress those up as coverage, they are filed as
`Priivacy-ai/spec-kitty#3192`: on the live delivery path the singular `details[*].detail`
key (`receivers.py:501`, read *first* in the fallback chain and the key the real SaaS
sends), and the per-event `accepted` / `warning` / `queued` statuses
(`receivers.py:406-410`), are implemented but pinned by no test in `tests/delivery/`. The
retired tests were their only pin.

Separately, `Priivacy-ai/spec-kitty#3191` records the T009(a) verdict: the per-event
historical mission-state screen is **still owed** and the daemon dispatch path has no
equivalent.

## The rows

Shape: `| <retired node id> | SURVIVOR <node id> | DEATH <one sentence> |`. Every SURVIVOR
value was checked with `grep -qF` against the post-change collection (**91 rows, 69 unique
survivor node ids, 0 misses** — corrected at WP02 review: the earlier "24 named survivors" was a stale
draft figure matching nothing countable, and the corpus had to be widened to `tests/delivery` +
`tests/auth` because two named survivors live outside the two cones the K command collects); no DEATH
sentence is reused.

| Retired node | Survivor / death |
|---|---|
| tests/architectural/test_batch_split_single_authority.py::test_shrink_delegates_to_shared_split_authority | SURVIVOR tests/architectural/test_batch_split_single_authority.py::test_no_reimplemented_len_half_split_outside_authority — DEATH The spy asserted the deleted `_shrink_events_for_retry` invoked `split_in_half`, so the delegation had no subject left; Priivacy-ai/spec-kitty#2755's actual requirement, that nobody re-derives the midpoint, is carried over all of `src/` by T018's AST sweep, which never referenced `batch.py`. |
| tests/architectural/test_batch_split_single_authority.py::test_shrink_uses_plain_split_not_create_aware | SURVIVOR tests/architectural/test_batch_split_single_authority.py::test_ast_matcher_is_non_vacuous — DEATH The forbidden-`create_aware_midpoint` spy guarded a choice made *inside* the deleted 413 byte-shrink, so with that caller gone no call site can reach for the create-aware primitive; the sweep's non-vacuity control stays to prove the surviving guard still fires. |
| tests/sync/test_batch_400_no_details_poison_2736.py::TestWholeBatch400NoDetailsIsTransient::test_no_details_400_does_not_reject_or_bump_innocents | SURVIVOR tests/delivery/test_poison_batch_2736.py::test_one_invalid_event_does_not_poison_innocent_events — DEATH The Priivacy-ai/spec-kitty#2736 requirement is pinned on the live receiver delivery path, and more strongly: the bisecting re-POST actually isolates the culprit and delivers the innocents, where this test only checked that a no-details 400 declined to mark them rejected. |
| tests/sync/test_batch_400_no_details_poison_2736.py::TestWholeBatch400WithDetailsStillRejects::test_details_400_rejects_named_events_and_bumps_retry | SURVIVOR tests/delivery/test_receivers.py::test_http_400_maps_per_event_rejected_with_details — DEATH The complementary arm — a 400 that *does* carry per-event `details` must still reject the events it names — was checked, not assumed, on the live `map_batch_response` path, where three cases cover structured-list, JSON-string and unstructured details. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_category_counts_property | SURVIVOR tests/sync/test_batch_error_surfacing.py::TestBatchSyncResultProperties::test_category_counts_empty — DEATH `category_counts` is a property of the retained `BatchSyncResult`, so it needed no `batch_sync` driver at all; the surviving property test exercises it directly instead of through a deleted sender. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_connection_error_populates_event_results | SURVIVOR tests/delivery/test_receivers.py::test_transport_failure_error_carries_underlying_exception_text — DEATH A connection error can only be raised by a transmit primitive, and `batch.py` now holds zero; the live path's equivalent asserts the underlying exception text survives into the delivery result. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_200_mixed_populates_event_results | SURVIVOR tests/delivery/test_receivers.py::test_rejected_maps_with_error_message_or_error — DEATH Populating per-event results from a mixed 200 body is now the live mapper's job, and it is pinned there per outcome rather than by one omnibus assertion over a `batch_sync` return value. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_400_with_details | SURVIVOR tests/delivery/test_receivers.py::test_http_400_maps_per_event_rejected_with_details — DEATH The 400-with-`details` surfacing requirement moved wholesale to `map_batch_response`, which is reached by every live receiver rather than only by the retired drain. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_400_with_structured_details | SURVIVOR tests/delivery/test_receivers.py::test_http_400_details_as_json_string_is_parsed — DEATH Parsing a JSON-string `details` array into per-event reasons is pinned on the live path; the retired version differed only in reaching that parser through `batch_sync`. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_401_populates_auth_expired_category | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[401] — DEATH A 401 is a batch-level failure the server never adjudicated per event, and the live path classifies it TRANSIENT for every event, which is the same "do not blame the events" conclusion this test expressed as an `auth_expired` category string. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_403_missing_private_team_preserves_direct_ingress_category | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[403] — DEATH The Priivacy-ai/spec-kitty#889 requirement that a missing-Private-Teamspace 403 must not be miscoded as a server error is preserved by the live path treating 403 as its own TRANSIENT batch-level case; the machine-facing category itself is pinned at the resolver, below. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_http_500_populates_server_error_category | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[500] — DEATH 5xx classification moved to the live batch-failure mapper, which additionally covers 503 — a status the retired test never exercised. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_missing_private_team_skip_has_machine_facing_category | SURVIVOR tests/sync/test_team_ingress_resolver.py::test_queue_ingress_skipped_on_no_private_team — DEATH The machine-facing `direct_ingress_missing_private_team` category is emitted by `sync/_team.py`, not by the drain, and the resolver test asserts that structured warning on the live queue-ingress path. |
| tests/sync/test_batch_error_surfacing.py::TestBatchSyncEventResults::test_timeout_populates_retryable_transport_category | SURVIVOR tests/delivery/test_receivers.py::test_transport_timeout_maps_transient_without_poisoning_retries — DEATH Distinguishing a timeout from a server error is a transport concern, and the live equivalent goes further by asserting the timeout does not poison the retry accounting. |
| tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_only_no_details | SURVIVOR tests/delivery/test_receivers.py::test_http_400_unstructured_details_falls_back_to_top_error — DEATH `_parse_error_response` was a second-tier private reachable only through `batch_sync`; the top-level-`error`-only fallback it implemented is pinned on the live mapper instead. |
| tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_with_plain_text_details | SURVIVOR tests/delivery/test_receivers.py::test_http_400_unstructured_details_falls_back_to_top_error — DEATH A plain-string `details` is not structured granularity, and the live path's identical conclusion — fall back to the top-level error rather than invent per-event reasons — covers this shape. |
| tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_with_structured_json_details_string | SURVIVOR tests/delivery/test_receivers.py::test_http_400_details_as_json_string_is_parsed — DEATH The JSON-string-inside-`details` shape is quirky enough to be worth an explicit pin, and it has one on the live path. |
| tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_error_with_details_as_list | SURVIVOR tests/delivery/test_receivers.py::test_http_400_maps_per_event_rejected_with_details — DEATH An already-decoded `details` list is the ordinary case, and the live test uses exactly that shape. |
| tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_details_invalid_json_treated_as_text | SURVIVOR tests/delivery/test_receivers.py::test_http_400_unstructured_details_falls_back_to_top_error — DEATH Malformed JSON in `details` must degrade to text rather than raise, and the live test's `details="not json"` case is the same defence against a `json.loads` blowing up the mapper. |
| tests/sync/test_batch_error_surfacing.py::TestParseErrorResponse::test_per_event_detail_key_surfaces_distinct_violations | SURVIVOR tests/delivery/test_receivers.py::test_http_400_maps_per_event_rejected_with_details — DEATH **Partial only, and filed rather than claimed:** `receivers.py:501` reads `detail.get("detail")` *first*, so the singular key the SaaS actually sends is implemented, but `grep -rn '"detail"' tests/delivery/` returns nothing — the branch is unpinned and is now `Priivacy-ai/spec-kitty#3192`. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_all_success | SURVIVOR tests/delivery/test_receivers.py::test_stub_and_teamspace_produce_identical_outcomes_for_equivalent_payloads — DEATH The all-success 200 path is the baseline the live receiver-equivalence test drives, so it is exercised on every receiver rather than only on the retired one. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_accepted_and_warning_are_successful | SURVIVOR tests/delivery/test_receivers.py::test_unknown_per_event_status_maps_rejected — DEATH **Partial only, and filed rather than claimed:** `receivers.py:406-407` does map `accepted`/`warning` to SUCCESS, but no `tests/delivery/` test names either status, and unrecognised statuses fall through to REJECTED — so the branch is unpinned and is now `Priivacy-ai/spec-kitty#3192`. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_mixed_results | SURVIVOR tests/delivery/test_receivers.py::test_stub_and_teamspace_agree_on_duplicate_redelivery — DEATH The success/duplicate/rejected mixture is decomposed on the live path into per-outcome tests plus a duplicate-redelivery pin, which is stricter than one combined counter assertion. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_empty_results_array | SURVIVOR tests/delivery/test_receivers.py::test_event_absent_from_results_maps_pending_not_success — DEATH An empty `results` array is the degenerate case of an event being absent from the response, and the live path's rule for that is strictly safer: PENDING, never a silent success. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_mixed_with_pending_does_not_inflate_errors | SURVIVOR tests/delivery/test_receivers.py::test_explicit_pending_status_maps_pending — DEATH Pending events inflating the error count was an artefact of the deleted parser's counter bookkeeping; the live path has no shared counter to inflate, because each event carries its own outcome value. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_pending_does_not_count_toward_success_count | SURVIVOR tests/sync/test_batch_sync.py::TestBatchSyncResult::test_success_count — DEATH `success_count` is terminal-success-only arithmetic on the retained `BatchSyncResult`, and the surviving property test pins that arithmetic without needing a response body at all. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_pending_status_is_pending_not_error | SURVIVOR tests/delivery/test_receivers.py::test_explicit_pending_status_maps_pending — DEATH The `Priivacy-ai/spec-kitty#1182` rule that a per-event `pending` must not become an Unknown error is pinned verbatim on the live mapper. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_queued_status_is_pending_not_error | SURVIVOR tests/delivery/test_receivers.py::test_explicit_pending_status_maps_pending — DEATH **Partial only, and filed rather than claimed:** `receivers.py:410` maps `queued` to PENDING, but only `"pending"` is pinned in `tests/delivery/`, so the `queued` half of `Priivacy-ai/spec-kitty#1182` is unpinned and is now `Priivacy-ai/spec-kitty#3192`. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_rejected_with_no_error_message | SURVIVOR tests/delivery/test_receivers.py::test_rejected_maps_with_error_message_or_error — DEATH Supplying a placeholder when a rejection carries no message is exactly what the live test's "error_message or error" pin covers, on a mapper every receiver shares. |
| tests/sync/test_batch_error_surfacing.py::TestParseEventResults::test_error_field_fallback | SURVIVOR tests/delivery/test_receivers.py::test_ordinary_rejection_stays_retryable — DEATH The `error_message` → `error` key fallback is one branch of the live mapper's rejection handling, whose observable contract — an ordinary content rejection stays retryable — is pinned there. |
| tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_401_does_not_bump_retry_count | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[401] — DEATH `retry_count` was a column the deleted drain wrote via `OfflineQueue.process_batch_results`; the live ledger replaces per-row counters with a durable status, and a 401 producing TRANSIENT for every event is the same Priivacy-ai/spec-kitty#889 guarantee expressed in that vocabulary. |
| tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_403_private_team_does_not_bump_retry_count | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[403] — DEATH The private-team 403 variant is covered by the live path's parametrised 403 case, which reaches the same non-blaming outcome without depending on which body text the server happened to return. |
| tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_403_generic_unauthorized_does_not_bump_retry_count | SURVIVOR tests/delivery/test_ledger.py::test_nonterminal_states_remain_selectable — DEATH A generic 403 left events eligible for a later attempt, and on the live path that eligibility is a ledger property — non-terminal rows stay selectable — rather than a counter that must be observed not to move. |
| tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_http_500_does_not_bump_retry_count | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[500] — DEATH 5xx never adjudicates individual events, and the live parametrised case asserts that for every event in the batch, extended to 503 as well. |
| tests/sync/test_batch_retry_hygiene.py::TestRetryCountStableOnBatchLevelFailures::test_preflight_no_private_team_does_not_bump_retry_count | SURVIVOR tests/sync/test_team_ingress_resolver.py::test_emitter_ingress_skipped_on_no_private_team — DEATH The pre-flight it exercised was the deleted `_current_team_slug`; the surviving resolver test proves the live ingress path skips rather than sends when no Private Teamspace resolves, which is the precondition this test approached from the queue-mutation side. |
| tests/sync/test_batch_retry_hygiene.py::TestRetryCountStillBumpsOnPerEventRejection::test_per_event_rejection_still_bumps_retry_count | SURVIVOR tests/delivery/test_ledger.py::test_batch_transient_does_not_flip_per_event_rejection — DEATH This was the positive control for the whole Priivacy-ai/spec-kitty#889 suite — a genuine per-event rejection *must* still be attributed — and the ledger survivor keeps exactly that distinction, pinning that a batch-level transient and a per-event rejection stay separately identifiable and neither becomes terminal. |
| tests/sync/test_batch_sync.py::TestBatchSyncEmptyQueue::test_batch_sync_empty_queue | SURVIVOR tests/delivery/test_dispatcher.py::test_post_empty_selection_short_circuits — DEATH Returning early on an empty queue is a property of whatever drains it, and the live dispatcher's empty-selection short-circuit is that property on the code path that actually runs. |
| tests/sync/test_batch_sync.py::TestSaasFeatureFlag::test_batch_sync_skips_network_when_disabled | SURVIVOR tests/sync/test_no_queue_drain_constructed_3030.py::test_no_production_module_constructs_the_queue_backed_drain — DEATH The flag check it exercised lived inside the deleted sender, and the stronger guarantee now holds unconditionally: no queue-backed drain can be constructed at all, flag or no flag. |
| tests/sync/test_batch_sync.py::TestHistoricalMissionStateGuard::test_batch_sync_rejects_legacy_status_row_before_network | SURVIVOR none — DEATH **The requirement did NOT die and no survivor exists:** the per-event forbidden-key screen is absent from all of `src/`, the live analogue `enforce_teamspace_mission_state_ready` is CLI-entry-time and unreachable from `sync/daemon.py`/`delivery/`, and the envelope contract gate is shallow (probed: a top-level `feature_slug` raises, the nested one this test used does not) and omits `legacy_aggregate_id`/`work_package_id` entirely — filed as `Priivacy-ai/spec-kitty#3191`. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_success | SURVIVOR tests/delivery/test_receivers.py::test_teamspace_posts_to_resolved_endpoint_with_bearer_header — DEATH The happy-path POST-and-remove behaviour belonged to the deleted sender; the live receiver test pins the equivalent successful POST on the path the daemon actually takes. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_rehydrates_stale_drain_blockers_before_post | SURVIVOR tests/sync/test_team_ingress_resolver.py::test_queue_ingress_rehydrates_and_sends_private — DEATH Re-resolving a stale `drain_blocked_reason` at drain time is the resolver's behaviour, and the surviving test drives that rehydrate-then-send sequence through `queue.py`'s live ingress rather than through `batch_sync`. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_leaves_rows_untouched_when_checkout_still_disabled | SURVIVOR tests/delivery/test_dispatch_window_consent_3030.py::test_no_non_consented_event_ever_enters_the_live_dispatch_window — DEATH This asserted the deleted sender left rows alone when the checkout was not sync-enabled; the live dispatch window enforces the stronger Priivacy-ai/spec-kitty#3030 invariant that a non-consented event never enters it in the first place. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_with_duplicates | SURVIVOR tests/delivery/test_receivers.py::test_stub_and_teamspace_agree_on_duplicate_redelivery — DEATH Duplicate handling is a response-mapping concern, and the live test pins it across two receivers so the two cannot drift. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_gzip_compression | SURVIVOR tests/delivery/test_receivers.py::test_teamspace_posts_to_resolved_endpoint_with_bearer_header — DEATH Gzip framing moved with the transmit surface: the live receiver compresses at `receivers.py:674` and the surviving test asserts `Content-Encoding: gzip` on the real POST. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_consumes_advertised_max_events_per_batch | SURVIVOR tests/delivery/test_dispatcher.py::test_select_undelivered_honours_limit — DEATH Server-advertised per-batch limits were probed by the deleted `_fetch_advertised_sync_ingress_limits`, which was itself a transmit primitive; batch sizing on the live path is a selection limit, pinned as such. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_shrinks_batch_to_advertised_decompressed_bytes | SURVIVOR tests/delivery/test_receivers.py::test_multi_event_413_maps_transient_not_terminal_failed — DEATH Pre-emptive byte-shrinking against an advertised cap is gone with the probe that fetched it; oversize is now handled reactively, and the live test pins that a multi-event 413 stays transient rather than being written off. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_caps_advertised_limit_to_cli_ceiling | SURVIVOR tests/delivery/test_receivers.py::test_oversized_413_maps_terminal_failed — DEATH The `Priivacy-ai/spec-kitty#1045` CLI ceiling clamped a value obtained from the deleted health probe, so the clamp has no input; the live path's protection against an unsendable payload is the terminal-failed classification pinned here. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_uses_fallback_decompressed_byte_limit | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_all_invalid_batch_is_bounded_and_every_event_isolated — DEATH The fallback byte budget existed for when the health probe was unavailable; with no probe there is no fallback, and boundedness is instead guaranteed by the bisection terminating with every event isolated. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_retries_smaller_batch_after_server_size_rejection | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_drain_leaves_exactly_the_culprit_and_re_drain_does_not_re_poison — DEATH Shrink-and-retry-on-size-rejection is superseded by the live bisecting re-POST, which the surviving test proves converges on exactly the culprit and does not re-poison on a second pass. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_reports_single_oversized_event_without_posting | SURVIVOR tests/delivery/test_receivers.py::test_oversized_413_maps_terminal_failed — DEATH Isolating a single unsendable event without posting it was `_handle_single_oversized_event`'s job; the live path reaches the same terminal verdict from the server's 413 instead of predicting it locally. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_server_413_on_single_event_classifies_as_oversized_event | SURVIVOR tests/delivery/test_receivers.py::test_server_refusal_category_maps_to_terminal_failed — DEATH Classifying a singleton 413 as permanent rather than as a content rejection is pinned on the live mapper, where a server refusal maps to terminal-failed. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_throttled_category_on_429 | SURVIVOR tests/delivery/test_receivers.py::test_batch_level_failure_maps_transient_for_every_event[503] — DEATH 429 was categorised `throttled` rather than `retryable_transport` so callers would back off; the live path folds throttling into the batch-level transient family, of which 503 is the pinned representative, and no caller now reads a category string to decide. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_auth_header | SURVIVOR tests/delivery/test_receivers.py::test_teamspace_endpoint_and_bearer_auth — DEATH Bearer-token attachment is a receiver property, and the live test asserts the exact `auth_headers()` mapping rather than inspecting a mocked call made by the drain. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_sends_private_team_slug_header | SURVIVOR tests/sync/test_team_ingress_resolver.py::test_emitter_ingress_rehydrates_and_sends_private — DEATH The header value came from the deleted `_current_team_slug`; that the Private Teamspace id is what reaches ingress is pinned at the resolver, on the emitter path that still runs. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_prefers_private_team_over_shared_default | SURVIVOR tests/auth/test_token_manager.py::test_rehydrate_early_returns_when_session_already_has_private — DEATH Preferring the Private Teamspace over a drifted session default is decided inside the token manager's membership resolution, which the surviving test pins directly at the branch that makes the choice. |
| tests/sync/test_batch_sync.py::TestBatchSyncSuccess::test_batch_sync_url_construction | SURVIVOR tests/delivery/test_receivers.py::test_external_endpoint_verbatim_and_optional_auth — DEATH URL assembly moved to the receivers, which expose `endpoint_url` as an inspectable attribute — a stronger pin than asserting the argument of a mocked `requests.post`. |
| tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_auth_failure | SURVIVOR tests/delivery/test_receivers.py::test_teamspace_gate_set_is_saas_private_teamspace_auth — DEATH A 401 from the deleted POST is unreachable; authentication is now a declarative receiver gate evaluated before any request, which is where the surviving test checks it. |
| tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_bad_request | SURVIVOR tests/delivery/test_receivers.py::test_http_400_unstructured_details_falls_back_to_top_error — DEATH Generic 400 handling is pinned on the live mapper, whose fallback to the top-level error is the same "surface something actionable" behaviour without a sender to drive it. |
| tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_server_error | SURVIVOR tests/delivery/test_ledger.py::test_transient_then_success_transitions_cleanly — DEATH Keeping events durable across a 5xx is now a ledger transition property, and the surviving test proves a transient row recovers cleanly to success on a later attempt. |
| tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_timeout | SURVIVOR tests/delivery/test_receivers.py::test_non_json_response_body_maps_transient — DEATH Timeouts and unparseable bodies are the same class of "no verdict from the server" on the live path, and the surviving test pins that class as transient rather than as a rejection. |
| tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_connection_error | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_transport_failure_is_not_bisected — DEATH A connection error must not be mistaken for a content problem, and the live path makes that explicit by refusing to bisect on transport failure — a distinction the retired test could not express. |
| tests/sync/test_batch_sync.py::TestBatchSyncErrors::test_batch_sync_partial_failure | SURVIVOR tests/delivery/test_ledger.py::test_delivered_to_a_still_selectable_for_b — DEATH Partial success within a batch is now recorded per event-and-target in the ledger, and the surviving test pins that per-pair independence, which is strictly finer than the retired counter split. |
| tests/sync/test_batch_sync.py::TestBatchSyncLimit::test_batch_sync_respects_limit | SURVIVOR tests/delivery/test_ledger.py::test_select_undelivered_respects_limit — DEATH The `limit` argument belonged to the deleted sender's signature; bounding how much is taken per pass is now a selection concern and is pinned at the selector. |
| tests/sync/test_batch_sync.py::TestBatchSync1000Events::test_batch_sync_1000_events | SURVIVOR tests/delivery/test_liveness_predicate_before_limit_3030.py::test_sc002_ten_consented_events_ship_behind_a_2000_row_backlog — DEATH Large-payload behaviour is exercised at greater scale on the live path, where a 2000-row backlog must not starve the events that are ready to ship. |
| tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_in_batches | SURVIVOR tests/delivery/test_nfr002_loop_permanence_3030.py::test_an_empty_selection_ends_the_pass_after_one_dispatch — DEATH Multi-batch looping was `sync_all_queued_events`, the second seed of this retirement; the live dispatcher's pass structure and its termination condition are pinned instead. |
| tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_stops_on_all_errors | SURVIVOR tests/delivery/test_liveness_predicate_before_limit_3030.py::test_the_backlog_is_left_in_the_journal_undeleted — DEATH Stopping when no event in a batch succeeded was the deleted `_should_stop_sync_loop`; the property that mattered — nothing is silently discarded when a pass makes no progress — is pinned as the journal being left undeleted. |
| tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_continues_past_oversized_event | SURVIVOR tests/delivery/test_liveness_predicate_before_limit_3030.py::test_a_delivered_prefix_must_not_starve_the_undelivered_tail — DEATH An oversized event at the queue head stalling everything behind it is head-of-line blocking, and the live guarantee against it is the stronger, more general one pinned here. |
| tests/sync/test_batch_sync.py::TestSyncAllQueuedEvents::test_sync_all_progress_output_is_log_readable | SURVIVOR tests/delivery/test_per_project_report_3030.py::test_non_consenting_projects_are_flagged_for_the_operator — DEATH The `print`-based progress output was emitted from inside the deleted loop; operator-facing reporting on the live path is the per-project dispatch report, which is what the surviving test inspects. |
| tests/sync/test_batch_sync.py::test_sync_all_queued_events_terminates_on_no_private_team | SURVIVOR tests/delivery/test_nfr002_loop_permanence_3030.py::test_an_empty_selection_ends_the_pass_after_one_dispatch — DEATH This post-merge regression pinned that the deleted loop could not spin forever when the resolver returned None for every batch; the live loop's termination is pinned unconditionally, and the spinning loop itself no longer exists. |
| tests/sync/test_batch_sync.py::test_batch_shared_only_session_triggers_one_me_rehydrate | SURVIVOR tests/sync/test_team_ingress_resolver.py::test_queue_ingress_rehydrates_and_sends_private — DEATH AC-002's exactly-one `/api/v1/me` rehydrate followed by a send is pinned with `me_route.call_count == 1` on the live queue-ingress path; the claim that this was "covered at `body_transport.py`" was **checked and is false** — that module never calls the resolver, it only imports the category constant. |
| tests/sync/test_batch_sync.py::test_batch_skips_ingress_when_rehydrate_yields_no_private | SURVIVOR tests/sync/test_team_ingress_resolver.py::test_emitter_ingress_skipped_on_no_private_team — DEATH AC-001/AC-004 — a rehydrate that yields no Private Teamspace must skip rather than send, with a structured warning — is pinned on both live ingress paths, emitter and queue, rather than only through the drain. |
| tests/sync/test_batch_sync.py::test_batch_negative_cache_honored_across_calls | SURVIVOR tests/auth/test_token_manager.py::test_rehydrate_negative_cache_skips_http — DEATH The at-most-one-GET-per-process guarantee is pinned at its mechanism instead of through a driver: one surviving test proves an authoritative empty-private response sets the cache, and this one proves a hot cache issues no HTTP. |
| tests/sync/test_batch_sync.py::test_batch_healthy_session_no_rehydrate | SURVIVOR tests/auth/test_token_manager.py::test_rehydrate_early_returns_when_session_already_has_private — DEATH A session that already exposes a Private Teamspace must short-circuit before any request, and the surviving test asserts that branch directly with `route.call_count == 0`. |
| tests/sync/test_integration.py::TestFullFlow::test_event_emission_to_queue_to_sync | SURVIVOR tests/delivery/test_incident_reproduction_3030.py::test_sc001_only_the_consented_project_is_delivered — DEATH The emit-to-queue-to-sync flow now terminates in the delivery dispatcher, and the live end-to-end pin is the Priivacy-ai/spec-kitty#3030 incident reproduction rather than a mocked POST from the retired sender. |
| tests/sync/test_integration.py::TestFullFlow::test_batch_payload_contains_correct_events | SURVIVOR tests/delivery/test_receivers.py::test_external_reuses_the_shared_batch_mapper — DEATH Payload construction moved to `receivers._build_payload`, and the surviving test pins that every receiver shares one mapper so the wire shape cannot fork per transport. |
| tests/sync/test_integration.py::TestFullFlow::test_lamport_clock_ordering_preserved | SURVIVOR tests/sync/test_integration.py::TestLamportClockReconciliation::test_clock_receive_updates_from_remote — DEATH Clock monotonicity is a `sync.clock` property that never needed a sender; the surviving class in this same file pins it against the clock directly, which is why the file was split rather than deleted. |
| tests/sync/test_integration.py::TestBatchSyncAuthHandling::test_401_marks_events_for_retry | SURVIVOR tests/delivery/test_ledger.py::test_nonterminal_states_remain_selectable — DEATH Marking events for retry after a 401 is expressed on the live path as the row staying non-terminal and therefore selectable on the next pass. |
| tests/sync/test_integration.py::TestBatchSyncAuthHandling::test_server_error_keeps_events_queued | SURVIVOR tests/delivery/test_ledger.py::test_record_success_is_terminal_and_does_not_delete_journal — DEATH Durability across a 5xx is now a journal invariant rather than a queue-row side effect, and the surviving test pins that even a terminal success does not delete the journal entry. |
| tests/sync/test_integration.py::TestMultiEventBatch::test_feature_created_plus_wp_batch | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_straddling_create_receipts_before_its_status — DEATH The finalize-tasks shape — a create event followed by its dependent status events in one batch — is pinned far more strictly on the live path, where the create must be receipted before its status even across a bisection split. |
| tests/sync/test_integration.py::TestMultiEventBatch::test_mixed_event_types_in_batch | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_same_wp_poison_pair_terminates_and_preserves_create_before_status — DEATH Heterogeneous event types in one batch are covered by the live ordering suite, which additionally proves the ordering survives a poison-pair funnel. |
| tests/sync/test_offline_replay.py::TestReconnectionTriggersBatchSync::test_reconnection_triggers_batch_sync | SURVIVOR tests/delivery/test_dispatcher.py::test_select_undelivered_honours_limit — DEATH Reconnection no longer triggers a queue-backed batch sync at all; the dispatcher selects undelivered work on its own schedule, which is the behaviour now worth pinning. |
| tests/sync/test_offline_replay.py::TestReconnectionTriggersBatchSync::test_multiple_reconnection_cycles | SURVIVOR tests/delivery/test_nfr003_predicate_cost_3030.py::test_nfr003_selection_cost_does_not_scale_with_journal_size — DEATH Repeated offline/online cycles were a proxy for "the drain stays healthy across many passes"; the live equivalent is the stronger claim that per-pass selection cost does not grow with the journal. |
| tests/sync/test_offline_replay.py::TestBatchSyncThroughput::test_batch_sync_throughput_1000_events | SURVIVOR tests/delivery/test_nfr003_predicate_cost_3030.py::test_the_filtered_read_carries_no_limit_and_no_payload — DEATH A wall-clock throughput assertion over a mocked network measured the deleted sender's own loop; the live cost guarantee is structural — the filtered read carries neither a limit nor payloads — which does not rot with machine speed. |
| tests/sync/test_offline_replay.py::TestBatchSyncThroughput::test_batch_sync_throughput_multiple_batches | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_adjacent_same_wp_pair_funnel_terminates_and_isolates_culprit — DEATH Preserving batch boundaries across several sends is pinned on the live path as a termination-and-isolation property, which is what "boundaries held" was standing in for. |
| tests/sync/test_offline_replay.py::TestIdempotency::test_idempotency_duplicate_events | SURVIVOR tests/delivery/test_batch_bisection_ordering.py::test_reposting_an_already_accepted_event_returns_duplicate — DEATH Re-sending an already-accepted `event_id` must come back `duplicate`, and the live test asserts that on the real repost path rather than against a fabricated response body. |
| tests/sync/test_offline_replay.py::TestIdempotency::test_idempotency_mixed_results | SURVIVOR tests/delivery/test_ledger.py::test_idempotent_redelivery_yields_duplicate_unchanged_event_ids — DEATH Mixing new and duplicate events in one batch is now a ledger idempotency property, pinned as redelivery leaving the event ids unchanged. |
| tests/sync/test_offline_replay.py::TestEventRecovery::test_100_percent_event_recovery | SURVIVOR tests/delivery/test_ledger.py::test_delivered_anywhere_true_on_any_terminal_success — DEATH Full recovery of a queued set is expressed on the live path as every event reaching a terminal success in the ledger, which is auditable per event rather than as an aggregate count. |
| tests/sync/test_offline_replay.py::TestEventRecovery::test_partial_failure_recovery | SURVIVOR tests/delivery/test_ledger.py::test_delivered_anywhere_false_for_only_nonterminal_rows — DEATH Eventual recovery after partial failure requires that non-terminal rows are not mistaken for delivered, which is exactly the negative case the surviving test pins. |
| tests/sync/test_offline_replay.py::TestEventRecovery::test_event_order_preserved | SURVIVOR tests/sync/test_offline_replay.py::TestQueueEventsOffline::test_queue_100_events_offline — DEATH FIFO ordering is an `OfflineQueue.drain_queue` property, and the surviving test in this same file asserts it over 100 events without any sender — which is why this file was split rather than deleted. |
| tests/sync/test_offline_replay.py::TestOfflineWorkflowEndToEnd::test_complete_offline_workflow | SURVIVOR tests/sync/test_offline_replay.py::TestQueueEventsOffline::test_queue_events_with_complex_payloads — DEATH The online→offline→reconnect→sync narrative had its final leg deleted; the half that remains real — that events queued offline are stored intact, nested payloads included — is pinned by the surviving class. |
| tests/sync/test_offline_replay.py::TestOfflineWorkflowEndToEnd::test_intermittent_connectivity | SURVIVOR tests/delivery/test_dispatch_honours_drain_blocked_3031.py::test_consent_predicate_must_apply_before_limit_not_after — DEATH Intermittent connectivity was simulated by alternating the deleted sender's mocked response; the live dispatcher's behaviour under partial progress is governed by Priivacy-ai/spec-kitty#3031's predicate-before-limit rule, pinned here. |

## The `tests/sync` cone (SC-006 / NFR-003), with the one difference I could NOT fully resolve

The base commit reproduces `analysis-report.md` §4's committed baseline exactly, which is what
makes the comparison below trustworthy at all:

| Run | Tree | Result | Errors |
|---|---|---|---|
| 1 | base `f04ee0a78` | 2376 passed, 19 skipped (input 2395) | 5 |
| 2 | base, the 89 `tests/sync` nodes `--deselect`ed | 2287 passed, 19 skipped, 89 deselected | 5 |
| 3 | WP02 applied | 2287 passed, 19 skipped (input 2306) | 7 |
| 4 | WP02 applied, re-run from a verified-clean tree | 2287 passed, 19 skipped | 6 |

Attributed:

- **input −89** — exactly the 89 retired `tests/sync` nodes (K's other 2 are architectural).
- **passed −89** — exactly the same 89. No other passing node was lost.
- **skipped 0.**
- **errors +1/+2 — disclosed, not resolved, and not reproducible.** The **same 5** appear in
  every run and are the known filed set. The *excess* names a different test each run and
  always reports only an anonymous live thread (`target=None`): run 3 added
  `test_background.py::TestSingletonAccessor::test_get_sync_service_returns_same_instance`
  and `test_daemon_self_retirement.py::TestStartSelfCheckTick::test_returned_timer_thread_is_daemon`;
  run 4 added `test_strict_json_stdout.py::test_agent_tasks_status_json_strict_with_sync_enabled_isolated`
  and **neither of run 3's two reappeared**. Run 3's pair passes cleanly when run narrowed at
  either commit. The guard diffs the live-thread set at teardown, so a thread still winding
  down is blamed on whichever test is observing it. Filed as
  `Priivacy-ai/spec-kitty#3193`; the underlying leaks are the already-filed
  `Priivacy-ai/spec-kitty#3130` / `Priivacy-ai/spec-kitty#3115` debt.

**I am not claiming the error count returned to baseline. It did not.** What is established is
that the excess is non-deterministic, names files this WP does not touch, does not reproduce on
the same node twice, and is absent when those tests run narrowed. Every daemon-bearing
measurement above was preceded by `pgrep -af 'run_sync[_]daemon'`; one earlier control run was
discarded because that check found two leaked daemons on ports 9400-9401, and it was re-run
from a verified-clean tree via a reap script (bracket class in both the `pkill -f` and
`pgrep -f` forms).

## Deliberate choices a reviewer should be able to reverse cheaply

- **Class names in the split files are unchanged**, including `TestBatchSyncSuccess`, which now
  holds a single `categorize_error` unit test. That reads oddly, and it is the accepted cost of
  keeping the surviving node ids stable — the mission's own survivor check greps them with
  `grep -qF`, so a tidier rename would have registered as 3 more retired nodes plus 3 new ones.
- **Two docstring "drain" occurrences in `sync/batch.py` were qualified** (`:131`
  → the dispatch drain loop, and `run_final_sync_with_retries`' "later daemon drain" → the
  dispatch drain via `delivery/selection.py`). Manifest §7 records that `batch.py`'s ambiguous
  drain prose is "handled inside WP02"; 13 of its 15 occurrences died with the deletion and
  these were the 2 left in surviving docstrings. FR-009's broader sweep remains WP04's.
- **`tests/sync/conftest.py` was NOT touched** (it belongs to IC-03/WP03). Its
  `specify_cli.sync.batch.is_sync_enabled_for_checkout` patch uses `raising=False`, so removing
  that name creates no red here — it now *creates* an attribute nothing reads, which is exactly
  the FR-005/FR-006 condition WP03 addresses.
- **The two `private_ingress_scope` autouse fixtures** in `test_batch_error_surfacing.py` and
  `test_offline_replay.py` were removed: they `monkeypatch.setattr` the deleted
  `batch._current_team_slug` with `raising` at its default, so leaving them would have failed
  every surviving test in both files at setup.
