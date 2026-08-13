"""数据库连接与初始化。

数据文件全部位于项目 data/ 目录，与代码分离，便于整体备份与迁移。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESUME_DIR = DATA_DIR / "resumes"
IMPORT_DIR = DATA_DIR / "imports"
BACKUP_DIR = DATA_DIR / "backups"
AUDIO_DIR = DATA_DIR / "audio"
CONFIG_DIR = BASE_DIR / "config"
DB_PATH = DATA_DIR / "app.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

for _d in (DATA_DIR, RESUME_DIR, IMPORT_DIR, BACKUP_DIR, AUDIO_DIR, CONFIG_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    from .models import DEFAULT_SETTINGS

    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO setting(key, value) VALUES(?, ?)", (key, value)
            )


def log_activity(conn, entity_type: str, entity_id, action: str, summary: str = "") -> None:
    conn.execute(
        "INSERT INTO activity_log(ts, entity_type, entity_id, action, summary)"
        " VALUES(?,?,?,?,?)",
        (now(), entity_type, entity_id, action, summary),
    )


def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM setting WHERE key=?", (key,)).fetchone()
    return row["value"] if row and row["value"] is not None else default


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO setting(key, value) VALUES(?,?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def load_json(text, fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return fallback


# 历史版本新增的字段（表, 列名, DDL），启动时自动补齐
_MIGRATIONS = [
    ("jd", "ai_parsed", "INTEGER NOT NULL DEFAULT 0"),
    ("jd", "direction_alert", "TEXT"),
    ("interview", "audio_path", "TEXT"),
    ("interview", "transcript", "TEXT"),
    ("interview", "ai_review", "TEXT"),
]


def migrate_db() -> None:
    """轻量自动迁移：为旧库补齐缺失的列，避免手动 ALTER TABLE。"""
    with get_conn() as conn:
        for table, col, ddl in _MIGRATIONS:
            try:
                cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            except sqlite3.Error:
                continue  # 表还不存在，交给 init_db 建表
            if col not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
