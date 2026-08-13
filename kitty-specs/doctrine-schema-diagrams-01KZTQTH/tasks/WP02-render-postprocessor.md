---
work_package_id: WP02
title: PlantUML render post-processor + workflow wiring
dependencies:
- WP01
requirement_refs:
- C-002
- FR-001
- NFR-004
- NFR-005
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
phase: Phase 2 - Capability
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/plantuml_render.py
create_intent:
- scripts/docs/plantuml_render.py
- tests/docs/test_plantuml_render.py
execution_mode: code_change
model: ''
owned_files:
- scripts/docs/plantuml_render.py
- .github/workflows/docs-build-pr.yml
- .github/workflows/docs-pages.yml
- tests/docs/test_plantuml_render.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#3366'
---

# Work Package Prompt: WP02 – PlantUML render post-processor + workflow wiring

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load` to load the profile and behave per its guidance first.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks. Use language identifiers in code blocks.

## Objectives & Success Criteria

Land the docsite render capability: a **host-native, stdlib-only** post-processor that recovers
` ```plantuml `-fenced `@start*` blocks from `docs/_site`, renders them to SVG via WP01's
`plantuml_invoke.py`, and injects the SVG with **derived, non-trivial** alt/aria text — wired into
**both** docs workflows immediately after `glossary_linker`.

**Definition of Done:**

1. `scripts/docs/plantuml_render.py` recovers fences, `html.unescape()`s the payload, renders, injects
   SVG + alt. The recovery **matches BOTH `lang-plantuml` AND `language-plantuml`** — DocFX/markdig
   emits `lang-plantuml` for hand-authored fences (the mission diagrams), while the custom
   `language-*` emitter only covers kitty-specs pages; assuming only `language-plantuml` silently
   renders nothing. The step **FAILS CLOSED on any recognized-but-unrendered `@start*` fence** (an
   "all fences consumed" positive check), so a class mismatch reds the build instead of shipping
   empty diagrams.
2. Wired into `docs-build-pr.yml` AND `docs-pages.yml`, **immediately after `glossary_linker`,
   before redirect-stub generation + `seo_verify --strict`** (verified real slots: docs-build-pr.yml
   ~L134→L143, docs-pages.yml ~L77→L113). Do **NOT ADD** host `setup-java` — neither workflow has it
   and java runs only in the pinned image; the risk is adding it, not removing it.
3. `docs-pages.yml`'s **enumerated** `paths:` allowlist extended to include the new script(s) (literal
   list, not a glob). `docs-build-pr.yml` already globs `scripts/docs/**` + `docs/**`, so it needs **no**
   `paths:` change — a reviewer should not flag a missing edit there.
4. Round-trip test proves fence→`_site`→recovered→SVG survives the full downstream chain; Mermaid is
   untouched; malformed fence + sha256 mismatch fail-closed.
5. Alt-text test asserts each SVG's `aria-label` equals the **exact literal `title` string authored
   in the fixture** (e.g. `"Agent Profile Schema"`) — not merely "two distinct captions not in the
   fallback set" (which a fake `f"diagram-{i}"` derivation would pass). Distinctness + fallback-set
   exclusion remain as secondary assertions.

## Context & Constraints

- **Source of truth**: [contracts/plantuml-render.md](../contracts/plantuml-render.md),
  [contracts/no-egress-proof.md](../contracts/no-egress-proof.md) (execution locus),
  [plan.md](../plan.md) IC-01. **Depends on WP01** (`plantuml_invoke.py`, pins).
- **Stdlib-only** (docs-pages.yml has no `pip install`) — import only `html`, `re`, `pathlib`,
  `json`, `subprocess`, etc. Reuse `scripts/docs/plantuml_invoke.py` from WP01.
- **Mirror the `glossary_linker.py` pattern** (same `_site` post-processing shape). Read it first.
- **NFR-004 non-regression**: `tests/docs/` + terminology guard must stay green; Mermaid untouched.
- **NFR-005 accessibility**: alt/aria derived from the diagram's `@startyaml` `title` (fallback to the
  surrounding markdown heading) — asserted non-trivial. The prose "restate the facts" duty is
  discharged by surrounding doctrine-kinds prose, NOT by re-listing fields (recorded in WP04 ADR).

## Subtasks & Detailed Guidance

### Subtask T007 – `scripts/docs/plantuml_render.py`

- **Purpose**: the actual post-DocFX render/inject step.
- **Steps**:
  1. Walk `docs/_site/**/*.html`. Recover rendered `@start*` fences matching **BOTH** class
     conventions — `lang-plantuml` (DocFX/markdig default, the mission diagrams) **and**
     `language-plantuml` (the custom kitty-specs emitter). Confirm both against a real built `_site`
     page. After processing a page, assert **zero** `@start*` fences remain unrendered (fail-closed —
     a class mismatch must red the build, never ship empty diagrams).
  2. Recover the fence payload and `html.unescape()` it (DocFX HTML-escapes `<`, `&`, quotes).
  3. Render via `plantuml_invoke.render_startyaml(...)` (SANDBOX, `--network=none`, `-failfast2`); the
     invoker's `svg_is_error` check (WP01) fails-closed on a PlantUML error SVG.
  4. Derive the caption: prefer the PlantUML `title …` line inside the block; else the nearest
     preceding markdown heading. Build alt/aria from it; **reject trivial captions** (empty or in
     `{"yaml","diagram"}`) by raising (fail-closed) — a diagram must carry a real title.
  5. Replace the `<pre><code …>` fence node with the `<svg>` (or `<figure><svg><figcaption>`), setting
     `role="img"` + `aria-label` + a `<title>` inside the SVG.
- **Files**: `scripts/docs/plantuml_render.py` (~180 lines).
- **Validation**: `ruff` + `mypy --strict` clean, **no *unjustified* suppressions**. Mirroring the
  canonical `glossary_linker.py` `sys.path` bootstrap requires exactly one inline-justified
  `# noqa: E402` on the post-bootstrap sibling import (charter-sanctioned narrow suppression) — that
  is acceptable; do not add any others.

### Subtask T008 – Wire into `docs-build-pr.yml`

- **Purpose**: PR-gate rendering.
- **Steps**:
  1. Read the current workflow; locate the `glossary_linker` step.
  2. Insert the render step **immediately after `glossary_linker`, before redirect-stub + `seo_verify
     --strict`**. Prefetch the JRE image (by digest) + download/verify the jar before it.
  3. Do **NOT add** host `setup-java` (it is absent today; java runs in the pinned image).
  4. **No `paths:` change** here — `docs-build-pr.yml` already globs `scripts/docs/**` + `docs/**`.
- **Files**: `.github/workflows/docs-build-pr.yml`.

### Subtask T009 – Wire into `docs-pages.yml` + extend `paths:` allowlist

- **Purpose**: deploy-path rendering + trigger correctness.
- **Steps**:
  1. Same insertion (after `glossary_linker`, before redirect-stub/`seo_verify`), same jar/image prep;
     do not add `setup-java`.
  2. **Extend the enumerated `paths:` allowlist** to include `scripts/docs/plantuml_render.py`,
     `scripts/docs/plantuml_invoke.py`, `scripts/docs/plantuml_pins.json` (literal entries — it is not
     a glob). Otherwise doc-only edits that touch the render script won't trigger the deploy.
  3. After wiring, `workflow_dispatch` the **real** `docs-pages.yml` path (or a dry-run job) to confirm
     `docker` is usable in the deploy-job context (permissions `contents: read`, Pages-deploy) — not
     only inside WP01's standalone spike job. "Proven, not asserted."
- **Files**: `.github/workflows/docs-pages.yml`.

### Subtask T010 – Round-trip + non-regression test

- **Purpose**: prove the fence survives the whole chain and nothing else breaks.
- **Steps**:
  1. Derive the fence class from a **real DocFX build** artifact in ≥1 test (not only a stub) so the
     `lang-`/`language-` recovery is validated against reality, not a self-fulfilling stub. A stubbed
     `_site` page may supplement but must not be the sole proof of the class.
  2. Run the render step, then the downstream steps after it (redirect-stub, `seo_verify`) over the
     injected page — assert the SVG is present and the page still passes `seo_verify`.
  3. Assert the Mermaid block is byte-unchanged.
  4. Assert **all `@start*` fences are consumed** (zero unrendered fences remain) — a `lang-`/`language-`
     class mismatch must FAIL here, not ship empty diagrams.
  5. Assert a **malformed** `@startyaml` fails-closed (non-zero / raised); a **jar sha256 mismatch**
     fails-closed **before** rendering; a PlantUML **error SVG** fails-closed (`svg_is_error`).
- **Files**: `tests/docs/test_plantuml_render.py`.
- **ATDD**: write these RED first (before T007 is complete), commit as the WP's first commit.

### Subtask T011 – Alt-text distinct-caption test

- **Purpose**: NFR-005 concrete predicate (reviewer MEDIUM).
- **Steps**: render **two differently-titled** diagrams; assert each injected SVG's `aria-label`
  equals the **exact literal `title` string authored in the fixture** (e.g. `"Agent Profile Schema"`)
  — a fake `f"diagram-{i}"` derivation would pass a mere distinct/non-fallback check, so the literal
  equality is the forcing assertion. Keep distinctness + `{"yaml","diagram",""}` exclusion as
  secondary. Confirm the derivation source (PlantUML `title` vs markdown heading) matches T007.
- **Files**: `tests/docs/test_plantuml_render.py` (same module).

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- `PWHEADLESS=1 python3 -m pytest tests/docs/test_plantuml_render.py -q`.
- Docker-gated assertions run in CI; locally, skip the real-docker render if unavailable but keep the
  fence-recovery/`html.unescape`/alt-derivation unit tests running everywhere (feed a canned SVG).
- Full `tests/docs/` + `pytest tests/architectural/test_no_legacy_terminology.py` stay green.

## Risks & Mitigations

- **DocFX fence class differs from assumption** → recovery misses. Mitigation: confirm against real
  `_site`; the round-trip test is the backstop.
- **`glossary_linker` reorders/escapes SVG** → corruption. Mitigation: render AFTER it; use the
  `<pre><code>` recovery form; round-trip test guards.
- **`seo_verify --strict` rejects injected markup** → build red. Mitigation: run it in T010 over the
  injected page and satisfy it (alt text, valid SVG).

## Review Guidance

- Confirm insertion order in BOTH workflows (after `glossary_linker`, before redirect-stub/`seo_verify`).
- Confirm `setup-java` removed and `paths:` allowlist extended in `docs-pages.yml`.
- Confirm stdlib-only (no third-party imports) and `ruff`/`mypy --strict` clean.
- Confirm the alt-text predicate is non-trivial (distinct, derived, not generic).
- Reviewer ≠ implementer. Verify RED-first commit exists for the tests.

## Activity Log

> Append newest entries at the END, chronological.
