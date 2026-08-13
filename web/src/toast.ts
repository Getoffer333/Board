import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warn'

export const toasts = reactive<{ id: number; type: ToastType; msg: string }[]>([])

let seq = 0

export function toast(type: ToastType, msg: string) {
  const id = ++seq
  toasts.push({ id, type, msg })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, 3200)
}
