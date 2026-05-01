---
work_package_id: WP01
title: Strict Private-Team Resolver
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-011
- FR-012
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-private-teamspace-ingress-safeguards-01KQH03Y
base_commit: d51eb075f3f5bfddc81bd1a274dc6fa946be9e62
created_at: '2026-05-01T08:13:55.248525+00:00'
subtasks:
- T001
- T002
- T003
- T004
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "2830"
history:
- date: '2026-05-01'
  author: spec-kitty.tasks
  note: Initial WP generated
agent_profile: python-pedro
authoritative_surface: src/specify_cli/auth/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/session.py
- tests/auth/test_session.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else in this prompt, load the assigned agent profile so your behavior, tone, and boundaries match what this work package expects:

```
/ad-hoc-profile-load python-pedro
```

This sets your role to `implementer`, scopes your editing surface to the `owned_files` declared in the frontmatter above, and applies the Python-specialist authoring standards. Do not skip this step.

## Objective

Add a single canonical strict resolver, `require_private_team_id(session) -> str | None`, in `src/specify_cli/auth/session.py`. The resolver is the only function direct-ingress code paths may use to derive the team id attached to `/api/v1/events/batch/` and `/api/v1/ws-token`. It NEVER returns `default_team_id` (even when set) and NEVER returns `teams[0].id` as a fallback.

Also tighten the docstring on the existing `pick_default_team_id` to make it explicit that it is **not** valid for direct ingress.

This WP establishes the foundational helper that WP04 and WP05 depend on. It has no behavioral effect on its own — call sites in `sync/` are not modified here.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` at `spec-kitty agent action implement WP01 --agent <name>`; do not guess the worktree path

## Context

### Why this exists

GitHub issue [Priivacy-ai/spec-kitty-saas#142](https://github.com/Priivacy-ai/spec-kitty-saas/issues/142) exposed that the CLI's direct sync ingress can resolve a shared-Teamspace target when the local session lacks a Private Teamspace. The SaaS rejects every such write with `Forbidden: Direct sync ingress must target Private Teamspace.`. The CLI must defend itself independently of the SaaS-side fix so stale sessions, old servers, or malformed auth payloads cannot cause direct ingress to target a shared Teamspace.

This WP introduces the strict resolver — pure function, no I/O — that downstream call sites will use exclusively for direct-ingress team identity. Pair it with `TokenManager.rehydrate_membership_if_needed()` (delivered in WP02) for the recovery path.

### Existing code surface

In `src/specify_cli/auth/session.py` two helpers already exist (lines 58–73):

```python
def pick_default_team_id(teams: list[Team]) -> str:
    """Return the preferred default team id for a new session.

    Private Teamspace wins when present; otherwise preserve the legacy first-team fallback.
    """
    for team in teams:
        if team.is_private_teamspace:
            return team.id
    return teams[0].id


def get_private_team_id(teams: list[Team]) -> str | None:
    """Return the user's Private Teamspace id when one is present."""
    for team in teams:
        if bool(getattr(team, "is_private_teamspace", False)):
            return team.id
    return None
```

`pick_default_team_id` is correctly used by login/UI default-team display; do **not** rename or remove it (Constraint C-004). `get_private_team_id` already returns the right thing for ingress callers — but it operates on `list[Team]` and the new resolver must take a full `StoredSession` (so it can be the canonical entry point for ingress code paths and so its docstring makes the contract explicit).

### Spec references

- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/spec.md` — FR-001, FR-002, FR-011, FR-012, NFR-004
- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md` §1
- `kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/data-model.md` (existing types section)

## Scope guardrail (binding)

This WP MUST NOT:

- Modify `pick_default_team_id`'s function body (only the docstring).
- Modify any call site in `sync/` — that is WP04/WP05 territory.
- Add I/O, logging, or any side effects to the new resolver.
- Touch `TokenManager` — that is WP02.

This WP MUST:

- Keep `mypy --strict` green for `src/specify_cli/auth/session.py` and `tests/auth/test_session.py`.
- Maintain ≥ 90% line coverage on the touched file.

## Subtasks

### T001 — Add `require_private_team_id(session)` strict resolver

**Purpose**: Introduce the single canonical entry point for direct-ingress team-id resolution.

**Steps**:

1. Open `src/specify_cli/auth/session.py`.
2. Below the existing `get_private_team_id` definition, add:

   ```python
   def require_private_team_id(session: StoredSession) -> str | None:
       """Return the Private Teamspace id for direct sync ingress, else None.

       Pure function. No I/O. No mutation.

       Contract:
         - If any team in ``session.teams`` has ``is_private_teamspace=True``, return that team's id.
           When more than one team has ``is_private_teamspace=True`` (today: not expected from SaaS),
           the first such team is returned for determinism.
         - Otherwise, return ``None``.
         - NEVER returns ``session.default_team_id`` (even when set).
         - NEVER returns ``session.teams[0].id`` as a fallback.

       Pair with ``TokenManager.rehydrate_membership_if_needed()`` to recover from
       a session whose ``teams`` list is stale.
       """
       return get_private_team_id(session.teams)
   ```

3. Confirm the import surface: `StoredSession` is already defined in this file; no new imports needed.

**Files**:

- `src/specify_cli/auth/session.py` — add the new function (≈ 18 lines including docstring).

**Validation**:

- [ ] Function signature is exactly `def require_private_team_id(session: StoredSession) -> str | None:`.
- [ ] Body delegates to `get_private_team_id(session.teams)`.
- [ ] No reference to `default_team_id` anywhere in the function.
- [ ] `mypy --strict src/specify_cli/auth/session.py` passes.
- [ ] `ruff check src/specify_cli/auth/session.py` passes.

---

### T002 — Tighten `pick_default_team_id` docstring

**Purpose**: Make the contract on `pick_default_team_id` explicit — it is for login/UI default display, not for direct ingress (FR-012).

**Steps**:

1. In `src/specify_cli/auth/session.py`, update the docstring of `pick_default_team_id` to:

   ```python
   def pick_default_team_id(teams: list[Team]) -> str:
       """Return the preferred default team id for new-session UI/login default display.

       Private Teamspace wins when present; otherwise preserves the legacy first-team
       fallback. This is *display-only* — it is **not** valid as a fallback for direct
       sync ingress. Direct-ingress code paths must use ``require_private_team_id`` paired
       with ``TokenManager.rehydrate_membership_if_needed()`` instead, which fails closed
       (returns ``None``) rather than returning a shared team.
       """
   ```

2. Do **not** modify the function body.

**Files**:

- `src/specify_cli/auth/session.py` — docstring change only.

**Validation**:

- [ ] Function body unchanged.
- [ ] Docstring contains the phrase "not valid as a fallback for direct sync ingress" verbatim (so callers searching for that string find it).
- [ ] No callers were modified.

---

### T003 — Unit tests for `require_private_team_id`

**Purpose**: Lock in the four critical contract cases. Use existing test fixtures from `tests/auth/conftest.py` (`StoredSession` factory + `Team` factory).

**Steps**:

1. Open or create `tests/auth/test_session.py`.
2. Add four test functions, all parametrized or inlined — whichever fits the file's existing style:

   ```python
   def test_require_private_team_id_returns_private_when_present(make_session, make_team):
       session = make_session(teams=[
           make_team(id="t-shared-1", is_private_teamspace=False),
           make_team(id="t-private", is_private_teamspace=True),
           make_team(id="t-shared-2", is_private_teamspace=False),
       ])
       assert require_private_team_id(session) == "t-private"


   def test_require_private_team_id_returns_none_when_no_private_team(make_session, make_team):
       session = make_session(teams=[
           make_team(id="t-shared-1", is_private_teamspace=False),
           make_team(id="t-shared-2", is_private_teamspace=False),
       ])
       assert require_private_team_id(session) is None


   def test_require_private_team_id_ignores_default_team_id(make_session, make_team):
       """Even when default_team_id is set to a shared team, no private team in
       the list means we return None — never fall back to default_team_id."""
       session = make_session(
           default_team_id="t-shared-default",
           teams=[
               make_team(id="t-shared-default", is_private_teamspace=False),
               make_team(id="t-shared-other", is_private_teamspace=False),
           ],
       )
       assert require_private_team_id(session) is None


   def test_require_private_team_id_never_returns_first_team_fallback(make_session, make_team):
       """Even with teams[0] populated, no private team => None. No teams[0] fallback."""
       session = make_session(teams=[
           make_team(id="t-first-shared", is_private_teamspace=False),
       ])
       assert require_private_team_id(session) is None
   ```

3. Import: `from specify_cli.auth.session import require_private_team_id`.
4. If the existing `tests/auth/conftest.py` does not yet expose `make_session`/`make_team` factories, use whatever the file currently uses (look at how `test_session.py` constructs sessions today). Match the existing style — do not refactor fixtures.

**Files**:

- `tests/auth/test_session.py` — add 4 test functions.

**Validation**:

- [ ] All four tests pass: `uv run pytest tests/auth/test_session.py -k require_private_team_id -v`.
- [ ] Coverage on `require_private_team_id` is 100% (all branches in the underlying `get_private_team_id` are exercised).
- [ ] No test modifies `pick_default_team_id`'s contract.

---

### T004 — Regression test: "Private wins even when default drifts"

**Purpose**: Spec NFR-004 requires that existing tests proving "Private Teamspace wins even when `default_team_id` drifts" continue to pass. This subtask validates that the new resolver behaves consistently and does not subtly alter that semantic.

**Steps**:

1. Search the existing test suite for the pattern that already covers this (likely in `tests/auth/test_session.py` or `tests/auth/test_authorization_code_flow.py`):

   ```bash
   grep -rn "default_team_id\|drift" tests/auth/ tests/sync/
   ```

2. If a "private wins even when default drifts" test exists, run it as-is and confirm green. Do not modify it.
3. Add a new explicit test for the resolver:

   ```python
   def test_require_private_team_id_wins_over_drifting_default(make_session, make_team):
       """Regression for spec NFR-004: when default_team_id points at a shared team
       but the team list contains a Private Teamspace, return the private id."""
       session = make_session(
           default_team_id="t-shared-default",
           teams=[
               make_team(id="t-shared-default", is_private_teamspace=False),
               make_team(id="t-private", is_private_teamspace=True),
           ],
       )
       assert require_private_team_id(session) == "t-private"
   ```

4. Run the existing related tests to confirm no regression: `uv run pytest tests/auth/test_session.py -v`.

**Files**:

- `tests/auth/test_session.py` — add 1 test function.

**Validation**:

- [ ] New regression test passes.
- [ ] All pre-existing tests in `tests/auth/test_session.py` still pass (no behavior change to `pick_default_team_id`).
- [ ] `uv run pytest tests/auth -v` is green.

---

## Definition of Done

- [ ] `require_private_team_id(session: StoredSession) -> str | None` exists in `src/specify_cli/auth/session.py` with the contract above.
- [ ] `pick_default_team_id` docstring contains the "not valid for direct ingress" guard.
- [ ] All four new tests pass (T003 + T004).
- [ ] All pre-existing tests in `tests/auth/test_session.py` pass.
- [ ] `mypy --strict` green for the touched file.
- [ ] `ruff check` green.
- [ ] Coverage on the new function is 100%.
- [ ] No call sites in `sync/` were modified (out of scope here).

## Risks & reviewer guidance

| Risk | Mitigation |
|------|------------|
| Adding the resolver but forgetting the docstring guard means future contributors may use `pick_default_team_id` for ingress | T002 makes the contract explicit; the phrase "not valid as a fallback for direct sync ingress" is searchable |
| Test fixtures might not exist with the names assumed in T003 | Author should adapt to the existing fixture style in `tests/auth/test_session.py`; the test bodies above are illustrative, not prescriptive on fixture names |
| A subtle behavior delta if `get_private_team_id` changes later | Body of `require_private_team_id` delegates to `get_private_team_id`; any future change to one must consider both — covered by the regression test in T004 |

**Reviewer should verify**:

- The new function does NOT touch `default_team_id`. (Read the body — it should be a single-line delegation.)
- Tests assert on `is None` for the no-private-team case, not on truthy/falsy.
- The "drift" regression test (T004) covers the exact scenario described in spec NFR-004.

---

## Implementation command (after dependencies satisfied)

```bash
spec-kitty agent action implement WP01 --agent <name>
```

This WP has no dependencies and can start immediately.

## Activity Log

- 2026-05-01T08:19:33Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=97766 – Started review via action command
- 2026-05-01T08:24:25Z – codex:gpt-5:reviewer-renata:reviewer – shell_pid=97766 – Moved to planned
- 2026-05-01T08:26:05Z – claude:sonnet:python-pedro:implementer – shell_pid=2830 – Started implementation via action command
- 2026-05-01T08:49:46Z – claude:sonnet:python-pedro:implementer – shell_pid=2830 – Review passed: strict private team resolver added with focused tests and auth validation green
