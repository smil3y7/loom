import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n/index.jsx'
import { api } from '../lib/api.js'

export default function Dashboard({ engineStatus }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    if (engineStatus === 'offline') { setLoading(false); return }
    if (engineStatus !== 'ok') return

    Promise.all([
      api.status().catch(() => null),
      api.threads().catch(() => ({ threads: [] })),
    ]).then(([s, t]) => {
      setStatus(s)
      setThreads(t?.threads?.slice(0, 3) || [])
      setLoading(false)
    })
  }, [engineStatus])

  function handleSearch(e) {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  if (engineStatus === 'offline') {
    return (
      <div className="page">
        <div className="page-header">
          <h2>{t('dashboard.title')}</h2>
        </div>
        <div className="offline-banner">
          <div>
            <h3>{t('dashboard.offline')}</h3>
            <p>{t('dashboard.offline.hint')}</p>
          </div>
          <button className="btn btn-secondary" onClick={() => window.location.reload()}>
            {t('dashboard.retry')}
          </button>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="page">
        <div className="loading-state">
          <div className="spinner" />
          {t('dashboard.connecting')}
        </div>
      </div>
    )
  }

  const embed = status?.embeddings || {}
  const cluster = status?.clustering || {}
  const sources = status?.sources || {}

  const stats = [
    { key: 'dreams', value: embed.embedded ?? '—', label: t('dashboard.stat.dreams') },
    { key: 'embedded', value: embed.embedded ?? '—', label: t('dashboard.stat.embedded') },
    { key: 'clusters', value: cluster.clusters ?? '—', label: t('dashboard.stat.clusters') },
    { key: 'threads', value: cluster.threads ?? '—', label: t('dashboard.stat.threads') },
  ]
  if (embed.queued > 0) {
    stats.push({ key: 'queued', value: embed.queued, label: t('dashboard.stat.queued') })
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>{t('dashboard.title')}</h2>
        <p>{t('dashboard.subtitle')}</p>
      </div>

      {/* Stats */}
      <div className="card-grid">
        {stats.map(s => (
          <div className="stat-card" key={s.key}>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Quick search */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="section-title">{t('dashboard.quickSearch')}</div>
        <form onSubmit={handleSearch} className="search-bar">
          <input
            className="input"
            placeholder={t('dashboard.searchPlaceholder')}
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
          <button className="btn btn-primary" type="submit">
            {t('nav.search')}
          </button>
        </form>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>

        {/* Sources */}
        <div className="card">
          <div className="section-title">{t('dashboard.sources')}</div>
          {Object.entries(sources).map(([name, info]) => (
            <div className="source-row" key={name}>
              <div className={`source-dot ${info.ok ? 'ok' : 'fail'}`} />
              <span className="source-name">{name}</span>
              <span className="source-count">
                {info.ok ? `${info.count ?? 0} ${t('common.dreams')}` : t('dashboard.source.fail')}
              </span>
            </div>
          ))}
          {Object.keys(sources).length === 0 && (
            <p style={{ fontSize: 13, color: 'var(--text-3)' }}>—</p>
          )}
        </div>

        {/* Recent threads */}
        <div className="card">
          <div className="section-title">{t('dashboard.recentThreads')}</div>
          {threads.length === 0 ? (
            <p style={{ fontSize: 13, color: 'var(--text-3)' }}>
              {t('dashboard.noThreads')}
            </p>
          ) : (
            threads.map(thread => (
              <div
                key={thread.thread_id}
                style={{ marginBottom: 12, cursor: 'pointer' }}
                onClick={() => navigate('/patterns')}
              >
                <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)', marginBottom: 2 }}>
                  {thread.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
                  {thread.dream_ids?.length} {t('common.dreams')} ·{' '}
                  {thread.first_seen} → {thread.last_seen}
                </div>
              </div>
            ))
          )}
          {threads.length > 0 && (
            <button
              className="btn btn-ghost"
              style={{ marginTop: 8, width: '100%', justifyContent: 'center' }}
              onClick={() => navigate('/patterns')}
            >
              {t('nav.patterns')} →
            </button>
          )}
        </div>

      </div>
    </div>
  )
}
