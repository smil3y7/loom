// Loom Sync — popup.js
// Upravlja UI in izvede download (URL.createObjectURL deluje v popup kontekstu).
// Vse uporabniško besedilo prek chrome.i18n — glej _locales/{en,sl}/messages.json.

const ONEIRO_URL = "https://oneiro-delta.vercel.app";

const main = document.getElementById("main");
const subtitle = document.getElementById("subtitle");
const extTitle = document.getElementById("extTitle");

let activeOneiroTabId = null; // nastavljeno v init(), uporabljeno v startSync()

function t(key, substitutions) {
  return chrome.i18n.getMessage(key, substitutions);
}

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  extTitle.textContent = t("extName");
  subtitle.textContent = t("subtitleDefault");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const isOnOneiro = tab?.url?.startsWith(ONEIRO_URL);

  if (!isOnOneiro) {
    showWrongPage();
    return;
  }

  activeOneiroTabId = tab.id;
  showReady();

  const { lastSync } = await chrome.storage.local.get("lastSync");
  if (lastSync) updateMeta(lastSync);
}

// ── UI states ─────────────────────────────────────────────────────────────────

function showWrongPage() {
  subtitle.textContent = t("subtitleWrongPage");
  main.innerHTML = `
    <div class="wrong-page">
      ${t("wrongPageBody", [`<a href="${ONEIRO_URL}" target="_blank">${t("wrongPageLinkText")}</a>`])}
    </div>
  `;
}

function showReady() {
  main.innerHTML = `
    <div class="status ok">
      <div class="dot"></div>
      ${t("statusDetected")}
    </div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">${t("btnSync")}</button>
      <button class="btn-secondary" id="btnSyncNew">${t("btnSyncNew")}</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
}

function showWorking(message) {
  main.innerHTML = `
    <div class="status working">
      <div class="dot pulse"></div>
      ${message ?? t("workingReading")}
    </div>
    <div class="actions">
      <button class="btn-primary" disabled>${t("btnSync")}</button>
      <button class="btn-secondary" disabled>${t("btnSyncNew")}</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
}

function showDone(count, dreamCount) {
  // Če je count > dreamCount, pomeni da so nekatere sanje proizvedle več
  // canonical zapisov (eden na interpretacijo) — prikaži oboje, ne samo
  // "N sanj izvoženih" kar je bilo zavajajoče (count je bil dejansko število
  // zapisov, ne sanj).
  const message = (dreamCount != null && dreamCount !== count)
    ? t("doneExportedDetailed", [String(dreamCount), String(count)])
    : t("doneExported", [String(count)]);

  main.innerHTML = `
    <div class="status ok">
      <div class="dot"></div>
      ${message}
    </div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">${t("btnSyncAgain")}</button>
      <button class="btn-secondary" id="btnSyncNew">${t("btnSyncNew")}</button>
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
      <button class="btn-primary" id="btnSync">${t("btnTryAgain")}</button>
      <button class="btn-secondary" id="btnSyncNew">${t("btnSyncNew")}</button>
    </div>
    <div class="meta" id="meta"></div>
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
}

function updateMeta(lastSync) {
  const meta = document.getElementById("meta");
  if (meta && lastSync) {
    // chrome.i18n.getUILanguage() namesto trdo kodiranega "sl-SI" — sledi
    // brskalnikovemu jeziku, enako kot izbira messages.json datoteke.
    const date = new Date(lastSync.timestamp).toLocaleString(chrome.i18n.getUILanguage());
    meta.textContent = t("metaLastSync", [date, String(lastSync.count)]);
  }
}

// ── Sync flow ─────────────────────────────────────────────────────────────────

async function startSync(onlyNew) {
  showWorking();

  let sinceTimestamp = null;
  if (onlyNew) {
    const { lastSync } = await chrome.storage.local.get("lastSync");
    sinceTimestamp = lastSync?.timestamp || null;
  }

  chrome.runtime.sendMessage({ action: "sync", sinceTimestamp, tabId: activeOneiroTabId }, async (response) => {
    if (chrome.runtime.lastError) {
      showError(t("errGeneric", [chrome.runtime.lastError.message]));
      return;
    }

    if (!response.ok) {
      showError(response.error || t("errUnknownError"));
      return;
    }

    if (response.count === 0) {
      showDone(0, 0);
      return;
    }

    // Download izvede popup (ne background) — URL.createObjectURL deluje tukaj
    if (response.mode === "download" && response.dreams) {
      try {
        await downloadJson(response.dreams, response.count);
      } catch (e) {
        showError(t("errExportFailed", [e.message]));
        return;
      }
    }

    const syncRecord = {
      timestamp: new Date().toISOString(),
      count: response.count,
    };
    await chrome.storage.local.set({ lastSync: syncRecord });

    showDone(response.count, response.dreamCount);
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
