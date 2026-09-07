---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-07T01:22:13Z'
reviewer_agent: codex
wp_id: WP08
---

# WP08 First Independent Review

Reviewer: Renata. Verdict: **REJECT**.
Frozen product: `9d78799b94f3c4df0f2e68d4ca8dda4ef3661801`.
Parent alone captures the verdict and owns lifecycle/Op closure.

## F1 [P2]: Preserve supporting hook directory permissions

[Codex companion collection](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-h/src/specify_cli/tool_surface/bundles/codex.py:159) discards each observed directory's mode, retaining only its destination path. [Staging](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-h/src/specify_cli/tool_surface/bundles/projection.py:444) consequently declares every absent supporting directory as `0755`; [application](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-h/src/specify_cli/tool_surface/bundles/projection.py:661) also hardcodes `0755`.

The existing public `CodexBundleProjector.build()` succeeds but converts source `hooks/` and its empty `hooks/private-empty/` from `0700` to `0755`. This broadens directory access and changes the previous copy behavior. The cumulative BASE diff removes `shutil.copytree`, whose directory-mode preservation is independently controlled in the witness. This is a real supported-input regression, not merely inaccurate effect reporting: assessment and application agree on the wrong final mode.

Fresh witness: [test_directory_modes.py](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/test_directory_modes.py:43), [raw log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/directory-modes.log).
- `0755` source-directory control: PASS.
- `0700` source directories: FAIL, both become `0755`.
- Both public builds complete; manifest exists; empty directory survives; script bytes and `0750` mode remain exact.
- No `skip_validate`, mocked writer, mocked rendering, or policy bypass. Only the optional offering source locator points to a disposable real tree.
- `shutil.copytree` control retains both modes. This is a baseline-primitive control, **not** a claimed historical BASE test run.
- Terminal status 1: **1 failed, 1 passed in 29.35s**. Original raw failure retained. No further product probes after confirmation.

T040 explicitly requires exact prepared type/mode and supporting descendants; T041 requires reconciling the existing hooks copy path, not replacing its mode semantics; T042 requires independently observed mode correctness. The existing effect-vs-delta tests cannot detect this when both sides accept the same hardcoded mode.

Correction needed: retain observed supporting-directory modes in concrete prepared data, declare correct final modes, and have the writer consume those modes. Preserve unknown existing directories; do not introduce blanket chmod/adoption policy. Add a regression covering a nondefault source mode and an empty descendant alongside the passing default-mode control.

## Separate Configured-Helper Consumer Verdict

**APPROVE at the bounded consumer seam; supporting Op `01M1WM2PAB09HACQVJEDDR422H` is closure-ready for configured-helper consumption.** This does not approve WP08 or close the Op.

The real provider's `_plans_for_projection` loads `load_agent_config(project_root).available` and passes it to the real `build_plans_for_bundles(..., tool_keys=agents)`. Fresh execution of all three `configured_consumer` controls passed: nondefault Gemini/configured subset, explicit empty list, and ordered duplicates. The tests delegate to the actual helper, check roster/plan behavior and read-only attempts/delta; this is not a dummy caller.

Both helper files are byte-identical to approved `e35cdc494237f55ef73b36cb6f979e0c56772bfe`. Reused [supplier review](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/bundle-configured-tool-independent-review.md), SHA-256 `d41fdf3956496dbcc79ae8c80c3c9b45a086186a1a5bb2383ba29eacaa9c8870`; no supplier re-review or supplier test repeat. Caller selection remains distinct from logical ownership.

WP10 root production composition and `upgrade.intent/parse_upgrade_intent` gates remain pending. No dummy caller, gate exemption, root edit, or full architecture rerun was requested/performed.

## Scope and Provenance

Read the full fresh canonical prompt, embedded original WP08 prompt/T039-T042, full handoff, author provenance/commands/verification, spec, plan, owner-operations and acceptance contracts. Reviewed the **entire cumulative 13-owned-file diff**, not just the final commit. Reused hash-verified prior governance and approved dependencies.

Both initial and final readonly provenance checks passed:
- BASE `a190a3d9d0115472d8e1555eb7ec3d7a200c22f7` is ancestor of frozen final.
- Frozen final is ancestor of execution HEAD `0d27ebe20e5e70799c62dce42cee9661816241e0`.
- Later differences are only mission `status.events.jsonl` and `status.json`; product/config/tests remain frozen, worktree clean.
- Cumulative changed path set is exactly **13 owned + 2 approved helper files**.
- All 13 source/test hashes, both helper hashes and original helper bytes match.
- Approved WP02/WP04/WP05/WP06/WP07 commits are ancestors of BASE. Their settled source/evidence is reused, not reopened.
- Every file in the author's evidence hash receipt still matches, including original failures and validator evidence.
- Pinned Claude binary SHA matches `ef5d2909c8af49f31ab6d5487e90316777bc2fac170adfe8160716caa8aaf4f9`.

Exact individual source hashes and assertions: [initial provenance](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/provenance.json), [final provenance](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/provenance-final.json), [provenance script](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/provenance.py). Full reviewed diff: [full-owned.diff](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/full-owned.diff).

## Criteria Disposition

| Criterion | Disposition and evidence |
| --- | --- |
| T039 policy/RED characterization | Reviewed cumulative RED and author raw failures: omitted members, churn, unavailable source, unknown link; later explicit build churn/destructive-copy RED. Default advisory/disabled is unselected, with no inventory/writes. Historical tests reused, not freshly replayed. |
| T040 immutable complete preparation | Frozen entries/observations/files/prepared bundle retain bytes, file modes, sources, supplier assessments and version. Parent/member/descriptor/ledger/catalog/wrapper/MCP/hooks outputs examined. **Fails F1 for source directory modes.** |
| T041 existing callers and application | Existing provider repair/project and explicit builders route through preparation. Whole-batch source/config/manifest/destination guards, no second render/assessment, exact member writers, manifest ordering and partial IDs reviewed. **Not acceptable overall because the real build regresses hook directory permissions.** |
| T042 independent acceptance | Author all-target, shared-output, conflict, preservation, races, partial failure, delta mutants, and repeat-no-churn tests reviewed. Fresh public-build control exposes a mode-contract gap despite declared-vs-actual delta agreement. **Incomplete until F1 regression is repaired and verified.** |
| Upstream authority | Concrete WP04-WP07 preparations consumed without applying project/global owners. Missing prepared output differs from unavailable required source; no stale fallback. Supporting supplier destination observations require staging before upstream repair. Full WP10 composition remains pending. |
| Scope/selection | Explicit BundleSources/selected targets supported; ordinary optional/disabled remains not_applicable. CONTEXT_FILE/RULE and user-global exclusions retained. Fresh configured-agent consumer controls pass. No new install/enable/removal policy. |
| Sharing/conflict | Same physical codex/vibe contribution retains owners; differing native profile bytes refuse rather than first-wins. Source review plus reused author positive/negative evidence. |
| Preservation/confinement | Unknown/custom/link occupants preserved, including ledger cases; known drift requires exact consent. Source and parent observations/nofollow checks, membership/config/link races reviewed. No blanket path-name ownership. |
| Exact apply/failure | Retained bytes, bounded atomic temporary artifacts, members before descriptor/ledger, actual succeeded/failed/skipped IDs reviewed with author raw controls. No cross-owner rollback or new cross-process project-lock promise. |
| Idempotence/clock | Byte/type/mode comparisons and prepared version avoid repeat churn/rerender. Author repeat-build/project and exact-delta evidence reused. F1 remains a source-mode semantic error, not an apply-clock finding. |
| Claude catalog fidelity | Owned correction preserves URL/path/version/category/name/location; adds required owner/description, removes ignored interface/policy. Codex local policy unchanged. Existing BASE catalog invalidity is not blamed on this WP. |
| Full gates | No current full subsystem/fast/architecture/public certification. Required later integration gates remain mandatory, without waivers. |

## Fresh Execution

Every command's full argv, UTC start/end, denial checks and terminal status is in [invocations.jsonl](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/invocations.jsonl). All product invocations use this review's isolated wrapper, not the parent's wrapper.

| Invocation | UTC start -> end, 2026-09-07 | Exit/result |
| --- | --- | --- |
| Canonical reviewer-renata profile show | 01:09:56.296160 -> 01:10:13.094006 | 0 |
| Charter context --action review | 01:10:18.757634 -> 01:10:40.819406 | 0 |
| Initial provenance | 01:11:18.511458 -> 01:11:19.546686 | 0 |
| Cumulative readonly git diff | 01:11:19.664230 -> 01:11:19.692159 | 0 |
| Actual configured-consumer pytest | 01:13:38.673275 -> 01:14:32.267686 | 0; 3 passed, 27 deselected, 32.02s |
| Real Codex directory-mode pytest | 01:17:47.125373 -> 01:18:37.545244 | 1; 1 passed, 1 failed, 29.35s |
| Final provenance-only check | 01:18:53.090439 -> 01:18:54.008762 | 0 |

[Configured-consumer raw log](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/configured-consumer.log). Exact replay command forms: [commands.md](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp08-independent-evidence/commands.md). Final provenance is an evidence/source-integrity check, not another behavioral probe after F1.

## Reused Evidence and Limits

- Final author owned suite: **145 passed, 338.94s**; 92.46% line / 91.07% changed-line coverage, 90% gate. Author Ruff/strict mypy: green, ten sources. These are **not fresh reviewer blanket coverage or static passes**.
- Earlier 924 subsystem / 1642 fast results are tied to their earlier source snapshots/patches, not final current full gates. Historical architecture included the helper dead gate and pending WP10 intent symbols; no claim of architecture pass now.
- Reused real Claude 2.1.263 final strict plugin/catalog PASS, zero errors/warnings, malformed-name FAIL exit1. Reviewed generator and raw logs, verified evidence/binary hashes. Reviewer did not rerun the external validator after F1.
- Author actual Claude 67-effect witness uses real prepare/apply and WP01 delta/member assertions. Validator `contents: []` does **not** prove member coverage; those are separate evidence.
- Full13file source review completed once. Fresh tests deliberately bounded to consumer integration and the concrete mode risk; no repeated 145-owner/924-subsystem/1642-fast/public/architecture matrix.
- External witness retains real conftest and actual public build. It logs `Config file not found: /.kittify/config.yaml`; no policy was relaxed and no global-home access occurred. The witness is a focused optional-hook source fixture, not a whole-project configured-provider acceptance substitute (the separate configured-consumer tests cover that seam).
- One ordinary source-text lookup used a guessed original-prompt filename and returned exit2/no such file; the exact attempt is retained in commands.md. The full original prompt was already read in the canonical prompt and its T040-T042 text was rechecked there. No failed product attempt was discarded.

## Isolation and Governance

Own external HOME/USERPROFILE/SPEC_KITTY_HOME/XDG/AppData/tmp/cache under evidence; `env -i`; direct warm WT Python 3.11.15, pytest9.0.3/events9.1.6; no uv sync/install. OS sandbox denies all network and both real-home aliases' reads/writes, and writes outside own evidence except /dev/null. Before every product invocation, known-existing skill-file noncreating/nontruncating O_RDONLY/O_WRONLY attempts are denied for both aliases, checkout/sharedGit writes denied, socket denied, and parent/child sync0 asserted/clamped.

Real conftest retained. External warm-fixture hook returns its cached result; scanner cache only redirected. No live-home inventory/rollback, no historical F038 isolation claim. Wrapper/policy/scripts/logs retained.

Canonical Renata resolution and charter action loading ran serially in the same isolated HOME. Known #3908 empty reference resolution is a **degraded resolver result**, not empty governance. Binding AGENTS/charter/profile contents from prior explicit reads were hash verified unchanged and applied. No governance waiver.

All review process handles terminal. No implementation/source edits, lifecycle writes, commits, COORD/root edits, Op closure, pushes or merges performed. Parent alone records the single WP08 REJECT and decides the separately supported consumer Op disposition.

