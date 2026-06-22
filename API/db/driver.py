from typing import Any, Optional
from .loader import get_conn

_SAFE_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _safe(name: str) -> str:
    """Allowlist-validate a table/column name to prevent injection."""
    if not all(c in _SAFE_CHARS for c in name):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return name


class JSONDriver:
    """PostgreSQL-backed query driver with the same interface as the old JSON driver."""

    def __init__(self, model: str):
        self._table = _safe(model)
        self._wheres: list[str] = []
        self._params: list[Any] = []
        self._search_clause: Optional[str] = None
        self._offset: int = 0
        self._limit: Optional[int] = None
        self._single: bool = False
        self._result: Any = None
        self._executed: bool = False

    def find_many(self, filters: Optional[dict] = None) -> "JSONDriver":
        if filters:
            for k, v in filters.items():
                self._wheres.append(f"{_safe(k)} = %s")
                self._params.append(v)
        return self

    def find_by_id(self, id: int) -> "JSONDriver":
        self._wheres.append("id = %s")
        self._params.append(int(id))
        self._single = True
        return self

    def search(self, fields: Optional[dict] = None) -> "JSONDriver":
        if fields:
            clauses = [f"{_safe(k)} ILIKE %s" for k in fields]
            self._search_clause = "(" + " OR ".join(clauses) + ")"
            for v in fields.values():
                self._params.append(f"%{v}%")
        return self

    def skip(self, amount: int) -> "JSONDriver":
        self._offset = amount
        return self

    def limit(self, amount: int) -> "JSONDriver":
        self._limit = amount
        return self

    def _execute(self) -> None:
        if self._executed:
            return
        self._executed = True

        conditions = list(self._wheres)
        if self._search_clause:
            conditions.append(self._search_clause)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = f"OFFSET {self._offset}" if self._offset else ""
        limit = f"LIMIT {self._limit}" if self._limit is not None else ""

        sql = f"SELECT * FROM {self._table} {where} {offset} {limit}".strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, self._params)
                if self._single:
                    row = cur.fetchone()
                    self._result = dict(row) if row else None
                else:
                    self._result = [dict(r) for r in cur.fetchall()]

    @property
    def data(self) -> Any:
        self._execute()
        return self._result
