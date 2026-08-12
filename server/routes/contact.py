from fastapi import APIRouter, Body
from datetime import timedelta

from ..db import today
from ..models import CONTACT_ROLES, WARMTH, BusinessError, assert_in
from ..repositories.sqlite_repo import repo

router = APIRouter(prefix="/api/contacts", tags=["contact"])


@router.get("")
def list_contacts(role: str = ""):
    rows = repo("contact").list()
    if role:
        rows = [r for r in rows if r["role"] == role]
    return rows


@router.post("")
def create_contact(payload: dict = Body(...)):
    assert_in(payload.get("role", "内推人"), CONTACT_ROLES, "role")
    assert_in(payload.get("warmth", "一般"), WARMTH, "warmth")
    data = {
        "name": payload.get("name", ""),
        "org": payload.get("org", ""),
        "role": payload.get("role", "内推人"),
        "wechat": payload.get("wechat", ""),
        "phone": payload.get("phone", ""),
        "email": payload.get("email", ""),
        "warmth": payload.get("warmth", "一般"),
        "last_contact_at": payload.get("last_contact_at"),
        "followup_cycle_days": payload.get("followup_cycle_days", 14),
        "next_followup_at": payload.get("next_followup_at"),
        "note": payload.get("note", ""),
    }
    if not data["name"]:
        raise BusinessError("联系人姓名必填")
    return repo("contact").create(data, summary=f"新增联系人 {data['name']}")


@router.put("/{cid}")
def update_contact(cid: int, payload: dict = Body(...)):
    assert_in(payload.get("role", "内推人"), CONTACT_ROLES, "role") if "role" in payload else None
    assert_in(payload.get("warmth", "一般"), WARMTH, "warmth") if "warmth" in payload else None
    data = {k: v for k, v in payload.items() if k in (
        "name", "org", "role", "wechat", "phone", "email", "warmth",
        "last_contact_at", "followup_cycle_days", "next_followup_at", "note")}
    # 记录一次联系：更新最近联系时间，并按周期推下一次
    if payload.get("touch"):
        data["last_contact_at"] = today()
        cycle = payload.get("followup_cycle_days") or 14
        data["next_followup_at"] = (today() + timedelta(days=int(cycle)))
    return repo("contact").update(cid, data)


@router.delete("/{cid}")
def delete_contact(cid: int):
    if repo("application").count("contact_id=?", (cid,)) > 0:
        raise BusinessError("该联系人已关联投递，无法删除")
    repo("contact").delete(cid, summary=f"删除联系人 {cid}")
    return {"ok": True}
