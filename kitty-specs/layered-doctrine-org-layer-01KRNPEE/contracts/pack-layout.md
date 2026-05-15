# Contract: Org Doctrine Pack Layout

**Version**: 1.0  
**Mission**: `layered-doctrine-org-layer-01KRNPEE`  
**Status**: Draft — normative for pack authors and `pack validate`

---

## Purpose

This document specifies the canonical directory layout that a spec-kitty org doctrine pack
must conform to. Any tool that produces a pack (including `doctrine fetch`, `pack assemble`,
or a custom build pipeline) must produce output matching this layout. The `doctrine pack
validate` command enforces this contract.

---

## Directory Layout

```
<pack-root>/
│
├── pack-manifest.yaml          [written by fetch/assemble; read-only for authors]
│
├── directives/                 [optional]
│   └── *.directive.yaml
│
├── tactics/                    [optional]
│   └── *.tactic.yaml
│
├── styleguides/                [optional]
│   └── **/*.styleguide.yaml    [subdirectory nesting allowed, same as project layer]
│
├── toolguides/                 [optional]
│   └── *.toolguide.yaml
│
├── paradigms/                  [optional]
│   └── *.paradigm.yaml
│
├── procedures/                 [optional]
│   └── *.procedure.yaml
│
├── agent_profiles/             [optional]
│   └── *.agent.yaml
│
├── mission_step_contracts/     [optional]
│   └── *.contract.yaml
│
├── drg/                        [optional]
│   └── *.graph.yaml            [DRG graph extension fragments]
│
└── org-charter.yaml            [optional] [org governance policy: interview defaults,
                                            required directives, advisory policies]
```

---

## Rules

### General rules

1. The `<pack-root>` directory MUST be readable as a filesystem directory.
2. All artifact subdirectories are OPTIONAL. A valid pack may contain any non-empty subset.
3. `org-charter.yaml` is OPTIONAL at the pack root. Packs without it contribute only doctrine
   artifacts; their governance policy is treated as empty (no interview defaults, no required
   directives, no advisory policies).
4. An entirely empty pack (no artifact files, no DRG extensions, no `org-charter.yaml`) is
   valid but produces no governance effect.

### Artifact files

4. Each artifact file MUST conform to the spec-kitty YAML schema for its type.
5. Each artifact MUST have a unique `id` field within its type. Duplicate IDs within the
   same pack are a validation error.
6. IDs in an org pack SHOULD be namespaced to reduce collision risk with shipped IDs.
   Recommended convention: prefix with an org-specific code (e.g., `acme-sec-001-...`).
   This is advisory; collisions with shipped IDs are permitted but result in full-replace
   semantics (the org artifact substitutes the shipped artifact) and produce an advisory
   warning in `charter lint`.

### DRG extensions

7. Graph extension files in `drg/` MUST NOT remove or modify existing shipped graph nodes
   or edges. Extensions are additive only.
8. Every artifact URN referenced in a DRG extension MUST resolve to an artifact present in
   the merged shipped + org artifact set. Dangling edges are a validation error.
9. Multiple fragment files in `drg/` are merged in alphabetical filename order. Fragment
   authors SHOULD name files to make ordering explicit (e.g., `010-security.graph.yaml`).

### org-charter.yaml

10. `org-charter.yaml` is OPTIONAL. Its absence is not a validation error.
11. When present, `org-charter.yaml` MUST conform to the `OrgCharterPolicy` schema
    (`schema_version`, `interview_defaults`, `required_directives`, `governance_policies`).
    Schema violations are a validation error.
12. `enforcement` values other than `"advisory"` are accepted with an advisory warning
    (future values may be added; unknown values SHOULD NOT fail validation).
13. `required_directives` entries that reference artifact IDs not present in the pack's own
    `directives/` directory are not an error — the directive may exist in another configured
    pack or in the built-in set. Unresolvable IDs produce an advisory warning at runtime.

### pack-manifest.yaml

14. `pack-manifest.yaml` is written by `doctrine fetch` (for non-git sources) and
    `doctrine pack assemble`. Pack authors MUST NOT create or modify this file manually.
15. For git-managed packs, `pack-manifest.yaml` is not written. Version information is
    read from `git describe --tags --always` on the local clone at display time.
16. The absence of `pack-manifest.yaml` is not a validation error for `pack validate`
    (authors run validate before the manifest is written).

---

## Artifact ID Conventions

| Artifact type | File glob | ID field | Recommended prefix |
|---|---|---|---|
| Directives | `*.directive.yaml` | `id` | `<org>-<seq>-<slug>` |
| Tactics | `*.tactic.yaml` | `id` | `<org>-tac-<seq>` |
| Styleguides | `*.styleguide.yaml` | `id` | `<org>-sty-<seq>` |
| Toolguides | `*.toolguide.yaml` | `id` | `<org>-tg-<seq>` |
| Paradigms | `*.paradigm.yaml` | `id` | `<org>-par-<seq>` |
| Procedures | `*.procedure.yaml` | `id` | `<org>-proc-<seq>` |
| Agent profiles | `*.agent.yaml` | `id` | `<org>-<role>` |
| Mission step contracts | `*.contract.yaml` | `id` | `<org>-msc-<seq>` |

---

## Validation Errors vs. Warnings

| Condition | Classification |
|---|---|
| Artifact YAML fails schema validation | Error |
| Duplicate artifact ID within the pack | Error |
| Dangling DRG edge (URN not in merged artifact set) | Error |
| DRG extension attempts to modify/remove a shipped node | Error |
| Artifact ID collides with a shipped artifact ID | Advisory warning |
| DRG fragment files contain duplicate edges (identical source+target+relation) | Advisory warning |
| `pack-manifest.yaml` is present and author-modified | Advisory warning |
