from sqlalchemy.orm import configure_mappers

from bridgescope.db.base import Base
import bridgescope.db.models  # noqa: F401


def test_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "bridge_datasets",
        "bridges",
        "import_runs",
        "import_issues",
    }


def test_orm_mappers_configure() -> None:
    configure_mappers()
