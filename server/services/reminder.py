"""提醒计算。

不做后台常驻推送（本地服务可能没开着），改为每次打开工作台时实时算。
"""

from datetime import date, datetime, timedelta

from ..models import (
    FOLLOWUP_STALE_DAYS,
    OFFER_DECISION_DAYS,
    REVIEW_OVERDUE_DAYS,
    STATUS_LABELS,
)
from ..repositories.sqlite_repo import repo


def _to_date(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    return None


def _days_since(value: str | None) -> int | None:
    d = _to_date(value)
    return (date.today() - d).days if d else None


def build_reminders() -> list[dict]:
    items: list[dict] = []
    today = date.today()

    apps = repo("application").list()
    app_map = {a["id"]: a for a in apps}

    for app in apps:
        label = f"{app['company_snapshot']} · {app['title_snapshot']}"
        status = app["status"]

        if status == "applied":
            gap = _days_since(app.get("stage_entered_at"))
            if gap is not None and gap >= FOLLOWUP_STALE_DAYS:
                items.append({
                    "type": "followup", "level": "warn" if gap < 14 else "urgent",
                    "title": f"{label} 已投递 {gap} 天无进展",
                    "detail": "建议找内推人或 HR 主动问一次进度，超过两周基本可以判定沉了。",
                    "entity": "application", "entity_id": app["id"],
                })

        if status == "offer":
            gap = _days_since(app.get("stage_entered_at"))
            if gap is not None and gap >= OFFER_DECISION_DAYS:
                items.append({
                    "type": "offer", "level": "urgent",
                    "title": f"{label} 的 offer 已挂 {gap} 天未决策",
                    "detail": "拖太久容易让对方以为你在观望，尽快给明确回复或谈条件。",
                    "entity": "application", "entity_id": app["id"],
                })

        nf = _to_date(app.get("next_followup_at"))
        if nf and status != "closed" and nf <= today:
            overdue = (today - nf).days
            items.append({
                "type": "followup", "level": "urgent" if overdue > 2 else "warn",
                "title": f"{label} 的跟进日期已到"
                         + (f"（逾期 {overdue} 天）" if overdue else ""),
                "detail": f"当前阶段：{STATUS_LABELS.get(status, status)}。",
                "entity": "application", "entity_id": app["id"],
            })

    for itv in repo("interview").list():
        app = app_map.get(itv["application_id"])
        if not app:
            continue
        label = f"{app['company_snapshot']} · {itv['round']}"
        sd = _to_date(itv.get("scheduled_at"))
        if not sd:
            continue
        if sd >= today and (sd - today).days <= 7:
            when = "今天" if sd == today else (
                "明天" if (sd - today).days == 1 else f"{(sd - today).days} 天后")
            items.append({
                "type": "interview", "level": "urgent" if (sd - today).days <= 1 else "info",
                "title": f"{when}有面试：{label}",
                "detail": f"时间 {itv.get('scheduled_at')}，方式 {itv.get('mode')}。"
                          "面试前把题库里同类问题过一遍。",
                "entity": "interview", "entity_id": itv["id"],
            })
        elif itv.get("result") == "pending" and (today - sd).days >= REVIEW_OVERDUE_DAYS:
            items.append({
                "type": "review", "level": "warn",
                "title": f"{label} 面完 {(today - sd).days} 天还没复盘",
                "detail": "记忆最鲜活的是 24 小时内，越晚复盘越没价值。",
                "entity": "interview", "entity_id": itv["id"],
            })

    for c in repo("contact").list():
        nf = _to_date(c.get("next_followup_at"))
        if nf and nf <= today:
            items.append({
                "type": "contact", "level": "info",
                "title": f"该联系 {c['name']}"
                         + (f"（{c.get('org') or ''}）" if c.get("org") else ""),
                "detail": f"上次联系：{c.get('last_contact_at') or '无记录'}，"
                          f"节奏 {c.get('followup_cycle_days')} 天。",
                "entity": "contact", "entity_id": c["id"],
            })

    order = {"urgent": 0, "warn": 1, "info": 2}
    items.sort(key=lambda x: order.get(x["level"], 3))
    return items


def default_next_followup(days: int = FOLLOWUP_STALE_DAYS) -> str:
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")
