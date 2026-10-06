from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from bridgescope.api.dependencies import DbSession
from bridgescope.api.v1.schemas.ranking import HighestAdtItem, HighestAdtRanking
from bridgescope.services.bridges import get_highest_adt_bridges, require_active_dataset
from bridgescope.services.errors import ActiveDatasetNotFoundError

router = APIRouter()


@router.get(
    "/highest-adt",
    response_model=HighestAdtRanking,
    summary="Rank bridges by reported Average Daily Traffic",
    description=(
        "Returns a bounded active-dataset leaderboard ordered by source-reported "
        "Average Daily Traffic. ADT is not live traffic, so each item includes "
        "the traffic measurement year when available."
    ),
)
def highest_adt_ranking(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> HighestAdtRanking:
    try:
        dataset = require_active_dataset(session)
    except ActiveDatasetNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    bridges = get_highest_adt_bridges(
        session,
        dataset_id=dataset.id,
        limit=limit,
    )

    return HighestAdtRanking(
        items=[
            HighestAdtItem(
                rank=rank,
                state_code=bridge.state_code,
                structure_number=bridge.structure_number,
                facility_carried=bridge.facility_carried,
                feature_crossed=bridge.feature_crossed,
                county_code=bridge.county_code,
                average_daily_traffic=bridge.average_daily_traffic,
                traffic_year=bridge.traffic_year,
            )
            for rank, bridge in enumerate(bridges, start=1)
        ],
        limit=limit,
    )
