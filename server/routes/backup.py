import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from openpyxl import Workbook

from ..db import BACKUP_DIR
from ..models import BusinessError

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
    for p in sorted(BACKUP_DIR.glob("*.xlsx"), reverse=True):
        files.append({"name": p.name, "size": p.stat().st_size, "time": p.stat().st_mtime})
    files.sort(key=lambda x: -x["time"])
    return files


@router.get("/download/{filename}")
def download_file(filename: str):
    """下载备份文件。"""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise BusinessError("非法文件名", 400)
    p = BACKUP_DIR / filename
    if not p.exists() or not p.is_file():
        raise BusinessError("文件不存在", 404)
    return FileResponse(str(p), filename=filename)
