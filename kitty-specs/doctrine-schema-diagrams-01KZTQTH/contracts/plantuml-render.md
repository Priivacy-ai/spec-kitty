# Contract: PlantUML render step (FR-001, NFR-003/004/005) — hardened per post-plan squad

## Placement
- Inserted **immediately after `glossary_linker`, before redirect-stub generation + `seo_verify --strict`**, in BOTH `docs-build-pr.yml` + `docs-pages.yml` (+ the deploy `paths:` enumerated allowlist — it is not a glob). A round-trip test runs the full downstream chain over an SVG-injected page.
- Recovers ` ```plantuml ` fences from `_site`: `html.unescape` the payload; **confirm the emitted fence class against real `_site` HTML** (`language-plantuml` vs `lang-…`) — the round-trip test is the backstop.

## Alt-text (NFR-005, reviewer MEDIUM — concrete predicate)
- Alt/aria derived from the diagram's title/caption; test renders **two differently-titled** diagrams and asserts **distinct** alt equal to the derived caption and NOT in a generic-fallback set (`{"yaml","diagram",""}`). Confirm the derivation source (PlantUML `title` vs surrounding markdown heading).

## Other testable guarantees
- Mermaid untouched; malformed fence fails-closed; jar sha256 mismatch fails before render; ≤60s is a monitored budget (not a gate).
