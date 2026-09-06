---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T18:48:19Z'
reviewer_agent: codex
wp_id: WP06
---

---
type: reference
audience: agentic-framework-core-team
updated: 2026-09-06
---

# WP06 Independent Review

Verdict: REJECT

Reviewed delivery: `1626c9fc4a9c52bfea6836ea325189346572cb0f`.
Three blocking findings remain against the actual PRIMARY T029-T033 contract.
The original edited-orphan fix and canonical org-health consumer fix have genuine
independent RED/GREEN evidence. Those successes do not satisfy the remaining
corrupt-state, truthful partial-result, and shared-owner obligations.

## Findings

### 1. [P1] Malformed manifest fields become complete assessments

Source: [manifest.py:85](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-f/src/specify_cli/tool_surface/profiles/manifest.py:85),
[manifest.py:170](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-f/src/specify_cli/tool_surface/profiles/manifest.py:170).
The new entry validation checks only that an entry is a dict, then delegates to
an existing decoder that coerces required values with `str(...)`; optional
string fields also stringify lists/dicts. Corrupt records therefore survive
loading instead of blocking the owner.

Fresh reproduction first installs real Claude profiles using existing
expand/probe/repair, parses the generated manifest, and changes exactly one field
in its first entry. Each of `profile_urn=null`, `tool_key=[]`,
`output_path=null`, `source_layer={}`, and `file_hash=[]` produces
`complete=True` with no error diagnostic. The output_path/source_layer cases
also propose one manifest update; the other three incorrectly report complete
zero-effect assessments. Unmodified canonical-manifest control passes with
complete/no effects. Snapshots prove assessment itself stays read-only.

This violates PRIMARY T030 step 7 and T033 step 9, plus owner-operations'
required corrupt-state refusal. Unsafe legacy paths may be preserved as
non-authorizing evidence, but structurally malformed JSON fields are not valid
legacy records. Validation needs to distinguish the two before coercion.

Baseline attribution: the same five loader checks fail against exact baseline
`fa0baabd6abd3e76587988cabfc49ff5ceb8456b`; the healthy control passes.
This is an inherited decoder gap left open by WP06's newly promised validation,
not a claim that WP06 introduced the old coercions. Baseline failure does not
waive the explicit contract.

Raw evidence:
[adversarial-canonical-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/adversarial-canonical-final.log),
[manifest-baseline.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/manifest-baseline.log).
Reproducer: [review_controls.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/review_controls.py), modes
`adversarial` and `manifest-load`.

### 2. [P2] Late confinement race escapes after writes and loses partial results

Source: [agent_profiles.py:837](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-f/src/specify_cli/tool_surface/providers/agent_profiles.py:837),
[_paths.py:80](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-f/src/specify_cli/tool_surface/profiles/_paths.py:80).
The write loop catches only `OSError`, while its per-effect confinement check
raises `ValueError`. A parent changed to a symlink after the whole-batch check
therefore escapes the owner and WP02 dispatcher, discarding the accumulated
success/failure result.

Fresh reproduction assesses a real Claude/Codex batch. At the existing writer
seam, immediately before the first Codex file write, the control renames
`.codex/agents` into a sandbox sibling and substitutes a symlink. The original
writer then refuses confinement. Before the exception, 29 actual effects had
succeeded, including 24 Claude files; the manifest was still absent.
The caller receives `ValueError: Unsafe profile parent: .../.codex/agents`,
not an `OwnerApplyResult` describing those partial writes.

Refusing the unsafe path is correct. Losing the partial result violates T032
step 7 and D5. This does not request cross-owner rollback or guarantee zero
writes for a race occurring after execution starts. The owner needs a truthful
bounded failure result for its own expected confinement/type errors.

Baseline attribution: these prepared writer/apply functions are new in
`b82807a1c673c56df4133fb40913af7d4f9a7469`; the baseline has no assessment/apply
protocol to replay. No missing-method failure is offered as behavioral RED.
The final failure is non-vacuous actual-I/O evidence. Healthy mixed
drift/missing Claude/Codex apply and two repeats pass.

Raw evidence:
[adversarial-canonical-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/adversarial-canonical-final.log),
`LATE_RACE_BEFORE_EXCEPTION actual_success_count 29 claude_files 24 manifest_exists False`.
Reproducer: [review_controls.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/review_controls.py), `late_parent_race`.

### 3. [P2] Shared orphan deletion drops an affected logical owner

Source: [agent_profiles.py:730](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-f/src/specify_cli/tool_surface/providers/agent_profiles.py:730).
Creation groups the real Copilot/VS Code projections and correctly reports both
logical owners. The manifest retains one canonical entry per output path.
Pruning later reports only `(entry.tool_key,)`, losing the other selected
logical owner and its surface ID.

Fresh reproduction installs a real admitted org profile for
`("copilot", "vscode")`, verifies creation owners are both tools, then sets
activation to empty and assesses the same tools. The sole physical deletion
reports `("copilot",)` and only
`copilot.agent_profile.orgzilla-org-analyst.agent.md`.
Real apply succeeds and the independent physical delta matches; the separate
owner-set assertion fails. Thus physical equality alone does not cover T031
step 6 or the all-affected-owner contract.

This finding requires accurate in-process effect attribution through existing
renderer/selection authority, not a new profile-refcount schema or Vibe native
primitive. Retained/excluded-owner preservation remains a separate obligation.

Baseline attribution: logical PhysicalEffect reporting is new in WP06; the
baseline's original dry-run omission is independently retained below. No
synthetic baseline API failure is counted.

Raw evidence: [shared-prune-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/shared-prune-final.log).
Reproducer: [shared_prune_control.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/shared_prune_control.py).
The test performs real installation, deactivation, assessment, deletion, manifest
update and independent delta equality before the owner assertion fails.

## Scope and Frozen Identity

ROOT: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc`.
Read-only lane: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-f`.
Actual PRIMARY task: [WP06-profile-projection-assessment.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/kitty-specs/upgrade-preview-mission-health-01M1V6E1/tasks/WP06-profile-projection-assessment.md).

Read the full canonical fresh review prompt, all handoff sections, actual
PRIMARY task, applicable AGENTS/charter, mission spec/plan/research/data model,
WP06 manifest ownership, owner/acceptance/CLI/schema contracts and excluded
corpus scope. Read the supplier's independent review and inspected its exact
three-file diff. PRIMARY lines 272/363 govern the no-refcount/no-Vibe boundary;
the broad acceptance examples do not invent profile primitives.

Exact sequence:

| Role | Commit |
| --- | --- |
| Baseline | fa0baabd6abd3e76587988cabfc49ff5ceb8456b |
| Original test-only RED | e8f41b3c9b59e906375d07bde9241dee5d16db8d |
| Original GREEN | b82807a1c673c56df4133fb40913af7d4f9a7469 |
| Approved supplier RED / local | cd21392aedc851c8535c127f870a1c445d5b99dc / d6bfb2b33da43a982b2aec83b179848961e835f3 |
| Approved supplier GREEN / local | 251c4a7f2dbe6d571cdc6a4d0d0ad6340521cdbc / 92f6bc29ea57607486913cb829f6a16b83e6dee0 |
| Consumer test-only RED | 8de620afccf05612e30d73d67141ecd18ba9a1b6 |
| Reviewed final | 1626c9fc4a9c52bfea6836ea325189346572cb0f |

Both RED commits have empty production diffs against their immediate production
predecessors. Baseline-to-final changes are exactly eleven owned paths plus
the three approved supplier paths; see [delivery-paths.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/delivery-paths.log).
The supplier files are byte-identical to approved `251c4a7`;
[supplier-identical.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/supplier-identical.log) is empty/exit 0.

Lane HEAD was `50156a76cd01becdc2349475fe0990f1558650c2` during review.
Its difference from reviewed final is four coordination/status/review artifacts,
not production/test changes. The complete src/tests/packs/build-policy comparison
is empty/exit 0: [delivery-source-identity.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/delivery-source-identity.log).
All eleven author-frozen hashes reverified:
[final-source-hashes.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/final-source-hashes.log).
Final worktree status is clean. No source, lifecycle, status, coordination,
root-state, commit, push or merge writes were performed by this review.

## Governance and Isolation

Resolved builtin `reviewer-renata` through the canonical profile-load skill.
Applied its quality-gate initialization, correctness/security/standards focus,
code-review mode, no implementation/product/work-package management boundary,
and handoff to parent/implementer. Directives 001/024/030/032/041 and
test reconstruction/readability discipline informed this review.
No dependency change warrants an invented supply-chain approval claim.

Review-action governance still has `references_count=0` and explicit unresolved
directives (#3908). It is NOT successful empty governance. Applied actual
charter/AGENTS and PRIMARY contracts. Explicit `code-review-incremental`
tactic resolution returned substantive content and was read.
Logs: [reviewer-profile.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/reviewer-profile.json),
[review-governance.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/review-governance.json),
[review-tactic.json](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/review-tactic.json).

Read cycle2-commands.md and external wp02-policy/sitecustomize.py before tests.
Checked lane interpreter/owner/oracle import provenance and attempted parent
sync=1 and child sync=1: both remain 0. A non-loopback connect was rejected by
the installed guard. Runtime/test/static commands used env -i, isolated
HOME/USERPROFILE/XDG/AppData/runtime/tmp, source-bound PYTHONPATH,
PYTHONDONTWRITEBYTECODE=1, UV_NO_SYNC/UV_OFFLINE/PIP_NO_INDEX, sync=0 last.
Direct warm .venv only; no resync, credentials, real global assets or live SaaS.
Ordinary pytest retained repository conftest, including the observed sync guard
assertion after fixtures. Standalone external probes supplement it.

[policy-provenance.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/policy-provenance.log) and
[commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/commands.md) give runtime proof and replayable commands.
Policy protects Python non-loopback socket.connect and child sync; it is not an
OS/native-process firewall. Snapshot and Python audit evidence do not prove
universal native-syscall purity.

## Fresh Independent Evidence

| Check | Observed result | Raw log |
| --- | --- | --- |
| Both provider files, complete profiles tests, org resolver and org activation seam | 289 passed, 3 warnings, 159.09s; exit 0 | [focused.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/focused.log) |
| Exact original RED tests against baseline production | 1 intended edited-orphan assertion failure; unchanged-prune and omission controls pass; exit 1 | [original-baseline.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/original-baseline.log) |
| Same three exact original RED tests against final | 3 pass; exit 0 | [original-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/original-final.log) |
| Independent org health, consumer RED | 4 corrupt assertion failures, 4 healthy controls pass; exit 1 | [health-consumer-red.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/health-consumer-red.log) |
| Independent org health, final | 8 pass; corruption/recovery, admission, real apply/delta and two repeat checks per case; exit 0 | [health-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/health-final.log) |
| Canonical malformed-record, mixed repair, late race controls | 6 fail, 2 pass; exit 1, findings 1/2 | [adversarial-canonical-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/adversarial-canonical-final.log) |
| Baseline canonical manifest loader controls | 5 fail, 1 healthy pass; exit 1 | [manifest-baseline.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/manifest-baseline.log) |
| Real shared-alias prune | Owner assertion fails after successful physical delta check; exit 1 | [shared-prune-final.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/shared-prune-final.log) |
| Explicit eleven owned files Ruff | Pass; exit 0 | [ruff.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/ruff.log) |
| Strict mypy profiles/provider/both tests | 13 files clean; exit 0 | [mypy.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/mypy.log) |
| Unchanged directory formatter policy | 7 files formatted; exit 0 | [format-policy.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/format-policy.log) |
| Exact delivery diff whitespace check | Pass; exit 0 | [diff-check.log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-independent-evidence/diff-check.log) |

Counterfactuals load exact Git blobs for the owner/profiles/org resolver in
memory, with lane-bound filenames for canonical package lookup; all other
dependencies remain the matching lane versions. Logs print each frozen module
SHA256. These are scoped production counterfactuals, not full historical
checkout/installed-wheel runs. The original test source is exactly from
`e8f41b3`; failure reaches its original line 161 assertion, not import or API
absence. Independent health uses parsed but schema-invalid `roles: 123`,
supplementing the author's malformed-YAML case, across absent/include/exclude/empty.
Health is checked before truthiness; falsey corrupt admission still blocks.

The exploratory adversarial-final.log had a handwritten invalid format literal;
it was superseded by canonical install-then-corrupt controls, with a healthy
control. It is retained as harness history, not cited as product proof.

## Contract Assessment and Limits

| Contract | Evidence and disposition |
| --- | --- |
| T029 | Genuine original RED/GREEN verified; status-less dry-run omission still explicitly witnessed, not presented as fixed public reporting. |
| T030 | Real immutable prepared bytes/provenance, manifest/directory effects, no preparation writes, safe absent-manifest adoption, canonical org-health retention pass checked cells. Malformed record validation fails finding 1. |
| T031 | Unchanged/absent/edited/dangling/disabled/unselected/legacy/Q prune cells pass; no synthetic Vibe/refcount. Shared deletion attribution fails finding 3. |
| T032 | Destination/manifest/source/addition/removal/config/parent pre-write changes, exclusive creation, Q exclusions and sandboxed doctor Q, writer/unlink/manifest OSError controls pass. Late confinement failure loses results: finding 2. |
| T033 | Nonempty create/manifest/delete effects, exact bytes and physical delta, Claude/Codex shared manifest, two no-churn repeats, omission/drift/mtime/owner negative controls pass their actual cells. Alias-prune owner gap remains. |
| FR-002/003 | Implemented owner effects are real, but malformed-state completeness and complete logical-owner reporting remain deficient. |
| FR-004 | Successful tested batches repeat without writes, including independent mixed drift/missing and health-recovery cases; no universal failure-recovery claim. |
| NFR-004 | Tested drift/custom/link/excluded/Q preservation succeeds. Findings require stronger health refusal and truthful post-failure reporting; no claim of observed unsafe-target writes in the race control. |
| C-001 | Canonical org-free base + activated-org resolver, original SkippedProfile tuple, existing renderer/path/manifest/protocol authorities retained; no competing activation rule introduced. |

Source health is retained at projection.py:175 before iterating/copying/truthiness,
and both source-invalid and overlay-conflict diagnostics consume it. Missing
configured roots and config errors remain separately diagnosed; canonical
empty skips alone are not interpreted as root health. Source observations
include additions/removals and immutable destination observations. Equal-state
apply does not rerender/save/chmod. Current owner preparation renders each
selected tool; legacy guarded reporting still constructs projectors separately,
so end-to-end single-scan/performance acceptance is not established here.

Inspected author frozen-source logs, not relabeled as fresh independent runs:
`/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp06-evidence/cycle2-subsystem-architecture.log` (811 pass),
`cycle2-fast.log` (1642 pass), `cycle2-callers.log` (22 pass),
static logs and pre/post source hashes. Coverage report is combined statement
coverage 95% (917 statements, 50 missed), provider 92%, manifest 93%,
projection 97%; not universal branch/new-code/platform coverage.
The tidy-first serializer extraction and its retained 16-test log were inspected.

The six formatter-debt paths reported by cycle2-format-final.log are explicitly
excluded from directory collection by unchanged pyproject.toml. Explicit-file
format check failed; the policy check passed seven files. No all-files formatter
pass or baseline exemption is inferred. Neither config nor exclusions changed.

The eight inherited public integration REDs remain downstream WP10/WP13 evidence:
G0 human/JSON, G1 human/JSON, P6 human/JSON, lower target 3.2.6 and original full
corpus audit. They were not freshly rerun here and are not waived or used to
excuse WP06 findings. No public startup purity, complete mission GREEN, wheel,
cross-repo E2E, full CORE architecture/contracts, platform-universal or
cold/warm p50/p95 performance approval is claimed.

## Required Prompt Checklist

| Item | Verdict | Basis |
| --- | --- | --- |
| Dead code | PASS | New owner/prepared/path/serializer symbols have production uses; live-callers.log retained. No new module. |
| Synthetic-fixture test | PASS | Required successful owner witnesses invoke real admission/rendering/dispatch/writers; failure injection only at explicit refusal/race seams. |
| Silent empty return | FAIL | Malformed required records reach complete empty effects (finding 1); optional no-renderer/absent-node returns have explicit reasons. |
| FR coverage | FAIL | Behavioral witnesses exist for every ref, but full required malformed-state and shared-prune-owner cells fail. |
| Frozen surface | PASS | Exact fourteen-path diff; frozen contracts/config/harness/corpus untouched. |
| Locked decision | FAIL | Corrupt required state accepted; partial result lost; all-affected-owner requirement incomplete. |
| Shared-file ownership | PASS | Three supplier files explicitly authorized and byte-identical; manual cycle-2 edits remain inside original ownership. |
| Production fragility | FAIL | Expected late confinement ValueError escapes after writes (finding 2). |

Parent owns canonical verdict serialization, lifecycle/status transitions and
subsequent fix routing. This report does not perform those operations.

