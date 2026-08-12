// API 基址：同源（后端单端口 7788 托管前端），留空字符串
const BASE = ''

async function request<T>(method: string, path: string, body?: any, isForm = false): Promise<T> {
  const opts: RequestInit = { method, headers: {} }
  if (body !== undefined) {
    if (isForm) {
      opts.body = body as FormData
    } else {
      ;(opts.headers as Record<string, string>)['Content-Type'] = 'application/json'
      opts.body = JSON.stringify(body)
    }
  }
  let data: any = null
  try {
    const res = await fetch(BASE + path, opts)
    const text = await res.text()
    if (text) {
      try {
        data = JSON.parse(text)
      } catch {
        data = text
      }
    }
    if (!res.ok) {
      const msg = data && data.error ? data.error : `请求失败 (HTTP ${res.status})`
      throw new Error(msg)
    }
    if (data && data.error) {
      throw new Error(data.error)
    }
  } catch (e) {
    if (e instanceof TypeError) {
      // 网络层错误（fetch 失败）
      throw new Error('网络请求失败，请确认后端服务已启动')
    }
    throw e
  }
  return data as T
}

export const api = {
  get: <T>(p: string) => request<T>('GET', p),
  post: <T>(p: string, b?: any) => request<T>('POST', p, b),
  put: <T>(p: string, b?: any) => request<T>('PUT', p, b),
  del: <T>(p: string) => request<T>('DELETE', p),
  postForm: <T>(p: string, form: FormData) => request<T>('POST', p, form, true),
  putForm: <T>(p: string, form: FormData) => request<T>('PUT', p, form, true)
}

export default api
