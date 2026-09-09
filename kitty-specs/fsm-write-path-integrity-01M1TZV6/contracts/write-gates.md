# Contract: Raw-Append Facade Strip and Write Gates (WP03)

**Owner**: `src/specify_cli/status/` + `tests/architectural/` · **Depends on**: WP01's fixed census
**Requirements**: FR-010, FR-011, SC-004 · **First instance of the census-gate rule** (note to be posted on #3895 per the PR body)

## 1. Facade strip — `status/_unsafe.py` (FR-010)

- Move the six `append_event*` names out of `status/__init__.__all__` (`:518-537`) into `status/_unsafe.py` as re-exports of `status/store.py`.
- `status/_unsafe.py` declares `ALLOWED_CALLERS: frozenset[str]` (dotted module paths), seeded from WP01's fixed census: families ②③⑤⑥⑦ (`data-model.md` §2) + `status/emit.py` + `coordination/status_transition.py`.
- **Shrink-only**: `tests/architectural/test_status_unsafe_allowlist.py` holds the committed baseline set; the test asserts `ALLOWED_CALLERS ⊆ BASELINE` and that every module importing `status._unsafe` (AST scan of `src/`) is in `ALLOWED_CALLERS`. Adding a caller fails the build; removing one requires editing both sets (deliberate).

## 2. AST writes-gate (FR-011)

`tests/architectural/test_status_events_writes_gate.py` scans `src/**/*.py` and FAILS when any module other than `src/specify_cli/status/store.py` contains:
- `open(<expr>, "a" | "a+" | "w" | "w+" | "ab" | "wb" …)` where `<expr>` is a string literal, f-string, `Path(...)/…`, or name whose static text ends in `status.events.jsonl`;
- `Path(...).write_text/write_bytes/open(...)` on such a path;
- `os.open(...)` with `O_WRONLY|O_APPEND|O_TRUNC` on such a path.

Resolution is static (best-effort name tracking within the function); a dynamic path that the scanner cannot resolve is NOT a pass — the gate also asserts a **positive census**: the set of modules where the scanner finds an *allowed* write (`store.py`) is exactly the expected set.

## 3. Non-vacuity floors (SC-004) — mandatory for both gates

| Gate | Floor test | Mechanism |
|---|---|---|
| allowlist | `test_allowlist_gate_is_not_vacuous` | Inject a synthetic module (tmp package on `sys.path`, or an AST fixture string) that imports `status._unsafe` and is NOT allowed ⇒ gate reports the violation. Also: `len(ALLOWED_CALLERS) >= 1` and every listed module actually imports `_unsafe` (a stale allowlist entry fails). |
| writes-gate | `test_writes_gate_is_not_vacuous` | Feed the scanner a synthetic source string with `open(p, "a")` where `p = ".../status.events.jsonl"` ⇒ violation reported. Feed it `store.py` ⇒ exactly the expected allowed sites found (count > 0). A scan matching zero writers anywhere ⇒ FAIL. |

Also covered by the writes-gate (R14): a third `feature_status_lock(...)` + append composition outside `status/emit.py` / `coordination/status_transition.py` / the WP01-hardened writer modules is reported (the gate scans for `feature_status_lock` call sites and asserts the set equals the census).

## 4. Rollout

1. Land WP01 (census fixed) → 2. add `_unsafe.py` + move exports → 3. add both gates GREEN with floors → 4. post the census-gate-rule note on #3895 → 5. delete/relocate any transitional red-first repro (C-009).
