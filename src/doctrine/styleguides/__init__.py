"""
Styleguides domain model - public API.

This package provides the Styleguide domain entity, supporting models,
and StyleguideRepository for loading, querying, and saving styleguide YAML files.
"""

from doctrine.styleguides.models import AntiPattern, Styleguide, StyleguideScope
from doctrine.styleguides.repository import StyleguideRepository

__all__ = [
    "AntiPattern",
    "Styleguide",
    "StyleguideRepository",
    "StyleguideScope",
]
