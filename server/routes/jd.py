from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_setting, load_json
from ..models import BusinessError, DIRECTIONS, assert_in
from ..repositories.sqlite_repo import repo
from ..services.matcher import match
from ..services.parser import guess_direction, guess_meta, parse_jd

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


@router.get("/{jid}/analyze")
def analyze_jd(jid: int):
    """JD 详情分析：保留原文 + 基于求职者背景与简历做匹配分析。"""
    jd = repo("jd").get(jid)
    if not jd:
        raise BusinessError("JD 不存在", 404)

    resumes = [r for r in repo("resume").list() if r.get("is_active", 1)]
    resume = resumes[0] if resumes else None

    result = {
        "jd": jd,
        "resume_version": resume["version_name"] if resume else None,
        "match": None,
        "user": {
            "primary_direction": get_setting("primary_direction", ""),
            "backup_directions": load_json(get_setting("backup_directions", "[]"), []),
            "years_experience": get_setting("years_experience", ""),
            "education": get_setting("education", ""),
            "current_city": get_setting("current_city", ""),
        },
    }
    if resume:
        try:
            result["match"] = match(resume, jd)
        except Exception:
            result["match"] = None
    return result


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

    # 方向偏离预警（规则层）
    primary = get_setting("primary_direction", "")
    backups = load_json(get_setting("backup_directions", "[]"), [])
    allowed = set([primary] + [b for b in backups if b])
    if d["direction_tag"] and d["direction_tag"] != "其他" \
            and allowed and d["direction_tag"] not in allowed:
        d["direction_alert"] = (
            f"方向偏离：该岗位为「{d['direction_tag']}」，"
            f"你的求职方向是「{'/'.join(sorted(allowed))}」")

    # 去重检测（同公司 + 同岗位）
    duplicate = False
    if d["company"] != "待定公司" and d["title"] != "待定岗位":
        for j in repo("jd").list():
            if j["company"] == d["company"] and j["title"] == d["title"]:
                duplicate = True
                break

    created = repo("jd").create(d, summary=f"新增 JD {d['company']} {d['title']}")
    if duplicate:
        created["duplicate_warning"] = True
    return created


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
