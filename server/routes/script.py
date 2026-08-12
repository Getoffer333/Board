"""面试逐字稿管理 — CRUD 路由。"""

from fastapi import APIRouter, Body

from ..db import now
from ..models import BusinessError, DIRECTIONS, SCRIPT_TAGS, SCRIPT_TYPES, assert_in
from ..repositories.sqlite_repo import repo

router = APIRouter(prefix="/api/scripts", tags=["script"])


@router.get("")
def list_scripts(direction: str = "", script_type: str = "", tag: str = ""):
    rows = repo("interview_script").list(order="sort_order, updated_at DESC")
    if direction:
        rows = [r for r in rows if r["direction_tag"] == direction]
    if script_type:
        rows = [r for r in rows if r["script_type"] == script_type]
    if tag:
        import json
        rows = [r for r in rows if tag in (json.loads(r.get("tags", "[]")) if isinstance(r.get("tags"), str) else r.get("tags", []))]
    return rows


@router.get("/{sid}")
def get_script(sid: int):
    item = repo("interview_script").get(sid)
    if not item:
        raise BusinessError("逐字稿不存在", 404)
    return item


@router.post("")
def create_script(payload: dict = Body(...)):
    assert_in(payload.get("direction_tag", "通用"), DIRECTIONS + ["通用"], "direction_tag")
    assert_in(payload.get("script_type", "自我介绍"), SCRIPT_TYPES, "script_type")
    tags = payload.get("tags", [])
    for t in (tags if isinstance(tags, list) else []):
        assert_in(t, SCRIPT_TAGS, "tags")
    data = {
        "title": payload.get("title", "未命名"),
        "direction_tag": payload.get("direction_tag", "通用"),
        "script_type": payload.get("script_type", "自我介绍"),
        "content": payload.get("content", ""),
        "tags": payload.get("tags", []),
        "note": payload.get("note", ""),
        "sort_order": payload.get("sort_order", 0),
    }
    return repo("interview_script").create(data, summary=f"新建逐字稿 {data['title']}")


@router.put("/{sid}")
def update_script(sid: int, payload: dict = Body(...)):
    allowed = {"title", "direction_tag", "script_type", "content", "tags", "note", "sort_order"}
    data = {k: v for k, v in payload.items() if k in allowed}
    if "direction_tag" in data:
        assert_in(data["direction_tag"], DIRECTIONS + ["通用"], "direction_tag")
    if "script_type" in data:
        assert_in(data["script_type"], SCRIPT_TYPES, "script_type")
    if "tags" in data:
        for t in data["tags"] if isinstance(data["tags"], list) else []:
            assert_in(t, SCRIPT_TAGS, "tags")
    return repo("interview_script").update(sid, data)


@router.post("/{sid}/practice")
def practice(sid: int):
    """记录一次练习打卡。"""
    item = repo("interview_script").get(sid)
    if not item:
        raise BusinessError("逐字稿不存在", 404)
    return repo("interview_script").update(sid, {
        "practice_count": (item.get("practice_count") or 0) + 1,
        "last_practiced_at": now(),
    }, summary=f"练习打卡 {item['title']}")


@router.post("/{sid}/master")
def toggle_master(sid: int):
    """切换掌握状态。"""
    item = repo("interview_script").get(sid)
    if not item:
        raise BusinessError("逐字稿不存在", 404)
    new_val = 0 if item.get("is_mastered") else 1
    return repo("interview_script").update(sid, {
        "is_mastered": new_val,
    }, summary=f"{'掌握' if new_val else '取消掌握'} {item['title']}")


@router.delete("/{sid}")
def delete_script(sid: int):
    repo("interview_script").delete(sid, summary=f"删除逐字稿 {sid}")
    return {"ok": True}
