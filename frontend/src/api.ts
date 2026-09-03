// Local Vite development uses a same-origin proxy, so browser CORS settings never block the app.
const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '/api' : 'http://127.0.0.1:5000/api')

export type ApiError = { error?: string }

export async function api<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init.headers || {}) } })
  const body = await response.json().catch(() => ({})) as T & ApiError
  if (!response.ok) throw new Error(body.error || 'Something went wrong. Please try again.')
  return body
}
