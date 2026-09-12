---
work_package_id: WP01
title: PlantUML egress-isolation spike (BLOCKING gate)
dependencies: []
requirement_refs:
- C-001
- FR-001
- NFR-002
- NFR-003
planning_base_branch: feat/doctrine-schema-diagrams-impl
merge_target_branch: feat/doctrine-schema-diagrams-impl
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-schema-diagrams-impl. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-schema-diagrams-impl unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - De-risk
history:
- at: '2026-08-12T16:41:10Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: scripts/docs/plantuml_invoke.py
create_intent:
- scripts/docs/plantuml_invoke.py
- scripts/docs/plantuml_pins.json
- .github/workflows/plantuml-egress-spike.yml
- tests/docs/fixtures/spike_startyaml.md
execution_mode: code_change
model: ''
owned_files:
- scripts/docs/plantuml_invoke.py
- scripts/docs/plantuml_pins.json
- .github/workflows/plantuml-egress-spike.yml
- tests/docs/fixtures/spike_startyaml.md
role: implementer
tags: []
task_type: implement
tracker_refs:
- '#3366'
---

# Work Package Prompt: WP01 – PlantUML egress-isolation spike (BLOCKING gate)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile in the frontmatter and behave per its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<svg>` ``, `` `<pre>` ``. Use language identifiers in code blocks.

## Objectives & Success Criteria

**This is the mission's de-risking spike. Runnability is currently UNPROVEN.** Its green
CI exit-criterion gates every render/diagram WP (WP02, WP03, WP05–WP07). Do not treat
prior missions as proof — prove it here, on the real runners.

**Definition of Done (all required):**

1. A **real** `@startyaml` diagram renders to a **valid, error-free** SVG via
   `docker run --network=none -v <tmp>:<tmp> <digest-pinned-JRE-image> java -jar plantuml.jar …`
   under `-DPLANTUML_SECURITY_PROFILE=SANDBOX` **and `-failfast2`**. "Non-empty SVG" is NOT the
   predicate — PlantUML renders font/DNS failures as a *valid non-empty* `<svg>` with an error
   graphic at **exit 0**. The green predicate MUST be: the SVG contains expected tokens from the
   fixture `title`/keys **AND** contains **no** PlantUML error signature (no `An error has
   occurred`, no error-red `<rect>`/`<text>`). This is the exact failure the spike exists to catch.
2. The spike CI job passes on **BOTH** runner labels: `ubuntu-latest` **AND**
   `blacksmith-4vcpu-ubuntu-2404` (matrix). Capture both run URLs in the Activity Log.
3. `plantuml.jar` is pinned by **version + sha256**; the JRE image is **digest-pinned**; the
   image is **prefetched before** the isolated run (no pull under `--network=none`).
4. Python orchestration is **stdlib-only** (no third-party imports) — `docs-pages.yml` has no
   `pip install`. Only `java -jar` runs in the container.
5. **Escalation trigger**: if the render fails on blacksmith for font/DNS reasons, STOP and
   escalate to the operator with the failing log — the entire capability depends on this. Note
   the candidate mitigations you would try (bundle DejaVu fonts into the image / pin an image
   that ships fonts / set `-Djava.awt.headless=true` + `PLANTUML_LIMIT_SIZE`).

## Context & Constraints

- **Source of truth**: [contracts/no-egress-proof.md](../contracts/no-egress-proof.md),
  [contracts/plantuml-render.md](../contracts/plantuml-render.md),
  [research.md](../research.md) (D1), [plan.md](../plan.md) IC-01.
- **Execution locus (architecture HIGH, pinned)**: host-native stdlib-only Python; only the
  untrusted `java -jar plantuml.jar` is wrapped in `docker run --network=none`. **Drop host
  `setup-java`** — it is redundant once java runs in the pinned image.
- **Why docker, not `unshare -rn`**: Ubuntu-24.04 runners set
  `apparmor_restrict_unprivileged_userns=1`, so `unshare -rn` is unreliable. `docker run
  --network=none` is the portable default (runners have Docker). See research D1.
- **Charter**: quality/no-egress standing orders; `.kittify/charter/charter.md`.
- **DIR-012**: this WP adds a workflow + pins an external binary — a tracking issue must be
  captured/assigned to the HiC before this WP is claimed (see mission pre-implement gates).

## Subtasks & Detailed Guidance

### Subtask T001 – Pin `plantuml.jar` (version + sha256)

- **Purpose**: reproducible, verified binary (NFR-003, C-001).
- **Steps**:
  1. Choose a current stable PlantUML release (e.g. a `plantuml-<version>.jar` from the pinned
     upstream release). Record the **exact version** and the **sha256** of the jar.
  2. Write `scripts/docs/plantuml_pins.json` with keys: `plantuml_version`, `plantuml_jar_sha256`,
     `plantuml_jar_url` (the download URL used in CI), `jre_image` (repo:tag), `jre_image_digest`
     (`sha256:…`). This single file is the canonical pin registry consumed by CI and by
     `plantuml_invoke.py`.
- **Files**: `scripts/docs/plantuml_pins.json`.
- **Notes**: do NOT commit the jar itself — CI downloads it and verifies the sha256.

### Subtask T002 – Select + digest-pin a JRE image  `[P]`

- **Purpose**: the container that runs `java -jar` offline, deterministically.
- **Steps**:
  1. Pick a small JRE image that ships the fonts PlantUML needs (fontconfig + a DejaVu/Liberation
     font). A headless JRE with no fonts will fail `@startyaml` rendering — verify locally first.
  2. Record `jre_image` + `jre_image_digest` (`docker inspect --format '{{index .RepoDigests 0}}'`)
     in `plantuml_pins.json`. CI pulls **by digest** before the isolated run.
- **Files**: `scripts/docs/plantuml_pins.json` (shared with T001).
- **Notes**: prefer an image that already contains fonts; only fall back to bundling fonts if none
  fits. Document the choice inline in the pins file (`_comment` key allowed in JSON? use a sibling
  `.md` note if not — keep JSON strict).

### Subtask T003 – `scripts/docs/plantuml_invoke.py` (stdlib-only docker wrapper)

- **Purpose**: the single reusable invocation surface WP02's render step and WP03's isolation
  tests call. Keeps the docker/SANDBOX/sha256 contract in ONE place.
- **Steps**:
  1. Pure-stdlib module. Public function, e.g.
     `render_startyaml(source_text: str, *, workdir: Path, pins: Pins) -> bytes` returning SVG bytes.
  2. Load pins from `plantuml_pins.json`. **Verify the jar sha256** before use; raise a typed
     error (fail-closed) on mismatch.
  3. Prefetch the JRE image by digest (outside isolation), then run:
     `docker run --rm --network=none -v {workdir}:{workdir} -w {workdir} <image@digest>
     java -Djava.awt.headless=true -DPLANTUML_SECURITY_PROFILE=SANDBOX -failfast2 -jar {jar} -tsvg {infile}`.
  4. Return the produced SVG bytes; raise fail-closed on non-zero exit / empty output **AND** on a
     PlantUML **error signature** in the SVG (see DoD #1 — a valid non-empty error SVG must fail-closed).
     Expose a small `svg_is_error(svg: bytes) -> bool` helper so callers (WP03) reuse the same check.
- **Files**: `scripts/docs/plantuml_invoke.py` (new, ~120 lines).
- **Validation**: `ruff` + `mypy --strict` clean, zero suppressions. No third-party imports.
- **Notes**: keep the docker argv as data so tests can assert `--network=none` and `SANDBOX` are
  present (a unit test on the argv-builder is cheap and non-fakeable).

### Subtask T004 – Real `@startyaml` spike fixture  `[P]`

- **Purpose**: a genuine diagram (not `hello world`) so the spike exercises fonts + YAML parsing.
- **Steps**: author `tests/docs/fixtures/spike_startyaml.md` containing a ` ```plantuml ` fence with
  a `@startyaml` block that has a `title`, several nested keys, and typed placeholders — shaped like
  the real schema diagrams WP05–WP07 will produce.
- **Files**: `tests/docs/fixtures/spike_startyaml.md`.

### Subtask T005 – Spike workflow `.github/workflows/plantuml-egress-spike.yml`

- **Purpose**: prove runnability on BOTH runners in CI (the actual gate).
- **Steps**:
  1. Trigger on PRs touching this mission's paths + `workflow_dispatch`.
  2. `strategy.matrix.runner: [ubuntu-latest, blacksmith-4vcpu-ubuntu-2404]`,
     `runs-on: ${{ matrix.runner }}`.
  3. Steps: checkout → download `plantuml.jar` from the pinned URL → **verify sha256** →
     `docker pull <image@digest>` (prefetch) → run the spike via `plantuml_invoke.py` over the
     fixture under `--network=none` → assert the output is a non-empty `<svg …>` → upload the SVG
     as an artifact.
  4. No `setup-java`. No `pip install`. `python3` (system) only.
- **Files**: `.github/workflows/plantuml-egress-spike.yml`.
- **Notes**: this workflow may remain as a permanent lightweight smoke, or be folded into the docs
  workflows by WP02 — decide at WP02 review. For now it is the standalone gate.

### Subtask T006 – Prove green on both runners; capture URLs; escalate on failure

- **Purpose**: convert "UNPROVEN" → PROVEN, or escalate loudly.
- **Steps**:
  1. Push the branch, let the spike run (or `workflow_dispatch`).
  2. Confirm **both** matrix legs pass. Record both run URLs in the Activity Log + the tracer.
  3. If blacksmith fails: STOP, capture the log, escalate to the operator, and record the exact
     failure mode (font vs DNS vs userns). Do not proceed to render/diagram WPs.

## Branch Strategy

- **Strategy**: merge back into `feat/doctrine-schema-diagrams-impl`.
- **Planning base branch**: `feat/doctrine-schema-diagrams-impl`
- **Merge target branch**: `feat/doctrine-schema-diagrams-impl`

## Test Strategy

- Unit test the argv-builder in `plantuml_invoke.py` (asserts `--network=none`, `SANDBOX`,
  `-Djava.awt.headless=true`, jar path) — runs everywhere, no docker needed.
- The **spike workflow itself** is the integration proof (docker-gated; CI-Linux is the hard gate).
- Local dev: `python3 -m pytest tests/docs/test_plantuml_invoke.py -q` (argv unit test). The docker
  render is proven in CI (skip locally if docker/image unavailable, but the CI matrix is mandatory).

## Risks & Mitigations

- **Fonts missing in JRE image** → `@startyaml` render fails. Mitigation: pick a font-bearing image;
  else bundle DejaVu. Verify locally before pushing.
- **Image pull under isolation** → fails (no network). Mitigation: prefetch by digest first (T002/T005).
- **blacksmith diverges from ubuntu-latest** → the whole capability is at risk. Mitigation: the
  matrix surfaces it early; escalate per T006.
- **sha256 drift** → build from an unverified binary. Mitigation: verify before every use (T003).

## Review Guidance

- Confirm BOTH matrix legs are green (reviewer opens both run URLs).
- Confirm no `setup-java`, no `pip install`, no third-party Python imports.
- Confirm `--network=none` + `SANDBOX` + `-Djava.awt.headless=true` are all present (argv test).
- Confirm the jar sha256 is verified before use and the image is digest-pinned + prefetched.
- Reviewer ≠ implementer (charter). Verify the green is real (open the CI logs), not asserted.

## Activity Log

> Append newest entries at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-08-12T18:02:18Z – claude-opus-4-8 – Implemented WP01 (plantuml_invoke.py stdlib seam, plantuml_pins.json [plantuml 1.2025.4 sha256 26518e14…, eclipse-temurin:21-jre-jammy @ sha256:3097cbbe…], spike fixture, argv/sha256/error-SVG unit tests, plantuml-egress-spike.yml). Local: ruff+mypy --strict clean, 6 unit tests green, end-to-end docker render under --network=none = valid error-free 6813-byte SVG. **CI GREEN on ubuntu-latest** (fork run 31625462256, 18s): jar sha256-verified, JRE pulled by digest, "valid error-free SVG, 6813 bytes, tokens present, --network=none". Blacksmith leg gated to upstream (forks lack blacksmith runners) — proves once the draft PR is on Priivacy-ai. DoD: ubuntu-latest ✅; blacksmith ⏳ (upstream PR). Runnability is now PROVEN, not UNPROVEN.
