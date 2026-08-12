<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { ROUNDS, MODES, RESULTS, RESULT_LABELS, CATEGORIES } from '../constants'
import type { Application, Interview } from '../types'

interface Row {
  app: Application
  interview: Interview
}

const rows = ref<Row[]>([])

async function load() {
  try {
    const apps = await api.get<Application[]>('/api/applications')
    const out: Row[] = []
    await Promise.all(
      apps.map(async (a) => {
        try {
          const ivs = await api.get<Interview[]>(`/api/interviews/by-application/${a.id}`)
          for (const iv of ivs) out.push({ app: a, interview: iv })
        } catch {
          /* ignore */
        }
      })
    )
    out.sort((x, y) => (x.interview.scheduled_at < y.interview.scheduled_at ? 1 : -1))
    rows.value = out
  } catch (e: any) {
    toast('error', e.message)
  }
}

// 新增面试
const showNew = ref(false)
const apps = ref<Application[]>([])
const nForm = ref({
  application_id: '',
  round: ROUNDS[1],
  scheduled_at: '',
  duration_min: 60,
  mode: MODES[0],
  location: '',
  interviewers: [] as { name: string; role: string }[],
  questions: [] as { q: string; my_answer: string; score: number }[]
})

function addInterviewer() {
  nForm.value.interviewers.push({ name: '', role: '' })
}
function addQuestion() {
  nForm.value.questions.push({ q: '', my_answer: '', score: 0 })
}

async function openNew() {
  try {
    apps.value = await api.get<Application[]>('/api/applications')
    nForm.value = {
      application_id: apps.value[0]?.id ? String(apps.value[0].id) : '',
      round: ROUNDS[1],
      scheduled_at: '',
      duration_min: 60,
      mode: MODES[0],
      location: '',
      interviewers: [],
      questions: []
    }
    showNew.value = true
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function createInterview() {
  if (!nForm.value.application_id) {
    toast('error', '请选择投递')
    return
  }
  const payload = {
    application_id: Number(nForm.value.application_id),
    round: nForm.value.round,
    scheduled_at: nForm.value.scheduled_at,
    duration_min: Number(nForm.value.duration_min),
    mode: nForm.value.mode,
    location: nForm.value.location,
    interviewers: nForm.value.interviewers.filter((i) => i.name),
    questions: nForm.value.questions.filter((q) => q.q)
  }
  try {
    await api.post('/api/interviews', payload)
    toast('success', '面试已添加')
    showNew.value = false
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

// 复盘
const showReview = ref(false)
const review = ref<Interview | null>(null)
const rForm = ref({
  went_well: '',
  went_bad: '',
  action_items: '',
  result: 'pending',
  self_score: 0,
  unanswered: [] as string[],
  bank: [] as { question: string; category: string }[]
})
const newUnanswered = ref('')
const newBankQ = ref('')
const newBankC = ref(CATEGORIES[0])

function openReview(iv: Interview) {
  review.value = iv
  rForm.value = {
    went_well: iv.went_well || '',
    went_bad: iv.went_bad || '',
    action_items: iv.action_items || '',
    result: iv.result || 'pending',
    self_score: iv.self_score || 0,
    unanswered: iv.unanswered ? [...iv.unanswered] : [],
    bank: iv.bank ? [...iv.bank] : []
  }
  showReview.value = true
}

function addUnanswered() {
  if (newUnanswered.value.trim()) {
    rForm.value.unanswered.push(newUnanswered.value.trim())
    newUnanswered.value = ''
  }
}
function addBank() {
  if (newBankQ.value.trim()) {
    rForm.value.bank.push({ question: newBankQ.value.trim(), category: newBankC.value })
    newBankQ.value = ''
  }
}

async function submitReview() {
  if (!review.value) return
  try {
    await api.post(`/api/interviews/${review.value.id}/review`, { ...rForm.value })
    toast('success', '复盘已保存')
    showReview.value = false
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function remove(iv: Interview) {
  if (!confirm('确认删除该面试记录？')) return
  try {
    await api.del(`/api/interviews/${iv.id}`)
    toast('success', '已删除')
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-slate-500">聚合所有投递下的面试，可按轮次复盘沉淀。</p>
      <button class="btn-primary" @click="openNew">+ 新增面试</button>
    </div>

    <div v-if="rows.length === 0" class="card py-10 text-center text-slate-400">暂无面试记录</div>

    <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
      <div v-for="r in rows" :key="r.interview.id" class="card">
        <div class="flex items-start justify-between">
          <div>
            <div class="font-semibold text-slate-800">
              {{ r.app.company_snapshot }} · {{ r.app.title_snapshot }}
            </div>
            <div class="mt-1 flex flex-wrap items-center gap-1 text-xs">
              <span class="badge bg-indigo-100 text-indigo-700">{{ r.interview.round }}</span>
              <span class="badge bg-slate-100 text-slate-500">{{ r.interview.mode }}</span>
              <span class="text-slate-400">{{ r.interview.scheduled_at }}</span>
              <span v-if="r.interview.result" class="badge bg-emerald-100 text-emerald-700">
                {{ RESULT_LABELS[r.interview.result] }}
              </span>
            </div>
          </div>
          <div class="flex gap-1">
            <button class="btn-ghost" @click="openReview(r.interview)">复盘</button>
            <button class="btn-danger" @click="remove(r.interview)">删除</button>
          </div>
        </div>
        <div v-if="r.interview.interviewers?.length" class="mt-2 text-xs text-slate-500">
          面试官：{{ r.interview.interviewers.map((i) => i.name + (i.role ? `(${i.role})` : '')).join('、') }}
        </div>
        <div v-if="r.interview.location" class="text-xs text-slate-400">地点：{{ r.interview.location }}</div>
      </div>
    </div>

    <!-- 新增 -->
    <Modal v-model="showNew" title="新增面试">
      <div class="space-y-4">
        <div>
          <label class="label">关联投递 *</label>
          <select v-model="nForm.application_id" class="input">
            <option v-for="a in apps" :key="a.id" :value="a.id">{{ a.company_snapshot }} · {{ a.title_snapshot }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">轮次</label>
            <select v-model="nForm.round" class="input">
              <option v-for="r in ROUNDS" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
          <div>
            <label class="label">方式</label>
            <select v-model="nForm.mode" class="input">
              <option v-for="m in MODES" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div>
            <label class="label">时间</label>
            <input v-model="nForm.scheduled_at" type="datetime-local" class="input" />
          </div>
          <div>
            <label class="label">时长(分钟)</label>
            <input v-model="nForm.duration_min" type="number" class="input" />
          </div>
        </div>
        <div>
          <label class="label">地点</label>
          <input v-model="nForm.location" class="input" />
        </div>
        <div>
          <label class="label">面试官</label>
          <div v-for="(iv, i) in nForm.interviewers" :key="i" class="mb-1 flex gap-2">
            <input v-model="iv.name" class="input" placeholder="姓名" />
            <input v-model="iv.role" class="input" placeholder="角色" />
          </div>
          <button class="btn-ghost" @click="addInterviewer">+ 添加面试官</button>
        </div>
        <div>
          <label class="label">题目</label>
          <div v-for="(q, i) in nForm.questions" :key="i" class="mb-1 flex gap-2">
            <input v-model="q.q" class="input" placeholder="题目" />
            <input v-model="q.my_answer" class="input" placeholder="我的回答" />
          </div>
          <button class="btn-ghost" @click="addQuestion">+ 添加题目</button>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showNew = false">取消</button>
        <button class="btn-primary" @click="createInterview">保存</button>
      </template>
    </Modal>

    <!-- 复盘 -->
    <Modal v-model="showReview" title="面试复盘" width="44rem">
      <div v-if="review" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">结果</label>
            <select v-model="rForm.result" class="input">
              <option v-for="r in RESULTS" :key="r.v" :value="r.v">{{ r.l }}</option>
            </select>
          </div>
          <div>
            <label class="label">自评分数</label>
            <input v-model="rForm.self_score" type="number" class="input" />
          </div>
        </div>
        <div>
          <label class="label">表现好</label>
          <textarea v-model="rForm.went_well" rows="2" class="input"></textarea>
        </div>
        <div>
          <label class="label">表现差</label>
          <textarea v-model="rForm.went_bad" rows="2" class="input"></textarea>
        </div>
        <div>
          <label class="label">行动项</label>
          <textarea v-model="rForm.action_items" rows="2" class="input"></textarea>
        </div>
        <div>
          <label class="label">未答出问题</label>
          <div class="flex gap-2">
            <input v-model="newUnanswered" class="input" placeholder="输入后回车添加" @keyup.enter="addUnanswered" />
            <button class="btn-ghost" @click="addUnanswered">添加</button>
          </div>
          <div class="mt-2 flex flex-wrap gap-1">
            <span v-for="(u, i) in rForm.unanswered" :key="i" class="badge bg-rose-100 text-rose-700">
              {{ u }}
              <button class="ml-1" @click="rForm.unanswered.splice(i, 1)">✕</button>
            </span>
          </div>
        </div>
        <div>
          <label class="label">沉淀题</label>
          <div class="flex gap-2">
            <input v-model="newBankQ" class="input" placeholder="题目" />
            <select v-model="newBankC" class="input w-28">
              <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
            </select>
            <button class="btn-ghost" @click="addBank">添加</button>
          </div>
          <ul class="mt-2 space-y-1 text-sm">
            <li v-for="(b, i) in rForm.bank" :key="i" class="flex items-center justify-between rounded bg-slate-50 px-2 py-1">
              <span>{{ b.question }} <span class="text-slate-400">[{{ b.category }}]</span></span>
              <button class="text-rose-500" @click="rForm.bank.splice(i, 1)">✕</button>
            </li>
          </ul>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showReview = false">取消</button>
        <button class="btn-primary" @click="submitReview">保存复盘</button>
      </template>
    </Modal>
  </div>
</template>
