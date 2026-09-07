# WP02 design note — glossary-runner design-story repair

**Mission**: `dead-port-disposition-01M1TZVN` (Mission B) · **WP**: WP02 · **Lane**: `kitty/mission-dead-port-disposition-01M1TZVN-lane-b`
**Requirements**: FR-008, FR-009, FR-010 · SC-004, SC-005 · **Contract**: `contracts/glossary-bootstrap.md`
**Decisions honoured**: OD5 (a) canonicalize the self-bootstrap (`01M1VAHKNXJTCMQNBQ350CWGEM`); OD6 resolved by the operator: **accept documented-but-unwired** as the steady state (spec non-goal 3 — wiring `execute_with_glossary` into the step executor is out of this mission).

Intended landing spot: `kitty-specs/dead-port-disposition-01M1TZVN/design-notes/WP02-glossary.md` (the lane gate forbids committing `kitty-specs/` on the lane, so the operator copies it in at consolidation time).

## 1. What was true before (the fiction)

Four sites told three variants of "`specify_cli` (or `glossary`) registers the runner at import/startup time":

| Site | Claim |
|---|---|
| `src/kernel/glossary_runner.py:12-16,33-38,79` | "`specify_cli` calls `register()` at import time"; provider usage block naming `specify_cli`; diagram `doctrine → kernel ← specify_cli`; `register()` docstring "Called by `specify_cli` at import time" |
| `src/charter/offering/missions/glossary_hook.py:16-17` | "registered … by `specify_cli` at startup" — contradicted eleven lines below by its own bootstrap |
| `src/kernel/README.md:18` | "`glossary` registers the concrete `GlossaryAwarePrimitiveRunner` at import time" |
| `src/kernel/__init__.py:41-42` | same as README |

Verified against `src/glossary/attachment.py`: it imports nothing from `kernel.glossary_runner` and calls `register()` nowhere. Nothing in `src/` registers at import or startup.

## 2. The contract now documented at all four sites

- `kernel.glossary_runner` is a **registry**: `GlossaryRunnerProtocol`, `register()`, `get_runner()`, `clear_registry()` (test-only).
- **Nobody registers at import or startup.** The only production provider is the consumer: `charter.offering.missions.glossary_hook.execute_with_glossary` → `_ensure_runner_registered()` → `get_runner()`; on `None`, `import_module("glossary.attachment")` → `register(GlossaryAwarePrimitiveRunner)` → retry `get_runner()`.
- **Degradation rule**: the primitive runs without glossary checks only when `import_module("glossary.attachment")` raises `ImportError` (pure-doctrine environments). "No runner registered" is not a steady state in a full install.
- **Dependency diagram**: `doctrine → kernel.glossary_runner ← charter.offering.missions.glossary_hook (lazy provider) ← glossary.attachment`. `specify_cli` plays no role.

## 3. Code motion (zero behaviour change)

The bootstrap at `glossary_hook.py:127-138` was extracted into `_ensure_runner_registered() -> type[GlossaryRunnerProtocol] | None` so the docstrings can name a function instead of a line range. Identical control flow and identical exception handling (`except Exception: return None`); `execute_with_glossary`'s signature, logging, and return paths are unchanged. The existing tests that patch `glossary_hook.get_runner` / `glossary_hook.import_module` still see the patches because the helper resolves both through module globals.

Safety probe before extracting: the escalated dead-symbol pin `specify_cli.missions::execute_with_glossary` (`test_no_dead_symbols.py:731`, hash `5942ba73…`) is the **re-export alias** hash (recomputed from `charter/primitives.py` and `charter/offering/missions/__init__.py`), not the function-body hash (`b64c2f5b…`), so the extraction cannot disturb the pin and the three-link re-export chain is untouched (US2-4).

## 4. Pins added (`tests/doctrine/missions/test_glossary_hook.py`)

- `TestSelfBootstrapContract::test_execute_with_glossary_self_bootstraps_registry` — invariant G-2 (FR-009).
- `TestSelfBootstrapContract::test_execute_with_glossary_degrades_only_when_attachment_unimportable` — degradation rule, via `monkeypatch.setitem(sys.modules, "glossary.attachment", None)`.
- `TestDesignStory` — invariant G-1 (SC-004) as a pinned test (same regex as the SC-004 grep, over the four sites), the self-bootstrap mention at each site, the helper being named by the hook docstring, and the FR-020 note (SC-005).
- Autouse `_clean_registry` fixture: `clear_registry()` before and after every test in the file (the registry is process-global).

ATDD-first (charter C-011): the pins were committed first; the `TestDesignStory` cases were RED on the WP's base commit and GREEN on the final commit; the two behaviour pins were green on base by design (they turn today's incidental mechanism into a pinned invariant).

## 5. FR-020 enforcement honesty — facts re-verified on this lane

```
grep -rn "execute_with_glossary(" src --include='*.py' | grep -v "def "
  → only the hook's own module docstring (`glossary_hook.py` prose + usage example); ZERO production call sites
grep -rn "glossary_check" packs/
  → ZERO matches
```

## 6. Tracker note for #1868 (operator posts; text ready to paste)

> **FR-020 enforcement honesty — from mission `dead-port-disposition-01M1TZVN` (Mission B, WP02, 2026-09).**
>
> `charter.offering.missions.glossary_hook` documents `glossary_check` as **enabled by default** (FR-020), and the kernel glossary-runner registry is live: `execute_with_glossary` lazily self-bootstraps `GlossaryAwarePrimitiveRunner` from `glossary.attachment` on first use (now documented at all four sites and pinned by `tests/doctrine/missions/test_glossary_hook.py::TestSelfBootstrapContract`).
>
> However, as verified on the mission lane:
> - `execute_with_glossary` has **zero production call sites** (`grep -rn "execute_with_glossary(" src --include='*.py' | grep -v "def "` matches only the hook's own docstring);
> - **no built-in step contract under `packs/` sets `glossary_check`** (`grep -rn "glossary_check" packs/` → zero).
>
> So the "enabled by default" claim is enforced **nowhere in the live mission loop**; the hook's tests pin the contract, not live behaviour. A code-adjacent `.. note::` in `glossary_hook.py`'s module docstring now says exactly this.
>
> SC-004 is green: `grep -n "at import time\|at startup\|registers the concrete\|specify_cli.*register" src/kernel/glossary_runner.py src/kernel/__init__.py src/kernel/README.md src/charter/offering/missions/glossary_hook.py` → zero matches; the former "`specify_cli`/`glossary` registers the runner at import/startup" story is gone.
>
> Working assumption recorded in the mission (OD6, operator-resolved): **documented-but-unwired is the accepted steady state.** Wiring the hook into the step executor is a **separate feature decision**, not implied by this note; if that decision is ever taken, it gets its own issue and mission.

## 7. Verification (commands + counts)

All run in the lane worktree with the shared `.venv` symlinked in; `timeout` bounded, foreground.

| Command | Result |
|---|---|
| `.venv/bin/pytest tests/doctrine/missions/test_glossary_hook.py -q -p no:cacheprovider` on the ATDD commit (base sites) | **10 failed, 23 passed** — the ten `TestDesignStory` cases RED on base; both `TestSelfBootstrapContract` pins green on base (expected) |
| same, on the final commit | **33 passed** |
| `.venv/bin/pytest tests/doctrine -q -p no:cacheprovider -n 4 --dist loadfile` | **3018 passed, 10 skipped, 1 failed** — the one failure was the FR-020 note pin's literal-substring brittleness against docstring wrapping; the pin was made whitespace-insensitive and the file re-run green (33 passed). A serial `tests/doctrine` run did not finish inside the 590 s foreground budget on the shared machine (three sibling pytest runs were live), hence the sanctioned `-n 4 --dist loadfile` shape |
| `.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py -q -p no:cacheprovider` | **96 passed** (terminology guard, layer rules incl. no `kernel → glossary` edge, dead-symbol gate incl. the escalated `execute_with_glossary` pin) |
| `.venv/bin/pytest tests/kernel/test_glossary_runner.py tests/agent/glossary/test_pipeline_integration.py -q -p no:cacheprovider` (the hook's other consumers) | **53 passed** |
| SC-004 grep (`grep -n "at import time\|at startup\|registers the concrete\|specify_cli.*register"` over the four sites) | **zero matches** |
| `ruff check` over the four changed `.py` files | All checks passed |
| `ruff format --check --force-exclude` over the four changed `.py` files | no reformat needed |
| `mypy src/kernel/glossary_runner.py src/charter/offering/missions/glossary_hook.py` (strict) | Success: no issues found in 2 source files |
| `grep -rn "execute_with_glossary(" src --include='*.py' \| grep -v "def "` | only the hook's own docstring (2 prose lines) — zero production call sites |
| `grep -rn "glossary_check" packs/` | zero matches |

`PWHEADLESS=1 make test-fast` was **not** run: it shells through `uv run`, which the lane rules forbid (`uv sync`/`uv run` off-limits); the blast-radius directories it covers (`tests/unit tests/status tests/cli tests/specify_cli/runtime`) contain no consumer of the five touched files (`grep -rl "glossary_hook\|glossary_runner" tests/` → `tests/agent/glossary/test_pipeline_integration.py`, `tests/doctrine/missions/test_glossary_hook.py`, `tests/architectural/test_no_dead_symbols.py`, `tests/kernel/test_glossary_runner.py` — all run above).
