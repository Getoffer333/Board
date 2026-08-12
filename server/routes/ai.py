from fastapi import APIRouter, Body

from ..db import now
from ..models import BusinessError
from ..repositories.sqlite_repo import repo
from ..services.matcher import match, suggest_skills_from_missing
from ..services.prompt_builder import (
    build_interview_q_prompt,
    build_jd_parse_prompt,
    build_match_prompt,
    validate_import,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/export-jd-parse")
def export_jd_parse(payload: dict = Body(...)):
    jd = repo("jd").get(payload.get("jd_id"))
    if not jd:
        raise BusinessError("JD 不存在", 404)
    return {"prompt": build_jd_parse_prompt(jd)}


@router.post("/export-match")
def export_match(payload: dict = Body(...)):
    jd = repo("jd").get(payload.get("jd_id"))
    resume = repo("resume").get(payload.get("resume_id"))
    if not jd or not resume:
        raise BusinessError("JD 或简历版本不存在", 404)
    return {"prompt": build_match_prompt(jd, resume)}


@router.post("/export-interview-q")
def export_interview_q(payload: dict = Body(...)):
    direction = payload.get("direction_tag") or "运营"
    return {"prompt": build_interview_q_prompt(direction)}


@router.post("/import-result")
def import_result(payload: dict = Body(...)):
    """接收 AI 回填 JSON，schema 校验后入库。脏数据拒绝。"""
    checked = validate_import(payload)
    t, result = checked["type"], checked["result"]

    if t == "jd_parse":
        jid = payload.get("jd_id") or result.get("jd_id")
        if not repo("jd").get(jid):
            raise BusinessError("回填的 JD 不存在", 404)
        repo("jd").update(jid, {
            "company": result["company"], "title": result["title"],
            "direction_tag": result["direction_tag"], "url": result.get("url", ""),
            "source": result.get("source", ""), "location": result.get("location", ""),
            "salary_range": result.get("salary_range", ""),
            "parsed_json": result["parsed_json"], "note": result.get("note", ""),
            "status": "active",
        }, summary="AI 回填解析 JD")
        return {"ok": True, "jd_id": jid}

    if t == "match":
        jd = repo("jd").get(result["jd_id"])
        resume = repo("resume").get(result["resume_id"])
        if not jd or not resume:
            raise BusinessError("匹配关联的 JD 或简历不存在", 404)
        # 覆盖同 JD+简历的旧匹配
        repo("match_result").raw(
            "DELETE FROM match_result WHERE jd_id=? AND resume_id=?",
            (result["jd_id"], result["resume_id"]))
        saved = repo("match_result").create({
            "jd_id": result["jd_id"], "resume_id": result["resume_id"],
            "score": result["score"], "dimension_scores": result["dimension_scores"],
            "matched_points": result["matched_points"],
            "missing_points": result["missing_points"],
            "suggestion": result.get("suggestion", ""), "source": "online",
        }, summary="AI 匹配结果回填")
        # 缺失关键词 → 技能差距候选（不自动建，返回建议让用户在界面点确认）
        return {
            "ok": True, "match_id": saved["id"],
            "suggested_skills": suggest_skills_from_missing(
                result["missing_points"], jd["direction_tag"]),
        }

    if t == "interview_q":
        created = []
        for q in result["questions"]:
            if not [x for x in repo("interview_question").list() if x["question"] == q["question"]]:
                created.append(repo("interview_question").create(q,
                                  summary="AI 生成面试题").get("id"))
        return {"ok": True, "created": len(created)}


@router.post("/match-local")
def match_local(payload: dict = Body(...)):
    """本地规则即时打分（不联网）。"""
    jd = repo("jd").get(payload.get("jd_id"))
    resume = repo("resume").get(payload.get("resume_id"))
    if not jd or not resume:
        raise BusinessError("JD 或简历版本不存在", 404)
    out = match(resume, jd)
    repo("match_result").raw(
        "DELETE FROM match_result WHERE jd_id=? AND resume_id=?",
        (jd["id"], resume["id"]))
    repo("match_result").create({
        "jd_id": jd["id"], "resume_id": resume["id"], "score": out["score"],
        "dimension_scores": out["dimension_scores"],
        "matched_points": out["matched_points"],
        "missing_points": out["missing_points"],
        "suggestion": out["suggestion"], "source": "local",
    }, summary="本地匹配打分")
    return out
