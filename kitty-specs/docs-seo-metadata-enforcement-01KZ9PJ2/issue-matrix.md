# Issue matrix — docs-seo-metadata-enforcement-01KZ9PJ2

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #1652 | SEO audit needed for GitHub Pages docs site | fixed | All eight WPs approved. Gate: `description_length_check: checked 672 page(s); 0 violation(s)` (was 547 with the 147 ADRs excluded, and the enforcement test covered only 16). 148 hand-authored ADR descriptions across WP02–WP04; render emits a description tag (WP05); built-output verifier blocks the Pages deploy (WP05); one-click nav (WP07); CI scoped (WP08). Two of the issue's own criteria were **already satisfied before this Mission** — see the breakdown below. Full per-criterion evidence in `acceptance-matrix.json` (21 pass / 1 pending). |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).

## Criterion breakdown for #1652

Recorded because **two of the issue's acceptance criteria were already satisfied in
production before this Mission began**. Without this note a later contributor would
"re-fix" correct pages. Verified live against `docs.spec-kitty.ai` on 2026-08-05.

**Already satisfied before this Mission began** — do not "re-fix" these:

- *`docs/reference/slash-commands` needs a CLI-reference title/description* — live `<title>` at `/api/slash-commands.html` is verbatim the issue's suggested wording. The page *moved*; the URL the issue cites is now a redirect stub (`scripts/docs/redirect_map.yaml`).
- *`install-spec-kitty.html` needs an install-intent title naming OS targets* — reads `Install Spec Kitty — macOS, Linux, and Windows Installation Guide`. Page moved `how-to/` → `guides/`.
- *Canonical URLs point at the preferred docs URL* — emitted for every indexed page by `scripts/docs/seo_postprocess.py`; re-asserted at build time by WP05 (V-08).
- *Social sharing metadata present* — OG + Twitter + JSON-LD already emitted; re-asserted by WP05 (V-09).

**Being closed by this Mission** (`in-mission`):

- *Unique, descriptive `<title>` on important pages* — WP05 (NFR-001). Measured baseline: 0 of 674 published pages lacked a title.
- *Useful meta descriptions for developer search intent* — WP02 (51 pages) + WP03 (48) + WP04 (49); 147 ADR pages shipped with **no** description tag at all. WP06 enforces at PR time.
- *Important pages reachable via clear internal links/navigation* — WP07; install guide and slash-command reference now one click from `docs/index.md`.
- *Output verifiable via curl / view-source* — WP05 `scripts/docs/seo_verify.py` plus the audit record (FR-010, FR-011).

### Defects this Mission's audit found that the issue did not name

- The enforcement gate covered **16 of 674** pages (2.4%): `tests/docs/test_docs_seo.py` globbed the pre-move directory layout, so an earlier reorganisation silently emptied it while it kept reporting green. Owners: WP01 (resolver single-sourced from `docs/docfx.json`), WP06 (coverage assertion).
- **147 ADR pages** shipped with zero `<meta name="description">` and one boilerplate `og:description` shared across all of them. Owners: WP02, WP03, WP04.
- `seo_postprocess.py` read a description but never emitted a `<meta name="description">` tag. Owner: WP05 (T022).

**Terminal verdict recorded at accept time (2026-08-05).** All eight WPs approved; the row
moved `in-mission` → `fixed`.

### Known gap carried past this Mission

`NFR-008` (documentation build wall-clock increase ≤ 10%) is **not measured** and is recorded
as `pending` in `acceptance-matrix.json`. It was flagged as analysis finding **C1 before
implementation began**: the requirement was mapped to WP05 but no subtask times the build, and
DocFX/.NET is unavailable in this environment. The verifier adds one read-only pass over
`_site`, so the risk is low — but low risk is not a measurement, and it is not claimed as one.
This does not affect any acceptance criterion of #1652 itself.
