<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import { DIRECTIONS } from '../constants'
import type { JD, Resume, SuggestedSkill } from '../types'

const jds = ref<JD[]>([])
const resumes = ref<Resume[]>([])
const settings = ref<any>(null)

async function load() {
  try {
    ;[jds.value, resumes.value, settings.value] = await Promise.all([
      api.get<JD[]>('/api/jds?status=&direction='),
      api.get<Resume[]>('/api/resumes?direction='),
      api.get<any>('/api/settings')
    ])
  } catch (e: any) {
    toast('error', e.message)
  }
}

function copy(text: string) {
  navigator.clipboard?.writeText(text)
  toast('info', '已复制到剪贴板')
}

const online = ref(settings.value?.llm_enabled === '1')

// 1) JD 解析
const jdSel = ref('')
const jdPrompt = ref('')
const jdImportJson = ref('')
async function exportJd() {
  if (!jdSel.value) return toast('error', '请选择 JD')
  try {
    const r = await api.post<{ prompt: string }>('/api/ai/export-jd-parse', { jd_id: Number(jdSel.value) })
    jdPrompt.value = r.prompt
  } catch (e: any) { toast('error', e.message) }
}
async function importJd() {
  try {
    const result = JSON.parse(jdImportJson.value)
    await api.post('/api/ai/import-result', { type: 'jd_parse', jd_id: Number(jdSel.value), result })
    toast('success', 'JD 解析结果已导入')
  } catch (e: any) { toast('error', e.message || 'JSON 解析失败') }
}
async function onlineJd() {
  if (!jdSel.value) return toast('error', '请选择 JD')
  try {
    const r = await api.post<any>('/api/ai/online-jd-parse', { jd_id: Number(jdSel.value) })
    toast('success', '在线解析完成')
  } catch (e: any) { toast('error', e.message) }
}

// 2) 简历匹配
const mJd = ref('')
const mResume = ref('')
const mPrompt = ref('')
const matchRes = ref<any>(null)
const suggested = ref<SuggestedSkill[]>([])
async function exportMatch() {
  if (!mJd.value || !mResume.value) return toast('error', '请选择 JD 与简历')
  try {
    const r = await api.post<{ prompt: string }>('/api/ai/export-match', { jd_id: Number(mJd.value), resume_id: Number(mResume.value) })
    mPrompt.value = r.prompt
  } catch (e: any) { toast('error', e.message) }
}
async function matchLocal() {
  if (!mJd.value || !mResume.value) return toast('error', '请选择 JD 与简历')
  try {
    const r = await api.post<any>('/api/ai/match-local', { jd_id: Number(mJd.value), resume_id: Number(mResume.value) })
    matchRes.value = r
    toast('success', `本地匹配得分 ${r.score}`)
  } catch (e: any) { toast('error', e.message) }
}
async function matchOnline() {
  if (!mJd.value || !mResume.value) return toast('error', '请选择 JD 与简历')
  try {
    const r = await api.post<any>('/api/ai/online-match', { jd_id: Number(mJd.value), resume_id: Number(mResume.value) })
    matchRes.value = r
    suggested.value = r.suggested_skills || []
    toast('success', `在线匹配得分 ${r.score}`)
  } catch (e: any) { toast('error', e.message) }
}
async function importMatch() {
  try {
    const result = {
      jd_id: Number(mJd.value), resume_id: Number(mResume.value),
      score: matchRes.value?.score ?? 0,
      dimension_scores: matchRes.value?.dimension_scores ?? {},
      matched_points: matchRes.value?.matched_points ?? [],
      missing_points: matchRes.value?.missing_points ?? [],
      suggestion: matchRes.value?.suggestion ?? ''
    }
    const r = await api.post<any>('/api/ai/import-result', { type: 'match', result })
    suggested.value = (r as any).suggested_skills || []
    toast('success', '匹配结果已导入')
  } catch (e: any) { toast('error', e.message) }
}
async function addSkill(s: SuggestedSkill) {
  try {
    await api.post('/api/skills', {
      name: s.name, direction_tag: s.direction_tag, category: s.category,
      current_level: '', target_level: '', source: s.source, source_ref: '', plan: '', status: '待开始'
    })
    toast('success', `已加入技能计划：${s.name}`)
    suggested.value = suggested.value.filter((x) => x.name !== s.name)
  } catch (e: any) { toast('error', e.message) }
}

// 3) 面试题生成
const qDir = ref(DIRECTIONS[1])
const qPrompt = ref('')
const qImportJson = ref('')
async function exportQ() {
  try {
    const r = await api.post<{ prompt: string }>('/api/ai/export-interview-q', { direction_tag: qDir.value })
    qPrompt.value = r.prompt
  } catch (e: any) { toast('error', e.message) }
}
async function importQ() {
  try {
    const result = JSON.parse(qImportJson.value)
    await api.post('/api/ai/import-result', { type: 'interview_q', result })
    toast('success', '面试题已导入题库')
  } catch (e: any) { toast('error', e.message || 'JSON 解析失败') }
}
async function onlineQ() {
  try {
    const r = await api.post<any>('/api/ai/online-interview-q', { direction_tag: qDir.value })
    toast('success', `在线生成了 ${r.created} 道题`)
  } catch (e: any) { toast('error', e.message) }
}

onMounted(load)
</script>

<template>
  <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
    <!-- JD 解析 -->
    <section class="card space-y-3">
      <h3 class="font-semibold text-slate-700">JD 解析</h3>
      <select v-model="jdSel" class="input">
        <option value="">选择 JD</option>
        <option v-for="j in jds" :key="j.id" :value="j.id">{{ j.company }} · {{ j.title }}</option>
      </select>
      <div class="flex gap-2">
        <button class="btn-primary flex-1" @click="onlineJd" :disabled="settings?.llm_enabled !== '1'">🤖 一键解析</button>
        <button class="btn-ghost flex-1" @click="exportJd">📋 导出</button>
      </div>
      <div v-if="settings?.llm_enabled !== '1'" class="text-xs text-amber-600">在线模式未开启（设置页配置 Key）</div>
      <textarea v-model="jdPrompt" rows="4" readonly class="input bg-slate-50" placeholder="导出的 prompt 将显示在此"></textarea>
      <button v-if="jdPrompt" class="btn-ghost w-full" @click="copy(jdPrompt)">复制 prompt</button>
      <div class="border-t border-slate-100 pt-3">
        <label class="label">粘贴 AI 返回 JSON 导入</label>
        <textarea v-model="jdImportJson" rows="3" class="input" placeholder='{"company":"...","title":"..."...}'></textarea>
        <button class="btn-primary mt-2 w-full" @click="importJd">导入结果</button>
      </div>
    </section>

    <!-- 简历匹配 -->
    <section class="card space-y-3">
      <h3 class="font-semibold text-slate-700">简历匹配</h3>
      <select v-model="mJd" class="input">
        <option value="">选择 JD</option>
        <option v-for="j in jds" :key="j.id" :value="j.id">{{ j.company }} · {{ j.title }}</option>
      </select>
      <select v-model="mResume" class="input">
        <option value="">选择简历版本</option>
        <option v-for="r in resumes" :key="r.id" :value="r.id">{{ r.version_name }}</option>
      </select>
      <div class="flex gap-2">
        <button class="btn-primary flex-1" @click="matchOnline" :disabled="settings?.llm_enabled !== '1'">🤖 在线匹配</button>
        <button class="btn-ghost flex-1" @click="matchLocal">⚡ 本地匹配</button>
      </div>
      <button class="btn-ghost w-full text-xs" @click="exportMatch">📋 导出 prompt</button>
      <textarea v-model="mPrompt" rows="3" readonly class="input bg-slate-50" placeholder="导出的 prompt 显示在此"></textarea>
      <button v-if="mPrompt" class="btn-ghost w-full" @click="copy(mPrompt)">复制 prompt</button>

      <div v-if="matchRes" class="rounded-lg bg-slate-50 p-3 text-sm">
        <div class="font-semibold">匹配得分：{{ matchRes.score }}</div>
        <div v-for="(v, k) in matchRes.dimension_scores" :key="k" class="mt-1 flex items-center gap-2">
          <span class="w-20 text-slate-500">{{ k }}</span>
          <span class="badge bg-indigo-100 text-indigo-700">{{ v }}</span>
        </div>
        <div class="mt-2 text-slate-600">缺失项：{{ (matchRes.missing_points || []).join('、') || '无' }}</div>
        <div class="mt-1 text-slate-600">建议：{{ matchRes.suggestion }}</div>
      </div>
      <button v-if="matchRes" class="btn-primary w-full" @click="importMatch">导入匹配结果</button>

      <div v-if="suggested.length" class="space-y-2">
        <div class="text-xs font-medium text-slate-500">建议加入技能计划：</div>
        <div v-for="s in suggested" :key="s.name" class="flex items-center justify-between rounded bg-indigo-50 px-2 py-1 text-sm">
          <span>{{ s.name }} <span class="text-slate-400">[{{ s.direction_tag }}]</span></span>
          <button class="btn-primary !px-2 !py-1 text-xs" @click="addSkill(s)">加入</button>
        </div>
      </div>
    </section>

    <!-- 面试题生成 -->
    <section class="card space-y-3">
      <h3 class="font-semibold text-slate-700">面试题生成</h3>
      <select v-model="qDir" class="input">
        <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
      </select>
      <div class="flex gap-2">
        <button class="btn-primary flex-1" @click="onlineQ" :disabled="settings?.llm_enabled !== '1'">🤖 一键生成</button>
        <button class="btn-ghost flex-1" @click="exportQ">📋 导出</button>
      </div>
      <textarea v-model="qPrompt" rows="4" readonly class="input bg-slate-50" placeholder="导出的 prompt 将显示在此"></textarea>
      <button v-if="qPrompt" class="btn-ghost w-full" @click="copy(qPrompt)">复制 prompt</button>
      <div class="border-t border-slate-100 pt-3">
        <label class="label">粘贴 AI 返回 JSON 导入</label>
        <textarea v-model="qImportJson" rows="3" class="input" placeholder='{"questions":[{"question":"...",...}]}'></textarea>
        <button class="btn-primary mt-2 w-full" @click="importQ">导入结果</button>
      </div>
    </section>
  </div>
</template>
