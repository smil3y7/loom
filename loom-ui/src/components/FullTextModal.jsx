import { useEffect, useState } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { api } from '../lib/api.js'

export default function FullTextModal({ dream, onClose }) {
  const { t } = useI18n()
  // `cycles === null` → še ni naloženo / se nalaga, ali je noč z enim
  // samim ciklom, ali je nalaganje spodletelo. V vseh teh primerih se UI
  // obnaša natanko kot prej — samo `dream`, brez cycle-switcherja, tako
  // da ta feature nikoli ne pokvari obstoječega single-cycle prikaza.
  const [cycles, setCycles] = useState(null)
  const [activeIndex, setActiveIndex] = useState(0)

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [onClose])

  useEffect(() => {
    setCycles(null)
    setActiveIndex(0)
    if (!dream?.dream_id) return
    let cancelled = false
    api.cycles(dream.dream_id)
      .then(res => {
        if (cancelled) return
        setCycles(res.total_cycles > 1 ? res.cycles : null)
        // Poišči začetni aktivni tab — dream_id ki smo ga odprli, ne vedno
        // prvi cikel (uporabnik je morda kliknil na 2. ali 3. cikel neke
        // noči direktno iz Search/Clusters kartice).
        if (res.total_cycles > 1) {
          const idx = res.cycles.findIndex(c => c.dream_id === dream.dream_id)
          setActiveIndex(idx >= 0 ? idx : 0)
        }
      })
      .catch(() => {
        // Tiho pade nazaj na single-cycle prikaz — mrežna napaka pri
        // cycles fetchu ne sme onemogočiti prikaza sanje, ki jo že imamo.
        if (!cancelled) setCycles(null)
      })
    return () => { cancelled = true }
  }, [dream?.dream_id])

  if (!dream) return null

  // Aktivna vsebina — iz cycles[activeIndex] če je multi-cycle noč, sicer
  // iz prvotno posredovanega `dream` propa (nespremenjeno obnašanje).
  const active = cycles ? cycles[activeIndex] : dream

  const src = active.source_app?.replace('browser_atlas', 'browser') || ''
  const date = active.timestamp?.slice(0, 10) || active.date || '—'
  const fullText = active.full_content || active.content || active.excerpt || '—'

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
              {active.title || t('common.no_title')}
            </h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{date}</span>
              {src && <span className="source-badge">{src}</span>}
              {active.language && <span className="badge badge-neutral" style={{ fontSize: 11 }}>{active.language}</span>}
            </div>
          </div>
          <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: 13, flexShrink: 0 }} onClick={onClose}>
            {t('common.close')} <span style={{ opacity: 0.5, fontSize: 11 }}>ESC</span>
          </button>
        </div>

        {cycles && cycles.length > 1 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 6 }}>
              {t('cycles.night_notice')}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {cycles.map((c, i) => (
                <button
                  key={c.dream_id}
                  className={`btn ${i === activeIndex ? 'btn-primary' : 'btn-ghost'}`}
                  style={{ padding: '4px 10px', fontSize: 12 }}
                  onClick={() => setActiveIndex(i)}
                >
                  {t('cycles.label')} {c.cycle_index ?? i + 1} {t('cycles.of')} {cycles.length}
                </button>
              ))}
            </div>
          </div>
        )}

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
