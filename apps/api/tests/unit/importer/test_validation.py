from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from bridgescope.importer.normalize import normalize_bridge_record
from bridgescope.importer.readers.fhwa_legacy import read_fhwa_legacy_file
from bridgescope.importer.records import (
    IssueSeverity,
    NormalizedBridgeRecord,
    ValidationIssue,
    ValidationResult,
)
from bridgescope.importer.validation import ValidationContext, validate_bridge_record

CONTEXT = ValidationContext(inventory_year=2025, state_code="06")


def valid_record() -> NormalizedBridgeRecord:
    return NormalizedBridgeRecord(
        source_row_number=2,
        state_code="06",
        structure_number="06 0021",
        county_code="089",
        facility_carried="Interstate 5 & RR",
        feature_crossed="Shasta Lake",
        latitude=Decimal("40.761664"),
        longitude=Decimal("-122.318611"),
        source_latitude_code="40454199",
        source_longitude_code="122190700",
        year_built=1941,
        year_reconstructed=2008,
        average_daily_traffic=19500,
        traffic_year=2009,
        truck_traffic_percent=Decimal("29"),
        lanes_on=4,
        bridge_length_m=Decimal("1093.6"),
        maximum_span_m=Decimal("192"),
        owner_code="69",
        material_code="3",
        design_type_code="09",
        inspection_month=6,
        inspection_year=2023,
        deck_condition_code="5",
        superstructure_condition_code="7",
        substructure_condition_code="7",
        culvert_condition_code="N",
        overall_condition_code="F",
        lowest_condition_rating=5,
    )


def issue_codes(record: NormalizedBridgeRecord) -> tuple[str, ...]:
    return tuple(issue.error_code for issue in validate_bridge_record(record, CONTEXT).issues)


def test_valid_record_has_no_issues() -> None:
    result = validate_bridge_record(valid_record(), CONTEXT)

    assert result.is_valid is True
    assert result.has_errors is False
    assert result.issues == ()


def test_validation_result_treats_fatal_as_error() -> None:
    result = ValidationResult(
        issues=(
            ValidationIssue(
                severity=IssueSeverity.FATAL,
                error_code="SOURCE_FORMAT_ERROR",
                field_name=None,
                message="Source cannot be interpreted.",
            ),
        )
    )

    assert result.has_errors is True
    assert result.is_valid is False


def test_missing_structure_number_is_error() -> None:
    result = validate_bridge_record(
        replace(valid_record(), structure_number=""),
        CONTEXT,
    )

    assert result.is_valid is False
    assert result.issues[0].severity == IssueSeverity.ERROR
    assert result.issues[0].error_code == "MISSING_STRUCTURE_NUMBER"
    assert result.issues[0].field_name == "structure_number"


def test_missing_and_unexpected_state_code_are_errors() -> None:
    assert issue_codes(replace(valid_record(), state_code="")) == (
        "MISSING_STATE_CODE",
    )
    assert issue_codes(replace(valid_record(), state_code="08")) == (
        "UNEXPECTED_STATE_CODE",
    )


def test_county_code_validation() -> None:
    assert issue_codes(replace(valid_record(), county_code="")) == (
        "MISSING_COUNTY_CODE",
    )
    assert issue_codes(replace(valid_record(), county_code="37")) == (
        "INVALID_COUNTY_CODE",
    )
    assert issue_codes(replace(valid_record(), county_code="ABC")) == (
        "INVALID_COUNTY_CODE",
    )

    result = validate_bridge_record(replace(valid_record(), county_code="999"), CONTEXT)

    assert result.is_valid is True
    assert result.issues[0].severity == IssueSeverity.WARNING
    assert result.issues[0].error_code == "UNKNOWN_COUNTY_CODE"


def test_missing_year_built_is_error() -> None:
    assert issue_codes(replace(valid_record(), year_built=None)) == (
        "MISSING_YEAR_BUILT",
    )


def test_future_year_built_is_error() -> None:
    result = validate_bridge_record(replace(valid_record(), year_built=2026), CONTEXT)

    assert result.is_valid is False
    assert result.issues[0].error_code == "YEAR_BUILT_AFTER_INVENTORY_YEAR"


def test_year_built_before_minimum_is_error() -> None:
    assert issue_codes(replace(valid_record(), year_built=1799)) == (
        "YEAR_BUILT_BEFORE_MINIMUM",
    )


def test_reconstruction_before_construction_is_warning() -> None:
    result = validate_bridge_record(
        replace(valid_record(), year_built=1995, year_reconstructed=1980),
        CONTEXT,
    )

    assert result.is_valid is True
    assert result.issues[0].severity == IssueSeverity.WARNING
    assert result.issues[0].error_code == "RECONSTRUCTION_BEFORE_CONSTRUCTION"


def test_reconstruction_after_inventory_year_is_warning() -> None:
    assert issue_codes(replace(valid_record(), year_reconstructed=2026)) == (
        "RECONSTRUCTION_AFTER_INVENTORY_YEAR",
    )


def test_negative_adt_is_error() -> None:
    result = validate_bridge_record(
        replace(valid_record(), average_daily_traffic=-1),
        CONTEXT,
    )

    assert result.is_valid is False
    assert result.issues[0].error_code == "NEGATIVE_AVERAGE_DAILY_TRAFFIC"


def test_traffic_year_after_inventory_year_is_error() -> None:
    result = validate_bridge_record(replace(valid_record(), traffic_year=2026), CONTEXT)

    assert result.is_valid is False
    assert result.issues[0].error_code == "TRAFFIC_YEAR_AFTER_INVENTORY_YEAR"


def test_truck_percent_boundaries() -> None:
    assert issue_codes(replace(valid_record(), truck_traffic_percent=Decimal("-1"))) == (
        "INVALID_TRUCK_TRAFFIC_PERCENT",
    )
    assert issue_codes(replace(valid_record(), truck_traffic_percent=Decimal("0"))) == ()
    assert issue_codes(replace(valid_record(), truck_traffic_percent=Decimal("50"))) == ()
    assert issue_codes(replace(valid_record(), truck_traffic_percent=Decimal("100"))) == ()
    assert issue_codes(replace(valid_record(), truck_traffic_percent=Decimal("101"))) == (
        "INVALID_TRUCK_TRAFFIC_PERCENT",
    )


def test_lanes_on_negative_is_warning() -> None:
    result = validate_bridge_record(replace(valid_record(), lanes_on=-1), CONTEXT)

    assert result.is_valid is True
    assert result.issues[0].error_code == "NEGATIVE_LANES_ON"


def test_dimension_negative_values_are_warnings() -> None:
    assert issue_codes(replace(valid_record(), bridge_length_m=Decimal("-1"))) == (
        "NEGATIVE_BRIDGE_LENGTH",
    )
    assert issue_codes(replace(valid_record(), maximum_span_m=Decimal("-1"))) == (
        "NEGATIVE_MAXIMUM_SPAN",
    )


def test_inspection_month_boundaries() -> None:
    assert issue_codes(replace(valid_record(), inspection_month=0)) == (
        "INVALID_INSPECTION_MONTH",
    )
    assert issue_codes(replace(valid_record(), inspection_month=1)) == ()
    assert issue_codes(replace(valid_record(), inspection_month=12)) == ()
    assert issue_codes(replace(valid_record(), inspection_month=13)) == (
        "INVALID_INSPECTION_MONTH",
    )


def test_inspection_year_after_inventory_year_is_warning() -> None:
    assert issue_codes(replace(valid_record(), inspection_year=2026)) == (
        "INSPECTION_YEAR_AFTER_INVENTORY_YEAR",
    )


def test_coordinate_earth_boundaries() -> None:
    assert issue_codes(replace(valid_record(), latitude=Decimal("-90"))) == (
        "LATITUDE_OUTSIDE_EXPECTED_STATE",
    )
    assert issue_codes(replace(valid_record(), latitude=Decimal("90"))) == (
        "LATITUDE_OUTSIDE_EXPECTED_STATE",
    )
    assert issue_codes(replace(valid_record(), latitude=Decimal("91"))) == (
        "LATITUDE_OUT_OF_RANGE",
    )
    assert issue_codes(replace(valid_record(), longitude=Decimal("-180"))) == (
        "LONGITUDE_OUTSIDE_EXPECTED_STATE",
    )
    assert issue_codes(replace(valid_record(), longitude=Decimal("180"))) == (
        "LONGITUDE_OUTSIDE_EXPECTED_STATE",
    )
    assert issue_codes(replace(valid_record(), longitude=Decimal("181"))) == (
        "LONGITUDE_OUT_OF_RANGE",
    )


def test_valid_earth_coordinate_outside_california_is_warning() -> None:
    result = validate_bridge_record(
        replace(valid_record(), latitude=Decimal("45"), longitude=Decimal("-122")),
        CONTEXT,
    )

    assert result.is_valid is True
    assert issue_codes(replace(valid_record(), latitude=Decimal("45"))) == (
        "LATITUDE_OUTSIDE_EXPECTED_STATE",
    )


def test_component_condition_codes() -> None:
    assert issue_codes(replace(valid_record(), deck_condition_code="0")) == ()
    assert issue_codes(replace(valid_record(), deck_condition_code="9")) == ()
    assert issue_codes(replace(valid_record(), deck_condition_code="N")) == ()
    assert issue_codes(replace(valid_record(), deck_condition_code=None)) == ()

    result = validate_bridge_record(replace(valid_record(), deck_condition_code="X"), CONTEXT)

    assert result.is_valid is True
    assert result.issues[0].severity == IssueSeverity.WARNING
    assert result.issues[0].error_code == "INVALID_DECK_CONDITION_CODE"


def test_each_component_condition_field_has_specific_error_code() -> None:
    assert issue_codes(replace(valid_record(), superstructure_condition_code="X")) == (
        "INVALID_SUPERSTRUCTURE_CONDITION_CODE",
    )
    assert issue_codes(replace(valid_record(), substructure_condition_code="X")) == (
        "INVALID_SUBSTRUCTURE_CONDITION_CODE",
    )
    assert issue_codes(replace(valid_record(), culvert_condition_code="X")) == (
        "INVALID_CULVERT_CONDITION_CODE",
    )


def test_overall_condition_codes() -> None:
    assert issue_codes(replace(valid_record(), overall_condition_code="G")) == ()
    assert issue_codes(replace(valid_record(), overall_condition_code="F")) == ()
    assert issue_codes(replace(valid_record(), overall_condition_code="P")) == ()
    assert issue_codes(replace(valid_record(), overall_condition_code=None)) == ()
    assert issue_codes(replace(valid_record(), overall_condition_code="X")) == (
        "INVALID_OVERALL_CONDITION_CODE",
    )


def test_lowest_rating_range() -> None:
    assert issue_codes(replace(valid_record(), lowest_condition_rating=0)) == ()
    assert issue_codes(replace(valid_record(), lowest_condition_rating=9)) == ()
    assert issue_codes(replace(valid_record(), lowest_condition_rating=-1)) == (
        "INVALID_LOWEST_CONDITION_RATING",
    )
    assert issue_codes(replace(valid_record(), lowest_condition_rating=10)) == (
        "INVALID_LOWEST_CONDITION_RATING",
    )


def test_unknown_reference_codes_are_warnings() -> None:
    result = validate_bridge_record(
        replace(
            valid_record(),
            owner_code="99",
            material_code="Z",
            design_type_code="99",
        ),
        CONTEXT,
    )

    assert result.is_valid is True
    assert [issue.severity for issue in result.issues] == [
        IssueSeverity.WARNING,
        IssueSeverity.WARNING,
        IssueSeverity.WARNING,
    ]
    assert [issue.error_code for issue in result.issues] == [
        "UNKNOWN_OWNER_CODE",
        "UNKNOWN_MATERIAL_CODE",
        "UNKNOWN_DESIGN_TYPE_CODE",
    ]


def test_multiple_issues_are_collected_in_deterministic_order() -> None:
    result = validate_bridge_record(
        replace(
            valid_record(),
            year_built=2026,
            year_reconstructed=None,
            average_daily_traffic=-1,
            truck_traffic_percent=Decimal("101"),
            deck_condition_code="X",
        ),
        CONTEXT,
    )

    assert [issue.error_code for issue in result.issues] == [
        "YEAR_BUILT_AFTER_INVENTORY_YEAR",
        "NEGATIVE_AVERAGE_DAILY_TRAFFIC",
        "INVALID_TRUCK_TRAFFIC_PERCENT",
        "INVALID_DECK_CONDITION_CODE",
    ]
    assert result.is_valid is False


def test_validator_does_not_mutate_record() -> None:
    record = replace(valid_record(), truck_traffic_percent=Decimal("101"))

    validate_bridge_record(record, CONTEXT)

    assert record.truck_traffic_percent == Decimal("101")


def test_representative_sample_validates_without_errors() -> None:
    repository_root = Path(__file__).resolve().parents[5]
    path = repository_root / "data/samples/ca_nbi_2025_sample.csv"

    results = [
        validate_bridge_record(normalize_bridge_record(raw), CONTEXT)
        for raw in read_fhwa_legacy_file(path)
    ]

    assert len(results) == 29
    assert sum(not result.is_valid for result in results) == 0
