<script setup lang="ts">
import { toasts } from '../toast'

const COLORS: Record<string, string> = {
  success: 'bg-emerald-600',
  error: 'bg-rose-600',
  info: 'bg-slate-700',
  warn: 'bg-amber-600'
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-[60] flex flex-col gap-2">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="rounded-lg px-4 py-2 text-sm text-white shadow-lg"
        :class="COLORS[t.type]"
      >
        {{ t.msg }}
      </div>
    </div>
  </Teleport>
</template>
