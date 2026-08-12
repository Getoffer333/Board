<script setup lang="ts">
import { onMounted, ref } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from '../components/Modal.vue'
import { ROLES, WARMTH } from '../constants'
import type { Contact } from '../types'

const items = ref<Contact[]>([])
const showModal = ref(false)
const editing = ref<Contact | null>(null)
const form = ref({
  name: '',
  org: '',
  role: ROLES[0],
  wechat: '',
  phone: '',
  email: '',
  warmth: WARMTH[1],
  last_contact_at: '',
  followup_cycle_days: 30,
  next_followup_at: '',
  note: ''
})

async function load() {
  try {
    items.value = await api.get<Contact[]>('/api/contacts')
  } catch (e: any) {
    toast('error', e.message)
  }
}

function openNew() {
  editing.value = null
  form.value = {
    name: '',
    org: '',
    role: ROLES[0],
    wechat: '',
    phone: '',
    email: '',
    warmth: WARMTH[1],
    last_contact_at: '',
    followup_cycle_days: 30,
    next_followup_at: '',
    note: ''
  }
  showModal.value = true
}

function openEdit(c: Contact) {
  editing.value = c
  form.value = {
    name: c.name,
    org: c.org,
    role: c.role,
    wechat: c.wechat,
    phone: c.phone,
    email: c.email,
    warmth: c.warmth,
    last_contact_at: c.last_contact_at || '',
    followup_cycle_days: c.followup_cycle_days,
    next_followup_at: c.next_followup_at || '',
    note: c.note
  }
  showModal.value = true
}

async function submit() {
  if (!form.value.name.trim()) {
    toast('error', '请填写姓名')
    return
  }
  try {
    if (editing.value) {
      await api.put(`/api/contacts/${editing.value.id}`, { ...form.value })
      toast('success', '已更新')
    } else {
      await api.post('/api/contacts', { ...form.value })
      toast('success', '已添加')
    }
    showModal.value = false
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function touch(c: Contact) {
  try {
    await api.put(`/api/contacts/${c.id}`, { touch: true })
    toast('success', '已标记为联系，已更新下次跟进')
    await load()
  } catch (e: any) {
    toast('error', e.message)
  }
}

async function remove(c: Contact) {
  if (!confirm(`确认删除联系人「${c.name}」？`)) return
  try {
    await api.del(`/api/contacts/${c.id}`)
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
      <p class="text-sm text-slate-500">维护内推人与 HR 人脉，按时跟进。</p>
      <button class="btn-primary" @click="openNew">+ 新建联系人</button>
    </div>

    <div class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">姓名</th>
            <th>机构</th>
            <th>角色</th>
            <th>亲密度</th>
            <th>最近联系</th>
            <th>下次跟进</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in items" :key="c.id" class="border-b border-slate-50">
            <td class="py-2 font-medium">{{ c.name }}</td>
            <td>{{ c.org || '—' }}</td>
            <td>{{ c.role }}</td>
            <td>{{ c.warmth }}</td>
            <td class="text-slate-500">{{ c.last_contact_at || '—' }}</td>
            <td class="text-slate-500">{{ c.next_followup_at || '—' }}</td>
            <td class="text-right whitespace-nowrap">
              <button class="btn-ghost mr-1" @click="openEdit(c)">编辑</button>
              <button class="btn-ghost mr-1" @click="touch(c)">标记联系</button>
              <button class="btn-danger" @click="remove(c)">删除</button>
            </td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="7" class="py-6 text-center text-slate-400">暂无联系人</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="showModal" :title="editing ? '编辑联系人' : '新建联系人'">
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label">姓名 *</label>
          <input v-model="form.name" class="input" />
        </div>
        <div>
          <label class="label">机构</label>
          <input v-model="form.org" class="input" />
        </div>
        <div>
          <label class="label">角色</label>
          <select v-model="form.role" class="input">
            <option v-for="r in ROLES" :key="r" :value="r">{{ r }}</option>
          </select>
        </div>
        <div>
          <label class="label">亲密度</label>
          <select v-model="form.warmth" class="input">
            <option v-for="w in WARMTH" :key="w" :value="w">{{ w }}</option>
          </select>
        </div>
        <div>
          <label class="label">微信</label>
          <input v-model="form.wechat" class="input" />
        </div>
        <div>
          <label class="label">电话</label>
          <input v-model="form.phone" class="input" />
        </div>
        <div>
          <label class="label">邮箱</label>
          <input v-model="form.email" class="input" />
        </div>
        <div>
          <label class="label">跟进周期(天)</label>
          <input v-model="form.followup_cycle_days" type="number" class="input" />
        </div>
        <div>
          <label class="label">最近联系</label>
          <input v-model="form.last_contact_at" type="date" class="input" />
        </div>
        <div>
          <label class="label">下次跟进</label>
          <input v-model="form.next_followup_at" type="date" class="input" />
        </div>
        <div class="col-span-2">
          <label class="label">备注</label>
          <textarea v-model="form.note" rows="2" class="input"></textarea>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="showModal = false">取消</button>
        <button class="btn-primary" @click="submit">保存</button>
      </template>
    </Modal>
  </div>
</template>
