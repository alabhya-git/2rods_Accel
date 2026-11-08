import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Stamp, Svg, Toggle } from '../components/ui'
import { SAYS } from '../i18n/call'
import { LANGS } from '../i18n/strings'
import { api, paise, rememberOrder, rupees, store, type Check, type KycResult, type OrderView, type SessionView } from '../lib/api'
import { CallEngine, browserHear, phoneIn, sentences, voiceOf } from '../lib/call'
import { useLang } from '../lib/i18n'

/** The AI call: the whole journey by voice, in the owner's language. The advisor and the rules engine are the same
 *  as the chat; the call adds ears, a voice, and cards for what must be tapped (consent, documents, payment). */

type Voice = 'idle' | 'speaking' | 'listening' | 'hearing' | 'thinking' | 'muted'
type Step = 'business' | 'plan' | 'details' | 'consent' | 'documents' | 'pay' | 'done'
const FLOW: [string, Step[]][] = [['business', ['business']], ['plan', ['plan', 'details']], ['consent', ['consent']], ['documents', ['documents']], ['pay', ['pay', 'done']]]
const ROUTE_DOCS: Record<string, string[]> = {
  gst: ['gst_certificate', 'udyam_certificate', 'address_proof', 'signatory_id'],
  udyam: ['udyam_certificate', 'address_proof', 'signatory_id'],
  shop_licence: ['shop_licence', 'address_proof', 'signatory_id'],
}
const SPECIMENS = ['K01', 'K02', 'K03', 'K04', 'K05', 'K06', 'K07', 'K08', 'K09', 'K10', 'K11', 'K12', 'K02R']
// lines with nothing to fill in: their voice is fetched at the start of the call
const AHEAD = ['call_filler', 'call_didnt_hear', 'call_consent', 'call_consent_tap', 'call_docs_route', 'call_checking', 'call_verified',
  'call_paid', 'call_step_help', 'call_need_digits', 'call_review', 'call_wait_owner', 'call_handoff']
const WINDOWS = ['asap', 'today_evening', 'tomorrow_morning', 'tomorrow_evening', 'after_9pm']
type Doc = { status: 'empty' | 'uploading' | 'read' | 'retake'; fields?: Record<string, string> }

const I = {
  phone: <path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" />,
  hang: <path d="M3 15.5c5-4.7 13-4.7 18 0l-2.2 2.6-3.6-1.3v-2.6a10 10 0 0 0-6.4 0v2.6l-3.6 1.3z" />,
  mic: <><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></>,
  micOff: <><path d="M9 9V6a3 3 0 0 1 5.7-1.3M15 11v0a3 3 0 0 1-4.6 2.5M5 11a7 7 0 0 0 11 5.7M19 11a7 7 0 0 1-.6 2.8M12 18v3M3 3l18 18" /></>,
  keys: <><rect x="2.5" y="6" width="19" height="12" rx="2.5" /><path d="M6.5 10h.01M10 10h.01M13.5 10h.01M17 10h.01M7.5 14h9" /></>,
  person: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  send: <path d="M3 20l18-8L3 4v6l12 2-12 2z" />,
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  camera: <><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></>,
  doc: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 12h6M9 16h6" /></>,
  close: <path d="M6 6l12 12M18 6L6 18" />,
}

export default function Call() {
  const { lang, setLang, t, bcp } = useLang()
  const nav = useNavigate()
  const hud = new URLSearchParams(location.search).get('hud') === '1'
  const [phase, setPhase] = useState<'lobby' | 'connecting' | 'live' | 'ended'>('lobby')
  const [voice, setVoice] = useState<Voice>('idle')
  const [step, setStep] = useState<Step>('business')
  const [caption, setCaption] = useState<{ parts: string[]; part: number; start: number; dur: number }>({ parts: [], part: 0, start: 0, dur: 0 })
  const [you, setYou] = useState('')
  const [log, setLog] = useState<{ who: 'ai' | 'you'; text: string }[]>([])
  const [session, setSession] = useState<SessionView | null>(null)
  const [order, setOrder] = useState<{ id: string; key: string } | null>(null)
  const [muted, setMuted] = useState(false)
  const [typing, setTyping] = useState(false)
  const [typed, setTyped] = useState('')
  const [handoff, setHandoff] = useState(false)
  const [timing, setTiming] = useState<Record<string, number>>({})
  const [started, setStarted] = useState(0)
  const [now, setNow] = useState(Date.now())
  const [err, setErr] = useState<string | null>(null)
  // the cards' own state
  const [phone, setPhone] = useState('')
  const [staff, setStaff] = useState(false)
  const [ownerPhone, setOwnerPhone] = useState('')
  const [notice, setNotice] = useState<{ version: string; purposes: Record<string, { required: boolean; data: string[] }> } | null>(null)
  const [choices, setChoices] = useState<Record<string, boolean>>({})
  const [route, setRoute] = useState<string | null>(null)
  const [docs, setDocs] = useState<Record<string, Doc>>({})
  const [kyc, setKyc] = useState<KycResult | null>(null)
  const [view, setView] = useState<OrderView | null>(null)
  const [upi, setUpi] = useState('')
  const [paid, setPaid] = useState(false)
  const [days, setDays] = useState<{ date: string; slots: string[] }[]>([])
  const [day, setDay] = useState<string | null>(null)
  const [slot, setSlot] = useState<string | null>(null)
  const [booked, setBooked] = useState<string | null>(null)
  const [cbPhone, setCbPhone] = useState('')
  const [cbWin, setCbWin] = useState('asap')
  const [cbDone, setCbDone] = useState<{ call_code: string; phone_masked: string } | null>(null)

  const engine = useRef<CallEngine | null>(null)
  const server = useRef(false)
  const busy = useRef(false)
  const lastAi = useRef('')
  const stepRef = useRef<Step>('business')
  stepRef.current = step
  const mutedRef = useRef(false)
  mutedRef.current = muted
  const files = useRef<Record<string, HTMLInputElement | null>>({})

  // server speech decides the voice; the greeting's audio is fetched while the owner reads the lobby
  useEffect(() => {
    let live = true
    fetch('/api/voice/status').then((r) => r.json()).then((s) => {
      server.current = Boolean(s.server_speech)
      return api.get<{ text: string }>(`/api/advisor/greeting?language=${lang}&channel=voice`)
    }).then((g) => { if (live) sentences(g.text).forEach((p) => voiceOf(p, lang, server.current)) }).catch(() => {})
    return () => { live = false }
  }, [lang])

  useEffect(() => () => engine.current?.close(), [])
  useEffect(() => {
    if (phase !== 'live') return
    const h = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(h)
  }, [phase])

  const mark = (k: string, ms: number) => setTiming((x) => ({ ...x, [k]: Math.round(ms) }))

  const listen = useCallback(() => {
    const e = engine.current
    if (!e) return
    if (mutedRef.current || !e.hasMic) {
      e.mode = 'off'
      setVoice(mutedRef.current ? 'muted' : 'listening')
      return
    }
    setVoice('listening')
    if (!server.current) { // no server speech: the browser hears one turn
      e.mode = 'off'
      browserHear(bcp).then((text) => { if (text) handleRef.current(text); else if (stepRef.current !== 'done') listen() })
      return
    }
    setTimeout(() => { if (engine.current === e && !busy.current && e.mode !== 'barge') e.mode = 'listen' }, 250) // let the room's echo die first
  }, [bcp])

  /** Say a line: sentence by sentence, the first already playing while the rest is made. */
  const say = useCallback(async (text: string): Promise<boolean> => {
    const e = engine.current
    if (!e || !text.trim()) return false
    const parts = sentences(text)
    lastAi.current = text
    setLog((l) => [...l, { who: 'ai', text }])
    setCaption({ parts, part: 0, start: performance.now(), dur: -1 }) // words appear with the voice, not before it
    setVoice('thinking')
    e.mode = e.hasMic && !mutedRef.current && server.current ? 'barge' : 'off'
    const t0 = performance.now()
    let first = true
    const done = await e.play(parts.map((p) => ({ text: p, audio: voiceOf(p, lang, server.current) })), bcp, (i, dur) => {
      if (first) { mark('voice', performance.now() - t0); setVoice('speaking'); first = false }
      setCaption({ parts, part: i, start: performance.now(), dur })
    })
    setCaption((c) => ({ ...c, part: parts.length - 1, dur: 0 }))
    if (done) listen()
    return done
  }, [bcp, lang, listen])

  const advisorTurn = useCallback(async (text: string) => {
    const e = engine.current!
    busy.current = true
    setVoice('thinking')
    e.mode = 'off'
    const t0 = performance.now()
    let filler: Promise<boolean> | null = null // a pause longer than a breath gets a word, like a person on the phone
    const h = setTimeout(() => { filler = e.play([{ text: t('call_filler'), audio: voiceOf(t('call_filler'), lang, server.current) }], bcp, () => {}) }, 1400)
    try {
      const s = await api.post<SessionView>(`/api/advisor/sessions/${session!.session_id}/messages`, { text, language: lang })
      clearTimeout(h)
      if (filler) await filler
      mark('reply', performance.now() - t0)
      setSession(s)
      const turn = s.turn!
      if (turn.stage === 'recommended') setStep('plan')
      if (turn.stage === 'accepted') setStep('details')
      if (turn.stage === 'handoff') openHandoff(false)
      busy.current = false
      await say(turn.text)
    } catch {
      clearTimeout(h)
      busy.current = false
      await say(t('call_didnt_hear'))
    }
  }, [bcp, lang, say, session, t]) // eslint-disable-line react-hooks/exhaustive-deps

  /** Whatever the owner said or typed, at whatever step they are. Rebuilt every render, so it never sees an old order. */
  const handle = async (text: string) => {
    setYou(text)
    setLog((l) => [...l, { who: 'you', text }])
    const st = stepRef.current
    if (SAYS.repeat.test(text) && text.split(/\s+/).length <= 4 && lastAi.current) return void say(lastAi.current)
    if (st === 'business' || st === 'plan') return void advisorTurn(text)
    if (SAYS.person.test(text)) return void openHandoff(true)
    if (st === 'details') {
      const p = phoneIn(text)
      if (p) {
        setPhone(p)
        return void say(t('call_phone_heard', { digits: p.split('').join(' ') }))
      }
      return void say(t('call_need_digits'))
    }
    if (st === 'consent') return void say(t('call_consent_tap'))
    if (st === 'documents' && !route) {
      const r = SAYS.udyam.test(text) ? 'udyam' : SAYS.shop.test(text) ? 'shop_licence' : SAYS.gst.test(text) && !SAYS.no.test(text) ? 'gst' : null
      if (r) return void chooseRoute(r)
      return void say(t('call_docs_route'))
    }
    return void say(t('call_step_help'))
  }
  const handleRef = useRef(handle)
  handleRef.current = handle

  const heard = useCallback(async (wav: Blob) => {
    if (busy.current) return
    busy.current = true
    const e = engine.current!
    e.mode = 'off'
    setVoice('thinking')
    const t0 = performance.now()
    let text = ''
    try {
      const fd = new FormData()
      fd.append('audio', wav, 'turn.wav')
      fd.append('language', lang)
      text = (await api.post<{ text: string }>('/api/voice/transcribe', fd)).text?.trim() ?? ''
    } catch { /* said below */ }
    mark('heard', performance.now() - t0)
    busy.current = false
    if (!text) return void say(t('call_didnt_hear'))
    handleRef.current(text)
  }, [lang, say, t])
  const heardRef = useRef(heard)
  heardRef.current = heard

  // ---- the call ----
  const start = async () => {
    setPhase('connecting')
    setErr(null)
    try {
      const e = await CallEngine.open() // first, inside the tap: sound and microphone are allowed from here
      engine.current = e
      e.onUtterance = (wav) => heardRef.current(wav)
      e.onSpeechStart = () => setVoice('hearing')
      e.onBargeIn = () => { setVoice('hearing'); setCaption((c) => ({ ...c, dur: 0 })) }
      e.onDiscard = () => { if (!busy.current) setVoice('listening') }
      const s = await api.post<SessionView>('/api/advisor/sessions', { language: lang, channel: 'voice' })
      store('session', s.session_id)
      setSession(s)
      setStarted(Date.now())
      setPhase('live')
      if (!e.hasMic) setTyping(true)
      say(s.turn!.text)
      setTimeout(() => AHEAD.forEach((k) => sentences(t(k)).forEach((p) => voiceOf(p, lang, server.current))), 3000)
    } catch (x: any) {
      engine.current?.close()
      engine.current = null
      setErr(x?.message || 'Could not start the call')
      setPhase('lobby')
    }
  }

  const end = () => {
    engine.current?.close()
    engine.current = null
    setPhase('ended')
  }

  const toggleMute = () => {
    const m = !muted
    setMuted(m)
    mutedRef.current = m
    const e = engine.current
    if (!e) return
    if (m) { e.mode = 'off'; if (voice !== 'speaking' && voice !== 'thinking') setVoice('muted') } else if (voice === 'muted') listen()
  }

  const interrupt = () => {
    engine.current?.stop()
    listen()
  }

  const sendTyped = () => {
    const text = typed.trim()
    if (!text || busy.current) return
    setTyped('')
    engine.current?.stop()
    handle(text)
  }

  // ---- what the cards do ----
  const openHandoff = (speak: boolean) => {
    setHandoff(true)
    setCbPhone((p) => p || phone)
    if (speak) say(t('call_handoff'))
  }

  const callback = async () => {
    setErr(null)
    try {
      const r = await api.post<{ phone_masked: string; call_code: string }>('/api/help', {
        phone: cbPhone, window: cbWin, language: lang, source: 'call', session_id: session?.session_id, order_id: order?.id, key: order?.key, reason: 'prefer_person' })
      setCbDone(r)
      say(t('call_handoff_done', { code: r.call_code.split('').join(' ') }))
    } catch (x: any) { setErr(x.message) }
  }

  const placeOrder = async () => {
    const b = session?.bundle
    if (!b) return
    setErr(null)
    try {
      const o = await api.post<OrderView>('/api/orders', { session_id: session!.session_id, items: Object.fromEntries(b.lines.map((l) => [l.product_id, l.qty])),
        term_months: b.term_months || 12, setup_emi: false, phone, placed_by: staff ? 'staff' : 'owner', owner_phone: staff ? ownerPhone : undefined })
      rememberOrder(o.order_id!, o.access_key!)
      setOrder({ id: o.order_id!, key: o.access_key! })
      const n = await api.get<{ version: string; purposes: Record<string, { required: boolean; data: string[] }> }>('/api/consent/notice')
      setNotice(n)
      setChoices(Object.fromEntries(Object.entries(n.purposes).map(([k, p]) => [k, p.required])))
      setStep('consent')
      say(t('call_consent'))
    } catch (x: any) { setErr(x.message) }
  }

  const agree = async () => {
    setErr(null)
    try {
      await api.post(`/api/orders/${order!.id}/consent?key=${order!.key}`, { choices, language: lang, channel: 'voice' })
      setStep('documents')
      say(t('call_docs_route'))
    } catch (x: any) { setErr(x.message) }
  }

  const chooseRoute = async (r: string) => {
    setErr(null)
    try {
      const out = await api.post<{ route: string }>(`/api/orders/${order!.id}/kyc/route?key=${order!.key}`, { route: r })
      setRoute(out.route)
      setDocs(Object.fromEntries(ROUTE_DOCS[out.route].map((d) => [d, { status: 'empty' }])))
      say(t('call_docs_upload', { docs: ROUTE_DOCS[out.route].map((d) => t(`doc_${d}`)).join(', ') }))
    } catch (x: any) { setErr(x.message) }
  }

  const outcome = async (result: KycResult) => {
    setKyc(result)
    if (result.outcome === 'verified') {
      const v = await loadPay()
      setStep('pay')
      const owner = v.approvals?.filter((a) => a.kind === 'owner').slice(-1)[0]
      if (!(await say(t('call_verified')))) return
      return void say(owner && owner.status !== 'approved' ? t('call_wait_owner') : t('call_pay', { due: paise((v.bundle as any).schedule.due_today) }))
    }
    if (result.outcome === 'review') {
      setStep('done')
      return void say(t('call_review'))
    }
    const fail = result.checks.find((c: Check) => c.status === 'fail')
    say(`${t('call_fix')} ${fail ? fail.args?.local_fix ?? fail.fix ?? fail.message : ''}`)
  }

  // the check runs while the assistant says it is checking; the result is spoken when both are done
  const check = async () => {
    setErr(null)
    try {
      const [, r] = await Promise.all([say(t('call_checking')), api.post<{ result: KycResult }>(`/api/orders/${order!.id}/kyc/evaluate?key=${order!.key}`)])
      await outcome(r.result)
    } catch (x: any) { setErr(x.message) }
  }

  const upload = async (doc: string, file: File) => {
    setDocs((d) => ({ ...d, [doc]: { status: 'uploading' } }))
    const fd = new FormData()
    fd.append('doc_type', doc)
    fd.append('file', file)
    try {
      const r = await api.post<any>(`/api/orders/${order!.id}/kyc/documents?key=${order!.key}`, fd)
      const bad = r.quality.blurred || r.quality.faint || (r.quality.detected && r.quality.detected !== doc)
      const next = { ...docs, [doc]: { status: bad ? 'retake' : 'read', fields: r.fields } as Doc }
      setDocs(next)
      if (bad) return void say(t('call_doc_retake', { doc: t(`doc_${doc}`) }))
      if (Object.values(next).every((d) => d.status === 'read')) return void check() // the last one in: check them all, no tap needed
      say(t('call_doc_ok', { doc: t(`doc_${doc}`) }))
    } catch (x: any) {
      setErr(x.message)
      setDocs((d) => ({ ...d, [doc]: { status: 'empty' } }))
    }
  }

  const specimen = async (k: string) => {
    setErr(null)
    try {
      // the specimens are GST applicants: check them on that route, whatever was said before
      const go = api.post(`/api/orders/${order!.id}/kyc/route?key=${order!.key}`, { route: 'gst' })
        .then(() => api.post<any>(`/api/orders/${order!.id}/kyc/specimen?key=${order!.key}`, { specimen: k }))
      const [, r] = await Promise.all([say(t('call_checking')), go])
      setRoute('gst')
      setDocs(Object.fromEntries(r.documents.map((d: any) => [d.doc_type, { status: d.quality.blurred || d.quality.faint ? 'retake' : 'read', fields: d.fields }])))
      await outcome(r.result)
    } catch (x: any) { setErr(x.message) }
  }

  const loadPay = async () => {
    const [v, s] = await Promise.all([api.get<OrderView>(`/api/orders/${order!.id}?key=${order!.key}`), api.get<{ days: { date: string; slots: string[] }[] }>(`/api/orders/${order!.id}/slots?key=${order!.key}`)])
    setView(v)
    setDays(s.days)
    setDay(s.days[0]?.date ?? null)
    return v
  }

  const pay = async () => {
    setErr(null)
    try {
      await api.post(`/api/orders/${order!.id}/pay?key=${order!.key}`, { method: 'upi_autopay', upi_id: upi })
      setPaid(true)
      say(t('call_paid'))
    } catch (x: any) { setErr(x.message) }
  }

  const fmtDay = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString(bcp, { weekday: 'short', day: 'numeric', month: 'short' })
  const book = async () => {
    setErr(null)
    try {
      await api.post(`/api/orders/${order!.id}/schedule?key=${order!.key}`, { slot: `${day} ${slot}` })
      const when = `${fmtDay(day!)}, ${slot}`
      setBooked(when)
      setStep('done')
      if (await say(t('call_done', { slot: when }))) setTimeout(end, 1200) // a call ends when it's done, like a call
    } catch (x: any) { setErr(x.message) }
  }

  // ---- screens ----
  if (phase === 'lobby' || phase === 'connecting') {
    return (
      <Stage>
        <header className="mx-auto flex w-full max-w-site items-center justify-between px-4 pt-4 lg:px-8">
          <Link to="/" className="btn-quiet -ml-2 px-2 text-ink-soft" aria-label={t('home')}><Svg d={<path d="M15 5l-7 7 7 7" />} width={2.5} /></Link>
          <Mark />
          <span className="w-10" />
        </header>
        <main className="mx-auto flex w-full max-w-[560px] flex-1 flex-col items-center px-4 pb-8 pt-2 text-center">
          <Orb engine={null} voice={phase === 'connecting' ? 'thinking' : 'idle'} size={210} />
          <h1 className="mt-2 text-[30px] font-extrabold leading-tight lg:text-[38px]">{t('call_title')}</h1>
          <p className="mt-2 text-[17px] leading-snug text-ink-soft">{t('call_sub')}</p>
          <div className="mt-6 grid w-full grid-cols-5 gap-1.5" role="radiogroup" aria-label={t('choose_language')}>
            {LANGS.map((l) => (
              <button key={l.code} role="radio" aria-checked={l.code === lang} onClick={() => setLang(l.code)} lang={l.code}
                style={{ fontFamily: `'${l.font}', 'Baloo 2'` }}
                className={`h-11 rounded-xl text-[14px] font-bold transition ${l.code === lang ? 'bg-kumkum text-onbrand shadow-brand' : 'bg-white/[.06] text-ink-soft ring-1 ring-white/10 hover:text-ink'}`}>
                {l.name}
              </button>
            ))}
          </div>
          <button onClick={start} disabled={phase === 'connecting'}
            className="group relative mt-7 flex h-16 w-full max-w-sm items-center justify-center gap-3 rounded-pill text-[19px] font-bold text-onbrand shadow-brand transition [background-image:linear-gradient(135deg,#ef233c,#b30c24)] hover:brightness-110 disabled:opacity-70">
            <span className="absolute inset-0 animate-ping rounded-pill bg-kumkum/30 [animation-duration:2.4s]" aria-hidden="true" />
            <span className="relative"><Svg d={I.phone} size={24} /></span>
            <span className="relative">{phase === 'connecting' ? t('call_connecting') : t('call_start')}</span>
          </button>
          <Link to="/help?source=call" className="mt-4 text-[15px] font-semibold text-ink-soft underline-offset-4 hover:text-ink hover:underline">{t('call_person_cta')}</Link>
          {err && <p className="mt-4 rounded-xl bg-kumkum/15 px-3 py-2 text-[15px] text-kumkum-dark" role="alert">{err}</p>}
          <div className="mt-auto space-y-2 pt-8 text-left text-[13px] leading-snug text-ink-faint">
            <p className="flex gap-2"><span className="mt-0.5 shrink-0"><Svg d={I.person} size={16} /></span>{t('call_ai_note')}</p>
            <p className="flex gap-2"><span className="mt-0.5 shrink-0"><Svg d={<><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" /></>} size={16} /></span>{t('call_privacy')}</p>
          </div>
        </main>
      </Stage>
    )
  }

  const secs = Math.max(0, Math.floor(((phase === 'ended' ? now : Date.now()) - started) / 1000))
  const clock = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`

  if (phase === 'ended') {
    return (
      <Stage>
        <main className="mx-auto flex w-full max-w-[560px] flex-1 flex-col px-4 py-10">
          <div className="text-center">
            <div className="mb-10 flex justify-center"><Mark /></div>
            {booked
              ? <span className="mx-auto grid h-20 w-20 animate-rise place-items-center rounded-full bg-leaf text-onbrand shadow-[0_10px_40px_-10px_rgba(34,160,90,.8)]"><Svg d={I.check} size={40} width={3} /></span>
              : <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-white/[.06] text-ink-soft ring-1 ring-white/10"><Svg d={I.hang} size={30} /></span>}
            <h1 className="mt-4 text-[28px] font-extrabold">{t('call_ended')}</h1>
            <p className="mt-1 text-ink-soft">{t('call_duration', { time: clock })}{order ? ` · ${t('call_order_placed', { id: order.id })}` : ''}</p>
          </div>
          {booked && <p className="mt-6 rounded-2xl bg-leaf/15 px-4 py-3 text-center font-semibold text-leaf">{booked}</p>}
          <div className="mt-6 grid gap-2 sm:grid-cols-2">
            {order && <button className="btn-primary" onClick={() => nav(`/track/${order.id}?key=${order.key}`)}>{t('track_title')}</button>}
            <button className="btn-secondary" onClick={() => location.reload()}>{t('call_again')}</button>
            {!order && <Link to="/" className="btn-quiet">{t('home')}</Link>}
          </div>
          <details className="mt-8 rounded-2xl bg-white/[.04] p-4 ring-1 ring-white/10" open={!order}>
            <summary className="cursor-pointer font-semibold">{t('call_transcript')}</summary>
            <ol className="mt-3 space-y-2 text-[15px]">
              {log.map((m, i) => <li key={i} className={m.who === 'you' ? 'text-ink' : 'text-ink-soft'}><b className="mr-1.5">{m.who === 'you' ? t('call_you') : 'AI'}:</b>{m.text}</li>)}
            </ol>
          </details>
        </main>
      </Stage>
    )
  }

  const flowAt = step === 'done' ? FLOW.length : FLOW.findIndex(([, s]) => s.includes(step))
  const bundle = session?.bundle
  const prof = session?.profile ?? {}
  const sched = (view?.bundle as any)?.schedule
  const owner = view?.approvals?.filter((a) => a.kind === 'owner').slice(-1)[0]
  const waiting = owner && owner.status !== 'approved'
  const rented = kyc?.checks.find((c) => c.status === 'fail' && c.id === 'address_proof.name' && c.args?.rented)
  const understood: [string, string][] = ([
    [t('call_flow_business'), prof.business_type], [t('staff_label'), prof.employees], [t('city_label'), prof.city],
    ['GST', prof.has_gstin === true ? t('yes_word') : prof.has_gstin === false ? t('no_word') : null],
  ] as [string, any][]).filter(([, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) => [k, String(v)])

  const card: ReactNode = handoff ? (
    <Panel title={t('callback_title')} onClose={cbDone ? undefined : () => setHandoff(false)}>
      {cbDone ? (
        <div className="text-center">
          <Stamp kind="ok">✓</Stamp>
          <p className="mt-3 text-[40px] font-extrabold tracking-[0.25em] text-ledger">{cbDone.call_code}</p>
          <p className="mt-1 text-[15px] text-ink-soft">{t('call_code_note', { code: cbDone.call_code })}</p>
        </div>
      ) : (
        <>
          <input className="field text-[19px] tracking-wide" inputMode="tel" value={cbPhone} onChange={(e) => setCbPhone(e.target.value)} placeholder="98XXXXXXXX" aria-label={t('phone_label')} />
          <div className="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-label={t('when_call')}>
            {WINDOWS.map((w) => <button key={w} role="radio" aria-checked={cbWin === w} onClick={() => setCbWin(w)} className="chip">{t('w_' + w)}</button>)}
          </div>
          <button className="btn-primary mt-4 w-full" disabled={cbPhone.replace(/\D/g, '').length < 10} onClick={callback}>{t('call_me')}</button>
        </>
      )}
    </Panel>
  ) : step === 'business' ? (
    understood.length > 0 ? (
      <Panel title={t('call_understood')}>
        <dl className="grid grid-cols-2 gap-2">
          {understood.map(([k, v]) => (
            <div key={k} className="rounded-xl bg-white/[.04] px-3 py-2 ring-1 ring-white/10 animate-rise">
              <dt className="truncate text-[12px] font-semibold uppercase tracking-wide text-ink-faint">{k}</dt>
              <dd className="truncate text-[16px] font-bold">{v}</dd>
            </div>
          ))}
        </dl>
      </Panel>
    ) : null
  ) : (step === 'plan' || step === 'details') && bundle ? (
    <Panel title={bundle.name}>
      <ul className="space-y-1.5">
        {bundle.lines.map((ln) => (
          <li key={ln.product_id} className="flex items-baseline justify-between gap-3 text-[15px]">
            <span className="min-w-0 truncate">{ln.name}{ln.qty > 1 && <span className="text-ink-soft"> ×{ln.qty}</span>}</span>
            <span className="money shrink-0 whitespace-nowrap text-ink-soft">{rupees(ln.monthly)}</span>
          </li>
        ))}
        {bundle.exclusions.map((x) => <li key={x.product_id} className="truncate text-[14px] text-kumkum-dark line-through decoration-kumkum/60">{x.name}</li>)}
      </ul>
      <div className="mt-3 flex items-end justify-between border-t border-white/10 pt-3">
        <span className="text-[14px] font-semibold text-ink-soft">{t('a_month')} + GST</span>
        <span className="money text-[28px] leading-none text-kumkum">{rupees(bundle.monthly)}</span>
      </div>
      {step === 'plan' ? (
        <button className="btn-primary mt-4 w-full" onClick={() => { engine.current?.stop(); handle(t('call_go_ahead')) }}>{t('call_go_ahead')}</button>
      ) : (
        <div className="mt-4 space-y-3 border-t border-white/10 pt-4">
          <input className="field text-[19px] tracking-wide" inputMode="tel" autoComplete="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98XXXXXXXX" aria-label={t('phone_label')} />
          <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label={t('who_ordering')}>
            {[false, true].map((s) => <button key={String(s)} role="radio" aria-checked={staff === s} onClick={() => setStaff(s)} className="choice text-center text-[15px]">{t(s ? 'i_work_here' : 'i_am_owner')}</button>)}
          </div>
          {staff && <input className="field text-[17px]" inputMode="tel" value={ownerPhone} onChange={(e) => setOwnerPhone(e.target.value)} placeholder={t('owner_phone')} aria-label={t('owner_phone')} />}
          <button className="btn-primary w-full" disabled={phone.replace(/\D/g, '').length < 10 || (staff && ownerPhone.replace(/\D/g, '').length < 10)} onClick={placeOrder}>{t('place_order')}</button>
        </div>
      )}
    </Panel>
  ) : step === 'consent' && notice ? (
    <Panel title={t('consent_title')}>
      <ul className="divide-y divide-white/10">
        {Object.entries(notice.purposes).map(([k, p]) => (
          <li key={k} className="flex items-start justify-between gap-3 py-2.5">
            <div className="min-w-0">
              <p className="font-semibold leading-tight">{t(`p_${k}`)}</p>
              <p className="mt-0.5 text-[13px] leading-snug text-ink-soft">{t(`p_${k}_use`)}</p>
              <p className="mt-0.5 text-[12px] text-ink-faint">{p.required ? t('needed') : t('optional')} · {t(`p_${k}_keep`)}</p>
            </div>
            <Toggle on={!!choices[k]} disabled={p.required} onChange={(v) => setChoices({ ...choices, [k]: v })} label={t(`p_${k}`)} />
          </li>
        ))}
      </ul>
      <div className="sticky -bottom-4 -mx-4 bg-white px-4 pb-1 pt-3 sm:-bottom-5 sm:-mx-5 sm:px-5"><button className="btn-primary w-full" onClick={agree}>{t('agree')}</button></div>
    </Panel>
  ) : step === 'documents' ? (
    <Panel title={t('kyc_title')}>
      <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label={t('route_title')}>
        {(['gst', 'udyam', 'shop_licence'] as const).map((r) => (
          <button key={r} role="radio" aria-checked={route === r} onClick={() => chooseRoute(r)} className="choice !px-2 text-center text-[14px] leading-tight">
            {t(r === 'gst' ? 'route_gst' : r === 'udyam' ? 'route_udyam' : 'route_shop')}
          </button>
        ))}
      </div>
      {route && (
        <ul className="mt-3 space-y-2">
          {ROUTE_DOCS[route].map((d) => {
            const s = docs[d] ?? { status: 'empty' }
            return (
              <li key={d} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 ring-1 ${s.status === 'read' ? 'bg-leaf/10 ring-leaf/40' : s.status === 'retake' ? 'bg-haldi/10 ring-haldi/50' : 'bg-white/[.04] ring-white/10'}`}>
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${s.status === 'read' ? 'bg-leaf text-onbrand' : 'bg-white/10 text-ink-soft'}`}>
                  {s.status === 'uploading' ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> : <Svg d={s.status === 'read' ? I.check : I.doc} size={18} />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold">{t(`doc_${d}`)}</span>
                  {s.fields && <span className="block truncate text-[13px] text-ink-soft">{Object.values(s.fields).slice(0, 2).join(' · ')}</span>}
                </span>
                <input ref={(el) => (files.current[d] = el)} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => e.target.files?.[0] && upload(d, e.target.files[0])} />
                <button className="btn-secondary min-h-[40px] shrink-0 !px-3 text-[14px]" disabled={s.status === 'uploading'} onClick={() => files.current[d]?.click()}
                  aria-label={`${t(`doc_${d}`)}: ${s.status === 'empty' ? t('take_photo') : t('retake')}`}>
                  {s.status === 'empty' ? <Svg d={I.camera} size={20} /> : t('retake')}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {kyc && kyc.outcome !== 'verified' && (
        <div className="mt-3 rounded-xl bg-kumkum/10 p-3 ring-1 ring-kumkum/30">
          {kyc.checks.filter((c) => c.status === 'fail').slice(0, 2).map((c) => <p key={c.id} className="text-[15px] font-semibold">{c.args?.local_fix ?? c.fix ?? c.message}</p>)}
          {rented && <Link className="btn-secondary mt-2 w-full" to={`/order/${order!.id}/kyc?key=${order!.key}`}>{t('call_finish_page')}</Link>}
        </div>
      )}
      {route && Object.values(docs).some((d) => d.status !== 'empty') && <button className="btn-primary mt-3 w-full" onClick={check}>{t('call_check_docs')}</button>}
      <details className="mt-3 rounded-xl border border-dashed border-white/15 p-3">
        <summary className="cursor-pointer text-[14px] font-semibold text-ink-soft">{t('call_specimen')}</summary>
        <div className="mt-2 grid grid-cols-5 gap-1.5">{SPECIMENS.map((k) => <button key={k} className="chip justify-center !px-1 text-[13px]" onClick={() => specimen(k)}>{k}</button>)}</div>
      </details>
    </Panel>
  ) : step === 'pay' && sched ? (
    <Panel title={t('pay_title')}>
      <div className="flex items-end justify-between">
        <span className="font-semibold text-ink-soft">{t('due_today')}</span>
        <span className="money text-[30px] leading-none text-kumkum">{paise(sched.due_today)}</span>
      </div>
      <p className="mt-1 flex justify-between text-[14px] text-ink-soft"><span>{t('all_in')}</span><span className="money">{paise(sched.monthly)}</span></p>
      {waiting ? (
        <p className="mt-3 rounded-xl bg-haldi/15 px-3 py-2 font-semibold text-haldi-dark">{t('waiting_owner', { phone: owner!.phone_masked })}</p>
      ) : !paid ? (
        <div className="mt-3 space-y-2">
          <input className="field" value={upi} onChange={(e) => setUpi(e.target.value)} placeholder="name@bank" autoComplete="off" aria-label={t('upi_id')} />
          <button className="btn-primary w-full" disabled={!upi.includes('@')} onClick={pay}>{t('pay_autopay')}</button>
        </div>
      ) : (
        <div className="mt-3">
          <p className="mb-2 font-semibold">{t('choose_slot')}</p>
          <div className="flex gap-1.5 overflow-x-auto pb-1">
            {days.map((d) => <button key={d.date} onClick={() => { setDay(d.date); setSlot(null) }} aria-pressed={day === d.date} className="choice shrink-0 !px-3 !py-1.5 text-[14px]">{fmtDay(d.date)}</button>)}
          </div>
          <div className="mt-2 grid grid-cols-3 gap-1.5">
            {days.find((d) => d.date === day)?.slots.map((s) => <button key={s} onClick={() => setSlot(s)} aria-pressed={slot === s} className="choice !px-1 !py-1.5 text-center text-[14px]">{s}</button>)}
          </div>
          <button className="btn-primary mt-3 w-full" disabled={!slot} onClick={book}>{t('book_slot')}</button>
        </div>
      )}
    </Panel>
  ) : step === 'done' && order ? (
    <Panel title={t('call_order_placed', { id: order.id })}>
      <div className="flex items-center gap-3">
        <Stamp kind={kyc?.outcome === 'review' ? 'review' : 'ok'}>{kyc?.outcome === 'review' ? t('outcome_review') : '✓'}</Stamp>
        {booked && <span className="font-semibold">{booked}</span>}
      </div>
      <button className="btn-primary mt-4 w-full" onClick={() => { end(); nav(`/track/${order.id}?key=${order.key}`) }}>{t('track_title')}</button>
    </Panel>
  ) : null

  const partShown = caption.parts.slice(0, caption.part).join(' ')
  return (
    <Stage>
      <header className="mx-auto flex w-full max-w-site items-center justify-between gap-3 px-4 pt-3 lg:px-8 lg:pt-5">
        <div className="flex min-w-0 items-center gap-2.5">
          <Mark small />
          <span className="min-w-0">
            <span className="block truncate text-[15px] font-bold leading-tight">{t('call_ai_label')}</span>
            <span className="flex items-center gap-1.5 text-[13px] text-ink-soft"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-leaf" />{clock} · {LANGS.find((l) => l.code === lang)?.name}</span>
          </span>
        </div>
        {hud && <span className="money shrink-0 rounded-lg bg-white/[.06] px-2 py-1 text-[12px] text-ink-soft" aria-hidden="true">heard {fmtS(timing.heard)} · reply {fmtS(timing.reply)} · voice {fmtS(timing.voice)}</span>}
      </header>
      <FlowBar at={flowAt} t={t} />

      <main className={`mx-auto grid min-h-0 w-full max-w-site flex-1 gap-3 px-4 pb-2 lg:grid-rows-1 lg:gap-10 lg:px-8 lg:pb-6 ${card ? 'grid-rows-[auto_1fr] lg:grid-cols-[1fr_420px]' : 'grid-rows-1'}`}>
        <section className="flex min-h-0 flex-col items-center justify-center text-center" aria-live="polite">
          <div className={card ? 'hidden sm:block lg:block' : ''}><Orb engine={engine.current} voice={voice} size={card ? 190 : 250} /></div>
          <div className={card ? 'sm:hidden lg:hidden' : 'hidden'}><Orb engine={engine.current} voice={voice} size={112} /></div>
          <p className={`mt-1 text-[14px] font-bold ${lang === 'en' ? 'uppercase tracking-[0.18em] !text-[13px]' : ''} ${voice === 'hearing' ? 'text-ink' : voice === 'speaking' ? 'text-kumkum-dark' : 'text-ink-faint'}`}>
            {t(voice === 'idle' ? 'call_connecting' : `call_${voice}`)}
          </p>
          {you && voice !== 'speaking' && <p className="mt-2 line-clamp-2 max-w-[560px] text-[15px] text-ink-soft"><b className="text-ink-faint">{t('call_you')} · </b>{you}</p>}
          <p className={`mt-2 max-w-[640px] font-semibold leading-snug text-ink ${card ? 'line-clamp-3 text-[17px] lg:line-clamp-none lg:text-[24px]' : 'line-clamp-5 text-[20px] lg:text-[28px]'}`}>
            {partShown && <span className="text-ink-soft">{partShown} </span>}
            <Reveal key={`${caption.part}-${caption.start}`} text={caption.parts[caption.part] ?? ''} dur={caption.dur} />
          </p>
        </section>
        <aside className={`min-h-0 overflow-y-auto overscroll-contain pb-2 lg:self-center ${card || err ? '' : 'hidden'}`}>{card}{err && <p className="mt-2 rounded-xl bg-kumkum/15 px-3 py-2 text-[14px] text-kumkum-dark" role="alert">{err}</p>}</aside>
      </main>

      <footer className="mx-auto w-full max-w-[560px] px-4" style={{ paddingBottom: 'max(14px, env(safe-area-inset-bottom))' }}>
        {voice === 'hearing' && <button className="mx-auto mb-2 block rounded-pill bg-white/10 px-4 py-1.5 text-[14px] font-semibold text-ink ring-1 ring-white/15" onClick={() => engine.current?.finish()}>{t('call_done_talking')}</button>}
        {voice === 'speaking' && engine.current?.hasMic && <button className="mx-auto mb-2 block rounded-pill bg-white/[.06] px-4 py-1.5 text-[14px] font-semibold text-ink-soft ring-1 ring-white/10" onClick={interrupt}>{t('call_interrupt')}</button>}
        {typing && (
          <form className="mb-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); sendTyped() }}>
            <input className="field flex-1" autoFocus value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={t('call_type_ph')} aria-label={t('call_type_ph')} />
            <button className="btn-primary h-12 px-4" disabled={!typed.trim()} aria-label={t('send')}><Svg d={I.send} size={20} /></button>
          </form>
        )}
        <div className="flex items-start justify-between">
          <Control icon={muted ? I.micOff : I.mic} label={muted ? t('call_unmute') : t('call_mute')} on={muted} onClick={toggleMute} disabled={!engine.current?.hasMic} />
          <Control icon={I.keys} label={t('call_keyboard')} on={typing} onClick={() => setTyping(!typing)} />
          <button onClick={end} aria-label={t('call_end')} className="flex flex-col items-center gap-1.5">
            <span className="grid h-[66px] w-[66px] place-items-center rounded-full bg-[#E5243B] text-onbrand shadow-[0_10px_30px_-8px_rgba(229,36,59,.8)] transition hover:brightness-110"><Svg d={I.hang} size={30} /></span>
            <span className="text-[12px] font-semibold text-ink-soft">{t('call_end')}</span>
          </button>
          <Control icon={I.person} label={t('call_person')} on={handoff} onClick={() => (handoff ? setHandoff(false) : openHandoff(true))} />
        </div>
      </footer>
    </Stage>
  )
}

const fmtS = (ms?: number) => (ms === undefined ? '–' : `${(ms / 1000).toFixed(1)}s`)

/** The call is always on a dark stage, like a phone call; the app's own dark colours apply inside it. */
function Stage({ children }: { children: ReactNode }) {
  return (
    <div className="dark fixed inset-0 z-50 flex flex-col overflow-hidden bg-[#07080C] text-ink"
      style={{ backgroundImage: 'radial-gradient(90% 55% at 50% -5%, rgba(213,15,43,.30), transparent 70%), radial-gradient(60% 40% at 50% 110%, rgba(213,15,43,.12), transparent 70%)' }}>
      {children}
    </div>
  )
}

function Mark({ small = false }: { small?: boolean }) {
  return (
    <span className="flex items-center gap-2">
      <svg width={small ? 34 : 30} height={small ? 34 : 30} viewBox="0 0 64 64" aria-hidden="true">
        <rect width="64" height="64" rx="16" fill="#D50F2B" />
        <path d="M21 15 H30 C43 15 50 21 50 32 C50 43 43 49 30 49 H21 Z" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M21 32 H34" stroke="#F2A900" strokeWidth="6" strokeLinecap="round" />
      </svg>
      {!small && <span className="text-[17px] font-extrabold tracking-tight">Dukaan Connect</span>}
    </span>
  )
}

/** Where the call is: business, plan, consent, documents, payment. */
function FlowBar({ at, t }: { at: number; t: (k: string) => string }) {
  return (
    <nav className="mx-auto mt-3 w-full max-w-site px-4 lg:mt-5 lg:px-8" aria-label={FLOW[Math.min(at, FLOW.length - 1)] ? t('call_flow_' + FLOW[Math.min(at, FLOW.length - 1)][0]) : ''}>
      <ol className="flex gap-1.5">
        {FLOW.map(([k], i) => (
          <li key={k} className="min-w-0 flex-1" aria-current={i === at ? 'step' : undefined}>
            <span className="relative block h-1 overflow-hidden rounded-pill bg-white/10">
              <span className={`absolute inset-y-0 left-0 rounded-pill bg-kumkum transition-all duration-700 ${i < at ? 'w-full' : i === at ? 'w-1/2 animate-pulse' : 'w-0'}`} />
            </span>
            <span className={`mt-1.5 flex items-center gap-1 truncate text-[12px] font-semibold lg:text-[13px] ${i === at ? 'text-ink' : i < at ? 'text-ink-soft' : 'text-ink-faint'}`}>
              {i < at && <Svg d={I.check} size={12} width={3} />}{t('call_flow_' + k)}
            </span>
          </li>
        ))}
      </ol>
    </nav>
  )
}

function Panel({ title, children, onClose }: { title: string; children: ReactNode; onClose?: () => void }) {
  return (
    <section className="animate-rise rounded-3xl bg-white p-4 shadow-lift ring-1 ring-white/10 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="truncate text-[18px] font-extrabold">{title}</h2>
        {onClose && <button className="btn-quiet -mr-2 px-2" onClick={onClose} aria-label="Close"><Svg d={I.close} size={18} /></button>}
      </div>
      {children}
    </section>
  )
}

function Control({ icon, label, on, onClick, disabled = false }: { icon: ReactNode; label: string; on: boolean; onClick: () => void; disabled?: boolean }) {
  return (
    <button onClick={onClick} disabled={disabled} aria-pressed={on} aria-label={label} className="flex w-16 flex-col items-center gap-1.5 disabled:opacity-40">
      <span className={`grid h-14 w-14 place-items-center rounded-full transition ${on ? 'bg-ink text-[#07080C]' : 'bg-white/[.08] text-ink ring-1 ring-white/10 hover:bg-white/[.14]'}`}><Svg d={icon} size={24} /></span>
      <span className="truncate text-[12px] font-semibold text-ink-soft">{label}</span>
    </button>
  )
}

/** The AI's words appear as they are spoken. */
function Reveal({ text, dur }: { text: string; dur: number }) {
  const words = text.split(/\s+/).filter(Boolean)
  const [n, setN] = useState(dur ? 0 : words.length)
  useEffect(() => {
    if (dur < 0) { setN(0); return }
    if (!dur) { setN(words.length); return }
    const t0 = performance.now()
    const h = setInterval(() => {
      const k = Math.min(words.length, Math.ceil(((performance.now() - t0) / (dur * 1000)) * words.length * 1.08))
      setN(k)
      if (k >= words.length) clearInterval(h)
    }, 90)
    return () => clearInterval(h)
  }, [text, dur]) // eslint-disable-line react-hooks/exhaustive-deps
  return <>{words.map((w, i) => <span key={i} className={`transition-opacity duration-300 ${i < n ? 'opacity-100' : 'opacity-0'}`}>{w} </span>)}</>
}

/** The voice, drawn: red rings that move with the AI's voice, a ring of bars that moves with the owner's,
 *  a turning arc while it thinks. No avatar, so nothing to load and no delay. */
function Orb({ engine, voice, size }: { engine: CallEngine | null; voice: Voice; size: number }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const state = useRef(voice)
  state.current = voice
  useEffect(() => {
    const c = ref.current
    if (!c) return
    const dpr = Math.min(2, window.devicePixelRatio || 1)
    c.width = size * dpr
    c.height = size * dpr
    const g = c.getContext('2d')!
    const hist = new Array(72).fill(0)
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    let raf = 0
    let level = 0
    let t = 0
    const draw = () => {
      t += still ? 0 : 1 / 60
      const s = state.current
      const target = s === 'speaking' ? Math.min(1, engine ? engine.outLevel * 6 : 0.35 + 0.25 * Math.sin(t * 7))
        : s === 'hearing' || s === 'listening' ? Math.min(1, (engine?.micLevel ?? 0) * 9) : 0
      level += (target - level) * 0.22
      hist.push(level)
      hist.shift()
      const cx = size / 2
      const R = size * 0.27
      g.setTransform(dpr, 0, 0, dpr, 0, 0)
      g.clearRect(0, 0, size, size)
      const red = s !== 'muted'
      const halo = g.createRadialGradient(cx, cx, R * 0.6, cx, cx, size / 2)
      halo.addColorStop(0, red ? `rgba(227,22,47,${0.32 + level * 0.35})` : 'rgba(140,145,160,.18)')
      halo.addColorStop(1, 'rgba(227,22,47,0)')
      g.fillStyle = halo
      g.fillRect(0, 0, size, size)
      if (s === 'speaking' || s === 'idle') { // ripples
        for (let i = 0; i < 3; i++) {
          const p = (t * (s === 'idle' ? 0.25 : 0.55) + i / 3) % 1
          g.beginPath()
          g.arc(cx, cx, R * (1.04 + p * (0.55 + level * 0.5)), 0, Math.PI * 2)
          g.strokeStyle = `rgba(255,90,105,${(1 - p) * (s === 'idle' ? 0.25 : 0.25 + level * 0.6)})`
          g.lineWidth = 2
          g.stroke()
        }
      }
      if (s === 'listening' || s === 'hearing') { // the owner's voice as a ring of bars
        const n = hist.length
        for (let i = 0; i < n; i++) {
          const a = (i / n) * Math.PI * 2 - Math.PI / 2
          const v = hist[(i * 5) % n]
          const len = R * (0.06 + v * 0.55 + (s === 'listening' ? 0.03 * (1 + Math.sin(t * 2 + i)) : 0))
          g.beginPath()
          g.moveTo(cx + Math.cos(a) * R * 1.12, cx + Math.sin(a) * R * 1.12)
          g.lineTo(cx + Math.cos(a) * (R * 1.12 + len), cx + Math.sin(a) * (R * 1.12 + len))
          g.strokeStyle = `rgba(255,255,255,${0.35 + v * 0.6})`
          g.lineWidth = Math.max(2, size / 110)
          g.lineCap = 'round'
          g.stroke()
        }
      }
      if (s === 'thinking') { // two arcs turning
        g.lineCap = 'round'
        g.lineWidth = Math.max(3, size / 60)
        g.beginPath()
        g.arc(cx, cx, R * 1.16, t * 4.2, t * 4.2 + 1.5)
        g.strokeStyle = '#F2A900'
        g.stroke()
        g.beginPath()
        g.arc(cx, cx, R * 1.16, t * 4.2 + Math.PI, t * 4.2 + Math.PI + 1.1)
        g.strokeStyle = 'rgba(255,90,105,.9)'
        g.stroke()
      }
      const r = R * (1 + level * 0.07 + (s === 'idle' ? 0.02 * Math.sin(t * 2) : 0))
      const core = g.createRadialGradient(cx - r * 0.35, cx - r * 0.4, r * 0.1, cx, cx, r)
      core.addColorStop(0, red ? '#FF4A5E' : '#6B7080')
      core.addColorStop(0.55, red ? '#D50F2B' : '#3D414C')
      core.addColorStop(1, red ? '#7A0617' : '#22252D')
      g.beginPath()
      g.arc(cx, cx, r, 0, Math.PI * 2)
      g.fillStyle = core
      g.shadowColor = red ? 'rgba(227,22,47,.7)' : 'transparent'
      g.shadowBlur = 30 + level * 40
      g.fill()
      g.shadowBlur = 0
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [engine, size])
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <canvas ref={ref} style={{ width: size, height: size }} aria-hidden="true" />
      <svg className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" width={size * 0.22} height={size * 0.22} viewBox="0 0 64 64" aria-hidden="true">
        <path d="M21 15 H30 C43 15 50 21 50 32 C50 43 43 49 30 49 H21 Z" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M21 32 H34" stroke="#F2A900" strokeWidth="6" strokeLinecap="round" />
      </svg>
    </div>
  )
}
