# Data Model: Layered Doctrine Resolution — Org Layer

**Phase 1 output** | Mission: `layered-doctrine-org-layer-01KRNPEE` | Date: 2026-05-15

---

## 1. Resolution Layer Model

### DoctrineLayers (enum)

| Value | Display name | Description | Root location |
|---|---|---|---|
| `builtin` | spec-kitty built-in | Bundled with the CLI; read-only | `site-packages/doctrine/` (resolved via `resolve_doctrine_root()`) |
| `org` | org / `<pack-name>` | Installed per developer machine; operator-managed; one or more named packs | `local_path` per pack in `doctrine.org.packs` |
| `project` | project | Per-project local overrides; developer-managed | `.kittify/doctrine/` |

**Merge precedence**: `builtin < org (packs in declaration order) < project`. Higher layer
takes ownership of the resolved artifact on ID collision; its `provenance` becomes that
layer. **Field-level merge applies**: fields present in the higher layer's YAML replace
same-named fields in the lower layer; fields absent from the higher layer fall through.
No two artifacts with the same ID coexist across layers — the higher layer's identity wins.
The resolver emits a `DoctrineLayerCollisionWarning` each time a higher layer shadows a
lower-layer artifact, with the artifact ID, source and target layers, and the count of
replaced fields. See ADR `architecture/2.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`.

**Fallback**: if no org packs are configured or no local paths exist on disk, resolution
falls back silently to builtin + project. A `spec-kitty doctor doctrine` diagnostic is
surfaced but no error is raised in normal operation. Projects with no `doctrine.org.packs`
config are completely unaffected by this feature.

---

## 2. Config Models

### OrgPackConfig

Pydantic model for a single named pack entry.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | **Yes** | Unique name for this pack (used by `--pack` flag and `doctor doctrine` display). |
| `local_path` | `Path` | **Yes** | Path to the local clone (git) or snapshot directory (non-git). `~` is expanded. |
| `source_type` | `Literal["git", "https", "api"] \| None` | No | Source type for `doctrine fetch`. Omit when pack is IT-provisioned. |
| `url` | `str \| None` | No | Remote URL; required if `source_type` is set. |
| `ref` | `str \| None` | No | Version pin (git tag/SHA, tarball filename, API version). Defaults to HEAD/latest. |

### PackRegistry

Ordered list of `OrgPackConfig`. Declaration order = precedence (later = higher). Maps to
`.kittify/config.yaml` under `doctrine.org.packs`.

**Multi-pack config example**:

```yaml
doctrine:
  org:
    packs:
      - name: security
        local_path: "~/.kittify/org/security/"
        source_type: git
        url: "git@example.com:security/doctrine.git"
        ref: "v2.1.0"
      - name: architecture
        local_path: "~/.kittify/org/architecture/"
        source_type: git
        url: "git@example.com:architecture/doctrine.git"
      - name: compliance
        local_path: "~/.kittify/org/compliance/"
        source_type: api
        url: "https://governance.example.com/compliance/v1"
```

**IT-provisioned clone (no fetch config)**:

```yaml
doctrine:
  org:
    packs:
      - name: org-doctrine
        local_path: "/opt/company/org-doctrine/"
```

**Backward-compat single-`local_path` form** (treated as one anonymous pack):

```yaml
doctrine:
  org:
    local_path: "~/.kittify/org/acme-corp/"
```

---

## 3. OrgDoctrineSource (fetch-time protocol)

Structural protocol (`typing.Protocol`). Any object satisfying this interface can act as a
fetch source. Spec-kitty ships three implementations; third parties may add others.

```
OrgDoctrineSource
  fetch(target_dir: Path) -> FetchResult
```

**FetchResult** (dataclass):

| Field | Type | Description |
|---|---|---|
| `ok` | `bool` | True if all artifacts were written successfully |
| `artifacts_written` | `int` | Number of artifact files written to `target_dir` |
| `pack_version` | `str \| None` | Version string from the source (tag, commit SHA, API version) |
| `errors` | `list[str]` | Error messages for any artifact that failed to fetch |

**Concrete implementations**:

| Class | Mechanism | Auth |
|---|---|---|
| `GitSource` | Shallow clone / pull via `git` subprocess | SSH keys or `GIT_TOKEN` env var |
| `HttpsBundleSource` | Download tarball via `requests`; extract to `target_dir` | `SPEC_KITTY_ORG_TOKEN` env var (bearer) |
| `ApiSource` | `GET` per artifact type to API endpoints; reconstruct pack layout | `SPEC_KITTY_ORG_TOKEN` env var (bearer) or `SPEC_KITTY_ORG_AUTH_HEADER` |

All implementations:
- Validate the fetched content against the schema before writing to `target_dir`
- Write atomically (write to a temp dir, then rename) so a failed fetch never corrupts
  an existing valid snapshot
- Write a `pack-manifest.yaml` at the root of `target_dir` containing pack version, fetch
  timestamp, and source URL (redacted of credentials)

---

## 4. OrgDoctrinePack (directory layout)

The canonical layout that all fetch sources must produce and that `pack validate` checks.
See [contracts/pack-layout.md](contracts/pack-layout.md) for the normative specification.

```
<pack-root>/
├── pack-manifest.yaml          ← written by doctrine fetch (version, timestamp, source)
├── directives/
│   └── *.directive.yaml
├── tactics/
│   └── *.tactic.yaml
├── styleguides/
│   └── *.styleguide.yaml
├── toolguides/
│   └── *.toolguide.yaml
├── paradigms/
│   └── *.paradigm.yaml
├── procedures/
│   └── *.procedure.yaml
├── agent_profiles/
│   └── *.agent.yaml
├── mission_step_contracts/
│   └── *.contract.yaml
└── drg/                        ← optional; contains graph extension fragments
    └── *.graph.yaml            ← additive DRG nodes and edges only
```

**Rules**:
- All artifact subdirectories are optional. A pack that only contains `directives/` is valid.
- The `drg/` directory is optional. If absent, the org layer contributes no DRG extensions.
- `pack-manifest.yaml` is written by `doctrine fetch`; pack authors do not create it manually.
- Artifact files must conform to their respective spec-kitty YAML schema.
- DRG graph fragments in `drg/` must not reference artifact URNs that don't exist in the
  merged shipped + org artifact set (validated by `pack validate`).

---

## 5. PackManifest (written by doctrine fetch)

```yaml
pack_version: "v1.2.0"           # tag / SHA / "api-v2" / etc.
fetched_at: "2026-05-15T11:30:00Z"
source_type: git
source_url: "git@internal.example.com:platform/org-doctrine-distributable.git"
artifact_counts:
  directives: 12
  tactics: 4
  agent_profiles: 8
  toolguides: 3
```

`spec-kitty doctor doctrine` reads this file to display version and counts without
re-loading all artifacts.

---

## 6. Three-Layer Repository Merge Invariants

The following invariants must hold after any `_load()` call on a three-layer repository.

| Invariant | Description |
|---|---|
| **Higher wins** | For any artifact ID present in multiple layers, only the highest layer's artifact is in `_items` |
| **Shipped completeness** | All shipped artifacts are present in the final set unless overridden by a higher layer |
| **No phantom org artifacts** | An org artifact whose ID is new (not in shipped) is present in `_items` |
| **No phantom project artifacts** | A project artifact whose ID is new (not in shipped or org) is present in `_items` |
| **Skipped-bad-file resilience** | A single malformed artifact file in any layer does not prevent valid artifacts in the same layer from loading |
| **Language-scope preserved** | `_include_item()` is applied after merge; an org artifact that does not apply to the active language set is excluded |

Property tests (hypothesis) will verify these invariants against randomly generated three-layer artifact sets.

---

## 7. Provenance Tracking Model

Each repository maintains a parallel `_provenance: dict[str, str]` keyed by artifact ID.
Values use the machine-readable layer tag. This dict is populated during `_load()`:

- Built-in artifacts → `"builtin"`
- Org overrides or new org artifacts → `"org"` (all packs share the `"org"` tag in context
  output; `doctor doctrine` shows which pack via the pack name separately)
- Project overrides or new project artifacts → `"project"`

`DoctrineService` exposes a `get_provenance(artifact_type: str, artifact_id: str) -> str | None`
method for callers that need source attribution (context serialisation, doctor, lint).

The `charter context --json` `"source"` field uses these machine-readable values: `"builtin"`,
`"org"`, `"project"`. The human display in `doctor doctrine` maps `"builtin"` to
`"spec-kitty built-in"` and org artifacts to `"org / <pack-name>"`.

---

## 8. State transitions for `doctrine fetch`

```
fetch invoked
    ↓
source resolved from config
    ↓
credentials resolved from environment
    ↓
FetchResult ← source.fetch(temp_dir)
    ↓
[ok=False?] → report errors, exit non-zero; existing snapshot unchanged
    ↓
validate temp_dir against schema
    ↓
[validation fails?] → report errors, exit non-zero; existing snapshot unchanged
    ↓
atomic rename: temp_dir → local_path
    ↓
write pack-manifest.yaml
    ↓
report success
```

**Atomicity guarantee**: the existing snapshot is never overwritten unless validation passes.
This is the only write operation during `doctrine fetch`.
