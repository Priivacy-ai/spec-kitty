# The measurement-substrate incident — two interpreters, and an inverted diagnosis

Recorded during the implement–review loop, after WP01/WP09/WP10 were approved. This is a
"our own process did the thing we are trying to stop" record, which is what `notes/` is for.
The binding rule lives in [`standing-rules.md`](../standing-rules.md); this is the incident
behind it.

## What is actually true

Two interpreters are reachable in this checkout and they are not interchangeable. Measured by
enumerating each one's `pytest11` entry points — the registry that produces the `plugins:` header:

| Interpreter | Python | pytest | `pytest11` registry |
|---|---|---|---|
| `.venv/bin/python` | **3.11** | **9.0.3** | anyio, asyncio, base_url, playwright, pytest_cov, respx, **timeout**, **xdist**, xdist.looponfail |
| bare `python3` → `/usr/bin/python3`, user-site | **3.14** | 9.1.1 | anyio, respx |

**The Python version is part of the substrate too, and an earlier draft of this table omitted
it** — an odd gap in a record whose thesis is *the substrate differs and nobody looked*. Two
minor versions apart, and it matters directly: an AST measurement parses with the running
interpreter's grammar. So FR-015's counts were re-run under **both** rather than assumed to
transfer — identical on each: **1198 files scanned, 0 parse failures, the same 5 false-positive
sites** (`locate_work_package` and `resolve_workspace_for_wp` in `resolution.py:617,628`,
`behind_commits_touch_only_planning_artifacts` and `resolve_workspace_for_wp` in
`tasks_parsing_validation.py:628,831`, `build_queue_scope` in `sync/preflight.py:752`). That
measurement is interpreter-independent; the *execution* measurements are not.

`import pytest_timeout` under `python3` raises `ModuleNotFoundError`. **`pytest-timeout` and `xdist`
exist only in the venv**, so a timeout-backstop or shard claim measured anywhere else is not weaker
evidence — it is **no evidence**. WP11's acceptance turns on a red being *on the counter, naming the
count* and specifically **not** `Failed: Timeout`; that distinction is observable only where
`pytest-timeout` is installed. WP12's entire requirement is unmeasurable outside the venv.

## How it surfaced

A full `tests/architectural` run reported **19 failed / 26 errors**, well beyond this mission's
briefed pre-existing set. WP10's reviewer attributed them to subprocesses invoking a hardcoded
`/usr/bin/python`, and controlled that attribution by putting the venv first on `PATH` and confirming
the failures persisted identically.

**That control could not have discriminated.** The subprocesses launch `sys.executable`, never a
literal path — every `/usr/bin/python` string in `tests/` is a mock fixture fed to install-method
detection. And a `PATH` change cannot alter an already-running interpreter's `sys.executable`. So
"persisted identically" was equally consistent with the competing explanation, which is the true one:
pytest had been launched by the system interpreter, where `typer` resolves from user-site `~/.local`,
so any test isolating `HOME` breaks that resolution and its subprocess dies with
`ModuleNotFoundError: No module named 'typer'`. Under the venv, `typer` lives inside the venv and
`HOME` isolation cannot reach it.

**Consequence: the 19/26 are a harness artefact of the degraded interpreter, not pre-existing
failures.** No follow-up issue was filed, and the charter's pre-existing-failure MUST is not
triggered. The control that does discriminate is printing `sys.executable` and `sys.prefix` from
inside the run.

## The orchestrator's error, which is the point of this record

On finding the above, the orchestrator ran `which python3`, saw `/usr/bin/python3`, and wrote a
standing rule asserting that **every** measurement on the mission had run on the system interpreter.

That was **inverted**. `which python3` reports what a bare `python3` resolves to — not what any agent
actually invoked. The evidence cited in support of the claim *disproves* it when read the right way
round:

- WP01's **implementer** quoted `plugins: anyio, xdist, timeout, cov, asyncio, respx, base-url,
  playwright` — eight names that map one-to-one onto the **venv**, and `base-url`/`playwright` exist
  nowhere else.
- WP01's **reviewer** quoted `plugins: respx, anyio` — exactly the **system** registry.

So implementers ran the venv and reviewers ran the system interpreter. The side to re-measure, if any,
is the **reviewer** side — the opposite of what the first version of the rule implied.

This is a real measurement, correctly taken, generalised into a conclusion it does not support. It is
the same shape as the `#3030` entries where a documented hazard *fitted* and was assumed to have
*fired*. It was caught by the `/analyze` gate, which returned `blocked` with a HIGH and refused to pass the
mission on to WP11. **Correction to an earlier draft of this record**, which claimed this was the
first time a gate rather than a reviewer caught a defect on this mission. It was not: **pass 1 of
`/analyze` also returned `blocked` on a HIGH** — the stale `lanes.json`, whose `lane-d` had lost
its `lane-a` edge and whose `lane-l` pointed at a file no work package owned. That fired *before
any work package dispatched*, eight passes earlier. The correction strengthens rather than
weakens the point: the gate has caught structural defects at both ends of the loop, and on both
occasions the thing it caught was invisible to every reviewer who had already passed the
artefact.

**Why it mattered enough to block**: `standing-rules.md` is copied verbatim into every subagent brief,
so all ten remaining work packages would have inherited a rule pointing at the wrong side, while the
two packages that most need the venv were told it was optional.

## What it corroborates, unplanned

Read correctly, WP01 is a **cross-environment replication**: the same red, with the same assertion
text and the same collected counts (4 collected → `1 failed, 3 passed`), obtained independently on
both interpreters. Nobody designed that. It is the strongest single piece of evidence in the mission,
and it existed unnoticed for three work packages because the two headers were never laid side by side.

## The absence claim that was checked because a wrong environment manufactures exactly this kind

*"`pytest-randomly` is not installed"* is load-bearing: it is why **C-005 was struck**, and why
WP01's determinism criterion had to be restated so it could fail. A wrong interpreter is precisely
what would fake it. Verified under **both** interpreters: `importlib.util.find_spec("pytest_randomly")`
returns `None`, and it appears in neither `pytest11` registry. **The strike is safe.**

## Standing consequences

1. **Use `.venv/bin/python -m pytest`**, or state the interpreter used and why.
2. **Quote `sys.executable` alongside the `plugins:` header** whenever a result is load-bearing. The
   header is the only reason this was recoverable after the fact.
3. **NFR-001 now governs it** — interpreter and plugin registry are part of the distribution a shard
   claim must state, alongside worker count, `--dist`, marker selection and `--cov`.
