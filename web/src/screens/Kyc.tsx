import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ErrorNote, Shell, Stamp, StickyBar, Working } from '../components/ui'
import { api, type Check, type KycResult, type OrderView } from '../lib/api'
import { useLang } from '../lib/i18n'

const ALL_DOCS = ['gst_certificate', 'udyam_certificate', 'shop_licence', 'address_proof', 'signatory_id'] as const
// the proof route decides the documents: no GST is a route, not a dead end
const ROUTE_DOCS: Record<string, string[]> = {
  gst: ['gst_certificate', 'udyam_certificate', 'address_proof', 'signatory_id'],
  udyam: ['udyam_certificate', 'address_proof', 'signatory_id'],
  shop_licence: ['shop_licence', 'address_proof', 'signatory_id'],
}
const DOCS = ALL_DOCS
type DocState = { status: 'empty' | 'uploading' | 'read' | 'retake' | 'digilocker'; fields?: Record<string, string>; skew?: number }
const LABELS: Record<string, string> = { gstin: 'GSTIN', udyam_number: 'Udyam no.', id_no: 'ID no.', legal_name: 'Legal name', trade_name: 'Trade name', consumer_no: 'Consumer no.', billed_to: 'Billed to', supply_address: 'Address', bill_date: 'Bill date', enterprise_name: 'Enterprise', major_activity: 'Activity', valid_till: 'Valid till', business: 'Business' }
const SPECIMENS = ['K01', 'K02', 'K03', 'K04', 'K05', 'K06', 'K07', 'K08', 'K09', 'K10', 'K11', 'K12']

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

  return (
    <Shell title={t('kyc_title')}>
      <p className="text-[17px] text-ink-soft">{t('kyc_intro')}</p>

      <fieldset className="mt-5">
        <legend className="mb-2 font-bold">{t('route_title')}</legend>
        <div className="grid gap-2" role="radiogroup">
          {(['gst', 'udyam', 'shop_licence'] as const).map((r) => (
            <button key={r} role="radio" aria-checked={route === r} onClick={() => chooseRoute(r)}
              className={`rounded-xl border-2 px-4 py-3 text-left font-semibold ${route === r ? 'border-ledger bg-ledger-soft text-ledger' : 'border-rule bg-white'}`}>
              {t(r === 'gst' ? 'route_gst' : r === 'udyam' ? 'route_udyam' : 'route_shop')}
            </button>
          ))}
        </div>
        {gstOnly.length > 0 && <p className="mt-2 rounded-lg bg-haldi-soft px-3 py-2 text-[15px] text-haldi-dark">{t('needs_gst')}: {gstOnly.join(', ')}</p>}
      </fieldset>

      {route === 'gst' && <section className="mt-5 rounded-xl border border-rule bg-white p-4">
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

      <ul className="mt-4 space-y-3">
        {DOCS.filter((d) => route && ROUTE_DOCS[route].includes(d)).map((d) => {
          const s = docs[d]
          return (
            <li key={d} className="rounded-xl border border-rule bg-white p-4">
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
                    <button className="btn-quiet border border-ledger" onClick={digilocker}>{t('digilocker')}</button>
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ul>

      <details className="mt-4 rounded-xl border border-dashed border-rule-strong bg-paper-tint p-4">
        <summary className="cursor-pointer font-semibold text-ledger">Demo: use a specimen applicant (K01 to K12)</summary>
        <div className="mt-3 grid grid-cols-6 gap-2">
          {SPECIMENS.map((k) => <button key={k} className="chip justify-center" onClick={() => specimen(k)}>{k}</button>)}
        </div>
        <p className="mt-2 text-[13px] text-ink-soft">Uploads the official synthetic documents for that applicant and runs the same checks.</p>
      </details>

      {busy && <div className="mt-5"><Working label={busy} /></div>}
      <ErrorNote msg={err} />

      {result && !busy && (
        <section className="mt-6 rounded-xl border-2 border-rule bg-white p-5" aria-live="polite">
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
          <details className="mt-4">
            <summary className="cursor-pointer text-[15px] text-ledger">{passes.length} checks passed{notes.length ? `, ${notes.length} ${notes.length === 1 ? 'note' : 'notes'}` : ''}</summary>
            <ul className="mt-2 space-y-1 text-[14px] text-ink-soft">
              {passes.map((c) => <li key={c.id}>✓ {c.message}</li>)}
              {notes.map((c) => <li key={c.id} className="text-haldi-dark">Note: {c.message}</li>)}
            </ul>
          </details>
        </section>
      )}

      <StickyBar>
        {outcome === 'verified' ? (
          <button className="btn-primary w-full" onClick={() => nav(`/order/${id}/pay?key=${key}`)}>{t('continue')}</button>
        ) : outcome === 'review' ? (
          <button className="btn-secondary w-full" onClick={() => nav(`/track/${id}?key=${key}`)}>{t('track_title')}</button>
        ) : (
          <button className="btn-primary w-full" onClick={verify} disabled={!!busy || !Object.values(docs).some((d) => d.status !== 'empty')}>{t('verify_now')}</button>
        )}
      </StickyBar>
    </Shell>
  )
}
