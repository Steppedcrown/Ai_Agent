from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from db.repositories import BossRepository

router = APIRouter(prefix="/bosses", tags=["Bosses"])
_repo = BossRepository()


@router.get("")
def list_bosses(
    page: int = Query(0, ge=0, description="Zero-based page index"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    name: Optional[str] = Query(None, description="Search by title (case-insensitive)"),
):
    return {"data": _repo.list(name=name, page=page, limit=limit), "success": True}


@router.get("/{boss_id}")
def get_boss(boss_id: int):
    boss = _repo.get_by_id(boss_id)
    if boss is None:
        raise HTTPException(status_code=404, detail="Boss not found")
    return {"data": boss, "success": True}
