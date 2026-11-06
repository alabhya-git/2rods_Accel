// Voice in 10 Indian languages. Server speech (Sarvam, key kept on the server) when it is on;
// the browser's own speech when it is not, so voice degrades instead of breaking.
// What was heard is always shown back for the owner to confirm before it changes anything.
import { useCallback, useEffect, useRef, useState } from 'react'

type Rec = { lang: string; interimResults: boolean; continuous: boolean; start(): void; stop(): void; onresult: any; onend: any; onerror: any }

let serverSpeech: Promise<boolean> | null = null
let serverSpeechKnown: boolean | null = null  // known before any tap, so playback can start inside the tap
function hasServerSpeech(): Promise<boolean> {
  serverSpeech ??= fetch('/api/voice/status').then((r) => r.json()).then((s) => (serverSpeechKnown = Boolean(s.server_speech)))
    .catch(() => (serverSpeechKnown = false))
  return serverSpeech
}
hasServerSpeech()

export function useVoice(bcp: string, onText: (t: string) => void) {
  const [listening, setListening] = useState(false)
  const [server, setServer] = useState(false)
  const recRef = useRef<Rec | null>(null)
  const media = useRef<MediaRecorder | null>(null)
  const W = window as any
  const Impl = W.SpeechRecognition || W.webkitSpeechRecognition
  useEffect(() => { hasServerSpeech().then(setServer) }, [])
  const supported = server ? Boolean(navigator.mediaDevices && W.MediaRecorder) : Boolean(Impl)

  const start = useCallback(async () => {
    if (server) {  // record, then transcribe on the server
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const rec = new MediaRecorder(stream)
        const chunks: Blob[] = []
        rec.ondataavailable = (e) => chunks.push(e.data)
        rec.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop())
          setListening(false)
          const fd = new FormData()
          fd.append('audio', new Blob(chunks, { type: rec.mimeType || 'audio/webm' }), 'voice.webm')
          fd.append('language', bcp.slice(0, 2))
          try {
            const r = await fetch('/api/voice/transcribe', { method: 'POST', body: fd })
            if (r.ok) { const j = await r.json(); if (j.text) onText(j.text) }
          } catch { /* the owner can type */ }
        }
        media.current = rec
        setListening(true)
        rec.start()
        setTimeout(() => rec.state === 'recording' && rec.stop(), 15000)  // a turn is a sentence, not a speech
      } catch { setListening(false) }
      return
    }
    if (!Impl) return
    const rec: Rec = new Impl()
    rec.lang = bcp
    rec.interimResults = false
    rec.continuous = false
    rec.onresult = (e: any) => {
      const text = Array.from(e.results).map((r: any) => r[0].transcript).join(' ')
      if (text.trim()) onText(text.trim())
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recRef.current = rec
    setListening(true)
    rec.start()
  }, [Impl, bcp, onText, server])

  const stop = useCallback(() => { media.current?.state === 'recording' ? media.current.stop() : recRef.current?.stop() }, [])
  return { supported, listening, start, stop, server }
}

export type SpeakState = 'idle' | 'loading' | 'playing'
let player: HTMLAudioElement | null = null

function deviceVoice(text: string, bcp: string, onState: (s: SpeakState) => void) {
  try {
    const u = new SpeechSynthesisUtterance(text)
    u.lang = bcp
    u.onend = () => onState('idle')
    u.onerror = () => onState('idle')
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(u)
    onState('playing')
  } catch {
    onState('idle')
  }
}

export function stopSpeaking() {
  player?.pause()
  player = null
  try { window.speechSynthesis.cancel() } catch { /* none */ }
}

/** Must be called straight from a tap: the audio element is created and played inside the gesture,
 *  and streams from the server, so browsers (iOS Safari included) don't block it. */
export function speak(text: string, bcp: string, onState: (s: SpeakState) => void = () => {}) {
  stopSpeaking()
  const clean = text.replace(/•/g, '').trim()
  if (!clean) return
  if (serverSpeechKnown) {
    const url = `/api/voice/speak?language=${bcp.slice(0, 2)}&text=${encodeURIComponent(clean.slice(0, 1200))}`
    const a = new Audio(url)
    player = a
    onState('loading')
    a.onplaying = () => onState('playing')
    a.onended = () => onState('idle')
    a.onerror = () => { if (player === a) deviceVoice(clean, bcp, onState) }  // server speech failed: the device reads it
    a.play().catch(() => { if (player === a) deviceVoice(clean, bcp, onState) })
    return
  }
  deviceVoice(clean, bcp, onState)
}
