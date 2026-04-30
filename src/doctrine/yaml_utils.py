"""Shared YAML utilities for the doctrine package.

Provides ``canonical_yaml`` — a deterministic, sorted-key YAML serializer
that returns bytes.  Extracted here so it can be used by both
``doctrine.versioning`` (migration hash computation) and
``charter.synthesizer.synthesize_pipeline`` (artifact-content hashing)
without creating a circular dependency.

Dependency direction: doctrine is a leaf package. It must NOT import from
charter.*.  Any code in charter that needs canonical YAML should import from
``charter.synthesizer.synthesize_pipeline.canonical_yaml`` (which delegates
here) or call this module directly.
"""

from __future__ import annotations

import io
from collections.abc import Mapping
from typing import Any

from ruamel.yaml import YAML


def canonical_yaml(body: Mapping[str, Any]) -> bytes:
    """Serialize ``body`` to YAML bytes in a deterministic canonical form.

    Rules:
    - Keys are sorted alphabetically at every level.
    - Default flow style is False (block style).
    - No YAML aliases (pure data, no anchors/references).
    - UTF-8 encoding.

    Returns:
        UTF-8-encoded YAML bytes.  Never calls ``.encode()`` on the result;
        the bytes are produced directly by ruamel.yaml's BytesIO dump.
    """
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.explicit_start = False

    def _sort_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _sort_keys(obj[k]) for k in sorted(obj.keys())}
        if isinstance(obj, (list, tuple)):
            return [_sort_keys(v) for v in obj]
        return obj

    sorted_body = _sort_keys(dict(body))
    buf = io.BytesIO()
    yaml.dump(sorted_body, buf)
    return buf.getvalue()


__all__ = ["canonical_yaml"]
