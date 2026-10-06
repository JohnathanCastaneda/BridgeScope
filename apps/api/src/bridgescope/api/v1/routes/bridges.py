from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bridgescope.api.dependencies import DbSession
from bridgescope.api.v1.schemas.pagination import BridgePage
from bridgescope.services.bridges import (
    BridgeQuery,
    BridgeSort,
    count_bridges_for_dataset,
    get_bridges_for_dataset,
    require_active_dataset,
)
from bridgescope.services.errors import ActiveDatasetNotFoundError

router = APIRouter()


class OverallConditionFilter(StrEnum):
    GOOD = "G"
    FAIR = "F"
    POOR = "P"


@router.get(
    "",
    response_model=BridgePage,
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

    try:
        dataset = require_active_dataset(session)
    except ActiveDatasetNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
        raise HTTPException(
            status_code=422,
            detail="year_built_min cannot be greater than year_built_max.",
        )

    if adt_min is not None and adt_max is not None and adt_min > adt_max:
        raise HTTPException(
            status_code=422,
            detail="adt_min cannot be greater than adt_max.",
        )

