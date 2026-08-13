<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import JDDetailModal from '../components/JDDetailModal.vue'
import { DIRECTIONS, CHANNELS, STATUS_LABELS } from '../constants'
import type { JD } from '../types'

const items = ref<JD[]>([])
const showModal = ref(false)
const form = ref({
  raw_text: '', company: '', title: '', direction_tag: '',
  salary_range: '', location: '', source: '', status: 'active', note: ''
})

// 批量解析
const batchParsing = ref(false)
const batchProgress = ref('')

const unparsedCount = computed(() =>
  items.value.filter(j => !j.ai_parsed && (j.raw_text || '').trim()).length
)

// 列表分区：待解析（上）/ 已解析（下）
const pendingItems = computed(() => items.value.filter(j => !j.ai_parsed))
const parsedItems = computed(() => items.value.filter(j => !!j.ai_parsed))

// 匹配评分排序
const sortByScore = ref<'asc' | 'desc' | null>(null)
function toggleSort() {
  sortByScore.value = sortByScore.value === 'desc' ? 'asc' : 'desc'
}
function sortList(list: JD[]): JD[] {
  if (!sortByScore.value) return list
  const dir = sortByScore.value === 'desc' ? -1 : 1
  return [...list].sort((a, b) => dir * ((a.match_score || 0) - (b.match_score || 0)))
}
const sortedPendingItems = computed(() => sortList(pendingItems.value))
const sortedParsedItems = computed(() => sortList(parsedItems.value))

async function load() {
  try {
    items.value = await api.get<JD[]>('/api/jds?status=&direction=')
  } catch (e: any) { toast('error', e.message) }
}

function openModal() {
  form.value = { raw_text: '', company: '', title: '', direction_tag: '', salary_range: '', location: '', source: '', status: 'active', note: '' }
  showModal.value = true
}

async function submit() {
  if (!form.value.raw_text.trim()) { toast('error', '请粘贴 JD 原文'); return }
  try {
    const created = await api.post<JD>('/api/jds', { ...form.value })
    if ((created as any).duplicate_warning) {
      toast('warn', `⚠️ 已存在相同岗位「${created.company} · ${created.title}」，可能重复`)
    } else {
      toast('success', 'JD 已创建')
    }
    showModal.value = false
    await load()
  } catch (e: any) { toast('error', e.message) }
}

async function batchParse() {
  if (batchParsing.value) return
  batchParsing.value = true
  batchProgress.value = `正在并行解析 ${unparsedCount.value} 个 JD（约 1-2 分钟）...`
  try {
    const r = await api.post<any>('/api/ai/batch-jd-parse')
    batchProgress.value = ''
    if (r.total === 0) {
      toast('info', r.message || '没有待解析的 JD')
    } else {
      toast('success', `批量解析完成：成功 ${r.parsed} / ${r.total}${r.failed ? `，失败 ${r.failed}` : ''}`)
      if (r.failed) {
        const errs = r.results.filter((x: any) => !x.ok).map((x: any) => `#${x.jd_id}: ${x.error}`).join('；')
        toast('error', `部分失败：${errs}`)
      }
    }
    await load()
  } catch (e: any) { toast('error', e.message) }
  batchParsing.value = false
}

async function remove(j: JD) {
  if (!confirm(`确认删除 JD「${j.company} · ${j.title}」？`)) return
  try { await api.del(`/api/jds/${j.id}`); toast('success', '已删除'); await load() }
  catch (e: any) { toast('error', e.message) }
}

// 详情（复用 JDDetailModal 组件）
const detailJdId = ref<number | null>(null)
function openDetail(j: JD) {
  detailJdId.value = j.id
}

// 关键词趋势
const showTrends = ref(false)
const trends = ref<any>(null)
async function openTrends() {
  showTrends.value = true
  trends.value = null
  try {
    trends.value = await api.get<any>('/api/stats/keyword-trends')
  } catch (e: any) { toast('error', e.message) }
}

// 勾选 + 批量 AI 匹配
const selectedIds = ref<Set<number>>(new Set())
const matchPanelOpen = ref(false)
const matchResults = ref<any>(null)
const matching = ref(false)
const forceMatch = ref(false)

function toggleSelect(id: number) {
  const s = new Set(selectedIds.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  selectedIds.value = s
}
function toggleAll() {
  selectedIds.value = selectedIds.value.size === parsedItems.value.length
    ? new Set()
    : new Set(parsedItems.value.map(j => j.id))
}
async function batchMatch() {
  if (selectedIds.value.size === 0) { toast('error', '请先勾选要匹配的 JD'); return }
  if (matching.value) return
  matching.value = true
  toast('info', forceMatch.value ? '强制重新匹配中，约需 1-2 分钟...' : `开始 AI 匹配 ${selectedIds.value.size} 个 JD（已匹配过的自动复用），约需 1-2 分钟...`)
  try {
    const r = await api.post<any>('/api/ai/batch-match', { jd_ids: [...selectedIds.value], force: forceMatch.value })
    matchResults.value = r
    matchPanelOpen.value = true
    toast('success', `匹配完成 ${r.matched}/${r.total}${r.reused ? `（复用 ${r.reused} 个）` : ''}`)
  } catch (e: any) { toast('error', e.message) }
  matching.value = false
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between gap-2 flex-wrap">
      <p class="text-sm text-slate-500">粘贴 JD 原文，批量解析后自动识别公司/岗位/关键词/方向。</p>
      <div class="flex gap-2">
        <button class="btn-ghost" @click="openTrends">📊 关键词趋势</button>
        <button class="btn-primary" :disabled="batchParsing" @click="batchParse">
          ⚡ 批量解析<span v-if="unparsedCount" class="ml-1 rounded bg-white/30 px-1.5 text-xs">{{ unparsedCount }}</span>
        </button>
        <button class="btn-primary" :disabled="matching" @click="batchMatch">
          🤖 一键匹配<span v-if="selectedIds.size" class="ml-1 rounded bg-white/30 px-1.5 text-xs">{{ selectedIds.size }}</span>
        </button>
        <label class="flex cursor-pointer items-center gap-1 text-xs text-slate-500" title="简历更新后勾选此项可重新匹配">
          <input type="checkbox" v-model="forceMatch" class="accent-rose-500" /> 强制重匹配
        </label>
        <button class="btn-primary" @click="openModal">+ 新建 JD</button>
      </div>
    </div>

    <div v-if="batchParsing" class="rounded-lg bg-indigo-50 px-4 py-3 text-sm text-indigo-700 animate-pulse">
      {{ batchProgress }}
    </div>

    <div v-if="matching" class="rounded-lg bg-blue-50 px-4 py-3 text-sm text-blue-700 animate-pulse">
      🤖 正在并行匹配 {{ selectedIds.size }} 个 JD（约 1-2 分钟），请稍候...
    </div>

    <!-- 待解析区 -->
    <div class="card overflow-x-auto">
      <div class="mb-2 flex items-center gap-2">
        <h3 class="font-semibold text-amber-700">⏳ 待解析</h3>
        <span class="text-xs text-slate-400">{{ pendingItems.length }} 份</span>
      </div>
      <table v-if="pendingItems.length" class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">公司</th>
            <th>岗位</th>
            <th>方向</th>
            <th>薪资</th>
            <th>匹配评分</th>
            <th>状态</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in sortedPendingItems" :key="j.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="py-2 font-medium"><button class="cursor-pointer text-indigo-600 hover:underline" @click="openDetail(j)">{{ j.company }}</button></td>
            <td>{{ j.title }}</td>
            <td>{{ j.direction_tag || '—' }}</td>
            <td class="text-slate-500">{{ j.salary_range || '—' }}</td>
            <td>
              <span v-if="j.match_score" class="font-semibold" :class="j.match_score >= 75 ? 'text-emerald-600' : j.match_score >= 55 ? 'text-amber-600' : 'text-slate-400'">{{ j.match_score }}</span>
              <span v-else class="text-slate-300">—</span>
            </td>
            <td>{{ STATUS_LABELS[j.status] || j.status }}</td>
            <td class="text-right">
              <button class="btn-ghost mr-1" @click="openDetail(j)">详情</button>
              <button class="btn-danger" @click="remove(j)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="py-4 text-center text-sm text-slate-400">没有待解析的 JD 🎉</div>
    </div>

    <!-- 已解析区 -->
    <div v-if="parsedItems.length" class="card overflow-x-auto">
      <div class="mb-2 flex items-center gap-2">
        <h3 class="font-semibold text-emerald-700">✅ 已解析</h3>
        <span class="text-xs text-slate-400">{{ parsedItems.length }} 份 · 勾选后可「🤖 一键匹配」</span>
      </div>
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="w-8 py-2"><input type="checkbox" :checked="selectedIds.size === parsedItems.length && parsedItems.length > 0" @change="toggleAll" /></th>
            <th class="py-2">公司</th>
            <th>岗位</th>
            <th>方向</th>
            <th>薪资</th>
            <th class="cursor-pointer select-none whitespace-nowrap" title="点击按匹配评分排序" @click="toggleSort">
              匹配评分
              <span v-if="sortByScore === 'desc'">↓</span>
              <span v-else-if="sortByScore === 'asc'">↑</span>
              <span v-else class="text-slate-300">↕</span>
            </th>
            <th>状态</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in sortedParsedItems" :key="j.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="w-8"><input type="checkbox" :checked="selectedIds.has(j.id)" @change="toggleSelect(j.id)" /></td>
            <td class="py-2 font-medium"><button class="cursor-pointer text-indigo-600 hover:underline" @click="openDetail(j)">{{ j.company }}</button></td>
            <td>{{ j.title }}</td>
            <td>
              <span class="inline-flex items-center gap-1">
                {{ j.direction_tag || '—' }}
                <span v-if="j.direction_alert" class="text-amber-500" :title="j.direction_alert">⚠️</span>
              </span>
            </td>
            <td class="text-slate-500">{{ j.salary_range || '—' }}</td>
            <td>
              <span v-if="j.match_score" class="font-semibold" :class="j.match_score >= 75 ? 'text-emerald-600' : j.match_score >= 55 ? 'text-amber-600' : 'text-slate-400'">{{ j.match_score }}</span>
              <span v-else class="text-slate-300">—</span>
            </td>
            <td>{{ STATUS_LABELS[j.status] || j.status }}</td>
            <td class="text-right">
              <button class="btn-ghost mr-1" @click="openDetail(j)">详情</button>
              <button class="btn-danger" @click="remove(j)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 详情弹窗（复用组件） -->
    <JDDetailModal v-model:jdId="detailJdId" @changed="load" />

    <!-- 关键词趋势弹窗 -->
    <Modal v-model="showTrends" title="📊 关键词需求趋势" width="44rem">
      <div v-if="!trends" class="py-8 text-center text-slate-400">加载中...</div>
      <div v-else class="space-y-4 max-h-[70vh] overflow-y-auto">
        <p class="text-sm text-slate-500">共 {{ trends.total_jds }} 份 JD，市场最常要求的技能关键词：</p>

        <div v-if="trends.missing?.length">
          <h4 class="mb-1 font-semibold text-rose-700">❌ 市场要，但你简历里没有</h4>
          <div class="flex flex-wrap gap-2">
            <span v-for="k in trends.missing" :key="k.keyword" class="badge bg-rose-100 text-rose-700">
              {{ k.keyword }} <span class="text-rose-400">×{{ k.count }}</span>
            </span>
          </div>
        </div>

        <div v-if="trends.matched?.length">
          <h4 class="mb-1 font-semibold text-emerald-700">✅ 你已具备</h4>
          <div class="flex flex-wrap gap-2">
            <span v-for="k in trends.matched" :key="k.keyword" class="badge bg-emerald-100 text-emerald-700">
              {{ k.keyword }} <span class="text-emerald-400">×{{ k.count }}</span>
            </span>
          </div>
        </div>

        <div v-if="!trends.top?.length" class="py-4 text-center text-slate-400">
          暂无关键词数据，先批量解析几份 JD 后就能看到趋势。
        </div>
      </div>
    </Modal>

    <!-- 匹配结果面板 -->
    <Modal v-model="matchPanelOpen" title="🤖 AI 匹配结果" width="56rem">
      <div v-if="!matchResults" class="py-8 text-center text-slate-400">加载中...</div>
      <div v-else class="space-y-4 max-h-[70vh] overflow-y-auto">
        <div class="text-sm text-slate-500">
          对比简历：<span class="font-medium text-slate-700">{{ matchResults.resume_version || '—' }}</span>
          · 成功 <span class="text-emerald-600">{{ matchResults.matched }}</span> / {{ matchResults.total }}
          <span v-if="matchResults.reused" class="text-slate-400"> · ♻️ 复用 {{ matchResults.reused }} 个</span>
        </div>
        <div v-for="r in matchResults.results" :key="r.jd_id" class="rounded-lg border border-slate-200 p-3">
          <div class="flex items-center justify-between">
            <div class="font-semibold text-slate-800">
              {{ r.company }} · {{ r.title }}
              <span v-if="r.reused && r.reused_source === 'online'" class="ml-1 text-xs font-normal text-slate-400">♻️ 复用 AI 结果</span>
              <span v-else-if="r.reused" class="ml-1 text-xs font-normal text-amber-500">⚠️ 复用本地结果（要 AI 分析请勾「强制重匹配」）</span>
            </div>
            <span v-if="r.ok" class="text-2xl font-bold" :class="r.score >= 75 ? 'text-emerald-600' : r.score >= 55 ? 'text-amber-600' : 'text-rose-600'">{{ r.score }}</span>
            <span v-else class="text-xs text-rose-600">失败：{{ r.error }}</span>
          </div>
          <template v-if="r.ok">
            <div v-if="r.matched_points?.length" class="mt-2 text-sm">
              <div class="font-medium text-emerald-700">✅ 符合</div>
              <ul class="list-disc pl-4 text-slate-600 space-y-0.5"><li v-for="(m, i) in r.matched_points" :key="i">{{ m }}</li></ul>
            </div>
            <div v-if="r.missing_points?.length" class="mt-2 text-sm">
              <div class="font-medium text-rose-700">❌ 不符合</div>
              <ul class="list-disc pl-4 text-slate-600 space-y-0.5"><li v-for="(m, i) in r.missing_points" :key="i">{{ m }}</li></ul>
            </div>
            <div v-if="r.resume_edits?.length" class="mt-2 rounded bg-blue-50 p-2 text-sm">
              <div class="font-medium text-blue-700">📝 简历怎么改</div>
              <ul class="list-disc pl-4 text-slate-700 space-y-0.5"><li v-for="(e, i) in r.resume_edits" :key="i">{{ e }}</li></ul>
            </div>
            <div v-if="r.suggestion" class="mt-2 text-sm text-slate-500">{{ r.suggestion }}</div>
          </template>
        </div>
      </div>
    </Modal>

    <!-- 新建 JD -->
    <Modal v-model="showModal" title="新建 JD">
      <div class="space-y-4">
        <div>
          <label class="label">JD 原文 *（其余可空，批量解析时 AI 自动填）</label>
          <textarea v-model="form.raw_text" rows="6" class="input" placeholder="粘贴职位描述全文…"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">公司</label><input v-model="form.company" class="input" /></div>
          <div><label class="label">岗位</label><input v-model="form.title" class="input" /></div>
          <div>
            <label class="label">方向</label>
            <select v-model="form.direction_tag" class="input">
              <option value="">（自动猜）</option>
              <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div><label class="label">薪资</label><input v-model="form.salary_range" class="input" /></div>
          <div><label class="label">城市</label><input v-model="form.location" class="input" /></div>
          <div>
            <label class="label">来源</label>
            <select v-model="form.source" class="input">
              <option value="">（可选）</option>
              <option v-for="c in CHANNELS" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showModal = false">取消</button>
        <button class="btn-primary" @click="submit">保存</button>
      </template>
    </Modal>
  </div>
</template>
