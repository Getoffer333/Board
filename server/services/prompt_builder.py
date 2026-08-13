"""AI 离线双通道：prompt 生成 + 回填 JSON 校验。

离线模式：工作台导出结构化 prompt → 用户在 AI 对话里跑 → 把结果 JSON
粘贴回「导入结果」接口。本模块负责两件事：
  1. 生成三类 prompt（JD 解析 / 简历匹配 / 面试题生成）
  2. 校验回填 JSON 的 schema，脏数据直接拒绝，不让进库

在线模式（可选）：settings 里填 LLM key 后，同类请求由后端直连，
结果写同一张表，用 source 区分。prompt 格式与离线完全一致。
"""

import json

from ..db import get_setting, load_json
from ..models import DIRECTIONS, BusinessError


def _owner_intro() -> str:
    name = get_setting("owner_name", "")
    years = get_setting("years_experience", "")
    edu = get_setting("education", "")
    city = get_setting("current_city", "")
    parts = [p for p in [f"姓名 {name}" if name else "",
                         f"工作年限 {years} 年" if years else "",
                         f"学历 {edu}" if edu else "",
                         f"所在城市 {city}" if city else ""] if p]
    return "；".join(parts) if parts else "（未在设置中填写个人背景）"


def _owner_direction() -> str:
    """求职方向（主方向 + 备选方向），用于方向偏离预警。"""
    primary = get_setting("primary_direction", "")
    backups = load_json(get_setting("backup_directions", "[]"), [])
    parts = [primary] if primary else []
    parts += [b for b in backups if b]
    return "/".join(parts) if parts else "未设置"


def build_jd_parse_prompt(jd: dict) -> str:
    raw = jd.get("raw_text") or ""
    head = (f"公司：{jd.get('company') or '未知'}\n"
            f"岗位：{jd.get('title') or '未知'}\n"
            f"方向：{jd.get('direction_tag') or '未知'}")
    direction = _owner_direction()
    return f"""你是一名招聘信息结构化助手。下面是一段 JD 原文（已带部分元信息）。

{head}

求职者的求职方向：{direction}

--- JD 原文开始 ---
{raw}
--- JD 原文结束 ---

请抽取字段，并以**一个纯 JSON 对象**返回（不要输出任何解释文字、不要加 ``` 包裹）：

{{
  "company": "公司名",
  "title": "岗位名",
  "direction_tag": "销售 | 运营 | 市场 | 其他（按内容选最贴切的一个）",
  "url": "来源链接，没有则留空",
  "source": "内推 | 官网 | 猎头 | 招聘平台 | 其他",
  "location": "工作城市",
  "salary_range": "薪资范围，如 15-25k，没有则留空",
  "parsed_json": {{
    "responsibilities": ["岗位职责要点，每条一句"],
    "requirements": ["任职要求要点，每条一句"],
    "keywords": ["该岗位核心技能/能力关键词"],
    "years_required": 经验年限数字或 null,
    "education_required": "学历要求或 null",
    "highlights": ["岗位亮点，如双休/期权/业务前景"]
  }},
  "direction_alert": "若该岗位方向与求职者方向（{direction}）明显不符（如机械工程师、程序员等），写一句预警说明；否则留空字符串",
  "note": "其他需要记住的信息"
}}
"""


def build_match_prompt(jd: dict, resume: dict) -> str:
    parsed = jd.get("parsed_json") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
    jd_text = jd.get("raw_text") or ""
    resume_text = resume.get("content_text") or ""
    return f"""你是简历匹配评估助手。请基于「求职者简历」与「目标 JD」做匹配度评估。

求职者背景：{_owner_intro()}

===== 目标 JD =====
公司：{jd.get('company')}　岗位：{jd.get('title')}　方向：{jd.get('direction_tag')}
JD 关键词：{', '.join(parsed.get('keywords', []))}
JD 要求：{chr(10).join(parsed.get('requirements', []))}

===== 简历版本：{resume.get('version_name')} =====
{resume_text[:4000]}

请输出**一个纯 JSON 对象**（不要解释文字、不要 ``` 包裹）：

{{
  "jd_id": {jd.get('id')},
  "resume_id": {resume.get('id')},
  "score": 0-100 的整数综合匹配分,
  "dimension_scores": {{
    "关键词覆盖": 0-45,
    "硬性条件": 0-25,
    "方向契合": 0-15,
    "职责呼应": 0-15
  }},
  "matched_points": ["简历中已体现、且 JD 看重的点"],
  "missing_points": ["JD 要求但简历里没体现的点（用于后续补简历/补技能）"],
  "suggestion": "给求职者的改写与投递建议，2-4 句"
}}
"""


def build_interview_q_prompt(direction: str) -> str:
    return f"""你是面试教练。请为「{direction}」方向的求职者生成一套高频面试题，
帮助ta提前准备。求职者背景：{_owner_intro()}

请输出**一个纯 JSON 对象**（不要解释文字、不要 ``` 包裹）：

{{
  "questions": [
    {{
      "question": "题目",
      "category": "行为 | 业务 | 专业 | 公司 | 反问 | 薪酬",
      "direction_tag": "{direction}",
      "company": "",
      "answer_hint": "回答要点提示"
    }}
  ]
}}

要求：生成 8-12 题，覆盖行为/业务/专业/反问多类；反问环节至少 2 题；
每题给可操作的回答要点。
"""


# ---------------- 回填校验 ----------------
def validate_import(payload: dict) -> dict:
    """校验 AI 回填 JSON，返回标准化 {type, result}。非法直接抛 BusinessError。"""
    if not isinstance(payload, dict):
        raise BusinessError("请求体必须是 JSON 对象")
    t = payload.get("type")
    if t not in ("jd_parse", "match", "interview_q"):
        raise BusinessError("type 非法，应为 jd_parse / match / interview_q")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise BusinessError("result 必须是 JSON 对象")

    if t == "jd_parse":
        for f in ("company", "title", "direction_tag"):
            if not str(result.get(f, "")).strip():
                raise BusinessError(f"jd_parse 的 result 缺少必填字段：{f}")
        if result["direction_tag"] not in DIRECTIONS:
            raise BusinessError(f"direction_tag 非法：{result['direction_tag']}")
        pj = result.get("parsed_json") or {}
        if not isinstance(pj, dict):
            raise BusinessError("parsed_json 必须是对象")
        result["parsed_json"] = {
            "responsibilities": list(pj.get("responsibilities", []) or []),
            "requirements": list(pj.get("requirements", []) or []),
            "keywords": list(p := pj.get("keywords", []) or []),
            "years_required": pj.get("years_required"),
            "education_required": pj.get("education_required"),
            "highlights": list(pj.get("highlights", []) or []),
        }
    elif t == "match":
        for f in ("jd_id", "resume_id", "score"):
            if f not in result:
                raise BusinessError(f"match 的 result 缺少必填字段：{f}")
        try:
            result["score"] = int(result["score"])
            result["jd_id"] = int(result["jd_id"])
            result["resume_id"] = int(result["resume_id"])
        except (TypeError, ValueError):
            raise BusinessError("jd_id / resume_id / score 必须是数字")
        if not (0 <= result["score"] <= 100):
            raise BusinessError("score 必须在 0-100 之间")
        ds = result.get("dimension_scores") or {}
        result["dimension_scores"] = {
            "关键词覆盖": int(ds.get("关键词覆盖", 0) or 0),
            "硬性条件": int(ds.get("硬性条件", 0) or 0),
            "方向契合": int(ds.get("方向契合", 0) or 0),
            "职责呼应": int(ds.get("职责呼应", 0) or 0),
        }
        result["matched_points"] = list(result.get("matched_points", []) or [])
        result["missing_points"] = list(result.get("missing_points", []) or [])
    elif t == "interview_q":
        questions = result.get("questions")
        if not isinstance(questions, list) or not questions:
            raise BusinessError("interview_q 的 result.questions 必须是非空数组")
        cleaned = []
        cats = ["行为", "业务", "专业", "公司", "反问", "薪酬"]
        for i, q in enumerate(questions):
            if not isinstance(q, dict) or not str(q.get("question", "")).strip():
                raise BusinessError(f"第 {i+1} 题缺少 question 字段")
            if q.get("category") and q["category"] not in cats:
                raise BusinessError(f"第 {i+1} 题 category 非法：{q['category']}")
            cleaned.append({
                "question": str(q["question"]).strip(),
                "category": q.get("category") or "行为",
                "direction_tag": q.get("direction_tag") or direction_fallback(q),
                "company": str(q.get("company") or ""),
                "answer_hint": str(q.get("answer_hint") or ""),
            })
        result["questions"] = cleaned

    return {"type": t, "result": result}


def direction_fallback(q: dict) -> str:
    return q.get("direction_tag") or get_setting("primary_direction", "运营")
