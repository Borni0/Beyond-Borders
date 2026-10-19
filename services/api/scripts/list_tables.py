"""List all tables in the live DB to verify migrations applied."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def main() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://fintech:fintech_dev_only@localhost:5432/fintech",
    )
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "ORDER BY tablename"
            )
        ).scalars().all()
        # Also check if alembic thinks it's up to date.
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).first()
    print("tables:")
    for r in rows:
        print(f"  - {r}")
    print(f"alembic version: {rev[0] if rev else '<not set>'}")


if __name__ == "__main__":
    main()
