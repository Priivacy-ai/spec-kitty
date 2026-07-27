# Tooling Friction Trace

Observed while preparing, specifying, and planning mission `templates-as-config-01KXMS1G` on 2026-07-16. Each entry records behavior seen in this fresh clone, its impact, and the workaround used; no claim is made that every item is a distinct product defect until triaged.

## TF-001 — Missing configured Codex skill surface

`.kittify/config.yaml` configured Codex, but the fresh clone had no `.agents/skills/` surface. `spec-kitty agent config sync` with defaults did not create it; `--create-missing` was required.

## TF-002 — Default sync removed tracked command fixtures

Running `spec-kitty agent config sync` with defaults removed tracked command fixtures from eleven agent directories as “orphaned.” The exact files had to be restored; a repository checkout should not be destructively normalized without an explicit flag.

## TF-003 — Safe sync dirtied the pinned manifest

`agent config sync --create-missing --keep-orphaned` rewrote the tracked command-skills manifest from the repository-pinned release/hashes to those of the globally installed CLI. The manifest was restored while the ignored generated Codex skills were retained.

## TF-004 — Four conflicting version signals

The checkout's `pyproject.toml` reports 3.2.6, root agent guidance mentions 3.2.0rc39, the pinned command manifest reported 3.2.0rc45, and the installed CLI reports 3.2.5. This makes generated-surface compatibility and bug attribution ambiguous.

## TF-005 — User guidance and generated skills have drifted

The installed how-to skill still describes a mandatory constitution command and Codex `.codex/prompts`, while this repository uses charter governance and `.agents/skills`. The generated specify skill also recommends `branch-context --mission`, but the actual command exposes no `--mission` option.

## TF-006 — Mission target changed during creation

Pre-create branch context reported `main`, but `mission create --start-branch feat/templates-as-config` made the feature branch the mission target and merge target. The CLI does not clearly distinguish this coordination target from the eventual repository PR target (`main`).

## TF-007 — Creation split mission state across branches

Mission creation created the coordination branch from the base but committed mission metadata only on the feature branch. The coordination branch initially had no mission directory or status stream, causing later split-state warnings.

## TF-008 — Creation committed before finishing metadata

Mission creation committed initial metadata, then wrote `pr_bound: true` afterward, leaving `meta.json` dirty. It also left specification/status/task scaffolding untracked instead of reporting a fully committed or explicitly staged boundary.

## TF-009 — Software-development spec scaffold was empty

Mission creation produced an empty `spec.md` when project-local template files were absent, even though the doctrine software-development artifact declares `spec-template.md`. This is direct runtime evidence of the template-authority gap addressed by issue #2658.

## TF-010 — SaaS sync failure severity varies by local command

With unauthenticated SaaS sync enabled, mission creation completed with a nonfatal warning, while `agent mission setup-plan` failed fatally before local scaffolding. Equivalent local workflows should expose consistent offline behavior and severity.

## TF-011 — `spec-commit` silently partially committed a mixed batch

When passed primary artifacts plus coordination-owned `status.events.jsonl`, `spec-commit` returned success and a commit but skipped the status file without identifying it. A second status-plus-`.gitkeep` call again committed only the primary-owned file, leaving coordination state behind.

## TF-012 — `safe-commit` routed the branch but used the wrong worktree

From the primary checkout, `safe-commit` recognized that status belonged on the coordination branch but attempted the commit against the primary worktree and failed a HEAD mismatch. Its suggestion to check out the coordination branch there was impossible because that branch was already checked out in its registered worktree.

## TF-013 — Decision verification's remediation could not fix its warning

`agent decision verify` materialized the coordination worktree, found no mission directory there, and fell back to primary state while recommending `doctor workspaces --fix`. That doctor reported the registered worktree healthy because it only addressed unregistered husks, so the suggested remediation could not repair missing coordination content.

## TF-014 — Mission-state doctor flags generated metadata shape

`doctor mission-state` reports generated valid keys such as `coordination_branch`, `flattened`, `pr_bound`, and `topology` as `UNKNOWN_SHAPE` informational findings. This suggests schema drift between mission creation and doctor validation.

## TF-015 — Coordination doctor cannot target one mission

`doctor coordination` has no mission filter and emitted a large repository-wide set of unrelated warnings while this task needed only one mission audited. The noise makes current-mission diagnosis difficult.

## TF-016 — Plan context points at the coordination directory

`agent context resolve --action plan` returns the coordination worktree as `feature_dir`, although the specification and plan are primary-checkout artifacts and the coordination tree initially held only status. `setup-plan` likewise mixed a coordination `feature_dir` with primary absolute paths for `spec_file` and `plan_file`.

## TF-017 — Inherited SaaS flag blocks a local plan

The environment contained `SPEC_KITTY_ENABLE_SAAS_SYNC=1`; while logged out, this made the otherwise local `setup-plan` command fatal with `SAAS_SYNC_UNAUTHENTICATED`. The workaround was command-local `env -u SPEC_KITTY_ENABLE_SAAS_SYNC`, which is non-obvious and easy to forget.

## TF-018 — Logged-out teamspace noise appears on local operations

Local commands repeatedly emit `logged_out_on_connected_teamspace` messaging even when no hosted operation is requested. This obscures the workflow-relevant result.

## TF-019 — Version output is not machine-quiet

`spec-kitty --version` prints a large ASCII logo before the version value. This makes a common diagnostic harder to parse in scripts and logs.

## TF-020 — Expected plan scaffold is reported as a blocked command

The first `setup-plan` correctly creates the template and waits for substantive authoring, but reports the normal two-pass workflow as a blocked result. This is workable, though “scaffolded/awaiting authoring” would distinguish expected progression from an error.

## TF-021 — Plan start mutates coordination status while plan lives elsewhere

Starting the plan modifies the coordination-owned status stream while creating `plan.md` in the primary checkout. Because commit helpers struggle with mixed ownership, the operator must notice and commit each tree separately to avoid stale lifecycle state.

## TF-022 — Task context and prerequisites disagree on feature directory

`agent context resolve --action tasks` returned the coordination worktree as the canonical absolute `feature_dir`, despite the command contract requiring task authoring in the primary checkout. Its exact `check-prerequisites` command then returned the primary checkout as `feature_dir`; following both outputs literally is impossible.

## TF-023 — Prerequisite artifact inventory omits existing planning files

Task prerequisites reported only `plan.md` and `spec.md` in `available_docs`, omitting the existing `research.md`, `data-model.md`, `quickstart.md`, `contracts/`, and `traces/`. It also returned `research_dir` as a nonexistent `research/` directory even though the workflow writes a `research.md` file.

## TF-024 — Invoked command and generated skill versions drift

The user-provided tasks command carries `spec-kitty-command-version: 3.1.2a3`, while the locally generated task skill comes from installed CLI 3.2.5 and declares its workflow as 0.11.0+. There is no compatibility diagnostic explaining which instruction set wins.

## TF-025 — Flat-task rule conflicts with the bundled prompt template

The task workflow repeatedly forbids status or phase subdirectories and requires every WP prompt directly under `tasks/`. The bundled software-development task prompt template ends by recommending optional phase subdirectories, creating a direct structural contradiction.

## TF-026 — Profile assignment occurs after the final commit boundary

The generated task skill says `finalize-tasks` performs the final commit and forbids later commits, then instructs agents to edit every WP frontmatter directly afterward to assign profiles without re-finalizing. Assigning profiles before validation/finalization is the only way to keep the committed task bundle consistent.

## TF-027 — Tracer governance conflicts with WP ownership validation

The charter requires implementation WPs to append mission tracer files, but `finalize-tasks --validate-only` rejects every `owned_files` path under `kitty-specs/` with `INVALID_WP_OWNED_FILES_KITTY_SPECS`, regardless of execution mode. The workaround is for WPs to return tracer-ready evidence in their Activity Logs and for the mission coordinator to append it from the primary checkout outside implementation-lane ownership.

## TF-028 — `finalize-tasks` reports a commit surface different from git reality

`agent mission finalize-tasks` returned JSON claiming the task bundle, `status.events.jsonl`, `status.json`, and acceptance matrix were committed together under its reported task commit. Inspecting that commit showed only task artifacts, lanes, and a dossier snapshot. The primary checkout retained untracked status copies, while the coordination branch received five separate status-transition commits plus a separate acceptance-matrix commit. The reported commit hash therefore does not identify every mutation the command says it committed.

## TF-029 — `record-analysis` reports the primary path but commits the coordination copy

`agent mission record-analysis` returned the primary-checkout `analysis-report.md` path, but its durable commit landed on the coordination branch and the same report remained untracked in the primary checkout. This path/placement split makes it unclear which returned artifact is canonical and requires manual inspection of both worktrees.

## TF-030 — Status display and implementation claim disagree on canonical WP state

Immediately after successful re-finalization, `agent tasks status --mission templates-as-config-01KXMS1G` displayed all five WPs in `planned` from the coordination status surface, while `agent action implement WP01` failed with “WP WP01 has no canonical status” and instructed the operator to run `finalize-tasks` again. The coordination `status.json` and event stream both contained the WP01 planned event. The two commands therefore resolved different status surfaces for the same mission and checkout.

## TF-031 — Implementation gate ignores the committed coordination analysis report

After restoring the primary status event surface, `agent action implement WP01` advanced past the status check but failed with `analysis_report_required`. A fresh READY report was already committed on the coordination branch by `record-analysis`, yet the implementation gate checked only the primary-checkout path. Because `record-analysis` had also left an untracked primary copy, implementation depended on retaining that duplicate rather than consuming the recorder's durable coordination artifact.

## TF-032 — WP transition classifies unrelated primary analysis residue as lane-owned

The normal WP01 and WP02 `move-task --to for_review` preflights rejected their handoffs because the primary checkout contained `kitty-specs/templates-as-config-01KXMS1G/analysis-report.md`, an untracked duplicate created by `record-analysis`. That coordination/planning artifact was outside both WPs' `owned_files` and outside their lane worktrees, yet each transition classified it as a WP-owned violation. Both implementation diffs were confined to their declared files; forced transitions were required. WP01 approval repeated the same false positive.

## TF-033 — Pre-review coverage gate runs outside the project test environment

WP01–WP05 pre-review transitions reported `no_coverage` because they attempted to import gate authorities under the globally installed Spec Kitty runtime, where `pytest` was unavailable. Each lane's declared `uv run` environment had pytest, pytest-cov, and diff-cover installed and every WP coverage gate passed at 100%. Runtime gate execution should use the project environment or provide a non-importing coverage adapter.

## TF-034 — Validating workflow commands skip the bundled terminology toolguide

Both implementation and review claims emitted a doctrine warning that `terminology-guard.toolguide.yaml` was skipped because its `references` field is rejected as an extra input by the installed `Toolguide` model. This means the generated workflow continues after silently dropping a built-in governance asset, while presenting no compatibility remediation beyond the Pydantic validation text.

## TF-035 — Fresh project test invocation lacked a declared runtime dependency

In the new WP02 lane, `uv run pytest` initially failed because `filelock` was unavailable. Running `uv sync --frozen --all-extras` restored the dependency and the same focused test command passed. A fresh finalized lane should either be immediately test-runnable under the documented command or tell the implementer that an all-extras sync is required.

## TF-036 — The implement-review diff-lint recipe is Bash-specific under zsh

The skill's mandatory example assigns newline-delimited paths to scalar `CHANGED_SRC` and invokes the linter with `$CHANGED_SRC`. Under the repository/operator's zsh, scalar expansion does not word-split those paths, so Ruff receives one invalid multiline filename and reports E902. A shell-safe array or `xargs` form passes on the same three files. The recipe should not assume Bash splitting semantics without declaring the shell.

## TF-037 — Generated review topology is stale at review start

WP03–WP05 generated implementation/review prompts showed all or most WPs as `planned`, even when the canonical status surface already had upstream dependencies approved and the current WP in progress or review. Prompts use this topology to explain dependency and base risk, so stale lane state can lead agents to evaluate the wrong execution context.

## TF-038 — Review claim can succeed without emitting its handoff output

`agent action review` for WP03 and WP04 exited successfully, changed canonical state to `in_review`, and generated prompt files, but returned no stdout. The operator had to query task status and scan the temporary prompt directory to recover the workspace/prompt handoff that the command normally prints. An earlier interrupted WP02 claim also left a stale review lock that the retry had to remove automatically.

## TF-039 — Review rejection duplicates feedback across split authority surfaces

The successful WP05 rejection created `review-cycle-1.md` under both the primary checkout and coordination worktree. It also modified primary `tasks.md` and the WP prompt, left primary `status.events.jsonl` untracked, and left the coordination feedback directory untracked rather than durably committing one canonical rejection record. The operator must determine which copy is authoritative and route/commit artifacts manually before re-dispatch.

## TF-040 — Rejection prompt format is incompatible with the later approval parser

The generated cycle-1 review prompt instructed the reviewer to write plain Markdown feedback. `move-task` accepted that report and moved WP05 to `planned`, but the later approval gate reparsed the latest review-cycle artifact only from YAML frontmatter and rejected the accepted `Verdict: **REJECT — changes required**` line as unparseable. Repair required adding canonical `verdict: rejected` frontmatter to both split copies. The review prompt and approval parser must share one artifact schema.

## TF-041 — Approval requires an artifact the generated review prompt never creates

After cycle-1 metadata repair, cycle-2 approval still required the latest review-cycle artifact to contain `verdict: approved`; the generated cycle-2 review prompt only instructed `move-task --to approved` and provided no approved-artifact creation step. The independent reviewer had to manually author `review-cycle-2.md` with canonical YAML before approval. The subsequent transition committed only coordination status, leaving the required review artifact untracked on primary alongside a modified WP Activity Log and untracked status copy.

## TF-042 — Acceptance cannot see the matrix created by task finalization

With all five WPs approved and decision verification clean, `spec-kitty accept` failed because `acceptance-matrix.json` was missing from the primary checkout. `finalize-tasks` had generated and committed a coordination copy while reporting the matrix among its committed files, but the acceptance gate resolved only the primary path. The generated coordination matrix also still contained placeholder `TODO` criteria and an overall `pending` verdict after all reviews. The operator had to route and populate the matrix manually before acceptance could run normally.

## TF-043 — Approval and merge read different review-artifact surfaces

WP05 cycle-2 approval succeeded after the primary checkout received `review-cycle-2.md` with `verdict: approved`. The subsequent `spec-kitty merge` failed because its review consistency gate read the coordination worktree, where the latest artifact was still cycle 1 with `verdict: rejected`. Approval and merge therefore evaluated different artifact sets for the same WP. The operator had to route the already-approved cycle-2 report to coordination and commit it there before merge could retry.

## TF-044 — Approval accepts review YAML that merge rejects

After routing cycle 2 to coordination, merge rejected the review artifact because an unquoted ISO timestamp had been parsed as a YAML datetime rather than the schema's required string. Its remediation also requires `affected_files` to be mappings with `path` keys, while the approval gate had accepted a list of strings. The generated review flow provides neither a schema template nor validation before approval, so stricter merge validation discovers incompatible metadata only at the final gate.

## TF-045 — Merge labels independently reviewed work as hollow from force count alone

`spec-kitty merge --mission templates-as-config-01KXMS1G` warned that every WP might have been approved by its implementer because each WP had a nonzero `force_count`. In this mission every WP had a separate implementer and reviewer identity, explicit review claims, reviewer-authored evidence, and WP05 had two review cycles. The forced transitions only bypassed the known unrelated `analysis-report.md` ownership false positive. Treating any force as evidence of a hollow review discards the recorded actor and review evidence and produces a false integrity warning at the final gate. Workaround: manually verify reviewer identities and artifacts from the event stream before proceeding. Status: issue-queue triage required.

## TF-046 — Failed target advancement leaves committed and working mission status opposed

The first merge integrated all five lane branches and committed five `approved -> done` transitions on the mission branch, then failed to advance `feat/templates-as-config` because a CLI-generated untracked primary `analysis-report.md` duplicate would be overwritten. The merge rollback rewrote the coordination working tree back to five `approved` WPs without reverting the committed `done` events, leaving `git show HEAD:status.json` at `done=5` while the checked-out `status.json` reported `approved=5`. A resume therefore announced `0/5 WPs already done`, skipped all already-integrated lanes, and recorded the transitions again before retrying target advancement. Workaround: verify and remove only the byte-identical generated duplicate, then use `spec-kitty merge --resume`; do not manually commit either opposed status surface. Status: issue-queue triage required.

## TF-047 — Merge cleanup reports a mission branch removed after Git refuses

The successful resumed merge removed all five lane worktrees and branches, then Git rejected deletion of `kitty/mission-templates-as-config-01KXMS1G` because the registered coordination worktree still had it checked out. Immediately afterward the CLI printed `Cleaned up 5 lane branch(es) + mission branch`, even though `git worktree list` and `git branch --list` still showed the coordination worktree and mission branch. The cleanup summary overstates what completed and leaves an unexplained retained worktree after a successful merge. Workaround: treat Git's explicit refusal and `git worktree list` as authoritative; retain the coordination worktree for review evidence until a supported cleanup path is identified. Status: issue-queue triage required.

## TF-048 — Stale-assertion analyzer floods merge with generic-string false positives

The post-merge stale-assertion check reported well over one hundred findings and a density of `10.0` per 100 LOC because two removed lines in `mission_creation.py` contained generic literals such as `templates` and `spec-template.md`. It paired those literals with assertions across unrelated charter, migration, pack, initialization, and E2E tests, often emitting the same test assertion twice for the two adjacent removed lines. These are still-live domain vocabulary and configured template names, not stale assertions. The output obscures actionable merge evidence and exceeds its own NFR ceiling while the warning itself recommends narrowing to function renames. Workaround: rely on the focused parity, architecture, integration, and mutation tests; manually inspect any stale-assertion candidate tied to a renamed symbol. Status: issue-queue triage required.

## TF-049 — Squash merge overwrites newer target-only mission traces

Immediately before merge, `safe-commit --to-branch feat/templates-as-config` committed current coordinator traces on the target branch. The squash merge commit correctly used that target commit as its parent, but replaced all three traces with older coordination-branch copies. It silently removed the WP05 closeout and remediation sections from `approach.md` and `design-decisions.md`, and removed TF-039 through TF-046 plus the WP05 observation sections from `tooling-friction.md`. The target history still contains the lost content in its parent, but the post-merge working tree did not. A merge should preserve target-side changes or raise a conflict instead of treating the mission-branch copies as authoritative over newer target artifacts. Workaround: compare every mission artifact against the merge parent and restore lost evidence with a new commit before post-merge review. Status: issue-queue triage required.

## TF-050 — Activity history writes to a different surface than status authority

`spec-kitty agent tasks add-history WP05 --mission templates-as-config-01KXMS1G ... --json` returned success from lane E but appended the WP Activity Log to the primary-checkout prompt, while modern status authority and review evidence were advertised through the coordination worktree. The resulting evidence was absent from the surface reviewers were told was canonical until the coordinator manually located and routed it. Workaround: inspect both primary and coordination prompt copies after every history append and commit the changed surface explicitly. Status: issue-queue triage required.

## TF-051 — `add-history` lacks a file input for shell-sensitive notes

`add-history` accepts inline `--note` but no `--note-file`. Markdown backticks passed through an inadequately escaped shell command triggered command substitution and mangled five append-only history entries, creating both evidence pollution and accidental execution risk for orchestrators. Workaround: single-quote plain text and avoid shell metacharacters, then append corrections because history is immutable. Recommendation: add `--note-file` parity with `--review-feedback-file`. Status: issue-queue triage required.

## TF-052 — Fresh monorepo preparation omitted a mandatory mission-review repository

The timestamped workspace created for this Spec Kitty mission contained `spec-kitty` but no `spec-kitty-end-to-end-testing` sibling. The post-merge mission-review skill defines that sibling's `scenarios/` suite as a hard gate, so review could not begin its cross-repository proof until the private repository was discovered missing and cloned late. Workaround: clone the E2E repository into the prepared workspace before running the gate. Recommendation: monorepo preparation should include repositories required by selected downstream skills or report the missing dependency up front. Status: issue-queue triage required.

## TF-053 — Cross-repo drift scenario omits its nested test dependency

The documented `contract_drift_caught` E2E scenario creates a nested environment, installs pytest, a fake events package, and editable Spec Kitty, then runs the full contract suite. It did not install Spec Kitty's packaging-test dependency `build`, so `tests/contract/test_packaging_no_vendored_events.py` errored in its wheel fixture after 254 passes and 3 skips, before the intended drift diagnostic. Fix: install `build` in the nested environment; verified by the repaired scenario at sibling commit `615f1a6`. Status: fixed in the prepared E2E repository; issue/PR reconciliation required.

## TF-054 — SaaS-enabled planning scenario does not classify missing auth as environmental

`dependent_wp_planning_lane` deliberately runs with `SPEC_KITTY_ENABLE_SAAS_SYNC=1`, but the harness neither provisions authenticated team credentials nor converts the expected readiness guard into its documented operator-exception path. On a logged-out machine, `spec-kitty plan` correctly returns `SAAS_SYNC_UNAUTHENTICATED`; the scenario treats that as a product assertion failure rather than an environmental block. Workaround: run only with authenticated test credentials or obtain a human-approved mission exception. Status: issue-queue triage required.

## TF-055 — Empty SaaS endpoint produces an unusable exception reproduction

The SaaS E2E floor xfails when neither supported endpoint environment variable is set, but renders the missing value directly into its instruction as `curl -fsS `. That is not a reproducible command and does not identify which variable must be configured. Workaround: inspect the scenario fixtures and endpoint environment manually. Recommendation: fail/xfail with the accepted variable names and a non-empty example or explicitly state that endpoint configuration is absent. Status: issue-queue triage required.

## TF-056 — Plan-template migration read mission identity from a meta-less status surface

Post-merge mission review reproduced `setup-plan` resolving its mission-type context from the coordination/status `feature_dir`, even though that directory intentionally has no `meta.json`; the same command already resolved `spec.md` and `plan.md` from the primary planning surface. The new reader therefore classified an activated software-development mission as typeless and invoked the hard-coded legacy `plan-template.md` fallback, violating this mission's own authority swap. Focused pre-merge tests mocked the context or used one directory and missed the real split. Workaround/fix: resolve context from canonical `plan_read_dir` while retaining the coordination directory only for lifecycle/status writes, with a distinct-surface regression test. Status: fixed post-merge; issue-queue triage required.

## TF-057 — Setup-plan rejected the repository's supported legacy metadata field

An adversarial replay of the real `setup-plan` helper with `meta.json` containing `{"mission":"software-dev"}` failed with `TemplateConfigurationError` demanding `mission_type`. This is a supported upgrade state, not a forged context: the repository's canonical metadata reader explicitly reads `mission_type` and then legacy `mission`, while issue #2660 separately owns removal of the meta-less template fallback. The focused suite passed without exercising this CLI boundary. Fix: canonicalize both fields from the command's single strict metadata snapshot and route a valid legacy field through configured-template resolution rather than the meta-less fallback. Status: fixed post-merge; issue-queue triage required.

## TF-058 — Authentication status has no machine-readable mode

The cross-repository gate preflight attempted `spec-kitty auth status --json`, matching the machine-readable pattern used by mission/runtime commands, but the auth command rejects `--json` with `No such option`. The human output correctly reported `Not authenticated`, yet automation must scrape presentation text or wait for a later mutating command to emit structured `SAAS_SYNC_UNAUTHENTICATED`. Recommendation: add a stable JSON status response so E2E harnesses can classify missing credentials before launching a long scenario. Status: issue-queue triage required.

## TF-059 — The dependent-WP E2E scenario never creates or merges work packages

The hard-gate runbook says `dependent_wp_planning_lane.py` proves that a mission with sequential dependent WPs plus a planning-lane WP merges without omitting approved commits, and the test docstring says it drives a four-WP fixture. The implementation stops after `spec-kitty plan`, then only asserts that planning files exist; it creates no tasks, dependencies, lanes, approvals, or merge. Even with SaaS credentials, the named cross-repository behavior remains untested. Status: issue-queue triage required.

## TF-060 — Environmental xfail can leave the hard-gate process successful

`saas_sync_enabled.py` deliberately uses `pytest.xfail` when no endpoint is configured, while the mission-review contract defines the cross-repo gate primarily by nonzero process exit. An xfail contributes exit zero when the rest of the suite passes, so automation that checks only the mandated command status can label an environmentally blocked gate successful unless it also parses outcome counts. The scenario prose expects reviewer interpretation, but the executable gate and documented exit-code rule disagree. Status: issue-queue triage required.

## TF-061 — Installing Spec Kitty after the fake drift package erased the drift

After adding the missing `build` dependency, `contract_drift_caught.py` ran all 293 contract tests successfully: the scenario had installed the editable fake `spec-kitty-events` package before editable Spec Kitty, and Spec Kitty dependency resolution replaced the fake with the released package. The purported drift was therefore absent. Fix: install Spec Kitty first and the fake candidate last; the targeted scenario then passed by observing the intended drift diagnostic in 9.44 seconds. Verified at sibling commit `615f1a6`. Status: fixed in the prepared E2E repository; issue/PR reconciliation required.

## TF-062 — Fresh-project implementation reveals charter prerequisites one at a time

A fresh non-interactive `spec-kitty init`, mission creation, planning, task finalization, and analysis recording all succeeded, but the first `agent action implement` failed with `charter_source missing; run spec-kitty charter sync`. Running the full deterministic interview → generate → sync path then exposed a second late failure, `synthesized_drg missing; run spec-kitty charter synthesize`. Both governance prerequisites are legitimate and their individual messages are actionable, but neither init nor the earlier planning/finalization gates report the complete prerequisite chain. Automation only discovers it after attempting implementation and must retry serially. Recommendation: fresh-project setup or an implementation preflight should report the full missing charter-state set and ordered deterministic remediation. Status: issue-queue triage required.

## TF-063 — Acceptance calls the same missing contracts artifact optional and required

For a software-development fixture with all four WPs approved, `spec-kitty accept --mode local --json` included `contracts` in `optional_missing` and warned `Optional artifacts missing`, while the same payload put the absent `contracts/` path in `path_violations`, `failed_checks`, and `recommended_fix_order`, making acceptance fail. A single artifact cannot be both optional and a blocking required path in one result. Recommendation: distinguish optional contract documents from the required contracts directory, or use one consistent severity. Status: issue-queue triage required.

## TF-064 — Acceptance's contracts remediation is relative to the wrong apparent root

The failed acceptance result recommended `mkdir -p contracts/`. Creating and committing exactly `contracts/.gitkeep` at the repository root did not clear the check. The validator actually resolves the software-development `contracts/` artifact against `kitty-specs/<mission>/contracts/`, while `src/` and `tests/` resolve against the repository root. The remediation omits that base distinction and leads an operator to create the wrong path. Creating `feature_dir/contracts/.gitkeep` cleared the gate. Recommendation: emit the resolved mission-relative path (or an absolute path in JSON) for artifact directories. Status: issue-queue triage required.

## TF-065 — Missing SaaS endpoint is reported as an unreachable empty URL

With both `SPEC_KITTY_SAAS_ENDPOINT` and `SK_E2E_SAAS_URL` absent, `saas_sync_enabled.py` xfails with `dev SaaS endpoint  is unreachable` and a reproduction of `curl -fsS `, containing no URL. The actual condition is unconfigured endpoint, not a failed reachability probe. The empty reproduction cannot be run and makes hard-gate diagnosis look like a network outage. Recommendation: distinguish missing configuration from reachability failure and only emit a curl reproduction when a nonempty URL was tested. Status: issue-queue triage required.

## TF-066 — Mission squash merge dropped canonical acceptance provenance

The accepted mission's commit `0c9526d0c` remained an ancestor of the final branch, but the post-merge `kitty-specs/templates-as-config-01KXMS1G/meta.json` no longer contained `accepted_at`, `accepted_by`, `accepted_from_commit`, `acceptance_mode`, `accept_commit`, or `acceptance_history`. It also lost the recorded `vcs` and `vcs_locked_at` fields. The values were present on the target-side baseline immediately before the mission squash and were replaced by the older mission-branch metadata, the same target-newer overwrite class previously observed for traces in TF-049. Fix for this mission: restore the exact accepted provenance and VCS lock fields while retaining the newer `baseline_merge_commit` and assigned `mission_number`. Recommendation: mission merge must reconcile canonical target-side metadata rather than replacing it wholesale with an older lane/coordination copy, with a regression test that preserves acceptance fields through squash. Status: mission artifact repaired; issue/PR reconciliation required.

## TF-067 — PR canary fails before tests when the branch has no Upsun environment

After opening E2E PR #340, the `teamspace-readiness-canary` check failed in `Discover Upsun canary target` before executing any branch code. The workflow used the Git branch name `fix/contract-drift-build-dependency` as `SK_E2E_UPSUN_ENVIRONMENT`; `upsun environment:info` returned `Specified environment not found` and exit 2 because no same-named remote preview existed. Local changed scenarios and the canonical-producer check pass, so the red check represents an unfulfilled preview-infrastructure prerequisite rather than a test regression. Recommendation: provision/resolve the preview deterministically, emit a structured blocked/skipped result when previews are unavailable, or document a mandatory pre-PR provisioning step. Status: reported as E2E #345.

### 2026-07-16 — WP05 implementation-loop observations

- Fresh lane bootstrap: `uv run pytest ...` created a minimal environment that omitted declared test dependency `filelock`, so collection failed in `tests/conftest.py`. Impact: a freshly claimed worktree cannot run the generated prompt's tests directly. Workaround: `uv sync --frozen --all-extras`. Status: resolved locally; issue-queue triage required.
- Stale implementation topology: the prompt generated by `spec-kitty agent action implement WP05` reported WP01-WP05 as `planned` in `WORKTREE_TOPOLOGY`, although dependencies were approved and WP05 had just moved to `in_progress`. Impact: generated scheduler context conflicts with canonical runtime status. Workaround: trust `spec-kitty agent tasks status` / `spec-kitty next` from the primary checkout. Status: issue-queue triage required.
- Split activity-log surface: `spec-kitty agent tasks add-history WP05 --mission templates-as-config-01KXMS1G ... --json` returned success from lane E but appended WP05 Activity Log entries to the primary checkout copy, not the coordination-worktree copy despite the prompt saying modern status authority resolves through coordination. Impact: evidence is invisible on the advertised authority surface until separately routed/committed. Workaround: locate the changed primary artifact and have the coordinator route it canonically. Status: issue-queue triage required.
- Inline-note quoting footgun: `add-history` exposes inline `--note` but no `--note-file`; markdown backticks passed through an inadequately escaped shell command triggered command substitution and mangled five append-only notes. Corrected entries were appended immediately. Impact: polluted immutable activity history and accidental command execution risk for orchestrators. Workaround: single-quote plain-text notes and avoid shell metacharacters. Recommendation: add `--note-file` parity with review-feedback-file. Status: issue-queue triage required.

### 2026-07-16 — WP05 handoff-gate follow-up observations

- `spec-kitty agent tasks move-task WP05 --to for_review ... --json` blocked on untracked primary `kitty-specs/templates-as-config-01KXMS1G/analysis-report.md`, classifying it as WP05-owned even though WP05 frontmatter owns only three test files. Impact: unrelated analysis residue prevents a clean lane handoff. Workaround: the explicitly authorized narrow `--force`; status: known false-positive, issue-queue triage required.
- The successful forced move returned `pre_review_gate.outcome=no_coverage` because importing `tests.architectural._gate_coverage` failed with `No module named pytest`, despite lane `.venv` containing pytest and explicit tests running successfully. Impact: the advertised automatic pre-review coverage authority was silently unavailable and nonblocking. Workaround: run explicit focused pytest plus pytest-cov/diff-cover and preserve output; status: issue-queue triage required.
