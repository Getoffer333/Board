<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api'
import { toast } from '../toast'
import { refreshOverdue, store } from '../store'
import { LEVEL_COLORS } from '../constants'
import type { SummaryStat, FunnelStat, DirectionStat, ResumeVersionStat, Overdue } from '../types'

const summary = ref<SummaryStat | null>(null)
const funnel = ref<FunnelStat | null>(null)
const direction = ref<DirectionStat[]>([])
const resumeVersions = ref<ResumeVersionStat[]>([])
const overdue = ref<Overdue[]>([])

const funnelEl = ref<HTMLElement | null>(null)
const barEl = ref<HTMLElement | null>(null)
let funnelChart: echarts.ECharts | null = null
let barChart: echarts.ECharts | null = null

const cardDefs = [
  { key: 'total_applications', label: '总投递', color: 'text-indigo-600' },
  { key: 'active', label: '进行中', color: 'text-blue-600' },
  { key: 'interviews', label: '面试', color: 'text-cyan-600' },
  { key: 'offers', label: 'Offer', color: 'text-emerald-600' },
  { key: 'resumes', label: '简历', color: 'text-violet-600' },
  { key: 'jds', label: 'JD', color: 'text-amber-600' },
  { key: 'contacts', label: '人脉', color: 'text-pink-600' },
  { key: 'questions', label: '题库', color: 'text-teal-600' },
  { key: 'skills', label: '技能', color: 'text-orange-600' },
  { key: 'reminders', label: '提醒', color: 'text-rose-600' }
] as const

async function load() {
  try {
    ;[summary.value, funnel.value, direction.value, resumeVersions.value, overdue.value] = await Promise.all([
      api.get<SummaryStat>('/api/stats/summary'),
      api.get<FunnelStat>('/api/stats/funnel'),
      api.get<DirectionStat[]>('/api/stats/direction'),
      api.get<ResumeVersionStat[]>('/api/stats/resume-versions'),
      api.get<Overdue[]>('/api/stats/overdue')
    ])
    store.overdue = overdue.value
    store.overdueCount = overdue.value.length
    await nextTick()
    renderCharts()
  } catch (e: any) {
    toast('error', e.message || '加载失败')
  }
}

function renderCharts() {
  if (!funnelEl.value) return
  funnelChart = echarts.init(funnelEl.value)
  const data = (funnel.value?.series || []).map((s) => ({ name: s.label, value: s.count }))
  funnelChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}' },
    series: [
      {
        type: 'funnel',
        left: '8%',
        right: '8%',
        top: 20,
        bottom: 20,
        minSize: '20%',
        sort: 'descending',
        gap: 2,
        label: { show: true, position: 'inside', formatter: '{b} {c}', color: '#fff' },
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        color: ['#4f46e5', '#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff'],
        data
      }
    ]
  })

  if (!barEl.value) return
  barChart = echarts.init(barEl.value)
  const dirs = direction.value.map((d) => d.direction)
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['投递', '面试', 'Offer'] },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dirs },
    yAxis: { type: 'value' },
    series: [
      { name: '投递', type: 'bar', data: direction.value.map((d) => d.applications), itemStyle: { color: '#4f46e5' } },
      { name: '面试', type: 'bar', data: direction.value.map((d) => d.interviews), itemStyle: { color: '#06b6d4' } },
      { name: 'Offer', type: 'bar', data: direction.value.map((d) => d.offers), itemStyle: { color: '#10b981' } }
    ]
  })
}

function onResize() {
  funnelChart?.resize()
  barChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  funnelChart?.dispose()
  barChart?.dispose()
})
</script>

<template>
  <div class="space-y-5">
    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      <div v-for="c in cardDefs" :key="c.key" class="card flex flex-col">
        <span class="text-xs text-slate-400">{{ c.label }}</span>
        <span class="mt-1 text-2xl font-bold" :class="c.color">{{ summary ? (summary as any)[c.key] : '-' }}</span>
      </div>
    </div>

    <!-- 图表 -->
    <div class="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <div class="card">
        <h3 class="mb-2 font-semibold text-slate-700">投递漏斗</h3>
        <div ref="funnelEl" class="h-72 w-full"></div>
      </div>
      <div class="card">
        <h3 class="mb-2 font-semibold text-slate-700">方向对比</h3>
        <div ref="barEl" class="h-72 w-full"></div>
      </div>
    </div>

    <!-- 简历版本效果 -->
    <div class="card">
      <h3 class="mb-3 font-semibold text-slate-700">简历版本效果</h3>
      <table class="w-full text-sm">
        <thead class="text-left text-slate-400">
          <tr class="border-b border-slate-100">
            <th class="py-2">版本</th>
            <th>方向</th>
            <th>使用次数</th>
            <th>面试</th>
            <th>Offer</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in resumeVersions" :key="r.id" class="border-b border-slate-50">
            <td class="py-2 font-medium">{{ r.version }}</td>
            <td>{{ r.direction }}</td>
            <td>{{ r.used }}</td>
            <td>{{ r.interviews }}</td>
            <td>{{ r.offers }}</td>
          </tr>
          <tr v-if="resumeVersions.length === 0">
            <td colspan="5" class="py-4 text-center text-slate-400">暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 提醒 -->
    <div class="card">
      <div class="mb-3 flex items-center justify-between">
        <h3 class="font-semibold text-slate-700">待办提醒（{{ overdue.length }}）</h3>
        <button class="text-xs text-indigo-600" @click="refreshOverdue">刷新</button>
      </div>
      <div v-if="overdue.length === 0" class="py-4 text-center text-sm text-slate-400">暂无提醒 🎉</div>
      <ul v-else class="space-y-2">
        <li
          v-for="(o, i) in overdue"
          :key="i"
          class="rounded-lg border px-3 py-2 text-sm"
          :class="LEVEL_COLORS[o.level] || 'bg-slate-50 border-slate-200'"
        >
          <div class="font-medium">{{ o.title }}</div>
          <div class="mt-0.5 opacity-80">{{ o.detail }}</div>
        </li>
      </ul>
    </div>
  </div>
</template>
