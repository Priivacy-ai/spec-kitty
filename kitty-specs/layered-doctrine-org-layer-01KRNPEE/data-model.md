# Data Model: Layered Doctrine Resolution — Org Layer

**Phase 1 output** | Mission: `layered-doctrine-org-layer-01KRNPEE` | Date: 2026-05-15

---

## 1. Resolution Layer Model

### DoctrineLayers (enum)

| Value | Description | Root location |
|---|---|---|
| `shipped` | Bundled with the CLI; read-only | `site-packages/doctrine/` (resolved via `resolve_doctrine_root()`) |
| `org` | Installed per developer machine; operator-managed | `config.doctrine.org.local_path` |
| `project` | Per-project local overrides; developer-managed | `.kittify/doctrine/` |

**Merge precedence**: `shipped < org < project`. Higher layer fully replaces lower layer on
artifact ID collision. No field-level merging across layers.

**Fallback**: if org layer is absent (unconfigured or snapshot missing), resolution falls
back silently to shipped + project. A `spec-kitty doctor doctrine` diagnostic is surfaced
but no error is raised in normal operation.

---

## 2. DoctrineOrgConfig (config model)

Pydantic model serialised to/from `.kittify/config.yaml` under the `doctrine.org` key.

| Field | Type | Required | Description |
|---|---|---|---|
| `local_path` | `Path` | **Yes** | Path to the local snapshot directory. `~` is expanded. |
| `source_type` | `Literal["git", "https", "api"] \| None` | No | Source type for `doctrine fetch`. Absent on machines where IT provisions the snapshot directly. |
| `url` | `str \| None` | No | Remote URL; required if `source_type` is set. |
| `ref` | `str \| None` | No | Version pin (git tag/SHA, tarball filename, API version). If absent, fetch pulls latest. |

**Config.yaml shape** (under existing top-level keys):

```yaml
doctrine:
  org:
    local_path: "~/.kittify/org/acme-corp/"
    source_type: git
    url: "git@internal.example.com:platform/org-doctrine-distributable.git"
    ref: "v1.2.0"
```

`local_path` only (IT-provisioned snapshot, no fetch config):

```yaml
doctrine:
  org:
    local_path: "/opt/company/org-doctrine/"
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

Each repository maintains a parallel `_provenance: dict[str, DoctrineLayers]` keyed by
artifact ID. This dict is populated during `_load()`:

- Shipped artifacts → `DoctrineLayers.shipped`
- Org overrides or new org artifacts → `DoctrineLayers.org`
- Project overrides or new project artifacts → `DoctrineLayers.project`

`DoctrineService` exposes a `get_provenance(artifact_type: str, artifact_id: str) -> DoctrineLayers | None` method for callers that need source attribution (context serialisation, doctor, lint).

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
