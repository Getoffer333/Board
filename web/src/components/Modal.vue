<script setup lang="ts">
const props = defineProps<{ modelValue: boolean; title?: string; width?: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 py-10"
      @click.self="close"
    >
      <div
        class="w-full rounded-2xl bg-white shadow-xl"
        :style="{ maxWidth: width || '40rem' }"
      >
        <div class="flex items-center justify-between border-b border-slate-100 px-5 py-3">
          <h3 class="text-base font-semibold text-slate-800">{{ title }}</h3>
          <button class="text-slate-400 hover:text-slate-600" @click="close">✕</button>
        </div>
        <div class="max-h-[70vh] overflow-y-auto px-5 py-4">
          <slot />
        </div>
        <div v-if="$slots.footer" class="flex justify-end gap-2 border-t border-slate-100 px-5 py-3">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>
