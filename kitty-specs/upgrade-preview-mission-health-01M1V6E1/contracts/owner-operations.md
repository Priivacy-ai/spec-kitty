# Owner Assessment and Application Contract

Audience: agentic-framework-core-team. Updated: 2026-09-06.
Normative implementation contract for FR-001-004, C-001 and preservation.

## Small In-Process Seam

Introduce immutable stdlib-only values in tool_surface/operations.py; no imports
of registries, providers, runtime, upgrade, CLI or filesystem writers.
An owner exposes this structural contract (names may be idiomatically integrated
into its existing module; semantics are fixed):

```text
assess(inputs, provider_owned_statuses) -> OwnerAssessment
apply(OwnerAssessment, explicit_consent) -> OwnerApplyResult

OwnerAssessment:
  owner_key
  effects: tuple[PhysicalEffect, ...]
  dispositions: tuple[Disposition, ...]
  diagnostics: tuple[Diagnostic, ...]
  complete: bool
  inputs_fingerprint: immutable owner input observations
  prepared: opaque immutable owner payload (rendered bytes/manifest changes)
```

This is not a generic writer callback framework. Existing owners retain their
format-aware write/merge/atomic-save functions. They extract one decision/render/
compare path that both assess and apply use. Prepared data is never serialized
as an executable token. No generic snapshot-overlay filesystem or rollback API.

SurfacePlanBuilder remains the configured tool/definition/provider inventory.
Status collection preserves provider instance/hash/source/manifest context.
SurfaceRepairService dispatches owner assessments and application, rather than
reconstructing instances from findings. New assessment protocol is separate
from the reporting protocol so unrelated consumers do not acquire a new
mutation API accidentally; built-in upgrade providers must all implement it.
Missing support on a selected required provider is an explicit incomplete
assessment, never silently skipped. Registry is still the provider authority.

## Effect Semantics

Wire schema is upgrade-plan.schema.json. Every effect has one executable owner,
all affected logical owners/surface IDs, a root ID and normalized relative path.
Ownership reference is a manifest entry or an exact existing managed-path
contract; it cannot be a filename prefix. Paths from separate root aliases that
name the same physical destination are deduplicated without following hostile
links. Resolve configured roots once. Contradictory desired content for one
path is an owner conflict, not last-writer-wins.

| Action | Observable postcondition and independent snapshot normalization |
| --- | --- |
| create | Absent -> node present with declared final kind/mode; includes file bytes or link target where applicable |
| update | Existing regular file -> new bytes, with final mode if also changed |
| delete | Existing owned node -> absent; directory delete requires enumerated owned descendants and empty-directory check |
| replace | Node kind changes, notably managed link -> file copy; never follow link target |
| retarget | Existing owned symlink -> different literal target (only where existing delivery policy permits links) |
| chmod | Same node kind/content/target -> different permission bits |

Existing project skill delivery stays copies, not newly introduced symlinks.
File creation with its final mode is one create, not an extra chmod. For a
same-type file changing bytes and mode, update captures both. The oracle emits
this same independently specified net-delta normalization, not production
effect helpers. All added/removed directories are represented. Parent mtimes
changed incidentally by child creation are observed but not separate apply
operations; preview must leave them unchanged.

Only effects correspond to automatic writes in the assessed consent mode.
Unchanged/preserve/not_applicable/consent_required are dispositions, not effects.
A preview does not prompt. A real interactive drift approval triggers a fresh
owner assessment of that exact managed path; unknown custom paths cannot be
approved into ownership through this flow. --yes leaves drift dispositions.

Include persistent supporting paths: metadata, config, all manifests/refcounts,
version stamps, owned prune targets, backup files, copies, mode changes, and
staged plugin outputs only when selected policy actually repairs them.
Include persistent apply lock-file creation as infrastructure effects; transient
temporary/lock artifacts are reported separately as owner execution artifacts,
with concrete directory and bounded owner naming rule. They are permitted on
apply only, never in preview. No hidden persistent writes may be excluded as
"cache". No byte-level plan for Git's implementation internals is promised:
commit_policy describes existing churn commits, and Git state is verified
separately. Mission-state repair is never an effect in this plan.

## Owner Coverage and Dependencies

### Clock and Retained Backup Allocation

Persistent backup names must be state-derived, not wall-clock-derived. In the
managed-skill owner, use the existing backup parent with a versioned `state-`
name containing SHA-256 of a canonical, sorted encoding of replacement-relative
paths, observed kind/content hash/literal link target/mode and desired stable
replacement content/kind/mode. Do not include absolute fixture root, mtime,
clock or new manifest timestamps in that identity. Retain the original relative
layout inside the backup directory. This is a local concrete owner rule, not
a shared allocator service; it applies only to ownership-proven, consent-
permitted replacements. Existing timestamp-named backups remain untouched.

If the candidate backup directory already exists, preserve it regardless of
content and select the first absent numeric suffix in ascending order. Observe
candidate collisions and the selected absent path in the batch preconditions.
Creation is exclusive/no-clobber; a racing occupant causes conflict/reassessment,
never overwrite, merge or an unreported alternate name. Include the chosen
directory, descendants and final paths as persistent effects, never transient
execution artifacts. Equivalent filesystem states therefore choose the same
paths even when assessed on different dates.

For a changed/new manifest or metadata stamp, sample operation time once in
assessment and retain it in prepared data. Render the final bytes and hash there;
the owning save method must accept/consume that prepared result, not sample
now again. Existing non-upgrade callers may prepare immediately before saving
through the same owner seam. Unchanged content retains existing timestamps and
is not rewritten. Apply after the clock advances must write exactly the prepared
bytes or refuse changed preconditions; no silent rerender/time substitution.

Full-plan after.sha256 is exact for its invocation's prepared bytes, not a
cross-process replay promise. Independent preview/apply runs may have different
new installed_at/updated_at/last_upgraded_at values: the test oracle may compare
decoded, owner-declared newly assigned fields with those three names using one
sentinel, and recompute comparison digests from that narrow normalization.
One additional exact owner/path allowance: managed-skills root `/created_at`
in `.kittify/skills-manifest.json`, only when that manifest was absent in both
independent baselines and is newly created. Sample it from prepared operation
time and record the baseline-absence proof and exact JSON pointer. This is not
a general created_at ignore rule: pre-existing manifest creation times and
mission-meta/historical identity creation times remain exact.
Raw bytes/hashes and exact field locations remain evidence. Do not normalize
preexisting timestamps, paths, other fields, whole manifests or arbitrary text.
Persistent paths/actions/kinds/modes and all nonvolatile content must match
across runs. The per-invocation advancing-clock witness permits no normalization.

### Provisioning Authority

`src/charter/activation/compiler.py` retains missing-key/seed policy;
`pack_manager.py` retains pointer-aware target resolution and legacy round-trip
serialization; `charter_yaml_io.py` retains validated section-only rendering.
IC-07 extracts pure preparation in those exact files and routes the existing
writer through the prepared bytes. Returned charter values are lower-layer
bytes, projected activation data and source observations, not PhysicalEffect.
The upgrade adapter wraps them and rechecks both pointer/config and target
observations before delegating apply. No upward charter import, duplicate YAML
serializer in upgrade, write interception as production preview, or same-version
incomplete escape for an ordinary missing key. Explicit empty lists stay empty;
dangling/unreadable pointers fail rather than fall back to legacy config.

| Owner | Required assessment coverage |
| --- | --- |
| Runtime bootstrap | Existing package managed-path set, absent/stale runtime, safe removals, version stamps and directories; preserve custom runtime data |
| Global skills/commands | Existing catalog/templates, health and retired-managed checks even with current markers, whole-agent bundle, permissions and stamps |
| Command skills | Full canonical command batch, source resolution, sharing/refcounts, command manifest, exact collision/drift checks |
| Managed skills | Selected catalog/activation, project copies, safe managed-link conversion, backups where existing policy permits, skills manifest, global preparation delegated to runtime |
| Profiles | Admission/projection, missing/stale output, exact manifest, orphan pruning including paths absent from expanded statuses; preserve drift |
| Native/session | Existing writer-managed sections/config entries, orientation, rules and hooks; preserve unrelated text/JSON keys |
| Plugin bundles | Existing applicable staged repair only, complete staged output and manifest; never new automatic plugin installation |
| Upgrade metadata/provisioning | Existing stamps and missing-key provisioning, preserve intentional empty activations and unknown config keys |

Missing manifests with retained files: canonical rendered-byte equality may
establish safe adoption only through the installer's existing explicit content
contract; record that proof. Any nonmatching unowned content is preserve/conflict.
Never create a placeholder hash of arbitrary disk content and then treat it as
managed on the subsequent install. Unknown custom symlinks survive, including
names beginning spec-kitty.; only exact ownership permits unlinking.
Proven managed but edited prune targets remain drift/consent-required.

Use configured agents exactly; malformed config is incomplete/blocked, not
all-known-tools fallback. Preserve required/disabled/advisory policies, profile
activation, Amazon Q's user-global exception and shared-root owners.

Phase composition takes concrete projected config/manifest values when
provisioning/normalization precedes status assessment. Source lookup can use the
installed package's canonical templates on an empty home; never bootstrap to
discover them. If an input cannot be read/projected, report incomplete with its
owner/reason. Do not silently substitute an unrelated source or infer no work.

Opaque historical migration file lists stay null in their existing migration
contract. Mark subsequent dependent assessment incomplete rather than invent
an all-files list. Preserve existing migration apply and then reassess actual
state before repair. Known independent effects may be reported; incomplete
ones cannot execute by replaying the report. Same-version plans must be complete.

## Preconditions, Consent and Failure

An owner observes content/type/mode/mtime, manifest/config source hashes,
activation/catalog identity and source template hashes needed for its batch.
Before writing, acquire existing lock where available and recheck the whole
batch, including parent confinement without following escaping links. A changed
source, replaced symlink parent or changed target stops the batch before writes,
with precondition_changed. A deliberate re-run reassesses; no automatic force.

Do not weaken command installer's collision checks or shared remove refcounts.
Preserve user regions in mixed files. Avoid empty manifest/timestamp rewrites
and redundant chmod so same-version second apply has zero persistent churn.

Known drift does not prevent independent missing-file automatic repair, but
remains surfaced and preserves current noninteractive unresolved-drift failure.
Corrupt required state/source blocks that owner before mutation; no catch-to-empty
success. Unexpected I/O failure may occur after partial writes: report actual
IDs and error, persist only valid manifest changes, do not emit success for all
requested IDs. Existing finalizer derives the final apply outcome; do not invent
a second command exit formula. Mission repair failure remains independently
reported and retains its existing non-fatal upgrade outcome semantics.

## Architectural Guard

Add a narrow AST/import gate over concrete upgrade assessment functions and
startup integration. A floor must assert the real CLI entry, phase composer
and all selected built-in assessment owners are covered; a missing registry
provider cannot reduce coverage silently. Reject direct writer/ensure/persistence
calls from assessment bodies and require the named apply boundary.
Self-mutation fixtures restore an unconditional root ensure and insert a
manifest save in an assessment; both must fail the gate. Do not rely on this
syntactic guard for transitive safety: public subprocess snapshots and
write-interception controls in acceptance.md remain mandatory.
