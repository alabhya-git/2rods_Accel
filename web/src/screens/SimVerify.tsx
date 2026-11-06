import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { ErrorNote, Shell, Stamp, Working } from '../components/ui'
import { api } from '../lib/api'
import { useLang } from '../lib/i18n'

/** The link each business-SIM user opens: their own consent, their own KYC (DigiLocker, mocked here). */
export default function SimVerify() {
  const { id } = useParams()
  const { t } = useLang()
  const [info, setInfo] = useState<{ business_name: string; product: string; status: string } | null>(null)
  const [agree, setAgree] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => { api.get<any>(`/api/sim/${id}`).then(setInfo).catch((e) => setErr(e.message)) }, [id])

  const verify = async () => {
    try {
      const r = await api.post<{ status: string }>(`/api/sim/${id}/verify`, { method: 'digilocker', consent: agree })
      setInfo({ ...info!, status: r.status })
    } catch (e: any) { setErr(e.message) }
  }

  if (!info) return <Shell title={t('sim_title')}><Working label="…" /><ErrorNote msg={err} /></Shell>
  return (
    <Shell title={t('sim_title')}>
      <p className="text-[19px] font-semibold">{info.business_name}</p>
      <p className="text-ink-soft">{info.product}</p>
      {info.status === 'verified' ? (
        <div className="mt-6"><Stamp kind="ok">{t('sim_verified')}</Stamp><p className="mt-4">{t('sim_done')}</p></div>
      ) : (
        <>
          <p className="mt-4">{t('sim_intro')}</p>
          <label className="mt-5 flex items-start gap-3">
            <input type="checkbox" className="mt-1 h-6 w-6" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
            <span>{t('sim_consent')}</span>
          </label>
          <button className="btn-primary mt-6 w-full" disabled={!agree} onClick={verify}>{t('verify_me')}</button>
          <p className="mt-3 text-[13px] text-ink-soft">DigiLocker is mocked in this demo.</p>
        </>
      )}
      <ErrorNote msg={err} />
    </Shell>
  )
}
