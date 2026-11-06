import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ErrorNote, Shell, Stamp, StickyBar, Working } from '../components/ui'
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

  if (!order) return <Shell title={t('pay_title')}><Working label="…" /></Shell>
  const b = order.bundle
  const s = (b as any).schedule as Schedule  // the same schedule the quote showed and the charge uses

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

  return (
    <Shell title={t('pay_title')}>
      <section className="khata">
        <div className="row justify-between"><span>{b.name}, {t('a_month')}</span><span className="money">{rupees(b.monthly)}</span></div>
        <div className="row justify-between"><span>GST 18%</span><span className="money">{paise(s.rows[0].gst)}</span></div>
        {s.rows[0].setup > 0 && <div className="row justify-between"><span>{s.setup_emi ? t('setup_instalments', { n: s.emi_months }) : t('setup_once')}</span><span className="money">{paise(s.rows[0].setup)}</span></div>}
        <div className="row justify-between border-t-2 border-ink font-bold"><span>{t('due_today')}</span><span className="money text-[24px] text-kumkum">{paise(s.due_today)}</span></div>
        <div className="row justify-between text-[15px] text-ink-soft"><span>{t('all_in')}</span><span className="money">{paise(s.monthly)}</span></div>
      </section>

      {!paid ? (
        <section className="mt-5">
          <label className="block">
            <span className="mb-1 block font-semibold">{t('upi_id')}</span>
            <input className="field" value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="name@bank" autoComplete="off" />
          </label>
          <p className="mt-2 text-[14px] text-ink-soft">Autopay pays each month's bill automatically. You can cancel it from your UPI app.</p>
          <button className="btn-primary mt-4 w-full" onClick={pay} disabled={!upi.includes('@')}>{t('pay_autopay')}</button>
        </section>
      ) : (
        <section className="mt-5">
          <div className="flex items-center justify-between"><Stamp kind="ok">{t('paid')}</Stamp><span className="text-[14px] text-ink-soft">{paid.reference}</span></div>
          <h2 className="mt-6 text-[19px] font-bold">{t('choose_slot')}</h2>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {days.map((d) => (
              <button key={d.date} onClick={() => { setDay(d.date); setSlot(null) }} aria-pressed={day === d.date}
                className={`shrink-0 rounded-xl border-2 px-3 py-2 text-[15px] ${day === d.date ? 'border-ledger bg-ledger text-white' : 'border-rule bg-white'}`}>{fmt(d.date)}</button>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {days.find((d) => d.date === day)?.slots.map((s) => (
              <button key={s} onClick={() => setSlot(s)} aria-pressed={slot === s}
                className={`rounded-xl border-2 py-2 text-[15px] ${slot === s ? 'border-ledger bg-ledger-soft font-bold text-ledger' : 'border-rule bg-white'}`}>{s}</button>
            ))}
          </div>
        </section>
      )}
      <ErrorNote msg={err} />
      {paid && <StickyBar><button className="btn-primary w-full" onClick={book} disabled={!slot}>{t('book_slot')}</button></StickyBar>}
    </Shell>
  )
}
