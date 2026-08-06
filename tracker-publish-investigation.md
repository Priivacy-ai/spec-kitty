# Pre-spec investigation: `tracker sync publish` (#3168) and `TrackerProjectConfig._extra` (#3169)

**Investigator:** Python Pedro (implementer profile, debugging mode)
**Tree:** `/home/jeroennouws/dev/sk-missions/3168`, branch `investigate/tracker-publish-3168`
**Commit:** `709a59534` (fresh checkout at `upstream/main`)
**Date:** 2026-08-07
**Status:** investigation only — no production code changed, no spec written, no mission created.

Every `file:line` below was re-derived on `709a59534`. The issues were verified at `abca7ec9`;
where the issue cites a line, I note whether it still matches (all cited lines do — no drift).

---

## Part 1 — #3168: reproduced

### Verdict: **REPRODUCED.** Real traceback from a real operator CLI invocation.

Reproduction recipe (fully deterministic, no mocks, no network):

```
mkdir -p /tmp/repro/.kittify
cat > /tmp/repro/.kittify/config.yaml <<'EOF'
tracker:
  provider: beads
  workspace: demo-workspace
  display_label: Demo
  some_unknown_key: preserved-value
EOF
cd /tmp/repro && SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty tracker sync publish
```

Terminal frames of the actual traceback, verbatim:

```
/home/jeroennouws/dev/sk-missions/3168/src/specify_cli/cli/commands/tracker.py:348 in _run_or_exit
   347 │   try:
 ❱ 348 │   │   return fn()
   349 │   except (RuntimeError, ValueError) as exc:

/home/jeroennouws/dev/sk-missions/3168/src/specify_cli/cli/commands/tracker.py:1225 in _run
 ❱ 1225 │   │   payload = _service().sync_publish()

/home/jeroennouws/dev/sk-missions/3168/src/specify_cli/tracker/service.py:203 in sync_publish
 ❱ 203 │   │   return self._resolve_backend().sync_publish(**kwargs)

AttributeError: 'LocalTrackerService' object has no attribute 'sync_publish'
```

Process exit status: **1**. The traceback is rendered by the top-level handler, not caught.

Both local providers reproduce identically:

| provider | result |
|---|---|
| `beads` | `AttributeError: 'LocalTrackerService' object has no attribute 'sync_publish'`, exit 1 |
| `fp`    | `AttributeError: 'LocalTrackerService' object has no attribute 'sync_publish'`, exit 1 |

### Precise call path

| # | Site | Code |
|---|---|---|
| 1 | `src/specify_cli/cli/commands/tracker.py:1211` | `def sync_publish_command(` — the `@sync_app.command("publish")` entry point |
| 2 | `src/specify_cli/cli/commands/tracker.py:1222` | `_check_sync_readiness()` — **no-op for local bindings** (see below) |
| 3 | `src/specify_cli/cli/commands/tracker.py:1235` | `_run_or_exit(_run)` |
| 4 | `src/specify_cli/cli/commands/tracker.py:348` | `return fn()` inside the `try` |
| 5 | `src/specify_cli/cli/commands/tracker.py:1225` | `payload = _service().sync_publish()` |
| 6 | `src/specify_cli/tracker/service.py:203` | `return self._resolve_backend().sync_publish(**kwargs)` ← **raise site** |

`_resolve_backend()` (`service.py:65`) returns `LocalTrackerService` for a local provider:

```python
if config.provider in LOCAL_PROVIDERS:
    return LocalTrackerService(self._repo_root, config)
```

### What a "beads/fp binding" is, and why it differs

`src/specify_cli/tracker/config.py:20-22` is the single source of truth:

```python
SAAS_PROVIDERS: frozenset[str] = frozenset({"linear", "jira", "github", "gitlab"})
LOCAL_PROVIDERS: frozenset[str] = frozenset({"beads", "fp"})
REMOVED_PROVIDERS: frozenset[str] = frozenset({"azure_devops"})
```

A beads/fp binding is a **local** provider: it routes to `LocalTrackerService`, which talks to a
local SQLite store and a direct connector, with no hosted control plane, no auth token, and no
background daemon. The difference that matters here is at
`src/specify_cli/cli/commands/tracker.py:296-312` — `_check_sync_readiness` short-circuits:

```python
if _is_local_binding():
    return
```

So a local binding **skips the entire readiness chain** and lands directly on the raise site.
A SaaS binding would be stopped earlier by auth/reachability checks in most environments. That is
why this surfaces on beads/fp and effectively only there.

### Missing, or present-but-wrong? — **Missing.**

This is the distinction you asked me to settle, and it settles cleanly:

```
sync_publish in dir(): False
has __getattr__:       False
MRO:                   ['LocalTrackerService', 'object']
sync_* attrs:          ['sync_pull', 'sync_push', 'sync_run']
```

No `__getattr__` fallback, no proxy, no inherited base that could supply it, no `None`-valued
attribute. The method is simply **not defined**. `grep -c "def sync_publish"
src/specify_cli/tracker/local_service.py` returns `0`, matching the issue's claim.

This is a *missing definition* defect, not a *wrong value* defect — the fix is to add a method,
not to guard a value.

### Reachable from a real operator invocation? — **Yes.**

The reproduction above is the real CLI binary (`.venv/bin/spec-kitty`), not an internal call. The
only precondition beyond a local binding is the rollout gate `SPEC_KITTY_ENABLE_SAAS_SYNC=1`
(`src/specify_cli/core/saas_sync_config.py:20`), enforced at `tracker.py:364`. Any operator with
the tracker surface enabled and a beads/fp binding hits this on the first `sync publish`.

### The delegation matrix — the decisive measurement

I extracted, by AST, every `TrackerService` method that delegates via `self._resolve_backend().X()`
and checked `hasattr` on both backends:

| facade method | → backend attr | `LocalTrackerService` | `SaaSTrackerService` |
|---|---|---|---|
| `map_add`      | `map_add`      | True  | True |
| `map_list`     | `map_list`     | True  | True |
| `status`       | `status`       | True  | True |
| **`sync_publish`** | **`sync_publish`** | **False** | **True** |
| `sync_pull`    | `sync_pull`    | True  | True |
| `sync_push`    | `sync_push`    | True  | True |
| `sync_run`     | `sync_run`     | True  | True |
| `unbind`       | `unbind`       | True  | True |

**Exactly one cell of sixteen is missing.** The facade contract is otherwise fully honoured on both
backends. This is the single strongest piece of evidence in this report.

### Why it shipped green

`tests/agent/cli/commands/test_tracker.py:1350`,
`test_sync_publish_local_provider_ignores_manual_daemon_policy`, exercises this exact command with a
local binding — and passes. It passes because of line 1380:

```python
    mock_svc = MagicMock()
    mock_svc.sync_publish.return_value = {
```

A bare `MagicMock()` with **no `spec=`** auto-creates `sync_publish`, so the test can never observe
that the real backend lacks it. The same test uses `MagicMock(spec=SyncConfig)` for its config mock
two lines earlier — the `spec=` discipline was applied to one mock and not the other. The test's
actual subject is the daemon-policy short-circuit, which it does validate correctly; it simply
never had the missing method in its field of view.

This is the `test-scaffolding-as-design-smell` pattern from my profile: the defect lives precisely
in the seam the mock replaced.

### A finding beyond the issue's scope

`sync publish` is **non-functional for every supported provider**, not just local ones.

The SaaS side is a deliberate refusal — `src/specify_cli/tracker/saas_service.py:612-616`:

```python
def sync_publish(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ARG002
    """Always fails -- snapshot publish is not supported for SaaS providers."""
    raise TrackerServiceError(
        "Snapshot publish is not supported for SaaS-backed providers. "
        "Use `spec-kitty tracker sync push` to push changes through the SaaS control plane."
    )
```

Confirmed live against a `github` binding:

```
TrackerServiceError: Snapshot publish is not supported for SaaS-backed providers.
Use `spec-kitty tracker sync push` to push changes through the SaaS control plane.
```

So across all six supported providers: **four raise a clean refusal, two raise a traceback, and
zero publish anything.** The CLI docstring at `tracker.py:1214-1220` states the intent:

> This command is not supported for SaaS-backed providers.  Use
> ``spec-kitty tracker sync push`` instead.
>
> For local providers: the facade will raise an error if this operation
> is not supported by the bound provider.

The docstring says publish is *for* local providers and that the facade *will raise an error* if
unsupported. The facade raises `AttributeError` instead of a `TrackerServiceError` — a documented
contract that is one method short of being honoured.

**There is no publish capability anywhere to route to.** The local backend builds its operations on
`SyncEngine` from the `spec_kitty_tracker` package, whose public surface is:

```
SyncEngine methods: ['checkpoint', 'pull', 'push', 'sync']
```

No `publish`. (`src/specify_cli/sync/daemon.py:554 handle_sync_publish` is unrelated — it is the
sync daemon's HTTP event handler, checked and excluded.)

Corroborating signal: the CLI success path at `tracker.py:1230-1232` prints `payload.get('endpoint')`,
`payload.get('status_code')`, `payload.get('ok')` — an HTTP-response shape that does **not** match
`LocalTrackerService._sync_result` (`local_service.py:248`), which returns `provider`/`status`
fields. Even a naive local implementation would print three `None`s. `sync publish` looks like
surface built for an endpoint that was never wired.

**Design implication (yours to decide, not mine):** the fix choice the issue poses — clean error vs.
implement `sync_publish` — is effectively pre-decided by the absence of any publish capability.
`TrackerServiceError` is a `RuntimeError` subclass (`service.py:23`, MRO confirmed), so raising it
from `LocalTrackerService.sync_publish` is caught by the existing `_run_or_exit` at `tracker.py:349`
and produces a clean message and exit 1 with no other changes. The larger question — whether a
command that refuses on all six providers should exist at all — is above my profile's boundary and
is flagged for you in Part 4.

---

## Part 2 — #3169: the `_extra` consumer audit

### Method, and its calibration

I used `ast`, not regex, for the structural pass. The classifier
(`scratchpad/extra_audit.py`) walks every `.py` file under `src/` and classifies each `_extra`
access as `DEFINITION`, `ATTR-READ`, `ATTR-WRITE`, `KWARG-WRITE`, or — critically — a *key-level*
access: `KEY-READ-SUBSCRIPT`, `KEY-READ-GET`/`POP`/`SETDEFAULT` (recording whether a default was
supplied), or `KEY-GUARD-IN`.

**Calibration is load-bearing here** because the real-codebase answer for key-level reads is
**zero** — and a broken classifier also returns zero. Silence from an uncalibrated tool means
nothing. So I built a positive-control fixture with seven hand-written cases of known expected
classification and ran the classifier against it first.

Control result: **7/7 expected classifications correct, 6/6 key-level reads detected**, including
the guarded-vs-unguarded distinction (`.get("egress", "off")` → `default supplied=True`;
`.get("webhook")` → `default supplied=False`) and correct key-name extraction on subscript,
`.get`, `.pop`, and `in`. The classifier demonstrably fires when key reads exist. Its zero on the
real codebase is therefore informative.

Real run: **1202 files parsed, 0 syntax errors, 7 total `_extra` accesses, 0 key-level reads.**

### The consumer table — complete

Every read of `TrackerProjectConfig._extra` anywhere in `src/`:

| # | `file:line` | Access | Key(s) read | Guards absence? | On `sync publish` path? | On missing key |
|---|---|---|---|---|---|---|
| 1 | `src/specify_cli/tracker/config.py:41` | `DEFINITION` — `_extra: dict[str, Any] = field(default_factory=dict, repr=False)` | n/a | n/a — `default_factory` means never unset | No | n/a |
| 2 | `src/specify_cli/tracker/config.py:55` | `ATTR-READ` — `**self._extra,` inside `to_dict()` | **none — whole-dict splat** | n/a — dict unpacking cannot fail on a missing key | No | n/a |
| 3 | `src/specify_cli/tracker/config.py:122` | `KWARG-WRITE` — `_extra=extra,` in `from_dict()` | n/a (write) | n/a | No | n/a |
| 4 | `src/specify_cli/tracker/saas_service.py:219` | `ATTR-READ` + `KWARG-WRITE` — `_extra=self._config._extra,` | **none — whole-dict passthrough** | n/a | No — SaaS binding-upgrade persist | n/a |
| 5 | `src/specify_cli/tracker/saas_service.py:316` | `ATTR-READ` + `KWARG-WRITE` — `_extra=dict(self._config._extra),` | **none — whole-dict copy** | n/a | No — SaaS bind/confirm persist | n/a |

**Not one consumer reads a key.** All three reads (#2, #4, #5) move the dict as an opaque whole:
one splats it into the outbound YAML mapping, two pass it into a freshly constructed
`TrackerProjectConfig` to survive a rewrite. There is no `_extra["k"]`, no `_extra.get("k")`, no
`"k" in _extra` anywhere in `src/`.

**None of the five sites is on the `tracker sync publish` path.** Sites 4 and 5 are on the SaaS
`bind`/binding-upgrade persistence path; sites 1–3 are the dataclass's own serialization. The
`sync publish` call path (Part 1) touches `load_tracker_config` → `from_dict` (site 3, a write)
and nothing else. **#3168 and #3169 do not overlap in code.**

### What the AST pass cannot see, and what I did about it

An AST search keyed on the name `_extra` cannot see reads that reach the data without naming it.
I checked all four escape routes explicitly:

| Escape route | Method | Result |
|---|---|---|
| `getattr(cfg, "_extra")` dynamic access | grep for `getattr(...config...)` | 4 hits, **all unrelated** (`agent_config`, `mission.config`); none on a `TrackerProjectConfig` |
| `dataclasses.asdict` / `fields()` reflection | grep over `src/specify_cli/tracker/` | **zero hits** |
| `__dict__` / `vars()` | n/a | impossible — the dataclass is `@dataclass(slots=True)` (`config.py:29`) |
| **Indirect via `to_dict()`** — the merged dict contains `_extra`'s contents flattened, so any caller reading an arbitrary key off it is a de-facto `_extra` consumer | grep for `*.to_dict()` callers | **exactly one caller**: `config.py:171`, `payload["tracker"] = config.to_dict()` inside `save_tracker_config` — the write-back path. Not a key reader. |

One near-miss worth recording so nobody re-walks it: `src/specify_cli/tracker/credentials.py:147`
and `:173` read a `"tracker"` block and looked like a second raw consumer. They are **not** —
that is the top-level table of the separate credentials **TOML** file (`_write_toml`,
`self.path = _credentials_path()`), unrelated to `.kittify/config.yaml`. Checked and excluded.

**Where I supplemented with grep, I have said so.** The four rows above are grep-based; grep cannot
prove absence of dynamic access constructed at runtime (e.g. `getattr(cfg, "_ex" + "tra")`). I saw
no evidence of such a construct and consider it a theoretical rather than live risk, but I mark it
`[UNVERIFIED]` rather than claim exhaustiveness.

### Round-trip behaviour, verified live

```
loaded _extra   : {'some_unknown_key': 'preserved-value'}
--- file after round-trip ---
tracker:
  some_unknown_key: preserved-value
  provider: beads
  binding_ref:
  ...
reloaded _extra : {'some_unknown_key': 'preserved-value'}
```

`_extra` does exactly what its docstring implies and nothing more: unknown keys survive a
load/save cycle byte-equivalently. Its **only** observable effect is the content of
`.kittify/config.yaml`. No behaviour anywhere branches on it.

Incidental observation, not a defect and not in scope: `to_dict()` emits every known field
unconditionally, so unset fields are written back as explicit YAML nulls (`binding_ref:`,
`project_slug:`, `provider_context:`). Pre-existing, cosmetic, noted only so it is not mistaken
for promotion damage later.

### Direct answer to #3169

The issue says: *"If the answer is 'nothing reads it', that is a useful and cheap result — say so
and close."*

**That is the answer. Nothing reads it, in the sense the issue cares about.** Zero consumers depend
on any key being present in `_extra`. Promoting any key to a known field — as `#3108` did with
`tracker.egress` — **cannot** silently change consumer behaviour, because there is no consumer
whose behaviour depends on a key. The only effect of promotion is that the key moves from the
splatted `**self._extra` prefix to an explicit named entry in the same output mapping.

Confidence: **high**. The classifier is calibrated against a known-answer control, the four
indirect routes are individually closed, and the total surface is five sites in two files.

---

## Part 3 — The question that shapes the mission

> Is #3168 **one bad binding**, or the **first symptom of `_extra` being an untyped bag**?

### Verdict: **One bad binding. A local defect. Confidence: high.**

The two issues are related only by provenance — both were split out of `#3108` — **not by
mechanism**. The evidence:

1. **`_extra` is not implicated in #3168 at all.** The crash is a missing method on a service
   class. The `sync publish` call path does not read `_extra`. Not one of the five `_extra` sites
   is on that path. There is no code route from `_extra`'s contents to the `AttributeError`.
2. **`_extra` is not an untyped bag that consumers read hopefully.** It is a write-only round-trip
   buffer with zero key readers, verified by a calibrated AST pass over 1202 files plus four
   closed indirect routes. "Read hopefully" requires a reader. There is none.
3. **The delegation matrix is 15/16 complete.** If this were a systemic contract failure between
   facade and backends, more cells would be empty. Exactly one is.
4. **The defect has a single, local, well-understood cause**: one method was never written on one
   of two backends, and the one test covering that path used a bare `MagicMock()` that
   auto-created it.

Nothing here is structural in the `_extra` sense. **#3169's answer is "nothing reads it — close
it,"** and that answer is cheap, now established, and does not need a mission.

**The caveat that does deserve your attention** is a different structural point than the one you
posed. The *narrow* defect is one method. But the surrounding finding — that `sync publish`
refuses on all six providers, that no publish capability exists in `SyncEngine`, and that the
CLI's success path prints keys no backend produces — suggests `tracker sync publish` may be
**unwired surface** rather than a working command with one broken binding. That is a
product/architecture question about whether the command should exist, and it is outside my
profile's boundary to decide. I flag it; you decide.

Confidence on the narrow verdict (one bad binding, not an `_extra` structural defect): **high**.
Confidence that `sync publish` is unwired surface rather than an incomplete feature awaiting a
publish endpoint: **moderate** — I established that no publish capability exists *today* in the
installed `spec_kitty_tracker` and that the CLI expects an HTTP-shaped payload, but I did not
establish the original design intent or check whether a publish endpoint is planned elsewhere.
Marked `[UNVERIFIED]`: whether a snapshot-publish endpoint exists or is planned in the hosted
control plane.

---

## Part 4 — Is this mission worth doing?

### Honest assessment: **the mission as framed is not worth its overhead. The decision it surfaces is.**

Taking the two issues at face value:

- **#3169 is already answered by this document.** The deliverable it asked for — an inventory of
  every `_extra` read — is the five-row table in Part 2, and the answer is the cheap one the issue
  itself pre-authorized: nothing reads it. **This issue can be closed with a link to this
  document. It needs no mission, no spec, and no code change.**
- **#3168's narrow fix is small.** Add `sync_publish` to `LocalTrackerService` raising
  `TrackerServiceError` (already a `RuntimeError`, already caught by `_run_or_exit` at
  `tracker.py:349`, already producing a clean message and exit 1), and tighten the mock at
  `test_tracker.py:1380` from `MagicMock()` to a `spec=`-bound mock so the seam is no longer
  blind. That is roughly a five-line production change plus test work.

So: three well-guarded consumers and a short fix — by your own stated criterion, **this does not
justify a full mission**, and I would rather say that now than at review.

**What I would put a mission around instead, if you want one:** not the fix, but the decision. The
non-trivial question this investigation surfaced is *"should `spec-kitty tracker sync publish`
exist?"* — a command that today refuses on four providers, crashes on two, publishes on none, has
no capability behind it in `SyncEngine`, and prints a payload shape no backend returns. The options
are roughly: (a) make it a clean refusal on local too and leave the surface in place; (b) remove
the command; (c) wire it to a real publish endpoint. Those have materially different scopes and
(b)/(c) are user-visible. That is a decision for you and an architect, not an implementer.

### What would make a mission here unsafe

1. **Scope creep from #3168 into removing the command.** Option (b) is a user-facing CLI removal
   with CHARTER implications (`CHANGELOG.md`, breaking-change documentation per DIR-009). If a
   mission is opened for the two-line fix and drifts into removal, the diff blurs exactly the way
   `#3108` avoided. Whichever option you pick, pick it *before* the mission opens.
2. **Bundling #3169 into it.** #3169 is answered and closeable. Carrying it into a mission gives
   the mission a work package with no work in it.
3. **Fixing the test the wrong way.** The instinct will be `MagicMock(spec=TrackerService)` — but
   the *facade* has `sync_publish`, so that spec still would not have caught this. The pin has to
   be against the **backend** contract (the delegation matrix in Part 1), not the facade. A test
   that spec'd the facade would look like a fix and remain blind.
4. **Rebaselining on a moved tree.** All line numbers here are `709a59534`. `tracker.py` is
   1200+ lines and actively edited; re-derive before editing.

### Safety notes for whoever implements

- Test baselines on this tree are **green**: `tests/sync/tracker` → **472 passed, 0 errors**;
  `tests/agent/cli/commands/test_tracker.py` → **51 passed, 0 errors**. No pre-existing failures,
  so no DIR-013 reporting obligation was triggered.
- Per the standing constraint, `tests/sync` and `tests/cli` were run **sequentially, never
  concurrently**. Keep that discipline.
- The reproduction needs no network, no auth, and no beads/fp binary — just a `.kittify/config.yaml`
  and the rollout env var. It is cheap to turn into a regression test, and that regression test
  should assert the **clean error and exit 1**, not merely "no AttributeError".

---

## Appendix — verification commands

| Claim | How verified |
|---|---|
| Crash reproduces on `beads` and `fp` | Real `spec-kitty tracker sync publish` invocation, exit 1, traceback captured |
| Attribute missing, not None/wrong-type | `dir()`, `__mro__`, `hasattr(L, '__getattr__')` on `LocalTrackerService` |
| Delegation matrix | AST extraction of `self._resolve_backend().X()` targets + `hasattr` on both backends |
| SaaS refuses cleanly | Live `TrackerService.sync_publish()` against a `github` binding |
| No publish capability | `dir(SyncEngine)` → `['checkpoint', 'pull', 'push', 'sync']` |
| `_extra` consumer set | Calibrated `ast` pass, 1202 files, 0 syntax errors |
| Classifier is trustworthy | Positive-control fixture, 7/7 classifications, 6/6 key-reads detected |
| Indirect routes closed | Targeted greps for `getattr`, `asdict`/`fields`, `to_dict()` callers; `slots=True` rules out `__dict__` |
| Round-trip preservation | Live load → save → reload of a config carrying an unknown key |
| Test baseline | `pytest tests/sync/tracker` and `pytest tests/agent/cli/commands/test_tracker.py`, run separately |
