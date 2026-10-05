from datetime import datetime, timezone

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import MultipleResultsFound

from bridgescope.db.models import Bridge, BridgeDataset, ImportIssue, ImportRun
from bridgescope.db.session import SessionLocal
from bridgescope.services.bridges import (
    count_active_bridges,
    count_bridges_for_dataset,
    get_active_bridges,
    get_active_dataset,
    get_bridges_for_dataset,
    require_active_dataset,
)
from bridgescope.services.errors import ActiveDatasetNotFoundError


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
    dataset = BridgeDataset(
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

    return dataset


def create_bridge(
    *,
    dataset_id: int,
    state_code: str = "06",
    structure_number: str,
    source_row_number: int,
) -> Bridge:
    return Bridge(
        dataset_id=dataset_id,
        state_code=state_code,
        structure_number=structure_number,
        county_code="089",
        year_built=1985,
        average_daily_traffic=1000,
        source_row_number=source_row_number,
    )


def test_get_active_dataset_returns_active_dataset_for_state() -> None:
    with SessionLocal.begin() as session:
        inactive = create_dataset(source_sha256="1".zfill(64), is_active=False)
        active = create_dataset(source_sha256="2".zfill(64), is_active=True)
        other_state = create_dataset(
            source_sha256="3".zfill(64),
            state_code="08",
            is_active=True,
        )
        session.add_all([inactive, active, other_state])

    with SessionLocal() as session:
        dataset = get_active_dataset(session, state_code="06")

    assert dataset.id == active.id
    assert dataset.id != inactive.id
    assert dataset.id != other_state.id


def test_get_active_dataset_returns_none_when_no_active_dataset_exists() -> None:
    with SessionLocal.begin() as session:
        session.add(create_dataset(source_sha256="4".zfill(64), is_active=False))

    with SessionLocal() as session:
        assert get_active_dataset(session, state_code="06") is None


def test_require_active_dataset_raises_service_exception_when_missing() -> None:
    with SessionLocal() as session:
        with pytest.raises(
            ActiveDatasetNotFoundError,
            match="No active dataset exists for state 06.",
        ):
            require_active_dataset(session, state_code="06")


def test_get_active_dataset_detects_multiple_active_datasets() -> None:
    with SessionLocal.begin() as session:
        session.add_all(
            [
                create_dataset(source_sha256="5".zfill(64), is_active=True),
                create_dataset(source_sha256="6".zfill(64), is_active=True),
            ]
        )

    with SessionLocal() as session:
        with pytest.raises(MultipleResultsFound):
            get_active_dataset(session, state_code="06")


def test_get_bridges_for_dataset_isolates_dataset_rows() -> None:
    with SessionLocal.begin() as session:
        dataset_a = create_dataset(source_sha256="7".zfill(64), is_active=True)
        dataset_b = create_dataset(source_sha256="8".zfill(64), is_active=False)
        session.add_all([dataset_a, dataset_b])
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=dataset_a.id,
                    structure_number="06 0022",
                    source_row_number=2,
                ),
                create_bridge(
                    dataset_id=dataset_a.id,
                    structure_number="06 0021",
                    source_row_number=3,
                ),
                create_bridge(
                    dataset_id=dataset_b.id,
                    structure_number="06 9999",
                    source_row_number=4,
                ),
            ]
        )

    with SessionLocal() as session:
        bridges = get_bridges_for_dataset(
            session,
            dataset_id=dataset_a.id,
            offset=0,
            limit=10,
        )

    assert [bridge.structure_number for bridge in bridges] == [
        "06 0021",
        "06 0022",
    ]


def test_get_bridges_for_dataset_uses_deterministic_ordering_and_pagination() -> None:
    with SessionLocal.begin() as session:
        dataset = create_dataset(source_sha256="9".zfill(64), is_active=True)
        session.add(dataset)
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=dataset.id,
                    state_code="06",
                    structure_number="06 0030",
                    source_row_number=2,
                ),
                create_bridge(
                    dataset_id=dataset.id,
                    state_code="01",
                    structure_number="01 0004",
                    source_row_number=3,
                ),
                create_bridge(
                    dataset_id=dataset.id,
                    state_code="06",
                    structure_number="06 0021",
                    source_row_number=4,
                ),
                create_bridge(
                    dataset_id=dataset.id,
                    state_code="01",
                    structure_number="01 0002",
                    source_row_number=5,
                ),
                create_bridge(
                    dataset_id=dataset.id,
                    state_code="06",
                    structure_number="06 0040",
                    source_row_number=6,
                ),
            ]
        )

    with SessionLocal() as session:
        first_page = get_bridges_for_dataset(
            session,
            dataset_id=dataset.id,
            offset=0,
            limit=2,
        )
        second_page = get_bridges_for_dataset(
            session,
            dataset_id=dataset.id,
            offset=2,
            limit=2,
        )

    assert [
        (bridge.state_code, bridge.structure_number)
        for bridge in first_page
    ] == [
        ("01", "01 0002"),
        ("01", "01 0004"),
    ]
    assert [
        (bridge.state_code, bridge.structure_number)
        for bridge in second_page
    ] == [
        ("06", "06 0021"),
        ("06", "06 0030"),
    ]


def test_count_bridges_for_dataset_is_scoped_to_dataset() -> None:
    with SessionLocal.begin() as session:
        dataset_a = create_dataset(source_sha256="10".zfill(64), is_active=True)
        dataset_b = create_dataset(source_sha256="11".zfill(64), is_active=False)
        session.add_all([dataset_a, dataset_b])
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=dataset_a.id,
                    structure_number="06 0021",
                    source_row_number=2,
                ),
                create_bridge(
                    dataset_id=dataset_a.id,
                    structure_number="06 0022",
                    source_row_number=3,
                ),
                create_bridge(
                    dataset_id=dataset_a.id,
                    structure_number="06 0023",
                    source_row_number=4,
                ),
                create_bridge(
                    dataset_id=dataset_a.id,
                    structure_number="06 0024",
                    source_row_number=5,
                ),
                create_bridge(
                    dataset_id=dataset_b.id,
                    structure_number="06 9991",
                    source_row_number=6,
                ),
                create_bridge(
                    dataset_id=dataset_b.id,
                    structure_number="06 9992",
                    source_row_number=7,
                ),
            ]
        )

    with SessionLocal() as session:
        assert count_bridges_for_dataset(session, dataset_id=dataset_a.id) == 4
        assert count_bridges_for_dataset(session, dataset_id=dataset_b.id) == 2


def test_active_bridge_helpers_scope_to_active_dataset() -> None:
    with SessionLocal.begin() as session:
        inactive = create_dataset(source_sha256="12".zfill(64), is_active=False)
        active = create_dataset(source_sha256="13".zfill(64), is_active=True)
        session.add_all([inactive, active])
        session.flush()
        session.add_all(
            [
                create_bridge(
                    dataset_id=inactive.id,
                    structure_number="06 9999",
                    source_row_number=2,
                ),
                create_bridge(
                    dataset_id=active.id,
                    structure_number="06 0022",
                    source_row_number=3,
                ),
                create_bridge(
                    dataset_id=active.id,
                    structure_number="06 0021",
                    source_row_number=4,
                ),
            ]
        )

    with SessionLocal() as session:
        bridges = get_active_bridges(session, offset=0, limit=10)
        count = count_active_bridges(session)

    assert [bridge.structure_number for bridge in bridges] == [
        "06 0021",
        "06 0022",
    ]
    assert count == 2

