from sqlalchemy import func, select
from sqlalchemy.orm import Session

from bridgescope.db.models import Bridge, BridgeDataset
from bridgescope.services.errors import ActiveDatasetNotFoundError


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
) -> list[Bridge]:
    statement = (
        select(Bridge)
        .where(Bridge.dataset_id == dataset_id)
        .order_by(
            Bridge.state_code.asc(),
            Bridge.structure_number.asc(),
        )
        .offset(offset)
        .limit(limit)
    )

    return list(session.scalars(statement))


def count_bridges_for_dataset(
    session: Session,
    *,
    dataset_id: int,
) -> int:
    statement = (
        select(func.count())
        .select_from(Bridge)
        .where(Bridge.dataset_id == dataset_id)
    )

    return session.scalar(statement) or 0


def get_active_bridges(
    session: Session,
    *,
    offset: int,
    limit: int,
    state_code: str = "06",
) -> list[Bridge]:
    dataset = require_active_dataset(session, state_code=state_code)

    return get_bridges_for_dataset(
        session,
        dataset_id=dataset.id,
        offset=offset,
        limit=limit,
    )


def count_active_bridges(
    session: Session,
    *,
    state_code: str = "06",
) -> int:
    dataset = require_active_dataset(session, state_code=state_code)

    return count_bridges_for_dataset(session, dataset_id=dataset.id)

