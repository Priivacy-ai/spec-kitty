"""Compatibility alias for the canonical charter compiler module."""

from __future__ import annotations

import sys

from charter import compiler as _compiler

sys.modules[__name__] = _compiler
