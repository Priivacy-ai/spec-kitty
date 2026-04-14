---
work_package_id: WP09
title: ADR, CHANGELOG, and Kent Diagnostic Comment
dependencies:
- WP01
- WP02
- WP05
- WP06
- WP07
requirement_refs:
- FR-021
- FR-022
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
phase: Phase 2 — Documentation and handoff
agent: "claude:opus-4.6:implementer:implementer"
shell_pid: "83553"
history:
- timestamp: '2026-04-14T05:26:49Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: architecture/1.x/adr/
execution_mode: code_change
mission_id: 01KP54ZWEEPCC2VC3YKRX1HT8W
owned_files:
- architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md
- CHANGELOG.md
tags: []
wp_code: WP09
---

# Work Package Prompt: WP09 — ADR, CHANGELOG, and Kent Diagnostic Comment

## Implementation Command

```bash
spec-kitty agent action implement WP09 --agent <your-agent-name> --mission 01KP54ZW
```

Depends on WP01, WP02, WP05, WP06, WP07. Start only after all technical WPs have landed so the ADR and CHANGELOG reflect the actual shipped architecture.

---

## Branch Strategy

- **Planning branch**: `main`
- **Final merge target**: `main`
- Lane allocation by `finalize-tasks`; resolve from `lanes.json`.

---

## Objective

Document the mission's architectural decision in an ADR, update the user-facing CHANGELOG with a recovery recipe for affected users, and post the diagnostic comment on Priivacy-ai/spec-kitty#588 asking Kent to confirm the origin of the sparse-checkout state.

---

## Context

- DIRECTIVE_003 (decision documentation) and the `adr-drafting-workflow` tactic require this ADR; R9 in research.md proposed it.
- FR-021 defines what the CHANGELOG must cover; the recovery recipe is the actionable part for users who already took the hit.
- FR-022 is a courtesy comment to the reporter; non-blocking.

---

## Subtask Guidance

### T034 — Draft the ADR

**Files**: `architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md` (new)

**What**: Follow the existing ADR template in `architecture/1.x/adr/`. Title: **"Sparse-Checkout Defence in Depth: Four-Layer Hybrid Preflight + Commit-Layer Backstop"**.

Sections:

1. **Status**: Accepted (date 2026-04-14).
2. **Context**: summarize the #588 regression and the three plausible responses (merge-only preflight, universal preflight, defence in depth). Reference the mission spec and Decision Log by path.
3. **Decision**: the four-layer hybrid:
   - Layer 1 (hard block at merge + implement)
   - Layer 2 (universal backstop in `safe_commit`)
   - Layer 3 (session-scoped warning at other CLI surfaces)
   - Layer 4 (`doctor` as the discovery surface)
4. **Consequences**:
   - Positive: data-loss regression closed at multiple layers. Legitimate-sparse users still have an escape hatch via `--allow-sparse-checkout`.
   - Negative: `safe_commit` now has a fail-closed assertion that may surface legitimate edge cases in existing callers; mitigated by audit of callers (WP01).
   - Open: the `--allow-sparse-checkout` override emits a log record only, not a durable event; tracked as Priivacy-ai/spec-kitty#617.
5. **Alternatives considered and rejected**:
   - Merge-only preflight (misses lane-worktree inheritance + external-pull cascade).
   - Blanket-gate on every state-mutating command (redundant with layer 2, degrades UX).
   - Reintroduce sparse-checkout support (explicitly out of scope per C-001).
6. **References**: Priivacy-ai/spec-kitty#588, #589, #617; mission spec path; PR link (to be filled in at merge time).

---

### T035 — CHANGELOG entry + recovery recipe [P]

**Files**: `CHANGELOG.md`

**What**: Append a new entry at the top of the unreleased section (or create the unreleased section if absent).

Required content:

- **Fixed**:
  - "`mission merge` no longer silently loses content when the repository carries legacy sparse-checkout state (Priivacy-ai/spec-kitty#588)."
  - "`move-task --to approved` and `--to planned` on a lane-worktree review no longer require `--force` when the only untracked content is `.spec-kitty/` (Priivacy-ai/spec-kitty#589)."
  - "Retry guidance emitted by the uncommitted-changes guard now names the actual target lane rather than hardcoded `for_review`."
- **Added**:
  - "`spec-kitty doctor --fix sparse-checkout` — migration for repositories upgraded from pre-3.0 spec-kitty that still carry sparse-checkout state."
  - "`--allow-sparse-checkout` flag on `mission merge` and `agent action implement` for users with intentional sparse configurations (use is logged at WARNING level)."
  - "Commit-time backstop inside `safe_commit` that aborts commits whose staging area contains unexpected paths."
- **Recovery for users already affected**:

  ```
  If a prior mission merge landed on your target branch with a silent
  content reversion (symptoms: a follow-up 'chore: record done transitions'
  commit that deleted content merged in the preceding commit), restore the
  content from the merge commit that introduced it:

      # Identify the merge commit
      git log --merges --oneline -- <affected-file>

      # Restore content from that merge
      git checkout <merge-sha> -- <affected-file> [...]

      # Commit the restoration
      git add <affected-file> [...]
      git commit -m "fix: restore content reverted by phantom-deletion bug"

  Then run the migration to prevent recurrence:

      spec-kitty doctor --fix sparse-checkout
  ```

---

### T036 — Post diagnostic comment on #588 [P]

**What**: Post a comment on `https://github.com/Priivacy-ai/spec-kitty/issues/588` asking Kent to run three diagnostic commands in his `kg-automation` primary repo and report the output:

```bash
git config --get core.sparseCheckout
git sparse-checkout list 2>/dev/null || echo "(no sparse-checkout list)"
cat .git/info/sparse-checkout 2>/dev/null || echo "(no pattern file)"
```

Explain that this confirms the legacy-spec-kitty-origin theory so future migrations and diagnostics can be tuned correctly. Link to Priivacy-ai/spec-kitty#617 for the follow-up on durable audit events.

Use `gh` to post:

```bash
unset GITHUB_TOKEN && gh issue comment 588 --repo Priivacy-ai/spec-kitty --body "<comment body>"
```

The comment is non-blocking for mission acceptance. If posting fails, retry or escalate to the user — do NOT mark T036 done without the comment landing.

---

## Definition of Done

- [ ] `architecture/1.x/adr/2026-04-14-1-sparse-checkout-defense-in-depth.md` exists with all required sections.
- [ ] `CHANGELOG.md` contains the entries listed in T035 (Fixed, Added, Recovery recipe).
- [ ] Diagnostic comment posted on Priivacy-ai/spec-kitty#588; link to the comment recorded in the CHANGELOG or research doc.
- [ ] No other code changes in this WP beyond the files listed in `owned_files`.

## Risks

- **Content stale-ness**: WP09 starts late; if any technical WP lands with subtly different behaviour than the spec anticipated, the ADR and CHANGELOG must track the actual shipped behaviour, not the original intent.
- **Comment posting authentication**: `gh` often has two auth contexts (`GITHUB_TOKEN` env var vs keyring). `unset GITHUB_TOKEN` before posting per the project's CLAUDE.md instruction.

## Reviewer Guidance

- Verify the ADR matches the Decision Log entries in `spec.md` (same alternatives, same rationale).
- Verify the CHANGELOG recovery recipe is copy-paste runnable.
- Verify the posted comment is locatable via `gh issue view 588 --repo Priivacy-ai/spec-kitty --comments`.

## Activity Log

- 2026-04-14T07:51:46Z – claude:opus-4.6:implementer:implementer – shell_pid=83553 – Started implementation via action command
- 2026-04-14T07:57:51Z – claude:opus-4.6:implementer:implementer – shell_pid=83553 – Ready for review
- 2026-04-14T07:59:52Z – claude:opus-4.6:implementer:implementer – shell_pid=83553 – ADR + CHANGELOG + #588 diagnostic comment approved. Scope respects owned_files (ADR new, CHANGELOG edit, no code). ADR covers all required sections (Context, Decision, four layers labeled, Consequences, Considered Options with pros/cons including Options A/B/D rejections, References, WP-surface index mapping WP01-WP07+WP09). Format matches adr template (Date/Status/Deciders/Tags header, Decision Drivers, Confirmation). CHANGELOG under [Unreleased], cites #588/#589/#617, has copy-paste recovery recipe with migration step. FR-021 (recovery recipe) and FR-022 (diagnostic comment link in CHANGELOG) both covered. Smoke tests: 89/89 pass on unit/git + sparse_checkout + review + worktree exclude suites. Final WP — mission ready to merge.
