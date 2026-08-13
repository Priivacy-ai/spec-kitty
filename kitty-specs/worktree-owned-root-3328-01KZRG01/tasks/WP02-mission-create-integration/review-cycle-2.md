---
affected_files: []
cycle_number: 2
mission_slug: worktree-owned-root-3328-01KZRG01
reproduction_command:
reviewed_at: '2026-08-11T17:02:00Z'
reviewer_agent: user
wp_id: WP02
---

# WP02 planning amendment required — public runtime surface contract

The amended create-time target seam is behaviorally green but the full
mission-runtime architectural gate exposed one additional owned-file boundary.

- Stable target reproduction: 1 failed (`main` vs `owned-mission`) before fix.
- Seam contract RED: missing package-root export before fix.
- Focused post-fix: 6 passed.
- WP02 scoped gates: 222 passed.
- Broader runtime/architecture gate: 313 passed, 1 failed.
- Blocking failure:
  `tests/architectural/test_mission_runtime_surface.py::TestMissionRuntimeSurface::test_public_surface_matches_contract`
  requires the new package-root symbol to be pinned in `_PUBLIC_SURFACE`.

That architectural contract file is not currently owned by WP02. Do not use a
compatibility attribute or internal-submodule import workaround; both would
violate the approved canonical umbrella boundary. Add only
`tests/architectural/test_mission_runtime_surface.py` to WP02 ownership and T008,
rerun canonical finalize/analyze, then reclaim and make the expected-symbol
assertion green.

Frozen WIP commit: `3f391ee1f31b8185d0e3f8118e8855498114511f`.
Runtime gate JUnit SHA-256:
`ae7dd7d8e190afeee6fe20e27d415ea417feab06bd11c45127c4d3a4a34edb81`.
