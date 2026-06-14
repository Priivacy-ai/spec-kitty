"""Tool surface contract bounded context.

The ``ToolSurfaceContract`` registry answers "what surfaces should exist for a
configured tool?" as *policy*, separately from manifests (which record what is
actually installed). Registry is policy; manifests are state.

This package deliberately distinguishes a *tool* (a coding harness such as
``claude`` or ``codex``) from an *agent* (a profile/persona the tool runs).
Type names use the ``ToolSurface*`` / ``Surface*`` prefixes and must not be
renamed to any ``Agent*`` variant.

Re-exports are intentionally omitted while the module stabilizes; import the
concrete symbols from their defining submodules.
"""
