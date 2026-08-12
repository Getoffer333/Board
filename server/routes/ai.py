"""AI 双通道：离线 prompt 导出 + 在线 LLM 直连 + JSON 回填校验。"""

import json

from fastapi import APIRouter, Body

from ..db import get_setting, load_json, now
from ..models import BusinessError, DIRECTIONS
from ..repositories.sqlite_repo import repo
from ..services.llm import call_llm_json
from ..services.matcher import match, suggest_skills_from_missing
from ..services.prompt_builder import (
    build_interview_q_prompt,
    build_jd_parse_prompt,
    build_match_prompt,
    validate_import,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ─── 离线导出 ────────────────────────────────────────────
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


# ─── 在线一键调用 ────────────────────────────────────────
@router.post("/online-jd-parse")
def online_jd_parse(payload: dict = Body(...)):
    """一键 JD 解析：LLM 直接调用 + 回填入库。"""
    jd = repo("jd").get(payload.get("jd_id"))
    if not jd:
        raise BusinessError("JD 不存在", 404)
    if get_setting("llm_enabled", "0") != "1":
        raise BusinessError("在线模式未开启，请在设置中启用并配置 API Key")
    prompt = build_jd_parse_prompt(jd)
    try:
        result = call_llm_json(prompt)
    except RuntimeError as e:
        raise BusinessError(str(e))
    # 回填
    repo("jd").update(jd["id"], {
        "company": result.get("company", jd["company"]),
        "title": result.get("title", jd["title"]),
        "direction_tag": result.get("direction_tag", jd["direction_tag"]),
        "url": result.get("url", ""),
        "source": result.get("source", ""),
        "location": result.get("location", ""),
        "salary_range": result.get("salary_range", ""),
        "parsed_json": result.get("parsed_json", {}),
        "note": result.get("note", ""),
    }, summary="AI 在线解析 JD")
    return {"ok": True, "result": result}


@router.post("/online-match")
def online_match(payload: dict = Body(...)):
    """一键简历匹配：LLM 直连 + 入库。"""
    jd = repo("jd").get(payload.get("jd_id"))
    resume = repo("resume").get(payload.get("resume_id"))
    if not jd or not resume:
        raise BusinessError("JD 或简历版本不存在", 404)
    if get_setting("llm_enabled", "0") != "1":
        raise BusinessError("在线模式未开启，请在设置中启用并配置 API Key")
    prompt = build_match_prompt(jd, resume)
    try:
        result = call_llm_json(prompt)
    except RuntimeError as e:
        raise BusinessError(str(e))
    # 入库
    repo("match_result").raw("DELETE FROM match_result WHERE jd_id=? AND resume_id=?", (jd["id"], resume["id"]))
    saved = repo("match_result").create({
        "jd_id": jd["id"], "resume_id": resume["id"],
        "score": result.get("score", 0),
        "dimension_scores": result.get("dimension_scores", {}),
        "matched_points": result.get("matched_points", []),
        "missing_points": result.get("missing_points", []),
        "suggestion": result.get("suggestion", ""),
        "source": "online",
    }, summary="AI 在线匹配打分")
    return {
        "ok": True, "match_id": saved["id"],
        "score": result.get("score"), "suggestion": result.get("suggestion"),
        "suggested_skills": suggest_skills_from_missing(result.get("missing_points", []), jd["direction_tag"]),
    }


@router.post("/online-interview-q")
def online_interview_q(payload: dict = Body(...)):
    """一键生成面试题：LLM 直连 + 入库。"""
    direction = payload.get("direction_tag") or "运营"
    if get_setting("llm_enabled", "0") != "1":
        raise BusinessError("在线模式未开启，请在设置中启用并配置 API Key")
    prompt = build_interview_q_prompt(direction)
    try:
        result = call_llm_json(prompt)
    except RuntimeError as e:
        raise BusinessError(str(e))
    created = 0
    for q in result.get("questions", []):
        if not [x for x in repo("interview_question").list() if x["question"] == q.get("question", "")]:
            repo("interview_question").create({
                "question": q.get("question", ""),
                "category": q.get("category", "行为"),
                "direction_tag": q.get("direction_tag", direction),
                "company": q.get("company", ""),
                "answer_hint": q.get("answer_hint", ""),
            }, summary="AI 在线生成面试题")
            created += 1
    return {"ok": True, "created": created, "questions": result.get("questions", [])}


# ─── 回填导入 ────────────────────────────────────────────
@router.post("/import-result")
def import_result(payload: dict = Body(...)):
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
        repo("match_result").raw("DELETE FROM match_result WHERE jd_id=? AND resume_id=?", (result["jd_id"], result["resume_id"]))
        saved = repo("match_result").create({
            "jd_id": result["jd_id"], "resume_id": result["resume_id"],
            "score": result["score"], "dimension_scores": result["dimension_scores"],
            "matched_points": result["matched_points"],
            "missing_points": result["missing_points"],
            "suggestion": result.get("suggestion", ""), "source": "online",
        }, summary="AI 匹配结果回填")
        return {
            "ok": True, "match_id": saved["id"],
            "suggested_skills": suggest_skills_from_missing(result["missing_points"], jd["direction_tag"]),
        }

    if t == "interview_q":
        created = []
        for q in result["questions"]:
            if not [x for x in repo("interview_question").list() if x["question"] == q["question"]]:
                created.append(repo("interview_question").create(q, summary="AI 生成面试题").get("id"))
        return {"ok": True, "created": len(created)}


# ─── 本地匹配 ────────────────────────────────────────────
@router.post("/match-local")
def match_local(payload: dict = Body(...)):
    jd = repo("jd").get(payload.get("jd_id"))
    resume = repo("resume").get(payload.get("resume_id"))
    if not jd or not resume:
        raise BusinessError("JD 或简历版本不存在", 404)
    out = match(resume, jd)
    repo("match_result").raw("DELETE FROM match_result WHERE jd_id=? AND resume_id=?", (jd["id"], resume["id"]))
    repo("match_result").create({
        "jd_id": jd["id"], "resume_id": resume["id"], "score": out["score"],
        "dimension_scores": out["dimension_scores"],
        "matched_points": out["matched_points"],
        "missing_points": out["missing_points"],
        "suggestion": out["suggestion"], "source": "local",
    }, summary="本地匹配打分")
    return out
