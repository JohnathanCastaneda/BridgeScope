from decimal import Decimal
from types import SimpleNamespace

from fastapi.encoders import jsonable_encoder

from bridgescope.api.v1.schemas.bridge import BridgeDetail, BridgeSummary
from bridgescope.api.v1.schemas.pagination import BridgePage


def test_bridge_summary_serializes_complete_fields() -> None:
    bridge = BridgeSummary(
        state_code="06",
        structure_number="06 0021",
        facility_carried="MAIN ST",
        feature_crossed="RIVER",
        county_code="067",
        year_built=1985,
        average_daily_traffic=25000,
        traffic_year=2023,
        overall_condition_code="G",
    )

    result = bridge.model_dump()

    assert result["structure_number"] == "06 0021"
    assert result["average_daily_traffic"] == 25000
    assert result["overall_condition_code"] == "G"


def test_bridge_summary_preserves_nullable_fields_and_internal_spaces() -> None:
    bridge = BridgeSummary(
        state_code="06",
        structure_number="06  0021",
        facility_carried=None,
        feature_crossed=None,
        county_code=None,
        year_built=None,
        average_daily_traffic=None,
        traffic_year=None,
        overall_condition_code=None,
    )

    result = bridge.model_dump()

    assert result["structure_number"] == "06  0021"
    assert result["facility_carried"] is None
    assert result["average_daily_traffic"] is None


def test_bridge_summary_validates_from_orm_style_attributes() -> None:
    orm_bridge = SimpleNamespace(
        state_code="06",
        structure_number="00000000000J003",
        facility_carried="COUNTY RD",
        feature_crossed=None,
        county_code="089",
        year_built=1972,
        average_daily_traffic=1000,
        traffic_year=2021,
        overall_condition_code="F",
    )

    schema = BridgeSummary.model_validate(orm_bridge)

    assert schema.structure_number == "00000000000J003"
    assert schema.overall_condition_code == "F"


def test_bridge_detail_supports_decimal_values_and_source_codes() -> None:
    bridge = BridgeDetail(
        state_code="06",
        structure_number="06 0021",
        facility_carried="Interstate 5 & RR",
        feature_crossed="Shasta Lake",
        county_code="089",
        latitude=Decimal("40.761664"),
        longitude=Decimal("-122.318611"),
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
        overall_condition_code="P",
        lowest_condition_rating=5,
    )

    dumped = bridge.model_dump()
    encoded = jsonable_encoder(bridge)

    assert dumped["latitude"] == Decimal("40.761664")
    assert dumped["culvert_condition_code"] == "N"
    assert dumped["overall_condition_code"] == "P"
    assert encoded["latitude"] == 40.761664
    assert encoded["truck_traffic_percent"] == 29
    assert "source_latitude_code" not in dumped
    assert "source_longitude_code" not in dumped
    assert "dataset_id" not in dumped


def test_bridge_page_serializes_summary_items() -> None:
    item = BridgeSummary(
        state_code="06",
        structure_number="06 0021",
        facility_carried="MAIN ST",
        feature_crossed="RIVER",
        county_code="067",
        year_built=1985,
        average_daily_traffic=25000,
        traffic_year=2023,
        overall_condition_code="G",
    )

    page = BridgePage(
        items=[item],
        page=1,
        page_size=25,
        total_items=25975,
        total_pages=1039,
    )

    result = page.model_dump()

    assert result["items"][0]["structure_number"] == "06 0021"
    assert result["page"] == 1
    assert result["page_size"] == 25
    assert result["total_items"] == 25975
    assert result["total_pages"] == 1039

