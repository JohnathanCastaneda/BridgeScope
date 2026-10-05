from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bridgescope.db.base import Base

if TYPE_CHECKING:
    from bridgescope.db.models.import_run import ImportRun


class ImportIssue(Base):
    __tablename__ = "import_issues"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('warning', 'error', 'fatal')",
            name="severity_valid",
        ),
        CheckConstraint(
            "row_number IS NULL OR row_number > 0",
            name="row_number_positive",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    import_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "import_runs.id",
            ondelete="CASCADE",
        ),
    )

    severity: Mapped[str] = mapped_column(String(16))
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    structure_number: Mapped[str | None] = mapped_column(String(15), nullable=True)
    field_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str] = mapped_column(String(64))
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text)
    raw_record: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    import_run: Mapped["ImportRun"] = relationship(
        "ImportRun",
        back_populates="issues",
    )
