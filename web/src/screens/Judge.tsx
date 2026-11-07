import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Logo, Working } from '../components/ui'
import { api } from '../lib/api'

export default function Judge() {
  const [health, setHealth] = useState<any>(null)
  const [sc, setSc] = useState<any>(null)
  const [kyc, setKyc] = useState<any>(null)
  const [cases, setCases] = useState<any[]>([])
  const [busy, setBusy] = useState<string | null>(null)

  useEffect(() => {
    api.get('/api/health').then(setHealth)
    api.get<any[]>('/api/judge/advisor-cases').then(setCases)
  }, [])
  const runScenarios = async () => { setBusy('sc'); setSc(await api.get('/api/judge/scenarios')); setBusy(null) }
  const runKyc = async () => { setBusy('kyc'); setKyc(await api.post('/api/judge/kyc')); setBusy(null) }
  const reset = async () => { if (confirm('Delete all demo orders, conversations and documents?')) { await api.post('/api/judge/reset'); alert('Demo data cleared') } }

  return (
    <div className="min-h-full">
      <header className="border-b border-rule bg-white">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-4"><Logo small /><span className="text-[18px] font-bold text-ink-soft">Judge console</span></div>
          <div className="flex gap-2"><a className="btn-quiet" href="/docs">API docs</a><button className="btn-quiet text-kumkum" onClick={reset}>Reset demo</button></div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl space-y-8 px-4 py-6">
        <section>
          <p className="text-[17px]">
            Language model: <b>{health?.llm ? `${health.llm.provider} (${health.llm.model})` : 'off, rules-only mode'}</b>. Either way the rules engine alone picks products and prices; the guard checks every reply.
          </p>
        </section>

        <section className="rounded-xl border border-rule bg-white p-4">
          <h2 className="text-[22px] font-bold">Hidden pain points: try them</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[16px]">
            <li><b>Existing Accel customer:</b> order with mobile <b>9876500001</b>. Welcome back, and their numbers become business SIMs with KYC on file.</li>
            <li><b>Staff ordering for the owner:</b> on the quote pick <i>I work here</i> and give another number. Payment stays locked until the owner e-signs from their link.</li>
            <li><b>Rented shop:</b> in KYC, specimen <b>K02R</b> (bill in the landlord's name). Ask the landlord to confirm, or upload the specimen rent agreement.</li>
            <li><b>Scam calls:</b> <Link className="text-ledger underline" to="/verify">check a caller</Link> (try PARTNER-001), and the code on every call-back.</li>
            <li><b>Setup after go-live:</b> order Cloud Email, go live, and see it tracked until it is set up.</li>
          </ul>
        </section>

        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-[22px] font-bold">Try any advisor case live</h2>
          </div>
          <p className="text-ink-soft">Each opens a fresh conversation with that message. Type your own scenarios too.</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {cases.map((c) => (
              <Link key={c.id} to={`/advisor?say=${encodeURIComponent(c.says)}`} target="_blank" className="rounded-xl border border-rule bg-white p-3 hover:border-ledger">
                <p className="text-[14px] font-semibold text-ledger">{c.title}</p>
                <p className="text-[15px]">{c.says}</p>
              </Link>
            ))}
          </div>
        </section>

        <section>
          <div className="flex flex-wrap items-center gap-4">
            <h2 className="text-[22px] font-bold">Rules engine scenarios</h2>
            <button className="btn-primary min-h-[42px]" onClick={runScenarios} disabled={busy === 'sc'}>Run all</button>
            {sc && <span className={`stamp ${sc.passed === sc.total ? 'text-leaf' : 'text-kumkum'}`}>{sc.passed}/{sc.total} passed in {sc.ms} ms</span>}
          </div>
          {busy === 'sc' && <Working label="Running" />}
          {sc && (
            <div className="mt-3 overflow-x-auto rounded-xl border border-rule bg-white">
              <table className="w-full min-w-[760px] text-left text-[14px]">
                <thead className="bg-paper-tint text-ink-soft"><tr><th className="px-3 py-2">Case</th><th className="px-3 py-2">Sold</th><th className="px-3 py-2">Refused (rule)</th><th className="px-3 py-2">Result</th></tr></thead>
                <tbody className="divide-y divide-rule">
                  {sc.results.map((r: any) => (
                    <tr key={r.id}><td className="px-3 py-2"><b>{r.id}</b> {r.title}</td><td className="px-3 py-2">{r.products.join(', ')}</td>
                      <td className="px-3 py-2">{r.refused.map((x: any) => `${x.product} (${x.rule})`).join(', ')}</td>
                      <td className={`px-3 py-2 font-bold ${r.passed ? 'text-leaf' : 'text-kumkum'}`}>{r.passed ? 'Pass' : r.problems.join('; ')}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <div className="flex flex-wrap items-center gap-4">
            <h2 className="text-[22px] font-bold">Smart KYC on the 12 specimen applicants</h2>
            <button className="btn-primary min-h-[42px]" onClick={runKyc} disabled={busy === 'kyc'}>Run OCR and checks</button>
            {kyc && <span className={`stamp ${kyc.correct === kyc.total ? 'text-leaf' : 'text-kumkum'}`}>{kyc.correct}/{kyc.total} correct, {kyc.false_rejections} false rejections</span>}
          </div>
          {busy === 'kyc' && <div className="mt-2"><Working label="Reading 47 document photos with self-hosted OCR" /></div>}
          {kyc && (
            <div className="mt-3 overflow-x-auto rounded-xl border border-rule bg-white">
              <table className="w-full min-w-[760px] text-left text-[14px]">
                <thead className="bg-paper-tint text-ink-soft"><tr><th className="px-3 py-2">Applicant</th><th className="px-3 py-2">Outcome</th><th className="px-3 py-2">What the checks found</th></tr></thead>
                <tbody className="divide-y divide-rule">
                  {kyc.results.map((r: any) => (
                    <tr key={r.id}><td className="px-3 py-2"><b>{r.id}</b> {r.business_name}</td>
                      <td className={`px-3 py-2 font-bold ${r.correct ? 'text-leaf' : 'text-kumkum'}`}>{r.outcome.replace('_', ' ')}{r.correct ? '' : ` (expected ${r.expected})`}</td>
                      <td className="px-3 py-2">{r.messages.length ? r.messages.join(' ') : 'All hard checks passed.'}{r.notes.length ? <span className="text-ink-faint"> Notes: {r.notes.length}</span> : null}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="grid gap-3 md:grid-cols-3">
          <Link to="/" className="rounded-xl border border-rule bg-white p-4 hover:border-ledger"><b>Owner journey</b><p className="text-ink-soft">Advisor, quote, consent, KYC, payment, tracker</p></Link>
          <Link to="/whatsapp" className="rounded-xl border border-rule bg-white p-4 hover:border-ledger"><b>WhatsApp channel</b><p className="text-ink-soft">The same advisor over chat</p></Link>
          <Link to="/partner" className="rounded-xl border border-rule bg-white p-4 hover:border-ledger"><b>Partner & reviewer desk</b><p className="text-ink-soft">Call-backs, leads, KYC reviews, metrics. Demo sign-ins are listed on its login page</p></Link>
        </section>
      </main>
    </div>
  )
}
