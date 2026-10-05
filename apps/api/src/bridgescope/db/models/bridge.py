from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bridgescope.db.base import Base

if TYPE_CHECKING:
    from bridgescope.db.models.bridge_dataset import BridgeDataset


class Bridge(Base):
    __tablename__ = "bridges"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "state_code",
            "structure_number",
            name="bridge_identity",
        ),
        CheckConstraint(
            "average_daily_traffic >= 0",
            name="adt_nonnegative",
        ),
        CheckConstraint(
            "truck_traffic_percent >= 0 AND truck_traffic_percent <= 100",
            name="truck_percent_range",
        ),
        CheckConstraint(
            "lanes_on >= 0",
            name="lanes_on_nonnegative",
        ),
        CheckConstraint(
            "bridge_length_m >= 0",
            name="bridge_length_m_nonnegative",
        ),
        CheckConstraint(
            "maximum_span_m >= 0",
            name="maximum_span_m_nonnegative",
        ),
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="longitude_range",
        ),
        CheckConstraint(
            "inspection_month >= 1 AND inspection_month <= 12",
            name="inspection_month_range",
        ),
        CheckConstraint(
            "deck_condition_code IN ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'N')",
            name="deck_condition_code_valid",
        ),
        CheckConstraint(
            "superstructure_condition_code IN ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'N')",
            name="superstructure_condition_code_valid",
        ),
        CheckConstraint(
            "substructure_condition_code IN ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'N')",
            name="substructure_condition_code_valid",
        ),
        CheckConstraint(
            "culvert_condition_code IN ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'N')",
            name="culvert_condition_code_valid",
        ),
        CheckConstraint(
            "overall_condition_code IN ('G', 'F', 'P')",
            name="overall_condition_code_valid",
        ),
        CheckConstraint(
            "lowest_condition_rating >= 0 AND lowest_condition_rating <= 9",
            name="lowest_condition_rating_range",
        ),
        Index(
            "ix_bridges_dataset_adt",
            "dataset_id",
            "average_daily_traffic",
        ),
        Index(
            "ix_bridges_dataset_county",
            "dataset_id",
            "county_code",
        ),
        Index(
            "ix_bridges_dataset_year_built",
            "dataset_id",
            "year_built",
        ),
        Index(
            "ix_bridges_dataset_overall_condition",
            "dataset_id",
            "overall_condition_code",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "bridge_datasets.id",
            ondelete="CASCADE",
        ),
    )

    state_code: Mapped[str] = mapped_column(CHAR(2))
    structure_number: Mapped[str] = mapped_column(String(15))
    county_code: Mapped[str] = mapped_column(CHAR(3))

    facility_carried: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_crossed: Mapped[str | None] = mapped_column(Text, nullable=True)

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    source_latitude_code: Mapped[str | None] = mapped_column(
        CHAR(8),
        nullable=True,
    )
    source_longitude_code: Mapped[str | None] = mapped_column(
        CHAR(9),
        nullable=True,
    )

    year_built: Mapped[int] = mapped_column(SmallInteger)
    year_reconstructed: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    average_daily_traffic: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    traffic_year: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    truck_traffic_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    lanes_on: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    bridge_length_m: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    maximum_span_m: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    owner_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    material_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    design_type_code: Mapped[str | None] = mapped_column(String(4), nullable=True)

    inspection_month: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )
    inspection_year: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    deck_condition_code: Mapped[str | None] = mapped_column(CHAR(1), nullable=True)
    superstructure_condition_code: Mapped[str | None] = mapped_column(
        CHAR(1),
        nullable=True,
    )
    substructure_condition_code: Mapped[str | None] = mapped_column(
        CHAR(1),
        nullable=True,
    )
    culvert_condition_code: Mapped[str | None] = mapped_column(
        CHAR(1),
        nullable=True,
    )
    overall_condition_code: Mapped[str | None] = mapped_column(
        CHAR(1),
        nullable=True,
    )
    lowest_condition_rating: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    source_row_number: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    dataset: Mapped["BridgeDataset"] = relationship(
        "BridgeDataset",
        back_populates="bridges",
    )
