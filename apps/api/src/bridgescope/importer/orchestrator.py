from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update

from bridgescope.db.models.bridge_dataset import BridgeDataset
from bridgescope.db.models.import_issue import ImportIssue
from bridgescope.db.models.import_run import ImportRun
from bridgescope.db.session import SessionLocal
from bridgescope.importer.errors import NormalizationError
from bridgescope.importer.normalize import normalize_bridge_record
from bridgescope.importer.persistence import (
    bridge_from_normalized,
    import_issue_from_validation,
)
from bridgescope.importer.readers.fhwa_legacy import read_fhwa_legacy_file
from bridgescope.importer.records import (
    IssueSeverity,
    ValidationIssue,
)
from bridgescope.importer.validation import (
    ValidationContext,
    validate_bridge_record,
)


@dataclass(frozen=True)
class ImportRequest:
    source_path: Path
    provider: str
    state_code: str
    inventory_year: int
    source_format: str
    source_specification: str
    source_url: str
    source_file_name: str
    source_sha256: str
    retrieved_at: datetime
    state_name: str | None = None


@dataclass(frozen=True)
class ImportResult:
    import_run_id: int
    dataset_id: int | None
    status: str
    rows_read: int
    rows_inserted: int
    rows_updated: int
    rows_unchanged: int
    rows_rejected: int
    warnings_count: int
    errors_count: int
    source_file_name: str | None = None
    source_sha256: str | None = None
    provider: str | None = None
    state_code: str | None = None
    state_name: str | None = None
    inventory_year: int | None = None
    issue_counts_by_code: Mapping[str, int] = field(default_factory=dict)
    failure_message: str | None = None


@dataclass
class _ImportCounters:
    rows_read: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_unchanged: int = 0
    rows_rejected: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    issue_counts_by_code: Counter[str] = field(default_factory=Counter)


def import_dataset(
    request: ImportRequest,
    *,
    session_factory=SessionLocal,
) -> ImportResult:
    import_run_id = create_import_run(request, session_factory=session_factory)

    try:
        return execute_import(
            import_run_id=import_run_id,
            request=request,
            session_factory=session_factory,
        )
    except Exception as exc:
        mark_import_failed(
            import_run_id,
            str(exc),
            session_factory=session_factory,
        )
        raise


def create_import_run(
    request: ImportRequest,
    *,
    session_factory=SessionLocal,
) -> int:
    with session_factory.begin() as session:
        import_run = ImportRun(
            source_file_name=request.source_file_name,
            source_sha256=request.source_sha256,
            status="running",
            started_at=_now(),
        )
        session.add(import_run)
        session.flush()

        return import_run.id


def execute_import(
    *,
    import_run_id: int,
    request: ImportRequest,
    session_factory=SessionLocal,
) -> ImportResult:
    counters = _ImportCounters()
    context = ValidationContext(
        inventory_year=request.inventory_year,
        state_code=request.state_code,
    )

    with session_factory.begin() as session:
        import_run = session.get_one(ImportRun, import_run_id)
        existing_dataset = session.scalar(
            select(BridgeDataset).where(
                BridgeDataset.source_sha256 == request.source_sha256
            )
        )

        if existing_dataset is not None:
            _finalize_duplicate_import_run(import_run, existing_dataset.id)
            return _result_from_import_run(import_run, request)

        dataset = _create_dataset(request)
        session.add(dataset)
        session.flush()

        import_run.dataset_id = dataset.id

        for raw_record in read_fhwa_legacy_file(request.source_path):
            counters.rows_read += 1

            try:
                normalized_record = normalize_bridge_record(raw_record)
            except NormalizationError as exc:
                issue = ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    error_code="NORMALIZATION_ERROR",
                    field_name=None,
                    message=str(exc),
                )
                _add_issue(
                    session,
                    import_run_id=import_run_id,
                    row_number=raw_record.row_number,
                    structure_number=_raw_structure_number(raw_record.values),
                    issue=issue,
                    counters=counters,
                )
                counters.rows_rejected += 1
                continue

            validation_result = validate_bridge_record(normalized_record, context)

            for issue in validation_result.issues:
                _add_issue(
                    session,
                    import_run_id=import_run_id,
                    row_number=normalized_record.source_row_number,
                    structure_number=normalized_record.structure_number or None,
                    issue=issue,
                    counters=counters,
                )

            if validation_result.is_valid:
                session.add(bridge_from_normalized(normalized_record, dataset.id))
                counters.rows_inserted += 1
            else:
                counters.rows_rejected += 1

        status = _status_for(counters)
        _activate_dataset(session, dataset)
        _finalize_import_run(import_run, status, counters)

        result = _result_from_import_run(
            import_run,
            request,
            issue_counts_by_code=counters.issue_counts_by_code,
        )

    return result


def mark_import_failed(
    import_run_id: int,
    failure_message: str,
    *,
    session_factory=SessionLocal,
) -> None:
    with session_factory.begin() as session:
        import_run = session.get_one(ImportRun, import_run_id)
        import_run.status = "failed"
        import_run.finished_at = _now()
        import_run.failure_message = failure_message
        import_run.summary = {"issue_counts_by_code": {"IMPORT_FAILED": 1}}

        session.add(
            ImportIssue(
                import_run_id=import_run_id,
                severity=IssueSeverity.FATAL.value,
                row_number=None,
                structure_number=None,
                field_name=None,
                error_code="IMPORT_FAILED",
                raw_value=None,
                message=f"Import failed: {failure_message}",
                raw_record=None,
            )
        )


def _create_dataset(request: ImportRequest) -> BridgeDataset:
    return BridgeDataset(
        provider=request.provider,
        state_code=request.state_code,
        inventory_year=request.inventory_year,
        source_format=request.source_format,
        source_specification=request.source_specification,
        source_url=request.source_url,
        source_file_name=request.source_file_name,
        source_sha256=request.source_sha256,
        retrieved_at=request.retrieved_at,
        is_active=False,
    )


def _add_issue(
    session,
    *,
    import_run_id: int,
    row_number: int | None,
    structure_number: str | None,
    issue: ValidationIssue,
    counters: _ImportCounters,
) -> None:
    session.add(
        import_issue_from_validation(
            issue,
            import_run_id=import_run_id,
            row_number=row_number,
            structure_number=structure_number,
        )
    )

    counters.issue_counts_by_code[issue.error_code] += 1

    if issue.severity == IssueSeverity.WARNING:
        counters.warnings_count += 1
    elif issue.severity in {IssueSeverity.ERROR, IssueSeverity.FATAL}:
        counters.errors_count += 1


def _activate_dataset(session, dataset: BridgeDataset) -> None:
    session.execute(
        update(BridgeDataset)
        .where(BridgeDataset.state_code == dataset.state_code)
        .where(BridgeDataset.id != dataset.id)
        .where(BridgeDataset.is_active.is_(True))
        .values(is_active=False)
    )
    dataset.is_active = True


def _finalize_import_run(
    import_run: ImportRun,
    status: str,
    counters: _ImportCounters,
) -> None:
    import_run.status = status
    import_run.finished_at = _now()
    import_run.rows_read = counters.rows_read
    import_run.rows_inserted = counters.rows_inserted
    import_run.rows_updated = counters.rows_updated
    import_run.rows_unchanged = counters.rows_unchanged
    import_run.rows_rejected = counters.rows_rejected
    import_run.warnings_count = counters.warnings_count
    import_run.errors_count = counters.errors_count
    import_run.summary = {
        "issue_counts_by_code": dict(sorted(counters.issue_counts_by_code.items()))
    }


def _finalize_duplicate_import_run(
    import_run: ImportRun,
    existing_dataset_id: int,
) -> None:
    import_run.status = "skipped_duplicate_file"
    import_run.finished_at = _now()
    import_run.rows_read = 0
    import_run.rows_inserted = 0
    import_run.rows_updated = 0
    import_run.rows_unchanged = 0
    import_run.rows_rejected = 0
    import_run.warnings_count = 0
    import_run.errors_count = 0
    import_run.summary = {
        "duplicate_dataset_id": existing_dataset_id,
        "issue_counts_by_code": {},
    }


def _result_from_import_run(
    import_run: ImportRun,
    request: ImportRequest,
    *,
    issue_counts_by_code: Mapping[str, int] | None = None,
) -> ImportResult:
    if issue_counts_by_code is None:
        raw_issue_counts = import_run.summary.get("issue_counts_by_code", {})
        issue_counts_by_code = (
            raw_issue_counts if isinstance(raw_issue_counts, dict) else {}
        )

    return ImportResult(
        import_run_id=import_run.id,
        dataset_id=import_run.dataset_id,
        status=import_run.status,
        rows_read=import_run.rows_read,
        rows_inserted=import_run.rows_inserted,
        rows_updated=import_run.rows_updated,
        rows_unchanged=import_run.rows_unchanged,
        rows_rejected=import_run.rows_rejected,
        warnings_count=import_run.warnings_count,
        errors_count=import_run.errors_count,
        source_file_name=request.source_file_name,
        source_sha256=request.source_sha256,
        provider=request.provider,
        state_code=request.state_code,
        state_name=request.state_name,
        inventory_year=request.inventory_year,
        issue_counts_by_code=dict(sorted(issue_counts_by_code.items())),
        failure_message=import_run.failure_message,
    )


def _status_for(counters: _ImportCounters) -> str:
    if counters.warnings_count == 0 and counters.errors_count == 0:
        return "completed"

    return "completed_with_warnings"


def _raw_structure_number(values: dict[str, str]) -> str | None:
    structure_number = values.get("STRUCTURE_NUMBER_008", "").strip()
    return structure_number or None


def _now() -> datetime:
    return datetime.now(timezone.utc)
