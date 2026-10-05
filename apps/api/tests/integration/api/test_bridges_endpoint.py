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

