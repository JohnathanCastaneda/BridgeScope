import csv
from pathlib import Path

import pytest

from bridgescope.importer.errors import (
    EmptySourceFileError,
    InvalidSourceRowError,
    MissingRequiredColumnsError,
)
from bridgescope.importer.readers.fhwa_legacy import (
    REQUIRED_FIELDS,
    read_fhwa_legacy_file,
)

BASE_HEADERS = [
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
]

BASE_ROW = {
    "STATE_CODE_001": "06",
    "STRUCTURE_NUMBER_008": "        06 0021",
    "FACILITY_CARRIED_007": "Interstate 5 & RR",
    "FEATURES_DESC_006A": "Shasta Lake",
    "COUNTY_CODE_003": "089",
    "LAT_016": "40454199",
    "LONG_017": "122190700",
    "YEAR_BUILT_027": "1941",
    "YEAR_RECONSTRUCTED_106": "2008",
    "ADT_029": "19500",
    "YEAR_ADT_030": "2009",
    "PERCENT_ADT_TRUCK_109": "29",
    "TRAFFIC_LANES_ON_028A": "4",
    "STRUCTURE_LEN_MT_049": "1093.6",
    "MAX_SPAN_LEN_MT_048": "192",
    "OWNER_022": "69",
    "STRUCTURE_KIND_043A": "3",
    "STRUCTURE_TYPE_043B": "09",
    "DATE_OF_INSPECT_090": "623",
    "DECK_COND_058": "5",
    "SUPERSTRUCTURE_COND_059": "7",
    "SUBSTRUCTURE_COND_060": "7",
    "CULVERT_COND_062": "N",
    "BRIDGE_CONDITION": "F",
    "LOWEST_RATING": "5",
}


def write_source(
    path: Path,
    headers: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as source_file:
        writer = csv.DictWriter(
            source_file,
            fieldnames=headers,
            delimiter=",",
            quotechar="'",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def test_valid_source_yields_raw_records(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    second_row = {**BASE_ROW, "STRUCTURE_NUMBER_008": "        1CA0070"}
    write_source(path, BASE_HEADERS, [BASE_ROW, second_row])

    records = list(read_fhwa_legacy_file(path))

    assert len(records) == 2
    assert records[0].row_number == 2
    assert records[1].row_number == 3
    assert records[0].values["STATE_CODE_001"] == "06"


def test_structure_number_remains_raw(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    write_source(path, BASE_HEADERS, [BASE_ROW])

    record = next(read_fhwa_legacy_file(path))

    assert record.values["STRUCTURE_NUMBER_008"] == "        06 0021"


def test_missing_required_header_raises(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    headers = [header for header in BASE_HEADERS if header != "ADT_029"]
    row = {key: value for key, value in BASE_ROW.items() if key != "ADT_029"}
    write_source(path, headers, [row])

    with pytest.raises(MissingRequiredColumnsError, match="ADT_029"):
        list(read_fhwa_legacy_file(path))


def test_multiple_missing_required_headers_are_sorted(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    headers = [
        header
        for header in BASE_HEADERS
        if header not in {"YEAR_ADT_030", "ADT_029"}
    ]
    row = {
        key: value
        for key, value in BASE_ROW.items()
        if key not in {"YEAR_ADT_030", "ADT_029"}
    }
    write_source(path, headers, [row])

    with pytest.raises(MissingRequiredColumnsError) as exc_info:
        list(read_fhwa_legacy_file(path))

    assert str(exc_info.value).endswith("ADT_029, YEAR_ADT_030")


def test_extra_header_is_allowed(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    headers = [*BASE_HEADERS, "SOME_FUTURE_FHWA_FIELD"]
    row = {**BASE_ROW, "SOME_FUTURE_FHWA_FIELD": "future"}
    write_source(path, headers, [row])

    records = list(read_fhwa_legacy_file(path))

    assert len(records) == 1
    assert records[0].values["SOME_FUTURE_FHWA_FIELD"] == "future"


def test_quoted_comma_stays_in_one_value(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    row = {**BASE_ROW, "FACILITY_CARRIED_007": "MAIN ST, ROUTE 5"}
    write_source(path, BASE_HEADERS, [row])

    record = next(read_fhwa_legacy_file(path))

    assert record.values["FACILITY_CARRIED_007"] == "MAIN ST, ROUTE 5"


def test_blank_value_remains_empty_string(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    row = {**BASE_ROW, "YEAR_RECONSTRUCTED_106": ""}
    write_source(path, BASE_HEADERS, [row])

    record = next(read_fhwa_legacy_file(path))

    assert record.values["YEAR_RECONSTRUCTED_106"] == ""


def test_too_many_values_raises(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    path.write_text(
        ",".join(BASE_HEADERS)
        + "\n"
        + ",".join(BASE_ROW[header] for header in BASE_HEADERS)
        + ",extra\n",
        encoding="utf-8",
    )

    with pytest.raises(
        InvalidSourceRowError,
        match="Row 2 contains more fields than the header.",
    ):
        list(read_fhwa_legacy_file(path))


def test_too_few_values_raises(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    path.write_text(
        ",".join(BASE_HEADERS)
        + "\n"
        + ",".join(BASE_ROW[header] for header in BASE_HEADERS[:-1])
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        InvalidSourceRowError,
        match="Row 2 contains fewer fields than the header.",
    ):
        list(read_fhwa_legacy_file(path))


def test_empty_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(EmptySourceFileError):
        list(read_fhwa_legacy_file(path))


def test_header_only_source_yields_no_records(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    write_source(path, BASE_HEADERS, [])

    records = list(read_fhwa_legacy_file(path))

    assert records == []


def test_base_headers_cover_reader_required_fields() -> None:
    assert set(BASE_HEADERS) == REQUIRED_FIELDS
