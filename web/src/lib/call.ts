// The call's ears and voice. Hands-free turn-taking: the page notices when the owner starts and stops talking
// (nothing to hold), keeps 300 ms from before they started so no first syllable is lost, and sends one clean
// 16 kHz clip per turn. Replies are spoken sentence by sentence: the first plays while the rest is still being made.

export type Mode = 'off' | 'listen' | 'barge' // barge: the AI is talking, and only clear, sustained speech cuts in

const FRAME_MS = 20
const PREROLL = 15 // frames kept before speech starts
const START_FRAMES = 3 // 60 ms above the line starts a turn
const BARGE_FRAMES = 15 // 300 ms of clear speech talks over the AI
const END_MS = 800 // this much quiet ends a turn
const MIN_SPEECH_MS = 250 // shorter is a cough or a tap, not a turn
const MAX_MS = 25000 // Sarvam's real-time limit is 30 s

export class CallEngine {
  readonly ctx: AudioContext
  readonly hasMic: boolean
  mode: Mode = 'off'
  micLevel = 0
  onUtterance: (wav: Blob, speechMs: number) => void = () => {}
  onSpeechStart: () => void = () => {}
  onBargeIn: () => void = () => {}
  onDiscard: () => void = () => {} // a cough or a tap: back to listening
  private stream: MediaStream | null
  private out: AnalyserNode
  private outBuf = new Float32Array(1024)
  private floor = 0.004
  private ring: Float32Array[] = []
  private clip: Float32Array[] | null = null
  private above = 0
  private speechMs = 0
  private quietMs = 0
  private gen = 0 // bumps on stop: a reply that was cut off never resumes
  private source: AudioBufferSourceNode | null = null
  private lock: any = null

  /** Call inside the tap that starts the call: browsers allow sound from that gesture on. */
  static async open(): Promise<CallEngine> {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext
    const ctx: AudioContext = new Ctx()
    const resumed = ctx.resume()
    let stream: MediaStream | null = null
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } })
      await ctx.audioWorklet.addModule('/mic-worklet.js')
    } catch {
      stream?.getTracks().forEach((t) => t.stop())
      stream = null // no microphone: the call goes on with typing, and the AI still speaks
    }
    await resumed
    return new CallEngine(ctx, stream)
  }

  private constructor(ctx: AudioContext, stream: MediaStream | null) {
    this.ctx = ctx
    this.stream = stream
    this.hasMic = Boolean(stream)
    this.out = ctx.createAnalyser()
    this.out.fftSize = 1024
    this.out.connect(ctx.destination)
    if (stream) {
      const node = new AudioWorkletNode(ctx, 'mic-frames')
      const sink = ctx.createGain()
      sink.gain.value = 0 // the worklet must be pulled to run; nothing from the mic reaches the speaker
      ctx.createMediaStreamSource(stream).connect(node)
      node.connect(sink).connect(ctx.destination)
      node.port.onmessage = (e) => this.frame(e.data.rms, e.data.pcm)
    }
    // a camera or file picker can suspend audio on a phone: pick up where we left off
    document.addEventListener('visibilitychange', this.wake)
    this.wake()
  }

  private wake = () => {
    if (document.visibilityState !== 'visible') return
    if (this.ctx.state !== 'running') this.ctx.resume().catch(() => {})
    ;(navigator as any).wakeLock?.request('screen').then((l: any) => (this.lock = l)).catch(() => {})
  }

  private frame(rms: number, pcm: Float32Array) {
    this.micLevel = this.micLevel * 0.6 + rms * 0.4
    if (this.mode === 'off') {
      this.clip = null
      this.above = 0
      return
    }
    const barge = this.mode === 'barge'
    if (!this.clip) {
      this.ring.push(pcm)
      if (this.ring.length > PREROLL) this.ring.shift()
      const start = barge ? Math.max(0.04, this.floor * 6) : Math.max(0.015, this.floor * 3)
      if (rms > start) this.above++
      else {
        this.above = 0
        if (!barge) this.floor = Math.min(0.03, Math.max(0.002, this.floor * 0.97 + rms * 0.03)) // the room's own noise, learnt while quiet
      }
      if (this.above >= (barge ? BARGE_FRAMES : START_FRAMES)) {
        if (barge) {
          this.stop()
          this.mode = 'listen'
          this.onBargeIn()
        }
        this.clip = this.ring
        this.ring = []
        this.speechMs = this.above * FRAME_MS
        this.quietMs = 0
        this.above = 0
        this.onSpeechStart()
      }
      return
    }
    this.clip.push(pcm)
    if (rms > Math.max(0.009, this.floor * 1.8)) {
      this.speechMs += FRAME_MS
      this.quietMs = 0
    } else this.quietMs += FRAME_MS
    if (this.quietMs >= END_MS || this.clip.length * FRAME_MS >= MAX_MS) this.finish()
  }

  /** End the turn now: the owner tapped "done" instead of waiting for the pause. */
  finish() {
    const clip = this.clip
    this.clip = null
    if (!clip) return
    const trailing = Math.max(0, Math.floor((this.quietMs - 200) / FRAME_MS))
    if (this.speechMs >= MIN_SPEECH_MS) this.onUtterance(toWav(clip.slice(0, clip.length - trailing)), this.speechMs)
    else this.onDiscard()
  }

  get hearing() { return this.clip !== null }

  /** Loudness of the AI's voice right now, for the orb. */
  get outLevel() {
    this.out.getFloatTimeDomainData(this.outBuf)
    let e = 0
    for (let i = 0; i < this.outBuf.length; i++) e += this.outBuf[i] * this.outBuf[i]
    return Math.sqrt(e / this.outBuf.length)
  }

  /** Speak a reply: every part is already being fetched; they play in order. Resolves false if cut off. */
  async play(parts: { text: string; audio: Promise<ArrayBuffer | null> }[], bcp: string, onPart: (i: number, seconds: number) => void): Promise<boolean> {
    const g = ++this.gen
    for (let i = 0; i < parts.length; i++) {
      const bytes = await parts[i].audio
      if (g !== this.gen) return false
      let buf: AudioBuffer | null = null
      if (bytes) try { buf = await this.ctx.decodeAudioData(bytes.slice(0)) } catch { buf = null }
      if (g !== this.gen) return false
      if (!buf) { // server speech failed: the device reads this part
        onPart(i, Math.max(1.5, parts[i].text.length / 14))
        await deviceSay(parts[i].text, bcp)
      } else {
        onPart(i, buf.duration)
        await new Promise<void>((done) => {
          const s = this.ctx.createBufferSource()
          s.buffer = buf
          s.connect(this.out)
          s.onended = () => done()
          this.source = s
          s.start()
        })
      }
      if (g !== this.gen) return false
    }
    return true
  }

  stop() {
    this.gen++
    try { this.source?.stop() } catch { /* already ended */ }
    this.source = null
    try { window.speechSynthesis.cancel() } catch { /* none */ }
  }

  close() {
    this.stop()
    this.mode = 'off'
    this.stream?.getTracks().forEach((t) => t.stop())
    document.removeEventListener('visibilitychange', this.wake)
    this.lock?.release?.().catch(() => {})
    this.ctx.close().catch(() => {})
  }
}

function deviceSay(text: string, bcp: string): Promise<void> {
  return new Promise((done) => {
    try {
      const u = new SpeechSynthesisUtterance(text)
      u.lang = bcp
      u.onend = () => done()
      u.onerror = () => done()
      window.speechSynthesis.speak(u)
    } catch { done() }
  })
}

function toWav(frames: Float32Array[]): Blob {
  const n = frames.reduce((a, f) => a + f.length, 0)
  const v = new DataView(new ArrayBuffer(44 + n * 2))
  const w = (o: number, s: string) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)) }
  w(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); w(8, 'WAVE'); w(12, 'fmt ')
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, 16000, true)
  v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, 'data'); v.setUint32(40, n * 2, true)
  let o = 44
  for (const f of frames) for (let i = 0; i < f.length; i++, o += 2) v.setInt16(o, Math.max(-1, Math.min(1, f[i])) * 0x7fff, true)
  return new Blob([v.buffer], { type: 'audio/wav' })
}

/** A reply cut where a listener would hear a pause: a short first part so the voice starts fast, then fuller ones. */
export function sentences(text: string): string[] {
  const raw = text.replace(/[•*]/g, '').split(/\n+/).flatMap((line) => line.match(/.+?(?:[.!?।॥](?=\s|$)|$)/g) ?? [])
    .map((s) => s.trim()).filter(Boolean)
  // a long first sentence is cut at its first comma or colon: those first words are what the owner waits for
  if (raw[0] && raw[0].length > 70) {
    const cut = raw[0].slice(20, 70).search(/[,:،]\s/)
    if (cut >= 0) raw.splice(0, 1, raw[0].slice(0, 20 + cut + 1).trim(), raw[0].slice(20 + cut + 1).trim())
  }
  const out: string[] = []
  for (const s of raw) {
    const last = out[out.length - 1]
    if (last !== undefined && ((last.length < 24 && out.length === 1 && !/[,:]$/.test(last)) || (out.length > 1 && last.length + s.length < 160))) out[out.length - 1] = `${last} ${s}`
    else out.push(s)
  }
  return out
}

// spoken lines repeat (greeting, prompts, fillers): fetch each once per visit; the server caches them too
const said = new Map<string, Promise<ArrayBuffer | null>>()
export function voiceOf(text: string, lang: string, server: boolean): Promise<ArrayBuffer | null> {
  if (!server) return Promise.resolve(null)
  const key = `${lang}|${text}`
  let p = said.get(key)
  if (!p) {
    p = fetch('/api/voice/speak', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ text: text.slice(0, 1500), language: lang, format: 'mp3' }) })
      .then((r) => (r.ok ? r.arrayBuffer() : null)).catch(() => null)
    p.then((b) => { if (!b) said.delete(key) })
    said.set(key, p)
  }
  return p
}

/** Without server speech the browser listens, one turn at a time. */
export function browserHear(bcp: string): Promise<string> {
  const W = window as any
  const Impl = W.SpeechRecognition || W.webkitSpeechRecognition
  if (!Impl) return Promise.resolve('')
  return new Promise((done) => {
    const rec = new Impl()
    rec.lang = bcp
    rec.interimResults = false
    rec.continuous = false
    let text = ''
    rec.onresult = (e: any) => { text = Array.from(e.results).map((r: any) => r[0].transcript).join(' ').trim() }
    rec.onend = () => done(text)
    rec.onerror = () => done('')
    try { rec.start() } catch { done('') }
  })
}

const DIGITS = [0x966, 0x9e6, 0xa66, 0xae6, 0xbe6, 0xc66, 0xce6, 0xd66] // Devanagari, Bengali, Gurmukhi, Gujarati, Tamil, Telugu, Kannada, Malayalam
/** A spoken mobile number, in any script: the last ten digits, or null. */
export function phoneIn(text: string): string | null {
  let ascii = ''
  for (const ch of text) {
    const c = ch.codePointAt(0)!
    const base = DIGITS.find((b) => c >= b && c <= b + 9)
    ascii += base !== undefined ? String(c - base) : ch
  }
  const d = ascii.replace(/\D/g, '')
  return d.length >= 10 ? d.slice(-10) : null
}
