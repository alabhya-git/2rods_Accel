import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, ErrorNote, Hint, Shell, Split, StickyBar, Svg, Working } from '../components/ui'
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

  if (!products) return <Shell back="/" title={t('express_title')} width="wide" step="choose"><Working label="…" /><ErrorNote msg={err} /></Shell>
  const chosen = products.filter((p) => p.id in picked)
  // say exactly what is missing instead of leaving a grey button
  const missing = gst === null ? t('gst_question') : chosen.length === 0 ? t('pick_one') : null

  return (
    <Shell back="/" title={t('express_title')} width="wide" step="choose">
      <Split aside={
        <>
          <Card title={t('your_selection')} className="hidden lg:block">
            {chosen.length === 0 ? <p className="text-ink-soft">{t('pick_one')}</p> : (
              <ul className="space-y-2">
                {chosen.map((p) => (
                  <li key={p.id} className="flex items-start justify-between gap-3">
                    <span className="font-semibold leading-snug">{p.name}</span>
                    <span className="shrink-0 text-[14px] text-ink-soft">{t('from_month', { amount: rupees(p.price_min) })}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <StickyBar hint={missing && <Hint>{missing}</Hint>}>
            <span className="text-[15px] font-semibold text-ink-soft lg:hidden">{t('n_selected', { n: chosen.length })}</span>
            <button className="btn-primary flex-1" disabled={!!missing} onClick={go}>{t('get_price')}</button>
          </StickyBar>
        </>
      }>
        <Card title={t('your_business')}>
          <div className="grid gap-4 md:grid-cols-[1.4fr_1fr]">
            <label className="block">
              <span className="label">{t('city_label')}</span>
              <input className="field" list="cities" value={city} onChange={(e) => setCity(e.target.value)} autoComplete="address-level2" />
              <datalist id="cities">{cities.map((c) => <option key={c.city} value={c.city} />)}</datalist>
            </label>
            <div>
              <span className="label">{t('staff_label')}</span>
              <span className="flex h-[50px] items-center gap-2">
                <button className="grid h-11 w-11 place-items-center rounded-full border-[1.5px] border-rule-strong text-[20px] hover:border-ink" onClick={() => setStaff(Math.max(1, staff - 1))} aria-label="−">−</button>
                <span className="w-12 text-center text-[20px] font-bold" aria-live="polite">{staff}</span>
                <button className="grid h-11 w-11 place-items-center rounded-full border-[1.5px] border-rule-strong text-[20px] hover:border-ink" onClick={() => setStaff(staff + 1)} aria-label="+">+</button>
              </span>
            </div>
          </div>
          <div className="mt-4">
            <span className="label">{t('gst_question')}</span>
            <div className="grid max-w-sm grid-cols-2 gap-2" role="radiogroup" aria-label={t('gst_question')}>
              {[true, false].map((v) => (
                <button key={String(v)} role="radio" className="choice text-center" aria-checked={gst === v} onClick={() => setGst(v)}>
                  {v ? t('yes_word') : t('no_word')}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {Object.entries(groups).map(([cat, ps]) => (
          <section key={cat} className="mt-8">
            <h2 className="text-[13px] font-bold uppercase tracking-[0.08em] text-ink-soft">{cat}</h2>
            <ul className="mt-3 grid gap-3 md:grid-cols-2">
              {ps.map((p) => {
                const why = blocked(p)
                const on = p.id in picked
                return (
                  <li key={p.id}>
                    <button className="choice flex h-full w-full items-start justify-between gap-3 !font-normal disabled:cursor-not-allowed disabled:bg-paper-tint disabled:opacity-70"
                      disabled={!!why} aria-pressed={on}
                      onClick={() => { const n = { ...picked }; if (on) delete n[p.id]; else n[p.id] = 1; setPicked(n) }}>
                      <span className="min-w-0">
                        <span className={`block font-bold ${on ? 'text-kumkum-dark' : 'text-ink'}`}>{p.name}</span>
                        <span className="mt-0.5 block text-[14px] leading-snug text-ink-soft">{p.description}</span>
                        <span className="mt-2 block text-[14px] font-semibold text-ink">{t('from_month', { amount: rupees(p.price_min) })}</span>
                        {why && <span className="mt-1 block text-[14px] font-semibold text-kumkum-dark">{why}</span>}
                      </span>
                      <span className={`mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md border-2 ${on ? 'border-kumkum bg-kumkum text-white' : 'border-rule-strong bg-white'}`} aria-hidden="true">
                        {on && <Svg d={<path d="M5 12.5l4.5 4.5L19 7" />} size={15} width={3.5} />}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
        <ErrorNote msg={err} />
      </Split>
    </Shell>
  )
}
