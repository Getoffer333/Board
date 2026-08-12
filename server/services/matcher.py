"""简历 × JD 本地匹配打分。

四个维度、可解释、不依赖任何外部模型：
  关键词覆盖 45 / 硬性条件 25 / 方向契合 15 / 岗位职责呼应 15
AI 通道的结果写入同一张表，用 source 字段区分。
"""

from ..db import get_setting, load_json
from .parser import KEYWORD_LIB, extract_keywords


def _resume_corpus(resume: dict) -> str:
    parts = [
        resume.get("content_text") or "",
        resume.get("note") or "",
        " ".join(resume.get("highlights") or []),
        resume.get("version_name") or "",
    ]
    return "\n".join(parts).lower()


def match(resume: dict, jd: dict) -> dict:
    parsed = jd.get("parsed_json") or {}
    if isinstance(parsed, str):
        parsed = load_json(parsed, {})

    corpus = _resume_corpus(resume)
    jd_keywords = parsed.get("keywords") or extract_keywords(
        f"{jd.get('raw_text') or ''} {jd.get('title') or ''}"
    )

    matched = [k for k in jd_keywords if k.lower() in corpus]
    missing = [k for k in jd_keywords if k.lower() not in corpus]

    # 1) 关键词覆盖 45 分
    if jd_keywords:
        kw_score = round(45 * len(matched) / len(jd_keywords))
    else:
        kw_score = 22  # JD 没抽到关键词时给中位分，避免误判为不匹配

    # 2) 硬性条件 25 分：年限与学历
    hard_score, hard_notes = 25, []
    years_need = parsed.get("years_required")
    years_have = int(get_setting("years_experience", "0") or 0)
    if years_need and years_have:
        if years_have + 1 < years_need:
            hard_score -= 12
            hard_notes.append(f"JD 要求 {years_need} 年经验，当前 {years_have} 年")
    edu_need = parsed.get("education_required")
    edu_rank = {"大专": 1, "本科": 2, "统招本科": 2, "研究生": 3, "硕士": 3, "博士": 4}
    if edu_need:
        need = edu_rank.get(edu_need, 0)
        have = edu_rank.get(get_setting("education", "本科"), 2)
        if have < need:
            hard_score -= 8
            hard_notes.append(f"学历要求 {edu_need}")

    # 3) 方向契合 15 分
    direction = jd.get("direction_tag") or "其他"
    tags = resume.get("direction_tags") or []
    if direction in tags:
        dir_score = 15
    elif not tags:
        dir_score = 8
    else:
        dir_score = 5
        hard_notes.append(f"该简历版本未标记「{direction}」方向")

    # 4) 岗位职责呼应 15 分：职责条目里的动词性描述在简历中是否有对应表达
    duties = parsed.get("responsibilities") or []
    if duties:
        hit = 0
        for duty in duties:
            words = [w for w in extract_keywords(duty)]
            if words and any(w.lower() in corpus for w in words):
                hit += 1
        duty_score = round(15 * hit / len(duties))
    else:
        duty_score = 8

    total = max(0, min(100, kw_score + hard_score + dir_score + duty_score))

    return {
        "jd_id": jd["id"],
        "resume_id": resume["id"],
        "score": total,
        "dimension_scores": {
            "关键词覆盖": kw_score,
            "硬性条件": hard_score,
            "方向契合": dir_score,
            "职责呼应": duty_score,
        },
        "matched_points": matched,
        "missing_points": missing,
        "suggestion": build_suggestion(total, matched, missing, hard_notes, direction),
        "source": "local",
    }


def build_suggestion(score, matched, missing, hard_notes, direction) -> str:
    lines = []
    if score >= 75:
        lines.append("匹配度较高，建议优先投递，重点在简历里前置已命中的关键词。")
    elif score >= 55:
        lines.append("中等匹配，值得投，但建议先针对性改一版简历再投。")
    else:
        lines.append("匹配度偏低，若不是特别想去的公司，优先级可以往后放。")

    if missing:
        top = "、".join(missing[:8])
        lines.append(f"简历里没有体现的 JD 关键词：{top}。如果你实际做过，务必补进经历描述。")
        lines.append("如果确实没做过，把它记进技能计划，不要在简历里硬凑。")
    if matched:
        lines.append(f"已命中并建议前置强化：{('、'.join(matched[:8]))}。")
    for note in hard_notes:
        lines.append(f"注意：{note}。")
    lines.append(f"该 JD 归属方向：{direction}。")
    return "\n".join(lines)


def suggest_skills_from_missing(missing: list[str], direction: str) -> list[dict]:
    """把匹配缺失项转成技能计划候选。只保留在词库中的正经技能词。"""
    pool = set(KEYWORD_LIB.get(direction, [])) | set(KEYWORD_LIB["通用"])
    return [
        {"name": word, "direction_tag": direction, "source": "匹配缺失",
         "category": "岗位要求"}
        for word in missing if word in pool
    ]
