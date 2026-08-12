from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models import BusinessError, DIRECTIONS, assert_in
from ..repositories.sqlite_repo import repo
from ..services.parser import guess_direction, guess_meta, parse_jd
from ..db import load_json

router = APIRouter(prefix="/api/jds", tags=["jd"])


class JdIn(BaseModel):
    company: str = ""
    title: str = ""
    direction_tag: str = ""
    url: str = ""
    source: str = ""
    location: str = ""
    salary_range: str = ""
    raw_text: str = ""
    status: str = "active"
    note: str = ""


@router.get("")
def list_jds(status: str = "", direction: str = ""):
    apps = repo("jd").list()
    if status:
        apps = [a for a in apps if a["status"] == status]
    if direction:
        apps = [a for a in apps if a["direction_tag"] == direction]
    return apps


@router.get("/{jid}")
def get_jd(jid: int):
    item = repo("jd").get(jid)
    if not item:
        raise BusinessError("JD 不存在", 404)
    return item


@router.post("")
def create_jd(payload: JdIn):
    d = payload.dict()
    raw = d.get("raw_text") or ""
    if not d.get("direction_tag"):
        d["direction_tag"] = guess_direction(raw) if raw else "其他"
    assert_in(d["direction_tag"], DIRECTIONS, "direction_tag")

    parsed = parse_jd(raw)
    # 自动猜元信息填充空字段
    if raw:
        meta = guess_meta(raw)
        for k in ("company", "title", "salary_range", "location"):
            if not d.get(k) and meta.get(k):
                d[k] = meta[k]
    d["parsed_json"] = parsed
    if not d.get("title"):
        d["title"] = "待定岗位"
    if not d.get("company"):
        d["company"] = "待定公司"
    return repo("jd").create(d, summary=f"新增 JD {d['company']} {d['title']}")


@router.put("/{jid}")
def update_jd(jid: int, payload: JdIn):
    d = {k: v for k, v in payload.dict().items() if v != "" or k in ("raw_text", "note")}
    if "direction_tag" in d:
        assert_in(d["direction_tag"], DIRECTIONS, "direction_tag")
    if "raw_text" in d and d["raw_text"]:
        d["parsed_json"] = parse_jd(d["raw_text"])
    return repo("jd").update(jid, d)


@router.delete("/{jid}")
def delete_jd(jid: int):
    if repo("application").count("jd_id=?", (jid,)) > 0:
        raise BusinessError("该 JD 已有投递记录，无法直接删除")
    repo("jd").delete(jid, summary=f"删除 JD {jid}")
    return {"ok": True}
