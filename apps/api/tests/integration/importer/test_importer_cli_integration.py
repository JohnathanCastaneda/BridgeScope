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

