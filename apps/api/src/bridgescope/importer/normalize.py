from decimal import Decimal, InvalidOperation

from bridgescope.importer.errors import NormalizationError
from bridgescope.importer.records import NormalizedBridgeRecord, RawBridgeRecord

DECIMAL_PLACES_6 = Decimal("0.000001")


def normalize_required_text(value: str) -> str:
    return value.strip()


def normalize_optional_text(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def normalize_optional_collapsed_text(value: str) -> str | None:
    normalized = " ".join(value.strip().split())
    return normalized or None


def normalize_structure_number(value: str) -> str:
    return value.strip()


def normalize_code(value: str) -> str | None:
    return normalize_optional_text(value)


def normalize_county_code(value: str) -> str:
    normalized = value.strip()

    if len(normalized) in {1, 2}:
        return normalized.zfill(3)

    return normalized


def normalize_integer(value: str) -> int:
    stripped = value.strip()

    try:
        return int(stripped)
    except ValueError as exc:
        raise NormalizationError(f"Cannot parse integer value: {value!r}") from exc


def normalize_optional_integer(value: str) -> int | None:
    stripped = value.strip()

    if stripped == "":
        return None

    return normalize_integer(stripped)


def normalize_reconstruction_year(value: str) -> int | None:
    stripped = value.strip()

    if stripped in {"", "0"}:
        return None

    return normalize_integer(stripped)


def normalize_traffic_year(value: str) -> int | None:
    stripped = value.strip()

    if stripped in {"", "0"}:
        return None

    return normalize_integer(stripped)


def normalize_adt(value: str) -> int | None:
    return normalize_optional_integer(value)


def normalize_optional_decimal(value: str) -> Decimal | None:
    stripped = value.strip()

    if stripped == "":
        return None

    try:
        normalized = Decimal(stripped)
        if not normalized.is_finite():
            raise InvalidOperation
        return normalized
    except InvalidOperation as exc:
        raise NormalizationError(f"Cannot parse decimal value: {value!r}") from exc


def normalize_optional_zero_sentinel_decimal(value: str) -> Decimal | None:
    stripped = value.strip()

    if stripped == "" or _is_all_zero_numeric_text(stripped):
        return None

    return normalize_optional_decimal(stripped)


def normalize_inspection_date(value: str) -> tuple[int | None, int | None]:
    stripped = value.strip()

    if stripped == "":
        return None, None

    if len(stripped) not in {3, 4} or not stripped.isdigit():
        raise NormalizationError(f"Cannot parse inspection date value: {value!r}")

    padded = stripped.zfill(4)
    month = int(padded[:2])
    year_two_digits = int(padded[2:])
    century = 2000 if year_two_digits <= 50 else 1900

    return month, century + year_two_digits


def normalize_source_latitude_code(value: str) -> str | None:
    return _normalize_source_coordinate_code(value)


def normalize_source_longitude_code(value: str) -> str | None:
    return _normalize_source_coordinate_code(value)


def normalize_latitude(value: str) -> Decimal | None:
    return _normalize_coordinate(value, degrees_digits=2, sign=1)


def normalize_longitude(value: str) -> Decimal | None:
    return _normalize_coordinate(value, degrees_digits=3, sign=-1)


def normalize_condition_code(value: str) -> str | None:
    return normalize_optional_text(value)


def normalize_overall_condition(value: str) -> str | None:
    return normalize_optional_text(value)


def normalize_lowest_condition_rating(value: str) -> int | None:
    stripped = value.strip()

    if stripped in {"", "N"}:
        return None

    return normalize_integer(stripped)


def normalize_bridge_record(record: RawBridgeRecord) -> NormalizedBridgeRecord:
    inspection_month, inspection_year = normalize_inspection_date(
        record.values["DATE_OF_INSPECT_090"]
    )

    return NormalizedBridgeRecord(
        source_row_number=record.row_number,
        state_code=normalize_required_text(record.values["STATE_CODE_001"]),
        structure_number=normalize_structure_number(
            record.values["STRUCTURE_NUMBER_008"]
        ),
        county_code=normalize_county_code(record.values["COUNTY_CODE_003"]),
        facility_carried=normalize_optional_collapsed_text(
            record.values["FACILITY_CARRIED_007"]
        ),
        feature_crossed=normalize_optional_collapsed_text(
            record.values["FEATURES_DESC_006A"]
        ),
        latitude=normalize_latitude(record.values["LAT_016"]),
        longitude=normalize_longitude(record.values["LONG_017"]),
        source_latitude_code=normalize_source_latitude_code(record.values["LAT_016"]),
        source_longitude_code=normalize_source_longitude_code(
            record.values["LONG_017"]
        ),
        year_built=normalize_optional_integer(record.values["YEAR_BUILT_027"]),
        year_reconstructed=normalize_reconstruction_year(
            record.values["YEAR_RECONSTRUCTED_106"]
        ),
        average_daily_traffic=normalize_adt(record.values["ADT_029"]),
        traffic_year=normalize_traffic_year(record.values["YEAR_ADT_030"]),
        truck_traffic_percent=normalize_optional_decimal(
            record.values["PERCENT_ADT_TRUCK_109"]
        ),
        lanes_on=normalize_optional_integer(record.values["TRAFFIC_LANES_ON_028A"]),
        bridge_length_m=normalize_optional_zero_sentinel_decimal(
            record.values["STRUCTURE_LEN_MT_049"]
        ),
        maximum_span_m=normalize_optional_zero_sentinel_decimal(
            record.values["MAX_SPAN_LEN_MT_048"]
        ),
        owner_code=normalize_code(record.values["OWNER_022"]),
        material_code=normalize_code(record.values["STRUCTURE_KIND_043A"]),
        design_type_code=normalize_code(record.values["STRUCTURE_TYPE_043B"]),
        inspection_month=inspection_month,
        inspection_year=inspection_year,
        deck_condition_code=normalize_condition_code(record.values["DECK_COND_058"]),
        superstructure_condition_code=normalize_condition_code(
            record.values["SUPERSTRUCTURE_COND_059"]
        ),
        substructure_condition_code=normalize_condition_code(
            record.values["SUBSTRUCTURE_COND_060"]
        ),
        culvert_condition_code=normalize_condition_code(
            record.values["CULVERT_COND_062"]
        ),
        overall_condition_code=normalize_overall_condition(
            record.values["BRIDGE_CONDITION"]
        ),
        lowest_condition_rating=normalize_lowest_condition_rating(
            record.values["LOWEST_RATING"]
        ),
    )


def _normalize_source_coordinate_code(value: str) -> str | None:
    stripped = value.strip()

    if stripped == "" or set(stripped) == {"0"}:
        return None

    return stripped


def _normalize_coordinate(
    value: str,
    *,
    degrees_digits: int,
    sign: int,
) -> Decimal | None:
    stripped = value.strip()

    if stripped == "" or set(stripped) == {"0"}:
        return None

    expected_length = degrees_digits + 6
    if len(stripped) != expected_length or not stripped.isdigit():
        raise NormalizationError(f"Cannot parse coordinate value: {value!r}")

    degrees = int(stripped[:degrees_digits])
    minutes = int(stripped[degrees_digits : degrees_digits + 2])
    seconds = Decimal(stripped[degrees_digits + 2 :]) / Decimal("100")

    decimal_degrees = (
        Decimal(degrees)
        + (Decimal(minutes) / Decimal("60"))
        + (seconds / Decimal("3600"))
    )

    return (decimal_degrees * sign).quantize(DECIMAL_PLACES_6)


def _is_all_zero_numeric_text(value: str) -> bool:
    return all(character in {"0", "."} for character in value) and "0" in value
