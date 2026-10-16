"""Public error categories shared by the additive V2 repositories."""

class RepositoryError(RuntimeError):
    """A V2 data-access operation failed."""


class RepositoryConflictError(RepositoryError):
    """A primary key or unique identity already exists."""


class RepositoryForeignKeyError(RepositoryError):
    """A referenced record is unavailable or still in use."""


class RepositoryValidationError(RepositoryError, ValueError):
    """The supplied or stored representation is invalid."""


class RepositoryNotFoundError(RepositoryError, KeyError):
    """The record targeted by a write does not exist."""
