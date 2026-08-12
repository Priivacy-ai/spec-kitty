# Contract: Schema-diagram drift guard (FR-004, NFR-001, C-003)
- Driven by an explicit file:class binding table (1:N).
- Introspection: Pydantic model_fields with `FieldInfo.alias or name` + transitive nested recursion; frozen-dataclass fields(); StrEnum via list(). Never a hand-copied count.
- Completeness: expected set derived from list(ArtifactKind) + priority list; FAIL if any priority kind has no bound diagram.
- Testable: add a field to a DEEPLY nested model → guard FAILS; unregistered priority kind → FAILS; matching diagram → PASSES. Binds styleguides.AntiPattern vs DRG anti_pattern correctly.
