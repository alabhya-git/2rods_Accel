import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ErrorNote, Shell, StickyBar, Toggle, Working } from '../components/ui'
import { api } from '../lib/api'
import { useLang } from '../lib/i18n'

type Purpose = { required: boolean; data: string[] }

export default function Consent() {
  const { id } = useParams()
  const key = new URLSearchParams(location.search).get('key')
  const { lang, t } = useLang()
  const nav = useNavigate()
  const [notice, setNotice] = useState<{ version: string; purposes: Record<string, Purpose> } | null>(null)
  const [choices, setChoices] = useState<Record<string, boolean>>({})
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ version: string; purposes: Record<string, Purpose> }>('/api/consent/notice').then((n) => {
      setNotice(n)
      setChoices(Object.fromEntries(Object.entries(n.purposes).map(([k, p]) => [k, p.required])))
    })
  }, [])

  const agree = async () => {
    try {
      await api.post(`/api/orders/${id}/consent?key=${key}`, { choices, language: lang, channel: 'web' })
      nav(`/order/${id}/kyc?key=${key}`)
    } catch (e: any) {
      setErr(e.message)
    }
  }
  if (!notice) return <Shell title={t('consent_title')}><Working label="…" /></Shell>

  return (
    <Shell title={t('consent_title')}>
      <p className="text-[18px]">{t('consent_intro')}</p>
      <ul className="mt-5 divide-y divide-rule rounded-xl border border-rule bg-white">
        {Object.entries(notice.purposes).map(([k, p]) => (
          <li key={k} className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[18px] font-bold">{t(`p_${k}`)}</p>
                <p className="text-[14px] font-semibold text-ink-soft">{p.required ? t('needed') : t('optional')}</p>
              </div>
              <Toggle on={!!choices[k]} disabled={p.required} onChange={(v) => setChoices({ ...choices, [k]: v })} label={t(`p_${k}`)} />
            </div>
            <p className="mt-2">{t(`p_${k}_use`)}</p>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[15px] text-ink-soft">
              <dt>{t('data_used')}</dt><dd>{p.data.join(', ')}</dd>
              <dt>{t('kept')}</dt><dd>{t(`p_${k}_keep`)}</dd>
            </dl>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[13px] text-ink-faint">Notice {notice.version}, under the Digital Personal Data Protection Act, 2023 and the DPDP Rules, 2025.</p>
      <ErrorNote msg={err} />
      <StickyBar><button className="btn-primary w-full" onClick={agree}>{t('agree')}</button></StickyBar>
    </Shell>
  )
}
