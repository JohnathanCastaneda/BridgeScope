from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    DateTime,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bridgescope.db.base import Base

if TYPE_CHECKING:
    from bridgescope.db.models.bridge import Bridge
    from bridgescope.db.models.import_run import ImportRun


class BridgeDataset(Base):
    __tablename__ = "bridge_datasets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    provider: Mapped[str] = mapped_column(String(32))
    state_code: Mapped[str] = mapped_column(CHAR(2))
    inventory_year: Mapped[int] = mapped_column(SmallInteger)

    source_format: Mapped[str] = mapped_column(String(64))
    source_specification: Mapped[str] = mapped_column(String(64))

    source_url: Mapped[str] = mapped_column(Text)
    source_file_name: Mapped[str] = mapped_column(Text)

    source_sha256: Mapped[str] = mapped_column(
        CHAR(64),
        unique=True,
    )

    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    bridges: Mapped[list["Bridge"]] = relationship(
        "Bridge",
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    import_runs: Mapped[list["ImportRun"]] = relationship(
        "ImportRun",
        back_populates="dataset",
    )
