import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { LANGS, STRINGS, type Lang } from '../i18n/strings'
import { store } from './api'

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (key: string, vars?: Record<string, string | number>) => string; bcp: string }
const LangCtx = createContext<Ctx | null>(null)

export function LangProvider({ children }: { children: ReactNode }) {
  const initial = (new URLSearchParams(location.search).get('lang') || store('lang') || 'en') as Lang
  const [lang, setLangState] = useState<Lang>(LANGS.some((l) => l.code === initial) ? initial : 'en')
  const meta = LANGS.find((l) => l.code === lang)!

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.style.setProperty('--font', `'${meta.font}', 'Baloo 2'`)
  }, [lang, meta.font])

  const value = useMemo<Ctx>(() => ({
    lang,
    bcp: meta.bcp,
    setLang: (l) => { setLangState(l); store('lang', l) },
    t: (key, vars) => {
      let s = STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v))
      return s
    },
  }), [lang, meta.bcp])
  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>
}

export function useLang() {
  const c = useContext(LangCtx)
  if (!c) throw new Error('LangProvider missing')
  return c
}
