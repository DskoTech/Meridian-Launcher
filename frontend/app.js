/* Meridian frontend — keyboard, mouse, and controller driven cross-bar UI.
 *
 * Navigation model (true "Xross Media Bar" style): the category row is
 * always live. Left/Right always changes the highlighted category, which
 * immediately refreshes the list shown below it. Up/Down always browses
 * the list currently shown. Confirm activates whatever is selected.
 *
 * Once you move past Apps, the category row becomes a circular carousel:
 * whichever category is highlighted slides into Apps' slot, and anything
 * that scrolls off the left loops back around to the right, behind System.
 */

const ICONS = {
  music: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/></svg>`,
  photos: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5.5-5.5L9 17"/></svg>`,
  videos: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="14" height="14" rx="2"/><path d="M17 9l4-2v10l-4-2"/></svg>`,
  apps: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>`,
  games: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="2" y="8" width="20" height="9" rx="4"/><path d="M7 10.5v4M5 12.5h4"/><circle cx="16" cy="11" r="1"/><circle cx="18.5" cy="13.5" r="1"/></svg>`,
  emulators: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="6" y="6" width="12" height="12" rx="1.5"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></svg>`,
  chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12a8 8 0 01-11.5 7.2L4 20l1-4.8A8 8 0 1121 12z"/></svg>`,
  streaming: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M10 9l5 3-5 3z" fill="currentColor" stroke="none"/></svg>`,
  web: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/></svg>`,
  files: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>`,
  system: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v8"/><path d="M6.3 6.3a9 9 0 1011.4 0"/></svg>`,
  macros: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M13 2L4 14h6l-1 8 9-12h-6z"/></svg>`,
  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.34 1.87l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.7 1.7 0 00-1.87-.34 1.7 1.7 0 00-1 1.56V21a2 2 0 11-4 0v-.09a1.7 1.7 0 00-1-1.56 1.7 1.7 0 00-1.87.34l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.7 1.7 0 00.34-1.87 1.7 1.7 0 00-1.56-1H3a2 2 0 110-4h.09a1.7 1.7 0 001.56-1 1.7 1.7 0 00-.34-1.87l-.06-.06a2 2 0 112.83-2.83l.06.06a1.7 1.7 0 001.87.34H9a1.7 1.7 0 001-1.56V3a2 2 0 114 0v.09a1.7 1.7 0 001 1.56 1.7 1.7 0 001.87-.34l.06-.06a2 2 0 112.83 2.83l-.06.06a1.7 1.7 0 00-.34 1.87V9a1.7 1.7 0 001.56 1H21a2 2 0 110 4h-.09a1.7 1.7 0 00-1.56 1z"/></svg>`,
  generic: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>`,
  archive: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 3v3M12 9v2M12 14v2"/><circle cx="12" cy="17" r="1.4" fill="currentColor" stroke="none"/></svg>`,
  document: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2h9l4 4v16H6z"/><path d="M15 2v4h4M8 12h8M8 16h8M8 8h3"/></svg>`,
  run: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M9 9l4 3-4 3z" fill="currentColor" stroke="none"/></svg>`,
  desktop: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M8 20h8M12 16v4"/></svg>`,
  explorer: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><path d="M9 13l2 2 4-4"/></svg>`,
  browser: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.5 6 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-6-3.5-9s1-6.5 3.5-9z"/></svg>`,
  power: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v8"/><path d="M6.3 6.3a9 9 0 1011.4 0"/></svg>`,
  sleep: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/></svg>`,
  hibernate: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2v20M2 12h20M5 5l14 14M19 5L5 19"/></svg>`,
  close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 6l12 12M18 6L6 18"/></svg>`,
  controlpanel: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="9" cy="6" r="1.6" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="10" cy="18" r="1.6" fill="currentColor" stroke="none"/></svg>`,
  taskmanager: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9h4M7 13h10M7 17h6"/></svg>`,
  bat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2h9l3 3v17H6z"/><path d="M10 10h4M10 14h4"/></svg>`,
  recyclebin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M6 7l1 13a2 2 0 002 2h6a2 2 0 002-2l1-13"/><path d="M10 11v6M14 11v6"/></svg>`,
  uninstallapps: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M15 17l5 5M20 17l-5 5"/></svg>`,
  commandprompt: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l4 3-4 3M13 15h4"/></svg>`,
  powershell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8l5 4-5 4M13 16h5"/></svg>`,
  msstore: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/></svg>`,
  windowsupdate: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 12a8 8 0 0114-5.3M20 12a8 8 0 01-14 5.3"/><path d="M18 3v4h-4M6 21v-4h4"/></svg>`,
  wifi: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 8.5a16 16 0 0120 0M5.5 12a11 11 0 0113 0M9 15.5a6 6 0 016 0"/><circle cx="12" cy="19" r="1.2" fill="currentColor" stroke="none"/></svg>`,
  bluetooth: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7l10 10-5 5V2l5 5L7 17"/></svg>`,
  audio: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 10v4h4l5 5V5L8 10H4z"/><path d="M17 8a5 5 0 010 8M19.5 5.5a9 9 0 010 13"/></svg>`,
};

const PALETTE = ["#60a5fa", "#f472b6", "#34d399", "#fb923c", "#e879f9", "#facc15", "#c084fc", "#38bdf8"];

// Note: Settings and System are appended in buildCategories(), in that
// order, so System always sits after Settings as the very last category.
// The five Settings options, shown as a list inside the Settings section
// (not as their own sections in the sections bar). Picking one renders just
// that group's blocks; B/back returns to this list.
const SETTINGS_OPTIONS = [
  ["controls", "Controls", "Controller reference and input status"],
  ["sections", "Sections", "Media folders, custom sections, display styles"],
  ["plugins", "Plugins", "Discovered Plugins/ folders, visibility, rescan"],
  ["themes", "Themes", "Window mode, layouts, colors, backgrounds"],
  ["addons", "Addon Settings", "Custom settings from plugins, plug-ons, and themes"],
  ["program", "Program", "App behavior, updates, factory reset"],
  ["about", "About", "Credits"],
];

const FIXED_CATEGORIES = [
  { id: "music", label: "Music", kind: "media", color: "var(--accent-music)" },
  { id: "photos", label: "Photos", kind: "media", color: "var(--accent-photos)" },
  { id: "videos", label: "Videos", kind: "media", color: "var(--accent-videos)" },
  { id: "apps", label: "Apps", kind: "exe_list", color: "var(--accent-apps)" },
  { id: "games", label: "Games", kind: "exe_list", color: "var(--accent-games)" },
  { id: "emulators", label: "Emulators", kind: "exe_list", color: "var(--accent-emulators)" },
  { id: "chat", label: "Chat", kind: "exe_list", color: "var(--accent-chat)" },
  { id: "streaming", label: "Streaming", kind: "exe_list", color: "var(--accent-streaming)" },
  { id: "web", label: "Web", kind: "web_list", color: "var(--accent-web)" },
  { id: "files", label: "Files", kind: "file_list", color: "var(--accent-files)" },
  { id: "macros", label: "Macros", kind: "macro_list", color: "var(--accent-macros)" },
];

// Web: CyberDeck Browser first, Default Browser second.
const WEB_ITEMS = [
  { id: "cyberdeck", label: "CyberDeck Browser", icon: "web" },
  { id: "default_browser", label: "Default Browser", icon: "web" },
];

// Files: Meridian Explorer first, Windows File Explorer second.
const FILE_ITEMS = [
  { id: "meridian_explorer", label: "Meridian Explorer", icon: "files" },
  { id: "windows_explorer", label: "Windows File Explorer", icon: "files" },
];

// Games: a permanent "Game Library" entry always sits at the top of the list.
const GAME_LIBRARY_ITEM = { __gameLibrary: true, name: "Game Library" };

// Safe-first: a stray confirm press lands on something harmless (Task
// Manager), not something destructive (Shut Down is last).
const SYSTEM_ITEMS = [
  { id: "close", label: "Close Program", icon: "close" },
  { id: "sleep", label: "Sleep", icon: "sleep" },
  { id: "hibernate", label: "Hibernate", icon: "hibernate" },
  { id: "shutdown", label: "Shut Down", icon: "power" },
  { id: "restart", label: "Restart", icon: "restart" },
  { id: "taskmanager", label: "Task Manager", icon: "taskmanager" },
  { id: "controlpanel", label: "Control Panel", icon: "controlpanel" },
  { id: "recyclebin", label: "Recycle Bin", icon: "recyclebin" },
  { id: "uninstallapps", label: "Uninstall Apps", icon: "uninstallapps" },
  { id: "commandprompt", label: "Command Prompt", icon: "commandprompt" },
  { id: "powershell", label: "Windows PowerShell", icon: "powershell" },
  { id: "msstore", label: "Microsoft Store", icon: "msstore" },
  { id: "windowsupdate", label: "Windows Update", icon: "windowsupdate" },
  { id: "wifi", label: "Wi-Fi", icon: "wifi" },
  { id: "bluetooth", label: "Bluetooth", icon: "bluetooth" },
  { id: "audio", label: "Audio Output", icon: "audio" },
];

// Carousel pivots at Apps (index 3): categories at/before it render in a
// fixed, normal left-to-right row; past it, the row becomes circular with
// the current category always sliding into Apps' slot.
const CAROUSEL_ANCHOR = 3;

const state = {
  categories: [],
  catIndex: 0,
  chatOptions: [], // [{id, label}] enabled option-type plugins targeting the Chat section
  chatPluginActive: null, // pluginId currently boxed from within the Chat list, if any
  sectionManuallyClosed: false, // true after "Close Section" from the Start menu, until any section is re-opened
  items: [],
  selected: 0,
  settings: null,
  playIndex: -1,
  musicQueue: [], // persistent Music queue for shoulder controls across sections
  musicRandomOrder: null, // cached shuffled path order for the persisted Random sort mode - see sortMusicItems
  userThemes: [], // discovered themes from the themes/ folder
  userThemeCss: {}, // { __active: slug } tracks which user theme CSS is injected
  musicIndex: 0,
  keyboardControls: null,
  introDismissed: false,
  folderStack: { music: [], photos: [], videos: [] }, // subfolder browsing, per kind
  mediaFocus: "list", // "list" | "folders" — which column has left/right/up/down focus in Music/Photos/Videos
  folderEntries: [], // flattened navigable sidebar rows for the current media category
  folderCursor: 0,
  settingsCursor: 0, // controller/keyboard cursor over Settings focusable controls
  settingsGroup: "menu", // "menu" = the option list, else which group is open
  settingsMenuIndex: 0, // cursor over the five Settings options
  colorGridIndex: null, // 2D sub-cursor into the theme color grid (null = not in grid)
  radialFocus: "sections", // "sections" | "options" | "subfolder" — CyberRadial layout only
  sectionsBrowseIndex: 0, // NightHorizon/CyberRadial: which section is highlighted while browsing, may differ from catIndex (the actually-loaded one) until confirmed
};

const el = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------------- clock & battery ----------------

function tickClock() {
  el("clock").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
setInterval(tickClock, 15000);

async function updateBatteryIndicator() {
  const ind = el("battery-indicator");
  const settings = state.settings;
  if (!settings || !settings.battery_indicator) { ind.classList.add("hidden"); return; }
  let status = await api().get_battery_status();
  if (!status) status = { percent: 100, plugged: true }; // desktop with no battery hardware — show full
  ind.classList.remove("hidden");
  el("battery-pct").textContent = `${status.percent}%`;
  ind.classList.toggle("charging", !!status.plugged);
  ind.classList.toggle("low", !status.plugged && status.percent <= 20);
  const fillWidth = Math.max(1, Math.round((status.percent / 100) * 18));
  el("battery-fill").setAttribute("width", String(fillWidth));
}
setInterval(updateBatteryIndicator, 30000);

// ---------------- category list (fixed + custom + settings + system) ----------------

async function loadChatOptions() {
  try {
    state.chatOptions = (await api().list_section_options("chat")) || [];
  } catch (e) {
    state.chatOptions = [];
  }
}

function buildCategories(settings) {
  const custom = (settings.custom_sections || []).map((cs, i) => ({
    id: cs.id, label: cs.label, kind: "exe_list", color: PALETTE[i % PALETTE.length],
  }));
  // Plugins: auto-discovered Plugins/ folders, appended after the last
  // manually-added custom section. Hidden by default; a plugin only
  // shows up here once enabled from Settings > Plugins.
  //
  // Special case: the "start" plugin (Windows Start Menu list) always
  // rides right after Desktop instead of here, when Desktop is enabled —
  // it's pulled out of this generic list and inserted directly into
  // afterDesktop below. When Desktop is off, "right after Desktop" is
  // moot, so it stays in its normal spot here instead of vanishing.
  const pluginToCategory = ([pid, p], i) => ({
    id: `plugin:${pid}`, pluginId: pid, label: p.label,
    kind: p.type === "webapp" ? "plugin_webapp" : "plugin_list",
    color: PALETTE[(custom.length + i) % PALETTE.length],
  });
  const visiblePluginEntries = Object.entries(settings.plugins || {})
    .filter(([, p]) => p.visible && p.type !== "option" && p.type !== "addon");
  const startEntry = visiblePluginEntries.find(([pid]) => pid === "start");
  const pinStartAfterDesktop = !!(startEntry && settings.desktop_section_enabled);
  const plugins = visiblePluginEntries
    .filter(([pid]) => !(pinStartAfterDesktop && pid === "start"))
    .map(pluginToCategory);
  const hiddenBuiltins = new Set(settings.hidden_builtin_sections || []);
  const visibleFixed = FIXED_CATEGORIES.filter((c) => !hiddenBuiltins.has(c.id));
  const base = [...visibleFixed, ...custom, ...plugins];
  // Kiosk mode hides Settings and System entirely — the only ways back out
  // are the secret code, a 45s Y hold, or hand-editing settings.json.
  const withSystem = settings.window_mode === "kiosk" ? base : [
    ...base,
    { id: "settings", label: "Settings", kind: "settings", color: "var(--accent-settings)" },
    { id: "system", label: "System", kind: "system_list", color: "var(--accent-system)" },
  ];
  // Desktop: auto-populated from the user's actual Desktop folder, off by
  // default (Settings toggle), always first in the list when it's on.
  if (!settings.desktop_section_enabled) return withSystem;
  const desktopCat = { id: "desktop", label: "Desktop", kind: "desktop_list", color: "var(--accent-desktop)" };
  const afterDesktop = [];
  if (pinStartAfterDesktop) afterDesktop.push(pluginToCategory(startEntry, 0));
  if (settings.browser_section_enabled) {
    afterDesktop.push({ id: "browser", label: "Browser", kind: "browser_section", color: "var(--accent-web)" });
  }
  return [desktopCat, ...afterDesktop, ...withSystem];
}

function iconFor(catId) {
  return ICONS[catId] || ICONS.generic;
}

// ---------------- category row: circular carousel with FLIP sliding ----------------

const categoryElements = new Map(); // id -> persistent DOM node, so transitions can animate

// Which index should visually drive the carousel/highlight right now: the
// browse cursor while the user is scrubbing through sections pre-confirm
// (NightHorizon/CyberRadial), or simply the loaded section otherwise.
function currentHighlightIndex() {
  return (state.radialFocus === "sections" && usesConfirmToLoadSections()) ? state.sectionsBrowseIndex : state.catIndex;
}

function computeDisplayOrder() {
  const n = state.categories.length;
  const anchor = currentHighlightIndex();
  const start = anchor <= CAROUSEL_ANCHOR ? 0 : anchor - CAROUSEL_ANCHOR;
  const order = [];
  for (let i = 0; i < n; i++) order.push((start + i) % n);
  return order;
}

function ensureCategoryElement(cat) {
  let wrap = categoryElements.get(cat.id);
  if (!wrap) {
    wrap = document.createElement("div");
    wrap.className = "category";
    wrap.addEventListener("click", () => {
      const idx = state.categories.findIndex((c) => c.id === cat.id);
      if (idx === -1) return;
      // A mouse click is a direct commit (unlike keyboard/controller
      // browsing, where confirm is a separate step) - open straight to
      // "options" so an embedded plugin measures the panel's final
      // position, not its still-hidden "sections" position.
      selectCategory(idx, true);
    });
    categoryElements.set(cat.id, wrap);
  }
  wrap.style.setProperty("--cat-color", cat.color);
  // Stable logical position (index into state.categories, by id) rather
  // than DOM position — the category row only mounts a moving window of
  // elements for the carousel, so nth-of-type-based theme styling (color
  // cycling per section) drifts/repeats unpredictably as that window
  // slides. Themes that want a stable per-section value (Factory Central's
  // icon/label color cycling) can key off this instead.
  const stableIdx = state.categories.findIndex((c) => c.id === cat.id);
  wrap.style.setProperty("--cat-idx", String(stableIdx === -1 ? 0 : stableIdx));
  wrap.innerHTML = `<div class="icon-ring">${iconFor(cat.id)}</div><div class="label">${escapeHtml(cat.label)}</div>`;
  return wrap;
}

function renderCategories() {
  const row = el("category-row");

  // drop persistent elements for categories that no longer exist (e.g. a removed custom section)
  const currentIds = new Set(state.categories.map((c) => c.id));
  for (const id of [...categoryElements.keys()]) {
    if (!currentIds.has(id)) categoryElements.delete(id);
  }

  const order = computeDisplayOrder();
  const highlightIdx = currentHighlightIndex();

  // FLIP part 1: record where each visible element currently sits
  const oldRects = new Map();
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const existing = categoryElements.get(cat.id);
    if (existing && existing.parentElement === row) oldRects.set(cat.id, existing.getBoundingClientRect());
  });

  // Rebuild in the new circular order (existing nodes are moved, not recreated)
  const frag = document.createDocumentFragment();
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const wrap = ensureCategoryElement(cat);
    wrap.classList.toggle("active", realIdx === highlightIdx);
    wrap.classList.toggle("pending-confirm", realIdx === highlightIdx && highlightIdx !== state.catIndex);
    frag.appendChild(wrap);
  });
  row.innerHTML = "";
  row.appendChild(frag);

  // CyberRadial: the active category is always pinned to angle 0 (the
  // fixed point straight out from the hub's center, pill pointing back in)
  // — not a moving highlight on a static arc. Everything else's angle is
  // just "how many positions away from active", so moving up/down rotates
  // neighbors into that fixed spot rather than moving a cursor along a
  // fixed ring. Harmless no-op in NightHorizon (angle unused there).
  const activePos = order.indexOf(highlightIdx);
  // Themes can opt into a full 360° ring (instead of the default ±90° arc)
  // by setting `--orbit-full: 1`. Factory Central uses this to spread the
  // sections evenly around a gear. Read from computed style so a user
  // theme's CSS can drive it without any JS of its own.
  let orbitFull = false;
  try {
    orbitFull = getComputedStyle(document.body).getPropertyValue("--orbit-full").trim() === "1";
  } catch (e) { orbitFull = false; }
  const ORBIT_STEP_DEG = 20;
  const ORBIT_FADE_RANGE = 5; // matches where clamping kicks in (90/20=4.5) so nothing visible ever shares a clamped angle
  order.forEach((realIdx, i) => {
    const cat = state.categories[realIdx];
    const elx = categoryElements.get(cat.id);
    const offset = i - activePos;
    let angle, fade;
    if (orbitFull) {
      // even spread around the whole circle; active stays pinned at 0°
      const step = 360 / Math.max(1, order.length);
      angle = offset * step;
      fade = 1; // nothing is "off the end" of a closed ring
    } else {
      angle = Math.max(-90, Math.min(90, offset * ORBIT_STEP_DEG));
      fade = Math.max(0, 1 - Math.abs(offset) / ORBIT_FADE_RANGE);
    }
    elx.style.setProperty("--orbit-angle", angle + "deg");
    elx.style.setProperty("--orbit-fade", fade.toFixed(3));
  });

  // FLIP part 2: animate from the old position to the new one. CyberRadial
  // positions categories via CSS left/top (transitioned in the stylesheet)
  // driven by --orbit-angle, so this transform-based trick is skipped there
  // — setting an inline transform would just clobber the orbit's own
  // translate(-50%,-50%) positioning transform.
  if (isCyberRadial()) return;
  order.forEach((realIdx) => {
    const cat = state.categories[realIdx];
    const elx = categoryElements.get(cat.id);
    const oldRect = oldRects.get(cat.id);
    if (!oldRect) { elx.style.transition = ""; elx.style.transform = ""; return; }
    const newRect = elx.getBoundingClientRect();
    const dx = oldRect.left - newRect.left;
    const dy = oldRect.top - newRect.top;
    if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
      elx.style.transition = "none";
      elx.style.transform = `translate(${dx}px, ${dy}px)`;
      requestAnimationFrame(() => {
        elx.style.transition = "transform 320ms ease";
        elx.style.transform = "translate(0, 0)";
      });
    } else {
      elx.style.transition = "";
      elx.style.transform = "";
    }
  });
}

// Keep the currently-highlighted category icon horizontally aligned with
// the icon column of whatever list is showing below it, regardless of
// section (measured live rather than hand-tuned, so it stays correct even
// as row/list content varies).
function alignCategoryRowToList() {
  // Left/right no longer changes which category is selected in either
  // layout (that's up/down now), so "line up the active icon with the
  // list's icon column on left/right" no longer applies. Kept as a no-op
  // rather than removing every call site.
  const row = el("category-row");
  row.style.transform = "";
}

function applyAccent() {
  document.documentElement.style.setProperty("--active-accent", state.categories[state.catIndex].color);
  applyLayoutClass();
  const cat = state.categories[state.catIndex] || {};
  document.body.dataset.activeCat = cat.id || "";
  document.body.dataset.displayType = getDisplayType(cat.id);
}

// "List Style" (default) vs "Gallery Style" — a generic per-section toggle
// (Settings > each section's own block), not just hardcoded for Games.
// Games defaults to gallery to match how it's always looked; everything
// else defaults to list. Purely a rendering concern: same items, same
// state, just a different CSS shape driven by body[data-display-type].
function getDisplayType(catId) {
  const map = (state.settings && state.settings.display_type) || {};
  return map[catId] || "list";
}

// Layout mode: "night_horizon" (default) is the vertical hub/orbit sidebar
// look; "cyber_radial" rearranges the same DOM into the orbital-arc variant.
// Purely a CSS concern driven by one body class — see style.css.
// A user custom theme is any layout value starting with "user-"; it renders
// on top of a chosen built-in base (see user_themes.py). We look it up in
// the cached list discovered from the themes/ folder.
function currentUserTheme() {
  const layout = state.settings && state.settings.layout;
  if (!layout || !layout.startsWith("user-")) return null;
  const slug = layout.slice("user-".length);
  return (state.userThemes || []).find((t) => t.slug === slug) || null;
}
function userThemeBase() {
  const t = currentUserTheme();
  return t ? t.base : null;
}

function isCyberRadial() {
  const base = userThemeBase();
  if (base) return base === "cyber_radial";
  return !!(state.settings && state.settings.layout === "cyber_radial");
}
function isDawningHorizon() {
  const base = userThemeBase();
  if (base) return base === "dawning_horizon";
  return !!(state.settings && (state.settings.layout === "dawning_horizon" || !state.settings.layout));
}
// NightHorizon and CyberRadial both require an explicit confirm to actually
// load a highlighted section; Dawning Horizon keeps the original "whatever's
// highlighted is already loaded" behavior.
function usesConfirmToLoadSections() {
  return true; // universal now — all three layouts share this nav model, differing only visually
}
// ---------------- Dawning Horizon: primary theme color ----------------
// "original" leaves the stylesheet's values alone. Anything else is
// "<palette>:<hue>": the background is re-tinted to that hue in that
// palette's saturation/lightness, and the per-section accents are
// reassigned as a ROYGBIV rainbow rotated to start at the background's
// complement — so the sections always read against the background rather
// than dissolving into it. All computed here and applied as inline CSS
// custom properties on <body>, which out-specifies the
// body.layout-dawninghorizon class block without touching the stylesheet.

const DAWNING_HUES = [
  ["red", 0], ["orange", 28], ["yellow", 52], ["green", 125],
  ["blue", 215], ["indigo", 255], ["violet", 285],
];

// Per-palette recipe: background stops, accent chroma, and whether the
// background is light enough to need dark text swapped in.
const DAWNING_PALETTES = {
  light:     { bg0: [40, 90], bg1: [46, 82], accent: [72, 38], lightBg: true },
  dark:      { bg0: [55, 6],  bg1: [50, 13], accent: [78, 64], lightBg: false },
  neon:      { bg0: [95, 5],  bg1: [100, 15], accent: [100, 60], lightBg: false },
  primary:   { bg0: [85, 26], bg1: [92, 40], accent: [95, 68], lightBg: false },
  pastel:    { bg0: [55, 91], bg1: [60, 84], accent: [52, 48], lightBg: true },
  bubblegum: { bg0: [82, 80], bg1: [90, 70], accent: [88, 42], lightBg: true },
};

// Derive an HSL hue (0-360) and a light/dark hint from a #rrggbb string,
// so a custom grid-picked color can drive the same hue-based engine as the
// named palettes.
function hexToHue(hex) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  let hue = 0;
  if (d !== 0) {
    if (max === r) hue = ((g - b) / d) % 6;
    else if (max === g) hue = (b - r) / d + 2;
    else hue = (r - g) / d + 4;
    hue *= 60;
    if (hue < 0) hue += 360;
  }
  const light = (max + min) / 2;
  return { hue, light };
}


function hslToHex(h, sPct, lPct) {
  const sN = sPct / 100, lN = lPct / 100;
  const c = (1 - Math.abs(2 * lN - 1)) * sN;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = lN - c / 2;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return "#" + [r, g, b].map((v) => Math.round((v + m) * 255).toString(16).padStart(2, "0")).join("");
}

function parseDawningThemeColor(settings) {
  const raw = (settings && settings.dawning_theme_color) || "original";
  if (raw === "original") return null;
  const [palette, hueName] = raw.split(":");
  if (palette === "hex") {
    // Custom color from the mspaint-style grid. Build a palette on the fly
    // from its hue, leaning light or dark to match the picked color.
    const { hue, light } = hexToHue(hueName);
    const isLight = light > 0.6;
    const pal = isLight
      ? { bg0: [55, 88], bg1: [60, 80], accent: [60, 44], lightBg: true }
      : { bg0: [80, 16], bg1: [88, 26], accent: [90, 62], lightBg: false };
    return { palette: pal, hue };
  }
  const pal = DAWNING_PALETTES[palette];
  const hueEntry = DAWNING_HUES.find(([name]) => name === hueName);
  if (!pal || !hueEntry) return null;
  return { palette: pal, hue: hueEntry[1] };
}

function applyDawningThemeColor(settings) {
  const body = document.body;
  const clear = () => {
    ["--bg-0", "--bg-1", "--text-hi", "--text-lo", "--panel", "--line"].forEach((v) => body.style.removeProperty(v));
    DAWNING_ACCENT_VARS.forEach((name) => body.style.removeProperty(`--accent-${name}`));
  };
  const theme = isDawningHorizon() ? parseDawningThemeColor(settings) : null;
  if (!theme) { clear(); return; }

  const { palette: pal, hue } = theme;
  const hsl = (h, s, l) => `hsl(${((h % 360) + 360) % 360}, ${s}%, ${l}%)`;
  body.style.setProperty("--bg-0", hsl(hue, pal.bg0[0], pal.bg0[1]));
  body.style.setProperty("--bg-1", hsl(hue, pal.bg1[0], pal.bg1[1]));

  // Light backgrounds need the text/panel/hairline colors flipped too, or
  // the original light-on-dark text vanishes.
  if (pal.lightBg) {
    body.style.setProperty("--text-hi", hsl(hue, 30, 12));
    body.style.setProperty("--text-lo", hsl(hue, 18, 34));
    body.style.setProperty("--panel", "rgba(255, 255, 255, 0.55)");
    body.style.setProperty("--line", "rgba(15, 23, 42, 0.18)");
  }

  // ROYGBIV accents, rotated so the rainbow starts at the background's
  // complementary hue and cycles from there.
  const shift = hue + 180 - DAWNING_HUES[0][1];
  DAWNING_ACCENT_VARS.forEach((name, i) => {
    const base = DAWNING_HUES[i % DAWNING_HUES.length][1];
    body.style.setProperty(`--accent-${name}`, hsl(base + shift, pal.accent[0], pal.accent[1]));
  });
}

// Every per-section accent variable the Dawning stylesheet defines, in the
// order they get rainbow hues. --active-accent itself follows whichever of
// these the selected category points at, so it needs no direct handling.
const DAWNING_ACCENT_VARS = [
  "music", "photos", "videos", "apps", "games", "emulators", "chat",
  "streaming", "web", "files", "system", "macros", "settings", "desktop",
];

// Toggle the body class for the active user theme (layout-user-<slug>) and
// make sure its CSS is present in a <style id="user-theme-css"> element.
// Only one user theme is active at a time; clear the class/CSS otherwise.
function applyUserThemeClass() {
  const t = currentUserTheme();
  // clear any previously-applied user-theme body classes
  Array.prototype.slice.call(document.body.classList)
    .filter((c) => c.indexOf("layout-user-") === 0)
    .forEach((c) => document.body.classList.remove(c));
  const styleEl = ensureUserThemeStyleEl();
  if (!t) { styleEl.textContent = ""; return; }
  document.body.classList.add("layout-user-" + t.slug);
  // Inject the theme CSS if we haven't already for this slug this session.
  if (state.userThemeCss.__active !== t.slug) {
    // fetch fresh from backend so edits to the .css are picked up on switch
    api().get_user_theme_css(state.settings.layout).then((res) => {
      styleEl.textContent = (res && res.css) || t.css || "";
      state.userThemeCss.__active = t.slug;
    }).catch(() => { styleEl.textContent = t.css || ""; });
  }
}
function ensureUserThemeStyleEl() {
  let el2 = document.getElementById("user-theme-css");
  if (!el2) {
    el2 = document.createElement("style");
    el2.id = "user-theme-css";
    document.head.appendChild(el2);
  }
  return el2;
}
async function loadUserThemes() {
  try {
    state.userThemes = (await api().list_user_themes()) || [];
  } catch (e) {
    state.userThemes = [];
  }
}

function applyLayoutClass() {
  // Built-in base classes are driven by isCyberRadial()/isDawningHorizon(),
  // which already resolve a user theme's chosen base. On top of that we add
  // the user theme's own class and inject its stylesheet.
  document.body.classList.toggle("layout-cyberradial", isCyberRadial());
  document.body.classList.toggle("layout-dawninghorizon", isDawningHorizon());
  document.body.classList.toggle("layout-nighthorizon", !isCyberRadial() && !isDawningHorizon());
  applyUserThemeClass();
  applyDawningThemeColor(state.settings);
  applyTaskbarPlacement();
  syncSubfolderNavWidth();
  applyIconSize();
  if (state.categories && state.categories.length) renderCategories();
  // theme changed -> its own background & overlay apply
  if (state.settings) { applyBackground(state.settings); applyOverlay(state.settings); }
}

// List icon size (small = classic, then medium/large/xl at 2x each): a
// body class drives a CSS variable; row heights grow with the icon since
// the rows size to their content.

function applyIconSize() {
  const size = (state.settings && state.settings.icon_size) || "small";
  document.body.classList.remove("icon-size-medium", "icon-size-large", "icon-size-xl");
  if (size !== "small") document.body.classList.add(`icon-size-${size}`);
}

// ---------------- category selection (always live, no separate "enter" step) ----------------

// Shared by every path that can change state.catIndex: makes sure any
// boxed Meridian FileBrowse/NetBrowse instance (a dedicated Explorer/
// Browser/webapp section, OR one launched as a Chat-section option) is
// actually terminated rather than left running invisibly in the
// background, whenever the destination isn't the category it's tied to.
// Previously only selectCategory did this — goToSettingsFor,
// refreshAfterSettingsChange, and refreshCategoriesAndLand could all move
// catIndex away from an active embedded section without ever unloading it.
function unloadEmbeddedBoxIfLeaving(newIndex) {
  const prevCat = state.categories[state.catIndex];
  if (prevCat && prevCat.kind === "browser_section" && newIndex !== state.catIndex) {
    api().unload_browser_box();
  }
  if (prevCat && prevCat.kind === "plugin_webapp" && newIndex !== state.catIndex) {
    api().unload_plugin_webapp_box(prevCat.pluginId);
  }
  if (state.chatPluginActive && newIndex !== state.catIndex) {
    api().unload_plugin_webapp_box(state.chatPluginActive);
    state.chatPluginActive = null;
    if (state.activeAddonLayout) restoreAddonLayout();
  }
}

function selectCategory(i, openImmediately) {
  unloadEmbeddedBoxIfLeaving(i);
  el("item-panel").classList.remove("hidden");
  state.catIndex = i;
  state.selected = 0;
  state.mediaFocus = "list";
  // A direct commit (mouse click) goes straight to "options" so the
  // panel is already in its final on-screen position by the time
  // refreshItemPanel measures it for an embedded plugin - flipping this
  // AFTER refreshItemPanel (as a separate step) meant Explorer/Browser/
  // webapp sections measured the panel while it was still in the
  // "sections" (off-screen/hidden) position, producing a bogus box
  // geometry that sometimes rendered the boxed app in the wrong place or
  // made it look like it had opened as a separate external window.
  state.radialFocus = openImmediately ? "options" : "sections";
  state.sectionsBrowseIndex = i;
  document.body.dataset.radialFocus = state.radialFocus;
  state.settingsCursor = 0;
  applyAccent();
  renderCategories();
  const newCat = state.categories[i];
  const nowEmbedded = !!(newCat && (newCat.kind === "browser_section" || newCat.kind === "plugin_webapp"));
  document.body.classList.toggle("embedded-plugin-active", nowEmbedded);
  refreshItemPanel();
}

function moveCategory(delta) {
  const next = (state.catIndex + delta + state.categories.length) % state.categories.length;
  selectCategory(next);
}

// Music/Photos/Videos, when Load Subfolders is off, show a folder sidebar
// to the left of the list. Left/Right there behaves differently from the
// usual "always changes category" rule: Left first moves focus into the
// sidebar; only pressing Left again (once already in the sidebar) moves to
// the section to the left. Right mirrors this back out to the file list.
function isSubfolderModeActive() {
  const cat = state.categories[state.catIndex];
  return !!(cat && cat.kind === "media" && state.settings && state.settings.load_subfolders === false);
}

// ---------------- sections / options / subfolder focus cycle ----------------
// Up/down always changes which section is highlighted. Left/right cycles
// which panel has focus: sections -> options -> subfolder -> sections
// (right), and the mirror (left). When the current category has no
// subfolder panel (most of them — media-only, same condition as
// elsewhere), this degrades to a clean 2-way sections<->options cycle
// instead of landing on a dead, invisible focus state. Same behavior in
// both NightHorizon and CyberRadial — this isn't a CyberRadial-only thing.
function radialSubfolderAvailable() {
  return isSubfolderModeActive();
}
function setRadialFocus(next) {
  const cat = state.categories[state.catIndex];
  if (cat.kind === "direct") return; // no options/subfolder concept there
  if (next === "options" && state.radialFocus === "sections" && usesConfirmToLoadSections()) {
    commitBrowsedSection();
    return;
  }
  if (next === "sections") state.sectionsBrowseIndex = state.catIndex; // start browsing from wherever's actually loaded
  setRadialFocusRaw(next);
}
function setRadialFocusRaw(next) {
  state.radialFocus = next;
  state.mediaFocus = next === "subfolder" ? "folders" : "list";
  document.body.dataset.radialFocus = next;
  const cat = state.categories[state.catIndex];
  if (cat.kind === "settings" || cat.kind === "direct") return; // no item-list to (re)render there
  if (next === "subfolder") renderSubfolderSidebar(cat.id);
  renderItemList(cat);
}
// Confirm (or right-nav) out of "sections": if the user browsed to a
// different section than what's actually loaded, load it now — otherwise
// (they just navigated back into the section that's already showing) skip
// straight to options without reloading anything.
function commitBrowsedSection() {
  el("item-panel").classList.remove("hidden");
  const targetCat = state.categories[state.sectionsBrowseIndex];
  const sameIndexButEmbedded = state.sectionsBrowseIndex === state.catIndex &&
    targetCat && (targetCat.kind === "browser_section" || targetCat.kind === "plugin_webapp");
  if (state.sectionsBrowseIndex !== state.catIndex || sameIndexButEmbedded || state.sectionManuallyClosed) {
    state.sectionManuallyClosed = false;
    unloadEmbeddedBoxIfLeaving(state.sectionsBrowseIndex);
    state.catIndex = state.sectionsBrowseIndex;
    state.selected = 0;
    state.mediaFocus = "list";
    state.settingsCursor = 0;
    applyAccent();
    renderCategories();
    // radial-focus flips to "options" BEFORE refreshItemPanel (not after):
    // an embedded plugin (Explorer/Browser/webapp section) measures
    // #item-panel's on-screen box the instant it loads, and that box is
    // only in its final position once the "options" slide-in state is
    // active - measuring while still in the "sections" (off-screen/
    // hidden) state gave a bogus box position, which is why boxed apps
    // sometimes rendered in the wrong place or looked like they'd opened
    // as a separate/external window instead of inside the panel.
    document.body.dataset.radialFocus = "options";
    state.radialFocus = "options";
    state.mediaFocus = targetCat && targetCat.kind === "subfolder" ? "folders" : "list";
    refreshItemPanel();
    return;
  }
  setRadialFocusRaw("options");
}
function sectionFocusLeftNav() {
  // DawningHorizon's sections bar is horizontal: left/right scrolls it while
  // the sections have focus (the vertical themes use up/down for this).
  if (isDawningHorizon() && state.radialFocus === "sections") {
    const n = state.categories.length;
    state.sectionsBrowseIndex = (state.sectionsBrowseIndex - 1 + n) % n;
    renderCategories();
  }
}
function sectionFocusRightNav() {
  if (isDawningHorizon() && state.radialFocus === "sections") {
    const n = state.categories.length;
    state.sectionsBrowseIndex = (state.sectionsBrowseIndex + 1) % n;
    renderCategories();
  }
}

// Dawning Horizon doesn't use the sections/options/subfolder focus cycle at
// all — it's the original interaction model verbatim: left/right always
// changes category (with the classic subfolder-sidebar dance for media
// categories with Load Subfolders off), up/down always browses whatever
// list/cursor is currently showing.

// Gallery Style: left/right first try to move within the grid row; only
// once you're at the leftmost/rightmost column does left/right fall
// through to the normal sections/options/subfolder focus cycle.
function galleryAtLeftEdge() {
  return (state.selected % galleryColumnCount()) === 0;
}
function galleryAtRightEdge() {
  const cols = galleryColumnCount();
  return (state.selected % cols) === cols - 1 || state.selected === state.items.length - 1;
}

// --- Color grid 2D navigation (Themes settings) ---
// The mspaint-style color grid is a single entry in the linear settings
// cursor. When the cursor sits on it, directional input moves a 2D
// sub-cursor over the cells instead of leaving the grid, and confirm picks
// the highlighted cell. Up past the top row / down past the bottom row
// releases back to the normal settings cursor so you can navigate past it.
function settingsCursorOnColorGrid() {
  const els = settingsFocusableElements();
  const node = els[state.settingsCursor];
  return node && node.classList && node.classList.contains("color-grid") ? node : null;
}
function colorGridDims(grid) {
  const cells = [...grid.querySelectorAll(".color-cell")];
  const cols = 24; // matches renderSettings grid construction
  const rows = Math.ceil(cells.length / cols);
  return { cells, cols, rows };
}
function highlightColorGridCell(grid) {
  const { cells, cols } = colorGridDims(grid);
  cells.forEach((cell, i) => {
    cell.classList.toggle("grid-cursor", i === state.colorGridIndex);
  });
  const cur = cells[state.colorGridIndex];
  if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: "nearest", inline: "nearest" });
}
// returns true if it handled the movement (i.e. stayed in / entered the grid)
function handleColorGridNav(dx, dy) {
  const grid = settingsCursorOnColorGrid();
  if (!grid) return false;
  const { cells, cols, rows } = colorGridDims(grid);
  if (!cells.length) return false;
  if (state.colorGridIndex == null) state.colorGridIndex = 0;
  let idx = state.colorGridIndex;
  let r = Math.floor(idx / cols);
  let col = idx % cols;
  if (dy < 0) {
    if (r === 0) { state.colorGridIndex = null; return false; } // release upward
    r -= 1;
  } else if (dy > 0) {
    if (r >= rows - 1) { state.colorGridIndex = null; return false; } // release downward
    r += 1;
  }
  if (dx < 0) col = Math.max(0, col - 1);
  else if (dx > 0) col = Math.min(cols - 1, col + 1);
  idx = Math.min(cells.length - 1, r * cols + col);
  state.colorGridIndex = idx;
  highlightColorGridCell(grid);
  return true;
}
function confirmColorGridCell() {
  const grid = settingsCursorOnColorGrid();
  if (!grid) return false;
  const { cells } = colorGridDims(grid);
  const cell = cells[state.colorGridIndex || 0];
  if (cell) { cell.click(); return true; }
  return false;
}

function handleLeftNav() {
  const cat = state.categories[state.catIndex];
  if (cat.kind === "settings" && handleColorGridNav(-1, 0)) return;
  if (cat.kind === "direct") { moveCategory(-1); return; }
  if (state.radialFocus === "options" && getDisplayType(cat.id) === "gallery" && state.items.length && !galleryAtLeftEdge()) {
    state.selected = Math.max(0, state.selected - 1);
    renderItemList(cat);
    scrollSelectedIntoView();
    return;
  }
  sectionFocusLeftNav();
}
function handleRightNav() {
  const cat = state.categories[state.catIndex];
  if (cat.kind === "settings" && handleColorGridNav(1, 0)) return;
  if (cat.kind === "direct") { moveCategory(1); return; }
  if (state.radialFocus === "options" && getDisplayType(cat.id) === "gallery" && state.items.length && !galleryAtRightEdge()) {
    state.selected = Math.min(state.items.length - 1, state.selected + 1);
    renderItemList(cat);
    scrollSelectedIntoView();
    return;
  }
  sectionFocusRightNav();
}

function moveSelection(delta) {
  const cat = state.categories[state.catIndex];
  if (usesConfirmToLoadSections() && state.radialFocus === "sections" && cat.kind !== "direct") {
    // DawningHorizon's sections bar is horizontal, so it scrolls with
    // left/right (handled in handleLeftNav/RightNav); up/down does nothing
    // to the sections there. The vertical themes scroll sections up/down.
    if (isDawningHorizon()) return;
    const n = state.categories.length;
    state.sectionsBrowseIndex = (state.sectionsBrowseIndex + delta + n) % n;
    renderCategories();
    return;
  }
  if (cat.kind === "direct") return; // no linear list to browse there
  if (cat.kind === "settings") {
    // The Settings landing list navigates like a normal item list.
    if (state.settingsGroup === "menu") {
      state.settingsMenuIndex = Math.max(0, Math.min(SETTINGS_OPTIONS.length - 1,
        state.settingsMenuIndex + delta));
      renderSettingsMenu();
      return;
    }
    // If the cursor is on the color grid, up/down move within it (and only
    // release to the normal cursor at the grid's top/bottom edge).
    if (handleColorGridNav(0, delta)) return;
    const count = settingsFocusableElements().length;
    if (!count) return;
    state.settingsCursor = Math.max(0, Math.min(count - 1, state.settingsCursor + delta));
    highlightSettingsCursor();
    // Entering the color grid from above/below starts its sub-cursor.
    if (settingsCursorOnColorGrid()) {
      const grid = settingsCursorOnColorGrid();
      const { cells, cols, rows } = colorGridDims(grid);
      // land on the near edge depending on travel direction
      state.colorGridIndex = delta > 0 ? 0 : Math.max(0, (rows - 1) * cols);
      highlightColorGridCell(grid);
    }
    return;
  }
  if (isSubfolderModeActive() && state.mediaFocus === "folders") {
    const entries = state.folderEntries || [];
    if (!entries.length) return;
    state.folderCursor = Math.max(0, Math.min(entries.length - 1, state.folderCursor + delta));
    renderSubfolderSidebar(cat.id);
    return;
  }
  if (!state.items.length) return;
  const step = getDisplayType(cat.id) === "gallery" ? galleryColumnCount() : 1;
  state.selected = Math.max(0, Math.min(state.items.length - 1, state.selected + delta * step));
  renderItemList(cat);
  scrollSelectedIntoView();
}

// How many tiles fit per row in the current gallery grid, measured from
// the actual rendered layout rather than assumed — so it stays correct
// regardless of screen size or column count. Up/down in Gallery Style
// jumps by this many items, landing one row down/up, since left/right is
// claimed by the sections/options/subfolder focus cycle and can't be used
// for intra-row movement anymore.
function galleryColumnCount() {
  const tiles = el("item-panel").querySelectorAll(".item-list > .item-row");
  if (tiles.length < 2) return 1;
  const firstTop = tiles[0].offsetTop;
  let count = 0;
  for (const t of tiles) {
    if (t.offsetTop !== firstTop) break;
    count++;
  }
  return Math.max(1, count);
}

function scrollSelectedIntoView() {
  const selectedEl = el("item-panel").querySelector(".item-row.selected");
  if (selectedEl) selectedEl.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// ---------------- filling the panel for whatever category is highlighted ----------------

// Plug-ons ("addon"-type plugins) and plain "option"-type plugins (e.g.
// Chat's Telegram/Discord/etc) both surface the same way: extra list
// entries in an existing section, boxed into a webapp window on
// activation. list_section_options(section_id) returns both kinds
// together; this just formats them into list items and tags addons
// separately (they carry layout prefs / auto-disable-if-section-hidden
// behavior "option" entries don't). Cached per section id per visit,
// same as the old chat-only version this replaces.
state.sectionOptionsCache = {};
async function getSectionOptionItems(sectionId) {
  const options = (await api().list_section_options(sectionId)) || [];
  state.sectionOptionsCache[sectionId] = options;
  return options.map((p) => ({
    __chatPlugin: true, pluginId: p.id, name: p.label,
    __addon: !!p.addon, addonLayout: p.layout || null,
  }));
}

async function refreshItemPanel() {
  const cat = state.categories[state.catIndex];
  // Settings navigation runs a touch faster than section browsing.
  try { api().set_nav_speed_fast(cat.kind === "settings"); } catch (e) {}
  try {
    if (cat.kind === "settings") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      // Entering Settings always lands on its option list.
      state.settingsGroup = "menu";
      await renderSettings("menu");
      return;
    }

    el("item-panel").innerHTML = `<div class="empty-msg">Loading&hellip;</div>`;

    if (cat.kind === "system_list") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const addonItems = await getSectionOptionItems(cat.id);
      state.items = [...SYSTEM_ITEMS, ...addonItems];
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "file_list") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const addonItems = await getSectionOptionItems(cat.id);
      state.items = [...FILE_ITEMS, ...addonItems];
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "web_list") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const shortcuts = (state.settings && state.settings.web_shortcuts) || [];
      const addonItems = await getSectionOptionItems(cat.id);
      state.items = [
        ...WEB_ITEMS,
        ...addonItems,
        ...shortcuts.map((s) => ({ ...s, __customWeb: true })),
        { __addShortcut: true, label: "Add web shortcut" },
      ];
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "media") {
      if (state.settings && state.settings.load_subfolders === false) {
        await refreshMediaBrowseView(cat.id);
      } else {
        setSubfolderNavHidden(true);
        let items = await api().scan_library(cat.id);
        if (cat.id === "music") items = sortMusicItems(items);
        const addonItems = await getSectionOptionItems(cat.id);
        state.items = items.length || addonItems.length ? [...items, ...addonItems] : [{ __empty: true }];
        state.selected = Math.min(state.selected, state.items.length - 1);
        renderItemList(cat);
      }
    } else if (cat.kind === "desktop_list") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const items = await api().list_desktop_items();
      const addonItems = await getSectionOptionItems(cat.id);
      state.items = items.length || addonItems.length ? [...items, ...addonItems] : [{ __empty: true }];
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "exe_list") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const items = await api().list_section_items(cat.id);
      // Option/addon plugins targeting this section (Chat's Discord/
      // Telegram/etc, or any plug-on aimed at Apps/Games/Emulators/Chat)
      // - below the section's own built-in entries, per plug-on ordering.
      const pluginItems = await getSectionOptionItems(cat.id);
      if (cat.id === "games") {
        const recents = await api().get_recent_games();
        state.items = [GAME_LIBRARY_ITEM, ...recents.map((r) => ({ ...r, __recent: true })), ...items, ...pluginItems];
      } else {
        state.items = [...items, ...pluginItems];
        if (!state.items.length) state.items = [{ __empty: true }];
      }
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "plugin_list") {
      // Plain data-driven list plugin (e.g. Start) — no list/gallery
      // toggle, no subfolder panel, just up/down + A like exe_list.
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const items = await api().list_plugin_items(cat.pluginId);
      state.items = items.length ? items : [{ __empty: true }];
      state.selected = Math.min(state.selected, state.items.length - 1);
      renderItemList(cat);
    } else if (cat.kind === "browser_section") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      el("item-panel").innerHTML = `<div class="explorer-box-placeholder empty-msg">Loading Meridian NetBrowse&hellip;</div>`;
      await loadBrowserBox(state.browserPendingUrl || null);
    } else if (cat.kind === "plugin_webapp") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      el("item-panel").innerHTML = `<div class="explorer-box-placeholder empty-msg">Loading ${escapeHtml(cat.label)}&hellip;</div>`;
      await loadPluginWebappBox(cat.pluginId);
    } else if (cat.kind === "macro_list") {
      setSubfolderNavHidden(true);
      el("preview-pane").classList.add("hidden");
      const items = await api().list_macro_items();
      state.items = items;
      state.selected = Math.min(state.selected, Math.max(items.length - 1, 0));
      renderItemList(cat);
    }
  } catch (err) {
    console.error("Failed to load section:", cat.id, err);
    el("item-panel").innerHTML = `<div class="empty-msg">Something went wrong loading ${escapeHtml(cat.label)}.<br>${escapeHtml(err && err.message ? err.message : String(err))}</div>`;
    alignCategoryRowToList();
  }
}

// ---------------- subfolder browsing (Load Subfolders disabled) ----------------

async function refreshMediaBrowseView(kind) {
  const roots = await api().get_root_folders(kind);
  if (!roots.length) {
    setSubfolderNavHidden(true);
    el("preview-pane").classList.add("hidden");
    const cat = state.categories[state.catIndex];
    const addonItems = cat ? await getSectionOptionItems(cat.id) : [];
    state.items = addonItems.length ? addonItems : [{ __empty: true }];
    state.selected = 0;
    renderItemList(state.categories[state.catIndex]);
    return;
  }
  setSubfolderNavHidden(false);
  if (!state.folderStack[kind] || !state.folderStack[kind].length) {
    state.folderStack[kind] = [roots[0]];
  }
  await loadCurrentBrowsePath(kind);
}

async function loadCurrentBrowsePath(kind) {
  const stack = state.folderStack[kind];
  const path = stack[stack.length - 1];
  const [result, roots] = await Promise.all([api().browse_folder(kind, path), api().get_root_folders(kind)]);
  state.subfoldersCurrent = result.subfolders;
  let items = result.items;
  if (kind === "music") items = sortMusicItems(items);
  const cat = state.categories[state.catIndex];
  const addonItems = cat ? await getSectionOptionItems(cat.id) : [];
  const combined = [...items, ...addonItems];
  state.items = combined.length ? combined : [{ __empty: true, __browsingEmpty: true }];
  state.selected = 0;
  state.folderEntries = buildFolderEntries(kind, roots);
  state.folderCursor = Math.max(0, Math.min(state.folderCursor, state.folderEntries.length - 1));
  renderSubfolderSidebar(kind);
  renderItemList(state.categories[state.catIndex]);
}

function buildFolderEntries(kind, roots) {
  const stack = state.folderStack[kind] || [];
  const entries = roots.map((r) => ({ type: "root", path: r }));
  if (stack.length > 1) entries.push({ type: "up" });
  (state.subfoldersCurrent || []).forEach((name) => entries.push({ type: "subfolder", name }));
  return entries;
}

async function activateFolderEntry(kind, entry) {
  if (entry.type === "root") {
    state.folderStack[kind] = [entry.path];
    state.folderCursor = 0;
    await loadCurrentBrowsePath(kind);
  } else if (entry.type === "up") {
    await goUpFolder(kind);
    state.folderCursor = 0;
  } else if (entry.type === "subfolder") {
    await enterSubfolder(kind, entry.name);
    state.folderCursor = 0;
  }
}

async function enterSubfolder(kind, name) {
  const stack = state.folderStack[kind];
  const current = stack[stack.length - 1];
  const sep = current.includes("\\") ? "\\" : "/";
  stack.push(current.replace(/[\\/]+$/, "") + sep + name);
  await loadCurrentBrowsePath(kind);
}

async function goUpFolder(kind) {
  const stack = state.folderStack[kind];
  if (!stack || stack.length <= 1) return false;
  stack.pop();
  await loadCurrentBrowsePath(kind);
  return true;
}

const FOLDER_ICON_SVG = `<svg class="sf-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z"/></svg>`;
const UP_ICON_SVG = `<svg class="sf-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>`;

function renderSubfolderSidebar(kind) {
  const nav = el("subfolder-nav");
  nav.classList.toggle("focused", state.mediaFocus === "folders");
  nav.innerHTML = `<div class="sf-header">Folders</div>`;
  const stack = state.folderStack[kind] || [];
  const currentRoot = stack[0];

  (state.folderEntries || []).forEach((entry, i) => {
    const row = document.createElement("div");
    const isCursor = state.mediaFocus === "folders" && i === state.folderCursor;
    let iconSvg, label, isCurrentRoot = false;
    if (entry.type === "root") {
      iconSvg = FOLDER_ICON_SVG;
      label = entry.path.split(/[\\/]/).filter(Boolean).pop() || entry.path;
      isCurrentRoot = entry.path === currentRoot;
    } else if (entry.type === "up") {
      iconSvg = UP_ICON_SVG;
      label = ".. Up";
    } else {
      iconSvg = FOLDER_ICON_SVG;
      label = entry.name;
    }
    row.className = "sf-row" + (isCursor ? " selected" : "") + (isCurrentRoot ? " current-root" : "");
    row.innerHTML = `${iconSvg}<span class="sf-label">${escapeHtml(label)}</span>`;
    row.addEventListener("click", () => {
      state.mediaFocus = "folders";
      state.folderCursor = i;
      activateFolderEntry(kind, entry);
    });
    nav.appendChild(row);
  });
  syncSubfolderNavWidth();
}

// CyberRadial only: the subfolder bar sits in the column immediately
// left of the options bar, right next to the section hub. The active
// section's pill has a glowing ::after extension (210px, see
// ".category.active .label::after" in style.css) that reaches further
// right depending on where that section sits on the arc, and can
// intrude into the subfolder column. Rather than hand-tune a fixed
// offset for one arc position, this measures the real geometry each
// time and narrows the bar (shrinking in from its left edge) only when
// there's an actual overlap, restoring full width otherwise.
// Whether the subfolder bar's grid column should stay reserved/visible
// even when this particular section has no subfolder content of its
// own - see setSubfolderNavHidden() below. Deliberately excludes the
// embedded-native-window sections (Explorer/Browser/webapp plugins),
// which need the full width back and wouldn't make sense showing a
// decorative filler next to someone else's window.
function _subfolderNavStaysReservedFor(cat) {
  if (!cat) return false;
  if (!document.body.classList.contains("layout-cyberradial")) return false;
  if (document.body.className.indexOf("layout-user-") !== -1) return false; // drop-in themes fully own their own layout
  return !["browser_section", "plugin_webapp"].includes(cat.kind);
}

// CyberRadial's box-size bug: #item-panel's grid column used to depend
// on whether #subfolder-nav was showing real content or was
// display:none (see the #content-area:has(#subfolder-nav.hidden) rule
// in style.css) - a section with no subfolder content at all (Apps,
// Games, Chat, System, ...) hid the bar entirely, which is exactly when
// the reserved-but-empty 220px column caused visible sizing
// inconsistencies. This keeps the bar's column PERMANENTLY reserved
// (never true display:none) for every list-based section in this theme,
// filling it with a decorative placeholder (gif + note, customizable in
// Settings > Theme) instead of hiding it outright - the two "bars"
// (subfolder width and options width) are no longer linked to whether
// this particular section happens to use subfolder navigation.
function setSubfolderNavHidden(hidden) {
  const nav = el("subfolder-nav");
  const cat = state.categories[state.catIndex];
  if (hidden && _subfolderNavStaysReservedFor(cat)) {
    nav.classList.remove("hidden");
    nav.classList.add("subfolder-filler");
    const gifUrl = (state.settings && state.settings.subfolder_filler_gif) || "assets/subfolder_filler.gif";
    nav.innerHTML = `<div class="subfolder-filler-inner"><img src="${escapeHtml(gifUrl)}" alt=""><p>No subfolder navigation here</p></div>`;
    return;
  }
  nav.classList.remove("subfolder-filler");
  nav.classList.toggle("hidden", hidden);
}

function syncSubfolderNavWidth() {
  const nav = el("subfolder-nav");
  if (!nav) return;
  // Always start clean so we measure the un-shrunk layout first.
  nav.style.removeProperty("margin-left");
  nav.style.removeProperty("width");
  if (!document.body.classList.contains("layout-cyberradial")) return;
  // Drop-in themes based on cyber_radial (e.g. Factory Central) can fully
  // reposition #subfolder-nav with their own fixed-position rules; this
  // collision math is tuned for the base theme's left-arc geometry and
  // would fight an unrelated layout's inline width instead of helping it.
  if (document.body.className.indexOf("layout-user-") !== -1) return;
  if (nav.classList.contains("hidden")) return;
  const navRect = nav.getBoundingClientRect();
  if (navRect.width === 0 && navRect.height === 0) return;
  const activeLabel = document.querySelector(".category.active .label");
  if (!activeLabel) return;
  const labelRect = activeLabel.getBoundingClientRect();
  const GLOW_WIDTH = 210; // matches .category.active .label::after
  const GAP = 12; // breathing room past the glow's edge
  const MIN_WIDTH = 60; // never shrink the bar past readability
  const glowRight = labelRect.right + GLOW_WIDTH;
  const verticallyOverlaps = labelRect.bottom > navRect.top && labelRect.top < navRect.bottom;
  if (!verticallyOverlaps || glowRight <= navRect.left) return;
  const intrude = Math.min(navRect.width - MIN_WIDTH, glowRight - navRect.left + GAP);
  if (intrude > 0) {
    nav.style.marginLeft = `${Math.round(intrude)}px`;
    nav.style.width = `calc(100% - ${Math.round(intrude)}px)`;
  }
}
window.addEventListener("resize", () => syncSubfolderNavWidth());

// ---------------- bigger preview pane (Music/Photos/Videos) ----------------

function updatePreviewPane() {
  const cat = state.categories[state.catIndex];
  const pane = el("preview-pane");
  if (!cat || cat.kind !== "media") { pane.classList.add("hidden"); return; }
  const item = state.items[state.selected];
  if (!item || item.__empty) { pane.classList.add("hidden"); return; }
  pane.classList.remove("hidden");
  el("preview-img").src = item.fullUrl || item.thumbUrl || "";
  el("preview-title").textContent = item.title || item.name || "";
}

// ---------------- one unified row renderer for every section kind ----------------

function rowContentFor(cat, item, i) {
  if (item.__browsingEmpty) {
    return `<div class="row-visual">${iconFor(cat.id)}</div><div class="meta"><div class="title">This folder is empty</div></div>`;
  }
  if (item.__empty) {
    return `<div class="row-visual">${iconFor(cat.id)}</div><div class="meta"><div class="title">Nothing added yet — press confirm to add it in Settings</div></div>`;
  }
  // Same reasoning as activateCurrentSelection: a plug-on/option-plugin
  // item can now be spliced into any built-in section's list, so it
  // needs its own row style checked before any per-section branch below
  // assumes fields (title/thumbUrl/is_dir/etc) an addon item doesn't have.
  if (item.__chatPlugin) {
    return `<div class="row-visual">${ICONS.browser || ICONS.generic}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div>${item.__addon ? `<div class="subtitle">Plug-on</div>` : ""}</div>`;
  }
  if (cat.id === "music") {
    return `
      <span class="idx">${String(i + 1).padStart(2, "0")}</span>
      <div class="row-visual">${item.thumbUrl ? `<img src="${item.thumbUrl}" alt="">` : ICONS.music}</div>
      <div class="meta"><div class="title">${escapeHtml(item.title)}</div><div class="subtitle">${escapeHtml(item.artist)} &middot; ${escapeHtml(item.album)}</div></div>
      <span class="dur">${item.durationLabel || ""}</span>`;
  }
  if (cat.kind === "media") { // photos / videos
    return `
      <div class="row-visual">${item.thumbUrl ? `<img src="${item.thumbUrl}" alt="">` : ICONS[cat.id]}</div>
      <div class="meta"><div class="title">${escapeHtml(item.title)}</div></div>
      ${cat.id === "videos" && item.durationLabel ? `<span class="dur">${item.durationLabel}</span>` : ""}`;
  }
  if (cat.kind === "exe_list" || cat.kind === "desktop_list") {
    if (item.__gameLibrary) {
      return `<div class="row-visual">${ICONS.games}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
    }
    if (item.__chatPlugin) {
      return `<div class="row-visual">${ICONS.browser || ICONS.generic}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
    }
    const iconHtml = item.iconUrl ? `<img src="${item.iconUrl}" alt="">` : (item.is_dir ? ICONS.explorer : iconFor(cat.id));
    const subtitle = item.__recent ? `<div class="subtitle">Recently played</div>` : "";
    return `<div class="row-visual">${iconHtml}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div>${subtitle}</div>`;
  }
  if (cat.kind === "macro_list") {
    const iconHtml = item.type === "builtin" ? ICONS.macros : (item.iconUrl ? `<img src="${item.iconUrl}" alt="">` : ICONS.bat);
    return `<div class="row-visual">${iconHtml}</div><div class="meta"><div class="title">${escapeHtml(item.name)}</div></div>`;
  }
  if (cat.kind === "system_list" || cat.kind === "file_list" || cat.kind === "web_list" || cat.kind === "plugin_list") {
    if (item.__addShortcut) {
      return `<div class="row-visual">${ICONS.web || ""}</div><div class="meta"><div class="title">+ Add web shortcut</div></div>`;
    }
    if (item.__customWeb) {
      return `<div class="row-visual">${ICONS.web || ""}</div><div class="meta"><div class="title">${escapeHtml(item.label)}</div><div class="subtitle">${escapeHtml(item.url)}</div></div>`;
    }
    return `<div class="row-visual">${ICONS[item.icon] || ICONS.generic || ""}</div><div class="meta"><div class="title">${escapeHtml(item.label)}</div></div>`;
  }
  return "";
}

function renderItemList(cat) {
  const wrap = document.createElement("div");
  wrap.className = "item-list";
  state.items.forEach((item, i) => {
    const row = document.createElement("div");
    const isEmpty = !!item.__empty || !!item.__browsingEmpty;
    row.className = "item-row" + (i === state.selected ? " selected" : "") + (isEmpty ? " empty-prompt-row" : "") + (item.__recent ? " recent-item" : "");
    row.innerHTML = rowContentFor(cat, item, i);
    row.addEventListener("click", () => { state.selected = i; renderItemList(cat); activateCurrentSelection(); });
    wrap.appendChild(row);
  });
  el("item-panel").innerHTML = "";
  el("item-panel").appendChild(wrap);
  const activeEl = wrap.querySelector(".selected");
  if (activeEl && typeof activeEl.scrollIntoView === "function") activeEl.scrollIntoView({ block: "nearest" });
  updatePreviewPane();
  alignCategoryRowToList();
  syncTaskbarSizeToLayout();
  syncSubfolderNavWidth();
}

// Dawning Horizon's item-panel grows with its content (normal document
// flow, no fixed height) while its open-programs bar is a fixed-height
// column pinned to the top-right - a long list can grow tall enough to
// visually collide with it. Shrinks the bar's height (from its normal
// top:24/bottom:64 span) to stop just above wherever the panel's content
// currently reaches, whenever they'd actually overlap; restores its
// normal height otherwise. Re-run after any item-list render and on
// resize, since both the panel's height and the bar's position can change.
function syncTaskbarSizeToLayout() {
  const bar = el("task-bar");
  if (!bar) return;
  // Always start clean: whichever theme's own logic below applies (if
  // any) sets exactly what it needs: stale inline styles left over from
  // a PREVIOUS theme (these are inline, so they'd otherwise outrank that
  // theme's own CSS rules) is what made the radial taskbar look "too
  // tall/wide, wrong spot" after having been in Dawning Horizon.
  bar.style.removeProperty("top");
  bar.style.removeProperty("bottom");
  bar.style.removeProperty("height");

  if (document.body.classList.contains("layout-dawninghorizon")) {
    const panel = el("item-panel");
    if (!panel || panel.classList.contains("hidden")) return;
    const panelRect = panel.getBoundingClientRect();
    if (panelRect.width === 0 && panelRect.height === 0) return;
    // Always align the bar's top edge with the options list's top edge -
    // previously this only shrank height on an actual overlap, which
    // still left it starting noticeably higher/taller than the options
    // list above the point of collision.
    const newTop = Math.max(8, Math.round(panelRect.top));
    bar.style.top = `${newTop}px`;
    // Bottom edge stays where its CSS normally puts it (64px reserved for
    // the clock/battery block) - recompute height from the new top so it
    // still reaches there, rather than leaving a leftover gap.
    const bottomReserved = 64;
    const newHeight = Math.max(80, window.innerHeight - newTop - bottomReserved);
    bar.style.height = `${newHeight}px`;
    return;
  }

  // Radial-family themes (CyberRadial, Factory Central, NightHorizon):
  // the taskbar sits along the bottom and should exactly match the
  // clock/battery block's real height and bottom offset, so the two read
  // as one continuous row - measured live (not a hardcoded px height)
  // so it's correct at any resolution/DPI/zoom instead of just whatever
  // one reference size it was tuned for.
  // Radial-family themes (CyberRadial, NightHorizon): bottom/height are
  // fixed, generous CSS values (see taskbar-pos-cyber/night's own rules)
  // rather than computed live here - precisely matching the clock
  // block's measured height turned out to be exactly what was clipping
  // the icon row (the clock is shorter than a full row of task icons
  // needs) across multiple attempts to fix this by adjusting the
  // computed values instead of removing the live computation.
}
window.addEventListener("resize", () => syncTaskbarSizeToLayout());

// ---------------- activating whatever is currently selected ----------------

async function activateCurrentSelection() {
  const cat = state.categories[state.catIndex];
  // Sections bar has focus -> confirm loads the browsed-to section. This has
  // to come FIRST: otherwise, while sections are focused on the Settings
  // category, A would fall into the settings handling below and never
  // confirm the section.
  if (usesConfirmToLoadSections() && state.radialFocus === "sections") { setRadialFocus("options"); return; }
  if (cat.kind === "settings") {
    if (state.settingsGroup === "menu") {
      openSettingsGroup(SETTINGS_OPTIONS[state.settingsMenuIndex][0]);
      return;
    }
    if (confirmColorGridCell()) return; // picking a color cell
    const els = settingsFocusableElements();
    const node = els[state.settingsCursor];
    if (node) node.click();
    return;
  }

  if (isSubfolderModeActive() && state.mediaFocus === "folders") {
    const entry = (state.folderEntries || [])[state.folderCursor];
    if (entry) await activateFolderEntry(cat.id, entry);
    return;
  }

  const item = state.items[state.selected];
  if (!item) return;
  if (item.__browsingEmpty) return; // just an inert "this folder is empty" placeholder
  if (item.__empty) { await goToSettingsFor(cat); return; }
  if (item.__gameLibrary) { await activateGameLibrary(); return; }
  // Plug-on / option-plugin entries can now appear spliced into any
  // built-in section's list (not just Chat's exe_list), so this has to
  // be checked before any of the per-section special cases below -
  // otherwise e.g. an addon entry in the Music list would fall into
  // playMusicAt() and try to play it as if it were a track.
  if (item.__chatPlugin) { activateChatPluginItem(item); return; }

  if (cat.id === "music") playMusicAt(state.selected);
  else if (cat.id === "photos") openPhoto(state.selected);
  else if (cat.id === "videos") openVideo(state.selected);
  else if (item.__playnite) launchRecentPlayniteGame(item);
  else if (cat.kind === "exe_list") launchAndNotify(item.path, cat.id);
  else if (cat.kind === "desktop_list") {
    if (item.is_dir) activateDesktopEntry(item);
    else launchAndNotify(item.path, cat.id);
  }
  else if (cat.kind === "macro_list") activateMacro(item);
  else if (cat.kind === "system_list") activateSystemItem(item);
  else if (cat.kind === "file_list") activateFileItem(item);
  else if (cat.kind === "web_list") activateWebItem(item);
  else if (cat.kind === "plugin_list") activatePluginItem(cat, item);
}

async function activatePluginItem(cat, item) {
  const res = await api().activate_plugin_item(cat.pluginId, item.id);
  if (res && res.ok === false) { showToast(`Couldn't open: ${res.error}`); return; }
  // A plugin can hand back the same route convention Desktop/Web items
  // use to ask for the embedded Explorer/Browser section instead of
  // launching anything itself - this used to be silently dropped here
  // (the only route handling lived in activateDesktopEntry/
  // openInternalUrl), so a plugin's request to open Explorer/Browser did
  // nothing at all, including when switching directly from a different
  // plugin section's list. Routing here the same way those two do means
  // a plugin can never end up launching Explorer/CyberDeckBrowser as a
  // separate external window either - only the boxed section, in every
  // theme, same as any other entry point into those sections.
  if (res && res.route === "browser_section") {
    const idx = state.categories.findIndex((c) => c.kind === "browser_section");
    if (idx !== -1) {
      state.browserPendingUrl = res.url || "";
      selectCategory(idx, true);
    }
    return;
  }
}

// Jump straight into Settings, scrolled to and briefly highlighting the
// block for the section the user just tried to use (since it has nothing
// in it yet). Only triggered by an explicit confirm on the empty-prompt row.
async function goToSettingsFor(cat) {
  const settingsIndex = state.categories.findIndex((c) => c.kind === "settings");
  if (settingsIndex === -1) return;
  unloadEmbeddedBoxIfLeaving(settingsIndex);
  state.catIndex = settingsIndex;
  state.selected = 0;
  applyAccent();
  renderCategories();
  await refreshItemPanel();
  try {
    const target = el(`settings-block-${cat.id}`);
    if (target && typeof target.scrollIntoView === "function") target.scrollIntoView({ behavior: "smooth", block: "start" });
    if (target) {
      target.classList.add("settings-block-highlight");
      setTimeout(() => target.classList.remove("settings-block-highlight"), 1600);
    }
  } catch (err) {
    console.warn("Couldn't scroll/highlight the settings block (non-fatal):", err);
  }
  showToast(`Nothing in ${cat.label} yet — add some here.`);
}

// ---------------- launching / macros / system / files ----------------

async function launchAndNotify(path, sectionId) {
  const res = await api().launch_exe(path, sectionId);
  if (!res.ok) showToast(`Couldn't launch: ${res.error}`);
}

async function launchRecentPlayniteGame(item) {
  const res = await api().launch_recent_game(item.id);
  if (!res.ok) showToast(`Couldn't launch: ${res.error}`);
}

async function activateGameLibrary() {
  const res = await api().launch_game_library();
  if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
}

function showToast(msg) {
  const t = el("empty-toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => t.classList.add("hidden"), 3500);
}

async function activateMacro(item) {
  if (item.type === "builtin" && item.id === "close_others") {
    const res = await api().run_macro(item.id);
    showToast(res.ok ? `Closed ${res.closed.length} other program(s).` : `Macro failed: ${res.error}`);
    return;
  }
  if (item.type === "builtin" && (item.id.startsWith("mx_") || item.id === "cdb_default_browser" || item.id === "fb_default_shell_browser" || item.id === "nb_default_shell_browser")) {
    const res = await api().run_macro(item.id);
    showToast(res.ok ? (res.message || "Done.") : `Failed: ${res.error}`);
    await refreshItemPanel(); // the Add/Remove context-menu label flips
    return;
  }
  if (item.type === "builtin" && item.id === "toggle_default_shell") {
    await runElevatedMacro(() => api().run_macro(item.id));
    return;
  }
  if (item.type === "ps1") {
    await runElevatedMacro(() => api().run_ps1_file(item.path));
    return;
  }
  launchAndNotify(item.path);
}

// Shared by any macro that needs to run elevated (.ps1 scripts): try a
// per-process UAC prompt first (system_actions.launch_ps1_elevated), and
// if even that fails, offer restarting Meridian Launcher itself as
// administrator rather than just reporting a dead-end error.
async function runElevatedMacro(invoke) {
  const res = await invoke();
  if (res.ok) { showToast(res.message || "Done."); return; }
  if (res.needs_admin_relaunch) {
    const yes = await openConfirmModal(
      "Administrator access needed",
      `${res.error || "This requires administrator access."} Restart Meridian Launcher as administrator now?`,
    );
    if (yes) {
      const relaunch = await api().relaunch_as_admin();
      if (!relaunch.ok) showToast(`Couldn't restart as administrator: ${relaunch.error}`);
    }
    return;
  }
  showToast(`Macro failed: ${res.error}`);
}

async function activateFileItem(item) {
  const res = item.id === "meridian_explorer" ? await api().launch_meridian_explorer() : await api().open_files();
  if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
}

function embeddedBoxGeometry() {
  // Deliberately NOT just panel.getBoundingClientRect() height: themes
  // position #item-panel very differently (grid child in the base
  // layout, position:fixed with its own top/bottom math in Factory
  // Central, etc), and a plain CSS override meant to make it reach the
  // bottom doesn't reliably apply across all of them (e.g. "bottom" has
  // no effect at all on a grid child unless it's also explicitly
  // positioned). Computing height as "from wherever the panel starts,
  // straight down to the bottom of the window" sidesteps all of that -
  // it's correct regardless of which theme/layout scheme is active.
  const panel = el("item-panel");

  // Factory Central (and any other theme using a transform to slide
  // #item-panel on/off screen based on data-radial-focus) animates that
  // transform over ~420ms. selectCategory() already sets radialFocus to
  // "options" before this runs, but that only changes which transform
  // the CSS *targets* - immediately measuring afterward can still catch
  // the panel mid-transition (or, worse, still at its off-screen
  // "sections" position if this runs in the same tick as the attribute
  // change, before the browser has committed to animating toward the
  // new value at all). Either way the measured rect would be wrong,
  // which is exactly why Explorer/Browser/plugin webapps previously
  // sometimes rendered off-position or looked like they'd opened as a
  // separate external window in that theme. Forcing the transform off
  // and reading the rect synchronously sidesteps the animation timing
  // entirely and always measures the settled, final position - a no-op
  // everywhere else, since only a theme using a transform like this is
  // affected by overriding it to "none".
  const prevTransition = panel.style.transition;
  const prevTransform = panel.style.transform;
  panel.style.transition = "none";
  panel.style.transform = "none";
  void panel.offsetHeight; // force a synchronous layout flush before reading the rect below
  const rect = panel.getBoundingClientRect();
  panel.style.transform = prevTransform;
  panel.style.transition = prevTransition;
  void panel.offsetHeight; // and again, so restoring the override doesn't itself flash a frame

  const x = Math.round(window.screenX + rect.left);
  const y = Math.round(window.screenY + rect.top);
  const w = Math.round(rect.width);
  const h = Math.round(window.innerHeight - rect.top - 4);
  return { x, y, w, h };
}

async function loadBrowserBox(url) {
  const { x, y, w, h } = embeddedBoxGeometry();
  state.browserPendingUrl = url;
  const res = await api().load_browser_box(url || "", x, y, w, h);
  if (res && res.ok === false) {
    el("item-panel").innerHTML = `<div class="empty-msg">${escapeHtml(res.error || "Couldn't load Meridian NetBrowse.")}</div>`;
  }
}

// ---------------- plug-on ("addon") layout preferences ----------------
// Applied while an addon's boxed window is open, restored on exit. Every
// preset is computed relative to #item-panel's own rect (via the same
// transform-neutralizing measurement as embeddedBoxGeometry), which is
// already clear of the Sections bar/hub in every theme - so every preset
// automatically "physically stops before" it too, including Dawning
// Horizon, where #item-panel already sits below the Sections bar by that
// theme's own layout rules.
state.activeAddonLayout = null;

function computeAddonBoxGeometry(windowPosition) {
  const base = embeddedBoxGeometry(); // {x,y,w,h}, already content-area-relative
  if (!windowPosition || windowPosition === "default") return base;
  if (windowPosition === "centered") {
    const w = Math.round(base.w * 0.7);
    const h = Math.round(base.h * 0.7);
    return { x: base.x + Math.round((base.w - w) / 2), y: base.y + Math.round((base.h - h) / 2), w, h };
  }
  if (windowPosition === "left_edge_to_right_edge") {
    // Full width from the item-panel's own left edge (already clear of
    // the Sections bar) out to the right edge of the window.
    const w = Math.round(window.innerWidth - base.x - 24);
    return { x: base.x, y: base.y, w: Math.max(w, 100), h: base.h };
  }
  if (windowPosition === "left_half") {
    return { x: base.x, y: base.y, w: Math.round(base.w / 2) - 10, h: base.h };
  }
  if (windowPosition === "right_half") {
    const w = Math.round(base.w / 2) - 10;
    return { x: base.x + base.w - w, y: base.y, w, h: base.h };
  }
  return base;
}

// show_subfolder/show_thumbnail/show_clock/show_battery/show_taskbar,
// each defaulting true if unset. Taskbar is the one exception even when
// false: pressing X still shows it on demand (see toggleTaskbarFocus),
// drawn above the boxed window instead of being unavailable outright -
// applyAddonLayout only sets up the "hidden unless forced" CSS class for
// that, it doesn't touch anything else about how X/the taskbar work.
function applyAddonLayout(layout) {
  state.activeAddonLayout = layout || null;
  const L = layout || {};
  if (L.show_subfolder === false) el("subfolder-nav").classList.add("addon-force-hidden");
  if (L.show_thumbnail === false) el("preview-pane").classList.add("addon-force-hidden");
  document.body.classList.toggle("addon-hide-clock", L.show_clock === false);
  document.body.classList.toggle("addon-hide-battery", L.show_battery === false);
  document.body.classList.toggle("addon-hide-music-player", L.show_music_player === false);
  // show_taskbar defaults true; addon-show-taskbar only actually reveals
  // it in practice for a non-"default" window_position (see the CSS
  // comment on .addon-show-taskbar) since "default" covers that screen
  // area with the boxed window's own OS-level topmost placement.
  document.body.classList.toggle("addon-show-taskbar", L.show_taskbar !== false);
  document.body.classList.toggle("addon-hide-taskbar", L.show_taskbar === false);
}

function restoreAddonLayout() {
  state.activeAddonLayout = null;
  el("subfolder-nav").classList.remove("addon-force-hidden");
  el("preview-pane").classList.remove("addon-force-hidden");
  document.body.classList.remove("addon-hide-clock", "addon-hide-battery", "addon-hide-music-player", "addon-hide-taskbar", "addon-show-taskbar", "addon-taskbar-forced");
}


async function activateChatPluginItem(item) {
  // Same boxed-webapp mechanic as a dedicated plugin section (Telegram
  // etc when it WAS its own section) — just triggered from inside a
  // section's list instead of by entering a section. state.chatPluginActive
  // marks that this came from the list, so onEmbeddedPluginExited returns
  // to that list on exit instead of the Sections bar.
  state.chatPluginActive = item.pluginId;
  document.body.classList.add("embedded-plugin-active");
  if (item.__addon) applyAddonLayout(item.addonLayout);
  await loadPluginWebappBox(item.pluginId, item.__addon ? item.addonLayout : null);
}

async function loadPluginWebappBox(pluginId, addonLayout) {
  const { x, y, w, h } = addonLayout ? computeAddonBoxGeometry(addonLayout.window_position) : embeddedBoxGeometry();
  const res = await api().load_plugin_webapp_box(pluginId, x, y, w, h);
  if (res && res.ok === false) {
    el("item-panel").innerHTML = `<div class="empty-msg">${escapeHtml(res.error || "Couldn't load this app.")}</div>`;
  }
}

async function activateDesktopEntry(item) {
  const res = await api().open_desktop_entry(item.path, !!item.is_dir);
  if (res && res.ok === false) { showToast(`Couldn't open: ${res.error}`); return; }
}

async function activateWebItem(item) {
  if (item.__addShortcut) { openWebShortcutModal(); return; }
  if (item.__customWeb) { await openInternalUrl(item.url); return; }
  if (item.id === "cyberdeck") {
    const res = await api().launch_cyberdeckbrowser_standalone();
    if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
    return;
  }
  const res = await api().open_web();
  if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
}

// Shared entry point for any internally-launched URL (Web-section
// shortcuts, the default "cyberdeck" item, etc): routes to the Browser
// section if it's enabled/visible, otherwise falls back through
// CyberDeckBrowser -> the system default browser (see open_web_link).
async function openInternalUrl(url) {
  const res = await api().open_web_link(url);
  if (res && res.ok === false) { showToast(`Couldn't open: ${res.error}`); return; }
  if (res && res.route === "browser_section") {
    const idx = state.categories.findIndex((c) => c.kind === "browser_section");
    if (idx !== -1) {
      state.browserPendingUrl = res.url;
      selectCategory(idx, true);
    }
  }
}

async function activateSystemItem(item) {
  const map = {
    shutdown: () => api().system_shutdown(),
    restart: () => api().system_restart(),
    sleep: () => api().system_sleep(),
    hibernate: () => api().system_hibernate(),
    close: () => api().quit_app(),
    controlpanel: () => api().system_control_panel(),
    taskmanager: () => api().system_task_manager(),
    recyclebin: () => api().system_recycle_bin(),
    uninstallapps: () => api().system_uninstall_apps(),
    commandprompt: () => api().system_command_prompt(),
    powershell: () => api().system_powershell(),
    msstore: () => api().system_microsoft_store(),
    windowsupdate: () => api().system_windows_update(),
    wifi: () => { openNetworkOverlay("wifi"); return null; },
    bluetooth: () => { openNetworkOverlay("bluetooth"); return null; },
    audio: () => { openNetworkOverlay("audio"); return null; },
  };
  const fn = map[item.id];
  if (!fn) return;
  const res = await fn();
  if (res && res.ok === false) showToast(`Couldn't complete: ${res.error}`);
}

// ---------------- Wi-Fi / Bluetooth ----------------

let networkMode = "wifi";
let pendingWifiSsid = null;

function closeNetworkOverlay() { el("network-overlay").classList.add("hidden"); }
el("network-close").addEventListener("click", closeNetworkOverlay);
el("network-refresh").addEventListener("click", refreshNetworkList);

async function openNetworkOverlay(mode) {
  networkMode = mode;
  el("network-title").textContent = mode === "wifi" ? "Wi-Fi" : mode === "audio" ? "Audio Output" : "Bluetooth";
  el("network-overlay").classList.remove("hidden");
  await refreshNetworkList();
}

async function refreshNetworkList() {
  const list = el("network-list");
  list.innerHTML = `<div class="empty-msg">Scanning&hellip;</div>`;
  if (networkMode === "wifi") {
    const res = await api().wifi_scan();
    if (!res.ok) { list.innerHTML = `<div class="empty-msg">${escapeHtml(res.error || "Couldn't scan for networks.")}</div>`; return; }
    renderWifiList(res.networks);
  } else if (networkMode === "audio") {
    const res = await api().list_audio_devices();
    list.innerHTML = "";
    if (!res.ok) {
      const msg = document.createElement("div");
      msg.className = "empty-msg";
      msg.textContent = res.error || "Couldn't list audio devices.";
      list.appendChild(msg);
    } else {
      renderAudioList(res.devices || []);
    }
  } else {
    const res = await api().bluetooth_list_devices();
    list.innerHTML = "";
    if (!res.ok) {
      const msg = document.createElement("div");
      msg.className = "empty-msg";
      msg.textContent = res.error || "Couldn't list Bluetooth devices.";
      list.appendChild(msg);
    } else {
      renderBluetoothList(res.devices || []);
    }
    const openBtn = document.createElement("button");
    openBtn.className = "btn-outline";
    openBtn.style.marginTop = "10px";
    openBtn.textContent = "Open Windows Bluetooth settings (to pair a new device)";
    openBtn.addEventListener("click", () => api().open_bluetooth_settings());
    list.appendChild(openBtn);
  }
}

function renderWifiList(networks) {
  const list = el("network-list");
  list.innerHTML = "";
  if (!networks.length) { list.innerHTML = `<div class="empty-msg">No networks found.</div>`; return; }
  networks.forEach((n) => {
    const row = document.createElement("div");
    row.className = "network-row";
    row.innerHTML = `
      ${ICONS.wifi.replace('class="', 'class="net-icon ')}
      <span class="net-name">${escapeHtml(n.ssid)}${n.secured ? " &#128274;" : ""}</span>
      <span class="net-status">${n.connected ? "Connected" : `${n.signal}%`}</span>`;
    const btn = document.createElement("button");
    btn.textContent = n.connected ? "Disconnect" : "Connect";
    btn.addEventListener("click", async () => {
      if (n.connected) {
        const res = await api().wifi_disconnect();
        if (!res.ok) showToast(`Couldn't disconnect: ${res.error}`); else refreshNetworkList();
      } else if (n.secured) {
        openWifiPasswordModal(n.ssid);
      } else {
        const res = await api().wifi_connect(n.ssid, "");
        showToast(res.ok ? `Connected to ${n.ssid}.` : `Couldn't connect: ${res.error}`);
        if (res.ok) refreshNetworkList();
      }
    });
    row.appendChild(btn);
    list.appendChild(row);
  });
}

function renderAudioList(devices) {
  const list = el("network-list");
  list.innerHTML = "";
  if (!devices.length) { list.innerHTML = `<div class="empty-msg">No active playback devices found.</div>`; return; }
  devices.forEach((d) => {
    const row = document.createElement("div");
    row.className = "network-row";
    row.innerHTML = `
      ${ICONS.audio.replace('class="', 'class="net-icon ')}
      <span class="net-name">${escapeHtml(d.name)}</span>
      <span class="net-status">${d.is_default ? "Default" : ""}</span>`;
    const btn = document.createElement("button");
    btn.textContent = d.is_default ? "Default" : "Set as Default";
    btn.disabled = d.is_default;
    btn.addEventListener("click", async () => {
      const res = await api().set_audio_output_device(d.id);
      showToast(res.ok ? `${d.name} is now the default output.` : `Couldn't switch: ${res.error}`);
      if (res.ok) refreshNetworkList();
    });
    row.appendChild(btn);
    list.appendChild(row);
  });
}

function renderBluetoothList(devices) {
  const list = el("network-list");
  if (!devices.length) {
    const msg = document.createElement("div");
    msg.className = "empty-msg";
    msg.textContent = "No known Bluetooth devices yet. Pair a new one from Windows settings below.";
    list.appendChild(msg);
    return;
  }
  devices.forEach((d) => {
    const row = document.createElement("div");
    row.className = "network-row";
    row.innerHTML = `
      ${ICONS.bluetooth.replace('class="', 'class="net-icon ')}
      <span class="net-name">${escapeHtml(d.name)}</span>
      <span class="net-status">${d.connected ? "Connected" : "Off"}</span>`;
    const btn = document.createElement("button");
    btn.textContent = d.connected ? "Disconnect" : "Connect";
    btn.addEventListener("click", async () => {
      const res = d.connected ? await api().bluetooth_disconnect(d.id) : await api().bluetooth_connect(d.id);
      showToast(res.ok ? "Done." : `Couldn't complete: ${res.error}`);
      if (res.ok) refreshNetworkList();
    });
    row.appendChild(btn);
    list.appendChild(row);
  });
}

function openWifiPasswordModal(ssid) {
  pendingWifiSsid = ssid;
  el("wifi-password-title").textContent = `Password for ${ssid}`;
  el("wifi-password-input").value = "";
  el("wifi-password-overlay").classList.remove("hidden");
  el("wifi-password-input").focus();
}
function closeWifiPasswordModal() {
  el("wifi-password-overlay").classList.add("hidden");
  pendingWifiSsid = null;
}
el("wifi-password-cancel").addEventListener("click", closeWifiPasswordModal);
el("wifi-password-confirm").addEventListener("click", async () => {
  const password = el("wifi-password-input").value;
  const ssid = pendingWifiSsid;
  closeWifiPasswordModal();
  const res = await api().wifi_connect(ssid, password);
  showToast(res.ok ? `Connected to ${ssid}.` : `Couldn't connect: ${res.error}`);
  if (res.ok) refreshNetworkList();
});
el("wifi-password-input").addEventListener("keydown", (e) => {
  e.stopPropagation();
  if (e.key === "Enter") el("wifi-password-confirm").click();
  if (e.key === "Escape") closeWifiPasswordModal();
});

// ---------------- generic Yes/No confirm modal (kiosk enable, factory reset) ----------------
// Controller/keyboard navigable like everything else: left/right swaps the
// highlighted button, confirm picks it, back always counts as "No".

let confirmResolveFn = null;
let confirmCursor = 1; // default to "No" — both callers are consequential actions

function isConfirmOpen() {
  return !el("confirm-overlay").classList.contains("hidden");
}

// Windows Store app picker (Apps/Streaming/etc. sections' "+ Add Windows
// Store App" button) - a search-filterable list of installed packaged
// apps (see system_actions.list_installed_store_apps for how they're
// found). Built as its own lightweight overlay rather than reusing the
// text-entry modal (#modal-overlay) or the yes/no confirm modal, since
// neither fits "pick one item from a list" - torn down completely on
// close/pick rather than kept as hidden DOM, since it's opened rarely.
function openStoreAppPicker(apps, onPick) {
  const overlay = document.createElement("div");
  overlay.className = "overlay";
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:500;";

  const box = document.createElement("div");
  box.style.cssText = "background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;width:min(480px,90vw);max-height:80vh;display:flex;flex-direction:column;";
  overlay.appendChild(box);

  const title = document.createElement("h3");
  title.textContent = "Add Windows Store App";
  title.style.margin = "0 0 12px";
  box.appendChild(title);

  if (!apps || !apps.length) {
    const empty = document.createElement("p");
    empty.className = "settings-note";
    empty.textContent = "No installed Windows Store apps found.";
    box.appendChild(empty);
    const closeBtn = document.createElement("button");
    closeBtn.className = "btn-outline";
    closeBtn.textContent = "Close";
    closeBtn.addEventListener("click", () => overlay.remove());
    box.appendChild(closeBtn);
    document.body.appendChild(overlay);
    return;
  }

  const filterInput = document.createElement("input");
  filterInput.type = "text";
  filterInput.placeholder = "Filter by name\u2026";
  filterInput.style.cssText = "margin-bottom:10px;padding:8px;border-radius:6px;border:1px solid var(--line);background:var(--bg-1);color:var(--text-hi);";
  box.appendChild(filterInput);

  const list = document.createElement("div");
  list.style.cssText = "overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:6px;";
  box.appendChild(list);

  const renderList = (filterText) => {
    list.innerHTML = "";
    const filtered = apps.filter((a) => a.name.toLowerCase().includes((filterText || "").toLowerCase()));
    if (!filtered.length) {
      const none = document.createElement("div");
      none.className = "empty-msg";
      none.textContent = "No matches.";
      list.appendChild(none);
      return;
    }
    filtered.forEach((app) => {
      const row = document.createElement("button");
      row.className = "btn-outline";
      row.style.textAlign = "left";
      row.textContent = app.name;
      row.addEventListener("click", () => {
        overlay.remove();
        onPick(app);
      });
      list.appendChild(row);
    });
  };
  renderList("");
  filterInput.addEventListener("input", () => renderList(filterInput.value));
  filterInput.focus();

  const cancelBtn = document.createElement("button");
  cancelBtn.className = "btn-link";
  cancelBtn.textContent = "Cancel";
  cancelBtn.style.marginTop = "12px";
  cancelBtn.addEventListener("click", () => overlay.remove());
  box.appendChild(cancelBtn);

  overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });
  document.addEventListener("keydown", function escHandler(e) {
    if (e.key === "Escape") { overlay.remove(); document.removeEventListener("keydown", escHandler); }
  });

  document.body.appendChild(overlay);
}

function openConfirmModal(title, message) {
  return new Promise((resolve) => {
    confirmResolveFn = resolve;
    confirmCursor = 1;
    el("confirm-title").textContent = title;
    el("confirm-message").textContent = message;
    el("confirm-overlay").classList.remove("hidden");
    highlightConfirmCursor();
  });
}

function closeConfirmModal(result) {
  el("confirm-overlay").classList.add("hidden");
  const fn = confirmResolveFn;
  confirmResolveFn = null;
  if (fn) fn(result);
}

function highlightConfirmCursor() {
  el("confirm-yes").classList.toggle("settings-focus", confirmCursor === 0);
  el("confirm-no").classList.toggle("settings-focus", confirmCursor === 1);
}

function handleConfirmOverlayInput(action) {
  if (action === "left" || action === "right") {
    confirmCursor = confirmCursor === 0 ? 1 : 0;
    highlightConfirmCursor();
  } else if (action === "confirm") {
    closeConfirmModal(confirmCursor === 0);
  } else if (action === "back") {
    closeConfirmModal(false);
  }
}

el("confirm-yes").addEventListener("click", () => closeConfirmModal(true));
el("confirm-no").addEventListener("click", () => closeConfirmModal(false));

// Native, remap-independent fallback: listens on window itself (capture
// phase, before the app's own custom keyboard-remapping dispatch) for
// the plain arrow/Enter/Escape keys, guarded by isConfirmOpen() so it
// only acts while this dialog is actually showing. Deliberately NOT
// attached to the overlay element itself - keydown only bubbles through
// actual DOM ancestors of whatever currently has focus, and the overlay
// isn't necessarily one of those, so a listener on it alone could simply
// never fire regardless of capture phase.
window.addEventListener("keydown", (e) => {
  if (!isConfirmOpen()) return;
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    e.preventDefault();
    handleConfirmOverlayInput(e.key === "ArrowLeft" ? "left" : "right");
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    handleConfirmOverlayInput("confirm");
  } else if (e.key === "Escape") {
    e.preventDefault();
    handleConfirmOverlayInput("back");
  }
}, true);

// ---------------- photo menu (Start button over a photo) ----------------
let photoMenuCursor = 0;
const PHOTO_MENU_ITEMS = ["photo-menu-edit", "photo-menu-background", "photo-menu-open-folder", "photo-menu-delete", "photo-menu-cancel"];

function isPhotoMenuOpen() {
  return !el("photo-menu-overlay").classList.contains("hidden");
}

function currentPhotoPath() {
  const cat = state.categories[state.catIndex];
  if (!cat || cat.id !== "photos") return null;
  const item = state.items && state.items[state.selected];
  return item && item.path ? item.path : null;
}

// Belt-and-suspenders guard: the instant the Start menu (or Photo menu,
// which the same Start press can open instead) opens, the very next
// "confirm" dispatch is swallowed here rather than reaching
// activateCurrentSelection() - normally isStartMenuOpen()/isPhotoMenuOpen()
// already prevent that (checked before the plain "confirm" handler ever
// runs), but this closes the gap for a same-tick double-fire from
// whatever triggered the menu open in the first place, so pressing
// Start can never also open/activate whatever was already selected
// underneath it.
let _suppressNextConfirm = false;

function handleMenuStart() {
  if (isPhotoMenuOpen() || isStartMenuOpen() || isMusicSortMenuOpen() || isMusicItemMenuOpen() || isTutorialOpen() || isConfirmOpen() || isOverlayOpen() || isOskCapturing()) return;
  _suppressNextConfirm = true;
  setTimeout(() => { _suppressNextConfirm = false; }, 150);
  const path = currentPhotoPath();
  if (path) {
    photoMenuCursor = 0;
    el("photo-menu-overlay").classList.remove("hidden");
    highlightPhotoMenuCursor();
    return;
  }
  const cat = state.categories[state.catIndex];
  if (cat && cat.kind === "media" && cat.id === "music") {
    openMusicItemMenu();
    return;
  }
  openStartMenu();
}

// ---------------- Music sort menu (Start button, Music section) ----------------
let musicSortMenuCursor = 0;
const MUSIC_SORT_MENU_ITEMS = [
  "music-sort-title-asc", "music-sort-title-desc", "music-sort-artist-asc",
  "music-sort-artist-desc", "music-sort-date-desc", "music-sort-random", "music-sort-cancel",
];
const MUSIC_SORT_MODES = {
  "music-sort-title-asc": "title_asc", "music-sort-title-desc": "title_desc",
  "music-sort-artist-asc": "artist_asc", "music-sort-artist-desc": "artist_desc",
  "music-sort-date-desc": "date_desc", "music-sort-random": "random",
};

function isMusicSortMenuOpen() {
  return !el("music-sort-overlay").classList.contains("hidden");
}

function openMusicSortMenu() {
  const current = (state.settings && state.settings.music_sort_mode) || "title_asc";
  musicSortMenuCursor = Math.max(0, MUSIC_SORT_MENU_ITEMS.findIndex((id) => MUSIC_SORT_MODES[id] === current));
  el("music-sort-overlay").classList.remove("hidden");
  highlightMusicSortMenuCursor();
}

function closeMusicSortMenu() {
  el("music-sort-overlay").classList.add("hidden");
}

function highlightMusicSortMenuCursor() {
  const current = (state.settings && state.settings.music_sort_mode) || "title_asc";
  MUSIC_SORT_MENU_ITEMS.forEach((id, i) => {
    el(id).classList.toggle("settings-focus", i === musicSortMenuCursor);
    el(id).classList.toggle("music-sort-active", MUSIC_SORT_MODES[id] === current);
  });
}

async function activateMusicSortMenuItem() {
  const choice = MUSIC_SORT_MENU_ITEMS[musicSortMenuCursor];
  closeMusicSortMenu();
  if (choice === "music-sort-cancel") return;
  const mode = MUSIC_SORT_MODES[choice];
  if (!mode) return;
  if (mode === "random") state.musicRandomOrder = null; // force a fresh shuffle on explicit re-pick
  state.settings = await api().set_music_sort_mode(mode);
  await refreshItemPanel();
}

function handleMusicSortMenuInput(action) {
  if (action === "up") { musicSortMenuCursor = (musicSortMenuCursor + MUSIC_SORT_MENU_ITEMS.length - 1) % MUSIC_SORT_MENU_ITEMS.length; highlightMusicSortMenuCursor(); }
  else if (action === "down") { musicSortMenuCursor = (musicSortMenuCursor + 1) % MUSIC_SORT_MENU_ITEMS.length; highlightMusicSortMenuCursor(); }
  else if (action === "confirm") activateMusicSortMenuItem();
  else if (action === "back") closeMusicSortMenu();
}

MUSIC_SORT_MENU_ITEMS.forEach((id, i) => {
  el(id).addEventListener("click", (e) => { e.stopPropagation(); musicSortMenuCursor = i; activateMusicSortMenuItem(); });
});

// ---------------- Music item options menu (Start button, Music section) ----------------
// Separate from the sort menu above - this is per-TRACK actions (Open
// Folder, Delete) plus a way into the sort picker ("Sort by..."),
// mirroring how the Photo options menu works for Photos. Start opens
// THIS menu now (see handleMenuStart), not the sort menu directly.
let musicItemMenuCursor = 0;
const MUSIC_ITEM_MENU_ITEMS = ["music-item-menu-sort", "music-item-menu-open-folder", "music-item-menu-delete", "music-item-menu-cancel"];

function isMusicItemMenuOpen() {
  return !el("music-item-menu-overlay").classList.contains("hidden");
}

function openMusicItemMenu() {
  musicItemMenuCursor = 0;
  el("music-item-menu-overlay").classList.remove("hidden");
  highlightMusicItemMenuCursor();
}

function closeMusicItemMenu() {
  el("music-item-menu-overlay").classList.add("hidden");
}

function highlightMusicItemMenuCursor() {
  MUSIC_ITEM_MENU_ITEMS.forEach((id, i) => el(id).classList.toggle("settings-focus", i === musicItemMenuCursor));
}

async function activateMusicItemMenuItem() {
  const choice = MUSIC_ITEM_MENU_ITEMS[musicItemMenuCursor];
  const item = state.items[state.selected];
  closeMusicItemMenu();
  if (choice === "music-item-menu-cancel") return;
  if (choice === "music-item-menu-sort") {
    openMusicSortMenu();
    return;
  }
  if (!item || !item.path) return;
  if (choice === "music-item-menu-open-folder") {
    const res = await api().open_containing_folder(item.path);
    if (res && res.ok === false) showToast(`Couldn't open the folder: ${res.error}`);
  } else if (choice === "music-item-menu-delete") {
    const label = item.title || item.name || "this track";
    const ok = await openConfirmModal("Delete this item?", `"${label}" will be moved to the Recycle Bin.`);
    if (!ok) return;
    const res = await api().delete_media_item("music", item.path);
    if (res && res.ok === false) showToast(`Couldn't delete: ${res.error}`);
    else { showToast("Moved to Recycle Bin."); await refreshItemPanel(); }
  }
}

function handleMusicItemMenuInput(action) {
  if (action === "up") { musicItemMenuCursor = (musicItemMenuCursor + MUSIC_ITEM_MENU_ITEMS.length - 1) % MUSIC_ITEM_MENU_ITEMS.length; highlightMusicItemMenuCursor(); }
  else if (action === "down") { musicItemMenuCursor = (musicItemMenuCursor + 1) % MUSIC_ITEM_MENU_ITEMS.length; highlightMusicItemMenuCursor(); }
  else if (action === "confirm") activateMusicItemMenuItem();
  else if (action === "back") closeMusicItemMenu();
}

MUSIC_ITEM_MENU_ITEMS.forEach((id, i) => {
  el(id).addEventListener("click", (e) => { e.stopPropagation(); musicItemMenuCursor = i; activateMusicItemMenuItem(); });
});

// Sorts a freshly-scanned music item list according to the persisted
// music_sort_mode setting. Client-side (not part of scan_library) since
// every field it sorts by is already present on each item and this
// keeps the sort order changeable instantly without a rescan.
function sortMusicItems(items, modeOverride) {
  const mode = modeOverride || (state.settings && state.settings.music_sort_mode) || "title_asc";
  const collator = (a, b) => String(a || "").localeCompare(String(b || ""), undefined, { sensitivity: "base" });
  const sorted = items.slice();
  if (mode === "title_desc") {
    sorted.sort((a, b) => collator(b.title, a.title));
  } else if (mode === "artist_asc") {
    sorted.sort((a, b) => collator(a.artist, b.artist) || collator(a.title, b.title));
  } else if (mode === "artist_desc") {
    sorted.sort((a, b) => collator(b.artist, a.artist) || collator(a.title, b.title));
  } else if (mode === "date_desc") {
    sorted.sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
  } else if (mode === "random") {
    if (modeOverride === "random" || !state.musicRandomOrder) {
      // Fresh Fisher-Yates shuffle - either this is the one-off "play a
      // random song" case (always wants a genuinely new shuffle, not a
      // browsing order), or there's no cached order yet for the
      // persisted Random sort mode (first time it's been applied this
      // session, or it was just explicitly re-picked - see
      // activateMusicSortMenuItem, which clears the cache on purpose).
      const shuffled = sorted.slice();
      for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
      }
      if (modeOverride !== "random") {
        // Cache the ORDER (paths), not the item objects themselves - the
        // underlying item list gets refetched/rebuilt on every refresh,
        // so caching objects would just go stale; caching the path
        // order lets it be reapplied to a freshly-fetched item list.
        state.musicRandomOrder = shuffled.map((it) => it.path);
      }
      return shuffled;
    }
    // Persisted Random mode, already shuffled once this session -
    // reapply that SAME order rather than reshuffling again, so the
    // list stays stable across incidental re-renders. Anything not in
    // the cached order (e.g. a newly added file) gets appended at the
    // end rather than silently dropped.
    const byPath = new Map(sorted.map((it) => [it.path, it]));
    const ordered = [];
    state.musicRandomOrder.forEach((p) => {
      if (byPath.has(p)) { ordered.push(byPath.get(p)); byPath.delete(p); }
    });
    byPath.forEach((it) => ordered.push(it));
    return ordered;
  } else {
    sorted.sort((a, b) => collator(a.title, b.title)); // title_asc, the default
  }
  return sorted;
}

function closePhotoMenu() {
  el("photo-menu-overlay").classList.add("hidden");
}

function highlightPhotoMenuCursor() {
  PHOTO_MENU_ITEMS.forEach((id, i) => el(id).classList.toggle("settings-focus", i === photoMenuCursor));
}

async function activatePhotoMenuItem() {
  const path = currentPhotoPath();
  const choice = PHOTO_MENU_ITEMS[photoMenuCursor];
  closePhotoMenu();
  if (!path) return;
  if (choice === "photo-menu-edit") {
    const res = await api().edit_photo(path);
    if (res && res.ok === false) showToast(`Couldn't open Paint: ${res.error}`);
  } else if (choice === "photo-menu-background") {
    const res = await api().set_background_from_path(path);
    if (res) { state.settings = res; showToast("Background updated"); applyBackground(res); }
  } else if (choice === "photo-menu-open-folder") {
    const res = await api().open_containing_folder(path);
    if (res && res.ok === false) showToast(`Couldn't open the folder: ${res.error}`);
  } else if (choice === "photo-menu-delete") {
    const item = state.items[state.selected];
    const label = (item && (item.title || item.name)) || "this photo";
    const ok = await openConfirmModal("Delete this item?", `"${label}" will be moved to the Recycle Bin.`);
    if (!ok) return;
    const res = await api().delete_media_item("photos", path);
    if (res && res.ok === false) showToast(`Couldn't delete: ${res.error}`);
    else { showToast("Moved to Recycle Bin."); await refreshItemPanel(); }
  }
}

function handlePhotoMenuInput(action) {
  if (action === "up") { photoMenuCursor = (photoMenuCursor + PHOTO_MENU_ITEMS.length - 1) % PHOTO_MENU_ITEMS.length; highlightPhotoMenuCursor(); }
  else if (action === "down") { photoMenuCursor = (photoMenuCursor + 1) % PHOTO_MENU_ITEMS.length; highlightPhotoMenuCursor(); }
  else if (action === "confirm") activatePhotoMenuItem();
  else if (action === "back") closePhotoMenu();
}

el("photo-menu-edit").addEventListener("click", (e) => { e.stopPropagation(); photoMenuCursor = 0; activatePhotoMenuItem(); });
el("photo-menu-background").addEventListener("click", (e) => { e.stopPropagation(); photoMenuCursor = 1; activatePhotoMenuItem(); });
el("photo-menu-open-folder").addEventListener("click", (e) => { e.stopPropagation(); photoMenuCursor = 2; activatePhotoMenuItem(); });
el("photo-menu-delete").addEventListener("click", (e) => { e.stopPropagation(); photoMenuCursor = 3; activatePhotoMenuItem(); });
el("photo-menu-cancel").addEventListener("click", (e) => { e.stopPropagation(); closePhotoMenu(); });

// ---------------- Start menu (Start button, everywhere but photos) ----------------
let startMenuCursor = 0;
const START_MENU_ITEMS_BASE = [
  "start-menu-tutorial", "start-menu-close-section", "start-menu-osm",
  "start-menu-minimize", "start-menu-close-launcher", "start-menu-cancel",
];
let startMenuItems = START_MENU_ITEMS_BASE;

function isStartMenuOpen() {
  return !el("start-menu-overlay").classList.contains("hidden");
}

// Controller Bridge (see xinput_to_keyboard.py) only makes sense with an
// actual Apps/Games item selected to enable it for - shown/hidden in the
// Start menu depending on context rather than being permanently there.
function _controllerBridgeEligibleItem() {
  const cat = state.categories[state.catIndex];
  if (!cat || cat.kind !== "exe_list" || (cat.id !== "apps" && cat.id !== "games")) return null;
  const item = state.items[state.selected];
  if (!item || !item.path || item.__gameLibrary || item.__recent || item.__chatPlugin) return null;
  return item;
}

// Delete (send to Recycle Bin) - only meaningful for a real file/folder:
// the Desktop section's own items, a plugin_list item that exposes a
// real path (currently just the "Start" plugin's shortcuts - see
// Plugins/Start/backend.py), or a Photos/Videos/Music item. Returns
// {item, target, pluginId?, mediaKind?} - target is "desktop" (deleted
// via delete_desktop_item), "plugin" (delete_plugin_item, pluginId
// set), or "media" (delete_media_item, mediaKind set to which section).
function _deleteEligibleItem() {
  const cat = state.categories[state.catIndex];
  if (!cat) return null;
  const item = state.items[state.selected];
  if (!item || !item.path || item.__chatPlugin) return null;
  if (cat.kind === "desktop_list") return { item, target: "desktop" };
  if (cat.kind === "plugin_list") return { item, target: "plugin", pluginId: cat.pluginId };
  if (cat.kind === "media") return { item, target: "media", mediaKind: cat.id };
  return null;
}

// Open Folder - Photos/Videos/Music sections only, as asked for; opens
// Windows Explorer with the file highlighted (the standard "show in
// folder" behavior), rather than just the folder with nothing selected.
function _openFolderEligibleItem() {
  const cat = state.categories[state.catIndex];
  if (!cat || cat.kind !== "media") return null;
  const item = state.items[state.selected];
  if (!item || !item.path) return null;
  return item;
}

// Open in Meridian Paint - Photos section, or the Downloads plugin (see
// Plugins/Downloads/backend.py), with an actual image file selected.
// Deliberately checks the extension rather than trying every item (a
// stray non-image landing on the Photos section's item list, or most
// things in Downloads, wouldn't make sense to hand to a paint program).
const _PAINT_OPENABLE_EXT = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"];
function _openInPaintEligibleItem() {
  const cat = state.categories[state.catIndex];
  if (!cat) return null;
  const item = state.items[state.selected];
  if (!item || !item.path) return null;
  const isPhotos = cat.kind === "media" && cat.id === "photos";
  const isDownloads = cat.kind === "plugin_list" && cat.pluginId === "downloads";
  if (!isPhotos && !isDownloads) return null;
  const lower = item.path.toLowerCase();
  if (!_PAINT_OPENABLE_EXT.some((ext) => lower.endsWith(ext))) return null;
  return item;
}

function openStartMenu() {
  startMenuCursor = 0;
  const bridgeItem = _controllerBridgeEligibleItem();
  const bridgeBtn = el("start-menu-controller-bridge");
  if (bridgeItem) {
    bridgeBtn.classList.remove("hidden");
    const enabled = (state.settings && state.settings.controller_bridge_items || []).includes(bridgeItem.path);
    bridgeBtn.textContent = enabled
      ? `Disable Controller Bridge for "${bridgeItem.title || bridgeItem.name}"`
      : `Enable Controller Bridge for "${bridgeItem.title || bridgeItem.name}" (needs a keyboard-controlled app)`;
    startMenuItems = START_MENU_ITEMS_BASE.slice();
    startMenuItems.splice(1, 0, "start-menu-controller-bridge");
  } else {
    bridgeBtn.classList.add("hidden");
    startMenuItems = START_MENU_ITEMS_BASE.slice();
  }
  const deleteEligible = _deleteEligibleItem();
  const deleteBtn = el("start-menu-delete");
  if (deleteEligible) {
    deleteBtn.classList.remove("hidden");
    const { item } = deleteEligible;
    deleteBtn.textContent = `Delete "${item.title || item.name || item.label}" (Recycle Bin)`;
    startMenuItems.splice(1, 0, "start-menu-delete");
  } else {
    deleteBtn.classList.add("hidden");
  }
  const openFolderItem = _openFolderEligibleItem();
  const openFolderBtn = el("start-menu-open-folder");
  if (openFolderItem) {
    openFolderBtn.classList.remove("hidden");
    openFolderBtn.textContent = `Open Folder ("${openFolderItem.title || openFolderItem.name || openFolderItem.label}")`;
    startMenuItems.splice(1, 0, "start-menu-open-folder");
  } else {
    openFolderBtn.classList.add("hidden");
  }
  const paintItem = _openInPaintEligibleItem();
  const paintBtn = el("start-menu-open-paint");
  if (paintItem) {
    paintBtn.classList.remove("hidden");
    paintBtn.textContent = `Open "${paintItem.title || paintItem.name || paintItem.label}" in Meridian Paint`;
    startMenuItems.splice(1, 0, "start-menu-open-paint");
  } else {
    paintBtn.classList.add("hidden");
  }
  el("start-menu-overlay").classList.remove("hidden");
  highlightStartMenuCursor();
}

function closeStartMenu() {
  el("start-menu-overlay").classList.add("hidden");
}

function highlightStartMenuCursor() {
  startMenuItems.forEach((id, i) => el(id).classList.toggle("settings-focus", i === startMenuCursor));
}

async function activateStartMenuItem() {
  const choice = startMenuItems[startMenuCursor];
  if (choice === "start-menu-cancel") { closeStartMenu(); return; }
  if (choice === "start-menu-tutorial") { closeStartMenu(); openTutorial(); return; }
  if (choice === "start-menu-close-section") { closeStartMenu(); closeCurrentSection(); return; }
  if (choice === "start-menu-controller-bridge") {
    closeStartMenu();
    const bridgeItem = _controllerBridgeEligibleItem();
    if (!bridgeItem) return;
    const res = await api().toggle_controller_bridge_for_item(bridgeItem.path);
    if (res) state.settings = res;
    const enabledNow = (state.settings && state.settings.controller_bridge_items || []).includes(bridgeItem.path);
    showToast(enabledNow
      ? `Controller Bridge will run while "${bridgeItem.title || bridgeItem.name}" is open.`
      : `Controller Bridge disabled for "${bridgeItem.title || bridgeItem.name}".`);
    return;
  }
  if (choice === "start-menu-delete") {
    closeStartMenu();
    const eligible = _deleteEligibleItem();
    if (!eligible) return;
    const { item, target, pluginId, mediaKind } = eligible;
    const ok = await openConfirmModal(
      "Delete this item?",
      `"${item.title || item.name || item.label}" will be moved to the Recycle Bin.`,
    );
    if (!ok) return;
    let res;
    if (target === "plugin") res = await api().delete_plugin_item(pluginId, item.id);
    else if (target === "media") res = await api().delete_media_item(mediaKind, item.path);
    else res = await api().delete_desktop_item(item.path);
    if (res && res.ok === false) showToast(`Couldn't delete: ${res.error}`);
    else { showToast(`Moved to Recycle Bin.`); await refreshItemPanel(); }
    return;
  }
  if (choice === "start-menu-open-folder") {
    closeStartMenu();
    const item = _openFolderEligibleItem();
    if (!item) return;
    const res = await api().open_containing_folder(item.path);
    if (res && res.ok === false) showToast(`Couldn't open the folder: ${res.error}`);
    return;
  }
  if (choice === "start-menu-open-paint") {
    closeStartMenu();
    const item = _openInPaintEligibleItem();
    if (!item) return;
    const res = await api().open_picture_in_paint(item.path);
    if (res && res.ok === false) showToast(`Couldn't open in Meridian Paint: ${res.error}`);
    return;
  }
  if (choice === "start-menu-osm") {
    closeStartMenu();
    const res = await api().toggle_onscreenmenu();
    if (res && res.ok === false) showToast(`Couldn't toggle onscreenmenu: ${res.error}`);
    return;
  }
  if (choice === "start-menu-minimize") { closeStartMenu(); await api().minimize_launcher(); return; }
  if (choice === "start-menu-close-launcher") { closeStartMenu(); await api().quit_app(); return; }
}

function handleStartMenuInput(action) {
  if (action === "up") { startMenuCursor = (startMenuCursor + startMenuItems.length - 1) % startMenuItems.length; highlightStartMenuCursor(); }
  else if (action === "down") { startMenuCursor = (startMenuCursor + 1) % startMenuItems.length; highlightStartMenuCursor(); }
  else if (action === "confirm") activateStartMenuItem();
  else if (action === "back") closeStartMenu();
}

[...START_MENU_ITEMS_BASE, "start-menu-controller-bridge", "start-menu-delete", "start-menu-open-folder", "start-menu-open-paint"].forEach((id) => {
  el(id).addEventListener("click", (e) => {
    e.stopPropagation();
    const i = startMenuItems.indexOf(id);
    if (i !== -1) { startMenuCursor = i; activateStartMenuItem(); }
  });
});

// "Close Section": hides the options/subfolder/thumbnail panels and moves
// focus to the Sections bar, without unloading whatever's actually loaded
// (an embedded Explorer/Browser/webapp plugin keeps running - this is
// purely a visibility/focus action). They come back automatically the
// next time any section is opened, since that always re-runs
// refreshItemPanel/renderItemList, which un-hides whatever that section
// actually uses.
function closeCurrentSection() {
  el("item-panel").classList.add("hidden");
  setSubfolderNavHidden(true);
  el("preview-pane").classList.add("hidden");
  state.sectionManuallyClosed = true;
  state.radialFocus = "sections";
  document.body.dataset.radialFocus = "sections";
  renderCategories();
}

// ---------------- Controls Tutorial (from the Start menu) ----------------
const TUTORIAL_PAGES = [
  { title: "Meridian Launcher Controls", key: "launcher" },
  { title: "Meridian Game Library Controls", key: "gamelibrary" },
  { title: "Meridian Explorer / FileBrowse Controls", key: "explorer" },
  { title: "onscreenmenu Controls", key: "osm" },
  { title: "CyberDeckBrowser / Meridian NetBrowse Controls", key: "cyberdeck" },
];

const TUTORIAL_TEXT = {
  launcher:
`Controller:
  A - Confirm / select the highlighted item
  B - Back / close overlays
  D-pad or Left stick - Navigate lists and sections
  Y (tap) - Subfolder/filter side panel
  Start (over a photo) - Edit / Set as Background popup
  Start (elsewhere) - This menu
  X (tap) - Jump to/from the open-programs bar
  X (hold 2s) - Close the highlighted task
  LB / RB - Previous / next music track
  LB+RB - Random track
  R3 (click right stick) - Stop music
  Right stick left/right - Rewind / fast-forward 10 seconds
  Start+Select - Bring Meridian Launcher to the foreground

Keyboard:
  Enter - Confirm    Space - Back    Arrow keys - Navigate
  \\ (backslash) - Subfolder/filter panel
  ContextMenu key - Same as Start on a controller
  Shift - Jump to/from the open-programs bar
  Delete - Close the highlighted task

Mouse/Click: click any section, row, or button directly to activate it.`,

  gamelibrary:
`Controller:
  A - Launch/Install the highlighted game
  B - Back
  D-pad or Left stick - Navigate
  Y - Hide/unhide, rename, and other game options
  Start - Program menu (quick actions, close program)
  X - Open-programs bar, same as Meridian Launcher

Keyboard:
  Enter - Confirm    Space/Escape - Back    Arrow keys - Navigate

Mouse/Click: click a game tile to launch/install it; click its corner
options icon (if shown) for hide/rename/etc.`,

  explorer:
`Controller:
  A - Open the highlighted file/folder
  B - Back / up a folder
  D-pad or Left stick - Navigate within a pane
  D-pad Left/Right or Tab - Switch panes
  Y or Start - Options popup (Open/Copy/Cut/Paste/Rename/Delete/etc,
    including Exit Program)
  LB/RB - Switch pane    LT/RT - Fast scroll
  Hold Select - Multi-select    R3 - Select all

In the built-in text/hex editor:
  A - Type the highlighted key    B - Backspace/Delete
  Y - Shift (one-shot)    LB/RB - Move cursor left/right
  LT/RT - Move cursor up/down    Start - Save

Keyboard: works directly - arrows move, Enter opens, Ctrl+S saves in the
editor, Esc backs out/exits.

Mouse/Click: click any file/folder/button directly.`,

  osm:
`onscreenmenu is a transparent controller overlay used to navigate native
Windows dialogs (like "Open With" pickers) that would otherwise need a
mouse or keyboard.

Controller:
  Left stick - Move the on-screen cursor
  A - Left click    B - Right click
  Y - Shortcuts menu    X - Key-combo menu (also has Virtual Keyboard
    and Close Onscreenmenu)
  R3 (click right stick) - Hibernate/wake

Keyboard/Mouse: the real keyboard and mouse still work normally alongside
onscreenmenu at any time.`,

  cyberdeck:
`Controller:
  Left stick - Move the virtual mouse cursor (triggers boost its speed)
  A - Left click    B - Right click
  Y - Browser menu (History/Downloads/Bookmarks/Translate/Settings/Find)
  X - Tools menu (Refresh/Enter URL/Previous/Next/New Tab/Close Tab/
    Close Browser or Exit Program)
  On-screen keyboard appears automatically in text fields.

Keyboard/Mouse: the real keyboard and mouse work normally too - typing
into a focused text field, or clicking directly, both work as expected.`,
};

let tutorialIndex = 0;

function isTutorialOpen() {
  return !el("tutorial-overlay").classList.contains("hidden");
}

function openTutorial() {
  tutorialIndex = 0;
  renderTutorialPage();
  el("tutorial-overlay").classList.remove("hidden");
}

function renderTutorialPage() {
  const page = TUTORIAL_PAGES[tutorialIndex];
  el("tutorial-title").textContent = page.title;
  el("tutorial-body").textContent = TUTORIAL_TEXT[page.key];
}

function handleTutorialInput(action) {
  if (action === "left") {
    tutorialIndex = (tutorialIndex + TUTORIAL_PAGES.length - 1) % TUTORIAL_PAGES.length;
    renderTutorialPage();
  } else if (action === "right") {
    tutorialIndex = (tutorialIndex + 1) % TUTORIAL_PAGES.length;
    renderTutorialPage();
  } else if (action === "back") {
    el("tutorial-overlay").classList.add("hidden");
    openStartMenu();
  }
}

// ---------------- settings ----------------

async function buildPluginsSettingsBlock() {
  const wrap = document.createElement("div");
  wrap.className = "settings-block";
  wrap.innerHTML = `<h3>Plugins</h3>
    <p class="settings-note">Custom sections auto-discovered from the Plugins/ folder next to Meridian Launcher. Each is hidden by default — enable the ones you want to show up in the sections bar, right after your custom sections. New plugin folders are also auto-scanned every time Meridian Launcher starts.</p>`;

  const rescanBtn = document.createElement("button");
  rescanBtn.className = "btn-outline";
  rescanBtn.textContent = "Rescan Plugins folder";
  rescanBtn.addEventListener("click", async () => {
    await api().rescan_plugins();
    await refreshAfterSettingsChange();
  });
  wrap.appendChild(rescanBtn);

  const plugins = await api().list_plugins();
  if (!plugins.length) {
    const empty = document.createElement("div");
    empty.className = "empty-msg";
    empty.style.marginTop = "10px";
    empty.textContent = "No plugins found in the Plugins/ folder yet.";
    wrap.appendChild(empty);
    return wrap;
  }

  plugins.forEach((p) => {
    const row = document.createElement("div");
    row.className = "settings-row";
    row.style.marginTop = "10px";
    const toggle = document.createElement("div");
    toggle.className = "toggle-switch" + (p.visible ? " on" : "");
    toggle.innerHTML = `<div class="knob"></div>`;
    toggle.addEventListener("click", async () => {
      const turningOn = !p.visible;
      await api().set_plugin_visible(p.id, turningOn);
      if (turningOn && (p.id === "start" || p.id === "downloads")) {
        // Fire-and-forget prefetch, same reasoning as the Desktop
        // section toggle above - ready with icons on first visit
        // instead of showing blank/loading then.
        api().list_plugin_items(p.id).catch(() => {});
      }
      await refreshAfterSettingsChange();
    });
    row.appendChild(toggle);
    const typeLabel = p.type === "addon" ? "Plug-on" : p.type === "option" ? "Option" : p.type === "webapp" ? "Webapp" : "List";
    const sectionSuffix = p.section ? ` → ${p.section}` : "";
    row.appendChild(document.createTextNode(`${p.label} (${typeLabel}${sectionSuffix}) — ${p.visible ? "Shown" : "Hidden"}`));
    wrap.appendChild(row);
  });

  return wrap;
}

function buildToggleBlock(title, isOn, onChange, note) {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.innerHTML = `<h3>${escapeHtml(title)}</h3>`;
  const row = document.createElement("div");
  row.className = "settings-row";
  const toggle = document.createElement("div");
  toggle.className = "toggle-switch" + (isOn ? " on" : "");
  toggle.innerHTML = `<div class="knob"></div>`;
  toggle.addEventListener("click", onChange);
  row.appendChild(toggle);
  row.appendChild(document.createTextNode(note || (isOn ? "Enabled" : "Disabled")));
  block.appendChild(row);
  return block;
}

// The Settings landing screen: the five options as a normal item list, so
// it navigates exactly like any other section's list (up/down + A).
function renderSettingsMenu() {
  const panel = el("item-panel");
  panel.innerHTML = "";
  const list = document.createElement("div");
  list.className = "item-list";
  SETTINGS_OPTIONS.forEach(([key, label, sub], i) => {
    const row = document.createElement("div");
    row.className = "item-row" + (i === state.settingsMenuIndex ? " selected" : "");
    row.innerHTML = `<div class="row-visual">${ICONS.settings || ""}</div>
      <div class="row-text"><div class="title">${label}</div><div class="subtitle">${sub}</div></div>`;
    row.addEventListener("click", () => openSettingsGroup(key));
    list.appendChild(row);
  });
  panel.appendChild(list);
}

// Enter one of the five Settings options.
function openSettingsGroup(key) {
  state.settingsCursor = 0;
  state.colorGridIndex = null;
  renderSettings(key);
}

// Settings > Addon Settings. One built-in block (CyberRadial's
// subfolder filler image) that used to live scattered elsewhere. Below
// that: every Plugins/<name>/settings.json and themes/<name>/
// settings.json discovered on disk, rendered generically from their own
// schema - see addon_settings.py for the full scanning/schema story.
async function renderAddonSettingsBlocks(c, settings) {
  // ---- CyberRadial: subfolder bar filler image ----
  const fillerBlock = document.createElement("div");
  fillerBlock.className = "settings-block";
  const fillerGif = settings.subfolder_filler_gif;
  fillerBlock.innerHTML = `<h3>Subfolder Bar Filler (CyberRadial theme)</h3>
    <p class="settings-note">Shown in the subfolder bar for sections that don't have real subfolder navigation of their own. ${fillerGif ? "Using a custom image." : "Using the default."}</p>`;
  const fillerRow = document.createElement("div");
  fillerRow.className = "settings-row";
  const chooseFillerBtn = document.createElement("button");
  chooseFillerBtn.className = "btn-link";
  chooseFillerBtn.textContent = "Choose custom image\u2026";
  chooseFillerBtn.addEventListener("click", async () => {
    state.settings = await api().set_subfolder_filler_gif();
    renderSettings();
  });
  fillerRow.appendChild(chooseFillerBtn);
  if (fillerGif) {
    const resetFillerBtn = document.createElement("button");
    resetFillerBtn.className = "btn-link";
    resetFillerBtn.textContent = "Reset to default";
    resetFillerBtn.addEventListener("click", async () => {
      state.settings = await api().clear_subfolder_filler_gif();
      renderSettings();
    });
    fillerRow.appendChild(resetFillerBtn);
  }
  fillerBlock.appendChild(fillerRow);
  c.appendChild(fillerBlock);

  // ---- Scanned Plugins/*/settings.json and themes/*/settings.json ----
  let groups = [];
  try { groups = await api().list_addon_setting_groups(); } catch (e) { groups = []; }
  if (!groups.length) {
    const note = document.createElement("p");
    note.className = "settings-note";
    note.textContent = "No plugin, plug-on, or theme has its own settings.json yet - see addon_settings.py for the schema a Plugins/<name>/ or themes/<name>/ folder can drop in to show up here.";
    c.appendChild(note);
    return;
  }
  groups.forEach((group) => {
    const block = document.createElement("div");
    block.className = "settings-block";
    const sourceLabel = group.source === "plugin" ? "Plugin" : "Theme";
    block.innerHTML = `<h3>${escapeHtml(group.title)} (${sourceLabel})</h3>`;
    group.fields.forEach((field) => {
      const row = document.createElement("div");
      row.className = "settings-row";
      row.style.marginTop = "8px";
      if (field.type === "toggle") {
        const isOn = !!field.value;
        const toggle = document.createElement("div");
        toggle.className = "toggle-switch" + (isOn ? " on" : "");
        toggle.innerHTML = `<div class="knob"></div>`;
        toggle.addEventListener("click", async () => {
          state.settings = await api().set_addon_setting_value(group.id, field.key, !isOn);
          renderSettings();
        });
        row.appendChild(toggle);
        row.appendChild(document.createTextNode(field.label || field.key));
      } else if (field.type === "choice") {
        const label = document.createElement("span");
        const current = field.choices.find((ch) => ch[0] === field.value) || field.choices[0];
        label.textContent = `${field.label || field.key}: ${current ? current[1] : field.value}`;
        const btn = document.createElement("button");
        btn.className = "btn-link";
        btn.textContent = "Change";
        btn.addEventListener("click", async () => {
          const idx = field.choices.findIndex((ch) => ch[0] === field.value);
          const next = field.choices[(idx + 1) % field.choices.length];
          state.settings = await api().set_addon_setting_value(group.id, field.key, next[0]);
          renderSettings();
        });
        row.appendChild(label);
        row.appendChild(btn);
      } else if (field.type === "file") {
        const label = document.createElement("span");
        label.textContent = `${field.label || field.key}: ${field.value ? escapeHtml(String(field.value)) : "(default)"}`;
        const btn = document.createElement("button");
        btn.className = "btn-link";
        btn.textContent = "Choose\u2026";
        btn.addEventListener("click", async () => {
          state.settings = await api().pick_addon_setting_file(group.id, field.key, field.accept || "");
          renderSettings();
        });
        row.appendChild(label);
        row.appendChild(btn);
      } else if (field.type === "text") {
        const label = document.createElement("span");
        label.textContent = `${field.label || field.key}: `;
        const input = document.createElement("input");
        input.type = "text";
        input.value = field.value || "";
        input.className = "addon-setting-text-input";
        input.addEventListener("focus", () => showOskFor(input));
        input.addEventListener("blur", async () => {
          hideOsk();
          state.settings = await api().set_addon_setting_value(group.id, field.key, input.value);
        });
        row.appendChild(label);
        row.appendChild(input);
      }
      block.appendChild(row);
    });
    c.appendChild(block);
  });
}

async function renderSettings(group) {
  // Settings renders EITHER its option list (group == null/"menu") or one
  // group's blocks. Rather than reorder the ~550 lines that build every
  // block, each is tagged with the group that's "current" as it's appended
  // (see the _settingsGroup(...) calls below) and only matching ones are kept.
  const wantGroup = group || state.settingsGroup || "menu";
  state.settingsGroup = wantGroup;

  if (wantGroup === "menu") {
    renderSettingsMenu();
    return;
  }

  // Preserve scroll position across the rebuild so actions like picking a
  // theme color (which re-render the whole panel) don't jump back to top.
  const _prevScroll = (() => { const ip = el("item-panel"); return ip ? ip.scrollTop : 0; })();
  const settings = await api().get_settings();
  state.settings = settings;
  // whether Meridian Explorer.exe is present (gates the folder-routing toggle)
  let mxAvailable = true;
  try { mxAvailable = await api().meridian_explorer_available(); } catch (e) { mxAvailable = true; }
  applyLayoutClass();
  const panel = el("item-panel");
  panel.innerHTML = "";
  const _realC = document.createElement("div");

  // "c" is a proxy: everything appended to it is tagged with the current
  // group and only kept if it matches the requested group.
  let _curGroup = "controls";
  const c = {
    _cur: () => _curGroup,
    appendChild: (node) => {
      if (wantGroup === "all" || _curGroup === wantGroup) {
        _realC.appendChild(node);
      }
      return node;
    },
  };
  const _settingsGroup = (g) => { _curGroup = g; };

  // controller controls quick reference — always the first settings block
  const controlsBlock = document.createElement("div");
  controlsBlock.className = "settings-block";
  controlsBlock.innerHTML = `<h3>Controller controls</h3>\n    <div id="controller-status-line" class="controller-status">Controller API: checking\u2026</div>
    <p class="settings-note">What each controller button does in Meridian Launcher. Confirm/Back/directions can be remapped in controller_controls.json; combos always use the physical buttons listed. Keyboard: Enter confirm, Space back, arrow keys navigate, the \\ key jumps to the side panel, Shift jumps to the open-programs bar, Delete closes the highlighted task there.</p>
    <div class="controls-grid"><div class="controls-row"><span class="controls-btn">A</span><span class="controls-desc">Confirm / select the highlighted item</span></div><div class="controls-row"><span class="controls-btn">B</span><span class="controls-desc">Back / close overlays</span></div><div class="controls-row"><span class="controls-btn">D-pad / Left stick</span><span class="controls-desc">Navigate — up/down through lists, left/right across sections</span></div><div class="controls-row"><span class="controls-btn">Y (tap)</span><span class="controls-desc">Jump to the subfolder / filter side panel</span></div><div class="controls-row"><span class="controls-btn">X (tap)</span><span class="controls-desc">Jump to / away from the open-programs bar (shown in every theme)</span></div><div class="controls-row"><span class="controls-btn">X (hold 2 seconds)</span><span class="controls-desc">Close the highlighted task on the open-programs bar (asks first unless "Close tasks without prompt" is on)</span></div><div class="controls-row"><span class="controls-btn">LB</span><span class="controls-desc">Previous music track</span></div><div class="controls-row"><span class="controls-btn">RB</span><span class="controls-desc">Next music track</span></div><div class="controls-row"><span class="controls-btn">LB + RB (together)</span><span class="controls-desc">Play a random track</span></div><div class="controls-row"><span class="controls-btn">R3 (click right stick)</span><span class="controls-desc">Stop music</span></div><div class="controls-row"><span class="controls-btn">Right stick left/right</span><span class="controls-desc">Rewind / fast-forward 10 seconds</span></div><div class="controls-row"><span class="controls-btn">Start (Music section)</span><span class="controls-desc">Sort menu</span></div><div class="controls-row"><span class="controls-btn">Start + Back (together)</span><span class="controls-desc">Bring Meridian Launcher to the foreground</span></div><div class="controls-row"><span class="controls-btn">Y (hold 45 seconds)</span><span class="controls-desc">Exit kiosk mode</span></div><div class="controls-row"><span class="controls-btn">Up Up Down Down Left Right Left Right B A (D-pad)</span><span class="controls-desc">Kiosk-mode exit code, works any time</span></div></div>`;
  c.appendChild(controlsBlock);
  setTimeout(updateControllerStatusLine, 0);

  // Input backend: cycles xinput (default) -> gameinput -> directinput ->
  // sdl3 -> joycon_pair -> auto -> xinput... XInput is the default because
  // it's the plain, stable, fully-public API and correctly reports every
  // button/trigger/stick; GameInput's vtable-slot probing has only ever
  // reliably decoded buttons, not sticks/triggers, on real hardware.
  // PlayStation controllers (DualShock 4 / DualSense) don't speak XInput
  // at all — "Auto" (or DirectInput/SDL3 directly) is what picks those up,
  // with correct Cross/Circle/Square/Triangle button mapping either way.
  // joycon_pair is deliberately NOT part of "Auto"'s chain (unlike every
  // other backend here) - see JoyConPairGamepad's docstring in
  // gameinput_api.py for why its button mapping is best-effort/unverified
  // rather than something safe to guess into automatically.
  const INPUT_BACKEND_ORDER = ["xinput", "gameinput", "directinput", "sdl3", "joycon_pair", "browser_gamepad", "auto"];
  const INPUT_BACKEND_LABEL = {
    xinput: "XInput (default — plain, stable, all buttons/triggers/sticks work; Xbox-compatible controllers only)",
    gameinput: "GameInput (uses gameinput_native if built; falls back to a less reliable method otherwise - see gameinput_native/README.md)",
    directinput: "DirectInput (for older/exotic controllers XInput doesn't recognize, including PlayStation DualShock 4 / DualSense)",
    sdl3: "SDL3 (needs SDL3.dll present next to the exe or on PATH; also covers PlayStation controllers)",
    joycon_pair: "Joy-Con Pair (combines a connected left + right Nintendo Joy-Con into one controller — experimental, button mapping unverified on real hardware)",
    browser_gamepad: "Browser Gamepad API (reads the controller via the web browser's own Gamepad API instead of native code — has been found to keep working inside Windows' Xbox Full Screen Experience when the others don't)",
    auto: "Auto (tries XInput, then GameInput, then DirectInput, then SDL3 — recommended for PlayStation controllers, since it finds them automatically)",
  };
  const currentBackend = settings.input_backend || "xinput";
  const ibBlock = document.createElement("div");
  ibBlock.className = "settings-block";
  ibBlock.innerHTML = `<h3>Controller input backend</h3>
    <p class="settings-note">${escapeHtml(INPUT_BACKEND_LABEL[currentBackend] || currentBackend)}</p>`;
  const ibBtn = document.createElement("button");
  ibBtn.className = "btn-outline";
  ibBtn.textContent = `Switch backend (currently: ${currentBackend})`;
  ibBtn.addEventListener("click", async () => {
    const next = INPUT_BACKEND_ORDER[(INPUT_BACKEND_ORDER.indexOf(currentBackend) + 1) % INPUT_BACKEND_ORDER.length];
    state.settings = await api().set_input_backend(next);
    if (next === "browser_gamepad") requestAnimationFrame(_pollBrowserGamepad);
    renderSettings();
  });
  ibBlock.appendChild(ibBtn);
  c.appendChild(ibBlock);

  // Controller debugger — live diagnostics, refreshed while it's on screen.
  const dbgBlock = document.createElement("div");
  dbgBlock.className = "settings-block";
  dbgBlock.innerHTML = `<h3>Controller debugger</h3>
    <p class="settings-note">Live view of the input pipeline. Press buttons and move the sticks \u2014 if "last action" and the raw state update, input is reaching the app.</p>
    <pre id="controller-debug" class="controller-debug">collecting\u2026</pre>`;
  const dbgReset = document.createElement("button");
  dbgReset.className = "btn-link";
  dbgReset.textContent = "Reset counters";
  dbgReset.addEventListener("click", async () => { await api().reset_controller_debug(); updateControllerDebug(); });
  dbgBlock.appendChild(dbgReset);

  const dbgDump = document.createElement("button");
  dbgDump.className = "btn-link";
  dbgDump.textContent = "Dump Diagnostics Now";
  dbgDump.title = "Writes the same diagnostic dump gameinput_api normally writes automatically a few minutes after startup, right now instead of waiting.";
  dbgDump.addEventListener("click", async () => {
    const original = dbgDump.textContent;
    dbgDump.disabled = true;
    dbgDump.textContent = "Dumping...";
    const res = await api().dump_controller_diag_now();
    dbgDump.disabled = false;
    dbgDump.textContent = original;
    showToast(res.ok ? `Dumped to ${res.path}` : `Dump failed: ${res.error}`);
  });
  dbgBlock.appendChild(dbgDump);

  c.appendChild(dbgBlock);
  startControllerDebugPolling();
  _settingsGroup("sections"); // everything after Controls, up to window mode

  // "List Style" vs "Gallery Style" — reused by both the media folder
  // blocks below and buildExeSectionBlock further down.
  function buildDisplayTypeBlock(sectionId) {
    const block = document.createElement("div");
    block.className = "settings-block";
    block.innerHTML = `<h3>Display type</h3>`;
    const radioWrap = document.createElement("div");
    radioWrap.className = "radio-group";
    [["gallery", "Gallery Style"], ["list", "List Style"]].forEach(([type, label]) => {
      const pill = document.createElement("div");
      pill.className = "radio-pill" + (getDisplayType(sectionId) === type ? " active" : "");
      pill.textContent = label;
      pill.addEventListener("click", async () => { await api().set_display_type(sectionId, type); renderSettings(); });
      radioWrap.appendChild(pill);
    });
    block.appendChild(radioWrap);
    return block;
  }

  // media folders — Desktop Section is inserted after the first one
  // (Music) rather than being the very first settings control
  ["music", "photos", "videos"].forEach((kind) => {
    const block = document.createElement("div");
    block.className = "settings-block";
    block.id = `settings-block-${kind}`;
    block.innerHTML = `<h3>${kind} folders</h3>`;
    (settings.folders[kind] || []).forEach((f) => {
      const row = document.createElement("div");
      row.className = "folder-row";
      row.innerHTML = `<span>${escapeHtml(f)}</span><button title="Remove">&#10005;</button>`;
      row.querySelector("button").addEventListener("click", async () => { await api().remove_folder(kind, f); renderSettings(); });
      block.appendChild(row);
    });
    const addBtn = document.createElement("button");
    addBtn.className = "add-folder-btn";
    addBtn.textContent = "+ Add folder";
    addBtn.addEventListener("click", async () => {
      const folder = await api().pick_folder();
      if (folder) { await api().add_folder(kind, folder); renderSettings(); }
    });
    block.appendChild(addBtn);
    c.appendChild(block);
    c.appendChild(buildDisplayTypeBlock(kind));

    if (kind === "music") {
      // Built-in fixed sections: show/hide each one individually. All on
      // by default (nothing here changes existing behavior unless you
      // turn one off).
      const builtinBlock = document.createElement("div");
      builtinBlock.className = "settings-block";
      builtinBlock.innerHTML = `<h3>Built-in Sections</h3>
        <p class="settings-note">Turn off any of these to remove them from the sections bar entirely.</p>`;
      const hiddenBuiltins = new Set(settings.hidden_builtin_sections || []);
      FIXED_CATEGORIES.forEach((cat) => {
        const row = document.createElement("div");
        row.className = "settings-row";
        row.style.marginTop = "8px";
        const isOn = !hiddenBuiltins.has(cat.id);
        const toggle = document.createElement("div");
        toggle.className = "toggle-switch" + (isOn ? " on" : "");
        toggle.innerHTML = `<div class="knob"></div>`;
        toggle.addEventListener("click", async () => {
          const turningOn = !isOn;
          await api().set_builtin_section_visible(cat.id, turningOn);
          if (turningOn && cat.id === "desktop") {
            // Fire-and-forget: warms up the icon extraction for every
            // Desktop item right away, so the section is actually ready
            // (icons and all) the moment it's first opened instead of
            // showing blank/loading then.
            api().list_desktop_items().catch(() => {});
          }
          await refreshAfterSettingsChange();
        });
        row.appendChild(toggle);
        row.appendChild(document.createTextNode(`${cat.label} — ${isOn ? "Shown" : "Hidden"}`));
        builtinBlock.appendChild(row);
      });
      c.appendChild(builtinBlock);

      // Desktop section — off by default, always first in the *category
      // list* when on (unrelated to its position here in Settings, which
      // is deliberately below Built-in Sections above).
      c.appendChild(buildToggleBlock(
        "Desktop Section",
        !!settings.desktop_section_enabled,
        async () => { await api().set_desktop_section_enabled(!settings.desktop_section_enabled); await refreshAfterSettingsChange(); },
        settings.desktop_section_enabled
          ? "Enabled — Desktop appears as the first section, showing whatever's on your actual Windows Desktop"
          : "Disabled — hidden from the section list",
      ));

      if (settings.desktop_section_enabled) c.appendChild(buildDisplayTypeBlock("desktop"));

      // Browser section — right after Desktop, off by default, same
      // no-list/gallery rule (it hosts an embedded browser box).
      c.appendChild(buildToggleBlock(
        "Browser Section",
        !!settings.browser_section_enabled,
        async () => { await api().set_browser_section_enabled(!settings.browser_section_enabled); await refreshAfterSettingsChange(); },
        settings.browser_section_enabled
          ? "Enabled — appears right after Explorer. Internally-launched URLs open here instead of in standalone CyberDeckBrowser."
          : "Disabled — hidden from the section list. Internally-launched URLs open in standalone CyberDeckBrowser (or the system default browser if that's missing).",
      ));
    }
  });

  // Load Subfolders (between Video folders and Apps, as requested)
  c.appendChild(buildToggleBlock(
    "Load Subfolders",
    settings.load_subfolders,
    async () => { await api().set_load_subfolders(!settings.load_subfolders); renderSettings(); },
    settings.load_subfolders
      ? "Enabled — Music/Photos/Videos scan all subfolders automatically"
      : "Disabled — browse folders manually in Music/Photos/Videos",
  ));

  // exe-list sections: apps/games/emulators/chat/streaming + custom sections
  const exeSections = [
    { id: "apps", label: "Apps" }, { id: "games", label: "Games" },
    { id: "emulators", label: "Emulators" }, { id: "chat", label: "Chat" },
    { id: "streaming", label: "Streaming" },
    ...(settings.custom_sections || []).map((cs) => ({ id: cs.id, label: cs.label, custom: true })),
  ];
  exeSections.forEach((sec) => { c.appendChild(buildExeSectionBlock(sec, settings)); c.appendChild(buildDisplayTypeBlock(sec.id)); });

  // web shortcuts (custom URLs opened in CyberDeckBrowser)
  const webBlock = document.createElement("div");
  webBlock.className = "settings-block";
  webBlock.innerHTML = `<h3>Web shortcuts</h3>`;
  (settings.web_shortcuts || []).forEach((s) => {
    const row = document.createElement("div");
    row.className = "folder-row";
    row.innerHTML = `<span>${escapeHtml(s.label)} — ${escapeHtml(s.url)}</span><button title="Remove">&#10005;</button>`;
    row.querySelector("button").addEventListener("click", async () => {
      await api().remove_web_shortcut(s.url);
      renderSettings();
    });
    webBlock.appendChild(row);
  });
  const addWebBtn = document.createElement("button");
  addWebBtn.className = "add-folder-btn";
  addWebBtn.textContent = "+ Add web shortcut";
  addWebBtn.addEventListener("click", openWebShortcutModal);
  webBlock.appendChild(addWebBtn);
  c.appendChild(webBlock);

  // add custom section
  const addSectionBtn = document.createElement("button");
  addSectionBtn.className = "btn-outline";
  addSectionBtn.textContent = "+ Add custom section";
  addSectionBtn.addEventListener("click", openSectionModal);
  const sectionBlockWrap = document.createElement("div");
  sectionBlockWrap.className = "settings-block";
  sectionBlockWrap.appendChild(addSectionBtn);
  c.appendChild(sectionBlockWrap);

  // macros
  c.appendChild(await buildMacroSectionBlock());

  _settingsGroup("plugins"); // discovered Plugins/ folders
  c.appendChild(await buildPluginsSettingsBlock());

  _settingsGroup("themes"); // window mode through the theme picker
  // window mode
  const winBlock = document.createElement("div");
  winBlock.className = "settings-block";
  winBlock.innerHTML = `<h3>Window mode</h3>`;
  const radioWrap = document.createElement("div");
  radioWrap.className = "radio-group";
  const WINDOW_MODE_LABELS = {
    exclusive_fullscreen: "Exclusive Fullscreen",
    windowed_fullscreen: "Windowed Fullscreen",
    windowed: "Windowed",
    kiosk: "Kiosk",
  };
  ["exclusive_fullscreen", "windowed_fullscreen", "windowed", "kiosk"].forEach((mode) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + (settings.window_mode === mode ? " active" : "");
    pill.textContent = WINDOW_MODE_LABELS[mode];
    pill.addEventListener("click", async () => {
      if (mode === "kiosk") {
        if (settings.window_mode === "kiosk") return;
        const yes = await openConfirmModal(
          "Enable kiosk mode?",
          "You sure you want to enable kiosk mode?This can only be disabled by editing the json settings, holding the controllers y button for 45 seconds, or entering the code dpad up, dpad up, dpad down, dpad down, dpad left, dpad right, dpad left, dpad right, b button, a button; or up key, up key, down key, down key, left key, right key, left key, right key, b key, a key."
        );
        await api().set_window_mode(yes ? "kiosk" : "windowed_fullscreen");
        await applyKioskChangeAndRefresh();
        return;
      }
      await api().set_window_mode(mode);
      renderSettings();
    });
    radioWrap.appendChild(pill);
  });
  winBlock.appendChild(radioWrap);
  c.appendChild(winBlock);

  // layout mode
  const layoutBlock = document.createElement("div");
  layoutBlock.className = "settings-block";
  layoutBlock.innerHTML = `<h3>Layouts</h3>`;
  const layoutRadioWrap = document.createElement("div");
  layoutRadioWrap.className = "radio-group";
  const builtinLayouts = [["dawning_horizon", "DawningHorizon"], ["night_horizon", "Verticular Blobs"], ["cyber_radial", "CyberRadial"]];
  // discovered user themes become extra options (base shown as a subtitle)
  const userLayouts = (state.userThemes || []).map((t) => [t.layout, t.name + " \u2022 user"]);
  [...builtinLayouts, ...userLayouts].forEach(([mode, label]) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + ((settings.layout || "dawning_horizon") === mode ? " active" : "");
    pill.textContent = label;
    pill.addEventListener("click", async () => {
      state.userThemeCss.__active = null; // force re-inject on switch
      await api().set_layout(mode);
      await loadUserThemes();
      renderSettings();
    });
    layoutRadioWrap.appendChild(pill);
  });
  layoutBlock.appendChild(layoutRadioWrap);
  const themeHint = document.createElement("p");
  themeHint.className = "settings-note";
  themeHint.textContent = "Add your own themes by dropping a .css file (or a folder with theme.css) into the themes/ folder next to the app, then reopen this screen.";
  layoutBlock.appendChild(themeHint);
  const rescan = document.createElement("button");
  rescan.className = "btn-link";
  rescan.textContent = "Rescan themes folder";
  rescan.addEventListener("click", async () => { await loadUserThemes(); renderSettings(); });
  layoutBlock.appendChild(rescan);
  c.appendChild(layoutBlock);

  // Dawning Horizon primary theme color
  const themeBlock = document.createElement("div");
  themeBlock.className = "settings-block";
  themeBlock.innerHTML = `<h3>Dawning Horizon theme color</h3>`;
  const themeNote = document.createElement("p");
  themeNote.className = "settings-note";
  themeNote.textContent = "Re-tints the DawningHorizon background to a chosen hue; section colors follow as a complementary ROYGBIV rainbow. Only affects the DawningHorizon layout.";
  themeBlock.appendChild(themeNote);
  const currentThemeColor = settings.dawning_theme_color || "original";
  const pickThemeColor = async (value) => {
    await api().set_dawning_theme_color(value);
    state.settings = await api().get_settings();
    applyDawningThemeColor(state.settings);
    renderSettings();
  };
  const origWrap = document.createElement("div");
  origWrap.className = "radio-group";
  const origPill = document.createElement("div");
  origPill.className = "radio-pill" + (currentThemeColor === "original" ? " active" : "");
  origPill.textContent = "Original";
  origPill.addEventListener("click", () => pickThemeColor("original"));
  origWrap.appendChild(origPill);
  themeBlock.appendChild(origWrap);
  [["light", "Light"], ["dark", "Dark"], ["neon", "Neon"], ["primary", "Primary"], ["pastel", "Pastel"], ["bubblegum", "Bubblegum"]].forEach(([pal, label]) => {
    const row = document.createElement("div");
    row.className = "theme-swatch-row";
    const lab = document.createElement("span");
    lab.className = "theme-swatch-label";
    lab.textContent = label;
    row.appendChild(lab);
    DAWNING_HUES.forEach(([hueName, hueDeg]) => {
      const value = `${pal}:${hueName}`;
      const sw = document.createElement("button");
      sw.type = "button";
      sw.className = "theme-swatch" + (currentThemeColor === value ? " active" : "");
      const rec = DAWNING_PALETTES[pal];
      sw.style.background = `hsl(${hueDeg}, ${rec.bg1[0]}%, ${rec.bg1[1]}%)`;
      sw.title = `${label} \u2014 ${hueName}`;
      sw.addEventListener("click", () => pickThemeColor(value));
      row.appendChild(sw);
    });
    themeBlock.appendChild(row);
  });
  // mspaint-style "edit colors" grid: an HSV plane of predefined cells
  // beneath the named palettes, plus a live custom swatch. Picking a cell
  // stores "hex:#rrggbb".
  const gridWrap = document.createElement("div");
  gridWrap.className = "color-grid-wrap";
  const gridLabel = document.createElement("p");
  gridLabel.className = "settings-note";
  gridLabel.textContent = "Custom color \u2014 pick from the grid:";
  gridWrap.appendChild(gridLabel);
  const grid = document.createElement("div");
  grid.className = "color-grid";
  const COLS = 24, ROWS = 8;
  const currentCustom = (currentThemeColor || "").startsWith("hex:")
    ? currentThemeColor.slice(4) : null;
  for (let r = 0; r < ROWS; r++) {
    for (let col = 0; col < COLS; col++) {
      const hue = Math.round((col / COLS) * 360);
      // top rows brighter, bottom rows darker; last column a grey ramp
      let cssColor, hex;
      if (col === COLS - 1) {
        const g = Math.round(255 * (1 - r / (ROWS - 1)));
        hex = "#" + [g, g, g].map((v) => v.toString(16).padStart(2, "0")).join("");
        cssColor = hex;
      } else {
        const light = 88 - (r / (ROWS - 1)) * 70; // 88% -> 18%
        const sat = 85;
        cssColor = `hsl(${hue}, ${sat}%, ${light}%)`;
        hex = hslToHex(hue, sat, light);
      }
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "color-cell" + (currentCustom && currentCustom.toLowerCase() === hex.toLowerCase() ? " active" : "");
      cell.style.background = cssColor;
      cell.title = hex;
      cell.addEventListener("click", () => pickThemeColor("hex:" + hex));
      grid.appendChild(cell);
    }
  }
  gridWrap.appendChild(grid);
  themeBlock.appendChild(gridWrap);
  c.appendChild(themeBlock);

  _settingsGroup("addons"); // built-in theme extras + scanned plugin/plug-on/theme settings.json files
  await renderAddonSettingsBlocks(c, settings);

  _settingsGroup("program"); // close-tasks through factory reset
  // open-programs bar behavior
  c.appendChild(buildToggleBlock(
    "Close tasks without prompt",
    !!settings.close_tasks_without_prompt,
    async () => {
      state.settings = await api().set_close_tasks_without_prompt(!settings.close_tasks_without_prompt);
      renderSettings();
    },
    settings.close_tasks_without_prompt
      ? "Holding X on an open-programs bar item closes it immediately, no confirmation."
      : "Holding X on an open-programs bar item asks for confirmation before closing it.",
  ));

  // Foreground trigger: how to bring Meridian Launcher to the front when it's in
  // the background. Input is always received in the background, but only
  // this trigger (or clicking) brings the window forward.
  const fgBlock = document.createElement("div");
  fgBlock.className = "settings-block";
  fgBlock.innerHTML = `<h3>Bring to foreground with</h3>`;
  const fgNote = document.createElement("p");
  fgNote.className = "settings-note";
  fgNote.textContent = "When Meridian Launcher is running in the background, this brings it to the front. Controller input is still received while backgrounded, but won't navigate or open menus until the window is focused again.";
  fgBlock.appendChild(fgNote);
  const fgGroup = document.createElement("div");
  fgGroup.className = "radio-group";
  const fgCur = (settings.foreground_trigger) || "start_select";
  [["start_select", "Start + Select"], ["xbox", "Xbox (Guide) button"], ["off", "Off"]].forEach(([val, label]) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + (fgCur === val ? " active" : "");
    pill.textContent = label;
    pill.addEventListener("click", async () => {
      state.settings = await api().set_foreground_trigger(val);
      renderSettings();
    });
    fgGroup.appendChild(pill);
  });
  fgBlock.appendChild(fgGroup);
  const fgXboxNote = document.createElement("p");
  fgXboxNote.className = "settings-note";
  fgXboxNote.textContent = "Note: the Xbox/Guide button is only reported by some controller drivers (via XInputGetStateEx). If it doesn't respond on your setup, use Start + Select.";
  fgBlock.appendChild(fgXboxNote);
  c.appendChild(fgBlock);


  if (mxAvailable) {
    c.appendChild(buildToggleBlock(
      "Open folders in Meridian Explorer",
      !!settings.route_folders_to_meridian_explorer,
      async () => {
        state.settings = await api().set_route_folders_to_meridian_explorer(!settings.route_folders_to_meridian_explorer);
        renderSettings();
      },
      settings.route_folders_to_meridian_explorer
        ? "Folder shortcuts and folder opens from the Launcher go to Meridian Explorer. For system-wide folder handling (right-click menu, or making it the default), see the Macros section."
        : "Folder shortcuts and folder opens from the Launcher use Windows Explorer.",
    ));
  } else {
    // Explorer exe missing -> show a disabled, explanatory row instead of a
    // toggle that can't do anything.
    const mxBlock = document.createElement("div");
    mxBlock.className = "settings-block settings-disabled";
    mxBlock.innerHTML = `<h3>Open folders in Meridian Explorer</h3><p class="settings-note">Unavailable \u2014 Meridian Explorer.exe was not found next to the Launcher.</p>`;
    c.appendChild(mxBlock);
  }

  // Icon size
  const iconSizeBlock = document.createElement("div");
  iconSizeBlock.className = "settings-block";
  iconSizeBlock.innerHTML = `<h3>Icon size</h3>`;
  const iconSizeNote = document.createElement("p");
  iconSizeNote.className = "settings-note";
  iconSizeNote.textContent = "Size of the icons in item lists. Each step doubles the size; the list rows grow to fit.";
  iconSizeBlock.appendChild(iconSizeNote);
  const iconSizeGroup = document.createElement("div");
  iconSizeGroup.className = "radio-group";
  const currentIconSize = settings.icon_size || "small";
  [["small", "Small"], ["medium", "Medium"], ["large", "Large"], ["xl", "XL"]].forEach(([val, label]) => {
    const pill = document.createElement("div");
    pill.className = "radio-pill" + (currentIconSize === val ? " active" : "");
    pill.textContent = label;
    pill.addEventListener("click", async () => {
      state.settings = await api().set_icon_size(val);
      applyIconSize();
      renderSettings();
    });
    iconSizeGroup.appendChild(pill);
  });
  iconSizeBlock.appendChild(iconSizeGroup);
  c.appendChild(iconSizeBlock);

  // video fullscreen
  c.appendChild(buildToggleBlock(
    "Video Fullscreen",
    settings.video_fullscreen,
    async () => { await api().set_video_fullscreen(!settings.video_fullscreen); renderSettings(); },
  ));

  // battery indicator
  c.appendChild(buildToggleBlock(
    "Battery Level Indicator",
    settings.battery_indicator,
    async () => { await api().set_battery_indicator(!settings.battery_indicator); renderSettings(); updateBatteryIndicator(); },
  ));

  // Fullscreen Helper: force whatever window a launched .exe opens into
  // borderless fullscreen, for apps that ignore the normal "start
  // maximized" request or only appear maximized with title bar/borders
  // still showing. Off by default — it's a blunt tool, so it's opt-in.
  c.appendChild(buildToggleBlock(
    "Fullscreen Helper",
    !!settings.fullscreen_helper_enabled,
    async () => { await api().set_fullscreen_helper_enabled(!settings.fullscreen_helper_enabled); renderSettings(); },
    settings.fullscreen_helper_enabled
      ? "Enabled — launched apps have their window chrome stripped and stretched to fill the screen, even if they only appear fullscreen."
      : "Disabled — apps launch with a normal maximize request only.",
  ));

  // Controller Bridge: per-item toggle lives in that item's Start menu
  // (Apps/Games sections only - see openStartMenu) - this is just the
  // one thing that needs an actual Settings UI, a custom keyboard
  // mapping file, since that applies to every item the bridge is
  // enabled for, not any one of them.
  {
    const bridgeBlock = document.createElement("div");
    bridgeBlock.className = "settings-block";
    const bridgeCount = ((settings.controller_bridge_items) || []).length;
    const mappingPath = await api().get_controller_bridge_mapping_path();
    bridgeBlock.innerHTML = `<h3>Controller Bridge</h3>
      <p class="settings-note">Translates real controller input into keyboard presses, only while a specific Apps/Games item that needs it is actually running (enabled per-item from that item's Start menu) — never left on globally, since that would make the controller fight Meridian Launcher's own keyboard shortcuts, or onscreenmenu's/CyberDeckBrowser's/Meridian Explorer's if any of those end up focused instead. Currently enabled for ${bridgeCount} item${bridgeCount === 1 ? "" : "s"}.</p>
      <p class="settings-note">Mapping: ${mappingPath ? escapeHtml(mappingPath) : "Default (arrow keys, Z/X/A/S for the face buttons — see xinput_to_keyboard.py)"}</p>`;
    const mappingBtnRow = document.createElement("div");
    mappingBtnRow.className = "settings-row";
    const chooseMappingBtn = document.createElement("button");
    chooseMappingBtn.className = "btn-link";
    chooseMappingBtn.textContent = "Choose custom mapping file\u2026";
    chooseMappingBtn.addEventListener("click", async () => {
      await api().set_controller_bridge_mapping_path();
      renderSettings();
    });
    mappingBtnRow.appendChild(chooseMappingBtn);
    if (mappingPath) {
      const clearMappingBtn = document.createElement("button");
      clearMappingBtn.className = "btn-link";
      clearMappingBtn.textContent = "Reset to default mapping";
      clearMappingBtn.addEventListener("click", async () => {
        await api().clear_controller_bridge_mapping_path();
        renderSettings();
      });
      mappingBtnRow.appendChild(clearMappingBtn);
    }
    bridgeBlock.appendChild(mappingBtnRow);
    c.appendChild(bridgeBlock);
  }

  // auto shuffle: when a song ends, load a random one instead of the next
  // in list order. Next/previous still just move relative to whatever's
  // currently loaded — including a shuffled pick — so they naturally keep
  // working the same way either way.
  c.appendChild(buildToggleBlock(
    "Auto Shuffle Songs",
    settings.auto_shuffle_songs !== false,
    async () => { await api().set_auto_shuffle_songs(!(settings.auto_shuffle_songs !== false)); renderSettings(); },
  ));

  // Plays one random track automatically once the app finishes booting -
  // a separate thing from Auto Shuffle Songs above, which only affects
  // what happens when a track that's ALREADY playing ends.
  c.appendChild(buildToggleBlock(
    "Play Random Song on Startup",
    !!settings.play_random_song_on_startup,
    async () => { await api().set_play_random_song_on_startup(!settings.play_random_song_on_startup); renderSettings(); },
  ));

  // launch external system features (Task Manager, Control Panel, Recycle
  // Bin, Uninstall Apps, "open Windows Bluetooth settings") with onscreenmenu
  c.appendChild(buildToggleBlock(
    "Launch External System features with onscreenmenu?",
    settings.launch_system_with_osm,
    async () => { await api().set_system_osm(!settings.launch_system_with_osm); renderSettings(); },
    settings.launch_system_with_osm
      ? "Enabled — opening Task Manager, Control Panel, Recycle Bin, Uninstall Apps, or Bluetooth settings also launches onscreenmenu, so those native dialogs are controller-navigable."
      : "Disabled — those System features open on their own, without the on-screen menu overlay.",
  ));

  // background image
  const bgBlock = document.createElement("div");
  bgBlock.className = "settings-block";
  bgBlock.innerHTML = `<h3>Custom background <span class="theme-scope">(this theme)</span></h3>`;
  const bgBtn = document.createElement("button");
  bgBtn.className = "btn-outline";
  bgBtn.textContent = themeBackground(settings) ? "Change image" : "Choose image";
  bgBtn.addEventListener("click", async () => { await api().set_background(); applyBackground(await api().get_settings()); renderSettings(); });
  bgBlock.appendChild(bgBtn);
  if (themeBackground(settings)) {
    const clear = document.createElement("button");
    clear.className = "btn-link";
    clear.textContent = "Clear";
    clear.addEventListener("click", async () => { await api().clear_background(); applyBackground(await api().get_settings()); renderSettings(); });
    bgBlock.appendChild(clear);
  }
  c.appendChild(bgBlock);

  // overlay
  const ovBlock = document.createElement("div");
  ovBlock.className = "settings-block";
  ovBlock.innerHTML = `<h3>Custom overlay <span class="theme-scope">(this theme)</span></h3>`;
  const ovRow = document.createElement("div");
  ovRow.className = "settings-row";
  const toggle = document.createElement("div");
  toggle.className = "toggle-switch" + (themeOverlayEnabled(settings) ? " on" : "");
  toggle.innerHTML = `<div class="knob"></div>`;
  toggle.addEventListener("click", async () => {
    await api().set_overlay_enabled(!themeOverlayEnabled(settings));
    await applyOverlay(await api().get_settings());
    renderSettings();
  });
  ovRow.appendChild(toggle);
  ovRow.appendChild(document.createTextNode("Enabled (white becomes transparent)"));
  ovBlock.appendChild(ovRow);
  const ovBtn = document.createElement("button");
  ovBtn.className = "btn-outline";
  ovBtn.textContent = themeOverlay(settings) ? "Change overlay" : "Choose overlay image";
  ovBtn.addEventListener("click", async () => { await api().set_overlay(); await applyOverlay(await api().get_settings()); renderSettings(); });
  ovBlock.appendChild(ovBtn);
  if (themeOverlay(settings)) {
    const clear = document.createElement("button");
    clear.className = "btn-link";
    clear.textContent = "Clear";
    clear.addEventListener("click", async () => { await api().clear_overlay(); await applyOverlay(await api().get_settings()); renderSettings(); });
    ovBlock.appendChild(clear);
  }
  c.appendChild(ovBlock);

  // opening video
  const vidBlock = document.createElement("div");
  vidBlock.className = "settings-block";
  vidBlock.innerHTML = `<h3>Opening video</h3>`;
  const vidBtn = document.createElement("button");
  vidBtn.className = "btn-outline";
  vidBtn.textContent = settings.opening_video ? "Change video" : "Choose video";
  vidBtn.addEventListener("click", async () => { await api().set_opening_video(); renderSettings(); });
  vidBlock.appendChild(vidBtn);
  if (settings.opening_video) {
    const clear = document.createElement("button");
    clear.className = "btn-link";
    clear.textContent = "Clear";
    clear.addEventListener("click", async () => { await api().clear_opening_video(); renderSettings(); });
    vidBlock.appendChild(clear);
  }
  c.appendChild(vidBlock);

  const hasFfmpeg = await api().has_ffmpeg();
  if (!hasFfmpeg) {
    const note = document.createElement("div");
    note.className = "empty-msg";
    note.textContent = "ffmpeg not found — video thumbnails and durations are limited until it's installed and on PATH.";
    c.appendChild(note);
  }

  // app data folder (settings.json, controls files, cached thumbnails)
  const dataBlock = document.createElement("div");
  dataBlock.className = "settings-block";
  dataBlock.innerHTML = `<h3>App data folder</h3>`;
  const dataBtn = document.createElement("button");
  dataBtn.className = "btn-outline";
  dataBtn.textContent = "Open App data folder";
  dataBtn.addEventListener("click", async () => {
    const result = await api().open_app_data_folder();
    if (!result || result.ok === false) {
      showToast(result && result.error ? result.error : "Couldn't open the app data folder.");
    }
  });
  dataBlock.appendChild(dataBtn);
  c.appendChild(dataBlock);

  // updates
  const updateBlock = document.createElement("div");
  updateBlock.className = "settings-block";
  const versionInfo = await api().get_version();
  updateBlock.innerHTML = `<h3>Updates</h3><p style="font-size:12px;color:var(--text-lo);margin:0 0 10px;">Version ${versionInfo.version}</p>`;
  const updateBtn = document.createElement("button");
  updateBtn.className = "btn-outline";
  updateBtn.textContent = "Check for Updates";
  updateBtn.addEventListener("click", async () => {
    updateBtn.disabled = true;
    updateBtn.textContent = "Checking...";
    const result = await api().check_for_updates();
    updateBtn.disabled = false;
    updateBtn.textContent = "Check for Updates";
    if (result && result.available) {
      showUpdateModal(result, { manual: true });
    } else if (result && result.error) {
      showToast(result.error);
    } else {
      showToast("You're on the latest version.");
    }
  });
  updateBlock.appendChild(updateBtn);
  c.appendChild(updateBlock);

  // thumbnail/metadata cache (music/photos/videos) — mostly self-managing,
  // but useful to force-clear if thumbnails ever get stuck stale
  const cacheBlock = document.createElement("div");
  cacheBlock.className = "settings-block";
  cacheBlock.innerHTML = `<h3>Thumbnail Cache</h3>`;
  const cacheBtn = document.createElement("button");
  cacheBtn.className = "btn-outline";
  cacheBtn.textContent = "Delete Thumbnail Cache";
  cacheBtn.addEventListener("click", async () => {
    const yes = await openConfirmModal(
      "Delete thumbnail cache?",
      "Clears every generated music/photo/video thumbnail. They'll regenerate automatically in the background, but sections may load slower again until that finishes.",
    );
    if (!yes) return;
    const res = await api().delete_thumbnail_cache();
    showToast(res && res.ok ? "Thumbnail cache cleared." : `Couldn't clear cache: ${res && res.error}`);
  });
  cacheBlock.appendChild(cacheBtn);
  c.appendChild(cacheBlock);

  // backup & restore — one .zip bundling settings.json, control maps,
  // the selected theme (part of settings.json), activated plugins
  // (settings.json's visibility flags) and the actual custom
  // sections/plugins folder contents (Plugins/, themes/)
  const backupBlock = document.createElement("div");
  backupBlock.className = "settings-block";
  backupBlock.innerHTML = `<h3>Backup & Restore</h3>
    <p class="settings-note">Export everything — settings, selected theme, activated plugins, and custom sections/plugins — into one .zip. Import it later (on this install or a fresh one) to restore it.</p>`;
  const backupRow = document.createElement("div");
  backupRow.style.display = "flex";
  backupRow.style.gap = "10px";
  backupRow.style.flexWrap = "wrap";

  const exportBtn = document.createElement("button");
  exportBtn.className = "btn-outline";
  exportBtn.textContent = "Export Backup...";
  exportBtn.addEventListener("click", async () => {
    exportBtn.disabled = true;
    const original = exportBtn.textContent;
    exportBtn.textContent = "Exporting...";
    const result = await api().export_backup();
    exportBtn.disabled = false;
    exportBtn.textContent = original;
    if (!result.path) return; // cancelled - not an error
    showToast(result.ok ? `Backup saved to ${result.path}` : `Export failed: ${result.error}`);
  });
  backupRow.appendChild(exportBtn);

  const importBtn = document.createElement("button");
  importBtn.className = "btn-outline";
  importBtn.textContent = "Import Backup...";
  importBtn.addEventListener("click", async () => {
    const picked = await api().pick_backup_to_import();
    if (!picked.path) return; // cancelled
    if (!picked.ok) {
      showToast(`Couldn't read that backup: ${picked.error}`);
      return;
    }
    const bits = [];
    if (picked.manifest && picked.manifest.app_version) bits.push(`from v${picked.manifest.app_version}`);
    if (picked.has_plugins) bits.push("includes Plugins/");
    if (picked.has_themes) bits.push("includes themes/");
    const detail = bits.length ? ` (${bits.join(", ")})` : "";
    const yes = await openConfirmModal(
      "Import this backup?",
      `This overwrites your current settings, control maps, and merges in the backed-up Plugins/ and themes/ folders${detail}. Anything not in the backup is left as-is. This cannot be undone.`,
    );
    if (!yes) return;
    importBtn.disabled = true;
    const result = await api().import_backup(picked.path);
    importBtn.disabled = false;
    if (!result.ok) {
      showToast(`Import failed: ${result.error}`);
      return;
    }
    state.settings = result.settings;
    await refreshCategoriesAndLand();
    applyBackground(state.settings);
    await applyOverlay(state.settings);
    await updateBatteryIndicator();
    showToast("Backup restored.");
  });
  backupRow.appendChild(importBtn);

  backupBlock.appendChild(backupRow);
  c.appendChild(backupBlock);

  // revert to factory settings — always the very last option
  const resetBlock = document.createElement("div");
  resetBlock.className = "settings-block";
  resetBlock.id = "settings-block-factory-reset";
  resetBlock.innerHTML = `<h3>Reset</h3>`;
  const resetBtn = document.createElement("button");
  resetBtn.className = "btn-outline btn-danger";
  resetBtn.textContent = "Revert to factory settings";
  resetBtn.addEventListener("click", async () => {
    const yes = await openConfirmModal(
      "Revert to factory settings?",
      "This clears out all saved user modifications — folders, sections, custom sections, toggles, background/overlay/opening video, and window mode. This cannot be undone.",
    );
    if (!yes) return;
    await api().factory_reset();
    await refreshCategoriesAndLand();
    applyBackground(state.settings);
    await applyOverlay(state.settings);
    await updateBatteryIndicator();
    showToast("Factory settings restored.");
  });
  resetBlock.appendChild(resetBtn);
  c.appendChild(resetBlock);


  _settingsGroup("about"); // the credit footer
  // Meridian Launcher's own license - shown ahead of the third-party
  // list below since it's the one that actually governs this codebase
  // itself, not something bundled/linked-against.
  const ownLicenseBlock = document.createElement("div");
  ownLicenseBlock.className = "settings-block settings-credit";
  ownLicenseBlock.innerHTML = `<h3>License</h3>
    <p class="settings-note">Meridian Launcher is licensed under the <b>DskoTech Source Available License 1.0</b> — see <code>LICENSE.txt</code> in the install folder for the full text. Summary, not a substitute for that file: free to view, study, compile, modify, and run for personal/educational/research/non-commercial use, and to fork or submit pull requests back — selling it, offering it as a paid service, redistributing a modified version, or using Meridian Launcher's branding/trademarks/artwork all require DskoTech's written permission first.</p>`;
  c.appendChild(ownLicenseBlock);
  // Third-party attributions/licenses — everything this suite bundles,
  // links against, or downloads and ships alongside itself (via
  // InstallMeridianSuite.bat's runtime-dependency step) that isn't
  // Meridian's own code. Compiled in good faith from requirements.txt
  // and the runtime components the installer/build scripts fetch; this
  // is a summary for convenience, not a substitute for each project's
  // own license file, which is the authoritative text in every case.
  const licenseBlock = document.createElement("div");
  licenseBlock.className = "settings-block settings-credit";
  licenseBlock.innerHTML = `<h3>Third-Party Software &amp; Licenses</h3>
    <p class="settings-note">Meridian Launcher is built on the following open-source and Microsoft-redistributable components. Each remains the property of its respective authors under its own license.</p>
    <div class="license-list">
      <p><b>Python packages (PyPI)</b></p>
      <ul>
        <li>pywebview — BSD-3-Clause</li>
        <li>PySide6 / shiboken6 (Qt for Python), including QtWebEngine — GNU Lesser General Public License v3 (LGPLv3). Distributed as dynamically-linked, unmodified libraries, as LGPLv3 requires for this kind of use; see qt.io/licensing for the upstream Qt licensing terms.</li>
        <li>pygame — GNU Lesser General Public License v2.1 (LGPLv2.1)</li>
        <li>mutagen — GNU General Public License v2.0 or later</li>
        <li>Pillow — Historical Permission Notice and Disclaimer (HPND)</li>
        <li>psutil — BSD-3-Clause</li>
        <li>pywin32 — Python Software Foundation License / MIT-style (varies by submodule)</li>
        <li>pycaw — MIT License</li>
        <li>comtypes — MIT License</li>
        <li>qrcode — BSD-3-Clause</li>
        <li>keyboard — MIT License</li>
        <li>PyInstaller — GNU General Public License v2.0 or later, with a bootloader exception explicitly permitting the compiled bootloader to be embedded in and distributed with applications like this one under any license, without extending GPL obligations to the packaged application's own code.</li>
      </ul>
      <p><b>Browser engine</b></p>
      <ul>
        <li>Chromium (via QtWebEngine) — BSD 3-Clause License, plus the licenses of Chromium's own numerous third-party components (see chromium.org/Home/chromium-security/... or chrome://credits from any Chromium-based browser for the full list)</li>
        <li>Google Widevine CDM — proprietary, © Google LLC. NOT bundled or redistributed by Meridian in any form — CyberDeckBrowser/Meridian NetBrowse only locate and point Chromium at a copy already installed on this machine by Google Chrome or Microsoft Edge, if present.</li>
      </ul>
      <p><b>Microsoft redistributable runtimes</b> (installed by InstallMeridianSuite.bat, not authored by Meridian)</p>
      <ul>
        <li>Microsoft Edge WebView2 Runtime — proprietary, © Microsoft Corporation, distributed under Microsoft's own WebView2 runtime distribution terms</li>
        <li>Microsoft Visual C++ 2015-2022 Redistributable — proprietary, © Microsoft Corporation</li>
        <li>Microsoft GameInput SDK headers/import library (gameinput_native/vendor/GameInput/) — proprietary, © Microsoft Corporation, used under the terms of the Microsoft Game Development Kit (GDK); the gameinput.dll runtime itself is not redistributed by Meridian and must already be present via the Xbox app/Game Bar or GameInputRedist.msi</li>
      </ul>
      <p><b>Optional runtime components</b> (best-effort, downloaded by InstallMeridianSuite.bat if available; the suite functions without them)</p>
      <ul>
        <li>ffmpeg / ffprobe — GNU General Public License v2.0 or later (the "essentials" builds this installer fetches include GPL-licensed encoders such as libx264, so the overall build is GPL-licensed even though ffmpeg's own code is dual LGPL/GPL); used only for generating media thumbnails, invoked as a separate process, never linked into Meridian's own code</li>
        <li>SDL3 — zlib License; used only if the optional "sdl3" controller input backend is selected in Settings &gt; Controls</li>
      </ul>
    </div>`;
  c.appendChild(licenseBlock);
  // credit footer — always the very last thing in the settings box
  const creditBlock = document.createElement("div");
  creditBlock.className = "settings-block settings-credit";
  creditBlock.innerHTML = `<p>Vibecoded by Samuel "Zenith" Schimmel (Madisico) 2026 — see the License block above for terms. Donations Appreciated, but Money Not Required.</p>`;
  c.appendChild(creditBlock);

  panel.appendChild(_realC);
  // restore the pre-render scroll position (see top of renderSettings)
  if (panel && _prevScroll) panel.scrollTop = _prevScroll;
  alignCategoryRowToList();
  const focusCount = settingsFocusableElements().length;
  state.settingsCursor = focusCount ? Math.max(0, Math.min(focusCount - 1, state.settingsCursor)) : 0;
  highlightSettingsCursor();
}

// Settings is controller/keyboard navigable like every other section: Up/Down
// moves a cursor over its buttons/toggles/radio-pills (in visual order),
// confirm clicks whichever one is highlighted. Native inputs (the custom
// section name field, the Wi-Fi password field) aren't part of this list —
// they get real focus directly when their modal opens.
function settingsFocusableElements() {
  // Color-grid cells are NOT individually focusable (192 of them makes the
  // list impossible to navigate past). The grid container is a single
  // focusable; when the cursor is on it, D-pad moves a 2D sub-cursor over
  // the cells and A picks the highlighted one (see handleColorGridNav).
  return [...el("item-panel").querySelectorAll("button, .toggle-switch, .radio-pill, .color-grid")]
    .filter((node) => !node.classList.contains("color-cell"));
}

function highlightSettingsCursor() {
  const els = settingsFocusableElements();
  els.forEach((node, i) => node.classList.toggle("settings-focus", i === state.settingsCursor));
  const current = els[state.settingsCursor];
  if (current && typeof current.scrollIntoView === "function") current.scrollIntoView({ block: "nearest" });
}

function buildExeSectionBlock(sec, settings) {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.id = `settings-block-${sec.id}`;
  const h = document.createElement("h3");
  h.textContent = sec.label;
  block.appendChild(h);

  const secSettings = (settings.sections && settings.sections[sec.id]) || {};
  const osmOn = secSettings.launch_with_osm !== false; // default on
  const osmRow = document.createElement("div");
  osmRow.className = "settings-row";
  const osmToggle = document.createElement("div");
  osmToggle.className = "toggle-switch" + (osmOn ? " on" : "");
  osmToggle.innerHTML = `<div class="knob"></div>`;
  osmToggle.addEventListener("click", async () => {
    await api().set_section_osm(sec.id, !osmOn);
    renderSettings();
  });
  osmRow.appendChild(osmToggle);
  osmRow.appendChild(document.createTextNode("Launch with onscreenmenu?"));
  block.appendChild(osmRow);

  const listWrap = document.createElement("div");
  block.appendChild(listWrap);

  const refreshList = (items) => {
    listWrap.innerHTML = "";
    items.forEach((it) => {
      const row = document.createElement("div");
      row.className = "folder-row";
      row.innerHTML = `<span>${escapeHtml(it.name)}</span><button title="Remove">&#10005;</button>`;
      row.querySelector("button").addEventListener("click", async () => {
        const updated = await api().remove_exe_from_section(sec.id, it.path);
        refreshList(updated);
      });
      listWrap.appendChild(row);
    });
  };

  api().list_section_items(sec.id).then(refreshList);

  const addBtn = document.createElement("button");
  addBtn.className = "add-folder-btn";
  addBtn.textContent = `+ Add .exe to ${sec.label}`;
  addBtn.addEventListener("click", async () => {
    const updated = await api().add_exe_to_section(sec.id);
    refreshList(updated);
  });
  block.appendChild(addBtn);

  const addStoreBtn = document.createElement("button");
  addStoreBtn.className = "add-folder-btn";
  addStoreBtn.textContent = `+ Add Windows Store App to ${sec.label}`;
  addStoreBtn.addEventListener("click", async () => {
    const apps = await api().list_installed_store_apps();
    openStoreAppPicker(apps, async (app) => {
      const updated = await api().add_store_app_to_section(sec.id, app.app_id, app.name);
      refreshList(updated);
    });
  });
  block.appendChild(addStoreBtn);

  if (sec.custom) {
    const rm = document.createElement("button");
    rm.className = "btn-link";
    rm.textContent = "Remove this section";
    rm.addEventListener("click", async () => { await api().remove_custom_section(sec.id); await refreshAfterSettingsChange(); });
    block.appendChild(rm);
  }

  return block;
}

async function buildMacroSectionBlock() {
  const block = document.createElement("div");
  block.className = "settings-block";
  block.id = "settings-block-macros";
  block.innerHTML = `<h3>Macros</h3>`;
  const listWrap = document.createElement("div");
  block.appendChild(listWrap);

  const refreshList = (items) => {
    listWrap.innerHTML = "";
    items.filter((it) => it.type !== "builtin").forEach((it) => {
      const row = document.createElement("div");
      row.className = "folder-row";
      row.innerHTML = `<span>${escapeHtml(it.name)}</span><button title="Remove">&#10005;</button>`;
      row.querySelector("button").addEventListener("click", async () => {
        const updated = await api().remove_macro_item(it.path);
        refreshList(updated);
      });
      listWrap.appendChild(row);
    });
  };

  const items = await api().list_macro_items();
  refreshList(items);

  const addBtn = document.createElement("button");
  addBtn.className = "add-folder-btn";
  addBtn.textContent = "+ Add .bat or .ps1 to Macros";
  addBtn.addEventListener("click", async () => {
    const updated = await api().add_bat_to_macros();
    refreshList(updated);
  });
  block.appendChild(addBtn);
  return block;
}

async function refreshAfterSettingsChange() {
  const settings = await api().get_settings();
  state.settings = settings;
  await loadChatOptions();
  const currentId = state.categories[state.catIndex] && state.categories[state.catIndex].id;
  state.categories = buildCategories(settings);
  let idx = state.categories.findIndex((c) => c.id === currentId);
  if (idx === -1) idx = Math.min(state.catIndex, state.categories.length - 1);
  unloadEmbeddedBoxIfLeaving(idx);
  state.catIndex = idx;
  renderCategories();
  await renderSettings();
}

// ---------------- generic text-input modal (custom sections, web shortcuts) ----------------

let modalMode = "section"; // "section" | "web_shortcut"

function openSectionModal() {
  modalMode = "section";
  el("modal-title").textContent = "New section";
  el("modal-input").placeholder = "";
  el("modal-input").maxLength = 24;
  el("modal-overlay").classList.remove("hidden");
  el("modal-input").value = "";
  el("modal-input").focus();
}
function openWebShortcutModal() {
  modalMode = "web_shortcut";
  el("modal-title").textContent = "Add web shortcut";
  el("modal-input").placeholder = "https://example.com";
  el("modal-input").maxLength = 100;
  el("modal-overlay").classList.remove("hidden");
  el("modal-input").value = "";
  el("modal-input").focus();
}
function closeSectionModal() {
  el("modal-overlay").classList.add("hidden");
}
el("modal-cancel").addEventListener("click", closeSectionModal);
el("modal-confirm").addEventListener("click", async () => {
  const value = el("modal-input").value.trim();
  if (!value) return;
  if (modalMode === "web_shortcut") {
    let url = value;
    if (!/^https?:\/\//i.test(url)) url = "https://" + url;
    state.settings = await api().add_web_shortcut(url);
    closeSectionModal();
    await refreshItemPanel();
  } else {
    await api().add_custom_section(value);
    closeSectionModal();
    await refreshAfterSettingsChange();
  }
});
el("modal-input").addEventListener("keydown", (e) => {
  e.stopPropagation();
  if (e.key === "Enter") el("modal-confirm").click();
  if (e.key === "Escape") closeSectionModal();
});

// ---------------- appearance: background & overlay ----------------


// Per-theme background/overlay accessors (the settings moved from single
// values to {layout: path} dicts). Fall back to the legacy single keys so
// nothing breaks mid-migration.
function currentLayoutKey() {
  return (state.settings && state.settings.layout) || "dawning_horizon";
}
function themeBackground(settings) {
  const k = currentLayoutKey();
  return (settings.background_by_theme && settings.background_by_theme[k]) || null;
}
function themeOverlay(settings) {
  const k = currentLayoutKey();
  return (settings.overlay_by_theme && settings.overlay_by_theme[k]) || null;
}
function themeOverlayEnabled(settings) {
  const k = currentLayoutKey();
  return !!(settings.overlay_enabled_by_theme && settings.overlay_enabled_by_theme[k]);
}

function applyBackground(settings) {
  const layer = el("bg-image-layer");
  const custom = themeBackground(settings);
  if (custom) {
    // Works for static images and animated .gif alike — this is a plain
    // CSS background layer, so GIFs animate on their own.
    api().get_media_url(custom).then((url) => {
      layer.style.backgroundImage = `url("${url}")`;
    });
  } else {
    // No custom pick for this theme -> use the theme's rendered placeholder.
    api().theme_asset_urls().then((a) => {
      layer.style.backgroundImage = a && a.background ? `url("${a.background}")` : "none";
    });
  }
}


// Overlay show/hide. Bound to the Left Trigger (the only unused controller
// input) and the O key. This is a runtime toggle — it doesn't change the
// saved per-theme overlay setting, it just gets the frame out of the way.
let _overlayHidden = false;
function toggleOverlayVisibility() {
  _overlayHidden = !_overlayHidden;
  const c = el("overlay-canvas");
  if (c) c.style.visibility = _overlayHidden ? "hidden" : "";
  showToast(_overlayHidden ? "Overlay hidden" : "Overlay shown");
}

async function applyOverlay(settings) {
  const canvas = el("overlay-canvas");
  if (!themeOverlayEnabled(settings)) {
    canvas.classList.remove("active");
    return;
  }
  const custom = themeOverlay(settings);
  let url;
  if (custom) {
    url = await api().get_media_url(custom);
  } else {
    const a = await api().theme_asset_urls();
    url = a && a.overlay;
    if (!url) { canvas.classList.remove("active"); return; }
  }
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.onload = () => {
    drawOverlay(img);
    canvas.classList.add("active");
  };
  img.src = url;
  applyOverlay._img = img; // keep alive, redraw on resize
}

function drawOverlay(img) {
  const canvas = el("overlay-canvas");
  const w = window.innerWidth, h = window.innerHeight;
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, w, h);

  const scale = Math.max(w / img.width, h / img.height);
  const dw = img.width * scale, dh = img.height * scale;
  const dx = (w - dw) / 2, dy = (h - dh) / 2;
  ctx.drawImage(img, dx, dy, dw, dh);

  const data = ctx.getImageData(0, 0, w, h);
  const px = data.data;
  const THRESH = 235;
  for (let i = 0; i < px.length; i += 4) {
    if (px[i] > THRESH && px[i + 1] > THRESH && px[i + 2] > THRESH) {
      px[i + 3] = 0;
    }
  }
  ctx.putImageData(data, 0, 0);
}

window.addEventListener("resize", () => {
  if (applyOverlay._img) drawOverlay(applyOverlay._img);
});

// ---------------- music playback ----------------

const audioEl = () => el("audio-el");

function playMusicAt(i) {
  const item = state.items[i];
  if (!item) return;
  state.playIndex = i;
  // Snapshot the currently-displayed list as the shoulder-controls queue
  // - this used to be set nowhere at all (musicQueue/musicIndex stayed
  // permanently empty/0), which is why LB/RB/LB+RB never worked: they
  // read from a queue that was never populated, and their fallback path
  // called playFromQueueAt(), a function that didn't exist anywhere in
  // this file. Snapshotting (rather than pointing at state.items
  // directly) is what lets the shoulder controls keep working for this
  // queue even after navigating away from the Music section to browse
  // something else, per the queue's own original intent (see its
  // declaration up in `state`).
  state.musicQueue = state.items.slice();
  state.musicIndex = i;
  _playQueueItem(item);
}

// Real target of playPrevTrack/playNextTrack/playRandomTrack/the "ended"
// handler below - plays a track from the persistent shoulder-controls
// queue (which can outlive the Music section being the active list) and
// keeps state.playIndex in step too, so the Music list's own highlighted
// row stays correct if that's still what's on screen.
function playFromQueueAt(i) {
  const item = state.musicQueue[i];
  if (!item) return;
  state.musicIndex = i;
  const cat = state.categories[state.catIndex];
  if (cat && cat.kind === "media" && cat.id === "music") state.playIndex = i;
  _playQueueItem(item);
}

function _playQueueItem(item) {
  audioEl().src = item.url;
  audioEl().play();
  el("now-playing").classList.remove("hidden");
  el("np-title").textContent = item.title;
  el("np-artist").textContent = item.artist;
  el("np-thumb").src = item.thumbUrl || "";
  const cat = state.categories[state.catIndex];
  if (cat && cat.kind === "media" && cat.id === "music") renderItemList(cat);
}
audioEl().addEventListener("timeupdate", () => {
  const a = audioEl();
  if (a.duration) el("np-progress-fill").style.width = `${(a.currentTime / a.duration) * 100}%`;
});
audioEl().addEventListener("ended", () => {
  const q = state.musicQueue || [];
  if (!q.length) return;
  const shuffle = !state.settings || state.settings.auto_shuffle_songs !== false; // default on
  if (shuffle) {
    playRandomTrack();
  } else if (state.musicIndex < q.length - 1) {
    playFromQueueAt(state.musicIndex + 1);
  }
});
el("np-play").addEventListener("click", () => { const a = audioEl(); a.paused ? a.play() : a.pause(); });
el("np-next").addEventListener("click", () => playNextTrack());
el("np-prev").addEventListener("click", () => playPrevTrack());

// ---------------- video / photo overlays ----------------

function openVideo(i) {
  const item = state.items[i];
  const v = el("video-el");
  v.src = item.url;
  v.classList.toggle("video-fullscreen", !!(state.settings && state.settings.video_fullscreen));
  el("video-overlay").classList.remove("hidden");
  v.play();
}
function closeVideo() {
  const v = el("video-el");
  v.pause(); v.removeAttribute("src"); v.load();
  el("video-overlay").classList.add("hidden");
}
el("video-close").addEventListener("click", closeVideo);

// Controller (and equivalent keyboard) playback controls while a video is open.
function handleVideoControllerInput(action) {
  const v = el("video-el");
  if (action === "confirm") { if (v.paused) v.play(); else v.pause(); }
  else if (action === "left") { v.currentTime = Math.max(0, v.currentTime - 10); }
  else if (action === "right") { v.currentTime = Math.min(v.duration || v.currentTime + 10, v.currentTime + 10); }
  else if (action === "up") { v.volume = Math.min(1, v.volume + 0.1); }
  else if (action === "down") { v.volume = Math.max(0, v.volume - 0.1); }
  else if (action === "back") { closeVideo(); }
}

let photoIndex = 0;
function openPhoto(i) { photoIndex = i; showPhoto(); el("photo-overlay").classList.remove("hidden"); }
function showPhoto() { el("photo-el").src = state.items[photoIndex].fullUrl; }
function closePhoto() { el("photo-overlay").classList.add("hidden"); }
el("photo-close").addEventListener("click", closePhoto);
el("photo-prev").addEventListener("click", () => { photoIndex = (photoIndex - 1 + state.items.length) % state.items.length; showPhoto(); });
el("photo-next").addEventListener("click", () => { photoIndex = (photoIndex + 1) % state.items.length; showPhoto(); });

function isOverlayOpen() {
  return !el("video-overlay").classList.contains("hidden")
    || !el("photo-overlay").classList.contains("hidden")
    || !el("modal-overlay").classList.contains("hidden")
    || !el("wifi-password-overlay").classList.contains("hidden")
    || !el("network-overlay").classList.contains("hidden")
    || isConfirmOpen();
}

function handleBack() {
  // A plug-on with its taskbar hidden by layout prefs can have it
  // force-shown via X (see toggleTaskbarFocus/.addon-taskbar-forced).
  // B re-hides it rather than falling through to whatever Back normally
  // does. This only ever runs for a plug-on that ISN'T suspending
  // Meridian Launcher's own controls (see _controller_suspended_for_plugin
  // in main.py): a boxed program with independent controls of its own
  // owns all input while it's focused, so this handler simply never gets
  // reached for one of those - nothing extra to gate here for that case.
  if (document.body.classList.contains("addon-taskbar-forced")) {
    document.body.classList.remove("addon-taskbar-forced");
    return;
  }
  if (!el("video-overlay").classList.contains("hidden")) { closeVideo(); return; }
  if (!el("photo-overlay").classList.contains("hidden")) { closePhoto(); return; }
  if (!el("modal-overlay").classList.contains("hidden")) { closeSectionModal(); return; }
  if (!el("wifi-password-overlay").classList.contains("hidden")) { closeWifiPasswordModal(); return; }
  if (!el("network-overlay").classList.contains("hidden")) { closeNetworkOverlay(); return; }
  if (isConfirmOpen()) { handleConfirmOverlayInput("back"); return; }
  // Inside one of the five Settings options -> step back to that list first,
  // before Back starts unwinding the section focus cycle.
  {
    const _cat = state.categories[state.catIndex];
    if (_cat && _cat.kind === "settings" && state.settingsGroup && state.settingsGroup !== "menu") {
      state.settingsGroup = "menu";
      renderSettingsMenu();
      return;
    }
  }
  // Back always steps out one level of the focus cycle — subfolder ->
  // options -> sections — the same everywhere now. Going up a directory
  // within the subfolder list has its own dedicated ".." entry there, so
  // Back doesn't need to double as folder navigation too.
  if (state.radialFocus === "subfolder") { setRadialFocus("options"); return; }
  if (state.radialFocus === "options") { setRadialFocus("sections"); return; }
  // Nothing else to "back" out of — the category bar is always visible.
}

// B held for 2 seconds (see controller_input.py's B_HOLD_SECONDS): same
// "close whatever options section is open" as a normal back press, but
// instead of just landing on the Sections bar, jumps straight into the
// System section and opens it immediately.
function handleBackHoldSystem() {
  const idx = state.categories.findIndex((c) => c.id === "system");
  if (idx === -1) return;
  selectCategory(idx, true);
}

// Y (quick press) / \ key: jump straight to the subfolder panel from
// options, when there is one. NightHorizon/CyberRadial only — Dawning
// Horizon keeps its original Left-into-sidebar gesture for this.
function handleJumpToSubfolder() {
  if (!usesConfirmToLoadSections()) return;
  if (state.radialFocus === "options" && radialSubfolderAvailable()) setRadialFocus("subfolder");
}

// Left/right shoulder: prev/next track; both at once: random track. Same
// underlying mechanism as the now-playing widget's own prev/next buttons,
// so it's reliable while the Music section is what's actually loaded —
// same as those buttons already were.
function playPrevTrack() {
  const q = state.musicQueue || [];
  if (state.musicIndex > 0) playFromQueueAt(state.musicIndex - 1);
}
function playNextTrack() {
  const q = state.musicQueue || [];
  if (q.length && state.musicIndex < q.length - 1) playFromQueueAt(state.musicIndex + 1);
}
function playRandomTrack() {
  const q = state.musicQueue || [];
  if (!q.length) return;
  if (q.length === 1) { playFromQueueAt(0); return; }
  let idx = Math.floor(Math.random() * q.length);
  while (idx === state.musicIndex) idx = Math.floor(Math.random() * q.length);
  playFromQueueAt(idx);
}

// R3: stop playback outright (not pause-and-resume-later - back to a
// blank now-playing state, same as if nothing had ever been played).
function stopMusic() {
  const a = audioEl();
  a.pause();
  a.removeAttribute("src");
  a.load();
  el("now-playing").classList.add("hidden");
  state.musicQueue = [];
  state.musicIndex = 0;
  state.playIndex = -1;
}

// Right stick left/right: rewind/fast-forward the current track by
// `seconds` (negative = back). No-op with nothing loaded or no known
// duration yet (can't clamp sensibly before metadata arrives).
function seekMusic(seconds) {
  const a = audioEl();
  if (!a.src || !isFinite(a.duration) || a.duration <= 0) return;
  a.currentTime = Math.max(0, Math.min(a.duration, a.currentTime + seconds));
}

// ---------------- on-screen keyboard (controller-navigable) ----------------
// Shown automatically whenever a text/password input is focused, positioned
// below it. Real physical keyboard typing keeps working the whole time —
// see the "bail out for focused inputs" check in the keydown handler below.

const OSK_ROWS = [
  ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
  ["⇧", "z", "x", "c", "v", "b", "n", "m", "⌫"],
  // Symbols row: the punctuation actually needed for typing a URL
  // (dots/slashes/colon for the address itself, @ ? # & = for query
  // strings) or a section name (hyphens, underscores, parentheses),
  // without trying to cram in every ASCII symbol a full keyboard has.
  [".", "/", ":", "-", "_", "@", "?", "#", "&", "="],
  ["space", "done"],
];
let oskShift = false;
let oskRow = 1;
let oskCol = 0;
let oskInputEl = null;

function buildOsk() {
  const container = el("osk");
  container.innerHTML = "";
  OSK_ROWS.forEach((row, r) => {
    const rowEl = document.createElement("div");
    rowEl.className = "osk-row";
    row.forEach((key, c) => {
      const btn = document.createElement("div");
      btn.className = "osk-key" + (key === "space" || key === "done" ? " wide" : "");
      btn.textContent = key === "space" ? "Space" : key === "done" ? "Done" : key;
      btn.dataset.row = String(r);
      btn.dataset.col = String(c);
      btn.addEventListener("mousedown", (e) => e.preventDefault()); // don't steal focus from the real input
      btn.addEventListener("click", () => { oskRow = r; oskCol = c; activateOskKey(); });
      rowEl.appendChild(btn);
    });
    container.appendChild(rowEl);
  });
}

function highlightOskKey() {
  el("osk").querySelectorAll(".osk-key").forEach((btn) => {
    const isSel = Number(btn.dataset.row) === oskRow && Number(btn.dataset.col) === oskCol;
    btn.classList.toggle("osk-selected", isSel);
  });
}

function showOskFor(inputEl) {
  oskInputEl = inputEl;
  oskRow = 1; oskCol = 0;
  const osk = el("osk");
  osk.classList.remove("hidden");
  const rect = inputEl.getBoundingClientRect();
  osk.style.top = `${rect.bottom + 8}px`;
  osk.style.left = `${rect.left}px`;
  highlightOskKey();
}

function hideOsk() {
  el("osk").classList.add("hidden");
  oskInputEl = null;
}

function isOskCapturing() {
  return oskInputEl !== null && !el("osk").classList.contains("hidden");
}

function insertIntoOskInput(text) {
  if (!oskInputEl) return;
  oskInputEl.value += text;
  oskInputEl.dispatchEvent(new Event("input", { bubbles: true }));
}

function activateOskKey() {
  if (!oskInputEl) { highlightOskKey(); return; }
  const key = OSK_ROWS[oskRow][oskCol];
  if (key === "⇧") { oskShift = !oskShift; }
  else if (key === "⌫") { oskInputEl.value = oskInputEl.value.slice(0, -1); oskInputEl.dispatchEvent(new Event("input", { bubbles: true })); }
  else if (key === "space") { insertIntoOskInput(" "); }
  else if (key === "done") { const inp = oskInputEl; hideOsk(); inp.blur(); }
  else { insertIntoOskInput(oskShift ? key.toUpperCase() : key); oskShift = false; }
  highlightOskKey();
}

function handleOskControllerInput(action) {
  const row = OSK_ROWS[oskRow];
  if (action === "left") oskCol = Math.max(0, oskCol - 1);
  else if (action === "right") oskCol = Math.min(row.length - 1, oskCol + 1);
  else if (action === "up") { oskRow = Math.max(0, oskRow - 1); oskCol = Math.min(oskCol, OSK_ROWS[oskRow].length - 1); }
  else if (action === "down") { oskRow = Math.min(OSK_ROWS.length - 1, oskRow + 1); oskCol = Math.min(oskCol, OSK_ROWS[oskRow].length - 1); }
  else if (action === "confirm") { activateOskKey(); return; }
  else if (action === "back") { const inp = oskInputEl; hideOsk(); if (inp) inp.blur(); return; }
  highlightOskKey();
}

document.addEventListener("focusin", (e) => {
  if (e.target.tagName === "INPUT" && (e.target.type === "text" || e.target.type === "password")) {
    showOskFor(e.target);
  }
});
document.addEventListener("focusout", (e) => {
  if (e.target === oskInputEl) {
    setTimeout(() => { if (document.activeElement !== oskInputEl) hideOsk(); }, 120);
  }
});

// ---------------- intro video ----------------

async function playIntroIfConfigured() {
  const settings = state.settings;
  if (!settings.opening_video) { state.introDismissed = true; return; }
  const url = await api().get_media_url(settings.opening_video);
  const v = el("intro-video-el");
  v.src = url;
  el("intro-overlay").classList.remove("hidden");
  v.play().catch(() => {});
  const dismiss = () => {
    if (state.introDismissed) return;
    state.introDismissed = true;
    v.pause();
    el("intro-overlay").classList.add("hidden");
  };
  v.addEventListener("ended", dismiss);
  window.addEventListener("keydown", dismiss, { once: true });
  window.addEventListener("mousedown", dismiss, { once: true });
  window._dismissIntro = dismiss; // reachable from controller bridge
}

// ---------------- keyboard ----------------
// Confirm/Back/Escape are edge-triggered (ignore e.repeat) since they
// trigger discrete one-shot actions (launch, close, shut down, etc).
// Holding a key shouldn't be able to re-fire those — only Up/Down/Left/Right
// (pure browsing) are allowed to auto-repeat.

document.addEventListener("keydown", (e) => {
  if (!state.introDismissed) return; // any key handled by the intro dismiss listener

  // Let real typing through untouched whenever a text/password field has
  // focus — the on-screen keyboard (if visible) is driven by the
  // controller separately and doesn't compete with this.
  const active = document.activeElement;
  if (active && active.tagName === "INPUT" && (active.type === "text" || active.type === "password")) {
    if (e.key === "Escape") { e.preventDefault(); if (!e.repeat) api().quit_app(); }
    return;
  }

  if (e.key === "Escape") {
    e.preventDefault();
    if (!e.repeat) api().quit_app();
    return;
  }

  // Shift = keyboard equivalent of X: jump to/away from the open-programs
  // bar. Delete closes the highlighted task while the bar has focus (the
  // keyboard stand-in for holding X for 2 seconds).
  if (e.key === "o" || e.key === "O") { if (!e.repeat) toggleOverlayVisibility(); return; }
  // ContextMenu is the dedicated "Menu" key most keyboards have (next to
  // Right Ctrl) — keyboard equivalent of pressing Start on a controller.
  if (e.key === "ContextMenu") { if (!e.repeat) window.handleControllerInput("menu_start"); return; }
  if (e.key === "Shift") {
    if (!e.repeat && !isConfirmOpen()) toggleTaskbarFocus();
    return;
  }
  if (taskbarState.focused && !isConfirmOpen()) {
    const kcT = state.keyboardControls;
    if (kcT) {
      if (e.key === kcT.up) { e.preventDefault(); handleTaskbarInput("up"); return; }
      if (e.key === kcT.down) { e.preventDefault(); handleTaskbarInput("down"); return; }
      if (e.key === kcT.left) { e.preventDefault(); handleTaskbarInput("left"); return; }
      if (e.key === kcT.right) { e.preventDefault(); handleTaskbarInput("right"); return; }
      if (e.key === kcT.confirm) { e.preventDefault(); if (!e.repeat) handleTaskbarInput("confirm"); return; }
      if (e.key === kcT.back) { e.preventDefault(); if (!e.repeat) handleTaskbarInput("back"); return; }
    }
    if (e.key === "Delete") { if (!e.repeat) closeTaskbarSelection(); return; }
    if (e.key === "\\") { if (!e.repeat) handleTaskbarInput("y_subfolder"); return; }
    return;
  }

  const kc = state.keyboardControls;
  const mapped = kc && [kc.confirm, kc.back, kc.up, kc.down, kc.left, kc.right].includes(e.key);
  if (mapped) e.preventDefault(); // stop space-bar page scroll / arrow-key div scroll fighting our nav

  if (!el("video-overlay").classList.contains("hidden")) {
    if (kc && e.key === kc.confirm && !e.repeat) handleVideoControllerInput("confirm");
    else if (kc && e.key === kc.left) handleVideoControllerInput("left");
    else if (kc && e.key === kc.right) handleVideoControllerInput("right");
    else if (kc && e.key === kc.up) handleVideoControllerInput("up");
    else if (kc && e.key === kc.down) handleVideoControllerInput("down");
    else if (kc && e.key === kc.back && !e.repeat) handleVideoControllerInput("back");
    return;
  }

  if (isConfirmOpen()) {
    if (e.key === "ArrowLeft" || (kc && e.key === kc.left)) { handleConfirmOverlayInput("left"); return; }
    if (e.key === "ArrowRight" || (kc && e.key === kc.right)) { handleConfirmOverlayInput("right"); return; }
    if (kc && e.key === kc.confirm && !e.repeat) { handleConfirmOverlayInput("confirm"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handleConfirmOverlayInput("back"); return; }
    return;
  }

  if (isPhotoMenuOpen()) {
    if (e.key === "ArrowUp" || (kc && e.key === kc.up)) { handlePhotoMenuInput("up"); return; }
    if (e.key === "ArrowDown" || (kc && e.key === kc.down)) { handlePhotoMenuInput("down"); return; }
    if ((kc && e.key === kc.confirm && !e.repeat) || (e.key === "Enter" && !e.repeat)) { handlePhotoMenuInput("confirm"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handlePhotoMenuInput("back"); return; }
    return;
  }

  if (isStartMenuOpen()) {
    if (e.key === "ArrowUp" || (kc && e.key === kc.up)) { handleStartMenuInput("up"); return; }
    if (e.key === "ArrowDown" || (kc && e.key === kc.down)) { handleStartMenuInput("down"); return; }
    if ((kc && e.key === kc.confirm && !e.repeat) || (e.key === "Enter" && !e.repeat)) { handleStartMenuInput("confirm"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handleStartMenuInput("back"); return; }
    return;
  }

  if (isMusicSortMenuOpen()) {
    if (e.key === "ArrowUp" || (kc && e.key === kc.up)) { handleMusicSortMenuInput("up"); return; }
    if (e.key === "ArrowDown" || (kc && e.key === kc.down)) { handleMusicSortMenuInput("down"); return; }
    if ((kc && e.key === kc.confirm && !e.repeat) || (e.key === "Enter" && !e.repeat)) { handleMusicSortMenuInput("confirm"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handleMusicSortMenuInput("back"); return; }
    return;
  }

  if (isMusicItemMenuOpen()) {
    if (e.key === "ArrowUp" || (kc && e.key === kc.up)) { handleMusicItemMenuInput("up"); return; }
    if (e.key === "ArrowDown" || (kc && e.key === kc.down)) { handleMusicItemMenuInput("down"); return; }
    if ((kc && e.key === kc.confirm && !e.repeat) || (e.key === "Enter" && !e.repeat)) { handleMusicItemMenuInput("confirm"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handleMusicItemMenuInput("back"); return; }
    return;
  }

  if (isTutorialOpen()) {
    if (e.key === "ArrowLeft" || (kc && e.key === kc.left)) { handleTutorialInput("left"); return; }
    if (e.key === "ArrowRight" || (kc && e.key === kc.right)) { handleTutorialInput("right"); return; }
    if (kc && e.key === kc.back && !e.repeat) { handleTutorialInput("back"); return; }
    return;
  }

  if (isOverlayOpen()) {
    if (e.key === "ArrowLeft" && !el("photo-overlay").classList.contains("hidden")) el("photo-prev").click();
    else if (e.key === "ArrowRight" && !el("photo-overlay").classList.contains("hidden")) el("photo-next").click();
    else if (kc && e.key === kc.back && !e.repeat) handleBack();
    return;
  }

  if (!kc) return;
  if (e.key === kc.confirm) { if (!e.repeat) { if (_suppressNextConfirm) { _suppressNextConfirm = false; } else { activateCurrentSelection(); } } }
  else if (e.key === kc.back || e.key === "Backspace") { if (!e.repeat) handleBack(); }
  else if (e.key === "\\") { if (!e.repeat) handleJumpToSubfolder(); }
  else if (e.key === kc.up) moveSelection(-1);
  else if (e.key === kc.down) moveSelection(1);
  else if (e.key === kc.left) handleLeftNav();
  else if (e.key === kc.right) handleRightNav();
});

// ---------------- controller bridge (called from Python via evaluate_js) ----------------
// Note: confirm/back are already edge-triggered on the Python side (XInput
// rising-edge detection), so no repeat-guard is needed here for those.


// Focus gating: controller input keeps arriving while the app is in the
// background (so the Python-side foreground combo can fire), but it must
// NOT navigate or open menus until the app is the foreground window again.
// We poll a cheap backend check and cache the result.
let _isForeground = true;
async function _pollForeground() {
  try { _isForeground = await api().is_foreground(); } catch (e) { _isForeground = true; }
}
setInterval(_pollForeground, 400);
_pollForeground();

window.handleControllerInput = function (action) {
  if (action === "toggle_overlay") { toggleOverlayVisibility(); return; }
  if (!state.introDismissed) return;
  if (!_isForeground) return; // backgrounded: receive but don't act
  if (isOskCapturing()) { handleOskControllerInput(action); return; }
  if (!el("video-overlay").classList.contains("hidden")) { handleVideoControllerInput(action); return; }
  if (isConfirmOpen()) { handleConfirmOverlayInput(action); return; }
  if (isPhotoMenuOpen()) { handlePhotoMenuInput(action); return; }
  if (isStartMenuOpen()) { handleStartMenuInput(action); return; }
  if (isMusicSortMenuOpen()) { handleMusicSortMenuInput(action); return; }
  if (isMusicItemMenuOpen()) { handleMusicItemMenuInput(action); return; }
  if (isTutorialOpen()) { handleTutorialInput(action); return; }
  if (isOverlayOpen()) {
    if (action === "left" && !el("photo-overlay").classList.contains("hidden")) el("photo-prev").click();
    else if (action === "right" && !el("photo-overlay").classList.contains("hidden")) el("photo-next").click();
    else if (action === "back") handleBack();
    return;
  }
  if (action === "x_taskbar") { toggleTaskbarFocus(); return; }
  if (taskbarState.focused) { handleTaskbarInput(action); return; }
  if (action === "x_taskbar_hold") return; // hold-to-close only applies inside the bar
  if (action === "confirm") { if (_suppressNextConfirm) { _suppressNextConfirm = false; } else { activateCurrentSelection(); } }
  else if (action === "menu_start") handleMenuStart();
  else if (action === "back") handleBack();
  else if (action === "back_hold_system") handleBackHoldSystem();
  else if (action === "y_subfolder") handleJumpToSubfolder();
  else if (action === "prev_track") playPrevTrack();
  else if (action === "next_track") playNextTrack();
  else if (action === "random_track") playRandomTrack();
  else if (action === "stop_music") stopMusic();
  else if (action === "seek_back_10") seekMusic(-10);
  else if (action === "seek_fwd_10") seekMusic(10);
  else if (action === "up") moveSelection(-1);
  else if (action === "down") moveSelection(1);
  else if (action === "left") handleLeftNav();
  else if (action === "right") handleRightNav();
};

window.handleControllerAny = function () {
  if (!state.introDismissed && window._dismissIntro) window._dismissIntro();
};


// ---------------- open-programs bar (taskbar replacement) ----------------
// A controller-first stand-in for the Windows taskbar: every open,
// taskbar-visible window as an icon box. X (or Shift) jumps focus into
// the bar, A refocuses the highlighted program, B returns to the sections
// bar, holding X for 2s closes the task (with a confirm unless the
// "Close tasks without prompt" setting is on), and Y still jumps to the
// subfolder panel like everywhere else.
//
// PLACEMENT IS PER-THEME AND DELIBERATELY UNSET FOR NOW: each layout gets
// an entry below ({ orientation: "horizontal"|"vertical", position:
// <css class suffix> }) once its spot in that theme is decided. While a
// layout's entry is null the bar stays hidden there and X/Shift do
// nothing, so shipping the machinery early changes no existing theme.
const TASKBAR_PLACEMENT = {
  dawning_horizon: { orientation: "vertical", position: "dawning" },
  // horizontal, along the bottom edge, left side starting at the edge of
  // the clock/battery sidebar, ending at the bottom-right corner.
  night_horizon: { orientation: "horizontal", position: "night" },
  // horizontal, bottom edge, from the left edge to the left side of the
  // bottom-right clock/battery block.
  cyber_radial: { orientation: "horizontal", position: "cyber" },
};

const taskbarState = { focused: false, index: 0, tasks: [], pollTimer: null };

function taskbarPlacement() {
  const layout = (state.settings && state.settings.layout) || "dawning_horizon";
  return TASKBAR_PLACEMENT[layout] || null;
}

function ensureTaskbarDom() {
  if (el("task-bar")) return;
  const bar = document.createElement("div");
  bar.id = "task-bar";
  bar.className = "hidden";
  bar.innerHTML = `
    <div id="task-bar-bubble" class="hidden"></div>
    <div id="task-bar-list"></div>`;
  document.body.appendChild(bar);
}

function applyTaskbarPlacement() {
  try {
    _applyTaskbarPlacement();
  } catch (e) {
    // The open-programs bar must never take the whole layout down with it;
    // if anything here fails, the rest of the UI still renders.
    console.error("taskbar placement failed:", e);
  }
}

function _applyTaskbarPlacement() {
  ensureTaskbarDom();
  const bar = el("task-bar");
  if (!bar || !bar.classList) return;
  const placement = taskbarPlacement();
  bar.classList.remove("taskbar-horizontal", "taskbar-vertical");
  // clear any previous position class (theme switches) — iterate a copied
  // array of names rather than spreading the live DOMTokenList
  Array.prototype.slice.call(bar.classList)
    .filter((c) => c.indexOf("taskbar-pos-") === 0)
    .forEach((c) => bar.classList.remove(c));
  if (!placement) {
    bar.classList.add("hidden");
    if (taskbarState.focused) exitTaskbar();
    if (taskbarState.pollTimer) { clearInterval(taskbarState.pollTimer); taskbarState.pollTimer = null; }
    return;
  }
  bar.classList.add(placement.orientation === "vertical" ? "taskbar-vertical" : "taskbar-horizontal");
  if (placement.position) bar.classList.add(`taskbar-pos-${placement.position}`);
  bar.classList.remove("hidden");
  syncTaskbarSizeToLayout();
  refreshTaskbarTasks();
  if (!taskbarState.pollTimer) {
    taskbarState.pollTimer = setInterval(refreshTaskbarTasks, 2500);
  }
}

async function refreshTaskbarTasks() {
  try {
    taskbarState.tasks = (await api().list_open_tasks()) || [];
  } catch (e) {
    taskbarState.tasks = [];
  }
  if (taskbarState.index >= taskbarState.tasks.length) {
    taskbarState.index = Math.max(0, taskbarState.tasks.length - 1);
  }
  renderTaskbar();
}

function renderTaskbar() {
  const list = el("task-bar-list");
  if (!list) return;
  list.innerHTML = "";
  taskbarState.tasks.forEach((t, i) => {
    const box = document.createElement("div");
    box.className = "task-box" + (taskbarState.focused && i === taskbarState.index ? " selected" : "");
    if (t.icon) {
      const img = document.createElement("img");
      img.src = t.icon;
      img.alt = "";
      box.appendChild(img);
    } else {
      const ph = document.createElement("span");
      ph.className = "task-box-placeholder";
      ph.textContent = (t.title || "?").charAt(0).toUpperCase();
      box.appendChild(ph);
    }
    if (t.resources) {
      const cpu = t.resources.cpu_percent;
      const badge = document.createElement("span");
      badge.className = "task-res-badge" + (cpu >= 50 ? " res-high" : cpu >= 20 ? " res-med" : "");
      badge.textContent = `${Math.round(cpu)}%`;
      box.appendChild(badge);
      box.title = `${t.title}\n${cpu.toFixed(1)}% CPU  ·  ${formatMb(t.resources.mem_mb)} RAM`;
    } else {
      box.title = t.title || "";
    }
    // Mouse interaction:
    //  - single click: focus the item in the bar
    //  - double click: activate it (focus that window)
    //  - press & hold 2s, then release: close it
    let holdTimer = null;
    let heldLongEnough = false;
    box.addEventListener("mousedown", () => {
      heldLongEnough = false;
      holdTimer = setTimeout(() => { heldLongEnough = true; }, 2000);
    });
    box.addEventListener("mouseup", () => {
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      taskbarState.index = i;
      if (!taskbarState.focused) enterTaskbar();
      if (heldLongEnough) {
        // held the full 2s -> close on release
        closeTaskbarSelection();
      }
      renderTaskbar();
    });
    box.addEventListener("mouseleave", () => {
      if (holdTimer) { clearTimeout(holdTimer); holdTimer = null; }
      heldLongEnough = false;
    });
    box.addEventListener("dblclick", () => {
      taskbarState.index = i;
      activateTaskbarSelection(); // open/focus the window
    });
    list.appendChild(box);
  });
  updateTaskbarBubble();
}

function formatMb(mb) {
  if (mb == null) return "?";
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${Math.round(mb)} MB`;
}

// The name bubble is FIXED in place (anchored just above the bar in
// horizontal mode, beside it in vertical mode via CSS) — it changes text,
// never position, so the eye always knows where to look.
function updateTaskbarBubble() {
  const bubble = el("task-bar-bubble");
  if (!bubble) return;
  const t = taskbarState.tasks[taskbarState.index];
  if (taskbarState.focused && t) {
    if (t.resources) {
      bubble.innerHTML = `${escapeHtml(t.title)}<span class="task-bar-bubble-res">${t.resources.cpu_percent.toFixed(1)}% CPU &middot; ${formatMb(t.resources.mem_mb)} RAM</span>`;
    } else {
      bubble.textContent = t.title;
    }
    bubble.classList.remove("hidden");
  } else {
    // Unload the name entirely when the bar isn't the section being
    // selected from; it's repopulated when focus returns to the bar.
    bubble.textContent = "";
    bubble.classList.add("hidden");
  }
}

function enterTaskbar() {
  if (!taskbarPlacement()) return; // not placed in this theme (yet)
  taskbarState.focused = true;
  el("task-bar").classList.add("focused");
  refreshTaskbarTasks();
}

function exitTaskbar() {
  taskbarState.focused = false;
  const bar = el("task-bar");
  if (bar) bar.classList.remove("focused");
  updateTaskbarBubble();
  renderTaskbar();
}

function isEmbeddedPluginSectionActive() {
  const cat = state.categories[state.catIndex];
  return !!(state.chatPluginActive || (cat && (cat.kind === "browser_section" || cat.kind === "plugin_webapp")));
}

function toggleTaskbarFocus() {
  // Meridian FileBrowse/NetBrowse/webapp plugins own all input while
  // loaded — switching to the taskbar mid-section would fight over
  // controls with whatever's boxed in there, so it's blocked entirely
  // until that section is exited. Exception: an addon with the taskbar
  // hidden by its own layout prefs still lets X force it visible - see
  // the .addon-show-taskbar/.addon-taskbar-forced CSS. This only
  // actually shows anything if the addon's window_position preset
  // doesn't fully cover the taskbar's screen area (see that CSS
  // comment); it's still safe to allow even when it wouldn't be
  // visible, since nothing else about input ownership changes here.
  if (isEmbeddedPluginSectionActive()) {
    if (state.activeAddonLayout && state.activeAddonLayout.show_taskbar === false) {
      document.body.classList.toggle("addon-taskbar-forced");
    }
    return;
  }
  if (taskbarState.focused) exitTaskbar();
  else enterTaskbar();
}

function moveTaskbarSelection(delta) {
  const n = taskbarState.tasks.length;
  if (!n) return;
  taskbarState.index = (taskbarState.index + delta + n) % n;
  renderTaskbar();
}

async function activateTaskbarSelection() {
  const t = taskbarState.tasks[taskbarState.index];
  if (!t) return;
  await api().focus_task(t.id);
}

async function closeTaskbarSelection() {
  const t = taskbarState.tasks[taskbarState.index];
  if (!t) return;
  const skipPrompt = !!(state.settings && state.settings.close_tasks_without_prompt);
  const ok = skipPrompt ? true : await openConfirmModal("Close task", `Close "${t.title}"?`);
  if (!ok) return;
  await api().close_task(t.id);
  showToast(`Asked "${t.title}" to close.`);
  setTimeout(refreshTaskbarTasks, 500);
}

function handleTaskbarInput(action) {
  const placement = taskbarPlacement() || { orientation: "horizontal" };
  const horizontal = placement.orientation !== "vertical";
  const prev = horizontal ? "left" : "up";
  const next = horizontal ? "right" : "down";
  if (action === prev) moveTaskbarSelection(-1);
  else if (action === next) moveTaskbarSelection(1);
  else if (action === "confirm") activateTaskbarSelection();
  else if (action === "back") exitTaskbar(); // back to the sections bar
  else if (action === "x_taskbar") exitTaskbar();
  else if (action === "x_taskbar_hold") closeTaskbarSelection();
  else if (action === "y_subfolder") { exitTaskbar(); handleJumpToSubfolder(); }
}


// Live controller-backend indicator inside the controls block: which API
// (GameInput / XInput / none) is actually driving input, and whether a
// pad is connected right now. Refreshes while the settings screen is up.

// ---------------- controller debugger ----------------
// Polls controller_debug() while the panel is on screen and renders a plain
// readout. The point is to make each stage of the pipeline visible:
// backend chosen -> readings arriving -> gamepad state decoded -> action
// dispatched to the UI. Whichever line stops updating is the broken stage.
let _ctrlDebugTimer = null;
function startControllerDebugPolling() {
  if (_ctrlDebugTimer) clearInterval(_ctrlDebugTimer);
  updateControllerDebug();
  _ctrlDebugTimer = setInterval(() => {
    if (!document.getElementById("controller-debug")) {
      clearInterval(_ctrlDebugTimer); _ctrlDebugTimer = null; return;
    }
    updateControllerDebug();
  }, 500);
}

async function updateControllerDebug() {
  const box = document.getElementById("controller-debug");
  if (!box) return;
  let d;
  try { d = await api().controller_debug(); } catch (e) { box.textContent = "debug unavailable: " + e; return; }
  const diag = d.diag || {};
  const st = diag.last_state;
  const lines = [];
  lines.push(`backend        : ${d.backend || "none"}  (input_backend setting: ${d.input_backend || "xinput"})`);
  if (d.env_override) lines.push(`env override   : MERIDIAN_INPUT_BACKEND=${d.env_override}`);
  if (diag.native_status) lines.push(`gameinput_native: ${diag.native_status}`);
  lines.push(`controller     : ${d.connected ? "connected" : "NOT connected"}`);
  lines.push(`app focused    : ${d.foreground === null ? "?" : (d.foreground ? "yes" : "no  (input is received but won't navigate)")}`);
  lines.push("");
  if (d.backend === "GameInput" || Object.keys(diag.slot_probe || {}).length) {
    lines.push("GameInput pipeline:");
    lines.push(`  stage        : ${diag.stage || "?"}`);
    lines.push(`  polls        : ${diag.polls || 0}`);
    lines.push(`  readings     : ${diag.readings || 0}   (no reading: ${diag.no_reading || 0})`);
    lines.push(`  states       : ${diag.states || 0}   (GetGamepadState false: ${diag.state_false || 0})`);
    lines.push(`  reading slot : ${d.gamepad_slot || diag.slot || "not resolved"}`);
    if (diag.last_hr !== null && diag.last_hr !== undefined) {
      const hr = diag.last_hr < 0 ? (diag.last_hr >>> 0).toString(16).toUpperCase() : diag.last_hr;
      lines.push(`  last HRESULT : 0x${hr}`);
    }
    const probe = diag.slot_probe || {};
    Object.keys(probe).forEach((k) => lines.push(`  slot ${k}      : ${probe[k]}`));
    lines.push("");
  }
  if (d.backend_errors && Object.keys(d.backend_errors).length) {
    lines.push("backend errors:");
    Object.keys(d.backend_errors).forEach((k) => lines.push(`  ${k}: ${d.backend_errors[k]}`));
    lines.push("");
  }
  // The decisive check: a wrong-but-plausible vtable slot returns zeros
  // forever, which is indistinguishable from an idle pad in one sample.
  if (d.backend === "GameInput" && (diag.states || 0) > 0) {
    const seen = diag.buttons_seen || 0;
    const anyInput = seen !== 0 || diag.stick_moved || diag.trigger_moved;
    lines.push(`input ever seen: ${anyInput ? "YES" : "NO  <-- slot " + (d.gamepad_slot || diag.slot) + " is decoding, but never sees input"}`);
    lines.push(`  buttons seen : 0x${(seen >>> 0).toString(16).toUpperCase().padStart(8, "0")}   (states with a button down: ${diag.nonzero_states || 0})`);
    lines.push(`  stick moved  : ${diag.stick_moved ? "yes" : "no"}    trigger moved: ${diag.trigger_moved ? "yes" : "no"}`);
    if (!anyInput) {
      lines.push("  >> press every button and waggle both sticks. If this stays");
      lines.push("     empty, this vtable slot is the wrong function. Turn on");
      lines.push("     'Prefer XInput' above to get working input meanwhile.");
    }
    lines.push("");
  }
  lines.push("raw pad state:");
  if (st) {
    lines.push(`  buttons ${st.buttons}   LT ${st.lt}  RT ${st.rt}`);
    lines.push(`  L stick ${st.lx}, ${st.ly}    R stick ${st.rx}, ${st.ry}`);
  } else {
    lines.push("  (none decoded yet)");
  }
  lines.push("");
  lines.push(`last action    : ${d.last_action || "(none yet)"}${d.last_action_age !== null && d.last_action_age !== undefined ? "   " + d.last_action_age + "s ago" : ""}`);
  box.textContent = lines.join("\n");
}

async function updateControllerStatusLine() {
  const elLine = document.getElementById("controller-status-line");
  if (!elLine) return;
  let st = null;
  try { st = await api().controller_status(); } catch (e) { st = null; }
  let text, cls;
  if (!st || !st.backend) {
    text = "Controller API: none available \u2014 keyboard/mouse only";
    cls = "status-bad";
  } else {
    text = `Controller API: ${st.backend} \u2014 ${st.connected ? "controller connected" : "no controller detected"}`;
    cls = st.connected ? "status-good" : "status-warn";
    if (st.override) text += ` (forced via MERIDIAN_INPUT_BACKEND=${st.override})`;
    // If GameInput was tried but rejected, show why (helps diagnose the
    // XInput fallback on Windows 11).
    if (st.backend === "GameInput" && st.gamepad_slot) {
      text += ` \u2014 reading slot ${st.gamepad_slot}`;
    }
    if (st.backend_errors && st.backend_errors.gameinput && st.backend !== "GameInput") {
      text += ` \u2014 GameInput unavailable: ${st.backend_errors.gameinput}`;
    }
  }
  elLine.textContent = text;
  elLine.className = `controller-status ${cls}`;
}
setInterval(updateControllerStatusLine, 2000);

// ---------------- kiosk mode: secret unlock code ----------------
// Works from anywhere, any time, regardless of what's on screen — matches
// physical DPAD/A/B on a controller or the literal arrow/b/a keys on a
// keyboard, independent of whatever confirm/back/etc. are remapped to.

const KIOSK_CODE_CONTROLLER = ["DPAD_UP", "DPAD_UP", "DPAD_DOWN", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "DPAD_LEFT", "DPAD_RIGHT", "B", "A"];
const KIOSK_CODE_KEYBOARD = ["arrowup", "arrowup", "arrowdown", "arrowdown", "arrowleft", "arrowright", "arrowleft", "arrowright", "b", "a"];
let controllerCodeBuffer = [];
let keyboardCodeBuffer = [];

window.handleRawControllerButton = function (name) {
  controllerCodeBuffer.push(name);
  if (controllerCodeBuffer.length > KIOSK_CODE_CONTROLLER.length) controllerCodeBuffer.shift();
  if (controllerCodeBuffer.length === KIOSK_CODE_CONTROLLER.length
      && controllerCodeBuffer.every((v, i) => v === KIOSK_CODE_CONTROLLER[i])) {
    controllerCodeBuffer = [];
    tryDisableKioskViaCode();
  }
};

document.addEventListener("keydown", (e) => {
  if (!state.introDismissed) return;
  const key = e.key.toLowerCase();
  if (!["arrowup", "arrowdown", "arrowleft", "arrowright", "b", "a"].includes(key)) return;
  keyboardCodeBuffer.push(key);
  if (keyboardCodeBuffer.length > KIOSK_CODE_KEYBOARD.length) keyboardCodeBuffer.shift();
  if (keyboardCodeBuffer.length === KIOSK_CODE_KEYBOARD.length
      && keyboardCodeBuffer.every((v, i) => v === KIOSK_CODE_KEYBOARD[i])) {
    keyboardCodeBuffer = [];
    tryDisableKioskViaCode();
  }
});

async function tryDisableKioskViaCode() {
  if (!state.settings || state.settings.window_mode !== "kiosk") return;
  const res = await api().disable_kiosk_via_code();
  if (res && res.ok) await exitKioskModeAndNotify();
}

// Rebuilds state.categories from current settings (Settings/System appear
// or disappear depending on kiosk state) and lands on a sane category if
// the one being viewed just vanished. Shared by every path that can flip
// kiosk mode in either direction.
async function refreshCategoriesAndLand() {
  const settings = await api().get_settings();
  state.settings = settings;
  const currentId = state.categories[state.catIndex] && state.categories[state.catIndex].id;
  state.categories = buildCategories(settings);
  let idx = state.categories.findIndex((c) => c.id === currentId);
  if (idx === -1) idx = 0;
  unloadEmbeddedBoxIfLeaving(idx);
  state.catIndex = idx;
  state.selected = 0;
  applyAccent();
  renderCategories();
  await refreshItemPanel();
}

async function applyKioskChangeAndRefresh() {
  await refreshCategoriesAndLand();
}

// Shared by every kiosk-exit path (secret code, 45s Y hold): refreshes the
// category list (Settings/System reappear), lands somewhere sane if the
// currently-viewed category just vanished, and confirms with a toast.
async function exitKioskModeAndNotify() {
  await refreshCategoriesAndLand();
  showToast("kiosk mode disabled");
}

window.onKioskDisabledExternally = function () { exitKioskModeAndNotify(); };

// Fired by main.py when a boxed embedded plugin (Meridian FileBrowse /
// Meridian NetBrowse) exits via its own "Exit Program" action, rather than
// the user navigating Meridian Launcher away from that section. Moves the
// selector back to the Sections bar; Meridian Launcher's own controls were
// already restored on the Python side before this fires.
// Called (via evaluate_js) by main.py's /internal/open-explorer endpoint —
// the target of the "Make Meridian FileBrowse the default shell browser"
// registration. Explorer is external-only now (no more boxed section to
// route into) - just launches it standalone with the requested path.
window.__meridianOpenPathInExplorer = async function (path) {
  const res = await api().open_meridian_explorer_path(path);
  if (res && res.ok === false) showToast(`Couldn't open: ${res.error}`);
};

// Called (via evaluate_js) by main.py's /internal/open-browser endpoint —
// the target of the "Make Meridian NetBrowse the default system web
// browser" registration.
window.__meridianOpenUrlInBrowser = async function (url) {
  if (!state.settings || !state.settings.browser_section_enabled) {
    state.settings = await api().set_browser_section_enabled(true);
    state.categories = buildCategories(state.settings);
  }
  const idx = state.categories.findIndex((c) => c.kind === "browser_section");
  if (idx === -1) return;
  state.browserPendingUrl = url;
  selectCategory(idx, true);
};

window.onEmbeddedPluginExited = function (which) {
  if (state.chatPluginActive && state.chatPluginActive === which) {
    // Launched from inside a section's list (Chat's Discord/Telegram/etc,
    // or a plug-on spliced into any built-in section) — go back to that
    // list, not all the way out to the Sections bar.
    state.chatPluginActive = null;
    document.body.classList.remove("embedded-plugin-active");
    if (state.activeAddonLayout) restoreAddonLayout();
    refreshItemPanel();
    return;
  }
  state.radialFocus = "sections";
  document.body.dataset.radialFocus = "sections";
  document.body.classList.remove("embedded-plugin-active");
  if (state.activeAddonLayout) restoreAddonLayout();
  renderCategories();
  // Don't call refreshItemPanel() here — for a still-boxed section (Browser/
  // a plugin webapp) it would immediately relaunch it. Show an inert
  // placeholder instead; navigating away and back in (selectCategory)
  // reloads it fresh.
  setSubfolderNavHidden(true);
  el("preview-pane").classList.add("hidden");
  el("item-panel").innerHTML = `<div class="empty-msg">Closed. Select this section again to reopen it.</div>`;
};

// ---------------- update available modal ----------------

function showUpdateModal(info, { manual = false } = {}) {
  let backdrop = document.getElementById("update-modal-backdrop");
  if (backdrop) backdrop.remove();

  backdrop = document.createElement("div");
  backdrop.id = "update-modal-backdrop";

  const box = document.createElement("div");
  box.className = "update-modal";

  const title = document.createElement("h3");
  title.textContent = "Update available";
  box.appendChild(title);

  const p = document.createElement("p");
  p.textContent = `Meridian Launcher ${info.latest} is out (you're on ${info.current}).`;
  box.appendChild(p);

  if (info.notes) {
    const notes = document.createElement("div");
    notes.className = "update-notes";
    notes.textContent = info.notes;
    box.appendChild(notes);
  }

  const actions = document.createElement("div");
  actions.className = "update-modal-actions";

  const laterBtn = document.createElement("button");
  laterBtn.textContent = manual ? "Close" : "Later";
  laterBtn.addEventListener("click", () => backdrop.remove());
  actions.appendChild(laterBtn);

  const updateBtn = document.createElement("button");
  updateBtn.className = "btn-primary";
  updateBtn.textContent = "Update Now";
  updateBtn.addEventListener("click", async () => {
    updateBtn.disabled = true;
    laterBtn.disabled = true;
    updateBtn.textContent = "Downloading...";
    const res = await api().start_update(info.download_url);
    if (res && res.ok === false) {
      updateBtn.disabled = false;
      laterBtn.disabled = false;
      updateBtn.textContent = "Update Now";
      showToast(res.error ? `Update failed: ${res.error}` : "Update failed.");
      return;
    }
    updateBtn.textContent = "Restarting...";
    p.textContent = "Downloaded. Meridian Launcher will close and the installer will open — follow its prompts to finish updating.";
  });
  actions.appendChild(updateBtn);

  box.appendChild(actions);
  backdrop.appendChild(box);
  document.body.appendChild(backdrop);
}

// Called by main.py once at boot (see _check_for_update_at_boot), only when
// an update is actually available — silent otherwise.
window.onUpdateAvailable = function (info) {
  showUpdateModal(info, { manual: false });
};

// ---------------- boot ----------------

// ---------------- NightHorizon: animated blob background ----------------
// A handful of soft circles drift and bounce, fused into lava-lamp-style
// blobs via the classic canvas blur+contrast "goo" trick (plain Canvas2D +
// a CSS filter — no WebGL, no external libs). Colors track whatever
// section is active (re-read from --active-accent every frame, cheap).
// Runs behind NightHorizon (and Game Library's equivalent "Verticular
// Blobs"); fades out when CyberRadial is active rather than tearing the
// canvas down and rebuilding it later.
let blobState = null;
function hexToRgbString(hex) {
  const m = hex.trim().replace("#", "");
  const full = m.length === 3 ? m.split("").map((c) => c + c).join("") : m;
  const n = parseInt(full, 16);
  if (Number.isNaN(n)) return "150,255,120";
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
}
function initBlobBackground() {
  if (blobState) return;
  const canvas = document.createElement("canvas");
  canvas.id = "blob-canvas";
  canvas.style.cssText = "position:fixed;inset:0;z-index:0;pointer-events:none;transition:opacity 500ms ease;filter:blur(20px) contrast(34) saturate(1.4);";
  const horizon = el("horizon-glow");
  horizon.insertAdjacentElement("afterend", canvas);
  const ctx = canvas.getContext("2d");

  const BLOB_COUNT = 16;
  const SPEED = 2.4; // 6x the original 0.4
  const blobs = Array.from({ length: BLOB_COUNT }, () => ({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    vx: (Math.random() - 0.5) * SPEED,
    vy: (Math.random() - 0.5) * SPEED,
    r: 40 + Math.random() * 60,
    shade: 0.75 + Math.random() * 0.5, // per-blob brightness variance around the accent color
    spin: Math.random() * Math.PI * 2,
    spinSpeed: (Math.random() < 0.5 ? -1 : 1) * (0.04 + Math.random() * 0.08),
  }));

  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  window.addEventListener("resize", resize);
  resize();

  function step() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const accentRgb = hexToRgbString(getComputedStyle(document.documentElement).getPropertyValue("--active-accent") || "#a6e83f");

    for (const b of blobs) {
      b.x += b.vx; b.y += b.vy;
      b.spin += b.spinSpeed;
      if (b.x - b.r < 0 || b.x + b.r > w) { b.vx *= -1; b.x = Math.max(b.r, Math.min(w - b.r, b.x)); }
      if (b.y - b.r < 0 || b.y + b.r > h) { b.vy *= -1; b.y = Math.max(b.r, Math.min(h - b.r, b.y)); }
    }

    for (const b of blobs) {
      const g = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r);
      g.addColorStop(0, `rgba(${accentRgb},${0.9 * b.shade})`);
      g.addColorStop(1, `rgba(${accentRgb},0)`);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2); ctx.fill();

      // spinning swirl: a brighter core orbiting inside the blob, spinning
      // around it as it drifts and bounces
      const sx = b.x + Math.cos(b.spin) * b.r * 0.42;
      const sy = b.y + Math.sin(b.spin) * b.r * 0.42;
      const sr = b.r * 0.32;
      const g2 = ctx.createRadialGradient(sx, sy, 0, sx, sy, sr);
      g2.addColorStop(0, `rgba(255,255,255,${0.35 * b.shade})`);
      g2.addColorStop(1, `rgba(${accentRgb},0)`);
      ctx.fillStyle = g2;
      ctx.beginPath(); ctx.arc(sx, sy, sr, 0, Math.PI * 2); ctx.fill();
    }

    canvas.style.opacity = (!isCyberRadial() && !isDawningHorizon()) ? "0.6" : "0";
    blobState.raf = requestAnimationFrame(step);
  }

  blobState = { canvas, blobs, raf: null };
  step();
}

// ---------------- Dawning Horizon: dancing silk threads ---------------
// Several glowing threads sweep out from the left-center of the screen in
// slow, waving arcs (silk-in-the-wind motion via a growing sine wave along
// each thread's length), colored with the active section's accent. Sparks
// occasionally break off and drift up/down and rightward, fading as they
// go. Runs only behind Dawning Horizon; fades out otherwise, same
// stay-alive-but-invisible approach as the blob canvas.
let threadState = null;
function initSilkThreads() {
  if (threadState) return;
  const canvas = document.createElement("canvas");
  canvas.id = "silk-canvas";
  canvas.style.cssText = "position:fixed;inset:0;z-index:0;pointer-events:none;transition:opacity 500ms ease;";
  const horizon = el("horizon-glow");
  horizon.insertAdjacentElement("afterend", canvas);
  const ctx = canvas.getContext("2d");

  const THREAD_COUNT = 7;
  const threads = Array.from({ length: THREAD_COUNT }, (_, i) => ({
    phase: Math.random() * Math.PI * 2,
    speed: 0.006 + Math.random() * 0.006,
    ampY: 36 + Math.random() * 56,
    yOffset: (i - (THREAD_COUNT - 1) / 2) * 24,
    length: 0.55 + Math.random() * 0.35,
  }));
  let particles = [];

  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  window.addEventListener("resize", resize);
  resize();

  function threadPoint(t, thr, w, h) {
    const originY = h / 2 + thr.yOffset;
    const x = t * w * thr.length;
    const wave = Math.sin(t * Math.PI * 2.2 + thr.phase) * thr.ampY * t; // amplitude grows with distance from the origin, like a swaying strand
    return { x, y: originY + wave };
  }

  function step() {
    const w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const accentRgb = hexToRgbString(getComputedStyle(document.documentElement).getPropertyValue("--active-accent") || "#fbbf24");

    threads.forEach((thr) => {
      thr.phase += thr.speed;
      ctx.beginPath();
      const segments = 40;
      for (let i = 0; i <= segments; i++) {
        const t = i / segments;
        const p = threadPoint(t, thr, w, h);
        if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
      }
      ctx.strokeStyle = `rgba(${accentRgb},0.5)`;
      ctx.lineWidth = 1.6;
      ctx.shadowColor = `rgba(${accentRgb},0.85)`;
      ctx.shadowBlur = 9;
      ctx.stroke();

      if (Math.random() < 0.06) {
        const t = Math.random();
        const p = threadPoint(t, thr, w, h);
        particles.push({ x: p.x, y: p.y, vx: 0.3 + Math.random() * 0.6, vy: (Math.random() - 0.5) * 1.2, life: 1, rgb: accentRgb });
      }
    });
    ctx.shadowBlur = 0;

    particles.forEach((p) => { p.x += p.vx; p.y += p.vy; p.vy += 0.01; p.life -= 0.012; });
    particles = particles.filter((p) => p.life > 0 && p.x < w + 20);
    particles.forEach((p) => {
      ctx.beginPath();
      ctx.fillStyle = `rgba(${p.rgb},${p.life})`;
      ctx.shadowColor = `rgba(${p.rgb},0.9)`;
      ctx.shadowBlur = 6;
      ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.shadowBlur = 0;

    canvas.style.opacity = isDawningHorizon() ? "0.8" : "0";
    threadState.raf = requestAnimationFrame(step);
  }

  threadState = { canvas, threads, raf: null };
  step();
}

async function boot() {
  tickClock();
  buildOsk();
  // Every theme's CSS gates things like the options/item panel behind
  // [data-radial-focus="..."] attribute selectors, but this was never set
  // before the first render — meaning on launch it was simply absent
  // until the first navigation happened to call setRadialFocusRaw(), and
  // themes whose *default* (unqualified) styling was "visible" showed the
  // item panel immediately instead of waiting for a section to be picked.
  document.body.dataset.radialFocus = "sections";
  const [settings, kc] = await Promise.all([api().get_settings(), api().get_keyboard_controls()]);
  state.settings = settings;
  state.keyboardControls = kc;
  await loadUserThemes(); // discover themes/ at startup so drop-ins just appear
  await loadChatOptions();
  state.categories = buildCategories(settings);

  // The controls hint text was removed per design; these spans may be
  // absent (kept commented in index.html for future use), so guard them.
  const _hc = el("hint-confirm"); if (_hc) _hc.textContent = `${kc.confirm} select`;
  const _hb = el("hint-back"); if (_hb) _hb.textContent = `${kc.back} back`;

  applyAccent();
  renderCategories();
  applyBackground(settings);
  await applyOverlay(settings);
  await updateBatteryIndicator();
  await refreshItemPanel(); // show the first category's content immediately, live
  // syncTaskbarSizeToLayout (called earlier via applyAccent -> applyLayoutClass)
  // ran before item-panel/clock-wrap had any real content, so on a cold
  // load it measured a 0-size or not-yet-laid-out rect and fell back to
  // the taskbar's plain oversized CSS instead of the synced size — it
  // only self-corrected the next time something re-rendered the item
  // list (e.g. picking an option). Re-run it now that there's an actual
  // layout to measure, after the browser has had a frame to paint it.
  requestAnimationFrame(() => { syncTaskbarSizeToLayout(); syncSubfolderNavWidth(); });
  initBlobBackground();
  initSilkThreads();

  await playIntroIfConfigured();
  await playRandomSongOnStartupIfConfigured();
  // Always started, regardless of the current input_backend setting -
  // _pollBrowserGamepad() checks that itself, fresh, every single frame
  // (see its own comment for why relying on a one-time check here used
  // to be fragile). Reading navigator.getGamepads() once per frame is
  // cheap enough that this costs nothing when it isn't the active
  // backend, and it means switching TO this backend later always finds
  // an already-running loop instead of depending on some other call site
  // (a Settings toggle click, a gamepadconnected event) to have fired.
  requestAnimationFrame(_pollBrowserGamepad);
}

// Separate from Auto Shuffle Songs (which only affects what happens once
// something already playing ends) - this plays one random track right
// after boot finishes, without navigating into the Music section at all.
async function playRandomSongOnStartupIfConfigured() {
  if (!state.settings || !state.settings.play_random_song_on_startup) return;
  try {
    let items = await api().scan_library("music");
    if (!items || !items.length) return;
    items = sortMusicItems(items, "random");
    state.musicQueue = items;
    state.musicIndex = 0;
    _playQueueItem(items[0]);
  } catch (e) {
    console.error("Couldn't start random song on startup:", e);
  }
}

// ---------------------------------------------------------------------
// Browser Gamepad API backend (Settings > Controls > "Browser Gamepad
// API") - polls navigator.getGamepads() directly in the frontend
// instead of Meridian Launcher reading the controller natively via
// gameinput_api.py. Whichever standard W3C Gamepad API implementation
// the WebView2/Chromium runtime this app is embedded in ships with
// handles the actual hardware access - notably, this has been found to
// keep working inside Windows' Xbox Full Screen Experience even when
// XInput/GameInput/DirectInput reads from native code don't, which is
// the whole reason this exists as an option: it sidesteps every one of
// the native-API reliability problems gameinput_api.py's other backends
// have had to work around (see that file's docstring) by not touching
// any of them at all.
//
// When this mode is selected (state.settings.input_backend ===
// "browser_gamepad"), main.py's own controller_input.py listener is
// left completely idle - open_gamepad(prefer=("browser_gamepad",))
// doesn't recognize that name as any of its real backends, so it just
// returns None and the Python-side polling thread never starts (see
// ControllerListener.start()). This loop is the only thing reading the
// controller in that mode, and it re-uses window.handleControllerInput
// (the exact same dispatch every other backend already funnels through)
// for everything, so all the app.js-side logic - menus, navigation,
// music controls, taskbar, etc - works identically regardless of which
// backend actually supplied the button press.
//
// Deliberately NOT the full feature set controller_input.py's own loop
// has: no quit combo (removed everywhere anyway), no foreground combo
// (this only runs while the app already has focus/is the active tab,
// so there's nothing to bring TO the foreground), no kiosk-exit Y-hold
// or raw-button kiosk-unlock code, no B-hold-2s System jump (added here
// too, actually - see below). Core navigation, confirm/back, Start
// menu, taskbar, and music transport controls are all covered.

const BROWSER_GAMEPAD_DEADZONE = 0.25;
const BROWSER_GAMEPAD_COOLDOWN_MS = 200;
const BROWSER_GAMEPAD_B_HOLD_MS = 2000;
const BROWSER_GAMEPAD_X_HOLD_MS = 2000;

// Standard W3C Gamepad API button/axis indices (the "standard" gamepad
// mapping - what every Xbox-shaped controller, and Chromium's own
// mapping for a DualShock/DualSense, normalizes to).
const BG_BUTTON = {
  A: 0, B: 1, X: 2, Y: 3,
  LEFT_SHOULDER: 4, RIGHT_SHOULDER: 5,
  LEFT_TRIGGER: 6, RIGHT_TRIGGER: 7,
  BACK: 8, START: 9,
  LEFT_THUMB: 10, RIGHT_THUMB: 11,
  DPAD_UP: 12, DPAD_DOWN: 13, DPAD_LEFT: 14, DPAD_RIGHT: 15,
  GUIDE: 16,
};

let _bgState = {
  lastFireAt: {},      // action -> timestamp, for the directional-repeat cooldown
  prevDpadHeld: {},    // up/down/left/right -> bool, for edge-triggered nav
  prevButtonHeld: {},  // confirm/back/menu_start/etc -> bool
  bHoldStart: null, bHoldFired: false,
  xHoldStart: null, xHoldFired: false,
  rstickSeekLatched: false,
  shouldersLatched: false,
};

function _bgCanFire(action) {
  const now = performance.now();
  const last = _bgState.lastFireAt[action] || 0;
  if (now - last >= BROWSER_GAMEPAD_COOLDOWN_MS) {
    _bgState.lastFireAt[action] = now;
    return true;
  }
  return false;
}

function _bgDeadzone(v) {
  return Math.abs(v) < BROWSER_GAMEPAD_DEADZONE ? 0 : v;
}

function _bgEdge(key, heldNow, fn) {
  const wasHeld = !!_bgState.prevButtonHeld[key];
  if (heldNow && !wasHeld) fn();
  _bgState.prevButtonHeld[key] = heldNow;
}

function _pollBrowserGamepad() {
  // Always reschedules itself, even when this isn't the active backend
  // right now - this used to return here WITHOUT calling
  // requestAnimationFrame again, which permanently killed the loop the
  // first time it ran before state.settings was populated (a real race
  // with boot()'s own async settings fetch, or gamepadconnected firing
  // very early) - once dead, it never resumed even after switching to
  // this backend later, since nothing else ever restarts it except the
  // few explicit call sites. Checking fresh every frame and no-op'ing
  // instead of dying is what actually makes this robust.
  if (!state.settings || state.settings.input_backend !== "browser_gamepad") {
    requestAnimationFrame(_pollBrowserGamepad);
    return;
  }
  const pads = (navigator.getGamepads && navigator.getGamepads()) || [];
  const gp = Array.prototype.find.call(pads, (p) => p && p.connected);
  if (!gp) return requestAnimationFrame(_pollBrowserGamepad);

  const btn = (i) => gp.buttons[i] && gp.buttons[i].pressed;

  // D-pad + left stick, both drive navigation - edge-triggered with the
  // same repeat cooldown controller_input.py's own _can_fire gives
  // real hardware, so holding a direction repeats at the same rate.
  const dpadUp = btn(BG_BUTTON.DPAD_UP) || _bgDeadzone(gp.axes[1] || 0) < 0;
  const dpadDown = btn(BG_BUTTON.DPAD_DOWN) || _bgDeadzone(gp.axes[1] || 0) > 0;
  const dpadLeft = btn(BG_BUTTON.DPAD_LEFT) || _bgDeadzone(gp.axes[0] || 0) < 0;
  const dpadRight = btn(BG_BUTTON.DPAD_RIGHT) || _bgDeadzone(gp.axes[0] || 0) > 0;
  if (dpadUp && _bgCanFire("up")) window.handleControllerInput("up");
  if (dpadDown && _bgCanFire("down")) window.handleControllerInput("down");
  if (dpadLeft && _bgCanFire("left")) window.handleControllerInput("left");
  if (dpadRight && _bgCanFire("right")) window.handleControllerInput("right");

  _bgEdge("confirm", btn(BG_BUTTON.A), () => window.handleControllerInput("confirm"));
  _bgEdge("back", btn(BG_BUTTON.B), () => window.handleControllerInput("back"));
  _bgEdge("menu_start", btn(BG_BUTTON.START), () => window.handleControllerInput("menu_start"));
  _bgEdge("y_subfolder", btn(BG_BUTTON.Y), () => window.handleControllerInput("y_subfolder"));
  _bgEdge("x_taskbar", btn(BG_BUTTON.X), () => window.handleControllerInput("x_taskbar"));
  _bgEdge("stop_music", btn(BG_BUTTON.RIGHT_THUMB), () => window.handleControllerInput("stop_music"));

  // B held 2s -> back_hold_system (same as controller_input.py's B_HOLD_SECONDS)
  if (btn(BG_BUTTON.B)) {
    if (_bgState.bHoldStart === null) { _bgState.bHoldStart = performance.now(); _bgState.bHoldFired = false; }
    else if (!_bgState.bHoldFired && performance.now() - _bgState.bHoldStart >= BROWSER_GAMEPAD_B_HOLD_MS) {
      _bgState.bHoldFired = true;
      window.handleControllerInput("back_hold_system");
    }
  } else {
    _bgState.bHoldStart = null; _bgState.bHoldFired = false;
  }

  // X held 2s -> x_taskbar_hold (close the highlighted task)
  if (btn(BG_BUTTON.X)) {
    if (_bgState.xHoldStart === null) { _bgState.xHoldStart = performance.now(); _bgState.xHoldFired = false; }
    else if (!_bgState.xHoldFired && performance.now() - _bgState.xHoldStart >= BROWSER_GAMEPAD_X_HOLD_MS) {
      _bgState.xHoldFired = true;
      window.handleControllerInput("x_taskbar_hold");
    }
  } else {
    _bgState.xHoldStart = null; _bgState.xHoldFired = false;
  }

  // Shoulders: single = prev/next track, both = random track
  const lb = btn(BG_BUTTON.LEFT_SHOULDER), rb = btn(BG_BUTTON.RIGHT_SHOULDER);
  if (lb && rb) {
    if (!_bgState.shouldersLatched) { _bgState.shouldersLatched = true; window.handleControllerInput("random_track"); }
  } else {
    _bgState.shouldersLatched = false;
    _bgEdge("prev_track", lb, () => window.handleControllerInput("prev_track"));
    _bgEdge("next_track", rb, () => window.handleControllerInput("next_track"));
  }

  // Right stick left/right: rewind/fast-forward 10s, edge-triggered on
  // crossing the deadzone (not repeat-fired while held over)
  const rx = _bgDeadzone(gp.axes[2] || 0);
  if (rx !== 0) {
    if (!_bgState.rstickSeekLatched) {
      _bgState.rstickSeekLatched = true;
      window.handleControllerInput(rx < 0 ? "seek_back_10" : "seek_fwd_10");
    }
  } else {
    _bgState.rstickSeekLatched = false;
  }

  requestAnimationFrame(_pollBrowserGamepad);
}

window.addEventListener("gamepadconnected", () => {
  if (state.settings && state.settings.input_backend === "browser_gamepad") {
    requestAnimationFrame(_pollBrowserGamepad);
  }
});

if (window.pywebview) boot();
else window.addEventListener("pywebviewready", boot);
