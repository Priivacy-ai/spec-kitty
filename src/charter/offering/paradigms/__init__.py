"""
Paradigms domain model - public API.

This package provides the Paradigm domain entity and ParadigmRepository for
loading, querying, and saving paradigm YAML files.
"""

from charter.offering.paradigms.models import Paradigm
from charter.offering.paradigms.repository import ParadigmRepository

__all__ = [
    "Paradigm",
    "ParadigmRepository",
]

