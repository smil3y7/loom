import { useState, useEffect } from 'react'
import { useI18n } from '../i18n/index.jsx'
import { api, apiErrorMessage } from '../lib/api.js'
import FullTextModal from '../components/FullTextModal.jsx'
import ConfirmRejectWorkflow from '../components/ConfirmRejectWorkflow.jsx'

// ── Časovna premica ───────────────────────────────────────────────────────────

function Timeline({ data }) {
  if (!data || data.length < 2) return null
  const max = Math.max(...data.map(d => d.count), 1)
  const total = data.length
  const barW = Math.max(2, Math.floor(300 / total) - 1)

  return (
    <div style={{ marginTop: 10 }}>
      <svg width="100%" height={36} style={{ display: 'block' }}>
        {data.map((d, i) => {
          const barH = d.count === 0 ? 2 : Math.max(4, (d.count / max) * 32)
          const x = `${(i / (total - 1)) * 98}%`
          const isRecent = d.year >= new Date().getFullYear() - 2
          return (
            <g key={d.year}>
              <rect
                x={x} y={36 - barH} width={Math.max(barW, 3)} height={barH}
                rx={1}
                fill={d.count === 0 ? 'var(--border)' : isRecent ? 'var(--accent)' : 'var(--accent-2)'}
                opacity={d.count === 0 ? 0.3 : 0.75}
              >
                <title>{d.year}: {d.count}</title>
              </rect>
            </g>
          )
        })}
      </svg>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-3)' }}>
        <span>{data[0]?.year}</span>
        <span>{data[data.length - 1]?.year}</span>
      </div>
    </div>
  )
}

// ── Thread kartica ────────────────────────────────────────────────────────────

const GENERIC_NAME_RE = /^(Vzorec|Pattern)\s+\d+/i

function ThreadCard({ thread, t, onChanged }) {
  const [expanded, setExpanded] = useState(false)
  const [modal, setModal] = useState(null)

  const score = thread.recurrence_score
    ? `${(thread.recurrence_score * 100).toFixed(0)}%`
    : '—'

  const emotions = Object.entries(thread.emotional_signature || {})
    .sort((a, b) => b[1] - a[1]).slice(0, 3)

  const samples = thread.sample_dreams || []

  // Ime kartice:
  // - Potrjeni: thread.name (kar je user vpisal)
  // - Nepotrjeni z generičnim imenom: naslovi prvih 3 vzorčnih sanj
  // - Nepotrjeni z lastnim imenom: thread.name
  const isGeneric = GENERIC_NAME_RE.test(thread.name)
  const sampleTitles = samples.slice(0, 3).map(s => s.title).filter(Boolean)

  let displayName, subLabel
  if (thread.confirmed) {
    displayName = thread.name
    subLabel = null
  } else if (isGeneric && sampleTitles.length > 0) {
    displayName = sampleTitles.join(' · ')
    subLabel = thread.name  // "Vzorec 4" kot opomba
  } else {
    displayName = thread.name
    subLabel = null
  }

  const previewSamples = samples.slice(0, 5)
  const moreSamples = samples.slice(5)

  // Predlagano ime za confirm dialog — enaka logika kot za displayName,
  // samo brez pogoja na thread.confirmed (dialog se odpre samo za nepotrjene).
  const suggestedName = isGeneric && sampleTitles.slice(0, 2).length > 0
    ? sampleTitles.slice(0, 2).join(' / ')
    : thread.name

  return (
    <div className={`thread-card ${thread.confirmed ? 'confirmed' : ''}`}>
      {/* Header */}
      <div className="thread-header">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="thread-name" style={{ wordBreak: 'break-word' }}>
            {displayName}
            {thread.confirmed && (
              <span className="badge badge-ok" style={{ marginLeft: 8, fontSize: 11, verticalAlign: 'middle' }}>
                {t('patterns.confirmed')}
              </span>
            )}
          </div>
          {subLabel && (
            <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 3 }}>
              {subLabel}
            </div>
          )}
        </div>
        <div className="thread-score">{score}</div>
      </div>

      {/* Meta */}
      <div className="thread-meta">
        <span className="badge badge-neutral">
          {thread.dream_ids?.length} {t('patterns.dreams')}
        </span>
        <span className="badge badge-neutral">
          {thread.first_seen} → {thread.last_seen}
        </span>
        {emotions.map(([e, v]) => (
          <span key={e} className="badge badge-accent" style={{ fontSize: 11 }}>
            {e} {(v * 100).toFixed(0)}%
          </span>
        ))}
      </div>

      {/* Časovna premica */}
      {thread.timeline && thread.timeline.length > 1 && (
        <Timeline data={thread.timeline} />
      )}

      {/* Vzorčne sanje — klikabilne za full text */}
      {previewSamples.length > 0 && (
        <div className="thread-sample" style={{ marginTop: 10 }}>
          <div className="thread-sample-title">{t('patterns.sample')}</div>
          {previewSamples.map((s, i) => (
            <div
              key={i}
              className="thread-sample-item"
              style={{ cursor: 'pointer' }}
              onClick={() => setModal(s)}
            >
              <span className="thread-sample-date">{s.date}</span>
              <span style={{ color: 'var(--accent)', fontSize: 13 }}>
                {s.title || t('common.no_title')}
              </span>
            </div>
          ))}

          {moreSamples.length > 0 && (
            <>
              {expanded && moreSamples.map((s, i) => (
                <div
                  key={i}
                  className="thread-sample-item"
                  style={{ cursor: 'pointer' }}
                  onClick={() => setModal(s)}
                >
                  <span className="thread-sample-date">{s.date}</span>
                  <span style={{ color: 'var(--accent)', fontSize: 13 }}>
                    {s.title || t('common.no_title')}
                  </span>
                </div>
              ))}
              <button
                style={{ fontSize: 12, color: 'var(--text-3)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0' }}
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? t('common.show_less') : t('common.show_more', { n: moreSamples.length })}
              </button>
            </>
          )}
        </div>
      )}

      {/* Potrdi/zavrni — deljena komponenta, isti backend pattern kot Clusters */}
      <ConfirmRejectWorkflow
        confirmed={thread.confirmed}
        rejected={thread.rejected}
        suggestedName={suggestedName}
        labels={{
          confirmButton: t('patterns.confirm'),
          rejectButton: t('patterns.reject'),
          renameLabel: t('patterns.rename'),
          rejectedNotice: `${t('patterns.rejected')} — ${thread.name}`,
        }}
        summary={
          <>
            <p style={{ marginBottom: 8, fontSize: 14, color: 'var(--text-2)' }}>
              {thread.dream_ids?.length} {t('patterns.dreams')} ·{' '}
              {thread.first_seen} → {thread.last_seen}
            </p>
            {samples.slice(0, 3).map((s, i) => (
              <div key={i} style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 3 }}>
                · {s.date} — {s.title || t('common.no_title')}
              </div>
            ))}
          </>
        }
        onConfirm={async (name) => {
          await api.confirmThread(thread.thread_id, name || thread.name)
          await onChanged()
        }}
        onReject={async () => {
          await api.rejectThread(thread.thread_id)
          await onChanged()
        }}
      />

      {/* Full text modal */}
      {modal && <FullTextModal dream={modal} onClose={() => setModal(null)} />}
    </div>
  )
}

// ── Glavna stran ──────────────────────────────────────────────────────────────

export default function Patterns() {
  const { t } = useI18n()
  const [threads, setThreads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [sortBy, setSortBy] = useState('score')

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.threads()
      setThreads(res.threads || [])
    } catch (e) {
      setError(apiErrorMessage(e, t))
    } finally {
      setLoading(false)
    }
  }

  const filtered = threads.filter(th => {
    if (filter === 'confirmed') return th.confirmed
    if (filter === 'pending') return !th.confirmed && !th.rejected
    return !th.rejected
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'score') return b.recurrence_score - a.recurrence_score
    if (sortBy === 'size') return (b.dream_ids?.length || 0) - (a.dream_ids?.length || 0)
    if (sortBy === 'date') return (b.last_seen || '').localeCompare(a.last_seen || '')
    return 0
  })

  const counts = {
    all: threads.filter(t => !t.rejected).length,
    pending: threads.filter(t => !t.confirmed && !t.rejected).length,
    confirmed: threads.filter(t => t.confirmed).length,
  }

  if (loading) return (
    <div className="page">
      <div className="loading-state"><div className="spinner" />{t('common.loading')}</div>
    </div>
  )

  return (
    <div className="page">
      <div className="page-header">
        <h2>{t('patterns.title')}</h2>
        <p>{t('patterns.subtitle')}</p>
      </div>

      {error && (
        <div className="card" style={{ borderColor: 'var(--err)', marginBottom: 20 }}>
          <p style={{ color: 'var(--err)', fontSize: 14 }}>{error}</p>
        </div>
      )}

      {threads.length > 0 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
          {['all', 'pending', 'confirmed'].map(f => (
            <button
              key={f}
              className={`btn ${filter === f ? 'btn-primary' : 'btn-ghost'}`}
              style={{ padding: '7px 14px', fontSize: 13 }}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? t('search.filter.all') :
               f === 'confirmed' ? t('patterns.confirmed') :
               t('patterns.unconfirmed')}
              {' '}<span style={{ opacity: 0.6 }}>({counts[f]})</span>
            </button>
          ))}
          <select
            className="input"
            style={{ width: 'auto', marginLeft: 'auto', fontSize: 13 }}
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="score">{t('patterns.sort.score')}</option>
            <option value="size">{t('patterns.sort.size')}</option>
            <option value="date">{t('patterns.sort.date')}</option>
          </select>
        </div>
      )}

      {sorted.length === 0 ? (
        <div className="empty-state"><h3>{t('patterns.noPatterns')}</h3></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {sorted.map(thread => (
            <ThreadCard
              key={thread.thread_id}
              thread={thread}
              t={t}
              onChanged={load}
            />
          ))}
        </div>
      )}
    </div>
  )
}
