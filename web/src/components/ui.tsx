import { useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LANGS } from '../i18n/strings'
import { useLang } from '../lib/i18n'

export function Logo({ small = false }: { small?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2" aria-label="Accel Business home">
      <svg width={small ? 28 : 34} height={small ? 28 : 34} viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="14" fill="#C8102E" />
        <path d="M14 46 L32 14 L50 46" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M22 36 H42" stroke="#F2A900" strokeWidth="6" strokeLinecap="round" />
      </svg>
      <span className="leading-none">
        <span className="block font-extrabold text-[19px] tracking-tight text-ink">Accel Business</span>
        {!small && <span className="block text-[12px] text-ink-soft">Udyam Digital</span>}
      </span>
    </Link>
  )
}

export function LangSwitch() {
  const { lang, setLang } = useLang()
  const [open, setOpen] = useState(false)
  const current = LANGS.find((l) => l.code === lang)!
  return (
    <div className="relative">
      <button className="chip whitespace-nowrap" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Change language">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="mr-1.5" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" /></svg>
        {current.name}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 grid w-64 grid-cols-2 gap-1 rounded-xl border border-rule bg-white p-2 shadow-lg">
          {LANGS.map((l) => (
            <button key={l.code} onClick={() => { setLang(l.code); setOpen(false) }}
              className={`rounded-lg px-3 py-2 text-left hover:bg-ledger-soft ${l.code === lang ? 'bg-ledger-soft font-bold text-ledger' : ''}`}>
              {l.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function Shell({ children, back, title, wide = false, right }: { children: ReactNode; back?: string | boolean; title?: string; wide?: boolean; right?: ReactNode }) {
  const nav = useNavigate()
  const { t } = useLang()
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-rule bg-white/95 backdrop-blur">
        <div className={`mx-auto flex h-16 items-center justify-between gap-3 px-4 ${wide ? 'max-w-6xl' : 'max-w-[480px]'}`}>
          <div className="flex items-center gap-2">
            {back && (
              <button className="btn-quiet -ml-3 px-2" onClick={() => (typeof back === 'string' ? nav(back) : nav(-1))} aria-label={t('back')}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
              </button>
            )}
            {title ? <h1 className="truncate text-[20px] font-bold">{title}</h1> : <Logo />}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {title && (
              <Link to="/" className="btn-quiet px-2" aria-label={t('home')} title={t('home')}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true"><path d="M3 11l9-7 9 7" /><path d="M5 10v10h5v-6h4v6h5V10" /></svg>
              </Link>
            )}
            {right ?? <LangSwitch />}
          </div>
        </div>
      </header>
      <main className={`mx-auto px-4 pb-28 pt-4 ${wide ? 'max-w-6xl' : 'max-w-[480px]'}`}>{children}</main>
    </div>
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
      <span className="inline-block h-5 w-5 animate-spin rounded-full border-[3px] border-rule border-t-ledger" aria-hidden="true" />
      {label}
    </div>
  )
}

export function ErrorNote({ msg }: { msg: string | null }) {
  if (!msg) return null
  return <p className="mt-3 rounded-lg bg-kumkum-soft px-4 py-3 text-kumkum-dark" role="alert">{msg}</p>
}

export function StickyBar({ children }: { children: ReactNode }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-rule bg-white/95 backdrop-blur" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
      <div className="mx-auto flex max-w-[480px] items-center gap-3 px-4 py-3">{children}</div>
    </div>
  )
}
