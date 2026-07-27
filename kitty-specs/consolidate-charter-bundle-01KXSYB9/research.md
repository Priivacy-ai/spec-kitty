# Research: Consolidate the Compiled Charter Bundle

Phase 0 decisions. Most were resolved by a 4-lens grounding squad + a thesis/antithesis dialectic + a neutral empirical trace (full write-up: `research/charter-authority-inversion-assessment.md`) and a 3-lens pre-plan squad (`research/pre-plan-grounding.md`). This file records the decisions in canonical form.

## Decision 1 — charter.yaml is the project charter and OWNS activation
- **Decision**: `charter.yaml` becomes the authoritative, git-tracked, authorable, pack-shaped project charter holding governance + directives + the resolving catalog + the project activation state + overrides, overlaying the layer-0 `default.yaml`. The activation state relocates out of `.kittify/config.yaml`.
- **Rationale**: The charter's canonical purpose is to activate doctrine (ADR 2026-07-15-1). Owning activation in `charter.yaml` unifies local + pack-provisioned activation and delivers single-canonical-authority. Operator-confirmed.
- **Alternatives considered**: (a) charter.yaml authoritative-for-read only, config.yaml keeps the activation write-target — rejected: leaves activation split, defers the unification. (b) config.yaml stays sole activation authority (the earlier C-005) — superseded by the operator decision.

## Decision 2 — Retire the prose→triad extractor; charter.md is a curated companion
- **Decision**: Delete the deterministic prose→triad scrape (`extractor.py SECTION_MAPPING` + `sync()` backward path + dead `extract_with_ai`); governance/directive loaders read `charter.yaml` structured fields. `charter.md` is hand-authored, never a resolving input, never clobbered.
- **Rationale**: Empirical trace proved the "AI extractor" is dead code (deterministic regex) and that governance prose is display-only — so `charter.yaml` seeds losslessly from the existing structured triad (yaml→yaml). Deletes a brittle scraper (deterministic-first).
- **Alternatives considered**: keep the extractor and derive charter.yaml from prose — rejected: perpetuates the brittle scrape and the dual-owned charter.md clobber.

## Decision 3 — Seed charter.yaml from the triad (deterministic, lossless)
- **Decision**: The migration + compile seed `charter.yaml`'s governance/directives/catalog from the existing structured YAML (`governance.yaml`/`directives.yaml`/`metadata.yaml`/`references.yaml`) — no prose parsing.
- **Rationale**: yaml→yaml is deterministic and idempotent (satisfies NFR-003); avoids the lossy prose-extraction the antithesis feared (which turned out to rest on the dead-AI mislabel).
- **Alternatives considered**: prose→structured extraction — rejected (lossy, non-idempotent).

## Decision 4 — Manifest tracked/derived semantics (Landmine 1)
- **Decision**: `charter.yaml` ∈ `tracked_files`; repurpose the manifest's `derived_files`/`derivation_sources` from "generated & gitignored" to "content-hash input set"; single `SCHEMA_VERSION` bump 1.0.0→2.0.0; `BUNDLE_CONTENT_HASH_FILES` → `("charter.yaml",)`. The `catalog` section is a derived-but-committed projection kept honest by config↔catalog parity + freshness (NOT split into a separate file).
- **Rationale**: A git-tracked file is the only thing that can be an authoring surface (C-001). Splitting the catalog re-creates the split-brain the mission removes. One schema cut (C-004) avoids the second bump #2519 exists to end.
- **Alternatives considered**: charter.yaml gitignored/derived (contradicts authorable); separate derived catalog file (partial split-brain).

## Decision 5 — Retire the charter.md-hash staleness (Landmine 2)
- **Decision**: Retire `_compute_charter_source` charter.md-hash staleness (or re-home the hash externally via the synthesis manifest's `bundle_content_hash`); do NOT carry a self-referential `charter_hash` inside `charter.yaml.metadata`.
- **Rationale**: `charter.md` is now a never-resolving companion — hashing it for freshness is the old model; a hash of charter.yaml cannot live inside charter.yaml (chicken-egg).
- **Alternatives considered**: keep charter.md-hash staleness — rejected (meaningless post-inversion; re-stales spuriously).

## Decision 6 — Delivery: one branch, one PR, tidy-first (no half-inverted ship)
- **Decision**: Deliver the full inversion + activation relocation on one branch, PRed as a consistent whole, sequenced tidy-first (IC-02 → {IC-01, IC-03} → IC-04 → {IC-05, IC-06} → IC-07; IC-08 P2; IC-09 parallel).
- **Rationale**: The charter.yaml schema is the expensive-to-reverse artifact; a half-inverted intermediate (schema authoritative but consumers/extractor inconsistent) is the NFR-005 failure. Operator-confirmed.
- **Alternatives considered**: split across PRs / separate fast-follow mission — rejected by the operator (re-cut risk + inconsistent intermediate state).

## Decision 7 — Foldability
- **Decision**: No folds. #2554 already fixed → verify + close as already-remediated (out of scope). #2373 strictly follow-up (doctrine-synthesis pipeline, under #1914). #2772 folded (FR-007/IC-03).
- **Rationale**: pre-plan squad verified #2554's arch test is green and its parity axis is different; #2373's root cause is a different pipeline the mission does not restructure.

## Decision 8 — Fence ADR 2026-07-15-1 runtime-gating OUT (C-008)
- **Decision**: This mission advances only the activation-surface/ownership axis. Runtime activation-gating + first-class DRG nodes for `mission_type`/`gate`/`asset` stay out. Local-doctrine-override mechanism assumed-compatible (separately tracked). The **charter-tier accumulation** (org⊆team⊆repo, the Flashpoint journey) is FORWARD-INTENT — `pack_roots` overlays artifact *definitions*, not activation tiers; activation today is a single flat set (paula MAJOR-4). This mission relocates that single flat surface; the diagram documents the tier model as target.
- **Rationale**: The full ADR 2026-07-15-1 restructure is a large separate epic (still Proposed); relocating the activation surface is the deliverable slice.

## Decision 9 — config.yaml keeps a one-line charter pointer (indirection)
- **Decision**: `.kittify/config.yaml` retains a single `charter:` pointer (default `.kittify/charter/charter.yaml`) that the resolver reads to locate the active charter; a charter swap is a one-line config change. `PackContext.from_config` resolves `charter.yaml` via this pointer (a two-file read — `org_packs` stay in config).
- **Rationale** (operator, 2026-07-18): the resolver finds `charter.yaml` deterministically; charter swaps (experimentation, local redirects, cross-project / shared charters) are one-line changes; multi-user repos avoid merge conflicts because churny activation/governance edits live in `charter.yaml` (or a redirected charter), not in `config.yaml`.
- **Alternatives considered**: a fixed hard-coded charter path — rejected (no swap/redirect capability, more merge friction). Fail-loud on a dangling pointer (no fallback), per C-003.

## Decision 10 — activation is FLAT at charter.yaml root; distinct content_hash_files field; partial writes
- **Decision** (post-alignment-squad): (a) activation keys are FLAT at `charter.yaml` root (matching `default.yaml`), not a nested `activation:` section — so `_read_activated_*` + `commit_plan` are unchanged; (b) the content-hash input set is a **distinct `content_hash_files` field** (`[charter.yaml]`), `derived_files=[]`, so `_validate`'s tracked∩derived invariant is untouched; (c) charter.yaml writes are **partial/merge writes** through one shared helper (preserve authored sections byte-for-byte — the #2772 clobber must not reappear inside charter.yaml).
- **Rationale**: alignment squad (paula BLOCKER-1 flat shape; renata M2 / alphonso MAJOR-1 validate; alphonso MAJOR-2/3 internal clobber + shared writer). All grounded in code.
- **Alternatives considered**: nested `activation:` (rejected — breaks flat readers/overlay); put charter.yaml in derived_files (rejected — violates `_validate`); full-file overwrite writer (rejected — clobbers authored edits).
