---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T18:17:43Z'
reviewer_agent: codex
wp_id: WP09
---

# WP09 Cycle-2 Independent Review

**REJECT**. Two P2 regressions remain. Original narrow R1-R3 controls pass, but
R2's comment-preservation repair is incomplete and valid explicit-key syntax
breaks an existing deactivation caller. Neither finding depends on unfinished
WP10 composition or public preview implementation.

## Review Identity

- Reviewer: reviewer-renata, independent read-only lane. Profile loaded via CLI
  using spk-doctrine-profile-load; charter review context loaded. Zero resolved
  context refs / unresolved governance (#3908) is not a governance pass; explicit
  canonical PRIMARY charter/contracts and the complete generated prompt apply.
- Canonical for_review event: 01M1VXZB8M62PHY8ZR5VQN9VAE.
- Canonical actionreview4934: terminal success. Its gate is NO_COVERAGE because
  no test command was configured, not PASS.
- Reviewed final: 4e72cedb49a13516fc1c0f12ff0a4d32b18d4c0d.
- Observed lane HEAD: b97dd3d408b7914815c1111a8ab37153b7670e84. Product/test source
  matches final; all seven frozen SHA256 entries verified.
- BASE comparator: c18531d304c4d71165c42aa35f07c134c6d76a90.
- Fresh prompt: [complete generated review prompt](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-review-prompts/spec-kitty-7aebe9a30bb5/upgrade-preview-mission-health-01M1V6E1/WP09/0da03d765cc34d66b0758c7c2e0af005.md).
  Updated handoff and original independent review read; original report preserved.
- Parent owns lifecycle verdicts, commits, integration and push. This report
  records review findings only; no lifecycle/Op/source changes were made.

## C2-R1: P2, Multiline Key Comments Are Silently Deleted

Location: [charter_yaml_io.py:261](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:261).

The blanket truncation of comments[2] to its first line assumes every subsequent
comment is a trailing separator outside the replacement span. A comment directly
between the key and its block collection is inside that span. It is removed
from the rendered document and removed from the original during replacement.

Minimal valid input:

```yaml
activated_directives: # rationale
# key detail
  - old
metadata: {}
```

Existing API:

```python
update_charter_yaml_section(path, "activation", {"activated_directives": []})
```

Actual final output:

```yaml
activated_directives: [] # rationale
metadata: {}
```

The call succeeds while deleting authored "# key detail". Replacing with ["new"]
also loses it. LF and CRLF reproduce. BASE retains the comment for all four
cells. The original single-line R2 test passes but does not cover this form.

This is also observable through the unchanged production caller
CharterPackManager().deactivate(ProjectContext(repo_root=project),
kind="directive", artifact_id="old"), both inline config and pointed charter.
Both calls report a successful removal while dropping the comment. BASE passes
the same caller assertions.

Contract: T044 step6 round-trip metadata/comments, T045 step8 existing
activate/deactivate behavior, T046 preservation. Preserve key-associated comments
inside replaced spans; distinguish them from separators actually left outside.
Add caller-level REDs for multiline comments before block lists/maps rather
than asserting only the first comment survives.

## C2-R2: P2, Explicit Owned Keys Break Existing Deactivation

Location: [charter_yaml_io.py:236](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:236);
replacement use at [charter_yaml_io.py:284](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-i/src/charter/activation/charter_yaml_io.py:284).

The replacement span starts at the key scalar rather than its complete mapping
entry syntax. With an explicit block key, it leaves the leading "? " in the
original while inserting a normal "activated_directives: ..." entry.

Minimal valid input:

```yaml
? activated_directives
: [old]
metadata: {}
```

The same existing update call to [] raises
"TypeError: unhashable type: 'CommentedSeq'". Updating to ["new"] raises
ParserError because the candidate begins "? activated_directives:" followed
by a block sequence. Both fail before writing, leaving original bytes intact.
This is honest refusal of the malformed *candidate*, but the authored input is
valid and was accepted by BASE. It is not the intentionally unsupported
flow-root deletion or an unowned alias-drift refusal.

Real CharterPackManager.deactivate also fails in both layouts. BASE removes
"old" successfully in both. LF/CRLF update controls give four final failures
against four BASE passes.

Contract: T045 step8 preserves existing activation/deactivation callers;
T044 step6 preserves valid round-trip input behavior. Bound replacement to
the actual complete entry, including explicit-key indicator syntax, and retain
real update/deactivation regressions for both layouts. Do not classify valid
authored YAML as malformed to waive this regression.

## Decisive Reproduction

All evidence is external. [Commands and environment](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/commands.md)
record exact invocations, source archives, plugin propagation and outputs.

```sh
sh /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/isolated.sh \
  env PYTHONPATH=/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence:/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp02-policy PYTEST_PLUGINS=gate_plugin \
  .venv/bin/python /var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/cycle2_regressions.py
```

Final: exit1, eight failing controls. Append "baseline": exit0, zero failures,
same eight assertions against archived BASE. No mocked serializer, replacement
writer or new-API existence assertion.

[Final minimal controls](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/regressions-final.jsonl),
[BASE controls](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/regressions-base.jsonl),
[real deactivation failures](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/deactivation-final.jsonl),
[BASE deactivation controls](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/deactivation-baseline.jsonl).
The deactivation script independently gives final exit1/four failures and
BASE exit0/zero failures.

The broader exploratory matrix completed 62 cells: 54 passed, eight failed in
these same two classes. Its exit0 means recording completed, not a green gate.
Its BASE run also checks newly promised exact-span/no-churn behavior, so its 44
old failures are not a clean regression comparator. The narrowed controls above
remove those unrelated expectations and establish introduced failures directly.

## Original Findings And RED Lineage

- Original R1: explicit null, tilde and empty document framing now produce valid
  mappings in both layouts, rather than successful invalid writes.
- Original R2: original single-line key-comment reproduction now passes.
  Multiline continuation remains broken as C2-R1.
- Original R3: numeric unowned key42 now remains intact in both layouts.
- Fresh original-reproduction script reports zero of the previous nine failing
  cells. Original authored-span and no-churn controls also return true.
- Archived 23c8dbcd25b9dfbce653545da7700c7decf5563d independently reproduces
  nine committed assertion failures; identical initial assertions pass final.
- Archived 0809227bfa9165081eaa33633699c8d02b661729 reproduces four
  block-to-empty failures and four flow passes. Final LF/CRLF block/flow
  collection-boundary matrix passes in fresh pytest.
- These archived assertion invocations are not advertised as pytest runs.
  Original d6095bda RED/tidy/portability lineage remains in the preserved
  cycle-1 report/evidence; no history rewrite or new RED lifecycle action.

## Fresh Verification

- **324 passed, 1 warning, 285.33s**: all four owned test files, both selected
  real deactivation/activation callers and three architecture suites.
  [Fresh focused log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/focused.log).
- Ruff check all seven: pass. Ruff format check: seven already formatted.
  Strict mypy, --follow-imports=silent, all seven: pass.
  [Mypy log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/mypy.log).
- Independent seven prewrite controls: appearing absent config, same-byte config
  rewrite, config mode, destination directory replacement, parent mode,
  parent symlink and destination symlink. Each refuses with zero write attempts
  and unchanged whole-root snapshot.
- Independent delayed-clock apply: prepare with absent .kittify in 2025, apply
  in 2030; exact retained bytes/hash, directory0755/file0644, no-op repeat with
  unchanged snapshot. No timestamp normalization.
- Independent unknown section/key controls refuse before any write. Owned tests
  additionally cover real changed seed/config/pointer/target/mode/parent inputs,
  malformed/dangling inputs, no-op/no-seed explicit empty vs absent, transient
  write-observer negative controls and defective-application negative controls.
- Null/comment/document framing, numeric/tagged/complex keys, anchors/aliases,
  inherited merge keys, CRLF and block/flow empty boundaries have fresh owned
  tests and independent real-file probes. Coverage is not universal proof:
  the two uncovered cases above block approval.
- Fresh real public P7 console preview/apply/repeat: both legacy and pointer
  layouts pass, exit0. Complete project/home/temp observations show one target
  update, exact separately prepared bytes, authored prefix retained and repeat
  unchanged. Preparation and preview remain read-only for these bounded fixtures.
  [Public receipts summary](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp09-cycle2-review-evidence/public-p7.jsonl); complete raw receipts
  under legacy-preview/apply/repeat and pointer-preview/apply/repeat in the same
  evidence directory. Preview still advertises empty pending_migrations and
  rendered_human; this is NOT public-preview completeness approval.

## T043-T046 Assessment

- T043: original existing-entrypoint RED evidence retained, cycle-2 and late
  boundary RED independently reproduced; no API-shape-only proof.
- T044: lower charter owns preparation, canonical pointer/default policy and
  immutable bounded values. No specify_cli/tool_surface import or new VFS.
  Reads/no-op/missing-key distinction work. Comment preservation incomplete.
- T045: shared actual writer consumes exact prepared bytes; full observed-input
  recheck and same-byte rewrite refusal work. Existing direct-file write
  boundary remains, with no invented atomicity/lock/rollback promise.
  Existing deactivation behavior regresses in C2-R1/C2-R2.
- T046: substantial fresh exact-delta/preservation/refusal coverage passes.
  Two independently witnessed input classes remain uncovered and broken.
- Product/test scope remains exactly compiler, pack_manager, charter_yaml_io and
  the four owned test files. Parent lifecycle/task changes in ancestry are not
  implementation scope expansion. Final tracked/untracked checks clean.

## Evidence Limits And Parent Handoff

Worker 1642 Make, timing1, broad3953/6skip/10fail and serial2pass/2fail are
inspected worker evidence, not fresh independent whole-suite runs. No redundant
whole broad run here. Broad final is not green: six historical assertions plus
four execution failures; serial rerun resolves cold-init/concurrency failures
and reaches the two actual human-preview mutation assertions.

Eight original public REDs (#3900-3903 and associated acceptance work) remain
unwaived for WP10/WP13 integration. No public-preview or full-mission acceptance
approval. Those known gaps do not excuse either introduced WP09 regression.

Six broad skips remain explicit: Linux /proc/self/fd, native Windows
read-only os.replace behavior, three absent synthesizer fixture cases and absent
directives.yaml fixtures. Controlled absence of os.fchmod passed in the owned
suite; this is not native Windows proof. No native Linux/Windows/wheel claim.

Warm lane Python3.11.15 was used directly. No uv sync/install/network/host
credentials/global assets were used. Offline policy inspected; sync forced0
including children. Exported pytest plugin has controller and all four worker
receipts, source-write refusal and relocated external caches. Existing fixtures,
scanners and assertions remain enabled.

No approved WP10 API handoff: owner remains rejected. The intended seam remains
prepare_mission_type_activations(project) -> immutable projection plus
PreparedYamlWrite, followed by its rechecking apply path. WP10 must not treat
this report as approval or claim public-preview completion.

Parent should return these two findings for bounded fixes and real caller REDs,
then request another independent review. Parent alone records lifecycle verdict,
commits, integration and push. Original independent report is unchanged.
