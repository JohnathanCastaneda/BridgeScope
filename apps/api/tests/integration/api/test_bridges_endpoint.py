from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from bridgescope.db.models import Bridge, BridgeDataset, ImportIssue, ImportRun
from bridgescope.db.session import SessionLocal
from bridgescope.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_import_tables() -> None:
    _clean_import_tables()
    yield
    _clean_import_tables()


def _clean_import_tables() -> None:
    with SessionLocal.begin() as session:
        session.execute(delete(ImportIssue))
        session.execute(delete(Bridge))
        session.execute(delete(ImportRun))
        session.execute(delete(BridgeDataset))


def create_dataset(
    *,
    source_sha256: str,
    state_code: str = "06",
    inventory_year: int = 2025,
    is_active: bool = False,
) -> BridgeDataset:
    return BridgeDataset(
        provider="FHWA",
        state_code=state_code,
        inventory_year=inventory_year,
        source_format="fhwa_legacy_csv",
        source_specification="nbi_2025_legacy",
        source_url="https://example.test/CA25.txt",
        source_file_name="CA25.txt",
        source_sha256=source_sha256,
        retrieved_at=datetime(2026, 8, 24, 4, 41, 55, tzinfo=timezone.utc),
        is_active=is_active,
    )


def create_bridge(
    *,
    dataset_id: int,
    structure_number: str,
    source_row_number: int,
    state_code: str = "06",
    facility_carried: str | None = "MAIN ST",
    feature_crossed: str | None = "RIVER",
    county_code: str = "001",
    year_built: int = 1978,
    average_daily_traffic: int | None = 18400,
    traffic_year: int | None = 2023,
    overall_condition_code: str | None = "G",
) -> Bridge:
    return Bridge(
        dataset_id=dataset_id,
        state_code=state_code,
        structure_number=structure_number,
        county_code=county_code,
        facility_carried=facility_carried,
        feature_crossed=feature_crossed,
        year_built=year_built,
        average_daily_traffic=average_daily_traffic,
        traffic_year=traffic_year,
        overall_condition_code=overall_condition_code,
        source_row_number=source_row_number,
    )


def seed_active_dataset(
    bridges: list[Bridge],
) -> BridgeDataset:
    with SessionLocal.begin() as session:
        dataset = create_dataset(source_sha256="1".zfill(64), is_active=True)
        session.add(dataset)
        session.flush()

        for bridge in bridges:
            bridge.dataset_id = dataset.id
            session.add(bridge)

    return dataset


def test_list_bridges_returns_active_dataset_page() -> None:
    seed_active_dataset(
        [
            create_bridge(dataset_id=0, structure_number="06 0030", source_row_number=2),
            create_bridge(
                dataset_id=0,
                structure_number="06 0021",
                source_row_number=3,
                average_daily_traffic=50000,
                traffic_year=2017,
                overall_condition_code="F",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0040",
                source_row_number=4,
                overall_condition_code=None,
            ),
        ]
    )

    response = client.get("/api/v1/bridges")

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 25
    assert payload["total_items"] == 3
    assert payload["total_pages"] == 1
    assert [item["structure_number"] for item in payload["items"]] == [
        "06 0021",
        "06 0030",
        "06 0040",
    ]
    assert payload["items"][0]["average_daily_traffic"] == 50000
    assert payload["items"][0]["traffic_year"] == 2017
    assert payload["items"][0]["overall_condition_code"] == "F"


def test_list_bridges_searches_facility_feature_and_structure_number() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="06 1001",
                source_row_number=2,
                facility_carried="SACRAMENTO AVE",
                feature_crossed="LOCAL ROAD",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 1002",
                source_row_number=3,
                facility_carried="MAIN ST",
                feature_crossed="Sacramento River",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="SAC 100",
                source_row_number=4,
                facility_carried="COUNTY RD",
                feature_crossed="CANAL",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 1003",
                source_row_number=5,
                facility_carried="ELM ST",
                feature_crossed="CREEK",
            ),
        ]
    )

    response = client.get("/api/v1/bridges", params={"q": "  sacramento  "})

    assert response.status_code == 200
    assert response.json()["total_items"] == 2
    assert [item["structure_number"] for item in response.json()["items"]] == [
        "06 1001",
        "06 1002",
    ]


def test_list_bridges_search_preserves_internal_spaces_in_structure_number() -> None:
    seed_active_dataset(
        [
            create_bridge(dataset_id=0, structure_number="06 0021", source_row_number=2),
            create_bridge(dataset_id=0, structure_number="060021", source_row_number=3),
        ]
    )

    response = client.get("/api/v1/bridges", params={"q": "06 0021"})

    assert response.status_code == 200
    assert [item["structure_number"] for item in response.json()["items"]] == [
        "06 0021",
    ]


def test_list_bridges_filters_by_county_year_range_adt_range_and_condition() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="06 0001",
                source_row_number=2,
                county_code="067",
                year_built=1940,
                average_daily_traffic=10000,
                overall_condition_code="G",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0002",
                source_row_number=3,
                county_code="067",
                year_built=1950,
                average_daily_traffic=50000,
                overall_condition_code="F",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0003",
                source_row_number=4,
                county_code="067",
                year_built=1975,
                average_daily_traffic=75000,
                overall_condition_code="F",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0004",
                source_row_number=5,
                county_code="067",
                year_built=2000,
                average_daily_traffic=100000,
                overall_condition_code="P",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0005",
                source_row_number=6,
                county_code="001",
                year_built=2010,
                average_daily_traffic=150000,
                overall_condition_code="F",
            ),
        ]
    )

    response = client.get(
        "/api/v1/bridges"
        "?county=067&year_built_min=1950&year_built_max=2000"
        "&adt_min=50000&adt_max=100000&condition=F"
    )

    assert response.status_code == 200
    assert response.json()["total_items"] == 2
    assert [item["structure_number"] for item in response.json()["items"]] == [
        "06 0002",
        "06 0003",
    ]


def test_list_bridges_combines_filters_with_search_using_and() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="06 0001",
                source_row_number=2,
                facility_carried="RIVER RD",
                feature_crossed="SLOUGH",
                county_code="067",
                year_built=1960,
                average_daily_traffic=60000,
                overall_condition_code="F",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0002",
                source_row_number=3,
                facility_carried="RIVER RD",
                feature_crossed="SLOUGH",
                county_code="001",
                year_built=1960,
                average_daily_traffic=60000,
                overall_condition_code="F",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0003",
                source_row_number=4,
                facility_carried="MARKET ST",
                feature_crossed="RIVER",
                county_code="067",
                year_built=1940,
                average_daily_traffic=60000,
                overall_condition_code="F",
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0004",
                source_row_number=5,
                facility_carried="RIVER RD",
                feature_crossed="SLOUGH",
                county_code="067",
                year_built=1960,
                average_daily_traffic=60000,
                overall_condition_code="G",
            ),
        ]
    )

    response = client.get(
        "/api/v1/bridges"
        "?q=river&county=067&year_built_min=1950&adt_min=50000&condition=F"
    )

    assert response.status_code == 200
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["structure_number"] == "06 0001"


def test_list_bridges_filters_before_counting_and_pagination() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number=f"06 00{number}",
                source_row_number=number,
                facility_carried="RIVER RD",
                feature_crossed="SLOUGH",
            )
            for number in range(1, 6)
        ]
        + [
            create_bridge(
                dataset_id=0,
                structure_number="06 9999",
                source_row_number=99,
                facility_carried="HILL RD",
                feature_crossed="CANYON",
            )
        ]
    )

    response = client.get("/api/v1/bridges?q=river&page=2&page_size=2")

    assert response.status_code == 200
    assert response.json()["total_items"] == 5
    assert response.json()["total_pages"] == 3
    assert [item["structure_number"] for item in response.json()["items"]] == [
        "06 003",
        "06 004",
    ]


def test_list_bridges_sorts_by_adt_desc_with_tie_breaker_and_nulls_last() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="06 0004",
                source_row_number=2,
                average_daily_traffic=100,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0002",
                source_row_number=3,
                average_daily_traffic=500,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0001",
                source_row_number=4,
                average_daily_traffic=500,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0003",
                source_row_number=5,
                average_daily_traffic=200,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0005",
                source_row_number=6,
                average_daily_traffic=None,
            ),
        ]
    )

    response = client.get("/api/v1/bridges?sort=adt_desc")

    assert response.status_code == 200
    assert [
        (item["structure_number"], item["average_daily_traffic"])
        for item in response.json()["items"]
    ] == [
        ("06 0001", 500),
        ("06 0002", 500),
        ("06 0003", 200),
        ("06 0004", 100),
        ("06 0005", None),
    ]


def test_list_bridges_sorts_by_year_built_ascending() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="06 0003",
                source_row_number=2,
                year_built=2000,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0001",
                source_row_number=3,
                year_built=1950,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="06 0002",
                source_row_number=4,
                year_built=1950,
            ),
        ]
    )

    response = client.get("/api/v1/bridges?sort=year_built_asc")

    assert response.status_code == 200
    assert [item["structure_number"] for item in response.json()["items"]] == [
        "06 0001",
        "06 0002",
        "06 0003",
    ]


def test_list_bridges_paginates_active_dataset() -> None:
    seed_active_dataset(
        [
            create_bridge(dataset_id=0, structure_number="06 0005", source_row_number=2),
            create_bridge(dataset_id=0, structure_number="06 0001", source_row_number=3),
            create_bridge(dataset_id=0, structure_number="06 0003", source_row_number=4),
            create_bridge(dataset_id=0, structure_number="06 0002", source_row_number=5),
            create_bridge(dataset_id=0, structure_number="06 0004", source_row_number=6),
        ]
    )

    first_page = client.get("/api/v1/bridges?page=1&page_size=2")
    second_page = client.get("/api/v1/bridges?page=2&page_size=2")
    third_page = client.get("/api/v1/bridges?page=3&page_size=2")

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert third_page.status_code == 200
    assert first_page.json()["total_items"] == 5
    assert first_page.json()["total_pages"] == 3
    assert [item["structure_number"] for item in first_page.json()["items"]] == [
        "06 0001",
        "06 0002",
    ]
    assert [item["structure_number"] for item in second_page.json()["items"]] == [
        "06 0003",
        "06 0004",
    ]
    assert [item["structure_number"] for item in third_page.json()["items"]] == [
        "06 0005",
    ]


def test_list_bridges_returns_empty_items_for_page_beyond_range() -> None:
    seed_active_dataset(
        [
            create_bridge(dataset_id=0, structure_number="06 0001", source_row_number=2),
            create_bridge(dataset_id=0, structure_number="06 0002", source_row_number=3),
            create_bridge(dataset_id=0, structure_number="06 0003", source_row_number=4),
        ]
    )

    response = client.get("/api/v1/bridges?page=10&page_size=2")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 10,
        "page_size": 2,
        "total_items": 3,
        "total_pages": 2,
    }


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page_size=0",
        "page_size=101",
        "county=67",
        "county=ABC",
        "condition=X",
        "sort=banana",
        "year_built_min=2000&year_built_max=1900",
        "adt_min=100000&adt_max=50000",
    ],
)
def test_list_bridges_rejects_invalid_pagination(query: str) -> None:
    response = client.get(f"/api/v1/bridges?{query}")

    assert response.status_code == 422


def test_list_bridges_accepts_max_page_size() -> None:
    seed_active_dataset(
        [create_bridge(dataset_id=0, structure_number="06 0001", source_row_number=2)]
    )

    response = client.get("/api/v1/bridges?page_size=100")

    assert response.status_code == 200
    assert response.json()["page_size"] == 100


def test_list_bridges_only_returns_active_dataset_rows() -> None:
    with SessionLocal.begin() as session:
        inactive = create_dataset(source_sha256="2".zfill(64), is_active=False)
        active = create_dataset(source_sha256="3".zfill(64), is_active=True)
        session.add_all([inactive, active])
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=inactive.id,
                    structure_number="OLD 0001",
                    source_row_number=2,
                ),
                create_bridge(
                    dataset_id=active.id,
                    structure_number="CURRENT",
                    source_row_number=3,
                    overall_condition_code="P",
                ),
            ]
        )

    response = client.get("/api/v1/bridges")

    assert response.status_code == 200
    assert [item["structure_number"] for item in response.json()["items"]] == [
        "CURRENT"
    ]
    assert response.json()["items"][0]["overall_condition_code"] == "P"


def test_list_bridges_returns_503_when_no_active_dataset_exists() -> None:
    with SessionLocal.begin() as session:
        session.add(create_dataset(source_sha256="4".zfill(64), is_active=False))

    response = client.get("/api/v1/bridges")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "No active dataset exists for state 06.",
    }


def test_list_bridges_does_not_expose_internal_database_fields() -> None:
    seed_active_dataset(
        [create_bridge(dataset_id=0, structure_number="06 0021", source_row_number=2)]
    )

    response = client.get("/api/v1/bridges")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert set(item) == {
        "state_code",
        "structure_number",
        "facility_carried",
        "feature_crossed",
        "county_code",
        "year_built",
        "average_daily_traffic",
        "traffic_year",
        "overall_condition_code",
    }
    assert "id" not in item
    assert "dataset_id" not in item
    assert "source_latitude_code" not in item
    assert "source_longitude_code" not in item
    assert "created_at" not in item
    assert "updated_at" not in item

