from fastapi import APIRouter, Body

from ..db import now
from ..models import (
    INTERVIEW_MODES,
    INTERVIEW_RESULTS,
    INTERVIEW_ROUNDS,
    BusinessError,
    assert_in,
)
from ..repositories.sqlite_repo import repo

router = APIRouter(prefix="/api/interviews", tags=["interview"])


@router.get("/by-application/{aid}")
def list_by_app(aid: int):
    return repo("interview").list("application_id=?", (aid,))


@router.post("")
def create_interview(payload: dict = Body(...)):
    aid = payload.get("application_id")
    if not aid or not repo("application").get(aid):
        raise BusinessError("关联投递不存在", 404)
    assert_in(payload.get("round", "一面"), INTERVIEW_ROUNDS, "round")
    assert_in(payload.get("mode", "线上"), INTERVIEW_MODES, "mode")
    data = {
        "application_id": aid,
        "round": payload.get("round", "一面"),
        "scheduled_at": payload.get("scheduled_at"),
        "duration_min": payload.get("duration_min"),
        "mode": payload.get("mode", "线上"),
        "location": payload.get("location", ""),
        "interviewers": payload.get("interviewers", []),
        "questions": payload.get("questions", []),
        "result": "pending",
    }
    return repo("interview").create(data, summary=f"新建面试 {data['round']}")


@router.put("/{iid}")
def update_interview(iid: int, payload: dict = Body(...)):
    assert_in(payload.get("round", "一面"), INTERVIEW_ROUNDS, "round") if "round" in payload else None
    assert_in(payload.get("mode", "线上"), INTERVIEW_MODES, "mode") if "mode" in payload else None
    data = {k: v for k, v in payload.items() if k in (
        "round", "scheduled_at", "duration_min", "mode", "location",
        "interviewers", "questions")}
    return repo("interview").update(iid, data)


@router.post("/{iid}/review")
def review(iid: int, payload: dict = Body(...)):
    itv = repo("interview").get(iid)
    if not itv:
        raise BusinessError("面试不存在", 404)
    assert_in(payload.get("result", "pending"), INTERVIEW_RESULTS, "result") if "result" in payload else None
    data = {k: v for k, v in payload.items() if k in (
        "went_well", "went_bad", "action_items", "result", "self_score")}
    repo("interview").update(iid, data, summary="提交面试复盘")

    # 闭环：未答出的题 → 题库沉淀 + 技能差距项
    for q in payload.get("unanswered", []) or []:
        q = q.strip()
        if not q:
            continue
        existing = [x for x in repo("interview_question").list()
                    if x["question"] == q]
        if existing:
            repo("interview_question").update(
                existing[0]["id"], {"frequency": existing[0]["frequency"] + 1})
        else:
            repo("interview_question").create({
                "question": q, "category": "专业",
                "direction_tag": payload.get("direction_tag", ""),
                "source_interview_id": iid, "company": payload.get("company", ""),
            }, summary="复盘沉淀高频题")
        # 技能差距项（面试复盘来源）
        same_skill = [s for s in repo("skill").list()
                      if s["name"] == q and (s.get("direction_tag") or "") == (payload.get("direction_tag") or "")]
        if not same_skill:
            repo("skill").create({
                "name": q, "direction_tag": payload.get("direction_tag", ""),
                "category": "面试复盘", "source": "面试复盘",
                "current_level": 1, "target_level": 3,
            }, summary="面试暴露的技能差距")

    # 主动沉淀面试题库
    for q in payload.get("bank", []) or []:
        q = (q.get("question") if isinstance(q, dict) else q) if isinstance(q, (dict, str)) else ""
        if isinstance(q, dict):
            qtext = q.get("question", "")
            cat = q.get("category", "行为")
        else:
            qtext, cat = q, "行为"
        qtext = (qtext or "").strip()
        if not qtext:
            continue
        if not [x for x in repo("interview_question").list() if x["question"] == qtext]:
            repo("interview_question").create({
                "question": qtext, "category": cat,
                "direction_tag": payload.get("direction_tag", ""),
                "source_interview_id": iid,
            })
    return repo("interview").get(iid)


@router.delete("/{iid}")
def delete_interview(iid: int):
    repo("interview").delete(iid, summary=f"删除面试 {iid}")
    return {"ok": True}
