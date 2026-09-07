---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-07T02:01:45Z'
reviewer_agent: codex
wp_id: WP08
---

# WP08 Review 2: REJECT

Reviewer Renata. Bounded scope: original F1, the four-file corrective diff, and directly adjacent directory-mode execution/preservation risks. Parent alone records verdict/lifecycle. No broad WP08 or supplier rereview.

## F1b [P2]: Final directory modes applied before descendants

[projection.py:662](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-h/src/specify_cli/tool_surface/bundles/projection.py:662) now creates/chmods each directory to its retained **final** mode immediately. The existing ordering processes parent directories before children. A readable, non-writable source hooks directory (`0555`) therefore becomes an unwritable destination before its empty child or script can be created.

Fresh real `CodexBundleProjector.build()` witness fails with:
```text
BuildError: [Errno 13] Permission denied: '.../dist/codex/hooks/empty'
```
Observed destination hooks mode is `0555`; its script and empty child are both absent. The independent `shutil.copytree` control successfully copies the same source bytes and both `0555` directory modes. This is a baseline-primitive control, not a historical BASE execution claim.

This is directly introduced by the corrective writer change, not F045 or an escaping sandbox path: both controls run under the same OS policy inside reviewer evidence. The source can be read/traversed normally; only the new destination's prematurely restrictive permissions prevent completing the batch.

Evidence: [test_readonly_directory.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/test_readonly_directory.py:29), [raw failure](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/readonly-directory.log), [observed state](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/readonly-directory-result.json). One test failed in 2.20s, terminal1. No mocks of writer/rendering, no skip_validate, no forced assertion failure, no root/supplier edits.

Required correction: materialize descendants without prematurely removing the writer's required directory permissions, then establish retained final directory modes in safe order. Keep exact final-mode effects, truthful succeeded/partial IDs, bounded apply behavior and unchanged/custom directory preservation. Do not replace this with rejection of readable source trees or a new mode policy. Add the real `0555` public-build regression. This remains the F1 directory-mode defect class; it is not a request to reopen unrelated ownership or integration work.

## Original F1 Disposition

**Original 0700 loss corrected; overall F1 correction not yet acceptable because of F1b.**

The byte-identical original independent witness was rerun against the fix:
- `0755` root/empty-child control: PASS.
- `0700` root/empty-child: PASS; neither widened to `0755`.
- Script bytes/`0750` mode and real manifest creation remain intact.
- Fresh result: **2 passed in 29.13s**, terminal0.
- Prior original RED remains immutable: 1 failed/1 passed on rejected product. No historical replay was invented.

[Original witness copy](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/test_directory_modes.py), [fresh GREEN](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/original-witness-green.log), [original review](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-review.md).

The full corrective diff was read. Codex retains immutable path/mode tuples, PreparedBundle stores them, explicit and inferred parent claims agree on mode, and existing directories still receive no chmod/adoption effect. Source-mode observations and all-batch guards are unchanged. Author source-root/empty-child chmod refusal and unknown existing directory/custom-content/no-churn assertions were inspected and their passing evidence reused. No additional tests were launched after actionable F1b confirmation.

## Exact Identity

- Corrective BASE: `624324aa744bb8b75c19e1d8faf9fae3eee67357`.
- RED: `ae45fac3b7e6ce2eeea1513fe2c15efa4266e602`; production unchanged from BASE.
- Fix: `451af47d3d18c0802debbb75298e2a16b09ee687`.
- Execution HEAD: `399d46a16b9511f553e0a34240e65832e6feccb7`.
- BASE -> RED -> fix -> HEAD ancestry verified. Only later lifecycle status files differ; source/config/lock/test identity equals fix. Worktree clean before/after tests.
- Exactly four corrective paths. Committed binary diff equals author's tested patch, SHA-256 `4783e68fca94f96561740274c65465528d7766598e7c993a45d955bbafb33cf1`.

| Corrective path | SHA-256 |
| --- | --- |
| src/specify_cli/tool_surface/bundles/codex.py | 91117b1e74771ebdfe23f44ef70d0e57c1bdf0df94a916fae19bc34e37fe6818 |
| src/specify_cli/tool_surface/bundles/model.py | 967203daef01a26432d6990fdde86a246619ba48e563e9e62ece222feacd9748 |
| src/specify_cli/tool_surface/bundles/projection.py | 2e7c740d8d49814e0b1f0a3e8a3e999d48c65ef6dd92ea39aacb0a4ff2b1e73a |
| tests/specify_cli/tool_surface/test_plugin_build_codex.py | 19d20cd1a66b6b78d9c9e8df3f3bd0c0c0bf9522bbac1280df3fd4719c1d9fcf |

[Provenance assertions](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/provenance.py), [initial receipt](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/provenance.json), [final receipt](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/provenance-final.json), [verified corrective diff](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/corrective.diff).
Both receipts pass, including all 110 original author evidence hashes, 16 correction evidence hashes, original reviewer seal/report/witness/failure hashes, unchanged remaining owned files/governance/policies, and exact approved helper bytes. Imported production modules resolve to lane-h source.

## Fresh Commands and Outcomes

Full exact argv, UTC start/end, OS denial checks, sync parent/child and terminal statuses: [invocations.jsonl](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/invocations.jsonl). Command expansion: [commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/commands.md).

| Invocation | UTC start -> end on 2026-09-07 | Result |
| --- | --- | --- |
| Protected readiness imports | 01:53:51.549167 -> 01:53:51.578706 | exit1, missing click.exceptions |
| Authorized dependency restoration (not protected product test) | 01:54:19 -> 01:54:22 | exit0, 134 packages |
| Protected readiness imports after restoration | 01:54:47.083463 -> 01:54:47.382310 | exit0 |
| Canonical reviewer-renata profile | 01:54:47.545924 -> 01:55:06.227848 | exit0 |
| Charter review context, serialized after profile | 01:55:47.342891 -> 01:56:09.384816 | exit0, #3908 degraded |
| Initial provenance | 01:56:16.206324 -> 01:56:17.515606 | exit0 |
| Original independent witness | 01:56:46.496346 -> 01:57:37.292240 | exit0, 2 passed |
| Adjacent readonly-directory witness | 01:57:48.181576 -> 01:57:52.219441 | exit1, 1 failed |
| Final provenance only | 01:58:26.081057 -> 01:58:27.426146 | exit0 |

After F1b, only evidence/provenance/sealing work; no new behavioral, static, validator, architecture or suite probe.

## Reused Evidence, Not Fresh Certification

Author correction evidence accurately records **10 passed / 1 test-expectation failure**, followed by the corrected failed case **1 passed**, at identical production bytes. It was not a single eleven-test green run. The failed expectation used the wrong root-relative paths when existing dist changed staging_root; final test normalizes all actual destinations to the snapshot root without dropping modes, hashes, paths, kinds or actions. Original failure retained and hash verified.

Author RED: 2 failed/1 passed, genuine public-build mode mismatch. Author Ruff four paths and strict mypy three sources passed, plus final test-only Ruff. These static results are reused, not independent static runs. Fresh static and further adjacent pytest selection stopped after F1b.

Prior supplier/helper, configured consumer, Claude validator and broader WP08 results stay at their recorded source snapshots. No 145-owner, 924-subsystem, 1642-fast, architecture/public, helper or external-validator repeat. The configured-helper Op is settled/closed per superseding parent handoff; its prior consumer verdict is unchanged and not reopened. WP10 root composition/public integration gates remain pending, without waiver.

## Narrow Criteria and Anti-Pattern Dispositions

| Criterion | Review 2 disposition |
| --- | --- |
| T039 | Prior RED reused; correction RED independently hash verified. |
| T040 retained directory modes/empty children | PASS for immutable path/mode representation and declared modes. Original witness now green. |
| T041 actual existing build/application | **FAIL F1b**: final parent permissions prevent completing readable source trees. |
| T042 exact behavior/no-churn/preservation | Original witness PASS; author chmod-staleness and existing-directory/no-churn evidence reused. Missing restrictive-mode case now fails independently. |
| Dead code | PASS within correction: no new public function/class/module; changed data consumed by real existing build/apply. Settled helper gate not reopened. |
| Synthetic fixtures | PASS: real public builds/prepare/apply, concrete files and independent snapshots; no literal substitute for implementation. |
| Silent empty return | PASS: no new catch-to-empty branch. |
| FR coverage | **FAIL overall** through F1b for complete mode-preserving real staging (FR-002/003; T040-T042); remaining FR-004/NFR-004/C-001 evidence reused, not recertified broadly. |
| Frozen surface | PASS: exact four-path diff, no shared fixture/helper/source/config/lock change. |
| Locked decision | No new installation/removal/activation policy; permission-preservation failure is F1b, not an authorized contract change. |
| Shared-file ownership | PASS: corrective paths all WP08-owned. |
| Production fragility | **FAIL F1b** supported readable input now triggers a real build error. New mode assertions otherwise enforce internal regular-directory/effect invariants, not new public input policy. |

## Environment and Governance Limits

F045 freshly reproduced `ModuleNotFoundError: No module named 'click.exceptions'`; attribution unknown. Explicitly authorized `uv sync --frozen --all-extras --reinstall` used ROOT/dependency-cache and external disposable HOME/cache/tmp. [Raw restoration](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-cycle2-independent-evidence/restore-environment.log) retains missing-RECORD uninstall warnings; exit0 is not a forensic explanation or proof of complete environment health. Protected imports and actual tests subsequently ran using Python3.11.15, pytest9.0.3/events9.1.6, Click8.3.3/annotated-doc0.0.4. No source/lock/config edits. Installation is expressly **not** an isolated product test.

All product readiness/CLI/Python/tests run through own env-i wrapper, dual live-home alias read/write denial, all-network denial and writes confined to own external evidence except /dev/null. Before each, known-existing skill-file O_RDONLY/O_WRONLY noncreating/nontruncating denials, checkout/sharedGit write denials, socket denial and parent/child sync0 clamp were recorded. No parent wrapper, no live-home inventory/rollback.

Real conftest remains loaded; external warm fixture hook RETURNs cached value; scanner cache only redirected. Original witness copied byte-for-byte; outputs go to new evidence, never overwrite first-review artifacts. Both optional-source witnesses retain the known `/.kittify/config.yaml` warning; no fixture/policy relaxation. POSIX permissions tested; no Windows or native-syscall audit claim.

Read full fresh canonical prompt, superseding handoff and own original review. Fresh canonical Renata profile and review charter calls serialized. #3908 returned zero references; explicit previously read charter/AGENTS/Renata binding hashes verified unchanged, not interpreted as empty governance. Reviewer's role remains quality gate, not implementer.

All handles terminal. No source fixes/commits, lifecycle/status/COORD/Op writes, accept/merge/push, or settled-area reopening. Parent captures WP08 **REJECT**.
