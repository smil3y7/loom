import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { I18nProvider, useI18n } from './i18n/index.jsx'
import { ThemeProvider } from './lib/theme.jsx'
import { api } from './lib/api.js'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import Patterns from './pages/Patterns.jsx'
import Clusters from './pages/Clusters.jsx'
import Settings from './pages/Settings.jsx'
import Help from './pages/Help.jsx'
import './index.css'

// ── Icons ─────────────────────────────────────────────────────────────────────

const Icons = {
  Dashboard: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1" y="1" width="6" height="6" rx="1.5"/>
      <rect x="9" y="1" width="6" height="6" rx="1.5"/>
      <rect x="1" y="9" width="6" height="6" rx="1.5"/>
      <rect x="9" y="9" width="6" height="6" rx="1.5"/>
    </svg>
  ),
  Search: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="6.5" cy="6.5" r="4.5"/>
      <path d="M10 10l4 4"/>
    </svg>
  ),
  Patterns: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 8c0-3.3 2.7-6 6-6s6 2.7 6 6-2.7 6-6 6"/>
      <path d="M8 5v3l2 2"/>
      <circle cx="8" cy="8" r="1" fill="currentColor" stroke="none"/>
    </svg>
  ),
  Clusters: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="4" r="2"/>
      <circle cx="3" cy="12" r="2"/>
      <circle cx="13" cy="12" r="2"/>
      <path d="M8 6l-3.5 4M8 6l3.5 4M3.5 10h9"/>
    </svg>
  ),
  Settings: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="2.5"/>
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/>
    </svg>
  ),
  Help: () => (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="6.5"/>
      <path d="M6 6c0-1.1.9-2 2-2s2 .9 2 2c0 1.5-2 2-2 2"/>
      <circle cx="8" cy="12" r="0.7" fill="currentColor" stroke="none"/>
    </svg>
  ),
}

// ── Engine status hook ────────────────────────────────────────────────────────

function useEngineStatus() {
  const [status, setStatus] = useState('loading') // 'loading' | 'ok' | 'offline'

  useEffect(() => {
    let mounted = true
    const check = async () => {
      try {
        await api.health()
        if (mounted) setStatus('ok')
      } catch {
        if (mounted) setStatus('offline')
      }
    }
    check()
    const interval = setInterval(check, 15000)
    return () => { mounted = false; clearInterval(interval) }
  }, [])

  return status
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ engineStatus }) {
  const { t } = useI18n()

  const navItems = [
    { to: '/', label: t('nav.dashboard'), Icon: Icons.Dashboard, end: true },
    { to: '/search', label: t('nav.search'), Icon: Icons.Search },
    { to: '/patterns', label: t('nav.patterns'), Icon: Icons.Patterns },
    { to: '/clusters', label: t('nav.clusters'), Icon: Icons.Clusters },
    { to: '/settings', label: t('nav.settings'), Icon: Icons.Settings },
    { to: '/help', label: t('nav.help'), Icon: Icons.Help },
  ]

  const statusLabel = {
    loading: t('common.loading'),
    ok: t('common.engine_online'),
    offline: t('common.engine_offline'),
  }[engineStatus]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>Loom</h1>
        <span>{t('dashboard.subtitle')}</span>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className={`engine-status ${engineStatus}`} />
        <span className="engine-status-text">{statusLabel}</span>
      </div>
    </aside>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────

function AppInner() {
  const engineStatus = useEngineStatus()

  return (
    <div className="app">
      <Sidebar engineStatus={engineStatus} />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard engineStatus={engineStatus} />} />
          <Route path="/search" element={<Search />} />
          <Route path="/patterns" element={<Patterns />} />
          <Route path="/clusters" element={<Clusters />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/help" element={<Help />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <I18nProvider>
          <AppInner />
        </I18nProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
