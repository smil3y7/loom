import { useState, useEffect } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { useTheme } from '../lib/theme.jsx'
import { api, apiErrorMessage } from '../lib/api.js'

export default function Settings() {
  const { t, lang, setLang, languages } = useI18n()
  const { theme, setTheme } = useTheme()
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem('loom_api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000'
  )
  const [saved, setSaved] = useState(false)
  const [backendVersion, setBackendVersion] = useState(null)

  // Pairing token — glej loom/lib/auth.py. Prikazan tu za ročni copy-paste
  // v Loom Sync extension (edini realen način, ker extension ne more sam
  // brati poljubnih lokalnih datotek).
  const [token, setToken] = useState(null)
  const [tokenError, setTokenError] = useState(null)
  const [copied, setCopied] = useState(false)
  const [confirmRegen, setConfirmRegen] = useState(false)
  const [regenBusy, setRegenBusy] = useState(false)
  const [regenDone, setRegenDone] = useState(false)

  // UI verzija je vgrajena ob buildu (glej vite.config.js) — vedno
  // ustreza dejansko naloženi kodi, ne rabi API klica.
  const uiVersion = typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '?'

  useEffect(() => {
    api.health()
      .then(res => setBackendVersion(res.version))
      .catch(() => setBackendVersion(null))
  }, [])

  useEffect(() => {
    api.token()
      .then(res => setToken(res.token))
      .catch(e => setTokenError(apiErrorMessage(e, t)))
  }, [])

  function handleSave() {
    localStorage.setItem('loom_api_url', apiUrl)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  function copyToken() {
    navigator.clipboard.writeText(token)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  async function handleRegenerate() {
    setRegenBusy(true)
    setTokenError(null)
    try {
      const res = await api.regenerateToken()
      setToken(res.token)
      setConfirmRegen(false)
      setRegenDone(true)
      setTimeout(() => setRegenDone(false), 3000)
    } catch (e) {
      setTokenError(apiErrorMessage(e, t))
    } finally {
      setRegenBusy(false)
    }
  }

  const versionMismatch = backendVersion && backendVersion !== uiVersion

  return (
    <div className="page">
      <div className="page-header">
        <h2>{t('settings.title')}</h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 480 }}>

        <div className="card">
          <div className="section-title">{t('settings.language')}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {languages.map(l => (
              <button
                key={l.code}
                className={`btn ${lang === l.code ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setLang(l.code)}
              >
                {l.name}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="section-title">{t('settings.theme')}</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {['light', 'dark', 'system'].map(th => (
              <button
                key={th}
                className={`btn ${theme === th ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setTheme(th)}
              >
                {t(`settings.theme.${th}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="section-title">{t('settings.api')}</div>
          <label style={{ fontSize: 13, color: 'var(--text-2)', display: 'block', marginBottom: 8 }}>
            {t('settings.apiUrl')}
            <span style={{ color: 'var(--text-3)', marginLeft: 8, fontSize: 12 }}>
              {t('settings.apiUrl.hint')}
            </span>
          </label>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              className="input"
              value={apiUrl}
              onChange={e => setApiUrl(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleSave}>
              {saved ? t('settings.saved') : t('settings.save')}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="section-title">{t('settings.pairing')}</div>
          <p style={{ fontSize: 13, color: 'var(--text-2)', marginBottom: 12, lineHeight: 1.5 }}>
            {t('settings.pairing.hint')}
          </p>

          {tokenError && (
            <p style={{ color: 'var(--err)', fontSize: 13, marginBottom: 12 }}>{tokenError}</p>
          )}

          {token && (
            <>
              <label style={{ fontSize: 13, color: 'var(--text-2)', display: 'block', marginBottom: 8 }}>
                {t('settings.pairing.token')}
              </label>
              <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
                <input className="input" value={token} readOnly style={{ fontFamily: 'monospace', fontSize: 13 }} />
                <button className="btn btn-secondary" onClick={copyToken}>
                  {copied ? t('settings.pairing.copied') : t('settings.pairing.copy')}
                </button>
              </div>
              <button className="btn btn-ghost" style={{ fontSize: 13 }} onClick={() => setConfirmRegen(true)}>
                {t('settings.pairing.regenerate')}
              </button>
              {regenDone && (
                <span style={{ color: 'var(--ok)', fontSize: 13, marginLeft: 10 }}>
                  {t('settings.pairing.regenerated')}
                </span>
              )}
            </>
          )}

          {confirmRegen && (
            <div className="dialog-overlay" onClick={() => !regenBusy && setConfirmRegen(false)}>
              <div className="dialog" onClick={e => e.stopPropagation()}>
                <h3>{t('settings.pairing.regenerate.confirmTitle')}</h3>
                <p style={{ margin: '12px 0 20px', fontSize: 14, color: 'var(--text-2)' }}>
                  {t('settings.pairing.regenerate.confirmBody')}
                </p>
                <div className="dialog-actions">
                  <button className="btn btn-secondary" disabled={regenBusy} onClick={() => setConfirmRegen(false)}>
                    {t('common.cancel')}
                  </button>
                  <button className="btn btn-danger" disabled={regenBusy} onClick={handleRegenerate}>
                    {t('settings.pairing.regenerate')}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="section-title">{t('settings.about')}</div>
          <div style={{ fontSize: 13, color: 'var(--text-2)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div>{t('settings.version.ui')}: <strong>{uiVersion}</strong></div>
            <div>
              {t('settings.version.backend')}:{' '}
              <strong>{backendVersion || t('common.unknown')}</strong>
            </div>
            {versionMismatch && (
              <div style={{ color: 'var(--warn)', fontSize: 12, marginTop: 4 }}>
                {t('settings.version.mismatch')}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}

