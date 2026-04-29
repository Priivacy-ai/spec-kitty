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

## R7. #846 — substantive-content definition (REVISED)

**Original decision (REJECTED in planning review)**: byte-length-delta-vs-scaffold OR section-presence.

**Reason for revision**: review caught that the byte-length OR could pass `scaffold + 300 bytes of arbitrary prose` as "substantive", which recreates the failure mode this mission exists to fix. A user can paste a paragraph of unrelated text and the gate would commit. That is exactly the silent-commit-of-non-spec-content bug, just with more bytes.

**Revised decision**: A spec/plan file is "substantive" iff it contains the required mandatory sections for that artifact, AND those sections contain real (non-template-placeholder) content.

- **spec**: at least one Functional Requirements row with an `FR-\d{3}` ID followed by description content that survives `[NEEDS CLARIFICATION …]` / `[e.g., …]` stripping.
- **plan**: a populated Technical Context section where `Language/Version` (and at least one peer field) contains a real value, not a template placeholder.

**Rationale**:
- Section-presence with placeholder-stripping is the precise signal we actually care about. A spec without an FR row is, by definition, not a spec.
- Resilience to template evolution: if a future template renames "Functional Requirements" to something else, the gate fails LOUDLY (clear regression to fix), not silently (passing scaffolds).
- Cheap and deterministic: regex parse over the file body.

**Alternatives reconsidered**:
- *Pure byte-length threshold.* Rejected (was rejected before, still rejected).
- *Byte-length OR section-presence.* **Now rejected** — recreates the failure mode with arbitrary filler.
- *Byte-length AND section-presence.* Rejected as redundant — section-presence alone is sufficient. Adding a length AND-gate would only false-reject edge cases where a one-FR-row spec is shorter than the scaffold (very rare, but possible if the scaffold is verbose).
- *Hash equality with the scaffold.* Still rejected — too strict.
- *AI/LLM judgement.* Still rejected — non-deterministic.

**Implication for tests**: the regression test must assert that scaffold + 300 bytes of arbitrary prose (no FR row) is **NON-substantive**. This was previously documented as a "this commits" case in the contract; that test scenario is removed and replaced with the stricter assertion.

## R8. #846 — where to gate auto-commit (REVISED)

**Original decision (REJECTED in planning review)**: single gate at the existing `setup-plan` auto-commit branch in `mission.py`.

**Reason for revision**: review caught that there is **no Python auto-commit branch for the populated `spec.md`** today. The slash-template `/spec-kitty.specify` instructs the agent to commit substantive `spec.md` content; that commit happens outside Python. The Python-side bug is at **`mission create`** (which auto-commits the empty `spec.md` scaffold), not at any specify-side commit branch. A gate placed only at `setup-plan` would let the empty-scaffold commit through.

**Revised decision**: gate at THREE places, all in `src/specify_cli/cli/commands/agent/mission.py`:

1. **`mission create`**: stop including `spec.md` in the create-time `safe_commit(files_to_commit=[…])` call. Empty scaffolds remain untracked at create time.
2. **`setup-plan` entry**: check `is_committed(spec, repo) AND is_substantive(spec, "spec")`. If false, emit `phase_complete=False / blocked_reason` and return without writing or committing `plan.md`.
3. **`setup-plan` exit**: gate the existing `_commit_to_branch(plan_file, …)` call on `is_substantive(plan, "plan")`.

**Rationale**:
- The `mission create` change alone doesn't enforce FR-014 (workflow state doesn't falsely advance). The setup-plan entry check is what surfaces "spec phase not yet complete" to downstream tools.
- The exit check is needed because today's `setup-plan` writes `plan.md` from a template, and an empty-but-template-only `plan.md` is exactly the failure mode for the plan side.
- Three small surgical changes are easier to review and test than one monolithic gate.

**Alternatives considered**:
- *Single gate at setup-plan entry only.* Rejected — leaves the create-time commit of empty `spec.md` in place, surfacing as `git log` clutter and creating reviewer noise. Also doesn't cover the `plan.md` template-only case.
- *Refactor `mission create` to delay scaffold commit until the slash-template's first commit*. Rejected — invasive; the right fix is just to omit `spec.md` from the existing scaffold-commit list.
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
