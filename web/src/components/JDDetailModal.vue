<script setup lang="ts">
import { ref, watch } from 'vue'
import api from '../api'
import { toast } from '../toast'
import Modal from './Modal.vue'
import { STATUS_LABELS } from '../constants'

const props = defineProps<{ jdId: number | null }>()
const emit = defineEmits<{ (e: 'update:jdId', v: number | null): void; (e: 'changed'): void }>()

const detail = ref<any>(null)
const loading = ref(false)

watch(() => props.jdId, (id) => {
  if (id) loadDetail(id)
})

async function loadDetail(id: number) {
  loading.value = true
  detail.value = null
  try {
    detail.value = await api.get<any>(`/api/jds/${id}/analyze`)
  } catch (e: any) { toast('error', e.message) }
  loading.value = false
}

function close() { emit('update:jdId', null) }

async function markIntention() {
  if (!detail.value?.jd) return
  try {
    const r = await api.post<any>(`/api/jds/${detail.value.jd.id}/mark-intention`)
    detail.value.jd.status = r.status
    if (r.status === 'intention') {
      if (r.warning) toast('warn', r.warning)
      else if (r.already_existed) toast('info', '已标为意向，投递看板已有该记录')
      else toast('success', '已标为意向 ⭐，已同步到投递看板「意向」栏')
    } else {
      toast('success', r.removed ? '已取消意向，投递看板记录已移除' : '已取消意向')
    }
    emit('changed')
  } catch (e: any) { toast('error', e.message) }
}
</script>

<template>
  <Modal :model-value="!!jdId" @update:model-value="close" title="JD 详情" width="52rem">
    <div v-if="loading" class="py-8 text-center text-slate-400">分析中...</div>
    <div v-else-if="detail" class="space-y-4">
      <!-- 顶部信息 -->
      <div>
        <div class="flex items-center gap-2">
          <span class="text-lg font-semibold text-slate-800">{{ detail.jd.company }} · {{ detail.jd.title }}</span>
          <span class="badge" :class="detail.jd.status === 'intention' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'">
            {{ STATUS_LABELS[detail.jd.status] || detail.jd.status }}
          </span>
        </div>
        <div class="mt-1 flex flex-wrap gap-2 text-xs">
          <span class="badge bg-indigo-100 text-indigo-700">{{ detail.jd.direction_tag }}</span>
          <span v-if="detail.jd.salary_range" class="badge bg-slate-100 text-slate-600">💰 {{ detail.jd.salary_range }}</span>
          <span v-if="detail.jd.location" class="badge bg-slate-100 text-slate-600">📍 {{ detail.jd.location }}</span>
          <span v-if="detail.jd.source" class="badge bg-slate-100 text-slate-600">{{ detail.jd.source }}</span>
        </div>
      </div>

      <!-- 方向预警 -->
      <div v-if="detail.jd.direction_alert" class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
        ⚠️ {{ detail.jd.direction_alert }}
      </div>

      <!-- 结构化解析 -->
      <div v-if="detail.jd.parsed_json" class="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div v-if="detail.jd.parsed_json.responsibilities?.length">
          <h4 class="mb-1 font-semibold text-slate-700">📋 岗位职责</h4>
          <ul class="list-disc space-y-0.5 pl-4 text-sm text-slate-600">
            <li v-for="(r, i) in detail.jd.parsed_json.responsibilities" :key="i">{{ r }}</li>
          </ul>
        </div>
        <div v-if="detail.jd.parsed_json.requirements?.length">
          <h4 class="mb-1 font-semibold text-slate-700">✅ 任职要求</h4>
          <ul class="list-disc space-y-0.5 pl-4 text-sm text-slate-600">
            <li v-for="(r, i) in detail.jd.parsed_json.requirements" :key="i">{{ r }}</li>
          </ul>
        </div>
      </div>

      <!-- 关键词 -->
      <div v-if="detail.jd.parsed_json?.keywords?.length">
        <h4 class="mb-1 font-semibold text-slate-700">🔑 核心关键词</h4>
        <div class="flex flex-wrap gap-2">
          <span v-for="k in detail.jd.parsed_json.keywords" :key="k" class="badge bg-indigo-100 text-indigo-700">{{ k }}</span>
        </div>
      </div>

      <!-- 基于你的情况分析 -->
      <div class="rounded-lg border border-indigo-100 bg-indigo-50/50 p-3">
        <h4 class="mb-2 font-semibold text-indigo-800">🎯 基于你的情况分析</h4>
        <div class="mb-2 flex flex-wrap gap-2 text-xs text-indigo-600">
          <span>主方向：{{ detail.user?.primary_direction || '未设置' }}</span>
          <span v-if="detail.user?.years_experience">工作年限：{{ detail.user.years_experience }}年</span>
          <span v-if="detail.user?.education">学历：{{ detail.user.education }}</span>
          <span v-if="detail.user?.current_city">城市：{{ detail.user.current_city }}</span>
          <span v-if="detail.resume_version">对比简历：{{ detail.resume_version }}</span>
        </div>
        <template v-if="detail.match">
          <div class="flex items-center gap-3">
            <span class="text-3xl font-bold" :class="detail.match.score >= 75 ? 'text-emerald-600' : detail.match.score >= 55 ? 'text-amber-600' : 'text-rose-600'">
              {{ detail.match.score }}
            </span>
            <span class="text-sm text-slate-500">/ 100 匹配分</span>
            <span v-if="detail.match.source === 'online'" class="badge bg-indigo-100 text-indigo-700">AI 匹配</span>
            <span v-else-if="detail.match.source === 'local'" class="badge bg-slate-100 text-slate-600">本地匹配</span>
          </div>
          <div v-if="detail.match.matched_points?.length" class="mt-2 text-sm">
            <div class="font-medium text-emerald-700">✅ 已命中</div>
            <div class="mt-1 flex flex-wrap gap-1">
              <span v-for="k in detail.match.matched_points" :key="k" class="badge bg-emerald-100 text-emerald-700">{{ k }}</span>
            </div>
          </div>
          <div v-if="detail.match.missing_points?.length" class="mt-2 text-sm">
            <div class="font-medium text-rose-700">❌ 缺失</div>
            <div class="mt-1 flex flex-wrap gap-1">
              <span v-for="k in detail.match.missing_points" :key="k" class="badge bg-rose-100 text-rose-700">{{ k }}</span>
            </div>
          </div>
          <div v-if="detail.match.resume_edits?.length" class="mt-2 rounded bg-blue-50 p-2 text-sm">
            <div class="font-medium text-blue-700">📝 简历怎么改</div>
            <ul class="mt-1 list-disc space-y-0.5 pl-4 text-slate-700">
              <li v-for="(e, i) in detail.match.resume_edits" :key="i">{{ e }}</li>
            </ul>
          </div>
          <div v-if="detail.match.suggestion" class="mt-2 rounded bg-white p-2 text-sm text-slate-600">{{ detail.match.suggestion }}</div>
        </template>
        <div v-else class="text-sm text-slate-400">暂无简历可对比，上传简历后可出匹配分析。</div>
      </div>
    </div>

    <template #footer>
      <button v-if="detail" class="btn-primary" @click="markIntention">
        {{ detail.jd.status === 'intention' ? '取消意向' : '⭐ 标为意向' }}
      </button>
    </template>
  </Modal>
</template>
