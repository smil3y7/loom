// Loom Sync — background.js
// Service worker: prosi Oneiro tab za dešifrirane sanje prek postMessage
// mostu (glej docs/loom-sync-protocol.md v Oneiro repozitoriju), ne bere
// več IndexedDB neposredno.
//
// ZAKAJ TA SPREMEMBA: Oneiro zdaj podpira šifriranje vsebine at-rest (PIN/
// geslo). Ko je nastavljen, so zapisi v IndexedDB VEDNO šifrirani (_enc
// blob), ne glede na to, ali je uporabnik trenutno odklenjen — ključ živi
// samo v pomnilniku odprte Oneiro strani, nikoli v shrambi. Neposredno
// branje IndexedDB zato od zdaj vedno vrne 0 uporabnih sanj, če ima
// uporabnik PIN. Namesto tega prosimo samo Oneiro stran (medtem ko je
// odprta in odklenjena), naj nam vrne že dešifrirane podatke.

const ONEIRO_URL = "https://oneiro-delta.vercel.app";
const SOURCE_APP = "oneiro";
const CCP_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8";

const BRIDGE_TIMEOUT_MS = 5000;

// PREJ: DELIVERY_MODE in LOOM_API_URL sta bila hardcoded konstanti — vsak
// preklop med download/api ali sprememba porta je zahteval urejanje kode +
// nov build. Zdaj se bere iz chrome.storage.local (nastavljivo prek
// popup.js settings zaslona), z varnimi privzetimi vrednostmi za obstoječe
// namestitve, ki settings še niso shranile.
const DEFAULT_SETTINGS = {
  deliveryMode: "download", // "download" | "api"
  apiUrl: "http://localhost:8000/api/ingest",
  apiToken: "",
};

async function getSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  return { ...DEFAULT_SETTINGS, ...(settings || {}) };
}

// ── Message handler ───────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "sync") {
    console.log("[Loom][bg] sync sprožen, sinceTimestamp:", message.sinceTimestamp, "tabId:", message.tabId);
    (async () => {
      try {
        const settings = await getSettings();
        const { dreams, interpretations } = await readFromOneiroTab(message.sinceTimestamp, message.tabId);
        console.log("[Loom][bg] prejeto od Oneira:", dreams.length, "sanj,", interpretations.length, "interpretacij");
        const canonical = mapAllToCanonical(dreams, interpretations);
        // count = število canonical ZAPISOV (lahko več na sanjo, eden na
        // interpretacijo) — dreamCount = dejansko število Oneiro sanj.
        // Prej se je v UI prikazoval samo count kot "N sanj izvoženih", kar
        // je zavajajoče kadar imajo sanje interpretacije (count > dreamCount).
        const dreamCount = dreams.length;

        if (settings.deliveryMode === "api") {
          await postToApi(canonical, settings);
          sendResponse({ ok: true, count: canonical.length, dreamCount, mode: "api" });
          return;
        }
        // Download mode — vrni podatke popupu, ta naredi download
        sendResponse({ ok: true, count: canonical.length, dreamCount, mode: "download", dreams: canonical });
      } catch (err) {
        console.error("[Loom][bg] sync napaka:", err);
        sendResponse({ ok: false, error: err.message, code: err.code || null });
      }
    })();
    return true;
  }
});

// ── Beri dešifrirane podatke iz Oneiro taba prek postMessage mostu ───────────

async function readFromOneiroTab(sinceTimestamp, preferredTabId) {
  let tabId = preferredTabId;

  if (tabId) {
    console.log("[Loom][bg] uporabljam posredovan tabId (aktivni tab iz popupa):", tabId);
  } else {
    // Fallback za primer, da tabId ni bil posredovan (npr. klic iz drugega
    // konteksta) — VEDNO se najprej poskusi z aktivnim tabom trenutnega
    // okna, šele nato s poljubnim ujemajočim tabom. Prejšnja različica je
    // vzela kar prvi ujemajoč tab (tabs[0]) — pri več odprtih Oneiro tabih
    // (potrjeno: uporabnik jih je imel 3 hkrati) je to lahko pobralo napačen,
    // nezaklenjen/neaktiven tab, kar je povzročilo tihi timeout.
    console.warn("[Loom][bg] tabId ni bil posredovan — poskušam najti aktivni tab kot fallback");
    const [activeTab] = await chrome.tabs.query({ active: true, url: `${ONEIRO_URL}/*` });
    if (activeTab) {
      tabId = activeTab.id;
    } else {
      const tabs = await chrome.tabs.query({ url: `${ONEIRO_URL}/*` });
      console.log("[Loom][bg] najdenih tabov (fallback, brez active filtra):", tabs.length, tabs.map(t => t.id));
      if (!tabs.length) {
        throw new Error(chrome.i18n.getMessage("errTabNotFound"));
      }
      tabId = tabs[0].id;
    }
  }

  console.log("[Loom][bg] injiciram bridge klic v tab", tabId);
  let results;
  try {
    results = await chrome.scripting.executeScript({
      target: { tabId },
      func: requestViaBridge,
      args: [sinceTimestamp, BRIDGE_TIMEOUT_MS],
      world: "MAIN",
    });
  } catch (execErr) {
    console.error("[Loom][bg] executeScript je vrgel napako:", execErr);
    throw new Error(chrome.i18n.getMessage("errInjection", [execErr.message]));
  }
  console.log("[Loom][bg] executeScript rezultat:", JSON.stringify(results));

  const response = results?.[0]?.result;
  if (!response) {
    throw new Error(chrome.i18n.getMessage("errNoResponse"));
  }
  if (!response.ok) {
    // Namensko IGNORIRAMO response.message — Oneiro ga (trenutno) pošlje
    // samo v angleščini, ne prek svojega i18n sistema. Extension ima svoj
    // pravilno lokaliziran niz za oba primera, ki mora imeti prednost, da
    // uporabnik dobi sporočilo v pravem jeziku ne glede na to, kaj Oneiro
    // pošlje na tej ravni protokola.
    if (response.locked) {
      throw new Error(chrome.i18n.getMessage("errLocked"));
    }
    throw new Error(chrome.i18n.getMessage("errUnknown"));
  }

  return { dreams: response.dreams || [], interpretations: response.interpretations || [] };
}

// ── Bridge klient (injiciran v Oneiro tab) ────────────────────────────────────
// Pošlje LOOM_SYNC_REQUEST, počaka na LOOM_SYNC_RESPONSE z istim requestId,
// z timeoutom če Oneiro stran nima naloženega bridge listenerja (stara
// verzija Oneira brez tega popravka, ali stran se še nalaga).
function requestViaBridge(sinceTimestamp, timeoutMs) {
  console.log("[Loom][injected] zaganjam bridge zahtevo, sinceTimestamp:", sinceTimestamp);
  return new Promise((resolve) => {
    const requestId = crypto.randomUUID();
    let settled = false;

    function cleanup() {
      window.removeEventListener("message", handleResponse);
      clearTimeout(timer);
    }

    function handleResponse(event) {
      if (event.source !== window) return;
      if (!event.data || event.data.type !== "LOOM_SYNC_RESPONSE") return;
      if (event.data.source !== "oneiro-app") return;
      if (event.data.requestId !== requestId) return;
      if (settled) return;
      console.log("[Loom][injected] odgovor prejet:", event.data.payload);
      settled = true;
      cleanup();
      resolve(event.data.payload);
    }

    const timer = setTimeout(() => {
      if (settled) return;
      console.warn("[Loom][injected] TIMEOUT — odgovor ni prispel v", timeoutMs, "ms");
      settled = true;
      cleanup();
      resolve(null); // signalizira "ni odgovora" naprej v readFromOneiroTab
    }, timeoutMs);

    window.addEventListener("message", handleResponse);
    console.log("[Loom][injected] pošiljam LOOM_SYNC_REQUEST, requestId:", requestId);
    window.postMessage({
      type: "LOOM_SYNC_REQUEST",
      source: "loom-extension",
      requestId,
      payload: { sinceTimestamp: sinceTimestamp || null },
    }, window.location.origin);
  });
}

// ── Canonical mapping ─────────────────────────────────────────────────────────
// Ena Oneiro sanja lahko ima 0-3 AI interpretacije (ena na mode) + ločen
// `notes` zapisek — Loom canonical shape ima en sam extras.oneiro_interpretation
// slot na entry. Izbrana rešitev: EN canonical entry na (sanja, interpretacija)
// par, plus ločen entry za notes, če obstaja. Če sanja nima ne interpretacije
// ne zapiska, dobi en entry z oneiro_interpretation: null.
//
// POMEMBNO — dream_id diferenciacija: ker en Oneiro `record.id` lahko proizvede
// VEČ canonical entryjev (do 4: base/ai×3/notes), mora vsak dobiti SVOJ
// deterministični dream_id. Prej je dream_id temeljil samo na record.id, kar je
// povzročilo kolizijo — vsi entryji iste sanje so trčili na isti ID, zadnji
// procesiran je tiho prepisal prejšnje (potrjeno na realnem exportu: 52 vhodnih
// zapisov → samo 26 preživelo). Popravek: dream_id zdaj vključuje interpretation
// diferenciator (source + mode) kadar entry NI osnovna sanja.

function mapAllToCanonical(dreams, interpretations) {
  const interpretationsByDream = new Map();
  for (const interp of interpretations) {
    const list = interpretationsByDream.get(interp.dreamId) || [];
    list.push(interp);
    interpretationsByDream.set(interp.dreamId, list);
  }

  const entries = [];
  for (const dream of dreams) {
    const dreamInterps = interpretationsByDream.get(dream.id) || [];

    if (dreamInterps.length === 0 && !dream.notes) {
      entries.push(mapToCanonical(dream, null, null, null, null));
      continue;
    }

    for (const interp of dreamInterps) {
      const text = interp.full_interpretation || interp.main_interpretation || interp.quick_insight || null;
      // Diferenciator mora biti interp.id (Oneirov lastni ID interpretacijskega
      // zapisa), NE interp.mode — isti mode se lahko regenerira večkrat
      // (uporabnik ponovno zahteva "neutral" interpretacijo), kar ustvari
      // VEČ ločenih zapisov z istim mode. Diferenciacija samo po mode je
      // povzročila preostalo kolizijo (potrjeno na realnem exportu: dve
      // različni "neutral" interpretaciji iste sanje sta trčili na isti ID).
      entries.push(mapToCanonical(dream, text, "ai", interp.mode || "unknown", interp.id));
    }
    if (dream.notes) {
      // dream.notes je eno samo polje na sanjo (ne seznam) — ni tveganja
      // kolizije med več "notes" zapisi iste sanje, zato ne rabi interp.id.
      entries.push(mapToCanonical(dream, dream.notes, "user", null, null));
    }
  }
  return entries;
}

function mapToCanonical(record, interpretationText, interpretationSource, interpretationMode, interpretationId) {
  // Diferenciator za dream_id — prazen za osnovno sanjo (interpretationSource
  // je null). Za AI interpretacije uporabi Oneirov lastni interpretation.id
  // (zagotovljeno unikaten), ne mode (mode se lahko ponovi pri regeneraciji).
  // Za user notes zadošča "source:default", ker je notes eno samo polje.
  let idSuffix = "";
  if (interpretationSource === "ai") {
    idSuffix = `:ai:${interpretationId || interpretationMode || "unknown"}`;
  } else if (interpretationSource === "user") {
    idSuffix = ":user:default";
  }

  return {
    dream_id: makeUuid5(CCP_NAMESPACE, `${SOURCE_APP}:${record.id}${idSuffix}`),
    source_app: SOURCE_APP,
    // record.createdAt je po protokolu v2 vedno prisoten na Dream objektu;
    // buildTimestamp(record.date) je samo varnostna mreža za robne primere
    // (starejši/nepopoln export). Prej je klical buildTimestamp(date, time)
    // — record.time ne obstaja v v2 protokolu (samo ločen `date`), to je
    // bil mrtev parameter, odstranjen.
    timestamp: record.createdAt || buildTimestamp(record.date),
    title: record.title || null,
    content: record.content,
    language: record.language || "other",
    metadata: {
      lucid: record.isLucid || false,
      tags: record.tags || null, // string (comma-separated), ni array
      emotions: record.emotionalTone ? [record.emotionalTone] : [],
      emotional_tone: record.emotionalTone || null,
      is_nightmare: record.isNightmare || false,
      is_recurring: record.isRecurring || false,
      vividness: record.intensity || null, // string enum, ni številka 1-5
      extras: {
        oneiro_id: record.id,
        oneiro_interpretation: interpretationText,
        oneiro_interpretation_id: interpretationId || null,  // NOVO — Oneirov lastni ID zapisa
        oneiro_interpretation_source: interpretationSource, // "ai" | "user" | null
        oneiro_interpretation_mode: interpretationMode,      // "neutral" | "jungian" | "shamanic" | null
        date: record.date || null,
        characters: record.characters || null,       // string, ni array
        body_sensations: record.bodySensations || null, // string, ni array
        sleep_context: record.sleepContext || null,    // array (ali null)
        last_edited_at: record.lastEditedAt || null,
      },
    },
    source_updated_at: record.lastEditedAt || null,
  };
}

// ── API delivery ──────────────────────────────────────────────────────────────

async function postToApi(dreams, settings) {
  let response;
  try {
    response = await fetch(settings.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Loom-Token": settings.apiToken || "",
      },
      body: JSON.stringify({ dreams }),
    });
  } catch (networkErr) {
    // fetch sam vrže samo pri mrežni napaki (Loom backend ne teče, napačen
    // URL, itd.) — ločeno sporočilo od HTTP-level napak spodaj, da
    // uporabnik ve, ali naj preveri da Loom sploh teče, ali pairing token.
    const err = new Error(chrome.i18n.getMessage("errApiUnreachable", [settings.apiUrl]));
    err.code = "unreachable";
    throw err;
  }

  if (response.status === 401) {
    const err = new Error(chrome.i18n.getMessage("errApiUnauthorized"));
    err.code = "unauthorized";
    throw err;
  }
  if (!response.ok) {
    const text = await response.text();
    throw new Error(chrome.i18n.getMessage("errApiFailed", [String(response.status), text]));
  }
}

// ── UUID helpers ──────────────────────────────────────────────────────────────
// Znana omejitev (glej README.md): ta FNV-based hash ni bit-kompatibilen s
// pravim UUID5 (Python `make_dream_id`). Ni spremenjeno v tem popravku —
// dotika se ločenega vprašanja od šifriranja/bridge-a. Če je to zdaj
// relevantno, je to ločen popravek.

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

function buildTimestamp(date) {
  if (!date) return new Date().toISOString();
  return `${date}T00:00:00.000Z`;
}
