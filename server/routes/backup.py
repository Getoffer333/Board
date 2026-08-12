import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from openpyxl import Workbook

from ..db import BACKUP_DIR

router = APIRouter(prefix="/api/backup", tags=["backup"])

TABLES = ["resume", "jd", "application", "interview", "interview_question",
          "contact", "skill", "skill_log", "match_result", "activity_log"]


@router.post("/export")
def export_backup():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # 全表 JSON
    dump = {}
    for t in TABLES:
        from ..repositories.sqlite_repo import repo
        dump[t] = repo(t).list()
    json_path = BACKUP_DIR / f"backup_{stamp}.json"
    json_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")

    # 投递与联系人 Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "投递"
    cols = ["id", "company_snapshot", "title_snapshot", "direction_tag", "status",
            "channel", "priority", "applied_at", "next_followup_at",
            "expected_salary", "offer_salary", "note"]
    ws.append(cols)
    for a in dump["application"]:
        ws.append([a.get(c, "") for c in cols])
    ws2 = wb.create_sheet("联系人")
    ccols = ["id", "name", "org", "role", "wechat", "phone", "email",
             "last_contact_at", "next_followup_at", "note"]
    ws2.append(ccols)
    for c in dump["contact"]:
        ws2.append([c.get(x, "") for x in ccols])
    xlsx_path = BACKUP_DIR / f"backup_{stamp}.xlsx"
    wb.save(xlsx_path)
    return {"json": json_path.name, "xlsx": xlsx_path.name,
            "size": json_path.stat().st_size + xlsx_path.stat().st_size}


@router.get("/files")
def list_files():
    files = []
    for p in sorted(BACKUP_DIR.glob("*.json"), reverse=True):
        files.append({"name": p.name, "size": p.stat().st_size, "time": p.stat().st_mtime})
    return files
