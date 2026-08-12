<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { DIRECTIONS, SOURCES, SKILL_STATUSES, SKILL_STATUS_COLORS } from '../constants'
import type { Skill, SkillLog } from '../types'

const items = ref<Skill[]>([])
const showModal = ref(false)
const form = ref({
  name: '',
  direction_tag: DIRECTIONS[1],
  category: '',
  current_level: '',
  target_level: '',
  source: SOURCES[0],
  source_ref: '',
  plan: '',
  status: SKILL_STATUSES[0]
})

async function load() {
  try {
    items.value = await api.get<Skill[]>('/api/skills?status=&direction=')
  } catch (e: any) {
    toast('error', e.message)
  }
}

function openModal() {
  form.value = {
    name: '',
    direction_tag: DIRECTIONS[1],
    category: '',
    current_level: '',
    target_level: '',
    source: SOURCES[0],
    source_ref: '',
    plan: '',
    status: SKILL_STATUSES[0]
  }
  showModal.value = true
}

async function submit() {
  if (!form.value.name.trim()) {
    toast('error', '请填写技能名称')
    return
  }
  try {
    await api.post('/api/skills', { ...form.value })
    toast('success', '技能已加入计划')
    showModal.value = false
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function checkin(s: Skill) {
  const content = prompt('打卡内容（可选）：') || ''
  const duration = Number(prompt('本次投入时长(分钟)：', '30') || '30')
  try {
    await api.post(`/api/skills/${s.id}/log`, {
      log_date: new Date().toISOString().slice(0, 10),
      duration_min: duration,
      content
    })
    toast('success', '打卡成功')
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function remove(s: Skill) {
  if (!confirm(`确认删除技能「${s.name}」？`)) return
  try {
    await api.del(`/api/skills/${s.id}`)
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
      <p class="text-sm text-slate-500">维护技能提升计划，每日打卡记录进展。</p>
      <button class="btn-primary" @click="openModal">+ 新建技能</button>
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">名称</th>
            <th>方向</th>
            <th>分类</th>
            <th>当前→目标</th>
            <th>来源</th>
            <th>状态</th>
            <th>打卡</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in items" :key="s.id" class="border-b border-slate-50 align-top">
            <td class="py-2 font-medium">{{ s.name }}</td>
            <td>{{ s.direction_tag }}</td>
            <td>{{ s.category || '—' }}</td>
            <td class="text-slate-500">{{ s.current_level || '—' }} → {{ s.target_level || '—' }}</td>
            <td>{{ s.source }}</td>
            <td><span class="badge" :class="SKILL_STATUS_COLORS[s.status]">{{ s.status }}</span></td>
            <td>
              <span class="badge bg-slate-100 text-slate-500">{{ s.log_count }} 次</span>
              <div v-if="s.logs?.length" class="mt-1 max-w-[12rem] text-xs text-slate-400">
                最近：{{ s.logs[0].log_date }} · {{ s.logs[0].duration_min }}min
              </div>
            </td>
            <td class="text-right whitespace-nowrap">
              <button class="btn-ghost mr-1" @click="checkin(s)">打卡</button>
              <button class="btn-danger" @click="remove(s)">删除</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="8" class="py-6 text-center text-slate-400">暂无技能计划</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" title="新建技能">
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">名称 *</label>
          <input v-model="form.name" class="input" />
        </div>
        <div>
          <label class="label">方向</label>
          <select v-model="form.direction_tag" class="input">
            <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>
        <div>
          <label class="label">分类</label>
          <input v-model="form.category" class="input" />
        </div>
        <div>
          <label class="label">来源</label>
          <select v-model="form.source" class="input">
            <option v-for="src in SOURCES" :key="src" :value="src">{{ src }}</option>
          </select>
        </div>
        <div>
          <label class="label">当前水平</label>
          <input v-model="form.current_level" class="input" />
        </div>
        <div>
          <label class="label">目标水平</label>
          <input v-model="form.target_level" class="input" />
        </div>
        <div class="col-span-2">
          <label class="label">来源引用</label>
          <input v-model="form.source_ref" class="input" placeholder="如 JD#1 / 复盘-面试#3" />
        </div>
        <div class="col-span-2">
          <label class="label">提升计划</label>
          <textarea v-model="form.plan" rows="2" class="input"></textarea>
        </div>
        <div>
          <label class="label">状态</label>
          <select v-model="form.status" class="input">
            <option v-for="st in SKILL_STATUSES" :key="st" :value="st">{{ st }}</option>
          </select>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showModal = false">取消</button>
        <button class="btn-primary" @click="submit">保存</button>
      </template>
    </Modal>
  </div>
</template>
