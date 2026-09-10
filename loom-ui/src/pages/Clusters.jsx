import { useState, useEffect } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { api, apiErrorMessage } from '../lib/api.js'
import FullTextModal from '../components/FullTextModal.jsx'
import ConfirmRejectWorkflow from '../components/ConfirmRejectWorkflow.jsx'

// Cluster label je avtomatsko generiran kot `f"Cluster {n}"` (lib/clustering.py)
// — vedno dobesedno ta angleška oblika, ne glede na UI jezik.
const GENERIC_LABEL_RE = /^Cluster\s+\d+$/i

function candidateTypeLabel(t, type) {
  return t(`clusters.candidateType.${type || 'unknown'}`)
}

export default function Clusters() {
  const { t } = useI18n()
  const [clusters, setClusters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(null)
  const [modal, setModal] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.clusters({ minSize: 2 })
      setClusters(res.clusters || [])
    } catch (e) {
      setError(apiErrorMessage(e, t))
    } finally {
      setLoading(false)
    }
  }

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
          {clusters.map(cluster => {
            const sampleTitles = (cluster.sample_dreams || []).slice(0, 3).map(s => s.title).filter(Boolean)
            const isGenericLabel = GENERIC_LABEL_RE.test(cluster.label)
            const suggestedName = cluster.confirmed_name
              || (isGenericLabel && sampleTitles.length > 0 ? sampleTitles.join(' · ') : cluster.label)

            return (
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
                          {t('clusters.type')}: {candidateTypeLabel(t, cluster.candidate_type)}
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

                {/* Potrdi/zavrni — deljena komponenta, isti backend pattern kot Patterns */}
                <ConfirmRejectWorkflow
                  confirmed={cluster.confirmed}
                  rejected={cluster.rejected}
                  suggestedName={suggestedName}
                  labels={{
                    confirmButton: t('clusters.confirm'),
                    rejectButton: t('clusters.reject'),
                    renameLabel: t('clusters.rename'),
                    rejectedNotice: t('clusters.rejectedNotice'),
                  }}
                  summary={
                    <>
                      <p style={{ marginBottom: 8, fontSize: 14, color: 'var(--text-2)' }}>
                        {cluster.size} {t('common.dreams')} ·{' '}
                        {cluster.first_seen} → {cluster.last_seen}
                      </p>
                      {(cluster.sample_dreams || []).slice(0, 3).map((s, i) => (
                        <div key={i} style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 3 }}>
                          · {s.date} — {s.title || t('common.no_title')}
                        </div>
                      ))}
                    </>
                  }
                  onConfirm={async (name) => {
                    await api.confirmCluster(cluster.cluster_id, {
                      confirmedType: cluster.candidate_type || 'thread',
                      confirmedName: name || cluster.label,
                    })
                    await load()
                  }}
                  onReject={async () => {
                    await api.rejectCluster(cluster.cluster_id)
                    await load()
                  }}
                />
              </div>
            )
          })}
        </div>
      )}

      {modal && <FullTextModal dream={modal} onClose={() => setModal(null)} />}
    </div>
  )
}
