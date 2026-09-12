"""Schema-diagram drift guard (WP08, mission doctrine-schema-diagrams-01KZTQTH).

Compares each authored ``@startyaml`` schema diagram's field set against its bound
code model, with BOTH sides derived by introspection/parse — never hand-copied.
See ``guard.py`` for the engine and ``binding_table.py`` for the explicit
``file:anchor -> model`` registry + the ArtifactKind disposition map.
"""
