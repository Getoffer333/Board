"""领域常量、枚举与状态机定义。

所有业务约束集中在这里，路由层只做调用，避免规则散落。
"""

DIRECTIONS = ["销售", "运营", "市场", "其他"]

# ---------------- 投递状态机 ----------------
STATUSES = ["intention", "applied", "written", "interview", "offer", "closed"]

STATUS_LABELS = {
    "intention": "意向",
    "applied": "已投递",
    "written": "笔试/测评",
    "interview": "面试中",
    "offer": "Offer",
    "closed": "已关闭",
}

# 白名单流转：禁止跳阶段，防止统计口径失真
TRANSITIONS = {
    "intention": ["applied", "closed"],
    "applied": ["written", "interview", "closed"],
    "written": ["interview", "closed", "applied"],
    "interview": ["interview", "offer", "closed", "written"],
    "offer": ["closed", "interview"],
    "closed": ["intention", "applied", "interview"],  # 允许误操作回滚
}

# 漏斗口径：只统计真正投出去的
FUNNEL_ORDER = ["applied", "written", "interview", "offer"]

CHANNELS = ["官网", "内推", "猎头", "BOSS直聘", "脉脉", "小红书", "其他"]
PRIORITIES = ["高", "中", "低"]
INTERVIEW_ROUNDS = ["笔试/测评", "一面", "二面", "三面", "交叉面", "终面", "HR面"]
INTERVIEW_MODES = ["线上", "电话", "现场"]
INTERVIEW_RESULTS = ["pending", "pass", "fail"]
CONTACT_ROLES = ["内推人", "HR", "猎头", "前同事", "业务对接人", "其他"]
WARMTH = ["熟", "一般", "弱"]
QUESTION_CATEGORIES = ["行为", "业务", "专业", "公司", "反问", "薪酬"]
SKILL_SOURCES = ["匹配缺失", "面试复盘", "自评"]
SKILL_STATUSES = ["待开始", "进行中", "已达成", "搁置"]
SCRIPT_TYPES = ["自我介绍", "工作经历", "项目介绍", "追问应答", "反问面试官", "薪资谈判", "其他"]
SCRIPT_TAGS = ["通用", "高频", "必背", "待打磨", "已定稿"]

# ---------------- 提醒规则 ----------------
# 投递后无进展多少天提醒跟进
FOLLOWUP_STALE_DAYS = 7
# 面试日过后多少天未填结果提醒复盘
REVIEW_OVERDUE_DAYS = 1
# offer 后多少天未决策提醒
OFFER_DECISION_DAYS = 3

DEFAULT_SETTINGS = {
    "primary_direction": "运营",
    "backup_directions": '["销售", "市场"]',
    "owner_name": "",
    "years_experience": "5",
    "education": "本科",
    "current_city": "杭州",
    "llm_enabled": "0",
    "llm_base_url": "",
    "llm_api_key": "",
    "llm_model": "",
}


class BusinessError(Exception):
    """可直接回给前端展示的业务错误。"""

    def __init__(self, message: str, code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code


def assert_transition(old: str, new: str) -> None:
    if old == new:
        return
    allowed = TRANSITIONS.get(old, [])
    if new not in allowed:
        raise BusinessError(
            f"不允许从「{STATUS_LABELS.get(old, old)}」直接变为"
            f"「{STATUS_LABELS.get(new, new)}」，请按流程逐步推进"
        )


def assert_in(value, options, field: str):
    if value is not None and value != "" and value not in options:
        raise BusinessError(f"{field} 取值非法：{value}")
    return value
