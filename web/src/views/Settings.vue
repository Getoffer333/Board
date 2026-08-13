<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import { DIRECTIONS } from '../constants'
import type { Settings } from '../types'

const form = ref<Settings>({
  primary_direction: '运营',
  backup_directions: '[]',
  owner_name: '',
  years_experience: '',
  education: '',
  current_city: '',
  llm_enabled: '0',
  llm_base_url: '',
  llm_api_key: '',
  llm_model: ''
})
const backups = ref<{ name: string; size: number; time: string }[]>([])
const backupExport = ref<any>(null)

const backupArr = ref<string[]>([])

async function load() {
  try {
    const s = await api.get<Settings>('/api/settings')
    form.value = s
    try {
      backupArr.value = JSON.parse(s.backup_directions || '[]')
    } catch {
      backupArr.value = []
    }
    backups.value = await api.get('/api/backup/files')
  } catch (e: any) {
    toast('error', e.message)
  }
}

function toggleBackup(d: string) {
  const i = backupArr.value.indexOf(d)
  if (i >= 0) backupArr.value.splice(i, 1)
  else backupArr.value.push(d)
}

async function save() {
  const payload = {
    ...form.value,
    backup_directions: JSON.stringify(backupArr.value)
  }
  try {
    await api.put('/api/settings', payload)
    toast('success', '设置已保存')
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function doExport() {
  try {
    backupExport.value = await api.post('/api/backup/export')
    toast('success', '备份已生成')
    backups.value = await api.get('/api/backup/files')
  } catch (e: any) {
    toast('error', e.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="max-w-3xl space-y-5">
    <div class="card space-y-4">
      <h3 class="font-semibold text-slate-700">基本资料</h3>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">主方向</label>
          <select v-model="form.primary_direction" class="input">
            <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>
        <div>
          <label class="label">工作年限</label>
          <input v-model="form.years_experience" class="input" />
        </div>
        <div>
          <label class="label">姓名</label>
          <input v-model="form.owner_name" class="input" />
        </div>
        <div>
          <label class="label">学历</label>
          <input v-model="form.education" class="input" />
        </div>
        <div>
          <label class="label">当前城市</label>
          <input v-model="form.current_city" class="input" />
        </div>
      </div>
      <div>
        <label class="label">备份方向（可多选）</label>
        <div class="flex flex-wrap gap-2">
          <button
            v-for="d in DIRECTIONS"
            :key="d"
            class="btn"
            :class="backupArr.includes(d) ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'"
            @click="toggleBackup(d)"
          >
            {{ d }}
          </button>
        </div>
      </div>
    </div>

    <div class="card space-y-4">
      <h3 class="font-semibold text-slate-700">大模型 (LLM) 配置</h3>
      <div class="flex items-center gap-3">
        <label class="label mb-0">启用 LLM</label>
        <button
          class="btn"
          :class="form.llm_enabled === '1' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'"
          @click="form.llm_enabled = form.llm_enabled === '1' ? '0' : '1'"
        >
          {{ form.llm_enabled === '1' ? '已开启' : '已关闭' }}
        </button>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">Base URL</label>
          <input v-model="form.llm_base_url" class="input" placeholder="https://..." />
        </div>
        <div>
          <label class="label">模型</label>
          <input v-model="form.llm_model" class="input" placeholder="gpt-4o" />
        </div>
        <div class="col-span-2">
          <label class="label">API Key</label>
          <input v-model="form.llm_api_key" type="password" class="input" />
        </div>
      </div>
    </div>

    <div class="card space-y-3">
      <h3 class="font-semibold text-slate-700">数据备份</h3>
      <button class="btn-primary" @click="doExport">生成备份</button>
      <div v-if="backupExport" class="space-y-2 rounded bg-slate-50 p-3 text-sm">
        <div class="text-slate-600">已生成备份（{{ (backupExport.size / 1024).toFixed(1) }} KB）</div>
        <div class="flex flex-wrap gap-2">
          <a class="btn-ghost" :href="`/api/backup/download/${backupExport.json}`" download>⬇️ 下载 JSON</a>
          <a class="btn-ghost" :href="`/api/backup/download/${backupExport.xlsx}`" download>⬇️ 下载 XLSX</a>
        </div>
      </div>
      <ul class="text-sm">
        <li v-for="b in backups" :key="b.name" class="flex items-center justify-between border-b border-slate-50 py-1">
          <span class="truncate">{{ b.name }}</span>
          <span class="flex shrink-0 items-center gap-2">
            <span class="text-slate-400">{{ (b.size / 1024).toFixed(1) }} KB</span>
            <a class="btn-ghost text-xs" :href="`/api/backup/download/${b.name}`" download>⬇️ 下载</a>
          </span>
        </li>
        <li v-if="!backups.length" class="text-slate-400">暂无备份文件</li>
      </ul>
    </div>

    <div class="flex justify-end">
      <button class="btn-primary" @click="save">保存设置</button>
    </div>
  </div>
</template>
