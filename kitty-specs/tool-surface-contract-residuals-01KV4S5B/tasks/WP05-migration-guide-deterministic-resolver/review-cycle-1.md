# WP05 Review Cycle 1 — Reviewer Renata + Architect Alphonso C-003 sign-off

**Review date:** 2026-06-15
**Reviewer:** reviewer-renata (with architect-alphonso C-003 boundary lens)
**Verdict:** REQUEST CHANGES (single blocking gap: T021 per-caller evidence not committed)

---

## Summary

The implementation is substantially correct. Every enforcement check passes EXCEPT T021's
per-caller evidence requirement. The fix is a one-liner code comment addition.

---

## Evidence collected

### Tests — PASS (PYTHONPATH=src, lane code)

```
PYTHONPATH=src python -m pytest tests/specify_cli/core/test_paths.py \
  tests/specify_cli/cli/commands/test_doctor_skills.py -q
17 passed in 1.16s
```

All three resolver tests pass:
- `test_env_root_authoritative_without_kittify` — determinism from resolver fix, not monkeypatch
- `test_env_root_ignored_when_path_missing` — `exists()` guard retained
- `test_c003_real_kittify_resolves_same_with_and_without_env` — C-003 regression guard green

### C-003 boundary (architect-alphonso sign-off) — PASS

`test_c003_real_kittify_resolves_same_with_and_without_env` confirms: a real `.kittify/` project
resolves to the same canonical root whether or not `SPECIFY_REPO_ROOT` is set. The `paths.py`
change only affects the case where an existing, `.kittify`-less path is set — it does not alter
the resolution path for any currently-correct project. C-003 is safe.

### Frozen envelope — PASS

`git log kitty/mission-tool-surface-contract-residuals-01KV4S5B-01KV4S5B..HEAD -- src/specify_cli/cli/commands/doctor.py`
returns empty — `doctor.py` is untouched.

Both new doctor-skills tests use exact-dict (`==`) comparison, not `in` or key-subset.
`test_doctor_skills_json_error_schema_stable` asserts the full 17-key envelope
byte-identically. `test_doctor_skills_not_in_project_envelope_frozen` pins the
2-key error envelope exactly. No frozen assertion was loosened.

### #1965 resolver fix — PASS

OLD behavior (line 79): `if env_path.exists() and (env_path / KITTIFY_DIR).is_dir():`
→ an existing, `.kittify`-less path silently falls through to Tier-2 walk-up.

NEW behavior: `if env_path.exists():`
→ any existing path wins outright; `.kittify` presence is not required.
Non-existent path still falls through (`exists()` guard kept).

### #1944 guide — PASS

`docs/how-to/tool-surface-upgrade-and-repair.md` present (118 lines). Added to
`docs/how-to/toc.yml` and `docs/development/3-2-page-inventory.yaml`. Docs-lint
and terminology guard pass (7 lint tests green, 2 terminology tests green).

### ruff + mypy — PASS (no regressions)

`ruff check` passes clean on all changed files. The 8 `mypy --strict` errors
are pre-existing baseline (confirmed by running `mypy` against the base commit):
- `paths.py:475/481` — `get_feature_target_branch` no-any-return (pre-existing)
- `test_doctor_skills.py:28/38/117/192/205/219` — `_invoke` missing return
  annotation and downstream Any propagation (pre-existing)

WP05's new code introduces zero new mypy errors.

### Anti-pattern checklist

| # | Item | Result |
|---|------|--------|
| 1 | Dead code | PASS — all new production code has live callers; `SurfaceFinding` removal is WP01's commit |
| 2 | Synthetic-fixture test | PASS — deleting the `paths.py` fix causes `test_env_root_authoritative_without_kittify` and `test_doctor_skills_json_error_schema_stable` to fail |
| 3 | Silent empty return | PASS — no new silent returns; existing `except RuntimeError: pass` in `resolve_template_path` is pre-existing and benign (global home not required) |
| 4 | FR coverage | PASS — FR-007 covered by resolver tests + doctor-skills test; FR-006 covered by guide |
| 5 | Frozen surface | PASS — `doctor.py` untouched; frozen-envelope assertions are byte-identical exact-match |
| 6 | Locked decision | PASS — no MUST NOT violations |
| 7 | Shared-file ownership | PASS — all changed files are in WP05 `owned_files` or `authoritative_surface` |
| 8 | Production fragility | PASS — no new `raise` in production paths |

---

## Blocking issue

### T021 — per-caller evidence not committed (BLOCKING)

**Requirement (WP05 subtask T021):**

> Enumerate each of the 4 `project_resolver` callers with a one-line evidence statement
> that it does NOT rely on env-var/worktree authority for correctness here —
> `cli/helpers.py`, `cli/commands/lint.py`, `compat/planner.py`, `core/__init__`.
> **A checkable list, not "confirmed they're fine."**
> Document in **code comment + PR body**.

**Current state:**

The `project_resolver.py` docstring names the 4 callers and says:
> "see `docs/how-to/tool-surface-upgrade-and-repair.md` and the WP05 PR body
>  for the per-caller evidence"

The guide (`tool-surface-upgrade-and-repair.md`) contains no per-caller evidence.
The "WP05 PR body" does not exist as a committed artifact.
The code comment does NOT include the one-line per-caller evidence statements.

**Why this is blocking:** T021 requires a *checkable list* in committed form. Deferring
to a future PR body leaves the evidence unverifiable at review time and is specifically
what T021's "not 'confirmed they're fine'" clause guards against.

**Fix required — small, targeted:**

Add a committed per-caller evidence block to `src/specify_cli/core/project_resolver.py`
(in the `locate_project_root` docstring or as a comment directly below it). Example form:

```python
    # Callers that do NOT require env-var / worktree authority (#1971 pre-analysis):
    #   cli/helpers.py          — interactive CLI root detection; callers pass an
    #                             explicit `start` path; CI env-var not needed.
    #   cli/commands/lint.py    — uses `or Path.cwd()` fallback; content-addressed
    #                             lint does not depend on worktree pointers.
    #   compat/planner.py       — resolver injected at construction; the planner
    #                             caller controls which resolver to supply.
    #   core/__init__.py        — re-export shim; delegates to this function with no
    #                             additional authority assumptions.
```

The exact wording is for the implementer to adjust; the above is the required *form*.
The list must be committed (in-repo), not left as a future PR-body artefact.

---

## Non-blocking observations (informational)

- The `specify_cli/__init__.py` defines a thin `locate_project_root()` shim that
  delegates to `project_resolver`. It is not a 5th direct caller — it is itself a
  re-export — but the docstring's "4 callers" count is correct. No action required.
- `research.py` imports `resolve_template_path` (not `locate_project_root`) from
  `project_resolver` — correctly excluded from the 4-caller list.
- The `except RuntimeError: pass` in `resolve_template_path` is pre-existing; no
  Sonar concern from WP05.
