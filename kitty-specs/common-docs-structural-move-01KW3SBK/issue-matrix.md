# Issue matrix — common-docs-structural-move-01KW3SBK

Per FR-037 of the spec-kitty-mission-review skill Gate-4. One row per issue referenced in spec.md.

| Issue | Title | Verdict | Evidence ref |
|-------|-------|---------|--------------|
| #651 | Common Docs structural consolidation | in-mission | Mission B docs/ fold; WP01 lands runtime-critical reads (spine head); terminal at mission close |
| #2165 | Docs consolidation tracking | in-mission | Mission B docs/ fold; resolved across WP02–WP15; terminal at mission close |
| #2054 | Docs structure relocation | in-mission | tree move lands WP03; runtime reads dual-read in WP01 |
| #2192 | Docs path references | in-mission | reference sweep WP08 after WP03 move; WP01 dual-reads in place |
| #1815 | Glossary/context relocation | in-mission | glossary→docs/context move WP03; extraction-source literal re-pointed WP01 |
| #2053 | ADR/architecture relocation | in-mission | architecture→docs/adr move WP03; authority-path reads dual-read WP01 |
| #1652 | Shim-registry / migrations docs | in-mission | shim-registry→docs/migrations move WP03; readers dual-read WP01 |
| #648 | Docs information architecture | in-mission | Mission B IA consolidation; terminal at mission close |

Valid `Verdict` values: `fixed`, `verified-already-fixed`, `deferred-with-followup`, `in-mission` (being fixed by a later WP in this mission; must reach a terminal verdict before mission `done`).
