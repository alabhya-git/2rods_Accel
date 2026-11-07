import { useState, type ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { LANGS } from '../i18n/strings'
import { useLang } from '../lib/i18n'

export function Logo({ small = false, light = false }: { small?: boolean; light?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5" aria-label="Accel Business home">
      <svg width={small ? 30 : 36} height={small ? 30 : 36} viewBox="0 0 64 64" aria-hidden="true">
        <defs>
          <linearGradient id="lg-mark" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#E3162F" /><stop offset="1" stopColor="#A80C22" /></linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill={light ? '#fff' : 'url(#lg-mark)'} />
        <path d="M14 46 L32 14 L50 46" fill="none" stroke={light ? '#D50F2B' : '#fff'} strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M22 36 H42" stroke="#F2A900" strokeWidth="6" strokeLinecap="round" />
      </svg>
      <span className="leading-none">
        <span className={`block text-[19px] font-extrabold tracking-tight ${light ? 'text-onbrand' : 'text-ink'}`}>Accel Business</span>
        {!small && <span className={`mt-0.5 block text-[12px] font-semibold tracking-wide ${light ? 'text-onbrand/75' : 'text-ink-faint'}`}>Udyam Digital</span>}
      </span>
    </Link>
  )
}

export function LangSwitch({ onRed = false }: { onRed?: boolean }) {
  const { lang, setLang } = useLang()
  const [open, setOpen] = useState(false)
  const current = LANGS.find((l) => l.code === lang)!
  return (
    <div className="relative">
      <button className={`chip whitespace-nowrap ${onRed ? '!border-onbrand/40 !bg-onbrand/10 !text-onbrand hover:!border-onbrand' : ''}`}
        onClick={() => setOpen(!open)} aria-expanded={open} aria-haspopup="true" aria-label="Change language">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" /></svg>
        {current.name}
      </button>
      {open && (
        <>
          <button className="fixed inset-0 z-30 cursor-default" aria-label="Close" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-40 mt-2 grid w-64 animate-rise grid-cols-2 gap-1 rounded-2xl border border-rule bg-white p-2 shadow-lift">
            {LANGS.map((l) => (
              <button key={l.code} onClick={() => { setLang(l.code); setOpen(false) }} lang={l.code}
                className={`rounded-xl px-3 py-2 text-left text-ink hover:bg-paper-tint ${l.code === lang ? 'bg-kumkum-soft font-bold text-kumkum-dark' : ''}`}>
                {l.name}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

const Icon = {
  back: <path d="M15 5l-7 7 7 7" />,
  home: <><path d="M3 11l9-7 9 7" /><path d="M5 10v10h5v-6h4v6h5V10" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
}
export function Svg({ d, size = 22, width = 2.2 }: { d: ReactNode; size?: number; width?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>
}

/** Light or dark, remembered on this device. theme.js applies it before the first paint. */
export function ThemeToggle() {
  const { t } = useLang()
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const flip = () => {
    const next = !dark
    document.documentElement.classList.toggle('dark', next)
    try { localStorage.setItem('theme', next ? 'dark' : 'light') } catch { /* private mode: still switches for this visit */ }
    setDark(next)
  }
  const label = t(dark ? 'light_mode' : 'dark_mode')
  return (
    <button onClick={flip} aria-label={label} title={label} aria-pressed={dark}
      className="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-pill border border-rule-strong bg-white text-ink transition hover:border-ink">
      {dark
        ? <Svg size={18} d={<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>} />
        : <Svg size={18} d={<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />} />}
    </button>
  )
}

/** One header everywhere: on a phone, back + page title; on a laptop, the brand and the four places people look for. */
export function SiteHeader({ back, title, right }: { back?: string | boolean; title?: string; right?: ReactNode }) {
  const nav = useNavigate()
  const { t } = useLang()
  const links = [{ to: '/', label: t('home'), end: true }, { to: '/orders', label: t('my_orders') }, { to: '/help?source=header', label: t('talk_person') },
    { to: '/verify', label: t('nav_check') }]
  return (
    <header className="sticky top-0 z-30 border-b border-rule/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-site items-center justify-between gap-3 px-4 lg:h-[72px] lg:px-8">
        <div className="flex min-w-0 items-center gap-1">
          {back && (
            <button className="btn-quiet -ml-3 px-2 lg:hidden" onClick={() => (typeof back === 'string' ? nav(back) : nav(-1))} aria-label={t('back')}>
              <Svg d={Icon.back} width={2.5} />
            </button>
          )}
          <div className={title ? 'hidden lg:block' : ''}><Logo /></div>
          {title && <p className="truncate text-[19px] font-bold lg:hidden" aria-hidden="true">{title}</p>}
        </div>
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}
              className={({ isActive }) => `rounded-pill px-4 py-2 text-[15px] font-semibold transition ${isActive ? 'bg-paper-tint text-ink' : 'text-ink-soft hover:bg-paper-tint hover:text-ink'}`}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-1.5">
          {title && <Link to="/" className="btn-quiet px-2 lg:hidden" aria-label={t('home')} title={t('home')}><Svg d={Icon.home} /></Link>}
          {right}
          <ThemeToggle />
          <LangSwitch />
        </div>
      </div>
    </header>
  )
}

// The buying journey, shown on every step so nobody wonders where they are or what comes next.
export const JOURNEY = ['choose', 'quote', 'consent', 'verify', 'pay', 'track'] as const
export type StepKey = (typeof JOURNEY)[number]

export function Steps({ current }: { current: StepKey }) {
  const { t } = useLang()
  const i = JOURNEY.indexOf(current)
  const label = t('step_of', { n: i + 1, total: JOURNEY.length })
  return (
    <nav aria-label={label} className="border-b border-rule bg-white">
      <div className="mx-auto max-w-site px-4 py-3 lg:px-8 lg:py-4">
        <div className="lg:hidden">
          <div className="flex items-baseline justify-between gap-3 text-[14px]">
            <span className="shrink-0 font-bold text-ink">{label} · {t('step_' + current)}</span>
            {i < JOURNEY.length - 1 && <span className="truncate text-ink-soft">{t('next_up', { step: t('step_' + JOURNEY[i + 1]) })}</span>}
          </div>
          <div className="mt-2 grid grid-cols-6 gap-1" aria-hidden="true">
            {JOURNEY.map((s, j) => <span key={s} className={`h-1.5 rounded-pill ${j <= i ? 'bg-kumkum' : 'bg-rule'}`} />)}
          </div>
        </div>
        <ol className="hidden items-center lg:flex">
          {JOURNEY.map((s, j) => (
            <li key={s} className="flex flex-1 items-center last:flex-none" aria-current={j === i ? 'step' : undefined}>
              <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-[14px] font-bold ${j < i ? 'bg-kumkum text-onbrand' : j === i ? 'bg-white text-kumkum ring-2 ring-kumkum' : 'bg-paper-tint text-ink-faint ring-1 ring-rule'}`}>
                {j < i ? <Svg d={Icon.check} size={16} width={3} /> : j + 1}
              </span>
              <span className={`ml-2.5 whitespace-nowrap text-[15px] ${j === i ? 'font-bold text-ink' : j < i ? 'font-semibold text-ink-soft' : 'text-ink-faint'}`}>{t('step_' + s)}</span>
              {j < JOURNEY.length - 1 && <span className={`mx-4 h-[2px] flex-1 rounded ${j < i ? 'bg-kumkum' : 'bg-rule'}`} aria-hidden="true" />}
            </li>
          ))}
        </ol>
      </div>
    </nav>
  )
}

/** Page frame. Form pages stay a readable width; shopping pages open into two columns on a laptop. */
export function Shell({ children, back, title, width = 'form', step, right }: {
  children: ReactNode; back?: string | boolean; title?: string; width?: 'form' | 'wide'; step?: StepKey; right?: ReactNode
}) {
  const nav = useNavigate()
  const { t } = useLang()
  return (
    <div className="flex min-h-full flex-col">
      <SiteHeader back={back} title={title} right={right} />
      {step && <Steps current={step} />}
      <main className={`mx-auto w-full flex-1 animate-fade px-4 pb-36 pt-5 lg:px-8 lg:pb-16 lg:pt-8 ${width === 'wide' ? 'max-w-site' : 'max-w-form'}`}>
        {back && (
          <button className="mb-2 hidden items-center gap-1 text-[15px] font-semibold text-ink-soft hover:text-ink lg:inline-flex"
            onClick={() => (typeof back === 'string' ? nav(back) : nav(-1))}>
            <Svg d={Icon.back} size={18} width={2.5} />{t('back')}
          </button>
        )}
        {title && <h1 className="sr-only lg:not-sr-only lg:mb-6 lg:text-[32px] lg:font-extrabold lg:leading-tight">{title}</h1>}
        {children}
      </main>
      <SiteFooter />
    </div>
  )
}

/** Main column and a summary column that stays in view on a laptop; on a phone the summary follows the content. */
export function Split({ children, aside }: { children: ReactNode; aside: ReactNode }) {
  return (
    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start lg:gap-8 xl:grid-cols-[minmax(0,1fr)_410px]">
      <div className="min-w-0">{children}</div>
      <aside className="mt-6 space-y-4 lg:sticky lg:top-24 lg:mt-0">{aside}</aside>
    </div>
  )
}

export function Card({ title, children, className = '' }: { title?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card p-5 ${className}`}>
      {title && <h2 className="section-title mb-3">{title}</h2>}
      {children}
    </section>
  )
}

/** Why the button can't be pressed yet: never leave someone staring at a grey button. */
export function Hint({ children }: { children: ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-[14px] leading-snug text-ink-soft" role="status">
      <span className="mt-0.5 shrink-0 text-ink-faint"><Svg d={Icon.info} size={16} /></span>{children}
    </p>
  )
}

export function SiteFooter({ always = false }: { always?: boolean }) {
  const { t } = useLang()
  return (
    <footer className={`${always ? '' : 'hidden lg:block'} border-t border-rule bg-white`}>
      <div className="mx-auto flex max-w-site flex-wrap items-center justify-between gap-x-8 gap-y-3 px-4 py-6 text-[14px] text-ink-soft lg:px-8">
        <Logo small />
        <nav className="flex flex-wrap gap-x-6 gap-y-2" aria-label="More">
          <Link className="hover:text-ink" to="/verify">{t('nav_check')}</Link>
          <Link className="hover:text-ink" to="/partner">{t('partner_mode')}</Link>
          <Link className="hover:text-ink" to="/judge">Judge console</Link>
        </nav>
        <p className="w-full text-[13px] text-ink-faint">Accel Telecom and Accel Business are fictional. All data is synthetic, built for the Airtel SYNC hackathon. Payments run in test mode.</p>
      </div>
    </footer>
  )
}

export function Toggle({ on, onChange, label, disabled = false }: { on: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button role="switch" aria-checked={on} aria-label={label} disabled={disabled} onClick={() => onChange(!on)}
      className={`relative h-7 w-12 shrink-0 rounded-pill transition-colors ${on ? 'bg-leaf' : 'bg-rule-strong'} ${disabled ? 'opacity-60' : ''}`}>
      <span className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow transition-all ${on ? 'left-6' : 'left-1'}`} />
    </button>
  )
}

export function Stamp({ kind, children, animate = true }: { kind: 'ok' | 'fix' | 'review'; children: ReactNode; animate?: boolean }) {
  const color = kind === 'ok' ? 'text-leaf' : kind === 'fix' ? 'text-haldi-dark' : 'text-kumkum'
  return <span className={`stamp ${color} ${animate ? 'stamp-in' : ''}`}>{children}</span>
}

export function Working({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-ink-soft" role="status">
      <span className="inline-block h-5 w-5 animate-spin rounded-full border-[3px] border-rule border-t-kumkum" aria-hidden="true" />
      {label}
    </div>
  )
}

export function ErrorNote({ msg }: { msg: string | null }) {
  if (!msg) return null
  return <p className="mt-3 rounded-xl border border-kumkum/20 bg-kumkum-soft px-4 py-3 text-kumkum-dark" role="alert">{msg}</p>
}

/** The step's main action: pinned to the bottom on a phone, in the flow (usually the summary column) on a laptop. */
export function StickyBar({ children, hint }: { children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-rule bg-white/95 shadow-[0_-10px_30px_-18px_rgba(16,24,40,.35)] backdrop-blur-md lg:static lg:z-auto lg:mt-5 lg:border-0 lg:bg-transparent lg:shadow-none lg:backdrop-blur-none"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <div className="mx-auto max-w-form px-4 py-3 lg:max-w-none lg:p-0">
        {hint && <div className="mb-2">{hint}</div>}
        <div className="flex items-center gap-3">{children}</div>
      </div>
    </div>
  )
}
