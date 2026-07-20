// Loom UI — API Client
// Vse API klice gredo skozi ta modul.
// URL prioriteta: uporabnikova nastavitev (Settings) > .env > localhost.

function getApiUrl() {
  return (
    localStorage.getItem('loom_api_url') ||
    import.meta.env.VITE_API_URL ||
    'http://localhost:8000'
  )
}

async function request(path, options = {}) {
  const url = `${getApiUrl()}${path}`
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
  } catch (e) {
    if (e.name === 'TypeError') {
      // Mrežna napaka (fetch se sploh ni izvedel) — ne hardcodiramo sporočila
      // tukaj, ker ta modul ni React komponenta in nima dostopa do i18n.
      // Klicna koda naj preveri `e.code === 'API_UNREACHABLE'` in prevede sama,
      // npr.: catch (e) { setError(e.code === 'API_UNREACHABLE' ? t('common.api_unreachable') : e.message) }
      const netErr = new Error('API_UNREACHABLE')
      netErr.code = 'API_UNREACHABLE'
      throw netErr
    }
    throw e
  }
}

// Prevede API napako v uporabniku razumljivo sporočilo prek i18n `t()`.
// Uporaba v komponenti: catch (e) { setError(apiErrorMessage(e, t)) }
export function apiErrorMessage(error, t) {
  if (error?.code === 'API_UNREACHABLE') {
    return t('common.api_unreachable')
  }
  return error?.message || t('common.error')
}

export const api = {
  // Health
  health: () => request('/health'),

  // Status
  status: () => request('/api/status'),

  // Search
  search: (query, { limit = 10, language, sourceApp, minSimilarity } = {}) => {
    const params = new URLSearchParams({ q: query, limit })
    if (language) params.set('language', language)
    if (sourceApp) params.set('source_app', sourceApp)
    if (minSimilarity) params.set('min_similarity', minSimilarity)
    return request(`/api/search?${params}`)
  },

  // Similar dreams
  similar: (dreamId, limit = 8) =>
    request(`/api/dreams/${dreamId}/similar?limit=${limit}`),

  // Clusters
  clusters: ({ minSize = 2, confirmedOnly = false, candidateType } = {}) => {
    const params = new URLSearchParams({ min_size: minSize, confirmed_only: confirmedOnly })
    if (candidateType) params.set('candidate_type', candidateType)
    return request(`/api/clusters?${params}`)
  },

  confirmCluster: (clusterId, { confirmedType, confirmedName }) =>
    request(`/api/clusters/${clusterId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ confirmed_type: confirmedType, confirmed_name: confirmedName }),
    }),

  rejectCluster: (clusterId) =>
    request(`/api/clusters/${clusterId}/reject`, { method: 'POST' }),

  // Threads
  threads: ({ confirmedOnly = false } = {}) =>
    request(`/api/threads?confirmed_only=${confirmedOnly}`),

  confirmThread: (threadId, name) =>
    request(`/api/threads/${threadId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),

  rejectThread: (threadId) =>
    request(`/api/threads/${threadId}/reject`, { method: 'POST' }),

  // Embed
  embed: () => request('/api/embed', { method: 'POST' }),

  // Ingest
  ingest: (dreams) =>
    request('/api/ingest', {
      method: 'POST',
      body: JSON.stringify({ dreams }),
    }),
}
