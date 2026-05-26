"""Charter-runtime facade placeholder.

Reserved for the high-level charter facade. No public symbols are exported yet;
this submodule exists to fix the umbrella shape declared by LD-5 / FR-014.

When a concrete facade is introduced, populate ``__all__`` and add the corresponding
shim re-export at ``specify_cli.charter`` per spec C-008.
"""

__all__: list[str] = []
