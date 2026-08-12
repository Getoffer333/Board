from fastapi import APIRouter, Body
from pydantic import BaseModel

from ..db import now, today
from ..models import (
    BusinessError,
    CHANNELS,
    PRIORITIES,
    STATUS_LABELS,
    assert_in,
    assert_transition,
)
from ..repositories.sqlite_repo import repo

router = APIRouter(prefix="/api/applications", tags=["application"])


class AppIn(BaseModel):
    jd_id: int
    resume_id: int
    contact_id: int | None = None
    channel: str = "官网"
    priority: str = "中"
    expected_salary: str = ""
    next_followup_at: str = ""
    note: str = ""


@router.get("")
def list_apps(status: str = "", direction: str = "", contact_id: int = 0):
    rows = repo("application").list()
    if status:
        rows = [r for r in rows if r["status"] == status]
    if direction:
        rows = [r for r in rows if r["direction_tag"] == direction]
    if contact_id:
        rows = [r for r in rows if r["contact_id"] == contact_id]
    return rows


@router.get("/{aid}")
def get_app(aid: int):
    item = repo("application").get(aid)
    if not item:
        raise BusinessError("投递记录不存在", 404)
    item["interviews"] = repo("interview").list("application_id=?", (aid,))
    return item


@router.post("")
def create_app(payload: AppIn):
    jd = repo("jd").get(payload.jd_id)
    resume = repo("resume").get(payload.resume_id)
    if not jd:
        raise BusinessError("关联的 JD 不存在")
    if not resume:
        raise BusinessError("关联的简历版本不存在")
    assert_in(payload.channel, CHANNELS, "channel")
    assert_in(payload.priority, PRIORITIES, "priority")

    nf = payload.next_followup_at or (today() if payload.channel else "")
    # 默认跟进日期：未投时留空，已投后 7 天
    if not nf and payload.channel:
        from datetime import timedelta

        nf = (today() + timedelta(days=7))

    data = {
        "jd_id": payload.jd_id,
        "resume_id": payload.resume_id,
        "contact_id": payload.contact_id,
        "company_snapshot": jd["company"],
        "title_snapshot": jd["title"],
        "direction_tag": jd["direction_tag"],
        "status": "intention",
        "channel": payload.channel,
        "priority": payload.priority,
        "expected_salary": payload.expected_salary,
        "next_followup_at": nf,
        "stage_entered_at": now(),
        "note": payload.note,
    }
    return repo("application").create(data, summary=f"新建投递 {jd['company']} {jd['title']}")


@router.put("/{aid}")
def update_app(aid: int, payload: dict = Body(...)):
    item = repo("application").get(aid)
    if not item:
        raise BusinessError("投递记录不存在", 404)
    allowed = {"contact_id", "channel", "priority", "expected_salary",
               "next_followup_at", "offer_salary", "close_reason", "note", "applied_at"}
    data = {k: v for k, v in payload.items() if k in allowed}
    if "channel" in data:
        assert_in(data["channel"], CHANNELS, "channel")
    if "priority" in data:
        assert_in(data["priority"], PRIORITIES, "priority")
    return repo("application").update(aid, data)


@router.post("/{aid}/transition")
def transition(aid: int, body: dict = Body(...)):
    target = body.get("target_status")
    item = repo("application").get(aid)
    if not item:
        raise BusinessError("投递记录不存在", 404)
    old = item["status"]
    assert_transition(old, target)
    data = {"status": target, "stage_entered_at": now()}
    if target == "applied" and not item.get("applied_at"):
        data["applied_at"] = now()
    if target == "closed":
        data["next_followup_at"] = None
    repo("application").update(aid, data,
                               summary=f"状态 {STATUS_LABELS.get(old)}→{STATUS_LABELS.get(target)}")
    return repo("application").get(aid)


@router.delete("/{aid}")
def delete_app(aid: int):
    repo("application").delete(aid, summary=f"删除投递 {aid}")
    return {"ok": True}
