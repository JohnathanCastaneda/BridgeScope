import csv
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from bridgescope.db.models.bridge import Bridge
from bridgescope.db.models.bridge_dataset import BridgeDataset
from bridgescope.db.models.import_issue import ImportIssue
from bridgescope.db.models.import_run import ImportRun
from bridgescope.db.session import SessionLocal
from bridgescope.importer.orchestrator import ImportRequest, import_dataset

BASE_HEADERS = [
    "STATE_CODE_001",
    "STRUCTURE_NUMBER_008",
    "FACILITY_CARRIED_007",
    "FEATURES_DESC_006A",
    "COUNTY_CODE_003",
    "LAT_016",
    "LONG_017",
    "YEAR_BUILT_027",
    "YEAR_RECONSTRUCTED_106",
    "ADT_029",
    "YEAR_ADT_030",
    "PERCENT_ADT_TRUCK_109",
    "TRAFFIC_LANES_ON_028A",
    "STRUCTURE_LEN_MT_049",
    "MAX_SPAN_LEN_MT_048",
    "OWNER_022",
    "STRUCTURE_KIND_043A",
    "STRUCTURE_TYPE_043B",
    "DATE_OF_INSPECT_090",
    "DECK_COND_058",
    "SUPERSTRUCTURE_COND_059",
    "SUBSTRUCTURE_COND_060",
    "CULVERT_COND_062",
    "BRIDGE_CONDITION",
    "LOWEST_RATING",
]

BASE_ROW = {
    "STATE_CODE_001": "06",
    "STRUCTURE_NUMBER_008": "        06 0021",
    "FACILITY_CARRIED_007": "Interstate 5 & RR",
    "FEATURES_DESC_006A": "Shasta Lake",
    "COUNTY_CODE_003": "089",
    "LAT_016": "40454199",
    "LONG_017": "122190700",
    "YEAR_BUILT_027": "1941",
    "YEAR_RECONSTRUCTED_106": "2008",
    "ADT_029": "19500",
    "YEAR_ADT_030": "2009",
    "PERCENT_ADT_TRUCK_109": "29",
    "TRAFFIC_LANES_ON_028A": "4",
    "STRUCTURE_LEN_MT_049": "1093.6",
    "MAX_SPAN_LEN_MT_048": "192",
    "OWNER_022": "69",
    "STRUCTURE_KIND_043A": "3",
    "STRUCTURE_TYPE_043B": "09",
    "DATE_OF_INSPECT_090": "623",
    "DECK_COND_058": "5",
    "SUPERSTRUCTURE_COND_059": "7",
    "SUBSTRUCTURE_COND_060": "7",
    "CULVERT_COND_062": "N",
    "BRIDGE_CONDITION": "F",
    "LOWEST_RATING": "5",
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


def write_source(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as source_file:
        writer = csv.DictWriter(
            source_file,
            fieldnames=BASE_HEADERS,
            delimiter=",",
            quotechar="'",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def make_request(path: Path, source_sha256: str) -> ImportRequest:
    return ImportRequest(
        source_path=path,
        provider="FHWA",
        state_code="06",
        inventory_year=2025,
        source_format="fhwa_legacy_csv",
        source_specification="nbi_2025_legacy",
        source_url="https://example.test/CA25.txt",
        source_file_name=path.name,
        source_sha256=source_sha256,
        retrieved_at=datetime(2026, 8, 24, 4, 41, 55, tzinfo=timezone.utc),
    )


def row_with_structure(structure_number: str) -> dict[str, str]:
    return {**BASE_ROW, "STRUCTURE_NUMBER_008": structure_number}


def table_count(model: type) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(model))


def issue_count_by_severity(severity: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(ImportIssue)
            .where(ImportIssue.severity == severity)
        )


def clone_bridge(bridge: Bridge, **overrides) -> Bridge:
    values = {
        "dataset_id": bridge.dataset_id,
        "state_code": bridge.state_code,
        "structure_number": bridge.structure_number,
        "county_code": bridge.county_code,
        "facility_carried": bridge.facility_carried,
        "feature_crossed": bridge.feature_crossed,
        "latitude": bridge.latitude,
        "longitude": bridge.longitude,
        "source_latitude_code": bridge.source_latitude_code,
        "source_longitude_code": bridge.source_longitude_code,
        "year_built": bridge.year_built,
        "year_reconstructed": bridge.year_reconstructed,
        "average_daily_traffic": bridge.average_daily_traffic,
        "traffic_year": bridge.traffic_year,
        "truck_traffic_percent": bridge.truck_traffic_percent,
        "lanes_on": bridge.lanes_on,
        "bridge_length_m": bridge.bridge_length_m,
        "maximum_span_m": bridge.maximum_span_m,
        "owner_code": bridge.owner_code,
        "material_code": bridge.material_code,
        "design_type_code": bridge.design_type_code,
        "inspection_month": bridge.inspection_month,
        "inspection_year": bridge.inspection_year,
        "deck_condition_code": bridge.deck_condition_code,
        "superstructure_condition_code": bridge.superstructure_condition_code,
        "substructure_condition_code": bridge.substructure_condition_code,
        "culvert_condition_code": bridge.culvert_condition_code,
        "overall_condition_code": bridge.overall_condition_code,
        "lowest_condition_rating": bridge.lowest_condition_rating,
        "source_row_number": bridge.source_row_number,
    }
    values.update(overrides)

    return Bridge(**values)


def test_successful_single_record_import(tmp_path: Path) -> None:
    source = tmp_path / "single.csv"
    write_source(source, [BASE_ROW])

    result = import_dataset(make_request(source, "1".zfill(64)))

    assert result.status == "completed"
    assert result.rows_read == 1
    assert result.rows_inserted == 1
    assert result.rows_rejected == 0
    assert result.warnings_count == 0
    assert result.errors_count == 0

    with SessionLocal() as session:
        dataset = session.get_one(BridgeDataset, result.dataset_id)
        bridge = session.scalar(select(Bridge))
        import_run = session.get_one(ImportRun, result.import_run_id)

    assert dataset.is_active is True
    assert bridge.structure_number == "06 0021"
    assert bridge.dataset_id == dataset.id
    assert import_run.status == "completed"
    assert import_run.dataset_id == dataset.id
    assert table_count(ImportIssue) == 0


def test_valid_record_with_warning_imports_bridge_and_issue(tmp_path: Path) -> None:
    source = tmp_path / "warning.csv"
    write_source(source, [{**BASE_ROW, "OWNER_022": "99"}])

    result = import_dataset(make_request(source, "2".zfill(64)))

    assert result.status == "completed_with_warnings"
    assert result.rows_inserted == 1
    assert result.rows_rejected == 0
    assert result.warnings_count == 1
    assert result.errors_count == 0

    with SessionLocal() as session:
        issue = session.scalar(select(ImportIssue))
        import_run = session.get_one(ImportRun, result.import_run_id)

    assert table_count(Bridge) == 1
    assert issue.import_run_id == result.import_run_id
    assert issue.severity == "warning"
    assert issue.error_code == "UNKNOWN_OWNER_CODE"
    assert issue.row_number == 2
    assert issue.structure_number == "06 0021"
    assert import_run.summary == {"issue_counts_by_code": {"UNKNOWN_OWNER_CODE": 1}}


def test_invalid_record_is_rejected_and_persists_issue(tmp_path: Path) -> None:
    source = tmp_path / "invalid.csv"
    write_source(source, [{**BASE_ROW, "STRUCTURE_NUMBER_008": "   "}])

    result = import_dataset(make_request(source, "3".zfill(64)))

    assert result.status == "completed_with_warnings"
    assert result.rows_read == 1
    assert result.rows_inserted == 0
    assert result.rows_rejected == 1
    assert result.warnings_count == 0
    assert result.errors_count == 1
    assert table_count(Bridge) == 0

    with SessionLocal() as session:
        issue = session.scalar(select(ImportIssue))

    assert issue.severity == "error"
    assert issue.error_code == "MISSING_STRUCTURE_NUMBER"
    assert issue.row_number == 2
    assert issue.structure_number is None


def test_mixed_records_have_exact_counters(tmp_path: Path) -> None:
    source = tmp_path / "mixed.csv"
    rows = [
        row_with_structure("        06 0021"),
        row_with_structure("        06 0022"),
        {**row_with_structure("        06 0023"), "OWNER_022": "99"},
        {
            **row_with_structure("        06 0024"),
            "YEAR_BUILT_027": "2026",
            "YEAR_RECONSTRUCTED_106": "0",
        },
    ]
    write_source(source, rows)

    result = import_dataset(make_request(source, "4".zfill(64)))

    assert result.status == "completed_with_warnings"
    assert result.rows_read == 4
    assert result.rows_inserted == 3
    assert result.rows_rejected == 1
    assert result.rows_updated == 0
    assert result.rows_unchanged == 0
    assert result.warnings_count == 1
    assert result.errors_count == 1
    assert table_count(Bridge) == 3
    assert table_count(ImportIssue) == 2
    assert result.rows_read == result.rows_inserted + result.rows_rejected
    assert result.warnings_count == issue_count_by_severity("warning")
    assert result.errors_count == issue_count_by_severity("error")

    with SessionLocal() as session:
        import_run = session.get_one(ImportRun, result.import_run_id)
        issues = session.scalars(
            select(ImportIssue).order_by(
                ImportIssue.row_number,
                ImportIssue.error_code,
            )
        ).all()

    assert import_run.summary == {
        "issue_counts_by_code": {
            "UNKNOWN_OWNER_CODE": 1,
            "YEAR_BUILT_AFTER_INVENTORY_YEAR": 1,
        }
    }
    assert [
        (
            issue.import_run_id,
            issue.row_number,
            issue.structure_number,
            issue.field_name,
            issue.error_code,
            issue.severity,
        )
        for issue in issues
    ] == [
        (
            result.import_run_id,
            4,
            "06 0023",
            "owner_code",
            "UNKNOWN_OWNER_CODE",
            "warning",
        ),
        (
            result.import_run_id,
            5,
            "06 0024",
            "year_built",
            "YEAR_BUILT_AFTER_INVENTORY_YEAR",
            "error",
        ),
    ]


def test_fatal_failure_rolls_back_dataset_and_bridges_but_keeps_run(
    tmp_path: Path,
) -> None:
    source = tmp_path / "fatal.csv"
    rows = [
        row_with_structure("        06 0021"),
        row_with_structure("1234567890123456"),
    ]
    write_source(source, rows)

    with pytest.raises(Exception):
        import_dataset(make_request(source, "5".zfill(64)))

    assert table_count(BridgeDataset) == 0
    assert table_count(Bridge) == 0

    with SessionLocal() as session:
        import_run = session.scalar(select(ImportRun))
        issue = session.scalar(select(ImportIssue))

    assert import_run.status == "failed"
    assert import_run.dataset_id is None
    assert import_run.failure_message
    assert issue.import_run_id == import_run.id
    assert issue.severity == "fatal"
    assert issue.error_code == "IMPORT_FAILED"


def test_failed_replacement_import_does_not_deactivate_existing_dataset(
    tmp_path: Path,
) -> None:
    first_source = tmp_path / "first.csv"
    failing_source = tmp_path / "failing.csv"
    write_source(first_source, [BASE_ROW])
    write_source(
        failing_source,
        [
            row_with_structure("        06 0021"),
            row_with_structure("1234567890123456"),
        ],
    )

    first_result = import_dataset(make_request(first_source, "9".zfill(64)))

    with pytest.raises(Exception):
        import_dataset(make_request(failing_source, "10".zfill(64)))

    with SessionLocal() as session:
        first_dataset = session.get_one(BridgeDataset, first_result.dataset_id)
        failed_run = session.scalar(
            select(ImportRun).where(ImportRun.status == "failed")
        )

    assert first_dataset.is_active is True
    assert table_count(BridgeDataset) == 1
    assert table_count(Bridge) == 1
    assert failed_run.dataset_id is None
    assert failed_run.failure_message


def test_successful_import_switches_active_dataset(tmp_path: Path) -> None:
    first_source = tmp_path / "first.csv"
    second_source = tmp_path / "second.csv"
    write_source(first_source, [BASE_ROW])
    write_source(second_source, [BASE_ROW])

    first_result = import_dataset(make_request(first_source, "6".zfill(64)))
    second_result = import_dataset(make_request(second_source, "7".zfill(64)))

    with SessionLocal() as session:
        first_dataset = session.get_one(BridgeDataset, first_result.dataset_id)
        second_dataset = session.get_one(BridgeDataset, second_result.dataset_id)
        active_count = session.scalar(
            select(func.count())
            .select_from(BridgeDataset)
            .where(BridgeDataset.is_active.is_(True))
        )

    assert first_dataset.is_active is False
    assert second_dataset.is_active is True
    assert table_count(BridgeDataset) == 2
    assert table_count(Bridge) == 2
    assert active_count == 1


def test_duplicate_source_sha_skips_without_new_dataset_or_bridges(tmp_path: Path) -> None:
    source = tmp_path / "duplicate.csv"
    write_source(source, [BASE_ROW])

    first_result = import_dataset(make_request(source, "11".zfill(64)))
    second_result = import_dataset(make_request(source, "11".zfill(64)))

    assert first_result.status == "completed"
    assert second_result.status == "skipped_duplicate_file"
    assert second_result.dataset_id is None
    assert second_result.rows_read == 0
    assert second_result.rows_inserted == 0
    assert table_count(BridgeDataset) == 1
    assert table_count(Bridge) == 1
    assert table_count(ImportRun) == 2

    with SessionLocal() as session:
        second_run = session.get_one(ImportRun, second_result.import_run_id)

    assert second_run.dataset_id is None
    assert second_run.summary == {
        "duplicate_dataset_id": first_result.dataset_id,
        "issue_counts_by_code": {},
    }


def test_representative_sample_imports_successfully() -> None:
    repository_root = Path(__file__).resolve().parents[5]
    source = repository_root / "data/samples/ca_nbi_2025_sample.csv"

    result = import_dataset(make_request(source, "8".zfill(64)))

    assert result.status == "completed"
    assert result.rows_read == 29
    assert result.rows_inserted == 29
    assert result.rows_rejected == 0
    assert result.warnings_count == 0
    assert result.errors_count == 0
    assert table_count(Bridge) == 29
    assert table_count(ImportIssue) == 0


def test_database_rejects_invalid_bridge_even_if_validation_is_bypassed(
    tmp_path: Path,
) -> None:
    source = tmp_path / "valid.csv"
    write_source(source, [BASE_ROW])
    import_dataset(make_request(source, "12".zfill(64)))

    with pytest.raises(IntegrityError):
        with SessionLocal.begin() as session:
            bridge = session.scalar(select(Bridge))
            bridge.truck_traffic_percent = Decimal("150")


def test_database_rejects_duplicate_bridge_identity_within_dataset(
    tmp_path: Path,
) -> None:
    source = tmp_path / "valid.csv"
    write_source(source, [BASE_ROW])
    import_dataset(make_request(source, "13".zfill(64)))

    with pytest.raises(IntegrityError):
        with SessionLocal.begin() as session:
            bridge = session.scalar(select(Bridge))
            session.add(clone_bridge(bridge, source_row_number=99))
