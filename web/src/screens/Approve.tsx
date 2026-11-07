import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ErrorNote, Shell, Stamp, Working } from '../components/ui'
import { api, paise, rememberOrder, rupees } from '../lib/api'
import { useLang } from '../lib/i18n'

type Page = {
  kind: 'owner' | 'landlord'; status: string; business_name: string; terms_version: string
  prepared_by?: string; lines?: { name: string; qty: number; monthly: number }[]; monthly_paise?: number; due_today_paise?: number
  term_months?: number; total_commitment_paise?: number; name_on_bill?: string; premises?: string
}

/** The link the owner (staff placed the order) or the landlord (the bill is in their name) opens. */
export default function Approve() {
  const { token } = useParams()
  const { t } = useLang()
  const nav = useNavigate()
  const [p, setP] = useState<Page | null>(null)
  const [name, setName] = useState('')
  const [otp, setOtp] = useState('')
  const [agree, setAgree] = useState(false)
  const [done, setDone] = useState<{ status: string; order_id?: string; access_key?: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api.get<Page>(`/api/approvals/${token}`).then(setP).catch((e) => setErr(e.message)) }, [token])
  if (!p) return <Shell title="…"><Working label="…" /><ErrorNote msg={err} /></Shell>

  const decide = async (decision: 'approve' | 'decline') => {
    setBusy(true)
    setErr(null)
    try {
      const r = await api.post<{ status: string; order_id?: string; access_key?: string }>(`/api/approvals/${token}`, { decision, name, otp, consent: agree })
      if (r.order_id && r.access_key) rememberOrder(r.order_id, r.access_key)
      setDone(r)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }
  const owner = p.kind === 'owner'
  const status = done?.status ?? p.status

  return (
    <Shell title={t(owner ? 'approve_owner' : 'approve_landlord')}>
      <p className="text-[17px]">{owner ? t('approve_owner_intro', { business: p.business_name, who: p.prepared_by ?? '' })
        : t('approve_landlord_intro', { business: p.business_name, name: p.name_on_bill ?? '' })}</p>

      {owner ? (
        <section className="khata mt-4">
          {p.lines!.map((l) => (
            <div key={l.name} className="row justify-between gap-3"><span className="truncate">{l.name}{l.qty > 1 ? ` ×${l.qty}` : ''}</span><span className="money">{rupees(l.monthly)}</span></div>
          ))}
          <div className="row justify-between border-t-2 border-ink font-bold"><span>{t('all_in')}</span><span className="money">{paise(p.monthly_paise)}</span></div>
          <div className="row justify-between"><span>{t('due_today')}</span><span className="money">{paise(p.due_today_paise)}</span></div>
          <div className="row justify-between text-[14px] text-ink-soft"><span>{t('total_commit', { n: p.term_months! })}</span><span className="money">{paise(p.total_commitment_paise)}</span></div>
        </section>
      ) : (
        <p className="mt-4 rounded-xl border border-rule bg-white px-4 py-3 text-[16px] font-semibold">{p.premises}</p>
      )}

      {status === 'pending' ? (
        <section className="mt-5 space-y-3">
          <label className="block">
            <span className="mb-1 block font-semibold">{t('name_on_aadhaar')}</span>
            <input className="field" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
          </label>
          <label className="block">
            <span className="mb-1 block font-semibold">{t('aadhaar_otp')}</span>
            <input className="field tracking-[0.3em]" inputMode="numeric" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))} placeholder="••••••" />
            <span className="mt-1 block text-[13px] text-ink-faint" lang="en">Demo: any 6 digits. In production this is Aadhaar eSign from a licensed provider.</span>
          </label>
          <label className="flex items-start gap-3 text-[15px]">
            <input type="checkbox" className="mt-1 h-5 w-5 shrink-0" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
            <span>{t(owner ? 'agree_owner' : 'agree_landlord')} <span className="text-ink-faint">({p.terms_version})</span></span>
          </label>
          <p className="rounded-lg bg-paper-tint px-3 py-2 text-[14px] text-ink-soft">{t('never_ask')}</p>
          <button className="btn-primary w-full" disabled={busy || !agree || otp.length !== 6 || name.trim().length < 3} onClick={() => decide('approve')}>{t('esign_approve')}</button>
          <button className="btn-quiet w-full border border-rule" disabled={busy} onClick={() => decide('decline')}>{t('not_now')}</button>
        </section>
      ) : (
        <section className="mt-6 text-center">
          <Stamp kind={status === 'approved' ? 'ok' : 'review'}>{status === 'approved' ? '✓' : '✕'}</Stamp>
          <p className="mt-4 text-[19px] font-semibold">{t(status === 'approved' ? 'approved_done' : 'declined_done')}</p>
          {done?.order_id && <button className="btn-secondary mt-4" onClick={() => nav(`/track/${done.order_id}?key=${done.access_key}`)}>{t('track_title')}</button>}
        </section>
      )}
      <ErrorNote msg={err} />
    </Shell>
  )
}
