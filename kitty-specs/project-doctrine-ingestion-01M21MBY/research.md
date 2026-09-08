# Project doctrine ingestion research

Resolved architect-alphonso investigated the v3.2.6.1 source and tests. Project scan currently emits profile nodes without references; activation reads only persisted graphs. The existing cascade test manually seeds a graph and misses the real CLI failure. Compiler activated-root resolution passes org roots but omits project layer roots. Activation writes before resynthesis runs. ManifestArtifactEntry admits only directive, tactic and styleguide.

Decision: register direct-authored project artifacts through a canonical charter-owned reconciliation path, reusing schema/kind registries and reference extraction. Preserve unrelated graph entries and source files. Project layer root is `.kittify`; the resolver appends doctrine and singular kind directories. Resolve resynthesis prerequisites before committing activations. Preserve list's glossary scope authority by sharing its seed store with show.

Evidence: src/charter/offering/drg/project_scan.py; src/charter/activation/_drg_helpers.py; src/charter/activation/compiler.py; src/specify_cli/cli/commands/charter/activate.py; src/charter/activation/synthesizer/manifest.py; tests/charter/test_project_profile_cascade_reach.py.

No unresolved product questions. Implementation risk: graph and provenance reconciliation must survive subsequent synthesis and preserve user-owned content.
