# Bundle B — orchestrator working notes (NOT a deliverable; scratch)

## Environment facts, measured 2026-07-31 in this clone

**Clone:** `/home/jeroennouws/dev/sk-missions/3110`
**Pinned to:** `upstream/main` = `bb2020fea924d6e5b157974f27a7cab1a77ad259`
(`bb2020fea` "landing fold: render the unadjusted leak path in the empty-charter governance test (anti-vacuity)")

### F-ENV-1 — the editable-install leak is USER-SITE, not venv-scoped (worse than dossier records)

`tracer-tooling-friction.md` records the editable `.pth` as living in
`.venv/lib/python3.11/site-packages/`. **On this machine it is in USER site-packages:**

```
/home/jeroennouws/.local/lib/python3.14/site-packages/_editable_impl_spec_kitty_cli.pth
  -> /home/jeroennouws/dev/spec-kitty/src
```

Measured: a bare `python3 -c "import specify_cli"` from inside THIS clone resolves to
`/home/jeroennouws/dev/spec-kitty/src/specify_cli` — a *different checkout*, which is
concurrently being edited by the Bundle A mission (`verification-trust-3115`).

So the hazard is no longer "worktree isolation is defeated". It is: **any unguarded
pytest/python run in this clone measures Bundle A's working tree.** Two live missions,
one importable package.

Mitigation, measured working:
`PYTHONPATH=/home/jeroennouws/dev/sk-missions/3110/src python3 ...` resolves correctly
to this clone. PYTHONPATH precedes `.pth` site entries on `sys.path`.

#### CORRECTION — measured, not assumed: `pytest` is NOT affected

I nearly wrote a false warning here. Applying the friction rule *"control your
diagnostic — run any probe against a case whose answer you already know"*, I ran an
actual probe test under pytest rather than trusting the `python3 -c` result:

```
tests/test_zz_probe_import_origin.py  ->  1 passed in 69.00s
resolved: /home/jeroennouws/dev/sk-missions/3110/src/specify_cli   # THIS clone
```

`pytest.ini` sets `pythonpath = src`, which pytest inserts at the FRONT of `sys.path`,
ahead of the user-site `.pth`. So **any `pytest` run whose rootdir is this clone imports
this clone.** The probe file was deleted after measuring.

**Revised scope of the hazard — it is narrower than the dossier's framing, but real:**
- `pytest` from this clone's root — **SAFE** (measured).
- bare `python3 -c "import specify_cli"` — **LEAKS** to the Bundle A checkout (measured).
- Therefore: mutation plugins, one-off import probes, `python -m` harnesses, and any
  pytest invocation whose rootdir is NOT this clone remain exposed.

**Rule for every subagent:** pytest from the clone root is fine; for anything else set
`PYTHONPATH=/home/jeroennouws/dev/sk-missions/3110/src` explicitly. Never trust a bare
`python3` import probe in this environment.

**Not established:** why the dossier recorded the leak defeating worktree isolation
despite `pythonpath = src`. Possibly a differing rootdir, `uv run` semantics, or the ini
option postdating that measurement. I did not chase it. Treat the dossier's rule as
still binding for non-pytest measurement.

#### Incidental: collection cost

That single trivial test took **69 seconds** wall-clock, essentially all import/collection.
Any plan that budgets "run the suite" must account for a large fixed cost per invocation.

### F-ENV-2 — only Python 3.14 is installed locally; CI runs 3.11/3.12

`/usr/bin/python3.14` is the only interpreter. `uv` is available, so a dedicated
3.11 venv is constructible (`uv venv --python 3.11`).

This makes friction rot-mode 4 ("a mutation can be inert on your interpreter and live on
CI's") maximally live: **every local green here is a 3.14 green.** The dossier's own
example was exactly this — a branch unreachable on 3.14, load-bearing on 3.11.

### F-ENV-3 — Bundle A has NOT landed

Measured via `gh issue view` against `Priivacy-ai/spec-kitty` on 2026-07-31:
- `#3115` (shard-parallel test isolation) — **OPEN**, `closedAt: null`
- `#3113` (egress guard positional-call blind spot) — **OPEN**, `closedAt: null`
- `#3110` (this bundle's consolidation issue) — OPEN

Consequences carried into the spec and the handoff:
- CI reds on this mission's test surface are suspect; per-case isolation required.
- The egress guard has a **known evasion for all-positional transport calls**. If the
  consolidation moves a sink, the guard may not see it.

### F-ENV-4 — the `pytest.ini` timeout gap, made concretely checkable

Measured at `bb2020fea`:

```
pytest.ini:11:  addopts = --tb=short          <-- NO --timeout
```

The only `--timeout=30` in the repo is `pyproject.toml:386`, inside the **mutmut**
config block — it does not apply to normal or CI pytest runs. `pytest-timeout` IS a
declared dev dependency (`pyproject.toml:105`) and a `timeout` marker is registered
(`pytest.ini:26`), so the plugin is present and the gap is purely the missing `addopts`
entry.

**Handoff check for "has Bundle A landed":** `grep addopts pytest.ini` — if the line
still reads exactly `addopts = --tb=short`, the timeout gap is still open.

This is why the friction doc's *"a hang is not a measurement, and two suites hang
instead of failing"* is live for this mission: with no global timeout, a hung suite
consumes the run rather than failing it.

## Scout B findings — `#3111`, the `decision_id` → owning-project question

### F-B1 — THE ANSWER: no such mapping exists, locally OR remotely

Ownership of a decision is encoded **positionally** — by which directory the file sits
in — and never as data.

- Ledger lives at `<repo_root>/kitty-specs/<mission-slug>/decisions/index.json`
  (`decisions/store.py:40-47`).
- `IndexEntry` (`decisions/models.py:68-96`) carries `mission_id` + `mission_slug` and
  **nothing else identifying**. No `project_uuid`, no `project_root`, no `repo_slug`.
  `model_config = ConfigDict(frozen=True, extra="forbid")` (`models.py:70`) — an
  out-of-schema `project_uuid` cannot even be present in a valid file.
- `meta.json` one hop away does not carry `project_uuid` either (union of keys over 100+
  missions in this repo checked).
- Creation (`decisions/service.py:265-279`) takes `repo_root` as a parameter, uses it to
  locate the dir, then **discards** it.
- **Not remote either.** The SaaS client's complete surface is five endpoints
  (`saas_client/client.py:215,249,284,309,326`); none returns a decision's project or
  team-of-record, and there is no "get decision" endpoint.

So this is "does not exist", not "exists only remotely". **This is a finding, not a
blocker** — it is the central design constraint for `#3111`.

### F-B2 — ESCALATION: the recorded precondition is already satisfied today

The dossier records: *"if that endpoint ever accepts a slug, the entry stops being benign."*

**Measured: `decision_id` has NO format validation on this path.** It is declared
`typer.Argument(..., help="ULID of the DecisionPoint to widen")` at `decision.py:525`,
and that help string is the *only* thing asserting ULID-ness. There is no regex, no
check in `cmd_widen` (`decision.py:523-572` — only `--invited` is validated), none in
`post_widen` (`client.py:249-282`), none in `_post`/`_team_path` (`client.py:181-209`).
The string is interpolated **raw into the URL** at `client.py:274`.

ULID regexes exist elsewhere (`decisions/verify.py:40`, `invocation/record.py:30`,
`context/mission_resolver.py:55`) but **none guards this argument**. The "it's a ULID"
belief comes from minting at `decisions/service.py:80-82`, not from validation.

**Consequence, and it is the mission's sharpest point:** the precondition does not wait
on a server change. The client already transmits whatever string the operator types, in
the **request line**, to a host authorised by *the cwd's* project. A slug typed there
egresses even if the server answers 404. **Server acceptance controls the effect;
the client controls the disclosure.** `#3111` is therefore bounded by operator typing
discipline, not by a wire contract.

**Verified by me directly, not taken from the scout** (`decision.py:523-572` read in
full): the only validation in `cmd_widen` is on `--invited` (non-empty, ints).
`decision_id` is passed through untouched; `mission_slug` is referenced only inside the
`dry_run` branch.

**The exact leak shape, stated precisely** (from `client.py:148-159,181-199`): the gate
`_refuse_unless_project_consents()` runs **before the URL is used**, so a non-consenting
cwd project transmits nothing. The failure is therefore *not* "unconsented egress" — it
is **consent laundering**: standing in a consenting project A and widening a decision
owned by project B sends B's identifier to **A's team, under A's token**, and every
gate answers "yes" truthfully about the wrong project.

**A further sharpening from the code's own docstring** (`client.py:148-155`): it states
that four of the five endpoints put `mission_id` in the request path and that
`mission_id` is *documented "ULID or slug", and a slug is a client engagement name*.
So the endpoint family already accepts engagement names by contract. Widen's ULID-ness
is the only thing bounding this site — and per F-B2 that bound is unenforced.

### F-B3 — the fix affordance already exists and is inert

`--mission-slug` is **already accepted and already ignored** on the live path:
declared at `decision.py:527`, referenced only inside the *dry-run* payload
(`decision.py:550`). With a slug + root, ownership is locally verifiable using two
existing calls — `resolve_feature_dir_for_mission(repo_root, mission_slug)`
(`missions/_read_path_resolver`, used at `widen/state.py:63`) then
`store.load_index(mission_dir)` (`decisions/store.py:61`) and a membership test of the
same shape already written at `store.py:117`.

### F-B4 — a THIRD divergence route, not previously recorded

`locate_project_root` (`core/paths.py:182-212`) honours **`SPECIFY_REPO_ROOT` first**,
before walking up from cwd. So root/owner divergence has three routes, not one:
operator's cwd, `SPECIFY_REPO_ROOT`, and the `or Path.cwd()` fallback.

The auth token and `team_slug` follow the same wrong root (`client.py:136-140`,
`_resolve_team_slug` `client.py:202-206`).

### F-B5 — the command name in the mission brief is wrong

There is no top-level `decision` typer. The real invocation is
**`spec-kitty agent decision widen`** (`cli/commands/agent/__init__.py:8,30` →
`cli/commands/decision.py:41`), and `cmd_widen` is `hidden` (`decision.py:523`).
The brief says `spec-kitty decision widen`. Cosmetic for design, but the successor
will not find the command otherwise.

### F-B6 — scope of `#3111` is exactly one command

`SaasClient` appears in `cli/commands/decision.py` only at lines 531 and 558. `open`,
`resolve`, `defer`, `cancel`, `verify` are purely local file I/O. The other three
`from_env` sites (`charter/interview.py:216`, `plan/plan_interview.py:150`,
`plan/specify_interview.py:150`) are the dossier's "root and owner agree by derivation"
cases — decision ids read back from `WidenPendingStore(repo_root, mission_slug)`.

### F-B7 — the consent chain would take a uuid; the gate would not

`resolve_project_consent(project_uuid, *, repo_root=None, checkout_roots=None)`
(`sync/consent.py:608`) is **uuid-primary**; roots are optional and only unlock
precedence level 1. But the seam above is path-typed end to end:
`resolve_egress_consent` is `Callable[[Path], bool]` (`invocation/adapters.py:82,148`),
and `project_egress_refusal(project_root: Path | None)`
(`saas_client/egress_consent.py:88`). And `saas_client/egress_consent.py:19-31`
explicitly forbids re-deriving the chain locally (C-003).

**So a uuid-keyed fix means changing the seam, not bypassing it.** This is directly
entangled with `#3110` — which is exactly why the operator bundled them.

## Scout A findings — `#3110` consolidation surface, guards, boundary, `#3109` seam

### F-A1 — the duplication is smaller than the issue implies, and nothing pins the divergence

Six diff hunks between the two modules. **Exactly one is a runtime string; five are
comments/docstrings.** The runtime one is the `DENIED` branch:
`saas_client:127` "mission and **decision** identifiers" vs `tracker:190` "mission and
**engagement** identifiers".

**No test pins either side** — grep for `decision identifiers` / `engagement identifiers`
across `tests/` returns zero hits. The only four text assertions in the repo all target
`"could not be determined"` (`test_client_consent_gate_3030.py:267,376`;
`test_saas_client_consent_gate_3030.py:352,418`), which is already byte-identical.

**So consolidation breaks no existing gate on text.** The risk is semantic accuracy for
the operator, not mechanical. Which word survives is a real decision, not a coin flip:
`saas_client` genuinely carries decision ids, `tracker` genuinely carries engagement
names. A single merged string must be true of both callers.

### F-A2 — `UNDETERMINED_PROJECT_REFUSAL` has zero external consumers

Referenced only inside each defining module (`saas:85`→`:101`, `tracker:140`→`:162`).
Both deliberately omit it from `__all__`. **It must stay out of `__all__` in any shared
module** or `tests/architectural/test_no_dead_symbols.py` reds immediately — that gate
requires every `__all__` name to have a non-test `src/` importer (`:22-28`), and tests
are explicitly not counted as callers (`:26-28`).

### F-A3 — THE TRAP, made concrete: four ways merging the guards halves coverage

Both guards are **fully independent today** — verified by their complete import lists
(`saas:16-26`, `tracker:28-37`), no shared helper, no conftest scanner.

- saas guard: `test_every_production_construction_site_attributes_its_project`
  at `tests/specify_cli/saas_client/test_client_consent_gate_3030.py:303`
- tracker guard: same function name at
  `tests/sync/tracker/test_saas_client_consent_gate_3030.py:355`

**Mechanism 1 — the load-bearing one.** The non-vacuity assertion is
`assert scanned` on a **single global int** (`saas:340`, `tracker:387`). It is per-package
today *because there is one guard per package*, not because the assertion says so. Merge
into one parametrized scanner accumulating into one `scanned`, and dropping/renaming one
of the two class names leaves `scanned > 0` from the other — **green while half the
construction sites go unscanned.** Any merged form needs a **per-class floor**, e.g.
`assert scanned["SaasClient"] and scanned["SaaSTrackerClient"]`.

**Mechanism 2 — the attribution rules are not interchangeable, and the silent direction
is widening.** saas accepts a bare positional *or* `repo_root=` for `from_env`; tracker
accepts **only** `project_root=`. Narrowing is loud (flags all four `from_env` sites).
Widening to accept any of the three silently accepts a future
`SaaSTrackerClient(repo_root=…)` that today's tracker guard rejects. Nothing would tell you.

**Mechanism 3 — the func-match predicates differ in strictness.** tracker uses
`getattr(func, "attr", None)` (accepts any `mod.SaaSTrackerClient(...)`); saas requires
the receiver be literal `Name("SaasClient")`. Unifying either way changes `scanned`
without zeroing it.

**Mechanism 4 — CI routing, and this one is invisible from the code.**
`src/specify_cli/tracker/**` is in the `agent_surface` dorny filter group
(`.github/workflows/ci-quality.yml:401`); `src/specify_cli/saas_client/**` is in
`platform` (`:427`). The tracker guard lives under `tests/sync/` (matched at `:204`, run
by the job at `:1125`); the saas guard is under `tests/specify_cli/saas_client/` with no
dedicated glob. **Put a merged guard in only one tree and a PR confined to the other
package routes to a job set that never runs it.**

*Safe direction, from the same finding:* a brand-new `src/specify_cli/<x>/` matches no
named group → `unmatched` → `run_all`, which is a loud alarm by design (`:438-446`).

### F-A4 — CORE placement is FORBIDDEN, and the reason is mechanical

`project_egress_refusal` contains a lazy `import specify_cli.sync` (`saas:108`,
`tracker:171`). `test_integration_boundary.py::_imports_in_tree` (`:109-124`) walks the
**full** AST and so catches lazy in-function imports (stated at `:22-30`). `ALLOWLIST` is
`frozenset()` and `test_allowlist_count_ratchet` (`:262`) asserts `len(ALLOWLIST) == 0`
(`:270-274`), described as "permanently closed".

So `invocation/`, `core/`, `status/`, `readiness/` are all **out**. Legal homes:
`sync/`, `tracker/`, `saas_client/`, `delivery/`, or a new neutral
`src/specify_cli/egress/`. A new **top-level** `src/<pkg>/` needs a second edit
(`test_layer_rules.py:193` `test_no_unregistered_src_packages`).

**Layering forbids only CORE placement.** The registry indirection through
`invocation.adapters.resolve_egress_consent` stays a C-003 choice, confirmed verbatim in
source at `tracker/egress_consent.py:39-45`.

### F-A5 — a gate that WILL red on a careless consolidation

`tests/architectural/test_egress_consent_boundary.py::test_seam_allowances_name_a_live_seam`
(`:807-830`) asserts `allowance.seam_symbol in seam_path.read_text(...)` (`:823`). The
tracker allowance (`:510-521`) names `seam_symbol="project_egress_refusal"` with
`seam_module="specify_cli/tracker/saas_client.py"`.

**Therefore: the function name `project_egress_refusal` must remain textually present in
`src/specify_cli/tracker/saas_client.py`.** Renaming the function, or removing the call
from that file, reds this gate. The saas allowance (`:522-533`) names
`_refuse_unless_project_consents` in `client.py` and is unaffected.

### F-A6 — "import-linter" is not established

The mission framing mentions import-linter. There is **no** `[tool.importlinter]` in
`pyproject.toml`, no `.importlinter`, no `lint-imports` invocation. The layering gates
are the pytest files. TID251 bans only `hashlib.sha256` and `click.exceptions.*`
(`pyproject.toml:249-260`) — **not triggered** by this work.

### F-A7 — the `#3109` seam: the READ side is live, only the WRITE side is dead

This is the fact the decision turns on, and it inverts the obvious reading.

- `register_saas_client_factory` (`invocation/adapters.py:130-145`) has **three `src/`
  references and all are definitional**: the def, the re-export at
  `invocation/__init__.py:21`, and the `__all__` entry at `:111`. **No production caller.**
- **But `get_saas_client` (`adapters.py:188-215`) has a real production reader:**
  `propagator.py:37` imports it, `:58-83` wraps it, and `:137` calls it live, with
  `:138-139` early-returning on `None`.
- The propagator's gate ordering is documented at `propagator.py:96-100` and is the
  safety property: consent gate (`:127-134`) → client lookup (`:137`) → projection
  (`:142`) → send. The hazard is named at `:79-81` — this path would carry
  `request_text`, **the verbatim agent prompt**.

So the slot is **not orphaned**. It is a live, gated, currently-empty seam.

`test_sync_registers_no_saas_client_factory` (`tests/invocation/test_adapters.py:302-339`)
pins the **absence of registration** — and critically **never names
`register_saas_client_factory`**. The symbol could be deleted today and that test would
still pass unchanged.

The docstring on `register_saas_client_factory` is **stale**: "Called once at sync package
startup" has been false since FR-032.

`_ws_client`: operator's claim **confirmed** — four hits in `src/`, all inside `#`
comments (`sync/local_commit.py:284,290`; `sync/__init__.py:380,390`). Zero live
`getattr`, zero assignment, zero `setattr`. Not to be confused with the live,
differently-owned `ws_client` (no underscore) on `sync/runtime.py:274`.

## ORCHESTRATOR DECISION D-1 — `#3109` seam: **KEEP `register_saas_client_factory`**, and pin it

The operator asked me to make the case either way and act, escalating only if the
evidence is genuinely balanced. **It is not balanced.** F-A7 breaks the tie.

### Why the obvious framing is wrong

The issue frames this as "a name kept alive for a future that may not arrive". That
framing assumes the seam is *orphaned*. It is not: the **read** side
(`get_saas_client`) has a live production consumer at `propagator.py:137`, inside a
documented consent-gate ordering (`propagator.py:96-100`). Only the **write** side is dead.

### The choice is three-way, and the middle option is dominated

- **(a) Keep the whole seam** — status quo.
- **(b) Delete only `register_saas_client_factory`** — leaves a getter that can *never*
  return non-`None` and a consumer branch at `propagator.py:138+` that is dead by
  construction. This is **strictly more confusing** than either neighbour: it is the
  incoherent state, not the tidy one. Dominated.
- **(c) Delete the entire seam** — `register`, `get`, and the propagator's egress branch.

So the real question is (a) vs (c).

### (a) over (c), on three grounds

1. **Scope.** (c) edits `propagator.py`'s gated egress path — precisely the code `#3030`
   hardened, and squarely outside Bundle B. Bundle B is "one wrapper, one shape"; it is
   not a mandate to remove an egress seam.
2. **The seam's value is as a documented refusal point.** `propagator.py:79-81` records
   that wiring a transport here would carry `request_text` — the verbatim agent prompt —
   and that doing so "was considered during #3030 and explicitly rejected". Deleting the
   seam deletes the *place where that refusal is written down*. A future author wanting a
   transport then adds one somewhere else, very likely **not** behind the consent gate the
   seam sits behind. Keeping the empty slot keeps the gate in front of it.
3. **Absence is already pinned, and pinning absence was the right call.** The dossier's
   own reasoning applies: when the correct state is *absence*, you must pin the absence or
   the next author reads the empty seam as an oversight.
   `test_sync_registers_no_saas_client_factory` does exactly that.

### But keeping it as-is is not good enough — two defects to fix

Keeping the seam untouched would leave the "oversight" reading intact. Two cheap
corrections remove it:

1. **The docstring is stale and actively misleading.** `adapters.py:130-145` says "Called
   once at sync package startup" — false since FR-032. It must state that nothing
   registers a factory today, and why (the `request_text` hazard).
2. **The pin does not cover the symbol.** `test_sync_registers_no_saas_client_factory`
   never names `register_saas_client_factory`; the seam could be deleted tomorrow and the
   test would stay green. So the *absence of a registration* is pinned while the
   *presence of the seam* is not. Add an assertion that the seam exists and is exported.

That converts "a name kept alive" into "a name **pinned** alive, with its reason written
where the next author will hit it".

### Preconditions that would falsify D-1

- **If `propagator.py`'s egress branch is ever removed** (making `get_saas_client` have no
  production reader), the read side dies too and option (c) becomes correct — delete the
  whole seam.
- **If a real transport is registered**, `test_sync_registers_no_saas_client_factory`
  reds by design. That is the moment to prove the propagator's consent gate holds against
  the new transport *before* landing it, exactly as the test's own message demands.
- **If the repo adopts a policy that empty seams must not exist regardless of read-side
  liveness**, D-1's ground 2 is overridden by policy and (c) follows.

## F-ENV-5 — the `#3113` blind spot, located mechanically (checkable handoff signal)

The evasion is in `_transmits_a_body`, `tests/architectural/test_egress_consent_boundary.py:295-306`:

```python
def _transmits_a_body(node: ast.Call) -> bool:
    tail = _attr_tail(node.func)
    if tail in _VALUE_CONSTRUCTORS:
        return False
    kwargs = {kw.arg for kw in node.keywords if kw.arg is not None}
    return "headers" in kwargs and bool(kwargs & _REQUEST_BODY_KWARGS)
```

**It reads `node.keywords` only — never `node.args`.** So a fully positional
`poster(url, data, headers)` yields `kwargs == set()` → `False` → the call is not
classified as a sink at all. `_classify` (`:309-331`) falls through to
`_transmits_a_body` for exactly the two cases that matter — a bare `ast.Name` callee
(`:316`) and an unrecognised attribute callee (`:331`) — i.e. **a transport passed in as
a parameter or reached through an alias**, which is the shape this rule exists to catch.

The limitation is also documented in prose at `:126-135` ("``client.put(some_var)`` with
no keywords is consequently **missed**").

### The concrete check for "has `#3113` landed"

```bash
sed -n '/def _transmits_a_body/,/^def /p' tests/architectural/test_egress_consent_boundary.py
```

- If the body still derives `kwargs` solely from `node.keywords` and returns
  `"headers" in kwargs and bool(kwargs & _REQUEST_BODY_KWARGS)` → **#3113 is NOT fixed.**
- Fixed looks like: positional arguments considered (or the limitation narrowed and the
  `:126-135` note rewritten to say what is now caught).

**Why this matters to Bundle B specifically:** if the consolidation *moves a sink* — or
introduces a call to the shared wrapper through an alias or an injected transport — the
guard may not see it. Any green from this gate on a moved sink must be reported as
conditional on this hole being closed.

## F-ENV-6 — Bundle B's blast radius spans FOUR dorny CI groups (verified verbatim)

From `.github/workflows/ci-quality.yml:378-436`, the src→group map for the dirs this
mission touches:

| Directory | dorny group |
|---|---|
| `src/specify_cli/invocation/**` | `lifecycle` (`:394`) |
| `src/specify_cli/tracker/**` | `agent_surface` (`:401`) |
| `src/specify_cli/saas_client/**` | `platform` (`:427`) |
| `src/specify_cli/decisions/**`, `widen/**` | `closeout` (`:408,411`) |

This is Mechanism 4 (F-A3) confirmed at source, and it is **worse than a two-way split**:
a change confined to any one of these routes to a different job set. Consequences:

- A merged guard placed in one test tree can be skipped entirely by a PR confined to
  another package. **Both guards must stay independently routable, not merely
  independently written.**
- Registering a new named group is explicitly a **5-edit atomic registration**
  (`:384-387`): member glob + `changes.outputs` row + unmatched-loop entry + test-job
  if-gate + `JOB_GROUPS` row. Not a one-liner — the plan must budget for it if it goes
  that way.
- **The safe default remains a new neutral `src/specify_cli/<x>/`**: it matches no named
  group, so `unmatched → run_all` fires (`:438-446`) — loud, and it runs everything.
  Costly per PR but it cannot silently under-run.

## CORRECTIONS to my own findings, raised by the spec author and adjudicated

The spec author challenged four of my findings. **Three stand as corrections to the
record; one I accept as an honest caveat.** Recorded here so the successor inherits the
corrected version, not the original.

### C-1 — F-A1 was right but narrower than it read (VERIFIED, my error)

I wrote that consolidation "breaks no existing gate on text". True, but I missed *why*
that is a weakness rather than a comfort.

Measured just now:

```
saas_client/egress_consent.py:86   "…could not be determined, so its consent to "   <- UNDETERMINED
saas_client/egress_consent.py:138  f"consent for the project at {…} could not be determined "  <- UNANSWERABLE
tracker/egress_consent.py:141      (same as :86)
tracker/egress_consent.py:201      (same as :138)
```

**The pinned substring `could not be determined` occurs in TWO branches, not one.** So
the four existing assertions cannot distinguish `UNDETERMINED_PROJECT_REFUSAL` from
`UNANSWERABLE`. A consolidation that merged those two branches into one message would
**keep the substring, stay green, and collapse a distinction the source explicitly says
must not collapse** — `tracker/egress_consent.py:136-139` records that "no checkout was
offered at all" is a *caller* fault whose operator fix differs from the resolver's own
vocabulary.

Handled in the spec as NFR-004 (refusal branches must remain distinguishable) rather than
by trusting the text gate. **The text gate is not protection here.**

### C-2 — F-B3 was optimistic; `--mission-slug` VERIFIES ownership, it does not ESTABLISH it

I called `--mission-slug` "the fix affordance". That overstates it. The operator supplies
the slug, so `resolve_feature_dir_for_mission` + `load_index` **verifies a claim** the
operator makes; it does not **discover an owner**. An operator who can mistype a
`decision_id` can equally mistype or simply omit the slug.

**Consequence, and it is the most likely place this mission stalls in plan:** if
`--mission-slug` stays optional, FR-001 has no input at all on the omission path, and the
design must choose between refusing outright (usability cost, stated deliberately) or
searching candidate checkouts (a *search*, not a mapping — and silent on any project never
toggled for sync, per F-B1). Recorded as spec open question Q4.

### C-3 — D-1's ground 2 is the weakest; the decision stands on grounds 1 and 3

Ground 2 was "keeping the empty slot keeps the consent gate in front of it". The
challenge is fair: **nothing makes a future author find the seam.** It has no production
caller, so it appears in no call graph they would traverse. FR-018's docstring fix is
doing all of ground 2's work, and only for someone already reading `adapters.py`.

**D-1 (KEEP) is unchanged** — grounds 1 (scope: deleting the whole seam edits
`propagator.py`'s gated egress path, outside Bundle B) and 3 (absence is already pinned,
and pinning absence was correct) are solid. But **ground 2 must not be quoted later as
load-bearing.** Downgraded to a secondary consideration.

### C-4 — NFR-001's baseline counts are inherited, not re-measured (open caveat)

The "3 tracker / 4 SaaS-client construction sites" figures were transcribed from the
parent mission's inventory ("3/3 tracker, 4/4 widen"), where the SaaS figure is described
as *widen-path* sites while `egress_consent.py`'s docstring enumerates four `from_env`
sites. Probably the same four — **not verified.**

**The plan must re-run the AST scan and quote the counts, not trust the transcription.**
This is exactly the parent mission's "print the input count alongside any all-checks-passed"
rule applied to a baseline.

### One thing the spec author added that I had missed

`test_no_unregistered_src_packages` (`test_layer_rules.py:203-209`) scans **top-level
`src/` dirs only** (`_SRC.iterdir()`). So a new *subpackage* of `specify_cli` does not
trip it — which means C-005's laundering protection is **genuinely absent**, not supplied
by some other gate. That is why C-005 mandates an explicit classification edit rather
than treating "no gate objects" as safety.

## Divergence already found by direct read (before scouts reported)

`saas_client/egress_consent.py` vs `tracker/egress_consent.py`, `DENIED` branch:
- saas_client: "mission and **decision** identifiers must not be transmitted"
- tracker:     "mission and **engagement** identifiers must not be transmitted"

They are near-identical, **not** identical. A consolidation that assumes verbatim
duplication will change one of these strings. Whether a test pins them is the question.
