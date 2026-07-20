import { useI18n } from '../i18n/index.jsx'

export default function Help() {
  const { t } = useI18n()

  const sections = [
    { q: t('help.what'), a: t('help.what.text') },
    { q: t('help.search'), a: t('help.search.text') },
    { q: t('help.patterns'), a: t('help.patterns.text') },
    { q: t('help.embeddings'), a: t('help.embeddings.text') },
    { q: t('help.privacy'), a: t('help.privacy.text') },
  ]

  return (
    <div className="page">
      <div className="page-header">
        <h2>{t('help.title')}</h2>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 640 }}>
        {sections.map((s, i) => (
          <div key={i} className="card">
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 10, color: 'var(--text)' }}>
              {s.q}
            </div>
            <p style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.7 }}>
              {s.a}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
