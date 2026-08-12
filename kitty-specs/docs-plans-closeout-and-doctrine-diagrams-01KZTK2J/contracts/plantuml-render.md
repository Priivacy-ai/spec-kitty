# Contract: PlantUML render step (`scripts/docs/plantuml_render.py`)

**Requirement**: FR-006, NFR-002, NFR-003, NFR-004, C-004, C-006

## Interface

- **Invocation**: run after `docfx docfx.json` in both docs workflows, over the built `docs/_site`.
- **Input**: HTML pages containing fenced `@startjson … @endjson` / `@startyaml … @endyaml` (and `@startuml`) blocks.
- **Output**: the same HTML with each recognized block replaced by an inline `<svg>` (or `<img>` to a generated SVG under `docs/_site/assets/`).
- **Renderer**: a pinned local `plantuml.jar` invoked with `-DPLANTUML_SECURITY_PROFILE=SANDBOX`.

## Guarantees (testable)

1. **No egress (NFR-002)**: the render path makes zero network calls to any PlantUML server; verified by a test that fails if the code references a remote PlantUML endpoint or opens a socket during render.
2. **Pinned integrity (NFR-003)**: the workflow fetches `plantuml.jar` by version and verifies its **sha256** before use; a mismatch fails the build.
3. **Mermaid non-regression (NFR-004)**: ` ```mermaid ` blocks are left untouched; the modern DocFX template still renders them client-side.
4. **Bounded cost (NFR-003)**: adds ≤ 60s to the full docs build.
5. **Idempotent**: a page with no `@start*` block is unchanged.

## Failure modes

- Malformed `@start*` block → the build fails with the offending page/line (fail-closed, not silent).
- Unverified jar → fail before any render.
