---
work_package_id: WP11
title: Provenance-preserving corpus recovery
dependencies: []
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-004
- C-006
planning_base_branch: codex/upgrade-preview-mission-health
merge_target_branch: codex/upgrade-preview-mission-health
branch_strategy: Planning artifacts for this mission were generated on codex/upgrade-preview-mission-health. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into codex/upgrade-preview-mission-health unless the human explicitly redirects the landing branch.
subtasks:
- T054
- T055
- T056
- T057
- T058
- T059
history: []
agent_profile: python-pedro
authoritative_surface: kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/
create_intent:
- docs/archive/program-evidence/upgrade-preview-mission-health-01M1V6E1/recovery-receipt.json
execution_mode: planning_artifact
owned_files:
- kitty-specs/R2-T1-local-legacy-removal/**
- kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/**
- kitty-specs/doctrine-drg-silent-drop-boundary-01M0PE7E/status.json
- kitty-specs/symbolkey-source-module-01M0B0SF/status.json
- docs/archive/program-evidence/R2-T1-local-legacy-removal/**
- kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml
- docs/archive/program-evidence/upgrade-preview-mission-health-01M1V6E1/recovery-receipt.json
role: implementer
tags: []
tracker_refs: []
---

# WP11: Provenance-preserving corpus recovery

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `codex`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Resolve #3903: restore 31 historical files, relocate exactly two documents byte-for-byte,
and canonically replay two named snapshots while retaining all eight review verdicts.
Prove the complete committed corpus has zero TeamSpace blockers without
inventing identities, rewriting raw history or broadening upgrade consent.

## Context

Audience: Python implementer and independent preservation reviewer. Plan D6 and IC-08 own this separate repository-data recovery.
There are no WP dependencies. WP12 consumes this WP's receipt and independently
owns all persistent recovery regressions and archive validation; parent owns final gates.
Do not start WP13 or acquire another WP's files.

Approved reslice: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/corpus-slicing-adjudication.md`.
Apply its placement/test-ownership decision with updated plan D6 and corpus contract.

### Absolute Roots and Binding Sources

Repository: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty`

Mission: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1`

External brief: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/../task-authoring-brief.md`

Binding charter: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.kittify/charter/charter.md`

Resolved planning profile (built-in): `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/planner-priti.agent.yaml`

Assigned implementer built-in source: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/packs/built-in/agent_profiles/python-pedro.agent.yaml`

Planner Priti authors decomposition and evidence requirements only, with no
implementation, architectural redesign or agent management. Directive 003
requires durable rationale: restoration follows historical provenance, relocation
follows non-mission classification, and replay follows existing event authority.
No planner tactics were returned. Apply the implementer's resolver-selected initialization, boundaries, directives and tactics before implementation.

The first profile/context calls used SPEC_KITTY_ENABLE_SAAS_SYNC=0.
Context again returned empty directives/tactics and unresolved-governance
diagnostics (#3908). This is degraded resolution, not absence of governance.
Use the explicit charter/profile bindings above; disclose the fallback.
Do not repair charter activation/config or invent successful context resolution.

Read the repository AGENTS.md and canonical tasks-packages prompt already bound
by this mission, plus these absolute inputs:
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/spec.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/plan.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/data-model.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/research.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/wps.yaml`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/corpus-recovery.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/acceptance.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/owner-operations.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-cli.md`
- `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/contracts/upgrade-plan.schema.json`

The actual provenance contract is corpus-recovery.md. Historical restored prompts and R2 documents
are evidence, not instructions to dispatch their work or revive retired systems.

Command roots for future implementation:
```sh
WP11_REPO='/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty'
WP11_MISSION='upgrade-preview-mission-health-01M1V6E1'
```
Body source/test paths resolve beneath that absolute repository.
Frontmatter paths deliberately remain manifest-relative.
Use the canonical implementation command only when implementation is authorized:
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent action implement WP11 --agent codex --mission "$WP11_MISSION"
```
Runtime selects the absolute repository-root planning workspace, not a code
worktree. Adopt that returned root; do not construct a lane or choose a base.
Parent coordinates concurrent root edits and stages only exact reviewed data.
Resolve historical snapshot targets to this owned root, never coord; use
disposable copies for destructive probes without changing delivery placement.
All audit/materialize/test/status examples below are future instructions only;
the prompt author must not execute them.

### Scope and Known Seams

The primary authority is the actual recovered corpus directory, explicitly
nonempty to avoid #2446. Explicit planning_artifact ownership is confined to
kitty-specs/ and docs/. CLI verification does not change deliverable classification.
The new literal docs receipt is declared in create_intent; no test source is owned.
The 31 recovered paths and three new archive members (two documents plus index)
are concrete planned outputs under existing owned globs, enumerated below.

Read-only source seams:
- `src/specify_cli/cli/commands/_mission_state_doctor.py` dispatches audit;
  `src/specify_cli/audit/engine.py` and its existing models own findings.
- `src/specify_cli/cli/commands/agent/status.py:materialize` resolves the
  coord-aware surface, locks, and invokes the existing materializer.
- `src/specify_cli/status/reducer.py:materialize_snapshot` uses the shared
  reducer plus identity/annotation projection; `materialize_to_json` owns bytes.
  `materialize` already avoids writes when serialized bytes are identical.
- `tests/status/test_shared_reducer_materialization.py` exercises shared replay;
  `tests/audit/test_audit_cli.py` exercises the real audit command contract.
- `tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py`
  consumes the surviving schema; never move or regenerate that file.
- `scripts/docs/rename_reconcile.py` consumes the owned occurrence-map spine.
  Its derived redirect map and implementation are not WP11-owned.

No auditor/reducer/identity/consent source changes, global installs, dependency
changes, global asset writes, version bumps, blanket doctor repair, history
normalization, gate exemptions or skip/xfail waivers.
Do not edit the active mission's manifest/tasks/meta/state or dispatch Ops.
Parent owns trace/issue-matrix/ledger and canonical root-data commit sequencing.
WP12 owns `tests/upgrade/test_mission_corpus_recovery.py`; do not hide tests in docs.
Use only the two named old status.json paths for planned snapshot correction.
The old cyclic mission's metadata/tasks/events are restored byte-for-byte,
not newly authored lifecycle state.

### Subtask T054: Capture original corpus audit and exact historical blob/mode/event provenance

**Purpose**: Witness the actual defect before recovery and establish independent,
nonempty preservation inputs that later output cannot redefine.

**Steps**:
1. Inspect owned data and existing audit/replay/test seams first. Record any
   focused tidy-first needs; immutable historical documents cannot be cleaned up.
   No source refactor is necessary or authorized for this data-only repair.
2. Capture baseline HEAD, dirty scope, executable/distribution/module identity,
   absolute checkout, effective environment and unfiltered corpus inventory.
   Preserve external evidence without turning a runtime success claim into data.
3. Through the unchanged public executable, run the full corpus audit in an
   isolated copy of the real baseline corpus. Assert the final desired contract,
   zero blockers, so it is genuinely RED before recovery.
4. Identify both original identity failures and both snapshot drifts by mission
   and actual finding code. Record process exit and complete JSON; a crash,
   missing fixture/receipt or unknown option is not #3903 RED evidence.
   Historical four-blocker/424-directory counts are observations, not a scan cap.
5. Retain actual pre-data CLI RED and focused missing-history/drift observations.
   Pin the untouched baseline for WP12's persistent original-state tests; do not
   recover data during probe setup or substitute retrospective RED claims.
6. Hand baseline SHA, exact commands/assertions/output hashes and probe recipe
   to WP12 before data approval. WP12 commits durable regressions in its own
   workflow; WP11 does not wait for that future file or author test programs.
   No xfail, conditional success on absent files or retry-to-green.
7. Read historical Git trees/blobs, not guessed identity templates. Source:
   `3442ca1afc20b1b83b27a7bc64fd7014050b12a1`; convergence:
   `2554bd13adc289d3457681308645fe52619bca0e`.
   Recheck the path-scoped diff against convergence's first parent is empty.
8. Capture the two current event SHA-256 values and complete per-WP verdict
   objects before replay. Preserve meta, IDs, event order/count, annotations,
   force provenance, lane values, mode and pre-recovery snapshot bytes.
   Never fill absent historical model/provider fields with invented values.

**Files**: Inspect corpus/source read-only; retain pre-data evidence for the
owned docs receipt in T058 and WP12's persistent regression handoff.

**Validation**: A real public audit failure and focused missing-history/drift
assertions precede data edits. Historical tree has 32 nonempty path entries,
including one zero-byte file; current retained set is the single schema.
Source-object failure is a prerequisite blocker, not an empty baseline pass.

### Subtask T055: Restore 31 original cyclic-mission files, retain schema/identity/history

**Purpose**: Recover the original mission record exactly rather than fabricate
enough metadata to silence identity audit.

**Steps**:
1. Pin the original mission ID `01M0QCK4D9D65AVNC15HKWAQZ7`.
   Keep created_at `2026-08-23T13:22:37.098012+00:00`,
   accepted_at `2026-08-23T17:12:57.441258+00:00`, acceptance history,
   authorship and original raw 71-row event stream unchanged.
2. Recheck every destination with lstat before recovery. A newly present,
   divergent file is a conflict; do not overwrite it. Reject escaping parents.
   Matching existing files on a repeat run are verified and left untouched.
3. Restore exact blob bytes and Git modes using the parent's bounded Git/blob
   workflow. No checkout/reset of the entire corpus or current worktree.
   The approved restore set is the historical tree minus the surviving schema.
4. Preserve `contracts/lane-dependency-cycle.schema.json` at its current path
   and blob `26cb3b8bafde72894f0d1ec0a9c1701cd511f497`.
   Its unchanged consumer must still parse and validate the same schema.
5. Verify all 31 blobs/modes before any possible replay. Compare against Git,
   not against hashes collected only from the just-restored working tree.
6. Preserve historical spelling, legacy fields, review evidence and nested
   dossier layout. Do not regenerate templates, mission ID, tasks or raw events.

**Files**: Exactly these relative paths under
`kitty-specs/reject-cyclic-lane-graphs-01M0QCK4/`:
```text
.kittify/dossiers/reject-cyclic-lane-graphs-01M0QCK4/snapshot-latest.json
acceptance-matrix.json
adversarial-review.md
analysis-report.md
checklists/requirements.md
data-model.md
decisions/DM-01M0QCNTD5CM0SE0HKQ79C9NF6.md
decisions/DM-01M0QDJWKXD5JHSVHV0NWSJDWM.md
decisions/DM-01M0QEAKZVM8QAVZPF9AE6D1N8.md
decisions/index.json
issue-matrix.json
lanes.json
meta.json
mission-review.md
plan.md
pr-summary.md
quickstart.md
research.md
retrospective.yaml
spec.md
status.events.jsonl
status.json
tasks.md
tasks/.gitkeep
tasks/README.md
tasks/WP01-authoritative-domain-cycle-gate.md
tasks/WP01-authoritative-domain-cycle-gate/review-cycle-1.md
tasks/WP01-authoritative-domain-cycle-gate/review-cycle-2.md
tasks/WP01-authoritative-domain-cycle-gate/review-feedback-1.md
tasks/WP02-finalization-diagnostics-and-persistence.md
tasks/WP03-determinism-performance-and-regression.md
```

**Validation**: Exact set equality, 31 restored plus one retained schema.
Check blob IDs, raw SHA-256, modes, original identity/timestamps and all event
bytes; include the zero-byte .gitkeep and hidden nested dossier.
A metadata-only recovery must fail the independent check and WP12 regression.

### Subtask T056: Exact two-document relocation, protected archive index and live-reference mapping

**Purpose**: Remove the non-mission bundle from immediate mission scanning
without discarding documents, misrepresenting identity or breaking provenance.

**Steps**:
1. Reconfirm the two R2-T1 files are program evidence, not an actual mission.
   Introduction commits are `0be7d692adcc71503ad1c3b0ad6b0d16accdef62`
   (deletion manifest) and `557a55946d9a23f0c4f7bf4311eb02bb8d3d04cb`
   (attribution notes). Capture current pinned source blobs/modes as well.
2. Move `kitty-specs/R2-T1-local-legacy-removal/deletion-manifest.md` to
   `docs/archive/program-evidence/R2-T1-local-legacy-removal/deletion-manifest.md`.
   Move `kitty-specs/R2-T1-local-legacy-removal/commit-history-notes.md` to
   `docs/archive/program-evidence/R2-T1-local-legacy-removal/commit-history-notes.md`.
3. Verify destination absence/confinement and exact bytes/mode before removing
   either source. Divergent destinations or extra source members require
   diagnosis; never delete a whole directory to conceal unexpected contents.
4. Remove the now-empty old directory only after both moves verify.
   Leave no stub, symlink alias, placeholder or synthetic meta.json under
   kitty-specs; any such immediate child could perpetuate the audit failure.
5. Create `docs/archive/program-evidence/R2-T1-local-legacy-removal/README.md`
   as a separate archive index, approximately 30-70 lines. Record classification,
   source commits, old/new mapping and relative-reference context. Mark the two
   originals immutable historical evidence; keep all old document bytes intact.
6. Scan tracked references across the repo. Classify active consumers versus
   historical quotations; do not rewrite historical records. Report a genuine
   zero-hit scan explicitly. Route out-of-map active edits through their owner.
7. Append only the two exact moves to the existing owned occurrence-map spine
   in its current from/to/reason format. Preserve all prior entries/comments.
   Inspect the reconciliation consumer's destination-directory convention.
   Any required derived redirect update is parent/owner work, not permission
   to modify scripts/docs/redirect_map.yaml or weaken the reconcile gate.
8. Protect the new index too: capture its reviewed bytes/hash/mode in the
   receipt, and ensure unexplained later alteration fails validation.
   It is additional context, not a loophole to change the relocated originals.

**Files**: Two source deletions, two destination additions, new README.md and
`kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml`.
No source, docs navigation or historical reference edits outside ownership.

**Validation**: Two exact byte-identical relocations, exact destination paths,
no residual old bundle and no lost reference context. Repeat is a verified
no-op; old occurrence entries remain intact. A move to a wrong destination or
an edited attribution sentence must fail even if corpus audit becomes green.

### Subtask T057: Scoped canonical materialization of two snapshots, preserve all eight verdicts

**Purpose**: Correct derived snapshots through the event authority while proving
review metadata and immutable history survive unchanged.

**Steps**:
1. Recheck these exact event inputs before mutation:
   doctrine-drg-silent-drop-boundary-01M0PE7E SHA-256
   `518d572629a39d026341d0cc26f47cc1a87c5f3323e21c5b8759cd0a02477b20`;
   symbolkey-source-module-01M0B0SF SHA-256
   `7e0326d9d1a9af04f3d1ce353e0b97caba765aab298de01074df4b889a455aaf`.
   A changed input requires adjudication, never silently repinning the receipt.
2. Resolve each mission's actual status partition at the runtime-selected
   planning root. Verify the exact root-owned historical path before writing;
   a mission selector alone does not exclude coord or an unrelated checkout.
3. Capture all five doctrine and all three symbolkey complete review_result
   objects and done lanes, not just verdict strings or counts. Record
   transition IDs, last event identity and annotation provenance as baselines.
4. Run the two canonical commands below, one mission at a time. Inspect the
   actual written path and resulting diff after each. Locks/temporary files are
   infrastructure to observe, not permission to edit events or another mission.
5. Independently compute expected snapshot bytes with the existing
   `materialize_snapshot` and `materialize_to_json` read/serialization seams
   from pinned meta/events in a disposable copy. Compare exact output bytes.
   Do not compare only the command's own stdout with its written status.json.
6. Require doctrine mission_type to become software-dev and retain all eight
   complete verdict objects, done lanes and immutable identity metadata.
   Preserve raw events byte-for-byte, including annotations and unknown fields.
7. Repeat each canonical materialization. Require identical bytes/mode/mtime
   for the two snapshots and unchanged event/meta/history files.
   Do not hand-write status JSON to obtain the expected output or timestamps.

**Future scoped commands**:
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent status materialize --mission doctrine-drg-silent-drop-boundary-01M0PE7E --json
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent status materialize --mission symbolkey-source-module-01M0B0SF --json
```

**Files**: Only the two manifest-listed status.json paths.
No raw event, old meta, reducer, auditor, coord state or verdict edits.

**Validation**: Canonical replay equality plus independent baseline preservation.
The planned correction set is exactly two snapshots. If the restored cyclic
snapshot exposes new drift, retain its historical blob proof and report it to
the parent for the contract's separately recorded, scoped replay disposition;
do not silently add a third replay or weaken the full-corpus gate.

### Subtask T058: Independently check repeat bytes/mtime, receipt and negative preservation controls

**Purpose**: Deliver a portable evidence receipt that an independent consumer
can verify rather than trust as a self-approved archive exemption.

**Steps**:
1. Create `docs/archive/program-evidence/upgrade-preview-mission-health-01M1V6E1/recovery-receipt.json` as evidence,
   not runtime state or an executable apply token. Record its schema/version
   explicitly and use stable repo-relative paths for portable comparisons.
2. Include source/baseline commit identities, the exact 31 restore entries
   with Git blob IDs/modes/SHA-256, the retained schema proof, two old/new
   relocation pairs and their introduction/current-source provenance.
3. Include both replay input hashes, metadata provenance, before/after snapshot
   hashes, canonical command and reducer provenance, full eight verdict objects,
   done-lane identity map and repeat-run evidence. Retain raw evidence locations
   or hashes; do not fabricate absent history or claim unexecuted commands.
4. Include the archive index hash/mode and exact occurrence-map delta.
   Record full audit outcome and corpus inventory identity separately from
   targeted checks. No user-home credentials or machine-dependent paths in
   the portable data contract; exact invocation cwd belongs in external evidence.
5. Independently validate the receipt against trusted Git objects and
   current lstat/content, exact contract path sets, pinned event streams and
   independently computed canonical replay. Reject duplicates, unknown actions,
   omissions, extra paths, absolute/traversal paths, wrong modes and escaping links.
6. Do not generate expected hashes from the output under test and call that
   independent validation. A forged receipt and matching corrupted output must
   still fail against historical objects or pinned baseline event hashes.
7. Exercise negative controls in disposable copies: omit one restored blob;
   change old ID/date/event bytes; move a document to a wrong path; edit a
   relocated byte; alter the index; drop/change one review reference/reviewer;
   write a noncanonical snapshot; replace a destination parent with a link.
8. Include same-bytes mtime rewrite and an unrelated archived-file edit as
   negative controls. The approved recovery diff must have exact membership;
   receipt presence cannot authorize arbitrary changes elsewhere.
   Each mutated case must fail and its unmutated control must pass.
9. Verify repeat restore/relocation/replay leaves persistent content and mtimes
   unchanged. Missing source after a completed move is only valid when the
   exact destination and pinned provenance verify, never unconditional success.

**Files**: New owned docs receipt only; no persistent Python test or hidden program.
Use read-only checks/disposable counterfactuals; inventory actual files independently
of receipt-listed paths. Preserve recipes and outputs for independent data review.
Transfer every original/corrupted-state assertion above to WP12's durable test,
including forged receipt plus candidate and post-landing receipt/index/result edits.

**Validation**: Nonempty exact 31/2/2/8 evidence, canonical replay and independent
object verification. WP12 and a separate reviewer revalidate the receipt.
WP11 cannot approve its own preservation exemption or weaken the archive gate.

### Subtask T059: Full corpus zero-blocker audit and portable evidence; no blanket doctor repair

**Purpose**: Prove the real corpus is healthy and hand off reproducible evidence,
with separate consent and unrelated historical data still preserved.

**Steps**:
1. Run the full public audit from the repaired runtime-selected planning root, then repeat
   against the final committed recovery tree after the parent's scoped commit.
   Do not use --fixture-dir, --include-fixtures, a mission filter or four-directory
   replacement as the final full-corpus witness.
2. Require process 0 and repo_summary.teamspace_blockers == 0. Parse complete
   stdout as one JSON object and retain all findings/corpus membership.
   Verify the restored mission is included and the relocated bundle is absent;
   an empty scan or four missing names is not success.
3. Compare against the baseline inventory and all four original findings.
   New blockers require diagnosis and owner disposition; do not relax thresholds,
   edit unrelated metadata, or run global/mission-scoped doctor --fix.
4. Run focused data checks and existing audit/status/consent/schema-consumer
   tests below. WP12 owns new-test lint/types and full recovery test integration.
   Provide pinned original and corrupted corpus probe recipes/evidence to WP12
   for the parent's public upgrade --yes negative-consent witness.
   Existing positive explicit-consent coverage must remain reachable.
5. Preserve all event/meta/verdict sentinels during consent-negative checks.
   A setup crash or pre-consent short circuit is not proof of consent denial.
   WP10 owns consent source/tests; route defects there without acquiring them.
6. Report exact commands, cwd, executable/source/commit provenance, counts,
   exits, raw output hashes, receipt hash and mutation-control results.
   Parent owns issue-matrix #3903 closure, tracers and final integrated gates.
7. Known #3911 archive-gate conflict remains WP12's responsibility. Supply
   evidence and seek independent review; a tracked red is not a passing gate.
   Do not claim parent CORE/E2E/wheel or WP13 acceptance has run.

**Future full audit**:
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" doctor mission-state --audit --fail-on teamspace-blocker --json
```

**Future focused and subsystem checks**:
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/pytest" -c "$WP11_REPO/pytest.ini" "$WP11_REPO/tests/specify_cli/cli/commands/agent/test_finalize_lane_dependency_cycle.py" "$WP11_REPO/tests/cli/commands/test_doctor_mission_state.py" "$WP11_REPO/tests/upgrade/test_teamspace_consent_scope.py" -v -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/pytest" -c "$WP11_REPO/pytest.ini" "$WP11_REPO/tests/audit" "$WP11_REPO/tests/status" -q -ra -p no:cacheprovider
SPEC_KITTY_ENABLE_SAAS_SYNC=0 make -C "$WP11_REPO" test-fast
```

Use the warm direct binaries; no uv sync or replacement environment. Before any child process, isolate HOME/USERPROFILE, XDG, APPDATA/LOCALAPPDATA,
SPEC_KITTY_HOME and temporary roots; clear escaping source/asset overrides.
Set child sync=0 last, use PYTHONDONTWRITEBYTECODE=1 and GIT_OPTIONAL_LOCKS=0.
Root conftest sets sync=1 and some targeted fixtures delete the variable:
parent must establish effective sync-off policy, not merely launch flags.
Do not disable conftest, silently skip affected tests, contact production SaaS,
or write real global assets. Record unresolved isolation prerequisites.
Run applicable existing archive/reference checks with parent/WP12 disposition;
no make test-full or independent gate-policy changes here.

## Definition of Done

- T054: actual pre-data public audit RED and pinned historical baseline evidence.
- T055: all 31 original blobs/modes restored; schema/ID/dates/events preserved.
- T056: exactly two byte-identical relocations, protected index and scoped mapping.
- T057: exactly two planned canonical snapshot corrections; eight verdicts retained.
- T058: independently validated receipt, negative controls and repeat no-churn proof.
- T059: full committed-corpus audit exits 0 with zero blockers; required checks
  and independent data review are supplied, with no fabricated gate success.
- WP12 receives all persistent original/corrupted counterfactual test obligations;
  its future regression file is not a prerequisite invocation for WP11 approval.

Subtask completion is an event-sourced record, not a ticked checkbox.
Only after evidence exists, use canonical
`spec-kitty agent tasks mark-status <Txxx> --status done`.
These instructions must not be executed during prompt authoring:
```sh
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent tasks mark-status T054 --status done --mission "$WP11_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent tasks mark-status T055 --status done --mission "$WP11_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent tasks mark-status T056 --status done --mission "$WP11_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent tasks mark-status T057 --status done --mission "$WP11_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent tasks mark-status T058 --status done --mission "$WP11_MISSION"
SPEC_KITTY_ENABLE_SAAS_SYNC=0 "$WP11_REPO/.venv/bin/spec-kitty" agent tasks mark-status T059 --status done --mission "$WP11_MISSION"
```
Let canonical resolution choose the status partition. Never manually write
runtime events/snapshots, claim review approval or use Op dispatch.

## Risks

- Historical-object absence: fail explicitly; never substitute regenerated files.
- Broad globs: authorize only enumerated recovery, not opportunistic archive edits.
- Misplaced replay: inspect resolved output roots; never fix by editing coord.
- Receipt self-certification: pin original objects and rederive canonical outputs.
- New corpus blockers: preserve evidence and escalate; zero remains the gate.
- Rename reconciliation may need another owner; no hidden out-of-map writes.
- Archive-gate disagreement is not permission to skip, repin or self-approve it.

## Reviewer Guidance

Reproduce RED before recovery and independently compare final data with pinned
Git blobs, not just receipt claims. Check exact 31/2/2 membership and all eight
complete verdict objects, including references/reviewers and raw annotations.
Verify the retained schema consumer, zero-byte file and hidden dossier survive.
Require independent no-churn and mutation witnesses; reject metadata-only fixes,
empty corpus scans, arbitrary receipt exemptions and historical byte rewrites.
Confirm full-corpus audit uses the final committed tree and zero blockers.
Keep WP12's preservation decision separate from this WP's evidence production.
Return exact review findings and commit evidence to the parent; do not start WP13.
