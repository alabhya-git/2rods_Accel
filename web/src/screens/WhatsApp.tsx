import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, store } from '../lib/api'

type Msg = { me: boolean; text: string; quote?: string }

export default function WhatsApp() {
  const [from] = useState(() => store('wa_from') || store('wa_from', '98' + String(Math.floor(10000000 + Math.random() * 89999999)))!)
  const [msgs, setMsgs] = useState<Msg[]>([{ me: false, text: 'Namaste! This is Dukaan Connect on WhatsApp. Tell me about your business in any language.' }])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs.length])

  const send = async () => {
    if (!text.trim()) return
    const t = text
    setText('')
    setMsgs((m) => [...m, { me: true, text: t }])
    setBusy(true)
    try {
      const r = await api.post<any>('/api/whatsapp/simulate', { from_number: from, text: t })
      const link = r.reply.match(/\/quote\?session=\S+/)
      setMsgs((m) => [...m, { me: false, text: r.reply.replace(/\n\nOpen your quote: \S+/, ''), quote: link?.[0] }])
    } finally { setBusy(false) }
  }

  return (
    <div className="flex h-full flex-col bg-[#ECE5DD]">
      <header className="flex h-16 items-center gap-3 bg-[#075E54] px-4 text-white">
        <Link to="/" aria-label="Back" className="text-[22px]">‹</Link>
        <div className="grid h-10 w-10 place-items-center rounded-full bg-kumkum font-bold">A</div>
        <div><p className="font-bold leading-tight">Dukaan Connect</p><p className="text-[13px] opacity-80">Verified business account (simulator)</p></div>
      </header>
      <div className="mx-auto w-full max-w-[480px] flex-1 space-y-2 overflow-y-auto px-3 py-4">
        {msgs.map((m, i) => (
          <div key={i} className={`max-w-[85%] whitespace-pre-line rounded-lg px-3 py-2 text-[16px] shadow-sm ${m.me ? 'ml-auto bg-[#DCF8C6]' : 'bg-white'}`}>
            {m.text}
            {m.quote && <Link to={m.quote} className="mt-2 block rounded-md border border-[#075E54] py-1.5 text-center font-semibold text-[#075E54]">Open my quote</Link>}
          </div>
        ))}
        {busy && <div className="w-14 rounded-lg bg-white px-3 py-2 text-center">…</div>}
        <div ref={end} />
      </div>
      <form className="mx-auto flex w-full max-w-[480px] gap-2 p-3" onSubmit={(e) => { e.preventDefault(); send() }}>
        <input className="h-12 flex-1 rounded-full border-0 bg-white px-4" value={text} onChange={(e) => setText(e.target.value)} placeholder="Message" aria-label="Message" />
        <button className="grid h-12 w-12 place-items-center rounded-full bg-[#075E54] text-white" aria-label="Send">➤</button>
      </form>
    </div>
  )
}
