---
affected_files: []
cycle_number: 2
mission_slug: docs-ia-onboarding-overhaul-01KY02JB
reproduction_command:
reviewed_at: '2026-07-20T18:35:45Z'
reviewer_agent: claude:sonnet-5:curator-carla:reviewer
verdict: rejected
wp_id: WP05
---

## Review cycle 2 — REJECTED

`docs/guides/troubleshoot-charter.md` §1 ("Stale bundle") is now correct and well-verified
against `src/charter/sync.py` and `src/specify_cli/cli/commands/charter/synthesize.py`. Thank you
for the "Model change" callout — it's clear and accurate.

However, the same staleness bug (charter.md treated as the authoritative/gating artifact) is
still present in two other spots in this file, plus the dead `charter sync` step recurs once
more. All three were called out as deliberately-left-untouched in your own report; on inspection
they are genuinely in scope for this fix, not adjacent/unrelated content.

**Issue 1 — §2 "Missing doctrine" (~line 88-92), still describes the retired model:**

```
If `charter synthesize` fails because `charter.md` does not exist:

# Run the interview and generate a charter.md first
uv run spec-kitty charter interview --profile minimal --defaults
uv run spec-kitty charter generate --from-interview
```

I traced every failure branch in `charter synthesize`
(`src/specify_cli/cli/commands/charter/synthesize.py` and `_synthesis.py`). None of them check
for `charter.md`'s existence — grepping those files for `charter.md` / `charter_md` returns zero
hits. The actual failure modes are: (a) missing interview answers (`answers.yaml`), (b)
`GeneratedArtifactMissingError` (no agent-authored YAML under `.kittify/charter/generated/`), (c)
`BUNDLE_INCOMPLETE_MESSAGE` when the bundle file derived from `charter.yaml` is missing. The
fresh-project short-circuit gates explicitly on `charter_yaml.is_file()` (`charter.yaml`), per the
code comment: "Gating signal re-pointed from charter.md to charter.yaml... charter.md is a
display-only companion (INV-3 — never a resolving signal)."

Fix: reframe the symptom/heading around `charter.yaml` (or the bundle/interview-answers state),
not `charter.md`. The example commands themselves (interview → generate) are fine to keep since
they do produce `charter.yaml`, but "does not exist... generate a charter.md first" is the wrong
diagnostic frame — a user chasing `charter.md`'s presence will miss the actual gate.

**Issue 2 — §3 "Compact-context limitation" (~line 117), workaround edits the wrong file:**

```
**Workarounds**:
- Reduce the scope of `charter.md` by removing directives that are not relevant to the current
  project phase or that overlap significantly with other directives.
```

This directly contradicts the model your own §1 fix just established: `charter.md` is "a
non-authoritative prose companion the runtime never parses" (INV-3, never a resolving signal).
Editing `charter.md` cannot shrink the DRG/compact-context payload — directives live in
`charter.yaml`'s `directives:` section (per your own corrected §1 text). This workaround has zero
effect as written and will send a user editing the wrong file.

Fix: change "Reduce the scope of `charter.md`" to reference `charter.yaml` (its `directives:`
section) as the file to trim.

**Issue 3 — §5 "Synthesizer rejection" (~line 190-191), dead `charter sync` step recurs:**

```
# 4. If you changed charter-derived state manually, re-run synthesis/validation as needed
uv run spec-kitty charter sync
uv run spec-kitty charter synthesize
uv run spec-kitty charter bundle validate
```

This is the identical dead command your own §1 fix just removed and explained: `charter.md`'s
`sync()` "no longer extracts or writes anything; it always reports `synced=False`" (per
`src/charter/sync.py` module docstring). It's still listed here as a "fix" step, teaching the same
no-op.

Fix: drop the `charter sync` line from this step (keep `synthesize` + `bundle validate`).

**Not in scope for this rejection** (confirmed clean):
- §1 itself — accurate.
- Sections 2, 4 (retrospective gate) otherwise, and the Diagnostic Quick Reference table — byte-
  identical to before cycle 1 (`git show 775c63f51` touches only §1).
- The other three owned files (`docs/context/charter-overview.md`,
  `docs/guides/charter-governed-workflow.md`, `docs/guides/setup-governance.md`) — confirmed
  untouched in cycle 2 via `git diff 8d4508829..775c63f51 --stat`.

Please apply the same "charter.yaml is authoritative, charter.md is a non-authoritative
companion" model consistently across all five failure-mode sections of this file, not just §1.
