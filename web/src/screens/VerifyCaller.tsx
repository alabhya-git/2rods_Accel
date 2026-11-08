import { useState } from 'react'
import { ErrorNote, Shell, Stamp } from '../components/ui'
import { api } from '../lib/api'
import { useLang } from '../lib/i18n'

/** "Someone called saying they are from Dukaan Connect": check the partner ID or the number before sharing anything. */
export default function VerifyCaller() {
  const { t } = useLang()
  const [q, setQ] = useState('')
  const [r, setR] = useState<{ genuine: boolean; name?: string } | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const check = async () => {
    setErr(null)
    try { setR(await api.get(`/api/verify-caller?q=${encodeURIComponent(q.trim())}`)) } catch (e: any) { setErr(e.message) }
  }

  return (
    <Shell back title={t('check_caller')}>
      <p className="text-[17px] text-ink-soft">{t('verify_intro')}</p>
      <div className="mt-4 flex gap-2">
        <input className="field flex-1" value={q} onChange={(e) => { setQ(e.target.value); setR(null) }} placeholder="PARTNER-001 / 98XXXXXXXX" />
        <button className="btn-secondary" onClick={check} disabled={q.trim().length < 3}>{t('check')}</button>
      </div>
      {r && (
        <section className={`mt-5 rounded-xl border-2 p-4 ${r.genuine ? 'border-leaf bg-leaf/10' : 'border-kumkum bg-kumkum/5'}`} role="status">
          <Stamp kind={r.genuine ? 'ok' : 'review'} animate={false}>{r.genuine ? '✓' : '!'}</Stamp>
          <p className="mt-3 text-[18px] font-semibold">{r.genuine ? t('verify_ok', { name: r.name ?? '' }) : t('verify_bad')}</p>
        </section>
      )}
      <p className="mt-6 rounded-lg bg-paper-tint px-3 py-2 text-[15px]">{t('never_ask')}</p>
      <ErrorNote msg={err} />
    </Shell>
  )
}
