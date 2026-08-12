<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { store, refreshOverdue } from './store'
import { LEVEL_COLORS } from './constants'
import ToastContainer from './components/ToastContainer.vue'

const router = useRouter()
const bellOpen = ref(false)

const menus = [
  { path: '/dashboard', label: '驾驶舱', icon: '📊', v2: '增强' },
  { path: '/resumes', label: '简历库', icon: '📄' },
  { path: '/jds', label: 'JD库', icon: '📋' },
  { path: '/applications', label: '投递看板', icon: '🚀' },
  { path: '/scripts', label: '逐字稿', icon: '🎙️', v2: '新增' },
  { path: '/interviews', label: '面试中心', icon: '🎤' },
  { path: '/skills', label: '技能提升', icon: '📈' },
  { path: '/contacts', label: '人脉内推', icon: '🤝' },
  { path: '/questions', label: '面试题库', icon: '❓' },
  { path: '/ai', label: 'AI工具', icon: '🤖', v2: '增强' },
  { path: '/settings', label: '设置', icon: '⚙️' }
]

onMounted(refreshOverdue)

function goOverdue(o: { entity: string; entity_id: number }) {
  bellOpen.value = false
  const map: Record<string, string> = {
    application: '/applications',
    contact: '/contacts',
    interview: '/interviews'
  }
  const target = map[o.entity]
  if (target) router.push(target)
}
</script>

<template>
  <div class="flex h-full">
    <!-- 左侧导航 -->
    <aside class="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div class="flex items-center gap-2 px-5 py-4 text-lg font-bold text-indigo-700">
        <span class="text-2xl">🎯</span> 求职工作台
      </div>
      <nav class="flex-1 space-y-1 px-3 pb-4">
        <RouterLink
          v-for="m in menus"
          :key="m.path"
          :to="m.path"
          class="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
          active-class="!bg-indigo-600 !text-white"
        >
          <span>{{ m.icon }}</span>{{ m.label }}<span v-if="m.v2" class="ml-auto text-[10px] rounded bg-indigo-100 px-1.5 py-0.5 text-indigo-600 font-bold">🆕{{ m.v2 }}</span>
        </RouterLink>
      </nav>
      <div class="border-t border-slate-100 px-5 py-3 text-xs text-slate-400">v2.0 · 本地数据</div>
    </aside>

    <!-- 主区 -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <h1 class="text-lg font-semibold text-slate-800">
          {{ (menus.find((m) => router.currentRoute.value.path.startsWith(m.path)) || menus[0]).label }}
        </h1>
        <div class="relative">
          <button
            class="relative rounded-full bg-slate-100 px-3 py-2 text-lg hover:bg-slate-200"
            @click="bellOpen = !bellOpen"
          >
            🔔
            <span
              v-if="store.overdueCount > 0"
              class="absolute -right-1 -top-1 flex h-5 min-w-[1.25rem] items-center justify-center rounded-full bg-rose-500 px-1 text-xs font-bold text-white"
            >
              {{ store.overdueCount }}
            </span>
          </button>
          <div
            v-if="bellOpen"
            class="absolute right-0 z-40 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-3 shadow-xl"
          >
            <div class="mb-2 flex items-center justify-between px-1">
              <span class="text-sm font-semibold text-slate-700">提醒（{{ store.overdueCount }}）</span>
              <button class="text-xs text-indigo-600" @click="refreshOverdue">刷新</button>
            </div>
            <div v-if="store.overdue.length === 0" class="px-1 py-3 text-center text-sm text-slate-400">
              暂无提醒 🎉
            </div>
            <ul v-else class="max-h-80 space-y-2 overflow-y-auto">
              <li
                v-for="(o, i) in store.overdue"
                :key="i"
                class="cursor-pointer rounded-lg border px-3 py-2 text-sm"
                :class="LEVEL_COLORS[o.level] || 'bg-slate-50 border-slate-200'"
                @click="goOverdue(o)"
              >
                <div class="font-medium">{{ o.title }}</div>
                <div class="mt-0.5 opacity-80">{{ o.detail }}</div>
              </li>
            </ul>
          </div>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>

    <ToastContainer />
  </div>
</template>
