---
affected_files:
- path: src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md
- path: src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md
- path: src/doctrine/skills/ad-hoc-profile-load/SKILL.md
- path: src/doctrine/skills/spk-doctrine-profile-load/SKILL.md
- path: src/doctrine/skills/spk-doctrine-profile-load/references/profile-load-mechanics.md
- path: src/doctrine/skills/adversarial-squad/SKILL.md
- path: src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml
- path: tests/architectural/test_profile_load_resolver_guidance.py
- path: tests/doctrine/test_spk_skill_pack.py
- path: tests/specify_cli/skills/__snapshots__/codex/tasks.SKILL.md
- path: tests/specify_cli/skills/__snapshots__/codex/tasks-packages.SKILL.md
- path: tests/specify_cli/skills/__snapshots__/vibe/tasks.SKILL.md
- path: tests/specify_cli/skills/__snapshots__/vibe/tasks-packages.SKILL.md
- path: tests/specify_cli/regression/_twelve_agent_baseline/
cycle_number: 3
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: PWHEADLESS=1 python -m pytest tests/specify_cli/skills/test_command_renderer.py
  tests/specify_cli/regression/test_twelve_agent_parity.py -q -p no:cacheprovider
reviewed_at: '2026-07-27T15:03:08Z'
reviewer_agent: claude
verdict: rejected
wp_id: WP03
---

# WP03 Review Cycle 3 — Independent Re-verification at Current HEAD

## Scope And Method

This is an **independent re-verification**, not an endorsement of `review-cycle-2.md`.
It was performed against the live tree at lane HEAD `6251ca35e` in
`.worktrees/annoying-bugs-sweep-01KYHQ9F-lane-c`, reviewing the cumulative diff of
`c3f290654` (initial implementation) and `096e50b0e` (cycle-2 raw-directory fallback fix)
against the WP's declared `base_commit` `dfc90cc24`.

`review-cycle-2.md` is confirmed to be a **stale artifact**: its body is byte-identical to
`review-cycle-1.md` (title "WP03 Review Cycle 1"), its `reviewer_agent` is `unknown`, its
`affected_files` is empty and its `reproduction_command` is blank. Its two HIGH findings were
re-adjudicated from first principles below and **both are genuinely fixed**. The stale
artifact is left untouched as the historical record.

**However, this review rejects on a different, newly-identified and currently-present
defect** (Finding 3): commit `096e50b0e` changed two canonical mission-step prompts without
regenerating the twelve-agent parity baselines and the codex/vibe skill snapshots, leaving
28 tests red on the lane branch that are green on the WP's own base commit.

## Verdict

**Rejected.** Both cycle-2 findings are correctly remediated, but the remediation introduced
a regression in the generated-command parity gates that must be closed before merge.

## Adjudication Of The Two Cycle-2 Findings

### Finding 1 (HIGH) — unbounded CLI-unavailable profile-directory fallbacks — **FIXED**

Both canonical source prompts now carry a bounded, caveated fallback. Verbatim at HEAD:

`src/doctrine/missions/mission-steps/software-dev/tasks/prompt.md:555-559`

```
> Only a read-only harness that cannot invoke the CLI may inspect profiles under
> `src/doctrine/agent_profiles/built-in/` and any user-defined profile directory.
> This degraded fallback can diverge because organization/project overlays,
> `specializes_from` lineage, and `enhances`/`overrides` semantics are not applied;
> state that limitation when selecting a profile this way.
```

`src/doctrine/missions/mission-steps/software-dev/tasks-packages/prompt.md:234-238` carries
the identical block. The pre-fix text
`> If this command is unavailable, look for profiles under \`src/doctrine/agent_profiles/built-in/\` and any user-defined profiles in \`.kittify/agent_profiles/\` or equivalent.`
is gone from both.

The fallback is bounded ("Only a read-only harness that cannot invoke the CLI") and states
the divergence warning across all three axes required by C-006 — overlays, `specializes_from`
lineage, and `enhances`/`overrides`. Only canonical `src/doctrine/**` sources were edited; no
`.agents/**` or agent-directory copy was touched.

I independently swept every remaining reference to `agent_profiles/` or `.agent.yaml` under
`src/doctrine/**` and confirmed the other two of issue #1840's four raw-read sites are also
bounded and caveated:

- `src/doctrine/skills/adversarial-squad/SKILL.md:54-58` — *"Only a read-only harness that
  cannot invoke the CLI may read `src/doctrine/agent_profiles/built-in/<id>.agent.yaml`; that
  degraded fallback can diverge because overlays, `specializes_from` lineage, and
  `enhances`/`overrides` semantics are not applied."*
- `src/doctrine/procedures/built-in/adversarial-squad-deployment.procedure.yaml:41-46` —
  same wording in the dispatch step description.
- `src/doctrine/skills/spk-doctrine-profile-load/references/profile-load-mechanics.md:59-69`
  — section "4. Read-Only Harness Fallback", which additionally states *"Do not use this
  fallback when either resolver-backed command can run, and do not use it to author or mutate
  a profile."*

Remaining `agent_profiles/` mentions in doctrine are benign data/path references (`README.md`
kind table, `skills/README.md` repository listing, two styleguide `related_artifacts` lists,
two tactic references to `agent_profiles/repository.py`). None present a raw read as primary.

**Finding 1 is closed.**

### Finding 2 (HIGH) — vacuous guard, false negative on directory lookups — **FIXED, mutation-proven**

`tests/architectural/test_profile_load_resolver_guidance.py` now carries a second predicate
pair alongside the `.agent.yaml` file matcher:

```python
_RAW_PROFILE_DIRECTORY = re.compile(
    r"(?:src/doctrine/)?agent_profiles/(?:built-in/)?", re.IGNORECASE)
_RAW_DIRECTORY_LOOKUP = re.compile(
    r"\b(?:look\s+for|search|searches|browse|browses|inspect|inspects)\b"
    r"(?:(?!\n\s*\n).){0,240}"
    r"(?:src/doctrine/)?agent_profiles/(?:built-in/)?",
    re.IGNORECASE | re.DOTALL)
```

`_raw_profile_instruction_offenders` now ORs `file_lookup` and `directory_lookup`, and both
paths are exempted only when `_is_bounded_read_only_fallback` finds **all** of `read-only`,
`cannot invoke the cli` **and all** of `diverge`, `overlays`, `lineage`, `overrides` in the
same paragraph.

#### Mutation proof — my own, not the committed fixtures

I did not rely on the two committed fixture tests. I imported the live predicate
`_raw_profile_instruction_offenders` from the guard module and drove 11 planted fixtures
through it (`scratchpad/mutation_probe.py`). Result: **11/11 behaved as expected.**

```
[PASS] M1 exact pre-fix wording (cycle-1 false negative): detected=True expected=True
[PASS] M1b exact pre-fix wording, no backticks: detected=True expected=True
[PASS] M2 raw .agent.yaml read presented as primary: detected=True expected=True
[PASS] M3 'search' verb variant: detected=True expected=True
[PASS] M4 'browse' verb variant: detected=True expected=True
[PASS] M5 shipped fallback text VERBATIM from tasks/prompt.md (must be allowed): detected=False expected=False
[PASS] M6 benign path mention, no imperative (must be allowed): detected=False expected=False
[PASS] M7 benign resolver instruction (must be allowed): detected=False expected=False
[PASS] M8 benign unrelated dir inspection (must be allowed): detected=False expected=False
[PASS] M9 partial caveat: read-only stated but NO divergence warning (must flag): detected=True expected=True
[PASS] M10 partial caveat: divergence stated but unbounded (must flag): detected=True expected=True

11/11 probes behaved as expected
```

M1 is the exact string cycle 1 proved returned `[]`. It is now **DETECTED**. The guard is no
longer vacuous for the declared defect class.

#### Historical-revert proof (strongest form)

I copied the live `src/doctrine/` tree to scratch, restored the *actual* pre-fix one-line
fallback into both real prompts, and re-ran the live predicate:

```
LIVE TREE: guidance files = 18  floor = 12
LIVE TREE: offenders = 0 []
all doctrine text files scanned = 610
REVERTED COPY: offenders = 2 ['missions/mission-steps/software-dev/tasks/prompt.md',
                              'missions/mission-steps/software-dev/tasks-packages/prompt.md']
```

The guard flags exactly the two production files when the defect is restored, and exactly
zero when it is not. Over-broadening is ruled out by M5–M8 (the shipped caveated fallback, a
benign path mention, a resolver instruction, and an imperative inspection of an unrelated
doctrine directory all pass) and by the live tree reporting 0 offenders across 610 scanned
doctrine text files.

**Finding 2 is closed.**

## New Finding

**[HIGH] `tests/specify_cli/regression/_twelve_agent_baseline/**` and
`tests/specify_cli/skills/__snapshots__/{codex,vibe}/{tasks,tasks-packages}.SKILL.md` —
generated-command baselines were not regenerated after the `096e50b0e` prompt edit, leaving
28 tests red on the lane branch that are green on the WP's base commit.**

`test_twelve_agent_parity.py::test_command_output_unchanged` and
`test_command_renderer.py::test_snapshot` render the twelve agent command files and the
codex/vibe skill files from `src/doctrine/missions/mission-steps/**` and diff them against
committed baselines. Changing the source prompt without regenerating the baselines breaks
them. Failure body:

```
tests/specify_cli/regression/test_twelve_agent_parity.py:148: in test_command_output_unchanged
    assert produced == expected, (
E   AssertionError: Command-file output for claude/tasks changed.
E     This mission must not modify the twelve non-migrated agents.
E     If the change is intentional (e.g. a cross-agent template edit),
E     regenerate the baseline with:
E       PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v
E     then commit the updated baseline files alongside the template change.
E     - > If this command is unavailable, look for profiles under `src/doctrine/agent_profiles/built-in/` and any user-defined profiles in `.kittify/agent_profiles/` or equivalent.
E     + > Only a read-only harness<!-- glossary:glossary:harness --> that cannot invoke the CLI may inspect profiles under...
```

The 28 failures are 24 `test_twelve_agent_parity` params (`tasks` and `tasks-packages` ×
claude, gemini, copilot, cursor, qwen, opencode, windsurf, kilocode, auggie, q, kiro,
antigravity) and 4 `test_command_renderer` snapshots (codex/vibe × tasks/tasks-packages).

**Attribution (baseline-red gotcha applied).** These are category-zero — *yours*, not
pre-existing. Same two files, same command:

| Tree | Result |
|------|--------|
| Base `dfc90cc24` (WP03 `base_commit`, temp detached worktree, `PYTHONPATH=<base>/src`) | **311 passed, 0 failed** |
| Lane HEAD `6251ca35e` | **283 passed, 28 failed** |

Not a known-P0 red (#2736/#2772/#1834), not a CI-environment/auth/sync-toggle failure, not a
stale-install false red — the diff text in the assertion is verbatim the `096e50b0e` change.

**Remediation.** Regenerate and commit both baseline sets alongside the template change, per
the failure message:

```bash
PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v
PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/skills/test_command_renderer.py -v
```

Note the rendered output injects a glossary annotation on "harness"
(`read-only harness<!-- glossary:glossary:harness -->`); this is the normal renderer pipeline,
not a defect, and will be captured by the regeneration. The regenerated baseline files must be
added to WP03's `owned_files` (see the observation below) since they are generated artifacts
of an owned source edit and no other WP touches them.

## Observations (non-blocking)

**[MEDIUM] Ownership map was not revised for the two mission-step prompts.** Cycle 1
instructed *"revise/finalize ownership before editing them"*. `096e50b0e`'s commit message
declares them "reviewer-authorized out-of-map edits", but
`WP03-resolver-backed-profile-load-doctrine.md` `owned_files` still lists only the original
seven paths. I verified no other WP in this mission (WP01, WP02, WP04, WP05) owns or touches
`src/doctrine/missions/mission-steps/**`, so the real guard — no overlap — holds, and charter
standing order 8 grants ownership-map leeway. Fold the two prompts (and the regenerated
baselines) into `owned_files` when addressing Finding 3.

**[LOW] `_GUIDANCE_FILE_FLOOR = 12` against an actual denominator of 18.** The floor is
concrete and non-zero as T016 requires, but it permits a one-third silent shrink before the
guard complains. Consider ratcheting toward the live count per the
`frozen-baseline-shrink-only-ratchet` tactic. Not a defect in this WP.

## Verification — verbatim gate output

WP-declared gate suite (lane HEAD):

```
$ PWHEADLESS=1 python -m pytest tests/architectural/test_profile_load_resolver_guidance.py \
    tests/doctrine/test_spk_skill_pack.py \
    tests/architectural/test_docs_cli_reference_parity.py \
    tests/architectural/test_no_legacy_terminology.py \
    tests/doctrine/test_procedure_consistency.py -q -p no:cacheprovider
............ss...........                                                [100%]
23 passed, 2 skipped in 40.45s
```

(Cycle 1 recorded 21 passed / 2 skipped; the +2 are the guard's new directory-lookup
offender and allowed-fallback fixtures.)

Diff-scoped ruff:

```
$ ruff check tests/architectural/test_profile_load_resolver_guidance.py \
    tests/doctrine/test_spk_skill_pack.py
All checks passed!
exit=0
```

Live guard telemetry on the current tree:

```
guidance files = 18 (floor 12) | offenders = 0 | doctrine text files scanned = 610
```

Regression gate (the blocking one):

```
$ PWHEADLESS=1 python -m pytest tests/specify_cli/skills/test_command_renderer.py \
    tests/specify_cli/regression/test_twelve_agent_parity.py -q -p no:cacheprovider
28 failed, 283 passed in 47.69s

# same command at base dfc90cc24:
311 passed in 64.66s (0:01:04)
```

Skill length ceiling (80 lines):

```
38 src/doctrine/skills/ad-hoc-profile-load/SKILL.md
41 src/doctrine/skills/spk-doctrine-profile-load/SKILL.md
81 src/doctrine/skills/spk-doctrine-profile-load/references/profile-load-mechanics.md  (reference, not a SKILL body)
```

Alias direction verified: `ad-hoc-profile-load/SKILL.md` states *"This is the compatibility
alias for `spk-doctrine-profile-load`. The canonical skill owns the mechanics; do not maintain
a second profile-loading procedure here."* and defers mechanics to the canonical reference.
`test_spk_skill_pack.py::test_profile_load_skill_owns_and_installs_detailed_mechanics` asserts
the reference is discovered through `SkillRegistry` / `CanonicalSkill.references`, so it is
installed and not orphaned.

## Anti-Pattern Checklist

- **Dead code** — PASS. Doctrine and tests only. The new reference is reachable through
  `CanonicalSkill.references` and asserted by the skill-pack test.
- **Synthetic-fixture test** — PASS (was FAIL in cycle 1). Independently mutation-proven:
  11/11 planted-fixture probes and a full historical-revert of the real production text that
  turns the guard red on exactly the two real files.
- **Silent empty return** — PASS. `_profile_guidance_files` is floored at 12 against a live
  18; the denominator cannot silently collapse to zero.
- **Guard over-broadening** — PASS. The shipped caveated fallback, benign path mentions,
  resolver instructions, and imperative inspection of unrelated doctrine directories are all
  allowed; 0 offenders across 610 scanned files.
- **FR coverage** — FR-007 PASS, FR-008 PASS, C-006 PASS, NFR-003 PASS. All four #1840
  raw-read sites are now bounded and caveated.
- **Frozen surface** — **FAIL.** The twelve-agent parity baseline and the codex/vibe renderer
  snapshots are frozen surfaces that were invalidated without regeneration (Finding 3).
- **Locked decision** — PASS.
- **Shared-file ownership** — PASS on overlap (no other WP touches the mission-step prompts);
  MEDIUM hygiene note on the un-revised `owned_files` list.
- **Production fragility** — N/A.
- **Baseline-red discipline** — PASS. The 28 reds were attributed against the WP's own base
  commit before being charged to this WP; base is green.
