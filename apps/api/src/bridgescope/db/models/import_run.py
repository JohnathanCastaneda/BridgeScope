from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bridgescope.db.base import Base

if TYPE_CHECKING:
    from bridgescope.db.models.bridge_dataset import BridgeDataset
    from bridgescope.db.models.import_issue import ImportIssue


class ImportRun(Base):
    __tablename__ = "import_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'completed_with_warnings', 'failed', 'skipped_duplicate_file')",
            name="status_valid",
        ),
        CheckConstraint("rows_read >= 0", name="rows_read_nonnegative"),
        CheckConstraint("rows_inserted >= 0", name="rows_inserted_nonnegative"),
        CheckConstraint("rows_updated >= 0", name="rows_updated_nonnegative"),
        CheckConstraint("rows_unchanged >= 0", name="rows_unchanged_nonnegative"),
        CheckConstraint("rows_rejected >= 0", name="rows_rejected_nonnegative"),
        CheckConstraint("warnings_count >= 0", name="warnings_count_nonnegative"),
        CheckConstraint("errors_count >= 0", name="errors_count_nonnegative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dataset_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "bridge_datasets.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    source_file_name: Mapped[str] = mapped_column(Text)
    source_sha256: Mapped[str] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(String(32))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rows_read: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_updated: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_unchanged: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    warnings_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errors_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset: Mapped["BridgeDataset | None"] = relationship(
        "BridgeDataset",
        back_populates="import_runs",
    )
    issues: Mapped[list["ImportIssue"]] = relationship(
        "ImportIssue",
        back_populates="import_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
