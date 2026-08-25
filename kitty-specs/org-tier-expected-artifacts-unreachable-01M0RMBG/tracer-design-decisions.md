# Tracer: Design Decisions — org-tier-expected-artifacts-unreachable-01M0RMBG

Seeded during the plan phase (author subagent), per charter Standing Order #3.

## The gate set

I did not accept the candidate gate list from the task prompt at face value — I read the
actual workflow YAML (`ci-quality.yml`, `doctrine-charter-tests.yml`, `module-kernel.yml`) to
find each gate's real scope before writing the plan's Gate Set section. Two findings changed
what I wrote versus what a lazier pass would have produced:

1. **"Kernel coverage ≥90%" does not apply**, but there IS a real, applicable 90% floor —
   just not the one named in the candidate list. `module-kernel.yml`'s 90% gate is scoped
   strictly to `src/kernel/**`; `src/charter/` is a sibling package with its own, separate 55%
   floor inside `fast-tests-charter`. But the PR-only `diff-coverage` job lists `src/charter/*`
   explicitly in its `critical_paths` array and enforces `--fail-under=90` on changed lines
   there. I judged this worth calling out precisely — not just "kernel floor doesn't apply, so
   ignore 90%" — because the mission's actual implementation commit (FR-001/FR-002, inside
   `src/charter/org_expected_artifacts.py`) IS subject to a real 90%-on-changed-lines
   obligation, and a shallower pass could have missed that by only checking the "kernel"
   framing and stopping there.
2. **`ruff check` full-report is genuinely advisory** (labeled `[INFO] ... (advisory)` in the
   workflow itself), but TID251 (a narrower `ruff --select TID251` invocation inside the same
   `lint` job) is separately `[ENFORCED]`. I split these into "excluded" and "included"
   respectively rather than treating "ruff" as one undifferentiated line item, because
   collapsing them would have either wrongly excluded a real enforced gate or wrongly included
   an advisory one as a blocker.

## Campsite-clean verdict: didn't

I read all six files (full file for the production module; the cited line ranges plus
surrounding context for each test file) specifically looking for something genuinely
domain-matched to clean — an over-long function, a Sonar-flaggable pattern, dead code near the
touched lines. I found none. `org_expected_artifacts.py` is 120 lines total across two small
functions, already has its one repeated literal hoisted to a module constant, and its single
`except` clause already does real work (log + return `None`, not a bare pass). The test files'
fixture helpers are 8-14 lines each and single-purpose. I state this as an explicit "no
campsite-clean needed" finding in the plan rather than a silent omission, per the mission
briefing's own instruction not to invent busywork — inventing a refactor here would have been
scope creep dressed as diligence, and the charter's `RECONCILE_CHANGE_SCOPE_TENSIONS` doesn't
reward padding.

## WP phasing order: why RED-first for FR-001/002/003's new case but not FR-003/004/005's
maintenance corrections

This is not my own invention — NFR-001 in spec.md draws the line explicitly, and I carried it
forward rather than re-deriving a different split. The underlying logic, as I understand it
having read the full spec: RED-first is a tool for pinning *new, previously-absent*
user-observable behavior (a pack at the correct anchor now resolves; a pack at the old anchor
now correctly resolves to `None`) — you want a reviewer to see the test fail against the
unfixed code and pass against the fixed code, proving the fix does what it claims. The
FR-003/004/005 fixture-helper corrections don't pin new behavior at all — they keep *existing,
already-passing* tests passing through an anchor move that would otherwise break them for a
reason unrelated to what they're actually testing (a fixture I/O detail, not the assertion
under test). Forcing a RED-first commit for those would be theater: the "RED" would be "test
fails because its fixture writes to the wrong directory," which proves nothing about the
resolver's correctness, and NFR-001's own text says as much by naming this exclusion directly
rather than leaving it for a plan-author to guess at. I sequenced the maintenance commit(s) to
land strictly after the FR-001/FR-002 implementation commit rather than before or interleaved,
so that in code review, the maintenance diff reads as a straightforward "keep these five
fixtures consistent with the anchor the prior commit just moved" — the causal order in the
commit log matches the causal order of the actual defect.
