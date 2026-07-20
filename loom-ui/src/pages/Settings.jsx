import { useState } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { useTheme } from '../lib/theme.jsx'

export default function Settings() {
  const { t, lang, setLang, languages } = useI18n()
  const { theme, setTheme } = useTheme()
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem('loom_api_url') || import.meta.env.VITE_API_URL || 'http://localhost:8000'
  )
  const [saved, setSaved] = useState(false)

  function handleSave() {
    localStorage.setItem('loom_api_url', apiUrl)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

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

      </div>
    </div>
  )
}
