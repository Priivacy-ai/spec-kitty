# Architecture

This directory is the canonical architecture corpus for Spec Kitty.

## Structure

| Path | Purpose |
|---|---|
| `architecture/1.x/` | Legacy architecture track (1.x), including 1.x ADRs |
| `architecture/2.x/` | Prior architecture track (2.x), captures the 2.x → 3.x cutover |
| `architecture/3.x/` | Current architecture track (3.x), starting with the 3.0.0 release (2026-03-30) |
| `architecture/audience/` | Persona catalog for architecture audiences and actor links |
| `architecture/glossary/` | Architecture-level glossary landing page and pointers |
| `architecture/adrs/` | Backward-compatibility links to moved 1.x ADR files (legacy compat shim) |
| `architecture/adr-template.md` | Shared ADR template used by all tracks |

## Versioned ADR Locations

- 1.x ADRs: `architecture/1.x/adr/`
- 2.x ADRs: `architecture/2.x/adr/` (pre-3.0 dates only; 3.x-era moves live under `3.x/`)
- 3.x ADRs: `architecture/3.x/adr/` (canonical for the current track)
- Legacy 1.x path compatibility: `architecture/adrs/` (symlink aliases)
- 2.x → 3.x move compatibility: each moved ADR retains a symlink at its old `architecture/2.x/adr/<filename>` path pointing into `architecture/3.x/adr/`, so CHANGELOG entries, test snapshots, and shipped docs that reference the old path continue to resolve.

## 2.x Architecture Model

2.x architecture docs are split intentionally:

1. `architecture/2.x/README.md#domain-breakdown` - cross-cutting responsibility and behavior domains.
2. `architecture/2.x/01_context/README.md` - external boundaries and authority contracts.
3. `architecture/2.x/02_containers/README.md` - runtime/governance container responsibilities.
4. `architecture/2.x/03_components/README.md` - component-level behavior sequences.
5. `architecture/audience/internal/*.md` and `architecture/audience/external/*.md` - persona references linked from user journey actor tables.

## Brainstorm Alignment Outcome

The brainstorming proposal was applied with two guardrails.
Source corpus: `architecture/2.x/initiatives/2026-02-architecture-discovery-and-restructure/`.

1. Adopted:
   - Versioned architecture split (`1.x` and `2.x`)
   - Dedicated 2.x `user_journey/` area
   - Dedicated 2.x `initiatives/` area
   - C4-oriented 2.x directories (`01_context`, `02_containers`, `03_components`)
   - Domain and audience expansion (`architecture/2.x/README.md#domain-breakdown`, `architecture/audience/`)
2. Deferred:
   - `archive/` lifecycle structure (can be introduced later once process is formalized)
3. Rejected for now:
   - C4 `04_code` architecture docs in this repo, because code-level tracking already lives in `src/` README and package docs

## Migration Notes

1. Brainstorm proposals were normalized to repository reality:
   - versioned docs live in `docs/1x` and `docs/2x`
   - versioned architecture lives in `architecture/1.x` and `architecture/2.x`
2. Legacy ADR links are intentionally preserved via `architecture/adrs/` compatibility aliases.
3. Deprecated architecture docs were moved from `docs/architecture/` to `architecture/1.x/notes/`.
4. Ongoing `next` mapping tracking moved from `docs/development/tracking/next-mission-mappings/` to `architecture/2.x/initiatives/next-mission-mappings/`.

## Creating a New ADR

Use the shared template:

```bash
cp architecture/adr-template.md architecture/2.x/adr/YYYY-MM-DD-N-your-decision.md
```

Use `architecture/1.x/adr/` only when documenting legacy 1.x behavior.

## Find ADRs

```bash
ls -1 architecture/1.x/adr | sort
ls -1 architecture/2.x/adr | sort
rg -n "Status:|Decision Outcome|Technical Story" architecture/1.x/adr architecture/2.x/adr
```

### Notable Recent ADRs (2.x)

| Filename | Title | Status | Date |
|---|---|---|---|
| `2026-04-11-1-saas-rollout-and-readiness.md` | SaaS Rollout Gate and Hosted Readiness Split | Accepted | 2026-04-11 |

See also:

- `architecture/ARCHITECTURE_DOCS_GUIDE.md`
- `architecture/NAVIGATION_GUIDE.md`
