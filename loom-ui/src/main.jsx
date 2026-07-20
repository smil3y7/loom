import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

// Set initial theme before React loads to avoid flash
const saved = localStorage.getItem('loom_theme') || 'system'
const isDark = saved === 'dark' ||
  (saved === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>
)
