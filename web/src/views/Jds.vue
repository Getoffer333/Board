<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { DIRECTIONS, CHANNELS, STATUS_LABELS } from '../constants'
import type { JD } from '../types'

const items = ref<JD[]>([])
const showModal = ref(false)
const form = ref({
  raw_text: '',
  company: '',
  title: '',
  direction_tag: '',
  salary_range: '',
  location: '',
  source: '',
  status: 'active',
  note: ''
})
const parsed = ref<JD | null>(null)

async function load() {
  try {
    items.value = await api.get<JD[]>('/api/jds?status=&direction=')
  } catch (e: any) {
    toast('error', e.message)
  }
}

function openModal() {
  form.value = { raw_text: '', company: '', title: '', direction_tag: '', salary_range: '', location: '', source: '', status: 'active', note: '' }
  parsed.value = null
  showModal.value = true
}

async function submit() {
  if (!form.value.raw_text.trim()) {
    toast('error', '请粘贴 JD 原文')
    return
  }
  try {
    const created = await api.post<JD>('/api/jds', { ...form.value })
    toast('success', 'JD 已创建并解析')
    showModal.value = false
    await load()
    parsed.value = created
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function remove(j: JD) {
  if (!confirm(`确认删除 JD「${j.company} · ${j.title}」？`)) return
  try {
    await api.del(`/api/jds/${j.id}`)
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
      <p class="text-sm text-slate-500">粘贴 JD 原文，服务端自动解析关键信息与关键词。</p>
      <button class="btn-primary" @click="openModal">+ 新建 JD</button>
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">公司</th>
            <th>岗位</th>
            <th>方向</th>
            <th>薪资</th>
            <th>状态</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in items" :key="j.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="py-2 font-medium">{{ j.company }}</td>
            <td>{{ j.title }}</td>
            <td>{{ j.direction_tag || '—' }}</td>
            <td class="text-slate-500">{{ j.salary_range || '—' }}</td>
            <td>{{ STATUS_LABELS[j.status] || j.status }}</td>
            <td class="text-right">
              <button class="btn-ghost mr-1" @click="parsed = j">关键词</button>
              <button class="btn-danger" @click="remove(j)">删除</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="6" class="py-6 text-center text-slate-400">暂无 JD</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="parsed" class="card">
      <div class="mb-2 flex items-center justify-between">
        <h3 class="font-semibold text-slate-700">解析关键词 · {{ parsed.company }} {{ parsed.title }}</h3>
        <button class="text-xs text-indigo-600" @click="parsed = null">收起</button>
      </div>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="k in parsed.parsed_json?.keywords || []"
          :key="k"
          class="badge bg-indigo-100 text-indigo-700"
        >{{ k }}</span>
        <span v-if="!parsed.parsed_json?.keywords?.length" class="text-slate-400">无关键词</span>
      </div>
      <div v-if="parsed.parsed_json?.years_required" class="mt-2 text-xs text-slate-500">
        经验要求：{{ parsed.parsed_json.years_required }} 年 · 学历：{{ parsed.parsed_json.education_required || '不限' }}
      </div>
    </div>

    <Modal v-model="showModal" title="新建 JD">
      <div class="space-y-4">
        <div>
          <label class="label">JD 原文 *（必填，其余可空，服务端自动猜）</label>
          <textarea v-model="form.raw_text" rows="6" class="input" placeholder="粘贴职位描述全文…"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">公司</label>
            <input v-model="form.company" class="input" />
          </div>
          <div>
            <label class="label">岗位</label>
            <input v-model="form.title" class="input" />
          </div>
          <div>
            <label class="label">方向</label>
            <select v-model="form.direction_tag" class="input">
              <option value="">（自动猜）</option>
              <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div>
            <label class="label">薪资</label>
            <input v-model="form.salary_range" class="input" />
          </div>
          <div>
            <label class="label">城市</label>
            <input v-model="form.location" class="input" />
          </div>
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
        <button class="btn-primary" @click="submit">保存并解析</button>
      </template>
    </Modal>
  </div>
</template>
