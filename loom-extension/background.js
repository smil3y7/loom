// Loom Sync — background.js
// Service worker: bere IndexedDB iz Oneiro taba in vrne podatke popupu.
// Download se izvede v popup.js kjer je URL.createObjectURL na voljo.

const ONEIRO_URL = "https://oneiro-delta.vercel.app";
const SOURCE_APP = "oneiro";
const CCP_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";

const DELIVERY_MODE = "download"; // "download" | "api"
const LOOM_API_URL = "http://localhost:8000/api/ingest";

// ── Message handler ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "sync") {
    readDreamsFromTab(message.sinceTimestamp)
      .then(dreams => {
        const canonical = dreams.map(mapToCanonical);
        if (DELIVERY_MODE === "api") {
          return postToApi(canonical)
            .then(() => sendResponse({ ok: true, count: canonical.length, mode: "api" }));
        }
        // Download mode — vrni podatke popupu, ta naredi download
        sendResponse({ ok: true, count: canonical.length, mode: "download", dreams: canonical });
      })
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true;
  }
});

// ── Beri IndexedDB iz Oneiro taba ─────────────────────────────────────────────

async function readDreamsFromTab(sinceTimestamp) {
  const tabs = await chrome.tabs.query({ url: `${ONEIRO_URL}/*` });
  if (!tabs.length) {
    throw new Error("Oneiro tab ni najden. Odpri Oneiro in poskusi znova.");
  }

  const results = await chrome.scripting.executeScript({
    target: { tabId: tabs[0].id },
    func: readIndexedDB,
    args: [sinceTimestamp],
  });

  const dreams = results?.[0]?.result;
  if (!Array.isArray(dreams)) {
    throw new Error("Napaka pri branju IndexedDB.");
  }
  return dreams;
}

// ── IndexedDB reader (injected into Oneiro tab) ───────────────────────────────

function readIndexedDB(sinceTimestamp) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("DreamInterpreterDB");
    request.onerror = () => reject(new Error("Ne morem odpreti IndexedDB"));
    request.onsuccess = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("dreams")) {
        resolve([]);
        return;
      }
      const tx = db.transaction("dreams", "readonly");
      const store = tx.objectStore("dreams");
      const req = store.getAll();
      req.onsuccess = () => {
        let dreams = req.result || [];
        dreams = dreams.filter(d => d.content && d.content.trim());
        if (sinceTimestamp) {
          dreams = dreams.filter(d => (d.createdAt || d.lastEditedAt || "") > sinceTimestamp);
        }
        resolve(dreams);
      };
      req.onerror = () => reject(new Error("Napaka pri branju sanj"));
    };
  });
}

// ── Canonical mapping ─────────────────────────────────────────────────────────

function mapToCanonical(record) {
  return {
    dream_id: makeUuid5(CCP_NAMESPACE, `${SOURCE_APP}:${record.id}`),
    source_app: SOURCE_APP,
    timestamp: record.createdAt || buildTimestamp(record.date, record.time),
    title: record.title || null,
    content: record.content,
    language: record.language || "other",
    metadata: {
      lucid: record.isLucid || false,
      tags: record.tags || [],
      emotions: record.emotionalTone ? [record.emotionalTone] : [],
      emotional_tone: record.emotionalTone || null,
      is_nightmare: record.isNightmare || false,
      is_recurring: record.isRecurring || false,
      vividness: record.intensity || null,
      extras: {
        oneiro_id: record.id,
        characters: record.characters || [],
        body_sensations: record.bodySensations || [],
        sleep_context: record.sleepContext || null,
        last_edited_at: record.lastEditedAt || null,
      },
    },
    source_updated_at: record.lastEditedAt || null,
  };
}

// ── API delivery ──────────────────────────────────────────────────────────────

async function postToApi(dreams) {
  const response = await fetch(LOOM_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dreams }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API napaka ${response.status}: ${text}`);
  }
}

// ── UUID helpers ──────────────────────────────────────────────────────────────

function makeUuid5(namespaceStr, name) {
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

function buildTimestamp(date, time) {
  if (!date) return new Date().toISOString();
  return `${date}T${time || "00:00"}:00.000Z`;
}
