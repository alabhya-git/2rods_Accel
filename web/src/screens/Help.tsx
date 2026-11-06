import { useState } from 'react'
import { ErrorNote, Shell, Stamp } from '../components/ui'
import { api } from '../lib/api'
import { useLang } from '../lib/i18n'

const WINDOWS = ['asap', 'today_evening', 'tomorrow_morning', 'tomorrow_evening', 'after_9pm']

/** "Talk to a person": a real task with a number, a window and the context, in the owner's language. */
export default function Help() {
  const { t, lang } = useLang()
  const p = new URLSearchParams(location.search)
  const [phone, setPhone] = useState('')
  const [win, setWin] = useState('today_evening')
  const [done, setDone] = useState<{ phone_masked: string; window: string } | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const send = async () => {
    setBusy(true)
    setErr(null)
    try {
      const r = await api.post<{ phone_masked: string; window: string }>('/api/help', {
        phone, window: win, language: lang, source: p.get('source') || (p.get('order') ? 'tracker' : 'advisor'),
        session_id: p.get('session'), order_id: p.get('order'), key: p.get('key'), reason: p.get('reason') || 'prefer_person',
      })
      setDone(r)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <Shell back title={t('callback_title')}>
      {done ? (
        <section className="mt-6 text-center">
          <Stamp kind="ok">✓</Stamp>
          <p className="mt-4 text-[19px] font-semibold">{t('callback_done', { phone: done.phone_masked, window: t('w_' + win) })}</p>
        </section>
      ) : (
        <>
          <p className="text-[17px] text-ink-soft">{t('callback_intro')}</p>
          <label className="mt-5 block">
            <span className="mb-1 block font-semibold">{t('phone_label')}</span>
            <input className="field text-[19px] tracking-wide" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98XXXXXXXX" />
          </label>
          <fieldset className="mt-5">
            <legend className="mb-2 font-semibold">{t('when_call')}</legend>
            <div className="flex flex-wrap gap-2" role="radiogroup">
              {WINDOWS.map((w) => (
                <button key={w} role="radio" aria-checked={win === w} onClick={() => setWin(w)}
                  className={`chip ${win === w ? '!border-ledger !bg-ledger !text-white' : ''}`}>{t('w_' + w)}</button>
              ))}
            </div>
          </fieldset>
          <button className="btn-primary mt-6 w-full" disabled={busy || phone.replace(/\D/g, '').length < 10} onClick={send}>{t('call_me')}</button>
          <ErrorNote msg={err} />
        </>
      )}
    </Shell>
  )
}
