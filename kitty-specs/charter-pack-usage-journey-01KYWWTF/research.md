# Phase 0 Research — Charter Pack Usage Journey

**Primary research artifact**: [notes/research-synthesis.md](./notes/research-synthesis.md) — the 2-lens
research squad (architect-alphonso reproduced all 8 journeys end-to-end; paula-patterns related-issues +
campsite) plus the 2026-08-01 revision-squad refresh against landed M1. That synthesis is the authoritative
design input; it already resolves the bridge decision (OPTION a — wire the existing compile seam), the
org-pack-safe dispatch predicate, the read-surface retarget list, the catalog-fallback retirement, and the
fourth-producer convergence. This file records only the **new decisions the plan phase had to close** that
the synthesis left as plan-phase investigations (the #3095/#3096/#3102 operator fold).

## Decision 1 — FR-010: produce the sections vs stop advertising (#3095/#3094)

**Question**: `charter context --include section:terminology-canon` / `section:code-review-checklist` (which
the generated `implement`/`review` prompts *require* — `src/doctrine/missions/mission-steps/software-dev/
{implement,review}/prompt.md`) dead-end with "No charter section found for selector". Should the mission make
the sections *resolve* (produce them) or make the surface *stop advertising* them?

**Investigation (this plan phase)**:
- The selector engine is `src/charter/context_renderers/section_bodies.py::render_critical_section_include`
  (`:282`). It calls `_extract_section_body(charter_content, heading)` (`:184`) where `heading` ∈
  `{"Terminology Canon", "Code Review Checklist"}` (`ACTION_CRITICAL_SECTIONS` for `implement`/`review`,
  `:34-46`). `charter_content` is the **`charter.md` prose** — so this correctly stays on the prose/section
  path (C-003), NOT the `charter.yaml` presence gate.
- **Root cause of the dead-end**: after `charter generate` (the compile), `charter.md` is seeded from
  `generate.py:189 _CHARTER_MD_COMPANION_SEED` — a **minimal starter** that does NOT contain those headings.
  So a freshly-applied+compiled pack has a `charter.md` with no "Terminology Canon"/"Code Review Checklist"
  section → `_extract_section_body` returns `None` → dead-end. (This repo's *own* dogfooded
  `.kittify/charter/charter.md` was hand-authored WITH those headings, which is why the selector works here
  and the bug is invisible in-repo — a false-green.)
- The two headings are **baseline governance every project needs for implement/review**, not pack-specific
  content — they appear canonically in `src/doctrine/templates/AGENTS.md` and both mission-step prompts.

**Decision**: **Make the selector graceful-degrade instead of hard-erroring, AND enrich the companion seed
with the action-critical section scaffolds** — a two-part fix with a clear precedence:
1. **Primary (no-dead-end guarantee)**: `render_critical_section_include` must render a soft, honest
   placeholder ("This charter has not yet authored a *Terminology Canon* section — add one to
   `.kittify/charter/charter.md`") when the section is absent, rather than the current
   "No charter section found for selector" error. This makes the *advertised selector always resolve to
   something usable* (US4.1 "resolves … or the surface no longer advertises") without fabricating
   authoritative governance content, and it is robust for every project regardless of how `charter.md` was
   produced.
2. **Secondary (better default)**: extend `_CHARTER_MD_COMPANION_SEED` so the generated companion includes
   stub "Terminology Canon" and "Code Review Checklist" headings (with a one-line "author this" prompt), so
   a freshly-compiled pack's selector resolves to a real (if starter) section, not just a placeholder.

   > **DEFERRED post-plan (authoritative — WP05/T040 and plan IC-06 override this):** part 2 (seed
   > enrichment) is **out of scope** for M2 — it tensions with #2808 (do not fabricate governance content)
   > and is deferred unless the operator reconciles it. WP05 implements **only** the primary graceful-degrade
   > placeholder in `section_bodies.py`; do **not** edit `generate.py`'s `_CHARTER_MD_COMPANION_SEED`. This
   > note supersedes the "AND enrich the companion seed" clause in the Decision above.

**Rejected**: "stop advertising" (delete the `--include section:` calls from the prompts) — the sections are
genuinely action-critical for implement/review; removing them loses a real governance touchpoint. Rejected
"produce authoritative per-project content in the compile" — the terminology canon is inherently
project-specific; the mission cannot synthesize it, and doing so would overreach into content authorship.

**Boundary reaffirmed (C-003)**: this fix lives entirely on the `charter.md` prose/section path
(`section_bodies.py` + the companion seed) — it does NOT touch the FR-005 presence-gate retarget and does NOT
collapse the prose reader onto `charter.yaml`. Two paths stay two paths.

## Decision 2 — FR-011: alias vs redirect for `spec-kitty analyze` (#3096)

**Question**: the documented `spec-kitty analyze` command does not exist (only `agent mission
record-analysis`). Expose a thin `analyze` alias, or redirect the documented surface to the supported command?

**Decision**: **Redirect the documented surface to the supported command** (the `spec-kitty.analyze` skill +
command-skills manifest + docs point *exclusively* at the canonical `agent mission record-analysis` flow),
rather than minting a new top-level `analyze` alias. Rationale: the canonical analysis entry point is already
`agent mission record-analysis` (it carries the staleness-gate + artifact contracts); adding a second
top-level verb that merely forwards creates a parity surface to keep in sync and invites drift. The gap is a
**documentation/skill-mapping** gap, not a missing capability — fix it where it is wrong. Implementation
confirms the exact skill + manifest + doc touch-points during IC-07 (all agent surfaces updated consistently).

**Fallback**: if IC-07 finds callers that hard-code `spec-kitty analyze` such that a redirect would break
them, expose the thin alias instead — but it MUST route through the canonical `record-analysis` flow (no
reimplementation; missing-CLI-command-is-a-gap → trace source).

## Decision 3 — FR-012: path-filter shape for the doctrine/charter CI workflow (#3102)

**Question**: what does the path-filtered workflow gate, and how does it behave for PRs that touch neither
path?

**Decision**: a dedicated GitHub Actions workflow keyed on `paths: [src/doctrine/**, src/charter/**]` that
runs the doctrine/charter test surface (DRG freshness/sharding, charter-context resolution, the
architectural/adversarial gates relevant to that layer) as an isolated job. For PRs that change neither path,
the workflow must **skip-with-green** (a required check that is satisfied when skipped), never skip-with-fail
— consistent with the repo's existing path-filter un-skip semantics. It must not double-charge gates the main
CI already runs; scope it to the fast doctrine/charter signal. Exact job list + required-check wiring
finalized in IC-08 against the current `.github/workflows/` layout.

## Standing constraints carried into design (from the synthesis, unchanged)

- Bridge = OPTION (a): wire the existing `compile_charter`/`write_compiled_charter` seam; build no compiler.
- Dispatch predicate splits governance-emptiness from routability (org-pack safe); "empty" = **bundle
  absent**, never "bundle present but activations empty" (pins against the #3064 exhaustiveness trap).
- Presence-gate retarget (FR-005) and section-selector fix (FR-010) stay **two distinct paths** (C-003).
- Do not revert M1's landed `resolver.py:187/:250` operator strings (C-002); trust M1's unified activation
  vocabulary (C-001). Classify reds vs merge-base, never green-wash (C-005).
