import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorNote, Shell, StickyBar, Working } from '../components/ui'
import { api, rupees } from '../lib/api'
import { useLang } from '../lib/i18n'

type Product = { id: string; name: string; description: string; category: string; unit: string; price_min: number; tiers: number[]
  min_employees: number; min_sites: number; requires_gstin: boolean; requires_one_of: string[] }

/** "I know what I need": pick products, see eligibility and price at once. Skips the advisor, never the rules. */
export default function Express() {
  const { t, lang } = useLang()
  const nav = useNavigate()
  const [products, setProducts] = useState<Product[] | null>(null)
  const [cities, setCities] = useState<{ city: string; tier: number }[]>([])
  const [city, setCity] = useState('')
  const [staff, setStaff] = useState(2)
  const [gst, setGst] = useState<boolean | null>(null)
  const [picked, setPicked] = useState<Record<string, number>>({})
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ products: Product[] }>('/api/catalogue').then((r) => setProducts(r.products)).catch((e) => setErr(e.message))
    api.get<{ cities: { city: string; tier: number }[] }>('/api/cities').then((r) => setCities(r.cities)).catch(() => {})
  }, [])

  const tier = cities.find((c) => c.city.toLowerCase() === city.trim().toLowerCase())?.tier ?? null
  const blocked = (p: Product): string | null => {
    if (tier !== null && !p.tiers.includes(tier)) return t('not_available')
    if (p.requires_gstin && gst === false) return t('needs_gst')
    if (p.min_employees > staff) return `${p.min_employees}+`
    return null
  }
  const groups = useMemo(() => {
    const g: Record<string, Product[]> = {}
    products?.forEach((p) => (g[p.category] ??= []).push(p))
    return g
  }, [products])

  const go = () => {
    const profile = { city: city.trim() || null, city_tier: tier, employees: staff, has_gstin: gst === true, gstin_status: gst ? 'Declared' : null,
      needs: [], only: true, language: lang }
    sessionStorage.setItem('express', JSON.stringify({ profile, items: picked }))
    nav('/quote?express=1')
  }

  if (!products) return <Shell back="/" title={t('express_title')}><Working label="…" /><ErrorNote msg={err} /></Shell>
  return (
    <Shell back="/" title={t('express_title')}>
      <section className="space-y-3">
        <label className="block">
          <span className="mb-1 block font-semibold">{t('city_label')}</span>
          <input className="field" list="cities" value={city} onChange={(e) => setCity(e.target.value)} autoComplete="address-level2" />
          <datalist id="cities">{cities.map((c) => <option key={c.city} value={c.city} />)}</datalist>
        </label>
        <div className="flex items-center justify-between gap-3">
          <span className="font-semibold">{t('staff_label')}</span>
          <span className="flex items-center gap-2">
            <button className="h-11 w-11 rounded-full border-2 border-rule text-[20px]" onClick={() => setStaff(Math.max(1, staff - 1))} aria-label="−">−</button>
            <span className="w-10 text-center text-[20px] font-bold">{staff}</span>
            <button className="h-11 w-11 rounded-full border-2 border-rule text-[20px]" onClick={() => setStaff(staff + 1)} aria-label="+">+</button>
          </span>
        </div>
        <div className="flex items-center justify-between gap-3">
          <span className="font-semibold">{t('gst_question')}</span>
          <span className="flex gap-2">
            {[true, false].map((v) => (
              <button key={String(v)} className={`chip ${gst === v ? '!border-ledger !bg-ledger !text-white' : ''}`} aria-pressed={gst === v} onClick={() => setGst(v)}>
                {v ? t('yes_word') : t('no_word')}
              </button>
            ))}
          </span>
        </div>
      </section>

      {Object.entries(groups).map(([cat, ps]) => (
        <section key={cat} className="mt-6">
          <h2 className="text-[15px] font-semibold text-ink-soft">{cat}</h2>
          <ul className="mt-2 divide-y divide-rule rounded-xl border border-rule">
            {ps.map((p) => {
              const why = blocked(p)
              const on = p.id in picked
              return (
                <li key={p.id}>
                  <button className="flex w-full items-start justify-between gap-3 p-3 text-left disabled:opacity-60" disabled={!!why}
                    aria-pressed={on} onClick={() => { const n = { ...picked }; if (on) delete n[p.id]; else n[p.id] = 1; setPicked(n) }}>
                    <span className="min-w-0">
                      <span className="block font-semibold">{p.name}</span>
                      <span className="block text-[14px] leading-snug text-ink-soft">{p.description}</span>
                      {why && <span className="mt-1 block text-[14px] text-kumkum-dark">{why}</span>}
                    </span>
                    <span className="shrink-0 text-right">
                      <span className="block text-[14px] text-ink-soft">{t('from_month', { amount: rupees(p.price_min) })}</span>
                      <span className={`mt-1 inline-block h-6 w-6 rounded-md border-2 ${on ? 'border-leaf bg-leaf' : 'border-rule'}`} aria-hidden="true" />
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
      ))}
      <ErrorNote msg={err} />
      <StickyBar>
        <button className="btn-primary w-full" disabled={!Object.keys(picked).length || gst === null} onClick={go}>{t('get_price')}</button>
      </StickyBar>
    </Shell>
  )
}
