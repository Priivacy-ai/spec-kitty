---
work_package_id: WP09
title: Canonical Glossary Term Check
dependencies: []
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: feat/docs-ia-onboarding-overhaul
merge_target_branch: feat/docs-ia-onboarding-overhaul
branch_strategy: Planning artifacts for this mission were generated on feat/docs-ia-onboarding-overhaul. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-ia-onboarding-overhaul unless the human explicitly redirects the landing branch.
subtasks:
- T038
- T039
agent: "claude:sonnet-5:python-pedro:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_glossary_canonical_terms.py
create_intent:
- tests/architectural/test_glossary_canonical_terms.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- tests/architectural/test_glossary_canonical_terms.py
role: implementer
tags: []
shell_pid: "77304"
shell_pid_created_at: "1784568171.345081"
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read, in order:
[spec.md](../spec.md) FR-013, [plan.md](../plan.md) §IC-07, [research.md](../research.md) item
5, [contracts/canonical-term-check-contract.md](../contracts/canonical-term-check-contract.md),
and `tests/architectural/test_no_legacy_terminology.py` in full — your new test must mirror its
structural conventions exactly (marker triple, exclusion pattern, `git grep`-based scan, repo
root resolution).

## Objective

Build a standing architectural test that flags any documentation page using a glossary term in
a non-canonical spelling or casing, sourced from the real 104-term
`.kittify/glossaries/spec_kitty_core.yaml` seed — not a hardcoded list. This is the "lighter
check now" scope the user explicitly confirmed (canonical-form checking only; full
alias/banned-synonym governance is deferred, see WP10's follow-up issue and spec.md C-003).

## Context

- `test_no_legacy_terminology.py` is the structural precedent, but checks a small, unrelated,
  hardcoded 2-term denylist. This new test is a **sibling**, not an extension — do not add your
  logic into that file; different data source, different failure semantics (per research.md
  item 5's explicit rationale for keeping them separate).
- Marker triple to reuse exactly: `pytest.mark.architectural`, `pytest.mark.git_repo`,
  `pytest.mark.docs_scoped`.
- Scan roots: `docs/` per the contract (this test does not need to cover `src/`/`tests/` the way
  the legacy-terminology guard does — glossary terms are a docs-content concern).
- The `docs/adr/` exemption pattern from `test_no_legacy_terminology.py` (immutable historical
  snapshots) likely applies here too — glossary-term casing inside a quoted historical ADR body
  shouldn't fail this check. Reuse the same exclusion-fragment approach.

## Subtask guidance

- **T038 — Write the test.** Load `.kittify/glossaries/spec_kitty_core.yaml`'s 104 `surface`
  values. For each, `git grep` (case-insensitive) across `docs/` (excluding `docs/adr/`,
  `kitty-specs/`, and other fragments matching `test_no_legacy_terminology.py`'s exclusion
  list) for occurrences of that term's text. For each hit, compare the matched text's exact
  casing/spelling against the canonical `surface` value (case-SENSITIVE comparison after
  normalizing whitespace, per the contract). Flag any mismatch. Assemble failures into one
  assertion message listing every flagged `{file}:{line}: found "{actual}", expected canonical
  form "{surface}"`, matching the contract's exact output shape. Apply the same three markers as
  `test_no_legacy_terminology.py`.
- **T039 — Run and record findings.** Run
  `pytest tests/architectural/test_glossary_canonical_terms.py -v` against the current `docs/`
  tree (as it stands after WP01-WP08's changes land, if you're running late in the sequence —
  if running early/in-parallel, note that pre-existing docs content may trigger findings that
  are not this WP's problem to fix). Record the raw output in this WP's Activity Log. Do NOT fix
  any flagged occurrence here — that's WP10's job (the terminology sweep), which runs last and
  owns the fix pass across everyone's combined output. Your job is only to prove the check
  itself works correctly (e.g. verify it correctly does NOT flag a term used in its exact
  canonical form, and DOES flag a deliberately miscased test string if you inject one
  temporarily to prove the check fires, then remove the injected string).

## Branch Strategy

Planning artifacts were generated on `feat/docs-ia-onboarding-overhaul`. This WP branches from
that base during `/spec-kitty.implement` and merges back into `feat/docs-ia-onboarding-overhaul`.
No dependencies — starts immediately, independent of the content/nav work.

## Definition of Done

- [ ] `tests/architectural/test_glossary_canonical_terms.py` exists, sourcing terms from the
      real glossary seed (not hardcoded).
- [ ] Marker triple matches `test_no_legacy_terminology.py` exactly.
- [ ] `docs/adr/` (and other established exclusions) are exempted, matching the existing
      pattern.
- [ ] The test correctly fires on a deliberately-miscased injected string and correctly does
      NOT fire on canonically-cased text (proven during T039, injected string removed after).
- [ ] Raw findings from a real run against current `docs/` are recorded in the Activity Log for
      WP10's reference.

## Risks & Mitigations

- **False positives from term/prose overlap**: a glossary term like "mission" is a very common
  English word — a naive substring match will produce enormous noise. Consider whether the
  contract's intent implies matching only when the FULL multi-word `surface` phrase appears (not
  fragments of single common words) — read the contract's exact wording again if unsure, and if
  genuinely ambiguous, favor precision (fewer false positives) over recall, and note the
  trade-off explicitly in this WP's Activity Log for the human reviewer to weigh in on.
- **Self-flagging**: like the legacy-terminology test, ensure this test file itself doesn't
  trigger against its own docstrings/comments if it happens to mention a glossary term.

## Review Guidance

- Run the test yourself against current `docs/` and sanity-check a sample of any flagged
  occurrences — are they real casing mismatches, or false positives from the matching strategy?
- Confirm the CI marker triple is byte-identical to `test_no_legacy_terminology.py`'s.

## Activity Log

- {{TIMESTAMP}} – system – Prompt created.
- 2026-07-20T16:38:03Z – claude:sonnet-5:python-pedro:implementer – shell_pid=64953 – Assigned agent via action command
- 2026-07-20T16:52:53Z – claude:sonnet-5:python-pedro:implementer – shell_pid=64953 – T038/T039: Wrote tests/architectural/test_glossary_canonical_terms.py, sourcing terms from the live 104-term .kittify/glossaries/spec_kitty_core.yaml seed via the canonical glossary.scope.load_seed_file loader. Marker triple pytest.mark.architectural/git_repo/docs_scoped matches test_no_legacy_terminology.py byte-for-byte. Scope decision: only multi-word surface values (63 of 104) are scanned, single-word terms (e.g. 'mission', 'build', 'charter') excluded to avoid prose-noise false positives -- pinned by test_single_word_terms_are_excluded_from_scan and documented in the module docstring for human review. docs/adr/ exempted as historical snapshots (same rationale as the legacy-terminology test). Proved fire/no-fire behavior via direct unit tests of the pure _flagged_occurrences matcher (test_term_pattern_does_not_flag_canonical_form / test_term_pattern_flags_miscased_occurrence) rather than staging a real docs/ fixture file, avoiding repo churn. Ran pytest tests/architectural/test_glossary_canonical_terms.py -v against the live docs/ tree: 6 passed (unit/logic tests), 1 failed (test_glossary_terms_use_canonical_casing) with 272 flagged non-canonical-casing occurrences across docs/ as it stands pre-WP10 (dominant patterns: 'Work Package' vs 'work package', 'Agent Skills' vs 'agent skills', 'Feature Branch' vs 'feature branch', 'Step Contract' vs 'step contract'). This is expected exploratory signal for WP10's terminology sweep, not fixed here per WP09 scope. ruff check and mypy both pass with zero issues; pytest --collect-only and -m architectural both correctly select the new test.
- 2026-07-20T16:53:28Z – claude:sonnet-5:python-pedro:implementer – shell_pid=64953 – Ready for review: new tests/architectural/test_glossary_canonical_terms.py sourcing 63 multi-word terms from the live 104-term glossary seed; 6 unit tests pass, main scan flags 272 real casing occurrences in docs/ (informational for WP10). ruff/mypy clean.
- 2026-07-20T17:22:53Z – claude:sonnet-5:python-pedro:reviewer – shell_pid=77304 – Started review via action command
- 2026-07-20T17:28:05Z – user – shell_pid=77304 – Review passed: verified test_glossary_canonical_terms.py mirrors test_no_legacy_terminology.py's marker triple/exclusion/repo-root conventions exactly; independently re-ran pytest (6 passed, 1 failed with 272 flagged occurrences, matching self-report exactly), mypy (clean), ruff (clean); spot-checked flagged occurrences against the glossary seed and confirmed real casing mismatches, not false positives; confirmed single-word exclusion is documented and pinned by a test; confirmed docs_scoped marker coverage test and marker-registry test pass; diff touches only the owned file.
