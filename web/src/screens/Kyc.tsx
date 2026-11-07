import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card, ErrorNote, Hint, Shell, Split, Stamp, StickyBar, Working } from '../components/ui'
import { api, type Check, type KycResult, type OrderView } from '../lib/api'
import { useLang } from '../lib/i18n'

const ALL_DOCS = ['gst_certificate', 'udyam_certificate', 'shop_licence', 'address_proof', 'signatory_id', 'rent_agreement'] as const
// the proof route decides the documents: no GST is a route, not a dead end
const ROUTE_DOCS: Record<string, string[]> = {
  gst: ['gst_certificate', 'udyam_certificate', 'address_proof', 'signatory_id'],
  udyam: ['udyam_certificate', 'address_proof', 'signatory_id'],
  shop_licence: ['shop_licence', 'address_proof', 'signatory_id'],
}
const DOCS = ALL_DOCS
type DocState = { status: 'empty' | 'uploading' | 'read' | 'retake' | 'digilocker'; fields?: Record<string, string>; skew?: number }
const LABELS: Record<string, string> = { gstin: 'GSTIN', udyam_number: 'Udyam no.', id_no: 'ID no.', legal_name: 'Legal name', trade_name: 'Trade name', consumer_no: 'Consumer no.', billed_to: 'Billed to', supply_address: 'Address', bill_date: 'Bill date', enterprise_name: 'Enterprise', major_activity: 'Activity', valid_till: 'Valid till', business: 'Business' }
const SPECIMENS = ['K01', 'K02', 'K03', 'K04', 'K05', 'K06', 'K07', 'K08', 'K09', 'K10', 'K11', 'K12', 'K02R']  // K02R: our rented-shop case

export default function Kyc() {
  const { id } = useParams()
  const key = new URLSearchParams(location.search).get('key')
  const { t } = useLang()
  const nav = useNavigate()
  const [order, setOrder] = useState<OrderView | null>(null)
  const [gstin, setGstin] = useState('')
  const [registry, setRegistry] = useState<any>(null)
  const [docs, setDocs] = useState<Record<string, DocState>>(Object.fromEntries(DOCS.map((d) => [d, { status: 'empty' }])))
  const [udyam, setUdyam] = useState('')
  const [result, setResult] = useState<KycResult | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const inputs = useRef<Record<string, HTMLInputElement | null>>({})
  const [route, setRouteState] = useState<string | null>(null)
  const [gstOnly, setGstOnly] = useState<string[]>([])
  const [landlordPhone, setLandlordPhone] = useState('')
  const [landlord, setLandlord] = useState<{ phone_masked: string; link: string } | null>(null)

  const load = () => api.get<OrderView>(`/api/orders/${id}?key=${key}`).then((o) => {
    setOrder(o)
    if (o.kyc) setResult(o.kyc)
    if (!route) setRouteState((o as any).kyc?.route ?? (o.gstin_masked ? 'gst' : null))
  })
  const chooseRoute = async (r: string) => {
    setErr(null)
    try {
      const out = await api.post<{ route: string; gst_only_products: string[] }>(`/api/orders/${id}/kyc/route?key=${key}`, { route: r })
      setRouteState(out.route)
      setGstOnly(out.gst_only_products)
    } catch (e: any) { setErr(e.message) }
  }
  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  // the landlord confirms on their own phone: their yes re-runs KYC, so keep the result fresh
  useEffect(() => {
    if (!landlord) return
    const h = setInterval(() => { if (document.visibilityState === 'visible') load() }, 4000)
    return () => clearInterval(h)
  }, [landlord]) // eslint-disable-line react-hooks/exhaustive-deps

  const askLandlord = async () => {
    setErr(null)
    try { setLandlord(await api.post(`/api/orders/${id}/landlord?key=${key}`, { phone: landlordPhone })) } catch (e: any) { setErr(e.message) }
  }
  const demoLease = async () => {
    setBusy(t('verifying'))
    try {
      const r = await api.post<any>(`/api/orders/${id}/kyc/specimen?key=${key}`, { specimen: 'K02R', docs: ['rent_agreement'] })
      setDocs((d) => ({ ...d, rent_agreement: { status: 'read', fields: r.documents[0]?.fields } }))
      setResult(r.result)
      load()
    } catch (e: any) { setErr(e.message) } finally { setBusy(null) }
  }

  const check = async () => {
    setErr(null)
    try {
      setRegistry(await api.post(`/api/orders/${id}/kyc/identifiers?key=${key}`, { gstin, udyam_number: udyam || undefined }))
    } catch (e: any) { setErr(e.message) }
  }

  const upload = async (doc: string, file: File) => {
    setDocs((d) => ({ ...d, [doc]: { status: 'uploading' } }))
    const fd = new FormData()
    fd.append('doc_type', doc)
    fd.append('file', file)
    try {
      const r = await api.post<any>(`/api/orders/${id}/kyc/documents?key=${key}`, fd)
      const bad = r.quality.blurred || r.quality.faint || (r.quality.detected && r.quality.detected !== doc)
      setDocs((d) => ({ ...d, [doc]: { status: bad ? 'retake' : 'read', fields: r.fields, skew: r.quality.skew_deg } }))
    } catch (e: any) {
      setErr(e.message)
      setDocs((d) => ({ ...d, [doc]: { status: 'empty' } }))
    }
  }

  const digilocker = async () => {
    setErr(null)
    try {
      const r = await api.post<any>(`/api/orders/${id}/kyc/digilocker?key=${key}`, { udyam_number: udyam || undefined })
      setDocs((d) => ({ ...d, udyam_certificate: { status: 'digilocker', fields: r.fields } }))
    } catch (e: any) { setErr(e.message) }
  }

  const verify = async () => {
    setBusy(t('verifying'))
    setErr(null)
    try {
      const r = await api.post<{ result: KycResult }>(`/api/orders/${id}/kyc/evaluate?key=${key}`)
      setResult(r.result)
      load()
    } catch (e: any) { setErr(e.message) } finally { setBusy(null) }
  }

  const specimen = async (k: string) => {
    setBusy(t('verifying'))
    setErr(null)
    try {
      const r = await api.post<any>(`/api/orders/${id}/kyc/specimen?key=${key}`, { specimen: k })
      const next: Record<string, DocState> = Object.fromEntries(DOCS.map((d) => [d, { status: 'empty' }]))
      for (const d of r.documents) {
        const bad = d.quality.blurred || d.quality.faint
        next[d.doc_type] = { status: bad ? 'retake' : 'read', fields: d.fields, skew: d.quality.skew_deg }
      }
      setDocs(next)
      setResult(r.result)
      setRouteState('gst')
      load()
    } catch (e: any) { setErr(e.message) } finally { setBusy(null) }
  }

  const outcome = result?.outcome
  const fails = (result?.checks ?? []).filter((c) => c.status === 'fail')
  const passes = (result?.checks ?? []).filter((c) => c.status === 'pass')
  const notes = (result?.checks ?? []).filter((c) => c.status === 'warn')
  // the bill is in someone else's name: a rented shop proves itself through the landlord
  const rented = fails.find((c) => c.id === 'address_proof.name' && c.args?.rented)

  function aside() {
    return (
      <>
        {busy && <Card><Working label={busy} /></Card>}
        <ErrorNote msg={err} />

        {!result && !busy && <Card><p className="text-ink-soft">{t('result_here')}</p></Card>}
        {result && !busy && (
          <section className="card p-5" aria-live="polite">
            <div className="flex justify-center py-2">
              <Stamp kind={outcome === 'verified' ? 'ok' : outcome === 'fix_needed' ? 'fix' : 'review'}>
                <span className="text-[22px]">{t(`outcome_${outcome}`)}</span>
              </Stamp>
            </div>
            {fails.length > 0 && (
              <ul className="mt-4 space-y-3">
                {fails.map((c: Check) => (
                  <li key={c.id} className="border-l-4 border-kumkum pl-3">
                    {/* the owner reads the fix in their own language; the English detail is for reviewers */}
                    <p className="font-semibold">{c.args?.local_fix ?? c.fix ?? c.message}</p>
                    {c.args?.local_fix && <p className="text-[13px] text-ink-soft" lang="en">{c.message}</p>}
                  </li>
                ))}
              </ul>
            )}
            {rented && (
              <div className="mt-4 rounded-xl border-2 border-haldi bg-haldi-soft p-4">
                <p className="font-bold text-haldi-dark">{t('rented_title')}</p>
                {landlord ? (
                  <>
                    <p className="mt-1 text-[15px]">{t('landlord_sent', { phone: landlord.phone_masked })}</p>
                    <button className="btn-quiet mt-2 border border-dashed border-rule-strong" onClick={() => window.open(landlord.link, '_blank')}>Demo: open the landlord's link</button>
                  </>
                ) : (
                  <>
                    <label className="mt-2 block">
                      <span className="mb-1 block text-[15px] font-semibold">{t('landlord_phone')}</span>
                      <input className="field" inputMode="tel" value={landlordPhone} onChange={(e) => setLandlordPhone(e.target.value)} placeholder="98XXXXXXXX" />
                    </label>
                    <button className="btn-primary mt-2 w-full" onClick={askLandlord} disabled={landlordPhone.replace(/\D/g, '').length < 10}>{t('ask_landlord')}</button>
                  </>
                )}
                <p className="mt-3 text-[15px] font-semibold">{t('or_upload_rent')}</p>
                {order?.specimen === 'K02R' && <button className="btn-quiet mt-1 border border-dashed border-rule-strong" onClick={demoLease}>Demo: upload the specimen rent agreement</button>}
              </div>
            )}
            <details className="mt-4">
              <summary className="cursor-pointer text-[15px] font-semibold text-ink-soft hover:text-ink">{passes.length} checks passed{notes.length ? `, ${notes.length} ${notes.length === 1 ? 'note' : 'notes'}` : ''}</summary>
              <ul className="mt-2 space-y-1 text-[14px] text-ink-soft">
                {passes.map((c) => <li key={c.id}>✓ {c.message}</li>)}
                {notes.map((c) => <li key={c.id} className="text-haldi-dark">Note: {c.message}</li>)}
              </ul>
            </details>
          </section>
        )}

        <StickyBar hint={!result && missing && <Hint>{missing}</Hint>}>
          {outcome === 'verified' ? (
            <button className="btn-primary w-full" onClick={() => nav(`/order/${id}/pay?key=${key}`)}>{t('continue')}</button>
          ) : outcome === 'review' ? (
            <button className="btn-secondary w-full" onClick={() => nav(`/track/${id}?key=${key}`)}>{t('track_title')}</button>
          ) : (
            <button className="btn-primary w-full" onClick={verify} disabled={!!busy || !!missing}>{t('verify_now')}</button>
          )}
        </StickyBar>
        <p className="rounded-xl bg-white px-3 py-2 text-[14px] text-ink-soft ring-1 ring-rule">{t('never_ask')}</p>

      </>
    )
  }

  const hasDoc = Object.values(docs).some((d) => d.status !== 'empty')
  const missing = !route ? t('need_route') : !hasDoc ? t('need_doc') : null

  return (
    <Shell title={t('kyc_title')} width="wide" step="verify">
      <Split aside={aside()}>
      <p className="text-[17px] text-ink-soft">{t('kyc_intro')}</p>

      <section className="card mt-5 p-5">
        <h2 id="route-title" className="section-title mb-3">{t('route_title')}</h2>
        <div className="grid gap-2 sm:grid-cols-3" role="radiogroup" aria-labelledby="route-title">
          {(['gst', 'udyam', 'shop_licence'] as const).map((r) => (
            <button key={r} role="radio" aria-checked={route === r} onClick={() => chooseRoute(r)} className="choice">
              {t(r === 'gst' ? 'route_gst' : r === 'udyam' ? 'route_udyam' : 'route_shop')}
            </button>
          ))}
        </div>
        {gstOnly.length > 0 && <p className="mt-2 rounded-lg bg-haldi-soft px-3 py-2 text-[15px] text-haldi-dark">{t('needs_gst')}: {gstOnly.join(', ')}</p>}
        {route === 'shop_licence' && (
          <div className="mt-3 rounded-xl border-2 border-leaf bg-leaf/10 p-4">
            <p className="font-bold text-leaf">{t('udyam_free_title')}</p>
            <p className="mt-1 text-[15px]">{t('udyam_free_sub')}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <a className="btn-secondary" href="https://udyamregistration.gov.in/UdyamRegistration.aspx" target="_blank" rel="noreferrer">{t('udyam_free_go')}</a>
              <button className="btn-quiet border border-rule-strong" onClick={() => chooseRoute('udyam')}>{t('i_have_udyam')}</button>
            </div>
          </div>
        )}
      </section>

      {route === 'gst' && <section className="card mt-5 p-5">
        <label className="block font-bold" htmlFor="gstin">{t('gstin_label')}</label>
        {order?.gstin_masked && !registry && <p className="text-[15px] text-ink-soft">{order.gstin_masked}</p>}
        <div className="mt-2 flex gap-2">
          <input id="gstin" className="field flex-1 uppercase tracking-wider" maxLength={15} value={gstin} onChange={(e) => setGstin(e.target.value.toUpperCase())} placeholder="27ABCDE1234F1Z5" />
          <button className="btn-secondary" onClick={check} disabled={gstin.length !== 15}>{t('check')}</button>
        </div>
        {registry && (
          <p className={`mt-2 text-[15px] ${registry.registry?.status === 'Active' ? 'text-leaf' : 'text-kumkum-dark'}`}>
            {registry.found ? `${registry.registry.trade_name}, ${registry.registry.constitution}, ${registry.registry.status}` : 'Not found in the GST registry'}
          </p>
        )}
      </section>}

      {route && <h2 className="section-title mt-8">{t('documents')}</h2>}
      <ul className="mt-3 grid gap-3 md:grid-cols-2">
        {DOCS.filter((d) => route && (ROUTE_DOCS[route].includes(d) || (d === 'rent_agreement' && (rented || docs.rent_agreement.status !== 'empty')))).map((d) => {
          const s = docs[d]
          return (
            <li key={d} className={`card p-4 ${s.status === 'read' || s.status === 'digilocker' ? 'ring-1 ring-leaf/40' : s.status === 'retake' ? 'ring-1 ring-haldi' : ''}`}>
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold">{t(`doc_${d}`)}</p>
                {s.status === 'read' && <Stamp kind="ok">{t('read_ok')}</Stamp>}
                {s.status === 'digilocker' && <Stamp kind="ok">DigiLocker</Stamp>}
                {s.status === 'retake' && <Stamp kind="fix">{t('retake')}</Stamp>}
              </div>
              {s.fields && Object.keys(s.fields).length > 0 && (
                <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 text-[14px] text-ink-soft">
                  {Object.entries(s.fields).slice(0, 4).flatMap(([k, v]) => [
                    <dt key={k + 'k'}>{LABELS[k] ?? k.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())}</dt>,
                    <dd key={k + 'v'} className="truncate text-ink">{v}</dd>,
                  ])}
                </dl>
              )}
              {s.skew ? <p className="mt-1 text-[13px] text-ink-faint">Straightened by {Math.abs(s.skew)}°</p> : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <input ref={(el) => (inputs.current[d] = el)} type="file" accept="image/*" capture="environment" className="hidden"
                  onChange={(e) => e.target.files?.[0] && upload(d, e.target.files[0])} />
                <button className="btn-secondary min-h-[42px] text-[15px]" onClick={() => inputs.current[d]?.click()} disabled={s.status === 'uploading'}>
                  {s.status === 'uploading' ? '…' : s.status === 'empty' ? t('take_photo') : t('retake')}
                </button>
                {d === 'udyam_certificate' && (s.status === 'empty' || s.status === 'retake') && (
                  <div className="flex w-full gap-2">
                    <input className="field min-h-[42px] flex-1 text-[15px] uppercase" value={udyam} onChange={(e) => setUdyam(e.target.value.toUpperCase())} placeholder="UDYAM-MH-00-1234567" aria-label="Udyam number" />
                    <button className="btn-quiet border border-rule-strong" onClick={digilocker}>{t('digilocker')}</button>
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      <details className="mt-4 rounded-xl border border-dashed border-rule-strong bg-paper-tint p-4">
        <summary className="cursor-pointer font-semibold text-ink">Demo: use a specimen applicant (K01 to K12, plus our K02R)</summary>
        <div className="mt-3 grid grid-cols-5 gap-2 sm:grid-cols-7">
          {SPECIMENS.map((k) => <button key={k} className="chip justify-center" onClick={() => specimen(k)}>{k}</button>)}
        </div>
        <p className="mt-2 text-[13px] text-ink-soft">Uploads the official synthetic documents for that applicant and runs the same checks. K02R is ours: K02's clinic in a rented unit, the bill in the landlord's name.</p>
      </details>

      </Split>
    </Shell>
  )
}
