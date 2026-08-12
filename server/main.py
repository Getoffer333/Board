"""FastAPI 入口：托管 API 与构建后的前端，单端口 7788。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .models import BusinessError
from .routes import (
    ai,
    application,
    backup,
    contact,
    interview,
    jd,
    question,
    resume,
    settings,
    skill,
    stats,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="个人求职工作台")


@app.on_event("startup")
def _startup() -> None:
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BusinessError)
async def _biz_error(_, exc: BusinessError):
    return JSONResponse(status_code=exc.code, content={"error": exc.message})


@app.get("/api/health")
async def health():
    return {"ok": True}


for _r in (resume, jd, application, interview, contact, skill, ai, stats, settings, backup, question):
    app.include_router(_r.router)

# 前端构建产物由后端单端口托管；Vue 用 hash 路由，不需要服务端 fallback
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:
    @app.get("/")
    async def _only_api():
        return {"msg": "后端已就绪，前端尚未构建（运行 npm run build 后生效）"}
