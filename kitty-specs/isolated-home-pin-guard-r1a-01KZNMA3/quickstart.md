# Quickstart — R1a

**Environment, binding.** Reuse the external pytest-9.0.3 venv. **Never a bare `uv run` or `uv sync`.**
**Never create a `.venv` inside `/home/jeroennouws/dev/sk-missions/3121`.**
`.pytest_cache/spec-kitty-test-venv/` is built by the suite's own fixture and is not yours.

```bash
export SK_VENV=/home/jeroennouws/dev/sk-missions/3108/.venv   # verified pytest 9.0.3
cd /home/jeroennouws/dev/sk-missions/3121
timeout 60 "$SK_VENV/bin/pytest" --version                     # expect: pytest 9.0.3
```

Every long command is bounded with `timeout`. **A timeout is a datum — record it, never silently retry.**

---

## Verify the C-011 evidence anchor (pure stdlib, no venv)

```bash
timeout 600 python3 kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/research/\
spec_kitty_home_pin_evidence/verify.py      # "C-011 OK: 40 members ..." and exit 0
```

**Never run `step3.py` to verify** — it is preserved verbatim and writes to the scratchpad it was authored
in, so it validates a temp file, not the checked-in artefact.

## Regenerate the artefacts (the single documented command, FR-004(2))

```bash
timeout 300 "$SK_VENV/bin/python" -m tests.architectural._home_pin_scan --regenerate \
  --root tests --sha <freeze sha> --owed-to '#3121' \
  --exempt-module tests.architectural._home_pin_exempt
```

**`--exempt-module` is part of the command literal, not an option.** Without it nothing subtracts the owner
and the retained-pin probe, which **are** in `discover(root=tests)` at this point, so the census is generated
containing the owner and the census assertion fails. FR-004(2) requires both artefacts to carry a header
naming **this exact command**, so a second literal documented as "the one" is a defect, not a convenience.
`<freeze sha>` is the freeze SHA, not `$(git rev-parse HEAD)` — the census is frozen at a stated commit.

`frozen_at_sha` and `owed_to` are written **once, into the file header** — not onto 40 rows (A1). Rows carry
the `MemberKey` 3-tuple, a non-authoritative `lineno`, `kind` and `home_partition`.

Emits `tests/architectural/census/spec_kitty_home_pin_R1a.yaml` and
`tests/architectural/spec_kitty_home_pin_baseline.yaml`. **Both files are generated, never hand-edited**,
and both carry a header saying so. The baseline hashes the sorted **`MemberKey` triples** — `(rel_path, enclosing_qualname,
normalized_token_line)` — never the file bytes (plan §5), and never the bare 2-tuple BLOCKER-1 refused.

## Run the gate measurement (WP-0)

The gate lives in its **own** module — `_home_pin_scan.py` stays free of `subprocess`/`git` because
collected tests import it under a 6-second budget:

```bash
timeout 900 "$SK_VENV/bin/python" -m tests.architectural._home_pin_gate \
  --start 709a59534a1b8aac7e55a1cf6f5d2106a32c31ea \
  --end   5d49d31ed6505627d98d8f95d8502c9bf6a2f5ac
```

It also publishes the **start-SHA cross-check**: the checked-in independent `clf.py` run against a
`git archive` extraction at the start SHA, and the symmetric difference against `discover()`'s site set
there. Without it the start SHA has no independent anchor and the path of least resistance is
*tune until `r >= 50%`*.

Publishes the operands at both SHAs, the rename pairs, refused-ambiguous candidates, unpaired departures
and arrivals, `R` / `|R|` / `|R_f|` / `r`, every attempted window, the exact invocation, the ±1 stability
result over **consequence** classes, and the machine-readable `verdict:`.

**If `verdict: halt`, stop.** WP-a…WP-d do not begin. Operator sign-off is required; the implementer may
not proceed on their own authority.

## Run the guard

```bash
# the always-on selection, locally
timeout 300 "$SK_VENV/bin/pytest" tests/architectural/test_spec_kitty_home_pin_guard.py \
  tests/architectural/test_spec_kitty_home_pin_census.py \
  tests/architectural/test_spec_kitty_home_pin_prefilter.py -q -p no:cacheprovider

# NFR-003 — identical verdicts in both modes, both demonstrated
timeout 300 "$SK_VENV/bin/pytest" tests/architectural/test_spec_kitty_home_pin_guard.py -q -n0
timeout 300 "$SK_VENV/bin/pytest" tests/architectural/test_spec_kitty_home_pin_guard.py -q \
  -n auto --dist loadfile          # NEVER bare --dist load
```

## Budget (a) — NFR-001, 6 s warm ×3, gating

The budget test is `timing`-marked and runs in CI's **`timing-nfr-serial`** job (`-m timing -n0`,
`blacksmith-4vcpu-ubuntu-2404`, always-on, merge-blocking). That job is where OD-003's runner figure comes
from. Locally, reproduce it serially:

```bash
timeout 300 "$SK_VENV/bin/pytest" tests/architectural/test_spec_kitty_home_pin_budget.py -m timing -n0 -q
```

Raw warm-loop equivalent, for iterating without pytest overhead:

```bash
for i in 1 2 3; do
  timeout 120 "$SK_VENV/bin/python" -c \
    'import time,pathlib;from tests.architectural._home_pin_scan import discover;
t=time.perf_counter();m=discover(pathlib.Path("tests"));print(len(m),time.perf_counter()-t)'
done
```

**The budget may be RAISED with runner evidence (OD-003). The walk may NEVER be narrowed** — no directory
filter, no filename filter, no `except SyntaxError: continue`.

## Static gates

```bash
timeout 300 "$SK_VENV/bin/ruff" check tests/architectural/ tests/conftest.py tests/_arch_shard_map.py
timeout 600 "$SK_VENV/bin/mypy" --strict tests/architectural/_home_pin_scan.py
```

`ruff check` only — **never `ruff format`.** No new `# noqa`, `# type: ignore`, or per-file ignore.

## Gate instructions to refuse

| If a gate tells you to | Do this instead |
|---|---|
| `PYTHONPATH=. uv run python scripts/docs/docs_index.py --write` (`check_docs_freshness.py`, `DOCS-INDEX-DRIFT`) | Run the script with `"$SK_VENV/bin/python"`. A bare `uv run` re-syncs and destroys the venv. |
| `git restore --source <branch> --staged --worktree -- kitty-specs/` (`tasks_parsing_validation.py:808`, `move-task`) | **Never.** It destroys uncommitted spec/plan/tasks work. Commit with explicit-path `git add` first, then reconcile by hand. |

## Git rules

Explicit-path `git add` only — never `git add -A`, `git reset --hard`, `git checkout -- .`, `git clean` or
`git stash`. **Nothing is merged**: no `gh pr merge`, no `git merge`, no un-drafting. **No `gh issue
create`** — `gh issue view` / `gh issue comment` are fine (#3121 is updated by comment).

Commits are commitlint-clean: `type(<word-scope>): subject` ≤ 100 chars, body lines ≤ 100 chars.
