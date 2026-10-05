from pathlib import Path

from bridgescope.importer.readers.fhwa_legacy import (
    REQUIRED_FIELDS,
    read_fhwa_legacy_file,
)


def test_reader_accepts_representative_sample_fixture() -> None:
    repository_root = Path(__file__).resolve().parents[5]
    path = repository_root / "data/samples/ca_nbi_2025_sample.csv"

    records = list(read_fhwa_legacy_file(path))

    assert len(records) == 29
    assert all(REQUIRED_FIELDS <= set(record.values) for record in records)
