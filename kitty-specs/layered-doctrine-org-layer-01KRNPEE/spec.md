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
shipped defaults and project-local configuration. An organisation publishes its governance
artifacts (directives, tactics, agent profiles, and so on) as a versioned **doctrine pack**.
Developers install the pack once on their machine using the `doctrine fetch` command. From that
point on, every project they create or open automatically inherits the organisation's governance
without any per-project setup.

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

### Scenario 2 — Doctrine maintainer assembles an org distributable

A governance maintainer aggregates multiple domain-specific packs (security, compliance,
architecture standards) into a single org distributable using `spec-kitty doctrine pack
assemble`. The assembled distributable includes a baseline charter fragment that all projects
inherit. She validates the assembled result, resolving any DRG edge conflicts between packs,
and publishes the distributable as a versioned artifact.

### Scenario 3 — IT enforces org doctrine installation

The company's platform team adds `spec-kitty doctrine fetch` to the standard developer
toolchain install script, pointing it at the published org distributable. All developers —
new starters and existing — receive the org governance layer as part of the standard toolchain.
No individual action is needed beyond running the install script.

### Scenario 4 — Developer starts a new project with zero org-layer configuration

A developer on a machine where the org doctrine pack is installed creates a new project and
runs `spec-kitty charter interview`. The interview surfaces org-layer directives, tactics, and
agent profiles alongside shipped defaults, each tagged with its source layer. The developer
selects the ones relevant to her project. During mission execution, org-layer governance is
injected into agent context automatically.

### Scenario 5 — Developer overrides one org artifact locally

A developer needs a project-specific variant of an org-layer security directive. She places an
override in `.kittify/doctrine/directives/`. The project layer takes precedence over the org
layer for that artifact; all other org artifacts continue to apply unchanged.

### Scenario 6 — Operator audits the full governance stack

A team lead runs `spec-kitty doctor` and sees the complete resolved doctrine stack with source
attribution: which artifacts are shipped, which are org-layer, and which are project overrides.
When `charter lint` runs, it emits advisory warnings for any org artifact that overrides a
shipped artifact, giving the team visibility without blocking the workflow.

---

## Domain Language

| Canonical term | Definition | Avoid |
|---|---|---|
| **doctrine pack** | A versioned, self-contained directory of org-layer governance artifacts, validated against the schema | "plugin", "extension", "module" |
| **org layer** | The middle resolution tier, between shipped and project | "company layer", "tenant layer", "custom layer" |
| **local snapshot** | The validated copy of an org doctrine pack written to the developer's machine by `doctrine fetch` | "cache", "mirror" |
| **resolution** | The process of merging shipped, org, and project layers into the active governance set | "loading", "compilation" |
| **source attribution** | The tag (`shipped`, `org`, `project`) carried by each resolved artifact indicating which layer it came from | "provenance label", "origin tag" |
| **assembling** | Merging multiple domain-specific packs into a single distributable | "bundling", "packaging" |
| **graph extension** | Additive DRG edges and nodes contributed by the org layer without replacing the shipped graph | "graph patch", "graph overlay" |

---

## Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| FR-001 | Doctrine resolution follows a strict three-layer order: shipped → org → project. A higher layer takes full precedence over a lower layer for any given artifact ID. | Proposed |
| FR-002 | All eight artifact types support the org layer: directives, tactics, styleguides, toolguides, paradigms, procedures, agent profiles, and mission step contracts. | Proposed |
| FR-003 | When the same artifact ID appears in multiple layers, the higher layer fully replaces the lower layer's artifact (full-replace semantics). Partial field merging is not applied across layers. | Proposed |
| FR-004 | The Doctrine Reference Graph can be loaded from either a single file or a directory of domain-scoped graph fragment files. All three layers (shipped, org, project) support the fragment-directory layout. | Proposed |
| FR-005 | Org-layer graph extensions are additive: they add nodes and edges to the graph without removing or replacing existing shipped nodes or edges. | Proposed |
| FR-006 | Operators can declare an org doctrine source in the project configuration file, specifying the source type, remote address, optional version pin, and local snapshot path. | Proposed |
| FR-007 | `spec-kitty doctrine fetch` pulls the org doctrine pack from a declared remote source and writes a validated local snapshot. The fetch is the only moment network or API calls occur; resolution always reads the local snapshot. | Proposed |
| FR-008 | `spec-kitty doctrine fetch` supports a **git repository** as the remote source. An optional version pin (git tag or commit SHA) can be specified; without a pin, the default branch is pulled. | Proposed |
| FR-009 | `spec-kitty doctrine fetch` supports an **HTTPS bundle or tarball URL** as the remote source. An optional version pin (tarball name or query parameter) can be specified. | Proposed |
| FR-010 | `spec-kitty doctrine fetch` supports an **HTTP API endpoint** as the remote source. The org exposes doctrine artifacts through the published API contract; fetch pulls all artifact types and writes them to the local snapshot in the standard pack layout. | Proposed |
| FR-011 | `spec-kitty doctrine fetch` validates all fetched artifacts against the schema before writing the local snapshot. If validation fails, the existing snapshot is not overwritten; the operator receives a list of validation errors. | Proposed |
| FR-012 | A pack author can run `spec-kitty doctrine pack validate <path>` against a local directory to confirm schema compliance, DRG edge consistency, and artifact completeness before publication. The command reports all violations with artifact-level detail. | Proposed |
| FR-013 | A doctrine maintainer can run `spec-kitty doctrine pack assemble <output-path> [<pack-path>...]` to merge multiple domain-specific packs into a single distributable snapshot. Conflicts between packs are reported and must be resolved before the assembled output is written. | Proposed |
| FR-014 | `charter context --json` includes a `"source"` field on every resolved artifact indicating its layer: `"shipped"`, `"org"`, or `"project"`. | Proposed |
| FR-015 | `spec-kitty doctor` lists all org-layer artifacts currently available on the machine, including their source pack, version (if known), and artifact type. | Proposed |
| FR-016 | `charter lint` emits an advisory warning (non-blocking) when an org artifact overrides a shipped artifact. The warning names the artifact ID and both the shipped and org sources. | Proposed |
| FR-017 | The artifact repository base class is documented as the canonical extension point for third-party repository implementations. The documentation describes the interface contract, loading lifecycle, and the expectation that any implementation must support the three-layer query pattern. No additional implementation is shipped by this mission. | Proposed |
| FR-018 | When no org doctrine snapshot is present on the machine, resolution falls back gracefully to shipped + project (two-layer). A diagnostic message is surfaced by `spec-kitty doctor` but no error is raised during normal operation. | Proposed |
| FR-019 | Resolution is deterministic: given the same local snapshot and project-layer files, the resolved governance set is always identical regardless of invocation order, timing, or environment. | Proposed |

---

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | `doctrine fetch` completes for a typical org pack (up to 200 artifacts, 50 graph nodes) within an acceptable interactive wait time. | Under 30 seconds on a standard broadband connection | Proposed |
| NFR-002 | Doctrine resolution (reading the local snapshot) adds no perceptible overhead to `charter context` response time compared to the current two-layer baseline. | Under 50 ms added latency for packs up to 200 artifacts | Proposed |
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
| C-004 | The configuration and CLI surface expose a single org-layer slot. The internal data model supports an ordered list of org roots to allow future multi-org composition, but that UX is not exposed in this mission. | Proposed |
| C-005 | When the API source type (FR-010) is used, the API call happens only during `doctrine fetch`. The snapshot written to disk has exactly the same format as a snapshot produced from a git or HTTPS source. No special API-aware code path exists in resolution. | Proposed |
| C-006 | Existing project-layer override behaviour is unchanged. Any project that currently relies on project-layer overrides continues to work without modification. | Proposed |
| C-007 | The `pack assemble` command does not automatically resolve inter-pack conflicts; it reports them and requires explicit operator resolution before writing output. | Proposed |

---

## Key Entities

| Entity | Description |
|---|---|
| **OrgDoctrinePack** | A versioned directory of doctrine artifacts and graph extensions conforming to the published pack layout. Published and versioned by a doctrine maintainer. |
| **OrgDoctrineSnapshot** | A validated local copy of a pack, written to a declared path on the developer's machine by `doctrine fetch`. The snapshot is the sole input to org-layer resolution. |
| **OrgDoctrineSource** | A declared fetch-time source: a git repository, an HTTPS bundle URL, or an HTTP API endpoint. Encapsulates the remote location, credentials hint, and optional version pin. |
| **DoctrineLayers** | The ordered resolution stack: shipped, org, project. Each layer is a root directory or absent. |
| **DoctrineArtifact** | Any governance artifact (directive, tactic, styleguide, toolguide, paradigm, procedure, agent profile, mission step contract) loadable from any layer. |
| **SourceAttribution** | The layer tag (`shipped`, `org`, `project`) carried by a resolved artifact in context and doctor output. |
| **GraphExtension** | A set of additive DRG nodes and edges contributed by the org layer or a graph fragment file. |
| **GraphFragment** | A domain-scoped partial DRG file loaded as part of a multi-file graph. Fragments are merged before layer merging. |

---

## Assumptions

- The org pack directory layout mirrors the shipped layout (`directives/`, `tactics/`, `agent_profiles/`, etc.) with an additional `graph-extensions.yaml` (or `drg/` fragment directory) for DRG additions.
- `doctrine fetch` is an explicit operator action invoked by a human or a machine provisioning script; there is no background auto-update or daemon.
- The HTTP API source contract is specified and published as part of this mission. Implementors of custom API sources must satisfy that contract.
- Multi-pack assembly conflict resolution is manual and deliberate; the command reports conflicts and exits, leaving the operator to resolve them before re-running.
- Projects that have no `.kittify/config.yaml` `doctrine.org` entry, or that are on machines with no installed snapshot, continue to operate with two-layer resolution (shipped + project) exactly as today.
- The version pin for git sources is a tag name or full commit SHA; branch names are supported but discouraged for reproducibility.
- A doctrine maintainer assembling a distributable is expected to curate the domain packs; `pack assemble` is a build-time tool, not a runtime feature.

---

## Success Criteria

1. An organisation can publish a versioned doctrine pack and distribute it to all developer machines with a single install command, without forking spec-kitty or modifying any project.
2. Every project on a machine with the org snapshot installed inherits org governance automatically — no per-project configuration is needed.
3. A developer can override any org artifact locally and have the project layer take precedence, with all other org artifacts still applying.
4. `charter context` output correctly attributes every resolved artifact to its source layer (`shipped`, `org`, or `project`).
5. `spec-kitty doctor` surfaces the complete resolved governance stack with source attribution and the installed pack version.
6. `doctrine fetch` completes successfully against git, HTTPS bundle, and API sources and produces a validated local snapshot that resolution can consume.
7. `pack validate` reliably detects and reports all schema violations and DRG edge consistency failures in a candidate pack before publication.
8. All existing shipped-layer and project-layer tests continue to pass unchanged after the org-layer changes are merged.
