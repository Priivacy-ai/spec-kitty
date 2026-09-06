---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T19:49:14Z'
reviewer_agent: codex
wp_id: WP09
---

# WP09 Cycle3 Independent Review

Audience: parent orchestrator and arbiter. Updated: 2026-09-06.

**REJECT. One P2 regression is proven introduced by the cycle3 corrective diff.**
C2-R1/R2 reproductions pass, but the new source-position comment filter loses
authored comments when an existing caller reuses its loaded document.

**Third rejection: parent ARBITER MODE required. No fourth automatic retry.**
This is a review finding, not a lifecycle verdict write or permission to lower
the acceptance bar.

## Scope And Authority

Applied user's latest narrowing: C2-R1/R2 correction and nearby comment/key
regressions only. Earlier-started checks finished naturally; no kill/restart,
new broad/full suite, timing retry or fresh public-P7 run after redirection.
Valid unchanged evidence is reused, not relabeled as fresh independent proof.

CLI-resolved reviewer-renata and review charter context both exit0. Applied
quality-gate/not-implementer boundary. #3908 remains unresolved with zero resolved
references; explicit actual PRIMARY charter, WP09 and contracts apply. Generated
python-pedro identity/lifecycle instructions do not override parent-only actions.
Read full fresh prompt95e920f07f7c4729a979db173b7fec41, all superseding handoff and
both original reports. Canonical actionreview27262 terminal exit0 is not
acceptance/test-pass evidence.

Reviewed GREEN: b86c191608cea1b1c591730a7a934c48a038e724.
Cycle3 RED: 555d07c4bef5ba43a687832d219443764dd660d8.
Entry: 9982b50ed56f02539fdeb1424d362ee08a9a0b62, source identical to rejected4e72cedb.
BASE: c18531d304c4d71165c42aa35f07c134c6d76a90.
Observed lane HEAD: 2bd33cd07ab4b5de42d60b6eaeb7d2d7135ba47a; reviewed source
matches GREEN, all seven frozen hashes match, tracked/untracked checks clean.
Cycle3 changes only YAML I/O and its two owned test files:129 additions/7 deletions.
Original seven-path scope preserved. No source/lifecycle/Op/COORD/PRIMARY edits.

## C3-R1 [P2]: Reused Round-Trip Documents Lose Key Comments

Location: [charter_yaml_io.py:292](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:292),
with the new rejection predicate at
[charter_yaml_io.py:301](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:301).

The new filter compares comment token positions from the caller's mutable
round-trip document against spans parsed from the current file. After an earlier
save changes preceding text length, that same document still carries its original
source marks. The filter misclassifies a key's own comment as outside its entry,
removes it from rendering, then replaces the disk entry including that comment.
The save succeeds and the comment disappears. No race or invalid YAML is involved.

Minimal original input:

```yaml
metadata: {}
activated_directives: # keep-rationale
  - old
```

Actual existing public entrypoints:

```python
doc = load_charter_yaml(path)
doc["metadata"] = {"long-entry": "x" * 100}
save_charter_yaml(path, doc)       # Comment is still present.
doc["activated_directives"] = []
save_charter_yaml(path, doc)       # Final source silently loses the comment.
```

Final file ends with "activated_directives: []" without "# keep-rationale".
BASE and cycle3 entry retain that comment. Both LF and CRLF reproduce.
Reloading the document between saves is a positive control: both forms pass final.
That control isolates stale source coordinates; it is not an approved new caller
precondition or a substitute for preserving the existing load/save API.

[Exact control script](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/reused_document_control.py),
[entry GREEN](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/reused-entry.jsonl),
[BASE GREEN](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/reused-baseline.jsonl),
[final RED and positive controls](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/reused-final.jsonl).

Entry and BASE each pass all four controls, exit0. Final fails the two reuse
controls and passes both reload controls, exit1. All use actual unpatched
load/save functions and real files; logs identify imported source paths.

Violates T044 step6 round-trip comment preservation, T045 step8 existing-writer
compatibility and NFR-004. Corrective code must not assume caller-held ruamel
marks describe the latest on-disk bytes. Parent arbiter should assess this bounded
fix direction and retain the existing no-duplication/separator regressions.

## Prior Findings

- C2-R1 multiline comments: original eight update cells now pass, including
  LF/CRLF and empty/nonempty replacement.
- C2-R2 explicit keys: original update/deactivation cells pass; four real
  CharterPackManager.deactivate controls cover legacy and pointer layouts.
- Original R1-R3: previous nine regression cells now zero failures; original
  raw-preservation and no-churn controls true.
- Existing boundary matrix:62/62 pass. Permanent expanded correction tests also
  pass in the already-running focused suite.
- Cycle3 author24-case committed RED provenance retained from555d07c4. No need
  to re-open settled earlier RED/tidy/portability history or repeat broad gates.

These fixes are real, but do not negate the new corrective-diff regression.

## Fresh Evidence

[Exact commands/isolation/provenance](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/commands.md).

| Check | Result |
| --- | --- |
| Already-started four owned files, two caller modules, three architecture gates | 388 passed,1 warning,390.32s; [focused log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/focused.log) |
| Ruff check/format, C901<=15, strict mypy all seven | Pass; external logs in evidence directory |
| Prior update/deactivation controls | 8+4 pass, actual existing APIs |
| Original regression controls | Zero previous failures |
| Prewrite/clock/strict-key controls | Seven stale-input refusals before any write; later-clock exact bytes/hash/modes and repeat no-churn; two invalid-key/section refusals |
| New bounded reuse attribution | BASE4pass, entry4pass; final2fail/2positive-control-pass |

No new serializer/upward import/unknown-key coercion or architecture exemption
was found in the corrective diff. Fresh import/layer/dead-symbol checks pass.
No-op False/absent observations retain documented meanings; fail-loud recheck
paths remain intact. T043 evidence remains valid; T044/T045/T046 comment/writer
preservation is incomplete solely on the bounded finding above, without claiming
full public FR-001/002/003 implementation.

## Preserved Observations Outside Final Narrowing

Before redirection, expanded_matrix.py completed108 valid cells with three
failures, not a green gate. Two legacy saver cases with "%YAML 1.2" directives
refused adding an activation key with ComposerError; a reused explicit-key
document duplicated its comment. The latter is related source-metadata reuse,
not an additional independent severity count.

Already-running cycle3_regressions.py narrowed the directive cases to LF/CRLF
null/map inputs: four final refusals vs four BASE successes. It also confirmed
the reused-map loss above. [Final raw results](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/regressions-final.jsonl),
[BASE raw results](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle3-review-evidence/regressions-baseline.jsonl).

The directive behavior is not established as newly caused by cycle3's corrective
diff; no further investigation or expansion was started after narrowing. It is
preserved as an unresolved parent-disposition item, not waived, not attributed
to WP10 composition and not the basis for inflating the corrective-diff findings.
No whole-document support or all-YAML-inputs approval is issued.

## Residual Gates And Handoff

Author388 owner/caller/architecture and1642 Make receipts remain valid evidence;
fresh independent388 is separately reported above. Author broad4018pass/6skip/9fail,
serial public follow-up1pass/5fail and timing failure remain non-green records.
All eight original public REDs remain unwaived WP10/WP13/integration obligations.

Author actual public P7 legacy/pointer apply/repeat on b86c1916 passes exact
prepared bytes, target-only net delta and no repeat churn. Reused, not rerun.
Preview still omits required work through empty pending_migrations/rendered_human:
no public-preview or full-mission acceptance approval.

Timing gate remains FAILED:3.896982s against unchanged3s. Author BASE/current
direct controls also failed3.73s/4.85s; unchanged source and call traces are not
conclusive causal attribution or an acceptance waiver. No independent timing
retry, threshold change or retry-until-green occurred here. Parent retains triage.

Six skips remain explicit: Linux /proc/self/fd, native Windows read-only replace,
three missing synthesizer fixtures and absent directives.yaml fixtures. Controlled
absent-fchmod evidence is not native Windows proof. No native Linux/Windows/wheel
claim. Snapshot equality does not prove every transient syscall; existing explicit
audit controls have bounded coverage.

Warm direct Python3.11.15 used; no resync/install, host credentials or real global
assets. Inspected env-i/offline policy forces sync0 despite conftest and children.
Exported pytest guard reaches workers and relocates only external caches.
No claim that Python audit hooks universally cover native child syscalls.

**Parent ARBITER MODE, not another automatic worker retry.** No approved WP10
API handoff or self-integration. Parent alone records lifecycle verdict,
arbitration/scope disposition, commits, integration and push. Original reports
and all prior RED/GREEN evidence are preserved.
