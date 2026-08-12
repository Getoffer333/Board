from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..db import RESUME_DIR, now
from ..models import BusinessError, DIRECTIONS
from ..repositories.sqlite_repo import repo
from ..services.parser import extract_resume_text

router = APIRouter(prefix="/api/resumes", tags=["resume"])


@router.get("")
def list_resumes(direction: str = ""):
    if direction:
        return [r for r in repo("resume").list() if direction in (r.get("direction_tags") or [])]
    return repo("resume").list()


@router.get("/{rid}")
def get_resume(rid: int):
    item = repo("resume").get(rid)
    if not item:
        raise BusinessError("简历版本不存在", 404)
    return item


@router.post("")
async def create_resume(
    version_name: str = Form(...),
    direction_tags: str = Form("[]"),
    note: str = Form(""),
    file: UploadFile | None = None,
):
    import json

    try:
        tags = json.loads(direction_tags)
    except (json.JSONDecodeError, TypeError):
        tags = []
    for t in tags:
        if t not in DIRECTIONS:
            raise BusinessError(f"方向非法：{t}")

    payload = {"version_name": version_name, "direction_tags": tags, "note": note}
    content_text = ""
    file_name = None
    rel_path = None
    if file and file.filename:
        data = await file.read()
        suffix = file.filename[file.filename.rfind("."):] if "." in file.filename else ""
        safe = f"{version_name}{suffix}".replace("/", "_")
        path = RESUME_DIR / safe
        path.write_bytes(data)
        rel_path = f"resumes/{safe}"
        file_name = file.filename
        content_text = extract_resume_text(path)
    payload.update(content_text=content_text, file_name=file_name, file_path=rel_path)
    return repo("resume").create(payload, summary=f"新建简历版本 {version_name}")


@router.put("/{rid}")
async def update_resume(
    rid: int,
    version_name: str = Form(None),
    direction_tags: str = Form(None),
    note: str = Form(None),
):
    import json

    payload = {}
    if version_name is not None:
        payload["version_name"] = version_name
    if note is not None:
        payload["note"] = note
    if direction_tags is not None:
        try:
            tags = json.loads(direction_tags)
        except (json.JSONDecodeError, TypeError):
            tags = []
        for t in tags:
            if t not in DIRECTIONS:
                raise BusinessError(f"方向非法：{t}")
        payload["direction_tags"] = tags
    return repo("resume").update(rid, payload)


@router.post("/{rid}/file")
async def upload_file(rid: int, file: UploadFile):
    item = repo("resume").get(rid)
    if not item:
        raise BusinessError("简历版本不存在", 404)
    data = await file.read()
    suffix = file.filename[file.filename.rfind("."):] if "." in file.filename else ""
    safe = f"{item['version_name']}{suffix}".replace("/", "_")
    path = RESUME_DIR / safe
    path.write_bytes(data)
    content_text = extract_resume_text(path)
    return repo("resume").update(
        rid, {"file_name": file.filename, "file_path": f"resumes/{safe}", "content_text": content_text}
    )


@router.get("/{rid}/download")
def download(rid: int):
    item = repo("resume").get(rid)
    if not item or not item.get("file_path"):
        raise BusinessError("无简历文件", 404)
    p = RESUME_DIR.parent / item["file_path"]
    if not p.exists():
        raise BusinessError("文件已丢失", 404)
    return FileResponse(str(p), filename=item.get("file_name") or p.name)


@router.delete("/{rid}")
def delete_resume(rid: int):
    if repo("application").count("resume_id=?", (rid,)) > 0:
        raise BusinessError("该简历已有投递记录，无法删除（可保留作历史）")
    repo("resume").delete(rid, summary=f"删除简历 {rid}")
    return {"ok": True}
