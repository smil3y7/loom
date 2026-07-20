// Loom Sync — popup.js
// Upravlja UI in izvede download (URL.createObjectURL deluje v popup kontekstu).

const ONEIRO_URL = "https://oneiro-delta.vercel.app";

const main = document.getElementById("main");
const subtitle = document.getElementById("subtitle");

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isOnOneiro = tab?.url?.startsWith(ONEIRO_URL);

  if (!isOnOneiro) {
    showWrongPage();
    return;
  }

  showReady();

  const { lastSync } = await chrome.storage.local.get("lastSync");
  if (lastSync) updateMeta(lastSync);
}

// ── UI states ─────────────────────────────────────────────────────────────────

function showWrongPage() {
  subtitle.textContent = "Oneiro ni odprt";
  main.innerHTML = `
    <div class="wrong-page">
      Odpri <a href="${ONEIRO_URL}" target="_blank">Oneiro</a>
      v tem tabu, nato klikni ikono znova.
    </div>
  `;
}

function showReady() {
  main.innerHTML = `
    <div class="status ok">
      <div class="dot"></div>
      Oneiro zaznan
    </div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">Sync z Loom</button>
      <button class="btn-secondary" id="btnSyncNew">Samo nove sanje</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
}

function showWorking(message = "Berem sanje...") {
  main.innerHTML = `
    <div class="status working">
      <div class="dot pulse"></div>
      ${message}
    </div>
    <div class="actions">
      <button class="btn-primary" disabled>Sync z Loom</button>
      <button class="btn-secondary" disabled>Samo nove sanje</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
}

function showDone(count) {
  main.innerHTML = `
    <div class="status ok">
      <div class="dot"></div>
      ${count} sanj izvoženih — premakni v Loom/sources/oneiro/
    </div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">Sync znova</button>
      <button class="btn-secondary" id="btnSyncNew">Samo nove sanje</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
}

function showError(message) {
  main.innerHTML = `
    <div class="status error">
      <div class="dot"></div>
      ${message}
    </div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">Poskusi znova</button>
      <button class="btn-secondary" id="btnSyncNew">Samo nove sanje</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
}

function updateMeta(lastSync) {
  const meta = document.getElementById("meta");
  if (meta && lastSync) {
    const date = new Date(lastSync.timestamp).toLocaleString("sl-SI");
    meta.textContent = `Zadnji sync: ${date} · ${lastSync.count} sanj`;
  }
}

// ── Sync flow ─────────────────────────────────────────────────────────────────

async function startSync(onlyNew) {
  showWorking("Berem sanje iz Oneire...");

  let sinceTimestamp = null;
  if (onlyNew) {
    const { lastSync } = await chrome.storage.local.get("lastSync");
    sinceTimestamp = lastSync?.timestamp || null;
  }

  chrome.runtime.sendMessage({ action: "sync", sinceTimestamp }, async (response) => {
    if (chrome.runtime.lastError) {
      showError("Napaka: " + chrome.runtime.lastError.message);
      return;
    }

    if (!response.ok) {
      showError(response.error || "Neznana napaka");
      return;
    }

    if (response.count === 0) {
      showDone(0);
      return;
    }

    // Download izvede popup (ne background) — URL.createObjectURL deluje tukaj
    if (response.mode === "download" && response.dreams) {
      try {
        await downloadJson(response.dreams, response.count);
      } catch (e) {
        showError("Napaka pri izvozu: " + e.message);
        return;
      }
    }

    const syncRecord = {
      timestamp: new Date().toISOString(),
      count: response.count,
    };
    await chrome.storage.local.set({ lastSync: syncRecord });

    showDone(response.count);
    updateMeta(syncRecord);
  });
}

// ── Download (izvede se v popup kontekstu) ────────────────────────────────────

async function downloadJson(dreams, count) {
  const timestamp = new Date().toISOString()
    .replace(/[:.]/g, "-")
    .slice(0, 19);
  const filename = `oneiro_export_${timestamp}.json`;
  const json = JSON.stringify(dreams, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  // Uporabi chrome.downloads API za shranjevanje
  await chrome.downloads.download({
    url,
    filename,
    saveAs: false,
  });

  // Cleanup
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

// ── Start ─────────────────────────────────────────────────────────────────────

init();
