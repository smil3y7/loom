import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n/index.jsx'
import { api, apiErrorMessage } from '../lib/api.js'
import FullTextModal from '../components/FullTextModal.jsx'

// ── Similar dreams panel ──────────────────────────────────────────────────────

function SimilarPanel({ dreamId, dreamTitle, onClose, t }) {
  const [results, setResults] = useState(null)
  const [modal, setModal] = useState(null)

  useEffect(() => {
    api.similar(dreamId, 10)
      .then(res => setResults(res.results || []))
      .catch(() => setResults([]))
  }, [dreamId])

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      style={{
        position: 'fixed', right: 0, top: 0, bottom: 0,
        width: 400,
        background: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        boxShadow: '-4px 0 24px rgba(0,0,0,0.15)',
        display: 'flex', flexDirection: 'column',
        zIndex: 50,
      }}
    >
      <div style={{
        padding: '20px 20px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 4 }}>
            {t('search.similar_title')}
          </div>
          <div style={{ fontSize: 15, fontWeight: 500, color: 'var(--text)', maxWidth: 280 }}>
            {dreamTitle || t('common.no_title')}
          </div>
        </div>
        <button
          className="btn btn-ghost"
          style={{ padding: '6px 10px', flexShrink: 0 }}
          onClick={onClose}
          title="ESC"
        >
          ✕
        </button>
      </div>

      <div style={{ overflowY: 'auto', flex: 1, padding: '12px 16px' }}>
        {results === null ? (
          <div className="loading-state"><div className="spinner" /></div>
        ) : results.length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--text-3)', padding: '20px 0' }}>
            {t('search.noResults')} —
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {results.map(r => (
              <div key={r.dream_id} className="dream-card">
                <div className="dream-meta">
                  <span className="dream-date">{r.timestamp?.slice(0, 10)}</span>
                  <span className="source-badge">
                    {r.source_app?.replace('browser_atlas', 'browser')}
                  </span>
                  {r.similarity && (
                    <span className="dream-similarity">
                      {(r.similarity * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                {r.title && <div className="dream-title">{r.title}</div>}
                <div className="dream-excerpt">{r.excerpt}</div>
                <button
                  style={{ marginTop: 8, fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  onClick={() => setModal(r)}
                >
                  {t('search.full_text')} →
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {modal && <FullTextModal dream={modal} onClose={() => setModal(null)} />}
    </div>
  )
}

// ── Dream card ────────────────────────────────────────────────────────────────

function DreamCard({ result, onSimilar, onFullText, t }) {
  const date = result.timestamp?.slice(0, 10) || '—'
  const src = result.source_app?.replace('browser_atlas', 'browser') || '—'
  const sim = result.similarity ? `${(result.similarity * 100).toFixed(0)}%` : null

  return (
    <div className="dream-card">
      <div className="dream-meta">
        <span className="dream-date">{date}</span>
        <span className="source-badge">{src}</span>
        <span className="badge badge-neutral" style={{ fontSize: 11 }}>{result.language}</span>
        {sim && <span className="dream-similarity">{sim}</span>}
      </div>
      {result.title && <div className="dream-title">{result.title}</div>}
      <div className="dream-excerpt">{result.excerpt}</div>
      <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
        <button
          onClick={() => onFullText(result)}
          style={{ fontSize: 12, color: 'var(--text-3)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
        >
          {t('search.full_text')} →
        </button>
        <button
          onClick={() => onSimilar(result)}
          style={{ fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
        >
          {t('search.similar')} →
        </button>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function Search() {
  const { t } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [allResults, setAllResults] = useState([])
  const [visibleCount, setVisibleCount] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)
  const [filterLang, setFilterLang] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [similar, setSimilar] = useState(null)
  const [modal, setModal] = useState(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const q = searchParams.get('q')
    if (q) { setQuery(q); doSearch(q) }
  }, [])

  async function doSearch(q) {
    if (!q?.trim()) return
    setLoading(true)
    setError(null)
    setSimilar(null)
    setSearched(true)
    setVisibleCount(10)
    setSearchParams({ q: q.trim() })
    try {
      const res = await api.search(q.trim(), { limit: 200 })
      setAllResults(res.results || [])
    } catch (e) {
      setError(apiErrorMessage(e, t))
      setAllResults([])
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setQuery('')
    setAllResults([])
    setSearched(false)
    setError(null)
    setSimilar(null)
    setSearchParams({})
    inputRef.current?.focus()
  }

  const filtered = allResults.filter(r => {
    if (filterLang && r.language !== filterLang) return false
    if (filterSource && r.source_app !== filterSource) return false
    return true
  })

  const visible = filtered.slice(0, visibleCount)
  const sources = [...new Set(allResults.map(r => r.source_app))].filter(Boolean)
  const languages = [...new Set(allResults.map(r => r.language))].filter(Boolean)

  return (
    <div className="page">
      <div className="page-header">
        <h2>{t('search.title')}</h2>
        <p>{t('search.subtitle')}</p>
      </div>

      {/* Search bar */}
      <form onSubmit={e => { e.preventDefault(); doSearch(query) }} className="search-bar">
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            ref={inputRef}
            className="input"
            placeholder={t('search.placeholder')}
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
            style={{ paddingRight: query ? 36 : 14 }}
          />
          {query && (
            <button
              type="button"
              onClick={handleClear}
              style={{
                position: 'absolute', right: 10, top: '50%',
                transform: 'translateY(-50%)',
                background: 'none', border: 'none',
                color: 'var(--text-3)', cursor: 'pointer', fontSize: 16,
              }}
            >✕</button>
          )}
        </div>
        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : t('search.button')}
        </button>
      </form>

      {/* Filters */}
      {allResults.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
          <select className="input" style={{ width: 'auto' }} value={filterLang}
            onChange={e => { setFilterLang(e.target.value); setVisibleCount(10) }}>
            <option value="">{t('search.filter.language')}: {t('search.filter.all')}</option>
            {languages.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
          <select className="input" style={{ width: 'auto' }} value={filterSource}
            onChange={e => { setFilterSource(e.target.value); setVisibleCount(10) }}>
            <option value="">{t('search.filter.source')}: {t('search.filter.all')}</option>
            {sources.map(s => <option key={s} value={s}>{s.replace('browser_atlas', 'browser')}</option>)}
          </select>
          {(filterLang || filterSource) && (
            <button className="btn btn-ghost" style={{ fontSize: 13 }}
              onClick={() => { setFilterLang(''); setFilterSource(''); setVisibleCount(10) }}>
              {t('common.clear')}
            </button>
          )}
          <span style={{ fontSize: 13, color: 'var(--text-3)', marginLeft: 'auto' }}>
            {filtered.length} {t('search.results').toLowerCase()}
          </span>
        </div>
      )}

      {error && (
        <div className="card" style={{ borderColor: 'var(--err)', marginBottom: 20 }}>
          <p style={{ color: 'var(--err)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      {searched && !loading && filtered.length === 0 && !error && (
        <div className="empty-state">
          <p>{t('search.noResults')} „{query}"</p>
        </div>
      )}

      {visible.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {visible.map(result => (
            <DreamCard
              key={result.dream_id}
              result={result}
              t={t}
              onFullText={r => setModal(r)}
              onSimilar={r => setSimilar(
                similar?.dreamId === r.dream_id ? null : { dreamId: r.dream_id, title: r.title }
              )}
            />
          ))}
          {visibleCount < filtered.length && (
            <button
              className="btn btn-secondary"
              style={{ alignSelf: 'center', marginTop: 8 }}
              onClick={() => setVisibleCount(v => v + 10)}
            >
              {t('search.show_more')} ({filtered.length - visibleCount})
            </button>
          )}
        </div>
      )}

      {/* Full text modal */}
      {modal && <FullTextModal dream={modal} onClose={() => setModal(null)} />}

      {/* Similar panel — fixed overlay, ne premika vsebine */}
      {similar && (
        <>
          <div
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', zIndex: 40 }}
            onClick={() => setSimilar(null)}
          />
          <SimilarPanel
            dreamId={similar.dreamId}
            dreamTitle={similar.title}
            onClose={() => setSimilar(null)}
            t={t}
          />
        </>
      )}
    </div>
  )
}
