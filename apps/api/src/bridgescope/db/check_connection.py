from sqlalchemy import text

from bridgescope.db.session import engine


def main() -> None:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar_one()

    if value != 1:
        raise RuntimeError("Unexpected database health-check result.")

    print("Database connection successful.")


if __name__ == "__main__":
    main()