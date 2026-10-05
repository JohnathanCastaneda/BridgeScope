from decimal import Decimal
from pathlib import Path

import pytest

from bridgescope.importer.errors import NormalizationError
from bridgescope.importer.normalize import (
    normalize_adt,
    normalize_bridge_record,
    normalize_code,
    normalize_condition_code,
    normalize_county_code,
    normalize_inspection_date,
    normalize_latitude,
    normalize_longitude,
    normalize_lowest_condition_rating,
    normalize_optional_collapsed_text,
    normalize_optional_decimal,
    normalize_optional_integer,
    normalize_optional_text,
    normalize_optional_zero_sentinel_decimal,
    normalize_overall_condition,
    normalize_reconstruction_year,
    normalize_required_text,
    normalize_source_latitude_code,
    normalize_source_longitude_code,
    normalize_structure_number,
    normalize_traffic_year,
)
from bridgescope.importer.readers.fhwa_legacy import read_fhwa_legacy_file
from bridgescope.importer.records import RawBridgeRecord


def test_required_text_trims_outer_whitespace() -> None:
    assert normalize_required_text("  06  ") == "06"


def test_optional_text_blanks_to_none() -> None:
    assert normalize_optional_text("") is None
    assert normalize_optional_text("   ") is None
    assert normalize_optional_text(" RIVER ") == "RIVER"


def test_optional_collapsed_text_trims_and_collapses_internal_whitespace() -> None:
    assert normalize_optional_collapsed_text("  MAIN   ST\tBRIDGE  ") == "MAIN ST BRIDGE"
    assert normalize_optional_collapsed_text("   ") is None


def test_structure_number_preserves_internal_formatting() -> None:
    assert normalize_structure_number("        06 0021") == "06 0021"
    assert normalize_structure_number("00000000000J003") == "00000000000J003"
    assert normalize_structure_number("  ABC 123  ") == "ABC 123"


def test_structure_number_identity_variants_are_distinct() -> None:
    variants = {
        normalize_structure_number("000000000000021"),
        normalize_structure_number("00000000000J003"),
        normalize_structure_number("        06 0021"),
        normalize_structure_number("06  0021"),
        normalize_structure_number(" 06 0021 "),
    }

    assert variants == {
        "000000000000021",
        "00000000000J003",
        "06 0021",
        "06  0021",
    }


def test_county_code_pads_short_codes() -> None:
    assert normalize_county_code("1") == "001"
    assert normalize_county_code("89") == "089"
    assert normalize_county_code("089") == "089"
    assert normalize_county_code("   ") == ""


def test_code_fields_remain_strings() -> None:
    assert normalize_code(" 01 ") == "01"
    assert normalize_code("") is None


def test_optional_integer_blank_to_none_and_parse_errors() -> None:
    assert normalize_optional_integer("") is None
    assert normalize_optional_integer(" 42 ") == 42

    with pytest.raises(NormalizationError, match="Cannot parse integer value"):
        normalize_optional_integer("ABC")


def test_reconstruction_year_sentinels() -> None:
    assert normalize_reconstruction_year("0") is None
    assert normalize_reconstruction_year("") is None
    assert normalize_reconstruction_year("1998") == 1998

    with pytest.raises(NormalizationError):
        normalize_reconstruction_year("ABC")


def test_traffic_year_sentinels() -> None:
    assert normalize_traffic_year("0") is None
    assert normalize_traffic_year("") is None
    assert normalize_traffic_year("2023") == 2023


def test_adt_preserves_zero() -> None:
    assert normalize_adt("550000") == 550000
    assert normalize_adt("0") == 0
    assert normalize_adt("") is None


def test_truck_percent_blank_and_zero_are_distinct() -> None:
    assert normalize_optional_decimal("") is None
    assert normalize_optional_decimal("0") == Decimal("0")


def test_decimal_fields_use_decimal_not_float() -> None:
    assert normalize_optional_decimal("6.1") == Decimal("6.1")
    assert normalize_optional_decimal("99") == Decimal("99")
    assert normalize_optional_decimal("") is None

    with pytest.raises(NormalizationError):
        normalize_optional_decimal("not-a-decimal")

    with pytest.raises(NormalizationError):
        normalize_optional_decimal("NaN")


def test_zero_sentinel_decimal_fields() -> None:
    assert normalize_optional_zero_sentinel_decimal("") is None
    assert normalize_optional_zero_sentinel_decimal("0") is None
    assert normalize_optional_zero_sentinel_decimal("0.0") is None
    assert normalize_optional_zero_sentinel_decimal("1093.6") == Decimal("1093.6")


def test_inspection_date_parses_month_and_century_cutoff() -> None:
    assert normalize_inspection_date("524") == (5, 2024)
    assert normalize_inspection_date("1024") == (10, 2024)
    assert normalize_inspection_date("1250") == (12, 2050)
    assert normalize_inspection_date("1251") == (12, 1951)
    assert normalize_inspection_date("1324") == (13, 2024)
    assert normalize_inspection_date("") == (None, None)


def test_inspection_date_malformed_values_raise() -> None:
    with pytest.raises(NormalizationError):
        normalize_inspection_date("ABC")

    with pytest.raises(NormalizationError):
        normalize_inspection_date("01024")


def test_condition_codes_are_trimmed_only() -> None:
    assert normalize_condition_code("7") == "7"
    assert normalize_condition_code(" N ") == "N"
    assert normalize_condition_code("") is None
    assert normalize_condition_code("X") == "X"


def test_overall_condition_is_not_validated_yet() -> None:
    assert normalize_overall_condition(" F ") == "F"
    assert normalize_overall_condition("") is None
    assert normalize_overall_condition("X") == "X"


def test_lowest_condition_rating_sentinels() -> None:
    assert normalize_lowest_condition_rating("") is None
    assert normalize_lowest_condition_rating("N") is None
    assert normalize_lowest_condition_rating("5") == 5


def test_latitude_conversion() -> None:
    assert normalize_latitude("38000000") == Decimal("38.000000")
    assert normalize_latitude("38153000") == Decimal("38.258333")
    assert normalize_latitude("00000000") is None


def test_longitude_conversion_negates_western_hemisphere() -> None:
    assert normalize_longitude("121000000") == Decimal("-121.000000")
    assert normalize_longitude("121153000") == Decimal("-121.258333")
    assert normalize_longitude("000000000") is None


def test_coordinate_codes_are_preserved_when_present() -> None:
    assert normalize_source_latitude_code(" 38153000 ") == "38153000"
    assert normalize_source_latitude_code("00000000") is None
    assert normalize_source_longitude_code("121153000") == "121153000"
    assert normalize_source_longitude_code("") is None


def test_coordinates_reject_wrong_length_and_nondigit_values() -> None:
    with pytest.raises(NormalizationError):
        normalize_latitude("3815300")

    with pytest.raises(NormalizationError):
        normalize_longitude("12115X000")


def test_coordinate_semantic_bounds_are_left_for_validation() -> None:
    assert normalize_latitude("38623000") == Decimal("39.041667")


def test_complete_record_normalization_from_raw_record() -> None:
    raw = RawBridgeRecord(
        row_number=9,
        values={
            "STATE_CODE_001": " 06 ",
            "STRUCTURE_NUMBER_008": "        06 0021",
            "FACILITY_CARRIED_007": " Main   Street ",
            "FEATURES_DESC_006A": " River   Crossing ",
            "COUNTY_CODE_003": "89",
            "LAT_016": "38153000",
            "LONG_017": "121153000",
            "YEAR_BUILT_027": "1941",
            "YEAR_RECONSTRUCTED_106": "0",
            "ADT_029": "0",
            "YEAR_ADT_030": "0",
            "PERCENT_ADT_TRUCK_109": "6.1",
            "TRAFFIC_LANES_ON_028A": "4",
            "STRUCTURE_LEN_MT_049": "1093.6",
            "MAX_SPAN_LEN_MT_048": "0",
            "OWNER_022": "01",
            "STRUCTURE_KIND_043A": "3",
            "STRUCTURE_TYPE_043B": "09",
            "DATE_OF_INSPECT_090": "524",
            "DECK_COND_058": "7",
            "SUPERSTRUCTURE_COND_059": "7",
            "SUBSTRUCTURE_COND_060": "6",
            "CULVERT_COND_062": "N",
            "BRIDGE_CONDITION": "F",
            "LOWEST_RATING": "5",
        },
    )

    normalized = normalize_bridge_record(raw)

    assert normalized.source_row_number == 9
    assert normalized.state_code == "06"
    assert normalized.structure_number == "06 0021"
    assert normalized.county_code == "089"
    assert normalized.facility_carried == "Main Street"
    assert normalized.feature_crossed == "River Crossing"
    assert normalized.latitude == Decimal("38.258333")
    assert normalized.longitude == Decimal("-121.258333")
    assert normalized.source_latitude_code == "38153000"
    assert normalized.source_longitude_code == "121153000"
    assert normalized.year_built == 1941
    assert normalized.year_reconstructed is None
    assert normalized.average_daily_traffic == 0
    assert normalized.traffic_year is None
    assert normalized.truck_traffic_percent == Decimal("6.1")
    assert normalized.lanes_on == 4
    assert normalized.bridge_length_m == Decimal("1093.6")
    assert normalized.maximum_span_m is None
    assert normalized.owner_code == "01"
    assert normalized.material_code == "3"
    assert normalized.design_type_code == "09"
    assert normalized.inspection_month == 5
    assert normalized.inspection_year == 2024
    assert normalized.deck_condition_code == "7"
    assert normalized.superstructure_condition_code == "7"
    assert normalized.substructure_condition_code == "6"
    assert normalized.culvert_condition_code == "N"
    assert normalized.overall_condition_code == "F"
    assert normalized.lowest_condition_rating == 5


def test_complete_record_normalization_isolates_malformed_field() -> None:
    raw = RawBridgeRecord(
        row_number=9,
        values={
            "STATE_CODE_001": "06",
            "STRUCTURE_NUMBER_008": "        06 0021",
            "FACILITY_CARRIED_007": "Main Street",
            "FEATURES_DESC_006A": "River",
            "COUNTY_CODE_003": "089",
            "LAT_016": "38153000",
            "LONG_017": "121153000",
            "YEAR_BUILT_027": "1941",
            "YEAR_RECONSTRUCTED_106": "0",
            "ADT_029": "ABC",
            "YEAR_ADT_030": "0",
            "PERCENT_ADT_TRUCK_109": "0",
            "TRAFFIC_LANES_ON_028A": "4",
            "STRUCTURE_LEN_MT_049": "1093.6",
            "MAX_SPAN_LEN_MT_048": "0",
            "OWNER_022": "01",
            "STRUCTURE_KIND_043A": "3",
            "STRUCTURE_TYPE_043B": "09",
            "DATE_OF_INSPECT_090": "524",
            "DECK_COND_058": "7",
            "SUPERSTRUCTURE_COND_059": "7",
            "SUBSTRUCTURE_COND_060": "6",
            "CULVERT_COND_062": "N",
            "BRIDGE_CONDITION": "F",
            "LOWEST_RATING": "5",
        },
    )

    with pytest.raises(NormalizationError, match="Cannot parse integer value"):
        normalize_bridge_record(raw)


def test_first_sample_record_normalizes_expected_fields() -> None:
    repository_root = Path(__file__).resolve().parents[5]
    path = repository_root / "data/samples/ca_nbi_2025_sample.csv"
    raw = next(read_fhwa_legacy_file(path))

    normalized = normalize_bridge_record(raw)

    assert normalized.source_row_number == 2
    assert normalized.state_code == "06"
    assert normalized.structure_number == "06 0021"
    assert normalized.county_code == "089"
    assert normalized.facility_carried == "Interstate 5 & RR"
    assert normalized.feature_crossed == "Shasta Lake"
    assert normalized.latitude == Decimal("40.761664")
    assert normalized.longitude == Decimal("-122.318611")
    assert normalized.source_latitude_code == "40454199"
    assert normalized.source_longitude_code == "122190700"
    assert normalized.year_built == 1941
    assert normalized.year_reconstructed == 2008
    assert normalized.average_daily_traffic == 19500
    assert normalized.traffic_year == 2009
    assert normalized.truck_traffic_percent == Decimal("29")
    assert normalized.lanes_on == 4
    assert normalized.bridge_length_m == Decimal("1093.6")
    assert normalized.maximum_span_m == Decimal("192")
    assert normalized.owner_code == "69"
    assert normalized.material_code == "3"
    assert normalized.design_type_code == "09"
    assert normalized.inspection_month == 6
    assert normalized.inspection_year == 2023
    assert normalized.deck_condition_code == "5"
    assert normalized.superstructure_condition_code == "7"
    assert normalized.substructure_condition_code == "7"
    assert normalized.culvert_condition_code == "N"
    assert normalized.overall_condition_code == "F"
    assert normalized.lowest_condition_rating == 5


def test_all_sample_records_normalize_without_crashing() -> None:
    repository_root = Path(__file__).resolve().parents[5]
    path = repository_root / "data/samples/ca_nbi_2025_sample.csv"

    normalized = [normalize_bridge_record(raw) for raw in read_fhwa_legacy_file(path)]

    assert len(normalized) == 29
