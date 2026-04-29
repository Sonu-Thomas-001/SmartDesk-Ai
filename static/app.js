// SmartDesk AI — Dashboard JS

const API_BASE = "";
let autoRefresh = true;
let refreshTimer = null;

// ---- Bootstrap ----
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    loadStats();
    loadRecent();
    loadConfig();
    loadTeams();
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

async function apiPut(path, body = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
}

// ---- Load / Save Config ----
async function loadConfig() {
    try {
        const c = await apiFetch("/api/config");
        document.getElementById("cfg-auto-threshold").value = Math.round(c.auto_assign_threshold * 100);
        document.getElementById("cfg-suggest-threshold").value = Math.round(c.suggest_threshold * 100);
        document.getElementById("cfg-polling").value = c.polling_interval;
        document.getElementById("cfg-model").value = c.gemini_model;
    } catch (e) {
        console.error("Failed to load config:", e);
    }
}

async function saveConfig() {
    const btn = document.getElementById("btn-save-config");
    const msg = document.getElementById("config-saved-msg");
    btn.disabled = true;
    msg.textContent = "";
    try {
        const payload = {
            auto_assign_threshold: parseInt(document.getElementById("cfg-auto-threshold").value) / 100,
            suggest_threshold: parseInt(document.getElementById("cfg-suggest-threshold").value) / 100,
            polling_interval: parseInt(document.getElementById("cfg-polling").value),
            gemini_model: document.getElementById("cfg-model").value.trim(),
        };
        await apiPut("/api/config", payload);
        msg.textContent = "Saved ✓";
        msg.style.color = "var(--green)";
        showToast("Configuration saved", "success");
        setTimeout(() => { msg.textContent = ""; }, 3000);
    } catch (e) {
        console.error("Save config failed:", e);
        msg.textContent = "Error";
        msg.style.color = "var(--red)";
        showToast("Failed to save config", "error");
    } finally {
        btn.disabled = false;
    }
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

    if (!results || results.length === 0) {
        feed.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <p>No incidents assigned yet.<br>Create an incident, then click "Assign" to trigger the AI agent.</p>
            </div>`;
        renderTeamBreakdown();
        return;
    }

    feed.innerHTML = results.map((r, i) => {
        const confPct = (r.confidence * 100).toFixed(0);
        const confColor = r.confidence >= 0.8 ? "var(--green)"
            : r.confidence >= 0.5 ? "var(--yellow)" : "var(--red)";

        const snowUrl = `https://dev375174.service-now.com/nav_to.do?uri=incident.do?sys_id=${encodeURIComponent(r.sys_id)}`;

        const hasResolution = r.resolution && r.resolution.steps;
        let resolutionHtml = '';
        if (hasResolution) {
            const res = r.resolution;
            resolutionHtml = `
            <div class="resolution-section">
                <div class="resolution-header" onclick="toggleResolution(this)">
                    <span>📋 Resolution Guide: ${esc(res.resolution_title || '')}</span>
                    <span class="resolution-toggle">▶</span>
                </div>
                <div class="resolution-body" style="display:none">
                    <div class="resolution-meta">
                        <span class="badge badge-category">⏱ ${esc(res.estimated_resolution_time || 'N/A')}</span>
                        ${(res.kb_articles_used || []).map(kb => `<span class="badge badge-kb">${esc(kb)}</span>`).join('')}
                    </div>
                    <div class="resolution-steps">
                        ${(res.steps || []).map(s => `
                            <div class="resolution-step">
                                <div class="step-number">${s.step_number}</div>
                                <div class="step-content">
                                    <div class="step-action">${esc(s.action)}</div>
                                    <div class="step-details">${esc(s.details)}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    ${(res.warnings || []).length ? `
                        <div class="resolution-warnings">
                            ${res.warnings.map(w => `<div class="warning-item">⚠️ ${esc(w)}</div>`).join('')}
                        </div>
                    ` : ''}
                    ${res.escalation_note ? `
                        <div class="resolution-escalation">
                            <strong>Escalation:</strong> ${esc(res.escalation_note)}
                        </div>
                    ` : ''}
                </div>
            </div>`;
        }

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
            ${r.assigned_to ? `<div class="assigned-to-row">👤 <strong>${esc(r.assigned_to)}</strong> <span style="color:var(--text-muted)">· ${esc(r.assigned_team)}</span></div>` : ''}
            <div class="confidence-bar-wrap">
                <span>Confidence</span>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width:${confPct}%;background:${confColor}"></div>
                </div>
                <span>${confPct}%</span>
            </div>
            ${resolutionHtml}
            <div class="card-actions">
                ${!hasResolution ? `<button class="btn btn-resolve" onclick="resolveIncident('${esc(r.sys_id)}', this)">📋 Get Resolution Steps</button>` : ''}
                <a href="${snowUrl}" target="_blank" rel="noopener noreferrer" class="btn btn-snow">
                    🔗 Open in ServiceNow
                </a>
            </div>
        </div>`;
    }).join("");

    loadTeams();
}

// ---- Team breakdown panel ----
let _teamData = [];

async function loadTeams() {
    try {
        const data = await apiFetch("/api/teams");
        _teamData = data.teams || [];
        renderTeamBreakdown();
    } catch (e) {
        console.error("Failed to load teams:", e);
    }
}

function renderTeamBreakdown() {
    const container = document.getElementById("team-breakdown");
    if (!_teamData.length) {
        container.innerHTML = '<p class="panel-empty">No teams configured</p>';
        return;
    }

    container.innerHTML = _teamData.map(t => {
        const memberList = t.members.map(m => {
            const isLead = m === t.lead;
            return `<span class="team-member${isLead ? ' team-lead' : ''}">${esc(m)}${isLead ? ' ★' : ''}</span>`;
        }).join("");

        return `
        <div class="team-group">
            <div class="team-group-header">
                <span class="team-group-name">${esc(t.name)}</span>
                <span class="count">${t.assigned_count}</span>
            </div>
            <div class="team-members">${memberList}</div>
        </div>`;
    }).join("");
}

// ---- Create Incident (one-click, LLM auto-generates) ----
async function createIncident() {
    const btn = document.getElementById("btn-create-incident");
    btn.disabled = true;
    btn.textContent = "Generating 5…";
    try {
        const data = await apiPost("/api/create-incident");
        const count = data.count || data.incidents?.length || 1;
        showToast(`${count} incidents created`, "success");
        await loadStats();
        await loadRecent();
    } catch (e) {
        console.error("Create incident failed:", e);
        showToast("Failed to create incidents", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "+ Create Incidents";
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

// ---- Resolve Incident (get resolution steps from resolver agent) ----
async function resolveIncident(sysId, btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = "Generating…";
    try {
        const data = await apiPost("/api/resolve", { sys_id: sysId });
        showToast("Resolution guide generated", "success");
        await loadRecent();
    } catch (e) {
        console.error("Resolve failed:", e);
        showToast("Failed to generate resolution", "error");
        btnEl.textContent = "Retry";
        btnEl.disabled = false;
    }
}

function toggleResolution(headerEl) {
    const body = headerEl.nextElementSibling;
    const toggle = headerEl.querySelector(".resolution-toggle");
    if (body.style.display === "none") {
        body.style.display = "block";
        toggle.textContent = "▼";
    } else {
        body.style.display = "none";
        toggle.textContent = "▶";
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
