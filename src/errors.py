"""Custom exception types for the SheetCards addon (extracted from utils.py)."""


class SyncError(Exception):
    """Base exception for sync-related errors."""

    pass


class NoteProcessingError(SyncError):
    """Exception raised when processing a note fails."""

    pass


class CollectionSaveError(SyncError):
    """Exception raised when saving the collection fails."""

    pass


class ConfigurationError(Exception):
    """Exception raised for configuration-related issues."""

    pass


class RemoteDeckError(Exception):
    """Custom exception for errors related to remote decks.

    Lives here rather than in :mod:`data_processor` so the pure layer
    (:mod:`tsv_model`) can raise it without importing a module that needs Anki.
    ``data_processor`` re-exports it, so ``from .data_processor import
    RemoteDeckError`` still resolves.
    """

    pass
