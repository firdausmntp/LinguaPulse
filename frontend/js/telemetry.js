// ============================================================================
// TELEMETRY.JS — Sensor Keystroke Dynamics, Focus/Visibility, & Pointer Heatmap
// ============================================================================

const initialTelemetry = () => ({
  activeDurationMs: 0,
  sessionStartMs: performance.now(),
  activePresses: {},
  lastPressTime: null,
  lastReleaseTime: null,
  dwellTimes: [],
  flightTimes: [],
  interkeyTimes: [],
  totalKeydowns: 0,
  backspaceCount: 0,
  pasteCount: 0,
  bulkInsertCount: 0,
  focusLossEpisodes: 0,
  hiddenDurationMs: 0,
  lossStartMs: null,
  zoneCounts: { passage: 0, answer: 0, navigation: 0 },
  heatmapPoints: [],
  timelineEvents: [],
  lastPointerSampleMs: 0,
  answerChangeCount: 0,
  navSwitchCount: 0,
  itemResponseTimes: [],
  lastItemAnsweredMs: null
});
const telemetryState = initialTelemetry();
let telemetryActive = false;
let telemetryActivatedAt = null;

function resetTelemetry(saved) {
  Object.assign(telemetryState, initialTelemetry(), saved || {});
  telemetryState.activePresses = {};
  telemetryState.lossStartMs = null;
}

function setTelemetryActive(active) {
  if (telemetryActive && telemetryActivatedAt !== null) {
    const now = performance.now();
    telemetryState.activeDurationMs += now - telemetryActivatedAt;
    if (telemetryState.lossStartMs !== null) telemetryState.hiddenDurationMs += now - telemetryState.lossStartMs;
  }
  telemetryState.lossStartMs = null;
  telemetryState.activePresses = {};
  telemetryState.lastPressTime = null;
  telemetryState.lastReleaseTime = null;
  telemetryActive = active;
  telemetryActivatedAt = active ? performance.now() : null;
  if (active) telemetryState.sessionStartMs = performance.now() - telemetryState.activeDurationMs;
}

function getTelemetrySnapshot() {
  const now = performance.now();
  return {
    ...telemetryState, activePresses: {}, lossStartMs: null,
    activeDurationMs: telemetryState.activeDurationMs + (telemetryActive && telemetryActivatedAt !== null ? now - telemetryActivatedAt : 0),
    hiddenDurationMs: telemetryState.hiddenDurationMs + (telemetryState.lossStartMs !== null ? now - telemetryState.lossStartMs : 0)
  };
}

function logTimelineEvent(type, detail) {
  if (!telemetryActive) return;
  const elapsedSec = Math.round((performance.now() - telemetryState.sessionStartMs) / 1000);
  telemetryState.timelineEvents.push({ t: elapsedSec, type, detail });
}

function recordAnswerChange(questionId) {
  if (!telemetryActive) return;
  telemetryState.answerChangeCount += 1;
  logTimelineEvent("ANSWER_REVISION", `Revisi jawaban ke-${telemetryState.answerChangeCount} pada soal ${questionId || 'N/A'}`);
}

function recordNavSwitch(label) {
  if (!telemetryActive) return;
  telemetryState.navSwitchCount += 1;
  logTimelineEvent("NAV_SWITCH", `Navigasi ke-${telemetryState.navSwitchCount}: ${label || 'pindah soal'}`);
}

function recordItemAnswer(questionId) {
  if (!telemetryActive) return;
  const now = performance.now();
  const prev = telemetryState.lastItemAnsweredMs || telemetryState.sessionStartMs;
  const elapsedSec = Math.max(0.1, Number(((now - prev) / 1000).toFixed(2)));
  telemetryState.itemResponseTimes.push(elapsedSec);
  telemetryState.lastItemAnsweredMs = now;
  logTimelineEvent("ITEM_ANSWER", `Jawaban soal ${questionId || 'N/A'} tersimpan (${elapsedSec}s)`);
}

function calcMedian(arr) {
  if (!arr.length) return 0;
  const s = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 !== 0 ? Math.round(s[mid]) : Math.round((s[mid - 1] + s[mid]) / 2);
}

function calcEntropy() {
  const { passage, answer, navigation } = telemetryState.zoneCounts;
  const N = passage + answer + navigation;
  if (N === 0) return 0;
  let H = 0;
  [passage / N, answer / N, navigation / N].forEach((q) => {
    if (q > 0) H -= q * Math.log2(q);
  });
  return H;
}

function refreshTelemetryMeters() {
  const totalPtr =
    telemetryState.zoneCounts.passage +
    telemetryState.zoneCounts.answer +
    telemetryState.zoneCounts.navigation;

  const navEl = document.getElementById("navTelemetryText");
  if (navEl) {
    navEl.textContent =
      `Ketikan: ${telemetryState.totalKeydowns} | Fokus Hilang: ${telemetryState.focusLossEpisodes} | Pointer: ${totalPtr}`;
  }

  const liveDwellEl = document.getElementById("liveDwell");
  if (liveDwellEl) liveDwellEl.textContent = `${calcMedian(telemetryState.dwellTimes)} ms`;

  const liveFlightEl = document.getElementById("liveFlight");
  if (liveFlightEl) liveFlightEl.textContent = `${calcMedian(telemetryState.flightTimes)} ms`;

  const liveBackspaceEl = document.getElementById("liveBackspace");
  if (liveBackspaceEl) {
    const bsPct = telemetryState.totalKeydowns > 0
      ? ((telemetryState.backspaceCount / telemetryState.totalKeydowns) * 100).toFixed(1)
      : "0.0";
    liveBackspaceEl.textContent = `${bsPct}%`;
  }

  const liveEntropyEl = document.getElementById("liveEntropy");
  if (liveEntropyEl) liveEntropyEl.textContent = `${calcEntropy().toFixed(2)} bits`;
}

function initTelemetrySensors() {
  // Auto-detect profil perangkat
  const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) || window.innerWidth < 768;
  const devSelect = document.getElementById("deviceProfile");
  if (devSelect) devSelect.value = isMobile ? "MOBILE_VIRTUAL" : "PC_PHYSICAL";

  // 1. Keystroke Dynamics & InputEvent
  document.addEventListener("keydown", (e) => {
    if (!telemetryActive) return;
    if (!e.target.classList || !e.target.classList.contains("telemetry-input")) return;
    if (e.repeat) return;

    const now = performance.now();
    const keySlot = e.code || e.key || "KEY";
    telemetryState.activePresses[keySlot] = now;
    telemetryState.totalKeydowns += 1;

    if (e.key === "Backspace" || e.key === "Delete") {
      telemetryState.backspaceCount += 1;
    }

    if (telemetryState.lastPressTime !== null) {
      const iki = now - telemetryState.lastPressTime;
      if (iki >= 0 && iki <= 15000) telemetryState.interkeyTimes.push(Number(iki.toFixed(2)));
    }
    if (telemetryState.lastReleaseTime !== null) {
      const flight = now - telemetryState.lastReleaseTime;
      if (flight >= -500 && flight <= 15000) telemetryState.flightTimes.push(Number(flight.toFixed(2)));
    }
    telemetryState.lastPressTime = now;
    refreshTelemetryMeters();
  });

  document.addEventListener("keyup", (e) => {
    if (!telemetryActive) return;
    if (!e.target.classList || !e.target.classList.contains("telemetry-input")) return;
    const now = performance.now();
    const keySlot = e.code || e.key || "KEY";
    const pTime = telemetryState.activePresses[keySlot];
    if (pTime !== undefined) {
      const dwell = now - pTime;
      if (dwell >= 0 && dwell <= 5000) telemetryState.dwellTimes.push(Number(dwell.toFixed(2)));
      delete telemetryState.activePresses[keySlot];
    }
    telemetryState.lastReleaseTime = now;
    refreshTelemetryMeters();
  });

  document.addEventListener("input", (e) => {
    if (!telemetryActive) return;
    if (!e.target.classList || !e.target.classList.contains("telemetry-input")) return;
    const inputType = e.inputType || "";
    const insertedLen = e.data ? e.data.length : 0;
    if (inputType === "insertFromPaste" || insertedLen > 12) {
      telemetryState.bulkInsertCount += 1;
      logTimelineEvent("BULK_INPUT", `InputEvent: ${inputType || "multi-char"}`);
    }
    if (e.target.id === "essayEditor") {
      const text = e.target.value.trim();
      const words = text ? text.split(/\s+/).length : 0;
      document.getElementById("essayWordCounter").textContent = `${words} kata`;
      appState.selectedAnswers[e.target.dataset.answer || "W1"] = e.target.value;
    }
  });

  document.addEventListener("paste", (e) => {
    if (!telemetryActive) return;
    if (!e.target.classList || !e.target.classList.contains("telemetry-input")) return;
    telemetryState.pasteCount += 1;
    logTimelineEvent("PASTE_EVENT", `Tindakan tempel ke-${telemetryState.pasteCount} (isi clipboard tidak disimpan)`);
    refreshTelemetryMeters();
  });

  // 2. Focus & Page Visibility API
  const startFocusLoss = (reason) => {
    if (!telemetryActive) return;
    if (telemetryState.lossStartMs === null) {
      telemetryState.lossStartMs = performance.now();
      telemetryState.focusLossEpisodes += 1;
      logTimelineEvent("FOCUS_LOSS", `Kehilangan fokus (${reason}) ke-${telemetryState.focusLossEpisodes}`);
      refreshTelemetryMeters();
    }
  };

  const endFocusLoss = () => {
    if (!telemetryActive) return;
    if (telemetryState.lossStartMs !== null) {
      const delta = performance.now() - telemetryState.lossStartMs;
      telemetryState.hiddenDurationMs += delta;
      telemetryState.lossStartMs = null;
      logTimelineEvent("FOCUS_RETURN", `Kembali ke halaman setelah ${(delta / 1000).toFixed(1)}s`);
      refreshTelemetryMeters();
    }
  };

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") startFocusLoss("tab_hidden");
    else endFocusLoss();
  });
  window.addEventListener("blur", () => startFocusLoss("window_blur"));
  window.addEventListener("focus", () => endFocusLoss());

  // 3. Pointer Events Heatmap (Hanya aktif saat di halaman ujian)
  const recordPointer = (e, isClick = false) => {
    // Sensor pointer hanya aktif saat pengguna berada di halaman ujian
    const examView = document.getElementById("viewExam");
    if (!telemetryActive || !examView || examView.classList.contains("hidden")) {
      return;
    }

    const now = performance.now();
    if (!isClick && now - telemetryState.lastPointerSampleMs < 120) return;
    telemetryState.lastPointerSampleMs = now;

    const zoneEl = e.target.closest("[data-zone]");
    const zoneName = zoneEl ? zoneEl.getAttribute("data-zone") : "answer";
    if (telemetryState.zoneCounts[zoneName] !== undefined) {
      telemetryState.zoneCounts[zoneName] += 1;
    }

    const normX = Number((e.clientX / Math.max(1, window.innerWidth)).toFixed(3));
    const normY = Number((e.clientY / Math.max(1, window.innerHeight)).toFixed(3));
    telemetryState.heatmapPoints.push({ x: normX, y: normY, zone: zoneName });
    if (telemetryState.heatmapPoints.length > 300) telemetryState.heatmapPoints.shift();
    refreshTelemetryMeters();
  };

  window.addEventListener("pointerdown", (e) => recordPointer(e, true));
  window.addEventListener("pointermove", (e) => recordPointer(e, false));
}

