"""PostgreSQL-backed ownership store.

Requires DATABASE_URL. Does not fall back to memory.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from app.security.ownership import TaskOwnershipRecord, TaskOwnershipStore


class PostgresOwnershipStore(TaskOwnershipStore):
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is required for PostgresOwnershipStore")
        try:
            import psycopg2
            self._driver = psycopg2
        except ImportError as exc:
            raise RuntimeError("psycopg2 is required for the PostgreSQL adapter") from exc

    @contextmanager
    def _conn(self):
        connection = self._driver.connect(self.dsn)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, record: TaskOwnershipRecord) -> None:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO task_ownership (task_id, owner_id, kind, created_at, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (task_id) DO NOTHING
                    """,
                    (record.task_id, record.owner_id, record.kind, record.created_at, json.dumps(record.metadata)),
                )
                if cur.rowcount == 0:
                    raise ValueError(f"task {record.task_id} already owned")

    def get(self, task_id: str):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT task_id, owner_id, kind, created_at, metadata FROM task_ownership WHERE task_id = %s",
                    (task_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return TaskOwnershipRecord(
                    task_id=row[0], owner_id=row[1], kind=row[2], created_at=row[3],
                    metadata=row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                )

    def list_for_owner(self, owner_id: str, limit: int = 100):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT task_id, owner_id, kind, created_at, metadata FROM task_ownership WHERE owner_id = %s ORDER BY created_at DESC LIMIT %s",
                    (owner_id, limit),
                )
                return [
                    TaskOwnershipRecord(task_id=r[0], owner_id=r[1], kind=r[2], created_at=r[3],
                                        metadata=r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"))
                    for r in cur.fetchall()
                ]

    def delete(self, task_id: str, owner_id: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM task_ownership WHERE task_id = %s AND owner_id = %s", (task_id, owner_id))
                return cur.rowcount > 0
