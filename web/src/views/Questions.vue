<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { DIRECTIONS, CATEGORIES } from '../constants'
import type { Question } from '../types'

const items = ref<Question[]>([])
const filterDir = ref('')
const filterCat = ref('')
const showModal = ref(false)
const editing = ref<Question | null>(null)
const form = ref({
  question: '',
  category: CATEGORIES[0],
  direction_tag: DIRECTIONS[1],
  company: '',
  answer_hint: '',
  mastered: 0
})

async function load() {
  try {
    const params = new URLSearchParams()
    if (filterDir.value) params.set('direction', filterDir.value)
    if (filterCat.value) params.set('category', filterCat.value)
    items.value = await api.get<Question[]>(`/api/questions?${params.toString()}`)
  } catch (e: any) {
    toast('error', e.message)
  }
}

const filtered = computed(() => items.value)

function openNew() {
  editing.value = null
  form.value = {
    question: '',
    category: CATEGORIES[0],
    direction_tag: DIRECTIONS[1],
    company: '',
    answer_hint: '',
    mastered: 0
  }
  showModal.value = true
}

function openEdit(q: Question) {
  editing.value = q
  form.value = {
    question: q.question,
    category: q.category,
    direction_tag: q.direction_tag,
    company: q.company,
    answer_hint: q.answer_hint,
    mastered: q.mastered
  }
  showModal.value = true
}

async function submit() {
  if (!form.value.question.trim()) {
    toast('error', '请填写题目')
    return
  }
  try {
    if (editing.value) {
      await api.put(`/api/questions/${editing.value.id}`, { ...form.value })
      toast('success', '已更新')
    } else {
      await api.post('/api/questions', { ...form.value })
      toast('success', '已添加')
    }
    showModal.value = false
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function toggleMastered(q: Question) {
  try {
    await api.put(`/api/questions/${q.id}`, { ...q, mastered: q.mastered ? 0 : 1 })
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function remove(q: Question) {
  if (!confirm('确认删除该题？')) return
  try {
    await api.del(`/api/questions/${q.id}`)
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
    <div class="flex flex-wrap items-center gap-3">
      <p class="text-sm text-slate-500">按方向/分类筛选，标记掌握情况。</p>
      <div class="ml-auto flex gap-2">
        <select v-model="filterDir" class="input w-auto" @change="load">
          <option value="">全部方向</option>
          <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
        </select>
        <select v-model="filterCat" class="input w-auto" @change="load">
          <option value="">全部分类</option>
          <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
        </select>
        <button class="btn-primary" @click="openNew">+ 新建</button>
      </div>
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">题目</th>
            <th>分类</th>
            <th>方向</th>
            <th>公司</th>
            <th>频次</th>
            <th>掌握</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="q in filtered" :key="q.id" class="border-b border-slate-50">
            <td class="py-2 max-w-md">{{ q.question }}</td>
            <td>{{ q.category }}</td>
            <td>{{ q.direction_tag }}</td>
            <td class="text-slate-500">{{ q.company || '—' }}</td>
            <td>{{ q.freq ?? 0 }}</td>
            <td>
              <button
                class="badge"
                :class="q.mastered ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'"
                @click="toggleMastered(q)"
              >
                {{ q.mastered ? '已掌握' : '未掌握' }}
              </button>
            </td>
            <td class="text-right whitespace-nowrap">
              <button class="btn-ghost mr-1" @click="openEdit(q)">编辑</button>
              <button class="btn-danger" @click="remove(q)">删除</button>
            </td>
          </tr>
          <tr v-if="filtered.length === 0">
            <td colspan="7" class="py-6 text-center text-slate-400">暂无题目</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? '编辑题目' : '新建题目'">
      <div class="space-y-3">
        <div>
          <label class="label">题目 *</label>
          <textarea v-model="form.question" rows="2" class="input"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">分类</label>
            <select v-model="form.category" class="input">
              <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div>
            <label class="label">方向</label>
            <select v-model="form.direction_tag" class="input">
              <option v-for="d in DIRECTIONS" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          <div>
            <label class="label">公司</label>
            <input v-model="form.company" class="input" />
          </div>
        </div>
        <div>
          <label class="label">参考答案提示</label>
          <textarea v-model="form.answer_hint" rows="2" class="input"></textarea>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showModal = false">取消</button>
        <button class="btn-primary" @click="submit">保存</button>
      </template>
    </Modal>
  </div>
</template>
