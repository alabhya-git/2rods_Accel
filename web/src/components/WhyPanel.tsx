import { rupees, type Turn } from '../lib/api'

const NEED: Record<string, string> = {
  internet: 'Internet', high_speed: '1 Gbps internet', dedicated_line: 'Leased line', email: 'Email', mobile_lines: 'Mobile lines',
  cctv: 'CCTV', pos: 'Billing / POS', website: 'Website', backup: 'Cloud backup', endpoint: 'Antivirus', firewall: 'Firewall',
  failover: 'Backup internet', sdwan: 'SD-WAN', static_ip: 'Static IP', telephony: 'Office phone', toll_free: 'Toll-free number',
  sms: 'Bulk SMS', iot: 'Machine monitoring', fleet: 'Vehicle tracking', guest_wifi: 'Guest Wi-Fi', whatsapp: 'WhatsApp Business',
}

function understood(p: Record<string, any>): [string, string][] {
  const rows: [string, string][] = []
  if (p.business_type) rows.push(['Business', p.business_type])
  if (p.employees != null) rows.push(['Staff', String(p.employees)])
  if (p.sites != null && p.sites > 1) rows.push(['Sites', String(p.sites)])
  if (p.city) rows.push(['City', p.city_tier ? `${p.city}, tier ${p.city_tier}` : p.city])
  if (p.has_gstin != null) rows.push(['GSTIN', p.has_gstin ? (p.gstin_status || 'Declared') : 'None'])
  if (p.needs?.length) rows.push(['Needs', p.needs.map((n: string) => NEED[n] ?? n.replace(/_/g, ' ')).join(', ')])
  return rows
}

export default function WhyPanel({ turn, profile }: { turn: Turn | null; profile?: Record<string, any> }) {
  if (!turn) return <p className="text-ink-soft">Send a message to see how the advisor reasons.</p>
  const b = turn.bundle
  const lookup = turn.trace.find((s) => s.step === 'lookup_gstin')
  const llm = turn.trace.find((s) => s.step === 'llm')
  const guard = turn.trace.find((s) => s.step === 'guard')
  const rows = profile ? understood(profile) : []
  return (
    <div className="space-y-5 text-[15px]">
      <p className="text-ink-soft">
        {turn.llm_used ? 'A language model understood the message and wrote the reply.' : 'Rules-only mode: no language model was used.'} Products and prices come only from the rules engine.
      </p>

      {rows.length > 0 && (
        <section>
          <p className="font-bold">What the advisor understood</p>
          <dl className="mt-1 grid grid-cols-[84px_1fr] gap-x-3 gap-y-0.5">
            {rows.map(([k, v]) => <div key={k} className="contents"><dt className="text-ink-soft">{k}</dt><dd>{v}</dd></div>)}
          </dl>
        </section>
      )}

      {lookup && (
        <section>
          <p className="font-bold">GST registry</p>
          <p className="text-ink-soft">{lookup.result?.found ? [lookup.result.trade_name, lookup.result.constitution, lookup.result.status].filter(Boolean).join(', ') : 'Not found in the registry'}</p>
        </section>
      )}

      {b && (
        <section>
          <p className="font-bold">The rules engine chose</p>
          <ul className="mt-1 space-y-0.5">
            {b.lines.map((ln) => (
              <li key={ln.product_id} className="flex justify-between gap-3">
                <span className="min-w-0">{ln.name}{ln.qty > 1 ? ` ×${ln.qty}` : ''}</span>
                <span className="money shrink-0 whitespace-nowrap">{rupees(ln.monthly)}</span>
              </li>
            ))}
            <li className="flex justify-between gap-3 border-t border-rule pt-1 font-bold">
              <span>A month, {b.term_months} months</span><span className="money whitespace-nowrap">{rupees(b.monthly)}</span>
            </li>
          </ul>
          <p className="mt-1 text-[14px] text-ink-soft">Plus 18% GST. On a {b.term_months === 24 ? 12 : 24}-month contract: {rupees(b.monthly_other_term)} a month.</p>
        </section>
      )}

      {b && b.exclusions.length > 0 && (
        <section>
          <p className="font-bold">Refused, and the rule behind it</p>
          <ul className="mt-1 space-y-1.5">
            {b.exclusions.map((e) => (
              <li key={e.product_id} className="rounded-lg bg-kumkum-soft px-3 py-2">
                <span>{e.reason ?? `${e.name}: ${e.rule.replace(/_/g, ' ')}`}</span>
                {e.alternative_name && <span className="block text-[14px] text-ink-soft">Offered instead: {e.alternative_name}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {llm && <p className="text-[14px] text-ink-soft">{llm.error ? `Language model unavailable; the rules engine answered.` : `Model: ${llm.provider} ${llm.model}; tools called: ${(llm.tool_calls || []).map((c: any) => c.tool).join(', ') || 'none'}.`}</p>}
      {guard && <p className={`text-[14px] ${guard.passed ? 'text-leaf' : 'text-kumkum'}`}>{guard.passed ? 'Guard: every product and rupee figure in the reply matched the rules engine.' : `Guard blocked: ${guard.issues.join('; ')}. The engine's own wording was sent instead.`}</p>}
    </div>
  )
}
