import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card, ErrorNote, Shell, Split, Working } from '../components/ui'
import { api, paise, rememberOrder, rupees, shareLink, type Milestone, type OrderView } from '../lib/api'
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
  const [access, setAccess] = useState<{ at: string; who: string; action: string; what: string }[]>([])

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
  useEffect(() => { api.get<{ entries: any[] }>(`/api/orders/${id}/access-log?key=${key}`).then((r) => setAccess(r.entries)).catch(() => {}) }, [id, key, tick])

  if (!order) return <Shell title={t('track_title')} width="wide" step="track"><Working label="…" />{err && <ErrorNote msg={err} />}</Shell>

  // a review is our job, not the owner's: say so, and never colour it as "needs you"
  const statusWord = (m: Milestone) => (m.status === 'done' ? (m.kind === 'product' ? t('live') : t('done'))
    : m.kind === 'kyc_review' ? t('outcome_review') : t(m.status))
  const dotFor = (m: Milestone) => DOT[m.kind === 'kyc_review' ? 'in_progress' : m.status] ?? DOT.pending
  const ownerAsk = order.approvals?.filter((a) => a.kind === 'owner').slice(-1)[0]
  const ownerWaiting = ownerAsk && ownerAsk.status !== 'approved'
  const next = order.status === 'kyc_verified' && ownerWaiting ? null
    : order.status === 'kyc_verified' ? { label: t('pay_title'), to: `/order/${id}/pay?key=${key}` }
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

  // the one next thing to do, and help: first thing on a phone, beside the timeline on a laptop
  const summary = (
    <Card>
    <div className="flex items-baseline justify-between gap-3">
      <p className="text-[20px] font-bold">{order.business_name}</p>
      <p className="money shrink-0 whitespace-nowrap text-[18px]">{rupees(order.monthly)}<span className="text-[14px] font-normal text-ink-soft"> {t('a_month')}</span></p>
    </div>
    <p className="text-[15px] text-ink-soft">{t('no_chasing')}</p>
    {next && <button className="btn-primary mt-4 w-full" onClick={() => nav(next.to)}>{next.label}</button>}
    <div className="mt-3 flex flex-wrap gap-2 lg:flex-col">
      <button className="btn-secondary flex-1 basis-40 whitespace-nowrap lg:flex-none lg:basis-auto" onClick={() => nav(`/help?order=${id}&key=${key}&source=tracker`)}>{t('talk_person')}</button>
      <button className="btn-quiet flex-1 basis-40 whitespace-nowrap border border-rule lg:flex-none lg:basis-auto" onClick={() => nav('/verify')}>{t('nav_check')}</button>
      {order.status === 'scheduled' && (
        <button className="btn-quiet w-full border border-dashed border-rule-strong" onClick={advance}>Demo: complete next step</button>
      )}
    </div>
    </Card>
  )

  return (
    <Shell title={t('track_title')} width="wide" step="track">
      <Split aside={
        <>
          <div className="hidden lg:block">{summary}</div>
          <section className="card p-5">
            <h2 className="section-title">{t('your_data')}</h2>
            <ul className="mt-2 divide-y divide-rule">
              {Object.entries(order.consent ?? {}).map(([p, c]) => (
                <li key={p} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-semibold">{t(`p_${p}`)}</p>
                    <p className="text-[14px] text-ink-soft">{c.granted ? `${t('given')} ${fmt(c.since)}` : c.withdrawn_at ? `${t('withdrawn')} ${fmt(c.withdrawn_at)}` : t('optional')}</p>
                  </div>
                  {c.granted && <button className="btn-quiet" onClick={() => withdraw(p)}>{t('withdraw')}</button>}
                </li>
              ))}
            </ul>
            <WhoOpened entries={access} fmt={fmt} />
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-quiet border border-rule" onClick={download}>{t('download_data')}</button>
              <button className="btn-quiet border border-rule text-kumkum" onClick={erase}>{t('erase_data')}</button>
            </div>
          </section>
        </>
      }>
      <div className="mb-4 lg:hidden">{summary}</div>
      {order.customer && (
        <section className="mb-4 rounded-2xl border border-leaf/30 bg-leaf-soft p-4">
          <p className="text-[18px] font-bold text-leaf">{t('welcome_back', { year: order.customer.since })}</p>
          <p className="mt-1 text-[15px]">{t('welcome_back_sub')}</p>
          <p className="mt-2 text-[14px] text-ink-soft">{order.customer.lines.map((l) => `${l.masked} (${l.plan})`).join(' · ')}</p>
        </section>
      )}
      {ownerWaiting && ownerAsk && (
        <section className="mb-4 rounded-2xl border border-haldi/50 bg-haldi-soft p-4">
          <p className="font-bold text-haldi-dark">{ownerAsk.status === 'declined' ? order.events.filter((e) => e.kind === 'owner_declined').slice(-1)[0]?.title : t('waiting_owner', { phone: ownerAsk.phone_masked })}</p>
          {ownerAsk.status === 'pending' && <p className="mt-1 text-[15px]">{t('owner_will_approve')}</p>}
          {ownerAsk.status === 'pending' && (
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-secondary" onClick={() => shareLink(ownerAsk.link, `${order.business_name}: ${t('approve_owner')}`)}>{t('share_link')}</button>
              <button className="btn-quiet border border-dashed border-rule-strong" onClick={() => nav(ownerAsk.link)}>Demo: open the owner's link</button>
            </div>
          )}
        </section>
      )}

      <section className="card p-5 lg:p-6">
      <h2 className="section-title mb-4">{t('status_now')}</h2>
      <ol className="relative space-y-0">
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
      </section>

      {order.events.filter((e) => e.kind === 'activation_hold' && !order.events.some((x) => x.kind === 'product_active' && x.product_id === e.product_id)).map((e) => (
        <p key={e.id} className="mt-3 rounded-xl bg-haldi-soft px-4 py-3 text-[15px] text-haldi-dark"><span className="font-semibold">{t('on_hold')}:</span> {e.title}</p>
      ))}
      <SimUsers orderId={id!} orderKey={key!} lines={order.bundle.lines} tick={tick} />
      {order.milestones.some((m) => m.kind === 'product' && m.status === 'done') && <Account orderId={id!} orderKey={key!} tick={tick} />}

      <ErrorNote msg={err} />
      </Split>

      {toast && (
        <div className="fixed inset-x-4 top-20 z-40 mx-auto max-w-[440px] animate-rise rounded-2xl bg-ink px-4 py-3 text-white shadow-lift lg:left-auto lg:right-8 lg:top-24" role="status">
          <p className="text-[13px] opacity-70">Accel Business (also sent on WhatsApp)</p>
          <p className="font-semibold">{toast}</p>
        </div>
      )}
    </Shell>
  )
}

const WHO: Record<string, string> = { 'Automatic KYC check': 'acc_auto', Reviewer: 'acc_reviewer', 'Installation team': 'acc_install', 'Order updates': 'acc_updates' }
const ACTION: Record<string, string> = { read: 'acc_read', reviewed: 'acc_reviewed', 'was refused': 'acc_refused' }

/** Who opened my documents: every look by anyone but the owner, with its reason, from the audit log. */
function WhoOpened({ entries, fmt }: { entries: { at: string; who: string; action: string; what: string }[]; fmt: (d?: string | null) => string }) {
  const { t } = useLang()
  const groups = new Map<string, { who: string; action: string; what: string; n: number; last: string }>()
  for (const e of entries) {
    if (e.who === 'You' || e.who === 'System' || !ACTION[e.action]) continue
    const k = `${e.who}|${e.action}|${e.what}`
    const g = groups.get(k)
    if (g) g.n += 1
    else groups.set(k, { ...e, n: 1, last: e.at })
  }
  if (!groups.size) return null
  const what = (w: string) => (w === 'identifier' ? t('acc_ids') : w === 'order' ? '' : t('doc_' + w.replace(/ /g, '_')))
  return (
    <div className="mt-4 rounded-xl border border-rule bg-white px-4 py-3">
      <p className="font-semibold">{t('who_opened')}</p>
      <p className="text-[14px] text-ink-soft">{t('who_opened_sub')}</p>
      <ul className="mt-2 space-y-1 text-[14px]">
        {[...groups.values()].map((g) => (
          <li key={`${g.who}${g.action}${g.what}`} className="flex justify-between gap-3">
            <span className="min-w-0 truncate">{t(WHO[g.who] ?? g.who)} · {t(ACTION[g.action])}{what(g.what) ? ` · ${what(g.what)}` : ''}</span>
            <span className="shrink-0 text-ink-soft">{g.n > 1 ? `×${g.n}, ` : ''}{fmt(g.last)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
