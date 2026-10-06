from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from bridgescope.db.models import Bridge, BridgeDataset, ImportIssue, ImportRun
from bridgescope.db.session import SessionLocal
from bridgescope.main import app

client = TestClient(app)

ACTIVE_DATASET_ERROR = {
    "error": {
        "code": "ACTIVE_DATASET_NOT_FOUND",
        "message": "Bridge data is currently unavailable.",
        "details": None,
    }
}


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
    county_code: str | None = "001",
    average_daily_traffic: int | None = 18400,
    traffic_year: int | None = 2023,
) -> Bridge:
    return Bridge(
        dataset_id=dataset_id,
        state_code=state_code,
        structure_number=structure_number,
        facility_carried=facility_carried,
        feature_crossed=feature_crossed,
        county_code=county_code,
        year_built=1978,
        average_daily_traffic=average_daily_traffic,
        traffic_year=traffic_year,
        source_row_number=source_row_number,
    )


def seed_active_dataset(bridges: list[Bridge]) -> BridgeDataset:
    with SessionLocal.begin() as session:
        dataset = create_dataset(source_sha256="1".zfill(64), is_active=True)
        session.add(dataset)
        session.flush()

        for bridge in bridges:
            bridge.dataset_id = dataset.id
            session.add(bridge)

    return dataset


def test_highest_adt_ranking_orders_by_reported_adt_descending() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="A",
                source_row_number=2,
                average_daily_traffic=100,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="B",
                source_row_number=3,
                average_daily_traffic=500,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="C",
                source_row_number=4,
                average_daily_traffic=300,
            ),
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    assert [
        (
            item["rank"],
            item["structure_number"],
            item["average_daily_traffic"],
        )
        for item in response.json()["items"]
    ] == [
        (1, "B", 500),
        (2, "C", 300),
        (3, "A", 100),
    ]


def test_highest_adt_ranking_uses_deterministic_tie_breaker() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="02",
                source_row_number=2,
                average_daily_traffic=500,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="01",
                source_row_number=3,
                average_daily_traffic=500,
            ),
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    assert [
        (item["rank"], item["structure_number"])
        for item in response.json()["items"]
    ] == [
        (1, "01"),
        (2, "02"),
    ]


def test_highest_adt_ranking_honors_limit_with_positional_ranks() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number=f"0{number}",
                source_row_number=number,
                average_daily_traffic=number * 100,
            )
            for number in range(1, 6)
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt?limit=3")

    assert response.status_code == 200
    assert response.json()["limit"] == 3
    assert [
        (item["rank"], item["structure_number"])
        for item in response.json()["items"]
    ] == [
        (1, "05"),
        (2, "04"),
        (3, "03"),
    ]


@pytest.mark.parametrize("query", ["limit=0", "limit=101"])
def test_highest_adt_ranking_rejects_invalid_limit(query: str) -> None:
    response = client.get(f"/api/v1/rankings/highest-adt?{query}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_highest_adt_ranking_limit_validation_uses_error_details() -> None:
    response = client.get("/api/v1/rankings/highest-adt?limit=101")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert any(
        detail["field"] == "query.limit"
        for detail in response.json()["error"]["details"]
    )


def test_highest_adt_ranking_accepts_max_limit() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="A",
                source_row_number=2,
                average_daily_traffic=100,
            )
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt?limit=100")

    assert response.status_code == 200
    assert response.json()["limit"] == 100


def test_highest_adt_ranking_excludes_null_adt_and_keeps_zero() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="A",
                source_row_number=2,
                average_daily_traffic=50,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="B",
                source_row_number=3,
                average_daily_traffic=0,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="C",
                source_row_number=4,
                average_daily_traffic=None,
            ),
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt?limit=10")

    assert response.status_code == 200
    assert [
        (item["structure_number"], item["average_daily_traffic"])
        for item in response.json()["items"]
    ] == [
        ("A", 50),
        ("B", 0),
    ]


def test_highest_adt_ranking_only_uses_active_dataset() -> None:
    with SessionLocal.begin() as session:
        inactive = create_dataset(source_sha256="2".zfill(64), is_active=False)
        active = create_dataset(source_sha256="3".zfill(64), is_active=True)
        session.add_all([inactive, active])
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=inactive.id,
                    structure_number="OLD",
                    source_row_number=2,
                    average_daily_traffic=900000,
                ),
                create_bridge(
                    dataset_id=active.id,
                    structure_number="CURRENT",
                    source_row_number=3,
                    average_daily_traffic=500000,
                ),
            ]
        )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    assert [
        item["structure_number"]
        for item in response.json()["items"]
    ] == ["CURRENT"]


def test_highest_adt_ranking_uses_active_revision_for_same_identity() -> None:
    with SessionLocal.begin() as session:
        inactive = create_dataset(source_sha256="4".zfill(64), is_active=False)
        active = create_dataset(source_sha256="5".zfill(64), is_active=True)
        session.add_all([inactive, active])
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=inactive.id,
                    structure_number="06 0021",
                    source_row_number=2,
                    average_daily_traffic=100000,
                ),
                create_bridge(
                    dataset_id=active.id,
                    structure_number="06 0021",
                    source_row_number=3,
                    average_daily_traffic=500000,
                    traffic_year=2018,
                ),
            ]
        )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    assert response.json()["items"][0]["structure_number"] == "06 0021"
    assert response.json()["items"][0]["average_daily_traffic"] == 500000


def test_highest_adt_ranking_preserves_traffic_year_context() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="A",
                source_row_number=2,
                average_daily_traffic=500000,
                traffic_year=2018,
            ),
            create_bridge(
                dataset_id=0,
                structure_number="B",
                source_row_number=3,
                average_daily_traffic=400000,
                traffic_year=None,
            ),
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    assert [
        (item["average_daily_traffic"], item["traffic_year"])
        for item in response.json()["items"]
    ] == [
        (500000, 2018),
        (400000, None),
    ]


def test_highest_adt_ranking_returns_503_when_no_active_dataset_exists() -> None:
    with SessionLocal.begin() as session:
        session.add(create_dataset(source_sha256="6".zfill(64), is_active=False))

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 503
    assert response.json() == ACTIVE_DATASET_ERROR


def test_highest_adt_ranking_returns_empty_items_for_no_rankable_bridges() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="A",
                source_row_number=2,
                average_daily_traffic=None,
            )
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "limit": 25,
    }


def test_highest_adt_ranking_does_not_expose_internal_database_fields() -> None:
    seed_active_dataset(
        [
            create_bridge(
                dataset_id=0,
                structure_number="A",
                source_row_number=2,
                average_daily_traffic=100,
            )
        ]
    )

    response = client.get("/api/v1/rankings/highest-adt")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert set(item) == {
        "rank",
        "state_code",
        "structure_number",
        "facility_carried",
        "feature_crossed",
        "county_code",
        "average_daily_traffic",
        "traffic_year",
    }
    assert "id" not in item
    assert "dataset_id" not in item
    assert "source_row_number" not in item
    assert "created_at" not in item
    assert "updated_at" not in item


def test_highest_adt_ranking_openapi_describes_reported_adt() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/v1/rankings/highest-adt"]["get"]
    assert operation["summary"] == "Rank bridges by reported Average Daily Traffic"
    assert "not live traffic" in operation["description"]
