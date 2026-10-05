from dataclasses import dataclass


@dataclass(frozen=True)
class RawBridgeRecord:
    row_number: int
    values: dict[str, str]