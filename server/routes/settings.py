from fastapi import APIRouter, Body

from ..db import get_setting, set_setting
from ..models import DEFAULT_SETTINGS, DIRECTIONS, BusinessError

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return {k: get_setting(k, v) for k, v in DEFAULT_SETTINGS.items()}


@router.put("")
def update_settings(payload: dict = Body(...)):
    allowed = set(DEFAULT_SETTINGS.keys())
    for k, v in payload.items():
        if k not in allowed:
            raise BusinessError(f"未知设置项：{k}")
        if k == "primary_direction" and v not in DIRECTIONS:
            raise BusinessError(f"主方向非法：{v}")
        set_setting(k, v)
    return {k: get_setting(k, v) for k, v in DEFAULT_SETTINGS.items()}
