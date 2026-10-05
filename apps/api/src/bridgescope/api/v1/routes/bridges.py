from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bridgescope.api.dependencies import DbSession
from bridgescope.api.v1.schemas.pagination import BridgePage
from bridgescope.services.bridges import (
    count_bridges_for_dataset,
    get_bridges_for_dataset,
    require_active_dataset,
)
from bridgescope.services.errors import ActiveDatasetNotFoundError

router = APIRouter()


@router.get(
    "",
    response_model=BridgePage,
)
def list_bridges(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> BridgePage:
    try:
        dataset = require_active_dataset(session)
    except ActiveDatasetNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    offset = (page - 1) * page_size
    total_items = count_bridges_for_dataset(session, dataset_id=dataset.id)
    total_pages = (total_items + page_size - 1) // page_size
    bridges = get_bridges_for_dataset(
        session,
        dataset_id=dataset.id,
        offset=offset,
        limit=page_size,
    )

    return BridgePage(
        items=bridges,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )

