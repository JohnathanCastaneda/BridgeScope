from bridgescope.importer.orchestrator import ImportResult
from bridgescope.importer.summary import format_import_summary


def make_result(**overrides) -> ImportResult:
    values = {
        "import_run_id": 12,
        "dataset_id": 34,
        "status": "completed_with_warnings",
        "rows_read": 100,
        "rows_inserted": 98,
        "rows_updated": 0,
        "rows_unchanged": 0,
        "rows_rejected": 2,
        "warnings_count": 4,
        "errors_count": 2,
        "source_file_name": "CA25.txt",
        "source_sha256": "6f9cf692cd82ff9ad57579e3f746bdfc55126882933d0e2815dabe6cb465f5",
        "provider": "FHWA",
        "state_code": "06",
        "state_name": "California",
        "inventory_year": 2025,
        "issue_counts_by_code": {
            "UNKNOWN_OWNER_CODE": 4,
            "COORDINATE_OUTSIDE_EXPECTED_STATE": 2,
        },
    }
    values.update(overrides)
    return ImportResult(**values)


def test_format_import_summary_includes_counts_metadata_and_issue_breakdown() -> None:
    summary = format_import_summary(make_result())

    assert "BridgeScope NBI Import" in summary
    assert "Source file:      CA25.txt" in summary
    assert "Inventory year:   2025" in summary
    assert "State:            California (06)" in summary
    assert "SHA-256:          6f9cf692cd82..." in summary
    assert "Rows read:        100" in summary
    assert "Inserted:         98" in summary
    assert "Rejected:         2" in summary
    assert "Warnings:         4" in summary
    assert "Errors:           2" in summary
    assert "UNKNOWN_OWNER_CODE" in summary
    assert "COORDINATE_OUTSIDE_EXPECTED_STATE" in summary
    assert "Status:           completed_with_warnings" in summary
    assert "Dataset ID:       34" in summary
    assert "Import run ID:    12" in summary


def test_format_duplicate_summary_explains_that_no_rows_were_imported() -> None:
    summary = format_import_summary(
        make_result(
            dataset_id=None,
            status="skipped_duplicate_file",
            rows_read=0,
            rows_inserted=0,
            rows_rejected=0,
            warnings_count=0,
            errors_count=0,
            issue_counts_by_code={},
        )
    )

    assert "Status:           skipped_duplicate_file" in summary
    assert "No bridge records were imported" in summary
    assert "Import run ID:    12" in summary
    assert "Dataset ID:" not in summary

