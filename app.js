// ==================== الإعدادات ====================
const API_BASE = window.RFID_API_BASE || "http://localhost:8000"; // بدّلها برابط سيرفرك بعد النشر
const GOOGLE_CLIENT_ID = window.RFID_GOOGLE_CLIENT_ID || ""; // حط Client ID من Google Cloud Console

let authToken = localStorage.getItem("token") || null;
let pendingAdminId = null;

// ==================== أدوات API ====================

async function api(path, options = {}) {
  const headers = options.headers || {};
  headers["Content-Type"] = "application/json";
  if (authToken) headers["Authorization"] = "Bearer " + authToken;

  const res = await fetch(API_BASE + path, { ...options, headers });
  let data = null;
  try { data = await res.json(); } catch (e) { /* بدون محتوى */ }

  if (!res.ok) {
    const msg = (data && data.detail) ? data.detail : t("err_generic");
    throw new Error(msg);
  }
  return data;
}

// ==================== شاشة الدخول: التنقل بين الخطوات ====================

function showLoginStep(step) {
  ["step-login", "step-set-password", "step-forgot", "step-reset"].forEach(id => {
    document.getElementById(id).style.display = (id === step) ? "block" : "none";
  });
  hideLoginMessages();
}

function showLoginError(msg) {
  const el = document.getElementById("login-error");
  el.textContent = msg;
  el.style.display = "block";
  document.getElementById("login-success").style.display = "none";
}
function showLoginSuccess(msg) {
  const el = document.getElementById("login-success");
  el.textContent = msg;
  el.style.display = "block";
  document.getElementById("login-error").style.display = "none";
}
function hideLoginMessages() {
  document.getElementById("login-error").style.display = "none";
  document.getElementById("login-success").style.display = "none";
}

// ==================== تسجيل الدخول بالإيميل وكلمة المرور ====================

document.getElementById("btn-login").addEventListener("click", async () => {
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  if (!email || !password) return;

  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    onLoginSuccess(data.token);
  } catch (e) {
    showLoginError(t("err_login"));
  }
});

document.getElementById("btn-show-forgot").addEventListener("click", () => showLoginStep("step-forgot"));
document.getElementById("btn-back-login-1").addEventListener("click", () => showLoginStep("step-login"));
document.getElementById("btn-back-login-2").addEventListener("click", () => showLoginStep("step-login"));

document.getElementById("btn-send-code").addEventListener("click", async () => {
  const email = document.getElementById("forgot-email").value.trim();
  if (!email) return;
  try {
    await api("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
    document.getElementById("reset-code").dataset.email = email;
    showLoginStep("step-reset");
  } catch (e) {
    showLoginError(e.message);
  }
});

document.getElementById("btn-reset-password").addEventListener("click", async () => {
  const email = document.getElementById("reset-code").dataset.email;
  const code = document.getElementById("reset-code").value.trim();
  const new_password = document.getElementById("reset-password").value;
  try {
    await api("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ email, code, new_password }),
    });
    showLoginStep("step-login");
    showLoginSuccess(t("save") + " ✔");
  } catch (e) {
    showLoginError(e.message);
  }
});

document.getElementById("btn-set-password").addEventListener("click", async () => {
  const password = document.getElementById("setpw-password").value;
  if (!password || !pendingAdminId) return;
  try {
    const data = await api("/auth/set-password", {
      method: "POST",
      body: JSON.stringify({ admin_id: pendingAdminId, password }),
    });
    onLoginSuccess(data.token);
  } catch (e) {
    showLoginError(e.message);
  }
});

// ==================== تسجيل الدخول عبر Google ====================

function initGoogleButton() {
  if (!window.google || !GOOGLE_CLIENT_ID) return;
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleCredential,
  });
  google.accounts.id.renderButton(document.getElementById("google-btn-container"), {
    theme: "filled_black", size: "large", shape: "pill", width: 300,
  });
}
window.addEventListener("load", () => setTimeout(initGoogleButton, 400));

async function handleGoogleCredential(response) {
  try {
    const data = await api("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token: response.credential }),
    });
    if (data.status === "logged_in") {
      onLoginSuccess(data.token);
    } else if (data.status === "needs_password") {
      pendingAdminId = data.admin_id;
      showLoginStep("step-set-password");
    }
  } catch (e) {
    showLoginError(e.message);
  }
}

function onLoginSuccess(token) {
  authToken = token;
  localStorage.setItem("token", token);
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("app-view").classList.add("active");
  loadOverview();
}

document.getElementById("btn-logout").addEventListener("click", () => {
  authToken = null;
  localStorage.removeItem("token");
  document.getElementById("app-view").classList.remove("active");
  document.getElementById("login-view").classList.remove("hidden");
  showLoginStep("step-login");
});

// ==================== التنقل بين الأقسام ====================

document.querySelectorAll(".nav-item[data-view]").forEach(btn => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});

function switchView(view) {
  document.querySelectorAll(".nav-item[data-view]").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view-section").forEach(s => s.classList.toggle("active", s.id === "view-" + view));

  if (view === "overview") loadOverview();
  if (view === "cards") loadCards();
  if (view === "emergency") loadEmergencyCards();
  if (view === "logs") loadLogs();
  if (view === "notifications") loadNotifications();
  if (view === "settings") loadSettings();
}

// ==================== لوحة التحكم (Overview) ====================

async function loadOverview() {
  try {
    const [cards, logs, unread] = await Promise.all([
      api("/cards"),
      api("/logs?limit=8"),
      api("/notifications/unread-count"),
    ]);

    document.getElementById("stat-total-cards").textContent = cards.length;
    document.getElementById("stat-allowed").textContent = cards.filter(c => c.status === "allowed").length;

    const today = new Date().toDateString();
    const todayCount = logs.filter(l => new Date(l.timestamp).toDateString() === today).length;
    document.getElementById("stat-today-events").textContent = todayCount;

    document.getElementById("stat-unread-notif").textContent = unread.unread;
    updateNotifBadge(unread.unread);

    renderRecentLogs(logs);
  } catch (e) { console.error(e); }
}

function renderRecentLogs(logs) {
  const el = document.getElementById("recent-logs-table");
  if (!logs.length) {
    el.innerHTML = `<div class="empty-state">${t("no_notifications")}</div>`;
    return;
  }
  el.innerHTML = `<table>
    <thead><tr><th>${t("table_name")}</th><th>${t("table_event")}</th><th>${t("table_time")}</th></tr></thead>
    <tbody>${logs.map(l => `
      <tr>
        <td>${escapeHtml(l.person_name || "-")}</td>
        <td>${eventBadge(l)}</td>
        <td class="mono">${formatTime(l.timestamp)}</td>
      </tr>`).join("")}
    </tbody></table>`;
}

function eventBadge(l) {
  if (!l.granted) return `<span class="badge badge-red">${t("denied")}</span>`;
  if (l.event_type === "entry") return `<span class="badge badge-green">${t("entry")}</span>`;
  return `<span class="badge badge-amber">${t("exit")}</span>`;
}

// ==================== فتح الباب عن بعد ====================

document.getElementById("btn-open-door").addEventListener("click", async () => {
  const btn = document.getElementById("btn-open-door");
  const label = btn.querySelector("span:last-child");
  const originalText = label.textContent;
  btn.disabled = true;
  label.textContent = t("opening");
  try {
    await api("/door/open", { method: "POST" });
    label.textContent = t("door_opened");
    setTimeout(() => { label.textContent = originalText; btn.disabled = false; }, 2000);
  } catch (e) {
    label.textContent = originalText;
    btn.disabled = false;
  }
});

// ==================== إدارة البطاقات ====================

let allCards = [];

async function loadCards() {
  try {
    allCards = await api("/cards");
    renderCardsTable(allCards, "cards-table", false);
  } catch (e) { console.error(e); }
}

async function loadEmergencyCards() {
  try {
    const cards = await api("/cards");
    renderCardsTable(cards.filter(c => c.is_emergency), "emergency-table", true);
  } catch (e) { console.error(e); }
}

function renderCardsTable(cards, containerId, emergencyView) {
  const el = document.getElementById(containerId);
  if (!cards.length) {
    el.innerHTML = `<div class="empty-state">—</div>`;
    return;
  }
  el.innerHTML = `<table>
    <thead><tr>
      <th>${t("table_uid")}</th><th>${t("table_name")}</th><th>${t("table_status")}</th>
      <th>${t("table_type")}</th>${emergencyView ? "" : `<th>${t("table_emergency")}</th>`}<th>${t("table_actions")}</th>
    </tr></thead>
    <tbody>${cards.map(c => `
      <tr>
        <td class="mono">${escapeHtml(c.uid)}</td>
        <td>${escapeHtml(c.person_name)}</td>
        <td>${c.status === "allowed" ? `<span class="badge badge-green">${t("allowed")}</span>` : `<span class="badge badge-red">${t("denied")}</span>`}</td>
        <td>${c.card_type === "temporary" ? `<span class="badge badge-amber">${t("temporary")}</span>` : `<span class="badge badge-blue">${t("permanent")}</span>`}</td>
        ${emergencyView ? "" : `<td>${c.is_emergency ? `<span class="badge badge-purple">${t("yes")}</span>` : t("no")}</td>`}
        <td class="row-actions">
          <button class="btn-sm" onclick="openEditCard(${c.id})">${t("edit")}</button>
          <button class="btn-sm danger" onclick="deleteCard(${c.id})">${t("delete")}</button>
        </td>
      </tr>`).join("")}
    </tbody></table>`;
}

document.getElementById("card-type").addEventListener("change", (e) => {
  document.getElementById("temp-fields").style.display = e.target.value === "temporary" ? "block" : "none";
});

document.getElementById("btn-add-card").addEventListener("click", () => openCardModal());
document.getElementById("btn-cancel-card").addEventListener("click", closeCardModal);

function openCardModal() {
  document.getElementById("card-modal-title").textContent = t("modal_add_card_title");
  document.getElementById("card-id").value = "";
  document.getElementById("card-uid").value = "";
  document.getElementById("card-name").value = "";
  document.getElementById("card-status").value = "allowed";
  document.getElementById("card-type").value = "permanent";
  document.getElementById("card-valid-from").value = "";
  document.getElementById("card-valid-to").value = "";
  document.getElementById("card-emergency").checked = false;
  document.getElementById("temp-fields").style.display = "none";
  document.getElementById("card-modal").classList.add("active");
}

window.openEditCard = function (id) {
  const c = allCards.find(x => x.id === id);
  if (!c) return;
  document.getElementById("card-modal-title").textContent = t("modal_edit_card_title");
  document.getElementById("card-id").value = c.id;
  document.getElementById("card-uid").value = c.uid;
  document.getElementById("card-name").value = c.person_name;
  document.getElementById("card-status").value = c.status;
  document.getElementById("card-type").value = c.card_type;
  document.getElementById("card-valid-from").value = c.valid_from ? c.valid_from.slice(0, 16) : "";
  document.getElementById("card-valid-to").value = c.valid_to ? c.valid_to.slice(0, 16) : "";
  document.getElementById("card-emergency").checked = !!c.is_emergency;
  document.getElementById("temp-fields").style.display = c.card_type === "temporary" ? "block" : "none";
  document.getElementById("card-modal").classList.add("active");
};

function closeCardModal() {
  document.getElementById("card-modal").classList.remove("active");
}

document.getElementById("btn-save-card").addEventListener("click", async () => {
  const id = document.getElementById("card-id").value;
  const payload = {
    uid: document.getElementById("card-uid").value.trim(),
    person_name: document.getElementById("card-name").value.trim(),
    status: document.getElementById("card-status").value,
    card_type: document.getElementById("card-type").value,
    valid_from: document.getElementById("card-valid-from").value || null,
    valid_to: document.getElementById("card-valid-to").value || null,
    is_emergency: document.getElementById("card-emergency").checked,
  };
  if (!payload.uid || !payload.person_name) return;

  try {
    if (id) {
      await api(`/cards/${id}`, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await api("/cards", { method: "POST", body: JSON.stringify(payload) });
    }
    closeCardModal();
    loadCards();
  } catch (e) {
    alert(e.message);
  }
});

window.deleteCard = async function (id) {
  if (!confirm(t("confirm_delete"))) return;
  try {
    await api(`/cards/${id}`, { method: "DELETE" });
    loadCards();
  } catch (e) { alert(e.message); }
};

// ==================== السجل ====================

async function loadLogs() {
  try {
    const logs = await api("/logs?limit=200");
    const el = document.getElementById("logs-table");
    if (!logs.length) {
      el.innerHTML = `<div class="empty-state">—</div>`;
      return;
    }
    el.innerHTML = `<table>
      <thead><tr>
        <th>${t("table_name")}</th><th>${t("table_uid")}</th><th>${t("table_event")}</th>
        <th>${t("table_reason")}</th><th>${t("table_time")}</th>
      </tr></thead>
      <tbody>${logs.map(l => `
        <tr>
          <td>${escapeHtml(l.person_name || "-")}</td>
          <td class="mono">${escapeHtml(l.card_uid || "-")}</td>
          <td>${eventBadge(l)} ${l.offline ? `<span class="badge badge-purple">${t("offline_badge")}</span>` : ""}</td>
          <td style="color:var(--text-dim);font-size:12px;">${l.reason || "-"}</td>
          <td class="mono">${formatTime(l.timestamp)}</td>
        </tr>`).join("")}
      </tbody></table>`;
  } catch (e) { console.error(e); }
}

// ==================== الإشعارات ====================

async function loadNotifications() {
  try {
    const notifs = await api("/notifications?limit=100");
    const el = document.getElementById("notifications-list");
    if (!notifs.length) {
      el.innerHTML = `<div class="empty-state">${t("no_notifications")}</div>`;
      return;
    }
    el.innerHTML = notifs.map(n => `
      <div class="notif-item ${n.is_read ? "read" : "unread"}">
        <span class="notif-dot"></span>
        <div>
          <div class="notif-title">${escapeHtml(currentLang === "ar" ? n.title_ar : n.title_en)}</div>
          <div class="notif-msg">${escapeHtml(currentLang === "ar" ? n.message_ar : n.message_en)}</div>
          <div class="notif-time mono">${formatTime(n.created_at)}</div>
        </div>
      </div>`).join("");

    const unread = await api("/notifications/unread-count");
    updateNotifBadge(unread.unread);
  } catch (e) { console.error(e); }
}

document.getElementById("btn-mark-all-read").addEventListener("click", async () => {
  try {
    await api("/notifications/read-all", { method: "PUT" });
    loadNotifications();
  } catch (e) { console.error(e); }
});

function updateNotifBadge(count) {
  const badge = document.getElementById("notif-badge");
  if (count > 0) {
    badge.textContent = count;
    badge.style.display = "inline-block";
  } else {
    badge.style.display = "none";
  }
}

// ==================== الإعدادات ====================

async function loadSettings() {
  try {
    const s = await api("/notifications/settings");
    document.getElementById("toggle-email-enabled").checked = !!s.notify_email_enabled;
    document.getElementById("toggle-on-denied").checked = !!s.notify_on_denied;
    document.getElementById("toggle-on-door-open").checked = !!s.notify_on_door_open;
    document.getElementById("toggle-on-emergency").checked = !!s.notify_on_emergency;
  } catch (e) { console.error(e); }
}

function bindSettingToggle(elId, field) {
  document.getElementById(elId).addEventListener("change", async (e) => {
    try {
      await api("/notifications/settings", {
        method: "PUT",
        body: JSON.stringify({ [field]: e.target.checked }),
      });
    } catch (err) { console.error(err); }
  });
}
bindSettingToggle("toggle-email-enabled", "notify_email_enabled");
bindSettingToggle("toggle-on-denied", "notify_on_denied");
bindSettingToggle("toggle-on-door-open", "notify_on_door_open");
bindSettingToggle("toggle-on-emergency", "notify_on_emergency");

// ==================== اللغة ====================

document.getElementById("btn-lang-toggle").addEventListener("click", () => {
  setLang(currentLang === "ar" ? "en" : "ar");
});

window.onLangChange = function () {
  document.getElementById("lang-label").textContent = currentLang === "ar" ? "EN" : "AR";
  // إعادة رسم الأقسام المفتوحة حالياً بلغتها الجديدة
  const activeView = document.querySelector(".nav-item.active")?.dataset.view;
  if (activeView) switchView(activeView);
};

// ==================== أدوات مساعدة ====================

function escapeHtml(str) {
  if (str == null) return "";
  return String(str).replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}

function formatTime(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString(currentLang === "ar" ? "ar-EG" : "en-US", { dateStyle: "short", timeStyle: "short" });
}

// ==================== البدء ====================

applyI18n();
document.getElementById("lang-label").textContent = currentLang === "ar" ? "EN" : "AR";

if (authToken) {
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("app-view").classList.add("active");
  loadOverview();
}
