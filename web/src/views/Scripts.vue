<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import api from '../api'
import { toast } from '../toast'
import { DIRECTIONS, SCRIPT_TYPES, SCRIPT_TAGS } from '../constants'

interface Script {
  id: number
  title: string
  direction_tag: string
  script_type: string
  content: string
  tags: string[]
  is_mastered: number
  practice_count: number
  last_practiced_at: string | null
  note: string
  sort_order: number
  created_at: string
  updated_at: string
}

const scripts = ref<Script[]>([])
const editId = ref<number | null>(null)
const form = ref({
  title: '', direction_tag: '通用', script_type: '自我介绍',
  content: '', tags: [] as string[], note: '', sort_order: 0
})
const filterDir = ref('')
const filterType = ref('')

const filteredScripts = computed(() => {
  let list = scripts.value
  if (filterDir.value) list = list.filter(s => s.direction_tag === filterDir.value)
  if (filterType.value) list = list.filter(s => s.script_type === filterType.value)
  return list.sort((a, b) => a.sort_order - b.sort_order || b.id - a.id)
})

const masteredCount = computed(() => scripts.value.filter(s => s.is_mastered).length)

async function load() {
  try {
    scripts.value = await api.get<Script[]>('/api/scripts')
  } catch (e: any) { toast('error', e.message) }
}

function resetForm() {
  editId.value = null
  form.value = { title: '', direction_tag: '通用', script_type: '自我介绍', content: '', tags: [], note: '', sort_order: 0 }
}

function edit(s: Script) {
  editId.value = s.id
  form.value = { title: s.title, direction_tag: s.direction_tag, script_type: s.script_type, content: s.content, tags: [...(s.tags || [])], note: s.note || '', sort_order: s.sort_order }
}

async function save() {
  if (!form.value.title.trim()) return toast('error', '标题不能为空')
  try {
    if (editId.value) {
      await api.put(`/api/scripts/${editId.value}`, form.value)
      toast('success', '已更新')
    } else {
      await api.post('/api/scripts', form.value)
      toast('success', '已创建')
    }
    resetForm()
    await load()
  } catch (e: any) { toast('error', e.message) }
}

async function remove(id: number) {
  if (!confirm('确定删除？')) return
  try {
    await api.del(`/api/scripts/${id}`)
    toast('success', '已删除')
    await load()
  } catch (e: any) { toast('error', e.message) }
}

async function toggleMaster(s: Script) {
  try {
    await api.post(`/api/scripts/${s.id}/master`)
    await load()
  } catch (e: any) { toast('error', e.message) }
}

async function practice(s: Script) {
  try {
    await api.post(`/api/scripts/${s.id}/practice`)
    await load()
    toast('info', `已打卡「${s.title}」`)
  } catch (e: any) { toast('error', e.message) }
}

function toggleTag(tag: string) {
  const idx = form.value.tags.indexOf(tag)
  if (idx >= 0) form.value.tags.splice(idx, 1)
  else form.value.tags.push(tag)
}

onMounted(load)
</script>

<template>
  <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
    <!-- 列表 -->
    <div class="lg:col-span-2 space-y-4">
      <!-- 统计条 -->
      <div class="flex items-center gap-3 text-sm text-slate-500">
        <span>共 {{ scripts.length }} 篇</span>
        <span class="text-emerald-600">已掌握 {{ masteredCount }}</span>
        <span class="text-slate-300">|</span>
        <select v-model="filterDir" class="input !w-auto !py-1 text-xs">
          <option value="">全部方向</option>
          <option value="通用">通用</option>
          <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
        </select>
        <select v-model="filterType" class="input !w-auto !py-1 text-xs">
          <option value="">全部类型</option>
          <option v-for="t in SCRIPT_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <div v-if="filteredScripts.length === 0" class="py-8 text-center text-slate-400 text-sm">暂无逐字稿，点击右侧新建</div>

      <div v-for="s in filteredScripts" :key="s.id" class="card flex items-start gap-3" :class="{ 'border-emerald-300 bg-emerald-50/30': s.is_mastered }">
        <button class="mt-1 shrink-0" @click="toggleMaster(s)">
          <span v-if="s.is_mastered" class="text-emerald-500 text-lg">✅</span>
          <span v-else class="text-slate-300 text-lg">⬜</span>
        </button>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="font-medium text-slate-800 truncate">{{ s.title }}</span>
            <span class="badge bg-slate-100 text-slate-500 text-xs">{{ s.script_type }}</span>
            <span class="badge bg-indigo-50 text-indigo-600 text-xs">{{ s.direction_tag }}</span>
          </div>
          <div class="mt-1 text-xs text-slate-400 line-clamp-2">{{ s.content.slice(0, 150) }}</div>
          <div class="mt-2 flex items-center gap-2 flex-wrap">
            <span v-for="t in (s.tags || [])" :key="t" class="badge bg-amber-50 text-amber-600 text-[10px]">{{ t }}</span>
            <span class="text-[10px] text-slate-400 ml-auto">练习 {{ s.practice_count }} 次</span>
          </div>
        </div>
        <div class="flex gap-1 shrink-0">
          <button class="btn-ghost !px-2 !py-1 text-xs" @click="practice(s)">🔄练</button>
          <button class="btn-ghost !px-2 !py-1 text-xs" @click="edit(s)">✏️</button>
          <button class="btn-ghost !px-2 !py-1 text-xs text-rose-500" @click="remove(s.id)">🗑</button>
        </div>
      </div>
    </div>

    <!-- 编辑表单 -->
    <div class="card space-y-3 sticky top-4 self-start">
      <h3 class="font-semibold text-slate-700">{{ editId ? '编辑逐字稿' : '新建逐字稿' }}</h3>

      <input v-model="form.title" class="input" placeholder="标题，如：自我介绍 40s 版" />

      <div class="grid grid-cols-2 gap-2">
        <select v-model="form.direction_tag" class="input text-sm">
          <option value="通用">通用</option>
          <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
        </select>
        <select v-model="form.script_type" class="input text-sm">
          <option v-for="t in SCRIPT_TYPES" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>

      <textarea v-model="form.content" rows="12" class="input font-mono text-sm" placeholder="粘贴逐字稿内容…"></textarea>

      <div>
        <label class="label">标签</label>
        <div class="flex flex-wrap gap-1 mt-1">
          <button v-for="t in SCRIPT_TAGS" :key="t" class="badge cursor-pointer text-xs"
            :class="form.tags.includes(t) ? 'bg-indigo-100 text-indigo-700 ring-1 ring-indigo-300' : 'bg-slate-100 text-slate-500'"
            @click="toggleTag(t)">{{ t }}</button>
        </div>
      </div>

      <input v-model="form.note" class="input text-sm" placeholder="备注（可选）" />

      <div class="flex gap-2">
        <button class="btn-primary flex-1" @click="save">{{ editId ? '更新' : '创建' }}</button>
        <button v-if="editId" class="btn-ghost flex-1" @click="resetForm">取消</button>
      </div>
    </div>
  </div>
</template>
