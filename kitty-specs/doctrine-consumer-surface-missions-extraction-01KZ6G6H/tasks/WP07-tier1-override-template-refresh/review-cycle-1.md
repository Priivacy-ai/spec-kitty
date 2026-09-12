# WP07 Review — cycle 1

Reviewer: reviewer-renata (claude:opus:reviewer-renata:reviewer)
Commit reviewed: `02d1a2239`
Verdict: **changes requested — one blocking item**

## Summary

The template refresh itself is correct and I verified every acceptance criterion by
direct execution. SC-004 is genuinely clean, both substituted commands really exist,
the `build_activation_aware_doctrine_service` call shape matches the documented
contract, and scope discipline holds. **The only blocker is the issue-matrix gate.**

Fix Issue 1 and this is approvable as-is. Issues 2 and 3 are observations —
address or explicitly wave off in your response; neither requires a code change.

---

## Issue 1 (BLOCKING) — issue-matrix row `#3182` verdict is still `unknown`

`kitty-specs/doctrine-consumer-surface-missions-extraction-01KZ6G6H/issue-matrix.json`
row `#3182` is an unfilled placeholder:

```json
{ "verdict": "unknown", "fr": null, "wp": null,
  "title": "<fill at WP-implementation time>", "evidence_ref": "<link or commit>" }
```

`#3182` is precisely the issue this WP closes — `spec.md:6` lists it under
"Bundled fixes: #3183, #3182", and this WP's own prompt cites it by number
("per the original issue #3182's own framing, this was deliberately not folded
into the sole-door landing for exactly this reason"). A per-WP `approved`
transition requires a non-`unknown` verdict on every issue the WP resolves;
`unknown` blocks approval.

I confirmed all 11 rows are still unfilled (zero non-`unknown` verdicts) and that
no fresher copy exists on any ref — `git log --all` shows the matrix untouched
since the planning commit `5c91fe1d5`. So nothing is stale in your checkout;
the row simply has not been recorded yet.

**Remedy** — record the verdict through the canonical command (it exists; I checked
`spec-kitty agent issue-verdict --help`). `in-mission` passes at per-WP `approved`;
`fixed` is also defensible here since the two files are now clean:

```
spec-kitty agent issue-verdict \
  --mission doctrine-consumer-surface-missions-extraction-01KZ6G6H \
  --issue "#3182" --verdict fixed --actor claude \
  --wp WP07 --evidence-ref 02d1a2239
```

Do not hand-edit the JSON — the command routes the write via
`write_target(ISSUE_MATRIX)`, which hand-editing bypasses.

---

## Issue 2 (non-blocking) — stated rationale cites PowerShell content the diff deleted

Your refresh-over-delete justification listed "PowerShell agent-identity flag docs"
as one of three divergences with no canonical equivalent, and therefore as a reason
to keep these files. But the diff removes **all** PowerShell content from
`implement.md`; `grep -i powershell` over both files now returns zero matches.

To be clear, I am not asking you to restore it wholesale:

- The first removed `<details>` block was a verbatim duplicate of the bash command
  (identical `spec-kitty agent workflow implement $ARGUMENTS --agent <your-name>`
  text). Deleting that is a clean win.
- The second block was genuinely different — `Set-Location .worktrees\...` plus
  `git add -A` / `git commit`. That was real Windows guidance and it is now gone.

Removing it is outside what FR-007 required, so it is not a correctness failure.
The problem is that the *argument for keeping the files* rested partly on content
the change then deleted. Either restore the `Set-Location` block, or state plainly
that the Windows guidance was intentionally dropped and why — so the next reader
is not misled about what the file still carries.

## Issue 3 (non-blocking) — `review.md` teaches `--to done`, canonical teaches `--to approved`

`review.md` (the reviewer-approval bullet, near line 117 in the refreshed file):

```
- ✅ Approve: `spec-kitty agent tasks move-task WP## --to done --mission <handle> --note "..."`
```

The canonical mission-step prompt at
`src/doctrine/missions/mission-steps/software-dev/review/prompt.md:258` teaches
`--to approved` instead. You edited this exact line (to add `--mission <handle>`),
so it was in your hands.

I verified this is **not** broken: `InReviewState.allowed_targets()` in
`src/specify_cli/status/wp_state.py:429-439` includes `Lane.DONE`, so
`in_review → done` is a legal transition. It is a divergence from canonical
guidance on a line this WP touched, in a file whose stated purpose is to stop
teaching stale things. Worth aligning to `approved`, or noting deliberately.

---

## What I verified by direct execution (not from your report)

| Criterion | Method | Result |
|---|---|---|
| SC-004 | the exact grep, both files | **no match** (exit 1), incl. prose and comments |
| `agent action implement\|review` exists | `spec-kitty agent action --help` | both subcommands present |
| `agent context resolve` exists with those flags | `spec-kitty agent context resolve --help` | `--action`, `--mission`, `--json` all present |
| `spec-kitty constitution` really retired | `spec-kitty constitution --help` | "No such command 'constitution'" |
| `spec-kitty agent workflow` really retired | `spec-kitty agent workflow --help` | "No such command 'workflow'" |
| builder call shape | signature at `src/charter/doctrine_service_builder.py:188` + SKILL.md:660-690 | matches: one positional `repo_root: Path` |
| the taught snippet actually runs | executed it | `service.agent_profiles.get('reviewer-renata')` → `AgentProfile`; `.initialization_declaration`, `.specialization.avoidance_boundary`, `.collaboration.handoff_to` all resolve |
| scope discipline | diffstat | only the 2 owned files; no `src/`, no tests, no sibling overrides |
| Terminology Canon | `pytest tests/architectural/test_no_legacy_terminology.py -q` | 10 passed |
| governance contract | `pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -q` | 26 passed |

## Refresh-vs-delete: your call was right, for a stronger reason than you gave

I went looking for the canonical template these files override and **there is none**.
`find . -type d -name command-templates` returns only project overrides
(`software-dev`, `documentation`, `research`, `plan`); nothing under `src/doctrine/`.
So the Tier-5 PACKAGE default has no `command-templates/implement.md` to fall back
to, and `grep -rn "Deterministic Pre-Read" src/doctrine/` returns nothing — that
section has no canonical equivalent either. Deleting would have destroyed content
with no replacement. Refresh holds.

## Deliberately NOT required of you

- **`service.directives.get(f"DIRECTIVE_{ref.code}")` returns `None` in this project.**
  I found `service.directives` is empty (0 keys) from both the lane and the repo root,
  while `agent_profiles` has 15. That line is unchanged context in your diff and is
  exactly what `SKILL.md:462` itself documents. Pre-existing and SKILL.md-sanctioned —
  not yours.
- **These override files may not be resolved at all.** `doctrine/resolver.py:164`
  builds Tier 1 as `.kittify/overrides/<subdir>/<name>` — with **no**
  `missions/<mission>/` segment — so `resolve_command("implement.md", ...)` would not
  hit `.kittify/overrides/missions/software-dev/command-templates/implement.md`.
  The WP prompt's "tracked TIER-1 template-resolver override" premise looks wrong.
  This affects the whole 12-file directory, is a planning/upstream gap rather than a
  WP07 defect, and the files are tracked and agent-readable regardless — so the
  refresh has value either way. Worth filing upstream; not yours to fix here.
- The pre-existing bad docstring path in `test_wp_prompt_governance_contract.py`.
- Sibling `constitution.md` in the same directory (an override for a fully retired
  command) — outside your `owned_files`.

## Anti-pattern checklist

1. Dead code — **N/A** (prose-only diff, no new symbols)
2. Synthetic-fixture test — **N/A** (no tests in scope; FR-007 is verified by grep)
3. Silent empty return — **N/A**
4. FR coverage — **PASS** (SC-004 grep is the specified gate and it passes)
5. Frozen surface — **PASS** (only the 2 declared `owned_files`)
6. Locked decision — **PASS** (no MUST NOT clause contradicted; the banned raw
   construction is removed, which is the point)
7. Shared-file ownership — **PASS** (WP07 owns lane-e alone; neither file appears in
   another WP's `owned_files`)
8. Production fragility — **N/A**
