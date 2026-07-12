"""Backward-compatibility shim for specify_cli.missions.

The canonical implementation is in doctrine.missions. This package
re-exports the public surface so that existing callers continue to work
without modification (C-006). Access is mediated through the
``charter.primitives`` facade per the runtime → charter → doctrine
boundary (mission ``charter-mediated-doctrine-selection-01KRTZCA``).
"""

from __future__ import annotations

from typing import Any

# Module-level lazy-import dict (relocation-hardened-dead-code-scanners-01KX958P
# WP02): the ``_symbol_key`` resolver's FR-003 facade-dict shape requires the
# ``{name: (module, attr)}`` mapping to be a MODULE-level ``Assign``/``AnnAssign``
# (so ``_find_dict_assign`` can locate it) -- a function-local dict built fresh
# inside ``__getattr__`` is an undecidable shape (fail-closed / un-keyable).
# This is a pure mechanical relocation of the same two entries; behavior is
# unchanged (still a lazy, on-demand import via ``__getattr__``). The
# module-path element is the SSOT the dead-SYMBOL gate hashes against; the
# runtime dispatch below imports ``charter.primitives`` with a STATIC
# ``from charter import primitives`` (not ``importlib.import_module``) so the
# dead-MODULES gate still sees ``charter.primitives`` as a live caller edge --
# a dynamic string import would erase that edge and orphan the module.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "PrimitiveExecutionContext": ("charter.primitives", "PrimitiveExecutionContext"),
    "execute_with_glossary": ("charter.primitives", "execute_with_glossary"),
}

# Kept as a literal (not ``list(_LAZY_IMPORTS)``) so the dead-symbol gate's
# static ``__all__`` extractor -- which only recognizes a literal list/tuple
# of string constants -- still sees this module's public surface.
__all__ = [
    "PrimitiveExecutionContext",
    "execute_with_glossary",
]


def __getattr__(name: str) -> Any:
    """Lazily expose the historical primitive helpers.

    Importing submodules such as ``specify_cli.missions._read_path_resolver``
    should not eagerly load the full charter/doctrine primitive stack. That
    startup path is latency-sensitive for ``spec-kitty next`` query mode.
    """
    if name not in _LAZY_IMPORTS:
        raise AttributeError(name)

    _module_path, attr = _LAZY_IMPORTS[name]
    from charter import primitives  # noqa: PLC0415  (lazy: keeps `next` query fast)

    return getattr(primitives, attr)
