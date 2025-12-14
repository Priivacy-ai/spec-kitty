"""Migration registry for Spec Kitty upgrade system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Type

from packaging.version import Version

if TYPE_CHECKING:
    from .migrations.base import BaseMigration


class MigrationRegistry:
    """Registry of all available migrations, ordered by target version."""

    _migrations: Dict[str, Type["BaseMigration"]] = {}

    @classmethod
    def register(
        cls, migration_class: Type["BaseMigration"]
    ) -> Type["BaseMigration"]:
        """Decorator to register a migration class.

        Args:
            migration_class: The migration class to register

        Returns:
            The same migration class (for decorator use)

        Raises:
            ValueError: If migration_id is not set
        """
        if not migration_class.migration_id:
            raise ValueError(
                f"Migration {migration_class.__name__} must have a migration_id"
            )
        cls._migrations[migration_class.migration_id] = migration_class
        return migration_class

    @classmethod
    def get_all(cls) -> List["BaseMigration"]:
        """Get all migrations as instances, ordered by target version.

        Returns:
            List of migration instances sorted by target version
        """
        instances = [m() for m in cls._migrations.values()]
        return sorted(instances, key=lambda m: Version(m.target_version))

    @classmethod
    def get_applicable(
        cls, from_version: str, to_version: str
    ) -> List["BaseMigration"]:
        """Get migrations needed to go from one version to another.

        Args:
            from_version: Current version
            to_version: Target version

        Returns:
            List of applicable migrations in order
        """
        from_v = Version(from_version)
        to_v = Version(to_version)

        applicable = []
        for migration in cls.get_all():
            target = Version(migration.target_version)
            # Include if target is > from_version AND <= to_version
            if from_v < target <= to_v:
                applicable.append(migration)

        return applicable

    @classmethod
    def get_by_id(cls, migration_id: str) -> "BaseMigration | None":
        """Get a specific migration by ID.

        Args:
            migration_id: The migration ID to look up

        Returns:
            Migration instance if found, None otherwise
        """
        migration_class = cls._migrations.get(migration_id)
        return migration_class() if migration_class else None

    @classmethod
    def clear(cls) -> None:
        """Clear all registered migrations (for testing)."""
        cls._migrations.clear()
