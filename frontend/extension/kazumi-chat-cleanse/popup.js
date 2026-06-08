const STORAGE_KEY = "kazumi_chat_cleanse_config";

const PRESETS = {
  chill: { aggressionThreshold: 3.0, spamThreshold: 8, capsThresholdPct: 100 },
  balanced: { aggressionThreshold: 2.0, spamThreshold: 5, capsThresholdPct: 90 },
  strict: { aggressionThreshold: 1.0, spamThreshold: 3, capsThresholdPct: 65 },
};

const DEFAULT_CONFIG = {
  enabled: true,
  mode: "balanced",
  localScoringOnly: true,
  hideAggression: true,
  hideSpam: true,
  hideCaps: true,
  aggressionThreshold: 2.0,
  spamThreshold: 5,
  capsThresholdPct: 90,
  whitelist: [],
  showHidden: false,
  audioEnabled: true,
  smartLeveling: true,
  voiceBoostPct: 120,
  gameTamePct: 35,
  masterGainPct: 100,
  latencySyncEnabled: true,
  latencySyncMs: 3500,
  apiBaseUrl: "http://localhost:8000",
  token: "",
};

const el = {
  apiBaseUrl: document.getElementById("apiBaseUrl"),
  email: document.getElementById("email"),
  password: document.getElementById("password"),
  enabled: document.getElementById("enabled"),
  mode: document.getElementById("mode"),
  localScoringOnly: document.getElementById("localScoringOnly"),
  hideAggression: document.getElementById("hideAggression"),
  hideSpam: document.getElementById("hideSpam"),
  hideCaps: document.getElementById("hideCaps"),
  aggressionThreshold: document.getElementById("aggressionThreshold"),
  spamThreshold: document.getElementById("spamThreshold"),
  capsThresholdPct: document.getElementById("capsThresholdPct"),
  aggressionLabel: document.getElementById("aggressionLabel"),
  spamLabel: document.getElementById("spamLabel"),
  capsLabel: document.getElementById("capsLabel"),
  audioEnabled: document.getElementById("audioEnabled"),
  smartLeveling: document.getElementById("smartLeveling"),
  voiceBoostPct: document.getElementById("voiceBoostPct"),
  gameTamePct: document.getElementById("gameTamePct"),
  masterGainPct: document.getElementById("masterGainPct"),
  voiceBoostLabel: document.getElementById("voiceBoostLabel"),
  gameTameLabel: document.getElementById("gameTameLabel"),
  masterGainLabel: document.getElementById("masterGainLabel"),
  latencySyncEnabled: document.getElementById("latencySyncEnabled"),
  latencySyncMs: document.getElementById("latencySyncMs"),
  latencySyncLabel: document.getElementById("latencySyncLabel"),
  whitelist: document.getElementById("whitelist"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  pullBtn: document.getElementById("pullBtn"),
  pushBtn: document.getElementById("pushBtn"),
  saveBtn: document.getElementById("saveBtn"),
  statusBox: document.getElementById("statusBox"),
};

let currentConfig = { ...DEFAULT_CONFIG };

function clamp(value, min, max, fallback) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function mergeConfig(source) {
  const raw = source || {};
  const mode = String(raw.mode || DEFAULT_CONFIG.mode).trim().toLowerCase();
  return {
    ...DEFAULT_CONFIG,
    ...raw,
    mode: ["chill", "balanced", "strict", "custom"].includes(mode) ? mode : DEFAULT_CONFIG.mode,
    enabled: raw.enabled !== false,
    localScoringOnly: raw.localScoringOnly !== false,
    hideAggression: raw.hideAggression !== false,
    hideSpam: raw.hideSpam !== false,
    hideCaps: raw.hideCaps !== false,
    aggressionThreshold: clamp(raw.aggressionThreshold, 0.5, 3.5, DEFAULT_CONFIG.aggressionThreshold),
    spamThreshold: Math.round(clamp(raw.spamThreshold, 2, 12, DEFAULT_CONFIG.spamThreshold)),
    capsThresholdPct: Math.round(clamp(raw.capsThresholdPct, 40, 100, DEFAULT_CONFIG.capsThresholdPct)),
    whitelist: Array.isArray(raw.whitelist)
      ? raw.whitelist.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 80)
      : [],
    audioEnabled: raw.audioEnabled !== false,
    smartLeveling: raw.smartLeveling !== false,
    voiceBoostPct: Math.round(clamp(raw.voiceBoostPct, 80, 220, DEFAULT_CONFIG.voiceBoostPct)),
    gameTamePct: Math.round(clamp(raw.gameTamePct, 0, 100, DEFAULT_CONFIG.gameTamePct)),
    masterGainPct: Math.round(clamp(raw.masterGainPct, 60, 170, DEFAULT_CONFIG.masterGainPct)),
    latencySyncEnabled: raw.latencySyncEnabled !== false,
    latencySyncMs: Math.round(clamp(raw.latencySyncMs, 0, 8000, DEFAULT_CONFIG.latencySyncMs)),
    apiBaseUrl: String(raw.apiBaseUrl || DEFAULT_CONFIG.apiBaseUrl).trim(),
    token: String(raw.token || "").trim(),
  };
}

function readConfig() {
  return new Promise((resolve) => {
    chrome.storage.sync.get([STORAGE_KEY], (result) => {
      resolve(mergeConfig(result[STORAGE_KEY]));
    });
  });
}

function writeConfig(config) {
  currentConfig = mergeConfig(config);
  return new Promise((resolve) => {
    chrome.storage.sync.set({ [STORAGE_KEY]: currentConfig }, resolve);
  });
}

function setStatus(text, kind = "") {
  el.statusBox.textContent = text;
  el.statusBox.className = `status ${kind}`.trim();
}

function readFormConfig() {
  const whitelist = String(el.whitelist.value || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const next = mergeConfig({
    ...currentConfig,
    apiBaseUrl: el.apiBaseUrl.value.trim(),
    enabled: el.enabled.checked,
    mode: el.mode.value,
    localScoringOnly: el.localScoringOnly.checked,
    hideAggression: el.hideAggression.checked,
    hideSpam: el.hideSpam.checked,
    hideCaps: el.hideCaps.checked,
    aggressionThreshold: Number(el.aggressionThreshold.value),
    spamThreshold: Number(el.spamThreshold.value),
    capsThresholdPct: Number(el.capsThresholdPct.value),
    audioEnabled: el.audioEnabled.checked,
    smartLeveling: el.smartLeveling.checked,
    voiceBoostPct: Number(el.voiceBoostPct.value),
    gameTamePct: Number(el.gameTamePct.value),
    masterGainPct: Number(el.masterGainPct.value),
    latencySyncEnabled: el.latencySyncEnabled.checked,
    latencySyncMs: Number(el.latencySyncMs.value),
    whitelist,
  });

  if (next.mode !== "custom") {
    const preset = PRESETS[next.mode] || PRESETS.balanced;
    next.aggressionThreshold = preset.aggressionThreshold;
    next.spamThreshold = preset.spamThreshold;
    next.capsThresholdPct = preset.capsThresholdPct;
  }
  return next;
}

function renderLabels(cfg) {
  el.aggressionLabel.textContent = cfg.aggressionThreshold.toFixed(1);
  el.spamLabel.textContent = String(cfg.spamThreshold);
  el.capsLabel.textContent = `${cfg.capsThresholdPct}%`;
  el.voiceBoostLabel.textContent = `${cfg.voiceBoostPct}%`;
  el.gameTameLabel.textContent = `${cfg.gameTamePct}%`;
  el.masterGainLabel.textContent = `${cfg.masterGainPct}%`;
  el.latencySyncLabel.textContent = `${Math.round(cfg.latencySyncMs / 1000)}s`;
}

function render(cfg) {
  const merged = mergeConfig(cfg);
  currentConfig = merged;
  el.apiBaseUrl.value = merged.apiBaseUrl;
  el.enabled.checked = merged.enabled;
  el.mode.value = merged.mode;
  el.localScoringOnly.checked = merged.localScoringOnly;
  el.hideAggression.checked = merged.hideAggression;
  el.hideSpam.checked = merged.hideSpam;
  el.hideCaps.checked = merged.hideCaps;
  el.aggressionThreshold.value = String(merged.aggressionThreshold);
  el.spamThreshold.value = String(merged.spamThreshold);
  el.capsThresholdPct.value = String(merged.capsThresholdPct);
  el.audioEnabled.checked = merged.audioEnabled;
  el.smartLeveling.checked = merged.smartLeveling;
  el.voiceBoostPct.value = String(merged.voiceBoostPct);
  el.gameTamePct.value = String(merged.gameTamePct);
  el.masterGainPct.value = String(merged.masterGainPct);
  el.latencySyncEnabled.checked = merged.latencySyncEnabled;
  el.latencySyncMs.value = String(merged.latencySyncMs);
  el.whitelist.value = (merged.whitelist || []).join("\n");
  renderLabels(merged);

  const customEnabled = merged.mode === "custom";
  el.aggressionThreshold.disabled = !customEnabled;
  el.spamThreshold.disabled = !customEnabled;
  el.capsThresholdPct.disabled = !customEnabled;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  let body = {};
  try {
    body = await response.json();
  } catch {
    body = {};
  }
  if (!response.ok) {
    const message = body.detail || body.message || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return body;
}

async function login() {
  const email = el.email.value.trim();
  const password = el.password.value;
  if (!email || !password) {
    setStatus("Email and password are required.", "warn");
    return;
  }

  try {
    setStatus("Logging in...");
    const payload = await fetchJson(`${currentConfig.apiBaseUrl.replace(/\/$/, "")}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const role = payload?.user?.role || "viewer";
    if (role !== "viewer") {
      setStatus("This extension expects a viewer account.", "warn");
    }
    const next = mergeConfig({ ...currentConfig, token: payload.token || "" });
    await writeConfig(next);
    render(next);
    setStatus("Connected. Token stored.", "ok");
    await pullCloud();
  } catch (error) {
    setStatus(`Login failed: ${error.message}`, "warn");
  }
}

async function pullCloud() {
  if (!currentConfig.token) {
    setStatus("Login first to pull cloud profile.", "warn");
    return;
  }
  try {
    setStatus("Pulling cloud profile...");
    const data = await fetchJson(
      `${currentConfig.apiBaseUrl.replace(/\/$/, "")}/api/viewer/chat-cleanse/preferences`,
      {
        headers: { Authorization: `Bearer ${currentConfig.token}` },
      },
    );
    const prefs = data.preferences || {};
    const next = mergeConfig({
      ...currentConfig,
      enabled: prefs.enabled,
      mode: prefs.mode,
      localScoringOnly: prefs.local_scoring_only,
      hideAggression: prefs.hide_aggression,
      hideSpam: prefs.hide_spam,
      hideCaps: prefs.hide_caps,
      aggressionThreshold: prefs.aggression_threshold,
      spamThreshold: prefs.spam_threshold,
      capsThresholdPct: prefs.caps_threshold_pct,
      whitelist: prefs.whitelist || [],
    });
    await writeConfig(next);
    render(next);
    setStatus("Cloud profile pulled.", "ok");
  } catch (error) {
    setStatus(`Pull failed: ${error.message}`, "warn");
  }
}

async function pushCloud() {
  if (!currentConfig.token) {
    setStatus("Login first to push cloud profile.", "warn");
    return;
  }
  try {
    const next = readFormConfig();
    await writeConfig(next);
    setStatus("Saving cloud profile...");
    await fetchJson(
      `${next.apiBaseUrl.replace(/\/$/, "")}/api/viewer/chat-cleanse/preferences`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${next.token}`,
        },
        body: JSON.stringify({
          enabled: next.enabled,
          mode: next.mode,
          local_scoring_only: next.localScoringOnly,
          hide_aggression: next.hideAggression,
          hide_spam: next.hideSpam,
          hide_caps: next.hideCaps,
          aggression_threshold: next.aggressionThreshold,
          spam_threshold: next.spamThreshold,
          caps_threshold_pct: next.capsThresholdPct,
          whitelist: next.whitelist,
        }),
      },
    );
    setStatus("Cloud profile pushed.", "ok");
  } catch (error) {
    setStatus(`Push failed: ${error.message}`, "warn");
  }
}

async function saveLocal() {
  const next = readFormConfig();
  await writeConfig(next);
  render(next);
  setStatus("Local profile saved.", "ok");
}

function bindEvents() {
  el.loginBtn.addEventListener("click", () => {
    void login();
  });
  el.logoutBtn.addEventListener("click", async () => {
    const next = mergeConfig({ ...currentConfig, token: "" });
    await writeConfig(next);
    render(next);
    setStatus("Logged out.", "warn");
  });
  el.pullBtn.addEventListener("click", () => {
    void pullCloud();
  });
  el.pushBtn.addEventListener("click", () => {
    void pushCloud();
  });
  el.saveBtn.addEventListener("click", () => {
    void saveLocal();
  });

  const refresh = () => {
    render(readFormConfig());
  };
  [
    el.mode,
    el.aggressionThreshold,
    el.spamThreshold,
    el.capsThresholdPct,
    el.audioEnabled,
    el.smartLeveling,
    el.voiceBoostPct,
    el.gameTamePct,
    el.masterGainPct,
    el.latencySyncEnabled,
    el.latencySyncMs,
    el.hideAggression,
    el.hideSpam,
    el.hideCaps,
  ].forEach((node) => node.addEventListener("change", refresh));
  [
    el.aggressionThreshold,
    el.spamThreshold,
    el.capsThresholdPct,
    el.voiceBoostPct,
    el.gameTamePct,
    el.masterGainPct,
    el.latencySyncMs,
  ].forEach((node) =>
    node.addEventListener("input", refresh),
  );
}

void readConfig().then((cfg) => {
  render(cfg);
  bindEvents();
  if (cfg.token) setStatus("Token loaded. Ready to sync.", "ok");
});
