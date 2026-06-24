from typing import Optional
from ..loader import get_conn


class BossRepository:
    """Storage interface for the boss table."""

    def list(
        self,
        name: Optional[str] = None,
        page: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        """Return a paginated list of bosses, optionally filtered by title."""
        params: list = []
        where = ""
        if name:
            where = "WHERE title ILIKE %s"
            params.append(f"%{name}%")
        sql = f"SELECT * FROM boss {where} ORDER BY id OFFSET %s LIMIT %s"
        params.extend([page * limit, limit])
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]

    def get_by_id(self, boss_id: int) -> Optional[dict]:
        """Return a single boss by ID, or None if not found."""
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM boss WHERE id = %s", (boss_id,))
                row = cur.fetchone()
                return dict(row) if row else None
