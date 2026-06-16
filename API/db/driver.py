from typing import Any, Optional
from .loader import json_loader


class JSONDriver:
    def __init__(self, model: str):
        # Shallow copy so driver mutations don't affect the shared cache
        self._data: Any = list(json_loader(model))

    def find_many(self, filters: Optional[dict] = None) -> "JSONDriver":
        if filters:
            self._data = [
                entry for entry in self._data
                if all(entry.get(k) == v for k, v in filters.items())
            ]
        return self

    def find_by_id(self, id: str) -> "JSONDriver":
        self._data = next(
            (entry for entry in self._data if str(entry.get("id")) == str(id)),
            None,
        )
        return self

    def search(self, fields: Optional[dict] = None) -> "JSONDriver":
        if fields:
            self._data = [
                entry for entry in self._data
                if any(
                    v.lower() in str(entry.get(k, "")).lower()
                    for k, v in fields.items()
                )
            ]
        return self

    def skip(self, amount: int) -> "JSONDriver":
        if isinstance(self._data, list):
            self._data = self._data[amount:]
        return self

    def limit(self, amount: int) -> "JSONDriver":
        if isinstance(self._data, list):
            self._data = self._data[:amount]
        return self

    @property
    def data(self) -> Any:
        return self._data
