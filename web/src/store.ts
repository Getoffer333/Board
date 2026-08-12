import { reactive } from 'vue'
import api from './api'
import type { Overdue } from './types'

export const store = reactive({
  overdue: [] as Overdue[],
  overdueCount: 0,
  loadingOverdue: false
})

export async function refreshOverdue() {
  if (store.loadingOverdue) return
  store.loadingOverdue = true
  try {
    const list = await api.get<Overdue[]>('/api/stats/overdue')
    store.overdue = list || []
    store.overdueCount = store.overdue.length
  } catch {
    store.overdue = []
    store.overdueCount = 0
  } finally {
    store.loadingOverdue = false
  }
}
