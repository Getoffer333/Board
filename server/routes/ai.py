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
def _apply_jd_parse(jd_id: int, result: dict) -> dict:
    """将 AI 解析结果回填到 JD，含方向偏离预警（AI 判断 + 规则兜底）。"""
    primary = get_setting("primary_direction", "")
    backups = load_json(get_setting("backup_directions", "[]"), [])
    allowed = set([primary] + [b for b in backups if b])
    direction = result.get("direction_tag", "")
    rule_alert = ""
    if direction and direction != "其他" and allowed and direction not in allowed:
        rule_alert = f"方向偏离：该岗位为「{direction}」，你的求职方向是「{'/'.join(sorted(allowed))}」"
    alert = (result.get("direction_alert") or "").strip() or rule_alert

    jd = repo("jd").get(jd_id)
    repo("jd").update(jd_id, {
        "company": result.get("company") or jd.get("company") or "",
        "title": result.get("title") or jd.get("title") or "",
        "direction_tag": direction or jd.get("direction_tag") or "",
        "url": result.get("url", ""),
        "source": result.get("source", ""),
        "location": result.get("location", ""),
        "salary_range": result.get("salary_range", ""),
        "parsed_json": result.get("parsed_json", {}),
        "direction_alert": alert,
        "note": result.get("note", ""),
        "ai_parsed": 1,
    }, summary="AI 在线解析 JD")
    return repo("jd").get(jd_id)


@router.post("/online-jd-parse")
def online_jd_parse(payload: dict = Body(...)):
    """一键 JD 解析：LLM 直接调用 + 回填入库。"""
    jd = repo("jd").get(payload.get("jd_id"))
    if not jd:
        raise BusinessError("JD 不存在", 404)
    if get_setting("llm_enabled", "0") != "1":
        raise BusinessError("在线模式未开启，请在设置中启用并配置 API Key")
    try:
        result = call_llm_json(build_jd_parse_prompt(jd))
    except RuntimeError as e:
        raise BusinessError(str(e))
    updated = _apply_jd_parse(jd["id"], result)
    return {"ok": True, "result": updated}


@router.post("/batch-jd-parse")
def batch_jd_parse():
    """批量解析：找出所有已粘贴但未 AI 解析的 JD，并行调用 LLM 后串行入库。"""
    if get_setting("llm_enabled", "0") != "1":
        raise BusinessError("在线模式未开启，请在设置中启用并配置 API Key")
    todos = [j for j in repo("jd").list()
             if not j.get("ai_parsed") and (j.get("raw_text") or "").strip()]
    if not todos:
        return {"ok": True, "total": 0, "parsed": 0, "failed": 0,
                "results": [], "message": "没有待解析的 JD"}

    from concurrent.futures import ThreadPoolExecutor

    def _fetch(jd):
        """并行调用 LLM（线程安全），结果暂不写库。"""
        try:
            result = call_llm_json(build_jd_parse_prompt(jd))
            return jd, result, None
        except Exception as e:
            return jd, None, str(e)

    # 并行调 LLM（耗时的部分），4 个并发
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(_fetch, todos))

    # 串行写库（SQLite 写入安全）
    results = []
    for jd, result, err in fetched:
        if err:
            results.append({"jd_id": jd["id"], "ok": False, "error": err})
        else:
            try:
                _apply_jd_parse(jd["id"], result)
                results.append({"jd_id": jd["id"], "ok": True,
                                "company": result.get("company", ""),
                                "title": result.get("title", "")})
            except Exception as e:
                results.append({"jd_id": jd["id"], "ok": False, "error": str(e)})

    ok = sum(1 for r in results if r["ok"])
    return {"ok": True, "total": len(todos), "parsed": ok,
            "failed": len(todos) - ok, "results": results}


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
        "resume_edits": result.get("resume_edits", []),
        "suggestion": result.get("suggestion", ""),
        "source": "online",
    }, summary="AI 在线匹配打分")
    return {
        "ok": True, "match_id": saved["id"],
        "score": result.get("score"), "suggestion": result.get("suggestion"),
        "dimension_scores": result.get("dimension_scores", {}),
        "matched_points": result.get("matched_points", []),
        "missing_points": result.get("missing_points", []),
        "resume_edits": result.get("resume_edits", []),
        "suggested_skills": suggest_skills_from_missing(result.get("missing_points", []), jd["direction_tag"]),
    }


@router.post("/batch-match")
def batch_match(payload: dict = Body(...)):
    """批量匹配：对勾选的多个 JD 用激活简历做 AI 匹配。已匹配过的直接复用结果（去重）。"""
    if get_setting("llm_enabled", "0") != "1":
        raise BusinessError("在线模式未开启，请在设置中启用并配置 API Key")
    jd_ids = payload.get("jd_ids") or []
    if not jd_ids:
        raise BusinessError("请先勾选要匹配的 JD")
    force = bool(payload.get("force", False))  # 强制重新匹配

    resume_id = payload.get("resume_id")
    resume = repo("resume").get(resume_id) if resume_id else None
    if not resume:
        actives = [r for r in repo("resume").list() if r.get("is_active", 1)]
        resume = actives[0] if actives else None
    if not resume:
        raise BusinessError("请先上传简历（无激活简历可匹配）", 404)

    jds = [repo("jd").get(i) for i in jd_ids]
    jds = [j for j in jds if j]
    if not jds:
        raise BusinessError("没有可匹配的 JD")

    # ── 去重：已匹配过的复用结果，只对新 JD 调 AI ──
    reused_results = []
    to_match = []
    for jd in jds:
        existing = repo("match_result").raw(
            "SELECT * FROM match_result WHERE jd_id=? AND resume_id=? AND source='online' ORDER BY id DESC LIMIT 1",
            (jd["id"], resume["id"]))
        if existing and not force:
            r = existing[0]
            reused_results.append({
                "jd_id": jd["id"], "company": jd["company"], "title": jd["title"],
                "ok": True, "reused": True,
                "score": r["score"],
                "dimension_scores": load_json(r["dimension_scores"], {}),
                "matched_points": load_json(r["matched_points"], []),
                "missing_points": load_json(r["missing_points"], []),
                "resume_edits": load_json(r.get("resume_edits"), []),
                "suggestion": r.get("suggestion", ""),
            })
        else:
            to_match.append(jd)

    from concurrent.futures import ThreadPoolExecutor

    def _match_one(jd):
        try:
            result = call_llm_json(build_match_prompt(jd, resume))
            return jd, result, None
        except Exception as e:
            return jd, None, str(e)

    fresh_results = []
    if to_match:
        with ThreadPoolExecutor(max_workers=4) as pool:
            fetched = list(pool.map(_match_one, to_match))

        for jd, result, err in fetched:
            if err:
                fresh_results.append({"jd_id": jd["id"], "company": jd["company"],
                                      "title": jd["title"], "ok": False, "error": err})
            else:
                repo("match_result").raw(
                    "DELETE FROM match_result WHERE jd_id=? AND resume_id=?",
                    (jd["id"], resume["id"]))
                repo("match_result").create({
                    "jd_id": jd["id"], "resume_id": resume["id"],
                    "score": result.get("score", 0),
                    "dimension_scores": result.get("dimension_scores", {}),
                    "matched_points": result.get("matched_points", []),
                    "missing_points": result.get("missing_points", []),
                    "resume_edits": result.get("resume_edits", []),
                    "suggestion": result.get("suggestion", ""),
                    "source": "online",
                }, summary="AI 批量匹配")
                fresh_results.append({
                    "jd_id": jd["id"], "company": jd["company"], "title": jd["title"],
                    "ok": True, "reused": False, "score": result.get("score", 0),
                    "dimension_scores": result.get("dimension_scores", {}),
                    "matched_points": result.get("matched_points", []),
                    "missing_points": result.get("missing_points", []),
                    "resume_edits": result.get("resume_edits", []),
                    "suggestion": result.get("suggestion", ""),
                })

    # 合并，按勾选顺序排序
    results = reused_results + fresh_results
    order = {i: idx for idx, i in enumerate(jd_ids)}
    results.sort(key=lambda x: order.get(x["jd_id"], 99999))

    ok = sum(1 for r in results if r["ok"])
    return {"ok": True, "total": len(jds), "matched": ok,
            "failed": len(jds) - ok, "reused": len(reused_results),
            "results": results, "resume_version": resume.get("version_name")}


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
            "resume_edits": result.get("resume_edits", []),
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
