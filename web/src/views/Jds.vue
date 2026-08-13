<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
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

// 详情
const detail = ref<any>(null)
const showDetail = ref(false)
const detailLoading = ref(false)
async function openDetail(j: JD) {
  showDetail.value = true
  detailLoading.value = true
  detail.value = { jd: j }
  try {
    detail.value = await api.get<any>(`/api/jds/${j.id}/analyze`)
  } catch (e: any) { toast('error', e.message) }
  detailLoading.value = false
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
        <button class="btn-primary" @click="openModal">+ 新建 JD</button>
      </div>
    </div>

    <div v-if="batchParsing" class="rounded-lg bg-indigo-50 px-4 py-3 text-sm text-indigo-700 animate-pulse">
      {{ batchProgress }}
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">公司</th>
            <th>岗位</th>
            <th>方向</th>
            <th>薪资</th>
            <th>解析</th>
            <th>状态</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in items" :key="j.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="py-2 font-medium">{{ j.company }}</td>
            <td>{{ j.title }}</td>
            <td>
              <span class="inline-flex items-center gap-1">
                {{ j.direction_tag || '—' }}
                <span v-if="j.direction_alert" class="text-amber-500" :title="j.direction_alert">⚠️</span>
              </span>
            </td>
            <td class="text-slate-500">{{ j.salary_range || '—' }}</td>
            <td>
              <span v-if="j.ai_parsed" class="badge bg-emerald-100 text-emerald-700">已解析</span>
              <span v-else-if="j.raw_text" class="badge bg-amber-100 text-amber-700">待解析</span>
              <span v-else class="text-slate-300">—</span>
            </td>
            <td>{{ STATUS_LABELS[j.status] || j.status }}</td>
            <td class="text-right">
              <button class="btn-ghost mr-1" @click="openDetail(j)">详情</button>
              <button class="btn-danger" @click="remove(j)">删除</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="7" class="py-6 text-center text-slate-400">暂无 JD</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 详情弹窗 -->
    <Modal v-model="showDetail" title="JD 详情" width="52rem">
      <div v-if="detailLoading" class="py-8 text-center text-slate-400">分析中...</div>
      <div v-else-if="detail" class="space-y-4 max-h-[70vh] overflow-y-auto">
        <!-- 顶部信息 -->
        <div>
          <div class="text-lg font-semibold text-slate-800">{{ detail.jd.company }} · {{ detail.jd.title }}</div>
          <div class="mt-1 flex flex-wrap gap-2 text-xs">
            <span class="badge bg-indigo-100 text-indigo-700">{{ detail.jd.direction_tag }}</span>
            <span v-if="detail.jd.salary_range" class="badge bg-slate-100 text-slate-600">💰 {{ detail.jd.salary_range }}</span>
            <span v-if="detail.jd.location" class="badge bg-slate-100 text-slate-600">📍 {{ detail.jd.location }}</span>
            <span v-if="detail.jd.source" class="badge bg-slate-100 text-slate-600">{{ detail.jd.source }}</span>
          </div>
        </div>

        <!-- 方向预警 -->
        <div v-if="detail.jd.direction_alert" class="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-700">
          ⚠️ {{ detail.jd.direction_alert }}
        </div>

        <!-- 原文 -->
        <div v-if="detail.jd.raw_text">
          <h4 class="mb-1 font-semibold text-slate-700">📄 原文</h4>
          <div class="max-h-48 overflow-y-auto rounded bg-slate-50 p-3 text-sm text-slate-600 whitespace-pre-wrap">{{ detail.jd.raw_text }}</div>
        </div>

        <!-- 结构化解析 -->
        <div v-if="detail.jd.parsed_json" class="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div v-if="detail.jd.parsed_json.responsibilities?.length">
            <h4 class="mb-1 font-semibold text-slate-700">📋 岗位职责</h4>
            <ul class="list-disc pl-4 text-sm text-slate-600 space-y-0.5">
              <li v-for="(r, i) in detail.jd.parsed_json.responsibilities" :key="i">{{ r }}</li>
            </ul>
          </div>
          <div v-if="detail.jd.parsed_json.requirements?.length">
            <h4 class="mb-1 font-semibold text-slate-700">✅ 任职要求</h4>
            <ul class="list-disc pl-4 text-sm text-slate-600 space-y-0.5">
              <li v-for="(r, i) in detail.jd.parsed_json.requirements" :key="i">{{ r }}</li>
            </ul>
          </div>
        </div>

        <!-- 关键词 -->
        <div v-if="detail.jd.parsed_json?.keywords?.length">
          <h4 class="mb-1 font-semibold text-slate-700">🔑 核心关键词</h4>
          <div class="flex flex-wrap gap-2">
            <span v-for="k in detail.jd.parsed_json.keywords" :key="k" class="badge bg-indigo-100 text-indigo-700">{{ k }}</span>
          </div>
        </div>

        <!-- 基于你的情况分析 -->
        <div class="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3">
          <h4 class="mb-2 font-semibold text-indigo-800">🎯 基于你的情况分析</h4>
          <div class="mb-2 flex flex-wrap gap-2 text-xs text-indigo-600">
            <span>主方向：{{ detail.user?.primary_direction || '未设置' }}</span>
            <span v-if="detail.user?.years_experience">工作年限：{{ detail.user.years_experience }}年</span>
            <span v-if="detail.user?.education">学历：{{ detail.user.education }}</span>
            <span v-if="detail.user?.current_city">城市：{{ detail.user.current_city }}</span>
            <span v-if="detail.resume_version">对比简历：{{ detail.resume_version }}</span>
          </div>

          <template v-if="detail.match">
            <div class="flex items-center gap-3">
              <span class="text-3xl font-bold" :class="detail.match.score >= 75 ? 'text-emerald-600' : detail.match.score >= 55 ? 'text-amber-600' : 'text-rose-600'">
                {{ detail.match.score }}
              </span>
              <span class="text-sm text-slate-500">/ 100 匹配分</span>
            </div>
            <div v-if="detail.match.matched_points?.length" class="mt-2 text-sm">
              <div class="font-medium text-emerald-700">✅ 已命中</div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="k in detail.match.matched_points" :key="k" class="badge bg-emerald-100 text-emerald-700">{{ k }}</span>
              </div>
            </div>
            <div v-if="detail.match.missing_points?.length" class="mt-2 text-sm">
              <div class="font-medium text-rose-700">❌ 缺失（简历里没体现）</div>
              <div class="flex flex-wrap gap-1 mt-1">
                <span v-for="k in detail.match.missing_points" :key="k" class="badge bg-rose-100 text-rose-700">{{ k }}</span>
              </div>
            </div>
            <div v-if="detail.match.suggestion" class="mt-2 rounded bg-white p-2 text-sm text-slate-600">{{ detail.match.suggestion }}</div>
          </template>
          <div v-else class="text-sm text-slate-400">暂无简历可对比，上传简历后可出匹配分析。</div>
        </div>
      </div>
    </Modal>

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
