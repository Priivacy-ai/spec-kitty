# Research: Layered Doctrine Resolution — Org Layer

**Phase 0 output** | Mission: `layered-doctrine-org-layer-01KRNPEE` | Date: 2026-05-15

---

## 1. Multi-file DRG loading strategy

### Decision
Introduce `load_graph_or_dir(path: Path) -> DRGGraph` in `src/doctrine/drg/loader.py`.
If `path` is a file, delegate to the existing `load_graph(path)`. If `path` is a directory,
glob `*.graph.yaml` in alphabetical order, call `load_graph()` on each, and reduce with
`merge_layers()`. The result is a single `DRGGraph` before any cross-layer merge happens.

The existing `load_graph()` function is unchanged. All callers that currently reference
`path / "graph.yaml"` directly are updated to call `load_graph_or_dir(path)` instead,
where `path` is the directory root. This means the convention shifts from "always
`graph.yaml`" to "either `graph.yaml` or a `drg/` fragment directory at the same root".

### Rationale
- Single entry point replaces twelve scattered `path / "graph.yaml"` constructions
- No breaking change: a root containing only `graph.yaml` behaves identically to today
- Fragment merging at load time keeps the cross-layer `merge_layers()` signature unchanged
- Enables the shipped graph to be split into domain files without regressions elsewhere

### Alternatives considered
- **Separate `load_graph_dir()` + unchanged callers**: more callers to update; the
  single-entry-point approach is cleaner and reduces the surface for future drift
- **Directory-only convention (deprecate single file)**: too disruptive; single-file support
  must be retained for the project overlay which will typically remain one file

### Caller update map

| File | Line(s) | Change |
|---|---|---|
| `src/charter/_drg_helpers.py` | 34–35 | Route through new `load_validated_graph()` (see §2) |
| `src/charter/context.py` | 228–229 | Route through `_drg_helpers.load_validated_graph()` |
| `src/charter/compiler.py` | 489 | Use `load_graph_or_dir` |
| `src/charter/reference_resolver.py` | 38 | Use `load_graph_or_dir` |
| `src/charter/synthesizer/validation_gate.py` | 61 | Use `load_graph_or_dir` |
| `src/charter/synthesizer/project_drg.py` | 240 | Use `load_graph_or_dir` |
| `src/charter/synthesizer/resynthesize_pipeline.py` | 450, 547 | Use `load_graph_or_dir` |
| `src/charter/synthesizer/write_pipeline.py` | 516 | Use `load_graph_or_dir` |

---

## 2. Three-layer merge at `_drg_helpers.py`

### Decision
`load_validated_graph(repo_root: Path, org_root: Path | None = None) -> DRGGraph`

```
shipped = load_graph_or_dir(doctrine_root)
org     = load_graph_or_dir(org_root / "drg") if org_root and (org_root / "drg").exists()
          else load_graph_or_dir(org_root / "graph-extensions.yaml") if that exists
          else None
project = load_graph_or_dir(project_dir) if project_dir.exists() else None

merged  = merge_layers(merge_layers(shipped, org), project)
assert_valid(merged)
```

Org-layer graph extensions are **additive only**: `merge_layers()` already implements this
(new nodes and edges added; existing shipped nodes get label override only; edges are
concatenated). No change to `merge_layers()` semantics is needed.

`org_root` is resolved from `DoctrineOrgConfig.local_path`. Callers that do not have an
org root (context.py, compiler.py) obtain it via a shared `_resolve_org_root(repo_root)`
helper in the same module, which reads `config.yaml` and returns `None` if unconfigured.

### Rationale
- Least-change approach: `merge_layers()` is already correct for additive semantics
- `_drg_helpers.py` becomes the single authoritative DRG assembly point for all non-
  synthesizer paths; synthesizer paths use `load_graph_or_dir` directly (they build graphs
  incrementally and don't need the full three-layer merge at each step)

---

## 3. OrgDoctrineSource protocol and authentication

### Decision
`OrgDoctrineSource` is a Python `Protocol` (structural typing, not ABC inheritance).
Each implementation exposes a single method:

```python
def fetch(self, target_dir: Path) -> FetchResult: ...
```

`FetchResult` is a dataclass: `{ ok: bool, artifacts_written: int, pack_version: str | None, errors: list[str] }`.

**`GitSource` is a persistent clone manager, not a one-shot copier.** On first fetch, it
runs `git clone <url> <target_dir>`, preserving `.git/`. On subsequent fetches it runs
`git -C <target_dir> fetch --tags` followed by `git reset --hard <ref>` (deterministic
regardless of local changes). Version is read from `git describe --tags --always`. This
means `target_dir` IS the working repository — `pack-manifest.yaml` is not written for
git sources; git metadata serves that purpose.

**`HttpsBundleSource` and `ApiSource`** write atomically to `target_dir` (temp dir →
validate → rename). They are not git repositories; `pack-manifest.yaml` is written after
the rename succeeds.

**Authentication** uses system-native mechanisms only — no spec-kitty-managed credential
storage in this mission:

| Source type | Auth mechanism |
|---|---|
| `GitSource` | SSH keys via `~/.ssh/`; HTTPS PAT via git credential helper or `GIT_TOKEN` env var |
| `HttpsBundleSource` | Bearer token via `SPEC_KITTY_ORG_TOKEN` env var; or no-auth for public bundles |
| `ApiSource` | Bearer token via `SPEC_KITTY_ORG_TOKEN` env var; or custom header via `SPEC_KITTY_ORG_AUTH_HEADER` |

Rationale: system-native auth keeps the implementation simple, avoids spec-kitty becoming
a secrets store, and follows the pattern established by other spec-kitty commands that
delegate to git for VCS operations.

### Alternatives considered
- **Python ABC over Protocol**: Protocol is preferred because implementations don't need to
  inherit from a base class — any object with a matching `fetch()` signature works. Easier
  for third-party source implementations.
- **Shallow clone + copy (discard .git)**: Rejected — discarding `.git` loses governance
  history and makes `git describe` unavailable. The working tree IS the value for git packs.
- **Credential storage in `.kittify/config.yaml`**: Rejected — credentials should not be in
  a config file that may be committed. Environment variables are the correct surface.

---

## 4. Config schema for `doctrine.org`

### Decision
Extend `.kittify/config.yaml` with an optional `doctrine.org.packs` list. Each entry is a
named pack with its own source and local path:

```yaml
doctrine:
  org:
    packs:
      - name: security
        local_path: "~/.kittify/org/security/"
        source_type: git
        url: "git@example.com:security/doctrine.git"
        ref: "v2.1.0"           # optional; HEAD of default branch if omitted
      - name: architecture
        local_path: "~/.kittify/org/architecture/"
        source_type: git
        url: "git@example.com:architecture/doctrine.git"
      - name: compliance
        local_path: "~/.kittify/org/compliance/"
        source_type: api
        url: "https://governance.example.com/compliance/v1"
```

`local_path` is the only field required for resolution. `source_type` + `url` are required
only for `doctrine fetch`. A machine where IT pre-clones the repositories needs only the
`local_path` entries; the source fields may be omitted.

**Backward compat**: a single `doctrine.org.local_path` (no `packs` list) is accepted and
treated as a single anonymous pack for forward compatibility with any existing config.

**Declaration order = precedence**: later packs in the list have higher precedence within
the org layer. An advisory warning is emitted when two packs define the same artifact ID.

The `OrgPackConfig` Pydantic model validates each entry. `PackRegistry` is the list model.
Path expansion (`~`) is resolved at load time for `local_path`.

### Rationale
- Multi-pack support without a single point of coordination: each team manages their
  repository independently; the config lists them all in precedence order.
- Backward-compatible: existing single-`local_path` configs keep working.
- Decouples "where the pack lives locally" from "how it is fetched" — consistent for both
  git clones (managed by `GitSource`) and non-git snapshots.

---

## 5. `pack assemble` conflict detection and reporting

### Decision
`pack assemble` detects conflicts at two levels:

1. **Artifact ID collision across input packs**: two packs both define artifact with the
   same ID. Reported as an error with the conflicting artifact ID and both source pack paths.
   The command exits non-zero without writing output.

2. **DRG edge conflict** (target URN not present in any merged layer): reported as an error
   with the dangling edge and the pack that introduced it. The command exits non-zero.

Conflict output is written to stdout (human-readable) and optionally to a JSON file via
`--conflicts-out <path>` for CI pipeline consumption.

The operator resolves conflicts by:
- Removing one pack from the assembly manifest, or
- Adding an explicit override artifact in the distributable's own layer

### Alternatives considered
- **Last-writer-wins (no error)**: rejected — silent override of one pack by another
  produces unpredictable governance for consumers; explicit resolution is required
- **Merge metadata from conflicting artifacts**: rejected — the full-replace semantics
  of the layer model must apply consistently; partial merge would be a special case

---

## 6. Provenance tag shape in `charter context --json`

### Decision
The existing `charter context --json` output adds a `"source"` field to each artifact
entry in the JSON response:

```json
{
  "directives": [
    { "id": "sec-001", "source": "org", "title": "..." },
    { "id": "DIR-001", "source": "shipped", "title": "..." },
    { "id": "PRJ-001", "source": "project", "title": "..." }
  ]
}
```

Source values: `"shipped"` | `"org"` | `"project"`.

The `DoctrineService` tracks provenance at load time by tagging artifacts during
`_apply_org_overrides()` and `_apply_project_overrides()`. A parallel `dict[str, str]`
(artifact_id → source) per repository provides O(1) lookup at serialisation time.

The human-readable `charter context` (non-JSON) output is unchanged — source attribution
is JSON-only to avoid cluttering the existing terminal output.

### Alternatives considered
- **Provenance in the artifact YAML itself**: rejected — provenance is a runtime property
  of the resolution, not a property of the artifact definition
- **Provenance in the non-JSON output**: deferred — the terminal format is consumed by
  agents; changing it risks regressions in agent parsing. JSON is the safe surface.

---

## 7. `spec-kitty doctor` org-layer listing surface

### Decision
Add a `spec-kitty doctor doctrine` subcommand (consistent with the existing
`doctor command-files`, `doctor identity`, etc. pattern):

```
spec-kitty doctor doctrine
spec-kitty doctor doctrine --json
```

Output shows:
- Whether an org doctrine snapshot is configured and present
- Snapshot path and pack version (read from `pack-manifest.yaml` written by `doctrine fetch`)
- Artifact counts by type across all three layers
- Any validation warnings from the snapshot

If no snapshot is configured: a diagnostic message (not an error) advising the operator
to run `doctrine fetch` or check `config.yaml`.

### Rationale
Consistent with existing `doctor` subcommand surface; keeps the main `doctor` invocation
lean while providing a focused diagnostic for doctrine-layer issues.

---

## 8. `charter lint` advisory warning placement

### Decision
The existing `charter lint` command gains one new check: **org-overrides-shipped warning**.

When the merged doctrine set contains any artifact whose ID exists in both shipped and
org layers (i.e., the org layer fully replaced a shipped artifact), `charter lint` emits:

```
ADVISORY  org layer overrides shipped artifact 'DIR-003' (sec-002-branding.directive.yaml)
```

This is classified as `ADVISORY` (not `WARNING` or `ERROR`) so it never blocks CI. The
`--strict` flag, if added in a future mission, could promote advisories to warnings.

The check is implemented in the existing lint check registry by adding a
`OrgOverridesShippedCheck` that reads provenance metadata from `DoctrineService`.

### Alternatives considered
- **Hard error on override**: rejected per spec C-003 — organisations need to be able to
  override shipped artifacts; it should be visible, not blocked
- **Separate `charter lint org`**: rejected — the advisory fits naturally in the existing
  lint run; a separate subcommand adds friction
