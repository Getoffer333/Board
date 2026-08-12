<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import draggable from 'vuedraggable'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { STATUSES, STATUS_LABELS, STATUS_COLORS, CHANNELS, PRIORITIES, PRIORITY_COLORS } from '../constants'
import type { Application, JD, Resume, Contact } from '../types'

const columns = ref<Record<string, Application[]>>({
  intention: [],
  applied: [],
  written: [],
  interview: [],
  offer: [],
  closed: []
})
const draggingId = ref<number | null>(null)

async function load() {
  try {
    const list = await api.get<Application[]>('/api/applications')
    const c: Record<string, Application[]> = { intention: [], applied: [], written: [], interview: [], offer: [], closed: [] }
    for (const a of list) (c[a.status] || (c[a.status] = [])).push(a)
    columns.value = c
  } catch (e: any) {
    toast('error', e.message)
  }
}

function onChange(status: string, evt: any) {
  if (evt.added) {
    const app: Application = evt.added.element
    draggingId.value = app.id
    api
      .post(`/api/applications/${app.id}/transition`, { target_status: status })
      .then(() => {
        toast('success', `已流转至「${STATUS_LABELS[status]}」`)
      })
      .catch((e: any) => {
        toast('error', e.message || '非法流转，已回滚')
        load() // 回滚：重新拉取服务端真实状态
      })
      .finally(() => {
        draggingId.value = null
      })
  }
}

// 详情抽屉
const showDetail = ref(false)
const detail = ref<Application | null>(null)
const dForm = reactive({
  contact_id: null as number | null,
  channel: '',
  priority: '',
  expected_salary: '',
  next_followup_at: '',
  offer_salary: '',
  close_reason: '',
  note: ''
})

async function openDetail(a: Application) {
  try {
    const full = await api.get<Application>(`/api/applications/${a.id}`)
    detail.value = full
    dForm.contact_id = full.contact_id
    dForm.channel = full.channel
    dForm.priority = full.priority
    dForm.expected_salary = full.expected_salary
    dForm.next_followup_at = full.next_followup_at || ''
    dForm.offer_salary = full.offer_salary != null ? String(full.offer_salary) : ''
    dForm.close_reason = full.close_reason || ''
    dForm.note = full.note
    showDetail.value = true
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function saveDetail() {
  if (!detail.value) return
  const payload: any = {
    contact_id: dForm.contact_id,
    channel: dForm.channel,
    priority: dForm.priority,
    expected_salary: dForm.expected_salary,
    next_followup_at: dForm.next_followup_at || null,
    offer_salary: dForm.offer_salary ? Number(dForm.offer_salary) : null,
    close_reason: dForm.close_reason || null,
    note: dForm.note
  }
  try {
    await api.put(`/api/applications/${detail.value.id}`, payload)
    toast('success', '已保存')
    showDetail.value = false
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

// 新建投递
const showNew = ref(false)
const jds = ref<JD[]>([])
const resumes = ref<Resume[]>([])
const contacts = ref<Contact[]>([])
const nForm = reactive({
  jd_id: '',
  resume_id: '',
  contact_id: '',
  channel: CHANNELS[0],
  priority: PRIORITIES[1]
})

async function openNew() {
  try {
    ;[jds.value, resumes.value, contacts.value] = await Promise.all([
      api.get<JD[]>('/api/jds?status=&direction='),
      api.get<Resume[]>('/api/resumes?direction='),
      api.get<Contact[]>('/api/contacts')
    ])
    nForm.jd_id = jds.value[0]?.id ? String(jds.value[0].id) : ''
    nForm.resume_id = resumes.value[0]?.id ? String(resumes.value[0].id) : ''
    nForm.contact_id = ''
    showNew.value = true
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function createApp() {
  if (!nForm.jd_id || !nForm.resume_id) {
    toast('error', '请选择 JD 与简历版本')
    return
  }
  const payload: any = {
    jd_id: Number(nForm.jd_id),
    resume_id: Number(nForm.resume_id),
    channel: nForm.channel,
    priority: nForm.priority
  }
  if (nForm.contact_id) payload.contact_id = Number(nForm.contact_id)
  try {
    await api.post('/api/applications', payload)
    toast('success', '投递已创建')
    showNew.value = false
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
      <p class="text-sm text-slate-500">拖拽卡片在阶段间流转；非法流转会自动回滚。</p>
      <button class="btn-primary" @click="openNew">+ 新建投递</button>
    </div>

    <div class="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <div v-for="st in STATUSES" :key="st" class="flex flex-col rounded-xl bg-slate-100/70 p-2">
        <div class="mb-2 flex items-center justify-between px-1">
          <span class="text-sm font-semibold text-slate-700">{{ STATUS_LABELS[st] }}</span>
          <span class="badge bg-white text-slate-500">{{ columns[st].length }}</span>
        </div>
        <draggable
          :list="columns[st]"
          group="apps"
          item-key="id"
          class="flex min-h-[6rem] flex-1 flex-col gap-2"
          ghost-class="opacity-40"
          @change="onChange(st, $event)"
        >
          <template #item="{ element }">
            <div
              class="cursor-pointer rounded-lg border border-slate-200 bg-white p-2 text-sm shadow-sm hover:border-indigo-300"
              :class="{ 'ring-2 ring-indigo-400': draggingId === element.id }"
              @click="openDetail(element)"
            >
              <div class="font-medium text-slate-800">{{ element.company_snapshot }}·{{ element.title_snapshot }}</div>
              <div class="mt-1 flex flex-wrap items-center gap-1">
                <span class="badge bg-slate-100 text-slate-500">{{ element.direction_tag }}</span>
                <span class="badge" :class="PRIORITY_COLORS[element.priority]">{{ element.priority }}</span>
              </div>
              <div class="mt-1 text-xs text-slate-400">
                {{ element.channel }} · 跟进 {{ element.next_followup_at || '—' }}
              </div>
            </div>
          </template>
        </draggable>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <Modal v-model="showDetail" title="投递详情" width="48rem">
      <div v-if="detail" class="space-y-4">
        <div class="rounded-lg bg-slate-50 p-3 text-sm">
          <div class="font-semibold">{{ detail.company_snapshot }} · {{ detail.title_snapshot }}</div>
          <div class="mt-1 text-slate-500">方向：{{ detail.direction_tag }} · 状态：{{ STATUS_LABELS[detail.status] }}</div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">渠道</label>
            <select v-model="dForm.channel" class="input">
              <option v-for="c in CHANNELS" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div>
            <label class="label">优先级</label>
            <select v-model="dForm.priority" class="input">
              <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div>
            <label class="label">期望薪资</label>
            <input v-model="dForm.expected_salary" class="input" />
          </div>
          <div>
            <label class="label">跟进日期</label>
            <input v-model="dForm.next_followup_at" type="date" class="input" />
          </div>
          <div>
            <label class="label">Offer 薪资</label>
            <input v-model="dForm.offer_salary" class="input" placeholder="数字" />
          </div>
          <div>
            <label class="label">关闭原因</label>
            <input v-model="dForm.close_reason" class="input" />
          </div>
        </div>
        <div>
          <label class="label">备注</label>
          <textarea v-model="dForm.note" rows="2" class="input"></textarea>
        </div>
        <div>
          <label class="label">面试记录（共 {{ detail.interviews?.length || 0 }}）</label>
          <ul class="space-y-1 text-sm text-slate-600">
            <li v-for="iv in detail.interviews || []" :key="iv.id" class="rounded bg-slate-50 px-2 py-1">
              {{ iv.round }} · {{ iv.scheduled_at }} · {{ iv.mode }}
            </li>
            <li v-if="!detail.interviews?.length" class="text-slate-400">暂无面试</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showDetail = false">关闭</button>
        <button class="btn-primary" @click="saveDetail">保存</button>
      </template>
    </Modal>

    <!-- 新建 -->
    <Modal v-model="showNew" title="新建投递">
      <div class="space-y-4">
        <div>
          <label class="label">选择 JD *</label>
          <select v-model="nForm.jd_id" class="input">
            <option v-for="j in jds" :key="j.id" :value="j.id">{{ j.company }} · {{ j.title }}</option>
          </select>
        </div>
        <div>
          <label class="label">选择简历版本 *</label>
          <select v-model="nForm.resume_id" class="input">
            <option v-for="r in resumes" :key="r.id" :value="r.id">{{ r.version_name }}</option>
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="label">渠道</label>
            <select v-model="nForm.channel" class="input">
              <option v-for="c in CHANNELS" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div>
            <label class="label">优先级</label>
            <select v-model="nForm.priority" class="input">
              <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="label">联系人（可选）</label>
          <select v-model="nForm.contact_id" class="input">
            <option value="">（无）</option>
            <option v-for="c in contacts" :key="c.id" :value="c.id">{{ c.name }} · {{ c.org }}</option>
          </select>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showNew = false">取消</button>
        <button class="btn-primary" @click="createApp">创建</button>
      </template>
    </Modal>
  </div>
</template>
