"""路由聚合，便于 main 统一导入。"""

from . import (
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

__all__ = [
    "resume",
    "jd",
    "application",
    "interview",
    "contact",
    "skill",
    "ai",
    "stats",
    "settings",
    "backup",
    "question",
]
