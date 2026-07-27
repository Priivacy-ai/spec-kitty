# Mission Specification: Naming/Identity Routing Rider

**Mission ID:** `01KV7SFD56KRZBDV977S9FMQMM` · **Slug:** `naming-identity-routing-rider-01KV7SFD`
**Type:** software-dev · **Planning/merge branch:** `feat/naming-rider-3-2-1` (stacked on
`design/naming-identity-ssot-alignment`; that branch PRs to `main`).
**Governing intent:** [`docs/release-goals/3.2.x.md`](../../docs/release-goals/3.2.x.md) G2 —
"strangle core domains onto SSOTs". This mission is the deliberate **low-risk opener** of the cycle
(operator chose safety-led over the neutral panel's impact lean; see
[`docs/engineering_notes/3-2-x-goal-corroboration/SCORING-SYNTHESIS.md`](../../docs/engineering_notes/3-2-x-goal-corroboration/SCORING-SYNTHESIS.md)).

## Purpose

**TL;DR:** Route the duplicated mission-identity derivation sites onto the existing canonical naming
seam, and guard the class with a tripwire — the low-risk opener of the 3.2.x SSOT cycle.

Spec Kitty derives mission identity — the `mid8` short-id and the branch / worktree / lanes paths — in
roughly twenty ad-hoc places (inline `mission_id[:8]`, hand-rolled path joins) instead of consuming the
single canonical seam built in 3.2.0 (`src/specify_cli/lanes/branch_naming.py` + the
`IdentityFragment` carried on `ExecutionContext`). The seam is **sound and load-bearing**; the defect is
**non-adoption**. This mission routes the consumers onto the seam, extends the architectural ratchet so
the duplication cannot silently regrow, and lands two pure-seam extractions — **building no new
authority** and **not** touching the heavier write-side coordination work, which is deferred to a follow-on mission (the read-path/write-side focus). It also folds in a bounded **command-contract-drift guard** (issue #2007 Focus A) — a sibling architectural-consistency guard plus the SOURCE doc/prompt repoints that keep agents from probing nonexistent CLI surfaces.

## Background & Motivation

Three research squads + a dialectic + a neutral scoring panel (2026-06-16) established: the read-path
identity SSOT already exists (`resolve_mid8`, `mid8()`, `IdentityFragment.mid8`, `resolve_action_context`);
the recurring split-brain regressions are **consumers re-deriving identity inline while a canonical
answer is available**. The literal-ban ratchet (`tests/architectural/test_no_worktree_name_guess.py`)
currently keys on the `mid8` token and so lets ~20 bare `mission_id[:8]`-class derivations escape. This
mission closes that adoption gap for the *cheap, low-risk* subset and arms the tripwire, leaving the
mutable-`ExecutionContext` builder-hardening and the write-side authority work to later 3.2.x patches.

## User Scenarios & Testing

### Primary actor
A Spec Kitty maintainer/contributor evolving identity-dependent code (and the **dashboard** as a
runtime consumer of derived identity).

### Scenario 1 — A consumer needs the short-id (happy path)
- **Trigger:** code needs the 8-char `mid8` for a branch/worktree/lanes path or a display.
- **Today:** the author writes `mission_id[:8]` inline (or hand-joins a path), creating another shadow
  derivation that drifts from the canonical grammar.
- **Desired outcome:** the call site obtains `mid8` from `resolve_mid8`/`mid8()` (when it has no
  context) or from the `IdentityFragment` it already holds (when it carries an `ExecutionContext`).
  There is exactly one derivation implementation in the tree.

### Scenario 2 — Someone reintroduces an inline derivation (regression guard)
- **Trigger:** a future change adds `mission_id[:8]` (or `…_id[:8]`) anywhere in active source.
- **Desired outcome:** the architectural-consistency ratchet **fails CI** and names the offending site;
  the allow-list does not grow.

### Scenario 3 — Verifying adoption is real (verification-by-deletion)
- **Trigger:** reviewer asks "is the routing genuine, or is the seam a parallel path?"
- **Desired outcome:** the shadow-path implementations are **deleted**; the behavioral suite stays green
  and identity-derived names/paths are unchanged. With only the canonical seam surviving, there is no
  second implementation (and no second fragment) left to conflate — the deletion *is* the proof.

### Test design principle (operator caveat, binding)
**Function over form.** Tests assert what the code *does* (identity derivation produces correct, stable
results end-to-end), not *how* it is wired. The wrong-fragment-conflation risk — where byte-identical
values could mask the wrong internal fragment being read — is handled **not** by white-box "which
fragment" assertions but by **verification-by-deletion** (Scenario 3). The **sole exception** is the
architectural-consistency tests (the literal-ban ratchet, terminology guards), which test form/structure
on purpose because that is their entire job.

## Domain Language

| Canonical term | Meaning | Avoid |
|----------------|---------|-------|
| `mission_id` | ULID (26 chars), canonical immutable machine identity | "feature id" |
| `mid8` | first 8 chars of `mission_id`; branch/worktree disambiguator | inline `mission_id[:8]` |
| **the seam** | `src/specify_cli/lanes/branch_naming.py` (compose/parse) + `mid8()`/`resolve_mid8` | "the helper(s)" |
| **IdentityFragment** | the identity value-object carried on `ExecutionContext` | re-deriving from `mission_id` |
| **shadow path** | any inline/duplicate identity derivation outside the seam | — |
| **tripwire** | the literal-ban ratchet as a *partial, syntax-level* regression guard (not a completeness oracle) | "the ratchet proves consolidation" |

## Functional Requirements

> **Revised 2026-06-16 after the adversarial scope review** (`scope-review/SCOPE-REVIEW-SYNTHESIS.md`).
> Routing core upheld; ticket mapping and the lanes-dir bet corrected. Changes: +5 missed sites; FR-004
> resized to a real AST detector; #1993 deferred (FR-005 retired); #2000 re-pointed at its true compose
> sites; #1888 promoted to a real bug fix; #1899-tail (phantom) and #1900 (deferred) dropped.

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Route every bare mission-`mid8` derivation in active source (`src/`) to `resolve_mid8`/`mid8()` where the site holds no `ExecutionContext` — **including the var-name-independent shapes** (`str(x)[:8]`, `mid[:8]`, `raw_mid[:8]`, `…_id_meta[:8]`). The verified set is **~15 sites** (the 10 originally inventoried + 5 the `*_id[:8]` grep missed; see research). | Draft |
| FR-002 | Verify that **no** call site re-derives `mid8`/branch/paths while holding an `ExecutionContext` (the inventory found 0); `IdentityFragment.mid8` remains the only context-held derivation. (Verification, not a change.) | Draft |
| FR-003 | Route the dashboard's identity derivation (`src/specify_cli/dashboard/scanner.py:438`) through the seam, preserving its `mid8 is None` registry contract (use `resolve_mid8(...) or None`). | Draft |
| FR-004 | Add a **new AST short-id detector** to the architectural ratchet (`tests/architectural/test_no_worktree_name_guess.py` — which today detects name *composes*, not slices), covering bare mission-`mid8` slices repo-wide **including** `dashboard/scanner.py`, on a documented name allow-list that must strictly **shrink**. Best-effort by construction (AST cannot distinguish `mission_id` from `invocation_id`); **verification-by-deletion (C-004) is the real guarantee, the ratchet is a tripwire.** | Draft |
| FR-005 | Route the **#2000 compose** sites — `core/mission_creation.py:321`, `core/worktree.py:367/370` — through the canonical `mission_dir_name`/`worktree_dir_name` seam functions (the defect is the *compose*, not the `mid8` slice; these already call `mid8()`). | Draft |
| FR-006 | #1971-tail: verify the `locate_project_root` delegation chain converges on the `core/paths.py` authority **and add a regression test that disproves the `SPECIFY_REPO_ROOT`/worktree split-brain the ticket asserts** (and pins the benign `__init__.py` no-arg signature divergence). Verify-and-close. | Draft |
| FR-007 | **#1888 (real bug fix):** add the missing **existence check** to `ownership/validation.py` so validation no longer passes phantom/non-existent owned paths silently; TDD-first (failing repro before the fix). | Draft |
| FR-008 | Preserve **byte-parity** (NFR-001) across all routed sites by honoring the two seam contracts: `mid8()` raises on short/None, `resolve_mid8()` returns `""`. Each routed site carries a per-site contract decision (raise / `""` / `None`); the `doctor.py:3070,3162` `try/except` short-id tolerance is changed only by conscious decision, not silent deletion. | Draft |
| FR-009 | Delete the shadow-path identity-derivation implementations made dead by FR-001/003/005; the canonical seam is the only surviving implementation (subject to FR-008's contract preservation). | Draft |
| FR-011 | **(#2007 Focus A) Repoint the 15 drifted SOURCE references** to real CLI surfaces: the 11 `doctrine list`/`doctrine show` refs in `src/doctrine/skills/spec-kitty-charter-doctrine/SKILL.md` + 1 in `spec-kitty-mission-system/SKILL.md` → the real `doctrine` subcommands / `DoctrineService` API; and the 3 behavioral refs in `src/doctrine/missions/mission-steps/software-dev/plan/prompt.md` (`agent context resolve` missing required `--action`; `setup-plan` no-flag-first → require `--mission`). Edit SOURCE only (agent copies regenerate). | Draft |
| FR-012 | **(#2007 Focus A) Add a command-snippet CI guard** generalizing the existing docs-CLI reference-parity test (`tests/architectural/test_docs_cli_reference_parity.py`, its agent-profile-subcommand parity check) + `scripts.docs._typer_walker.walk()`: validate `spec-kitty …` snippets in doctrine SOURCE prompts/skills/docs against the registered Typer surface, with three finding codes (unregistered-path, unknown-flag, internal-as-public). Runs in the existing docs-contract gate (no new CI job); empty-frozenset allow-list ratchet. Catches snippet drift, not behavioral drift. | Draft |
| FR-013 | **(#2007 Focus A) Fix the reproducing surface hints:** repoint the `agent worktree repair` hint (#13/#1890) to the real recovery surface (`doctor workspaces --fix`), and resolve the implement/review JSON-contract mismatch (#16/#1891) by **documenting/rewording** the canonical vs internal surface so agents don't pick the wrong one (adding `--json` to `agent action implement/review` is left to the read-path follow-on, not this guard). | Draft |
| FR-010 | **Use the 3.2.0 failover mechanic as THE SSOT entrypoint (option b — operator decision 2026-06-16).** Demote bare `mid8()` → internal `_mid8` so the **only public mid8 door is the failover-aware `resolve_mid8`** (canonical-first, "name proposes/authority disposes"); `resolve_transaction_mid8`/`resolve_mission_branch` remain the branch/transaction doors. The ratchet (FR-004) **forbids** correctness-path bypasses. Blast radius is bounded: **6 bare `mid8()` callers** — 3 internal to `branch_naming.py` (renamed to `_mid8`), 2 are the #2000 composes in `core/worktree.py`/`core/mission_creation.py` (routed through `worktree_dir_name`/`mission_dir_name`, which removes the call), and 1 in `lanes/worktree_allocator.py` (routed to `resolve_mid8`). Preserve the one-shot `DeprecationWarning` + `reset_legacy_failover_warning` test seam. | Draft |

## Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Behavioral parity: identity-derived names/paths (branch, worktree, lanes dir, project root, mid8) are byte-identical before and after. | 100% of derived strings unchanged across the behavioral suite; 0 snapshot diffs. | Draft |
| NFR-002 | Tests are behavioral / structure-detached (function over form). | 0 new white-box "which-fragment" assertions; architectural-consistency tests are the only form-coupled tests added. | Draft |
| NFR-003 | The ratchet allow-list shrinks. | Allow-list entry count after < count before; targeted `mission_id[:8]`-class entries → 0. | Draft |
| NFR-004 | Bounded conflict surface. | Only the named seam + consumer files are modified; no churn in unrelated modules. | Draft |
| NFR-005 | Idempotency preserved: no on-disk worktree/coord state churn from the routing. | 0 new/removed worktrees or coordination dirs produced by the changed code paths in tests. | Draft |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | **No new authority/SSOT.** Adopt the existing `branch_naming`/`mid8()` seam only; do not build a parallel helper. (The scope review confirmed a `resolve_lanes_dir` would *violate* this — lanes.json is already centralized in `persistence.py`.) | Active |
| C-002 | **No second path-authority** (C-001 corollary): the lanes-file path is already encapsulated by `persistence.py` (`read_lanes_json`/`require_lanes_json`); do **not** add a `resolve_lanes_dir` seam. #1993's real coord-aware target (`_lanes_feature_dir` in `implement()`) is deferred to a follow-on mission. | Active |
| C-003 | **TDD-first** for every behavioral fix (#1888, and any routing that changes a contract): the failing regression/characterization test lands before the change. | Active |
| C-004 | **Verification-by-deletion** is the primary correctness guarantee: shadow-path implementations are deleted and the behavioral suite must stay green; this replaces structure-coupled adoption assertions (the ratchet is a tripwire, not the proof). | Active |
| C-005 | **Out of scope (→ follow-on missions / later focus):** the #2007 **read-path/error-fidelity adoption** class (#4, #8, #12, #14, #15 + #2 — the next named focus), #1993 (coord-aware `_lanes_feature_dir`), #1900 (coord write-side ratchet, gated on coord-merge-stabilization), #1832 (read-path no-workspace), #1716 (coord topology authority), #1827 (re-test first), #1619 `ExecutionContext` builder-hardening. The `feature_dir.parent.parent` repo-root derivation class (~9 sites) is also deferred. Do not pull these in. | Active |
| C-006 | New code passes `ruff` + `mypy` with zero issues; no `# noqa`/`# type: ignore`/suppression to pass; complexity ≤ 15. | Active |
| C-007 | Not a bulk-edit mission: routing is per-site judgment (route vs. verify) + compose-routing + a ratchet + one bug fix, not a mechanical same-string rename. No `occurrence_map.yaml`. | Active |

## Success Criteria

| ID | Outcome (measurable, technology-agnostic) |
|----|-------------------------------------------|
| SC-001 | The ~15 inventoried bare mission-`mid8` derivations are routed through the seam and deleted; the ratchet's allow-list for that class has shrunk toward zero. *(Scoped honestly: this covers the inventoried class, not a universal "cannot regrow" — AST-indirection shapes and the deferred repo-root class are named limits, see FR-004/C-005.)* |
| SC-002 | Every identity-derived name/path is byte-unchanged for existing missions (behavioral parity, no migration, no on-disk churn) — including the contract-sensitive sites (FR-008). |
| SC-003 | The shadow-path implementations are deleted and the full test suite is green — proving the canonical seam is the only path (verification-by-deletion). |
| SC-004 | Each **addressed** ticket carries a terminal issue-matrix verdict: **#2000** fixed, **#1971-tail** verified-and-closed (with the split-brain-disproving test), **#1888** fixed. **#1899-tail** recorded as duplicate-of-#2000 (no independent tail); **#1900** and **#1993** recorded deferred-with-followup → a follow-on mission. Plus the folded **#2007 Focus A** command-drift items (FR-011/012/013). |
| SC-005 | The ratchet's coverage demonstrably includes `dashboard/scanner.py` (a planted inline derivation there fails CI); the `invocation_id[:8]` non-target does not trip it. |
| SC-006 | **(#2007 Focus A)** Zero drifted CLI snippets remain in doctrine SOURCE prompts/skills/docs (the 15 repoints landed); the command-snippet guard fails CI on a planted nonexistent-command snippet and passes clean; the `worktree repair` hint points to the real recovery surface. |

## Key Entities

- **`mission_id` / `mid8`** — canonical identity and its 8-char short form.
- **The seam** — `branch_naming.py` (compose/parse), `mid8()`, `resolve_mid8`.
- **`IdentityFragment` / `ExecutionContext`** — the carried identity value-object (read-only consumption only; no builder changes here).
- **`mission_dir_name` / `worktree_dir_name`** — the canonical compose seam functions (#2000 routes to these).
- **`locate_project_root`** — the project-root derivation seam, already consolidated in `core/paths.py` (#1971-tail, verify).
- **`ownership/validation.py`** — the phantom-path validation surface that #1888 fixes (add existence check).
- **The ratchet** — `tests/architectural/test_no_worktree_name_guess.py` (the tripwire; gains a new AST short-id detector).

## Tracker / Issue Matrix (to be detailed at tasks time)

**Addresses (revised after scope review + #2007 fold-in):** **#2000** (compose-routing, real files),
**#1971-tail** (verify-and-close), **#1888** (real existence-check fix); **#2007 Focus A** command-drift —
the 15 SOURCE repoints + the command-snippet CI guard + the #13/#1890 hint and #16/#1891 contract-doc
fixes (FR-011/012/013). Advances epics **#1868** (canonical seams) · **#1619** (runtime SSOT) via the
~15-site mid8 routing + ratchet, and **#2007** (command-contract-drift class).
**Dropped / deferred:** **#1899-tail** = duplicate-of-#2000 (#1899 closed in PR #2001, no independent
tail); **#1900** → follow-on (coord write-side, gated); **#1993** → follow-on (real target is the
coord-aware `_lanes_feature_dir` fallback; lanes.json path already centralized).
**Next focus (own mission):** the **#2007 read-path/error-fidelity adoption** class (#4, #8, #12, #14,
#15 + #2) — the field-proven read-side surface; "finish + adopt" the existing typed resolver.
**Reproduced live despite the fix being present on HEAD/v3.2.0 — DO NOT close (operator, 2026-06-16):**
#6, #7, #9, #10, #11. A static "fix is in the code" is a claim; Robert's live failure is evidence. The
#1944/#1965 fix for #6 *is* in v3.2.0 (an ancestor of HEAD) yet #6 still fired ⇒ the fix doesn't cover
the real path. Carried **OPEN**, re-investigated for the missed path (incomplete-coverage / unwired /
alternate-trigger), and owned by the **read-path/error-fidelity adoption** follow-on focus — **not** this
mission and **not** closed.
**Out of scope (later focus):** #1832, #1716, #1827, #1619 builder-hardening, the `parent.parent`
repo-root class.

## Assumptions

1. The `branch_naming`/`mid8()` seam and `IdentityFragment` are correct as-is; this mission only routes
   consumers to them (validated by the 2026-06-16 investigation).
2. The mission integrates onto `feat/naming-rider-3-2-1` and that branch is PR'd to `main`; the design
   branch it stacks on is doc-only, minimizing rebase risk.
3. #1993 is **deferred to a follow-on mission** (scope review: its real target is coord-aware and a `resolve_lanes_dir` seam would violate C-001; lanes.json is already centralized).
4. The call-site inventory is **~15** (Phase 0 + the adversarial scope review's 5 additional shapes), not the original ~20 estimate.

## Out of Scope

- The mutable-`ExecutionContext` builder hardening (un-mutate; fix `branch_name ≠ branch_ref.target_branch`).
- The **#2007 read-path/error-fidelity adoption** class (#4/#8/#12/#14/#15 + #2) — the **next named focus**, its own mission.
- The write-side coordination/topology authority (#1716), read-path workspace resolution (#1832), **#1993** (coord-aware `_lanes_feature_dir`), and **#1900** (coord write-side ratchet) — later focus.
- The `feature_dir.parent.parent` repo-root derivation class (~9 sites) — deferred with #1716/#1832.
- Any `--json` surface work (#1891) and the merge-baseline bug (#1827).
- Semantic/AST-semantic detection beyond the best-effort AST slice tripwire — verification-by-deletion is the real guarantee; the ratchet's indirection limit is acknowledged.
