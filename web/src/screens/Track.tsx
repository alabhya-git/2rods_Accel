import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ErrorNote, Shell, Working } from '../components/ui'
import { api, paise, rememberOrder, rupees, type Milestone, type OrderView } from '../lib/api'
import { Account, SimUsers } from '../components/AfterSale'
import { useLang } from '../lib/i18n'

const DOT: Record<string, string> = { done: 'bg-leaf border-leaf', in_progress: 'bg-haldi border-haldi', attention: 'bg-kumkum border-kumkum', pending: 'bg-white border-rule-strong' }

export default function Track() {
  const { id } = useParams()
  const key = new URLSearchParams(location.search).get('key')
  const { t, bcp } = useLang()
  const [order, setOrder] = useState<OrderView | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const nav = useNavigate()
  const [tick, setTick] = useState(0)

  const load = useCallback(() => api.get<OrderView>(`/api/orders/${id}?key=${key}`).then(setOrder).catch((e) => setErr(e.message)), [id, key])

  useEffect(() => {
    if (id && key) rememberOrder(id, key)  // any order opened here shows up in My orders
    load()
    const es = new EventSource(`/api/orders/${id}/stream?key=${key}`)
    es.addEventListener('order', (e) => {
      const ev = JSON.parse((e as MessageEvent).data)
      setToast(ev.title)
      setTimeout(() => setToast(null), 3500)
      load()
      setTick((n) => n + 1)
    })
    // the stream is a nicety: a quiet poll keeps the tracker right if a proxy holds events back
    const poll = setInterval(() => { if (document.visibilityState === 'visible') { load(); setTick((n) => n + 1) } }, 10000)
    return () => { es.close(); clearInterval(poll) }
  }, [id, key, load])

  if (!order) return <Shell title={t('track_title')}><Working label="…" />{err && <ErrorNote msg={err} />}</Shell>

  // a review is our job, not the owner's: say so, and never colour it as "needs you"
  const statusWord = (m: Milestone) => (m.status === 'done' ? (m.kind === 'product' ? t('live') : t('done'))
    : m.kind === 'kyc_review' ? t('outcome_review') : t(m.status))
  const dotFor = (m: Milestone) => DOT[m.kind === 'kyc_review' ? 'in_progress' : m.status] ?? DOT.pending
  const next = order.status === 'kyc_verified' ? { label: t('pay_title'), to: `/order/${id}/pay?key=${key}` }
    : order.status === 'paid' ? { label: t('choose_slot'), to: `/order/${id}/pay?key=${key}` }
    : order.status === 'kyc_fix' ? { label: t('how_to_fix'), to: `/order/${id}/kyc?key=${key}` }
    : order.status === 'draft' ? { label: t('continue'), to: `/order/${id}/consent?key=${key}` }
    : order.status === 'consented' || order.status === 'kyc_pending' ? { label: t('kyc_title'), to: `/order/${id}/kyc?key=${key}` } : null
  const fmt = (d?: string | null) => (d ? new Date(d.length === 10 ? d + 'T00:00:00' : d).toLocaleDateString(bcp, { day: 'numeric', month: 'short' }) : '')
  const advance = async () => { try { await api.post(`/api/orders/${id}/advance?key=${key}`); await load(); setTick((n) => n + 1) } catch (e: any) { setErr(e.message) } }
  const withdraw = async (p: string) => { await api.post(`/api/orders/${id}/consent/${p}/withdraw?key=${key}`); load() }
  const download = async () => {
    const data = await api.get(`/api/orders/${id}/my-data?key=${key}`)
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
    a.download = `accel-my-data-${id}.json`
    a.click()
  }
  const erase = async () => { if (confirm(t('erase_confirm'))) { await api.post(`/api/orders/${id}/erase?key=${key}`); load() } }

  return (
    <Shell title={t('track_title')}>
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[20px] font-bold">{order.business_name}</p>
        <p className="money shrink-0 whitespace-nowrap text-[18px]">{rupees(order.monthly)}<span className="text-[14px] font-normal text-ink-soft"> {t('a_month')}</span></p>
      </div>
      <p className="text-[15px] text-ink-soft">{t('no_chasing')}</p>

      <ol className="relative mt-5 space-y-0">
        {order.milestones.map((m, i) => (
          <li key={i} className="relative flex gap-4 pb-5 pl-1">
            {i < order.milestones.length - 1 && <span className="absolute left-[11px] top-6 h-full w-[2px] bg-rule" aria-hidden="true" />}
            <span className={`relative mt-1 h-[22px] w-[22px] shrink-0 rounded-full border-[3px] ${dotFor(m)}`} aria-hidden="true" />
            <div className="min-w-0 flex-1">
              <p className={`font-semibold ${m.status === 'pending' ? 'text-ink-soft' : ''}`}>{m.title}</p>
              <p className="text-[14px] text-ink-soft">
                {statusWord(m)}
                {m.at ? `, ${fmt(m.at)}` : m.eta ? `, ${t('expected', { date: fmt(m.eta) })}` : ''}
              </p>
            </div>
          </li>
        ))}
      </ol>

      {next && <button className="btn-primary mb-3 w-full" onClick={() => nav(next.to)}>{next.label}</button>}
      <div className="mt-2 flex flex-wrap gap-2">
        <button className="btn-secondary" onClick={() => nav(`/help?order=${id}&key=${key}&source=tracker`)}>{t('talk_person')}</button>
        {order.status === 'scheduled' && (
          <button className="btn-quiet border border-dashed border-rule-strong" onClick={advance}>Demo: complete next step</button>
        )}
      </div>
      {order.events.filter((e) => e.kind === 'activation_hold' && !order.events.some((x) => x.kind === 'product_active' && x.product_id === e.product_id)).map((e) => (
        <p key={e.id} className="mt-3 rounded-lg bg-haldi-soft px-4 py-3 text-[15px] text-haldi-dark"><span className="font-semibold">{t('on_hold')}:</span> {e.title}</p>
      ))}
      <SimUsers orderId={id!} orderKey={key!} lines={order.bundle.lines} tick={tick} />
      {order.milestones.some((m) => m.kind === 'product' && m.status === 'done') && <Account orderId={id!} orderKey={key!} tick={tick} />}

      <section className="mt-8">
        <h2 className="text-[19px] font-bold">{t('your_data')}</h2>
        <ul className="mt-3 divide-y divide-rule rounded-xl border border-rule bg-white">
          {Object.entries(order.consent ?? {}).map(([p, c]) => (
            <li key={p} className="flex items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="font-semibold">{t(`p_${p}`)}</p>
                <p className="text-[14px] text-ink-soft">{c.granted ? `${t('given')} ${fmt(c.since)}` : c.withdrawn_at ? `${t('withdrawn')} ${fmt(c.withdrawn_at)}` : t('optional')}</p>
              </div>
              {c.granted && <button className="btn-quiet" onClick={() => withdraw(p)}>{t('withdraw')}</button>}
            </li>
          ))}
        </ul>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="btn-quiet border border-rule" onClick={download}>{t('download_data')}</button>
          <button className="btn-quiet border border-rule text-kumkum" onClick={erase}>{t('erase_data')}</button>
        </div>
      </section>
      <ErrorNote msg={err} />

      {toast && (
        <div className="fixed inset-x-4 top-20 z-40 mx-auto max-w-[440px] rounded-xl bg-ink px-4 py-3 text-white shadow-lg" role="status">
          <p className="text-[13px] opacity-70">Accel Business (also sent on WhatsApp)</p>
          <p className="font-semibold">{toast}</p>
        </div>
      )}
    </Shell>
  )
}
