import { useState } from 'react'
import { useI18n } from '../i18n/index.jsx'

/**
 * Deljena potrdi/zavrni/preimenuj interakcija za CCP kandidate.
 *
 * Uporabljata jo Clusters.jsx in Patterns.jsx (in karkoli podobnega v
 * prihodnje, npr. bodoči AI agent predlogi) — backend vzorec je pri obeh
 * enak: potrditev sprejme (tip +) ime, zavrnitev je samo POST brez telesa.
 * Komponenta ne pozna API oblike kandidata (cluster vs. thread) — kliče
 * `onConfirm(name)` / `onReject()`, ki ju posreduje klicna stran.
 *
 * Prej je bila ta logika (dialog state, rename input, confirm/reject
 * gumbi) podvojena samo v Patterns.jsx; Clusters.jsx je iste backend
 * endpointe (api.confirmCluster/rejectCluster) imel na voljo v api.js,
 * ampak jih nikoli ni uporabil — od tod ta komponenta, namesto da bi
 * podvojili isto kodo drugič.
 */
export default function ConfirmRejectWorkflow({
  confirmed,
  rejected,
  suggestedName = '',
  summary = null,       // JSX — kontekst v confirm dialogu (št. sanj, datumski razpon, vzorci ...)
  labels,               // { confirmButton, rejectButton, renameLabel, rejectedNotice, confirmHelp? }
  onConfirm,            // async (name) => void
  onReject,             // async () => void
}) {
  const { t } = useI18n()
  const [dialog, setDialog] = useState(null) // 'confirm' | 'reject' | null
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (confirmed || rejected) return null

  function openConfirm() {
    setName(suggestedName || '')
    setError(null)
    setDialog('confirm')
  }

  function openReject() {
    setError(null)
    setDialog('reject')
  }

  function close() {
    if (busy) return // ne zapiraj sredi klica — prepreči izgubljen rezultat
    setDialog(null)
  }

  async function handleConfirm() {
    setBusy(true)
    setError(null)
    try {
      await onConfirm(name)
      setDialog(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleReject() {
    setBusy(true)
    setError(null)
    try {
      await onReject()
      setDialog(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="thread-actions">
        <button className="btn btn-primary" style={{ fontSize: 13 }} onClick={openConfirm}>
          {labels.confirmButton}
        </button>
        <button className="btn btn-ghost" style={{ fontSize: 13 }} onClick={openReject}>
          {labels.rejectButton}
        </button>
      </div>

      {dialog === 'confirm' && (
        <div className="dialog-overlay" onClick={close}>
          <div className="dialog" onClick={e => e.stopPropagation()}>
            <h3>{labels.confirmButton}</h3>
            {summary}
            <div style={{ marginTop: 16, marginBottom: 8 }}>
              <label style={{ fontSize: 13, color: 'var(--text-2)', display: 'block', marginBottom: 8 }}>
                {labels.renameLabel}
              </label>
              <input
                className="input"
                value={name}
                onChange={e => setName(e.target.value)}
                autoFocus
                disabled={busy}
              />
            </div>
            {labels.confirmHelp && (
              <p style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 12 }}>
                {labels.confirmHelp}
              </p>
            )}
            {error && (
              <p style={{ color: 'var(--err)', fontSize: 13, marginBottom: 12 }}>{error}</p>
            )}
            <div className="dialog-actions">
              <button className="btn btn-secondary" disabled={busy} onClick={close}>
                {t('common.cancel')}
              </button>
              <button className="btn btn-primary" disabled={busy} onClick={handleConfirm}>
                {t('common.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {dialog === 'reject' && (
        <div className="dialog-overlay" onClick={close}>
          <div className="dialog" onClick={e => e.stopPropagation()}>
            <h3>{labels.rejectButton}</h3>
            <p style={{ marginBottom: 20 }}>{labels.rejectedNotice}</p>
            {error && (
              <p style={{ color: 'var(--err)', fontSize: 13, marginBottom: 12 }}>{error}</p>
            )}
            <div className="dialog-actions">
              <button className="btn btn-secondary" disabled={busy} onClick={close}>
                {t('common.cancel')}
              </button>
              <button className="btn btn-danger" disabled={busy} onClick={handleReject}>
                {labels.rejectButton}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
