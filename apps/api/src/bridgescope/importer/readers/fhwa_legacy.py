import csv
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from bridgescope.importer.errors import (
    EmptySourceFileError,
    InvalidSourceRowError,
    MissingRequiredColumnsError,
)
from bridgescope.importer.records import RawBridgeRecord

REQUIRED_FIELDS = frozenset(
    {
        "STATE_CODE_001",
        "STRUCTURE_NUMBER_008",
        "FACILITY_CARRIED_007",
        "FEATURES_DESC_006A",
        "COUNTY_CODE_003",
        "LAT_016",
        "LONG_017",
        "YEAR_BUILT_027",
        "YEAR_RECONSTRUCTED_106",
        "ADT_029",
        "YEAR_ADT_030",
        "PERCENT_ADT_TRUCK_109",
        "TRAFFIC_LANES_ON_028A",
        "STRUCTURE_LEN_MT_049",
        "MAX_SPAN_LEN_MT_048",
        "OWNER_022",
        "STRUCTURE_KIND_043A",
        "STRUCTURE_TYPE_043B",
        "DATE_OF_INSPECT_090",
        "DECK_COND_058",
        "SUPERSTRUCTURE_COND_059",
        "SUBSTRUCTURE_COND_060",
        "CULVERT_COND_062",
        "BRIDGE_CONDITION",
        "LOWEST_RATING",
    }
)


def validate_headers(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise EmptySourceFileError("Source file has no header row.")

    missing = REQUIRED_FIELDS - set(fieldnames)

    if missing:
        formatted = ", ".join(sorted(missing))
        raise MissingRequiredColumnsError(
            f"Source file is missing required columns: {formatted}"
        )


def validate_row_shape(
    row: dict[str | None, str | list[str] | None],
    row_number: int,
) -> None:
    if None in row:
        raise InvalidSourceRowError(
            f"Row {row_number} contains more fields than the header."
        )

    missing_values = [field for field, value in row.items() if value is None]

    if missing_values:
        raise InvalidSourceRowError(
            f"Row {row_number} contains fewer fields than the header."
        )


def read_fhwa_legacy_file(path: Path) -> Iterator[RawBridgeRecord]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as source_file:
        reader = csv.DictReader(
            source_file,
            delimiter=",",
            quotechar="'",
        )

        validate_headers(reader.fieldnames)

        # Row numbers are logical CSV record positions including the header offset.
        for row_number, row in enumerate(reader, start=2):
            validate_row_shape(row, row_number)

            yield RawBridgeRecord(
                row_number=row_number,
                values=cast(dict[str, str], row),
            )
