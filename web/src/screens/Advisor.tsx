import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LangSwitch, Logo, ErrorNote } from '../components/ui'
import WhyPanel from '../components/WhyPanel'
import { api, rupees, store, type SessionView, type Turn } from '../lib/api'
import { useLang } from '../lib/i18n'
import { speak, stopSpeaking, useVoice, type SpeakState } from '../lib/voice'

export default function Advisor() {
  const { lang, t, bcp } = useLang()
  const nav = useNavigate()
  const params = new URLSearchParams(location.search)
  const [session, setSession] = useState<SessionView | null>(null)
  const [turn, setTurn] = useState<Turn | null>(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [why, setWhy] = useState(false)
  const [sayState, setSayState] = useState<SpeakState>('idle')
  const endRef = useRef<HTMLDivElement>(null)
  const started = useRef(false)
  const ready = useRef<Promise<string> | null>(null)  // a message typed before the session exists waits for it

  useEffect(() => {
    if (started.current) return
    started.current = true
    const existing = params.get('session')
    const go = async () => {
      try {
        const s = existing
          ? await api.get<SessionView>(`/api/advisor/sessions/${existing}`)
          : await api.post<SessionView>('/api/advisor/sessions', { language: lang, channel: params.get('partner') ? 'partner' : 'web', partner_id: params.get('partner') }, { 'X-Staff-Token': sessionStorage.getItem('staff_token') || '' })
        setSession(s)
        setTurn(s.turn)
        store('session', s.session_id)
        if (!existing) history.replaceState(null, '', `/advisor?session=${s.session_id}`)
        const say = params.get('say')
        if (say) send(say, s.session_id)
        return s.session_id
      } catch (e: any) {
        setErr(e.message)
        throw e
      }
    }
    ready.current = go().catch(() => '')
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [session?.messages.length, busy])

  const send = useCallback(async (msg: string, sid?: string) => {
    if (!msg.trim()) return
    setBusy(true)
    setErr(null)
    setText('')
    try {
      const id = sid || session?.session_id || (await ready.current)
      if (!id) { setText(msg); return }
      setSession((s) => (s ? { ...s, messages: [...s.messages, { role: 'user', text: msg }] } : s))
      const s = await api.post<SessionView>(`/api/advisor/sessions/${id}/messages`, { text: msg, language: lang })
      setSession(s)
      setTurn(s.turn)
    } catch (e: any) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }, [session?.session_id, lang])

  // a tap on a price question is a typed patch: exact, no model in the loop
  const patch = useCallback(async (p: Record<string, any>) => {
    if (!session) return
    setBusy(true)
    try {
      const s = await api.post<SessionView>(`/api/advisor/sessions/${session.session_id}/profile`, p)
      setSession(s)
      setTurn(s.turn)
    } catch (e: any) { setErr(e.message) } finally { setBusy(false) }
  }, [session])

  const voice = useVoice(bcp, (spoken) => setText(spoken))  // heard words land in the box: the owner confirms before sending
  const bundle = session?.bundle
  const lastAi = [...(session?.messages ?? [])].reverse().find((m) => m.role === 'assistant')

  return (
    <div className="flex h-[100dvh] flex-col">
      <header className="sticky top-0 z-20 border-b border-rule bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4">
          <Logo small />
          <div className="flex items-center gap-2">
            <button className="chip whitespace-nowrap lg:hidden" onClick={() => setWhy(!why)} aria-expanded={why}>{t('why_panel')}</button>
            <LangSwitch />
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-h-0 w-full max-w-6xl flex-1 gap-6 px-0 lg:px-4">
        <section className="flex min-h-0 w-full max-w-[480px] flex-1 flex-col lg:mx-0 mx-auto" aria-label="Conversation">
          {session?.partner_id && <p className="mx-4 mt-3 rounded-lg bg-haldi-soft px-3 py-2 text-[15px] text-haldi-dark">Assisted by partner {session.partner_id}</p>}
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
            {session?.messages.map((m, i) => (
              <div key={i} className={m.role === 'user' ? 'bubble-me' : 'bubble-ai'}>
                {m.text}
                {m.role === 'assistant' && m === lastAi && (
                  <button className="mt-2 flex items-center gap-1.5 rounded-pill border border-ledger/40 px-3 py-1 text-[14px] font-semibold text-ledger"
                    onClick={() => (sayState === 'idle' ? speak(m.text, bcp, setSayState) : (stopSpeaking(), setSayState('idle')))}
                    aria-label={t('read_aloud')} aria-pressed={sayState !== 'idle'}>
                    {sayState === 'loading' ? <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-rule border-t-ledger" aria-hidden="true" />
                      : sayState === 'playing' ? <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><rect x="6" y="6" width="12" height="12" rx="2" /></svg>
                      : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16 9a4 4 0 0 1 0 6" /></svg>}
                    {t('read_aloud')}
                  </button>
                )}
              </div>
            ))}
            {busy && <div className="bubble-ai w-16 text-center text-ink-faint" aria-label="Typing">…</div>}
            {bundle && turn?.stage === 'recommended' && (
              <div className="khata mt-2">
                <p className="row text-[18px] font-bold">{bundle.name}</p>
                {bundle.lines.map((ln) => (
                  <div key={ln.product_id} className="row justify-between gap-3">
                    <span className="flex min-w-0 gap-1"><span className="truncate">{ln.name}</span>{ln.qty > 1 && <span className="shrink-0">×{ln.qty}</span>}</span>
                    <span className="money shrink-0 whitespace-nowrap">{rupees(ln.monthly)}</span>
                  </div>
                ))}
                <div className="row justify-between border-t-2 border-ink">
                  <span className="font-bold">{t('a_month')}</span>
                  <span className="money text-[22px] text-kumkum">{rupees(bundle.monthly)}</span>
                </div>
                {turn.diff && (turn.diff.added.length + turn.diff.removed.length + turn.diff.changed.length > 0) && (
                  <p className="row-free mt-2 rounded-lg bg-ledger-soft px-3 py-2 text-[15px] text-ledger" role="status">
                    <span className="font-semibold">{t('quote_changed')}: </span>
                    {[...turn.diff.removed.map((n) => `− ${n}`), ...turn.diff.added.map((n) => `+ ${n}`), ...turn.diff.changed.map((c) => `${c.name} ${c.from}→${c.to}`)].join(' · ')}
                  </p>
                )}
                {turn.refine?.map((r) => (
                  <div key={r.key} className="mt-3 rounded-lg border border-rule p-3">
                    <p className="text-[13px] font-semibold uppercase tracking-wide text-ink-soft">{t('refine_title')}</p>
                    <p className="mt-1 font-semibold">{r.question}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {r.options.map((o) => (
                        <button key={o.label} className="chip" onClick={() => patch(o.patch)}>
                          {o.label}{o.monthly_delta ? <span className="ml-1 text-ink-soft">{o.monthly_delta > 0 ? '+' : '−'}{rupees(Math.abs(o.monthly_delta))}</span> : null}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                <button className="btn-primary mt-3 w-full" onClick={() => nav(`/quote?session=${session!.session_id}`)}>{t('see_quote')}</button>
              </div>
            )}
            {turn?.stage === 'handoff' && (
              <button className="btn-primary w-full" onClick={() => nav(`/help?session=${session!.session_id}&source=advisor`)}>{t('call_me')}</button>
            )}
            <div ref={endRef} />
          </div>

          <div className="sticky bottom-0 border-t border-rule bg-white px-4 pb-3 pt-2" style={{ paddingBottom: 'max(12px, env(safe-area-inset-bottom))' }}>
            {turn?.quick_replies?.length ? (
              <div className="mb-2 flex flex-wrap gap-2">
                {turn.quick_replies.map((q) => (
                  <button key={q} className="chip" onClick={() => (turn.stage === 'recommended' && q === turn.quick_replies[0] ? nav(`/quote?session=${session!.session_id}`) : send(q))}>{q}</button>
                ))}
              </div>
            ) : null}
            <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); send(text) }}>
              {voice.supported && (
                <button type="button" onClick={voice.listening ? voice.stop : voice.start} aria-label={voice.listening ? t('listening') : t('speak')}
                  className={`grid h-12 w-12 shrink-0 place-items-center rounded-full border-2 ${voice.listening ? 'animate-pulse border-kumkum bg-kumkum text-white' : 'border-rule text-ledger'}`}>
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
                </button>
              )}
              <input className="field flex-1" value={text} onChange={(e) => setText(e.target.value)} placeholder={voice.listening ? t('listening') : t('type_message')} aria-label={t('type_message')} />
              <button className="btn-primary h-12 px-4" disabled={busy || !text.trim()} aria-label={t('send')}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 20l18-8L3 4v6l12 2-12 2z" /></svg>
              </button>
            </form>
            <p className="mt-2 text-[13px] text-ink-faint">{t('privacy_line')}</p>
            <ErrorNote msg={err} />
          </div>
        </section>

        <aside className={`${why ? 'fixed inset-x-0 bottom-0 top-16 z-30 overflow-y-auto bg-white p-5' : 'hidden'} lg:static lg:block lg:w-[380px] lg:shrink-0 lg:overflow-y-auto lg:border-l lg:border-rule lg:p-6`} aria-label={t('why_panel')}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[19px] font-bold">{t('why_panel')}</h2>
            <button className="btn-quiet lg:hidden" onClick={() => setWhy(false)}>Close</button>
          </div>
          <WhyPanel turn={turn} profile={session?.profile} />
        </aside>
      </div>
    </div>
  )
}
