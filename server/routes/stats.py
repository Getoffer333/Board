from datetime import datetime, timedelta

from fastapi import APIRouter

from ..models import FUNNEL_ORDER, STATUS_LABELS
from ..repositories.sqlite_repo import repo
from ..services.reminder import build_reminders

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/funnel")
def funnel():
    apps = repo("application").list()
    counts = {s: 0 for s in STATUS_LABELS}
    for a in apps:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    total = len(apps)
    series = []
    prev = None
    for s in FUNNEL_ORDER:
        c = counts.get(s, 0)
        rate_from_prev = None if prev is None else (round(c / prev * 100) if prev else 0)
        rate_from_start = round(c / total * 100) if total else 0
        series.append({
            "status": s, "label": STATUS_LABELS[s], "count": c,
            "rate_from_prev": rate_from_prev, "rate_from_start": rate_from_start,
        })
        prev = c
    return {"total": total, "counts": counts, "series": series}


@router.get("/direction")
def by_direction():
    apps = repo("application").list()
    out = {}
    for a in apps:
        d = a["direction_tag"]
        out.setdefault(d, {"direction": d, "applications": 0, "interviews": 0, "offers": 0, "closed": 0})
        out[d]["applications"] += 1
        if a["status"] in ("interview", "offer"):
            out[d]["interviews"] += 1
        if a["status"] == "offer":
            out[d]["offers"] += 1
        if a["status"] == "closed":
            out[d]["closed"] += 1
    for v in out.values():
        v["interview_rate"] = round(v["interviews"] / v["applications"] * 100) if v["applications"] else 0
        v["offer_rate"] = round(v["offers"] / v["applications"] * 100) if v["applications"] else 0
    return list(out.values())


@router.get("/resume-versions")
def resume_versions():
    apps = repo("application").list()
    out = {}
    for r in repo("resume").list():
        out[r["id"]] = {
            "id": r["id"], "version": r["version_name"],
            "direction": (r.get("direction_tags") or [])[0] if r.get("direction_tags") else "",
            "used": 0, "interviews": 0, "offers": 0,
        }
    for a in apps:
        rid = a["resume_id"]
        if rid in out:
            out[rid]["used"] += 1
            if a["status"] in ("interview", "offer"):
                out[rid]["interviews"] += 1
            if a["status"] == "offer":
                out[rid]["offers"] += 1
    return list(out.values())


@router.get("/overdue")
def overdue():
    return build_reminders()


@router.get("/summary")
def summary():
    apps = repo("application").list()
    active = [a for a in apps if a["status"] not in ("closed",)]
    return {
        "total_applications": len(apps),
        "active": len(active),
        "interviews": sum(1 for a in apps if a["status"] == "interview"),
        "offers": sum(1 for a in apps if a["status"] == "offer"),
        "resumes": repo("resume").count(),
        "jds": repo("jd").count(),
        "contacts": repo("contact").count(),
        "questions": repo("interview_question").count(),
        "skills": repo("skill").count(),
        "scripts": repo("interview_script").count(),
        "reminders": len(build_reminders()),
    }


# ─── 新增：时间线与日历 ──────────────────────────────────
@router.get("/timeline")
def timeline(days: int = 30):
    """最近 N 天的投递活动时间线。"""
    apps = repo("application").list()
    logs = repo("activity_log").raw(
        "SELECT * FROM activity_log ORDER BY ts DESC LIMIT ?",
        (days * 3,))
    today = datetime.now().date()
    cutoff = today - timedelta(days=days)

    # 投递时间线
    items = []
    for a in apps:
        applied = a.get("applied_at")
        if applied:
            try:
                d = datetime.strptime(applied[:10], "%Y-%m-%d").date()
                if d >= cutoff:
                    items.append({"date": str(d), "type": "投递", "company": a["company_snapshot"], "title": a["title_snapshot"], "status": a["status"]})
            except (ValueError, TypeError):
                pass

    # 活动日志
    for log in logs:
        try:
            d = datetime.strptime(log["ts"][:10], "%Y-%m-%d").date()
            if d >= cutoff:
                items.append({"date": str(d), "type": log["action"], "summary": log.get("summary", ""), "entity_type": log["entity_type"]})
        except (ValueError, TypeError):
            pass

    # 按日期倒序
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:50]


@router.get("/calendar")
def calendar_view(month: str = ""):
    """获取指定月份的面试日程。"""
    now_dt = datetime.now()
    if month:
        try:
            year, mon = month.split("-")
            now_dt = datetime(int(year), int(mon), 1)
        except (ValueError, IndexError):
            pass

    interviews = []
    for itv in repo("interview").list():
        scheduled = itv.get("scheduled_at")
        if scheduled:
            try:
                d = datetime.strptime(scheduled[:10], "%Y-%m-%d")
                app = repo("application").get(itv["application_id"])
                interviews.append({
                    "id": itv["id"],
                    "date": str(d.date()),
                    "round": itv["round"],
                    "company": (app["company_snapshot"] if app else "未知"),
                    "title": (app["title_snapshot"] if app else ""),
                    "mode": itv["mode"],
                    "result": itv["result"],
                })
            except (ValueError, TypeError):
                pass

    interviews.sort(key=lambda x: x["date"])
    return {"interviews": interviews, "month": f"{now_dt.year}-{now_dt.month:02d}"}


# ─── 新增：JD 智能推荐 ────────────────────────────────────
@router.get("/jd-recommendations")
def jd_recommendations():
    """列出所有 JD 的匹配分，按得分排序。"""
    jds = repo("jd").list()
    resumes = repo("resume").list()
    matches = repo("match_result").list()

    out = []
    for jd in jds:
        if jd["status"] == "closed":
            continue
        # 找该 JD 的最佳匹配分
        best_score = 0
        best_resume = ""
        for m in matches:
            if m["jd_id"] == jd["id"] and m["score"] > best_score:
                best_score = m["score"]
                best_resume = next((r["version_name"] for r in resumes if r["id"] == m["resume_id"]), "")

        # 检查是否已投递
        applied = any(a["jd_id"] == jd["id"] and a["status"] not in ("closed",) for a in repo("application").list())

        out.append({
            "jd_id": jd["id"],
            "company": jd["company"],
            "title": jd["title"],
            "direction": jd["direction_tag"],
            "location": jd.get("location", ""),
            "salary": jd.get("salary_range", ""),
            "match_score": best_score,
            "matched_resume": best_resume,
            "applied": applied,
            "status": jd["status"],
        })

    out.sort(key=lambda x: -x["match_score"])
    return out


@router.get("/weekly-snapshot")
def weekly_snapshot():
    """本周/下周快照。"""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    next_monday = monday + timedelta(days=7)
    next_sunday = next_monday + timedelta(days=6)

    apps = repo("application").list()
    interviews = repo("interview").list()

    this_week_apps = 0
    next_week_interviews = 0
    next_week_followups = 0

    for a in apps:
        applied = a.get("applied_at")
        if applied:
            try:
                d = datetime.strptime(applied[:10], "%Y-%m-%d").date()
                if monday <= d <= sunday:
                    this_week_apps += 1
            except (ValueError, TypeError):
                pass
        nf = a.get("next_followup_at")
        if nf:
            try:
                d = datetime.strptime(nf[:10], "%Y-%m-%d").date()
                if next_monday <= d <= next_sunday:
                    next_week_followups += 1
            except (ValueError, TypeError):
                pass

    for itv in interviews:
        scheduled = itv.get("scheduled_at")
        if scheduled and itv.get("result") != "fail":
            try:
                d = datetime.strptime(scheduled[:10], "%Y-%m-%d").date()
                if next_monday <= d <= next_sunday:
                    next_week_interviews += 1
            except (ValueError, TypeError):
                pass

    return {
        "this_week": {"start": str(monday), "end": str(sunday), "applications": this_week_apps},
        "next_week": {"start": str(next_monday), "end": str(next_sunday), "interviews": next_week_interviews, "followups": next_week_followups},
    }
