// Loom Sync — popup.js
// Upravlja UI in izvede download (URL.createObjectURL deluje v popup kontekstu).
// Vse uporabniško besedilo prek chrome.i18n — glej _locales/{en,sl}/messages.json.

const ONEIRO_URL = "https://oneiro-delta.vercel.app";
const DEFAULT_SETTINGS = {
  deliveryMode: "download",
  apiUrl: "http://localhost:8000/api/ingest",
  apiToken: "",
};
const MAX_HISTORY = 10;

const main = document.getElementById("main");
const subtitle = document.getElementById("subtitle");
const extTitle = document.getElementById("extTitle");
const footer = document.getElementById("footer");
const btnSettingsToggle = document.getElementById("btnSettingsToggle");

let activeOneiroTabId = null; // nastavljeno v init(), uporabljeno v startSync()
let view = "sync"; // "sync" | "settings"

function t(key, substitutions) {
  return chrome.i18n.getMessage(key, substitutions);
}

async function getSettings() {
  const { settings } = await chrome.storage.local.get("settings");
  return { ...DEFAULT_SETTINGS, ...(settings || {}) };
}

async function saveSettings(settings) {
  await chrome.storage.local.set({ settings });
}

async function getHistory() {
  const { syncHistory } = await chrome.storage.local.get("syncHistory");
  return syncHistory || [];
}

async function pushHistory(entry) {
  const history = await getHistory();
  history.unshift(entry);
  await chrome.storage.local.set({ syncHistory: history.slice(0, MAX_HISTORY) });
}

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
  extTitle.textContent = t("extName");
  footer.textContent = t("footerVersion", [chrome.runtime.getManifest().version]);

  btnSettingsToggle.title = t("settingsTitle");
  btnSettingsToggle.addEventListener("click", toggleSettings);

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  activeOneiroTabId = tab?.url?.startsWith(ONEIRO_URL) ? tab.id : null;

  await renderSyncView();
}

function toggleSettings() {
  view = view === "sync" ? "settings" : "sync";
  if (view === "settings") {
    renderSettingsView();
  } else {
    renderSyncView();
  }
}

// ── Sync view ─────────────────────────────────────────────────────────────────

async function renderSyncView() {
  subtitle.textContent = t("subtitleDefault");

  if (!activeOneiroTabId) {
    showWrongPage();
    return;
  }

  const settings = await getSettings();
  await showReady(settings);
}

function showWrongPage() {
  subtitle.textContent = t("subtitleWrongPage");
  main.innerHTML = `
    <div class="wrong-page">
      ${t("wrongPageBody", [`<a href="${ONEIRO_URL}" target="_blank">${t("wrongPageLinkText")}</a>`])}
    </div>
  `;
}

async function showReady(settings) {
  const modeLabel = settings.deliveryMode === "api" ? t("currentModeApi") : t("currentModeDownload");
  const history = await getHistory();

  main.innerHTML = `
    <div class="status ok">
      <div class="dot"></div>
      ${t("statusDetected")}
    </div>
    <div class="mode-badge">${modeLabel}</div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">${t("btnSync")}</button>
      <button class="btn-secondary" id="btnSyncNew">${t("btnSyncNew")}</button>
    </div>
    <div class="meta" id="meta"></div>
    ${renderHistorySection(history)}
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
  attachHistoryToggle();

  if (history[0]) updateMeta(history[0]);
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

async function showDone(count, dreamCount) {
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
    ${renderHistorySection(await getHistory())}
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
  attachHistoryToggle();
}

function showError(message, code) {
  // Pri "unauthorized" (napačen/potekel pairing token) dodaj bližnjico
  // direktno v Nastavitve, namesto da uporabnik sam ugotovi kam iti.
  const settingsHint = code === "unauthorized"
    ? `<button class="btn-secondary" id="btnGoToSettings" style="margin-top: 6px;">${t("settingsTitle")}</button>`
    : "";

  main.innerHTML = `
    <div class="status error">
      <div class="dot"></div>
      ${message}
    </div>
    <div class="actions">
      <button class="btn-primary" id="btnSync">${t("btnTryAgain")}</button>
      <button class="btn-secondary" id="btnSyncNew">${t("btnSyncNew")}</button>
      ${settingsHint}
    </div>
    <div class="meta" id="meta"></div>
  `;
  document.getElementById("btnSync").addEventListener("click", () => startSync(false));
  document.getElementById("btnSyncNew").addEventListener("click", () => startSync(true));
  document.getElementById("btnGoToSettings")?.addEventListener("click", () => {
    view = "settings";
    renderSettingsView();
  });
}

function updateMeta(lastEntry) {
  const meta = document.getElementById("meta");
  if (meta && lastEntry) {
    // chrome.i18n.getUILanguage() namesto trdo kodiranega "sl-SI" — sledi
    // brskalnikovemu jeziku, enako kot izbira messages.json datoteke.
    const date = new Date(lastEntry.timestamp).toLocaleString(chrome.i18n.getUILanguage());
    meta.textContent = t("metaLastSync", [date, String(lastEntry.count)]);
  }
}

// ── Zgodovina ─────────────────────────────────────────────────────────────────
// Prej se je shranil samo EN zapis (lastSync) — vsak nov sync je prejšnjega
// prepisal. Zdaj syncHistory array (cap MAX_HISTORY), da uporabnik lahko
// preveri vzorec preteklih sync-ov, ne samo zadnjega.

let historyExpanded = false;

function renderHistorySection(history) {
  if (history.length === 0) return "";
  return `
    <div class="history">
      <button class="history-toggle" id="btnHistoryToggle">
        ${historyExpanded ? "▲" : "▼"} ${t("historyTitle")} (${history.length})
      </button>
      ${historyExpanded ? `<div class="history-list">${history.map(renderHistoryItem).join("")}</div>` : ""}
    </div>
  `;
}

function renderHistoryItem(entry) {
  const date = new Date(entry.timestamp).toLocaleString(chrome.i18n.getUILanguage());
  if (entry.status === "error") {
    return `<div class="history-item error"><span>${date}</span><span>${t("historyEntryError")}</span></div>`;
  }
  return `<div class="history-item"><span>${date}</span><span>${entry.count} · ${entry.mode}</span></div>`;
}

function attachHistoryToggle() {
  document.getElementById("btnHistoryToggle")?.addEventListener("click", async () => {
    historyExpanded = !historyExpanded;
    await showReady(await getSettings());
  });
}

// ── Nastavitve view ───────────────────────────────────────────────────────────

async function renderSettingsView() {
  subtitle.textContent = t("settingsTitle");
  const settings = await getSettings();

  main.innerHTML = `
    <div class="settings-panel">
      <div class="mode-toggle">
        <button id="modeDownload" class="${settings.deliveryMode === "download" ? "active" : ""}">
          ${t("deliveryModeDownload")}
        </button>
        <button id="modeApi" class="${settings.deliveryMode === "api" ? "active" : ""}">
          ${t("deliveryModeApi")}
        </button>
      </div>

      <div id="apiFields" style="display: ${settings.deliveryMode === "api" ? "block" : "none"};">
        <div class="field">
          <label>${t("apiUrlLabel")}</label>
          <input type="text" id="inputApiUrl" value="${escapeHtml(settings.apiUrl)}" />
        </div>
        <div class="field">
          <label>${t("apiTokenLabel")}</label>
          <input type="text" id="inputApiToken" value="${escapeHtml(settings.apiToken)}" placeholder="${t("apiTokenPlaceholder")}" />
          <span class="hint">${t("apiTokenHint")}</span>
        </div>
      </div>

      <div class="settings-actions">
        <button class="btn-secondary" id="btnSettingsBack">${t("settingsBack")}</button>
        <button class="btn-primary" id="btnSettingsSave">${t("settingsSave")}</button>
      </div>
    </div>
  `;

  let selectedMode = settings.deliveryMode;
  const apiFields = document.getElementById("apiFields");

  document.getElementById("modeDownload").addEventListener("click", () => {
    selectedMode = "download";
    document.getElementById("modeDownload").classList.add("active");
    document.getElementById("modeApi").classList.remove("active");
    apiFields.style.display = "none";
  });
  document.getElementById("modeApi").addEventListener("click", () => {
    selectedMode = "api";
    document.getElementById("modeApi").classList.add("active");
    document.getElementById("modeDownload").classList.remove("active");
    apiFields.style.display = "block";
  });

  document.getElementById("btnSettingsBack").addEventListener("click", () => {
    view = "sync";
    renderSyncView();
  });

  document.getElementById("btnSettingsSave").addEventListener("click", async () => {
    const newSettings = {
      deliveryMode: selectedMode,
      apiUrl: document.getElementById("inputApiUrl").value.trim() || DEFAULT_SETTINGS.apiUrl,
      apiToken: document.getElementById("inputApiToken").value.trim(),
    };
    await saveSettings(newSettings);
    const btn = document.getElementById("btnSettingsSave");
    btn.textContent = t("settingsSaved");
    setTimeout(() => { btn.textContent = t("settingsSave"); }, 1500);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Sync flow ─────────────────────────────────────────────────────────────────

async function startSync(onlyNew) {
  showWorking();

  let sinceTimestamp = null;
  if (onlyNew) {
    const history = await getHistory();
    sinceTimestamp = history[0]?.timestamp || null;
  }

  chrome.runtime.sendMessage({ action: "sync", sinceTimestamp, tabId: activeOneiroTabId }, async (response) => {
    if (chrome.runtime.lastError) {
      showError(t("errGeneric", [chrome.runtime.lastError.message]));
      return;
    }

    if (!response.ok) {
      await pushHistory({ timestamp: new Date().toISOString(), status: "error" });
      showError(response.error || t("errUnknownError"), response.code);
      return;
    }

    if (response.count === 0) {
      await showDone(0, 0);
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

    await pushHistory({
      timestamp: new Date().toISOString(),
      count: response.count,
      dreamCount: response.dreamCount,
      mode: response.mode,
      status: "ok",
    });

    await showDone(response.count, response.dreamCount);
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
