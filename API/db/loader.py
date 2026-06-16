import json
from pathlib import Path
from typing import Any

_cache: dict[str, list[Any]] = {}
_DATA_DIR = Path(__file__).parent.parent / "data"


def json_loader(model: str) -> list[Any]:
    if model not in _cache:
        path = _DATA_DIR / f"{model}.json"
        if not path.exists():
            raise FileNotFoundError(f"No data file found for model '{model}' at {path}")
        with open(path, encoding="utf-8") as f:
            _cache[model] = json.load(f)
    return _cache[model]
