from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Path, Query

from bridgescope.api.dependencies import DbSession
from bridgescope.api.errors import ApiErrorResponse, ApiValidationError, ErrorDetail
from bridgescope.api.v1.schemas.bridge import BridgeDetail
from bridgescope.api.v1.schemas.pagination import BridgePage
from bridgescope.services.bridges import (
    BridgeQuery,
    BridgeSort,
    count_bridges_for_dataset,
    get_bridges_for_dataset,
    require_active_dataset,
    require_bridge_by_identity,
)

router = APIRouter()


class OverallConditionFilter(StrEnum):
    GOOD = "G"
    FAIR = "F"
    POOR = "P"


@router.get(
    "",
    response_model=BridgePage,
    responses={
        422: {
            "model": ApiErrorResponse,
            "description": "Request validation failed",
        },
        503: {
            "model": ApiErrorResponse,
            "description": "No active bridge dataset",
        },
    },
)
def list_bridges(
    session: DbSession,
    q: str | None = None,
    county: Annotated[str | None, Query(pattern=r"^\d{3}$")] = None,
    year_built_min: Annotated[int | None, Query(ge=0)] = None,
    year_built_max: Annotated[int | None, Query(ge=0)] = None,
    adt_min: Annotated[int | None, Query(ge=0)] = None,
    adt_max: Annotated[int | None, Query(ge=0)] = None,
    condition: OverallConditionFilter | None = None,
    sort: BridgeSort = BridgeSort.STRUCTURE_NUMBER_ASC,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> BridgePage:
    _validate_ranges(
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        adt_min=adt_min,
        adt_max=adt_max,
    )

    dataset = require_active_dataset(session)

    bridge_query = BridgeQuery(
        q=q,
        county=county,
        year_built_min=year_built_min,
        year_built_max=year_built_max,
        adt_min=adt_min,
        adt_max=adt_max,
        condition=condition.value if condition is not None else None,
        sort=sort,
    )
    offset = (page - 1) * page_size
    total_items = count_bridges_for_dataset(
        session,
        dataset_id=dataset.id,
        query=bridge_query,
    )
    total_pages = (total_items + page_size - 1) // page_size
    bridges = get_bridges_for_dataset(
        session,
        dataset_id=dataset.id,
        offset=offset,
        limit=page_size,
        query=bridge_query,
    )

    return BridgePage(
        items=bridges,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


@router.get(
    "/{state_code}/{structure_number}",
    response_model=BridgeDetail,
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Bridge not found",
        },
        422: {
            "model": ApiErrorResponse,
            "description": "Request validation failed",
        },
        503: {
            "model": ApiErrorResponse,
            "description": "No active bridge dataset",
        },
    },
)
def get_bridge_detail(
    state_code: Annotated[str, Path(pattern=r"^\d{2}$")],
    structure_number: str,
    session: DbSession,
) -> BridgeDetail:
    dataset = require_active_dataset(session)

    bridge = require_bridge_by_identity(
        session,
        dataset_id=dataset.id,
        state_code=state_code,
        structure_number=structure_number.strip(),
    )

    return _bridge_detail_response(
        bridge,
        inventory_year=dataset.inventory_year,
    )


def _validate_ranges(
    *,
    year_built_min: int | None,
    year_built_max: int | None,
    adt_min: int | None,
    adt_max: int | None,
) -> None:
    if (
        year_built_min is not None
        and year_built_max is not None
        and year_built_min > year_built_max
    ):
        raise ApiValidationError(
            [
                ErrorDetail(
                    field="query.year_built_min",
                    message="year_built_min cannot be greater than year_built_max.",
                    type="value_error.range",
                )
            ]
        )

    if adt_min is not None and adt_max is not None and adt_min > adt_max:
        raise ApiValidationError(
            [
                ErrorDetail(
                    field="query.adt_min",
                    message="adt_min cannot be greater than adt_max.",
                    type="value_error.range",
                )
            ]
        )


def _bridge_detail_response(bridge, *, inventory_year: int) -> BridgeDetail:
    return BridgeDetail(
        state_code=bridge.state_code,
        structure_number=bridge.structure_number,
        inventory_year=inventory_year,
        facility_carried=bridge.facility_carried,
        feature_crossed=bridge.feature_crossed,
        county_code=bridge.county_code,
        latitude=bridge.latitude,
        longitude=bridge.longitude,
        year_built=bridge.year_built,
        year_reconstructed=bridge.year_reconstructed,
        average_daily_traffic=bridge.average_daily_traffic,
        traffic_year=bridge.traffic_year,
        truck_traffic_percent=bridge.truck_traffic_percent,
        lanes_on=bridge.lanes_on,
        bridge_length_m=bridge.bridge_length_m,
        maximum_span_m=bridge.maximum_span_m,
        owner_code=bridge.owner_code,
        material_code=bridge.material_code,
        design_type_code=bridge.design_type_code,
        inspection_month=bridge.inspection_month,
        inspection_year=bridge.inspection_year,
        deck_condition_code=bridge.deck_condition_code,
        superstructure_condition_code=bridge.superstructure_condition_code,
        substructure_condition_code=bridge.substructure_condition_code,
        culvert_condition_code=bridge.culvert_condition_code,
        overall_condition_code=bridge.overall_condition_code,
        lowest_condition_rating=bridge.lowest_condition_rating,
    )

