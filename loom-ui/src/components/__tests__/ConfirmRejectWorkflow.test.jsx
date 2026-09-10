// src/components/__tests__/ConfirmRejectWorkflow.test.jsx
//
// Regresijski test za deljeno potrdi/zavrni komponento (uporabljata jo
// Clusters.jsx in Patterns.jsx). Isti manual render pattern kot
// FullTextModal.test.jsx (brez @testing-library/react — ni med
// odvisnostmi projekta).

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createRoot } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { I18nProvider } from '../../i18n/index.jsx'
import ConfirmRejectWorkflow from '../ConfirmRejectWorkflow.jsx'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

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

const labels = {
  confirmButton: 'Potrdi grupo',
  rejectButton: 'Zavrni',
  renameLabel: 'Ime grupe',
  rejectedNotice: 'Grupa ne bo več predlagana.',
}

function render(props) {
  act(() => {
    root.render(
      <I18nProvider>
        <ConfirmRejectWorkflow labels={labels} {...props} />
      </I18nProvider>
    )
  })
}

function clickButtonWithText(text) {
  const btn = Array.from(container.querySelectorAll('button')).find(b => b.textContent.trim() === text)
  expect(btn).toBeTruthy()
  act(() => { btn.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
  return btn
}

describe('ConfirmRejectWorkflow', () => {
  it('že potrjen/zavrnjen kandidat ne prikaže nobenih gumbov', () => {
    render({ confirmed: true, rejected: false, onConfirm: vi.fn(), onReject: vi.fn() })
    expect(container.querySelectorAll('button').length).toBe(0)
  })

  it('KLJUČNI REGRESIJSKI TEST: potrditev pokliče onConfirm s poimenovanim (rename) imenom, ne z suggestedName privzeto', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    render({ confirmed: false, rejected: false, suggestedName: 'Predlagano ime', onConfirm, onReject: vi.fn() })

    clickButtonWithText('Potrdi grupo')
    // Input naj bo prednapolnjen s suggestedName
    const input = container.querySelector('input.input')
    expect(input.value).toBe('Predlagano ime')

    // Uporabnik spremeni ime pred potrditvijo
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(input, 'Moje lastno ime')
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })

    clickButtonWithText('Potrdi')
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(onConfirm).toHaveBeenCalledWith('Moje lastno ime')
  })

  it('zavrnitev pokliče onReject brez argumentov in prikaže rejectedNotice', async () => {
    const onReject = vi.fn().mockResolvedValue(undefined)
    render({ confirmed: false, rejected: false, onConfirm: vi.fn(), onReject })

    clickButtonWithText('Zavrni')
    expect(container.textContent).toContain('Grupa ne bo več predlagana.')

    // Znotraj reject dialoga je gumb z istim labelom kot rejectButton
    const dialogButtons = Array.from(container.querySelectorAll('.dialog button'))
    const confirmRejectBtn = dialogButtons.find(b => b.textContent.trim() === 'Zavrni')
    act(() => { confirmRejectBtn.dispatchEvent(new MouseEvent('click', { bubbles: true })) })
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(onReject).toHaveBeenCalledTimes(1)
  })

  it('napaka iz onConfirm se prikaže v dialogu in dialog ostane odprt (ne izgubi vnosa)', async () => {
    const onConfirm = vi.fn().mockRejectedValue(new Error('Strežnik ni dosegljiv'))
    render({ confirmed: false, rejected: false, suggestedName: 'X', onConfirm, onReject: vi.fn() })

    clickButtonWithText('Potrdi grupo')
    clickButtonWithText('Potrdi')
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(container.textContent).toContain('Strežnik ni dosegljiv')
    // Dialog mora ostati odprt — input še vedno v DOM-u
    expect(container.querySelector('input.input')).toBeTruthy()
  })
})
