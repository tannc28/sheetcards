"""Custom exception types for the Sheets2Anki addon (extracted from utils.py)."""


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


# =============================================================================
# SUBDECK FUNCTIONS (moved to avoid circular import)
# =============================================================================
