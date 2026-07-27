# Spec: Layered Doctrine Resolution — Org Layer

**Mission ID:** 01KRNPEE69Q0T540T7PRWSZ6CB  
**Mission slug:** layered-doctrine-org-layer-01KRNPEE  
**Status:** Draft  
**Mission type:** software-dev  
**Target branch:** feat/org-doctrine-layer  
**Related issues:** #832  
**Successor mission:** Governance-Aware Context (Mission B, closes #883 and #1013)

---

## Overview

Spec-kitty currently resolves governance doctrine from two layers: a shipped set bundled with
the CLI and a project-local set in `.kittify/doctrine/`. This two-layer model works for
individual projects but does not support organisations that adopt spec-kitty across multiple
teams. Today those organisations must either fork the CLI to embed their governance standards,
or repeat the same configuration in every project — both of which are unsustainable at scale.

This mission adds a third resolution layer — the **organisation layer** — sitting between the
shipped defaults and project-local configuration. An organisation manages its governance
artifacts (directives, tactics, agent profiles, and so on) in one or more **doctrine packs**,
each a git-managed repository in its own right — with changelogs, PR-based governance, and
version tags. Developers install packs on their machine using the `doctrine fetch` command,
which maintains a persistent local clone of each repository. From that point on, every project
they create or open automatically inherits the organisation's governance without any per-project
setup.

Multiple packs can be configured independently and fetched independently. A security team, an
architecture team, and a compliance team may each own their own pack repository; changes to any
one pack do not require the others to rebuild or re-release.

The mission also extends the Doctrine Reference Graph to support multiple fragment files per
layer, provides tooling for pack authors to validate and assemble packs before publication, and
surfaces provenance information in all governance context outputs so teams know which layer each
artifact came from.

---

## User Scenarios

### Scenario 1 — Security policy lead publishes an org doctrine pack

A security policy lead in an engineering organisation needs every development team to follow
the company's security discovery process and mandatory security directives. She creates a
security doctrine pack containing the relevant artifacts, validates it against the schema using
`spec-kitty doctrine pack validate`, tags it as a versioned release, and publishes it to the
company's internal git repository.

She does not fork spec-kitty, and no project team needs to copy any files — the pack is the
single source of truth for security governance.

### Scenario 2 — Multiple domain teams each own a doctrine repository

A large organisation has three independent doctrine repositories: one maintained by the
security team, one by the architecture team, and one by the compliance team. Each team governs
their repository with their own PR process, changelog, and release tags. When the security team
patches a directive, they merge a PR and tag a release — the architecture and compliance packs
are unaffected and do not need to rebuild.

Developers configure all three packs in their `.kittify/config.yaml` and run
`spec-kitty doctrine fetch` to install all of them. They can also run
`spec-kitty doctrine fetch --pack security` to update just the security pack without touching
the others. Resolution merges all three org packs in declaration order, with later packs taking
precedence over earlier ones; the project layer still overrides all org packs.

### Scenario 3 — Doctrine maintainer assembles an org distributable (optional)

For organisations that prefer a single distribution artifact over multiple independent
repositories, a governance maintainer aggregates multiple domain-specific packs into a single
distributable using `spec-kitty doctrine pack assemble`. She validates the assembled result,
resolving any DRG edge conflicts, and publishes the distributable as a versioned artifact.
Consumers then configure a single pack pointing at the distributable.

This scenario is optional — organisations may choose Scenario 2 (independent repositories)
or Scenario 3 (assembled distributable) based on their governance model.

### Scenario 4 — IT enforces org doctrine installation

The company's platform team adds `spec-kitty doctrine fetch` to the standard developer
toolchain install script, pointing it at all configured org repositories. All developers —
new starters and existing — receive the org governance layer as part of the standard toolchain.
No individual action is needed beyond running the install script.

### Scenario 5 — Developer starts a new project with zero org-layer configuration

A developer on a machine where the org doctrine pack is installed creates a new project and
runs `spec-kitty charter interview`. The interview surfaces org-layer directives, tactics, and
agent profiles alongside shipped defaults, each tagged with its source layer. The developer
selects the ones relevant to her project. During mission execution, org-layer governance is
injected into agent context automatically.

### Scenario 6 — Developer overrides one org artifact locally

A developer needs a project-specific variant of an org-layer security directive. She places an
override in `.kittify/doctrine/directives/`. The project layer takes precedence over the org
layer for that artifact; all other org artifacts continue to apply unchanged.

### Scenario 7 — Operator audits the full governance stack

A team lead runs `spec-kitty doctor doctrine` and sees the complete resolved doctrine stack:
the spec-kitty built-in pack, each configured org pack (by name, version, and artifact count),
and the project-local pack. `charter lint` emits advisory warnings for any org artifact that
overrides a built-in artifact, giving the team visibility without blocking the workflow.

---

## Domain Language

| Canonical term | Definition | Avoid |
|---|---|---|
| **doctrine pack** | A versioned, self-contained directory of doctrine artifacts conforming to the published pack layout. Every layer is a pack: the spec-kitty built-in pack, any number of org packs, and the project-local pack. | "plugin", "extension", "module" |
| **spec-kitty built-in** | The default doctrine artifacts bundled with the CLI. Referred to as "spec-kitty built-in" in all user-facing output and documentation. Machine-readable source tag: `"builtin"`. This naming allows the built-in set to be extracted into its own repository in a future release without a terminology break. | "shipped", "default", "core doctrine" |
| **org pack** | A doctrine pack maintained by an organisation, installed on the developer's machine via `doctrine fetch`. May be a git-managed repository, an HTTPS bundle, or an API-backed source. | "company layer", "custom layer", "tenant pack" |
| **org layer** | The middle resolution tier, composed of one or more org packs merged in declaration order (later packs override earlier ones). | "company layer", "tenant layer" |
| **git-managed pack** | A doctrine pack whose canonical home is a git repository, governed by PR review and version tags. The local installation is a persistent git clone. | "git snapshot", "git cache" |
| **local clone** | The persistent `git clone` of a git-managed pack on the developer's machine. The clone is the installation — its working tree is read directly by resolution. | "cache", "mirror", "snapshot" (for git sources) |
| **local snapshot** | The validated filesystem copy of a non-git doctrine pack (HTTPS bundle or API source), written atomically by `doctrine fetch`. Not applicable to git-managed packs. | "cache", "mirror" |
| **pack registry** | The ordered list of configured org packs declared in `.kittify/config.yaml` under `doctrine.org.packs`. | "pack list", "org config" |
| **resolution** | The process of merging the built-in pack, org packs, and project-local pack into the active governance set | "loading", "compilation" |
| **source attribution** | The tag (`builtin`, `org`, `project`) carried by each resolved artifact indicating which layer it came from. Displayed in `charter context --json` and `doctor doctrine` output. | "provenance label", "origin tag" |
| **assembling** | Merging multiple org packs into a single distributable pack (itself publishable as a git-managed repository) | "bundling", "packaging" |
| **graph extension** | Additive DRG edges and nodes contributed by an org pack without replacing or removing built-in graph nodes or edges | "graph patch", "graph overlay" |

---

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Doctrine resolution follows a strict three-layer order: shipped → org → project. A higher layer takes full precedence over a lower layer for any given artifact ID. | Proposed |
| FR-002 | All eight artifact types support the org layer: directives, tactics, styleguides, toolguides, paradigms, procedures, agent profiles, and mission step contracts. | Proposed |
| FR-003 | When the same artifact ID appears in multiple layers, the higher layer takes ownership of the resolved artifact (its `provenance` becomes that layer). Field-level merge applies: fields present in the higher layer's YAML replace the same-named fields in the lower layer; fields absent from the higher layer fall through to the lower layer's value. No two artifacts with the same ID coexist across layers — the higher layer's identity wins. The resolver emits an operator-visible collision warning each time a higher layer shadows a lower-layer artifact, with the artifact ID, source and target layers, and the count of replaced fields. See ADR `architecture/2.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`. | Proposed |
| FR-004 | The Doctrine Reference Graph can be loaded from either a single file or a directory of domain-scoped graph fragment files. All three layers (shipped, org, project) support the fragment-directory layout. | Proposed |
| FR-005 | Org-layer graph extensions are additive: they add nodes and edges to the graph without removing or replacing existing shipped nodes or edges. | Proposed |
| FR-006 | Operators declare org doctrine packs in the project configuration file as an ordered list. Each pack entry specifies a name, source type, remote address, optional version pin, and local path. Multiple packs may be configured simultaneously; declaration order determines precedence (later entries override earlier ones within the org layer). | Proposed |
| FR-007 | `spec-kitty doctrine fetch` installs or updates all configured org doctrine packs. The fetch is the only moment network or API calls occur; resolution always reads from local paths. | Proposed |
| FR-008 | `spec-kitty doctrine fetch` supports a **git repository** as the remote source. For git sources, the local installation is a **persistent git clone**: the first fetch runs `git clone`; subsequent fetches run `git fetch` and reset to the declared ref. The working tree of the clone is read directly by resolution. An optional version pin (git tag or commit SHA) can be specified; without a pin, the default branch HEAD is used. | Proposed |
| FR-009 | `spec-kitty doctrine fetch` supports an **HTTPS bundle or tarball URL** as the remote source. Fetched content is written atomically to a local snapshot directory. An optional version pin can be specified. | Proposed |
| FR-010 | `spec-kitty doctrine fetch` supports an **HTTP API endpoint** as the remote source. The org exposes doctrine artifacts through the published API contract; fetch pulls all artifact types and writes them atomically to a local snapshot directory in the standard pack layout. | Proposed |
| FR-011 | `spec-kitty doctrine fetch` validates all fetched artifacts against the schema. For non-git sources, validation happens before the atomic write; if validation fails, the existing snapshot is not overwritten. For git sources, validation runs after the checkout; on failure, a diagnostic is emitted and the clone remains at the previous commit. The operator receives a list of validation errors in both cases. | Proposed |
| FR-012 | A pack author can run `spec-kitty doctrine pack validate <path>` against a local directory to confirm schema compliance, DRG edge consistency, and artifact completeness before publication. The command reports all violations with artifact-level detail. | Proposed |
| FR-013 | A doctrine maintainer can run `spec-kitty doctrine pack assemble <output-path> [<pack-path>...]` to merge multiple domain-specific packs into a single distributable snapshot. Conflicts between packs are reported and must be resolved before the assembled output is written. | Proposed |
| FR-014 | `charter context --json` includes a `"source"` field on every resolved artifact indicating its layer: `"builtin"` (spec-kitty built-in pack), `"org"` (any configured org pack), or `"project"` (project-local overrides). | Proposed |
| FR-015 | `spec-kitty doctor doctrine` lists all configured org doctrine packs, with per-pack status: whether the local clone or snapshot is present, the installed version (git describe output or pack-manifest version), and artifact counts by type. | Proposed |
| FR-016 | `charter lint` emits an advisory warning (non-blocking) when an org artifact overrides a built-in artifact, or when two org packs declare the same artifact ID. The warning names the artifact ID and both source packs. | Proposed |
| FR-017 | The artifact repository base class is documented as the canonical extension point for third-party repository implementations. The documentation describes the interface contract, loading lifecycle, and the expectation that any implementation must support the three-layer query pattern. No additional implementation is shipped by this mission. | Proposed |
| FR-018 | When no org doctrine snapshot is present on the machine, resolution falls back gracefully to shipped + project (two-layer). A diagnostic message is surfaced by `spec-kitty doctor` but no error is raised during normal operation. | Proposed |
| FR-019 | Resolution is deterministic: given the same local pack content and project-layer files, the resolved governance set is always identical regardless of invocation order, timing, or environment. | Proposed |
| FR-020 | `spec-kitty doctrine fetch` accepts an optional `--pack <name>` flag. When provided, only the named pack is fetched; all other configured packs are left unchanged. When omitted, all configured packs are fetched in declaration order. | Proposed |
| FR-021 | For git-managed packs, the version installed on the machine is visible via `git describe` on the local clone. `spec-kitty doctor doctrine` surfaces this information per pack without requiring a separate `pack-manifest.yaml` for git sources. For non-git sources, version information is read from the `pack-manifest.yaml` written by `doctrine fetch`. | Proposed |
| FR-022 | A `pack assemble` output (a merged distributable pack directory) may be published as a git-managed repository and subsequently configured and consumed as a git source by developers. The distributable is not a special artifact type — any directory conforming to the pack layout, when hosted in a git repository, can be declared as a git-source pack. | Proposed |
| FR-023 | Projects that do not declare a `doctrine.org.packs` block in their `.kittify/config.yaml` experience no change in behavior. The org-layer feature has zero effect on existing kittified projects that have not opted in. Existing two-layer resolution (built-in + project) continues to work exactly as before this mission. | Proposed |
| FR-024 | `spec-kitty doctor doctrine` presents an overview of all active doctrine packs in a unified listing: the spec-kitty built-in pack, all configured org packs (by name), and the project-local pack (`.kittify/doctrine/`). This gives operators a single command to see the complete active doctrine stack across all layers. | Proposed |
| FR-025 | The charter supports a tiered composition model parallel to the doctrine layer. An org pack may include an `org-charter.yaml` file declaring org-wide governance policy: interview default answers, required directive selections, and advisory governance policies. The composition order is: spec-kitty built-in charter defaults → org charter(s) in pack declaration order → project charter. | Proposed |
| FR-026 | `spec-kitty charter interview` incorporates org charter policy from all configured org packs. Interview questions are pre-filled with `interview_defaults` declared in each `org-charter.yaml` (merged in pack precedence order). Directive IDs listed in `required_directives` are pre-selected. The user may inspect and modify pre-filled values during the interactive interview. | Proposed |
| FR-027 | `charter context --action <action>` includes org charter governance elements in the rendered context, with source attribution indicating whether each policy element originates from the spec-kitty built-in defaults, a named org charter pack, or the project charter. | Proposed |
| FR-028 | `charter lint` emits advisory warnings (non-blocking) when the project charter deviates from a governance policy declared in an org charter. Advisory enforcement is the only enforcement model in this mission; no hard errors or workflow blocks are produced for org charter policy deviations. | Proposed |
| FR-029 | `spec-kitty doctor doctrine` includes per-pack org charter status: whether `org-charter.yaml` is present, how many `interview_defaults`, `required_directives`, and `governance_policies` it declares. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | `doctrine fetch` completes for a typical org pack (up to 200 artifacts, 50 graph nodes) within an acceptable interactive wait time. For git sources, subsequent fetches (pull) are faster than initial clones. | Under 30 seconds per pack on a standard broadband connection | Proposed |
| NFR-002 | Doctrine resolution (reading local pack directories) adds no perceptible overhead to `charter context` response time compared to the current two-layer baseline. The threshold applies to the total resolved artifact set across all configured org packs combined, not per individual pack. | Under 50 ms added latency when total org-layer artifacts across all configured packs ≤ 200 and configured pack count ≤ 10 | Proposed |
| NFR-003 | `pack validate` completes for a pack of up to 200 artifacts without undue wait. | Under 5 seconds | Proposed |
| NFR-004 | Invalid or corrupt artifacts in the org pack are skipped individually with a warning. A single bad artifact does not prevent the remaining artifacts from loading. | Zero fatal failures caused by individual artifact schema violations | Proposed |
| NFR-005 | The introduction of the org layer does not break any existing shipped-layer or project-layer test. All prior test scenarios continue to pass unchanged. | 100% of existing tests pass | Proposed |
| NFR-006 | The org-layer feature is fully usable without network access after `doctrine fetch` has been run once. All resolution, context, and lint commands work offline. | No network dependency at resolution time | Proposed |

---

## Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | No runtime remote calls: network or API calls are permitted only during `doctrine fetch`, never during governance resolution, context generation, or linting. | Proposed |
| C-002 | Live synchronisation or background auto-update of the org snapshot is out of scope for this mission. Snapshot updates are always explicit operator actions via `doctrine fetch`. | Proposed |
| C-003 | The shipped doctrine layer is read-only; org-layer artifacts do not modify or patch shipped content. | Proposed |
| C-004 | The configuration and CLI surface expose a multi-pack org layer. Each pack is independently sourced, fetched, and versioned. The internal data model accumulates all configured pack paths as an ordered list (`org_roots: list[Path]`) in declaration order. There is no hard limit on the number of packs; practical limits are determined by governance policy, not the tool. | Proposed |
| C-005 | When the API source type is used, the API call happens only during `doctrine fetch`. The snapshot written to disk has the same pack layout as any other source type. No special API-aware code path exists in resolution — resolution reads local files regardless of how they were originally fetched. Git-managed packs are read from their working tree directly; non-git snapshots are read from their snapshot directory. | Proposed |
| C-006 | Existing project-layer override behaviour is unchanged. Any project that currently relies on project-layer overrides continues to work without modification. | Proposed |
| C-007 | The `pack assemble` command does not automatically resolve inter-pack conflicts; it reports them and requires explicit operator resolution before writing output. | Proposed |

---

## Key Entities

| Entity | Description |
|---|---|
| **OrgDoctrinePack** | A versioned, self-contained directory of doctrine artifacts and graph extensions conforming to the published pack layout. May be a git repository, an HTTPS bundle, or an API-backed source. A `pack assemble` distributable is a valid pack and can itself be published as a git repository. |
| **OrgPackConfig** | A single named entry in the pack registry: name, source type, remote URL, optional version pin, and local path. Drives a single `doctrine fetch` invocation. |
| **PackRegistry** | The ordered list of `OrgPackConfig` entries declared in `.kittify/config.yaml` under `doctrine.org.packs`. Declaration order determines intra-org-layer precedence. |
| **GitManagedPack** | A doctrine pack whose canonical home is a git repository with its own PR process and release tags. The local installation is a persistent `git clone`; the working tree is read directly by resolution. |
| **LocalClone** | The persistent git clone of a `GitManagedPack` on the developer's machine. For git sources this replaces the concept of a "snapshot" — the clone IS the installed pack. |
| **LocalSnapshot** | The atomic filesystem copy of a non-git doctrine pack (HTTPS bundle or API source), written by `doctrine fetch`. Not applicable to git-managed packs. |
| **OrgDoctrineSource** | A fetch-time source adapter: git repository, HTTPS bundle URL, or HTTP API endpoint. Encapsulates the remote location, credentials hint, and optional version pin. |
| **DoctrineLayers** | The ordered resolution stack: shipped, org (one or more packs merged in declaration order), project. Each layer is one or more root directories or absent. |
| **DoctrineArtifact** | Any governance artifact (directive, tactic, styleguide, toolguide, paradigm, procedure, agent profile, mission step contract) loadable from any layer. |
| **SourceAttribution** | The layer tag (`shipped`, `org`, `project`) carried by a resolved artifact in context and doctor output. |
| **OrgCharterPolicy** | The structured governance policy declared in an org pack's `org-charter.yaml`: interview defaults, required directive selections, and advisory governance constraints. Parallels the doctrine artifact set within a pack. |
| **GraphExtension** | A set of additive DRG nodes and edges contributed by the org layer or a graph fragment file. |
| **GraphFragment** | A domain-scoped partial DRG file loaded as part of a multi-file graph. Fragments are merged before layer merging. |

---

## Assumptions

- The org pack directory layout mirrors the shipped layout (`directives/`, `tactics/`, `agent_profiles/`, etc.) with an optional `drg/` fragment directory for DRG additions, and an optional `org-charter.yaml` for org governance policy.
- `doctrine fetch` is an explicit operator action invoked by a human or a machine provisioning script; there is no background auto-update or daemon.
- For git-managed packs, the local clone directory contains a `.git/` subdirectory. Resolution reads the working tree directly; it does not shell out to git at resolution time.
- The HTTP API source contract is specified and published as part of this mission. Implementors of custom API sources must satisfy that contract.
- Multi-pack assembly conflict resolution is manual and deliberate; `pack assemble` reports conflicts and exits, leaving the operator to resolve them before re-running.
- A `pack assemble` distributable is itself a valid pack layout; it may be pushed to a git repository and subsequently consumed as a git-source pack by any number of developers. The tooling treats it identically to a hand-authored git-managed pack.
- Projects that have no `doctrine.org.packs` entry in `.kittify/config.yaml`, or that are on machines where no packs have been fetched, continue to operate with two-layer resolution (shipped + project) exactly as today.
- The version pin for git sources is a tag name or full commit SHA; branch names are accepted but discouraged for reproducibility. `git describe --tags --always` is the canonical version display.
- Precedence within the org layer follows declaration order in `packs`: the last declared pack has the highest precedence within the org layer (overrides earlier packs on artifact ID collision, and on `org-charter.yaml` `interview_defaults` key collision). An advisory warning is emitted when two org packs declare the same artifact ID.
- Org charter enforcement is advisory-only in this mission. The `mandatory` enforcement tier is deferred to a future mission where the UX for hard policy blocking can be designed deliberately.
- `pack assemble` merges `org-charter.yaml` files from input packs: `interview_defaults` are deep-merged (later pack wins on key collision); `required_directives` are unioned; `governance_policies` are concatenated with deduplication.

---

## Success Criteria

1. An organisation can maintain multiple independently versioned doctrine packs in separate git repositories, each governed by its own PR process, and distribute them to all developer machines without forking spec-kitty or modifying any project.
2. Every project on a machine with org packs installed inherits all configured org governance automatically — no per-project configuration is needed.
3. A developer can run `spec-kitty doctrine fetch --pack <name>` to update a single pack without disturbing the others.
4. A developer can override any org artifact locally and have the project layer take precedence, with all other org artifacts still applying.
5. `charter context` output correctly attributes every resolved artifact to its source layer (`shipped`, `org`, or `project`).
6. `spec-kitty doctor doctrine` surfaces each configured pack with per-pack install status, version, and artifact counts.
7. `doctrine fetch` completes successfully against git (clone-or-pull), HTTPS bundle, and API sources.
8. For git-managed packs, the installed version is always readable via `git describe` on the local clone without any additional spec-kitty tooling.
9. A `pack assemble` distributable, when pushed to a git repository, can be consumed as a git-source pack with no additional configuration — it is indistinguishable from a hand-authored pack repository.
10. `pack validate` reliably detects and reports all schema violations, DRG edge consistency failures, and `org-charter.yaml` schema errors in a candidate pack before publication.
11. `charter interview` pre-fills answers from org charter policy; a project starting from scratch on a machine with org packs configured immediately gets org-mandated defaults without manual selection.
12. All existing shipped-layer and project-layer tests continue to pass unchanged after the org-layer changes are merged.
