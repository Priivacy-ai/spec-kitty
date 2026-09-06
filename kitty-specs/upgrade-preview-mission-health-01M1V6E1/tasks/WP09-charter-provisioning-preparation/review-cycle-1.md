---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T16:06:05Z'
reviewer_agent: codex
wp_id: WP09
---

# WP09 Independent Review: REJECT

Audience: parent orchestrator and WP09 implementer. Updated: 2026-09-06.
Reviewer: CLI-resolved reviewer-renata; independent, read-only lane review.

Three introduced defects block approval: one writes invalid YAML while claiming success, one discards authored comments, and one refuses previously supported unowned YAML keys. These reproduce on final production source and do not reproduce on BASE. No implementation, lifecycle, verdict-event, commit, or push writes were made.

## Findings

### R1 [P1] Null/explicit-empty documents become invalid persisted YAML

Location: [charter_yaml_io.py:171](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:171), specifically the early return at line 172.

The existing loaders deliberately interpret a YAML-null document as an empty mapping. When adding the missing mission-type key, this branch appends the new mapping to the original scalar/document terminator and returns before the final parse/equality validation at line 204. The real provisioner returns True after writing an unreadable document.

Reproduction, both legacy config and non-default pointed charter:

1. Target bytes are `null\n`, `~ # keep\n`, or `---\n...\n`.
2. Call the existing `compiler.provision_mission_type_activations(project)`.
3. It returns True. For the first case the file now begins `null\nmission_type_activations:\n`.
4. Reading with the existing YAML authority fails: `ScannerError: mapping values are not allowed here`. The explicit-empty document yields a multi-document ComposerError.

BASE provisions a valid nonempty mapping for all six layout/input cells. Final writes invalid YAML in all six. Ordinary zero-byte and comment-only documents still work; this is specifically the distinction between parsed-null and an actually empty source span.

Expected: prepare one valid mapping under the existing empty-document convention, preserving applicable comments/document framing; if a form cannot be supported, refuse before any write. Every render path needs the same validity guarantee.

Violates T044 preparation/valid-input handling, T045 honest success and writer compatibility, T046 refusal/readback; FR-003/NFR-004. This can strand subsequent charter/config readers.

Evidence: [final controls](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/adversarial-final-enforced.jsonl), [BASE controls](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/adversarial-baseline-enforced.jsonl), cases null/tilde/empty-explicit.

### R2 [P2] Updating a block activation list deletes its authored key comment

Location: [charter_yaml_io.py:220](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:220), together with the replacement span starting at line 181.

The replacement constructs a fresh one-entry CommentedMap containing only the value. It does not carry the original map's key-comment metadata. A block collection's replaced source span includes the comment after its key, so that comment is deleted. Re-parsing compares values only and accepts the loss.

Reproduction through the existing shared update API:

```yaml
activated_directives: # keep this rationale
  - old
metadata: {}
```

Call `update_charter_yaml_section(path, "activation", {"activated_directives": ["new"]})`.

Final result:

```yaml
activated_directives:
- new
metadata: {}
```

BASE retains `# keep this rationale`. This affects the writer used by normal activation and pack operations, beyond missing-key provisioning. The existing new test covers a trailing comment after a flow sequence, whose source mark falls before the comment; it does not exercise this block-key case.

Expected: retain the round-trip key comment when replacing its collection value. T044 explicitly requires comment/round-trip metadata preservation; T045 requires existing writer behavior to remain intact. NFR-004 is not satisfied by semantic YAML equality.

Evidence: block-key-comment in the same final/BASE controls.

### R3 [P2] Unowned numeric YAML keys incorrectly enter the deletion path

Location: [charter_yaml_io.py:178](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:178).

`key_node.value` is lexical text, while the loaded map contains constructed YAML keys. For `42: user-value`, the code looks for string `"42"` in a map keyed by integer `42`, misclassifies the untouched key as deleted, and removes its span from the candidate. The final semantic comparison then refuses with the unrelated diagnosis `Cannot preserve YAML aliases or section boundaries`.

Reproduction: target bytes `42: user-value\n`, missing mission_type_activations, then the existing provisioner. Both legacy and pointer layouts succeed on BASE and preserve this unowned key; both refuse without writing on final. No alias or malformed YAML is involved.

Expected: identify source keys consistently with the YAML authority so untouched valid keys remain untouched. Do not broaden known-activation-key validation into a new restriction on unrelated authored YAML.

Violates T044 raw unowned-content handling and T045 existing-caller behavior. Evidence: numeric-key cases in final/BASE controls.

## Exact Provenance

- BASE: `c18531d304c4d71165c42aa35f07c134c6d76a90`.
- Original RED: `d6095bda3013b88537ee00bd346f05f0e5fc9281`.
- Tidy extraction: `20b68d3c66096472607fe6023bc13e12444479ca`.
- Implementation GREEN: `2432b5eb1ce54cae2f12f0a76a906565e0b193db`.
- Portability RED: `0d3ceb18cf5c49a19653182872538e4640fc72c3`.
- Final production GREEN: `3ca087912b9c27cebf3626a2c0ac51620798ffc3`.
- Live lane/public receipt HEAD: `5cdcbe142e48afb1e88457141361d5ea0466d220`. Parent review-claim coordination/auto-rebase advanced HEAD. `git diff 3ca0879 HEAD -- src tests packs pyproject.toml uv.lock` is empty. Tests review the same final implementation, not an unreported source revision.
- BASE to final production diff: exactly seven authorized files, 806 insertions/210 deletions. `git diff --check` passes. Lane git status is clean.
- BASE controls import charter source and its real shipped seed extracted byte-for-byte by `git archive BASE src/charter` outside the repo. All remaining dependencies use the same warm Python 3.11.15 environment. No production method or writer is mocked.
- Original RED replay imports the two test files extracted from the exact RED commit and directly executes their original three assertions against archived BASE and final source. BASE has all three intended assertion failures; final passes all three. This is direct assertion replay, not a separate pytest-suite claim.

## Initialization and Authority

Used [spk-doctrine-profile-load](/Users/robert/.agents/skills/spk-doctrine-profile-load/SKILL.md), then the lane CLI:

```text
spec-kitty agent profile show reviewer-renata
spec-kitty charter context --action review --json
```

Both exited 0. Applied Renata's reviewer boundary: assess and report, do not implement/manage WPs. Context had zero references and unresolved selected-governance diagnostics (#3908); no successful governance-activation claim or repair.

Read the external handoff, full generated review prompt `05511d151c6145f2960901fbbbb242fe.md`, actual PRIMARY WP09 prompt, canonical charter, manifest and relevant spec/plan/data-model/research/contracts. Parent's explicit reviewer identity and parent-only lifecycle constraint override generated implementer identity and move-task instructions. The terminal review-claim prompt was received before this verdict.

The change's intent is sound: compiler owns absent-key/seed policy, pack manager owns pointer/legacy authority, YAML I/O owns preparation and exact-byte application. WP10 owns upward adaptation. No new VFS or upward dependency was introduced.

## Fresh Review Evidence

Commands and isolated environment: [commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/commands.md).
Scratch, logs, baseline exports and public fixtures are all under this external evidence directory.

| Check | Fresh result | Evidence |
| --- | --- | --- |
| All four owned test files | 142 passed, 148.46s, exit 0 | [focused-corrected.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/focused-corrected.log) |
| Three required architecture gates plus activation-engine, normalization and provenance-migration callers | 134 passed, 135.94s, exit 0 | [callers-architecture.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/callers-architecture.log) |
| Ruff, seven changed source/test files | Pass, exit 0 | [ruff.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/ruff.log) |
| Strict mypy, seven changed source/test files | No issues, exit 0 | [mypy.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/mypy.log) |
| Original three committed RED assertions on BASE/final | 3 expected BASE failures, 3 final passes | [BASE replay](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/original-red-baseline.jsonl), [final replay](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/original-red-final.jsonl) |
| New real-file regression controls on BASE/final | BASE 0 regressions/exit 0; final 9 failing cells/exit 1, grouped into R1-R3 | [BASE](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/adversarial-baseline-enforced.jsonl), [final](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/adversarial-final-enforced.jsonl) |
| Additional pre-write refusal, absence, clock and key checks | 10 controls passed, exit 0 | [recheck-clock.jsonl](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/recheck-clock.jsonl) |
| Actual public P7 preview/apply/repeat, both layouts | Exact target-only apply; prepared bytes match; repeat unchanged | [public-p7.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/public-p7.log) |

The first pytest attempt was stopped before tests by the review source-write guard: the real collection scanner tried opening its repository cache lock. Its output is retained in [focused.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-review-evidence/focused.log). The corrected external harness relocates only that cache and the shared test-venv lock/state paths. The real conftest, collection scan, fixture validation and tests remain enabled; the already valid cached test venv is only read. No dependency resync/install or gate disabling occurred.

The inspected parent offline policy remains on PYTHONPATH. Outer environments use an env-i allowlist, disposable HOME/USERPROFILE/XDG/APPDATA/LOCALAPPDATA/SPEC_KITTY_HOME/temp roots, sync=0, no bytecode and no git optional locks. The harness asserts sync=0 after per-test fixtures. WP01 public child helpers independently bind sync=0 last. No host credentials/global assets or production network were used.

## Scope Coverage

| Obligation | Assessment |
| --- | --- |
| T043 original preservation/no-churn RED and tidy-first | Verified original three RED assertions and separate validation-extraction commit |
| T044 lower-layer immutable preparation | Correct ownership/dependency direction; frozen bytes/tuples; no PackContext discovery, saver, VFS or generation path during preparation. R1/R3 invalidate full supported-input correctness |
| T045 actual writers/shared bytes/recheck | Existing compiler provisioner, save/update and pack manager route through shared writer. Observed config/pointer/target/seed identities and ancestor/absence state retained. R1/R2/R3 are introduced writer regressions |
| T046 preservation/idempotence/refusal | Extensive real assertions pass, but new BASE comparisons reveal the three missing coverage classes above |
| FR-001 | Pure preparation passes existing transient observer and whole-root snapshots; no unsupported whole-public-preview acceptance claim |
| FR-002/003 | Both ordinary layouts have nonempty intended/actual exact target agreement; absent .kittify directory/file creation also witnessed through compiler; R1 breaks valid successful outcome |
| FR-004 | Explicit [] and custom lists stay unchanged; repeated provisioning/shared save/update preserve bytes/mode/mtime |
| NFR-004 | FAIL: R2 authored comment lost; R1 leaves required authored document unreadable |
| C-001 | Pointer resolver, default loader, activation vocabulary and lower-layer boundaries retained; no duplicate upgrade-side YAML authority |

Additional recheck controls: absent config becomes present; config is rewritten with identical bytes; config mode changes; target becomes directory; parent mode changes; parent becomes link; target becomes link. Each refuses before any audited mkdir/open/chmod/write attempt, with the whole sandbox unchanged. Existing focused tests additionally cover config retarget, target content/same-byte rewrite/mode, seed changes, forged prepared bytes, invalid/missing defaults, dangling/unreadable/malformed targets and actual injected I/O failure.

The clock/absence control uses the real compiler on a project lacking .kittify: prepare under 2025, apply under 2030, exact retained bytes and SHA-256, exactly directory 0755 + config file 0644, then no-op repeat. No timestamps or paths are normalized. Existing seven faulty-outcome negative controls and transient-denial negative controls passed fresh.

No direct-file lock/temp/atomic protocol existed on BASE. This review does not demand a new one, cross-owner rollback, or race-free atomicity after the promised pre-write recheck. I/O errors remain exceptions; observations do not turn them into empty success.

## Public P7 and Remaining Gates

Fresh actual console subprocesses use same-version, warm G5 fixtures and nonempty real defaults, without a replacement Typer app/provider/compiler. Both legacy config and non-default pointed charter preserve the entire authored prefix. The whole project/home/temp net delta is exactly one independently chosen target update. Applied bytes equal the separately prepared bytes; second public apply has no changes, including mtimes. Complete receipts are in legacy-preview/apply/repeat and pointer-preview/apply/repeat under this review evidence root.

Both legacy JSON previews still emit ALLOW, empty pending_migrations and empty rendered_human while the lower owner knows provisioning is needed. Their raw snapshots are unchanged. This is retained WP10/WP13 composition work, not successful mission preview acceptance and not a new WP09 defect.

Worker evidence was inspected, not relabeled as fresh review: 3877 passed/9 failed/6 skipped broad run; eight retained WP01 public REDs (#3900-#3903) and the corrected uv-PATH harness test (separate 1 pass). The broad suite remains non-green. Its 1642 fast-test passes and 89 architecture passes are historical receipts; this review independently reran the specified architecture gates inside the 134-test selection.

Six broad skips remain explicit: three missing fd8f2b3c6906 directive-fixture checks, one absent directives.yaml fixture check, Linux /proc/self/fd, and native Windows os.replace behavior. Fresh 142/134 selections had no skips. macOS real link/mode/mtime and controlled absent-os.fchmod coverage passed; no native Windows/Linux validation claim.

## Generated Anti-Pattern Checklist

| Item | Result |
| --- | --- |
| Dead code | PASS: production call sites for exported additions; existing provisioner consumes compiler preparation; three required gates pass. WP10 import remains a pending cross-layer consumer |
| Synthetic-fixture test | PASS: real production/filesystem and actual public witnesses; patched historical app tests are not used as public purity evidence |
| Silent empty return | PASS: deliberate absent observation and no-op False have documented meanings; malformed required input generally raises. R1 is false successful write, not a caught-empty-return pattern |
| FR coverage | PASS for existence of scoped behavioral assertions; adequacy fails R1-R3, so this is not a claim of complete FR fulfillment |
| Frozen surface | PASS: seven authorized implementation/test files only; no shared gates/conftest/preview_support source edit |
| Locked decision | FAIL: R1/R2/R3 violate required valid/preserving, compatible owner behavior |
| Shared-file ownership | PASS: exact WP09 manifest ownership; no overlapping production file edits |
| Production fragility | FAIL: R3 introduces a spurious fail-loud refusal for supported, unchanged unowned data |

## Parent Handoff

REJECT WP09 until R1-R3 have real existing-entrypoint RED/GREEN fixes and targeted preservation/caller reruns. Preserve all current implementation and tests while correcting these defects in the authorized owner files. New checks belong in the existing four owned test files, not a new production module.

No approved WP10 API handoff is issued. The lower-layer seam is structurally appropriate, but integrating it before these writer defects are resolved would propagate them. Parent alone records the review verdict, reopens canonical task state as appropriate, coordinates WP10, and owns commits/publication.

