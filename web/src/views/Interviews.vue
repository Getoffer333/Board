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
        } catch { /* ignore */ }
      })
    )
    out.sort((x, y) => (x.interview.scheduled_at < y.interview.scheduled_at ? 1 : -1))
    rows.value = out
  } catch (e: any) { toast('error', e.message) }
}

// 新增面试
const showNew = ref(false)
const apps = ref<Application[]>([])
const nForm = ref({
  application_id: '', round: ROUNDS[1], scheduled_at: '', duration_min: 60,
  mode: MODES[0], location: '',
  interviewers: [] as { name: string; role: string }[],
  questions: [] as { q: string; my_answer: string; score: number }[]
})
function addInterviewer() { nForm.value.interviewers.push({ name: '', role: '' }) }
function addQuestion() { nForm.value.questions.push({ q: '', my_answer: '', score: 0 }) }
async function openNew() {
  try {
    apps.value = await api.get<Application[]>('/api/applications')
    nForm.value = {
      application_id: apps.value[0]?.id ? String(apps.value[0].id) : '',
      round: ROUNDS[1], scheduled_at: '', duration_min: 60,
      mode: MODES[0], location: '', interviewers: [], questions: []
    }
    showNew.value = true
  } catch (e: any) { toast('error', e.message) }
}
async function createInterview() {
  if (!nForm.value.application_id) { toast('error', '请选择投递'); return }
  try {
    await api.post('/api/interviews', {
      application_id: Number(nForm.value.application_id),
      round: nForm.value.round, scheduled_at: nForm.value.scheduled_at,
      duration_min: Number(nForm.value.duration_min), mode: nForm.value.mode,
      location: nForm.value.location,
      interviewers: nForm.value.interviewers.filter(i => i.name),
      questions: nForm.value.questions.filter(q => q.q)
    })
    toast('success', '面试已添加'); showNew.value = false; await load()
  } catch (e: any) { toast('error', e.message) }
}

// 复盘
const showReview = ref(false)
const review = ref<Interview | null>(null)
const rForm = ref({
  went_well: '', went_bad: '', action_items: '', result: 'pending', self_score: 0,
  unanswered: [] as string[], bank: [] as { question: string; category: string }[]
})
const newUnanswered = ref('')
const newBankQ = ref('')
const newBankC = ref(CATEGORIES[0])

function openReview(iv: Interview) {
  review.value = iv
  rForm.value = {
    went_well: iv.went_well || '', went_bad: iv.went_bad || '', action_items: iv.action_items || '',
    result: iv.result || 'pending', self_score: iv.self_score || 0,
    unanswered: iv.unanswered ? [...iv.unanswered] : [], bank: iv.bank ? [...iv.bank] : []
  }
  showReview.value = true
}
function addUnanswered() {
  if (newUnanswered.value.trim()) { rForm.value.unanswered.push(newUnanswered.value.trim()); newUnanswered.value = '' }
}
function addBank() {
  if (newBankQ.value.trim()) { rForm.value.bank.push({ question: newBankQ.value.trim(), category: newBankC.value }); newBankQ.value = '' }
}
async function submitReview() {
  if (!review.value) return
  try {
    await api.post(`/api/interviews/${review.value.id}/review`, { ...rForm.value })
    toast('success', '复盘已保存'); showReview.value = false; await load()
  } catch (e: any) { toast('error', e.message) }
}
async function remove(iv: Interview) {
  if (!confirm('确认删除该面试记录？')) return
  try { await api.del(`/api/interviews/${iv.id}`); toast('success', '已删除'); await load() }
  catch (e: any) { toast('error', e.message) }
}

// ─── 🎙️ 录音 & AI 复盘 ───
const audioIid = ref<number | null>(null)
const audioTranscript = ref('')
const audioReview = ref<any>(null)
const audioLoading = ref('')

async function uploadAudio(iid: number, file: File) {
  audioLoading.value = '上传中...'
  try {
    const form = new FormData(); form.append('file', file)
    await api.postForm(`/api/interviews/${iid}/upload-audio`, form)
    toast('success', '录音已上传')
    await load()
  } catch (e: any) { toast('error', e.message) }
  audioLoading.value = ''
}

async function doTranscribe(iid: number) {
  audioLoading.value = '转写中（Whisper 本地处理，约需 1-3 分钟）...'
  try {
    const r = await api.post<{ transcript: string }>(`/api/interviews/${iid}/transcribe`)
    audioTranscript.value = r.transcript
    toast('success', '转写完成')
    await load()
  } catch (e: any) { toast('error', e.message) }
  audioLoading.value = ''
}

async function doAiReview(iid: number) {
  audioLoading.value = 'AI 分析中...'
  try {
    const r = await api.post<{ review: any }>(`/api/interviews/${iid}/ai-review`)
    audioReview.value = r.review
    toast('success', 'AI 复盘完成')
    await load()
  } catch (e: any) { toast('error', e.message) }
  audioLoading.value = ''
}

function openAudioPanel(iv: Interview) {
  audioIid.value = iv.id
  audioTranscript.value = (iv as any).transcript || ''
  try { audioReview.value = (iv as any).ai_review ? JSON.parse((iv as any).ai_review) : null } catch { audioReview.value = null }
}

function triggerUpload(iid: number) {
  const input = document.createElement('input')
  input.type = 'file'; input.accept = 'audio/*'
  input.onchange = () => { if (input.files?.[0]) uploadAudio(iid, input.files[0]) }
  input.click()
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-slate-500">聚合所有投递下的面试，支持录音上传 + AI 复盘。</p>
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
            <div v-if="(r.interview as any).audio_path" class="mt-1 text-xs text-emerald-600">🎙️ 有录音</div>
            <div v-if="(r.interview as any).transcript" class="mt-1 text-xs text-blue-600">📝 已转写</div>
            <div v-if="(r.interview as any).ai_review" class="mt-1 text-xs text-purple-600">🤖 AI 已复盘</div>
          </div>
          <div class="flex gap-1">
            <button class="btn-ghost text-xs" @click="openAudioPanel(r.interview)">🎙️</button>
            <button class="btn-ghost" @click="openReview(r.interview)">复盘</button>
            <button class="btn-danger" @click="remove(r.interview)">删除</button>
          </div>
        </div>
        <div v-if="r.interview.interviewers?.length" class="mt-2 text-xs text-slate-500">
          面试官：{{ r.interview.interviewers.map(i => i.name + (i.role ? `(${i.role})` : '')).join('、') }}
        </div>
      </div>
    </div>

    <!-- 录音 & AI 面板 -->
    <Modal v-if="audioIid" v-model="audioIid" :title="'🎙️ 录音 & AI 复盘'" width="44rem">
      <div class="space-y-4">
        <div class="flex gap-2">
          <button class="btn-primary" @click="triggerUpload(audioIid!)">📤 上传录音</button>
          <button class="btn-ghost" @click="doTranscribe(audioIid!)">📝 语音转文字</button>
          <button class="btn-primary" @click="doAiReview(audioIid!)" :disabled="!audioTranscript">🤖 AI 复盘</button>
        </div>

        <div v-if="audioLoading" class="text-sm text-indigo-600 animate-pulse">{{ audioLoading }}</div>

        <!-- 转录文本 -->
        <div v-if="audioTranscript">
          <h4 class="font-semibold text-slate-700 mb-1">📝 转录文本</h4>
          <div class="max-h-40 overflow-y-auto rounded bg-slate-50 p-3 text-sm text-slate-600 whitespace-pre-wrap">{{ audioTranscript }}</div>
        </div>

        <!-- AI 复盘结果 -->
        <div v-if="audioReview" class="space-y-3">
          <h4 class="font-semibold text-slate-700">🤖 AI 复盘分析</h4>

          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-500">综合评分：</span>
            <span class="text-2xl font-bold" :class="audioReview.overall_score >= 7 ? 'text-emerald-600' : audioReview.overall_score >= 5 ? 'text-amber-600' : 'text-rose-600'">
              {{ audioReview.overall_score }}/10
            </span>
          </div>

          <div class="grid grid-cols-1 gap-2">
            <div class="rounded bg-emerald-50 p-2 text-sm">
              <div class="font-medium text-emerald-700">✅ 做得好的</div>
              <ul class="mt-1 list-disc pl-4 text-emerald-600 space-y-0.5">
                <li v-for="s in audioReview.strengths" :key="s">{{ s }}</li>
              </ul>
            </div>
            <div class="rounded bg-rose-50 p-2 text-sm">
              <div class="font-medium text-rose-700">⚠️ 需要改进</div>
              <ul class="mt-1 list-disc pl-4 text-rose-600 space-y-0.5">
                <li v-for="w in audioReview.weaknesses" :key="w">{{ w }}</li>
              </ul>
            </div>
          </div>

          <div v-if="audioReview.questions_quality?.length" class="text-sm">
            <div class="font-medium text-slate-700 mb-1">📋 逐题分析</div>
            <div v-for="(q, i) in audioReview.questions_quality" :key="i" class="rounded bg-slate-50 p-2 mb-1">
              <div class="font-medium">{{ q.question }}</div>
              <div class="text-slate-500">评价：{{ q.your_answer_quality }}</div>
              <div class="text-indigo-600">建议：{{ q.suggestion }}</div>
            </div>
          </div>

          <div v-if="audioReview.communication_issues?.length" class="text-sm">
            <div class="font-medium text-slate-700">🗣️ 沟通问题</div>
            <ul class="list-disc pl-4 text-slate-500">
              <li v-for="c in audioReview.communication_issues" :key="c">{{ c }}</li>
            </ul>
          </div>

          <div v-if="audioReview.missed_opportunities?.length" class="text-sm">
            <div class="font-medium text-slate-700">💡 遗漏的亮点</div>
            <ul class="list-disc pl-4 text-slate-500">
              <li v-for="m in audioReview.missed_opportunities" :key="m">{{ m }}</li>
            </ul>
          </div>

          <div v-if="audioReview.action_items?.length" class="text-sm">
            <div class="font-medium text-slate-700">🎯 后续行动</div>
            <ul class="list-disc pl-4 text-slate-500">
              <li v-for="a in audioReview.action_items" :key="a">{{ a }}</li>
            </ul>
          </div>

          <div class="rounded bg-indigo-50 p-2 text-sm text-indigo-700">
            <div class="font-medium">📝 总结</div>
            <div>{{ audioReview.summary }}</div>
          </div>
        </div>
      </div>
    </Modal>

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
          <div><label class="label">轮次</label><select v-model="nForm.round" class="input"><option v-for="r in ROUNDS" :key="r" :value="r">{{ r }}</option></select></div>
          <div><label class="label">方式</label><select v-model="nForm.mode" class="input"><option v-for="m in MODES" :key="m" :value="m">{{ m }}</option></select></div>
          <div><label class="label">时间</label><input v-model="nForm.scheduled_at" type="datetime-local" class="input" /></div>
          <div><label class="label">时长(分钟)</label><input v-model="nForm.duration_min" type="number" class="input" /></div>
        </div>
        <div><label class="label">地点</label><input v-model="nForm.location" class="input" /></div>
        <div>
          <label class="label">面试官</label>
          <div v-for="(iv, i) in nForm.interviewers" :key="i" class="mb-1 flex gap-2">
            <input v-model="iv.name" class="input" placeholder="姓名" /><input v-model="iv.role" class="input" placeholder="角色" />
          </div>
          <button class="btn-ghost" @click="addInterviewer">+ 添加面试官</button>
        </div>
        <div>
          <label class="label">题目</label>
          <div v-for="(q, i) in nForm.questions" :key="i" class="mb-1 flex gap-2">
            <input v-model="q.q" class="input" placeholder="题目" /><input v-model="q.my_answer" class="input" placeholder="我的回答" />
          </div>
          <button class="btn-ghost" @click="addQuestion">+ 添加题目</button>
        </div>
      </div>
      <template #footer><button class="btn-ghost" @click="showNew = false">取消</button><button class="btn-primary" @click="createInterview">保存</button></template>
    </Modal>

    <!-- 复盘 -->
    <Modal v-model="showReview" title="面试复盘" width="44rem">
      <div v-if="review" class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label">结果</label><select v-model="rForm.result" class="input"><option v-for="r in RESULTS" :key="r.v" :value="r.v">{{ r.l }}</option></select></div>
          <div><label class="label">自评分数</label><input v-model="rForm.self_score" type="number" class="input" /></div>
        </div>
        <div><label class="label">表现好</label><textarea v-model="rForm.went_well" rows="2" class="input"></textarea></div>
        <div><label class="label">表现差</label><textarea v-model="rForm.went_bad" rows="2" class="input"></textarea></div>
        <div><label class="label">行动项</label><textarea v-model="rForm.action_items" rows="2" class="input"></textarea></div>
        <div>
          <label class="label">未答出问题</label>
          <div class="flex gap-2"><input v-model="newUnanswered" class="input" placeholder="输入后回车" @keyup.enter="addUnanswered" /><button class="btn-ghost" @click="addUnanswered">添加</button></div>
          <div class="mt-2 flex flex-wrap gap-1"><span v-for="(u,i) in rForm.unanswered" :key="i" class="badge bg-rose-100 text-rose-700">{{ u }}<button class="ml-1" @click="rForm.unanswered.splice(i,1)">✕</button></span></div>
        </div>
        <div>
          <label class="label">沉淀题</label>
          <div class="flex gap-2"><input v-model="newBankQ" class="input" placeholder="题目" /><select v-model="newBankC" class="input w-28"><option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option></select><button class="btn-ghost" @click="addBank">添加</button></div>
          <ul class="mt-2 space-y-1 text-sm"><li v-for="(b,i) in rForm.bank" :key="i" class="flex items-center justify-between rounded bg-slate-50 px-2 py-1"><span>{{ b.question }} <span class="text-slate-400">[{{ b.category }}]</span></span><button class="text-rose-500" @click="rForm.bank.splice(i,1)">✕</button></li></ul>
        </div>
      </div>
      <template #footer><button class="btn-ghost" @click="showReview = false">取消</button><button class="btn-primary" @click="submitReview">保存复盘</button></template>
    </Modal>
  </div>
</template>
