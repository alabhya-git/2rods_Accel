import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shell, Working } from '../components/ui'
import { api, myOrders, rupees, type OrderView } from '../lib/api'
import { useLang } from '../lib/i18n'

type Row = { id: string; key: string; order: OrderView | null }

/** Every order placed on this phone, newest first: open one to track it or reach My account. */
export default function Orders() {
  const { t, bcp } = useLang()
  const nav = useNavigate()
  const [rows, setRows] = useState<Row[] | null>(null)

  useEffect(() => {
    const saved = myOrders()
    Promise.all(saved.map((s) => api.get<OrderView>(`/api/orders/${s.id}?key=${s.key}`).then((o) => ({ ...s, order: o })).catch(() => ({ ...s, order: null }))))
      .then((r) => setRows(r.filter((x) => x.order)))
  }, [])

  const word = (s: string) => s === 'active' ? t('live') : s.startsWith('kyc_review') ? t('outcome_review') : s === 'kyc_fix' ? t('attention') : t('in_progress')
  return (
    <Shell back="/" title={t('my_orders')}>
      {!rows ? <Working label="…" /> : rows.length === 0 ? (
        <div className="mt-6 text-center">
          <p className="text-ink-soft">{t('no_orders')}</p>
          <button className="btn-primary mt-4" onClick={() => nav('/')}>{t('door_help')}</button>
        </div>
      ) : (
        <ul className="space-y-3">
          {rows.map(({ id, key, order: o }) => (
            <li key={id}>
              <button className="w-full rounded-xl border border-rule bg-white p-4 text-left hover:border-ledger" onClick={() => nav(`/track/${id}?key=${key}`)}>
                <div className="flex items-baseline justify-between gap-3">
                  <p className="truncate text-[18px] font-bold">{o!.business_name}</p>
                  <p className="money shrink-0">{rupees(o!.monthly)}</p>
                </div>
                <p className="truncate text-[15px] text-ink-soft">{o!.bundle.lines.map((l) => l.name).join(', ')}</p>
                <div className="mt-1 flex justify-between text-[14px]">
                  <span className={o!.status === 'active' ? 'font-semibold text-leaf' : 'text-ink-soft'}>{word(o!.status)}</span>
                  <span className="text-ink-soft">{new Date(o!.created_at ?? Date.now()).toLocaleDateString(bcp, { day: 'numeric', month: 'short' })}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Shell>
  )
}
