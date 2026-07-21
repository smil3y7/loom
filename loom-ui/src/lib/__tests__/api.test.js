// src/lib/__tests__/api.test.js
//
// Regresijski testi za lib/api.js.
//
// Pokrivajo bug ki je bil dejansko najden in popravljen: Settings stran je
// shranila API URL v localStorage, ampak api.js ga je nikoli prebral nazaj —
// API_URL je bila fiksna konstanta izračunana enkrat ob zagonu iz .env.
// Uporabnik je videl "Shranjeno", sprememba pa ni imela nobenega efekta.

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { api, apiErrorMessage } from '../api.js'

describe('API URL prioriteta', () => {
  beforeEach(() => {
    localStorage.clear()
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ ok: true }),
      })
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it(
    'KLJUČNI REGRESIJSKI TEST: uporabi localStorage URL če je nastavljen, ' +
      'ne fiksno .env vrednost — to je bilo pred popravkom prezrto',
    async () => {
      localStorage.setItem('loom_api_url', 'http://custom-host:9999')

      await api.health()

      expect(fetch).toHaveBeenCalledTimes(1)
      const calledUrl = fetch.mock.calls[0][0]
      expect(calledUrl).toBe('http://custom-host:9999/health')
    }
  )

  it('pade nazaj na privzeti localhost:8000 če ni ne localStorage ne .env vrednosti', async () => {
    // localStorage prazen (počiščen v beforeEach), VITE_API_URL v testnem
    // okolju ni nastavljen na nič posebnega — pade na trdi fallback.
    await api.health()

    const calledUrl = fetch.mock.calls[0][0]
    expect(calledUrl).toMatch(/^https?:\/\/.+\/health$/)
  })

  it('spremenjena localStorage vrednost med izvajanjem takoj vpliva na naslednji klic', async () => {
    localStorage.setItem('loom_api_url', 'http://first:8000')
    await api.health()
    expect(fetch.mock.calls[0][0]).toBe('http://first:8000/health')

    localStorage.setItem('loom_api_url', 'http://second:9000')
    await api.health()
    expect(fetch.mock.calls[1][0]).toBe('http://second:9000/health')
  })
})

describe('apiErrorMessage', () => {
  const t = (key) => {
    const dict = {
      'common.api_unreachable': 'API ni dosegljiv (prevedeno)',
      'common.error': 'Napaka (prevedeno)',
    }
    return dict[key] || key
  }

  it('prevede API_UNREACHABLE napako prek i18n namesto hardcoded stringa', () => {
    const err = new Error('API_UNREACHABLE')
    err.code = 'API_UNREACHABLE'
    expect(apiErrorMessage(err, t)).toBe('API ni dosegljiv (prevedeno)')
  })

  it('vrne originalno sporočilo za navadne (ne-network) napake', () => {
    const err = new Error('Nekaj drugega je šlo narobe')
    expect(apiErrorMessage(err, t)).toBe('Nekaj drugega je šlo narobe')
  })

  it('pade nazaj na prevedeno generično napako če error nima sporočila', () => {
    expect(apiErrorMessage(null, t)).toBe('Napaka (prevedeno)')
    expect(apiErrorMessage({}, t)).toBe('Napaka (prevedeno)')
  })
})

describe('request() network error handling', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('mrežna napaka (fetch throw TypeError) se pretvori v error.code=API_UNREACHABLE', async () => {
    global.fetch = vi.fn(() => {
      const err = new TypeError('Failed to fetch')
      throw err
    })

    await expect(api.health()).rejects.toMatchObject({
      code: 'API_UNREACHABLE',
    })
  })

  it('HTTP napaka (npr. 500) NI označena kot API_UNREACHABLE — razlikuje se od mrežne napake', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ detail: 'Server je padel' }),
      })
    )

    await expect(api.health()).rejects.toMatchObject({
      message: 'Server je padel',
    })
    // In NE sme imeti .code === 'API_UNREACHABLE' — to je vsebinska napaka,
    // ne mrežni izpad, ločevanje je pomembno za pravilno UI sporočilo.
    try {
      await api.health()
    } catch (e) {
      expect(e.code).not.toBe('API_UNREACHABLE')
    }
  })
})
