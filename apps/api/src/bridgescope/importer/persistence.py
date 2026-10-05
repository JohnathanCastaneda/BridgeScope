from bridgescope.db.models.bridge import Bridge
from bridgescope.db.models.import_issue import ImportIssue
from bridgescope.importer.records import NormalizedBridgeRecord, ValidationIssue


def bridge_from_normalized(
    record: NormalizedBridgeRecord,
    dataset_id: int,
) -> Bridge:
    return Bridge(
        dataset_id=dataset_id,
        state_code=record.state_code,
        structure_number=record.structure_number,
        county_code=record.county_code,
        facility_carried=record.facility_carried,
        feature_crossed=record.feature_crossed,
        latitude=record.latitude,
        longitude=record.longitude,
        source_latitude_code=record.source_latitude_code,
        source_longitude_code=record.source_longitude_code,
        year_built=record.year_built,
        year_reconstructed=record.year_reconstructed,
        average_daily_traffic=record.average_daily_traffic,
        traffic_year=record.traffic_year,
        truck_traffic_percent=record.truck_traffic_percent,
        lanes_on=record.lanes_on,
        bridge_length_m=record.bridge_length_m,
        maximum_span_m=record.maximum_span_m,
        owner_code=record.owner_code,
        material_code=record.material_code,
        design_type_code=record.design_type_code,
        inspection_month=record.inspection_month,
        inspection_year=record.inspection_year,
        deck_condition_code=record.deck_condition_code,
        superstructure_condition_code=record.superstructure_condition_code,
        substructure_condition_code=record.substructure_condition_code,
        culvert_condition_code=record.culvert_condition_code,
        overall_condition_code=record.overall_condition_code,
        lowest_condition_rating=record.lowest_condition_rating,
        source_row_number=record.source_row_number,
    )


def import_issue_from_validation(
    issue: ValidationIssue,
    *,
    import_run_id: int,
    row_number: int | None,
    structure_number: str | None,
) -> ImportIssue:
    return ImportIssue(
        import_run_id=import_run_id,
        severity=issue.severity.value,
        row_number=row_number,
        structure_number=structure_number,
        field_name=issue.field_name,
        error_code=issue.error_code,
        raw_value=None,
        message=issue.message,
        raw_record=None,
    )
