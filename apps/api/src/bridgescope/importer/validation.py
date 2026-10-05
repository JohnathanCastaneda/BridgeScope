from dataclasses import dataclass
from decimal import Decimal

from bridgescope.importer.records import (
    IssueSeverity,
    NormalizedBridgeRecord,
    ValidationIssue,
    ValidationResult,
)

MIN_YEAR_BUILT = 1800

CALIFORNIA_LATITUDE_MIN = Decimal("32.5")
CALIFORNIA_LATITUDE_MAX = Decimal("42.1")
CALIFORNIA_LONGITUDE_MIN = Decimal("-124.5")
CALIFORNIA_LONGITUDE_MAX = Decimal("-114.1")

CALIFORNIA_COUNTY_CODES = frozenset(
    {
        "001",
        "003",
        "005",
        "007",
        "009",
        "011",
        "013",
        "015",
        "017",
        "019",
        "021",
        "023",
        "025",
        "027",
        "029",
        "031",
        "033",
        "035",
        "037",
        "039",
        "041",
        "043",
        "045",
        "047",
        "049",
        "051",
        "053",
        "055",
        "057",
        "059",
        "061",
        "063",
        "065",
        "067",
        "069",
        "071",
        "073",
        "075",
        "077",
        "079",
        "081",
        "083",
        "085",
        "087",
        "089",
        "091",
        "093",
        "095",
        "097",
        "099",
        "101",
        "103",
        "105",
        "107",
        "109",
        "111",
        "113",
        "115",
    }
)

VALID_COMPONENT_CONDITION_CODES = frozenset(
    {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "N"}
)
VALID_OVERALL_CONDITION_CODES = frozenset({"G", "F", "P"})

# Codes observed in the documented 2025 California source profile. Unknown codes are
# warnings because BridgeScope preserves source codes instead of enum-decoding them.
KNOWN_OWNER_CODES = frozenset(
    {
        "01",
        "02",
        "03",
        "04",
        "11",
        "12",
        "21",
        "25",
        "26",
        "27",
        "32",
        "53",
        "56",
        "57",
        "61",
        "62",
        "63",
        "64",
        "66",
        "68",
        "69",
        "70",
        "72",
        "73",
        "74",
        "75",
    }
)
KNOWN_MATERIAL_CODES = frozenset(str(value) for value in range(10))
KNOWN_DESIGN_TYPE_CODES = frozenset(f"{value:02d}" for value in range(23))


@dataclass(frozen=True)
class ValidationContext:
    inventory_year: int
    state_code: str


def validate_bridge_record(
    record: NormalizedBridgeRecord,
    context: ValidationContext,
) -> ValidationResult:
    issues: list[ValidationIssue] = []

    validate_identity(record, context, issues)
    validate_years(record, context, issues)
    validate_traffic(record, context, issues)
    validate_dimensions(record, issues)
    validate_inspection(record, context, issues)
    validate_coordinates(record, issues)
    validate_conditions(record, issues)
    validate_reference_codes(record, issues)

    return ValidationResult(issues=tuple(issues))


def validate_identity(
    record: NormalizedBridgeRecord,
    context: ValidationContext,
    issues: list[ValidationIssue],
) -> None:
    if not record.state_code:
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "MISSING_STATE_CODE",
                "state_code",
                "State code is required.",
            )
        )
    elif record.state_code != context.state_code:
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "UNEXPECTED_STATE_CODE",
                "state_code",
                f"State code must be {context.state_code} for this import.",
            )
        )

    if not record.structure_number:
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "MISSING_STRUCTURE_NUMBER",
                "structure_number",
                "Structure number is required.",
            )
        )

    if not record.county_code:
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "MISSING_COUNTY_CODE",
                "county_code",
                "County code is required.",
            )
        )
    elif len(record.county_code) != 3 or not record.county_code.isdigit():
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "INVALID_COUNTY_CODE",
                "county_code",
                "County code must be exactly three digits.",
            )
        )
    elif record.county_code not in CALIFORNIA_COUNTY_CODES:
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "UNKNOWN_COUNTY_CODE",
                "county_code",
                "County code is not recognized for California.",
            )
        )


def validate_years(
    record: NormalizedBridgeRecord,
    context: ValidationContext,
    issues: list[ValidationIssue],
) -> None:
    if record.year_built is None:
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "MISSING_YEAR_BUILT",
                "year_built",
                "Year built is required.",
            )
        )
    else:
        if record.year_built <= 0:
            issues.append(
                _issue(
                    IssueSeverity.ERROR,
                    "INVALID_YEAR_BUILT",
                    "year_built",
                    "Year built must be greater than zero.",
                )
            )
        elif record.year_built < MIN_YEAR_BUILT:
            issues.append(
                _issue(
                    IssueSeverity.ERROR,
                    "YEAR_BUILT_BEFORE_MINIMUM",
                    "year_built",
                    f"Year built must be {MIN_YEAR_BUILT} or later.",
                )
            )

        if record.year_built > context.inventory_year:
            issues.append(
                _issue(
                    IssueSeverity.ERROR,
                    "YEAR_BUILT_AFTER_INVENTORY_YEAR",
                    "year_built",
                    "Year built cannot be after the inventory year.",
                )
            )

    if record.year_reconstructed is not None:
        if (
            record.year_built is not None
            and record.year_reconstructed < record.year_built
        ):
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    "RECONSTRUCTION_BEFORE_CONSTRUCTION",
                    "year_reconstructed",
                    "Reconstruction year is before year built.",
                )
            )

        if record.year_reconstructed > context.inventory_year:
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    "RECONSTRUCTION_AFTER_INVENTORY_YEAR",
                    "year_reconstructed",
                    "Reconstruction year is after the inventory year.",
                )
            )


def validate_traffic(
    record: NormalizedBridgeRecord,
    context: ValidationContext,
    issues: list[ValidationIssue],
) -> None:
    if (
        record.average_daily_traffic is not None
        and record.average_daily_traffic < 0
    ):
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "NEGATIVE_AVERAGE_DAILY_TRAFFIC",
                "average_daily_traffic",
                "Average daily traffic cannot be negative.",
            )
        )

    if record.traffic_year is not None and record.traffic_year > context.inventory_year:
        issues.append(
            _issue(
                IssueSeverity.ERROR,
                "TRAFFIC_YEAR_AFTER_INVENTORY_YEAR",
                "traffic_year",
                "Traffic year cannot be after the inventory year.",
            )
        )

    if record.truck_traffic_percent is not None and not (
        Decimal("0") <= record.truck_traffic_percent <= Decimal("100")
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "INVALID_TRUCK_TRAFFIC_PERCENT",
                "truck_traffic_percent",
                "Truck traffic percent must be between 0 and 100.",
            )
        )

    if record.lanes_on is not None and record.lanes_on < 0:
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "NEGATIVE_LANES_ON",
                "lanes_on",
                "Lanes on cannot be negative.",
            )
        )


def validate_dimensions(
    record: NormalizedBridgeRecord,
    issues: list[ValidationIssue],
) -> None:
    if record.bridge_length_m is not None and record.bridge_length_m < 0:
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "NEGATIVE_BRIDGE_LENGTH",
                "bridge_length_m",
                "Bridge length cannot be negative.",
            )
        )

    if record.maximum_span_m is not None and record.maximum_span_m < 0:
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "NEGATIVE_MAXIMUM_SPAN",
                "maximum_span_m",
                "Maximum span length cannot be negative.",
            )
        )


def validate_inspection(
    record: NormalizedBridgeRecord,
    context: ValidationContext,
    issues: list[ValidationIssue],
) -> None:
    if record.inspection_month is not None and not (
        1 <= record.inspection_month <= 12
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "INVALID_INSPECTION_MONTH",
                "inspection_month",
                "Inspection month must be between 1 and 12.",
            )
        )

    if (
        record.inspection_year is not None
        and record.inspection_year > context.inventory_year
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "INSPECTION_YEAR_AFTER_INVENTORY_YEAR",
                "inspection_year",
                "Inspection year cannot be after the inventory year.",
            )
        )


def validate_coordinates(
    record: NormalizedBridgeRecord,
    issues: list[ValidationIssue],
) -> None:
    if record.latitude is not None:
        if not (Decimal("-90") <= record.latitude <= Decimal("90")):
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    "LATITUDE_OUT_OF_RANGE",
                    "latitude",
                    "Latitude must be between -90 and 90.",
                )
            )
        elif not (
            CALIFORNIA_LATITUDE_MIN
            <= record.latitude
            <= CALIFORNIA_LATITUDE_MAX
        ):
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    "LATITUDE_OUTSIDE_EXPECTED_STATE",
                    "latitude",
                    "Latitude is outside expected California bounds.",
                )
            )

    if record.longitude is not None:
        if not (Decimal("-180") <= record.longitude <= Decimal("180")):
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    "LONGITUDE_OUT_OF_RANGE",
                    "longitude",
                    "Longitude must be between -180 and 180.",
                )
            )
        elif not (
            CALIFORNIA_LONGITUDE_MIN
            <= record.longitude
            <= CALIFORNIA_LONGITUDE_MAX
        ):
            issues.append(
                _issue(
                    IssueSeverity.WARNING,
                    "LONGITUDE_OUTSIDE_EXPECTED_STATE",
                    "longitude",
                    "Longitude is outside expected California bounds.",
                )
            )


def validate_conditions(
    record: NormalizedBridgeRecord,
    issues: list[ValidationIssue],
) -> None:
    _validate_component_condition(
        record.deck_condition_code,
        "deck_condition_code",
        "INVALID_DECK_CONDITION_CODE",
        issues,
    )
    _validate_component_condition(
        record.superstructure_condition_code,
        "superstructure_condition_code",
        "INVALID_SUPERSTRUCTURE_CONDITION_CODE",
        issues,
    )
    _validate_component_condition(
        record.substructure_condition_code,
        "substructure_condition_code",
        "INVALID_SUBSTRUCTURE_CONDITION_CODE",
        issues,
    )
    _validate_component_condition(
        record.culvert_condition_code,
        "culvert_condition_code",
        "INVALID_CULVERT_CONDITION_CODE",
        issues,
    )

    if (
        record.overall_condition_code is not None
        and record.overall_condition_code not in VALID_OVERALL_CONDITION_CODES
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "INVALID_OVERALL_CONDITION_CODE",
                "overall_condition_code",
                "Overall condition code must be G, F, or P.",
            )
        )

    if record.lowest_condition_rating is not None and not (
        0 <= record.lowest_condition_rating <= 9
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "INVALID_LOWEST_CONDITION_RATING",
                "lowest_condition_rating",
                "Lowest condition rating must be between 0 and 9.",
            )
        )


def validate_reference_codes(
    record: NormalizedBridgeRecord,
    issues: list[ValidationIssue],
) -> None:
    if record.owner_code is not None and record.owner_code not in KNOWN_OWNER_CODES:
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "UNKNOWN_OWNER_CODE",
                "owner_code",
                "Owner code is not recognized.",
            )
        )

    if (
        record.material_code is not None
        and record.material_code not in KNOWN_MATERIAL_CODES
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "UNKNOWN_MATERIAL_CODE",
                "material_code",
                "Material code is not recognized.",
            )
        )

    if (
        record.design_type_code is not None
        and record.design_type_code not in KNOWN_DESIGN_TYPE_CODES
    ):
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                "UNKNOWN_DESIGN_TYPE_CODE",
                "design_type_code",
                "Design type code is not recognized.",
            )
        )


def _validate_component_condition(
    value: str | None,
    field_name: str,
    error_code: str,
    issues: list[ValidationIssue],
) -> None:
    if value is not None and value not in VALID_COMPONENT_CONDITION_CODES:
        issues.append(
            _issue(
                IssueSeverity.WARNING,
                error_code,
                field_name,
                "Component condition code must be 0-9 or N.",
            )
        )


def _issue(
    severity: IssueSeverity,
    error_code: str,
    field_name: str | None,
    message: str,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        error_code=error_code,
        field_name=field_name,
        message=message,
    )
