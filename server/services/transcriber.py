"""Whisper 语音转文字服务 + DeepSeek AI 复盘。"""

import json
from pathlib import Path

from ..db import get_setting
from ..services.llm import call_llm_json


def transcribe_audio(audio_path: str) -> str:
    """用本地 Whisper 将音频转为文字。"""
    try:
        import whisper
        model = whisper.load_model("small")  # small 模型平衡速度与精度
        result = model.transcribe(audio_path, language="zh")
        return result["text"].strip()
    except ImportError:
        raise RuntimeError("Whisper 未安装，请运行: pip install openai-whisper")
    except Exception as e:
        raise RuntimeError(f"语音转写失败: {e}")


def ai_review_interview(transcript: str, interview_context: dict) -> dict:
    """基于面试转录和上下文，用 AI 生成复盘分析。"""
    app_info = interview_context.get("application_info", {})
    questions = interview_context.get("questions", [])
    round_name = interview_context.get("round", "")

    questions_text = ""
    for i, q in enumerate(questions):
        if isinstance(q, dict):
            questions_text += f"Q{i+1}: {q.get('q', '')}\n"
            questions_text += f"A{i+1}: {q.get('my_answer', '')}\n\n"

    prompt = f"""你是一位资深的面试复盘教练。请基于以下面试录音转录文本，对求职者的表现进行全面分析。

### 面试信息
- 面试轮次：{round_name}
- 公司：{app_info.get('company', '未知')}
- 岗位：{app_info.get('title', '未知')}

### 面试录音转录
{transcript[:8000]}

### 已记录的面试问题与回答
{questions_text[:2000] if questions_text else '(面试官未单独记录题目)'}

请对这次面试进行全面复盘分析，输出一个纯 JSON 对象（不要 markdown 包裹）：

{{
  "overall_score": 1-10 的整数综合评分,
  "strengths": ["做得好的 2-3 个方面"],
  "weaknesses": ["做得不好的 2-3 个方面"],
  "key_moments": ["关键转折点（如有）"],
  "interviewer_signals": ["面试官释放的信号（正面/负面/中性）"],
  "questions_quality": [
    {{"question": "面试官问的问题", "your_answer_quality": "回答质量评价", "suggestion": "改进建议"}}
  ],
  "communication_issues": ["表达/沟通方面的问题"],
  "missed_opportunities": ["你应该提到但没说到的点"],
  "action_items": ["面试后需要做的 2-3 件事"],
  "summary": "整体评价，2-3 句话"
}}
"""
    return call_llm_json(prompt)
