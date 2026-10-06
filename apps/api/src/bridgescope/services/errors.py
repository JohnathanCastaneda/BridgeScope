class ActiveDatasetNotFoundError(Exception):
    """Raised when a query requires an active dataset and none exists."""


class BridgeNotFoundError(Exception):
    """Raised when a bridge identity is not present in the active dataset."""

