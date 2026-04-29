// SmartDesk AI — Dashboard JS

const API_BASE = "";
let autoRefresh = true;
let refreshTimer = null;

// ---- Bootstrap ----
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    loadStats();
    loadRecent();
    startAutoRefresh();

    document.getElementById("btn-create-incident").addEventListener("click", createIncident);
    document.getElementById("btn-poll").addEventListener("click", triggerPoll);
    document.getElementById("btn-refresh").addEventListener("click", () => {
        loadStats();
        loadRecent();
    });
    document.getElementById("theme-toggle").addEventListener("click", toggleTheme);
});

// ---- Theme ----
function initTheme() {
    const saved = localStorage.getItem("smartdesk-theme") || "dark";
    document.documentElement.setAttribute("data-theme", saved);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("smartdesk-theme", next);
}

// ---- Toast Notifications ----
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icons = { success: "✓", error: "✕", info: "ℹ" };
    toast.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${esc(message)}`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add("toast-exit");
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ---- Auto-refresh ----
function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(() => {
        if (autoRefresh) {
            loadStats();
            loadRecent();
        }
    }, 15000);
}

// ---- API helpers ----
async function apiFetch(path) {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

async function apiPost(path, body = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// ---- Load stats ----
async function loadStats() {
    try {
        const data = await apiFetch("/api/stats");
        animateValue("stat-kb-size", data.knowledge_base_size ?? 0);
        animateValue("stat-processed", data.recent_processed ?? 0);
        const acc = data.accuracy?.accuracy ?? 0;
        document.getElementById("stat-accuracy").textContent = `${(acc * 100).toFixed(1)}%`;
        animateValue("stat-total-feedback", data.accuracy?.total ?? 0);
    } catch (e) {
        console.error("Failed to load stats:", e);
    }
}

function animateValue(id, newVal) {
    const el = document.getElementById(id);
    const current = parseInt(el.textContent) || 0;
    if (current === newVal) return;
    el.textContent = newVal;
    el.style.animation = "none";
    el.offsetHeight; // trigger reflow
    el.style.animation = "countUp 0.4s ease both";
}

// ---- Load recent incidents ----
async function loadRecent() {
    try {
        const data = await apiFetch("/api/recent");
        renderCreatedFeed(data.created || []);
        renderAssignedFeed(data.results || []);
    } catch (e) {
        console.error("Failed to load recent:", e);
    }
}

// ---- Render created (unassigned) feed ----
function renderCreatedFeed(created) {
    const feed = document.getElementById("created-feed");

    if (!created || created.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <div class="icon">📝</div>
                <p>No unassigned incidents.<br>Click "+ Create Incident" to generate one.</p>
            </div>`;
        return;
    }

    feed.innerHTML = created.map((c, i) => {
        const snowUrl = `https://dev375174.service-now.com/nav_to.do?uri=incident.do?sys_id=${encodeURIComponent(c.sys_id)}`;
        return `
        <div class="incident-card card-unassigned" style="animation-delay:${i * 0.06}s">
            <div class="card-header">
                <span class="inc-number">${esc(c.number)}</span>
                <span class="badge badge-pending">unassigned</span>
            </div>
            <div class="short-desc">${esc(c.short_description)}</div>
            <div class="tags">
                <span class="badge badge-category">${esc(c.category)}</span>
                <span style="font-size:0.76rem;color:var(--text-muted);">Urgency: ${esc(c.urgency)} | Impact: ${esc(c.impact)}</span>
            </div>
            <div class="card-actions">
                <button class="btn btn-assign" onclick="assignIncident('${esc(c.sys_id)}', this)">
                    🤖 Assign with AI
                </button>
                <a href="${snowUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-snow">
                    🔗 Open in ServiceNow
                </a>
            </div>
        </div>`;
    }).join("");
}

// ---- Render assigned incidents feed ----
function renderAssignedFeed(results) {
    const feed = document.getElementById("incident-feed");
    const teamMap = {};

    if (!results || results.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <p>No incidents assigned yet.<br>Create an incident, then click "Assign" to trigger the AI agent.</p>
            </div>`;
        renderTeamBreakdown({});
        return;
    }

    feed.innerHTML = results.map((r, i) => {
        teamMap[r.assigned_team] = (teamMap[r.assigned_team] || 0) + 1;

        const confPct = (r.confidence * 100).toFixed(0);
        const confColor = r.confidence >= 0.8 ? "var(--green)"
            : r.confidence >= 0.5 ? "var(--yellow)" : "var(--red)";

        const snowUrl = `https://dev375174.service-now.com/nav_to.do?uri=incident.do?sys_id=${encodeURIComponent(r.sys_id)}`;

        return `
        <div class="incident-card" style="animation-delay:${i * 0.06}s">
            <div class="card-header">
                <span class="inc-number">${esc(r.incident_number)}</span>
                <span class="badge badge-action-${r.action}">${r.action.replace("_", " ")}</span>
            </div>
            <div class="short-desc">${esc(r.short_description || r.summary)}</div>
            <div class="tags">
                <span class="badge badge-category">${esc(r.category)}</span>
                <span class="badge badge-severity-${r.severity.toLowerCase()}">${esc(r.severity)}</span>
                <span class="badge badge-action-auto_assign">${esc(r.assigned_team)}</span>
            </div>
            <div class="confidence-bar-wrap">
                <span>Confidence</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width:${confPct}%;background:${confColor}"></div>
                </div>
                <span>${confPct}%</span>
            </div>
            <div class="card-actions">
                <a href="${snowUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-snow">
                    🔗 Open in ServiceNow
                </a>
            </div>
        </div>`;
    }).join("");

    renderTeamBreakdown(teamMap);
}

// ---- Team breakdown panel ----
function renderTeamBreakdown(teamMap) {
    const container = document.getElementById("team-breakdown");
    const entries = Object.entries(teamMap).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:0.82rem;">No data yet</p>';
        return;
    }
    container.innerHTML = entries.map(([team, count]) => `
        <div class="team-row">
            <span>${esc(team)}</span>
            <span class="count">${count}</span>
        </div>
    `).join("");
}

// ---- Create Incident (one-click, LLM auto-generates) ----
async function createIncident() {
    const btn = document.getElementById("btn-create-incident");
    btn.disabled = true;
    btn.textContent = "Generating…";
    try {
        const data = await apiPost("/api/create-incident");
        showToast(`Incident ${data.number} created`, "success");
        await loadStats();
        await loadRecent();
    } catch (e) {
        console.error("Create incident failed:", e);
        showToast("Failed to create incident", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "+ Create Incident";
    }
}

// ---- Assign Incident (triggers agentic pipeline for one ticket) ----
async function assignIncident(sysId, btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = "Assigning…";
    try {
        const data = await apiPost("/api/assign-incident", { sys_id: sysId });
        showToast(`Assigned to ${data.result?.assigned_team || "team"}`, "success");
        await loadStats();
        await loadRecent();
    } catch (e) {
        console.error("Assign failed:", e);
        showToast("Assignment failed", "error");
        btnEl.textContent = "Retry";
        btnEl.disabled = false;
    }
}

// ---- Trigger manual poll ----
async function triggerPoll() {
    const btn = document.getElementById("btn-poll");
    btn.disabled = true;
    btn.textContent = "Polling…";
    try {
        await apiPost("/api/poll-now");
        showToast("Poll complete", "info");
        await loadStats();
        await loadRecent();
    } catch (e) {
        console.error("Poll failed:", e);
        showToast("Poll failed", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Poll Now";
    }
}

// ---- Utility ----
function esc(str) {
    if (!str) return "";
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}
