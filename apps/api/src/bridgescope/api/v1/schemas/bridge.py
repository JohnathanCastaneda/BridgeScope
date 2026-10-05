from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

BRIDGE_SCHEMA_CONFIG = ConfigDict(
    from_attributes=True,
)


class BridgeSummary(BaseModel):
    model_config = BRIDGE_SCHEMA_CONFIG

    state_code: str
    structure_number: str

    facility_carried: str | None
    feature_crossed: str | None
    county_code: str | None

    year_built: int | None

    average_daily_traffic: int | None
    traffic_year: int | None

    overall_condition_code: str | None


class BridgeDetail(BaseModel):
    model_config = BRIDGE_SCHEMA_CONFIG

    state_code: str
    structure_number: str

    facility_carried: str | None
    feature_crossed: str | None
    county_code: str | None

    latitude: Decimal | None
    longitude: Decimal | None

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

    @field_serializer(
        "latitude",
        "longitude",
        "truck_traffic_percent",
        "bridge_length_m",
        "maximum_span_m",
        when_used="json",
    )
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        if value is None:
            return None

        return float(value)

