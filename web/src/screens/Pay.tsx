import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card, ErrorNote, Hint, Shell, Split, Stamp, StickyBar, Working } from '../components/ui'
import { api, paise, rupees, type OrderView, type Schedule } from '../lib/api'
import { useLang } from '../lib/i18n'

export default function Pay() {
  const { id } = useParams()
  const key = new URLSearchParams(location.search).get('key')
  const { t, bcp } = useLang()
  const nav = useNavigate()
  const [order, setOrder] = useState<OrderView | null>(null)
  const [upi, setUpi] = useState('')
  const [paid, setPaid] = useState<any>(null)
  const [days, setDays] = useState<{ date: string; slots: string[] }[]>([])
  const [day, setDay] = useState<string | null>(null)
  const [slot, setSlot] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.get<OrderView>(`/api/orders/${id}?key=${key}`).then((o) => { setOrder(o); if (o.payment) setPaid(o.payment) })
    api.get<{ days: any[] }>(`/api/orders/${id}/slots?key=${key}`).then((r) => { setDays(r.days); setDay(r.days[0]?.date) })
  }, [id, key])

  if (!order) return <Shell title={t('pay_title')} width="wide" step="pay"><Working label="…" /></Shell>
  const b = order.bundle
  const s = (b as any).schedule as Schedule  // the same schedule the quote showed and the charge uses
  // staff prepared it: the owner's e-sign comes before any charge
  const owner = order.approvals?.filter((a) => a.kind === 'owner').slice(-1)[0]
  const waiting = owner && owner.status !== 'approved'

  const pay = async () => {
    setErr(null)
    try { setPaid(await api.post(`/api/orders/${id}/pay?key=${key}`, { method: 'upi_autopay', upi_id: upi })) } catch (e: any) { setErr(e.message) }
  }
  const book = async () => {
    try {
      await api.post(`/api/orders/${id}/schedule?key=${key}`, { slot: `${day} ${slot}` })
      nav(`/track/${id}?key=${key}`)
    } catch (e: any) { setErr(e.message) }
  }
  const fmt = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString(bcp, { weekday: 'short', day: 'numeric', month: 'short' })
  const payMissing = waiting ? t('waiting_owner', { phone: owner!.phone_masked }) : !upi.includes('@') ? t('need_upi') : null

  return (
    <Shell title={t('pay_title')} width="wide" step="pay">
      <Split aside={
        <>
          <Card title={t('order_summary')}>
            <dl className="space-y-2 text-[16px]">
              <div className="flex justify-between gap-3"><dt className="min-w-0 truncate">{b.name}, {t('a_month')}</dt><dd className="money">{rupees(b.monthly)}</dd></div>
              <div className="flex justify-between gap-3"><dt>GST 18%</dt><dd className="money">{paise(s.rows[0].gst)}</dd></div>
              {s.rows[0].setup > 0 && <div className="flex justify-between gap-3"><dt>{s.setup_emi ? t('setup_instalments', { n: s.emi_months }) : t('setup_once')}</dt><dd className="money">{paise(s.rows[0].setup)}</dd></div>}
            </dl>
            <div className="mt-4 flex items-end justify-between gap-3 border-t border-rule pt-4">
              <span className="font-bold">{t('due_today')}</span>
              <span className="money text-[30px] leading-none text-kumkum">{paise(s.due_today)}</span>
            </div>
            <p className="mt-2 flex justify-between text-[15px] text-ink-soft"><span>{t('all_in')}</span><span className="money">{paise(s.monthly)}</span></p>
          </Card>
          <p className="rounded-xl bg-white px-3 py-2 text-[14px] text-ink-soft ring-1 ring-rule">{t('never_ask')}</p>
        </>
      }>
        {!paid ? (
          <Card title={t('pay_autopay')}>
            <label className="block">
              <span className="label">{t('upi_id')}</span>
              <input className="field" value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="name@bank" autoComplete="off" />
            </label>
            <p className="mt-2 text-[14px] text-ink-soft">Autopay pays each month's bill automatically. You can cancel it from your UPI app.</p>
            {waiting && <p className="mt-3 rounded-xl bg-haldi-soft px-3 py-2 font-semibold text-haldi-dark">{t('waiting_owner', { phone: owner!.phone_masked })}</p>}
            <div className="mt-4 space-y-2">
              {payMissing && !waiting && <Hint>{payMissing}</Hint>}
              <button className="btn-primary w-full" onClick={pay} disabled={!!payMissing}>{t('pay_autopay')}</button>
            </div>
          </Card>
        ) : (
          <Card>
            <div className="flex items-center justify-between gap-3"><Stamp kind="ok">{t('paid')}</Stamp><span className="text-[14px] text-ink-soft">{paid.reference}</span></div>
            <h2 className="section-title mt-6">{t('choose_slot')}</h2>
            <div className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:flex-wrap lg:overflow-visible">
              {days.map((d) => (
                <button key={d.date} onClick={() => { setDay(d.date); setSlot(null) }} aria-pressed={day === d.date} className="choice shrink-0 !py-2 text-[15px]">{fmt(d.date)}</button>
              ))}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {days.find((d) => d.date === day)?.slots.map((sl) => (
                <button key={sl} onClick={() => setSlot(sl)} aria-pressed={slot === sl} className="choice !px-2 !py-2 text-center text-[15px]">{sl}</button>
              ))}
            </div>
          </Card>
        )}
        <ErrorNote msg={err} />
        {paid && (
          <StickyBar hint={!slot && <Hint>{t('need_slot')}</Hint>}>
            <button className="btn-primary w-full" onClick={book} disabled={!slot}>{t('book_slot')}</button>
          </StickyBar>
        )}
      </Split>
    </Shell>
  )
}
