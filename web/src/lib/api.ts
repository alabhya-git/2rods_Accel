export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function req<T>(method: string, path: string, body?: unknown, headers: Record<string, string> = {}): Promise<T> {
  const init: RequestInit = { method, headers: { ...headers } }
  if (body instanceof FormData) init.body = body
  else if (body !== undefined) {
    init.body = JSON.stringify(body)
    ;(init.headers as Record<string, string>)['content-type'] = 'application/json'
  }
  const r = await fetch(path, init)
  const text = await r.text()
  const data = text ? JSON.parse(text) : null
  if (!r.ok) {
    const detail = data?.detail
    throw new ApiError(r.status, typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg ?? 'Request failed' : 'Request failed')
  }
  return data as T
}

export const api = {
  get: <T,>(p: string, h?: Record<string, string>) => req<T>('GET', p, undefined, h),
  post: <T,>(p: string, b?: unknown, h?: Record<string, string>) => req<T>('POST', p, b ?? {}, h),
}

export function rupees(n: number | null | undefined): string {
  if (n === null || n === undefined) return ''
  return 'Rs ' + Math.round(n).toLocaleString('en-IN')
}

export function store(key: string, value?: string): string | null {
  try {
    if (value === undefined) return localStorage.getItem(key)
    localStorage.setItem(key, value)
    return value
  } catch {
    return null
  }
}

// ---- types mirrored from the API ----
export type Line = {
  product_id: string; name: string; category: string; unit: string; qty: number; unit_price: number; monthly: number
  setup: number; contract_months: number; install_days: number; source: string; need: string | null; reason: Record<string, any>
}
export type Exclusion = { product_id: string; name: string; rule: string; args: Record<string, any>; alternative_id: string | null; alternative_name: string | null; reason?: string }
export type AddOn = { need: string; product_id: string; name: string; qty: number; unit_price: number; monthly: number; setup: number; eligible: boolean; rule: string | null; args: Record<string, any> }
export type Bundle = {
  name: string; segment: string | null; term_months: number; lines: Line[]; exclusions: Exclusion[]; addons: AddOn[]
  monthly: number; monthly_other_term: number; setup: number; setup_emi: number; gst_monthly: number; first_payment: number
  contract_months: number; install_days: number; notes: Record<string, any>[]
}
export type Turn = {
  text: string; language: string; stage: string; bundle: Bundle | null; quick_replies: string[]; trace: Record<string, any>[]
  llm_used: boolean; guard: { passed: boolean; issues: string[] } | null; asked: string | null; refine?: Refine[]; diff?: QuoteDiff | null
}
export type SessionView = {
  session_id: string; language: string; channel: string; partner_id: string | null; status: string; profile: Record<string, any>
  bundle: Bundle | null; messages: { role: string; text: string }[]; turn: Turn | null
}
export type Milestone = { kind: string; title: string; status: string; at?: string | null; eta?: string | null; product_id?: string; install_days?: number }
export type OrderView = {
  id: string; status: string; business_name: string | null; segment: string | null; city: string | null; language: string
  bundle: Bundle; term_months: number; monthly: number; setup: number; setup_emi: boolean; kyc_outcome: string | null
  kyc: KycResult | null; payment: Record<string, any> | null; install_slot: string | null; gstin_masked: string | null; created_at?: string
  specimen: string | null; milestones: Milestone[]; events: { id: number; ts: string; kind: string; title: string; product_id?: string | null; detail: any }[]
  consent?: Record<string, { granted: boolean; since: string; withdrawn_at: string | null }>
  access_key?: string; order_id?: string; phone_masked?: string
}
export type Check = { id: string; level: string; status: string; severity: string; message: string; fix: string | null; args: Record<string, any> }
export type KycResult = { outcome: string; checks: Check[]; registry: Record<string, any>; extracted: Record<string, any> }

export type Refine = { key: string; question: string; impact: number; product_id: string; options: { label: string; patch: Record<string, any>; monthly_delta: number }[] }
export type QuoteDiff = { added: string[]; removed: string[]; changed: { name: string; from: number; to: number }[]; monthly_before: number | null; monthly_after: number }
export type ScheduleRow = { month: number; recurring: number; setup: number; gst: number; total: number }
export type Schedule = {
  term_months: number; setup_emi: boolean; rows: ScheduleRow[]; due_today: number; monthly: number; monthly_after_emi: number
  emi_months: number; instalment: number; last_instalment: number; setup_total: number; total_commitment: number; mandate_limit: number; hash: string
}

/** Paise from the payment schedule, shown as Rs with Indian grouping (paise only when present). */
export function paise(n: number | null | undefined): string {
  if (n === null || n === undefined) return ''
  const r = Math.floor(n / 100), p = n % 100
  return 'Rs ' + r.toLocaleString('en-IN') + (p ? '.' + String(p).padStart(2, '0') : '')
}

/** Orders placed on this device (no login needed): id + access key, newest first. */
export type SavedOrder = { id: string; key: string; at: string }
export function myOrders(): SavedOrder[] {
  try { return JSON.parse(store('orders') || '[]') } catch { return [] }
}
export function rememberOrder(id: string, key: string) {
  const list = myOrders().filter((o) => o.id !== id)
  store('orders', JSON.stringify([{ id, key, at: new Date().toISOString() }, ...list].slice(0, 20)))
}
