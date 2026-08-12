"""数据访问抽象层。

所有读写都必须经过 Repository 接口，路由层不直接写 SQL。
将来上云换 Postgres / REST 只需新增一个实现类，业务代码不动。
"""

from __future__ import annotations

from typing import Any, Protocol


class Repository(Protocol):
    table: str

    def list(self, where: str = "", params: tuple = (), order: str = "") -> list[dict]: ...

    def get(self, row_id: int) -> dict | None: ...

    def create(self, payload: dict) -> dict: ...

    def update(self, row_id: int, payload: dict) -> dict: ...

    def delete(self, row_id: int) -> None: ...

    def count(self, where: str = "", params: tuple = ()) -> int: ...

    def raw(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]: ...
