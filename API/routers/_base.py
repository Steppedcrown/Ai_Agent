from fastapi import APIRouter, HTTPException, Query  # type: ignore
from typing import Optional
from db import JSONDriver


def make_router(
    model: str,
    search_field: str = "title",
    table: str | None = None,
    tag: str | None = None,
) -> APIRouter:
    """
    Returns a router with list + detail endpoints backed by PostgreSQL.

    Args:
        model:        URL prefix, e.g. "locations" → GET /locations
        search_field: Column used for the ?search= query (default "title")
        table:        DB table name (defaults to model if not set)
        tag:          OpenAPI tag (defaults to model capitalized)
    """
    table = table or model
    tag = tag or model.replace("_", " ").replace("-", " ").title()
    singular = tag.rstrip("s")

    router = APIRouter(prefix=f"/{model}", tags=[tag])

    @router.get("")
    def list_items(
        page: int = Query(0, ge=0, description="Zero-based page index"),
        limit: int = Query(200, ge=1, le=500, description="Items per page"),
        search: Optional[str] = Query(None, description=f"Search by {search_field}"),
    ):
        driver = JSONDriver(table)
        if search:
            driver.search({search_field: search})
        driver.skip(page * limit).limit(limit)
        return {"data": driver.data, "success": True}

    @router.get("/{item_id}")
    def get_item(item_id: int):
        driver = JSONDriver(table)
        driver.find_by_id(item_id)
        if driver.data is None:
            raise HTTPException(status_code=404, detail=f"{singular} not found")
        return {"data": driver.data, "success": True}

    return router
