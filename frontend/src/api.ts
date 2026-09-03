// Local Vite and the hosted single-service deployment both use a same-origin
// /api route. A custom VITE_API_URL remains available for split deployments.
const API = import.meta.env.VITE_API_URL || '/api'

export type ApiError = { error?: string }

export async function api<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(init.headers || {}) } })
  const body = await response.json().catch(() => ({})) as T & ApiError
  if (!response.ok) throw new Error(body.error || 'Something went wrong. Please try again.')
  return body
}
