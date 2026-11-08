import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { JudgeMenu, SiteFooter, SiteHeader, Svg } from '../components/ui'
import { LANGS } from '../i18n/strings'
import { myOrders } from '../lib/api'
import { useLang } from '../lib/i18n'

const ICONS: Record<string, ReactNode> = {
  help: <path d="M4 5h16v11H8l-4 4V5z" />,
  express: <path d="M4 7h16M4 12h16M4 17h10" />,
  person: <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" />,
  whatsapp: <path d="M20 11.5a8.5 8.5 0 0 1-12.6 7.4L3 20l1.2-4.2A8.5 8.5 0 1 1 20 11.5z" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  bill: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" /><path d="M9 8h6M9 12h6" /></>,
  lock: <><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  shield: <><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" /></>,
  lang: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" /></>,
  chevron: <path d="M9 5l7 7-7 7" />,
}

/** The 2-minute overview for first-time owners: the problem, then the six steps. */
function OverviewVideo() {
  return (
    <video className="aspect-video w-full rounded-2xl bg-black shadow-lift ring-1 ring-black/10" controls playsInline preload="metadata"
      poster="/videos/dukaan-connect-overview-poster.jpg">
      <source src="/videos/dukaan-connect-overview.mp4" type="video/mp4" />
    </video>
  )
}

/** Four doors, one order: the owner chooses how to buy, not the AI. */
export default function Home() {
  const { lang, setLang, t } = useLang()
  const nav = useNavigate()
  const partner = new URLSearchParams(location.search).get('partner')
  const hasOrders = myOrders().length > 0
  const doors = [
    { key: 'help', title: t('door_help'), sub: t('door_help_sub'), go: () => nav(`/advisor?lang=${lang}${partner ? `&partner=${partner}` : ''}`), primary: true, live: false },
    // a call answered at once by the AI; a person is one tap away inside it
    { key: 'person', title: t('call_door'), sub: t('call_door_sub'), go: () => nav('/call'), primary: false, live: true },
    { key: 'whatsapp', title: t('on_whatsapp'), sub: t('door_wa_sub'), go: () => nav('/whatsapp'), primary: false, live: false },
    { key: 'express', title: t('door_express'), sub: t('door_express_sub'), go: () => nav('/express'), primary: false, live: false },
  ]
  const why = [['clock', t('time_promise')], ['bill', t('one_bill')], ['lock', t('privacy_line')], ['shield', t('never_ask')]]

  return (
    <div className="flex min-h-full flex-col bg-white">
      <SiteHeader />

      <section className="hero-red text-onbrand">
        <div className="mx-auto grid max-w-site grid-cols-1 gap-8 px-4 pb-10 pt-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:items-center lg:gap-16 lg:px-8 lg:py-20">
          <div className="animate-rise">
            <div className="flex items-center justify-between gap-3">
              <p className="eyebrow min-w-0 !text-onbrand/80">Dukaan Connect</p>
              <div className="shrink-0 sm:hidden"><JudgeMenu onRed /></div>
            </div>
            <h1 className="mt-3 text-[30px] font-extrabold leading-[1.12] sm:text-[38px] lg:text-[50px]">{t('tagline')}</h1>
            <p className="mt-4 max-w-xl text-[18px] text-onbrand/90 lg:text-[20px]">{t('time_promise')}</p>
            <div className="mt-7 hidden lg:block">
              <OverviewVideo />
              <p className="mt-2 text-[15px] text-onbrand/85">{t('how_video')}</p>
            </div>
          </div>

          <div className="animate-rise rounded-3xl bg-white p-3 text-ink shadow-lift sm:p-6">
            <h2 className="px-1 text-[18px] font-bold">{t('start_title')}</h2>
            <nav className="mt-3 flex flex-col gap-3" aria-label={t('start_title')}>
              {doors.map((d) => (
                <button key={d.key} onClick={d.go}
                  className={`group relative flex items-center gap-3 rounded-2xl p-3.5 text-left transition sm:gap-4 sm:p-4 ${d.primary
                    ? 'text-onbrand shadow-brand hover:brightness-105 [background-image:linear-gradient(135deg,#e3162f,#b30c24)]'
                    : 'border-[1.5px] border-rule bg-white hover:border-ink hover:shadow-card'}`}>
                  <span className={`relative grid h-11 w-11 shrink-0 place-items-center rounded-2xl sm:h-12 sm:w-12 ${d.primary ? 'bg-onbrand/15' : 'bg-kumkum-soft text-kumkum'}`}>
                    <Svg d={ICONS[d.key]} size={24} width={2} />
                    {d.live && <span className="absolute -right-0.5 -top-0.5 flex h-3 w-3" aria-hidden="true"><span className="absolute inset-0 animate-ping rounded-full bg-leaf/70" /><span className="relative h-3 w-3 rounded-full bg-leaf ring-2 ring-white" /></span>}
                  </span>
                  <span className="min-w-0 flex-1">
                    {d.primary && <span className="mb-1 inline-block rounded-pill bg-onbrand px-2.5 py-0.5 text-[12px] font-bold uppercase tracking-wide text-kumkum">{t('not_sure')}</span>}
                    <span className="block text-[19px] font-bold leading-tight">{d.title}</span>
                    <span className={`mt-0.5 block text-[15px] leading-snug ${d.primary ? 'text-onbrand/90' : 'text-ink-soft'}`}>{d.sub}</span>
                  </span>
                  <span className={`shrink-0 transition group-hover:translate-x-0.5 ${d.primary ? 'text-onbrand' : 'text-ink-faint'}`}><Svg d={ICONS.chevron} /></span>
                </button>
              ))}
            </nav>
            {hasOrders && <button className="btn-secondary mt-3 w-full" onClick={() => nav('/orders')}>{t('my_orders')}</button>}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-site px-4 py-10 lg:px-8 lg:py-16">
        <h2 className="text-[24px] font-extrabold lg:text-[32px]">{t('why_title')}</h2>
        <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {why.map(([icon, text]) => (
            <li key={icon} className="card p-5">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-kumkum-soft text-kumkum"><Svg d={ICONS[icon]} size={22} width={2} /></span>
              <p className="mt-3 text-[16px] font-semibold leading-snug">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="border-y border-rule bg-paper-tint lg:hidden">
        <div className="mx-auto max-w-site px-4 py-10">
          <h2 className="text-[24px] font-extrabold">{t('how_title')}</h2>
          <div className="mt-5"><OverviewVideo /></div>
          <p className="mt-2 text-[15px] text-ink-soft">{t('how_video')}</p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-site px-4 py-10 lg:px-8 lg:pb-16 lg:pt-0" aria-labelledby="pick">
        <h2 id="pick" className="text-[20px] font-bold">{t('choose_language')}</h2>
        <p className="mt-1 text-ink-soft">{t('ten_langs')}</p>
        <div className="mt-4 grid grid-cols-5 gap-2 lg:grid-cols-10">
          {LANGS.map((l) => (
            <button key={l.code} onClick={() => setLang(l.code)} aria-pressed={l.code === lang}
              className={`h-12 rounded-xl border-[1.5px] text-[15px] font-bold transition ${l.code === lang ? 'border-kumkum bg-kumkum text-onbrand shadow-brand' : 'border-rule bg-white text-ink hover:border-ink'}`}
              style={{ fontFamily: `'${l.font}', 'Baloo 2'` }} lang={l.code}>
              {l.name}
            </button>
          ))}
        </div>
      </section>

      <SiteFooter always />
    </div>
  )
}
