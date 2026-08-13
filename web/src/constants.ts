// 枚举与中文标签（前端下拉/显示用）
export const STATUSES = ['intention', 'applied', 'written', 'interview', 'offer', 'closed']

export const STATUS_LABELS: Record<string, string> = {
  active: '待处理',
  intention: '意向',
  applied: '已投递',
  written: '笔试/测评',
  interview: '面试中',
  offer: 'Offer',
  closed: '已关闭'
}

export const STATUS_COLORS: Record<string, string> = {
  intention: 'bg-slate-100 text-slate-600',
  applied: 'bg-blue-100 text-blue-700',
  written: 'bg-cyan-100 text-cyan-700',
  interview: 'bg-indigo-100 text-indigo-700',
  offer: 'bg-emerald-100 text-emerald-700',
  closed: 'bg-rose-100 text-rose-700'
}

export const DIRECTIONS = ['销售', '运营', '市场', '其他']

export const CHANNELS = ['官网', '内推', '猎头', 'BOSS直聘', '脉脉', '小红书', '其他']

export const PRIORITIES = ['高', '中', '低']

export const PRIORITY_COLORS: Record<string, string> = {
  高: 'bg-red-100 text-red-700',
  中: 'bg-amber-100 text-amber-700',
  低: 'bg-slate-100 text-slate-600'
}

export const ROUNDS = ['笔试/测评', '一面', '二面', '三面', '交叉面', '终面', 'HR面']

export const MODES = ['线上', '电话', '现场']

export const RESULTS: { v: string; l: string }[] = [
  { v: 'pending', l: '待定' },
  { v: 'pass', l: '通过' },
  { v: 'fail', l: '未通过' }
]

export const RESULT_LABELS: Record<string, string> = {
  pending: '待定',
  pass: '通过',
  fail: '未通过'
}

export const ROLES = ['内推人', 'HR', '猎头', '前同事', '业务对接人', '其他']

export const WARMTH = ['熟', '一般', '弱']

export const CATEGORIES = ['行为', '业务', '专业', '公司', '反问', '薪酬']

export const SOURCES = ['匹配缺失', '面试复盘', '自评']

export const SKILL_STATUSES = ['待开始', '进行中', '已达成', '搁置']

export const SKILL_STATUS_COLORS: Record<string, string> = {
  待开始: 'bg-slate-100 text-slate-600',
  进行中: 'bg-indigo-100 text-indigo-700',
  已达成: 'bg-emerald-100 text-emerald-700',
  搁置: 'bg-amber-100 text-amber-700'
}

export const LEVEL_COLORS: Record<string, string> = {
  urgent: 'bg-rose-50 border-rose-300 text-rose-700',
  warn: 'bg-amber-50 border-amber-300 text-amber-700',
  info: 'bg-sky-50 border-sky-300 text-sky-700'
}

// 逐字稿相关
export const SCRIPT_TYPES = ['自我介绍', '工作经历', '项目介绍', '追问应答', '反问面试官', '薪资谈判', '其他']
export const SCRIPT_TAGS = ['通用', '高频', '必背', '待打磨', '已定稿']
