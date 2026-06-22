from fastapi import APIRouter, HTTPException, Query  # type: ignore
from typing import Optional
from db import JSONDriver


def make_router(model: str, search_field: str = "name") -> APIRouter:
    """
    Returns a router with list + detail endpoints for a JSON data model.

    Args:
        model:        Name of the JSON file in data/ (without extension), e.g. "bosses"
        search_field: Field used for the ?name= search query (default "name")

    Endpoints created:
        GET /{model}        - paginated list with optional ?name= search
        GET /{model}/{id}   - single entry by id
    """
    router = APIRouter(prefix=f"/{model}", tags=[model.capitalize()])
    singular = model.rstrip("s").capitalize()

    @router.get("")
    def list_items(
        page: int = Query(0, ge=0, description="Zero-based page index"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        name: Optional[str] = Query(None, description=f"Search by {search_field}"),
    ):
        driver = JSONDriver(model)
        if name:
            driver.search({search_field: name})
        driver.skip(page * limit).limit(limit)
        return {"data": driver.data, "success": True}

    @router.get("/{item_id}")
    def get_item(item_id: int):
        driver = JSONDriver(model)
        driver.find_by_id(item_id)
        if driver.data is None:
            raise HTTPException(status_code=404, detail=f"{singular} not found")
        return {"data": driver.data, "success": True}

    return router
