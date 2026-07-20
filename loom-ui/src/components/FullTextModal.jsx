import { useEffect } from 'react'
import { useI18n } from '../i18n/index.jsx'

export default function FullTextModal({ dream, onClose }) {
  const { t } = useI18n()

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [onClose])

  if (!dream) return null

  const src = dream.source_app?.replace('browser_atlas', 'browser') || ''
  const date = dream.timestamp?.slice(0, 10) || dream.date || '—'
  const fullText = dream.full_content || dream.content || dream.excerpt || '—'

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div
        className="dialog"
        style={{ width: 680, maxWidth: '95vw', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12, gap: 12 }}>
          <div>
            <h3 style={{ fontSize: 20, marginBottom: 6 }}>
              {dream.title || t('common.no_title')}
            </h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{date}</span>
              {src && <span className="source-badge">{src}</span>}
              {dream.language && <span className="badge badge-neutral" style={{ fontSize: 11 }}>{dream.language}</span>}
            </div>
          </div>
          <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: 13, flexShrink: 0 }} onClick={onClose}>
            {t('common.close')} <span style={{ opacity: 0.5, fontSize: 11 }}>ESC</span>
          </button>
        </div>
        <div style={{
          overflowY: 'auto', flex: 1,
          fontSize: 14, lineHeight: 1.85,
          color: 'var(--text-2)',
          whiteSpace: 'pre-wrap',
          paddingRight: 4,
        }}>
          {fullText}
        </div>
      </div>
    </div>
  )
}
