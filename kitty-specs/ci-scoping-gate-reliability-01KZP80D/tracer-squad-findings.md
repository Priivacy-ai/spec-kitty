# Tracer: Post-Plan Squad Findings (architect-alphonso, 2026-08-10)

Authoritative plan-remediation record. `/spec-kitty.tasks` and implementers MUST honor these.

## BLOCKER — fix before /tasks

- **B1 — discrete globs in `on.paths`, NOT brace form.** GitHub `on.pull_request.paths`/`push.paths`
  do NOT support `{a,b}` brace expansion (only `* ** ? + ! []`); dorny filters DO. So in
  `ci-quality.yml` `on.paths`/`push.paths` (:14-30, :44-66) the corpus trigger MUST be discrete lines:
  `kitty-specs/**/spec.md`, `kitty-specs/**/plan.md`, `kitty-specs/**/tasks/**`,
  `kitty-specs/**/contracts/**`, `kitty-specs/**/acceptance-matrix.json`, `packs/**`,
  `.kittify/charter/**`, `.kittify/glossaries/**`, `.kittify/doctrine/**`,
  `.kittify/release/downstream-verified.json`. Brace form would match nothing → #3008 fix inert.

## MAJOR — address in plan/tasks

- **M1 — no double-run via a marker, not whole dirs.** Running whole corpus dirs re-runs suites already
  in fast-tests-doctrine/missions/charter + integration-core-misc (tests/architectural, tests/contract)
  on push + mixed PRs; tests/architectural is huge and mostly non-corpus. Add `@pytest.mark.corpus` to
  the corpus-reading tests and run the `fast-tests-corpus` job with `-m corpus`. (If operator wants
  whole-dir simplicity, NFR-004 must be rewritten to accept overlap — do not claim PASS as-is.)
- **M2 — corpus group follows the `docs` precedent, NOT ci_topology_census.json.** The census is an
  auto-derived src/specify_cli child-dir map (test_ci_topology_worklist asserts census.worklist ==
  live_derived_worklist()); a hand-added corpus row REDS that test. Register corpus like `docs`:
  changes.outputs.corpus row + `corpus:` dorny filter + `fast-tests-corpus` if-gate +
  JOB_GROUPS["fast-tests-corpus"]=["corpus"] + quality-gate.needs edge. Do NOT add to
  src_backed_groups / the unmatched→run_all loop / the census.
- **M3 — #3147 co-evolution must include two more guards + keep the push:main backstop.**
  `tests/docs/test_docs_freshness_invariant.py` statically pins: PR allowlist excludes tests/**+
  kitty-specs/**, and an unfiltered `push: main` backstop MUST exist. FR-005 (retained whole-tree scan)
  IS that existing `docs-freshness.yml:48-49` push:main run (already non-blocking) — RETAIN it; a
  `schedule:` trigger is optional/additive, never a replacement. Also co-evolve
  `tests/docs/test_rulers_blocking.py` (CLI RED-proof for relative_link_fixer/related_validator) to pass
  a base/changed-set and keep the seeded-violation RED green.
- **M4 — add a corpus completeness invariant** (mirror docs-freshness.yml:6-9): assert every committed
  path a corpus-marked test reads is matched by the corpus trigger globs, so a future reader can't
  silently re-open #3008. (Current narrow globs verified to cover all current readers — no blind spot today.)
- **M5 — #3147 base-ref must be explicit + fail-closed.** relative_link_fixer.py (--check, whole docs
  rglob :390) and related_validator.py --strict have NO diff concept. Diff-scope must derive changed
  files from `github.event.pull_request.base.sha` with checkout fetch-depth:0, and FAIL-CLOSED on an
  empty/unresolvable changed-set (empty set must error, never pass trivially). Apply to BOTH scripts.

## NOTE / MINOR

- **N1 — docs-freshness is NOT a required check** (per test_docs_freshness_invariant docstring). #3147's
  over-fire is red-X friction, not a merge block. Do NOT wire docs-freshness into quality-gate.needs
  (a required docs-freshness leaves every non-docs PR pending forever). Spec's uniform "blocking"
  language conflates this with the genuinely-blocking corpus gate — distinguish the two senses.
- **N2 — fast-tests-corpus needs a quality-gate.needs edge** or test_suite_jobs_gate_blocking.py reds
  (pytest-jobs containment; contracts/quality-gate-needs-containment.md). NFR-001 implies it; name it.
- **MINOR-3 — drop `.kittify/skills/**`** (no such dir in this repo). `acceptance-matrix.json` has no
  committed reader (tmp-fixture only) — keep for future-proofing or drop; low stakes.
- **Fold candidate — #3265** (orchestrator-boundary.yml + doctrine-charter-tests.yml lack an unfiltered
  push:main backstop) is the same push-backstop/gate-scoping class; evaluate for fold at /tasks.
  #3127 (fast-tests-status skipped by a needs-gate) is different mechanism → keep separate.

## Verdict
Strategy sound; current narrow globs verified complete. But B1 makes the headline fix inert and M1-M3
leave NFRs unmet / red an arch guard — fold B1+M1-M3 before /tasks; M4-M5+N1-N2 become task acceptance criteria.
