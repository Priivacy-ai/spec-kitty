# Internal Contract: Activated Mission Template Resolution

## Purpose

Define the internal boundary used by content-template readers to resolve an artifact template without duplicating doctrine configuration or changing file override precedence. This is a Python module contract, not a public network API.

## Inputs

- Activated/resolved mission-type context.
- Requested artifact kind, initially `spec` or `plan`.
- Existing project/user/package resolution context required by the file resolver.

## Successful Result

The contract returns the same effective file representation already consumed by the caller after:

1. Reading the requested filename from `ResolvedMissionType.template_set`.
2. Passing that filename to the existing five-tier resolver for the active mission type.

The contract MUST NOT hard-code `software-dev-default`, manufacture `spec-template.md` or `plan-template.md`, or read a profile-level default string as mapping authority.

## Failure Results

| Failure | Required diagnostic context | Forbidden behavior |
|---|---|---|
| Resolved mapping is null | Mission-type ID and artifact kind | Borrow another mission type's template |
| Artifact key is absent | Mission-type ID and artifact kind | Substitute a conventional filename |
| Mapped filename cannot resolve | Mission-type ID, artifact kind, and mapped filename where safe | Create an empty artifact or silently continue |
| Mission type is not activated/available | Requested mission-type identity | Load it merely because an artifact exists on disk |
| Resolved context is neutral/typeless | Neutral identity and artifact kind | Infer software-development inside the configured-template seam |

The concrete API may represent failure as a typed exception or explicit unavailable result, matching the caller boundary, but CLI-facing paths must render an actionable message.

## File Precedence Compatibility

Once a filename is selected, the resolver MUST retain the established five-tier precedence unchanged. A project-level or user-level override that won before this mission must still win for the mapped filename. The mapping selects *what filename* to look for; it does not select *which copy* wins.

## Determinism and Performance

- Repeated resolution for the same activated mission type, artifact kind, and configuration returns the same mapping content and effective winner.
- Resolved mission-type context construction remains within the existing 100 ms typical-local-project budget.
- Mapping access follows existing lazy/cached context behavior; readers do not rescan doctrine artifacts independently.

## Compatibility Boundary

Known activated mission types follow this contract and fail closed for absent configuration. The configured-template seam rejects a neutral/typeless context with `TemplateConfigurationError`. A production reader that already supports a typeless legacy mission must route that case through its unchanged explicit compatibility boundary before calling the new seam; known activated types never enter that branch. Issue #2660 owns retirement of the compatibility branch.

## Verification Contract

- Doctrine/context tests assert exact mappings and explicit nulls for all built-in activated types.
- Reader-path tests cover `spec` mission creation and `plan` setup/pristine comparison.
- Integration behavior proves permitted overrides still win.
- Missing mapping, missing key, and unresolved filename never select software-development content.
- A temporary parity scaffold proves exact shipped software-development outcomes during migration and is absent from the merge-ready tree.
