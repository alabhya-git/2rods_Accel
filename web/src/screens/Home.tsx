import { Link, useNavigate } from 'react-router-dom'
import { Logo, LangSwitch } from '../components/ui'
import { LANGS } from '../i18n/strings'
import { myOrders } from '../lib/api'
import { useLang } from '../lib/i18n'

/** Three doors, one order: the owner chooses how to buy, not the AI. */
export default function Home() {
  const { lang, setLang, t } = useLang()
  const nav = useNavigate()
  const partner = new URLSearchParams(location.search).get('partner')
  const hasOrders = myOrders().length > 0
  const doors = [
    { key: 'help', title: t('door_help'), sub: t('door_help_sub'), go: () => nav(`/advisor?lang=${lang}${partner ? `&partner=${partner}` : ''}`), primary: true,
      icon: <path d="M4 5h16v11H8l-4 4V5z" /> },
    { key: 'express', title: t('door_express'), sub: t('door_express_sub'), go: () => nav('/express'), primary: false,
      icon: <path d="M4 7h16M4 12h16M4 17h10" /> },
    { key: 'person', title: t('door_person'), sub: t('door_person_sub'), go: () => nav('/help?source=home'), primary: false,
      icon: <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" /> },
  ]
  return (
    <div className="min-h-full bg-white">
      <div className="mx-auto flex max-w-[480px] flex-col px-5 pb-10 pt-5">
        <div className="flex items-center justify-between">
          <Logo />
          <LangSwitch />
        </div>

        <p className="mt-7 text-[26px] font-bold leading-[1.2] text-ink">{t('tagline')}</p>

        <nav className="mt-6 flex flex-col gap-3" aria-label="How do you want to start?">
          {doors.map((d) => (
            <button key={d.key} onClick={d.go}
              className={`flex items-start gap-4 rounded-2xl border-2 p-4 text-left transition-colors ${d.primary ? 'border-kumkum bg-kumkum text-white' : 'border-rule bg-white hover:border-ledger'}`}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mt-0.5 shrink-0" aria-hidden="true">{d.icon}</svg>
              <span>
                <span className="block text-[20px] font-bold leading-tight">{d.title}</span>
                <span className={`mt-1 block text-[15px] leading-snug ${d.primary ? 'text-white/90' : 'text-ink-soft'}`}>{d.sub}</span>
              </span>
            </button>
          ))}
          {hasOrders && (
            <button className="btn-secondary" onClick={() => nav('/orders')}>{t('my_orders')}</button>
          )}
          <button className="btn-quiet" onClick={() => nav('/whatsapp')}>{t('on_whatsapp')}</button>
        </nav>

        <section className="mt-8" aria-labelledby="pick">
          <h2 id="pick" className="text-[15px] text-ink-soft">{t('choose_language')}</h2>
          <div className="mt-2 grid grid-cols-5 gap-1.5">
            {LANGS.map((l) => (
              <button key={l.code} onClick={() => setLang(l.code)} aria-pressed={l.code === lang}
                className={`h-12 rounded-lg border-2 text-[15px] font-bold ${l.code === lang ? 'border-kumkum bg-kumkum text-white' : 'border-rule bg-white text-ink hover:border-ledger'}`}
                style={{ fontFamily: `'${l.font}', 'Baloo 2'` }} lang={l.code}>
                {l.name}
              </button>
            ))}
          </div>
        </section>

        <ol className="mt-8 space-y-3">
          {['how_1', 'how_2', 'how_3', 'how_4'].map((k, i) => (
            <li key={k} className="flex items-start gap-3">
              <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-haldi-soft text-[15px] font-bold text-haldi-dark">{i + 1}</span>
              <span className="text-[17px]">{t(k)}</span>
            </li>
          ))}
        </ol>

        <div className="mt-12 flex flex-wrap gap-x-5 gap-y-2 border-t border-rule pt-5 text-[15px]">
          <Link className="text-ledger underline-offset-4 hover:underline" to="/partner">{t('partner_mode')}</Link>
          <Link className="text-ledger underline-offset-4 hover:underline" to="/judge">Judge console</Link>
        </div>
        <p className="mt-4 text-[13px] text-ink-soft">Accel Telecom and Accel Business are fictional. All data is synthetic, built for the Airtel SYNC hackathon. Payments run in test mode.</p>
      </div>
    </div>
  )
}
