from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from bridgescope.db.models import Bridge, BridgeDataset
from bridgescope.services.errors import ActiveDatasetNotFoundError


class BridgeSort(StrEnum):
    STRUCTURE_NUMBER_ASC = "structure_number_asc"
    YEAR_BUILT_ASC = "year_built_asc"
    YEAR_BUILT_DESC = "year_built_desc"
    ADT_ASC = "adt_asc"
    ADT_DESC = "adt_desc"


@dataclass(frozen=True)
class BridgeQuery:
    q: str | None = None
    county: str | None = None
    year_built_min: int | None = None
    year_built_max: int | None = None
    adt_min: int | None = None
    adt_max: int | None = None
    condition: str | None = None
    sort: BridgeSort = BridgeSort.STRUCTURE_NUMBER_ASC


def get_active_dataset(
    session: Session,
    *,
    state_code: str = "06",
) -> BridgeDataset | None:
    statement = select(BridgeDataset).where(
        BridgeDataset.state_code == state_code,
        BridgeDataset.is_active.is_(True),
    )

    return session.scalars(statement).one_or_none()


def require_active_dataset(
    session: Session,
    *,
    state_code: str = "06",
) -> BridgeDataset:
    dataset = get_active_dataset(session, state_code=state_code)

    if dataset is None:
        raise ActiveDatasetNotFoundError(
            f"No active dataset exists for state {state_code}."
        )

    return dataset


def get_bridges_for_dataset(
    session: Session,
    *,
    dataset_id: int,
    offset: int,
    limit: int,
    query: BridgeQuery | None = None,
) -> list[Bridge]:
    query = query or BridgeQuery()
    conditions = _bridge_filter_conditions(dataset_id=dataset_id, query=query)
    statement = (
        select(Bridge)
        .where(*conditions)
        .order_by(*_bridge_sort_expressions(query.sort))
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement))


def get_bridge_by_identity(
    session: Session,
    *,
    dataset_id: int,
    state_code: str,
    structure_number: str,
) -> Bridge | None:
    statement = select(Bridge).where(
        Bridge.dataset_id == dataset_id,
        Bridge.state_code == state_code,
        Bridge.structure_number == structure_number,
    )

    return session.scalars(statement).one_or_none()


def count_bridges_for_dataset(
    session: Session,
    *,
    dataset_id: int,
    query: BridgeQuery | None = None,
) -> int:
    query = query or BridgeQuery()
    conditions = _bridge_filter_conditions(dataset_id=dataset_id, query=query)
    statement = (
        select(func.count())
        .select_from(Bridge)
        .where(*conditions)
    )

    return session.scalar(statement) or 0


def get_active_bridges(
    session: Session,
    *,
    offset: int,
    limit: int,
    state_code: str = "06",
    query: BridgeQuery | None = None,
) -> list[Bridge]:
    dataset = require_active_dataset(session, state_code=state_code)

    return get_bridges_for_dataset(
        session,
        dataset_id=dataset.id,
        offset=offset,
        limit=limit,
        query=query,
    )


def count_active_bridges(
    session: Session,
    *,
    state_code: str = "06",
    query: BridgeQuery | None = None,
) -> int:
    dataset = require_active_dataset(session, state_code=state_code)

    return count_bridges_for_dataset(session, dataset_id=dataset.id, query=query)


def _bridge_filter_conditions(*, dataset_id: int, query: BridgeQuery):
    conditions = [Bridge.dataset_id == dataset_id]

    search_term = query.q.strip() if query.q is not None else ""
    if search_term:
        search_pattern = f"%{search_term}%"
        conditions.append(
            or_(
                Bridge.structure_number.ilike(search_pattern),
                Bridge.facility_carried.ilike(search_pattern),
                Bridge.feature_crossed.ilike(search_pattern),
            )
        )

    if query.county is not None:
        conditions.append(Bridge.county_code == query.county)

    if query.year_built_min is not None:
        conditions.append(Bridge.year_built >= query.year_built_min)

    if query.year_built_max is not None:
        conditions.append(Bridge.year_built <= query.year_built_max)

    if query.adt_min is not None:
        conditions.append(Bridge.average_daily_traffic >= query.adt_min)

    if query.adt_max is not None:
        conditions.append(Bridge.average_daily_traffic <= query.adt_max)

    if query.condition is not None:
        conditions.append(Bridge.overall_condition_code == query.condition)

    return conditions


def _bridge_sort_expressions(sort: BridgeSort):
    tie_breakers = (
        Bridge.state_code.asc(),
        Bridge.structure_number.asc(),
    )

    sort_expressions = {
        BridgeSort.STRUCTURE_NUMBER_ASC: tie_breakers,
        BridgeSort.YEAR_BUILT_ASC: (
            Bridge.year_built.asc().nulls_last(),
            *tie_breakers,
        ),
        BridgeSort.YEAR_BUILT_DESC: (
            Bridge.year_built.desc().nulls_last(),
            *tie_breakers,
        ),
        BridgeSort.ADT_ASC: (
            Bridge.average_daily_traffic.asc().nulls_last(),
            *tie_breakers,
        ),
        BridgeSort.ADT_DESC: (
            Bridge.average_daily_traffic.desc().nulls_last(),
            *tie_breakers,
        ),
    }

    return sort_expressions[sort]

