---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T18:35:35Z'
reviewer_agent: codex
wp_id: WP12
---

# WP12 Independent Preservation Review

## Verdict: REJECT

Independent review of RED `6e60f8b42e783b2c8fb8dea237a7a5514854a8ec` and GREEN `ee431b2fc8cd3d334e70bc56de857cb62dc92402`, starting from `ebd949707254abb0db361cd9d781cad43f4a7daf`. Two introduced defects reproduced below. Strong preservation positives do not satisfy the missing durable full-corpus control.

Read-only lane: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-k`.
Observed HEAD: `441a071f764feea2e5802cddeb3ef3baac07f4cb`. Its differences from GREEN are mission lifecycle/review data, not source/tests. Final `git diff GREEN -- src tests` empty; final `git status --short` empty. Reachable, unchanged `origin/main` and comparison merge-base: `c0054153b9bce0778cf41a85d11ecd4e9650031d`.

Scope: exactly the three owned test files. No source, receipt, historical corpus, lane index/ref, root lifecycle, Op, or shared coordination edits. Only external reviewer harness/evidence/report created. Parent owns durable verdict, repairs, integration, and final mission acceptance.

## Findings

### P1: Full-corpus regression passes while the real scanner omits 419 missions

Location: [tests/upgrade/test_mission_corpus_recovery.py:162](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-k/tests/upgrade/test_mission_corpus_recovery.py:162), with nonempty-only zero assertion at line 102 and incomplete corruption checks at lines 172-187.

The recovered membership oracle comes from the original audit report itself. The original report need contain only the four named defective missions; no independently derived corpus inventory is required. Landed/corruption/healthy reports are not compared against an independent expected membership either. Consequently, the comment claiming these controls prove absence of a narrowed scan is false.

Fresh reproduction: external [narrow_scanner.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/narrow_scanner.py) wraps the actual audit engine's `_scan_missions`, restricting its existing `allowed_dirs` argument to the four named defect directories. It still calls the real scanner, real classifiers, aggregation, and public CLI; no output JSON or gate result is fabricated. No tracked file is changed. Run the unchanged existing `test_original_full_corpus_fails_then_recovered_and_landed_corpus_passes` with this reviewer-only fault injection.

Result: **1 passed in 222.73s; actual terminal exit 0** (229.98s including process lifetime). All eleven audits ran. Original physical corpus: 423 directories, only 4 scanned. Recovered/landed/corruption/control physical corpus: 422 directories, only 3 scanned. The same 419 unrelated missions disappear throughout, yet the persistent test accepts every expected zero/corruption result.

Evidence: [narrowed-corpus.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/narrowed-corpus.json), [narrowed-corpus.stdout](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/narrowed-corpus.stdout), [narrow-scan-records.jsonl](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/narrow-scan-records.jsonl), [audit-summary.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/audit-summary.json). Full raw CLI records remain under `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/narrowed-fixtures/test_original_full_corpus_fail0/cli-evidence/`.

Impact: T064 steps 9-10 explicitly forbid a four-directory substitute and require corpus membership retained independently. The test cannot detect future scanner filtering or omitted unrelated blockers. This is a demonstrated acceptance-control gap, not a claim that the unmutated scanner currently filters the corpus. FR-009/NFR-003 full-corpus assurance remains unmet.

Required correction: derive expected membership independently from the pinned Git/disk corpus, account explicitly for the authorized relocation, and require exact membership with no duplicates for original, recovered, landed, corruption, and healthy reports. Add a durable negative control that narrows discovery or drops an unrelated mission. Do not hardcode a historical total, mutate the receipt, or delegate WP12's persistent control back to WP11.

### P2: Unchanged Gitlink outside the archive roots breaks the archive gate

Location: [tests/architectural/test_archive_root_byte_identical.py:109](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-k/tests/architectural/test_archive_root_byte_identical.py:109), reached by unscoped `_tree(port_base_rev)` at [tests/architectural/test_archive_root_byte_identical.py:392](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-k/tests/architectural/test_archive_root_byte_identical.py:392). The nonempty-baseline helper also reads the unscoped tree before filtering.

The new recursive tree reader asserts every entry in the entire repository is a blob. A valid baseline Gitlink has mode 160000 and kind `commit`, including when unrelated to all four protected roots.

Fresh reproduction in a real disposable Git repository:
1. Establish nonempty protected history and exercise the real canonical lifecycle append.
2. Add `vendor/example` using `git update-index --add --cacheinfo 160000,<valid-commit>,vendor/example`, commit it as baseline, and keep a reachable real `origin/main`.
3. Run the actual old gate body against that unchanged baseline: passes.
4. Run GREEN's gate on the same repository: rejects with `vendor/example: non-blob historical entry`.

Evidence: [probes.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/probes.py) (Gitlink setup near line 107), [probes-results.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/probes-results.json), [probes-corrected.stdout](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/probes-corrected.stdout); physical fixture `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/original-entry-repo-v2`.

Impact: introducing an unrelated submodule into a repository now blocks archive checks even with no protected-history violation. This broadens a four-root preservation gate into an unsupported whole-repository blob-only policy. Current lane does not contain this Gitlink; this is a reproduced valid-configuration regression, not a current-lane failure.

Required correction: retain unscoped rename endpoint visibility, but restrict protected-kind validation to protected inputs, or represent unrelated tree kinds without failing archive policy. Add an unchanged outside-root Gitlink control. Do not relax protected-path kind checks.

## Requirement Coverage

| Requirement | Independent result |
| --- | --- |
| T060: original RED and append authority | PASS. Actual old entrypoint rejects a real canonical append; GREEN accepts identical bytes/delta. Original operator append-permitting decision read, not inferred from candidate code. |
| T061: byte prefix, every row, modes/kinds, index/worktree | PASS in fresh focused and independent controls. Invalid middle and last suffix rows, old-prefix whitespace rewrite, staged corruption behind healthy disk, and chmod rejected. |
| T062: independently approved WP11 receipt and exact recovery | Positive scope PASS. Immutable proof, 31 restores plus retained schema, two moves, three canonical snapshots, eleven full verdicts, raw history and no-churn exercised. Not blanket mission acceptance. |
| T063: mixed diffs, forged proof, links, post-landing protection | Preservation attacks rejected, including matching forged receipt/output and healthy-disk/bad-index attacks before and after simulated landing. P2 unrelated Gitlink false rejection remains. |
| T064: owner witnesses, self-mutations, corpus controls and regressions | FAIL: narrowed-scanner mutation survives. Real writer/public next, full healthy audit, corruption failures, and separate real TTY consent pass. Broad suite/final parent landing remain separate evidence limits. |
| FR-007/FR-008 recovery preservation | Strong positive evidence for exact owned recovery and retained history, bounded by tested source/ref. |
| FR-009/NFR-003 full-corpus audit | Healthy complete scan independently verified; durable anti-narrowing requirement fails. |
| FR-010 separate consent | Fresh real damaged-corpus upgrade tests pass: --yes alone does not authorize repair; separate POSIX TTY approval reaches owner effect. |
| FR-011 / final evidence and acceptance | Raw evidence retained; parent integrated final corpus/terminal acceptance not granted here. |
| NFR-004, canonical ownership and evidence integrity | Trusted Git pins, exact bytes/modes and canonical owner replay supported; no producer self-authorization or schema waiver. |

Counts follow actual approved three-snapshot/eleven-verdict recovery, not obsolete smaller counts in residual prose.

## Authority and Preservation Evidence

Read full canonical review prompt, full WP12 handoff, full independent WP11 review, actual PRIMARY WP12, all five PRIMARY contracts, actual charter, corpus-slicing adjudication, archive-freeze remediation design, and parent archive classification. Read all three owned files and relevant writer/reducer/audit seams. Relevant spec/plan sections inspected; not claiming every repository document was read.

Reviewer-renata profile and review charter-context CLI both completed with exit 0; captures: [profile.stdout](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/profile.stdout), [charter.stdout](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/charter.stdout). Applied reviewer identity/boundaries rather than the prompt capsule's implementer role. Context returned empty doctrine collections; **#3908 explicit fallback remains**: actual charter used as binding authority, not a claim that resolver success means full doctrine resolution. Legacy org.packs warning retained; no local repair/activation.

Original operator decision at `7afd572fc:kitty-specs/retire-doctrine-term-01M0JMK9/decisions/DM-01M0P6C8C7Q6SPBT412V39RPN0.md` explicitly allows runtime append. New-row schema validity is not actor authentication; review does not claim otherwise.

WP11 authority consumed, not minted by WP12:
- Independent approval event: `01M1VMFHA7K9XJAK0Y2MJR6NRV`.
- Original source: `3442ca1afc20b1b83b27a7bc64fd7014050b12a1`; convergence: `2554bd13adc289d3457681308645fe52619bca0e`, with expected first parent.
- Receipt RED: `13e75ffd06434e02b0ddd578b7047f22506bc917`; restored: `3cb4af0ccce9a3b8db73e03fb37149d62bf3ef53`; recovered/adjudicated: `8e2d40bc0cbf607eea3af97ae9a80e82f18ee8f4`.
- Immutable receipt blob: `1f2df686485dfb95195f097ee4132769d009ae96`; SHA256: `f320ada834fbabcddd7186147d606551dcecf066dad4c4eef182eafcf0a7f4b8`.
- Retained schema blob: `26cb3b8bafde72894f0d1ec0a9c1701cd511f497`.
- Candidate proof must match independently pinned blob/mode and working bytes; Git replace objects disabled. Matching forged receipt and output rejected both before and after landing.
- Exact 31 restored paths plus retained schema include hidden dossier content and .gitkeep. Two historical documents relocate byte-identically; destination README remains protected.
- Three snapshots are doctrine/symbolkey/cyclic; full review-result inventory is 5+3+3=11, not just verdict labels. Cyclic raw history contains 71 rows. IDs, dates, force and annotations preserved; canonical pure composition checked.
- Independent gate no-write inventory compared 120 nodes, including directory/file/link state, bytes, full modes, mtimes, .git/index and .git/HEAD.
- Independent pre/postlanding corruption controls cover each snapshot, both moved documents, README, .gitkeep, cyclic metadata, raw history, forged proof/output, and staged destination hidden by healthy disk. Healthy controls restored and rerun between attacks.

## Fresh Execution

All listed completed processes reached actual terminal exit 0 unless explicitly marked RED/harness error. Command argv, cwd, terminal status and process duration are recorded in each corresponding JSON; stdout/stderr retained separately.

| Reviewer run | Result |
| --- | --- |
| Owned corpus module | 5 passed, 794.45s pytest; terminal 0 after 976.77s. [corpus.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/corpus.json) |
| Owned gate/preservation focused selection | 92 passed, 90 deselected, 760.39s pytest; terminal 0 after 779.24s. [focused.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/focused.json) |
| Narrowed-scanner fault injection | 1 passed, 222.73s pytest; terminal 0 after 229.98s. Surviving mutation, NOT healthy acceptance. [narrowed-corpus.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/narrowed-corpus.json) |
| Independent physical Git/filesystem probes | 33 observations plus completion record, terminal 0, 358.32s. Includes 27 preservation-negative rejections, original RED/GREEN, positives and Gitlink regression. [probes-corrected.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/probes-corrected.json) |
| Ruff check, all three | Exit 0; All checks passed! 0.25s. [ruff.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/ruff.json) |
| Ruff format --check, all three | Exit 0; 3 files already formatted. 0.23s. [format.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/format.json) |
| Mypy --strict, all three | Exit 0; no issues in 3 source files. 14.64s. [mypy.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/mypy.json) |
| Independent membership/raw-hash summary | Exit 0, 4.04s. [summarize.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/summarize.json) |
| Effective isolation/sync-child/network-denial control | Exit 0. [policy-control.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/policy-control.json) |

Fresh normal pytest total: **97 passed**. Not claiming a fresh 187-test sweep: the 90 deselected cases are repeated postlanding/snapshot-verdict combinations. Independent probes supplement them but do not relabel them executed pytest cases.

Focused selection excluded `recovery_results_remain_protected_after_landing` and `snapshot_history_and_complete_verdict_are_pinned`. It retained all live archive-gate checks, real lifecycle writer/public next witness, middle-row validation, mode/link/index attacks, four-root mixed diffs, NUL path handling, CI missing-base/empty controls, relocation forms, receipt attacks, canonical drift plus matching output, repeat collision, purity and gate self-mutations.

Original RED is behavioral: actual old gate source from RED executed in memory with only repository-root rebinding, over a real Git delta produced by the canonical writer. It rejects `M\tkitty-ops/lifecycle.jsonl`; GREEN accepts the same append. Old source SHA256: `b561cd1a34c40d5d3b899668f583b09dbeb07a66d590c084576b40c5e194a995`.

Honest harness limit: first external probe launch omitted the lifecycle constructor's required mission_id and stopped before gate execution (3.71s). It is **not** product RED. Corrected external harness/new fixture completed; original failed logs retained in `probes.{json,stdout,stderr}`.

## Complete-Corpus Evidence

Unmutated public `doctor mission-state --audit --fail-on teamspace-blocker --json` executed eleven times on the Git-reconstructed reference corpus, without fixture/mission filters. Reviewer independently derived expected immediate mission-directory membership from `git ls-tree` at the actual pinned source, not from audit output or a hardcoded count. Every unmutated report matched exactly and contained no duplicate mission IDs. Every mutant report was a strict subset. Separate empty `missions=[]` control rejects with `empty corpus discovery`.

| Raw command index | State | Missions | Blockers | Exit |
| --- | --- | ---: | ---: | ---: |
| 0 | Original | 423 | 4 | 1 |
| 1 | Recovered | 422 | 0 | 0 |
| 2 | Simulated landed | 422 | 0 | 0 |
| 3 | Cyclic metadata removed | 422 | 2 | 1 |
| 4 | Healthy control | 422 | 0 | 0 |
| 5 | Doctrine snapshot stale | 422 | 1 | 1 |
| 6 | Healthy control | 422 | 0 | 0 |
| 7 | Symbolkey snapshot stale | 422 | 1 | 1 |
| 8 | Healthy control | 422 | 0 | 0 |
| 9 | Cyclic snapshot stale | 422 | 1 | 1 |
| 10 | Healthy control | 422 | 0 | 0 |

Original finding-code controls identify both IDENTITY_MISSING and both SNAPSHOT_DRIFT cases. Complete raw stdout, stderr and per-command records: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/corpus-fixtures/test_original_full_corpus_fail0/cli-evidence/`. Verified hashes in [audit-summary.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/audit-summary.json):
- Original stdout: `8729d734fef7b361232388cfb16192541922c0bc50fd50b2662a506c9dc5e6fd`.
- Recovered, landed and all healthy stdout: `0988ae29e082b516b67db48a3d105c62623818f1fe3174240e2ecef7c0f93cff`.
- Cyclic-meta corruption: `5f1256acba379c43562b163497872e63912fc565e06e9045ebc6f551affbf0f3`.
- Doctrine corruption: `09d12f8758d6ebaeadbc5c6f7dfba130c8c6efaa8a9bb95b8bfa68c3ee643f8a`.
- Symbolkey corruption: `a859d51d56f6cba71c481deed26e9c8282a5fba2e23183b188da7582fae95a12`.
- Cyclic-snapshot corruption: `c90169207c4bed74851b157949edcb0fb2f1a15e4ebc70436303d5673ce497c3`.
- All stderr empty: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

This proves the current healthy reference corpus, not a future integrated parent tree. The reference corpus does not retroactively include the current planning mission. The external independent membership checker is not delivered WP12 regression code; it cannot cure finding 1.

## Isolation, Hashes and Limits

Warm direct Python/pytest/ruff/mypy binaries; no uv sync/install. Python 3.11.15; spec-kitty-events 9.1.6. Resolved package and reducer paths are lane/src, not a substitute installed wheel. Existing real Git refs retained, literal CI=true, cleared PYTEST_ADDOPTS, bytecode writes disabled.

[run.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/run.py) clears inherited environment and confines twelve HOME/XDG/app/temp roots externally. [sitecustomize.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/sitecustomize.py) executes inspected ROOT/wp02-policy/sitecustomize.py and reinjects it into child PYTHONPATH. Verified sync remains 0 even after parent/child attempts to set 1. Non-loopback Python connection attempt to documentation-range address was denied by the audit hook before connection. This is an effective Python-process control, not an OS-wide firewall claim. No credentials or hosted traffic used.

[review_policy.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp12-independent-evidence/review_policy.py) binds the existing warmed test venv and redirects wall-clock scan cache externally; it does not disable conftest, scanner checks, or canonical guards. Pytest cache disabled; mypy cache external. Mutant opt-in applies only to its dedicated run. Local Git fixture commits/ref updates remain external.

Final owned-file SHA256:
- Archive gate: `6e2723adba8f4521cb032cce56f7399301924a72b611d9ac1f267832fec732b9`.
- Preservation tests: `24820766a4db859d864fea92511b7f25d18c44bfc1e0ecc187f23b395c2f1dea`.
- Corpus tests: `aeebf6332f36080ef8a20caa28474a6b15199945b59814d8ee5c77b64321f66e`.
- Receipt SHA remains the immutable value above.

Worker's 187 committed-tree passes/static evidence and reported broad counts are worker evidence, not my executions. Full architecture, make test-fast, broad upgrade/audit/status/doctor suites, wheel/platform E2E and final integrated corpus not rerun here. macOS/POSIX TTY exercised; no Windows/Linux claim.

Known external reds remain explicit, not waived:
- #3919 terminology guard conflicts with immutable receipt ID `rename-ceremony-to-status-commit-01KSPN6C`.
- #3914 redirect failures (124 reported).
- Supporting shard/format correction `910940be0209d3115a0d1bf216e83e64a10cf0dc` independently approved in PRIMARY earlier, not merged into this lane.
- Sync guard expects 1 whereas required offline policy pins 0; not changed to obtain a green run.
- Worker reported architecture 10 failed, 1951 passed, 2 skipped, 2 xfailed. Not a full architectural green and not independently reattributed here.

## Anti-Pattern Check

| Check | Result |
| --- | --- |
| Dead code | N/A production change; three test files only. |
| Synthetic-only evidence | PASS for healthy witnesses: actual public CLI, writer, reducer, Git and filesystem. Narrow-scanner mutation explicitly labeled fault injection. |
| Silent empty/fallback success | Empty corpus rejected; missing comparison base fails under CI. No fallback green claim. |
| Requirement coverage | FAIL: durable full-corpus anti-narrowing control missing. |
| Frozen historical inputs | PASS in tested controls; no data/receipt rewrite proposed. |
| Locked decisions | Full-corpus decision not yet enforced against reproduced narrowing; other tested preservation boundaries retained. |
| Ownership | PASS: no producer self-approval; review-only external output. |
| Production fragility | No runtime source diff; P2 is a new test-gate compatibility regression. |

Parent should route fixes for the two scoped findings and request independent follow-up controls. No Op closure, lifecycle verdict mutation, integration, push, blanket waiver, or final mission approval performed.

