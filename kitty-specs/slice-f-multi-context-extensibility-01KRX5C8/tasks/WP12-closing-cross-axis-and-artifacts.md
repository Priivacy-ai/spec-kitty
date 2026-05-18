---
work_package_id: WP12
title: Closing — cross-axis integration tests + glossary canonical promotion + READMEs + charter amendments + auth-transport ADR + GitHub ticket
dependencies:
- WP01
- WP02
- WP03
- WP04
- WP05
- WP06
- WP07
- WP08
- WP09
- WP10
- WP11
requirement_refs:
- C-004
- C-005
- C-006
- C-007
- C-010
- C-011
- FR-200
- FR-201
- FR-202
- FR-300
- FR-301
- FR-302
- FR-303
- FR-304
- NFR-001
- NFR-002
- NFR-003
- NFR-004
- NFR-005
- NFR-007
- NFR-008
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T061
- T062
- T063
- T064
- T065
- T066
- T067
- T068
- T069
- T070
- T071
- T072
agent: "claude:sonnet-4-6:python-pedro:implementer"
history: []
agent_profile: python-pedro
authoritative_surface: architecture/adrs/
execution_mode: code_change
owned_files:
- architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md
- tests/architectural/README.md
- src/specify_cli/upgrade/migrations/README.md
- glossary/contexts/doctrine.md
- .kittify/charter/charter.md
- tests/glossary/test_canonical_promotion.py
- tests/integration/test_slice_f_cross_axis.py
- kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/atdd-coverage.md
role: implementer
tags: []
shell_pid: "2952685"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else. WP12 spans documentation, glossary, charter amendments, ADR authorship, and final regression sweeps — it benefits from architect-alphonso review at the ADR section (see Reviewer Guidance), but the default profile remains `python-pedro` for execution.

---

## Objective

Close the mission. Twelve deliverables:

1. **Auth-transport ADR (FR-200, AC-12, C-005)** — author `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` per HiC §5a.3. No source change to `src/specify_cli/auth/transport.py`.
2. **GitHub ticket (FR-201, AC-13)** — open against `Priivacy-ai/spec-kitty` labelled for Robert's queue; pin URL in commit message.
3. **5-axis architectural README (FR-300, AC-14)** — `tests/architectural/README.md` documents the 5-axis model and lists every gate.
4. **Forward-staged migrations README (FR-301, AC-15, Q7)** — `src/specify_cli/upgrade/migrations/README.md` documents the convention.
5. **Glossary canonical promotion (FR-302, AC-11, C-010, NFR-004)** — promote all 10 Slice F domain terms in `glossary/contexts/doctrine.md` from `candidate` to `canonical`.
6. **Canonical-promotion ATDD test (FR-302, C-010)** — `tests/glossary/test_canonical_promotion.py`.
7. **Charter amendments (FR-303, AC-16, C-004/C-007/C-011)** — burn-down policy + `__all__` convention + ATDD-first discipline in `.kittify/charter/charter.md`.
8. **Cross-axis integration test (FR-300 broader)** — Axis 1 + Axis 2 + Axis 3 interact correctly in a single fixture (org pack + monorepo + custom workflow).
9. **`atdd-coverage.md` status update (FR-304)** — every row's `Status` column set to `green`; RED commit SHA pinned.
10. **Full architectural + governance regression sweep (NFR-001, NFR-003, NFR-005, AC-17)** — `PWHEADLESS=1 pytest tests/architectural/ tests/specify_cli/next/test_wp_prompt_governance_contract.py -v` exit 0.
11. **`spec-kitty analyze` (NFR-007, AC-18)** — verdict READY FOR IMPLEMENTATION with 0 CRITICAL / 0 HIGH.
12. **Close-out commit (FR-304)** — aggregates every test now GREEN, every FR satisfied, charter sections amended, ADR landed, GitHub ticket URL.

---

## Context

WP12 is the mission closer. By the time WP12 starts, WPs 01-11 have landed:

- Lane A: ratchet burn-down model + symbol-level dead-code + contract round-trip gate (architectural rigor).
- Lane B: DRIFT-1 alias deleted + CLI logging bootstrap with Rich-aware handler.
- Lane C: org-DRG loader + merge + provenance + operator UX.
- Lane D: ADR-8 + CharterScope + workflow registry + runtime integration.

WP12's job is to surface the conventions in the charter (future missions inherit), promote glossary terms (pre-acceptance gate per C-010), document the architectural model (5-axis README), document the forward-staged migrations convention, and ship the auth-transport ADR + GitHub ticket (descoped per HiC §5a.3 — ADR-only, no source change).

References:
- [spec.md FR-200..FR-304](../spec.md)
- [spec.md AC-12..AC-18](../spec.md)
- [plan.md §1.9, §6](../plan.md)
- [atdd-coverage.md existence-only ACs](../atdd-coverage.md)
- [decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md](../decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md)

**Existence-only ACs (NFR-008 slack):** AC-12 (ADR), AC-13 (ticket), AC-14 (README), AC-15 (doc), AC-16 (charter) ship pure-documentation artefacts whose existence IS the test. No red→green discipline applies to those — but T066 lands the canonical-promotion ATDD test for AC-11, which IS subject to red→green.

**C-005 (binding) — NO source change to `src/specify_cli/auth/transport.py`.** WP12 authors the ADR + opens the ticket only. Deletion is Robert's call.

---

## ATDD Discipline

WP12 has ONE failing-first ATDD test (T066 for AC-11). The other 11 deliverables are existence-only or aggregation tasks.

1. **Commit A (RED, T066):** `tests/glossary/test_canonical_promotion.py::test_all_slice_f_terms_are_canonical_in_doctrine_context`. RED on planning base because the 10 Slice F terms are still `candidate` (per WP08). Commit message: `covers: AC-11, FR-302, C-010 — expected GREEN at: WP12 final commit after T065 promotion`.
2. **Commit B (GREEN, T065):** promote all 10 terms to `canonical` in `glossary/contexts/doctrine.md`. T066 turns GREEN.

Other deliverables sequence into commits as listed below; the close-out commit (T072) aggregates everything per FR-304.

---

## Subtasks

### T061 — Author auth-transport ADR (FR-200, AC-12, C-005)

**File:** `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` (new)

Per FR-200 + HiC §5a.3 (verbatim in C-005):

```markdown
# ADR 2026-05-18-2 — DELETE specify_cli.auth.transport (deferred to Robert)

**Status:** Accepted (DELETE recommended; deferred for execution to lead maintainer Robert)
**Decision driver:** post-Mission-B architectural review, HIGH-3 finding
**HiC adjudication:** 2026-05-18 §5a.3 (verbatim binding)

## Context

`src/specify_cli/auth/transport.py` ships as part of the spec-kitty CLI but has
zero non-test callers. Verified at HEAD `6ae8d449`:

```bash
rg "from specify_cli.auth.transport" src/specify_cli/
# returns 0 matches
```

Alternate HTTP paths exist in sync and tracker subsystems; the
`test_auth_transport_singleton` architectural gate passes vacuously
(allowlist of 2 entries — neither call site is currently live).
This is a C4 contradiction: the module claims to mediate auth-transport
but mediates nothing.

## Audit Evidence

- Module exposes `AuthTransport` (singleton); zero callers in `src/specify_cli/`.
- `tests/architectural/test_auth_transport_singleton.py` asserts the singleton
  pattern; the `_ALLOWED_DIRECT_HTTPX_FILES` allowlist (2 entries) names files
  that don't currently route through the module.
- Sync subsystem uses its own `httpx.AsyncClient` directly.
- Tracker subsystem uses its own request flow.

## Recommendation

**DELETE** `src/specify_cli/auth/transport.py` and remove `test_auth_transport_singleton.py`.

## Deferral rationale (HiC §5a.3, binding via C-005)

Verbatim HiC adjudication (2026-05-18):

> "Delete, but explicitly create an ADR for it, which is to be updated mentioning
> the code that is deleted, and the commit in which it happened. In general: we
> want to be extremely careful with auth-path cleanup as Robert (lead maintainer)
> has indicated the SaaS platform has had recent auth-related challenges. It
> would be best to highlight this, add our research / evidence and
> recommendations, but leave the decision and clean-up action to Robert.
> (descope from our proposed mission scope, but create a ticket with our
> findings)."

## Reserved field for Robert

**Deleted in commit:** `<SHA>` (to be filled when deletion happens)
**Deletion PR:** `<URL>` (to be filled)
**Date of deletion:** `<DATE>` (to be filled)

## Related

- GitHub ticket: `Priivacy-ai/spec-kitty#<NNNN>` (opened by WP12 T062)
- spec.md FR-200, FR-201, FR-202, C-005, AC-12, AC-13
- HiC §5a.3 adjudication record (verbatim in spec.md)
```

### T062 — Open GitHub ticket (FR-201, AC-13)

Run:

```bash
gh issue create \
  --repo Priivacy-ai/spec-kitty \
  --title "[ROBERT-QUEUE] DELETE specify_cli.auth.transport (zero callers; auth-caution per HiC §5a.3)" \
  --label "auth,cleanup,architecture" \
  --body "$(cat <<'EOF'
Per ADR 2026-05-18-2 (architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md), `src/specify_cli/auth/transport.py` has zero callers (verified at HEAD 6ae8d449). The DELETE recommendation is deferred to Robert per HiC §5a.3 (binding via Slice F C-005) because of SaaS auth-path caution.

## Evidence
- `rg "from specify_cli.auth.transport" src/specify_cli/` returns 0 matches
- Sync + tracker subsystems use their own HTTP paths
- `test_auth_transport_singleton` passes vacuously (allowlist of 2)

## Ask
Lead maintainer to schedule the deletion in a separate PR. Update the ADR's
"Deleted in commit X" field at execution time.

## Slice F constraint
Per C-005 binding, Slice F MUST NOT modify `src/specify_cli/auth/transport.py`
or `tests/architectural/test_auth_transport_singleton.py`. Cleanup is
Robert's call.
EOF
)"
```

Capture the issue URL. Pin it in the WP12 close-out commit message (T072) and in the ADR's `GitHub ticket:` reserved field.

If `gh` fails with token scope errors, run `unset GITHUB_TOKEN && gh issue create ...` (per CLAUDE.md "GitHub CLI Authentication for Organization Repos" section).

### T063 — `tests/architectural/README.md` 5-axis model (FR-300, AC-14)

**File:** `tests/architectural/README.md` (new)

Per spec §"From `work/ratchet-coherence-audit.md` §3":

```markdown
# Architectural Test Suite — 5-Axis Model

The architectural tests in this directory enforce a **5-axis model** of the
spec-kitty architecture. Reading the gates collectively gives a faithful
one-page architecture description:

> *spec-kitty is a strictly layered system (kernel ← doctrine ← charter ← specify_cli)
> with mediated boundaries (charter mediates doctrine access; auth.transport
> mediates HTTP; emitter-adapter mediates cross-cutting events). Surfaces
> declared as facades or schemas must match implementation reality (parity).
> Operator-authored vocabularies are closed and SSOT-pinned. Every shipped
> module has a runtime caller; every released version has a migration path.
> Dependency manifests are exact and exclude retired packages. Process
> artifacts (markers, safety, compat shims) follow uniform conventions.*

## The 5 axes

| Axis | What it enforces | Representative gates |
|---|---|---|
| **1. Layer direction** | `kernel ← doctrine ← charter ← specify_cli` | `test_layer_rules.py`, `test_runtime_charter_doctrine_boundary.py` |
| **2. Surface completeness** | Schemas/facades match implementation reality | `test_artifact_selection_completeness.py`, `test_activation_registry_schema.py` |
| **3. Closed-vocabulary integrity** | Operator-authored vocabularies are closed and SSOT-pinned | `test_all_declarations_required.py`, `test_no_dead_symbols.py` |
| **4. Lifecycle presence** | Every shipped module has a runtime caller; every release has a migration | `test_no_dead_modules.py`, `test_migration_chain_integrity.py` |
| **5. Dependency hygiene** | Manifests are exact; cross-cutting boundaries mediated | `test_auth_transport_singleton.py`, `test_compat_shims.py`, `test_shared_package_boundary.py` |

## Gate index

(... full enumeration of every test in `tests/architectural/`, one bullet per file, citing the axis it covers ...)

## Burn-down policy

Per charter §"Burn-down policy" (binding per HiC §5a.2), each mutable
allowlist baseline in `_baselines.yaml` MUST NOT grow without an explicit
edit; Cat-7 (`test_no_dead_modules._CATEGORY_7_GRANDFATHERED`) shrinks ≥2
entries per major release with target 0 by 4.0.

See `_baselines.yaml` for the canonical per-test, per-category baselines.
See `test_ratchet_baselines.py` for the meta-test enforcing burn-down.
```

### T064 — Forward-staged migrations README (FR-301, AC-15, Q7)

**File:** `src/specify_cli/upgrade/migrations/README.md` (new or extend if exists)

```markdown
# Migrations — forward-staged convention

(Q7 resolution: forward-staged migrations convention documented per FR-301.)

The migration chain target may LEAD `pyproject.toml`'s version. The version
bump is a separate release step, run by the release maintainer after the
migration is verified at HEAD.

## Why

This keeps the migration chain testable and reviewable as a separate
artifact, decoupled from PyPI cut decisions. Pre-release verification
(`spec-kitty doctor upgrade --dry-run`) can target the next version
without forcing a release.

## Convention

- New migration files land at `m_X_Y_Z_<slug>.py` where `X.Y.Z` is the
  target version. The version may not yet be in `pyproject.toml`.
- The release process bumps `pyproject.toml` AND tags the release in the
  same commit; the migration is already present.
- `test_migration_chain_integrity.py` enforces ordering and contiguity.

See spec.md FR-301, plan.md Q7 resolution.
```

### T065 — Promote 10 Slice F glossary terms to `canonical`

**File:** `glossary/contexts/doctrine.md`

WP08 landed all 10 Slice F terms as `Status: candidate`. WP12 changes each entry's `Status:` line from `candidate` to `canonical`. The 10 terms (from spec §"Domain Language"):

1. Three-layer DRG
2. Organisation tier (org tier / org pack)
3. CharterScope
4. Workflow sequence
5. Workflow ID
6. Ratchet baseline
7. Cat-7 grandfathered orphans
8. Symbol-level dead code
9. Catalog miss
10. `__all__` declaration convention

This is a pre-acceptance gate per **C-010** (binding) — the mission cannot be accepted with any term still `candidate`.

### T066 — Land failing-first canonical-promotion ATDD test

**File:** `tests/glossary/test_canonical_promotion.py` (new)

```python
"""AC-11 / C-010 / NFR-004: Slice F glossary terms are canonical."""
from __future__ import annotations

import re
from pathlib import Path

SLICE_F_TERMS = [
    "Three-layer DRG",
    "Organisation tier",
    "CharterScope",
    "Workflow sequence",
    "Workflow ID",
    "Ratchet baseline",
    "Cat-7 grandfathered orphans",
    "Symbol-level dead code",
    "Catalog miss",
    "__all__ declaration convention",
]


def test_all_slice_f_terms_are_canonical_in_doctrine_context() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    glossary = (repo_root / "glossary" / "contexts" / "doctrine.md").read_text()
    offenders: list[str] = []
    for term in SLICE_F_TERMS:
        # find the section heading then assert the next Status: line is canonical
        pattern = re.compile(
            re.escape(term) + r".*?\*\*Status:\*\*\s*(\w+)",
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(glossary)
        if not match:
            offenders.append(f"{term}: missing or malformed entry")
        elif match.group(1).lower() != "canonical":
            offenders.append(f"{term}: Status={match.group(1)!r} (expected canonical)")
    assert not offenders, "Glossary canonical-promotion failures:\n  " + "\n  ".join(offenders)
```

**Validation:** on planning base (or even after WP08 if Slice F terms are still candidate), this test FAILS. After T065 it turns GREEN.

### T067 — Charter amendments (FR-303, AC-16)

**File:** `.kittify/charter/charter.md`

Add three sections per FR-303 / AC-16:

```markdown
## Burn-down policy (binding per HiC §5a.2 / C-004)

(a) Every mutable architectural allowlist is governed by a baseline in
`tests/architectural/_baselines.yaml`. Growth above baseline FAILS CI;
shrinkage WARNS (informational, non-fatal).

(b) `test_no_dead_modules._CATEGORY_7_GRANDFATHERED` (Cat-7) shrinks by ≥2
entries per major release; target 0 by 4.0.

(c) Pure-shim files (`test_compat_shims._ADAPTER_FILES`) target 0 by 4.0.

## `__all__` declaration convention (binding per C-007)

Every module under `src/charter/` and `src/kernel/` MUST declare `__all__`.
The symbol-level dead-code gate (`test_no_dead_symbols.py`) walks `__all__`
and asserts every name has at least one caller in `src/`.

Future expansion to other subpackages is a per-mission scope decision.

## ATDD-first discipline (binding per C-011)

Every implementation work package follows the red-green-refactor cycle.
The WP cannot start coding until at least one failing-first ATDD test
exists that pins the user-observable behaviour the WP delivers. The ATDD
test is committed as a separate commit (often the first commit of the lane)
BEFORE any implementation commits.

The reviewer verifies red→green: the test was RED on the WP's
`planning_base_branch` AND GREEN on the WP's final commit.

This mirrors Mission B's executable-contract pattern (the 7-file ATDD spec
at `bd95f1f5` was the canonical contract).
```

**Also amend the existing "Charter Resolution Hints" section (analyze finding F-CHA-01):** the current `authority_paths` declares `[glossary/contexts/, architecture/2.x/adr/]` but the repo's de-facto active ADR directory is `architecture/adrs/` (32+ ADRs there, including the two Slice F lands at T064 and elsewhere). Update the line to:

```yaml
authority_paths:
  - glossary/contexts/   # canonical terminology
  - architecture/2.x/adr/   # 2.x-era architectural decisions (historical)
  - architecture/adrs/   # active ADR directory (de-facto convention)
```

Without this amendment, every new ADR Slice F writes diverges from the charter-declared authority path. F-CHA-01 closure.

### T068 — Cross-axis integration test (FR-300 broader)

**File:** `tests/integration/test_slice_f_cross_axis.py` (new)

Asserts the three axes interact correctly in a single fixture:

```python
"""Cross-axis integration: org pack + monorepo + custom workflow."""

def test_org_pack_in_monorepo_with_custom_workflow(tmp_complex_setup):
    """Axis 1 + Axis 2 + Axis 3 in one fixture."""
    # Configure: org pack + charter_scopes + meta.json::workflow_id
    # Assert: charter_status reports 3 layers AND scope is correct AND next-action is per workflow
    ...
```

### T069 — Update `atdd-coverage.md` Status column (FR-304)

**File:** `kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/atdd-coverage.md`

For every row in the coverage table, change `Status: planned` to `Status: green` (or `red→green` with the RED commit SHA pinned per FR-304). Example:

```markdown
| Scenario 1 | Scenario | tests/integration/test_three_layer_drg_end_to_end.py | test_org_drg_fragment_merges_through_three_layers_with_provenance | WP06 (RED: <SHA>) | WP06 (GREEN: <SHA>) | green |
```

This is the canonical audit trail; reviewers consult it to verify red→green per spec §"Reviewer obligation".

### T070 — Full architectural + governance regression sweep

```bash
PWHEADLESS=1 pytest tests/architectural/ tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
# EXPECTED: exit 0 (NFR-001, NFR-003, NFR-005, AC-17)

pytest tests/architectural/test_wp_prompt_build_latency.py -v
# EXPECTED: within 1.2× Mission B baseline (NFR-002)
```

Capture timing data in the close-out commit message.

### T071 — `spec-kitty analyze` (NFR-007, AC-18)

```bash
spec-kitty analyze --mission slice-f-multi-context-extensibility-01KRX5C8
# EXPECTED: verdict READY FOR IMPLEMENTATION; 0 CRITICAL; 0 HIGH
```

Capture the analysis report at `kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/analysis-report.md`. If MEDIUM findings surface, document follow-up.

### T072 — Close-out commit aggregation (FR-304)

Single close-out commit aggregates:

- List of every test now GREEN (with SHA references).
- List of every FR satisfied.
- Charter sections amended (FR-303 a/b/c).
- ADR landed (`architecture/adrs/2026-05-18-2-...`).
- GitHub ticket URL (from T062).
- `spec-kitty analyze` verdict.
- Latency measurement (NFR-002).
- Glossary promotion (10 terms → canonical).

Commit message template:

```
chore(WP12): Close Slice F mission (slice-f-multi-context-extensibility-01KRX5C8)

Deliverables:
- ADR landed: architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md
- GitHub ticket: <URL>
- 5-axis architectural README: tests/architectural/README.md
- Forward-staged migrations README: src/specify_cli/upgrade/migrations/README.md
- Glossary promotion: 10 Slice F terms → canonical
- Charter amendments: FR-303(a/b/c) burn-down + __all__ + ATDD-first
- Cross-axis integration: tests/integration/test_slice_f_cross_axis.py

Test results:
- tests/architectural/: exit 0 (NFR-005)
- 23 governance-contract fixtures unchanged (NFR-001)
- test_layer_rules.py: pass (NFR-003)
- Latency: <X> ms (within 1.2× Mission B baseline, NFR-002)
- spec-kitty analyze: READY FOR IMPLEMENTATION, 0 CRITICAL, 0 HIGH (NFR-007, AC-18)

Closes: FR-200, FR-201, FR-202, FR-300, FR-301, FR-302, FR-303, FR-304
Covers: AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18
```

---

## Definition of Done

The following deliverables ship with this WP:

- ✅ `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` exists with all FR-200 sections + reserved field for Robert (AC-12)
- ✅ GitHub ticket open at `Priivacy-ai/spec-kitty` labelled for Robert's queue (AC-13)
- ✅ `tests/architectural/README.md` documents 5-axis model + every gate (AC-14)
- ✅ `src/specify_cli/upgrade/migrations/README.md` documents forward-staged convention (AC-15)
- ✅ 10 Slice F glossary terms promoted from `candidate` to `canonical` (AC-11, C-010, NFR-004)
- ✅ `tests/glossary/test_canonical_promotion.py::test_all_slice_f_terms_are_canonical_in_doctrine_context` GREEN (was RED before T065)
- ✅ `.kittify/charter/charter.md` amended with burn-down (FR-303a), `__all__` convention (FR-303b), ATDD-first discipline (FR-303c) (AC-16)
- ✅ `tests/integration/test_slice_f_cross_axis.py` GREEN (Axis 1 + 2 + 3 interaction)
- ✅ `atdd-coverage.md` Status column updated for all rows with RED/GREEN SHA references (FR-304)
- ✅ Full architectural sweep exit 0 (NFR-005)
- ✅ 23 governance-contract fixtures unchanged (NFR-001, AC-17)
- ✅ Layer-rule sweep unchanged (NFR-003)
- ✅ Latency within 1.2× Mission B baseline (NFR-002)
- ✅ `spec-kitty analyze` verdict READY FOR IMPLEMENTATION; 0 CRITICAL; 0 HIGH (NFR-007, AC-18)

FR coverage:

- ✅ FR-200, FR-201, FR-202 — ADR + ticket; NO source change to auth.transport (C-005 binding)
- ✅ FR-300 — `tests/architectural/README.md` documents 5-axis model
- ✅ FR-301 — forward-staged migrations convention documented
- ✅ FR-302 — 10 Slice F terms promoted to canonical
- ✅ FR-303 — charter amended with three new sections
- ✅ FR-304 — every ATDD commit cites scenario/AC + expected GREEN WP; close-out commit aggregates

AC coverage:

- ✅ AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18

---

## Risks

1. **C-005 violation — accidentally modify `src/specify_cli/auth/transport.py`** during the sweep. Mitigation: T070 explicitly greps `git diff feat/org-doctrine-layer HEAD -- src/specify_cli/auth/transport.py` and verifies empty diff. Reviewer rejects if any change appears.
2. **`gh` authentication fails on organization repo** (CLAUDE.md GitHub CLI section). Mitigation: T062 falls back to `unset GITHUB_TOKEN && gh issue create ...`. If still fails, document the manual ticket creation steps in the close-out commit and pin the ticket URL once filed.
3. **Glossary entry format drift** — `glossary/contexts/doctrine.md` may have a structured schema enforced by a validator. Mitigation: T065 reads an existing canonical entry (from Mission B) and mirrors the format exactly when changing the Status line.
4. **`spec-kitty analyze` surfaces a HIGH finding** that requires additional WP work. Mitigation: NFR-007 binds — if HIGH appears, document it as a follow-up ticket and either fix in WP12 or defer to a post-merge mission. AC-18 is a gate; a HIGH finding blocks mission close.
5. **Charter amendment conflicts with existing charter text** (overlapping sections). Mitigation: T067 reads the current charter, finds the right anchor, inserts the three new sections cleanly. If a conflict surfaces, reviewer adjudicates per spec §"Reviewer obligation".
6. **Cross-axis integration test fixture is complex** — org pack + monorepo + custom workflow setup may require ~50 LOC. Mitigation: T068 composes Lane C / Lane D fixtures via fixture chaining (`pytest fixtures`); each axis's setup is reused, not re-implemented.
7. **`atdd-coverage.md` SHA pinning requires WP-level final SHAs** — by the time WP12 runs, every prior WP's final SHA is known. Mitigation: T069 reads `git log --oneline feat/org-doctrine-layer` and extracts the GREEN SHA per WP.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011, applies to T066 only):**

```bash
# 1. RED on planning base (or pre-T065 state):
git checkout feat/org-doctrine-layer
pytest tests/glossary/test_canonical_promotion.py -v
# EXPECTED: failure (terms still `candidate`)

# 2. GREEN on WP final commit (after T065 promotion):
git checkout <wp_branch>
pytest tests/glossary/test_canonical_promotion.py -v
# EXPECTED: GREEN
```

**Substantive review checks:**

- Confirm `architecture/adrs/2026-05-18-2-delete-specify-cli-auth-transport.md` contains: (a) dead-code finding with `rg` verification command, (b) audit evidence, (c) DELETE recommendation, (d) deferral rationale (HiC verbatim), (e) "Deleted in commit X" reserved field — REJECT if any section missing (FR-200 binding).
- Confirm `git diff feat/org-doctrine-layer HEAD -- src/specify_cli/auth/transport.py` is EMPTY (C-005 binding — REJECT any change).
- Confirm `git diff feat/org-doctrine-layer HEAD -- tests/architectural/test_auth_transport_singleton.py` is EMPTY (C-005 binding).
- Confirm GitHub ticket URL is pinned in the ADR's reserved field AND in the close-out commit message.
- Confirm `tests/architectural/README.md` documents all 5 axes and indexes every test file (FR-300).
- Confirm `src/specify_cli/upgrade/migrations/README.md` documents the forward-staged convention (FR-301, Q7).
- Confirm all 10 Slice F glossary terms have `Status: canonical` (verify by running T066's test).
- Confirm charter has THREE new sections (burn-down, `__all__`, ATDD-first) per FR-303 (a/b/c).
- Confirm `atdd-coverage.md` Status column is updated for every row.
- Confirm full architectural sweep exit 0 (NFR-001, NFR-003, NFR-005, AC-17).
- Confirm latency within 1.2× baseline (NFR-002).
- Confirm `spec-kitty analyze` report shows READY FOR IMPLEMENTATION; 0 CRITICAL; 0 HIGH (NFR-007, AC-18) — REJECT if not.

**Architect review hint (optional):** the auth-transport ADR (T061) and the 5-axis README (T063) are architecturally load-bearing. After the implementer's submission, request a brief review pass from an architect-alphonso profile to verify the ADR sections match the architect's debrief framing and the 5-axis model description is correct.

**FR-304 commit-message check:** T066 RED commit cites `covers: AC-11, FR-302, C-010 — expected GREEN at: WP12 final commit`. T072 close-out commit aggregates every test now GREEN with SHA references.

## Activity Log

- 2026-05-18T20:41:22Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2952685 – Started implementation via action command
- 2026-05-18T21:07:01Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2952685 – WP12 closing: cross-axis tests + glossary canonical (10 terms -> canonical) + charter burn-down/__all__/ATDD-first amendments + auth-transport ADR + GitHub ticket #1118. C-005 binding honored (zero diff on transport.py). NFR-001 23/23 unchanged. Architectural sweep 236/237 (1 known pre-existing regression: ratchet-baseline-format.md::block-1 resolves at mission-merge). Ruff clean.
