import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, paise, rupees, type Line } from '../lib/api'
import { useLang } from '../lib/i18n'
import { ErrorNote, Stamp } from './ui'

type SimView = { needed: number; verified: number; users: { id: string; product_id: string; status: string; invite: string; phone_masked: string }[] }

/** Business SIMs: each user verifies through their own link before their line goes live (DoT, 2023). */
export function SimUsers({ orderId, orderKey, lines, tick }: { orderId: string; orderKey: string; lines: Line[]; tick: number }) {
  const { t } = useLang()
  const [view, setView] = useState<SimView | null>(null)
  const [rows, setRows] = useState<{ name: string; phone: string }[]>([])
  const [err, setErr] = useState<string | null>(null)
  const hasSims = lines.some((l) => l.product_id === 'P07' || l.product_id === 'P08')

  useEffect(() => {
    if (!hasSims) return
    api.get<SimView>(`/api/orders/${orderId}/sim-users?key=${orderKey}`).then((v) => {
      setView(v)
      setRows(Array.from({ length: Math.max(0, v.needed - v.users.length) }, () => ({ name: '', phone: '' })))
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
  return (
    <section className="mt-6 rounded-xl border border-rule bg-white p-4">
      <div className="flex items-center justify-between"><h2 className="text-[18px] font-bold">{t('sim_title')}</h2><span className="text-ink-soft">{view.verified}/{view.needed}</span></div>
      <p className="mt-1 text-[15px] text-ink-soft">{t('sim_intro')}</p>
      <ul className="mt-3 space-y-2">
        {view.users.map((u) => (
          <li key={u.id} className="flex items-center justify-between gap-3">
            <span>{u.phone_masked}</span>
            {u.status === 'verified' ? <Stamp kind="ok" animate={false}>{t('sim_verified')}</Stamp>
              : <a className="text-ledger underline" href={u.invite} target="_blank" rel="noreferrer">{t('sim_waiting')}</a>}
          </li>
        ))}
      </ul>
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
  help: { id: string; status: string; window: string }[]; setup_tasks: { product_id: string; task: string }[]
}

/** After go-live the tracker becomes My account: one bill, one help button, what is left to set up. */
export function Account({ orderId, orderKey, tick }: { orderId: string; orderKey: string; tick: number }) {
  const { t } = useLang()
  const nav = useNavigate()
  const [a, setA] = useState<AccountView | null>(null)
  useEffect(() => { api.get<AccountView>(`/api/orders/${orderId}/account?key=${orderKey}`).then(setA).catch(() => {}) }, [orderId, orderKey, tick])
  if (!a) return null
  return (
    <section className="mt-6 rounded-xl border-2 border-ledger bg-white p-4">
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
          <ul className="mt-1 list-disc pl-5 text-[15px]">{a.setup_tasks.map((s) => <li key={s.product_id}>{s.task}</li>)}</ul>
        </>
      )}
      <button className="btn-primary mt-4 w-full" onClick={() => nav(`/help?order=${orderId}&key=${orderKey}&source=account&reason=not_working`)}>{t('get_help')}</button>
      {a.help.map((h) => (
        <p key={h.id} className="mt-2 flex justify-between text-[14px] text-ink-soft">
          <span>{t('talk_person')}</span>
          <span className={h.status === 'resolved' || h.status === 'called' ? 'text-leaf' : ''}>
            {t(h.status === 'open' ? 'pending' : h.status === 'assigned' ? 'in_progress' : 'done')}
          </span>
        </p>
      ))}
    </section>
  )
}
