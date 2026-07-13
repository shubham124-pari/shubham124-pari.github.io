// =====================================================
// admin.html logic
// Relies on globals from auth.js: skpApiRequest, skpGetSessionUser,
// skpVerifySession, skpSignOut.
// The backend re-checks role="admin" fresh from the DB on every
// /api/admin/* call — this frontend gate is just for UX (hiding the
// panel from non-admins), never the real security boundary.
// =====================================================

document.addEventListener("DOMContentLoaded", async () => {

    const guard = document.getElementById("adminGuard");
    const guardText = document.getElementById("adminGuardText");
    const shell = document.getElementById("adminShell");
    const adminSignInBtn = document.getElementById("adminSignInBtn");

    const tabs = document.querySelectorAll("#adminTabs .account-tab");
    const panels = document.querySelectorAll(".account-panel");

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str == null ? "" : String(str);
        return div.innerHTML;
    }

    function formatDate(iso) {
        if (!iso) return "";
        try {
            return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
        } catch (e) {
            return "";
        }
    }

    function showAlert(el, type, text) {
        if (!el) return;
        el.textContent = text;
        el.className = "auth-alert show " + type;
    }

    if (adminSignInBtn) {
        adminSignInBtn.addEventListener("click", () => {
            const btn = document.getElementById("signInBtn");
            if (btn) btn.click();
        });
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.toggle("active", t === tab));
            const targetId = tab.dataset.atab + "Panel";
            panels.forEach((p) => p.classList.toggle("active", p.id === targetId));
        });
    });

    // ---------------- Guard ----------------

    async function boot() {
        const cached = skpGetSessionUser();
        if (!cached) {
            guard.style.display = "block";
            return;
        }
        const user = await skpVerifySession();
        if (!user) {
            guard.style.display = "block";
            return;
        }
        if (user.role !== "admin") {
            guardText.textContent = "This account doesn't have admin access.";
            adminSignInBtn.style.display = "none";
            guard.style.display = "block";
            return;
        }

        shell.style.display = "block";
        loadOverview();
        loadUsers();
        loadMessages();
    }

    // ---------------- Overview ----------------

    async function loadOverview() {
        try {
            const data = await skpApiRequest("/admin/analytics", { auth: true });
            document.getElementById("statUsers").textContent = data.total_users ?? "–";
            document.getElementById("statProjects").textContent = data.total_projects ?? "–";
            document.getElementById("statMessages").textContent = data.total_messages ?? "–";
            document.getElementById("statNewMessages").textContent = data.new_messages ?? "–";
            document.getElementById("statChats").textContent = data.total_chatbot_conversations ?? "–";

            drawBarChart("signupsChart", zeroFillLast7Days(data.signups_last_7_days), "#38bdf8");
            drawBarChart("chatsChart", zeroFillLast7Days(data.chats_last_7_days), "#a855f7");
        } catch (err) {
            // stats are non-critical; fail quietly
        }
    }

    // The backend only returns rows for days that had activity, so gaps
    // (a day with zero signups/chats) would otherwise just be missing
    // instead of showing as a zero bar. Fill in the last 7 calendar days
    // here so the chart always has a bar for every day.
    function zeroFillLast7Days(rows) {
        const byDay = {};
        (rows || []).forEach((row) => {
            const key = new Date(row.day).toISOString().slice(0, 10);
            byDay[key] = row.total;
        });

        const result = [];
        const today = new Date();
        for (let i = 6; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(d.getDate() - i);
            const key = d.toISOString().slice(0, 10);
            result.push({
                label: d.toLocaleDateString(undefined, { weekday: "short" }),
                value: byDay[key] || 0,
            });
        }
        return result;
    }

    // Minimal dependency-free bar chart on <canvas>. Deliberately not
    // pulling in a charting library for two small bar charts — keeps the
    // static frontend at zero extra network requests / build steps.
    function drawBarChart(canvasId, points, color) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const width = canvas.width;
        const height = canvas.height;
        const padding = 28;

        ctx.clearRect(0, 0, width, height);

        const maxValue = Math.max(1, ...points.map((p) => p.value));
        const chartHeight = height - padding * 2;
        const barSlot = (width - padding * 2) / points.length;
        const barWidth = barSlot * 0.55;

        ctx.strokeStyle = "rgba(255,255,255,0.12)";
        ctx.beginPath();
        ctx.moveTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();

        ctx.font = "11px Sora, sans-serif";
        ctx.textAlign = "center";

        points.forEach((point, i) => {
            const barHeight = (point.value / maxValue) * chartHeight;
            const x = padding + i * barSlot + (barSlot - barWidth) / 2;
            const y = height - padding - barHeight;

            ctx.fillStyle = color;
            ctx.fillRect(x, y, barWidth, Math.max(barHeight, point.value > 0 ? 2 : 0));

            ctx.fillStyle = "#94a3b8";
            ctx.fillText(point.label, x + barWidth / 2, height - padding + 16);

            if (point.value > 0) {
                ctx.fillStyle = "#e2e8f0";
                ctx.fillText(String(point.value), x + barWidth / 2, y - 6);
            }
        });
    }

    // ---------------- Users ----------------

    const usersTableBody = document.getElementById("usersTableBody");
    const usersEmpty = document.getElementById("usersEmpty");
    const usersAlert = document.getElementById("usersAlert");

    async function loadUsers() {
        try {
            const data = await skpApiRequest("/admin/users", { auth: true });
            renderUsers(data.users || []);
        } catch (err) {
            showAlert(usersAlert, "error", err.message);
        }
    }

    function renderUsers(users) {
        usersTableBody.innerHTML = "";
        usersEmpty.style.display = users.length === 0 ? "block" : "none";

        const me = skpGetSessionUser();

        users.forEach((u) => {
            const tr = document.createElement("tr");
            const roleBadge = `<span class="admin-badge ${u.role === "admin" ? "admin" : "user"}">${escapeHtml(u.role)}</span>`;
            const banBadge = u.is_banned ? ' <span class="admin-badge banned">banned</span>' : "";

            const isSelf = me && me.id === u.id;

            tr.innerHTML = `
                <td>${escapeHtml(u.name)}</td>
                <td>${escapeHtml(u.email)}</td>
                <td>${roleBadge}${banBadge}</td>
                <td>${escapeHtml(formatDate(u.created_at))}</td>
                <td>
                    <div class="admin-row-actions">
                        <button type="button" class="ban-btn">${u.is_banned ? "Unban" : "Ban"}</button>
                        <button type="button" class="danger delete-user-btn" ${isSelf ? "disabled title=\"You can't delete your own account here\"" : ""}>Delete</button>
                    </div>
                </td>
            `;

            tr.querySelector(".ban-btn").addEventListener("click", async () => {
                try {
                    await skpApiRequest(`/admin/users/${u.id}/ban`, {
                        method: "PUT", auth: true, body: { is_banned: !u.is_banned },
                    });
                    loadUsers();
                } catch (err) {
                    showAlert(usersAlert, "error", err.message);
                }
            });

            const deleteBtn = tr.querySelector(".delete-user-btn");
            if (!isSelf) {
                deleteBtn.addEventListener("click", async () => {
                    if (!confirm(`Permanently delete ${u.name} (${u.email})? This can't be undone.`)) return;
                    try {
                        await skpApiRequest(`/admin/users/${u.id}`, { method: "DELETE", auth: true });
                        loadUsers();
                        loadOverview();
                    } catch (err) {
                        showAlert(usersAlert, "error", err.message);
                    }
                });
            }

            usersTableBody.appendChild(tr);
        });
    }

    // ---------------- Messages ----------------

    const messagesTableBody = document.getElementById("messagesTableBody");
    const messagesEmpty = document.getElementById("messagesEmpty");
    const messagesAlert = document.getElementById("messagesAlert");

    async function loadMessages() {
        try {
            const data = await skpApiRequest("/admin/messages", { auth: true });
            renderMessages(data.messages || []);
        } catch (err) {
            showAlert(messagesAlert, "error", err.message);
        }
    }

    function renderMessages(messages) {
        messagesTableBody.innerHTML = "";
        messagesEmpty.style.display = messages.length === 0 ? "block" : "none";

        messages.forEach((m) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${escapeHtml(m.name)}<br><span class="account-meta" style="margin:0;text-align:left;opacity:0.7;">${escapeHtml(m.email)}</span></td>
                <td>
                    <strong>${escapeHtml(m.subject || "(no subject)")}</strong><br>
                    <span style="color:var(--text-light);font-size:0.82rem;">${escapeHtml(m.message.slice(0, 140))}${m.message.length > 140 ? "…" : ""}</span>
                </td>
                <td>
                    <select class="status-select">
                        <option value="new" ${m.status === "new" ? "selected" : ""}>New</option>
                        <option value="read" ${m.status === "read" ? "selected" : ""}>Read</option>
                        <option value="resolved" ${m.status === "resolved" ? "selected" : ""}>Resolved</option>
                    </select>
                </td>
                <td>${escapeHtml(formatDate(m.date))}</td>
                <td>
                    <div class="admin-row-actions">
                        <button type="button" class="danger delete-message-btn">Delete</button>
                    </div>
                </td>
            `;

            tr.querySelector(".status-select").addEventListener("change", async (e) => {
                try {
                    await skpApiRequest(`/admin/messages/${m.id}/status`, {
                        method: "PUT", auth: true, body: { status: e.target.value },
                    });
                    loadOverview();
                } catch (err) {
                    showAlert(messagesAlert, "error", err.message);
                }
            });

            tr.querySelector(".delete-message-btn").addEventListener("click", async () => {
                if (!confirm("Delete this message?")) return;
                try {
                    await skpApiRequest(`/admin/messages/${m.id}`, { method: "DELETE", auth: true });
                    loadMessages();
                    loadOverview();
                } catch (err) {
                    showAlert(messagesAlert, "error", err.message);
                }
            });

            messagesTableBody.appendChild(tr);
        });
    }

    boot();
});
