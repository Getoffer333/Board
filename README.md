# 求职工作台 v2.0

个人求职全流程管理工具：简历 → JD → 投递 → 面试 → 复盘 → Offer，本地数据不联网。

## 一键启动（Mac）

```bash
cd ~/Desktop/求职工作台
git pull origin main
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/start.sh
```

浏览器打开 `http://localhost:7788`

## 模块

| 模块 | 说明 |
|------|------|
| 📊 驾驶舱 | 漏斗/方向对比/JD推荐/时间线/周快照 |
| 📄 简历库 | 多版本管理，docx/pdf 解析 |
| 📋 JD库 | 粘贴 JD 自动解析关键词 |
| 🚀 投递看板 | 六状态拖拽看板 |
| 🎙️ 逐字稿 🆕 | 自我介绍/工作经历逐字稿管理+练习打卡 |
| 🎤 面试中心 | 轮次管理+复盘→技能闭环 |
| 🤖 AI工具 🆕 | 在线一键 JD解析/匹配/面试题生成（需 DeepSeek Key） |
| ⚙️ 设置 | 配 Key 解锁 AI 在线功能 |

## Windows 启动

双击 `start.bat`
