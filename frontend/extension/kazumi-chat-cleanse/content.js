const STORAGE_KEY = "kazumi_chat_cleanse_config";

const MODE_PRESETS = {
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

const CHAT_NODE_SELECTORS = [
  "div[data-a-target='chat-line-message']",
  "li[data-a-target='chat-line-message']",
  ".chat-line__message",
  "yt-live-chat-text-message-renderer",
  "yt-live-chat-paid-message-renderer",
];

const REASON_LABELS = {
  aggression: "aggression",
  spam: "spam",
  caps: "all-caps",
};

let config = { ...DEFAULT_CONFIG };
const hiddenItems = new Map();
const recentMessages = new Map();
const hiddenStats = {
  total: 0,
  reasons: { aggression: 0, spam: 0, caps: 0 },
};

let overlayRoot = null;
let overlayLine = null;
let overlayReasons = null;
let overlayToggle = null;
let hasSeenChatNode = false;
let audioContext = null;
const audioChains = new WeakMap();
const latencyDelayTimers = new WeakMap();

function clamp(value, min, max, fallback) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function mergeConfig(source) {
  const raw = source || {};
  const mode = typeof raw.mode === "string" ? raw.mode.toLowerCase().trim() : DEFAULT_CONFIG.mode;
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
      ? raw.whitelist
          .map((item) => String(item || "").trim().toLowerCase())
          .filter(Boolean)
          .slice(0, 80)
      : [],
    showHidden: raw.showHidden === true,
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

function getLatencyDelayMs(currentConfig) {
  if (!currentConfig.latencySyncEnabled) return 0;
  return Math.max(0, Math.round(Number(currentConfig.latencySyncMs || 0)));
}

function loadConfig() {
  return new Promise((resolve) => {
    chrome.storage.sync.get([STORAGE_KEY], (result) => {
      config = mergeConfig(result[STORAGE_KEY]);
      resolve(config);
    });
  });
}

function saveConfig(nextConfig) {
  config = mergeConfig(nextConfig);
  chrome.storage.sync.set({ [STORAGE_KEY]: config });
}

function normalizeText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function allCapsRatio(value) {
  const words = String(value || "").split(/\s+/).filter(Boolean);
  if (!words.length) return 0;
  const capsWords = words.filter((word) => word.length > 2 && word.toUpperCase() === word).length;
  return capsWords / words.length;
}

function aggressionScore(value) {
  const textValue = String(value || "").toLowerCase();
  const aggressive = [
    "idiot",
    "moron",
    "stupid",
    "trash",
    "garbage",
    "kill",
    "hate",
    "loser",
    "dumb",
    "pathetic",
    "shut up",
    "kys",
  ];
  let score = 0;
  for (const token of aggressive) {
    if (textValue.includes(token)) score += 1;
  }
  if (/[!?]{3,}/.test(value || "")) score += 0.5;
  return score;
}

function isHypeMessage(value) {
  const textValue = String(value || "").toLowerCase();
  return (
    textValue.includes("lets go") ||
    textValue.includes("let's go") ||
    textValue.includes("lfg") ||
    textValue.includes("pog") ||
    textValue.includes("poggers") ||
    textValue.includes("hype") ||
    textValue.includes("gg") ||
    textValue.includes("sheesh")
  );
}

function isWhitelisted(normalized, list) {
  if (!normalized) return false;
  for (const item of list) {
    if (!item) continue;
    const token = normalizeText(item);
    if (token && normalized.includes(token)) return true;
  }
  return false;
}

function getThresholds(currentConfig) {
  if (currentConfig.mode === "custom") {
    return {
      aggressionThreshold: currentConfig.aggressionThreshold,
      spamThreshold: currentConfig.spamThreshold,
      capsThresholdPct: currentConfig.capsThresholdPct,
    };
  }
  return MODE_PRESETS[currentConfig.mode] || MODE_PRESETS.balanced;
}

function registerMessageAndGetRepeatCount(normalized) {
  if (!normalized) return 1;
  const now = Date.now();
  const cutoff = now - 30000;
  const list = (recentMessages.get(normalized) || []).filter((ts) => ts >= cutoff);
  list.push(now);
  recentMessages.set(normalized, list);
  return list.length;
}

function evaluateLocal(message, normalized, repeatedCount, currentConfig) {
  if (!currentConfig.enabled || !normalized) {
    return { hide: false, reason: "", scores: {} };
  }
  if (isWhitelisted(normalized, currentConfig.whitelist)) {
    return { hide: false, reason: "", scores: {} };
  }

  const thresholds = getThresholds(currentConfig);
  const scores = {
    aggression: aggressionScore(message),
    capsRatio: allCapsRatio(message),
    repeatedCount30s: repeatedCount,
    isHype: isHypeMessage(message),
  };

  let reason = "";
  if (currentConfig.hideAggression && scores.aggression >= thresholds.aggressionThreshold) {
    reason = "aggression";
  } else if (currentConfig.hideSpam && scores.repeatedCount30s >= thresholds.spamThreshold) {
    reason = "spam";
  } else if (currentConfig.hideCaps && scores.capsRatio >= thresholds.capsThresholdPct / 100) {
    reason = "caps";
  }

  if (scores.isHype && currentConfig.mode !== "strict") {
    reason = "";
  } else if (scores.isHype && currentConfig.mode === "strict" && reason !== "spam") {
    reason = "";
  }

  return { hide: Boolean(reason), reason, scores };
}

async function evaluateRemote(message, repeatedCount, currentConfig) {
  if (!currentConfig.apiBaseUrl || !currentConfig.token) return null;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 800);
  try {
    const res = await fetch(`${currentConfig.apiBaseUrl.replace(/\/$/, "")}/api/viewer/chat-cleanse/score`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentConfig.token}`,
      },
      body: JSON.stringify({
        message,
        mode: currentConfig.mode,
        repeated_count_30s: repeatedCount,
        whitelist: currentConfig.whitelist,
      }),
      signal: controller.signal,
    });
    if (!res.ok) return null;
    const payload = await res.json();
    const reason = String(payload.reason || "");
    return {
      hide: Boolean(payload.hide),
      reason,
      scores: payload.scores || {},
    };
  } catch {
    return null;
  } finally {
    window.clearTimeout(timeout);
  }
}

async function evaluateMessage(message, normalized, repeatedCount, currentConfig) {
  const localResult = evaluateLocal(message, normalized, repeatedCount, currentConfig);
  if (currentConfig.localScoringOnly) return localResult;

  const remoteResult = await evaluateRemote(message, repeatedCount, currentConfig);
  if (!remoteResult) return localResult;

  if (isWhitelisted(normalized, currentConfig.whitelist)) {
    return { hide: false, reason: "", scores: remoteResult.scores || {} };
  }

  let reason = remoteResult.reason || "";
  if (reason === "aggression" && !currentConfig.hideAggression) reason = "";
  if (reason === "spam" && !currentConfig.hideSpam) reason = "";
  if (reason === "caps" && !currentConfig.hideCaps) reason = "";
  if (isHypeMessage(message) && currentConfig.mode !== "strict") reason = "";
  if (isHypeMessage(message) && currentConfig.mode === "strict" && reason !== "spam") reason = "";

  return { hide: Boolean(reason), reason, scores: remoteResult.scores || {} };
}

function ensureAudioContext() {
  if (!audioContext) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioContext = new Ctx();
  }
  return audioContext;
}

function createAudioChain(video) {
  const ctx = ensureAudioContext();
  if (!ctx) return null;
  try {
    const source = ctx.createMediaElementSource(video);
    const inputGain = ctx.createGain();
    const lowShelf = ctx.createBiquadFilter();
    lowShelf.type = "lowshelf";
    lowShelf.frequency.value = 220;

    const presence = ctx.createBiquadFilter();
    presence.type = "peaking";
    presence.frequency.value = 2200;
    presence.Q.value = 1.1;

    const compressor = ctx.createDynamicsCompressor();
    compressor.threshold.value = -24;
    compressor.knee.value = 20;
    compressor.ratio.value = 2.2;
    compressor.attack.value = 0.012;
    compressor.release.value = 0.24;

    const outputGain = ctx.createGain();

    source.connect(inputGain);
    inputGain.connect(lowShelf);
    lowShelf.connect(presence);
    presence.connect(compressor);
    compressor.connect(outputGain);
    outputGain.connect(ctx.destination);

    return { ctx, source, inputGain, lowShelf, presence, compressor, outputGain };
  } catch {
    return null;
  }
}

function applyAudioSettings(video, chain, currentConfig) {
  if (!video || !chain) return;
  const enabled = currentConfig.audioEnabled !== false;
  const smart = currentConfig.smartLeveling !== false;
  const voiceBoost = Math.max(80, Math.min(220, Number(currentConfig.voiceBoostPct || 120))) / 100;
  const gameTame = Math.max(0, Math.min(100, Number(currentConfig.gameTamePct || 35))) / 100;
  const master = Math.max(60, Math.min(170, Number(currentConfig.masterGainPct || 100))) / 100;

  if (!enabled) {
    chain.inputGain.gain.value = 1.0;
    chain.lowShelf.gain.value = 0;
    chain.presence.gain.value = 0;
    chain.compressor.ratio.value = 1.0;
    chain.outputGain.gain.value = 1.0;
    return;
  }

  // Voice clarity emphasis and low-frequency tame to reduce game rumble masking speech.
  chain.inputGain.gain.value = 1.0 + (voiceBoost - 1.0) * 0.12;
  chain.lowShelf.gain.value = -gameTame * 9.0;
  chain.presence.gain.value = (voiceBoost - 1.0) * 7.5;
  chain.compressor.threshold.value = smart ? -26 : -18;
  chain.compressor.ratio.value = smart ? 3.0 : 1.8;
  chain.compressor.attack.value = smart ? 0.01 : 0.02;
  chain.compressor.release.value = smart ? 0.2 : 0.3;
  chain.outputGain.gain.value = master;

  if (chain.ctx.state === "suspended") {
    const resume = () => {
      chain.ctx.resume().catch(() => {});
      window.removeEventListener("pointerdown", resume, true);
      window.removeEventListener("keydown", resume, true);
    };
    window.addEventListener("pointerdown", resume, true);
    window.addEventListener("keydown", resume, true);
  }
}

function attachAudioLeveling(video) {
  if (!video || !(video instanceof HTMLMediaElement)) return;
  if (audioChains.has(video)) {
    const chain = audioChains.get(video);
    applyAudioSettings(video, chain, config);
    return;
  }
  const chain = createAudioChain(video);
  if (!chain) return;
  audioChains.set(video, chain);
  applyAudioSettings(video, chain, config);
}

function scanAndAttachAudioLeveling() {
  document.querySelectorAll("video").forEach((video) => {
    attachAudioLeveling(video);
  });
}

function refreshAudioSettings() {
  document.querySelectorAll("video").forEach((video) => {
    const chain = audioChains.get(video);
    if (!chain) {
      attachAudioLeveling(video);
      return;
    }
    applyAudioSettings(video, chain, config);
  });
}

function ensureOverlay() {
  if (overlayRoot && document.body.contains(overlayRoot)) return;
  overlayRoot = document.createElement("div");
  overlayRoot.className = "kazumi-overlay";
  overlayRoot.innerHTML = `
    <div class="kazumi-overlay-head">
      <div class="kazumi-overlay-title">Kazumi Chat Cleanse</div>
    </div>
    <div class="kazumi-overlay-body">
      <div class="kazumi-overlay-line"></div>
      <div class="kazumi-overlay-reasons"></div>
      <div class="kazumi-overlay-actions">
        <button type="button" data-kazumi-action="toggle-show">Show hidden</button>
        <button type="button" data-kazumi-action="reset">Reset stats</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlayRoot);
  overlayLine = overlayRoot.querySelector(".kazumi-overlay-line");
  overlayReasons = overlayRoot.querySelector(".kazumi-overlay-reasons");
  overlayToggle = overlayRoot.querySelector("[data-kazumi-action='toggle-show']");

  overlayRoot.querySelector("[data-kazumi-action='toggle-show']").addEventListener("click", () => {
    saveConfig({ ...config, showHidden: !config.showHidden });
    refreshHiddenVisibility();
    updateOverlay();
  });

  overlayRoot.querySelector("[data-kazumi-action='reset']").addEventListener("click", () => {
    hiddenStats.total = 0;
    hiddenStats.reasons = { aggression: 0, spam: 0, caps: 0 };
    updateOverlay();
  });
}

function updateOverlay() {
  if (!hasSeenChatNode && hiddenStats.total === 0) return;
  ensureOverlay();
  if (!overlayLine || !overlayReasons || !overlayToggle) return;
  overlayLine.textContent = `${hiddenStats.total} hidden`;
  overlayReasons.textContent = `spam ${hiddenStats.reasons.spam} | aggression ${hiddenStats.reasons.aggression} | all-caps ${hiddenStats.reasons.caps}`;
  overlayToggle.textContent = config.showHidden ? "Hide hidden" : "Show hidden";
}

function setItemVisibility(node, item) {
  if (!node || !item) return;
  const visible = Boolean(config.showHidden || item.manualReveal);
  node.classList.remove("kazumi-chat-hidden", "kazumi-chat-show-hidden");
  if (visible) node.classList.add("kazumi-chat-show-hidden");
  else node.classList.add("kazumi-chat-hidden");
  const button = item.row.querySelector("button");
  if (button) button.textContent = item.manualReveal ? "Hide" : "Reveal";
}

function refreshHiddenVisibility() {
  for (const [node, item] of hiddenItems.entries()) {
    if (!node || !node.isConnected) {
      hiddenItems.delete(node);
      continue;
    }
    setItemVisibility(node, item);
  }
}

function collapseNode(node, reason, author, messagePreview) {
  if (!node || hiddenItems.has(node)) return;
  const row = document.createElement("div");
  row.className = "kazumi-collapse-row";
  const reasonLabel = REASON_LABELS[reason] || "filtered";
  const authorLabel = author ? `${author}: ` : "";
  const text = document.createElement("span");
  text.textContent = `Kazumi collapsed (${reasonLabel}) - ${authorLabel}${messagePreview}`;
  const toggleButton = document.createElement("button");
  toggleButton.type = "button";
  toggleButton.textContent = "Reveal";
  row.appendChild(text);
  row.appendChild(toggleButton);
  const item = { reason, row, manualReveal: false };
  toggleButton.addEventListener("click", () => {
    item.manualReveal = !item.manualReveal;
    setItemVisibility(node, item);
  });

  if (node.parentElement) {
    node.parentElement.insertBefore(row, node);
  }

  hiddenItems.set(node, item);
  setItemVisibility(node, item);
}

function extractMessageText(node) {
  if (!node) return "";
  if (node.matches("yt-live-chat-text-message-renderer, yt-live-chat-paid-message-renderer")) {
    const ytMessage = node.querySelector("#message");
    if (ytMessage && ytMessage.innerText) return ytMessage.innerText.trim();
  }

  const direct = node.querySelector("[data-a-target='chat-message-text']");
  if (direct && direct.innerText) return direct.innerText.trim();

  const fragments = node.querySelectorAll(".text-fragment");
  if (fragments.length) {
    return Array.from(fragments)
      .map((el) => el.innerText || "")
      .join(" ")
      .trim();
  }

  const body = node.querySelector("[data-test-selector='chat-line-message-body']");
  if (body && body.innerText) return body.innerText.trim();

  return (node.innerText || "").trim();
}

function extractAuthor(node) {
  const yt = node.querySelector("#author-name");
  if (yt && yt.textContent) return yt.textContent.trim();
  const twitch = node.querySelector(".chat-author__display-name, [data-a-target='chat-message-username']");
  if (twitch && twitch.textContent) return twitch.textContent.trim();
  return "";
}

function collectNodes(root) {
  const found = [];
  if (!(root instanceof Element)) return found;
  for (const selector of CHAT_NODE_SELECTORS) {
    if (root.matches(selector)) found.push(root);
    root.querySelectorAll(selector).forEach((node) => found.push(node));
  }
  return found;
}

async function processMessageNode(node) {
  if (!(node instanceof Element)) return;
  if (node.dataset.kazumiProcessed === "1") return;
  if (node.dataset.kazumiDelayPending === "1") return;

  const message = extractMessageText(node);
  const normalized = normalizeText(message);
  if (!normalized) return;

  const delayMs = getLatencyDelayMs(config);
  if (delayMs > 0 && node.dataset.kazumiDelayApplied !== "1") {
    node.dataset.kazumiDelayPending = "1";
    node.dataset.kazumiDelayApplied = "1";
    node.classList.add("kazumi-chat-delay-pending");
    const timer = window.setTimeout(() => {
      latencyDelayTimers.delete(node);
      if (!node.isConnected) return;
      delete node.dataset.kazumiDelayPending;
      node.classList.remove("kazumi-chat-delay-pending");
      void processMessageNode(node);
    }, delayMs);
    latencyDelayTimers.set(node, timer);
    return;
  }

  hasSeenChatNode = true;
  node.dataset.kazumiProcessed = "1";
  const repeatedCount = registerMessageAndGetRepeatCount(normalized);
  const result = await evaluateMessage(message, normalized, repeatedCount, config);
  if (!result.hide || !result.reason) {
    updateOverlay();
    return;
  }

  hiddenStats.total += 1;
  hiddenStats.reasons[result.reason] = (hiddenStats.reasons[result.reason] || 0) + 1;
  collapseNode(node, result.reason, extractAuthor(node), message.slice(0, 80));
  updateOverlay();
}

function processRoot(root) {
  if (root instanceof Element) {
    if (root.matches("video") || root.querySelector("video")) {
      scanAndAttachAudioLeveling();
    }
  }
  const nodes = collectNodes(root);
  for (const node of nodes) {
    void processMessageNode(node);
  }
}

function bootObserver() {
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        processRoot(node);
      });
    }
  });
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });

  processRoot(document.documentElement);
  scanAndAttachAudioLeveling();
  window.setInterval(() => processRoot(document.documentElement), 2500);
  window.setInterval(scanAndAttachAudioLeveling, 3000);
}

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName !== "sync") return;
  if (!changes[STORAGE_KEY]) return;
  config = mergeConfig(changes[STORAGE_KEY].newValue);
  refreshHiddenVisibility();
  refreshAudioSettings();
  updateOverlay();
});

void loadConfig().then(() => {
  updateOverlay();
  scanAndAttachAudioLeveling();
  bootObserver();
});
