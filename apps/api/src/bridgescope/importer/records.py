from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RawBridgeRecord:
    row_number: int
    values: dict[str, str]


@dataclass(frozen=True)
class NormalizedBridgeRecord:
    source_row_number: int

    state_code: str
    structure_number: str
    county_code: str

    facility_carried: str | None
    feature_crossed: str | None

    latitude: Decimal | None
    longitude: Decimal | None
    source_latitude_code: str | None
    source_longitude_code: str | None

    year_built: int | None
    year_reconstructed: int | None

    average_daily_traffic: int | None
    traffic_year: int | None
    truck_traffic_percent: Decimal | None
    lanes_on: int | None

    bridge_length_m: Decimal | None
    maximum_span_m: Decimal | None

    owner_code: str | None
    material_code: str | None
    design_type_code: str | None

    inspection_month: int | None
    inspection_year: int | None

    deck_condition_code: str | None
    superstructure_condition_code: str | None
    substructure_condition_code: str | None
    culvert_condition_code: str | None
    overall_condition_code: str | None

    lowest_condition_rating: int | None
