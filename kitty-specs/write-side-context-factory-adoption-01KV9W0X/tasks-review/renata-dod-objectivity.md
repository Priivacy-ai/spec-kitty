# reviewer-renata — Mission B WP decomposition: DoD-objectivity / acceptance audit

**Profile:** reviewer-renata (loaded from `src/doctrine/agent_profiles/built-in/reviewer-renata.agent.yaml`).
**Lens:** acceptance objectivity / requirement coverage / reviewer-actionability. I review code; here I am
reviewing whether each WP is *objectively acceptable-or-rejectable as written*, BEFORE implementation.
**Mission:** `write-side-context-factory-adoption-01KV9W0X` · branch `feat/write-side-context-factory-adoption`.
**Date:** 2026-06-17.

Overall this is a strong, disciplined decomposition — verification-by-deletion is operationalized, the
keystone (NFR-006) has its own WP, idempotency is named per-WP, and the highest-risk WP (WP05) has a genuinely
strong reviewer-failure-mode list. The gaps below are about a few DoD items that are still *asserted* rather
than *told-how-to-prove*, two coverage holes, and the issue-matrix not yet being review-ready. None of the
blockers are about the *strategy* — they are about making the acceptance bar mechanical so a weak
implementation gets rejected, not waved through.

---

## BLOCKER

### B-1 — Issue-matrix has no per-issue verdict plan; the approve/done gate will block later (coverage / gate-readiness)
`issue-matrix.md` is a stub: every one of the 15 issues (#2015/#1716/#1878/#1619/#2007/#1970/#2017/#2016/
#1993/#2000/#2012/#2010/#2011/#1832/#2004) is `Verdict: unknown` with `<fill at WP-implementation time>` and
no title. The `in-mission` verdict the spec relies on (#1716 bounded slice, #1619 increment, #1993 FR-008)
**must reach a terminal verdict before mission `done`** (the matrix's own footer says so). As written, nothing
in the WP set produces those verdicts: no WP DoD says "update issue-matrix row #X to verdict Y with evidence
ref." The spec's matrix (spec.md §Tracker) already *states the intended disposition per issue* (in-mission /
deferred-with-followup / verified-already-fixed) — but that intent never propagates into the gating
`issue-matrix.md`, and no WP owns closing it.
- **Remediation:** (a) Pre-fill `issue-matrix.md` now from the spec's Tracker table — each row gets its
  title and its *intended* verdict (e.g. #1716 → `in-mission`, #1878 → `deferred-with-followup`, #2016/#2000 →
  `verified-already-fixed`, #1993 → `in-mission`). (b) Add an explicit DoD line to **WP08** (the integration
  keystone, last WP): "Update `issue-matrix.md`: every row reaches a terminal-or-`in-mission` verdict with an
  evidence ref (commit/PR/test). #1716/#1619/#1993 = `in-mission` justified by the landed adoption; the
  `verified-already-fixed` rows cite Mission A commits (`d4f0cf581`, naming-rider #2012)." Without an owning
  WP, the matrix stays `unknown` and the accept gate stalls.

### B-2 — `acceptance-matrix.json` is entirely placeholder ("TODO: replace with a real acceptance criterion")
All 9 criteria are `"Verify FR-00X is satisfied"` / `proof_type: automated_test` / `notes: TODO`, and
`negative_invariants: []`. The mission's whole value proposition is *negative/idempotency* invariants
(NFR-004 no on-disk churn, C-007 never-flatten-to-primary_root, NFR-006 zero-coord-paths-touched) — exactly
the things that belong in `negative_invariants`, and they are empty. A reviewer at accept time has no concrete
oracle to check FR-by-FR; the descriptions are tautological.
- **Remediation:** Replace each criterion with the concrete proof the WP already names — e.g. FR-001 →
  "WP01 net + `tests/status/` green after `.parent.parent` deletion; lock-root value equality row passes";
  FR-004 → "WP01 FR-004 oracle flips RED→green; before/after on-disk-target idempotency test passes";
  NFR-006 → "WP08 keystone: every fragment==base, zero `.worktrees/` paths, write-target==target_branch."
  Populate `negative_invariants` with: (i) no on-disk worktree/coord path changes before/after an adopted
  write; (ii) status surface never resolves to `primary_root` under coord topology; (iii) zero coord/lane
  paths read or written in the all-base case. These are the bars that make a weak impl *rejectable*.

---

## SHOULD-FIX

### S-1 — WP08 (keystone) "byte-identical to the pre-lane flat path" is not given a concrete oracle
WP08 DoD says "behavior byte-identical to the pre-lane flat path" and "every fragment == base; ZERO
`.worktrees/`/coord paths touched." The fragment-equality and zero-coord-paths parts are checkable. But
**"byte-identical to the pre-lane flat path" has no defined baseline** — there is no captured pre-lane
artifact to diff against, and "pre-lane" code no longer exists to run. As written a reviewer cannot
objectively confirm or refute it; it will be accepted on the implementer's say-so. This is the keystone /
operator-binding requirement (NFR-006) — its bar must be the strongest, not the vaguest.
- **Remediation:** Make the bar mechanical. Replace "byte-identical to the pre-lane flat path" with the
  *observable* equivalents the test can actually assert: (1) every adopted fragment (root, placement, status
  surface, lanes-dir, write-target) `== base`/`target_branch`; (2) the status event JSONL written in the flat
  case is *shape-identical* (assert the event dict keys/values, not a vague "byte-identical"); (3) a
  filesystem watcher / path-set assertion proves **no path under `.worktrees/` or any coord-surface dir is
  read or written** (this is the concrete proxy for "as it used to be"). Drop the un-anchored "byte-identical
  to pre-lane" phrasing or define exactly which captured baseline it diffs.

### S-2 — Idempotency DoD (WP04/WP05/WP06) tells *what* to prove but only WP04 tells *how* (capture/assert-equal)
The standing note flagged this: are WP04/05/06 told to capture-before, capture-after, assert-equal — or just
asserted? Reading them:
- **WP04** is good: T019 explicitly says "asserting the resolved `feature_dir` ... is byte-identical to the
  pre-adoption value for a given `(worktree_path, branch_name)`" and the reviewer guidance says "Confirm via
  the before/after assertion, not by inspection." This is the model the others should match.
- **WP05** T025 says "before/after on-disk-target idempotency ... the coord case writes to the SAME on-disk
  target as before" — *what* is clear, but "as before" has no captured baseline named. A pre-adoption HEAD is
  on the dependency branch; the test can't trivially run both. The reviewer guidance ("the idempotency
  before/after is asserted, not inspected") is right, but the WP doesn't tell the implementer HOW to establish
  the "before" oracle. WP01's T002/T003 *characterization* rows are the intended "before" snapshot — but WP05
  never says "the before value is the frozen WP01 oracle row." That link is load-bearing and implicit.
- **WP06** T029 says "lanes.json on-disk location unchanged for the coord case" and points at WP01's S-8
  oracle — better than WP05, but still doesn't say "assert against the frozen S-8 value."
- **Remediation:** In WP05 T025 and WP06 T029, state explicitly: "The 'before' value is the frozen WP01
  characterization oracle (T002/T003 for WP05; S-8 for WP06); the adoption test asserts the post-adoption
  resolved target/path `==` that frozen oracle value. Do not re-derive 'before' by running pre-adoption code."
  That turns "idempotent" from a claim into a diff against a named constant.

### S-3 — WP05 "surface never resolves to primary_root under coord" — concrete check is implied, not spelled out
The standing question. WP05 reviewer guidance #1 says: "the surface NEVER resolves to `primary_root` under
coord topology (C-007 — a flatten here is the #2004/#2007 regression)." That names the failure mode (good),
but the *check* is left to the reviewer to invent. The DoD line ("surface → `status_surface.status_write_dir`
(coord authority, never `primary_root`, C-007)") asserts the property without a positive assertion the test
must contain.
- **Remediation:** Add to WP05 T025 / DoD: "The D-5 equivalence test MUST contain a *positive* assertion under
  the coord fixture: `resolved_status_write_dir == <coord feature dir>` AND `resolved_status_write_dir !=
  workspace.primary_root` (they differ under coord topology — if they're equal the fixture isn't materializing
  a coord worktree, which is itself a failure)." A bare "never primary_root" is unfalsifiable if the fixture
  silently collapses; the `!=` assertion plus a `==coord-dir` assertion makes it objective.

### S-4 — NFR-006 maps ONLY to WP08, which hard-depends on WP05 (the thing it guards) — gate ordering risk
Coverage-wise NFR-006 → WP08 is correct. But D-2/D-7 state the keystone is *the guard that makes the FR-004
write-target flip (WP05) safe*, while WP08 `dependencies: [WP02..WP06]`. So the risky write-target lands and
can be **approved in WP05 before its binding guard exists** (WP08 is later). If WP05 is approved and WP08 then
surfaces a flat-collapse failure, WP05's approval was premature. The reviewer of WP05 has no in-WP keystone to
lean on.
- **Remediation:** Either (a) add to WP05 DoD an *inline* minimal flat-case assertion ("the flat arm of the
  D-5 equivalence test asserts write-target == `target_branch`, not git HEAD — SC-008 flat arm — proven within
  WP05, with WP08 the full integration keystone"), so WP05 carries its own flat-arm proof; or (b) make the
  WP05 reviewer guidance explicitly state "do not approve WP05's FR-004 flip until the flat-arm write-target
  assertion is green *in this WP*; WP08 is the integration keystone, not WP05's only guard." WP05 T023 mentions
  the flat arm but the DoD doesn't bind it as an acceptance gate.

### S-5 — FR-007 "second-factory reduction" lacks an objective acceptance bar (how much reduction is enough?)
WP05 covers FR-007 ("Reduce `_identity_for_request` ... to consume the projection; defer S2"). DoD: "
`_identity_for_request` reduced to consume the projection (FR-007); S2 ladder untouched." "Reduced" is
subjective — an implementer could consume the projection in one spot and leave most re-derivation, and a
reviewer couldn't objectively reject it. The boundary between "the bounded covered portion" and "the deferred
S2 ladder" is described in prose (research) but not as a checkable line.
- **Remediation:** Give FR-007 a concrete bar: "After WP05, `_identity_for_request` contains NO inline
  `feature_dir.parent.parent`, NO inline `coord_branch or _current_branch`, and NO inline `mission_id[:8]`/
  `mid8` recompute (these now come from fragments); the ONLY remaining re-derivation is the named S2 ladder
  (`_read_contract_from_transaction_target`), which the FR-005 ratchet (WP08) allow-lists by name." That makes
  "reduced enough" a grep-able assertion and ties it to the ratchet allow-list — objective accept/reject.

---

## NIT

### N-1 — WP06 title is truncated in frontmatter: `title: Lanes/coord adoption (FR-008,`
The YAML `title` ends mid-parenthesis (`(FR-008,`). Cosmetic, but it will render oddly in dashboards/status.
Fix to `Lanes/coord adoption (FR-008, #1993)`.

### N-2 — WP01 FR-004 oracle: "RED-on-HEAD or xfail or captured baseline" leaves the witnessing form optional
WP01 T002 offers three ways to witness the FR-004 divergence (RED test / xfail / captured baseline). All three
are legitimate, but a reviewer accepting WP01 needs ONE chosen form to verify "the oracle exists." Suggest the
DoD pin the preferred form (captured-baseline-asserted-equal-to-current-wrong-value is the most robust, since
a literal RED test makes WP01 itself red and complicates its own acceptance). Minor — the intent is clear.

### N-3 — SC→WP traceability is implicit; SC-002 ("0 readers → load-bearing") has no single owning verification
Every SC has a producing WP (SC-001/008→WP02/05, SC-004→WP07, SC-005→WP04/05/06, SC-007→WP08, SC-009→WP09),
which is good. SC-002 (the three fragments go 0-readers→load-bearing) is asserted across WP02+WP05 but no WP
DoD says "re-run the census / grep that these three fragment fields now have ≥1 live reader." It's *implied* by
verification-by-deletion but not an explicit check. Optional: add a one-line census re-confirmation to WP08's
integration step.

---

## Coverage confirmation (the parts that ARE clean)
- **FR-001..009 all map to a WP** (tasks.md coverage table + each WP's `requirement_refs` frontmatter agree):
  FR-001→WP02/03/05, FR-002→WP04, FR-003/004/007→WP05, FR-005→WP08, FR-006→WP07, FR-008→WP06, FR-009→WP09. No
  orphan FR.
- **NFR-001/002** → enabled by WP01 (net + topology-true fixtures); **NFR-003** verification-by-deletion is
  in every adoption WP DoD; **NFR-004** idempotency is named in WP04/05/06; **NFR-005** ruff/mypy≤15 is in
  every WP; **NFR-006** → WP08. No orphan NFR (but see S-2/S-4 on *how* NFR-004/006 are proven).
- **SC-001..009** each have a producing WP (see N-3 caveat on SC-002's explicit check).
- **Reviewer guidance** is present in all 9 WPs and is genuinely failure-mode-specific (esp. WP05's 4-point
  list and WP08's "try planting a `.parent.parent` — the ratchet must flag it"). This is above the bar.
- **WP05 acceptance bar** (the highest-risk WP) is strong on the never-flatten and FR-004-oracle dimensions;
  S-3/S-5 only ask to make two of its checks positively-assertable rather than property-asserted.

---

## Verdict

NEEDS-REMEDIATION
