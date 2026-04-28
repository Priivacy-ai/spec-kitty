# Research — Charter E2E #827 Follow-ups (Tranche A)

Research artifact for [plan.md](plan.md). Each section is a discrete engineering decision with rationale and rejected alternatives, per DIRECTIVE_003 and the `adr-drafting-workflow` tactic.

## R1. #848 — drift-check mechanism

**Decision**: Implement the `uv.lock` vs installed-package drift check as a new pytest at `tests/architectural/test_uv_lock_pin_drift.py`.

**Rationale**:
- Architectural-test pattern already exists (`test_shared_package_boundary.py`, `test_pyproject_shape.py`, `test_no_runtime_pypi_dep.py`). Engineering muscle memory and CI plumbing are already in place.
- Pytest runs in both CI and developer-laptop review-gate flows. CI alone (the `clean-install-verification` job) catches drift after-the-fact; a pytest catches it pre-PR.
- The test budget cap (NFR-006 in the shared-package-boundary mission says ≤30s for all architectural tests) easily accommodates one more parser-level test.

**Alternatives considered**:
- *Standalone shell script invoked by review-gate.* Rejected — splits enforcement across two surfaces, and no existing pattern.
- *Pre-commit hook.* Rejected — pre-commit isn't part of this project's review-gate contract; would create an inconsistent enforcement surface.
- *CI-only (no local check).* Rejected — drift creates spurious failures during local review; the test must run pre-PR.

## R2. #848 — sync command

**Decision**: The documented sync command is `uv sync --frozen`. The drift-check failure message includes this command verbatim.

**Rationale**:
- The existing `clean-install-verification` CI job uses `uv sync --frozen` (per CLAUDE.md notes and standard `uv` semantics). Matching that command keeps developers and CI in lockstep.
- `--frozen` is the right semantic: it forces installed packages to match `uv.lock` exactly, which is what FR-001 / FR-002 require.

**Alternatives considered**:
- *`uv sync` (no `--frozen`).* Rejected — `uv sync` may resolve and update `uv.lock` in some configurations, which is not what we want for the drift-correction action.
- *`pip install -r requirements.txt`.* Rejected — project uses `uv`, not `pip`+requirements; would introduce a parallel toolchain.

## R3. #844 — wire field name

**Decision**: Keep both `prompt_file` and `prompt_path` as legal wire field names. Designate `prompt_file` as the **canonical** name. Tighten the contract on whichever field is populated.

**Rationale**:
- Both names already exist in the wire format (see `src/specify_cli/next/decision.py:61` and the existing E2E assertion in `tests/e2e/test_charter_epic_golden_path.py:570` that accepts either).
- Renaming or removing one would be a downstream-breaking change. This mission is scoped to **tighten** the contract, not redesign it.
- The redundancy is harmless once the non-null + on-disk invariant is enforced for `kind=step`.

**Alternatives considered**:
- *Drop `prompt_path`.* Rejected — out of scope; potentially breaks downstream consumers and tests not in this mission's verification matrix.
- *Add a third field name.* Rejected — adds churn without solving the bug.

## R4. #844 — where to enforce non-null + on-disk

**Decision**: Enforce **at envelope construction time** in `src/specify_cli/next/decision.py` (and any peer construction site in `src/specify_cli/next/runtime_bridge.py`). A `kind=step` decision with no resolvable prompt is a programmer error and must be re-routed to `kind=blocked` with a reason.

**Rationale**:
- Putting validation at the construction boundary makes the invariant impossible to violate downstream. The wire format becomes self-consistent by definition.
- Aligns with C-005 ("must not weaken the existing `kind=step` contract by making the prompt field optional").

**Alternatives considered**:
- *Enforce only in the E2E test.* Rejected — closes the test gap but leaves the runtime free to emit illegal envelopes that escape into other consumers (dashboard, downstream agent integrations).
- *Enforce in a serializer post-hook.* Rejected — same blast surface but more indirection.

## R5. #845 — ownership policy

**Decision**: **Exclude** `.kittify/dossiers/<mission_slug>/snapshot-latest.json` from the worktree dirty-state pre-flight (rather than tracking + auto-committing it).

**Rationale**:
- The filename `snapshot-latest.json` is a self-describing mutable-by-design artifact. Tracking it would create churn on every status transition and provide no review value (reviewers would see massive auto-generated JSON diffs in every PR).
- The snapshot is reproducible from the dossier source — `compute_snapshot()` in `src/specify_cli/dossier/snapshot.py:68` is deterministic. A reviewer who needs the snapshot can recompute it.
- Per C-006, we must pick exactly one policy. Exclusion is simpler (one rule, one place) and keeps the worktree clean for actual review-relevant diffs.

**Alternatives considered**:
- *Track + auto-stage + auto-commit on each write.* Rejected — commit churn, review noise, conflicts during merges, and the snapshot file becomes a magnet for spurious history. Would also require a "is this commit substantive?" guard, layering complexity on the very pattern #846 is fixing.
- *Move the snapshot out of the worktree entirely (e.g. into `~/.cache/spec-kitty/`).* Rejected — breaks the `state_contract` declaration at `src/specify_cli/state_contract.py:211` and changes the on-disk layout that downstream tools may depend on.
- *Keep current behavior but add a `--force` flag to `agent tasks move-task`.* Rejected — operator papercut, doesn't actually fix the defect.

## R6. #845 — implementation surface

**Decision**: Belt-and-suspenders: (a) add the snapshot path glob to root `.gitignore`, AND (b) add an explicit path filter in the dirty-state pre-flight code path.

**Rationale**:
- `.gitignore` alone covers the common case (ad-hoc human `git status`, default `git status --porcelain`).
- Some pre-flight code paths read git state in ways that may bypass `.gitignore` (e.g. `git diff --quiet` on a specific path, or in-process diff against the index). The explicit filter is the airtight version.
- Together they form a small, easy-to-review change that closes the regression without leaving holes.

**Alternatives considered**:
- *Only `.gitignore`.* Rejected — risks a code path that ignores it.
- *Only explicit filter.* Rejected — leaves the file showing up in `git status` for humans, which is its own UX bug.

## R7. #846 — substantive-content definition

**Decision**: A spec/plan file is "substantive" iff **either**:
- (a) the file's byte-length exceeds the canonical scaffold's byte-length by a fixed threshold (default: 256 bytes), **or**
- (b) the file contains all of a small, hard-coded list of required mandatory sections for that artifact (spec: a non-empty Functional Requirements table with at least one row; plan: a non-empty Technical Context section).

**Rationale**:
- The OR makes it permissive enough not to false-block legitimate small specs while still catching the empty-scaffold case.
- Both checks are deterministic and cheap (file read + cheap parse).
- The byte-length check is robust to template changes; the section check is robust to abbreviated specs that happen to be near the threshold size.

**Alternatives considered**:
- *Pure byte-length threshold.* Rejected — false-blocks legitimately small specs near the threshold.
- *Pure section-presence check.* Rejected — couples the gate to a specific section structure that may evolve; also brittle if a future template renames sections.
- *Hash equality with the scaffold.* Rejected — too strict; any whitespace edit would pass even when content is still scaffold-like.
- *AI/LLM judgement of "is this substantive".* Rejected — non-deterministic, expensive, off-pattern for a CLI guard.

## R8. #846 — where to gate auto-commit

**Decision**: Gate the auto-commit at the same code path that performs the auto-commit today (in `src/specify_cli/cli/commands/agent/mission.py`, around `setup-plan` and the equivalent specify path). The gate is a single conditional: `if not _is_substantive(file_path, kind): emit_blocked_status_and_skip_commit(); return`.

**Rationale**:
- One gate, one place. Easiest to reason about and test.
- Workflow status (the JSON returned to the calling agent) reflects the gated state, so downstream tools see "incomplete" rather than "ready".

**Alternatives considered**:
- *Block at template render time.* Rejected — too early; the template render is intentionally permissive.
- *Block at a separate `validate-content` CLI subcommand.* Rejected — adds a step the agent might skip.

## R9. Test coverage strategy

**Decision**: For each issue, add **one regression test that exercises the exact pre-existing failure path** plus any contract assertions the spec mandates.

**Rationale**:
- Per FR-011 and FR-015 the spec explicitly requires "regression coverage for the exact pre-flight path that used to block" and "regression coverage or workflow documentation". One targeted test per issue keeps the suite focused and the failure messages diagnostic.
- Architectural test for #848 doubles as both regression and live enforcement.

**Alternatives considered**:
- *Property-based / fuzz testing.* Rejected — overkill for these defects; would slow the test suite.
- *Snapshot/golden tests of full envelopes.* Rejected — coarse; failure modes wouldn't pinpoint the regression.

## R10. PR closeout mechanics

**Decision**: PR body includes the four `Closes #...` lines, the `#847 out of scope` note, the `#827 remains open` note, and the `PR #855 was superseded` note. This is enforced socially (FR-016 in spec), not mechanically — no code-level enforcement.

**Rationale**:
- These are PR-body conventions, not runtime invariants. Mechanizing them would creep beyond mission scope (C-004 spirit: stay narrow).
- The mission-review checklist will catch a missing line during human review.

**Alternatives considered**:
- *Add a CI check that scans the PR body for required strings.* Rejected — out of scope; would touch CI workflow surface.
- *Pre-commit hook.* Rejected — same reason; not how this project enforces PR-body content.

## R11. Doctrine doc scrub for #844

**Decision**: Walk `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and any inline comment that says "advance mode populates this" (`src/specify_cli/next/decision.py:79`) and replace with text that explicitly says null is illegal for `kind=step`.

**Rationale**:
- FR-008 mandates removal of host-facing text legitimizing null prompts. The doctrine SKILL is the host-facing surface.
- Inline comment is also visible to anyone reading the source; updating it removes a future foot-gun.

**Alternatives considered**:
- *Leave the inline comment, only update SKILL.* Rejected — the inline comment is the more dangerous foot-gun; future contributors read the source.

## Open questions (none deferred)

No `[NEEDS CLARIFICATION]` markers were emitted during planning. All 11 decisions above are made with documented rationale. If any decision is later challenged, the alternatives table is the place to renegotiate.
