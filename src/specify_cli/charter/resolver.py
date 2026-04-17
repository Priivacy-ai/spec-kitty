"""Compatibility alias for the canonical charter resolver module."""

from __future__ import annotations

import sys

from charter import resolver as _resolver

sys.modules[__name__] = _resolver
