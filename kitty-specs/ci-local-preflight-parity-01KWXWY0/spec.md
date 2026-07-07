# Mission Specification: Local pre-PR CI parity + contract-conformance boundary

**Status**: Draft
**Issues**: Closes [#2283](https://github.com/Priivacy-ai/spec-kitty/issues/2283) (Phase 3 — the delivery-topology follow-through)

## User Scenarios & Testing *(mandatory)*

**Primary actor**: a contributor whose **local** `pytest tests/` diverges from CI — CLI shards behave differently on their `.venv`, and there is no local command to run the CI residual selection before pushing — so functional failures still surface only in CI.

**Grounding** (architect-first design, verified against the live branch):
- **Factor (a)'s CI marker gate ALREADY landed** — commit `6e5453e6d` (mission ci-suite-map-bind, closes #2034) added the always-on `unit-contract-residual` job (`ci-quality.yml:2407-2421`) selecting `(unit or contract)`, in the blocking `quality-gate.needs` (`:3437`). #2283's premise "no CI gate selects `-m unit`/`-m contract`" is **stale** on the live branch. → this mission **verifies** it, does NOT re-add (re-adding reds `test_marker_job_completeness.py:288` — "exactly one gate selects unit+contract").
- **Factor (c-dynamic) — "a consuming test now fails" — delivered in #2438 (M5's `pre_review_gate.py`, which runs the consuming shards at `for_review`), PENDING its merge** — its code is NOT yet on this branch (see C-003 / FR-005; the boundary decision records this conditionally, never as settled fact). Do NOT rebuild it here.
- **Remaining real gaps** (both at the LOCAL pre-PR layer #2283 names as "blind"):
  - **(b) venv skew**: `pyproject.toml:52-53` pins `typer>=0.24.1` / `click>=8.2.1` (lower-bound only). CI installs `uv sync --frozen` → exactly `typer==0.24.2` / `click==8.3.3`. A local `.venv` built **without** `--frozen` can pull `typer>=0.26`, which vendors click and stops re-exporting it (the repo defends this intentionally: TID251 Gap-5 ban `pyproject.toml:253-259`, the `typer>=0.26` compat CI step `ci-quality.yml:683`) → local CLI-shard behavior diverges from CI. The preflight `_test_env_check.py:21-33` only checks `import pytest` — **blind** to the skew.
  - **(a)-local**: no local command runs the residual `-m` selection (`ci-quality.yml:2418`) before pushing.
- **(c-static / c′)** — "a production caller still references a retired contract that NO test exercises" — is a genuine residual that a *test-run* structurally CANNOT catch (it proves the *presence* of a new failure, never the *absence* of a retired symbol). It is **out of this mission** — already routed to CT7 (#2077); this mission adjudicates the boundary + sharpens the handoff.

### User Story 1 - Local run faithfully mirrors CI's CLI shards (Priority: P1)
As a contributor, I want a preflight that flags when my `.venv`'s `typer`/`click` diverge from `uv.lock`, so my local CLI-shard results aren't silently masked by a version skew I can't see.

**Independent test**: with an active env whose `typer`/`click` differ from `uv.lock`, the review preflight raises an explicit skew diagnostic naming the remediation (`uv sync --frozen --all-extras`); with a matching env it passes.

### User Story 2 - A local command runs the CI residual before push (Priority: P2)
As a contributor, I want a single local command that runs the same `(unit or contract)` residual selection CI runs, so marker-orphan failures surface pre-push, not post-merge.

### User Story 3 - The contract-conformance boundary is adjudicated, not relitigated (Priority: P2)
As a maintainer, I want a written decision recording that #2438 discharges factor (c-dynamic) and (c-static) is owned by CT7 (#2077), plus a filed contract-ownership issue — so the three-mechanism overlap (#2438 dynamic / stale_assertions static-on-tests / the grep family) stops spawning a new bespoke net each time.

### Edge Cases
- The lock-parity check must read the ACTUAL locked versions from `uv.lock` (single source), not a hardcoded copy — so it can't drift from the pin.
- The local residual runner must single-source its `-m` expression from `ci-quality.yml:2418` (or the same `_gate_coverage` model), NEVER a divergent hand-copied string.
- Default is **warn-loud, not fail-closed** — a legitimately forward-compat dev loop (testing `typer>=0.26`) must not be bricked; fail-closed is opt-in.
- This mission ships **NO** new (c) sweep/grep mechanism and adds **NO** new allowlist artifact (would be a 4th detector — the over-scope trap).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
| --- | --- | --- | --- | --- |
| FR-001 | Preflight typer/click lock-parity check | As a contributor, I want `_test_env_check.py` extended with a check that reads the locked `typer`/`click` versions from `uv.lock` and compares them to the installed versions (`importlib.metadata`), raising a **new `MISSION_REVIEW_ENV_SKEW`** diagnostic (following the `MISSION_REVIEW_*` pattern in `review/ERROR_CODES.md`) with remediation `uv sync --frozen --all-extras` on divergence. **Warn-loud by default; fail-closed opt-in.** Wired into the review preflight (`review/__init__.py:307`, after `assert_pytest_available`). NOT a `pyproject.toml` pin change (the repo intentionally stays forward-compat with `typer>=0.26`). | High | Open |
| FR-002 | Local residual-selection runner | As a contributor, I want a local command (a `doctor`/preflight sub-check or a documented one-liner) that runs the CI residual `-m (unit or contract) and not (...)` selection over `tests/`, with the `-m` expression **single-sourced** from the CI selector (`ci-quality.yml:2418` / the `_gate_coverage` marker model), never a hand-copied duplicate. Surfaces the unit/contract failures locally that today reach CI. | Medium | Open |
| FR-003 | Docs: the NEW local-parity affordances | As a contributor, I want `docs/guides/review-gates.md` — which ALREADY documents the `--frozen` requirement (`:16-78`) — to gain the two genuinely-NEW items: (1) the preflight now flags typer/click version skew (`MISSION_REVIEW_ENV_SKEW`) and how to resolve it, and (2) how to run the residual `(unit or contract)` selection locally. Cross-link from `testing-parallel.md` only if not already linked. Canonical "Mission" terminology (terminology guard). | Medium | Open |
| FR-004 | Verify factor-(a) CI gate (no re-add, no duplication) | As a maintainer, I want a verification that asserts ONLY the facts NOT already pinned by `test_marker_job_completeness.py` (which already asserts exactly-one-gate-selects-unit+contract at `:288` + routed-by-marker at `:223`): namely that the `unit-contract-residual` job is **always-on** (no `if:` gate) and is a **named member of `quality-gate.needs`** — with a regression note that **references** (does not re-pin) the existing exactly-one assertion. **No workflow edit; no duplicated invariant.** | Medium | Open |
| FR-005 | Contract-conformance boundary adjudication + CT7 handoff | As a maintainer, I want a written decision (in the mission dossier + a filed tracked issue) recording: **#2438 discharges factor (c-dynamic) ONCE IT MERGES to upstream** — its `pre_review_gate.py` is NOT yet on the target branch, so the decision states this **conditionally** ("(c-dynamic) is delivered-pending-#2438-merge, NOT closed"), never as settled fact; (c-static/c′) — repo-wide assert-absence of a retired-contract literal / `falls_back` name / removed-signature call-site that no test exercises — remains open and is owned by **CT7 (#2077)** with a sharpened payload ("mechanise the `test_no_legacy_*` grep-absence family into a content-anchored, allowlist-free retired-contract sweep, triggered on shared-contract retirement"); and a filed **contract-ownership boundary** issue (the durable fix = give a shared contract an owner + declared consumer set) **whose URL(s) are EMBEDDED in the dossier decision record** (so the handoff is grep-verifiable, not a dangling pointer). **NO new (c) mechanism code here.** | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| NFR-001 | Low blast radius | FR-001/002/003 touch NO `.github/workflows/` file, NO dependency graph, NO `uv.lock` (zero lock churn), and define no dorny filter group — so the ci-suite-map-bind / census coherence invariants are untouched. FR-004 is read-only verification. | Safety | High | Open |
| NFR-002 | No drift | The lock-parity check reads `uv.lock` live; the residual runner reads the CI `-m` expression live — neither hardcodes a copy that can silently diverge. | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| C-001 | Not a pin change | Do NOT add a `typer`/`click` upper bound or edit the pins — the repo intentionally maintains forward-compat with `typer>=0.26` (CI step `:683`, Gap-5 ban `:253-259`). | Technical | High | Open |
| C-002 | No 4th detector / no new allowlist | Ship NO new (c) sweep/grep mechanism and NO new standalone static-analysis allowlist artifact (would duplicate #2438 + stale_assertions + the `test_no_legacy_*` family — the over-scope trap). (c-static) is CT7's. | Technical | High | Open |
| C-003 | Coordinate with #2438 | `pre_review_gate.py` is absent on upstream/main (it's our unmerged #2438). FR-002's local runner must NOT double-implement M5's gate; land-order / reuse must be coordinated. | Technical | High | Open |
| C-004 | No new suppressions | `ruff` + `mypy --strict` clean; no new `# noqa`/`# type: ignore`. | Technical | High | Open |

### Key Entities
- **`src/specify_cli/cli/commands/_test_env_check.py`** (`:21-33` `assert_pytest_available`) — the preflight seam; FR-001 adds the lock-parity check here.
- **`src/specify_cli/cli/commands/review/__init__.py`** (`:307`) — where the preflight is invoked; FR-001/002 wire in after `assert_pytest_available`.
- **`review/ERROR_CODES.md`** — the `MISSION_REVIEW_*` catalog; FR-001 adds `MISSION_REVIEW_ENV_SKEW`.
- **`pyproject.toml:52-53`** (typer/click pins) + **`uv.lock`** (locked `typer==0.24.2`/`click==8.3.3`) — read-only source for the parity check.
- **`.github/workflows/ci-quality.yml`** `unit-contract-residual` (`:2407-2421`, selector `:2418`) + `quality-gate.needs` (`:3437`) — read-only for FR-002/FR-004.
- **`docs/guides/review-gates.md`** — FR-003 docs.
- The (c-static) residual + the contract-ownership boundary → **CT7 #2077** + a new filed issue (FR-005); NOT built here.

## Success Criteria *(mandatory)*
- **SC-001**: With an env whose `typer`/`click` diverge from `uv.lock`, the review preflight raises `MISSION_REVIEW_ENV_SKEW` naming `uv sync --frozen --all-extras`; a matching env passes. Default warn-loud; fail-closed opt-in.
- **SC-002**: A documented/available local command runs the CI residual `(unit or contract)` selection, with its `-m` expression single-sourced from the CI selector (proven: no hand-copied duplicate string).
- **SC-003**: `docs/guides/review-gates.md` gains the two NEW items (the typer/click skew flag + the local residual-run instructions) alongside its existing `--frozen` section; terminology guard green.
- **SC-004**: The factor-(a) verification asserts the two facts NOT already covered — `unit-contract-residual` is always-on (no `if:`) + a named member of `quality-gate.needs` — and **references** (does not duplicate) the existing exactly-one-selects assertion in `test_marker_job_completeness.py:288`, WITHOUT editing any workflow.
- **SC-005**: The boundary decision is recorded in the dossier — **conditionally scoped on #2438's merge for (c-dynamic)** — with the filed contract-ownership/CT7-sharpening issue **URL(s) embedded in the record** (grep-verifiable, not a bare "an issue was filed" claim); NO new (c) mechanism/allowlist ships.
- **SC-006**: NFR-001 holds — `git diff` touches no `.github/workflows/` file, no `uv.lock`, no `pyproject.toml` deps; `ruff` + `mypy --strict` clean; no new suppressions.

## Out of Scope
- Factor (a)'s CI marker gate (already landed via #2034 — verify only).
- Factor (c-dynamic) (delivered in #2438, pending its merge — not rebuilt here).
- The (c-static) retired-contract sweep mechanism itself (CT7 #2077) + the contract-ownership registry (a separate mission / CT7).
- Any dorny-routing / census widening to raise #2438's recall — that's a #2438 follow-up, not #2283 factor (a).
- Any typer/click pin change.

## Assumptions
- Factor (a)-CI is landed ON the target branch (#2034 / `6e5453e6d`); factor (c-dynamic) is delivered in **#2438 (pending its merge to upstream)** — the boundary decision (FR-005) records it conditionally, not as already-on-branch. The real remaining #2283 work is the local pre-PR parity + the boundary decision.
- `uv.lock` is the authoritative pinned-version source the parity check can read at review time.
