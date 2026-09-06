# Domain Model

Audience: agentic-framework-core-team. Updated: 2026-09-06.

| Concept | Meaning | Authority / Invariant |
| --- | --- | --- |
| Upgrade intent | Preview/apply, project/CLI, target and worktree selection | One interpretation before startup writes |
| Compatibility verdict | Installed/project schema and invocation compatibility | Existing compat planner; not a write manifest |
| Target validity | Current-to-requested version policy | Existing version validator, not lexical ordering |
| Repair assessment | Ordered owner-produced intended operations and conflicts | Existing provider/installer authority; no duplicate path catalog |
| Physical effect | Scope, path, operation, reason, ownership and preconditions | Deduplicate shared paths without dropping owners |
| Managed surface | Runtime/command/skill/profile/config/manifest | Exact ownership proof; unknown customizations preserved |
| Mission identity | Historical immutable ID and creation context | Recover original evidence, never generate replacement for known mission |
| Event history | Authoritative transitions, annotations and review evidence | Byte-preserve in scoped snapshot repair |
| Snapshot | Materialized mission/WP state | Canonical replay, with review/provenance preserved |

Assessment precedes mutation. Human and JSON are projections of assessment;
neither renderer invents policy. Application rechecks ownership/preconditions.
Mission-state repair is a separate consent boundary, not a repair-plan side effect.

## Implementation Values

These are planned in-process values, not implemented classes or a persistent
transaction protocol. Wire names are frozen in contracts/upgrade-plan.schema.json.

| Value | Fields / responsibility |
| --- | --- |
| UpgradeIntent | mode (preview/apply/guidance), representation (human/legacy/full/outcome), project, target, include_worktrees, confirm; one parse-only interpretation |
| TargetValidation | current, requested, relation (lower/equal/higher/unknown/invalid), valid, reason; existing validator owns PEP 440 |
| FileState | kind (absent/file/directory/symlink), file sha256, literal link target, mode; mtime_ns retained internally for precondition checks |
| PhysicalEffect | ID, phase, owner, logical owners/surface IDs, root, relative path, action, before/after, reason, ownership proof |
| Disposition | owner, root/path if applicable, unchanged/preserve/consent_required/not_applicable, reason; not a promised write |
| OwnerAssessment | owner, effects, dispositions, diagnostics, complete, opaque prepared data, input fingerprints |
| UpgradeAssessment | intent, target, compatibility, owner assessments, migrations, completeness, decision, diagnostics, commit policy |
| OwnerApplyResult | actual succeeded/failed/skipped IDs and diagnostics; truthful partial outcome |
| PreparedActivation | Charter-owned target, projected activation values, rendered bytes and source/pointer observations; upgrade adapter creates PhysicalEffect without upward imports |
| PreparedTime | Once-sampled operation time used only for newly changed manifest/stamp fields; retained in prepared bytes, never resampled by apply |
| BackupAllocation | Concrete state-derived path plus collision/absence observations; owner-local, persistent and no-clobber; never clock-derived or normalized away |

## Invariants and Flow

1. Assessment/serialization performs no filesystem writes, network, persistence,
   prompts or implicit installs. Application is a separate operation.
2. Root identity comes from existing resolvers. Paths are normalized relative
   paths; no absolute or parent traversal segments. Never follow an untrusted
   link to establish confinement or ownership. Shared paths have one writer
   retaining all logical owners and manifest refcounts.
3. Equal bytes/type/mode imply no persistent effect. Unchanged manifests retain
   timestamps; mtimes detect intervening changes but never prove ownership.
4. Parent directory creation is explicit. File creation includes final mode.
   Existing-file mode-only changes are chmod; symlink-to-copy conversion is
   replace, never a write to its target. Wire normalization is in the owner contract.
5. Recheck sources/config/manifests and destination preconditions for the whole
   owner batch before its first write. Conflict stops that batch; --yes is not
   a recheck bypass. Existing atomic writes/locks stay; no global rollback claim.
6. Missing/corrupt required sources/config do not become empty success.
   Unknown ownership is preserve, not manifest adoption. Optional unsupported
   surfaces remain dispositions rather than blockers for unrelated work.
7. Target validity and compatibility are independent. Migration count is neither.
   Unknown current version does not justify fabricating known metadata.
8. Complete means all selected generated/supporting effects are known.
   Opaque migration-dependent effects mark completeness false; same-version
   fixtures require true. Empty effects with false completeness is not no work.
9. Preview describes consent-required drift without consuming consent.
   --yes does not authorize drift overwrite or mission-state repair.
10. Full-plan JSON is a report, never an apply token or new remote API.
11. Within one assessment/apply invocation, prepared after hashes are exact even
    if the clock advances. Across independent invocations only newly assigned
    installed_at/updated_at/last_upgraded_at fields, plus root `/created_at` in
    a newly created `.kittify/skills-manifest.json` absent in both baselines,
    may differ under the narrow owner-contract oracle rule. No other created_at
    allowance; existing manifest/mission identity times remain exact. Raw hashes,
    per-invocation exact bytes and unchanged mtimes remain required.
    Paths/actions and all other content must agree.
12. Charter target/key/section-render authority stays in charter.activation.
    Pure preparation and the existing writer share bytes/policy; explicitly
    empty activations are not missing, and dangling pointers are not fallback.

```text
intent -> target + compatibility -> owner assessment
  preview -> report complete / blocked / incomplete -> no writes
  apply -> permitted automatic work -> batch recheck -> existing writers
           conflict/error -> report actual outcome, never silent retry
           migration changed inputs -> reassess dependent repair phase
finalizer -> optional independent mission-state consent gate
```

Conflicts may coexist with known missing-file repairs. A required unreadable
config/manifest/source prevents its owner batch, not a fallback to all agents.
Event logs remain byte-identical during snapshot remediation; original eight
done lanes and review_result objects survive canonical annotation projection.
