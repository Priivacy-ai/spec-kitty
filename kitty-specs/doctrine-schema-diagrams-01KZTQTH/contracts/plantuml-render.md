# Contract: PlantUML render step (FR-001, NFR-002/003/004/005)
- Inserted AFTER glossary_linker in BOTH docs-build-pr.yml + docs-pages.yml (+ deploy paths: allowlist).
- Recovers ```plantuml fences from _site (html.unescape; assert language-plantuml class); renders via pinned (version+sha256) plantuml.jar under SANDBOX; injects SVG with derived non-trivial alt/aria.
- Testable: round-trip (md→_site→recovered→SVG); Mermaid untouched; malformed fence fails-closed; jar sha256 mismatch fails before render; ≤60s monitored (not gate).
