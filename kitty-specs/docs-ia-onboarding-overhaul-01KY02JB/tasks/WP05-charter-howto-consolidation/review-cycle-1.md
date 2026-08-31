---
affected_files: []
cycle_number: 1
mission_slug: docs-ia-onboarding-overhaul-01KY02JB
reproduction_command:
reviewed_at: '2026-07-20T18:28:49Z'
reviewer_agent: claude:sonnet-5:curator-carla:reviewer
verdict: rejected
wp_id: WP05
---

**Issue 1**: `docs/guides/troubleshoot-charter.md` §1 "Stale bundle" still teaches the retired
charter.md-is-authoritative model that this WP correctly retired everywhere else.

Verified against source:
- `src/specify_cli/charter_runtime/freshness/computer.py` (module docstring): "Post-inversion
  `charter.yaml` (not `charter.md`) is the authoritative, resolving source... The historical
  `charter.md`-SHA-vs-`metadata.yaml::charter_hash` staleness mechanism is **retired outright, not
  re-homed**... `charter_source` therefore never returns `stale`."
- `src/charter/sync.py :: sync()` docstring: "the prose->triad scrape this module used to perform
  ... is RETIRED... `synced` is now always `False` and `files_written` always empty."

Current `troubleshoot-charter.md` §1 (lines 21-48) still says:
- Symptom: "`uv run spec-kitty charter status` reports drift between `charter.md` and the bundle"
  — per `computer.py`, this specific symptom can no longer occur; `charter_source` never returns
  `stale`.
- "What is happening": "`charter.md` was edited after the last synthesis run, so the derived
  bundle files no longer match the authoritative source" — wrong model; `charter.yaml` is
  authoritative, not `charter.md`.
- Fix step 1: `uv run spec-kitty charter sync  # Re-sync charter.md to YAML config files` — this
  command is now a confirmed no-op (`sync()` always returns `synced=False`, ignoring `--force`).
  A user following this fix will see "Charter already in sync" and get no closer to resolving
  anything.

This directly contradicts this same WP's own corrected `docs/context/charter-overview.md`, which
now states explicitly (lines 79-81): "`charter sync` still exists for canonical-root resolution
and back-compat call sites, but it no longer extracts anything from `charter.md` — running it is
always a no-op." The WP's commit message claims "corrected a stale model repeated across three of
the four pages," but the fourth page (`troubleshoot-charter.md`) carries the exact same stale
model and was left untouched (confirmed via `git diff` — only frontmatter/cross-links were added).

**Fix**: Rewrite `troubleshoot-charter.md` §1 "Stale bundle" (or replace it with whatever failure
mode is now real, e.g. `synthesized_drg.state == "stale"` per `computer.py`'s content-hash
comparison against the synthesis manifest) so it matches the current architecture: `charter.yaml`
is authoritative, `charter sync` is a no-op, and the real fix path is `charter lint` →
`charter synthesize` → `charter bundle validate` → `charter status` (i.e., drop the dead `charter
sync` step and correct the symptom/explanation to describe `charter.yaml` vs. the synthesized DRG,
not `charter.md` vs. "the bundle"). Re-verify against `computer.py`'s documented state-transition
rules before resubmitting, and re-run the `git diff` content-preservation check once the section is
corrected (the correction should replace stale content, not delete useful content).

All other checks passed: setup-governance.md is a genuinely complete single flow with `type:
how-to` frontmatter; charter-overview.md and charter-governed-workflow.md now link into the
how-to without content loss; frontmatter description lengths are within 50-180 chars; no files
outside the four owned files were touched; `relative_link_fixer.py --check` reports 0 dead links.
