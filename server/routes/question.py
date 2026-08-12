from fastapi import APIRouter, Body

from ..models import QUESTION_CATEGORIES, assert_in
from ..repositories.sqlite_repo import repo

router = APIRouter(prefix="/api/questions", tags=["question"])


@router.get("")
def list_questions(direction: str = "", category: str = "", mastered: int = -1):
    rows = repo("interview_question").list()
    if direction:
        rows = [r for r in rows if (r.get("direction_tag") or "") == direction]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if mastered >= 0:
        rows = [r for r in rows if r["mastered"] == mastered]
    rows.sort(key=lambda x: x.get("frequency", 0), reverse=True)
    return rows


@router.post("")
def create_question(payload: dict = Body(...)):
    assert_in(payload.get("category", "行为"), QUESTION_CATEGORIES, "category")
    data = {
        "question": payload.get("question", ""),
        "category": payload.get("category", "行为"),
        "direction_tag": payload.get("direction_tag", ""),
        "company": payload.get("company", ""),
        "answer_hint": payload.get("answer_hint", ""),
    }
    if not data["question"]:
        raise BusinessError("题目必填")
    return repo("interview_question").create(data, summary="新增题库题目")


@router.put("/{qid}")
def update_question(qid: int, payload: dict = Body(...)):
    data = {k: v for k, v in payload.items() if k in (
        "question", "category", "direction_tag", "company",
        "answer_hint", "mastered")}
    if "category" in data:
        assert_in(data["category"], QUESTION_CATEGORIES, "category")
    return repo("interview_question").update(qid, data)


@router.delete("/{qid}")
def delete_question(qid: int):
    repo("interview_question").delete(qid, summary=f"删除题库题目 {qid}")
    return {"ok": True}
