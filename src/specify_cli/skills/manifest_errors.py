"""Structured error types for the skills manifest store.

Kept in a sibling module so the installer, migration, and doctor can import
error codes without pulling in the full manifest store API.

Supported error codes
---------------------
``"unsupported_schema_version"``
    The on-disk ``schema_version`` is not ``1``.  ``context["found"]`` carries
    the actual value.

``"schema_validation_failed"``
    The document failed JSON-Schema validation.  ``context["errors"]`` is a
    list of human-readable message strings.

``"corrupt_json"``
    The file could not be parsed as JSON.  ``context["path"]`` is the file path
    and ``context["detail"]`` is the low-level error message.

``"duplicate_path"``
    Two or more entries share the same ``path``.  ``context["path"]`` is the
    duplicated value.
"""

from __future__ import annotations


class ManifestError(Exception):
    """Raised by the manifest store when loading or saving fails.

    Attributes:
        code: A machine-readable error code string (see module docstring).
        context: A dict of additional diagnostic fields that vary by code.
    """

    def __init__(self, code: str, **context: object) -> None:
        self.code = code
        self.context = context
        super().__init__(f"{code}: {context}")
