class SourceReaderError(Exception):
    """Base error for source-file reading failures."""


class MissingRequiredColumnsError(SourceReaderError):
    """Raised when the source file is missing required columns."""


class InvalidSourceRowError(SourceReaderError):
    """Raised when a source row cannot be parsed structurally."""


class EmptySourceFileError(SourceReaderError):
    """Raised when a source file has no header row."""
