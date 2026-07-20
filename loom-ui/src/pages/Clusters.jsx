import { useState, useEffect } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { api, apiErrorMessage } from '../lib/api.js'
import FullTextModal from '../components/FullTextModal.jsx'

export default function Clusters() {
  const { t } = useI18n()
  const [clusters, setClusters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)
  const [modal, setModal] = useState(null)

  useEffect(() => {
    api.clusters({ minSize: 2 })
      .then(res => { setClusters(res.clusters || []); setLoading(false) })
      .catch(e => { setError(apiErrorMessage(e, t)); setLoading(false) })
  }, [])

  if (loading) return (
    <div className="page">
      <div className="loading-state"><div className="spinner" />{t('common.loading')}</div>
    </div>
  )

  return (
    <div className="page">
      <div className="page-header">
        <h2>{t('clusters.title')}</h2>
        <p>{t('clusters.subtitle')}</p>
      </div>

      {/* Razlaga */}
      <div className="card" style={{ marginBottom: 24, background: 'var(--accent-soft)', borderColor: 'var(--accent)' }}>
        <p style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.6 }}>
          {t('clusters.about')}
        </p>
      </div>

      {error && <p style={{ color: 'var(--err)', marginBottom: 20 }}>{error}</p>}

      {clusters.length === 0 ? (
        <div className="empty-state">
          <h3>{t('clusters.noData')}</h3>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {clusters.map(cluster => (
            <div key={cluster.cluster_id} className="card">
              {/* Header — vedno viden */}
              <div
                style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
                onClick={() => setExpanded(expanded === cluster.cluster_id ? null : cluster.cluster_id)}
              >
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: 15, fontFamily: 'DM Serif Display, serif', color: 'var(--text)' }}>
                    {cluster.confirmed_name || cluster.label}
                  </span>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                    {cluster.confirmed && (
                      <span className="badge badge-ok">{t('patterns.confirmed')}</span>
                    )}
                    <span className="badge badge-accent">{cluster.size} {t('common.dreams')}</span>
                    <span className="badge badge-neutral">
                      {t('clusters.coherence')} {(cluster.coherence * 100).toFixed(0)}%
                    </span>
                    <span className="badge badge-neutral">
                      {cluster.first_seen} → {cluster.last_seen}
                    </span>
                    {cluster.candidate_type && (
                      <span className="badge badge-neutral">
                        {t('clusters.type')}: {cluster.candidate_type}
                      </span>
                    )}
                  </div>
                </div>
                <span style={{ fontSize: 12, color: 'var(--text-3)', marginLeft: 12, flexShrink: 0 }}>
                  {expanded === cluster.cluster_id ? t('clusters.collapse') : t('clusters.expand')}
                </span>
              </div>

              {/* Vzorčne sanje — expandable */}
              {expanded === cluster.cluster_id && (
                <div className="thread-sample" style={{ marginTop: 12 }}>
                  <div className="thread-sample-title">{t('clusters.sample')}</div>
                  {(cluster.sample_dreams || []).map((s, i) => (
                    <div key={i} className="thread-sample-item">
                      <span className="thread-sample-date">{s.date}</span>
                      <div style={{ flex: 1 }}>
                        <span>{s.title || t('common.no_title')}</span>
                        <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                          {s.excerpt}
                        </div>
                        <button
                          style={{
                            fontSize: 12, color: 'var(--accent)',
                            background: 'none', border: 'none',
                            cursor: 'pointer', padding: '2px 0',
                          }}
                          onClick={e => { e.stopPropagation(); setModal(s) }}
                        >
                          {t('search.full_text')} →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {modal && <FullTextModal dream={modal} onClose={() => setModal(null)} />}
    </div>
  )
}
