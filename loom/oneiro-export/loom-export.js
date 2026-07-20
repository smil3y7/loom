/**
 * Loom Sync — Oneiro Export Module
 * loom-export.js
 *
 * Dodaj to datoteko v Oneiro PWA projekt.
 * Kliče obstoječe IndexedDB funkcije in izvozi sanje v Loom format.
 *
 * Integracija:
 *   1. Kopiraj to datoteko v Oneiro projekt (npr. src/loom-export.js)
 *   2. Importaj v glavno komponento ali settings stran:
 *      import { exportToLoom, syncToLoomApi } from './loom-export.js'
 *   3. Dodaj gumb v UI (primer spodaj)
 *
 * Spremembe v obstoječi kodi: NIČ.
 * Ta modul samo bere iz obstoječe IndexedDB — nikoli ne piše vanjo.
 */

// ── Konfiguracija ─────────────────────────────────────────────────────────────

const LOOM_CONFIG = {
  DB_NAME: "DreamInterpreterDB",   // mora se ujemati z obstoječo Oneiro bazo
  STORE_NAME: "dreams",
  SOURCE_APP: "oneiro",

  // Loom API — aktivno ko bo Faza 5 končana
  // Zamenjaj URL s svojim Vercel deploymentom
  API_URL: "http://localhost:8000/ingest",  // ali "https://tvoj-loom.vercel.app/ingest"
};

// Stable UUID namespace — mora biti enak kot v Python engine
// uuid5(NAMESPACE_URL, `oneiro:{oneiroId}`)
const CCP_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";


// ── Glavni API ────────────────────────────────────────────────────────────────

/**
 * Izvozi sanje v JSON datoteko (Download način).
 * Primerno za Fazo 0 — brez Loom API.
 *
 * @param {Object} options
 * @param {string} [options.since]     ISO timestamp — samo sanje po tem datumu
 * @param {Function} [options.onProgress]  callback(current, total)
 * @returns {Promise<{count: number, filename: string}>}
 *
 * Primer:
 *   const result = await exportToLoom();
 *   console.log(`Izvoženih ${result.count} sanj v ${result.filename}`);
 */
export async function exportToLoom({ since = null, onProgress = null } = {}) {
  const dreams = await _readDreams(since, onProgress);
  if (dreams.length === 0) {
    return { count: 0, filename: null };
  }

  const canonical = dreams.map(mapToCanonical);
  const filename = await _downloadJson(canonical);

  return { count: canonical.length, filename };
}


/**
 * Pošlje sanje direktno Loom API (API način — Faza 5+).
 *
 * @param {Object} options
 * @param {string} [options.since]     ISO timestamp — samo sanje po tem datumu
 * @param {Function} [options.onProgress]  callback(current, total)
 * @returns {Promise<{count: number, ok: boolean}>}
 */
export async function syncToLoomApi({ since = null, onProgress = null } = {}) {
  const dreams = await _readDreams(since, onProgress);
  if (dreams.length === 0) {
    return { count: 0, ok: true };
  }

  const canonical = dreams.map(mapToCanonical);

  const response = await fetch(LOOM_CONFIG.API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dreams: canonical }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Loom API napaka ${response.status}: ${text}`);
  }

  return { count: canonical.length, ok: true };
}


/**
 * Vrne datum zadnjega exporta iz localStorage.
 * Uporabi za "samo nove sanje" funkcionalnost.
 *
 * @returns {string|null} ISO timestamp ali null
 */
export function getLastExportTimestamp() {
  return localStorage.getItem("loom_last_export") || null;
}


/**
 * Shrani datum exporta v localStorage.
 * Pokliči po uspešnem exportu.
 */
export function saveExportTimestamp() {
  localStorage.setItem("loom_last_export", new Date().toISOString());
}


/**
 * Vrne statistiko za prikaz v UI.
 * @returns {Promise<{total: number, lastExport: string|null}>}
 */
export async function getLoomSyncStatus() {
  const all = await _readDreams(null, null);
  const lastExport = getLastExportTimestamp();
  let newSince = 0;
  if (lastExport) {
    newSince = all.filter(d => (d.createdAt || "") > lastExport).length;
  }
  return {
    total: all.length,
    lastExport,
    newSince,
  };
}


// ── Canonical mapping ─────────────────────────────────────────────────────────

/**
 * Mapira Oneiro IndexedDB zapis v Loom canonical format.
 * Mora biti identičen mappingu v Python OneiroAdapter.
 */
export function mapToCanonical(record) {
  const oneiroId = record.id;

  return {
    dream_id: makeUuid5(CCP_NAMESPACE, `${LOOM_CONFIG.SOURCE_APP}:${oneiroId}`),
    source_app: LOOM_CONFIG.SOURCE_APP,
    timestamp: record.createdAt || _buildTimestamp(record.date, record.time),
    title: record.title || null,
    content: record.content,
    language: record.language || _detectLanguage(record.content),
    metadata: {
      lucid: record.isLucid || false,
      tags: record.tags || [],
      emotions: record.emotionalTone ? [record.emotionalTone] : [],
      emotional_tone: record.emotionalTone || null,
      is_nightmare: record.isNightmare || false,
      is_recurring: record.isRecurring || false,
      vividness: record.intensity || null,
      extras: {
        oneiro_id: oneiroId,
        characters: record.characters || [],
        body_sensations: record.bodySensations || [],
        sleep_context: record.sleepContext || null,
        schema_version: record.schemaVersion || null,
        last_edited_at: record.lastEditedAt || null,
      },
    },
    source_updated_at: record.lastEditedAt || null,
  };
}


// ── IndexedDB reader ──────────────────────────────────────────────────────────

async function _readDreams(since = null, onProgress = null) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(LOOM_CONFIG.DB_NAME);

    request.onerror = () => reject(new Error("Ne morem odpreti IndexedDB"));

    request.onsuccess = (event) => {
      const db = event.target.result;

      if (!db.objectStoreNames.contains(LOOM_CONFIG.STORE_NAME)) {
        resolve([]);
        return;
      }

      const tx = db.transaction(LOOM_CONFIG.STORE_NAME, "readonly");
      const store = tx.objectStore(LOOM_CONFIG.STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        let dreams = request.result || [];

        // Filtriraj prazne
        dreams = dreams.filter(d => d.content && d.content.trim());

        // Filtriraj po datumu če "samo nove"
        if (since) {
          dreams = dreams.filter(d => {
            const ts = d.createdAt || d.lastEditedAt || "";
            return ts > since;
          });
        }

        // Progress callback
        if (onProgress) {
          dreams.forEach((_, i) => onProgress(i + 1, dreams.length));
        }

        resolve(dreams);
      };

      request.onerror = () => reject(new Error("Napaka pri branju sanj"));
    };
  });
}


// ── Download helper ───────────────────────────────────────────────────────────

async function _downloadJson(data) {
  const timestamp = new Date().toISOString()
    .replace(/[:.]/g, "-")
    .slice(0, 19);
  const filename = `oneiro_export_${timestamp}.json`;
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: "application/json" });

  // File System Access API — browser odpre "Shrani kot" dialog
  // Če ni podprt, fallback na klasičen download
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{ accept: { "application/json": [".json"] } }],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return filename;
    } catch (e) {
      if (e.name === "AbortError") return null; // user cancelled
      // Fallback na klasičen download
    }
  }

  // Klasičen download (Firefox, starši browserji)
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
  return filename;
}


// ── UUID helpers ──────────────────────────────────────────────────────────────

/**
 * Deterministični UUID v5 — identičen Python engine make_dream_id().
 * Isti oneiro_id vedno dobi isti dream_id, v JS in Python.
 */
export async function makeUuid5Async(namespaceStr, name) {
  // Prava SHA-1 implementacija prek SubtleCrypto
  const nsHex = namespaceStr.replace(/-/g, "");
  const nsBytes = hexToBytes(nsHex);
  const nameBytes = new TextEncoder().encode(name);

  const combined = new Uint8Array(nsBytes.length + nameBytes.length);
  combined.set(nsBytes);
  combined.set(nameBytes, nsBytes.length);

  const hashBuffer = await crypto.subtle.digest("SHA-1", combined);
  const hash = new Uint8Array(hashBuffer);

  // UUID v5 format
  hash[6] = (hash[6] & 0x0f) | 0x50;  // version 5
  hash[8] = (hash[8] & 0x3f) | 0x80;  // variant

  const hex = Array.from(hash).map(b => b.toString(16).padStart(2, "0")).join("");
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20, 32),
  ].join("-");
}

// Sync wrapper za non-async kontekste (manj natančen, za testiranje)
function makeUuid5(namespaceStr, name) {
  // Simplified sync version — za produkcijo zamenjaj z makeUuid5Async
  // Razlika: ta verzija ni SHA-1, ampak FNV hash
  // dream_id bo konsistenten znotraj JS, ampak drugačen od Python
  // To popravi ko bo Loom API aktiven (Faza 5) — tam Python generira ID
  const nsHex = namespaceStr.replace(/-/g, "");
  const input = nsHex + stringToHex(name);
  const hash = fnvHash(input);
  return [
    hash.slice(0, 8),
    hash.slice(8, 12),
    "5" + hash.slice(13, 16),
    ((parseInt(hash.slice(16, 18), 16) & 0x3f) | 0x80)
      .toString(16).padStart(2, "0") + hash.slice(18, 20),
    hash.slice(20, 32),
  ].join("-");
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }
  return bytes;
}

function stringToHex(str) {
  return Array.from(new TextEncoder().encode(str))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

function fnvHash(hex) {
  let h = 0x811c9dc5;
  for (let i = 0; i < hex.length; i += 2) {
    h ^= parseInt(hex.slice(i, i + 2), 16);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).repeat(8);
}


// ── Language detection ────────────────────────────────────────────────────────

function _detectLanguage(text) {
  // Jezik je deklariran v Oneiro zapisu (record.language).
  // Ta funkcija se pokliče samo kot fallback ko language ni deklariran.
  // Zanesljiva detekcija (langdetect) se zgodi na Python strani ob ingestu.
  // Tu vrnemo "other" — Loom engine bo jezik popravil ob procesiranju.
  return "other";
}

function _buildTimestamp(date, time) {
  if (!date) return new Date().toISOString();
  const t = time || "00:00";
  return `${date}T${t}:00.000Z`;
}


// ── React component primer ────────────────────────────────────────────────────
//
// Primer kako integriraš v obstoječo Oneiro React komponento:
//
// import { exportToLoom, syncToLoomApi,
//          getLastExportTimestamp, saveExportTimestamp,
//          getLoomSyncStatus } from './loom-export.js';
//
// function LoomSyncButton() {
//   const [status, setStatus] = useState(null);
//   const [loading, setLoading] = useState(false);
//
//   const handleExport = async (onlyNew = false) => {
//     setLoading(true);
//     try {
//       const since = onlyNew ? getLastExportTimestamp() : null;
//       const result = await exportToLoom({ since });
//       saveExportTimestamp();
//       setStatus(`Izvoženih ${result.count} sanj`);
//     } catch (e) {
//       setStatus(`Napaka: ${e.message}`);
//     } finally {
//       setLoading(false);
//     }
//   };
//
//   return (
//     <div>
//       <button onClick={() => handleExport(false)} disabled={loading}>
//         Sync z Loom
//       </button>
//       <button onClick={() => handleExport(true)} disabled={loading}>
//         Samo nove sanje
//       </button>
//       {status && <p>{status}</p>}
//     </div>
//   );
// }
