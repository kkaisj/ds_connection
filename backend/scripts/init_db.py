"""Initialize database schema and seed data from scripts/init.sql.

Usage:
    cd backend
    uv run python -m scripts.init_db
"""

from __future__ import annotations

from pathlib import Path

import pymysql

from config.settings import settings


def _split_sql(sql_text: str) -> list[str]:
    lines: list[str] = []
    for line in sql_text.splitlines():
        if line.lstrip().startswith("--"):
            continue
        lines.append(line)
    sql = "\n".join(lines)
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    normalized: list[str] = []
    for stmt in statements:
        if stmt.upper().startswith("INSERT INTO "):
            normalized.append("INSERT IGNORE INTO " + stmt[len("INSERT INTO ") :])
        else:
            normalized.append(stmt)
    return normalized


def main() -> None:
    sql_path = Path(__file__).resolve().parent / "init.sql"
    sql_text = sql_path.read_text(encoding="utf-8")
    statements = _split_sql(sql_text)

    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
    finally:
        conn.close()

    print(
        f"Initialized DB by init.sql: {settings.db_user}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


if __name__ == "__main__":
    main()
