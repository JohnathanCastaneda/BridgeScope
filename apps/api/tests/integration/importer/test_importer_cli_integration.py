import csv
from io import StringIO
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select

from bridgescope.db.models.bridge import Bridge
from bridgescope.db.models.bridge_dataset import BridgeDataset
from bridgescope.db.models.import_issue import ImportIssue
from bridgescope.db.models.import_run import ImportRun
from bridgescope.db.session import SessionLocal
from bridgescope.importer.cli import main

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


def table_count(model: type) -> int:
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(model))


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


def sample_source_path() -> Path:
    repository_root = Path(__file__).resolve().parents[5]
    return repository_root / "data/samples/ca_nbi_2025_sample.csv"


def test_cli_imports_sample_and_prints_summary() -> None:
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(["--input", str(sample_source_path())], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert "BridgeScope NBI Import" in stdout.getvalue()
    assert "Rows read:        29" in stdout.getvalue()
    assert "Inserted:         29" in stdout.getvalue()
    assert "Status:           completed" in stdout.getvalue()
    assert table_count(BridgeDataset) == 1
    assert table_count(Bridge) == 29
    assert table_count(ImportRun) == 1


def test_cli_skips_duplicate_source_file() -> None:
    source_path = sample_source_path()
    first_stdout = StringIO()
    second_stdout = StringIO()

    assert main(["--input", str(source_path)], stdout=first_stdout, stderr=StringIO()) == 0
    assert main(["--input", str(source_path)], stdout=second_stdout, stderr=StringIO()) == 0

    assert "Status:           skipped_duplicate_file" in second_stdout.getvalue()
    assert "No bridge records were imported" in second_stdout.getvalue()
    assert table_count(BridgeDataset) == 1
    assert table_count(Bridge) == 29
    assert table_count(ImportRun) == 2

    with SessionLocal() as session:
        statuses = list(
            session.scalars(select(ImportRun.status).order_by(ImportRun.id))
        )

    assert statuses == ["completed", "skipped_duplicate_file"]


def test_cli_missing_input_file_returns_failure_without_audit_run(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.txt"
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(["--input", str(missing_path)], stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "BridgeScope import failed." in stderr.getvalue()
    assert "Source: missing.txt" in stderr.getvalue()
    assert table_count(BridgeDataset) == 0
    assert table_count(Bridge) == 0
    assert table_count(ImportRun) == 0


def test_cli_invalid_source_returns_failure_and_failed_audit_run(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.csv"
    invalid_path.write_text("NOT_A_REQUIRED_HEADER\nvalue\n", encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(["--input", str(invalid_path)], stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "BridgeScope import failed." in stderr.getvalue()
    assert "missing required columns" in stderr.getvalue().lower()
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


def test_cli_warning_import_exits_successfully(tmp_path: Path) -> None:
    source_path = tmp_path / "warning.csv"
    write_source(source_path, [{**BASE_ROW, "OWNER_022": "99"}])
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(["--input", str(source_path)], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert "Status:           completed_with_warnings" in stdout.getvalue()
    assert "Warnings:         1" in stdout.getvalue()
    assert table_count(BridgeDataset) == 1
    assert table_count(Bridge) == 1

    with SessionLocal() as session:
        issue = session.scalar(select(ImportIssue))

    assert issue.severity == "warning"
    assert issue.error_code == "UNKNOWN_OWNER_CODE"

