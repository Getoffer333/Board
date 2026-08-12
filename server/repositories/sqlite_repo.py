"""SQLite 实现。JSON 字段自动序列化/反序列化。"""

from __future__ import annotations

import json
import sqlite3

from ..db import get_conn, log_activity, now
from ..models import BusinessError

# 每张表中需要按 JSON 存取的字段，以及默认值类型
JSON_FIELDS = {
    "resume": {"direction_tags": list, "highlights": list},
    "jd": {"parsed_json": dict},
    "interview": {"interviewers": list, "questions": list},
    "match_result": {"dimension_scores": dict, "matched_points": list, "missing_points": list},
    "interview_script": {"tags": list},
}

TIMESTAMPED = {
    "resume", "jd", "contact", "application", "interview",
    "interview_question", "skill", "interview_script",
}


class SqliteRepository:
    def __init__(self, table: str):
        self.table = table
        self.json_fields = JSON_FIELDS.get(table, {})

    # ---------- 序列化 ----------
    def _dump(self, payload: dict) -> dict:
        out = dict(payload)
        for field, kind in self.json_fields.items():
            if field in out and not isinstance(out[field], str):
                out[field] = json.dumps(out[field] if out[field] is not None else kind(),
                                        ensure_ascii=False)
        return out

    def _load(self, row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        item = dict(row)
        for field, kind in self.json_fields.items():
            if field in item:
                try:
                    item[field] = json.loads(item[field]) if item[field] else kind()
                except (json.JSONDecodeError, TypeError):
                    item[field] = kind()
        return item

    def _columns(self, conn) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({self.table})").fetchall()
        return {r["name"] for r in rows}

    # ---------- 查询 ----------
    def list(self, where: str = "", params: tuple = (), order: str = "") -> list[dict]:
        sql = f"SELECT * FROM {self.table}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {order}" if order else " ORDER BY id DESC"
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._load(r) for r in rows]

    def get(self, row_id: int) -> dict | None:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT * FROM {self.table} WHERE id=?", (row_id,)
            ).fetchone()
        return self._load(row)

    def count(self, where: str = "", params: tuple = ()) -> int:
        sql = f"SELECT COUNT(*) AS c FROM {self.table}"
        if where:
            sql += f" WHERE {where}"
        with get_conn() as conn:
            return conn.execute(sql, params).fetchone()["c"]

    def raw(self, sql: str, params: tuple = ()) -> list[dict]:
        with get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ---------- 写入 ----------
    def create(self, payload: dict, summary: str = "") -> dict:
        data = self._dump(payload)
        ts = now()
        with get_conn() as conn:
            cols = self._columns(conn)
            data = {k: v for k, v in data.items() if k in cols and k != "id"}
            if self.table in TIMESTAMPED:
                data.setdefault("created_at", ts)
                data.setdefault("updated_at", ts)
            elif "created_at" in cols:
                data.setdefault("created_at", ts)
            if not data:
                raise BusinessError("没有可写入的字段")
            keys = ", ".join(data)
            marks = ", ".join("?" for _ in data)
            try:
                cur = conn.execute(
                    f"INSERT INTO {self.table}({keys}) VALUES({marks})",
                    tuple(data.values()),
                )
            except sqlite3.IntegrityError as exc:
                raise BusinessError(_friendly(exc, self.table)) from exc
            new_id = cur.lastrowid
            log_activity(conn, self.table, new_id, "create", summary)
        return self.get(new_id)

    def update(self, row_id: int, payload: dict, summary: str = "") -> dict:
        if self.get(row_id) is None:
            raise BusinessError("记录不存在", 404)
        data = self._dump(payload)
        with get_conn() as conn:
            cols = self._columns(conn)
            data = {k: v for k, v in data.items() if k in cols and k not in ("id", "created_at")}
            if self.table in TIMESTAMPED:
                data["updated_at"] = now()
            if not data:
                return self.get(row_id)
            sets = ", ".join(f"{k}=?" for k in data)
            try:
                conn.execute(
                    f"UPDATE {self.table} SET {sets} WHERE id=?",
                    (*data.values(), row_id),
                )
            except sqlite3.IntegrityError as exc:
                raise BusinessError(_friendly(exc, self.table)) from exc
            log_activity(conn, self.table, row_id, "update", summary)
        return self.get(row_id)

    def delete(self, row_id: int, summary: str = "") -> None:
        with get_conn() as conn:
            try:
                conn.execute(f"DELETE FROM {self.table} WHERE id=?", (row_id,))
            except sqlite3.IntegrityError as exc:
                raise BusinessError(
                    "该记录已被其他数据引用，无法删除。请先解除关联"
                ) from exc
            log_activity(conn, self.table, row_id, "delete", summary)


def _friendly(exc: Exception, table: str) -> str:
    text = str(exc)
    if "UNIQUE" in text:
        if table == "resume":
            return "已存在同名简历版本，请换一个版本名"
        if table == "skill":
            return "该方向下已有同名技能项"
        return "存在重复记录"
    if "FOREIGN KEY" in text:
        return "关联的记录不存在或已被删除"
    if "NOT NULL" in text:
        field = text.split(".")[-1] if "." in text else ""
        return f"必填字段缺失：{field}"
    return text


_cache: dict[str, SqliteRepository] = {}


def repo(table: str) -> SqliteRepository:
    if table not in _cache:
        _cache[table] = SqliteRepository(table)
    return _cache[table]
