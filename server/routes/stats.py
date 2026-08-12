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
        "reminders": len(build_reminders()),
    }
