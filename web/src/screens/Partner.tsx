import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ErrorNote, Logo, Working } from '../components/ui'
import { api, rupees } from '../lib/api'

type Tab = 'help' | 'queue' | 'reviews' | 'orders' | 'metrics' | 'model'
const TABS: [Tab, string][] = [['help', 'Call-back requests'], ['queue', 'Leads to call'], ['reviews', 'KYC reviews'], ['orders', 'Orders'], ['metrics', 'Metrics'], ['model', 'Lead score']]
const SEG: Record<string, string> = { micro: 'Micro retail', prof: 'Professional office', multi: 'Multi-site', mfg: 'Manufacturer' }
type Who = { token: string; sub: string; role: string; name: string; partner_id: string | null }

/** Staff sign in as themselves: every action carries a real name and role, never a shared passcode. */
export default function Partner() {
  const [who, setWho] = useState<Who | null>(() => { try { return JSON.parse(sessionStorage.getItem('staff') || 'null') } catch { return null } })
  const [user, setUser] = useState('PARTNER-001')
  const [secret, setSecret] = useState('')
  const [tab, setTab] = useState<Tab>('help')
  const [err, setErr] = useState<string | null>(null)
  const H: Record<string, string> = who ? { Authorization: `Bearer ${who.token}` } : {}

  const login = async () => {
    try {
      const w = await api.post<Who>('/api/staff/login', { user, secret })
      sessionStorage.setItem('staff', JSON.stringify(w))
      sessionStorage.setItem('staff_token', w.token)
      setWho(w)
      setErr(null)
    } catch (e: any) { setErr(e.status === 401 ? 'Wrong name or passcode' : e.message) }
  }
  useEffect(() => { if (who) api.get('/api/staff/me', H).catch(() => { sessionStorage.removeItem('staff'); setWho(null) }) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (!who) return (
    <div className="mx-auto max-w-sm px-5 pt-16">
      <Logo />
      <h1 className="mt-8 text-[24px] font-bold">Partner desk</h1>
      <p className="text-ink-soft">For Accel field staff, KYC reviewers and channel partners. Demo accounts: PARTNER-001 / partner-demo, reviewer-1 or reviewer-2 / review-demo.</p>
      <form className="mt-4 space-y-2" onSubmit={(e) => { e.preventDefault(); login() }}>
        <input className="field w-full" value={user} onChange={(e) => setUser(e.target.value)} placeholder="Staff ID" aria-label="Staff ID" autoComplete="username" />
        <input className="field w-full" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="Passcode" aria-label="Passcode" autoComplete="current-password" />
        <button className="btn-primary w-full">Sign in</button>
      </form>
      <ErrorNote msg={err} />
    </div>
  )

  return (
    <div className="min-h-full">
      <header className="border-b border-rule bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4">
          <div className="flex items-center gap-4"><Logo small /><span className="text-[18px] font-bold text-ink-soft">Partner desk</span>
            <span className="hidden text-[14px] text-ink-soft sm:inline">{who.name} · {who.role}</span></div>
          <div className="flex items-center gap-2">
            {who.partner_id && <Link className="btn-primary min-h-[42px]" to={`/advisor?partner=${who.partner_id}`}>Start assisted journey</Link>}
            <button className="btn-quiet" onClick={() => { sessionStorage.removeItem('staff'); sessionStorage.removeItem('staff_token'); setWho(null) }}>Sign out</button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4" aria-label="Sections">
          {TABS.map(([k, label]) => (
            <button key={k} onClick={() => setTab(k)} aria-current={tab === k}
              className={`shrink-0 border-b-[3px] px-3 py-2 font-semibold ${tab === k ? 'border-kumkum text-ink' : 'border-transparent text-ink-soft'}`}>{label}</button>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-5">
        <ErrorNote msg={err} />
        {tab === 'help' && <HelpQueue H={H} />}
        {tab === 'queue' && <Queue H={H} />}
        {tab === 'reviews' && (who.role === 'reviewer' || who.role === 'admin' ? <Reviews H={H} /> : <p className="text-ink-soft">KYC reviews need a reviewer sign-in.</p>)}
        {tab === 'orders' && <Orders H={H} />}
        {tab === 'metrics' && <Metrics H={H} />}
        {tab === 'model' && <Model H={H} />}
      </main>
    </div>
  )
}

function Queue({ H }: { H: Record<string, string> }) {
  const [data, setData] = useState<any>(null)
  const [seg, setSeg] = useState('')
  const [reason, setReason] = useState('')
  const [calls, setCalls] = useState<Record<string, string>>({})
  useEffect(() => {
    const qs = new URLSearchParams({ limit: '30', ...(seg && { segment: seg }), ...(reason && { reason }) })
    api.get<any>(`/api/backoffice/leads?${qs}`, H).then(setData)
  }, [seg, reason]) // eslint-disable-line react-hooks/exhaustive-deps
  const call = async (lead: string) => {
    const r = await api.post<any>(`/api/backoffice/leads/${lead}/call`, {}, H)
    setCalls({ ...calls, [lead]: r.virtual_number })
  }
  if (!data) return <Working label="Scoring leads" />
  return (
    <div>
      <p className="max-w-3xl text-ink-soft">
        Leads that did not activate last quarter, highest chance first. The score is a logistic regression on what was known when each lead arrived
        (cross-validated AUC {data.model.auc}); the top 30% of leads held {Math.round(data.model.top30_share * 100)}% of activations.
        Calls go through a masked number, so the customer's real number is never shown.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <select className="field max-w-[220px]" value={seg} onChange={(e) => setSeg(e.target.value)} aria-label="Segment">
          <option value="">All segments</option>
          {Object.entries(SEG).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="field max-w-[320px]" value={reason} onChange={(e) => setReason(e.target.value)} aria-label="Drop reason">
          <option value="">All drop reasons</option>
          {data.reasons.map((r: string) => <option key={r}>{r}</option>)}
        </select>
      </div>
      <div className="mt-4 overflow-x-auto rounded-xl border border-rule bg-white">
        <table className="w-full min-w-[860px] text-left text-[15px]">
          <thead className="bg-paper-tint text-ink-soft"><tr>
            <th className="px-3 py-2 font-semibold">Business</th><th className="px-3 py-2 font-semibold">Why it stalled</th>
            <th className="px-3 py-2 font-semibold">Chance</th><th className="px-3 py-2 font-semibold">Next action</th><th className="px-3 py-2" />
          </tr></thead>
          <tbody className="divide-y divide-rule">
            {data.leads.map((l: any) => (
              <tr key={l.lead_id}>
                <td className="px-3 py-2"><p className="font-semibold">{l.business_name}</p><p className="text-[13px] text-ink-soft">{l.business_type}, {l.city}, {l.language}{l.has_gstin ? ', GSTIN' : ''}</p></td>
                <td className="px-3 py-2"><p>{l.drop_reason}</p><p className="text-[13px] text-ink-soft">Reached: {l.stage_reached}</p></td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2"><div className="h-2 w-20 rounded bg-rule"><div className="h-2 rounded bg-ledger" style={{ width: `${Math.min(100, l.score * 400)}%` }} /></div><span className="money">{Math.round(l.score * 100)}%</span></div>
                </td>
                <td className="px-3 py-2"><p className="font-semibold">{l.channel}</p><p className="text-[13px] text-ink-soft">{l.action}</p></td>
                <td className="px-3 py-2 text-right">
                  {calls[l.lead_id] ? <span className="whitespace-nowrap text-[14px] text-leaf">Dial {calls[l.lead_id]}</span> : <button className="btn-quiet whitespace-nowrap border border-ledger" onClick={() => call(l.lead_id)}>Call (masked)</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Reviews({ H }: { H: Record<string, string> }) {
  const [rows, setRows] = useState<any[] | null>(null)
  const load = () => api.get<any[]>('/api/backoffice/reviews', H).then(setRows)
  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  const [msg, setMsg] = useState<string | null>(null)
  const decide = async (id: string, decision: string) => {
    try { const r = await api.post<any>(`/api/backoffice/orders/${id}/review`, { decision, note: decision === 'approve' ? 'Original document checked' : undefined }, H); setMsg(r.message ?? null) } catch (e: any) { setMsg(e.message) }
    load()
  }
  if (!rows) return <Working label="Loading" />
  if (!rows.length) return <p className="text-ink-soft">Nothing waiting. Applicants the checks cannot clear on their own appear here.</p>
  return (
    <ul className="space-y-3">
      {rows.map((r) => (
        <li key={r.id} className="rounded-xl border border-rule bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[18px] font-bold">{r.business_name} {r.specimen && <span className="text-[14px] font-normal text-ink-soft">({r.specimen})</span>}</p>
            <span className={`rounded-pill px-3 py-0.5 text-[14px] font-semibold ${r.status === 'kyc_review' ? 'bg-kumkum-soft text-kumkum-dark' : 'bg-haldi-soft text-haldi-dark'}`}>{r.status === 'kyc_review' ? 'Needs review' : 'Owner fixing'}</span>
          </div>
          <ul className="mt-2 space-y-1">{r.failed_checks.map((c: any) => <li key={c.id} className="text-[15px]">• {c.message}</li>)}</ul>
          <p className="mt-1 text-[14px] text-ink-soft">Route: {r.route ?? 'gst'}
            {r.needs_two_reviewers && ' · needs two reviewers'}{r.pending_approval && ` · first approval by ${r.pending_approval}`}
            {r.cannot_approve?.length > 0 && ' · cannot be approved: change the order instead'}</p>
          {msg && <p className="mt-2 rounded-lg bg-ledger-soft px-3 py-2 text-[15px] text-ledger">{msg}</p>}
          {r.status === 'kyc_review' && (
            <div className="mt-3 flex gap-2">
              <button className="btn-primary min-h-[40px]" onClick={() => decide(r.id, 'approve')}>Approve</button>
              <button className="btn-quiet border border-rule" onClick={() => decide(r.id, 'ask_fix')}>Ask owner to re-upload</button>
              <button className="btn-quiet border border-rule text-kumkum" onClick={() => decide(r.id, 'reject')}>Reject</button>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}

function Orders({ H }: { H: Record<string, string> }) {
  const [rows, setRows] = useState<any[] | null>(null)
  useEffect(() => { api.get<any[]>('/api/backoffice/orders', H).then(setRows) }, []) // eslint-disable-line react-hooks/exhaustive-deps
  if (!rows) return <Working label="Loading" />
  return (
    <div className="overflow-x-auto rounded-xl border border-rule bg-white">
      <table className="w-full min-w-[720px] text-left text-[15px]">
        <thead className="bg-paper-tint text-ink-soft"><tr><th className="px-3 py-2">Business</th><th className="px-3 py-2">Status</th><th className="px-3 py-2">KYC</th><th className="px-3 py-2">Monthly</th><th className="px-3 py-2">Channel</th><th className="px-3 py-2">Created</th></tr></thead>
        <tbody className="divide-y divide-rule">
          {rows.map((o) => (
            <tr key={o.id}><td className="px-3 py-2 font-semibold">{o.business_name}</td><td className="px-3 py-2">{o.status.replace('_', ' ')}</td><td className="px-3 py-2">{o.kyc_outcome ?? ''}</td>
              <td className="money px-3 py-2">{rupees(o.monthly)}</td><td className="px-3 py-2">{o.partner_id ? `Partner ${o.partner_id}` : o.channel}, {o.language}</td><td className="px-3 py-2">{new Date(o.created_at).toLocaleString('en-IN')}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Metrics({ H }: { H: Record<string, string> }) {
  const [m, setM] = useState<any>(null)
  useEffect(() => { api.get<any>('/api/backoffice/metrics', H).then(setM) }, []) // eslint-disable-line react-hooks/exhaustive-deps
  if (!m) return <Working label="Loading" />
  const rows = [
    ['Lead-to-activation conversion', `${(m.baseline.conversion * 100).toFixed(1)}%`, `${m.targets.conversion * 100}%`],
    ['Days from lead to activation', `${m.baseline.days_to_activate}`, `${m.targets.days_to_activate} or fewer`],
    ['Cost per activation', rupees(m.baseline.cost_per_activation), `under ${rupees(m.targets.cost_per_activation)}`],
    ['Status-chase calls per customer', `${m.baseline.status_chases}`, `${m.targets.status_chases} or fewer`],
    ['6-month churn', `${(m.baseline.churn_6m * 100).toFixed(1)}%`, `${m.targets.churn_6m * 100}% or less`],
  ]
  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <div className="overflow-x-auto rounded-xl border border-rule bg-white">
        <table className="w-full text-left text-[15px]">
          <thead className="bg-paper-tint text-ink-soft"><tr><th className="px-3 py-2">Metric</th><th className="px-3 py-2">Apr to Jun 2026</th><th className="px-3 py-2">Pilot target</th></tr></thead>
          <tbody className="divide-y divide-rule">{rows.map((r) => <tr key={r[0]}><td className="px-3 py-2">{r[0]}</td><td className="money px-3 py-2">{r[1]}</td><td className="money px-3 py-2 text-leaf">{r[2]}</td></tr>)}</tbody>
        </table>
        <p className="px-3 py-2 text-[13px] text-ink-faint">Baseline computed live from smb_leads.csv ({m.baseline.leads.toLocaleString('en-IN')} leads, synthetic).</p>
      </div>
      <div className="rounded-xl border border-rule bg-white p-4">
        <h3 className="font-bold">This demo so far</h3>
        <dl className="mt-2 grid grid-cols-[1fr_auto] gap-y-1 text-[15px]">
          <dt>Advisor conversations</dt><dd className="money">{m.live.sessions}</dd>
          <dt>Got a quote</dt><dd className="money">{m.live.quoted}</dd>
          <dt>Orders</dt><dd className="money">{m.live.orders}</dd>
          <dt>Live</dt><dd className="money">{m.live.active}</dd>
          <dt>KYC cleared automatically</dt><dd className="money">{m.live.kyc_auto_verified_share === null ? '' : `${Math.round(m.live.kyc_auto_verified_share * 100)}%`}</dd>
          <dt>Minutes from chat to order (median)</dt><dd className="money">{m.live.median_minutes_chat_to_order ?? ''}</dd>
          <dt>Status-chase calls</dt><dd className="money">{m.live.status_chase_calls}</dd>
        </dl>
      </div>
    </div>
  )
}

function Model({ H }: { H: Record<string, string> }) {
  const [c, setC] = useState<any>(null)
  useEffect(() => { api.get<any>('/api/backoffice/model', H).then(setC) }, []) // eslint-disable-line react-hooks/exhaustive-deps
  if (!c) return <Working label="Training" />
  const max = Math.max(...c.lift.map((l: any) => l.activation_rate))
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="rounded-xl border border-rule bg-white p-4">
        <h3 className="font-bold">Activation rate by score decile</h3>
        <p className="text-[14px] text-ink-soft">Top decile activates at {Math.round(c.top_decile_rate * 100)}% against {Math.round(c.base_rate * 1000) / 10}% overall. AUC {c.auc}.</p>
        <div className="mt-4 flex h-44 items-end gap-2" role="img" aria-label="Activation rate by decile, highest first">
          {c.lift.map((l: any) => (
            <div key={l.decile} className="flex flex-1 flex-col items-center gap-1">
              <span className="text-[12px] text-ink-soft">{Math.round(l.activation_rate * 100)}%</span>
              <div className={`w-full rounded-t ${l.decile >= 8 ? 'bg-ledger' : 'bg-rule-strong'}`} style={{ height: `${(l.activation_rate / max) * 130}px` }} />
              <span className="text-[12px] text-ink-soft">{11 - l.decile}</span>
            </div>
          ))}
        </div>
        <p className="mt-1 text-center text-[12px] text-ink-faint">Decile, 1 = highest score</p>
      </div>
      <div className="rounded-xl border border-rule bg-white p-4">
        <h3 className="font-bold">Strongest signals</h3>
        <ul className="mt-2 space-y-1 text-[15px]">
          {c.drivers.map((d: any) => <li key={d.feature} className="flex justify-between gap-3"><span>{d.feature}</span><span className={`money ${d.weight > 0 ? 'text-leaf' : 'text-kumkum'}`}>{d.weight > 0 ? '+' : ''}{d.weight}</span></li>)}
        </ul>
        <p className="mt-3 text-[13px] text-ink-faint">{c.algorithm}.</p>
      </div>
    </div>
  )
}


function HelpQueue({ H }: { H: Record<string, string> }) {
  const [rows, setRows] = useState<any[] | null>(null)
  const load = () => api.get<any[]>('/api/backoffice/help', H).then(setRows)
  useEffect(() => { load(); const i = setInterval(load, 5000); return () => clearInterval(i) }, []) // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (id: string, status: string) => { await api.post(`/api/backoffice/help/${id}`, { status }, H); load() }
  if (!rows) return <Working label="Loading call-backs" />
  if (!rows.length) return <p className="text-ink-soft">No call-back requests yet. Owners ask from the home screen, the advisor, the tracker or My account.</p>
  return (
    <ul className="space-y-3">
      {rows.map((h) => (
        <li key={h.id} className="rounded-xl border border-rule bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-bold">{h.summary?.business_type ?? 'New owner'} · {h.summary?.city ?? ''}</p>
            <span className="chip">{h.status}{h.assignee ? ` · ${h.assignee}` : ''}</span>
          </div>
          <p className="text-[15px] text-ink-soft">Call {h.window} · language: <b>{h.language}</b> · from {h.source} · reason: {h.reason}</p>
          {h.summary?.products?.length > 0 && <p className="mt-1 text-[15px]">Quote: {h.summary.products.join(', ')}{h.summary.monthly ? ` · ${rupees(h.summary.monthly)} a month` : ''}</p>}
          {h.summary?.last_messages?.length > 0 && <p className="mt-1 text-[14px] italic text-ink-soft">"{h.summary.last_messages.at(-1)}"</p>}
          <div className="mt-3 flex gap-2">
            {h.status === 'open' && <button className="btn-primary min-h-[40px]" onClick={() => act(h.id, 'assigned')}>Take it</button>}
            {h.status === 'assigned' && <button className="btn-secondary min-h-[40px]" onClick={() => act(h.id, 'called')}>Called (masked number)</button>}
            {h.status !== 'resolved' && <button className="btn-quiet border border-rule" onClick={() => act(h.id, 'resolved')}>Resolved</button>}
          </div>
        </li>
      ))}
    </ul>
  )
}
