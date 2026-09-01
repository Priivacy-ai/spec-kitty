# Post-Merge Fidelity Audit — findings & dispositions

**Date:** 2026-08-23. **Branch:** `pr/doctrine-drg-silent-drop-boundary` (clean 6-commit
rebase on upstream/main). **Squad (profile-loaded, read-only):** reviewer-renata
(FR-coverage), doctrine-daphne (DRG drift/dead-code), debugger-debbie (adversarial
claims-vs-reality).

## Outcome verdict: PASS — closing claims hold

All 13 FRs satisfied by shipped code with non-fakeable tests (behaviour pins,
divergent-fixture data-moving branches, count pins, real `generate_graph` e2e).
Golden `agent_profile.graph.yaml` byte-fresh; doctor healthy; SSOT consistent;
migration lossless + idempotent; no new drift. #3608/#3629/#3530 genuinely
delivered on the production path.

## Findings & dispositions

| # | Finding (lens) | Sev | Disposition |
|---|----------------|-----|-------------|
| A1 | **`assert_governance_scope_resolves` guard is dead/shadowed in production** — strict subset of `validate_dangling_references`, which `load_validated_graph` already runs; operator never sees its specialized message; no caller injects a graph. Fail-loud actually delivered by edge-minting + the pre-existing check. (debbie) | MED | **fixed** (operator decision) → removed the guard + both call sites (`validator.py`, `executor.py`, `action_doctrine_bundle.py`); rewrote `test_org_governance_failloud.py` to assert org-tier fail-loud via the **production path** (`DRGValidationError`). Commit `f16193035d`. The mission is now dead-code-honest. |
| A2 | **Two SKILL.md sources still list "6 sections: context_sources"** (`spec-kitty-charter-doctrine/SKILL.md:414`, `spec-kitty-mission-system/SKILL.md:327`) — the exact stale-doc anti-pattern the mission targets. (daphne) | MED | **fixed** → both updated to the `*-references` surface + note the retired block. |
| A3 | **Stale #3658 CHANGELOG line** claims the context-sources deprecation is "tracked separately as its own bulk-edit mission" — this mission did it. (renata via review-first) | MED | **fixed** → reconciled to point at this mission + the Breaking entry. |
| A4 | C-006 contract **prose** names only the pedro/034 delta; true ledgered delta is **3 edges** (pedro/034 + 2 diagram-daisy toolguide `suggests`). Code/test/ledger already consistent; only prose under-described. (all three) | LOW | **fixed** → contract updated to name all 3 edges + reachability-neutral note. |
| A5 | Migration `_summarise` reports dropped **count** not **id** — an author who set a custom `additional:`/`doctrine-layers:` binding can't see which id was dropped. (debbie) | LOW | **fixed** → `_summarise` now names each dropped `key:value`. |
| A6 | Bare `# noqa: ARG002` on `can_apply` lacks an inline rationale (charter requires justified suppressions). (renata) | LOW | **fixed** → rationale comment added. |
| A7 | `schema_models.py:223-232` stale "Section 3…6" numbering after Sections 1–2 removed. (daphne) | LOW | **noted** — cosmetic comment numbering; left for a future touch (no behaviour/doc-consumer impact). |
| A8 | `charter/context_renderers/fetch_stanza.py::_VALID_SELECTOR_KINDS` is another hand-literal kind set — but it is **permissive** (fails open on unknown kinds), not a silent-drop gate of the #3608 class. (debbie) | LOW | **noted** — out of scope (different, non-silent surface); candidate for a separate whack-a-copy follow-up (family #3562/#3461/#3427). |
| — | acceptance-matrix.json boilerplate TODO notes (evidence fields are real). (renata) | LOW | **noted** — mission-artifact cosmetic; no shipped-code impact. |

## Net effect on the PR

One code commit (A1 dead-guard removal) + one docs/nits commit (A2–A6). A7/A8 and
the acceptance-matrix cosmetic are recorded as accepted debt / follow-up candidates,
not blockers. Tests green throughout.
