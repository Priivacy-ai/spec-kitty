---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: name-vs-authority-remediation-01KTYGTE
mission_id: 01KTYGTE9JV0212WFJ2K82BQ8J
generated_at: '2026-06-12T20:01:11.945047+00:00'
analyzer_agent: unknown
input_artifacts:
  spec.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/name-vs-authority-remediation-01KTYGTE/spec.md
    sha256: d7a3162287a3c232cf088374536361667b90408b0a904f1587360f81820a2a11
  plan.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/name-vs-authority-remediation-01KTYGTE/plan.md
    sha256: a633be7cae1da31b30668cad1d15cd4ef93bc657ba9fe202635b3da9f88b542f
  tasks.md:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/kitty-specs/name-vs-authority-remediation-01KTYGTE/tasks.md
    sha256: 733b1dd4647285e94a01fb6b9dab5a1abb096db917bc2cf52b88e4141bd39dbd
  charter:
    path: /home/stijn/Documents/_code/SDD/fork/spec-kitty/.kittify/charter/charter.md
    sha256: a59cddc8725b34acacd83b9bec24e97b1ae68aa80716b7335c425c6106c18791
verdict: unknown
issue_counts:
  info:
  low:
  high:
  critical:
  medium:
findings: []
---

# Specification Analysis Report — name-vs-authority-remediation-01KTYGTE

Analyzed: spec.md (13 FR / 5 NFR / 4 C / 4 SC), plan.md (13 ICs, D1–D4 resolved), tasks.md + 9 WP
prompts (T001–T032), data-model.md, contracts/authority-seams.md, issue-matrix.md (19 rows),
research/ (5 docs; `research-authority-seams.md` normative). Run after finalize commit `624304f22`.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage | RESOLVED | tasks/WP0*.md frontmatter | `owned_files` was `[]` in all 9 WPs (finalize accepted silently — no overlap check possible, review diff-heuristics blind) | FIXED pre-implement: real per-WP ownership maps + authoritative_surface patched, re-finalized in `624304f22` |
| C2 | Inconsistency | RESOLVED | tasks/WP04 body | Site listed as `lanes/manifest.py:156` — file does not exist; real site is `src/specify_cli/manifest.py:156` (feature-branch name-shape scan) | FIXED in `624304f22`; incorrect doc paths are blocking per review standard |
| I1 | Inconsistency | MEDIUM | WP06 T022 vs WP08 T029 | Both Wave-1 lanes can write `src/doctrine/graph.yaml` if #1865–67 deltas touch `references` blocks. T022 carries the coordination clause (leave regen to WP08 if refs unchanged) | MONITOR at WP06 review: if reference blocks changed, merge WP06 lane into WP08 lane before T029 regen (or re-regen at accept); freshness test is the backstop |
| I2 | Underspecification | MEDIUM | WP01–WP05 vs C-002 | Range discipline on `coordination/status_transition.py` / `cli/commands/merge.py` (upstream coord-merge-stab adjacency) is prompt-enforced only; no automated guard until WP09 ratchet | Reviewer must diff-check touched line ranges in those two files on every WP touching them (WP02/WP03/WP04/WP05) |
| A1 | Ambiguity | LOW | spec.md FR table | FR-013 row precedes FR-012 (cosmetic ordering; both substantive) | Leave as-is; IDs are stable |
| A2 | Coverage | LOW | finalize ownership_warnings | 7 zero-match `owned_files` globs are NEW test files the WPs create (e.g. `test_topology_resolution_boundary.py`) | Benign by construction; no action |

**Coverage Summary** (from finalize `requirement_refs_parsed` — authoritative):

| FR | WP | | FR | WP |
|----|----|---|----|----|
| FR-001 | WP01 | | FR-008 | WP03 |
| FR-002 | WP02 | | FR-009 | WP09 |
| FR-003 | WP01 | | FR-010 | WP06 |
| FR-004 | WP01 | | FR-011 | WP07 |
| FR-005 | WP03 | | FR-012 | WP08 |
| FR-006 | WP04 | | FR-013 | WP01 |
| FR-007 | WP05 | | | |

13/13 FRs mapped (100%); 0 unmapped tasks; every subtask T001–T032 appears in exactly one WP.
NFR-001..005 are threaded through the COMMON constraints block present in all 9 prompts (verified:
NFR-003 fail-closed wording + ATDD ordering + full-mission-slug rule in each).

**Dependency graph** (frontmatter == tasks.md == plan IC sequencing, verified):
WP05 ← {WP03, WP04}; WP09 ← {WP03, WP04, WP05}; rest independent. No cycles. Dual-seam files
(aggregate.py, status_transition.py, implement.py) isolated to WP05 — no ownership overlap with the
seam WPs. graph.yaml solely WP08-owned (see I1). Lanes: 9 (lane-a..lane-i), no collapse.

**Charter Alignment:** no MUST conflicts. ATDD-first honored (pinning fixtures before fix on every
defect FR, per NFR-004); burn-down respected (NFR-001 forbids test deletion); `__all__` convention
noted in seam WPs. Charter check in plan.md remains accurate post-tasks.

**Issue-matrix consistency:** all 10 `in-mission` rows trace to an FR and a WP; FR-004 verification
rows (#1889, #1885-symptom) are WP01 subtasks with proof-recording DoD; 4 deferred rows carry
follow-up refs. No `unknown` verdicts.

**Metrics:** Requirements 13 FR + 5 NFR + 4 C · Tasks 32 in 9 WPs · Coverage 100% · Ambiguity 1 (LOW)
· Duplication 0 · Critical 0 (2 would-be-criticals resolved pre-implement in `624304f22`).

**Next Actions:** No blocking findings. Proceed to implement — Wave 1: WP01/WP02 (release-critical
P0s) + WP03/WP04/WP06/WP07/WP08 parallel; Wave 2: WP05 (merge WP03+WP04 lanes in first); Wave 3:
WP09 (ratchet, lands last, strictness-proof DoD). Watch I1 at WP06 review and I2 at every review of
the two C-002 shared files.
