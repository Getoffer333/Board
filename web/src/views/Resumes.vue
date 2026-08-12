<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { DIRECTIONS } from '../constants'
import type { Resume } from '../types'

const items = ref<Resume[]>([])
const showModal = ref(false)
const form = ref({ version_name: '', direction_tags: [] as string[], note: '', file: null as File | null })
const fileInput = ref<HTMLInputElement | null>(null)
const preview = ref<Resume | null>(null)

async function load() {
  try {
    items.value = await api.get<Resume[]>('/api/resumes?direction=')
  } catch (e: any) {
    toast('error', e.message)
  }
}

function openModal() {
  form.value = { version_name: '', direction_tags: [], note: '', file: null }
  if (fileInput.value) fileInput.value.value = ''
  showModal.value = true
}

function toggleDir(d: string) {
  const i = form.value.direction_tags.indexOf(d)
  if (i >= 0) form.value.direction_tags.splice(i, 1)
  else form.value.direction_tags.push(d)
}

async function submit() {
  if (!form.value.version_name.trim()) {
    toast('error', '请填写版本名')
    return
  }
  const fd = new FormData()
  fd.append('version_name', form.value.version_name)
  fd.append('direction_tags', JSON.stringify(form.value.direction_tags))
  fd.append('note', form.value.note)
  if (form.value.file) fd.append('file', form.value.file)
  try {
    const created = await api.postForm<Resume>('/api/resumes', fd)
    toast('success', '简历已创建')
    showModal.value = false
    await load()
    if (created.content_text) {
      preview.value = created
      toast('info', '已解析内容，可在下方查看预览')
    }
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function remove(r: Resume) {
  if (!confirm(`确认删除简历「${r.version_name}」？`)) return
  try {
    await api.del(`/api/resumes/${r.id}`)
    toast('success', '已删除')
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  form.value.file = f || null
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-slate-500">管理你的简历版本，上传后可自动解析正文。</p>
      <button class="btn-primary" @click="openModal">+ 新建简历</button>
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">版本名</th>
            <th>方向标签</th>
            <th>文件名</th>
            <th>备注</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in items" :key="r.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="py-2 font-medium">{{ r.version_name }}</td>
            <td>
              <span v-for="d in r.direction_tags" :key="d" class="badge bg-indigo-100 text-indigo-700 mr-1">{{ d }}</span>
            </td>
            <td class="text-slate-500">{{ r.file_name || '—' }}</td>
            <td class="text-slate-500">{{ r.note || '—' }}</td>
            <td class="text-right">
              <button class="btn-ghost mr-1" @click="preview = r">预览</button>
              <button class="btn-danger" @click="remove(r)">删除</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="5" class="py-6 text-center text-slate-400">暂无简历</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 预览 -->
    <div v-if="preview" class="card">
      <div class="mb-2 flex items-center justify-between">
        <h3 class="font-semibold text-slate-700">内容预览 · {{ preview.version_name }}</h3>
        <button class="text-xs text-indigo-600" @click="preview = null">收起</button>
      </div>
      <pre class="max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-600">{{ preview.content_text || '（无解析内容）' }}</pre>
    </div>

    <Modal v-model="showModal" title="新建简历">
      <div class="space-y-4">
        <div>
          <label class="label">版本名 *</label>
          <input v-model="form.version_name" class="input" placeholder="如：运营-大厂版" />
        </div>
        <div>
          <label class="label">方向标签（可多选）</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="d in DIRECTIONS"
              :key="d"
              class="btn"
              :class="form.direction_tags.includes(d) ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600'"
              @click="toggleDir(d)"
            >
              {{ d }}
            </button>
          </div>
        </div>
        <div>
          <label class="label">备注</label>
          <input v-model="form.note" class="input" />
        </div>
        <div>
          <label class="label">简历文件（可选）</label>
          <input ref="fileInput" type="file" class="input" accept=".pdf,.doc,.docx,.txt" @change="onFile" />
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showModal = false">取消</button>
        <button class="btn-primary" @click="submit">保存</button>
      </template>
    </Modal>
  </div>
</template>
