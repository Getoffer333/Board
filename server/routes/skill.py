from fastapi import APIRouter, Body

from ..models import SKILL_SOURCES, SKILL_STATUSES, BusinessError, assert_in
from ..repositories.sqlite_repo import repo

router = APIRouter(prefix="/api/skills", tags=["skill"])


@router.get("")
def list_skills(status: str = "", direction: str = ""):
    rows = repo("skill").list()
    if status:
        rows = [r for r in rows if r["status"] == status]
    if direction:
        rows = [r for r in rows if (r.get("direction_tag") or "") == direction]
    for r in rows:
        logs = repo("skill_log").list("skill_id=?", (r["id"],))
        r["logs"] = logs
        r["log_count"] = len(logs)
    return rows


@router.post("")
def create_skill(payload: dict = Body(...)):
    assert_in(payload.get("source", "自评"), SKILL_SOURCES, "source")
    assert_in(payload.get("status", "进行中"), SKILL_STATUSES, "status")
    data = {
        "name": payload.get("name", ""),
        "direction_tag": payload.get("direction_tag", ""),
        "category": payload.get("category", ""),
        "current_level": payload.get("current_level", 1),
        "target_level": payload.get("target_level", 4),
        "source": payload.get("source", "自评"),
        "source_ref": payload.get("source_ref", ""),
        "plan": payload.get("plan", ""),
        "status": payload.get("status", "进行中"),
    }
    if not data["name"]:
        raise BusinessError("技能名必填")
    return repo("skill").create(data, summary=f"新增技能项 {data['name']}")


@router.put("/{sid}")
def update_skill(sid: int, payload: dict = Body(...)):
    assert_in(payload.get("status", "进行中"), SKILL_STATUSES, "status") if "status" in payload else None
    data = {k: v for k, v in payload.items() if k in (
        "name", "direction_tag", "category", "current_level",
        "target_level", "source", "source_ref", "plan", "status")}
    return repo("skill").update(sid, data)


@router.delete("/{sid}")
def delete_skill(sid: int):
    repo("skill").delete(sid, summary=f"删除技能项 {sid}")
    return {"ok": True}


@router.post("/{sid}/log")
def add_log(sid: int, payload: dict = Body(...)):
    if not repo("skill").get(sid):
        raise BusinessError("技能项不存在", 404)
    data = {
        "skill_id": sid,
        "log_date": payload.get("log_date", ""),  # 由前端给 today
        "duration_min": payload.get("duration_min", 30),
        "content": payload.get("content", ""),
    }
    if not data["log_date"]:
        from ..db import today
        data["log_date"] = today()
    return repo("skill_log").create(data)


@router.get("/{sid}/logs")
def get_logs(sid: int):
    return repo("skill_log").list("skill_id=?", (sid,))
