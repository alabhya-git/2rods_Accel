import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, ErrorNote, Hint, Shell, Split, StickyBar, Toggle, Working } from '../components/ui'

function Tick({ on, onChange, label, disabled = false }: { on: boolean; onChange: () => void; label: string; disabled?: boolean }) {
  return (
    <button className="tick" role="checkbox" aria-checked={on} aria-label={label} disabled={disabled} onClick={onChange}>
      {on && <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7" /></svg>}
    </button>
  )
}
import { api, paise, rememberOrder, rupees, type Bundle, type OrderView, type Schedule } from '../lib/api'
import { useLang } from '../lib/i18n'

type Q = Bundle & { switched_off: { product_id: string; name: string; qty: number; why: string }[]; business_type?: string; city?: string; partner_id?: string | null
  schedule_options: { upfront: Schedule; emi: Schedule }; current_spend: number | null }

function expressCart(): { profile: Record<string, any>; items: Record<string, number> } | null {
  if (!new URLSearchParams(location.search).get('express')) return null
  try { return JSON.parse(sessionStorage.getItem('express') || 'null') } catch { return null }
}
const PER_UNIT = new Set(['per user', 'per device', 'per camera', 'per counter', 'per line', 'per channel', 'per vehicle', 'per site'])

export default function Quote() {
  const { lang, t } = useLang()
  const nav = useNavigate()
  const sid = new URLSearchParams(location.search).get('session')
  const [items, setItems] = useState<Record<string, number> | null>(null)
  const [term, setTerm] = useState(12)
  const [emi, setEmi] = useState(false)
  const [q, setQ] = useState<Q | null>(null)
  const [phone, setPhone] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [placing, setPlacing] = useState(false)
  const known = useRef<Record<string, { name: string; unit: string }>>({})
  const express = useRef(expressCart()).current
  const [spend, setSpend] = useState('')
  const [staff, setStaff] = useState(false)  // only 41% of leads are owners: staff prepare, the owner approves
  const [ownerPhone, setOwnerPhone] = useState('')

  // first load: the advisor's recommendation, or the express cart
  useEffect(() => {
    api.post<Q>('/api/quote', { session_id: sid, profile: express?.profile, items: express?.items ?? {}, term_months: term, language: lang }).then((r) => {
      if (r.current_spend) setSpend(String(r.current_spend))
      setQ(r)
      setItems(Object.fromEntries(r.lines.map((l) => [l.product_id, l.qty])))
    }).catch((e) => setErr(e.message))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // re-price on every change: the server re-checks every rule
  useEffect(() => {
    if (!items) return
    const h = setTimeout(() => {
      api.post<Q>('/api/quote', { session_id: sid, profile: express?.profile, items, term_months: term, language: lang }).then((r) => {
        setQ(r)
        const ids = new Set(r.lines.map((l) => l.product_id))
        if (Object.keys(items).some((k) => !ids.has(k)) || r.lines.some((l) => !(l.product_id in items))) {
          setItems(Object.fromEntries(r.lines.map((l) => [l.product_id, l.qty])))
        }
      }).catch((e) => setErr(e.message))
    }, 150)
    return () => clearTimeout(h)
  }, [items, term, lang]) // eslint-disable-line react-hooks/exhaustive-deps

  useMemo(() => {
    q?.lines.forEach((l) => (known.current[l.product_id] = { name: l.name, unit: l.unit }))
    q?.addons.forEach((a) => (known.current[a.product_id] = { name: a.name, unit: '' }))
  }, [q])

  if (!q || !items) return <Shell back title={t('quote_title')} width="wide" step="quote"><Working label="…" />{err && <ErrorNote msg={err} />}</Shell>

  const toggle = (pid: string, qty: number, on: boolean) => {
    const next = { ...items }
    if (on) next[pid] = qty
    else delete next[pid]
    setItems(next)
  }
  const setQty = (pid: string, qty: number) => setItems({ ...items, [pid]: Math.max(1, Math.min(200, qty)) })
  const saving = term === 12 ? q.monthly - q.monthly_other_term : 0
  // every amount below is read from the server's payment schedule: nothing is recomputed here
  const s = q.schedule_options[emi ? 'emi' : 'upfront']
  const today = Number(spend.replace(/\D/g, '')) * 100
  const vsToday = today > 0 ? s.monthly_after_emi - today : null

  const place = async () => {
    setPlacing(true)
    setErr(null)
    try {
      const o = await api.post<OrderView>('/api/orders', { session_id: sid, profile: express?.profile, items, term_months: term, setup_emi: emi, phone,
        placed_by: staff ? 'staff' : 'owner', owner_phone: staff ? ownerPhone : undefined })
      rememberOrder(o.order_id!, o.access_key!)
      nav(`/order/${o.order_id}/consent?key=${o.access_key}`)
    } catch (e: any) {
      setErr(e.message)
      setPlacing(false)
    }
  }

  // what is still missing before the order can be placed, said plainly
  const missing = phone.replace(/\D/g, '').length < 10 ? t('need_phone') : staff && ownerPhone.replace(/\D/g, '').length < 10 ? t('owner_phone') : null

  return (
    <Shell back={express ? '/express' : `/advisor?session=${sid}`} title={t('quote_title')} width="wide" step="quote">
      <Split aside={
        <>
          <Card title={t('order_summary')}>
            <div className="flex items-center justify-between gap-3">
              <span className="font-semibold">{t('contract')}</span>
              <div className="flex rounded-pill bg-paper-tint p-1 ring-1 ring-rule" role="radiogroup" aria-label={t('contract')}>
                {[12, 24].map((m) => (
                  <button key={m} role="radio" aria-checked={term === m} onClick={() => setTerm(m)}
                    className={`rounded-pill px-3.5 py-1 text-[15px] font-semibold transition ${term === m ? 'bg-white text-kumkum-dark shadow-card ring-1 ring-kumkum/30' : 'text-ink-soft hover:text-ink'}`}>
                    {t(m === 12 ? 'months12' : 'months24')}
                  </button>
                ))}
              </div>
            </div>
            {saving > 0 && (
              <button className="mt-2 w-full rounded-xl bg-haldi-soft px-3 py-2 text-left text-[15px] font-semibold text-haldi-dark hover:brightness-95" onClick={() => setTerm(24)}>{t('save_24', { amount: rupees(saving) })}</button>
            )}
            {q.setup > 0 && (
              <div className="mt-3 flex items-center justify-between gap-3">
                <span className="text-[15px] leading-tight">{t('setup_emi')}</span>
                <Toggle on={emi} onChange={setEmi} label={t('setup_emi')} />
              </div>
            )}
            <div className="mt-4 border-t border-rule pt-4">
              <div className="flex flex-wrap items-end justify-between gap-x-3 gap-y-1">
                <span className="text-[16px] font-bold leading-tight">{t('all_in')}</span>
                <span className="money whitespace-nowrap text-[30px] leading-none text-kumkum sm:text-[36px]">{paise(s.monthly)}</span>
              </div>
              <dl className="mt-3 space-y-1.5 text-[15px]">
                <div className="flex justify-between"><dt>{t('due_today')}</dt><dd className="money">{paise(s.due_today)}</dd></div>
                {s.setup_emi && (
                  <>
                    <div className="flex justify-between gap-3"><dt>{t('setup_instalments', { n: s.emi_months })}</dt>
                      <dd className="money">{paise(s.instalment)}{s.last_instalment !== s.instalment ? ` … ${paise(s.last_instalment)}` : ''}</dd></div>
                    {s.monthly_after_emi !== s.monthly && <div className="flex justify-between"><dt>{t('after_emi', { n: s.emi_months })}</dt><dd className="money">{paise(s.monthly_after_emi)}</dd></div>}
                  </>
                )}
                {!s.setup_emi && q.setup > 0 && <div className="flex justify-between"><dt>{t('setup_once')}</dt><dd className="money">{rupees(q.setup)} {t('plus_gst')}</dd></div>}
                <div className="flex justify-between text-[14px] text-ink-soft"><dt>{t('total_commit', { n: s.term_months })}</dt><dd className="money">{paise(s.total_commitment)}</dd></div>
              </dl>
            </div>
          </Card>

          <Card title={t('your_details')}>
            <label className="block">
              <span className="label">{t('today_spend')}</span>
              <input className="field" inputMode="numeric" value={spend} onChange={(e) => setSpend(e.target.value)} placeholder="Rs 900" />
            </label>
            {vsToday !== null && (
              <p className={`mt-2 rounded-xl px-3 py-2 text-[15px] font-semibold ${vsToday > 0 ? 'bg-haldi-soft text-haldi-dark' : 'bg-leaf-soft text-leaf'}`} role="status">
                {t(vsToday > 0 ? 'vs_more' : 'vs_less', { diff: paise(Math.abs(vsToday)) })}
              </p>
            )}
            <label className="mt-4 block">
              <span className="label">{t('phone_label')}</span>
              <input className="field text-[19px] tracking-wide" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98XXXXXXXX" />
            </label>
            <fieldset className="mt-4">
              <legend className="label">{t('who_ordering')}</legend>
              <div className="grid grid-cols-2 gap-2" role="radiogroup">
                {[false, true].map((st) => (
                  <button key={String(st)} role="radio" aria-checked={staff === st} onClick={() => setStaff(st)} className="choice text-center text-[15px]">
                    {t(st ? 'i_work_here' : 'i_am_owner')}
                  </button>
                ))}
              </div>
              {staff && (
                <label className="mt-3 block">
                  <span className="label">{t('owner_phone')}</span>
                  <input className="field text-[19px] tracking-wide" inputMode="tel" value={ownerPhone} onChange={(e) => setOwnerPhone(e.target.value)} placeholder="98XXXXXXXX" />
                  <span className="mt-1.5 block text-[14px] text-ink-soft">{t('owner_will_approve')}</span>
                </label>
              )}
            </fieldset>
          </Card>
          <ErrorNote msg={err} />

          <StickyBar hint={missing && <Hint>{missing}</Hint>}>
            <div className="flex-1 lg:hidden">
              <p className="money text-[22px] leading-tight">{paise(s.monthly)}</p>
              <p className="text-[13px] text-ink-soft">{t('all_in')}</p>
            </div>
            <button className="btn-primary lg:flex-1" disabled={placing || q.lines.length === 0 || !!missing} onClick={place}>{t('place_order')}</button>
          </StickyBar>
        </>
      }>
        {q.partner_id && <p className="mb-3 rounded-xl bg-haldi-soft px-3 py-2 text-[15px] text-haldi-dark">Assisted by partner {q.partner_id}</p>}
        <div className="khata">
          <p className="row truncate text-[20px] font-extrabold">{q.name}</p>
          <div className="row justify-between gap-3 text-[15px] text-ink-soft">
            <span className="truncate">{t('in_bundle')}</span>
            <span className="shrink-0 whitespace-nowrap">{t('live_in', { days: q.install_days })}</span>
          </div>
          {q.lines.map((ln) => (
            <div key={ln.product_id}>
              <div className="row justify-between gap-3">
                <Tick on onChange={() => toggle(ln.product_id, ln.qty, false)} label={ln.name} />
                <span className="truncate font-semibold">{ln.name}</span>
                <span className="money shrink-0 whitespace-nowrap">{rupees(ln.monthly)}</span>
              </div>
              <div className="row justify-between gap-3 text-[14px] text-ink-soft">
                <span className="truncate">{(ln as any).why}</span>
                {PER_UNIT.has(ln.unit) && !(ln.unit === 'per site' && ln.qty === 1) && (
                  <span className="flex shrink-0 items-center gap-1">
                    <button className="h-7 w-7 rounded-full border border-rule-strong bg-white hover:border-ink" onClick={() => setQty(ln.product_id, ln.qty - 1)} aria-label={`Fewer ${ln.name}`}>−</button>
                    <span className="w-7 text-center font-bold text-ink">{ln.qty}</span>
                    <button className="h-7 w-7 rounded-full border border-rule-strong bg-white hover:border-ink" onClick={() => setQty(ln.product_id, ln.qty + 1)} aria-label={`More ${ln.name}`}>+</button>
                  </span>
                )}
              </div>
            </div>
          ))}

          {(q.switched_off.length > 0 || q.addons.length > 0) && <p className="row text-[15px] font-semibold text-ink-soft">{t('add_more')}</p>}
          {q.switched_off.map((so) => (
            <div key={so.product_id} className="row justify-between gap-3">
              <Tick on={false} onChange={() => toggle(so.product_id, so.qty, true)} label={so.name} />
              <span className="truncate">{so.name}{so.qty > 1 ? ` ×${so.qty}` : ''}</span>
            </div>
          ))}
          {q.addons.map((a) => (
            <div key={a.product_id}>
              <div className="row justify-between gap-3">
                <Tick on={false} disabled={!a.eligible} onChange={() => toggle(a.product_id, a.qty, true)} label={a.name} />
                <span className={`truncate ${a.eligible ? '' : 'text-ink-faint line-through decoration-kumkum/60'}`}>{a.name}{a.qty > 1 ? ` ×${a.qty}` : ''}</span>
                {a.eligible && <span className="money shrink-0 whitespace-nowrap text-ink-soft">+{rupees(a.monthly)}</span>}
              </div>
              {!a.eligible && <p className="row truncate text-[14px] text-kumkum-dark">{(a as any).why}</p>}
            </div>
          ))}

          {q.exclusions.length > 0 && (
            <>
              <p className="row text-[15px] font-semibold text-ink-soft">{t('not_available')}</p>
              {q.exclusions.map((e) => <p key={e.product_id} className="row-free text-[15px] leading-tight text-kumkum-dark">{(e as any).why}</p>)}
            </>
          )}
        </div>
      </Split>
    </Shell>
  )
}
