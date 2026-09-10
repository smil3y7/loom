// src/components/__tests__/FullTextModal.test.jsx
//
// Regresijski test za multi-cycle grupiranje v FullTextModal — brez
// @testing-library/react (ni med odvisnostmi projekta), zato render
// direktno prek react-dom/client + act, kot je edini pattern na voljo
// znotraj obstoječih devDependencies (vitest + jsdom).

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createRoot } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { I18nProvider } from '../../i18n/index.jsx'
import { api } from '../../lib/api.js'
import FullTextModal from '../FullTextModal.jsx'

// Brez tega React 18 concurrent rendering ne flusha state updateov
// sinhrono znotraj act() v tem ročnem render-setupu (ni RTL, ki to
// nastavi sama) — posledica bi bila, da klik na cycle-switcher gumb ne
// bi bil viden v testu dokler ne bi šli skozi dodaten event loop tick.
globalThis.IS_REACT_ACT_ENVIRONMENT = true

vi.mock('../../lib/api.js', () => ({
  api: { cycles: vi.fn() },
}))

let container, root

beforeEach(() => {
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => { root.unmount() })
  container.remove()
  vi.restoreAllMocks()
})

function renderModal(dream) {
  act(() => {
    root.render(
      <I18nProvider>
        <FullTextModal dream={dream} onClose={() => {}} />
      </I18nProvider>
    )
  })
}

describe('FullTextModal — multi-cycle grouping', () => {
  it('single-cycle dream: ne prikaže cycle-switcherja, obnašanje nespremenjeno', async () => {
    api.cycles.mockResolvedValue({
      dream_id: 'solo-1',
      parent_dream_id: null,
      total_cycles: 1,
      cycles: [{ dream_id: 'solo-1', cycle_index: null, title: 'Sama sanja', full_content: 'Vsebina.' }],
    })

    renderModal({ dream_id: 'solo-1', title: 'Sama sanja', full_content: 'Vsebina.', timestamp: '2026-01-01T00:00:00Z' })
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(container.textContent).toContain('Sama sanja')
    expect(container.querySelectorAll('button').length).toBe(1) // samo Zapri gumb
  })

  it('KLJUČNI REGRESIJSKI TEST: multi-cycle noč prikaže switcher in klik zamenja prikazano vsebino', async () => {
    api.cycles.mockResolvedValue({
      dream_id: 'cycle-1',
      parent_dream_id: 'night-x',
      total_cycles: 2,
      cycles: [
        { dream_id: 'cycle-1', cycle_index: 1, title: 'Prvi cikel', full_content: 'Vsebina prvega cikla.' },
        { dream_id: 'cycle-2', cycle_index: 2, title: 'Drugi cikel', full_content: 'Vsebina drugega cikla.' },
      ],
    })

    renderModal({ dream_id: 'cycle-1', title: 'Prvi cikel', full_content: 'Vsebina prvega cikla.', timestamp: '2026-01-01T00:00:00Z' })
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(container.textContent).toContain('Vsebina prvega cikla.')

    const buttons = Array.from(container.querySelectorAll('button'))
    const secondCycleBtn = buttons.find(b => /^Cikel 2\b/.test(b.textContent.trim()))
    expect(secondCycleBtn).toBeTruthy()

    act(() => { secondCycleBtn.dispatchEvent(new MouseEvent('click', { bubbles: true })) })

    expect(container.textContent).toContain('Vsebina drugega cikla.')
    expect(container.textContent).not.toContain('Vsebina prvega cikla.')
  })

  it('mrežna napaka pri nalaganju ciklov tiho pade nazaj na single-cycle prikaz', async () => {
    api.cycles.mockRejectedValue(new Error('API_UNREACHABLE'))

    renderModal({ dream_id: 'x', title: 'Naslov', full_content: 'Vsebina.', timestamp: '2026-01-01T00:00:00Z' })
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(container.textContent).toContain('Vsebina.')
    expect(container.querySelectorAll('button').length).toBe(1)
  })
})
