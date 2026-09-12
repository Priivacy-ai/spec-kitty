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
- path: tests/specify_cli/regression/_twelve_agent_baseline/
- path: tests/specify_cli/skills/__snapshots__/codex/tasks.SKILL.md
- path: tests/specify_cli/skills/__snapshots__/codex/tasks-packages.SKILL.md
- path: tests/specify_cli/skills/__snapshots__/vibe/tasks.SKILL.md
- path: tests/specify_cli/skills/__snapshots__/vibe/tasks-packages.SKILL.md
- path: kitty-specs/annoying-bugs-sweep-01KYHQ9F/tasks/WP03-resolver-backed-profile-load-doctrine.md
cycle_number: 4
mission_slug: annoying-bugs-sweep-01KYHQ9F
reproduction_command: PWHEADLESS=1 python -m pytest tests/specify_cli/skills/test_command_renderer.py
  tests/specify_cli/regression/test_twelve_agent_parity.py -q -p no:cacheprovider
reviewed_at: '2026-07-27T16:15:00Z'
reviewer_agent: claude
verdict: approved
wp_id: WP03
---

# WP03 Review Cycle 4 — Independent Verification Of The Cycle-3 Regression Fix

**Verdict: Approved.**

## Scope And Method

Independent review at lane HEAD `fc82caa01` in
`.worktrees/annoying-bugs-sweep-01KYHQ9F-lane-c`, plus the planning-branch commit
`95f320985` on `fix/annoying-bugs-sweep` (not visible from the lane).

Commits adjudicated:

| Commit | Branch | Content |
|--------|--------|---------|
| `716497624` | lane-c | Baseline regeneration (28 files) + `_GUIDANCE_FILE_FLOOR` 12→18 |
| `78d42708c` | lane-c | Relocate planning artifacts off the lane |
| `95f320985` | `fix/annoying-bugs-sweep` | `owned_files` + activity log |
| `fc82caa01` | lane-c | Auto-rebase merge — status churn only (see below) |

Cycle-3's two closed findings (raw-directory fallbacks; vacuous guard) were **spot-checked,
not redone**. Focus was the cycle-3 regression fix and anything new.

## Finding 3 (cycle 3) — 28 red baselines — **CLOSED**

Verified by running the gate myself, not by trusting the claim:

```
$ PWHEADLESS=1 python -m pytest tests/specify_cli/skills/test_command_renderer.py \
    tests/specify_cli/regression/test_twelve_agent_parity.py -q -p no:cacheprovider
311 passed in 46.30s
```

**311 passed matches base `dfc90cc24` exactly** (cycle 3 recorded 311 at base, 283+28 at the
broken lane HEAD). The count matches, not merely the colour.

## Baselines Were Regenerated Correctly, Not Merely Regenerated

The uniformity claim holds. All 28 baseline files in `716497624` show `6 +++++-` — exactly
5 insertions / 1 deletion each. Distinct-line analysis of the 28-file diff:

```
=== DISTINCT REMOVED LINES ===
  28 -> If this command is unavailable, look for profiles under `src/doctrine/agent_profiles/built-in/` and any user-defined profiles in `.kittify/agent_profiles/` or equivalent.

=== DISTINCT ADDED LINES ===
  28 +> state that limitation when selecting a profile this way.
  28 +> `src/doctrine/agent_profiles/built-in/` and any user-defined profile directory.
  24 +> `specializes_from` lineage, and `enhances<!-- glossary:glossary:enhances -->`/`overrides<!-- glossary:glossary:overrides -->` semantics are not applied;
  24 +> Only a read-only harness<!-- glossary:glossary:harness --> that cannot invoke the CLI may inspect profiles under
  16 +> This degraded fallback can diverge because organization/project overlays,
  12 +> This degraded fallback can diverge because organization/project<!-- glossary:glossary:project --> overlays,
   4 +> `specializes_from` lineage, and `enhances`/`overrides` semantics are not applied;
   4 +> Only a read-only harness that cannot invoke the CLI may inspect profiles under
```

**Exactly ONE distinct removed line** across all 28 files, and it is the old unbounded
fallback. Every added line is the bounded caveat. **No unrelated drift was absorbed.**

### Correction to the implementer's rendering-variant explanation

The implementer described the variance as "24 command baselines carry glossary annotations,
4 codex/vibe skill snapshots carry none." That is **incomplete** — it explains the `harness`
annotation but not the 12/16 split on `project`. I established the actual mechanism rather
than accepting the summary:

- **`harness`** — annotated in all 24 command baselines, absent from the 4 skill snapshots.
- **`project`** — annotated in the 12 `tasks-packages` command baselines only; absent from
  the 12 `tasks` baselines and the 4 skill snapshots.

Root cause is **first-occurrence-per-term-per-file**, not a missed source prompt:

```
$ grep -c 'glossary:glossary:project' _twelve_agent_baseline/claude/tasks.md    -> 1
$ grep -n  'glossary:glossary:project' _twelve_agent_baseline/claude/tasks.md
68:# Run from project<!-- glossary:glossary:project --> root (same directory as /spec-kitty.plan):
```

`tasks.md` already spends its single `project` annotation at line 68, so the later
occurrence in the new fallback block is unannotated. `tasks-packages.md` has no earlier
`project`, so the annotation lands in the new block. `harness` occurs exactly once per
command baseline — in the new block — so all 24 carry it.

The codex/vibe claim is confirmed by construction, not assertion: **all 24 codex/vibe
snapshots (not just the 4 touched) contain zero `glossary:glossary:` occurrences**, so the
skill renderer does not run the glossary pass at all. A missing annotation there cannot
indicate a missed source prompt.

### No stale text survives

Lane-worktree sweep (tracked and filesystem, including the 12 generated agent dirs present
in the worktree):

```
$ git grep -n "look for profiles under"
kitty-specs/.../review-cycle-1.md:24,40      # historical review record
kitty-specs/.../review-cycle-2.md:35,51      # historical review record
tests/architectural/test_profile_load_resolver_guidance.py:142   # the guard's own planted fixture
```

Zero hits in `src/doctrine/**`, zero in any baseline or snapshot, zero in any agent
directory. The three surviving classes are all correct: immutable review artifacts and the
self-mutation fixture that proves the guard non-vacuous.

## Generated Agent Copies Were Not Hand-Edited

```
$ git diff kitty/mission-annoying-bugs-sweep-01KYHQ9F..HEAD --name-only \
    | grep -E '^\.(claude|amazonq|augment|github|gemini|cursor|qwen|opencode|windsurf|kilocode|roo|kiro|agent|agents)/'
NONE — no generated agent copies touched
```

37 non-`kitty-specs/` files changed; every one is a canonical `src/doctrine/**` source, a
test, or a generated baseline/snapshot regenerated through `PYTEST_UPDATE_SNAPSHOTS=1`. The
regeneration is self-proving: the parity and renderer gates pass, which means committed
baseline == live renderer output byte-for-byte. A hand-edit would have to reproduce the
renderer exactly to pass, and the distinct-line analysis above rules out any extra edit.

## `_GUIDANCE_FILE_FLOOR` 12 → 18 — Judgement: **Sound**

Live telemetry (run against lane source with `PYTHONPATH=<lane-c>/src`):

```
live guidance files = 18  floor = 18
total doctrine text files scanned = 610
offenders = []
```

**The ratchet is correct, for three reasons.**

1. **Polarity is right.** The assertion is `len(guidance_files) >= _GUIDANCE_FILE_FLOOR`.
   Growth is free; only *shrink* trips it. That is exactly the direction that matters for a
   coverage denominator — the failure this guards is the scanned surface silently narrowing
   while the offender scan still reports green. A floor of 12 against a live 18 permitted a
   **33% silent shrink**, which is the vacuity risk charter standing order 5 exists to
   prevent.
2. **The failure mode is loud and self-adjudicating.** The assertion message enumerates
   every file found, and the new comment states the resolution rule explicitly ("Raise this
   in lockstep when new profile-load guidance lands; lower it ONLY alongside a deliberate,
   reviewed doctrine relocation that explains where the guidance went"). A brittle-but-loud
   gate with a one-line documented fix is strictly preferable to a silent gap.
3. **Convention-consistent.** The `frozen-baseline-shrink-only-ratchet` tactic names
   `tests/architectural/_baselines.yaml` as canonical, but that file backs only 3 gates
   (`test_no_dead_modules`, `test_no_dead_symbols`, `test_ratchet_baselines`), while the
   module-constant floor/ceiling style is the prevailing convention across 7+ gates in
   `tests/architectural/`. This is not a canonical-source violation.

**Counter-argument, weighed and rejected as blocking.** The denominator is built from fuzzy
markers, so two of the 18 files (`java-conventions.styleguide.yaml`,
`python-conventions.styleguide.yaml`) match incidentally. An unrelated edit removing a
passing mention could redden the gate for a reason unconnected to profile-load doctrine.
Real, but low-cost: a loud red with a full file listing and a documented one-line
adjudication. Note that the tactic is cited **by analogy** — it governs a debt allowlist
where *growth* is the failure, whereas this is a coverage floor where *shrink* is the
failure. The transferable principle (pin a countable to the live value; movement in the
unsafe direction requires deliberate reviewed human action with recorded rationale) holds.

## `owned_files` (commit `95f320985`) — Verified Independently

Parsed all five WP frontmatters with `yaml.safe_load`:

```
WP01: YAML OK, 5 owned paths
WP02: YAML OK, 5 owned paths
WP03: YAML OK, 14 owned paths
WP04: YAML OK, 6 owned paths
WP05: YAML OK, 2 owned paths

=== pairwise overlap WP03 vs others (exact + directory-prefix) ===
  WP03 vs WP01: disjoint
  WP03 vs WP02: disjoint
  WP03 vs WP04: disjoint
  WP03 vs WP05: disjoint
```

14 paths, YAML parses (the interleaved `# Added cycle 3:` comments are valid), disjoint
under both exact and directory-prefix matching. **Overlap-in-fact** also checked — no other
lane branch's diff touches any WP03-owned path. The 14 declared paths cover all 37 changed
non-`kitty-specs/` files (24 baselines + 4 snapshots + 7 doctrine + 2 tests).

**Cross-branch consistency verified.** The `78d42708c` (remove from lane) →
`95f320985` (add on planning branch) relocation nets out correctly: the WP md is now
**byte-identical** on `fix/annoying-bugs-sweep`, `kitty/mission-...-01KYHQ9F`, and
`...-lane-c`, all carrying the 14-entry list. There is no risk of the lane merge reverting
the ownership map.

## Additional Verification Not Requested

**No phantom commands introduced.** #1840's second stale claim was a phantom-command
assertion, so I checked that every CLI surface the new doctrine instructs actually exists —
resolved against **lane source**, since ambient `import specify_cli` resolves to a different
checkout (`/home/stijn/.../spec-kitty/src/specify_cli`, confirmed):

| Instructed surface | Exists |
|---|---|
| `spec-kitty agent profile show <id>` (`--json`, `--all`) | yes |
| `spec-kitty agent profile list --json` (`--all`) | yes |
| `spec-kitty charter context --action <a> --json` (`--include`) | yes |
| `spec-kitty dispatch "<req>" --profile <id>` | yes |

**T017 (#1840) satisfied.** The ticket body carries a "Two corrections to this ticket's
earlier body (2026-07-27)" section that explicitly withdraws both stale claims — the
"`agent profile show` is a phantom command" claim and the "reliable mechanism today is
reading the profile YAML directly" recommendation.

**`fc82caa01` is not WP03 content.** The auto-rebase merge carries only
`status.events.jsonl` / `status.json` churn from WP04/WP05 activity on other lanes. Per the
WP-isolation rules, ignored.

**Guard non-vacuity spot-check** (4 independent probes against the live predicate, not the
committed fixtures):

```
[PASS] A pre-fix wording VERBATIM (cycle-1 false negative): detected=True  expected=True
[PASS] B shipped caveated fallback VERBATIM from real prompt: detected=False expected=False
[PASS] C benign path mention (no imperative): detected=False expected=False
[PASS] D read-only stated but NO divergence caveat: detected=True  expected=True

4/4 spot-check probes behaved as expected
```

Consistent with cycle 3's 11-probe sweep. Guard is non-vacuous and not over-broad.

**Skill-pack test is not a synthetic fixture.** `test_profile_load_skill_owns_and_installs_detailed_mechanics`
invokes `SkillRegistry.from_local_repo(REPO_ROOT)` and asserts on `skill.references` —
production resolution, not a literal dict.

**Alias direction correct.** `ad-hoc-profile-load/SKILL.md` defers to
`spk-doctrine-profile-load`; the canonical skill does **not** depend on the alias for
mechanics. Body lengths: alias 38, canonical 41, reference 81 (a reference, not a SKILL
body). The enforced ≤80 rule applies to `SPK_SKILLS` bodies only; `adversarial-squad` body
is 69 lines.

## Base-vs-HEAD Failing-Node Diff

This is the check the earlier (wrongly-approving) review skipped. Broad adjacent suites,
same command, at HEAD and at merge-base `78c7d64d1`:

```
$ PWHEADLESS=1 python -m pytest tests/architectural/ tests/doctrine/ \
    tests/specify_cli/skills/ tests/specify_cli/regression/ -q -p no:cacheprovider

BASE: 1 failed, 4558 passed, 4 skipped, 83 warnings in 1308.19s (0:21:48)
HEAD: 1 failed, 4565 passed, 4 skipped, 83 warnings in 1315.79s (0:21:55)
```

```
=== BASE failing nodes ===
FAILED tests/architectural/test_no_raw_mission_spec_paths.py::test_constant_based_mission_spec_path_construction_stays_in_constructor_files
=== HEAD failing nodes ===
FAILED tests/architectural/test_no_raw_mission_spec_paths.py::test_constant_based_mission_spec_path_construction_stays_in_constructor_files
=== diff of failing-node sets ===
IDENTICAL — zero introduced, zero masked
```

**Zero introduced, zero masked.** The single failure is present at base — pre-existing, not
this diff (baseline-red gotcha applied).

**+7 passed is fully attributable.** 4558 → 4565 = exactly WP03's 7 new tests: 6 in the new
`test_profile_load_resolver_guidance.py` and 1 in `test_spk_skill_pack.py`. No test count
inflation, no silently-skipped test.

## Verbatim Gate Output

WP-declared 5-file doctrine gate suite:

```
$ PWHEADLESS=1 python -m pytest tests/architectural/test_profile_load_resolver_guidance.py \
    tests/doctrine/test_spk_skill_pack.py tests/architectural/test_docs_cli_reference_parity.py \
    tests/architectural/test_no_legacy_terminology.py tests/doctrine/test_procedure_consistency.py \
    -q -p no:cacheprovider
............ss...........                                                [100%]
23 passed, 2 skipped in 38.92s
```

Terminology guard, standalone (required — doctrine prose touched):

```
$ PWHEADLESS=1 python -m pytest tests/architectural/test_no_legacy_terminology.py -q -p no:cacheprovider
....                                                                     [100%]
4 passed in 35.28s
```

Regression gate (the cycle-3 blocker):

```
$ PWHEADLESS=1 python -m pytest tests/specify_cli/skills/test_command_renderer.py \
    tests/specify_cli/regression/test_twelve_agent_parity.py -q -p no:cacheprovider
311 passed in 46.30s
```

Diff-scoped ruff (`main` does not exist in this checkout; base is
`kitty/mission-annoying-bugs-sweep-01KYHQ9F`):

```
$ ruff check tests/architectural/test_profile_load_resolver_guidance.py \
    tests/doctrine/test_spk_skill_pack.py
All checks passed!
exit=0
```

## Anti-Pattern Checklist

1. **Dead code** — PASS. Doctrine and tests only. The new reference is reachable through
   `CanonicalSkill.references` and asserted via live `SkillRegistry` resolution.
2. **Synthetic-fixture test** — PASS. Guard non-vacuity re-proven by 4 independent probes
   including the exact cycle-1 false-negative string; skill-pack test drives production
   resolution.
3. **Silent empty return** — PASS. No new exception handlers. The guidance denominator is
   floored at 18 and cannot silently collapse.
4. **FR coverage** — PASS. C-005, C-006, FR-007, FR-008, FR-009, FR-011, NFR-003 all
   exercised by the guard and skill-pack assertions.
5. **Frozen surface** — PASS (was FAIL in cycle 3). Baselines regenerated through the
   sanctioned mechanism; parity and renderer gates green at the base's own count.
6. **Locked decision** — PASS. No unconditional raw-read ban; the bounded fallback survives
   as #2304 requires.
7. **Shared-file ownership** — PASS. 14 paths, disjoint by declaration and in fact,
   consistent across all three branches.
8. **Production fragility** — N/A. No production `raise` added.
9. **Baseline-red discipline** — PASS. Failing-node sets diffed base vs HEAD; the single red
   is pre-existing.

## Non-Blocking Observations

- **[LOW]** The implementer's rendering-variant explanation was incomplete (see the
  correction above). The underlying regeneration is correct; only the narrative was.
- **[LOW]** `_GUIDANCE_FILE_FLOOR` guards a marker-matched subset (18 files), while the
  offender scan's true denominator is all 610 doctrine text files. Non-vacuity is
  nonetheless established by the three committed self-mutation tests plus reviewer probes.
  A future tightening could floor the 610 as well.
