import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, paise, rupees, type Line } from '../lib/api'
import { useLang } from '../lib/i18n'
import { ErrorNote, Stamp } from './ui'

type SimView = {
  needed: number; verified: number; users: { id: string; product_id: string; status: string; invite: string; phone_masked: string; on_file: boolean }[]
  existing: { id: string; masked: string; plan: string }[]
}

/** Business SIMs: each user verifies through their own link before their line goes live (DoT, 2023). */
export function SimUsers({ orderId, orderKey, lines, tick }: { orderId: string; orderKey: string; lines: Line[]; tick: number }) {
  const { t } = useLang()
  const [view, setView] = useState<SimView | null>(null)
  const [rows, setRows] = useState<{ name: string; phone: string }[]>([])
  const [err, setErr] = useState<string | null>(null)
  const [pick, setPick] = useState<string[]>([])
  const hasSims = lines.some((l) => l.product_id === 'P07' || l.product_id === 'P08')

  useEffect(() => {
    if (!hasSims) return
    api.get<SimView>(`/api/orders/${orderId}/sim-users?key=${orderKey}`).then((v) => {
      setView(v)
      setRows(Array.from({ length: Math.max(0, v.needed - v.users.length) }, () => ({ name: '', phone: '' })))
      setPick(v.existing.slice(0, Math.max(0, v.needed - v.users.length)).map((l) => l.id))
    }).catch(() => {})
  }, [orderId, orderKey, hasSims, tick])

  if (!hasSims || !view) return null
  const send = async () => {
    setErr(null)
    try {
      const v = await api.post<SimView>(`/api/orders/${orderId}/sim-users?key=${orderKey}`, { users: rows.filter((r) => r.name && r.phone) })
      setView(v)
      setRows([])
    } catch (e: any) { setErr(e.message) }
  }
  // an existing Accel customer's numbers: no new SIM, KYC already on file, live at once
  const moveMine = async () => {
    setErr(null)
    try {
      const v = await api.post<SimView>(`/api/orders/${orderId}/sim-users/existing?key=${orderKey}`, { line_ids: pick })
      setView(v)
      setRows(Array.from({ length: Math.max(0, v.needed - v.users.length) }, () => ({ name: '', phone: '' })))
    } catch (e: any) { setErr(e.message) }
  }
  const room = view.needed - view.users.length
  return (
    <section className="card mt-6 p-5">
      <div className="flex items-center justify-between"><h2 className="text-[18px] font-bold">{t('sim_title')}</h2><span className="text-ink-soft">{view.verified}/{view.needed}</span></div>
      <p className="mt-1 text-[15px] text-ink-soft">{t('sim_intro')}</p>
      <ul className="mt-3 space-y-2">
        {view.users.map((u) => (
          <li key={u.id} className="flex items-center justify-between gap-3">
            <span>{u.phone_masked}</span>
            {u.status === 'verified' ? <Stamp kind="ok" animate={false}>{t(u.on_file ? 'on_file' : 'sim_verified')}</Stamp>
              : <a className="text-ledger underline" href={u.invite} target="_blank" rel="noreferrer">{t('sim_waiting')}</a>}
          </li>
        ))}
      </ul>
      {view.existing.length > 0 && room > 0 && (
        <div className="mt-3 rounded-xl border border-leaf/30 bg-leaf-soft p-3">
          <p className="font-semibold text-leaf">{t('use_my_numbers')}</p>
          <p className="text-[14px]">{t('use_my_numbers_sub')}</p>
          <ul className="mt-2 space-y-1">
            {view.existing.map((l) => (
              <li key={l.id}>
                <label className="flex items-center gap-3 text-[15px]">
                  <input type="checkbox" className="h-5 w-5" checked={pick.includes(l.id)}
                    disabled={!pick.includes(l.id) && pick.length >= room}
                    onChange={(e) => setPick(e.target.checked ? [...pick, l.id] : pick.filter((x) => x !== l.id))} />
                  <span>{l.masked}</span><span className="text-ink-soft">{l.plan}</span>
                </label>
              </li>
            ))}
          </ul>
          <button className="btn-primary mt-2 w-full" onClick={moveMine} disabled={pick.length === 0}>{t('use_my_numbers')}</button>
        </div>
      )}
      {rows.length > 0 && (
        <div className="mt-3 space-y-2">
          {rows.map((r, i) => (
            <div key={i} className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <input className="field w-full min-w-0" placeholder={t('sim_name')} value={r.name} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
              <input className="field w-full min-w-0" inputMode="tel" placeholder="98XXXXXXXX" value={r.phone} onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, phone: e.target.value } : x)))} />
            </div>
          ))}
          <button className="btn-secondary w-full" onClick={send} disabled={!rows.some((r) => r.name && r.phone.replace(/\D/g, '').length >= 10)}>{t('sim_invite')}</button>
        </div>
      )}
      <ErrorNote msg={err} />
    </section>
  )
}

type AccountView = {
  services: { product_id: string; name: string; qty: number; monthly: number; status: string }[]
  bill: { next_debit_paise: number | null; monthly_paise: number; monthly_after_emi_paise: number; emi_months_left: number; autopay: boolean; lines: { name: string; qty: number; monthly: number }[] }
  help: { id: string; status: string; window: string; call_code?: string }[]
  setup_tasks: { product_id: string; name: string; minutes: number; live: boolean; done: boolean; days_live: number | null }[]
}

/** After go-live the tracker becomes My account: one bill, one help button, what is left to set up. */
export function Account({ orderId, orderKey, tick }: { orderId: string; orderKey: string; tick: number }) {
  const { t } = useLang()
  const nav = useNavigate()
  const [a, setA] = useState<AccountView | null>(null)
  useEffect(() => { api.get<AccountView>(`/api/orders/${orderId}/account?key=${orderKey}`).then(setA).catch(() => {}) }, [orderId, orderKey, tick])
  if (!a) return null
  const markDone = async (pid: string) => {
    const r = await api.post<{ setup_tasks: AccountView['setup_tasks'] }>(`/api/orders/${orderId}/setup/${pid}?key=${orderKey}`)
    setA({ ...a, setup_tasks: r.setup_tasks })
  }
  return (
    <section className="card mt-6 p-5">
      <h2 className="text-[19px] font-bold">{t('account_title')}</h2>
      <p className="text-[15px] font-semibold text-leaf">{t('one_bill')}</p>
      <div className="khata mt-3">
        {a.bill.lines.map((l) => (
          <div key={l.name} className="row justify-between gap-3"><span className="truncate">{l.name}{l.qty > 1 ? ` ×${l.qty}` : ''}</span><span className="money">{rupees(l.monthly)}</span></div>
        ))}
        <div className="row justify-between border-t-2 border-ink font-bold"><span>{t('all_in')}</span><span className="money">{paise(a.bill.monthly_paise)}</span></div>
        {a.bill.next_debit_paise !== null && <div className="row justify-between text-[15px]"><span>{t('next_debit')}</span><span className="money">{paise(a.bill.next_debit_paise)}</span></div>}
      </div>
      <ul className="mt-3 space-y-1">
        {a.services.map((s) => <li key={s.product_id} className="flex justify-between text-[15px]"><span>{s.name}</span><span className={s.status === 'live' ? 'text-leaf' : 'text-ink-soft'}>{s.status === 'live' ? t('live') : t('in_progress')}</span></li>)}
      </ul>
      {a.setup_tasks.length > 0 && (
        <>
          <h3 className="mt-4 font-semibold">{t('setup_tasks')}</h3>
          <ul className="mt-2 space-y-3">
            {a.setup_tasks.map((s) => (
              <li key={s.product_id} className="rounded-xl border border-rule p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">{t('setup_' + s.product_id)}</p>
                    <p className="text-[13px] text-ink-soft">{s.name} · {t('setup_minutes', { n: s.minutes })}</p>
                  </div>
                  {s.done ? <Stamp kind="ok" animate={false}>{t('done')}</Stamp> : !s.live && <span className="shrink-0 text-[14px] text-ink-soft">{t('pending')}</span>}
                </div>
                {s.live && !s.done && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button className="btn-secondary min-h-[40px] text-[15px]" onClick={() => markDone(s.product_id)}>{t('setup_done_btn')}</button>
                    <button className="btn-quiet min-h-[40px] border border-rule text-[15px]" onClick={() => nav(`/help?order=${orderId}&key=${orderKey}&source=account&reason=setup`)}>{t('setup_with_me')}</button>
                  </div>
                )}
              </li>
            ))}
          </ul>
          {a.setup_tasks.some((s) => s.live && !s.done) && <p className="mt-2 text-[14px] text-ink-soft">{t('setup_nudge')}</p>}
        </>
      )}
      <button className="btn-primary mt-4 w-full" onClick={() => nav(`/help?order=${orderId}&key=${orderKey}&source=account&reason=not_working`)}>{t('get_help')}</button>
      {a.help.map((h) => (
        <p key={h.id} className="mt-2 flex justify-between text-[14px] text-ink-soft">
          <span>{t('talk_person')}{h.call_code ? ` · ${h.call_code}` : ''}</span>
          <span className={h.status === 'resolved' || h.status === 'called' ? 'text-leaf' : ''}>
            {t(h.status === 'open' ? 'pending' : h.status === 'assigned' ? 'in_progress' : 'done')}
          </span>
        </p>
      ))}
    </section>
  )
}
